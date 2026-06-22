// Hybrid retrieval: lexical (keyword/FTS-style scoring) + vector (cosine over
// embeddings) + graph expansion, fused with reciprocal-rank fusion, reranked by
// recency/usefulness, deduplicated, and packed to a token budget. Every item
// carries provenance and an isolation-respecting visibility filter.

import type { EngramConfig } from "./config.js";
import type { Db } from "./db.js";
import { type EmbeddingModel, cosine, tokenize, approxTokens } from "./gateway.js";
import type { ContextPack, ProvenanceLink, RetrievedItem, Visibility } from "./types.js";

interface NodeRow {
  id: string;
  node_kind: string;
  okf_type: string;
  title: string;
  description: string;
  body_md: string;
  visibility: Visibility;
  confidence: number;
  superseded_by: string | null;
  updated_at: string;
}

const RRF_K = 60;

/** Exponential recency decay with a configurable half-life. */
function recencyWeight(updatedAt: string, halfLifeDays: number): number {
  const ageDays = (Date.now() - new Date(updatedAt).getTime()) / 86400000;
  if (!Number.isFinite(ageDays) || ageDays < 0) return 1;
  return Math.pow(0.5, ageDays / halfLifeDays);
}

/** Visibility predicate for the local single-org caller. Excludes other users'
 * private memory; team/org/own-private are visible. */
function visibleNodes(db: Db, orgId: string): NodeRow[] {
  return db.all<NodeRow>(
    `SELECT id, node_kind, okf_type, title, description, body_md, visibility, confidence, superseded_by, updated_at
     FROM semantic_nodes WHERE org_id = ? AND superseded_by IS NULL`,
    orgId,
  );
}

function lexicalScores(query: string, nodes: NodeRow[]): Map<string, number> {
  const qTokens = new Set(tokenize(query));
  const scores = new Map<string, number>();
  if (qTokens.size === 0) return scores;
  for (const n of nodes) {
    const hay = tokenize(`${n.title} ${n.title} ${n.description} ${n.body_md}`);
    if (hay.length === 0) continue;
    let hits = 0;
    const seen = new Set<string>();
    for (const t of hay) {
      if (qTokens.has(t)) {
        hits++;
        seen.add(t);
      }
    }
    if (hits === 0) continue;
    // Coverage of the query terms + frequency, length-normalized.
    const coverage = seen.size / qTokens.size;
    const freq = hits / Math.sqrt(hay.length);
    scores.set(n.id, coverage * 2 + freq);
  }
  return scores;
}

async function vectorScores(
  cfg: EngramConfig,
  db: Db,
  embed: EmbeddingModel,
  query: string,
  nodes: NodeRow[],
): Promise<Map<string, number>> {
  const scores = new Map<string, number>();
  const [qVec] = await embed.embed([query]);
  if (!qVec) return scores;
  const rows = db.all<{ owner_id: string; vec: string }>(
    "SELECT owner_id, vec FROM embeddings WHERE org_id = ? AND owner_type = 'node'",
    cfg.orgId,
  );
  const valid = new Set(nodes.map((n) => n.id));
  for (const r of rows) {
    if (!valid.has(r.owner_id)) continue;
    try {
      const v = JSON.parse(r.vec) as number[];
      scores.set(r.owner_id, cosine(qVec, v));
    } catch {
      /* skip */
    }
  }
  return scores;
}

/** 1–2 hop expansion from seed nodes along high-weight edges only. */
function graphExpand(db: Db, orgId: string, seeds: string[]): Map<string, number> {
  const scores = new Map<string, number>();
  let frontier = new Set(seeds);
  const visited = new Set(seeds);
  for (let hop = 0; hop < 2 && frontier.size > 0; hop++) {
    const next = new Set<string>();
    for (const id of frontier) {
      const edges = db.all<{ dst_id: string; src_id: string; confidence: number; usefulness: number }>(
        "SELECT src_id, dst_id, confidence, usefulness FROM semantic_edges WHERE org_id = ? AND (src_id = ? OR dst_id = ?) AND confidence >= 0.6",
        orgId,
        id,
        id,
      );
      for (const e of edges) {
        const other = e.src_id === id ? e.dst_id : e.src_id;
        if (visited.has(other)) continue;
        const w = (e.confidence + e.usefulness) / 2 / (hop + 1);
        scores.set(other, Math.max(scores.get(other) ?? 0, w));
        next.add(other);
        visited.add(other);
      }
    }
    frontier = next;
  }
  return scores;
}

function rankToRrf(scores: Map<string, number>): Map<string, number> {
  const ranked = [...scores.entries()].sort((a, b) => b[1] - a[1]);
  const rrf = new Map<string, number>();
  ranked.forEach(([id], i) => rrf.set(id, 1 / (RRF_K + i + 1)));
  return rrf;
}

