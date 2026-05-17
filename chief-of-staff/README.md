# Chief-of-Staff Agent

A composite multi-reasoner system that acts as an engineering chief-of-staff.
It takes natural-language directives from a human, classifies intent, assembles
shared context (centralized knowledge + Linear state + team topology), routes
into the right deep planning subgraph, and either previews or actuates work
across Linear initiatives, projects, and issues.

## Architecture

- **Entry reasoner:** `chief-of-staff.chief_of_staff`
- **Patterns layered:** Reasoner Composition Cascade (depth 5) · Dynamic Router
  (5-way intent classification) · Parallel Hunters (context + per-initiative
  status + per-stakeholder alignment) · Meta-Prompting (project decomposition
  spawns N project planners; each spawns M issue drafters at runtime)
- **Intents handled:**
  - `new_idea` → scope → decompose into projects (N) → draft issues per project (M) → body + owner per issue (parallel) → risks
  - `status_check` → per-initiative analyzer (parallel) → velocity + blockers → narrative
  - `modify` → impact scoping → per-entity delta drafting (parallel)
  - `knowledge_update` → conflict check → canonical topic → canonical note (persisted to memory)
  - `strategic` → stakeholder map → per-stakeholder alignment (parallel) → comms drafts

Inter-reasoner traffic flows through `app.call(f"{NODE_ID}.X", ...)` so the
control plane records the full workflow DAG and emits a verifiable credential
chain for every run. Per-request `model` overrides propagate through every layer.

## Linear integration

- When `LINEAR_API_KEY` is set, the read skills hit `https://api.linear.app/graphql`
  for real initiatives / projects / issues / teams, and `execution_mode="execute"`
  with the `new_idea` intent creates real Linear initiatives, projects, and issues.
- When `LINEAR_API_KEY` is **unset**, the read skills return clearly labeled
  `[MOCK]` data so the smoke test below produces a real reasoned answer without
  any external setup. Writes in mock mode are stubbed and return `preview: true`.

## Secrets — Doppler

This agent is wired for Doppler-managed secrets. `doppler run --` exports the
configured secrets as env vars to the spawned process, which docker-compose
then interpolates into the container environments.

**One-time setup:**

```bash
# Install Doppler CLI if you don't already have it
curl -Ls --tlsv1.2 https://cli.doppler.com/install.sh | sh

# Authenticate (browser auth)
doppler login

# Pin this directory to a project + config. Doppler writes `doppler.yaml`.
# Use the keys listed in `.env.example` as the Doppler secret names.
cd chief-of-staff
doppler setup
```

Required Doppler secrets (names exactly as below):

