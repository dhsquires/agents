# Design: add-self-improving-memory

## 1. Context

Engram is a memory **service**, not a model. Any MCP-enabled agent (Claude, or any other
client speaking MCP) attaches to it. The agent reads a context pack at the start of a task
and writes back observations, outcomes, and corrections during the task. Overnight, a
durable worker turns that raw stream into a refined context graph and learns how to do the
work better, behind an eval gate.

Three architectural decisions were fixed by the requester:

- **Audience:** company employees → one org, many users, per-user isolation plus shared
  team/org memory.
- **Overnight compute:** an **external worker on Railway**, orchestrated by **Inngest**.
- **Capture:** **hybrid** — active MCP write tools *and* overnight synthesis.

## 2. The memory model (three layers + a graph)

| Layer | What it holds | Lifecycle |
|---|---|---|
| **Episodic** | Raw per-session events: task framing, tool calls, outcomes (success/failure), corrections, sources used and whether each was useful or a dead end | Append-only; decays; TTL + usefulness threshold |
| **Semantic** ("the wiki") | Consolidated, deduplicated entities & facts: People, Projects, Connectors, Artifacts, Concepts | Versioned pages; updated overnight; provenance edges |
| **Procedural** | Learned "how to do task type T well here": recipes, preferred sources, known dead ends, correction-derived rules | Versioned; the primary self-improvement payload |

All three are nodes in **one typed graph**.

- **Node kinds:** `person, project, connector, artifact, concept, procedure, source,
  session, task`.
- **Edge kinds:** `authored_by, part_of, derived_from, corrects, supersedes, cites,
  used_source, contradicts, relates_to`.
- **Edge attributes:** `confidence`, `recency`, `usefulness` (weights that retrieval and
  decay both read).
- The **"LLM wiki"** is simply the semantic nodes rendered as Markdown pages on demand and
  exposed as MCP Resources (`engram://wiki/{entity_id}`).

## 3. Data model (Postgres / Supabase)

```
orgs(id, name, created_at)
users(id, org_id, idp_subject, email, role, created_at)
memberships(user_id, team_id, role)                 -- team scoping
teams(id, org_id, name)

episodic_events(
  id, org_id, user_id, session_id, task_id,
  kind,                 -- observation | tool_call | outcome | correction | source_use
  payload jsonb,        -- typed, untrusted content (data, never instructions)
  visibility,           -- private | team | org
  created_at, decay_at)

semantic_nodes(
  id, org_id, node_kind, title, body_md,
  visibility, version, superseded_by,
  confidence numeric, created_at, updated_at)

semantic_edges(
  id, org_id, src_id, dst_id, edge_kind,
  confidence numeric, usefulness numeric, recency numeric, created_at)

procedures(
  id, org_id, task_type, recipe_md, preferred_sources jsonb,
  known_dead_ends jsonb, version, confidence, visibility, updated_at)

embeddings(
  owner_id, owner_type,           -- node | procedure | episodic
  org_id, embedding vector(N),    -- N from gateway model card
  model, created_at)              -- HNSW index; recomputed only on change

sources(id, org_id, uri, content_hash, snapshot_path, last_seen_at)
corrections(id, org_id, user_id, target_id, target_type, reason, created_at)

consolidation_runs(id, org_id, started_at, finished_at, status,
  token_cost numeric, candidates int, promoted int, quarantined int,
  rolled_back boolean, memory_version_before, memory_version_after)
run_metrics(run_id, metric, value)            -- correctness/recall/cost/turns/...
provenance(memory_id, memory_type, source_event_id, source_uri, weight)
audit_log(id, org_id, actor, action, target, scope, at)   -- append-only
redactions(id, org_id, selector jsonb, reason, requested_by, completed_at)
```

**Indexing.** `embeddings` uses an HNSW index (`vector_cosine_ops`). Lexical search uses a
`tsvector` GIN index over `semantic_nodes.body_md` and `episodic_events.payload`. Graph
traversal uses btree indexes on `semantic_edges(src_id)` / `(dst_id)` plus a recursive CTE
bounded to 1–2 hops.

## 4. Retrieval — assembling the context pack

At task start the agent calls `get_context_pack(task_descriptor, token_budget)`. The
Retrieval Engine runs three retrievers in parallel and fuses them:

1. **Lexical** — Postgres FTS over node bodies and recent episodic payloads.
2. **Vector** — pgvector kNN over node/procedure embeddings (HNSW).
3. **Graph** — 1–2 hop expansion from the top lexical/vector seeds along high-weight edges.

Results are fused (reciprocal-rank fusion), reranked, de-duplicated, and packed to the token
budget. **Every packed item carries its provenance** and a freshness/usefulness score.
Recency uses an exponential decay (60-day half-life by default, matching the requester's
established pattern); usefulness is updated by `record_outcome`.

