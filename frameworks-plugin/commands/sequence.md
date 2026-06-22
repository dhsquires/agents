---
name: sequence
description: Run a compounding multi-framework analysis on a complex problem — diagnose, decompose, pressure-test, then package.
argument-hint: "<describe the complex problem> [| sales | personal]"
allowed-tools: Read, Glob, Grep, Skill, Task
---

# Compounding framework sequence

The problem: **$ARGUMENTS**

Run the problem through a sequence of frameworks so each output feeds the next. Pick the track that fits; default to the general track. State which track you're using, then work each stage by invoking the matching Skill.

## General complex-problem track (default)
1. **rumelt-kernel** → diagnose the real problem (not symptoms).
2. **mece-issue-tree** → decompose the diagnosed problem into clean branches.
3. **second-order-thinking** → pressure-test the leading solution's downstream effects.
4. **inversion-thinking** → identify what would make the solution fail, and guard against it.
5. **scqa-pyramid** or **scr-framework** → structure the finding for communication.

## Sales / solutions-engineering track (if input mentions sales, deal, prospect, or ends with `| sales`)
1. **spin-selling** → design the discovery conversation.
2. **jobs-to-be-done** → understand the buyer's decision forces.
3. **ssi-executive-framing** → package the executive recommendation.
4. **trust-equation** → diagnose where the relationship is stuck.

## Personal-decision track (if input ends with `| personal`)
1. **first-principles** → strip inherited assumptions.
2. **second-order-thinking** → trace the consequences.
3. **inversion-thinking** → find the failure modes.
4. **give-and-take** → audit the relationships involved.

At each stage, carry forward the prior stage's output, make assumptions explicit, and note where you lack data. End with a one-paragraph synthesis and the single highest-leverage next action. For a heavy problem, consider delegating stages to the relevant orchestrator agents (strategy-advisor, decision-coach, exec-communicator).
