# Engram Architecture (local edition)

Engram is the local-first, install-anywhere implementation of the self-improving
memory layer specified in [`openspec/`](../openspec). The OpenSpec change
`add-self-improving-memory` describes the full vendor-neutral, multi-user cloud
deployment (Supabase + Vercel + Railway + Inngest + OAuth/OIDC). **This repository
ships the same architecture collapsed to a single machine** so any MCP-enabled
coding agent can use it with zero infrastructure.

## What maps to what

| Spec (cloud) | This repo (local) |
|---|---|
| Postgres + pgvector + FTS (derived index) | Node built-in **SQLite** (`node:sqlite`) + in-process hybrid scoring |
| Git repo of OKF bundles (system of record) | the **`brain/`** directory in *this git repo* |
| Indexer service (git webhook → reindex) | [`src/indexer.ts`](../src/indexer.ts), run on start / `engram index` |
| MCP server (Streamable HTTP, OAuth) | [`src/server.ts`](../src/server.ts) over **stdio**, local scope model |
| Consolidation worker (Railway + Inngest) | [`src/consolidation.ts`](../src/consolidation.ts), run via `engram consolidate` or the `consolidate` tool |
| Provider-agnostic model gateway | [`src/gateway.ts`](../src/gateway.ts): local hashed embeddings by default, OpenAI-compatible opt-in |
| Memory version = commit SHA | the bundle's git `HEAD`; rollback = `git checkout` |

## Three-layer memory over one typed graph

- **Episodic** — raw per-session events (`remember`, `record_outcome`, `correct`).
  Lives only in SQLite, append-only, decays. Never committed to git.
- **Semantic** — consolidated concepts, the "LLM wiki". Canonical as OKF markdown
  in `brain/`; projected into `semantic_nodes` + `embeddings`.
- **Procedural** — learned task recipes (`type: Playbook`), the primary
  self-improvement payload.

All three are nodes/edges in one graph (`semantic_nodes`, `semantic_edges`).

## Retrieval

`get_context_pack(task, token_budget)` runs three retrievers and fuses them:

1. **Lexical** — query-term coverage + frequency scoring over node bodies.
2. **Vector** — cosine over embeddings (local hashed bag-of-words by default).
3. **Graph** — 1–2 hop expansion from top seeds along high-weight edges.

Reciprocal-rank fusion → recency/usefulness/confidence reranking → dedupe →
token-budget packing. Every item carries provenance and a freshness score.
Recency uses an exponential decay (60-day half-life by default).

## Consolidation (the self-improvement loop)

```
collect → extract → resolve/dedupe → reflect/grade
        → update (write OKF) → EVAL GATE → emit (log.md + commit)
                                   │
                            fail → ROLLBACK to memory_version_before (git)
```

- **Provenance is mandatory** — an unprovenanced candidate is never promoted.
- **Contradictions are quarantined** — never silently overwritten (see the
  `quarantine` table; review via the CLI/DB).
- **Eval gate** — promotion must not drop retrieval recall below the baseline and
  must keep provenance coverage at 100%, or the batch rolls back.
- **Rollback is a git operation** — the bundle is restored to the prior commit.
- **Cost cap** — a run that exceeds `ENGRAM_RUN_TOKEN_CAP` halts as `capped`.

## Security / governance (local posture)

- Content from sessions/imports is stored as **untrusted data** (`_untrusted`
  marker) and is never executed as instructions.
- The **audit log is append-only** (enforced by SQLite triggers).
- `forget` cascades redaction across episodic + provenance + derived embeddings,
  and reports when a committed concept needs a git history rewrite.
- Per-tool **scopes** (`memory:read|write|forget|admin`) are enforced in the
  server; locally the single user holds all scopes unless `ENGRAM_ALLOWED_SCOPES`
  restricts them. The cloud spec binds these to OAuth 2.1.

## C4 (condensed)

- **Context:** a coding agent ⇄ Engram MCP server ⇄ the `brain/` git bundle.
- **Containers:** MCP server (stdio), CLI, derived SQLite index, OKF bundle in git.
- **Components:** indexer, retrieval engine, memory ops, consolidation pipeline,
  bundle interchange, model gateway.

The full ADRs and cloud diagrams live in
[`openspec/changes/add-self-improving-memory/design.md`](../openspec/changes/add-self-improving-memory/design.md).
