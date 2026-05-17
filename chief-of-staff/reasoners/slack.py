"""Slack integration: inbound mention trigger + outbound reply skill.

Architecture (per triggers.md):
  - `on_slack_mention` is a THIN entry reasoner. It dedupes by event_id,
    strips the bot mention from the directive, calls `chief_of_staff` once,
    and posts the response back to the same Slack thread.
  - `post_slack_reply_skill` is a thin Slack-API wrapper around chat.postMessage.

Secrets:
  - `SLACK_SIGNING_SECRET` — read by the CONTROL PLANE to verify the
    X-Slack-Signature HMAC on every inbound event. Configured via the
    `secret_env=` argument on the trigger.
  - `SLACK_BOT_TOKEN` — read by `post_slack_reply_skill` at request time.
"""
from __future__ import annotations

import os
import re

import httpx
from agentfield import AgentRouter, EventTrigger, TriggerContext

NODE_ID = os.getenv("AGENT_NODE_ID", "chief-of-staff")
router = AgentRouter(prefix="", tags=["slack"])


# ----- Slack envelope peeler (used as `transform=` on the trigger) ------------
# Must be SYNCHRONOUS and side-effect free per triggers.md.

def _peel_slack_envelope(evt: dict) -> dict:
    """Peel `{"event": {...inner...}, "event_id": "Ev...", "team_id": "T..."}`
    down to the inner event, but preserve the outer event_id under
    `_outer_event_id` so the reasoner can use it for idempotency cross-refs.
    """
    inner = evt.get("event") or evt
    return {
        **inner,
        "_outer_event_id": evt.get("event_id"),
        "_team_id": evt.get("team_id"),
    }


# ----- Outbound reply (Slack Web API) -----------------------------------------

@router.reasoner()
async def post_slack_reply_skill(
    channel: str,
    text: str,
    thread_ts: str | None = None,
) -> dict:
    """Post a message to a Slack channel/thread via chat.postMessage."""
    token = os.getenv("SLACK_BOT_TOKEN")
    if not token:
        return {"ok": False, "skipped": "SLACK_BOT_TOKEN not set", "channel": channel}
    if not channel or not text:
        return {"ok": False, "skipped": "channel and text are required", "channel": channel}

    payload: dict = {"channel": channel, "text": text}
    if thread_ts:
        payload["thread_ts"] = thread_ts

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://slack.com/api/chat.postMessage",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json; charset=utf-8",
                },
                json=payload,
            )
            resp.raise_for_status()
            body = resp.json()
            return {
                "ok": bool(body.get("ok")),
                "ts": body.get("ts"),
                "channel": body.get("channel") or channel,
                "error": body.get("error"),
            }
    except Exception as e:
        return {"ok": False, "channel": channel, "error": str(e)}


# ----- Inbound mention trigger ------------------------------------------------

# Strip leading bot mentions like "<@U01ABCDEF> please draft an initiative"
_MENTION_PREFIX = re.compile(r"^\s*(?:<@[UW][A-Z0-9]+>\s*)+", re.IGNORECASE)


def _strip_bot_mention(text: str) -> str:
    return _MENTION_PREFIX.sub("", text or "").strip()


def _format_for_slack(response: dict) -> str:
    """Render the chief_of_staff response into a short, thread-friendly message."""
    r = response or {}
    headline = r.get("headline") or "Done."
    summary = r.get("summary") or ""
    actions = r.get("actions_taken") or []
    nexts = r.get("proposed_next_steps") or []
    citations = r.get("citations") or []

    lines = [f"*{headline}*"]
    if summary:
        lines.append(summary)
    if actions:
        lines.append("\n*Actions taken*")
        lines.extend(f"• {a}" for a in actions[:6])
    if nexts:
        lines.append("\n*Proposed next steps*")
        lines.extend(f"• {n}" for n in nexts[:6])
    if citations:
        cited = ", ".join(citations[:10])
        suffix = "" if len(citations) <= 10 else f" (+{len(citations) - 10} more)"
        lines.append(f"\n_References: {cited}{suffix}_")
    return "\n".join(lines)


@router.reasoner(
    triggers=[
        EventTrigger(
            source="slack",
            types=["app_mention"],
            secret_env="SLACK_SIGNING_SECRET",
            transform=_peel_slack_envelope,
        ),
    ],
)
async def on_slack_mention(
    event: dict,
    trigger: TriggerContext | None = None,
) -> dict:
    """Slack mention → chief_of_staff → reply to thread.

    Thin entry reasoner. Idempotency-checks via `app.memory`, peels the
    directive out of the mention text, calls `chief_of_staff` (preview mode),
    posts the response back to the same thread.
    """
    # 1. Idempotency — Slack retries deliveries; skip if we already handled this event_id.
    event_id = (trigger.event_id if trigger else None) or event.get("_outer_event_id")
    dedupe_key = f"slack-evt:{event_id}" if event_id else None
    if dedupe_key:
        try:
            if await router.memory.exists(dedupe_key, scope="agent"):
                return {"skipped": "duplicate", "event_id": event_id}
        except Exception:
            pass  # If memory is unavailable, fall through — at-least-once is acceptable.

    # 2. Shape check — bail on anything we don't handle.
    if event.get("type") not in (None, "app_mention"):
        return {"skipped": "non-mention event", "type": event.get("type")}
    if event.get("bot_id") or event.get("subtype") in ("bot_message",):
        return {"skipped": "ignoring bot messages"}

    raw_text = event.get("text") or ""
    directive = _strip_bot_mention(raw_text)
    channel = event.get("channel") or ""
    # Reply in-thread: prefer existing thread_ts; otherwise start a thread on this message.
    thread_ts = event.get("thread_ts") or event.get("ts")

    if not directive:
        # Quick reply so the user knows we saw it.
        await router.call(
            f"{NODE_ID}.post_slack_reply_skill",
            channel=channel,
            text="I saw the mention but couldn't find a directive — try `@chief-of-staff <your request>`.",
            thread_ts=thread_ts,
        )
        return {"skipped": "empty directive after stripping mention"}

    # 3. Mark the event as in-flight (writes happen before downstream work so a
    #    retry from Slack doesn't re-fire the pipeline mid-flight).
    if dedupe_key:
        try:
            await router.memory.set(
                dedupe_key,
                {"channel": channel, "thread_ts": thread_ts, "directive": directive[:240]},
                scope="agent",
            )
        except Exception:
            pass

    # 4. Run the chief-of-staff pipeline (preview mode — Slack mentions never
    #    auto-execute Linear writes; the human can re-run with execute=true).
    result = await router.call(
        f"{NODE_ID}.chief_of_staff",
        directive=directive,
        execution_mode="preview",
    )

    # 5. Post the response back to the thread.
    reply_text = _format_for_slack(result.get("response") or {})
    reply_result = await router.call(
        f"{NODE_ID}.post_slack_reply_skill",
        channel=channel,
        text=reply_text,
        thread_ts=thread_ts,
    )

    return {
        "event_id": event_id,
        "channel": channel,
        "thread_ts": thread_ts,
        "directive": directive,
        "intent": (result.get("intent") or {}).get("intent"),
        "reply_ok": reply_result.get("ok"),
        "reply_error": reply_result.get("error"),
    }
