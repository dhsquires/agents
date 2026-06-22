---
name: pr-faq-working-backwards
description: Use when planning a new product, feature, or initiative and you want to validate it before building — triggers include "working backwards", "PR/FAQ", "press release", "should we build this", "product launch", "validate an idea", or pitching to leadership. Applies Amazon's PR/FAQ Working Backwards method (Jeff Bezos / Bryar & Carr), which writes the launch press release and customer + internal FAQs first to test whether the product is understood well enough to build.
---

# PR/FAQ Working Backwards

> Write the press release announcing the finished product first; if you can't, you don't understand it well enough to build it.

**Author:** Jeff Bezos / Amazon (early 2000s); documented by Colin Bryar and Bill Carr
**Source:** *Working Backwards* (St. Martin's Press, 2021); *The PRFAQ Framework* by Marcelo Calbucci
**Field-tested:** Every major Amazon launch (AWS, Kindle, Alexa, Prime Video); exported to Google, Microsoft, and countless startups

## When to use this
- Deciding whether to build a new product or feature
- Pitching an initiative to leadership or investors
- Aligning a team on what "done and successful" actually looks like
- Pressure-testing a vague idea before committing resources
- Choosing between competing product bets

## The framework
- **Press Release** — Written from the customer's perspective: headline, customer problem, your solution, customer quote, how to get started
- **Customer FAQ** — The 5–7 hardest questions a skeptical customer would ask
- **Internal FAQ** — The 5–7 hardest questions leadership/investors would ask (cost, timeline, risks, dependencies)

**Rule:** If you can't write a compelling press release, you don't understand the product well enough to build it.

## How to run it (step by step)
1. Write the press release in plain English — no jargon, no technical specs
2. Force yourself to write the customer quote: what would a real customer say they can now do?
3. Generate the Customer FAQ by asking what the most skeptical customer would ask
4. Generate the Internal FAQ by asking what a board member focused on risk would ask
5. Use the document as the decision filter: if you can't answer the FAQs clearly, don't proceed

## Facilitating with the user
When this skill activates, you (Claude) should:
1. Restate or gather the user's context (the product/initiative, target customer, the problem it solves)
2. Walk through each step of the framework sequentially, applied to their situation
3. Make any filled-in gaps explicit and labeled as assumptions
4. Flag the step where the analysis is weakest or you lack data
5. Suggest 1-2 complementary frameworks for a second pass (e.g., OKRs to set targets, Schlep Blindness to test defensibility)

## Output template
- **Headline:** <one line, customer-facing>
- **Press Release:** 4 paragraphs from the customer's perspective, as if already launched
- **Customer Quote:** <what a real customer says they can now do>
- **Customer FAQ:** 5 hardest questions from skeptical customers + answers
- **Internal FAQ:** 5 hardest questions from executives (risk, cost, feasibility, dependencies) + answers
- **Go / No-Go:** which FAQs you cannot answer clearly yet

## Watch out for
- Jargon and technical specs creeping into the press release — keep it plain English
- Softball FAQs; the value is in the *hardest* questions, not the easy ones
- Treating it as a marketing exercise rather than a decision filter
- Skipping the Internal FAQ — that's where cost, timeline, and risk get exposed

## Resources
- 📚 *Working Backwards* — Colin Bryar and Bill Carr (St. Martin's, 2021)
- 📚 *The PRFAQ Framework* — Marcelo Calbucci (theprfaq.com)
- 🎙️ TechLead Journal Ep. 218: "The PRFAQ Framework"
- 🎙️ YouTube: "Innovation and Transformation — Working Backwards" (AWS)
