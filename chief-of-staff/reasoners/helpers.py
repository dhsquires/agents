"""Plain-Python helpers: Linear GraphQL client, prose renderers, fallbacks.

These are intentionally NOT decorated as `@app.skill` — they are internal
utilities consumed inside reasoner bodies. A few of them are exposed through
`@router.reasoner()` wrappers in the individual reasoner files for places
where another reasoner needs to invoke them via `app.call(...)`.
"""
from __future__ import annotations

import asyncio
import os
from typing import Any

import httpx

from .models import (
    BlockerScan, ConflictCheck, CanonicalNote, CanonicalTopic,
    DependencyPlan, EntityExtraction, HumanResponse, ImpactScope,
    IntentClassification, InitiativeScope, IssueBody, IssueDraftPlan,
    KnowledgeRetrieval, OwnerSuggestion, ProjectDecomposition,
    RiskAnalysis, StakeholderMap, StatusSynthesis, TeamTopology,
    UpdateSpec, VelocityJudgment,
)

LINEAR_API_URL = "https://api.linear.app/graphql"
LINEAR_KEY_ENV = "LINEAR_API_KEY"


def linear_enabled() -> bool:
    return bool(os.getenv(LINEAR_KEY_ENV))


async def linear_graphql(query: str, variables: dict | None = None) -> dict:
    """Execute a Linear GraphQL request. Raises on transport/auth failure."""
    key = os.getenv(LINEAR_KEY_ENV)
    if not key:
        raise RuntimeError("LINEAR_API_KEY is not set")
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            LINEAR_API_URL,
            headers={
                "Authorization": key,
                "Content-Type": "application/json",
            },
            json={"query": query, "variables": variables or {}},
        )
        resp.raise_for_status()
        body = resp.json()
        if "errors" in body and body["errors"]:
            raise RuntimeError(f"Linear GraphQL error: {body['errors']}")
        return body.get("data", {})


# ---------------- Mock fixtures (used when LINEAR_API_KEY is absent) -----------

def _mock_initiatives() -> list[dict]:
    return [
        {
            "id": "INI-MOCK-1",
            "name": "[MOCK] Developer Productivity 2026",
            "description": "Lift developer cycle time across services.",
            "state": "InProgress",
        },
        {
            "id": "INI-MOCK-2",
            "name": "[MOCK] Reliability & SLO Maturity",
            "description": "Reach 99.95% on tier-1 surfaces.",
            "state": "Planned",
        },
    ]


def _mock_projects() -> list[dict]:
    return [
        {
            "id": "PRJ-MOCK-1",
            "name": "[MOCK] CI pipeline refactor",
            "description": "Cut median pipeline time by 40%.",
            "state": "started",
            "initiative_id": "INI-MOCK-1",
            "lead": "alice",
            "completed_issue_count": 6,
            "total_issue_count": 18,
        },
        {
            "id": "PRJ-MOCK-2",
            "name": "[MOCK] Test flake elimination",
            "description": "Triage and stabilize the top-50 flaky tests.",
            "state": "started",
            "initiative_id": "INI-MOCK-1",
            "lead": "bob",
            "completed_issue_count": 3,
            "total_issue_count": 12,
        },
        {
            "id": "PRJ-MOCK-3",
            "name": "[MOCK] SLO instrumentation pass",
            "description": "Wire SLO metrics for the checkout and search surfaces.",
            "state": "planned",
            "initiative_id": "INI-MOCK-2",
            "lead": "carol",
            "completed_issue_count": 0,
            "total_issue_count": 9,
        },
    ]


