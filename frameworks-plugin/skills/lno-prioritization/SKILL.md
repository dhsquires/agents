---
name: lno-prioritization
description: Use when prioritizing tasks or a weekly plan — "how do I prioritize," "too much on my plate," "what to focus on," "high-leverage work," time management, or audit my to-do list. Applies Shreyas Doshi's LNO Framework, classifying tasks as Leverage (10x+), Neutral (1x), or Overhead (<1x) and front-loading Leverage work at peak energy.
---

# LNO Framework (Leverage / Neutral / Overhead)

> Classify every task by its return on effort and spend your best energy on the work that compounds.

**Author:** Shreyas Doshi (ex-Stripe, Twitter, Google, Yahoo product leader)
**Source:** coda.io/@shreyas/lno-framework — publicly published by Doshi
**Field-tested:** Doshi's personal system at Stripe and Twitter; widely adopted in the PM community.

## When to use this
- Your to-do list is overwhelming and everything feels urgent
- Planning a week and deciding where to put your best hours
- You suspect you're polishing low-value work
- Auditing whether your time matches your impact
- Deciding what to eliminate or delegate

## The framework
- **L (Leverage) tasks** — 10x or 100x return; these compound. Do them at peak energy in a deep-focus environment.
- **N (Neutral) tasks** — 1:1 return. Necessary but not compounding.
- **O (Overhead) tasks** — Less return than effort required. Necessary but minimize and time-box.

Target distribution: ~40% L, ~35% N, ~20% O.

## How to run it (step by step)
1. List your tasks for the week.
2. Classify each as L, N, or O.
3. Audit: what percentage is L? Under 30% means you're in a trap.
4. Eliminate O tasks where possible; delegate the rest.
5. Schedule L tasks at your cognitive peak (morning for most people).

## Facilitating with the user
When this skill activates, you (Claude) should:
1. Restate or gather the user's context (the actual task list and their energy/peak hours)
2. Walk through classifying each task and computing the current L/N/O distribution
3. Make any filled-in gaps explicit and labeled as assumptions
4. Flag tasks where the classification is debatable (an L disguised as O, or vice versa)
5. Suggest 1-2 complementary frameworks for a second pass (e.g., North Star Metric, JTBD)

## Output template
- **Task list classified:** L / N / O per task
- **Current distribution:** L __% · N __% · O __%
- **Misclassified tasks:** ...
- **Eliminate / delegate:** ...
- **Restructured week (L front-loaded):** ...

## Watch out for
- Over-perfecting Overhead tasks that deserve a quick, time-boxed pass
- Labeling comfortable busywork as Leverage to justify it
- Scheduling Leverage work in low-energy slots
- Ignoring the distribution check — under 30% L is the core warning sign

## Resources
- coda.io/@shreyas/lno-framework (original, free)
- Podcast: "Ep. 118 — Shreyas Doshi — Making of a Great Leader"
- substack.com/p/influence-power-and-product-management
