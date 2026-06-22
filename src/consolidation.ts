// Overnight self-improvement pipeline (local edition of the Railway+Inngest worker):
// collect → extract → resolve/dedupe → reflect/grade → update → EVAL GATE → emit.
// Promotions are written as OKF and committed to git; a failing gate rolls back via
// git. Extraction is heuristic-first (works offline); a ChatModel can refine it.

import crypto from "node:crypto";
import path from "node:path";
import type { EngramConfig } from "./config.js";
import type { Db } from "./db.js";
import { type ChatModel, type EmbeddingModel, approxTokens } from "./gateway.js";
import { Git } from "./git.js";
import { rebuildIndex } from "./indexer.js";
import { readConcept, writeConcept, serializeOkf, type OkfDoc } from "./okf.js";
import { search } from "./retrieval.js";
import type { RunReport } from "./types.js";

function uid(p: string): string {
  return `${p}_${crypto.randomBytes(6).toString("hex")}`;
}
function today(): string {
  return new Date().toISOString().slice(0, 10);
}
function slug(s: string): string {
  return s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 48) || "item";
}

interface EpRow {
  id: string;
  kind: string;
  payload: string;
  task_id: string | null;
  created_at: string;
  usefulness: number;
}

interface Candidate {
  concept_id: string;
  okf_type: string;
  title: string;
  description: string;
  body: string;
  provenance: string[]; // episodic event ids
  value: number;
  confidence: number;
  contradicts?: string;
}

export interface ConsolidateOptions {
  dryRun?: boolean;
  noCommit?: boolean;
}

