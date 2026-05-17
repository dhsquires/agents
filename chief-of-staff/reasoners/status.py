"""Status synthesis subgraph (status_check intent).

Per-initiative analyzers fan out in parallel. Each combines a deterministic
completion-percent skill with two .ai() judgments (velocity + blockers) and
produces an InitiativeProgress carrying Linear citations.
"""
from __future__ import annotations

import asyncio
import os

from agentfield import AgentRouter

from . import helpers as H
from .models import (
    Blocker, BlockerScan, InitiativeProgress, StatusSynthesis,
    VelocityJudgment,
)

NODE_ID = os.getenv("AGENT_NODE_ID", "chief-of-staff")
router = AgentRouter(prefix="", tags=["status"])


@router.reasoner()
async def compute_completion_skill(completed: int, total: int) -> dict:
    return {"percent": H.compute_completion_percent(completed, total)}


@router.reasoner()
async def judge_velocity(
    initiative_name: str,
    project_lines: str,
    model: str | None = None,
) -> VelocityJudgment:
    if not project_lines.strip():
        return VelocityJudgment(
            trend="unknown",
            rationale="No projects found under this initiative.",
            confident=True,
        )
    result = await router.ai(
        system=(
            "You judge velocity from a small project portfolio. Pick exactly one "
            "trend: accelerating / steady / slowing / stalled / unknown. Provide a "
            "1-sentence rationale citing the project IDs. If the data is too sparse "
            "to judge (no started projects, no progress numbers), use 'unknown' and "
            "set confident=true."
        ),
        user=f"INITIATIVE: {initiative_name}\nPROJECTS:\n{project_lines}",
        schema=VelocityJudgment,
        model=model,
    )
    if not result.confident:
        return H.fallback_velocity_judgment()
    return result


@router.reasoner()
async def find_blockers(
    initiative_name: str,
    issue_lines: str,
    model: str | None = None,
) -> BlockerScan:
    if not issue_lines.strip():
        return BlockerScan(blockers=[], confident=True)
    result = await router.ai(
        system=(
            "Scan the issues under this initiative for blockers. A blocker is an "
            "issue that is stalled, waiting on something external, or has an "
            "explicit blocked_reason. For each blocker return: issue_ref (the "
            "identifier you see in the input), a 1-sentence summary, and severity. "
            "Return [] if none are blocked. Do not fabricate blockers."
        ),
        user=f"INITIATIVE: {initiative_name}\nISSUES:\n{issue_lines}",
        schema=BlockerScan,
        model=model,
    )
    if not result.confident:
        return H.fallback_blocker_scan()
    return result


@router.reasoner()
async def analyze_initiative_progress(
    initiative: dict,
    projects: list,
    issues: list,
    model: str | None = None,
) -> InitiativeProgress:
    """Orchestrator per-initiative. Deterministic %, parallel velocity + blockers."""
    init_id = initiative.get("id") or "UNKNOWN"
    init_name = initiative.get("name") or init_id

    related_projects = [p for p in projects if p.get("initiative_id") == init_id]
    project_ids = {p.get("id") for p in related_projects}
    related_issues = [i for i in issues if i.get("project_id") in project_ids]

    completed = sum(int(p.get("completed_issue_count") or 0) for p in related_projects)
    total = sum(int(p.get("total_issue_count") or 0) for p in related_projects)
    completion_dict = await router.call(
        f"{NODE_ID}.compute_completion_skill",
        completed=completed,
        total=total,
    )

    project_lines = "\n".join(
        f"  - [{p.get('id')}] {p.get('name')} (state: {p.get('state')}, "
        f"progress: {p.get('completed_issue_count')}/{p.get('total_issue_count')}, "
        f"lead: {p.get('lead')})"
        for p in related_projects
    ) or "(no projects)"
    issue_lines = "\n".join(
        f"  - [{i.get('identifier') or i.get('id')}] {i.get('title')} "
        f"(state: {i.get('state')}, assignee: {i.get('assignee')})"
        + (f" — {i.get('blocked_reason')}" if i.get("blocked_reason") else "")
        for i in related_issues
    ) or "(no issues)"

    velocity_dict, blocker_dict = await asyncio.gather(
        router.call(
            f"{NODE_ID}.judge_velocity",
            initiative_name=init_name,
            project_lines=project_lines,
            model=model,
        ),
        router.call(
            f"{NODE_ID}.find_blockers",
            initiative_name=init_name,
            issue_lines=issue_lines,
            model=model,
        ),
    )
    velocity = VelocityJudgment(**velocity_dict)
    blockers = BlockerScan(**blocker_dict).blockers

    citations: list[str] = [str(init_id)]
    citations.extend(str(p.get("id")) for p in related_projects if p.get("id"))
    citations.extend(
        str(i.get("identifier") or i.get("id")) for i in related_issues if i.get("identifier") or i.get("id")
    )

    return InitiativeProgress(
        initiative_ref=str(init_id),
        name=init_name,
        percent_complete=int(completion_dict.get("percent", 0)),
        velocity_trend=velocity.trend,
        velocity_rationale=velocity.rationale,
        blockers=blockers,
        citations=citations,
    )


