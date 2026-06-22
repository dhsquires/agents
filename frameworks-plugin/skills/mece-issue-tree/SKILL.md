---
name: mece-issue-tree
description: Use when a user needs to break a big ambiguous problem into structured parts, scope an analysis, build a hypothesis tree, or organize a diagnosis — keywords like MECE, issue tree, problem structuring, mutually exclusive collectively exhaustive, McKinsey, hypothesis tree, root cause breakdown. Applies Barbara Minto / McKinsey's MECE Issue Tree, decomposing a core question into non-overlapping, exhaustive branches.
---

# MECE Issue Tree

> Decompose a core question into mutually exclusive, collectively exhaustive branches so nothing overlaps and nothing is missed.

**Author:** Barbara Minto (McKinsey & Company, 1960s); extended as a consulting methodology by McKinsey
**Source:** *The Pyramid Principle: Logic in Writing and Thinking* (Minto Books International, 1987)
**Field-tested:** Used on every McKinsey engagement since the 1970s; standard at BCG, Bain, and all major consulting firms

## When to use this
- A problem feels too big or vague to attack directly
- You need to scope and divide analytical work
- Multiple causes or solutions must be considered without gaps
- You want to prioritize where to dig first
- Structuring a diagnosis, solution set, or hypothesis test

## The framework
- **MECE** (Mutually Exclusive, Collectively Exhaustive): categories don't overlap, and together cover all possibilities.
- **Issue Tree:** the trunk is the core question; each branch is a MECE sub-question; branches break into further sub-branches.
- **Types:** diagnostic trees (why is X happening?), solution trees (how do we solve X?), hypothesis trees (is hypothesis Y true?).

## How to run it (step by step)
1. Write the core question as a single sentence.
2. Break it into 3–5 MECE branches (no overlaps, no gaps).
3. For each branch, generate sub-branches recursively.
4. Assign work or hypotheses to each branch.
5. Prioritize branches most likely to contain the answer.

## Facilitating with the user
When this skill activates, you (Claude) should:
1. Restate or gather the user's context (the core question and known facts/data)
2. Walk through trunk → branches → sub-branches, checking MECE at each level
3. Make any filled-in gaps explicit and labeled as assumptions
4. Flag the step where the analysis is weakest or you lack data
5. Suggest 1-2 complementary frameworks for a second pass (SCQA Pyramid, First Principles)

## Output template
**Core question:** <single sentence>
**Branches (MECE):**
1. <branch> [diagnostic | hypothesis]
   - <sub-branch>
   - <sub-branch>
2. <branch> [diagnostic | hypothesis]
   - <sub-branch>
**Priority branches:** <where to dig first>
**Data gaps:** <branches needing data you lack>

## Watch out for
- Branches that overlap (not mutually exclusive) or leave gaps (not collectively exhaustive)
- Going too deep before checking each level is MECE
- Trees with no prioritization — wasting effort on low-yield branches
- Mislabeling diagnostic vs hypothesis branches

## Resources
- *The Pyramid Principle* — Barbara Minto (Minto Books, 1987)
- LinkedIn post by Glenn Leibowitz (ex-McKinsey): "When I joined McKinsey 28 years ago…" (SCQA + MECE)
- StrategyU.co: "Issue Trees — What Are They and How Do You Use Them?"
