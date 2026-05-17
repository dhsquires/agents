"""Persistence + Linear actuator.

`persist_outcomes` writes the captured knowledge note to `app.memory` scope=agent
and, IF `execution_mode == "execute"`, calls the Linear write skills in parallel.
In `preview` mode (the default), Linear writes are stubbed and the plan is
returned for human review.
"""
from __future__ import annotations

import asyncio
import os
import uuid

from agentfield import AgentRouter

from . import helpers as H

NODE_ID = os.getenv("AGENT_NODE_ID", "chief-of-staff")
router = AgentRouter(prefix="", tags=["persist"])


# ----- Knowledge write ---------------------------------------------------------

@router.reasoner()
async def write_knowledge_note_skill(
    topic: str,
    body: str,
    references: list[str] | None = None,
) -> dict:
    """Write a canonical knowledge note. Returns the persistent ref_id."""
    refs = references or []
    ref_id = f"kb:{topic}:{uuid.uuid4().hex[:8]}"
    try:
        await router.memory.set(
            ref_id,
            {"topic": topic, "body": body, "references": refs},
            scope="agent",
        )
        return {"ref_id": ref_id, "topic": topic, "stored": True}
    except Exception as e:
        return {"ref_id": ref_id, "topic": topic, "stored": False, "error": str(e)}


# ----- Linear write skills -----------------------------------------------------

@router.reasoner()
async def create_linear_initiative_skill(name: str, description: str) -> dict:
    return await H.linear_create_initiative(name=name, description=description)


@router.reasoner()
async def create_linear_project_skill(
    name: str,
    description: str,
    initiative_id: str | None = None,
    team_ids: list[str] | None = None,
) -> dict:
    return await H.linear_create_project(
        name=name,
        description=description,
        initiative_id=initiative_id,
        team_ids=team_ids or [],
    )


@router.reasoner()
async def create_linear_issue_skill(
    title: str,
    description: str,
    team_id: str,
    project_id: str | None = None,
    labels: list[str] | None = None,
) -> dict:
    return await H.linear_create_issue(
        title=title,
        description=description,
        team_id=team_id,
        project_id=project_id,
        labels=labels or [],
    )


# ----- Top-level persistence orchestrator -------------------------------------

@router.reasoner()
async def persist_outcomes(
    intent: str,
    payload: dict,
    execution_mode: str = "preview",
    default_team_id: str = "",
) -> dict:
    """Write knowledge and (optionally) actuate Linear writes.

    `payload` carries the subgraph output for the active intent. The shape we
    look at depends on intent:
      - knowledge_update → payload['note'] = {topic, body, references}
      - new_idea (execute) → payload['initiative_name'], ['planned_projects'][*]
      - modify (execute) → payload['updates'] (we DO NOT auto-mutate in v1;
        deltas are surfaced for human review even in execute mode)
      - status_check / strategic → nothing to persist beyond optional note
    """
    persisted: list[dict] = []
    actuated: list[dict] = []

    # 1. Knowledge note (always for knowledge_update; optional for others)
    if intent == "knowledge_update":
        note = payload.get("note") or {}
        topic = str(note.get("topic") or "general")
        body = str(note.get("body") or "")
        refs = list(note.get("references") or [])
        if body:
            write = await router.call(
                f"{NODE_ID}.write_knowledge_note_skill",
                topic=topic,
                body=body,
                references=refs,
            )
            persisted.append({"kind": "knowledge_note", **write})

    # 2. Linear writes (only in execute mode, only for new_idea intent in v1)
    if execution_mode == "execute" and intent == "new_idea":
        initiative_name = payload.get("initiative_name") or "Untitled initiative"
        initiative_scope = payload.get("one_paragraph_scope") or ""
        ini = await router.call(
            f"{NODE_ID}.create_linear_initiative_skill",
            name=initiative_name,
            description=initiative_scope,
        )
        actuated.append({"kind": "initiative", **ini})
        initiative_id = ini.get("id") if ini.get("success") else None

        projects = payload.get("planned_projects") or []
        project_results = await asyncio.gather(*[
            router.call(
                f"{NODE_ID}.create_linear_project_skill",
                name=p.get("name", ""),
                description=p.get("scope", ""),
                initiative_id=initiative_id,
                team_ids=[default_team_id] if default_team_id else [],
            )
            for p in projects
        ]) if projects else []

        for p_spec, p_result in zip(projects, project_results):
            actuated.append({"kind": "project", **p_result})
            project_id = p_result.get("id") if p_result.get("success") else None
            issues = p_spec.get("drafted_issues") or []
            issue_results = await asyncio.gather(*[
                router.call(
                    f"{NODE_ID}.create_linear_issue_skill",
                    title=i.get("title", ""),
                    description=i.get("description", ""),
                    team_id=default_team_id or "",
                    project_id=project_id,
                    labels=i.get("labels") or [],
                )
                for i in issues
            ]) if issues else []
            for ir in issue_results:
                actuated.append({"kind": "issue", **ir})

    return {
        "persisted": persisted,
        "actuated": actuated,
        "execution_mode": execution_mode,
    }
