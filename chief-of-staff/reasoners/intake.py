"""Intake: intent classification, entity extraction, and context assembly.

The "front door" of the system. Every directive flows through here. Context
assembly fans out three calls in parallel (knowledge / Linear / topology) so
the deep planning layers receive a tight, citation-keyed brief.
"""
from __future__ import annotations

import asyncio
import os

from agentfield import AgentRouter

from . import helpers as H
from .models import (
    EntityExtraction, IntentClassification, KnowledgeHit, KnowledgeRetrieval,
    TeamOwnership, TeamTopology,
)

NODE_ID = os.getenv("AGENT_NODE_ID", "chief-of-staff")
router = AgentRouter(prefix="", tags=["intake"])


# ----- Atomic classifiers / extractors ----------------------------------------

@router.reasoner()
async def classify_intent(directive: str, model: str | None = None) -> IntentClassification:
    result = await router.ai(
        system=(
            "You are the routing layer of a chief-of-staff agent that coordinates "
            "engineering work in Linear. Classify the human's directive into exactly "
            "ONE intent. Be conservative — if the directive could be interpreted "
            "multiple ways, prefer the broader 'strategic' bucket and set confident=false."
            "\n\nIntents:"
            "\n- new_idea: the human is proposing new work that needs to be scoped, "
            "decomposed into projects/issues, and possibly created."
            "\n- status_check: the human is asking for a status, progress, or health "
            "report on existing initiatives/projects/issues."
            "\n- modify: the human wants to change something that already exists — "
            "rescope, reassign, deprioritize, accelerate, split, merge."
            "\n- knowledge_update: the human is sharing a fact, decision, or learning "
            "that should be captured into the centralized knowledge context."
            "\n- strategic: the human is asking a cross-cutting question that needs "
            "stakeholder mapping, alignment checks, and communication drafting."
        ),
        user=f"Directive: {directive}",
        schema=IntentClassification,
        model=model,
    )
    if not result.confident:
        return result  # downstream uses confident flag to gate fallbacks
    return result


@router.reasoner()
async def extract_entities(directive: str, model: str | None = None) -> EntityExtraction:
    result = await router.ai(
        system=(
            "Extract any references to Linear entities or people mentioned by name "
            "or identifier in the directive. Return empty lists if none are mentioned. "
            "Do NOT invent IDs."
        ),
        user=f"Directive: {directive}",
        schema=EntityExtraction,
        model=model,
    )
    return result


# ----- Knowledge retrieval (semantic-ish; key-listing with relevance filter) --

@router.reasoner()
async def retrieve_knowledge(directive: str, intent: str, model: str | None = None) -> KnowledgeRetrieval:
    """List stored knowledge keys (scope=agent) and let an .ai() filter the relevant ones."""
    try:
        keys = await router.memory.list_keys(scope="agent")
    except Exception:
        keys = []
    if not keys:
        return KnowledgeRetrieval(hits=[], confident=True)

    candidates: list[dict] = []
    for k in keys[:50]:
        try:
            val = await router.memory.get(k, default=None, scope="agent")
        except Exception:
            val = None
        if val is None:
            continue
        topic = ""
        body = ""
        if isinstance(val, dict):
            topic = str(val.get("topic", ""))
            body = str(val.get("body", ""))
        else:
            topic = str(k)
            body = str(val)
        candidates.append({"ref_id": str(k), "topic": topic, "excerpt": body[:240]})

    if not candidates:
        return KnowledgeRetrieval(hits=[], confident=True)

    catalog = "\n".join(
        f"- ref_id={c['ref_id']} topic={c['topic']!r} excerpt={c['excerpt']!r}"
        for c in candidates
    )

    result = await router.ai(
        system=(
            "You are a knowledge-relevance filter. Given the human's directive and a "
            "catalog of stored knowledge notes, return ONLY the notes that are clearly "
            "relevant to the directive. Preserve their ref_id, topic, and excerpt fields. "
            "If nothing is relevant, return an empty list."
        ),
        user=(
            f"Intent: {intent}\nDirective: {directive}\n\nCatalog:\n{catalog}"
        ),
        schema=KnowledgeRetrieval,
        model=model,
    )
    return result


# ----- Linear state fetchers ---------------------------------------------------

@router.reasoner()
async def list_initiatives_skill() -> dict:
    return {"initiatives": await H.linear_list_initiatives()}


@router.reasoner()
async def list_projects_skill() -> dict:
    return {"projects": await H.linear_list_projects()}


@router.reasoner()
async def list_issues_skill() -> dict:
    return {"issues": await H.linear_list_issues()}


@router.reasoner()
async def list_teams_skill() -> dict:
    return {"teams": await H.linear_list_teams()}


@router.reasoner()
async def fetch_linear_state() -> dict:
    """Fan-out the four Linear list calls in parallel."""
    inits, projs, issues, teams = await asyncio.gather(
        router.call(f"{NODE_ID}.list_initiatives_skill"),
        router.call(f"{NODE_ID}.list_projects_skill"),
        router.call(f"{NODE_ID}.list_issues_skill"),
        router.call(f"{NODE_ID}.list_teams_skill"),
    )
    return {
        "initiatives": inits.get("initiatives", []),
        "projects": projs.get("projects", []),
        "issues": issues.get("issues", []),
        "teams": teams.get("teams", []),
    }


# ----- Team topology mapper ----------------------------------------------------

@router.reasoner()
async def map_team_topology(linear_state_prose: str, model: str | None = None) -> TeamTopology:
    """From the Linear state prose, derive who owns what."""
    if not linear_state_prose or "(no Linear state available)" in linear_state_prose:
        return TeamTopology(ownerships=[], confident=True)
    result = await router.ai(
        system=(
            "You map team-and-person ownership from Linear state. For each project "
            "or initiative you can see, name the team or person who appears to own it "
            "and a 1-line rationale citing the project/initiative ID. Return up to 8 "
            "ownerships — prefer high-confidence ones. Be conservative; if you cannot "
            "tell, leave ownerships empty and set confident=false."
        ),
        user=f"Linear state:\n{linear_state_prose}",
        schema=TeamTopology,
        model=model,
    )
    return result


# ----- The intake orchestrator (single entry point for all subgraphs) ---------

@router.reasoner()
async def assemble_context(directive: str, intent: str, model: str | None = None) -> dict:
    """Parallel fan-out: knowledge + Linear state + team topology.

    Returns a dict with `knowledge`, `linear_state`, `linear_state_prose`,
    `team_topology`, and a flat `citations` list of every entity ID referenced.
    """
    knowledge_task = router.call(
        f"{NODE_ID}.retrieve_knowledge",
        directive=directive,
        intent=intent,
        model=model,
    )
    linear_task = router.call(f"{NODE_ID}.fetch_linear_state")

    knowledge_dict, linear_state = await asyncio.gather(knowledge_task, linear_task)

    linear_state_prose = H.render_linear_state(linear_state)
    topology_dict = await router.call(
        f"{NODE_ID}.map_team_topology",
        linear_state_prose=linear_state_prose,
        model=model,
    )

    citations: list[str] = []
    for k in ("initiatives", "projects", "issues"):
        for entity in linear_state.get(k, []) or []:
            ref = entity.get("identifier") or entity.get("id")
            if ref and ref != "ERR":
                citations.append(str(ref))
    for h in knowledge_dict.get("hits", []) or []:
        ref = h.get("ref_id")
        if ref:
            citations.append(f"KB:{ref}")

    return {
        "knowledge": knowledge_dict,
        "linear_state": linear_state,
        "linear_state_prose": linear_state_prose,
        "team_topology": topology_dict,
        "citations": citations,
    }
