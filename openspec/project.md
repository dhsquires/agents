# Project: Engram — Self-Improving Memory Layer for MCP-Enabled Agents

> **Working name:** Engram (an *engram* is the physical trace a memory leaves behind).
> Generalizes Perplexity's "Brain" into a vendor-neutral memory substrate that any
> MCP-enabled LLM can attach to.

## Purpose

Give every MCP-enabled agent used inside the company a shared, self-improving memory
that remembers **what the agent did** — what worked, what failed, what was corrected,
which sources were reliable, and which were dead ends — and rewrites itself overnight so
each new task starts from a better place. Memory about the *user* is supported but
secondary; the primary purpose of memory here is to make the *work* better.

## Audience & tenancy

- **Single organization, multi-user** (company employees).
- Every memory is scoped by `org_id` and a `visibility` of `private` (one user),
  `team`, or `org`. There is exactly one org per deployment instance.
- Identity comes from the company IdP (OIDC/SSO). The MCP server and the Console both
  exchange the IdP token for a short-lived JWT that drives Postgres Row-Level Security.

## Tech stack (pinned)

| Layer | Choice | Version target |
|---|---|---|
| Frontend (Console) | Next.js (App Router) on Vercel | Next 15.x, React 19.x |
| MCP server | Node.js + TypeScript, `@modelcontextprotocol/sdk`, Streamable HTTP transport | Node 22 LTS, MCP SDK ≥ 1.x |
| Background worker | Node.js + TypeScript on Railway | Node 22 LTS |
| Durable orchestration | Inngest (cron, fan-out, retries, idempotency) | Inngest 3.x |
| Database | Supabase Postgres 15 + `pgvector` (HNSW) + `tsvector` FTS + RLS + Realtime | pgvector ≥ 0.7 |
| Object storage | Supabase Storage (raw artifacts / source snapshots) | — |
| Auth / IdP | OIDC via company IdP; tokens minted to Supabase-compatible JWTs | OAuth 2.1 |
| Model access | Provider-agnostic gateway (chat + embeddings behind one interface) | — |
| Spec tooling | OpenSpec (`@fission-ai/openspec`) | Node ≥ 20.19 |
| System of record | Git repository of OKF bundles (markdown + YAML frontmatter) | OKF v0.1 |
| Derived index | Postgres + pgvector + FTS, rebuilt from git by an Indexer service | — |
| Indexer / sync | Git-webhook-driven service that projects commits into the derived index | — |

## Conventions

- **Provenance is non-negotiable.** Every semantic or procedural memory MUST link back to
  the episodic event(s), source(s), or correction(s) it was derived from. No provenance ⇒
  not promotable.
- **Ingested content is data, never instructions.** Text pulled from sessions, documents,
  or connectors is treated as untrusted and is never executed as agent instructions.
- **Self-improvement must not regress.** Any overnight change to memory passes an eval gate
  before it goes live; a failing gate triggers automatic rollback to the prior memory
  version.
- **Forgetting is a first-class operation.** Redaction / right-to-be-forgotten cascades
  through episodic → semantic → procedural → embeddings.
- **Git-versioned OKF bundles are the system of record.** Semantic and procedural memory
  lives canonically as OKF (markdown + YAML frontmatter) in a git repository. Postgres
  (pgvector + FTS + graph edges) is a **derived, rebuildable index** — it can be dropped and
  reconstructed from the bundles at any commit. A memory version IS a git commit SHA.
- **Episodic memory stays in Postgres.** The raw, high-volume, privacy-sensitive event stream
  is mutable runtime state and is NOT committed to git; only consolidated semantic/procedural
  knowledge is.
- **Diagrams follow the C4 model** (Context → Container → Component) and are kept in
  `design.md` and the architecture HTML.
- **Specs use SHALL language and `#### Scenario:` blocks** with `WHEN` / `THEN` steps.
- Capabilities are small and composable; one change may touch several capability specs via
  delta files under `changes/<id>/specs/<capability>/spec.md`.

## Non-goals (for the initiating change)

- No public/multi-org SaaS control plane (single org per instance).
- No fine-tuning of base models; learning happens in the memory layer, not in weights.
- No replacement of existing connectors; Engram consumes their outputs.