| Secret | Required? | What it gates |
|---|---|---|
| `OPENROUTER_API_KEY` (or `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `GOOGLE_API_KEY`) | yes | Every `.ai()` call |
| `AI_MODEL` | recommended | Per-deploy default model string |
| `LINEAR_API_KEY` | optional | Real Linear reads + writes (mocks otherwise) |
| `SLACK_SIGNING_SECRET` | required for Slack trigger | Inbound webhook signature verification (CP-side) |
| `SLACK_BOT_TOKEN` | required for Slack replies | `chat.postMessage` from the agent |

## Run

```bash
cd chief-of-staff
doppler run -- docker compose up --build
```

Wait until you see `agent registered` in the logs (~30–90 seconds first run while
the control-plane image pulls).

> **Local-dev fallback (no Doppler):** `cp .env.example .env`, edit, then
> `docker compose up --build`. Compose's automatic `.env` loading picks the
> values up the same way.

## Open the UI

| URL | What it shows |
|---|---|
| `http://localhost:8080/ui/` | Live workflow DAG, reasoner discovery, execution history, VC chains |
| `http://localhost:8080/api/v1/discovery/capabilities` | JSON: every reasoner registered (proves the build deployed) |
| `http://localhost:8080/api/v1/health` | Health check |

## Verify (run in another terminal)

```bash
# 1. Control plane up?
curl -fsS http://localhost:8080/api/v1/health | jq '.status'

# 2. Agent registered and reasoners discoverable? (durable primary check)
curl -fsS http://localhost:8080/api/v1/discovery/capabilities \
  | jq '.capabilities[] | select(.agent_id=="chief-of-staff") | {
      agent_id,
      n_reasoners: (.reasoners | length),
      entry: [.reasoners[] | select(.tags[]? == "entry") | .id],
      all_reasoner_ids: [.reasoners[].id]
    }'
```

## Try it — canonical async smoke test

The pipeline composes ~20 LLM calls per run, so always hit the async endpoint
(it has no time ceiling; the sync endpoint has a 90-second timeout):

```bash
EXEC_ID=$(curl -sS -X POST http://localhost:8080/api/v1/execute/async/chief-of-staff.chief_of_staff \
  -H 'Content-Type: application/json' \
  -d '{
    "input": {
      "directive": "We need to cut p95 checkout latency in half by Q3. Spin up an initiative, draft the projects and the first wave of issues, and flag what could go wrong.",
      "execution_mode": "preview",
      "model": "openrouter/google/gemini-2.5-flash"
    }
  }' | jq -r '.execution_id')
echo "Execution: $EXEC_ID"

while :; do
  R=$(curl -sS http://localhost:8080/api/v1/executions/$EXEC_ID)
  S=$(echo "$R" | jq -r '.status')
  case "$S" in
    succeeded) echo "$R" | jq '.result'; break ;;
    failed)    echo "$R" | jq '.'; break ;;
    *)         sleep 2 ;;
  esac
done
```

### More directives to try (one per intent)

```bash
# status_check
'{"input": {"directive": "What is the current status of every active engineering initiative? Where are we stuck?", "model": "openrouter/google/gemini-2.5-flash"}}'

# modify
'{"input": {"directive": "Deprioritize ENG-211 to medium and reassign it to the Reliability team — it is blocked on shared fixtures and should wait.", "model": "openrouter/google/gemini-2.5-flash"}}'

# knowledge_update
'{"input": {"directive": "Decision: we standardize on the Postgres pgvector extension for all new embedding storage. We are sunsetting Pinecone for new use cases.", "model": "openrouter/google/gemini-2.5-flash"}}'

# strategic
'{"input": {"directive": "Engineering is misaligned with Product on the 2026 reliability roadmap. Map the stakeholders and draft messages to get us aligned.", "model": "openrouter/google/gemini-2.5-flash"}}'
```

### Actuating real Linear writes (iteration 2)

To turn the `new_idea` plan into real Linear work:

1. Get a Linear Personal API key from <https://linear.app/settings/api> and set
   `LINEAR_API_KEY=lin_api_...` in `.env`.
2. Find your Linear team's `teamId` (UUID). One easy way:
   ```bash
   curl -sS -H "Authorization: $LINEAR_API_KEY" -H 'Content-Type: application/json' \
     -d '{"query":"query { teams { nodes { id key name } } }"}' \
     https://api.linear.app/graphql | jq
   ```
3. Re-issue the curl with `"execution_mode": "execute"` and the team ID:
   ```bash
   curl -sS -X POST http://localhost:8080/api/v1/execute/async/chief-of-staff.chief_of_staff \
     -H 'Content-Type: application/json' \
     -d '{"input": {"directive": "...", "execution_mode": "execute", "default_team_id": "<uuid>"}}'
   ```

Use `preview` first. Always.

## Slack integration

When `SLACK_SIGNING_SECRET` and `SLACK_BOT_TOKEN` are present, the agent
registers a webhook trigger that listens for `app_mention` events. Mentioning
the bot in any channel where it's invited fires `chief_of_staff` in preview
mode and posts the headline + summary + actions + next-steps back to the same
thread.

### Wire it up in Slack (one-time)

1. <https://api.slack.com/apps> → **Create New App** → From scratch.
2. **OAuth & Permissions** → add bot scopes: `app_mentions:read`,
   `chat:write`. Install to the workspace; copy the **Bot User OAuth Token**
   (starts with `xoxb-`) into Doppler as `SLACK_BOT_TOKEN`.
3. **Basic Information** → **App Credentials** → copy the **Signing Secret**
   into Doppler as `SLACK_SIGNING_SECRET`.
4. **Event Subscriptions** → Enable Events. Request URL:
   `https://<your-public-control-plane>/api/v1/triggers/slack` (the CP
   exposes this; tunnel it with `ngrok http 8080` for local testing and use
   that URL). Subscribe to bot event **`app_mention`**.
5. Invite the bot to a channel (`/invite @chief-of-staff`) and mention it:
   `@chief-of-staff cut p95 checkout latency in half by Q3`.

### Confirm the trigger registered

```bash
curl -fsS http://localhost:8080/api/v1/triggers \
  | jq '.triggers[] | select(.target_reasoner | contains("on_slack_mention")) | {source_name, target_reasoner, id}'
```

You should see a row with `source_name: "slack"` and
`target_reasoner: "chief-of-staff.on_slack_mention"`.

## Showpiece — verifiable workflow chain

```bash
LAST_EXEC=$(curl -s http://localhost:8080/api/v1/executions | jq -r '.[0].workflow_id')
curl -s http://localhost:8080/api/v1/did/workflow/$LAST_EXEC/vc-chain | jq
```

Every reasoner that ran, with cryptographic provenance. No other agent
framework gives you this.

## Stop

```bash
docker compose down
docker compose down --volumes   # also clears local control-plane state and memory
```

## Project structure

```
chief-of-staff/
├── main.py                      # Agent + entry reasoner + intent routing
├── reasoners/
│   ├── __init__.py
│   ├── models.py                # All Pydantic schemas
│   ├── helpers.py               # Linear GraphQL client, prose renderers, fallbacks
│   ├── intake.py                # classify_intent, extract_entities, assemble_context, fetch_linear_state, ...
│   ├── initiative.py            # plan_initiative → decompose → plan_project → draft_issues → draft_issue → compose_issue_body + assess_issue_owner
│   ├── status.py                # synthesize_status + analyze_initiative_progress + judge_velocity + find_blockers + compose_status_narrative
│   ├── change.py                # plan_change + identify_impact_scope + compute_delta_for_entity + draft_update_spec
│   ├── knowledge.py             # curate_knowledge + check_for_conflicts + identify_canonical_topic + compose_canonical_note
│   ├── strategy.py              # coordinate_strategy + map_stakeholders + check_alignment + draft_communications
│   ├── persist.py               # persist_outcomes + write_knowledge_note_skill + Linear write skills
│   ├── respond.py               # compose_human_response
│   └── slack.py                 # on_slack_mention trigger + post_slack_reply_skill
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── .dockerignore
└── CLAUDE.md
```