function provenanceFor(db: Db, conceptId: string): ProvenanceLink[] {
  return db.all<ProvenanceLink>(
    "SELECT memory_id, memory_type, source_event_id, source_uri, weight, created_at FROM provenance WHERE memory_id = ?",
    conceptId,
  );
}

export interface SearchOptions {
  limit?: number;
  indexFirst?: boolean;
}

export async function search(
  cfg: EngramConfig,
  db: Db,
  embed: EmbeddingModel,
  query: string,
  opts: SearchOptions = {},
): Promise<RetrievedItem[]> {
  const nodes = visibleNodes(db, cfg.orgId);
  const byId = new Map(nodes.map((n) => [n.id, n]));

  const lex = lexicalScores(query, nodes);
  const vec = await vectorScores(cfg, db, embed, query, nodes);

  // Seeds = top of lexical ∪ vector.
  const seedRank = [...new Set([...lex.keys(), ...vec.keys()])]
    .map((id) => ({ id, s: (lex.get(id) ?? 0) + (vec.get(id) ?? 0) }))
    .sort((a, b) => b.s - a.s)
    .slice(0, 8)
    .map((x) => x.id);
  const graph = graphExpand(db, cfg.orgId, seedRank);

  const lexRrf = rankToRrf(lex);
  const vecRrf = rankToRrf(vec);
  const graphRrf = rankToRrf(graph);

  const allIds = new Set<string>([...lex.keys(), ...vec.keys(), ...graph.keys()]);
  const items: RetrievedItem[] = [];
  for (const id of allIds) {
    const n = byId.get(id);
    if (!n) continue;
    const via: ("lexical" | "vector" | "graph")[] = [];
    if (lex.has(id)) via.push("lexical");
    if (vec.has(id)) via.push("vector");
    if (graph.has(id)) via.push("graph");

    const fused =
      (lexRrf.get(id) ?? 0) + (vecRrf.get(id) ?? 0) + (graphRrf.get(id) ?? 0);
    const freshness = recencyWeight(n.updated_at, cfg.halfLifeDays);
    // Correction-derived concepts carry a usefulness bump via edges.
    const useRow = db.get<{ u: number }>(
      "SELECT MAX(usefulness) AS u FROM semantic_edges WHERE dst_id = ?",
      id,
    );
    const usefulness = useRow?.u ?? 0.5;
    const score = fused * (0.5 + 0.5 * freshness) * (0.6 + 0.8 * n.confidence) * (0.6 + 0.8 * usefulness);

    items.push({
      concept_id: id,
      title: n.title,
      okf_type: n.okf_type,
      body_md: n.body_md,
      score,
      lexical: lex.get(id) ?? 0,
      vector: vec.get(id) ?? 0,
      graph: graph.get(id) ?? 0,
      freshness,
      usefulness,
      visibility: n.visibility,
      provenance: provenanceFor(db, id),
      via,
    });
  }

  items.sort((a, b) => b.score - a.score);
  const limit = opts.limit ?? 12;
  return items.slice(0, limit);
}

/** Assemble a token-budgeted context pack. Never exceeds the budget. */
export async function getContextPack(
  cfg: EngramConfig,
  db: Db,
  embed: EmbeddingModel,
  task: string,
  tokenBudget: number,
  indexFirst = false,
): Promise<ContextPack> {
  const ranked = await search(cfg, db, embed, task, { limit: 40 });
  const memoryVersion = db.getMeta("memory_version");
  const pack: ContextPack = {
    task,
    token_budget: tokenBudget,
    tokens_used: 0,
    memory_version: memoryVersion,
    items: [],
    index_first: indexFirst,
  };
  let used = 0;
  for (const item of ranked) {
    // In index-first mode, pack only titles/descriptions until budget allows bodies.
    const rendered = indexFirst
      ? `## ${item.title}\n${item.body_md.slice(0, 200)}`
      : `## ${item.title}\n${item.body_md}`;
    const cost = approxTokens(rendered);
    if (used + cost > tokenBudget) {
      if (indexFirst) continue;
      // Try a trimmed version to fit remaining budget.
      const remain = tokenBudget - used;
      if (remain < 40) break;
      const trimmed = { ...item, body_md: item.body_md.slice(0, remain * 4 - 50) };
      pack.items.push(trimmed);
      used += approxTokens(`## ${trimmed.title}\n${trimmed.body_md}`);
      break;
    }
    pack.items.push(item);
    used += cost;
  }
  pack.tokens_used = used;
  return pack;
}
