# Tasks: add-self-improving-memory

> Implement top to bottom. Each task is atomic and independently checkable.
> `[ ]` = not started.

## 1. Foundations & schema
- [ ] 1.1 Provision Supabase project; enable `pgvector` and `pg_trgm`; set Postgres 15 baseline
- [ ] 1.2 Create core tables (orgs, users, teams, memberships) with `org_id` on every row
- [ ] 1.3 Create memory tables (episodic_events, semantic_nodes, semantic_edges, procedures)
- [ ] 1.4 Create `embeddings` table with `vector(N)`; add HNSW index (`vector_cosine_ops`)
- [ ] 1.5 Add FTS: `tsvector` columns + GIN indexes on node bodies and episodic payloads
- [ ] 1.6 Create governance tables (sources, corrections, provenance, audit_log, redactions)
- [ ] 1.7 Create ops tables (consolidation_runs, run_metrics) + memory-version sequence

## 2. Security & RLS
- [ ] 2.1 Write RLS policies: scope by `org_id` AND `visibility` (private/team/org)
- [ ] 2.2 Add request-scoped claim setter (`set_config`) invoked from the MCP/Console layer
- [ ] 2.3 Restrict the service role to the worker only; deny it from request-path roles
- [ ] 2.4 Add append-only trigger + revoke UPDATE/DELETE on `audit_log` and `provenance`
- [ ] 2.5 Implement OIDC→JWT exchange (audience-bound, short TTL) for Console and MCP
- [ ] 2.6 Define OAuth scopes: `memory:read|write|forget|admin`; map tools→scopes

## 3. Provider-agnostic model gateway
- [ ] 3.1 Define `ChatModel` and `EmbeddingModel` interfaces (provider-neutral)
- [ ] 3.2 Implement one default provider for each; read model + dimension `N` from config
- [ ] 3.3 Add per-call + per-run token accounting and a hard cost-cap guard

## 4. MCP server (Railway)
- [ ] 4.1 Stand up MCP server with `@modelcontextprotocol/sdk`, Streamable HTTP transport
- [ ] 4.2 Auth middleware: validate JWT, set RLS claims, enforce per-tool scope
- [ ] 4.3 Implement read tools: `search`, `get_context_pack`, `trace`
- [ ] 4.4 Implement write tools: `remember`, `record_outcome`, `correct`, `link`
- [ ] 4.5 Implement governance tool: `forget` (enqueues redaction)
- [ ] 4.6 Expose wiki Resources (`engram://wiki/{id}`) and a `load_context` Prompt
- [ ] 4.7 Sanitize all tool inputs; tag stored content as untrusted data

## 5. Retrieval engine
- [ ] 5.1 Lexical retriever (FTS) with org/visibility filters
- [ ] 5.2 Vector retriever (pgvector kNN, HNSW) with the same filters
- [ ] 5.3 Graph expander (recursive CTE, 1–2 hops, high-weight edges only)
- [ ] 5.4 Fusion + rerank + dedupe; attach provenance + freshness/usefulness
- [ ] 5.5 Context-pack assembler with token-budget packing and decay weighting

## 6. Consolidation worker (Railway + Inngest)
- [ ] 6.1 Inngest client + cron schedule; fan-out per `(org_id, user_id)`
- [ ] 6.2 `collect` step (episodic deltas + connector deltas + changed sources + corrections)
- [ ] 6.3 `extract` map step (batched, capped) → typed candidates
- [ ] 6.4 `resolve/dedupe` step (entity resolution + merge)
- [ ] 6.5 `reflect/grade` step (confidence/value scoring + contradiction detection)
- [ ] 6.6 `update` step (versioned upserts, incremental re-embedding, decay/forget)
- [ ] 6.7 **EVAL GATE** step (replay held-out + synthetic; compute deltas vs thresholds)
- [ ] 6.8 **ROLLBACK** path (restore `memory_version_before` on gate failure)
- [ ] 6.9 `emit` step (run report, provenance refresh, proactive opportunities/risks)
- [ ] 6.10 Idempotency keys per step; per-run cost cap → `capped` status

