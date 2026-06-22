---
name: first-principles
description: Use when a user wants to challenge assumptions, rethink a problem from scratch, escape "this is how it's always done", cut costs radically, or innovate — keywords like first principles, fundamental truths, deconstruct, reason from scratch, question assumptions, why is this true. Applies Elon Musk's First Principles Thinking, deconstructing to ground truths and reconstructing fresh solutions.
---

# First Principles Thinking

> Strip a problem down to what is irreducibly true, then rebuild a solution from those truths alone.

**Author:** Formalized by Elon Musk; originates from Aristotelian philosophy and the physics method
**Source:** Musk's 2013 TED Talk; *The Book of Elon Musk*; SpaceX battery cost example
**Field-tested:** SpaceX rocket cost reduction (~10x lower cost per kg to orbit), Tesla battery pack pricing, Musk's rejection of conventional cost assumptions

## When to use this
- A cost or constraint is "accepted" but never verified
- You're told something is impossible or fixed by convention
- You want genuinely novel solutions, not incremental tweaks
- The problem is well-defined and technical (physics, math, hard limits)
- Inherited industry practice may be the real bottleneck

## The framework
- **Deconstruct** — Identify and list every assumption you're making about the problem.
- **Break to fundamental truths** — Keep asking "Why is this true?" until you reach facts that cannot be reduced further.
- **Reconstruct** — Build a new solution from those ground truths only, ignoring inherited conventions.
- **Test & Iterate** — Experiment, refine the first principles if wrong, try again.

## How to run it (step by step)
1. State the problem as you currently understand it.
2. List every assumption embedded in that framing.
3. Challenge each assumption: "Is this actually true, or just tradition?"
4. Identify what is irreducibly true (physics, math, hard constraints).
5. Build the solution fresh from those truths.

## Facilitating with the user
When this skill activates, you (Claude) should:
1. Restate or gather the user's context (the problem and its current framing/assumptions)
2. Walk through Deconstruct → Ground Truth → Reconstruct → Test sequentially
3. Make any filled-in gaps explicit and labeled as assumptions
4. Flag the step where the analysis is weakest or you lack data
5. Suggest 1-2 complementary frameworks for a second pass (Inversion, Rumelt Kernel)

## Output template
**Problem:** <current framing>
**Assumptions detected:**
- <assumption — true or tradition?>
**Irreducible truths:** <facts that cannot be disputed>
**Reconstructed solutions (2-3):**
- <solution built only from the truths>
**Test plan:** <how to validate / iterate>

## Watch out for
- Most powerful in well-defined technical domains
- In complex social/organizational settings it can miss tacit expert knowledge (Cedric Chin's critique)
- Mistaking a strong opinion for a fundamental truth
- Skipping the test/iterate loop

## Resources
- Elon Musk TED Talk 2013: "The Mind Behind Tesla, SpaceX, SolarCity"
- *The Book of Elon Musk* — Steve Jurvetson (foreword)
- CNBC: "Why Elon Musk Wants His Employees to Use First Principles"