def _mock_issues() -> list[dict]:
    return [
        {
            "id": "ISS-MOCK-1",
            "identifier": "ENG-204",
            "title": "[MOCK] CI: cache npm install across PR builds",
            "state": "started",
            "project_id": "PRJ-MOCK-1",
            "assignee": "alice",
            "priority": 2,
        },
        {
            "id": "ISS-MOCK-2",
            "identifier": "ENG-211",
            "title": "[MOCK] Parallelize backend test suite",
            "state": "todo",
            "project_id": "PRJ-MOCK-1",
            "assignee": None,
            "priority": 2,
            "blocked_reason": "Waiting on shared fixtures redesign",
        },
        {
            "id": "ISS-MOCK-3",
            "identifier": "ENG-156",
            "title": "[MOCK] Quarantine test_payment_retry flake",
            "state": "in_review",
            "project_id": "PRJ-MOCK-2",
            "assignee": "bob",
            "priority": 1,
        },
        {
            "id": "ISS-MOCK-4",
            "identifier": "REL-12",
            "title": "[MOCK] Define checkout SLO + alerts",
            "state": "backlog",
            "project_id": "PRJ-MOCK-3",
            "assignee": None,
            "priority": 3,
        },
    ]


def _mock_teams() -> list[dict]:
    return [
        {"id": "TEAM-ENG", "name": "Engineering", "key": "ENG", "members": ["alice", "bob"]},
        {"id": "TEAM-REL", "name": "Reliability", "key": "REL", "members": ["carol"]},
    ]


# ---------------- Read APIs (with mock fallback) -------------------------------

INITIATIVES_QUERY = """
query Initiatives($first: Int!) {
  initiatives(first: $first) {
    nodes { id name description status { name } }
  }
}
"""

PROJECTS_QUERY = """
query Projects($first: Int!) {
  projects(first: $first) {
    nodes {
      id name description state
      lead { name displayName }
      initiative { id }
      issues(first: 0) { pageInfo { hasNextPage } }
      completedIssueCountHistory
      scopeHistory
    }
  }
}
"""

ISSUES_QUERY = """
query Issues($first: Int!) {
  issues(first: $first) {
    nodes {
      id identifier title priority
      state { name }
      assignee { name displayName }
      project { id }
    }
  }
}
"""

TEAMS_QUERY = """
query Teams($first: Int!) {
  teams(first: $first) {
    nodes {
      id name key
      members { nodes { name displayName } }
    }
  }
}
"""


async def linear_list_initiatives(limit: int = 20) -> list[dict]:
    if not linear_enabled():
        return _mock_initiatives()
    try:
        data = await linear_graphql(INITIATIVES_QUERY, {"first": limit})
        nodes = data.get("initiatives", {}).get("nodes", []) or []
        return [
            {
                "id": n["id"],
                "name": n.get("name", ""),
                "description": n.get("description", ""),
                "state": (n.get("status") or {}).get("name", "Unknown"),
            }
            for n in nodes
        ]
    except Exception as e:
        return [{"id": "ERR", "name": f"[LINEAR ERROR] {e!s}", "description": "", "state": "error"}]


async def linear_list_projects(limit: int = 50) -> list[dict]:
    if not linear_enabled():
        return _mock_projects()
    try:
        data = await linear_graphql(PROJECTS_QUERY, {"first": limit})
        nodes = data.get("projects", {}).get("nodes", []) or []
        out = []
        for n in nodes:
            scope_history = n.get("scopeHistory") or []
            completed_history = n.get("completedIssueCountHistory") or []
            total = scope_history[-1] if scope_history else 0
            done = completed_history[-1] if completed_history else 0
            out.append({
                "id": n["id"],
                "name": n.get("name", ""),
                "description": n.get("description", ""),
                "state": n.get("state", "unknown"),
                "initiative_id": (n.get("initiative") or {}).get("id"),
                "lead": ((n.get("lead") or {}).get("displayName")
                         or (n.get("lead") or {}).get("name") or ""),
                "completed_issue_count": done,
                "total_issue_count": total,
            })
        return out
    except Exception as e:
        return [{"id": "ERR", "name": f"[LINEAR ERROR] {e!s}", "description": "",
                 "state": "error", "initiative_id": None, "lead": "",
                 "completed_issue_count": 0, "total_issue_count": 0}]


