"""Chief-of-Staff agent.

A composite multi-reasoner system that turns human directives into
coordinated engineering work across Linear (initiatives / projects / issues),
while maintaining a centralized knowledge context.

Entry reasoner: `chief-of-staff.chief_of_staff`
Architecture (vocabulary):
  - Reasoner Composition Cascade (depth 5) — every reasoner is a small API
  - Dynamic Router — 5-way intent classification picks the active subgraph
  - Parallel Hunters — context assembly + per-initiative status + per-stakeholder
    alignment all fan-out via asyncio.gather
  - Meta-Prompting — decompose_into_projects (N runtime) → plan_project →
    draft_issues (M runtime) → draft_issue: the call graph shape is decided
    by intermediate LLM output, not declared upfront.
"""
from __future__ import annotations

import asyncio
import os

from agentfield import Agent, AIConfig

from reasoners import (
    intake_router,
    initiative_router,
    status_router,
    change_router,
    knowledge_router,
    strategy_router,
    persist_router,
    respond_router,
    slack_router,
)
from reasoners import helpers as H
from reasoners.models import (
    ChangePlan, EntityExtraction, HumanResponse, InitiativePlan,
    IntentClassification, KnowledgeUpdate, StatusSynthesis, StrategicPlan,
)


# ---- Agent ----

app = Agent(
    node_id=os.getenv("AGENT_NODE_ID", "chief-of-staff"),
    agentfield_server=os.getenv("AGENTFIELD_SERVER", "http://localhost:8080"),
    ai_config=AIConfig(model=os.getenv("AI_MODEL", "openrouter/google/gemini-2.5-flash")),
    dev_mode=True,
)

app.include_router(intake_router)
app.include_router(initiative_router)
app.include_router(status_router)
app.include_router(change_router)
app.include_router(knowledge_router)
app.include_router(strategy_router)
app.include_router(persist_router)
app.include_router(respond_router)
app.include_router(slack_router)


# ---- Entry reasoner ----

@app.reasoner(tags=["entry"])
async def chief_of_staff(
    directive: str,
    execution_mode: str = "preview",
    default_team_id: str = "",
    model: str | None = None,
) -> dict:
    """Orchestrate engineering work across Linear in response to a human directive.

    Args:
      directive: the natural-language instruction or idea from the human.
      execution_mode: "preview" (default) returns the plan only. "execute"
        actuates Linear writes (for new_idea intent) and persists knowledge
        notes. Use "preview" first; switch to "execute" once the plan checks
        out and a LINEAR_API_KEY is set.
      default_team_id: required when execution_mode="execute" and you want
        issues created — Linear's IssueCreate API requires a teamId.
      model: optional per-request model override (e.g. "openrouter/openai/gpt-4o").
    """
    # 1. Classify intent and extract entities IN PARALLEL.
    intent_dict, entity_dict = await asyncio.gather(
        app.call(f"{app.node_id}.classify_intent", directive=directive, model=model),
        app.call(f"{app.node_id}.extract_entities", directive=directive, model=model),
    )
    intent = IntentClassification(**intent_dict)
    entities = EntityExtraction(**entity_dict)

    if not intent.confident:
        intent_obj_for_branch = H.fallback_intent(intent.rationale or "Intent not confident")
    else:
        intent_obj_for_branch = intent

    # 2. Assemble shared context (parallel fan-out: knowledge + Linear + topology).
    context_payload = await app.call(
        f"{app.node_id}.assemble_context",
        directive=directive,
        intent=intent_obj_for_branch.intent,
        model=model,
    )

    # 3. Dynamic routing — exactly ONE branch fires based on intent.
    subgraph_kind = intent_obj_for_branch.intent
    subgraph_payload: dict = {}
    persistence_payload: dict = {}

    if subgraph_kind == "new_idea":
        plan_dict = await app.call(
            f"{app.node_id}.plan_initiative",
            directive=directive,
            context_payload=context_payload,
            model=model,
        )
        plan = InitiativePlan(**plan_dict)
        subgraph_payload = plan.model_dump()
        persistence_payload = subgraph_payload

    elif subgraph_kind == "status_check":
        status_dict = await app.call(
            f"{app.node_id}.synthesize_status",
            directive=directive,
            context_payload=context_payload,
            model=model,
        )
        status = StatusSynthesis(**status_dict)
        subgraph_payload = status.model_dump()

    elif subgraph_kind == "modify":
        change_dict = await app.call(
            f"{app.node_id}.plan_change",
            directive=directive,
            context_payload=context_payload,
            entity_extraction=entities.model_dump(),
            model=model,
        )
        change = ChangePlan(**change_dict)
        subgraph_payload = change.model_dump()
        # NOTE: we do NOT auto-apply field updates in v1, even in execute mode.
        # Deltas are surfaced for human review. Adding apply_update_skill is a
        # safe iteration-2 upgrade.

    elif subgraph_kind == "knowledge_update":
        ku_dict = await app.call(
            f"{app.node_id}.curate_knowledge",
            directive=directive,
            context_payload=context_payload,
            model=model,
        )
        ku = KnowledgeUpdate(**ku_dict)
        subgraph_payload = ku.model_dump()
        persistence_payload = {"note": ku.note.model_dump()}

    else:  # strategic
        strat_dict = await app.call(
            f"{app.node_id}.coordinate_strategy",
            directive=directive,
            context_payload=context_payload,
            plan_execution=False,
            model=model,
        )
        strat = StrategicPlan(**strat_dict)
        subgraph_payload = strat.model_dump()

    # 4. Persist outcomes (knowledge write always for knowledge_update;
    #    Linear writes only on execute + new_idea).
    persistence = await app.call(
        f"{app.node_id}.persist_outcomes",
        intent=subgraph_kind,
        payload=persistence_payload,
        execution_mode=execution_mode,
        default_team_id=default_team_id,
    )

    # 5. Compose the human-facing response.
    subgraph_prose = _render_subgraph_for_human(subgraph_kind, subgraph_payload)
    persistence_prose = _render_persistence(persistence)
    citations = list(subgraph_payload.get("citations") or context_payload.get("citations") or [])

    response_dict = await app.call(
        f"{app.node_id}.compose_human_response",
        directive=directive,
        intent=subgraph_kind,
        subgraph_prose=subgraph_prose,
        persistence_prose=persistence_prose,
        citations=citations,
        model=model,
    )
    response = HumanResponse(**response_dict)

    return {
        "directive": directive,
        "intent": intent.model_dump(),
        "entities": entities.model_dump(),
        "context": {
            "knowledge": context_payload.get("knowledge"),
            "team_topology": context_payload.get("team_topology"),
            "linear_state_summary": _summarize_linear_state(context_payload.get("linear_state", {})),
        },
        "subgraph": subgraph_kind,
        "subgraph_output": subgraph_payload,
        "persistence": persistence,
        "response": response.model_dump(),
    }


