---
name: kano-model
description: Use when prioritizing features or requirements by customer satisfaction — "which features to build," "roadmap prioritization," "must-have vs nice-to-have," "delighters," "are we overinvesting," or product survey design. Applies Noriaki Kano's Kano Model, classifying features as Must-Be, Performance, Delighter, Indifferent, or Reverse.
---

# Kano Model (Must-Be / Performance / Delighter)

> Features affect satisfaction differently — some merely prevent anger, some scale with quality, some delight.

**Author:** Professor Noriaki Kano, Tokyo University of Science (1984)
**Source:** "Attractive Quality and Must-Be Quality" (1984); *Journal of the Japanese Society for Quality Control*
**Field-tested:** Used by Toyota, P&G, and Motorola for roadmap prioritization; adopted in Agile/Scrum.

## When to use this
- Prioritizing a feature backlog or roadmap
- Deciding what's a baseline expectation vs. a differentiator vs. a delight
- Worried you're overinvesting in features customers don't care about
- Designing a customer survey to validate feature value
- Justifying cuts or investments to stakeholders

## The framework

| Category | Present | Absent |
|----------|---------|--------|
| **Must-Be (Basic)** | Expected (neutral) | Causes dissatisfaction |
| **Performance (One-Dimensional)** | Satisfies proportionally | Dissatisfies proportionally |
| **Delighter (Attractive)** | Causes delight | No dissatisfaction |
| **Indifferent** | No effect | No effect |
| **Reverse** | Causes dissatisfaction | Causes satisfaction |

**Survey method:** For each feature ask two questions — "How would you feel if this existed?" and "How would you feel if it didn't?" — then cross-reference to classify.

## How to run it (step by step)
1. List proposed features or requirements.
2. For each, ask the functional and dysfunctional questions to a sample of users.
3. Map responses to the five categories.
4. Prioritize: fix all Must-Be failures first; invest in Performance for differentiation; deploy Delighters selectively.

## Facilitating with the user
When this skill activates, you (Claude) should:
1. Restate or gather the user's context (the product and the candidate feature list)
2. Walk through classifying each feature with reasoning for their situation
3. Make any filled-in gaps explicit and labeled as assumptions
4. Flag that classifications are hypotheses until validated with the two-question survey
5. Suggest 1-2 complementary frameworks for a second pass (e.g., JTBD, North Star Metric)

## Output template
- **Product:** ...
- **Per-feature classification:** Must-Be / Performance / Delighter / Indifferent / Reverse (with reasoning)
- **Prioritization recommendation:** ...
- **Possible overinvestment:** ...

## Watch out for
- Treating a Must-Be as a differentiator (no one is delighted by basics that work)
- Categories drifting over time — today's Delighter becomes tomorrow's Must-Be
- Classifying from intuition instead of the two-question survey
- Chasing Delighters while a Must-Be is still broken

## Resources
- leanscape.io/kano-model-customer-needs/ — comprehensive guide
- Scrum.org: "Kano Model" resource
- sensefolks.com/blog/kano-model-feature-prioritization/ — practical guide