async def linear_list_issues(limit: int = 50) -> list[dict]:
    if not linear_enabled():
        return _mock_issues()
    try:
        data = await linear_graphql(ISSUES_QUERY, {"first": limit})
        nodes = data.get("issues", {}).get("nodes", []) or []
        return [
            {
                "id": n["id"],
                "identifier": n.get("identifier", ""),
                "title": n.get("title", ""),
                "state": (n.get("state") or {}).get("name", "unknown"),
                "project_id": (n.get("project") or {}).get("id"),
                "assignee": ((n.get("assignee") or {}).get("displayName")
                             or (n.get("assignee") or {}).get("name")),
                "priority": n.get("priority", 0),
            }
            for n in nodes
        ]
    except Exception as e:
        return [{"id": "ERR", "identifier": "ERR", "title": f"[LINEAR ERROR] {e!s}",
                 "state": "error", "project_id": None, "assignee": None, "priority": 0}]


async def linear_list_teams(limit: int = 20) -> list[dict]:
    if not linear_enabled():
        return _mock_teams()
    try:
        data = await linear_graphql(TEAMS_QUERY, {"first": limit})
        nodes = data.get("teams", {}).get("nodes", []) or []
        return [
            {
                "id": n["id"],
                "name": n.get("name", ""),
                "key": n.get("key", ""),
                "members": [
                    (m.get("displayName") or m.get("name") or "")
                    for m in ((n.get("members") or {}).get("nodes") or [])
                ],
            }
            for n in nodes
        ]
    except Exception as e:
        return [{"id": "ERR", "name": f"[LINEAR ERROR] {e!s}", "key": "ERR", "members": []}]


# ---------------- Write APIs ---------------------------------------------------

CREATE_ISSUE_MUTATION = """
mutation IssueCreate($input: IssueCreateInput!) {
  issueCreate(input: $input) {
    success
    issue { id identifier title url }
  }
}
"""

CREATE_PROJECT_MUTATION = """
mutation ProjectCreate($input: ProjectCreateInput!) {
  projectCreate(input: $input) {
    success
    project { id name url }
  }
}
"""

CREATE_INITIATIVE_MUTATION = """
mutation InitiativeCreate($input: InitiativeCreateInput!) {
  initiativeCreate(input: $input) {
    success
    initiative { id name }
  }
}
"""


async def linear_create_issue(*, title: str, description: str, team_id: str,
                              project_id: str | None = None,
                              labels: list[str] | None = None) -> dict:
    if not linear_enabled():
        return {"id": f"ISS-PREVIEW", "identifier": "PREVIEW",
                "title": title, "url": "(preview — no LINEAR_API_KEY set)",
                "success": False, "preview": True}
    try:
        payload: dict[str, Any] = {
            "title": title,
            "description": description,
            "teamId": team_id,
        }
        if project_id:
            payload["projectId"] = project_id
        data = await linear_graphql(CREATE_ISSUE_MUTATION, {"input": payload})
        issue = (data.get("issueCreate") or {}).get("issue") or {}
        return {
            "id": issue.get("id", ""),
            "identifier": issue.get("identifier", ""),
            "title": issue.get("title", title),
            "url": issue.get("url", ""),
            "success": bool((data.get("issueCreate") or {}).get("success")),
        }
    except Exception as e:
        return {"id": "ERR", "identifier": "ERR", "title": title,
                "url": "", "success": False, "error": str(e)}


async def linear_create_project(*, name: str, description: str,
                                initiative_id: str | None = None,
                                team_ids: list[str] | None = None) -> dict:
    if not linear_enabled():
        return {"id": "PRJ-PREVIEW", "name": name,
                "url": "(preview — no LINEAR_API_KEY set)",
                "success": False, "preview": True}
    try:
        payload: dict[str, Any] = {
            "name": name,
            "description": description,
            "teamIds": team_ids or [],
        }
        if initiative_id:
            payload["initiativeId"] = initiative_id
        data = await linear_graphql(CREATE_PROJECT_MUTATION, {"input": payload})
        project = (data.get("projectCreate") or {}).get("project") or {}
        return {
            "id": project.get("id", ""),
            "name": project.get("name", name),
            "url": project.get("url", ""),
            "success": bool((data.get("projectCreate") or {}).get("success")),
        }
    except Exception as e:
        return {"id": "ERR", "name": name, "url": "", "success": False, "error": str(e)}


