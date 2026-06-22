#!/usr/bin/env python3
"""UserPromptSubmit hook for the frameworks-plugin.

Reads the hook event JSON from stdin, scans the user's prompt for intent
signals, and — when there is a strong match — prints a short note to stdout
suggesting the most relevant framework skill(s) to apply. On UserPromptSubmit,
anything printed to stdout (with exit code 0) is added to the model's context
for that turn.

The hook is intentionally conservative: it only speaks up when a prompt clearly
maps to one or more frameworks, and it caps the number of suggestions so it
never floods the conversation.
"""

import json
import re
import sys

# (compiled keyword regex, skill name, one-line reason)
RULES = [
    (r"\b(strateg(y|ic)|guiding policy|root cause|good strategy|bad strategy)",
     "rumelt-kernel", "diagnose the real challenge before proposing actions"),
    (r"\b(first principles|from scratch|fundamental(s)?|why is this true|reinvent)",
     "first-principles", "strip the problem down to ground truths"),
    (r"\b(avoid failure|what could go wrong|worst case|pre-?mortem|de-?risk)",
     "inversion-thinking", "work backward from how this fails"),
    (r"\b(break down|structure the problem|decompose|issue tree|mece)",
     "mece-issue-tree", "decompose into mutually exclusive branches"),
    (r"\b(brief (the|an|my) exec|executive (summary|update)|exec conversation)",
     "ssi-executive-framing", "frame Situation -> Solution -> Impact"),
    (r"\b(pyramid principle|scqa|structure (the|this) (memo|doc|narrative)|lead with the answer)",
     "scqa-pyramid", "structure with Situation/Complication/Question/Answer"),
    (r"\b(slide|deck|presentation|storyline|board (deck|presentation))",
     "scr-framework", "build a Situation/Complication/Resolution storyline"),
    (r"\b(sales call|discovery (call|questions)|qualify (a|the) (deal|lead)|b2b sell)",
     "spin-selling", "run SPIN discovery questions"),
    (r"\b(react (fast|quickly)|competitor moved|fast-moving|tempo|out-maneuver)",
     "ooda-loop", "cycle Observe-Orient-Decide-Act faster than the rival"),
    (r"\b(time-?pressured decision|gut call|under pressure|first instinct)",
     "recognition-primed-decision", "pattern-match and simulate the first viable option"),
    (r"\b(and then what|downstream|knock-on|unintended consequence|ripple effect)",
     "second-order-thinking", "trace the second- and third-order consequences"),
    (r"\b(either/or|trade-?off|both options|can't decide between|tension between)",
     "integrative-thinking", "synthesize a third option superior to both"),
    (r"\b(team (audit|health)|right people|reorg|team structure|org design)",
     "four-p-team-audit", "score People / Purpose / Process / Platform"),
    (r"\b(wartime|peacetime|existential threat|crisis mode|turnaround)",
     "wartime-peacetime-ceo", "diagnose wartime vs peacetime and the right playbook"),
    (r"\b(build trust|trusted advisor|advisor relationship|why don't they trust)",
     "trust-equation", "score Credibility+Reliability+Intimacy over Self-orientation"),
    (r"\b(negotiat|counterpart|hostage|salary discussion|deal terms|push back)",
     "tactical-empathy", "prep labels, mirrors, and calibrated questions"),
    (r"\b(giver|taker|matcher|reciprocity|being taken advantage|networking)",
     "give-and-take", "audit giver/taker/matcher dynamics"),
    (r"\b(jobs to be done|jtbd|why (do|would) (customers|users) (buy|switch)|customer motivation)",
     "jobs-to-be-done", "map the four forces of progress"),
    (r"\b(prioriti|task list|what to work on|leverage|too much on my plate|backlog of tasks)",
     "lno-prioritization", "sort tasks into Leverage / Neutral / Overhead"),
    (r"\b(feature prioriti|kano|must-have|delighter|which features|roadmap priorit)",
     "kano-model", "classify features Must-Be / Performance / Delighter"),
    (r"\b(north star|key metric|which metric|nsm|metric that matters)",
     "north-star-metric", "pick the metric that captures value and predicts revenue"),
    (r"\b(pr/?faq|press release|working backwards|launch announcement|new product idea)",
     "pr-faq-working-backwards", "write the press release and FAQ first"),
    (r"\b(organize (my )?(notes|files|knowledge)|second brain|para|note-?taking system)",
     "para-method", "sort into Projects / Areas / Resources / Archives"),
    (r"\b(okr|objectives and key results|quarterly goals|goal setting)",
     "okrs", "draft Objectives with measurable Key Results"),
    (r"\b(tacit knowledge|learn from experts|accelerate expertise|apprentice|deliberate practice)",
     "tacit-knowledge-commoncog", "use cognitive task analysis to extract expertise"),
    (r"\b(cognitive load|too many responsibilities|context switching|team topolog|overloaded)",
     "cognitive-load-team-topologies", "separate intrinsic / extraneous / germane load"),
    (r"\b(boring idea|too much work|tedious|schlep|nobody wants to build|moat)",
     "schlep-blindness", "apply the Someone-Else test to find defensible work"),
    (r"\b(product-?led|plg|pls|self-?serve|go-to-market|gtm motion)",
     "plg-strategy", "assess the product-led growth / sales motion"),
]

MAX_SUGGESTIONS = 3


def main():
    raw = sys.stdin.read()
    try:
        event = json.loads(raw) if raw.strip() else {}
    except (ValueError, TypeError):
        event = {}

    prompt = (event.get("prompt") or "").lower()
    if not prompt:
        return 0

    seen = set()
    matches = []
    for pattern, skill, reason in RULES:
        if skill in seen:
            continue
        if re.search(pattern, prompt, flags=re.IGNORECASE):
            matches.append((skill, reason))
            seen.add(skill)
        if len(matches) >= MAX_SUGGESTIONS:
            break

    if not matches:
        return 0

    lines = [
        "[frameworks-plugin] This request maps to field-tested thinking framework(s). "
        "Consider invoking the matching Skill before answering:"
    ]
    for skill, reason in matches:
        lines.append(f"  - frameworks-plugin:{skill} — {reason}")
    lines.append(
        "Use the most relevant one if it fits; otherwise ignore this note. "
        "Run /frameworks-plugin:recommend for a fuller suggestion."
    )
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
