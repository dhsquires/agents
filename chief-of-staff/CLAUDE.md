# CLAUDE.md — Chief-of-Staff Agent

## Mission

A composite multi-reasoner system that acts as an engineering chief-of-staff:
it ingests human directives, classifies intent, assembles centralized
knowledge + Linear state, routes into the right deep planning subgraph, and
either previews or actuates work across Linear initiatives, projects, and
issues.

External callers should hit `chief-of-staff.chief_of_staff` first.

## Architecture at a glance

- **Patterns:** Reasoner Composition Cascade (depth 5) · Dynamic Router
  (5-way intent classification) · Parallel Hunters (context fan-out,
  per-initiative status, per-stakeholder alignment) · Meta-Prompting
  (decompose_into_projects → plan_project → draft_issues → draft_issue,
  with N and M decided at runtime by intermediate LLM output)
- **Topology:** one AgentField node (`chief-of-staff`) with eight router
  modules + one entry reasoner in `main.py`
- **Entry reasoner:** `chief_of_staff` (in `main.py`) — orchestrates intake,
  context assembly, dynamic routing, persistence, and final response.
- **Inter-reasoner traffic:** every call goes through
  `app.call(f"{NODE_ID}.X", ...)` so the control plane records the workflow
  DAG and emits a verifiable credential chain. Never direct HTTP between
  reasoners.

### Reasoner inventory

Intake (`reasoners/intake.py`):
- `classify_intent` (.ai) — 5-way classification (new_idea / status_check /
  modify / knowledge_update / strategic) with `confident` flag
- `extract_entities` (.ai) — pull mentioned Linear refs from the directive
- `retrieve_knowledge` (.ai over `app.memory` scope=agent) — relevant prior notes
- `list_initiatives_skill`, `list_projects_skill`, `list_issues_skill`,
  `list_teams_skill` — Linear GraphQL reads, mock fallback when
  `LINEAR_API_KEY` is unset
- `fetch_linear_state` — orchestrator: 4-way parallel fan-out of the above
- `map_team_topology` (.ai) — derive ownership from Linear state
- `assemble_context` — orchestrator: knowledge + Linear + topology in parallel

Initiative planning (`reasoners/initiative.py`):
- `scope_initiative` (.ai) — initiative scope + success criteria
- `decompose_into_projects` (.ai) — N projects (META, runtime fan-out width)
- `plan_project` — orchestrator per project: drafts all issues in parallel
- `draft_issues` (.ai) — M issues per project (META, runtime fan-out width)
- `draft_issue` — orchestrator per issue: body + owner in parallel
- `compose_issue_body` (.ai) — title + description + labels
- `assess_issue_owner` (.ai) — team/person + rationale
- `plan_project_dependencies` (.ai) — explicit blockers between issues
- `assess_risks` (.ai) — initiative-level risks against the concrete plan
- `plan_initiative` — top of the new_idea subgraph

Status (`reasoners/status.py`):
- `compute_completion_skill` — deterministic completion percent
- `judge_velocity` (.ai) — trend judgement per initiative
- `find_blockers` (.ai) — per-initiative blocker scan
- `analyze_initiative_progress` — orchestrator per initiative
- `compose_status_narrative` (.ai) — final prose report
- `synthesize_status` — top of the status_check subgraph

Change (`reasoners/change.py`):
- `identify_impact_scope` (.ai) — which Linear entities are affected
- `draft_update_spec` (.ai) — field-by-field delta for one entity
- `compute_delta_for_entity` — orchestrator per impacted entity
- `plan_change` — top of the modify subgraph

Knowledge (`reasoners/knowledge.py`):
- `check_for_conflicts` (.ai) — does this contradict prior notes?
- `identify_canonical_topic` (.ai) — topic slug
- `compose_canonical_note` (.ai) — canonical body + references
- `curate_knowledge` — top of the knowledge_update subgraph

Strategy (`reasoners/strategy.py`):
- `map_stakeholders` (.ai) — affected teams/people
- `check_alignment` (.ai) — per-stakeholder alignment judgement
- `draft_communications` (.ai) — short tailored messages
- `coordinate_strategy` — top of the strategic subgraph; can chain back into
  `plan_initiative` when `plan_execution=True`

Persistence (`reasoners/persist.py`):
- `write_knowledge_note_skill` — stores a canonical note in `app.memory`
  scope=agent
- `create_linear_initiative_skill`, `create_linear_project_skill`,
  `create_linear_issue_skill` — Linear GraphQL mutations (preview-only when
  `LINEAR_API_KEY` is unset)
- `persist_outcomes` — knowledge write always; Linear writes only when
  `execution_mode="execute"` AND intent is `new_idea`

Response (`reasoners/respond.py`):
- `compose_human_response` (.ai) — final HumanResponse with citations

Slack (`reasoners/slack.py`):
- `on_slack_mention` — **triggered entry reasoner**:
  `@on_event(source="slack", types=["app_mention"], secret_env="SLACK_SIGNING_SECRET")`.
  Thin router: dedupes by `trigger.event_id` via `app.memory` scope=agent,
  strips the bot mention from the directive, calls `chief_of_staff` in
  preview mode, posts the response to the originating Slack thread. Stays
  callable from direct curls / tests because `trigger` is `Optional`.