export async function consolidate(
  cfg: EngramConfig,
  db: Db,
  embed: EmbeddingModel,
  chat: ChatModel,
  opts: ConsolidateOptions = {},
): Promise<RunReport> {
  const git = new Git(cfg.brainDir);
  const runId = uid("run");
  const startedAt = new Date().toISOString();
  const versionBefore = git.headSha();
  let tokenCost = 0;
  const notes: string[] = [];

  db.run(
    "INSERT INTO consolidation_runs(id, org_id, started_at, status, memory_version_before) VALUES(?,?,?,?,?)",
    runId,
    cfg.orgId,
    startedAt,
    "running",
    versionBefore,
  );
  db.audit(cfg.orgId, "worker", "consolidate:start", runId);

  const finish = (
    status: RunReport["status"],
    counts: { candidates: number; promoted: number; quarantined: number; rolledBack: boolean },
    versionAfter: string | null,
    metrics: Record<string, number>,
  ): RunReport => {
    const finishedAt = new Date().toISOString();
    db.run(
      "UPDATE consolidation_runs SET finished_at=?, status=?, token_cost=?, candidates=?, promoted=?, quarantined=?, rolled_back=?, memory_version_after=?, notes=? WHERE id=?",
      finishedAt,
      status,
      tokenCost,
      counts.candidates,
      counts.promoted,
      counts.quarantined,
      counts.rolledBack ? 1 : 0,
      versionAfter,
      JSON.stringify(notes),
      runId,
    );
    for (const [m, v] of Object.entries(metrics)) {
      db.run("INSERT INTO run_metrics(run_id, metric, value) VALUES(?,?,?)", runId, m, v);
    }
    db.audit(cfg.orgId, "worker", `consolidate:${status}`, runId);
    return {
      run_id: runId,
      started_at: startedAt,
      finished_at: finishedAt,
      status,
      candidates: counts.candidates,
      promoted: counts.promoted,
      quarantined: counts.quarantined,
      rolled_back: counts.rolledBack,
      token_cost: tokenCost,
      memory_version_before: versionBefore,
      memory_version_after: versionAfter,
      metrics,
      notes,
    };
  };

  // ---- collect ----
  const events = db.all<EpRow>(
    "SELECT id, kind, payload, task_id, created_at, usefulness FROM episodic_events WHERE org_id = ? AND consolidated = 0 AND redacted = 0 ORDER BY created_at ASC",
    cfg.orgId,
  );
  if (events.length === 0) {
    notes.push("No new episodic events to consolidate.");
    return finish("no_changes", { candidates: 0, promoted: 0, quarantined: 0, rolledBack: false }, versionBefore, {});
  }
  tokenCost += approxTokens(events.map((e) => e.payload).join(" "));
  if (tokenCost > cfg.runTokenCap) {
    notes.push("Cost cap reached during collect.");
    return finish("capped", { candidates: 0, promoted: 0, quarantined: 0, rolledBack: false }, versionBefore, {});
  }

  // ---- extract (heuristic; untrusted content handled strictly as data) ----
  const candByConcept = new Map<string, Candidate>();
  const parse = (p: string) => {
    try {
      return JSON.parse(p) as any;
    } catch {
      return { content: p };
    }
  };

  // Procedures from task outcomes (what worked / dead ends).
  const byTask = new Map<string, EpRow[]>();
  for (const e of events) {
    if (!e.task_id) continue;
    (byTask.get(e.task_id) ?? byTask.set(e.task_id, []).get(e.task_id)!).push(e);
  }
  for (const [taskId, evs] of byTask) {
    const outcome = evs.find((e) => e.kind === "outcome");
    if (!outcome) continue;
    const meta = parse(outcome.payload).metadata ?? {};
    const status = meta.status ?? "unknown";
    const sources = (meta.sources_used ?? []) as { uri: string; useful: boolean }[];
    const worked = sources.filter((s) => s.useful).map((s) => s.uri);
    const deadEnds = sources.filter((s) => !s.useful).map((s) => s.uri);
    const conceptId = `procedures/${slug(taskId)}`;
    const observations = evs
      .filter((e) => e.kind === "observation")
      .map((e) => `- ${String(parse(e.payload).content ?? "").slice(0, 300)}`)
      .join("\n");
    const body = [
      `> Learned procedure for task type \`${taskId}\` (last outcome: **${status}**).`,
      "",
      "## Recipe",
      observations || "_No detailed steps captured yet._",
      "",
      "## Preferred sources",
      worked.length ? worked.map((u) => `- ${u}`).join("\n") : "_None recorded._",
      "",
      "## Known dead ends",
      deadEnds.length ? deadEnds.map((u) => `- ${u}`).join("\n") : "_None recorded._",
    ].join("\n");
    candByConcept.set(conceptId, {
      concept_id: conceptId,
      okf_type: "Playbook",
      title: `Procedure: ${taskId}`,
      description: `How to do "${taskId}" well, distilled from session outcomes.`,
      body,
      provenance: evs.map((e) => e.id),
      value: status === "success" ? 0.85 : 0.6,
      confidence: Math.min(0.95, 0.55 + 0.1 * evs.length),
    });
  }

  // Corrections → updates to existing concepts (or new correction notes).
  for (const e of events.filter((x) => x.kind === "correction")) {
    const pay = parse(e.payload);
    const meta = pay.metadata ?? {};
    const target: string = meta.target ?? "";
    const existing = target && readConcept(cfg.brainDir, target);
    if (existing) {
      // Append a correction; detect a naive contradiction with existing body.
      const contradicts =
        /\b(not|never|wrong|incorrect|actually)\b/i.test(String(pay.content)) ? target : undefined;
      const merged = candByConcept.get(target);
      const note = `\n\n> **Correction (${today()}):** ${String(pay.content).slice(0, 500)}`;
      const base = merged?.body ?? `${existing.body}`;
      candByConcept.set(target, {
        concept_id: target,
        okf_type: typeof existing.frontmatter.type === "string" ? existing.frontmatter.type : "concept",
        title: typeof existing.frontmatter.title === "string" ? existing.frontmatter.title : target,
        description:
          typeof existing.frontmatter.description === "string" ? existing.frontmatter.description : "",
        body: base + note,
        provenance: [...(merged?.provenance ?? []), e.id],
        value: 0.9,
        confidence: 0.9,
        contradicts,
      });
    } else {
      const conceptId = `notes/corrections/${slug(target || pay.content || e.id)}`;
      candByConcept.set(conceptId, {
        concept_id: conceptId,
        okf_type: "concept",
        title: `Correction: ${target || "general"}`,
        description: "A correction recorded during a session.",
        body: `> ${String(pay.content).slice(0, 800)}`,
        provenance: [e.id],
        value: 0.8,
        confidence: 0.85,
      });
    }
  }

  const candidates = [...candByConcept.values()].filter((c) => c.provenance.length > 0);
  tokenCost += approxTokens(candidates.map((c) => c.body).join(" "));

  // ---- reflect/grade: quarantine contradictions; require provenance ----
  const promote: Candidate[] = [];
  let quarantined = 0;
  for (const c of candidates) {
    if (c.provenance.length === 0) {
      notes.push(`Rejected unprovenanced candidate ${c.concept_id}.`);
      continue;
    }
    if (c.contradicts) {
      db.run(
        "INSERT INTO quarantine(id, org_id, run_id, concept_id, candidate, contradicts, reason, created_at) VALUES(?,?,?,?,?,?,?,?)",
        uid("q"),
        cfg.orgId,
        runId,
        c.concept_id,
        JSON.stringify(c),
        c.contradicts,
        "Candidate contradicts existing memory; needs human review.",
        new Date().toISOString(),
      );
      quarantined++;
      notes.push(`Quarantined ${c.concept_id} (contradiction).`);
      continue;
    }
    if (c.value >= 0.6) promote.push(c);
  }

  if (opts.dryRun) {
    notes.push("Dry run: no files written, no commit.");
    return finish(
      "no_changes",
      { candidates: candidates.length, promoted: 0, quarantined, rolledBack: false },
      versionBefore,
      { dry_run: 1 },
    );
  }

  // Baseline for the eval gate: measure how retrievable existing concepts are
  // BEFORE the update, so the gate fires only on a genuine regression.
  const baseline = db.all<{ id: string; title: string }>(
    "SELECT id, title FROM semantic_nodes WHERE org_id = ?",
    cfg.orgId,
  );
  let baselineHits = 0;
  for (const b of baseline) {
    const res = await search(cfg, db, embed, b.title, { limit: 8 });
    if (res.some((r) => r.concept_id === b.id)) baselineHits++;
  }
  const baselineRecall = baseline.length ? baselineHits / baseline.length : 1;

  // ---- update: write OKF files + provenance ----
  const writtenPaths: string[] = [];
  const createdPaths: string[] = []; // newly created (not previously on disk)
  for (const c of promote) {
    const existing = readConcept(cfg.brainDir, c.concept_id);
    if (!existing) createdPaths.push(`${c.concept_id}.md`);
    const version =
      existing && typeof existing.frontmatter.engram_version === "number"
        ? (existing.frontmatter.engram_version as number) + 1
        : 1;
    const doc: OkfDoc = {
      frontmatter: {
        type: c.okf_type,
        title: c.title,
        description: c.description,
        timestamp: today(),
        tags: ["consolidated"],
        engram_visibility: "private",
        engram_confidence: Number(c.confidence.toFixed(2)),
        engram_version: version,
        engram_node_id: c.concept_id,
        provenance: c.provenance.map((id) => ({ source_event_id: id })),
      },
      body: c.body,
    };
    const full = writeConcept(cfg.brainDir, c.concept_id, doc);
    writtenPaths.push(full);
    // Provenance coverage = 100% by construction.
    for (const ev of c.provenance) {
      db.run(
        "INSERT INTO provenance(memory_id, memory_type, source_event_id, source_uri, weight, created_at) VALUES(?,?,?,?,?,?)",
        c.concept_id,
        "node",
        ev,
        null,
        1.0,
        new Date().toISOString(),
      );
    }
  }

  // Reindex so retrieval reflects the new bundle (DERIVED from files).
  await rebuildIndex(cfg, db, embed);

  // ---- EVAL GATE ----
  let recallHits = 0;
  for (const b of baseline) {
    const res = await search(cfg, db, embed, b.title, { limit: 8 });
    if (res.some((r) => r.concept_id === b.id)) recallHits++;
  }
  const recall = baseline.length ? recallHits / baseline.length : 1;
  const provCoverage =
    promote.length === 0
      ? 1
      : promote.filter((c) => c.provenance.length > 0).length / promote.length;
  // Regression = a DROP relative to the pre-update baseline (not vs. a perfect 1.0).
  const recallDrop = baselineRecall - recall;
  const costDelta = 0; // local heuristic extraction has negligible marginal cost

  const metrics = {
    recall: Number(recall.toFixed(3)),
    baseline_recall: Number(baselineRecall.toFixed(3)),
    recall_drop: Number(recallDrop.toFixed(3)),
    provenance_coverage: Number(provCoverage.toFixed(3)),
    cost_delta: costDelta,
    promoted: promote.length,
    quarantined,
  };

  const regressed =
    recallDrop > cfg.evalThresholds.recall + 1e-9 ||
    provCoverage < 1 - 1e-9 ||
    costDelta > cfg.evalThresholds.cost;

  if (regressed) {
    // ---- ROLLBACK (git op) ----
    notes.push(
      `Eval gate FAILED (recall=${recall.toFixed(2)}, provenance=${provCoverage.toFixed(2)}). Rolling back.`,
    );
    const fs = await import("node:fs");
    if (git.available && versionBefore) {
      // Restore tracked files to the prior commit...
      git.revertTo(versionBefore, git.bundleRelPath());
    } else {
      // No git: physically remove every file we just wrote.
      for (const p of writtenPaths) {
        try {
          fs.rmSync(p);
        } catch {
          /* ignore */
        }
      }
    }
    // ...and remove NEW files git checkout leaves behind (untracked additions).
    for (const rel of createdPaths) {
      try {
        fs.rmSync(path.join(cfg.brainDir, rel));
      } catch {
        /* ignore */
      }
    }
    await rebuildIndex(cfg, db, embed);
    return finish(
      "rolled_back",
      { candidates: candidates.length, promoted: 0, quarantined, rolledBack: true },
      versionBefore,
      metrics,
    );
  }

  // ---- emit: update log.md, mark consolidated, commit ----
  if (promote.length > 0) {
    appendLog(cfg, runId, promote, quarantined);
  }
  for (const e of events) {
    db.run("UPDATE episodic_events SET consolidated = 1 WHERE id = ?", e.id);
  }

  let versionAfter = versionBefore;
  if (promote.length > 0 && git.available && !opts.noCommit) {
    const rel = git.bundleRelPath();
    const sha = git.commit(
      [rel],
      `engram: consolidate ${runId} — +${promote.length} concept(s), ${quarantined} quarantined`,
    );
    versionAfter = sha ?? versionBefore;
    if (sha) {
      db.setMeta("memory_version", sha);
      notes.push(`Committed memory version ${sha.slice(0, 8)}.`);
    }
  }

  const status: RunReport["status"] = promote.length > 0 ? "promoted" : "no_changes";
  notes.push(`Promoted ${promote.length}, quarantined ${quarantined}.`);
  return finish(
    status,
    { candidates: candidates.length, promoted: promote.length, quarantined, rolledBack: false },
    versionAfter,
    metrics,
  );
}

function appendLog(cfg: EngramConfig, runId: string, promoted: Candidate[], quarantined: number): void {
  const logId = "log";
  const existing = readConcept(cfg.brainDir, logId);
  const date = today();
  const entry = [
    `## ${date}`,
    "",
    `- Consolidation run \`${runId}\`: promoted ${promoted.length} concept(s), ${quarantined} quarantined.`,
    ...promoted.map((c) => `  - Updated [${c.title}](${c.concept_id}.md)`),
    "",
  ].join("\n");

  if (existing) {
    // Insert newest-first after the first heading block.
    const body = existing.body;
    const firstDate = body.search(/^## \d{4}-\d{2}-\d{2}/m);
    const newBody =
      firstDate === -1 ? `${body}\n\n${entry}` : `${body.slice(0, firstDate)}${entry}\n${body.slice(firstDate)}`;
    writeConcept(cfg.brainDir, logId, { frontmatter: existing.frontmatter, body: newBody });
  } else {
    writeConcept(cfg.brainDir, logId, {
      frontmatter: {
        type: "Log",
        title: "Update Log",
        description: "Change history for this brain, newest first.",
        timestamp: date,
        tags: ["log"],
        engram_visibility: "private",
      },
      body: entry,
    });
  }
}
