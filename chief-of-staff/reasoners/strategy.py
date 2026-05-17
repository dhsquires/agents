"""Strategic-coordination subgraph (strategic intent).

Maps stakeholders, runs alignment checks per stakeholder in parallel, drafts
communications for each, and may chain back into the initiative planner when
the strategic directive needs concrete decomposition.
"""
from __future__ import annotations

import asyncio
import os

from agentfield import AgentRouter

from . import helpers as H
from .models import (
    AlignmentCheck, CommunicationDraft, CommunicationDrafts,
    InitiativePlan, Stakeholder, StakeholderMap, StrategicPlan,
)

NODE_ID = os.getenv("AGENT_NODE_ID", "chief-of-staff")
router = AgentRouter(prefix="", tags=["strategy"])


@router.reasoner()
async def map_stakeholders(
    directive: str,
    team_topology_prose: str,
    linear_state_prose: str,
    model: str | None = None,
) -> StakeholderMap:
    result = await router.ai(
        system=(
            "Identify the teams or individuals who have a stake in this strategic "
            "decision. For each, name them and write a 1-sentence interest "
            "statement (what they care about or what they will be asked to change). "
            "Use only stakeholders supported by the team topology and Linear state — "
            "do NOT invent people. Maximum 5 stakeholders."
        ),
        user=(
            f"DIRECTIVE:\n{directive}\n\n"
            f"TEAM TOPOLOGY:\n{team_topology_prose or '(none)'}\n\n"
            f"LINEAR STATE:\n{linear_state_prose}"
        ),
        schema=StakeholderMap,
        model=model,
    )
    if not result.confident:
        return H.fallback_stakeholder_map()
    return result


@router.reasoner()
async def check_alignment(
    directive: str,
    stakeholder: str,
    stakeholder_interest: str,
    linear_state_prose: str,
    model: str | None = None,
) -> AlignmentCheck:
    result = await router.ai(
        system=(
            "Judge whether this stakeholder is aligned with the proposed direction. "
            "Pick exactly one: aligned / partial / misaligned / unknown. Name the "
            "specific gap if not aligned (1 sentence). Use the Linear state to "
            "ground your judgment when relevant; if you cannot tell, use 'unknown' "
            "and set confident=true."
        ),
        user=(
            f"DIRECTIVE:\n{directive}\n\n"
            f"STAKEHOLDER: {stakeholder} — interest: {stakeholder_interest}\n\n"
            f"LINEAR STATE:\n{linear_state_prose}"
        ),
        schema=AlignmentCheck,
        model=model,
    )
    return result


@router.reasoner()
async def draft_communications(
    directive: str,
    stakeholders_prose: str,
    alignment_prose: str,
    model: str | None = None,
) -> CommunicationDrafts:
    if not stakeholders_prose.strip():
        return CommunicationDrafts(drafts=[], confident=True)
    result = await router.ai(
        system=(
            "For each stakeholder listed, draft a single short message (≤120 words) "
            "tailored to their interest and current alignment. Pick a sensible "
            "medium per audience (slack-channel / email / 1-1-message / "
            "all-hands-update). Avoid generic language — name what you want from "
            "them and what they get in return. Maximum 5 drafts."
        ),
        user=(
            f"DIRECTIVE:\n{directive}\n\n"
            f"STAKEHOLDERS:\n{stakeholders_prose}\n\n"
            f"ALIGNMENT:\n{alignment_prose}"
        ),
        schema=CommunicationDrafts,
        model=model,
    )
    return result


@router.reasoner()
async def coordinate_strategy(
    directive: str,
    context_payload: dict,
    model: str | None = None,
    plan_execution: bool = False,
) -> StrategicPlan:
    linear_state_prose = context_payload.get("linear_state_prose", "")
    topology = context_payload.get("team_topology", {}) or {}
    topology_prose = "\n".join(
        f"- {o.get('team')} owns {o.get('owns')}: {o.get('rationale')}"
        for o in topology.get("ownerships", []) or []
    ) or "(no topology mapped)"

    stakeholder_dict = await router.call(
        f"{NODE_ID}.map_stakeholders",
        directive=directive,
        team_topology_prose=topology_prose,
        linear_state_prose=linear_state_prose,
        model=model,
    )
    stakeholders = StakeholderMap(**stakeholder_dict).stakeholders

    if not stakeholders:
        return StrategicPlan(
            stakeholders=[],
            alignment_checks=[],
            communications=[],
            follow_on_initiative=None,
            citations=context_payload.get("citations", []) or [],
        )

    alignment_dicts = await asyncio.gather(*[
        router.call(
            f"{NODE_ID}.check_alignment",
            directive=directive,
            stakeholder=s.team_or_person,
            stakeholder_interest=s.interest,
            linear_state_prose=linear_state_prose,
            model=model,
        )
        for s in stakeholders
    ])
    alignment_checks = [AlignmentCheck(**d) for d in alignment_dicts]

    stakeholders_prose = "\n".join(
        f"- {s.team_or_person}: {s.interest}" for s in stakeholders
    )
    alignment_prose = "\n".join(
        f"- {a.stakeholder}: {a.alignment} — {a.gap}" for a in alignment_checks
    )
    comms_dict = await router.call(
        f"{NODE_ID}.draft_communications",
        directive=directive,
        stakeholders_prose=stakeholders_prose,
        alignment_prose=alignment_prose,
        model=model,
    )
    communications = CommunicationDrafts(**comms_dict).drafts

    follow_on: InitiativePlan | None = None
    if plan_execution:
        plan_dict = await router.call(
            f"{NODE_ID}.plan_initiative",
            directive=directive,
            context_payload=context_payload,
            model=model,
        )
        follow_on = InitiativePlan(**plan_dict)

    return StrategicPlan(
        stakeholders=stakeholders,
        alignment_checks=alignment_checks,
        communications=communications,
        follow_on_initiative=follow_on,
        citations=context_payload.get("citations", []) or [],
    )
