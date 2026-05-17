"""Initiative-planning subgraph (the deepest part of the system).

This is where the new_idea intent decomposes into projects, then into issues.
Meta-prompting happens at decompose_into_projects (N runtime) and draft_issues
(M runtime). Per-issue work fans out into compose_issue_body + assess_issue_owner
in parallel.
"""
from __future__ import annotations

import asyncio
import os

from agentfield import AgentRouter

from . import helpers as H
from .models import (
    DependencyEdge, DependencyPlan, DraftedIssue, InitiativePlan,
    InitiativeScope, IssueBody, IssueDraftPlan, IssueSpec, OwnerSuggestion,
    PlannedProject, ProjectDecomposition, ProjectSpec, Risk, RiskAnalysis,
)

NODE_ID = os.getenv("AGENT_NODE_ID", "chief-of-staff")
router = AgentRouter(prefix="", tags=["initiative"])


# ----- Scope the initiative ---------------------------------------------------

@router.reasoner()
async def scope_initiative(
    directive: str,
    linear_state_prose: str,
    knowledge_prose: str,
    model: str | None = None,
) -> InitiativeScope:
    result = await router.ai(
        system=(
            "You are an engineering chief-of-staff scoping a new initiative. Produce "
            "a concise one-paragraph scope (3-5 sentences) and 3-5 crisp success "
            "criteria (each a single short sentence). Anchor wording in the existing "
            "Linear state when relevant; do NOT invent IDs. If the directive is too "
            "vague to scope responsibly, set confident=false and provide what you can."
        ),
        user=(
            f"DIRECTIVE:\n{directive}\n\n"
            f"EXISTING LINEAR STATE (cite IDs when referencing):\n{linear_state_prose}\n\n"
            f"RELEVANT KNOWLEDGE:\n{knowledge_prose or '(none)'}"
        ),
        schema=InitiativeScope,
        model=model,
    )
    if not result.confident:
        return H.fallback_initiative_scope(result.name, "Initiative scoper was not confident.")
    return result


# ----- Decompose initiative into projects (META: spawns N project planners) ---

@router.reasoner()
async def decompose_into_projects(
    scope_prose: str,
    linear_state_prose: str,
    model: str | None = None,
) -> ProjectDecomposition:
    result = await router.ai(
        system=(
            "Decompose this initiative scope into 2-5 distinct projects. Each project "
            "must (a) be independently shippable, (b) own a clear slice of the scope, "
            "(c) be small enough for one team to execute. Order with sequence_hint "
            "(1=earliest). If existing Linear projects could absorb part of the scope, "
            "you may name them in `scope`. Keep the total to ≤5 projects."
        ),
        user=f"INITIATIVE SCOPE:\n{scope_prose}\n\nEXISTING LINEAR STATE:\n{linear_state_prose}",
        schema=ProjectDecomposition,
        model=model,
    )
    if not result.confident:
        return H.fallback_project_decomposition()
    return result


# ----- Draft issues for one project (META: spawns M issue drafters) -----------

@router.reasoner()
async def draft_issues(
    project_name: str,
    project_scope: str,
    model: str | None = None,
) -> IssueDraftPlan:
    result = await router.ai(
        system=(
            "Draft 3-6 individual issues that, taken together, would deliver this "
            "project. Each issue title should be a single concrete deliverable in "
            "imperative voice (e.g., 'Add Postgres index on orders.user_id'). The "
            "scope field is a 1-2 sentence acceptance summary. Do NOT bundle multiple "
            "concerns into one issue. Do NOT write more than 6 issues."
        ),
        user=f"PROJECT: {project_name}\nSCOPE: {project_scope}",
        schema=IssueDraftPlan,
        model=model,
    )
    if not result.confident:
        return H.fallback_issue_draft_plan()
    return result


# ----- Per-issue: body + owner (parallel) -------------------------------------

