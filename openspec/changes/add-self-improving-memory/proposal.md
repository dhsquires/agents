# Change: add-self-improving-memory

## Why

Agents used across the company are stateless between sessions. They re-derive the same
context, repeat corrected mistakes, re-visit dead-end sources, and burn tokens rebuilding
understanding that a colleague's agent already established yesterday. Existing "memory"
features remember facts *about the user*; they do not remember **what the work required or
how it went**.

Perplexity's Brain demonstrates the higher-value model: memory about *what the agent did*,
held as a living context graph and rewritten on a schedule so the agent gets measurably
better at the job (reported +25% correctness on seen tasks, +16% recall, −13% cost on
tasks needing historical context). We want that capability, but **vendor-neutral**: usable
by any MCP-enabled LLM, fronted by Vercel, backed by Supabase, with the heavy overnight
learning on an external Railway/Inngest worker.

## What Changes

- **NEW capability `memory-model`** — a three-layer memory (episodic / semantic /
  procedural) expressed as a typed, provenance-bearing context graph in Postgres.
- **NEW capability `mcp-interface`** — Engram is exposed as an MCP server (Streamable HTTP,
  OAuth 2.1) with read tools (`search`, `get_context_pack`, `trace`), write tools
  (`remember`, `record_outcome`, `correct`, `link`), a governance tool (`forget`), plus MCP
  Resources for wiki pages.
- **NEW capability `retrieval`** — hybrid lexical + vector + graph retrieval that assembles
  a token-budgeted, provenance-tagged "context pack" at task start.
- **NEW capability `consolidation`** — a durable overnight pipeline (collect → extract →
  resolve → reflect/grade → update → **eval-gate** → emit) with per-run cost caps,
  contradiction quarantine, decay/forgetting, and **automatic rollback on regression**.
- **NEW capability `security-governance`** — org+user+visibility RLS, per-tool OAuth scopes,
  PII classification and right-to-be-forgotten cascade, prompt-injection/memory-poisoning
  defenses, and an immutable audit log.
- **NEW capability `knowledge-interchange`** — adopts Google's Open Knowledge Format (OKF)
  as the vendor-neutral serialization for semantic and procedural memory: OKF-conformant
  frontmatter mapping, concept-ID addressing, `export_bundle` / `import_bundle` / `get_index`
  tools, progressive disclosure via `index.md`, update history via `log.md`, citations and
  `references/` concepts, and permissive consumption — with **git-versioned OKF bundles as the system of record** and Postgres serving as a derived,
  rebuildable index.
- **NEW capability `observability-metrics`** — KPI tracking (correctness, recall, cost,
  turns, calls, retrieval precision, provenance coverage, contradiction rate) with per-run
  reports surfaced in the Console.

## Impact

- **Affected systems:** a **canonical git repository of OKF bundles** (system of record); a
  new **Indexer/sync service** (git webhook → derived index); new Next.js Console (Vercel);
  new MCP server (Railway); new consolidation worker (Railway + Inngest) that **commits to
  git**; Supabase Postgres + pgvector + FTS + RLS as the **derived read model**; a
  provider-agnostic model gateway.
- **Affected users:** every employee whose agent connects via MCP; admins who curate memory
  in the Console.
- **Dependencies added:** `@modelcontextprotocol/sdk`, Inngest, pgvector, an embeddings
  provider, a chat-model provider (both behind the gateway), and a YAML-frontmatter
  markdown library for OKF read/write.
- **Interoperability:** exported bundles are consumable by any OKF tool (Obsidian, MkDocs, the
  bundled graph viewer, other agents) and importable from external catalogs that emit OKF;
  bundles validate against the OKF reference implementation.
- **Data:** introduces durable storage of work artifacts and derived memory. Requires a data
  classification + retention policy and a documented forgetting path before go-live.
- **Risk posture:** self-improvement is gated and reversible; ingested content is sandboxed
  as data; tenant isolation enforced at the row level. Residual risks tracked in the review
  log.
- **Backwards compatibility:** additive only. Agents that do not call Engram are unaffected.
