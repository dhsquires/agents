---
name: scqa-pyramid
description: Use when a user needs to structure a memo, pitch, email, or report that leads with the answer — keywords like SCQA, pyramid principle, situation complication question answer, Minto, executive memo, lead with the conclusion, structured writing. Applies Barbara Minto's SCQA / Pyramid Principle, setting up Situation, Complication, Question, and an answer-first conclusion supported by MECE arguments.
---

# SCQA / Pyramid Principle

> Set the scene, name what changed, surface the question it raises, then lead with the answer — supported by MECE arguments.

**Author:** Barbara Minto, McKinsey & Company (1960s)
**Source:** *The Pyramid Principle* (1987); McKinsey's internal communication standard for 50+ years
**Field-tested:** Every McKinsey deck, BCG strategy paper, and Goldman Sachs memo uses this structure

## When to use this
- Writing a memo, email, or report that must be persuasive
- You bury the conclusion and readers lose the thread
- Pitching an idea that needs a clear logical spine
- Structuring a document for busy, senior readers
- Turning a tangle of points into an answer-first narrative

## The framework
- **Situation** — The background your audience already accepts as true.
- **Complication** — What has changed or gone wrong; why action is needed *now*.
- **Question** — The key issue this raises (often implicit).
- **Answer** — Your main recommendation, stated upfront.

The Pyramid then provides supporting arguments beneath the Answer in a MECE structure.

## How to run it (step by step)
1. Write S: what is stable and accepted? (1–2 sentences)
2. Write C: what has disrupted or complicated that stability? (1–2 sentences)
3. Write Q: what does the audience implicitly want to ask? (1 sentence)
4. Write A: your answer to Q, stated as a conclusion, not a process.

## Facilitating with the user
When this skill activates, you (Claude) should:
1. Restate or gather the user's context (topic, audience, the recommendation, key facts)
2. Walk through Situation → Complication → Question → Answer sequentially
3. Make any filled-in gaps explicit and labeled as assumptions
4. Flag the step where the analysis is weakest or you lack data
5. Suggest 1-2 complementary frameworks for a second pass (MECE Issue Tree, SCR)

## Output template
**Situation:** <1-2 sentences of accepted background>
**Complication:** <1-2 sentences on what changed / why now>
**Question:** <1 sentence — the implicit question>
**Answer:** <conclusion-first recommendation, 1 paragraph>
**Supporting pyramid (MECE):**
1. <argument>
2. <argument>
3. <argument>

## Watch out for
- Stating the answer as a process instead of a conclusion
- A Situation that is actually the Complication (no real tension yet)
- Supporting points that overlap or leave gaps (not MECE)
- Skipping the Question, leaving the Answer floating

## Resources
- *The Pyramid Principle* — Barbara Minto (Minto Books, 1987)
- GitHub: life-itself/issuetrees — open-source SCQA + issue tree tools
- YouTube: "The SCQA Formula to Turn Any Idea into a Winning Pitch"