@router.reasoner()
async def compose_issue_body(
    title: str,
    scope: str,
    project_name: str,
    model: str | None = None,
) -> IssueBody:
    result = await router.ai(
        system=(
            "Expand this issue into a concrete Linear issue body. Produce: "
            "(1) the final imperative title (≤80 chars), "
            "(2) a markdown description with sections '## Context', "
            "'## Acceptance criteria' (bullet list), '## Out of scope', "
            "(3) 1-4 labels (e.g., 'eng', 'reliability', 'tech-debt', 'spike')."
        ),
        user=f"PROJECT: {project_name}\nWORKING TITLE: {title}\nSCOPE: {scope}",
        schema=IssueBody,
        model=model,
    )
    if not result.confident:
        return H.fallback_issue_body(title, scope)
    return result


@router.reasoner()
async def assess_issue_owner(
    title: str,
    scope: str,
    team_topology_prose: str,
    model: str | None = None,
) -> OwnerSuggestion:
    result = await router.ai(
        system=(
            "Suggest the best team or person to own this issue based on the team "
            "topology provided. Prefer a team name over a person unless a specific "
            "person clearly owns the area. Provide a 1-sentence rationale. "
            "If the topology is empty or unclear, set confident=false and propose "
            "'NEEDS_HUMAN_REVIEW'."
        ),
        user=(
            f"ISSUE TITLE: {title}\nSCOPE: {scope}\n\n"
            f"TEAM TOPOLOGY:\n{team_topology_prose or '(none)'}"
        ),
        schema=OwnerSuggestion,
        model=model,
    )
    if not result.confident:
        return H.fallback_owner_suggestion()
    return result


@router.reasoner()
async def draft_issue(
    title: str,
    scope: str,
    project_name: str,
    team_topology_prose: str,
    model: str | None = None,
) -> DraftedIssue:
    """Per-issue orchestrator: body + owner in parallel, then merge."""
    body_dict, owner_dict = await asyncio.gather(
        router.call(
            f"{NODE_ID}.compose_issue_body",
            title=title,
            scope=scope,
            project_name=project_name,
            model=model,
        ),
        router.call(
            f"{NODE_ID}.assess_issue_owner",
            title=title,
            scope=scope,
            team_topology_prose=team_topology_prose,
            model=model,
        ),
    )
    body = IssueBody(**body_dict)
    owner = OwnerSuggestion(**owner_dict)
    return DraftedIssue(
        title=body.title,
        description=body.description,
        labels=body.labels,
        owner_suggestion=owner.team_or_person,
        owner_rationale=owner.rationale,
    )


# ----- Project-level dependency planner ---------------------------------------

@router.reasoner()
async def plan_project_dependencies(
    project_name: str,
    issue_titles_csv: str,
    model: str | None = None,
) -> DependencyPlan:
    if not issue_titles_csv.strip():
        return DependencyPlan(edges=[], confident=True)
    result = await router.ai(
        system=(
            "Given a project and its issue titles, list ONLY the dependencies that "
            "are obviously required by the work itself (e.g., 'X must land before Y' "
            "because Y depends on X's output). If there are no obvious dependencies, "
            "return an empty list. Do not invent dependencies."
        ),
        user=f"PROJECT: {project_name}\nISSUES:\n{issue_titles_csv}",
        schema=DependencyPlan,
        model=model,
    )
    if not result.confident:
        return H.fallback_dependency_plan()
    return result


# ----- Project orchestrator: drafts all issues in parallel --------------------

@router.reasoner()
async def plan_project(
    project_name: str,
    project_scope: str,
    sequence_hint: int,
    team_topology_prose: str,
    model: str | None = None,
) -> PlannedProject:
    plan_dict = await router.call(
        f"{NODE_ID}.draft_issues",
        project_name=project_name,
        project_scope=project_scope,
        model=model,
    )
    plan = IssueDraftPlan(**plan_dict)

    if not plan.issues:
        return PlannedProject(
            name=project_name,
            scope=project_scope,
            sequence_hint=sequence_hint,
            drafted_issues=[],
            dependencies=[],
        )

    issue_dicts = await asyncio.gather(*[
        router.call(
            f"{NODE_ID}.draft_issue",
            title=spec.title,
            scope=spec.scope,
            project_name=project_name,
            team_topology_prose=team_topology_prose,
            model=model,
        )
        for spec in plan.issues
    ])
    drafted = [DraftedIssue(**d) for d in issue_dicts]

    issue_titles_csv = "\n".join(f"- {d.title}" for d in drafted)
    dep_dict = await router.call(
        f"{NODE_ID}.plan_project_dependencies",
        project_name=project_name,
        issue_titles_csv=issue_titles_csv,
        model=model,
    )
    deps = DependencyPlan(**dep_dict).edges

    return PlannedProject(
        name=project_name,
        scope=project_scope,
        sequence_hint=sequence_hint,
        drafted_issues=drafted,
        dependencies=deps,
    )


