// Core memory operations behind the MCP write/governance tools and `trace`.
// Episodic writes land in SQLite immediately; canonical (semantic/procedural)
// knowledge becomes git-committed OKF via consolidation.

import crypto from "node:crypto";
import type { EngramConfig } from "./config.js";
import type { Db } from "./db.js";
import type { EpisodicKind, ProvenanceLink, Visibility } from "./types.js";

function uid(prefix: string): string {
  return `${prefix}_${crypto.randomBytes(8).toString("hex")}`;
}

function addDays(iso: string, days: number): string {
  const d = new Date(iso);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString();
}

export interface RememberInput {
  content: string;
  kind?: EpisodicKind;
  session_id?: string;
  task_id?: string;
  visibility?: Visibility;
  tags?: string[];
  metadata?: Record<string, unknown>;
}

/** Append an episodic observation. All content is stored as untrusted DATA. */
export function remember(cfg: EngramConfig, db: Db, input: RememberInput): { id: string } {
  const id = uid("ep");
  const now = new Date().toISOString();
  const kind: EpisodicKind = input.kind ?? "observation";
  const payload = {
    content: input.content,
    tags: input.tags ?? [],
    metadata: input.metadata ?? {},
    // Marker: ingested text is data, never instructions.
    _untrusted: true,
  };
  db.run(
    `INSERT INTO episodic_events(id, org_id, user_id, session_id, task_id, kind, payload, visibility, created_at, decay_at, usefulness)
     VALUES(?,?,?,?,?,?,?,?,?,?,?)`,
    id,
    cfg.orgId,
    cfg.userId,
    input.session_id ?? null,
    input.task_id ?? null,
    kind,
    JSON.stringify(payload),
    input.visibility ?? "private",
    now,
    addDays(now, cfg.episodicTtlDays),
    0.5,
  );
  db.audit(cfg.orgId, cfg.userId, `remember:${kind}`, id, input.visibility ?? "private");
  return { id };
}

export interface OutcomeInput {
  task_id: string;
  status: "success" | "failure" | "partial";
  sources_used?: { uri: string; useful: boolean }[];
  summary?: string;
  session_id?: string;
}

/** Record a task outcome and update the usefulness of the sources it cited
 * (closes the retrieval feedback loop). */
export function recordOutcome(cfg: EngramConfig, db: Db, input: OutcomeInput): { id: string } {
  const { id } = remember(cfg, db, {
    content: input.summary ?? `Task ${input.task_id} → ${input.status}`,
    kind: "outcome",
    task_id: input.task_id,
    session_id: input.session_id,
    metadata: { status: input.status, sources_used: input.sources_used ?? [] },
  });

  const now = new Date().toISOString();
  for (const s of input.sources_used ?? []) {
    const delta = s.useful ? 0.15 : -0.2;
    // Reflect usefulness onto matching source nodes and source records.
    db.run(
      "UPDATE semantic_edges SET usefulness = MAX(0, MIN(1, usefulness + ?)) WHERE dst_id IN (SELECT id FROM semantic_nodes WHERE body_md LIKE ? OR title LIKE ?)",
      delta,
      `%${s.uri}%`,
      `%${s.uri}%`,
    );
    const existing = db.get<{ id: string }>("SELECT id FROM sources WHERE uri = ?", s.uri);
    if (existing) {
      db.run("UPDATE sources SET last_seen_at = ? WHERE id = ?", now, existing.id);
    } else {
      db.run(
        "INSERT INTO sources(id, org_id, uri, last_seen_at) VALUES(?,?,?,?)",
        uid("src"),
        cfg.orgId,
        s.uri,
        now,
      );
    }
  }
  db.audit(cfg.orgId, cfg.userId, `record_outcome:${input.status}`, input.task_id);
  return { id };
}

export interface CorrectInput {
  target: string; // concept id or prior episodic id this corrects
  correction: string;
  reason?: string;
  task_id?: string;
}

/** Record a correction — a high-signal episodic event plus a `corrects` edge and
 * a correction record. Corrections outrank ordinary observations in retrieval. */
export function correct(cfg: EngramConfig, db: Db, input: CorrectInput): { id: string } {
  const now = new Date().toISOString();
  const ep = remember(cfg, db, {
    content: input.correction,
    kind: "correction",
    task_id: input.task_id,
    metadata: { target: input.target, reason: input.reason ?? "" },
  });
  // Corrections start more useful than ordinary observations.
  db.run("UPDATE episodic_events SET usefulness = 0.9 WHERE id = ?", ep.id);

  const corrId = uid("cor");
  db.run(
    "INSERT INTO corrections(id, org_id, user_id, target_id, target_type, reason, created_at) VALUES(?,?,?,?,?,?,?)",
    corrId,
    cfg.orgId,
    cfg.userId,
    input.target,
    "concept",
    input.reason ?? input.correction,
    now,
  );

  // If the target is an existing semantic node, add a high-weight corrects edge.
  const targetNode = db.get<{ id: string }>("SELECT id FROM semantic_nodes WHERE id = ?", input.target);
  if (targetNode) {
    db.run(
      "INSERT OR REPLACE INTO semantic_edges(id, org_id, src_id, dst_id, edge_kind, confidence, usefulness, recency, created_at) VALUES(?,?,?,?,?,?,?,?,?)",
      `${ep.id}->${input.target}:corrects`,
      cfg.orgId,
      ep.id,
      input.target,
      "corrects",
      0.95,
      0.95,
      1.0,
      now,
    );
  }
  db.audit(cfg.orgId, cfg.userId, "correct", input.target);
  return { id: corrId };
}