## 5. Consolidation — the overnight self-improvement (Railway + Inngest)

A cron-triggered Inngest function fans out **per (org, user)** and runs durable steps with
retries and idempotency keys:

```
collect  → extract(fan-out) → resolve/dedupe → reflect/grade
        → update wiki + procedures → EVAL GATE → emit (report + provenance)
                                          │
                                   fail → ROLLBACK to memory_version_before
```

- **collect** — episodic events since last run + connector deltas + changed source docs +
  corrections.
- **extract** (map step, batched) — an LLM proposes candidate entities, facts, relations,
  procedures, and "lessons" (what worked / failed). Per-batch token cap.
- **resolve/dedupe** — entity resolution against existing semantic nodes (vector + lexical),
  then merge.
- **reflect/grade** — a reflector LLM scores each candidate for confidence + value and
  detects contradictions with current memory. High-value ⇒ promote; contradictions ⇒
  **quarantine** for Console review (never silently overwrite).
- **update** — upsert nodes/edges/procedures, bump versions, recompute embeddings only for
  changed items, decay/forget stale low-usefulness memories.
- **EVAL GATE** — replay a held-out task set (and synthetic probes); compute correctness /
  recall / cost deltas. If any metric regresses past its threshold, the whole batch is
  rolled back to `memory_version_before`.
- **emit** — write the run report, refresh provenance, and optionally surface proactive
  "opportunities / risks."

Idempotency: each step keyed by `(org_id, user_id, run_id, step)`; Inngest guarantees
at-least-once with dedupe so partial failures resume safely. Per-run **cost cap** halts a
run that exceeds its token budget and marks it `capped`.

## 6. MCP interface

Transport: **Streamable HTTP**. Auth: **OAuth 2.1** bearer; the IdP token is exchanged for a
short-lived, audience-bound JWT. The server validates the JWT, then sets request-scoped RLS
claims before any query. **Per-tool scopes:** `memory:read`, `memory:write`,
`memory:forget`, `memory:admin`.

| Tool | Scope | Purpose |
|---|---|---|
| `search` | read | ranked results + provenance for a query |
| `get_context_pack` | read | assembled, budgeted pack for a task |
| `trace` | read | full provenance chain for a memory id |
| `remember` | write | append an episodic observation |
| `record_outcome` | write | task status + sources used + usefulness (feedback loop) |
| `correct` | write | record a correction (high-signal edge) |
| `link` | write | add an explicit typed edge |
| `forget` | forget | request redaction / right-to-be-forgotten |

Resources expose wiki pages (`engram://wiki/{entity_id}`); a `load_context` MCP Prompt lets
clients pull a starter pack without bespoke wiring.

## 7. Container placement (why what runs where)

- **Console → Vercel.** Read-mostly UI; serverless functions are short-lived, so they do
  **not** run consolidation — they trigger and visualize it.
- **MCP server → Railway (container).** Streamable HTTP sessions favor a long-lived process;
  co-locating with the worker keeps DB latency low.
- **Consolidation worker → Railway + Inngest.** Durable, long-running, fan-out, retries —
  exactly Inngest's shape; Vercel/Supabase functions would time out.
- **Postgres/pgvector/Storage/Realtime → Supabase.** Single source of truth + RLS boundary.
- **Model + embedding providers → external, behind one gateway** so Engram stays
  vendor-neutral and model choice is a config change.

(Full C4 Context / Container / Component diagrams live in `architecture.html` and
`architecture.md`.)

## 8. Key decisions (ADRs, condensed)

- **ADR-1: One typed graph over separate stores.** Episodic/semantic/procedural share a
  node/edge schema → simpler provenance and traversal than three subsystems.
- **ADR-2: Postgres-native retrieval (pgvector + FTS + CTE) over an external vector DB.**
  Keeps the RLS boundary in one place and avoids a second consistency domain at our scale.
- **ADR-3: Inngest on Railway over pg_cron or Vercel Cron.** Durable multi-step fan-out with
  retries/idempotency is first-class; the others lack durable step semantics for a
  multi-stage learning job.
- **ADR-4: Eval gate + versioned rollback is mandatory.** "Self-improvement" without a
  regression guard is a liability; memory is versioned so a bad batch is reversible.
- **ADR-5: Ingested content is data, not instructions.** Hard rule across extraction and
  retrieval to defend against memory poisoning / indirect prompt injection.
- **ADR-6: Provider-agnostic gateway.** Embedding dimensionality and chat model are config;
  no lock-in, satisfying "any MCP-enabled LLM."

## 9. Open questions (for human decision)

1. Embedding provider/model (sets vector dimension `N` and the cost line). Default: a
   general-purpose hosted embedding behind the gateway.
2. Retention windows per memory layer and per visibility, and the legal owner of the
   forgetting policy.
3. Whether org-level memory writes require admin approval by default (recommended: yes).