- `post_slack_reply_skill` — thin httpx wrapper around
  `https://slack.com/api/chat.postMessage`; reads `SLACK_BOT_TOKEN` at
  request time and no-ops with a clear error when the token is unset.

## Why this architecture (not a chain)

Three architectural choices make this composite intelligence:

1. **Dynamic routing on intent** — exactly one of five distinct subgraphs
   fires per request. A chain framework would either fork at every step or
   require a `match`-style monolith; here the orchestrator picks the right
   sub-orchestrator from a one-shot classification.
2. **Meta-prompting at two layers** — `decompose_into_projects` decides N at
   runtime, then each `plan_project` calls `draft_issues` which decides M.
   The shape of the call graph is computed from the LLM output, not declared.
3. **Multi-layer parallelism** — fan-out fires at context assembly, the
   per-initiative status analyzer, per-project issue drafting, per-issue
   body/owner composition, per-stakeholder alignment, and the Linear write
   stage. Total wall-clock time is dominated by the slowest path, not the
   sum.

The cost of a wrong "plan" is bounded by `execution_mode="preview"` (the
default), so no adversarial verification layer is needed. If the user starts
auto-applying modify-intent deltas in iteration 2, an adversarial reviewer
(HUNT→PROVE) becomes earned and should be added.

## Primitive selection rules (binding)

- `.ai()` is used at every cognitive judgment: intent classification, entity
  extraction, scoping, decomposition, issue drafting, owner suggestion, risk
  assessment, velocity judgment, blocker scanning, impact scoping, delta
  drafting, conflict checking, canonical topic, canonical note, stakeholder
  mapping, alignment checking, communication drafting, and final response
  composition. Every `.ai()` schema has a `confident: bool` field and a
  deterministic safe-default fallback in `helpers.py`.
- `@router.reasoner()` wrappers expose Linear API calls and the completion
  formula so the control plane records them in the workflow DAG (and the
  test surface can curl them individually).
- `app.harness()` is **not** used in v1. The default container has no coding
  CLI installed. Iteration 2 could add a harness for "explore the codebase
  for context on this initiative" — that would justify installing
  `@anthropic-ai/claude-code` in the Dockerfile.
- Plain Python helpers in `reasoners/helpers.py` for: Linear GraphQL client,
  mock fixtures, prose renderers, fallback constructors. No decorator
  ceremony for internal-only utilities.

## Data-flow rules

- Structured Pydantic models within a single reasoner body — yes.
- Across `app.call(...)` boundaries — payloads arrive as plain dicts. The
  orchestrator either renders to prose before the call OR reconstructs with
  `Model(**payload)` on receive. The cross-boundary trap (every Pydantic
  instance becomes a dict) is handled at every boundary.
- LLM-to-LLM handoff is via prose strings (e.g., `render_planned_projects`,
  `render_linear_state`). Never raw JSON between two `.ai()` calls.

## Secrets — Doppler

This project pulls every runtime secret from **Doppler**. The canonical run
command is:

```bash
doppler run -- docker compose up --build
```

`doppler run` exports configured secrets as env vars to docker-compose, and
compose's `${VAR:-}` interpolation forwards them into the container
environments. The list of expected secret names is the source of truth in
`.env.example`. A local `.env` file is supported as a fallback (compose
auto-loads it), but production deploys should always go through Doppler.

**Hard rule: never hardcode a secret in source.** The trigger reasoner
declares `secret_env="SLACK_SIGNING_SECRET"` — the control plane reads the
env var at request time and the literal value never leaves the container.
Same for `SLACK_BOT_TOKEN`, `LINEAR_API_KEY`, and the provider keys.

When adding a new integration, document the required secret in
`.env.example`, add it to docker-compose.yml under the right service's
`environment:`, and update the Doppler-secrets table in README.md. Do not
introduce a new way to load secrets.

## Model selection

- Default model: `anthropic/claude-sonnet-4-6` via `AI_MODEL` env, calling
  the Anthropic API directly with `ANTHROPIC_API_KEY`. Sonnet 4.6 is slower
  per call than a flash-tier model, so the canonical smoke test always uses
  the async endpoint — never sync.
- The entry reasoner accepts an optional `model` parameter that propagates
  through every `app.call(..., model=model)` and every `router.ai(..., model=model)`.
  Per-request A/B testing requires no redeploy.
- Provider keys supported: `ANTHROPIC_API_KEY` (configured default),
  `OPENROUTER_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_API_KEY` — any
  LiteLLM-compatible model works.

## Linear integration

- Reads use Linear's GraphQL API (`https://api.linear.app/graphql`) with
  bearer auth from `LINEAR_API_KEY`. When unset, the read skills return
  labeled `[MOCK]` fixtures so the smoke test works out of the box.
- Writes are gated on TWO conditions: `execution_mode="execute"` AND
  `LINEAR_API_KEY` is set. In `preview` mode (the default), writes return
  `preview: true` without calling the API.