@router.reasoner()
async def compose_status_narrative(
    progress_prose: str,
    directive: str,
    model: str | None = None,
) -> dict:
    """Returns a narrative string. Plain prose, not a schema."""
    if not progress_prose.strip():
        return {
            "narrative": "No active initiatives found to report on.",
            "confident": True,
        }
    text = await router.ai(
        system=(
            "Compose a tight status narrative for an engineering leader. Lead with "
            "the headline (3-4 sentences): overall trend, biggest win, biggest "
            "concern. Then list initiative-by-initiative bullets (1 line each) "
            "citing initiative IDs in [brackets]. Then a 'Watch list' of named "
            "blockers, each with its issue ID in [brackets]. Be specific. No filler. "
            "Maximum 250 words."
        ),
        user=f"DIRECTIVE: {directive}\n\nPROGRESS DATA:\n{progress_prose}",
        model=model,
    )
    return {"narrative": str(text), "confident": True}


@router.reasoner()
async def synthesize_status(
    directive: str,
    context_payload: dict,
    model: str | None = None,
) -> StatusSynthesis:
    """Top-level status orchestrator."""
    linear_state = context_payload.get("linear_state", {}) or {}
    initiatives = linear_state.get("initiatives", []) or []
    projects = linear_state.get("projects", []) or []
    issues = linear_state.get("issues", []) or []

    if not initiatives:
        return StatusSynthesis(
            initiatives=[],
            narrative="No initiatives found in Linear. Nothing to report on.",
            citations=context_payload.get("citations", []) or [],
        )

    progress_dicts = await asyncio.gather(*[
        router.call(
            f"{NODE_ID}.analyze_initiative_progress",
            initiative=init,
            projects=projects,
            issues=issues,
            model=model,
        )
        for init in initiatives
    ])
    progress = [InitiativeProgress(**d) for d in progress_dicts]

    progress_prose = "\n\n".join(
        f"INITIATIVE [{p.initiative_ref}] {p.name}\n"
        f"  Completion: {p.percent_complete}%\n"
        f"  Velocity: {p.velocity_trend} — {p.velocity_rationale}\n"
        f"  Blockers: "
        + (
            "\n    - " + "\n    - ".join(
                f"[{b.issue_ref}] ({b.severity}) {b.summary}" for b in p.blockers
            )
            if p.blockers else "none"
        )
        for p in progress
    )
    narrative_dict = await router.call(
        f"{NODE_ID}.compose_status_narrative",
        progress_prose=progress_prose,
        directive=directive,
        model=model,
    )

    all_citations: list[str] = []
    for p in progress:
        all_citations.extend(p.citations)

    return StatusSynthesis(
        initiatives=progress,
        narrative=str(narrative_dict.get("narrative", "")),
        citations=all_citations,
    )
