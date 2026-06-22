---
name: north-star-metric
description: Use when choosing a single guiding metric for a product or company — "what's our north star metric," "what KPI should we track," "one metric that matters," "growth metric," driver trees, or avoiding vanity metrics. Applies Lenny Rachitsky's North Star Metric framework and its six archetypes to find the metric that captures customer value and predicts revenue.
---

# North Star Metric Framework

> One metric that captures the core value you deliver to customers and predicts long-term revenue.

**Author:** Lenny Rachitsky (ex-Airbnb), building on Sean Ellis and Amplitude
**Source:** Lenny's Newsletter: "Choosing Your North Star Metric" (2021); survey of 40+ top companies
**Field-tested:** Airbnb (nights booked), Slack (messages sent), Spotify (time spent listening).

## When to use this
- Choosing or pressure-testing a single guiding metric for a team or company
- Aligning a product org around one number
- Replacing a vanity metric with one tied to real value
- Building a driver tree of the inputs that move growth
- Picking the right metric for your business model and stage

## The framework
The NSM sits at the intersection of customer value and business results. Six archetypes:
1. **Revenue** — ARR, GMV (≈50% of companies)
2. **Customer Growth** — paid users, market share
3. **Consumption Growth** — messages sent, nights booked, files created
4. **Engagement Growth** — DAU/MAU, active users
5. **Growth Efficiency** — LTV/CAC, margin
6. **User Experience** — NPS, CSAT

## How to run it (step by step)
1. Ask: "Which metric, if it increased today, would most accelerate our business flywheel?"
2. Test for: customer-value alignment, leading (not lagging) indicator, team's ability to move it, plain-language expressibility.
3. Build a driver tree: what inputs drive the NSM?
4. Watch for vanity metrics and Goodhart's law (gaming the metric).

## Facilitating with the user
When this skill activates, you (Claude) should:
1. Restate or gather the user's context (company/product, business model, stage)
2. Walk through the six archetypes and the four tests, applied to their situation
3. Make any filled-in gaps explicit and labeled as assumptions
4. Flag where you lack data on whether the metric truly predicts revenue
5. Suggest 1-2 complementary frameworks for a second pass (e.g., LNO, JTBD)

## Output template
- **Company / product / stage:** ...
- **Recommended NSM (and archetype):** ...
- **Why it reflects customer value AND predicts business results:** ...
- **2-level driver tree:** NSM → key inputs → sub-inputs
- **Gaming / vanity risks to watch:** ...

## Watch out for
- Vanity metrics that look impressive but don't track value
- Goodhart's law: once a metric is a target, people game it
- Picking a lagging metric the team can't actually influence
- Choosing a metric that grows while customer value erodes

## Resources
- Lenny's Newsletter: "Choosing Your North Star Metric" (free)
- lennyrachitsky.wiki — podcast wiki synthesizing 300+ episodes