## 7. Console (Vercel / Next.js)
- [ ] 7.1 App scaffold with App Router; OIDC sign-in; Supabase RLS-aware data access
- [ ] 7.2 Wiki browser: graph view + entity pages with provenance links
- [ ] 7.3 Quarantine review: approve/reject contradicted candidates
- [ ] 7.4 Forgetting console: submit + track redaction requests
- [ ] 7.5 Run reports + KPI dashboards (Realtime status)
- [ ] 7.6 RBAC for `org`-scoped memory writes (admin approval flow)

## 8. Observability & metrics
- [ ] 8.1 Define KPI set + thresholds (correctness, recall, cost, turns, calls, precision@k,
      provenance coverage = 100%, contradiction rate, forgetting precision)
- [ ] 8.2 Instrument retrieval, tools, and runs; persist to `run_metrics`
- [ ] 8.3 Structured logs + traces across MCP, worker, gateway
- [ ] 8.4 Alert on eval-gate failure, cost-cap trip, contradiction-rate spike

## 9. Evaluation harness
- [ ] 9.1 Curate a held-out task set with graded answers
- [ ] 9.2 Synthetic probes for recall + injection resistance
- [ ] 9.3 Regression thresholds wired into the eval-gate step
- [ ] 9.4 Memory-poisoning red-team suite (untrusted-content injection cases)

## 11. OKF interchange
- [ ] 11.1 Add OKF document read/write (YAML frontmatter + body) with serialize/parse round-trip
- [ ] 11.2 Map `node_kind` ⇄ open OKF `type`; populate required `type`/`title`/`description`/`timestamp`
- [ ] 11.3 Concept-ID addressing (slug grammar) shared by bundle paths and `engram://wiki/{id}`
- [ ] 11.4 `export_bundle` — scope-filtered OKF bundle with `okf_version` in root `index.md`
- [ ] 11.5 `import_bundle` — ingest external/authored bundles as a provenance-tagged source
- [ ] 11.6 `get_index` + index-first retrieval mode (progressive disclosure)
- [ ] 11.7 Render structured provenance as `# Citations` + materialize `references/<slug>` concepts
- [ ] 11.8 Maintain `log.md` per scope from consolidation runs
- [ ] 11.9 Conformance check against the OKF reference validator + round-trip fidelity metric
- [ ] 11.10 Visibility-safe serialization + redaction cascade into retained bundle artifacts

## 12. Git-canonical store & indexer
- [ ] 12.1 Provision canonical git repo(s)/namespaces per visibility (private / team / org)
- [ ] 12.2 Map git repo/namespace permissions to employee identity (canonical access control)
- [ ] 12.3 Build the Indexer service: git webhook → rebuild derived Postgres index (edges, embeddings, FTS)
- [ ] 12.4 Make the derived index reproducible — rebuild from any commit SHA (DR + version pinning)
- [ ] 12.5 Consolidation commits OKF + log.md to a candidate branch; eval gate runs pre-merge
- [ ] 12.6 Merge-to-canonical + reindex on pass; revert/reset on fail (rollback = git op)
- [ ] 12.7 Wire memory_version = commit SHA through provenance, retrieval pinning, and run reports
- [ ] 12.8 Visibility-safe commit routing (concept → namespace matching its visibility)
- [ ] 12.9 RTBF runbook: PII-exclusion at consolidation + history-rewrite + reindex path
- [ ] 12.10 Index-freshness + rebuild-fidelity monitors and alerts

## 10. Validation & rollout
- [ ] 10.1 `openspec validate add-self-improving-memory --strict` passes
- [ ] 10.6 Round-trip an exported bundle through the OKF reference visualizer + validator
- [ ] 10.2 Seed one team in shadow mode (read-only context packs, no promotion)
- [ ] 10.3 Enable writes + nightly consolidation for the pilot team
- [ ] 10.4 Review KPI trend over 2 weeks; tune decay + thresholds
- [ ] 10.5 Org-wide enablement; document runbooks (rollback, redaction, incident)