# ---- Local prose helpers (NOT reasoners — just rendering) --------------------

def _summarize_linear_state(state: dict) -> dict:
    return {
        "n_initiatives": len(state.get("initiatives") or []),
        "n_projects": len(state.get("projects") or []),
        "n_issues": len(state.get("issues") or []),
        "n_teams": len(state.get("teams") or []),
        "using_mocks": not H.linear_enabled(),
    }


def _render_subgraph_for_human(intent: str, payload: dict) -> str:
    if intent == "new_idea":
        lines = [
            f"INITIATIVE: {payload.get('initiative_name')}",
            f"SCOPE: {payload.get('one_paragraph_scope')}",
            "SUCCESS CRITERIA:",
        ]
        for s in payload.get("success_criteria") or []:
            lines.append(f"  - {s}")
        lines.append(H.render_planned_projects(payload.get("planned_projects") or []))
        if payload.get("risks"):
            lines.append("RISKS:")
            for r in payload["risks"]:
                lines.append(f"  - ({r['severity']}) {r['risk']} — mitigation: {r['mitigation']}")
        return "\n".join(lines)

    if intent == "status_check":
        return payload.get("narrative") or "(empty status)"

    if intent == "modify":
        return "CHANGE PLAN:\n" + (payload.get("summary") or "(no summary)")

    if intent == "knowledge_update":
        note = payload.get("note") or {}
        out = [
            f"CANONICAL NOTE — topic: {note.get('topic')}",
            note.get("body") or "",
        ]
        if payload.get("conflicts"):
            out.append(f"Conflicts with: {', '.join(payload['conflicts'])}")
        return "\n".join(out)

    out = ["STAKEHOLDERS:"]
    for s in payload.get("stakeholders") or []:
        out.append(f"  - {s['team_or_person']}: {s['interest']}")
    out.append("ALIGNMENT:")
    for a in payload.get("alignment_checks") or []:
        out.append(f"  - {a['stakeholder']}: {a['alignment']} — {a['gap']}")
    if payload.get("communications"):
        out.append("DRAFTED COMMUNICATIONS:")
        for c in payload["communications"]:
            msg = c['message']
            preview = msg[:160] + ("..." if len(msg) > 160 else "")
            out.append(f"  - [{c['medium']}] to {c['audience']}: {preview}")
    return "\n".join(out)


def _render_persistence(persistence: dict) -> str:
    lines = [f"execution_mode: {persistence.get('execution_mode')}"]
    for p in persistence.get("persisted", []) or []:
        if p.get("kind") == "knowledge_note":
            lines.append(f"  - stored knowledge note: {p.get('ref_id')} (topic: {p.get('topic')})")
    actuated = persistence.get("actuated", []) or []
    if actuated:
        lines.append(f"  - actuated {len(actuated)} Linear entities:")
        for a in actuated:
            ok = "OK" if a.get("success") else "FAIL"
            ref = a.get("identifier") or a.get("id") or "(no-id)"
            lines.append(f"    [{ok}] {a.get('kind')} {ref}: {a.get('name') or a.get('title') or ''}")
    return "\n".join(lines)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8001")), auto_port=False)
