# Engram — a local, self-improving memory MCP for your coding agents

Engram gives any **MCP-enabled coding agent** (Claude Code, Cursor, Windsurf,
Claude Desktop, …) a persistent, self-improving memory you can carry **anywhere**
by installing this one GitHub repo. It implements two documents:

1. **LLM Brain — Personal Context Architecture** → the [`brain/`](brain) OKF bundle
   (a ready-to-populate personal knowledge graph) + an
   [interview questionnaire](interview/interview-questionnaire.md) to fill it.
2. **Engram — Self-Improving Memory** ([OpenSpec](openspec)) → a local
   implementation of a three-layer memory (episodic / semantic / procedural) that
   remembers *what your work required and how it went*, and rewrites itself behind
   an eval gate.

Everything runs **locally with zero API keys and zero cloud infrastructure**.
The system of record is a **git-versioned bundle of Open Knowledge Format (OKF)
markdown files**; a Node built-in **SQLite** database is a rebuildable derived
index. A memory version is a git commit SHA, and rollback is a git operation.

> The full vendor-neutral, multi-user cloud design (Supabase + Vercel + Railway +
> Inngest + OAuth) is preserved in [`openspec/`](openspec). This repo is that
> architecture collapsed to a single machine — see [docs/architecture.md](docs/architecture.md).

---

## Quick start

Requires **Node.js ≥ 22.5** (uses the built-in `node:sqlite` — no native build step).

```bash
git clone https://github.com/dhsquires/agents.git
cd agents
npm install          # also builds (via the prepare script)
node dist/cli.js doctor
```

`doctor` should report your bundle, the derived index counts, and `"ok": true`.

### Add it to your coding agent

**Claude Code** (project- or user-scoped MCP). Add to `.mcp.json` (project) or
`~/.claude.json` / settings:

```jsonc
{
  "mcpServers": {
    "engram": {
      "command": "node",
      "args": ["/ABSOLUTE/PATH/TO/agents/dist/index.js"]
    }
  }
}
```

…or register it from the CLI:

```bash
claude mcp add engram -- node /ABSOLUTE/PATH/TO/agents/dist/index.js
```

**Cursor / Windsurf / Claude Desktop** — use the same `command`/`args` shape in
that client's MCP settings (see [`examples/`](examples)).

**Zero-clone option** (npx straight from GitHub):

```jsonc
{ "mcpServers": { "engram": { "command": "npx", "args": ["-y", "github:dhsquires/agents", "engram-brain"] } } }
```

On first run Engram indexes the `brain/` bundle automatically. That's it — your
agent now has `search`, `get_context_pack`, `remember`, `consolidate`, and more.

---

## Use it

### 1. Seed your brain (one time)

Open a chat with your agent and paste:

> *Open `interview/interview-questionnaire.md` and interview me one question at a
> time starting at Module 1. After each answer, decide whether to probe deeper or
> move on, and write my answers into the matching files under `brain/`.*

Prioritize Modules 1–6 if short on time. Then ask it to generate the 300-word
synthesis for `brain/core/identity.md` and run `engram index`.

### 2. Let agents read and write memory

A typical task loop an agent follows:

- **Start:** call `get_context_pack(task, token_budget)` → loads the most relevant
  concepts, budgeted and provenance-tagged.
- **During:** `remember` observations, `record_outcome` (with the sources it used
  and whether each helped), `correct` mistakes.
- **Overnight / on demand:** `consolidate` folds episodic events into versioned
  OKF knowledge — committed to git only if it passes the eval gate.

### 3. Drive it yourself with the CLI

```bash
node dist/cli.js search "how should AI talk to me"
node dist/cli.js pack "refactor the auth module" 1500
node dist/cli.js remember "ripgrep beats grep on big repos" --task search-codebase
node dist/cli.js outcome search-codebase success --summary "found it with ripgrep"
node dist/cli.js consolidate            # self-improve (commits to git on pass)
node dist/cli.js export ./my-brain --vis private
node dist/cli.js import ./some-okf-bundle
```

