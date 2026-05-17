"""Final human-facing response composer.

Wraps every subgraph output into a tight narrative aimed at the human who
issued the directive. Carries citations forward so every claim is traceable.
"""
from __future__ import annotations

import os

from agentfield import AgentRouter

from . import helpers as H
from .models import HumanResponse

NODE_ID = os.getenv("AGENT_NODE_ID", "chief-of-staff")
router = AgentRouter(prefix="", tags=["respond"])


@router.reasoner()
async def compose_human_response(
    directive: str,
    intent: str,
    subgraph_prose: str,
    persistence_prose: str,
    citations: list[str],
    model: str | None = None,
) -> HumanResponse:
    if not subgraph_prose.strip():
        return H.fallback_human_response(
            intent,
            "No usable output was produced for this intent.",
        )

    result = await router.ai(
        system=(
            "You are an engineering chief-of-staff responding to the human who issued "
            "the directive. Produce a tight response:\n"
            "- headline: one sentence stating the upshot (≤120 chars)\n"
            "- summary: 2-3 sentences expanding the headline, citing entity IDs in [brackets]\n"
            "- actions_taken: bullets of things this run already did (e.g., 'Captured "
            "  knowledge note kb:...', 'Drafted N issues across M projects')\n"
            "- proposed_next_steps: 2-4 bullets the human can act on next\n"
            "- citations: the list of entity IDs and knowledge ref_ids touched\n"
            "Be specific. Quote IDs verbatim. Do NOT hallucinate IDs."
        ),
        user=(
            f"DIRECTIVE: {directive}\n"
            f"INTENT: {intent}\n\n"
            f"SUBGRAPH OUTPUT:\n{subgraph_prose}\n\n"
            f"PERSISTENCE OUTCOME:\n{persistence_prose}\n\n"
            f"AVAILABLE CITATIONS: {', '.join(citations) if citations else '(none)'}"
        ),
        schema=HumanResponse,
        model=model,
    )
    if not result.citations and citations:
        result.citations = citations
    return result
