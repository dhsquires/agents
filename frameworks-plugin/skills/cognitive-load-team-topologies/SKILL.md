---
name: cognitive-load-team-topologies
description: Use when a team (or you personally) is overloaded, context-switching, or struggling to ship — triggers include "cognitive load", "Team Topologies", "team is overwhelmed", "too many responsibilities", "platform vs stream team", "org design", or "what should I stop doing". Applies Skelton & Pais's Team Topologies framework, classifying load as intrinsic, extraneous, or germane and structuring teams (stream-aligned, platform, enabling, complicated-subsystem) to maximize the work that matters.
---

# Cognitive Load Optimization (Team Topologies)

> Every team has a finite cognitive load budget; good design eliminates extraneous load to maximize the creative work the team is there to do.

**Author:** Matthew Skelton and Manuel Pais
**Source:** *Team Topologies: Organizing Business and Technology Teams for Fast Flow* (IT Revolution Press, 2019)
**Field-tested:** Adopted by major technology organizations globally; applied at companies running complex platform engineering

## When to use this
- A team is overwhelmed, slow, or constantly context-switching
- Designing or restructuring team responsibilities
- Deciding whether to stand up a platform or enabling team
- Auditing your own personal workload and mental budget
- Diagnosing why "everything is hard" on a team

## The framework
Three types of cognitive load:
- **Intrinsic** — inherent complexity of the domain (can't be eliminated)
- **Extraneous** — complexity from bad tooling, process, org design (should be eliminated)
- **Germane** — the creative work the team is actually there to do (should be maximized)

Four team types:
1. **Stream-aligned team** — owns a product/service end-to-end
2. **Platform team** — reduces cognitive load on stream-aligned teams
3. **Enabling team** — fills temporary skill gaps (like a consulting team)
4. **Complicated-subsystem team** — owns a technically complex component

**Personal application:** What is your extraneous load? Which tools, meetings, and responsibilities drain budget you should aim at high-leverage work?

## How to run it (step by step)
1. Inventory the responsibilities, tooling, and structure in scope
2. Classify each load source as Intrinsic, Extraneous, or Germane
3. Identify the top 3 sources of Extraneous load to eliminate
4. Restructure responsibilities to protect Germane capacity
5. Map work onto the four team types where relevant (or your own roles)

## Facilitating with the user
When this skill activates, you (Claude) should:
1. Restate or gather the user's context (responsibilities, team structure, tooling, current challenges)
2. Walk through each step of the framework sequentially, applied to their situation
3. Make any filled-in gaps explicit and labeled as assumptions
4. Flag the step where the analysis is weakest or you lack data
5. Suggest 1-2 complementary frameworks for a second pass (e.g., OKRs to refocus Germane work, PARA to cut tool sprawl)

## Output template
- **Load inventory (classified):**
  - Intrinsic: <unavoidable domain complexity>
  - Extraneous: <load to eliminate>
  - Germane: <work to protect/maximize>
- **Top 3 extraneous loads to eliminate:** <with how>
- **Restructure recommendations:** <team-type mapping or role changes>

## Watch out for
- Treating intrinsic complexity as if it can be removed — it can't, only managed
- Adding a platform/enabling team without first cutting extraneous load
- Confusing "busy" (load) with "productive" (germane output)
- Spreading one team across too many domains, blowing its budget

## Resources
- 📚 *Team Topologies* — Matthew Skelton and Manuel Pais (IT Revolution Press, 2019)
- 📝 Martin Fowler's summary: martinfowler.com/bliki/TeamTopologies.html
- 🎙️ TechDebtBurndown Podcast: Matthew Skelton on cognitive load and tech debt