- `modify` intent never auto-applies field changes in v1 — even in `execute`
  mode it returns deltas for human approval. Promoting this to auto-apply
  is a deliberate iteration-2 decision and requires adding the
  adversarial-verification layer mentioned above.

## Runtime contract

- Local runtime is `docker-compose.yml` in this directory.
- One container: `agentfield/control-plane:latest` (local mode, SQLite/BoltDB).
- One container: this Python agent node, built from `Dockerfile`.
- Default ports: control plane 8080, agent node 8001.

## Delivery contract — every change must preserve

- A runnable `docker compose up --build`
- A valid `.env.example` listing OpenRouter / OpenAI / Anthropic / Google +
  LINEAR_API_KEY
- A README with the canonical async curl smoke test for at least one intent
- This CLAUDE.md kept in sync with the reasoner inventory

## Validation commands (run after every change)

```bash
python3 -m py_compile main.py
python3 -m py_compile reasoners/*.py
docker compose config > /dev/null
docker compose up --build -d
# wait for registration
for i in 1 2 3 4 5 6 7 8 9 10; do
  READY=$(curl -fsS http://localhost:8080/api/v1/discovery/capabilities 2>/dev/null \
    | jq -r '.capabilities[] | select(.agent_id=="chief-of-staff") | .agent_id')
  [ -n "$READY" ] && break
  sleep 3
done
# canonical curl from README.md
docker compose down
```

If any of those fail, the change is not done.

## Anti-patterns (reject these)

- ❌ Direct HTTP between reasoners. All internal traffic uses `app.call`.
- ❌ Hardcoded `node_id` strings in `app.call`. Always use
  `f"{NODE_ID}.X"` inside router files (with `NODE_ID = os.getenv("AGENT_NODE_ID", "chief-of-staff")`)
  and `f"{app.node_id}.X"` in `main.py`.
- ❌ Hardcoded model strings. Always read from env (`AI_MODEL`) and accept
  the per-request override.
- ❌ Replacing the dynamic 5-way routing in `chief_of_staff` with a single
  monolithic `.ai()` call.
- ❌ Removing the `confident` field from a `.ai()` schema without replacing
  the fallback path in `helpers.py`.
- ❌ Auto-applying field changes for the `modify` intent without first
  adding an adversarial-verification layer. The cost of an
  auto-modify-gone-wrong on a real Linear workspace is unbounded.
- ❌ Promoting any Linear write to "always-on" (i.e., bypassing the
  `execution_mode="preview"` default). The default-preview behavior is
  intentional safety, not a stub.
- ❌ Passing Pydantic instances directly across `app.call` boundaries
  expecting the type to survive. The serialization boundary always returns
  `dict` / `list[dict]`. Reconstruct with `Model(**payload)` or render to prose.
- ❌ Doing long synthesis or multi-step reasoning **inside** `on_slack_mention`
  (or any other triggered reasoner). The trigger reasoner is a thin router:
  validate shape, dedupe, hand off to `chief_of_staff` via `app.call`, post
  the reply. Stuffing logic into the trigger body breaks both observability
  (the work doesn't get its own reasoner span) and reusability (you can't
  fire the same logic from a curl).
- ❌ Hardcoding a webhook secret, or using `secret_env="X"` for a secret X
  that isn't actually configured into both the control plane AND the agent
  container via docker-compose.yml. The CP verifies signatures before
  dispatch — it needs the secret on its side.
- ❌ Trusting that `transform=` will be re-run on a retried delivery. The CP
  applies it once. Treat it as pure envelope-peeling — no I/O, no async.

## Extension points (where to safely add work)

- **Add a new subgraph (e.g., `incident_response`)**: extend the
  `IntentClassification` enum in `models.py`, add a branch in
  `chief_of_staff`, add a new router module with the subgraph reasoners,
  and register it in `reasoners/__init__.py` and `main.py`.
- **Promote knowledge retrieval to semantic search**: replace
  `retrieve_knowledge` in `intake.py` with a flow that embeds the directive
  and calls `router.memory.search_vectors(...)`. The schema already
  matches.
- **Slack trigger already wired**: see `reasoners/slack.py`. Iteration-2
  upgrades for it: add a slash command trigger (`@on_event(source="slack",
  types=["slash_command"], secret_env="SLACK_SIGNING_SECRET")`), support
  DMs (filter on `event.channel_type == "im"`), or add a confirmation
  button (Block Kit) before promoting `execution_mode` to `"execute"`.
- **Real-codebase awareness**: add `app.harness(provider="claude-code", ...)`
  inside `scope_initiative` for "explore the relevant code areas to ground
  the scope". Requires installing the Claude Code CLI in the Dockerfile and
  adding a startup `shutil.which("claude")` check.
- **Adversarial review for modify intent**: add a `prove_delta` reasoner that
  receives each `UpdateSpec` and tries to falsify it (find reasons the change
  is wrong). Gate auto-apply on `prove_delta` agreeing.

## Owner

Scaffolded by the `agentfield-multi-reasoner-builder` skill. To rebuild,
run that skill again with the same use case description. To extend, follow
this CLAUDE.md.
