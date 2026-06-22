// Indexer: projects the git-versioned OKF bundle into the derived SQLite index
// (semantic nodes + embeddings + graph edges). Idempotent and fully rebuildable
// from any commit. memory_version is recorded as the bundle's git HEAD SHA.

import path from "node:path";
import type { EngramConfig } from "./config.js";
import type { Db } from "./db.js";
import type { EmbeddingModel } from "./gateway.js";
import { Git } from "./git.js";
import {
  walkBundle,
  readConcept,
  normalizeFrontmatter,
  okfTypeToNodeKind,
  conceptIdFromPath,
} from "./okf.js";
import type { EdgeKind } from "./types.js";

const LINK_RE = /\[[^\]]*\]\(([^)]+)\)/g;

/** Resolve a markdown link target to a concept id within the bundle, or null. */
function resolveLink(fromConceptId: string, target: string): string | null {
  if (/^[a-z]+:\/\//i.test(target) || target.startsWith("#") || target.startsWith("mailto:")) {
    return null;
  }
  const clean = target.split("#")[0].split("?")[0];
  if (!clean.endsWith(".md")) return null;
  const fromDir = path.posix.dirname(fromConceptId);
  const joined = path.posix.normalize(path.posix.join(fromDir, clean));
  return conceptIdFromPath(joined);
}

export async function rebuildIndex(
  cfg: EngramConfig,
  db: Db,
  embed: EmbeddingModel,
): Promise<{ nodes: number; edges: number; sha: string | null }> {
  const git = new Git(cfg.brainDir);
  const sha = git.headSha();

  // Wipe derived rows (episodic + runtime state are preserved).
  db.exec(
    "DELETE FROM semantic_nodes; DELETE FROM semantic_edges; DELETE FROM embeddings WHERE owner_type = 'node';",
  );

  const ids = walkBundle(cfg.brainDir);
  const now = new Date().toISOString();
  const bundleConceptIds = new Set(ids);

  const insertNode = (
    id: string,
    kind: string,
    okfType: string,
    title: string,
    description: string,
    body: string,
    visibility: string,
    version: number,
    confidence: number,
    tags: string[],
    sourcePath: string,
  ) =>
    db.run(
      `INSERT INTO semantic_nodes(id, org_id, node_kind, okf_type, title, description, body_md,
        visibility, version, superseded_by, confidence, tags, source_path, created_at, updated_at)
       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)`,
      id,
      cfg.orgId,
      kind,
      okfType,
      title,
      description,
      body,
      visibility,
      version,
      null,
      confidence,
      JSON.stringify(tags),
      sourcePath,
      now,
      now,
    );

  let nodeCount = 0;
  const texts: string[] = [];
  const textOwners: string[] = [];

  for (const id of ids) {
    const doc = readConcept(cfg.brainDir, id);
    if (!doc) continue;
    const fm = normalizeFrontmatter(doc.frontmatter, path.posix.basename(id));
    const kind = okfTypeToNodeKind(fm.type);
    insertNode(
      id,
      kind,
      fm.type,
      fm.title,
      fm.description,
      doc.body,
      fm.visibility,
      fm.version,
      fm.confidence,
      fm.tags,
      `${id}.md`,
    );
    nodeCount++;
    texts.push(`${fm.title}\n${fm.description}\n${doc.body}`);
    textOwners.push(id);

    // Carry provenance declared in frontmatter (engram extension key).
    const prov = doc.frontmatter["provenance"];
    if (Array.isArray(prov)) {
      for (const p of prov) {
        const uri = typeof p === "string" ? p : (p as any)?.source_uri ?? null;
        if (uri) {
          db.run(
            "INSERT INTO provenance(memory_id, memory_type, source_event_id, source_uri, weight, created_at) VALUES(?,?,?,?,?,?)",
            id,
            "node",
            null,
            String(uri),
            1.0,
            now,
          );
        }
      }
    }
  }

  // Embeddings for all nodes (recomputed on rebuild).
  if (texts.length) {
    const vecs = await embed.embed(texts);
    for (let i = 0; i < vecs.length; i++) {
      db.run(
        "INSERT INTO embeddings(owner_id, owner_type, org_id, dim, model, vec, created_at) VALUES(?,?,?,?,?,?,?) ON CONFLICT(owner_id, owner_type) DO UPDATE SET vec = excluded.vec, model = excluded.model",
        textOwners[i],
        "node",
        cfg.orgId,
        embed.dim,
        embed.id,
        JSON.stringify(vecs[i]),
        now,
      );
    }
  }

  // Edges from markdown links (rendered as relates_to; weights derived here).
  let edgeCount = 0;
  for (const id of ids) {
    const doc = readConcept(cfg.brainDir, id);
    if (!doc) continue;
    const seen = new Set<string>();
    let m: RegExpExecArray | null;
    LINK_RE.lastIndex = 0;
    while ((m = LINK_RE.exec(doc.body)) !== null) {
      const dst = resolveLink(id, m[1]);
      if (!dst || dst === id || seen.has(dst)) continue;
      seen.add(dst);
      const kind: EdgeKind = "relates_to";
      // A link to a missing concept is tolerated (not-yet-written knowledge).
      const weight = bundleConceptIds.has(dst) ? 0.7 : 0.4;
      db.run(
        "INSERT INTO semantic_edges(id, org_id, src_id, dst_id, edge_kind, confidence, usefulness, recency, created_at) VALUES(?,?,?,?,?,?,?,?,?)",
        `${id}->${dst}:${kind}`,
        cfg.orgId,
        id,
        dst,
        kind,
        weight,
        0.5,
        1.0,
        now,
      );
      edgeCount++;
    }
  }

  db.setMeta("memory_version", sha ?? "uncommitted");
  db.setMeta("embedding_model", embed.id);
  db.setMeta("indexed_at", now);
  db.audit(cfg.orgId, "indexer", "reindex", sha ?? "uncommitted", "bundle");

  return { nodes: nodeCount, edges: edgeCount, sha };
}