export interface LinkInput {
  src: string;
  dst: string;
  edge_kind: string;
  confidence?: number;
}

/** Add an explicit typed edge between two concepts. */
export function link(cfg: EngramConfig, db: Db, input: LinkInput): { id: string } {
  const id = `${input.src}->${input.dst}:${input.edge_kind}`;
  db.run(
    "INSERT OR REPLACE INTO semantic_edges(id, org_id, src_id, dst_id, edge_kind, confidence, usefulness, recency, created_at) VALUES(?,?,?,?,?,?,?,?,?)",
    id,
    cfg.orgId,
    input.src,
    input.dst,
    input.edge_kind,
    input.confidence ?? 0.7,
    0.5,
    1.0,
    new Date().toISOString(),
  );
  db.audit(cfg.orgId, cfg.userId, `link:${input.edge_kind}`, `${input.src}->${input.dst}`);
  return { id };
}

export interface ForgetInput {
  selector: Record<string, unknown>; // { query?, concept_id?, source_uri?, task_id? }
  reason: string;
}

/** Enqueue a redaction and run the cascade across episodic + provenance.
 * Returns once the cascade over the derived index has completed. Canonical
 * (committed) bundle redaction is reported as a follow-up git step. */
export function forget(
  cfg: EngramConfig,
  db: Db,
  input: ForgetInput,
): { id: string; removed_episodic: number; affected_concepts: string[]; needs_git_rewrite: boolean } {
  const now = new Date().toISOString();
  const id = uid("red");
  db.run(
    "INSERT INTO redactions(id, org_id, selector, reason, requested_by, requested_at) VALUES(?,?,?,?,?,?)",
    id,
    cfg.orgId,
    JSON.stringify(input.selector),
    input.reason,
    cfg.userId,
    now,
  );
  db.audit(cfg.orgId, cfg.userId, "forget:requested", JSON.stringify(input.selector));

  const sel = input.selector;
  let removed = 0;
  const affected: string[] = [];

  // Cascade over episodic events.
  if (typeof sel.task_id === "string") {
    const r = db.run("UPDATE episodic_events SET redacted = 1, payload = '{\"redacted\":true}' WHERE task_id = ?", sel.task_id);
    removed += Number(r.changes ?? 0);
  }
  if (typeof sel.query === "string") {
    const r = db.run(
      "UPDATE episodic_events SET redacted = 1, payload = '{\"redacted\":true}' WHERE payload LIKE ?",
      `%${sel.query}%`,
    );
    removed += Number(r.changes ?? 0);
  }
  if (typeof sel.source_uri === "string") {
    db.run("DELETE FROM provenance WHERE source_uri = ?", sel.source_uri);
    db.run("DELETE FROM sources WHERE uri = ?", sel.source_uri);
  }

  // Concepts derived from redacted data must be revisited; flag any that cite it.
  if (typeof sel.concept_id === "string") {
    affected.push(sel.concept_id);
    db.run("DELETE FROM embeddings WHERE owner_id = ? AND owner_type = 'node'", sel.concept_id);
  }

  // A committed bundle concept requires a git history rewrite to fully forget.
  const needsGit =
    typeof sel.concept_id === "string" &&
    !!db.get("SELECT 1 FROM semantic_nodes WHERE id = ?", sel.concept_id);

  db.run("UPDATE redactions SET completed_at = ? WHERE id = ?", now, id);
  db.audit(cfg.orgId, cfg.userId, "forget:cascaded", id);
  return { id, removed_episodic: removed, affected_concepts: affected, needs_git_rewrite: !!needsGit };
}

/** Full provenance chain for a memory id (concept or episodic). */
export function trace(
  cfg: EngramConfig,
  db: Db,
  memoryId: string,
): { memory_id: string; provenance: ProvenanceLink[]; edges: any[]; corrections: any[] } {
  const provenance = db.all<ProvenanceLink>(
    "SELECT memory_id, memory_type, source_event_id, source_uri, weight, created_at FROM provenance WHERE memory_id = ?",
    memoryId,
  );
  const edges = db.all(
    "SELECT src_id, dst_id, edge_kind, confidence, usefulness FROM semantic_edges WHERE src_id = ? OR dst_id = ?",
    memoryId,
    memoryId,
  );
  const corrections = db.all(
    "SELECT id, target_id, reason, created_at FROM corrections WHERE target_id = ?",
    memoryId,
  );
  return { memory_id: memoryId, provenance, edges, corrections };
}