# ----- Risks -------------------------------------------------------------------

@router.reasoner()
async def assess_risks(
    scope_prose: str,
    planned_projects_prose: str,
    model: str | None = None,
) -> RiskAnalysis:
    result = await router.ai(
        system=(
            "Identify 2-5 concrete risks to delivering this initiative. For each, "
            "name a specific risk (not generic), classify severity, and propose a "
            "single concrete mitigation. Avoid 'team capacity' and 'scope creep' "
            "unless you can name the specific reason. Be honest if you don't have "
            "enough context — set confident=false in that case."
        ),
        user=f"SCOPE:\n{scope_prose}\n\nPLANNED PROJECTS:\n{planned_projects_prose}",
        schema=RiskAnalysis,
        model=model,
    )
    if not result.confident:
        return H.fallback_risk_analysis()
    return result


# ----- Top of the initiative subgraph -----------------------------------------

@router.reasoner()
async def plan_initiative(
    directive: str,
    context_payload: dict,
    model: str | None = None,
) -> InitiativePlan:
    """Top-level orchestrator for the new_idea intent.

    1. Scope the initiative
    2. In parallel: decompose into projects, and pre-assess generic risks
    3. Fan-out plan_project over the N projects
    4. Re-assess risks against the concrete plan, then synthesize
    """
    linear_state_prose = context_payload.get("linear_state_prose", "")
    knowledge = context_payload.get("knowledge", {}) or {}
    knowledge_prose = H.render_knowledge(knowledge.get("hits") or [])
    topology = context_payload.get("team_topology", {}) or {}
    topology_prose = "\n".join(
        f"- {o.get('team')} owns {o.get('owns')}: {o.get('rationale')}"
        for o in topology.get("ownerships", []) or []
    ) or "(no topology mapped)"

    scope_dict = await router.call(
        f"{NODE_ID}.scope_initiative",
        directive=directive,
        linear_state_prose=linear_state_prose,
        knowledge_prose=knowledge_prose,
        model=model,
    )
    scope = InitiativeScope(**scope_dict)
    scope_prose = (
        f"Name: {scope.name}\n"
        f"Scope: {scope.one_paragraph_scope}\n"
        f"Success criteria: {'; '.join(scope.success_criteria)}"
    )

    decomp_dict = await router.call(
        f"{NODE_ID}.decompose_into_projects",
        scope_prose=scope_prose,
        linear_state_prose=linear_state_prose,
        model=model,
    )
    decomp = ProjectDecomposition(**decomp_dict)

    if not decomp.projects:
        return InitiativePlan(
            initiative_name=scope.name,
            one_paragraph_scope=scope.one_paragraph_scope,
            success_criteria=scope.success_criteria,
            planned_projects=[],
            risks=[],
            citations=context_payload.get("citations", []) or [],
        )

    project_dicts = await asyncio.gather(*[
        router.call(
            f"{NODE_ID}.plan_project",
            project_name=p.name,
            project_scope=p.scope,
            sequence_hint=p.sequence_hint,
            team_topology_prose=topology_prose,
            model=model,
        )
        for p in decomp.projects
    ])
    planned = [PlannedProject(**d) for d in project_dicts]

    planned_prose = H.render_planned_projects([p.model_dump() for p in planned])
    risk_dict = await router.call(
        f"{NODE_ID}.assess_risks",
        scope_prose=scope_prose,
        planned_projects_prose=planned_prose,
        model=model,
    )
    risks = RiskAnalysis(**risk_dict).risks

    return InitiativePlan(
        initiative_name=scope.name,
        one_paragraph_scope=scope.one_paragraph_scope,
        success_criteria=scope.success_criteria,
        planned_projects=planned,
        risks=risks,
        citations=context_payload.get("citations", []) or [],
    )
