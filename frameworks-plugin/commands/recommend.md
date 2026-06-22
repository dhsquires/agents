---
name: recommend
description: Describe a situation and get the best-fit framework(s) recommended, with a short rationale and an offer to run them.
argument-hint: "<describe your situation or problem>"
allowed-tools: Read, Glob, Grep, Skill, Task
---

# Recommend a framework

The user's situation: **$ARGUMENTS**

Recommend the most relevant framework(s) from the Master Framework Compendium for this situation.

1. Briefly classify the problem (strategy, communication, decision, org/people, product, or productivity — it may span more than one).
2. Recommend 1-3 frameworks, best fit first. For each: framework name, author, the matching `frameworks-plugin:<skill>`, and one sentence on why it fits *this* situation.
3. If the problem is complex, suggest a short sequence (e.g. diagnose → decompose → pressure-test → communicate) and name the frameworks for each stage.
4. Offer to run the top recommendation now. If the intent is clear, go ahead and invoke the relevant Skill (or delegate to the `framework-selector` agent for a guided session) and facilitate.

If `$ARGUMENTS` is empty, ask the user for a one-paragraph description of their situation first.
