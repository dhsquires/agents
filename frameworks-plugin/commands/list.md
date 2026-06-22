---
name: list
description: List every framework in the Master Framework Compendium, grouped by scenario, with its matching skill.
argument-hint: "[optional: scenario filter e.g. strategy|decisions|communication|product|org|productivity]"
allowed-tools: Read, Glob
---

# List the framework compendium

Show the user the frameworks available in this plugin, grouped by scenario. If the user passed a filter in `$ARGUMENTS`, show only the matching group(s); otherwise show all.

Present each framework as: **Framework name** (author) — one-line use case — `frameworks-plugin:<skill>`.

## Strategy & Problem Diagnosis
- **Rumelt Kernel** (Richard Rumelt) — diagnose good vs bad strategy — `frameworks-plugin:rumelt-kernel`
- **First Principles** (Elon Musk) — decompose to ground truths — `frameworks-plugin:first-principles`
- **Inversion** (Charlie Munger) — avoid failure by working backward — `frameworks-plugin:inversion-thinking`
- **MECE Issue Tree** (Barbara Minto) — structure a sprawling problem — `frameworks-plugin:mece-issue-tree`

## Communication & Executive Influence
- **SSI** — Situation/Solution/Impact exec framing — `frameworks-plugin:ssi-executive-framing`
- **SCQA / Pyramid** (Barbara Minto) — lead-with-the-answer memos — `frameworks-plugin:scqa-pyramid`
- **SCR** (McKinsey) — slide/deck storylines — `frameworks-plugin:scr-framework`
- **SPIN Selling** (Neil Rackham) — B2B discovery questions — `frameworks-plugin:spin-selling`

## Decision-Making
- **OODA Loop** (John Boyd) — fast competitive decisions — `frameworks-plugin:ooda-loop`
- **Recognition-Primed Decision** (Gary Klein) — expert calls under pressure — `frameworks-plugin:recognition-primed-decision`
- **Second-Order Thinking** (Ray Dalio) — trace downstream consequences — `frameworks-plugin:second-order-thinking`
- **Integrative Thinking** (Roger Martin) — resolve either/or dilemmas — `frameworks-plugin:integrative-thinking`

## Organizational & People
- **4P Audit** (Nils Vinje) — team health: People/Purpose/Process/Platform — `frameworks-plugin:four-p-team-audit`
- **Wartime/Peacetime CEO** (Ben Horowitz) — leadership mode — `frameworks-plugin:wartime-peacetime-ceo`
- **Trust Equation** (David Maister) — diagnose advisory trust — `frameworks-plugin:trust-equation`
- **Tactical Empathy** (Chris Voss) — negotiation — `frameworks-plugin:tactical-empathy`
- **Give and Take** (Adam Grant) — reciprocity & networks — `frameworks-plugin:give-and-take`

## Product & Prioritization
- **Jobs to Be Done** (Christensen/Moesta) — customer motivation — `frameworks-plugin:jobs-to-be-done`
- **LNO** (Shreyas Doshi) — task prioritization — `frameworks-plugin:lno-prioritization`
- **Kano Model** (Noriaki Kano) — feature prioritization — `frameworks-plugin:kano-model`
- **North Star Metric** (Lenny Rachitsky) — pick the metric that matters — `frameworks-plugin:north-star-metric`
- **PR/FAQ Working Backwards** (Amazon) — vet a new idea — `frameworks-plugin:pr-faq-working-backwards`
- **PLG / PLS** (Elena Verna) — go-to-market motion — `frameworks-plugin:plg-strategy`

## Personal Productivity & Knowledge
- **PARA Method** (Tiago Forte) — organize knowledge — `frameworks-plugin:para-method`
- **OKRs** (Andy Grove) — goal setting — `frameworks-plugin:okrs`
- **Tacit Knowledge / Commoncog** (Cedric Chin) — accelerate expertise — `frameworks-plugin:tacit-knowledge-commoncog`
- **Cognitive Load / Team Topologies** (Skelton & Pais) — team design & focus — `frameworks-plugin:cognitive-load-team-topologies`
- **Schlep Blindness** (Paul Graham) — find avoided high-value work — `frameworks-plugin:schlep-blindness`

After listing, invite the user to run `/frameworks-plugin:recommend <situation>` or `/frameworks-plugin:apply <framework> <context>`.
