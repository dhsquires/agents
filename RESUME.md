# Resume: Slack mention smoke test

Active work branch: `claude/add-agentfield-install-veJzJ`.

## State at last pause

- Tree clean, pushed to `origin`.
- Last functional commit before this doc: `4e921b9` — *Fix Linear GraphQL queries discovered by live smoke test*.
- No Docker containers from this stack are running.
- The previous web-session container needed a sandbox-only TLS workaround in `chief-of-staff/Dockerfile` (extra CA cert + pip `--trusted-host`). It was intentionally **not** committed; fresh builds (web or local) should work without it. Only re-apply if pip fails with SSL errors during the image build, and never commit it.

## What's done on the branch

- `chief-of-staff/` AgentField project wired to Doppler for secrets.
- Slack `app_mention` trigger added (handler + route).
- Linear GraphQL queries fixed via live smoke.
- Default model: `anthropic/claude-sonnet-4-6`.

## What's left

1. Mint a fresh `dev`-scoped Doppler service token (the previous one was revoked).
2. `docker compose up -d` with that token, then `cloudflared tunnel --url http://localhost:8080`.
3. In the Slack app dashboard: Event Subscriptions → paste tunnel URL → wait for verify → subscribe `app_mention` → reinstall app.
4. `/invite` the bot to channel **C0B3V1VLQR5**.
5. Mention the bot in that channel → confirm reply lands.

---

## Resume in a new Claude Code on the Web session

Open this repo in a new session and paste this as your first message:

```
Resume the Slack mention smoke test on branch claude/add-agentfield-install-veJzJ.
Read RESUME.md for context. I'm about to paste a fresh dev-scoped Doppler service
token — when it arrives, bring up chief-of-staff/ via docker compose, expose :8080
with cloudflared, give me the public URL plus an iOS-friendly walkthrough for
Event Subscriptions + /invite to channel C0B3V1VLQR5, then watch agent logs while
I mention the bot. Note: previous session needed an in-memory Dockerfile patch to
work around this sandbox's TLS-intercepting proxy — try the build first without
it; if pip fails with SSL errors, apply the smoke-only cert workaround and do not
commit it.
```

## Resume locally

```bash
git clone <repo-url> agents && cd agents
git checkout claude/add-agentfield-install-veJzJ

# Tooling: Docker, Doppler CLI, cloudflared
brew install dopplerhq/cli/doppler cloudflare/cloudflare/cloudflared

doppler login && doppler setup   # pick the chief-of-staff project / dev config

cd chief-of-staff
doppler run -- docker compose up --build -d
cloudflared tunnel --url http://localhost:8080
# paste the printed *.trycloudflare.com URL into Slack Event Subscriptions
```

## External state (not in the repo)

- **Doppler**: project per `chief-of-staff/doppler.yaml`, `dev` config.
- **Slack target channel**: `C0B3V1VLQR5`.
- **Slack app scopes required**: `app_mentions:read`, `chat:write`. The bot must be invited to the channel before mentions fire.
- **Slack app dashboard**: https://api.slack.com/apps

## Housekeeping before pausing

If the old `dev` Doppler token from the previous session's transcript has not been revoked yet, revoke it now (Doppler dashboard → Access → Service Tokens). The next session will mint its own.
