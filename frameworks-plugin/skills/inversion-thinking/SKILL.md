---
name: inversion-thinking
description: Use when a user is stuck approaching a goal directly, wants to avoid failure, de-risk a plan, run a pre-mortem, or find what to NOT do — keywords like inversion, invert, avoid failure, what would go wrong, pre-mortem, worst case, Munger. Applies Charlie Munger's "Invert, Always Invert", listing failure causes and building a strategy that avoids each.
---

# Inversion Thinking

> Solve hard problems backward: figure out how to guarantee failure, then systematically avoid it.

**Author:** Charlie Munger, Vice Chairman of Berkshire Hathaway; adapted from mathematician Carl Jacobi
**Source:** Munger's speeches collected in *Poor Charlie's Almanack*; 25iq.com compendium
**Field-tested:** Berkshire Hathaway's investment discipline (focus on what destroys value, not what creates it), Munger's study of how great institutions fail

## When to use this
- Direct, forward planning has stalled
- You want to stress-test a plan before committing
- Avoiding catastrophe matters more than optimizing upside
- Running a pre-mortem on a project or decision
- You need a concrete list of risks to mitigate

## The framework
- **Step 1:** State the original goal (e.g., "How do I build a great sales team?")
- **Step 2:** Invert the question ("How would I guarantee the worst possible sales team?")
- **Step 3:** Generate a thorough list of causes for the inverted (failure) outcome.
- **Step 4:** Build a strategy that avoids all those causes.

> "Many hard problems are best solved when they are addressed backward."

## How to run it (step by step)
1. Write the positive goal.
2. Write the opposite goal (the worst possible outcome).
3. Brainstorm every action that would guarantee the worst outcome.
4. Treat that list as your constraint set — eliminate or mitigate each.

## Facilitating with the user
When this skill activates, you (Claude) should:
1. Restate or gather the user's context (the goal and current plan)
2. Walk through Goal → Inversion → Failure causes → Avoidance strategy sequentially
3. Make any filled-in gaps explicit and labeled as assumptions
4. Flag the step where the analysis is weakest or you lack data
5. Suggest 1-2 complementary frameworks for a second pass (First Principles, Rumelt Kernel)

## Output template
**Goal:** <positive goal>
**Inverted goal:** <the guaranteed-failure version>
**Failure causes (be exhaustive):**
- <cause>
**Avoidance strategy:**
- <how each cause is eliminated or mitigated>

## Watch out for
- Stopping the failure list too early — aim for comprehensiveness
- Listing vague risks instead of concrete, actionable causes
- Forgetting to convert each failure cause into a mitigation
- Using inversion as pessimism rather than as a constraint-finder

## Resources
- *Poor Charlie's Almanack* — Charlie Munger (Donning Company Publishers, 2005)
- 25iq.com: "A Dozen Things I've Learned from Charlie Munger About Inversion"
- YouTube: "Charlie Munger's Secret to Solving All Problems: Inversion Thinking"
