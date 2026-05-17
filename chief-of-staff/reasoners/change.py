"""Change-planning subgraph (modify intent).

Identifies which Linear entities are impacted, computes a delta per entity in
parallel, and synthesizes a change plan. The actuator (persist.py) decides
whether the deltas get written or just previewed.
"""
from __future__ import annotations

import asyncio
import os

from agentfield import AgentRouter

from . import helpers as H
from .models import (
    ChangePlan, FieldChange, ImpactedEntity, ImpactScope, UpdateSpec,
)

NODE_ID = os.getenv("AGENT_NODE_ID", "chief-of-staff")
router = AgentRouter(prefix="", tags=["change"])


@router.reasoner()
async def identify_impact_scope(
    directive: str,
    linear_state_prose: str,
    entity_refs_csv: str,
    model: str | None = None,
) -> ImpactScope:
    result = await router.ai(
        system=(
            "Identify which Linear entities (initiative / project / issue) are "
            "directly impacted by the requested change. Only include entities you "
            "can find in the provided Linear state — do NOT invent IDs. Use the "
            "exact entity IDs as they appear. Provide a 1-sentence rationale per "
            "entity. If nothing in the state matches, return an empty list and set "
            "confident=false."
        ),
        user=(
            f"DIRECTIVE:\n{directive}\n\n"
            f"MENTIONED REFS: {entity_refs_csv or '(none)'}\n\n"
            f"LINEAR STATE:\n{linear_state_prose}"
        ),
        schema=ImpactScope,
        model=model,
    )
    if not result.confident:
        return H.fallback_impact_scope()
    return result


@router.reasoner()
async def draft_update_spec(
    directive: str,
    entity_kind: str,
    entity_ref: str,
    entity_prose: str,
    model: str | None = None,
) -> UpdateSpec:
    result = await router.ai(
        system=(
            "Draft the concrete field-by-field update for this Linear entity that "
            "would implement the requested change. For each field changed, provide "
            "from_value (current) and to_value (proposed). Use field names a human "
            "would understand (state, priority, assignee, title, description, "
            "labels, due_date). Provide a 1-sentence rationale. Be conservative — "
            "only propose changes you can justify from the directive."
        ),
        user=(
            f"DIRECTIVE:\n{directive}\n\n"
            f"ENTITY ({entity_kind}, {entity_ref}):\n{entity_prose}"
        ),
        schema=UpdateSpec,
        model=model,
    )
    if not result.confident:
        return H.fallback_update_spec(entity_kind, entity_ref)
    return result


@router.reasoner()
async def compute_delta_for_entity(
    directive: str,
    impacted: dict,
    linear_state: dict,
    model: str | None = None,
) -> UpdateSpec:
    """Find the entity in the Linear state and call draft_update_spec on it."""
    kind = impacted.get("entity_kind", "issue")
    ref = impacted.get("entity_ref", "UNKNOWN")
    bucket = {
        "initiative": linear_state.get("initiatives", []),
        "project": linear_state.get("projects", []),
        "issue": linear_state.get("issues", []),
    }.get(kind, [])

    entity = next(
        (e for e in bucket
         if (e.get("id") == ref or e.get("identifier") == ref or e.get("name") == ref)),
        None,
    )
    if not entity:
        return H.fallback_update_spec(kind, ref)

    entity_prose = "\n".join(f"  {k}: {v}" for k, v in entity.items())
    spec_dict = await router.call(
        f"{NODE_ID}.draft_update_spec",
        directive=directive,
        entity_kind=kind,
        entity_ref=ref,
        entity_prose=entity_prose,
        model=model,
    )
    return UpdateSpec(**spec_dict)


@router.reasoner()
async def plan_change(
    directive: str,
    context_payload: dict,
    entity_extraction: dict,
    model: str | None = None,
) -> ChangePlan:
    linear_state = context_payload.get("linear_state", {}) or {}
    linear_state_prose = context_payload.get("linear_state_prose", "")
    citations = context_payload.get("citations", []) or []

    refs_csv = ", ".join(
        (entity_extraction.get("initiative_refs") or [])
        + (entity_extraction.get("project_refs") or [])
        + (entity_extraction.get("issue_refs") or [])
    )

    impact_dict = await router.call(
        f"{NODE_ID}.identify_impact_scope",
        directive=directive,
        linear_state_prose=linear_state_prose,
        entity_refs_csv=refs_csv,
        model=model,
    )
    impact = ImpactScope(**impact_dict)

    if not impact.impacted_entities:
        return ChangePlan(
            updates=[],
            summary="No impacted Linear entities could be identified — refer to human.",
            citations=citations,
        )

    update_dicts = await asyncio.gather(*[
        router.call(
            f"{NODE_ID}.compute_delta_for_entity",
            directive=directive,
            impacted=imp.model_dump() if hasattr(imp, "model_dump") else imp,
            linear_state=linear_state,
            model=model,
        )
        for imp in [ImpactedEntity(**e) if isinstance(e, dict) else e
                    for e in impact.impacted_entities]
    ])
    updates = [UpdateSpec(**d) for d in update_dicts]

    summary_lines = []
    for u in updates:
        changes_csv = "; ".join(
            f"{fc.field}: {fc.from_value!r} → {fc.to_value!r}" for fc in u.field_changes
        ) or "no concrete changes"
        summary_lines.append(f"- [{u.entity_kind} {u.entity_ref}] {changes_csv} ({u.rationale})")

    return ChangePlan(
        updates=updates,
        summary="\n".join(summary_lines) or "No updates planned.",
        citations=citations,
    )