(Install globally with `npm link` to call `engram …` directly.)

---

## MCP surface

| Tool | Scope | Purpose |
|---|---|---|
| `search` | read | hybrid lexical+vector+graph search, ranked + provenance |
| `get_context_pack` | read | token-budgeted, deduplicated context pack for a task |
| `trace` | read | full provenance chain for a memory id |
| `get_index` | read | OKF `index.md` listing (progressive disclosure) |
| `export_bundle` | read | scope-filtered OKF bundle with citations |
| `remember` | write | append an episodic observation (stored as data) |
| `record_outcome` | write | task status + sources used → updates usefulness |
| `correct` | write | record a high-signal correction |
| `link` | write | add an explicit typed edge between concepts |
| `forget` | forget | enqueue + cascade a redaction (right-to-be-forgotten) |
| `import_bundle` | admin | ingest an external OKF bundle as a source |
| `consolidate` | admin | run the self-improvement pipeline (eval-gated) |

**Resources:** `engram://wiki/{concept_id}` returns OKF-conformant pages.
**Prompt:** `load_context` pulls a starter pack without bespoke wiring.

---

## The `brain/` bundle

An OKF v0.1 bundle — markdown + YAML frontmatter, one concept per file, links
form the graph. Layers and update cadence:

| Layer | Files | Cadence |
|---|---|---|
| Boot | `boot-context.md` | monthly |
| Core | `core/{identity,values,goals}.md` | quarterly |
| Professional | `professional/{career,work-style,learning}.md` | after milestones |
| Personal | `personal/{relationships,health,finances,lifestyle}.md` | monthly |
| Worldview | `worldview/{philosophy,narrative}.md` | annually |
| Knowledge | `knowledge/{domains,tools}.md` | as your stack changes |
| Meta | `meta/ai-prefs.md`, `okf-spec.md` | as preferences evolve |

`index.md` (with `okf_version: 0.1`) is the root; `log.md` is the change history.
Because it's plain markdown in git, it's also readable in Obsidian, MkDocs, on
GitHub, or by any other OKF tool.

---

## Configuration (all optional, via env vars)

| Variable | Default | Meaning |
|---|---|---|
| `ENGRAM_BRAIN_DIR` | `./brain` | the OKF bundle (system of record) |
| `ENGRAM_DB_PATH` | `~/.engram/engram.sqlite` | derived index location |
| `ENGRAM_TOKEN_BUDGET` | `2000` | default context-pack budget |
| `ENGRAM_HALF_LIFE_DAYS` | `60` | recency decay half-life |
| `ENGRAM_EMBEDDINGS_PROVIDER` | `local` | `local` or `openai` |
| `ENGRAM_EMBEDDINGS_MODEL` / `_DIM` / `_BASE_URL` / `_API_KEY` | — | OpenAI-compatible embeddings |
| `ENGRAM_CHAT_PROVIDER` | `heuristic` | `heuristic`, `openai`, or `anthropic` |
| `ENGRAM_RUN_TOKEN_CAP` | `200000` | consolidation cost cap |
| `ENGRAM_ALLOWED_SCOPES` | all | restrict tool scopes |

Defaults are fully offline. Point the gateway at a real embeddings/chat endpoint
to sharpen retrieval and extraction without changing any code.

---

## How self-improvement stays safe

- **Provenance is mandatory** — nothing is promoted without a traceable source.
- **Contradictions are quarantined**, never silently overwritten.
- **Eval gate + git rollback** — a batch that regresses retrieval recall or drops
  provenance coverage below 100% is rolled back to the prior commit.
- **Ingested content is data, never instructions** — defends against memory
  poisoning / indirect prompt injection.
- **Append-only audit log** and a cascading `forget`.

See [docs/architecture.md](docs/architecture.md) and the
[capability specs](openspec/changes/add-self-improving-memory/specs).

---

## Development

```bash
npm run build     # tsc → dist/
npm test          # build + run the smoke suite (node:test)
npm run doctor    # environment + bundle health
```

MIT licensed.
