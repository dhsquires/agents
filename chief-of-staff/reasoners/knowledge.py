"""Knowledge curation subgraph (knowledge_update intent).

Receives a directive that contains a learning/decision/fact, checks for
conflicts with existing notes, picks a canonical topic, drafts a canonical
note. The actual write happens in persist.py.
"""
from __future__ import annotations

import os

from agentfield import AgentRouter

from . import helpers as H
from .models import (
    CanonicalNote, CanonicalTopic, ConflictCheck, KnowledgeUpdate,
)

NODE_ID = os.getenv("AGENT_NODE_ID", "chief-of-staff")
router = AgentRouter(prefix="", tags=["knowledge"])


@router.reasoner()
async def check_for_conflicts(
    directive: str,
    existing_notes_prose: str,
    model: str | None = None,
) -> ConflictCheck:
    if not existing_notes_prose or "(no relevant knowledge entries)" in existing_notes_prose:
        return ConflictCheck(conflicts_with_ref_ids=[], rationale="No prior notes to compare against.", confident=True)
    result = await router.ai(
        system=(
            "Check whether this new piece of knowledge contradicts or supersedes any "
            "existing canonical note. Return the ref_ids of every conflicting note "
            "(empty list if none). Provide a 1-sentence rationale. Do not flag a "
            "conflict just because two notes are on the same topic — only flag "
            "actual contradictions or supersession."
        ),
        user=f"NEW DIRECTIVE:\n{directive}\n\nEXISTING NOTES:\n{existing_notes_prose}",
        schema=ConflictCheck,
        model=model,
    )
    if not result.confident:
        return H.fallback_conflict_check()
    return result


@router.reasoner()
async def identify_canonical_topic(
    directive: str,
    model: str | None = None,
) -> CanonicalTopic:
    result = await router.ai(
        system=(
            "Pick a single canonical topic slug (lowercase, hyphens, ≤40 chars) that "
            "best categorizes this knowledge update. Prefer specific topics (e.g., "
            "'ci-cache-policy', 'authn-session-ttl') over generic ones (e.g., 'eng', "
            "'general'). Provide a 1-sentence rationale."
        ),
        user=f"DIRECTIVE:\n{directive}",
        schema=CanonicalTopic,
        model=model,
    )
    if not result.confident:
        return H.fallback_canonical_topic()
    return result


@router.reasoner()
async def compose_canonical_note(
    directive: str,
    topic: str,
    linear_state_prose: str,
    model: str | None = None,
) -> CanonicalNote:
    result = await router.ai(
        system=(
            "Compose a canonical knowledge note. The body should be: "
            "(a) one sentence stating the decision or fact in the present tense, "
            "(b) one paragraph of rationale, "
            "(c) a 'References' line listing any Linear entity IDs from the state "
            "that are tied to this decision (or 'none'). Keep under 200 words."
        ),
        user=(
            f"TOPIC: {topic}\n\nDIRECTIVE:\n{directive}\n\n"
            f"AVAILABLE LINEAR STATE (for reference):\n{linear_state_prose}"
        ),
        schema=CanonicalNote,
        model=model,
    )
    if not result.confident:
        return H.fallback_canonical_note(topic)
    return result


@router.reasoner()
async def curate_knowledge(
    directive: str,
    context_payload: dict,
    model: str | None = None,
) -> KnowledgeUpdate:
    knowledge = context_payload.get("knowledge", {}) or {}
    existing_prose = H.render_knowledge(knowledge.get("hits") or [])
    linear_state_prose = context_payload.get("linear_state_prose", "")

    conflict_dict = await router.call(
        f"{NODE_ID}.check_for_conflicts",
        directive=directive,
        existing_notes_prose=existing_prose,
        model=model,
    )
    conflicts = ConflictCheck(**conflict_dict)

    topic_dict = await router.call(
        f"{NODE_ID}.identify_canonical_topic",
        directive=directive,
        model=model,
    )
    topic = CanonicalTopic(**topic_dict)

    note_dict = await router.call(
        f"{NODE_ID}.compose_canonical_note",
        directive=directive,
        topic=topic.topic,
        linear_state_prose=linear_state_prose,
        model=model,
    )
    note = CanonicalNote(**note_dict)

    return KnowledgeUpdate(
        note=note,
        conflicts=conflicts.conflicts_with_ref_ids,
        citations=context_payload.get("citations", []) or [],
    )