async def linear_create_initiative(*, name: str, description: str) -> dict:
    if not linear_enabled():
        return {"id": "INI-PREVIEW", "name": name,
                "success": False, "preview": True}
    try:
        data = await linear_graphql(CREATE_INITIATIVE_MUTATION,
                                    {"input": {"name": name, "description": description}})
        ini = (data.get("initiativeCreate") or {}).get("initiative") or {}
        return {
            "id": ini.get("id", ""),
            "name": ini.get("name", name),
            "success": bool((data.get("initiativeCreate") or {}).get("success")),
        }
    except Exception as e:
        return {"id": "ERR", "name": name, "success": False, "error": str(e)}


# ---------------- Prose renderers ---------------------------------------------

def render_linear_state(state: dict) -> str:
    inits = state.get("initiatives", []) or []
    projs = state.get("projects", []) or []
    issues = state.get("issues", []) or []
    teams = state.get("teams", []) or []
    lines = []
    if inits:
        lines.append("INITIATIVES:")
        for i in inits:
            lines.append(f"  - [{i.get('id')}] {i.get('name')} (state: {i.get('state')}) — {i.get('description') or '(no description)'}")
    if projs:
        lines.append("PROJECTS:")
        for p in projs:
            lines.append(
                f"  - [{p.get('id')}] {p.get('name')} (state: {p.get('state')}, "
                f"initiative: {p.get('initiative_id')}, lead: {p.get('lead')}, "
                f"progress: {p.get('completed_issue_count')}/{p.get('total_issue_count')})"
            )
    if issues:
        lines.append("RECENT ISSUES:")
        for it in issues:
            extra = f" — {it.get('blocked_reason')}" if it.get("blocked_reason") else ""
            lines.append(
                f"  - [{it.get('identifier') or it.get('id')}] {it.get('title')} "
                f"(state: {it.get('state')}, assignee: {it.get('assignee')}, "
                f"project: {it.get('project_id')}){extra}"
            )
    if teams:
        lines.append("TEAMS:")
        for t in teams:
            lines.append(f"  - [{t.get('id')}] {t.get('name')} ({t.get('key')}) — members: {', '.join(t.get('members', []))}")
    return "\n".join(lines) or "(no Linear state available)"


def render_knowledge(hits: list[dict]) -> str:
    if not hits:
        return "(no relevant knowledge entries)"
    return "\n".join(
        f"- [{h.get('ref_id')}] {h.get('topic')}: {h.get('excerpt')}"
        for h in hits
    )


def render_intent(intent_dict: dict, entity_dict: dict) -> str:
    refs = []
    for k, label in (
        ("initiative_refs", "initiatives"),
        ("project_refs", "projects"),
        ("issue_refs", "issues"),
        ("people_or_team_refs", "people/teams"),
    ):
        vals = entity_dict.get(k) or []
        if vals:
            refs.append(f"{label}={', '.join(vals)}")
    return (
        f"Intent: {intent_dict.get('intent')} (confident={intent_dict.get('confident')}); "
        f"rationale: {intent_dict.get('rationale')}. "
        f"Mentioned refs: {'; '.join(refs) if refs else '(none)'}"
    )


def render_planned_projects(projects: list[dict]) -> str:
    out = []
    for p in projects:
        out.append(f"\nPROJECT: {p['name']} (sequence={p['sequence_hint']})")
        out.append(f"  Scope: {p['scope']}")
        out.append("  Issues:")
        for i in p.get("drafted_issues", []):
            out.append(f"    - {i['title']} — owner: {i['owner_suggestion']} ({i['owner_rationale']})")
            out.append(f"      labels: {', '.join(i.get('labels') or [])}")
            out.append(f"      desc: {i['description'][:120]}{'...' if len(i['description'])>120 else ''}")
        if p.get("dependencies"):
            out.append("  Dependencies:")
            for d in p["dependencies"]:
                out.append(f"    - {d['from_issue_title']} → {d['to_issue_title']} ({d['rationale']})")
    return "\n".join(out) or "(no projects planned)"


# ---------------- Deterministic safe-default fallbacks -------------------------

def fallback_intent(reason: str) -> IntentClassification:
    return IntentClassification(intent="strategic", rationale=f"[fallback] {reason}", confident=False)


def fallback_entity_extraction() -> EntityExtraction:
    return EntityExtraction(confident=False)


def fallback_knowledge_retrieval() -> KnowledgeRetrieval:
    return KnowledgeRetrieval(confident=False)


def fallback_team_topology() -> TeamTopology:
    return TeamTopology(confident=False)


def fallback_initiative_scope(name: str, reason: str) -> InitiativeScope:
    return InitiativeScope(
        name=name or "Unnamed initiative",
        one_paragraph_scope=f"[NEEDS_HUMAN_REVIEW] {reason}",
        success_criteria=[],
        confident=False,
    )


def fallback_project_decomposition() -> ProjectDecomposition:
    return ProjectDecomposition(confident=False)


def fallback_issue_draft_plan() -> IssueDraftPlan:
    return IssueDraftPlan(confident=False)


def fallback_issue_body(title: str, scope: str) -> IssueBody:
    return IssueBody(
        title=title or "Untitled issue",
        description=f"[NEEDS_HUMAN_REVIEW] Auto-drafting was not confident. Scope was: {scope}",
        labels=["needs-human-review"],
        confident=False,
    )


def fallback_owner_suggestion() -> OwnerSuggestion:
    return OwnerSuggestion(
        team_or_person="NEEDS_HUMAN_REVIEW",
        rationale="Auto-owner suggestion was not confident.",
        confident=False,
    )


def fallback_dependency_plan() -> DependencyPlan:
    return DependencyPlan(confident=False)


def fallback_risk_analysis() -> RiskAnalysis:
    return RiskAnalysis(confident=False)


def fallback_velocity_judgment() -> VelocityJudgment:
    return VelocityJudgment(trend="unknown",
                            rationale="Velocity could not be judged confidently.",
                            confident=False)


def fallback_blocker_scan() -> BlockerScan:
    return BlockerScan(confident=False)


def fallback_impact_scope() -> ImpactScope:
    return ImpactScope(confident=False)


def fallback_update_spec(entity_kind: str, entity_ref: str) -> UpdateSpec:
    return UpdateSpec(
        entity_kind=entity_kind,  # type: ignore[arg-type]
        entity_ref=entity_ref,
        field_changes=[],
        rationale="Auto-delta was not confident — refer to human.",
        confident=False,
    )


def fallback_conflict_check() -> ConflictCheck:
    return ConflictCheck(rationale="Conflict check was not confident.", confident=False)


def fallback_canonical_topic() -> CanonicalTopic:
    return CanonicalTopic(topic="general", rationale="Topic could not be inferred confidently.", confident=False)


def fallback_canonical_note(topic: str) -> CanonicalNote:
    return CanonicalNote(topic=topic, body="[NEEDS_HUMAN_REVIEW] Canonical body could not be drafted confidently.",
                         references=[], confident=False)


def fallback_stakeholder_map() -> StakeholderMap:
    return StakeholderMap(confident=False)


def fallback_human_response(intent: str, reason: str) -> HumanResponse:
    return HumanResponse(
        headline=f"NEEDS_HUMAN_REVIEW: {intent} request could not be processed confidently",
        summary=reason,
        actions_taken=[],
        proposed_next_steps=["Review the captured context and reissue the directive with more specifics."],
        citations=[],
        confident=False,
    )


# ---------------- Misc utilities ----------------------------------------------

def compute_completion_percent(completed: int, total: int) -> int:
    if total <= 0:
        return 0
    return max(0, min(100, int(round(100 * completed / total))))


def safe_first(*candidates: str | None) -> str:
    for c in candidates:
        if c:
            return c
    return ""
