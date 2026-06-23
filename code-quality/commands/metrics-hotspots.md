---
description: Find behavioural hotspots — files that are both complex and frequently changed — plus change coupling and bus-factor risk from git history.
argument-hint: "[path] (default: whole repo)"
allowed-tools: Bash, Read
---

# Code hotspots

Surface the highest-leverage refactoring targets by overlaying git churn with
static complexity (the CodeScene/Tornhill "hotspot" model), and flag hidden
logical dependencies and knowledge-loss risks.

## What to do

1. Run the behavioural analysis:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/code-quality.py" hotspots \
       ${ARGUMENTS:-.} --format json
   ```

2. Interpret the three sections:
   - **hotspots** — `score = commits × complexity`. These are where technical
     debt costs the most because the team keeps working there. Highest scores
     are the best refactoring ROI.
   - **change_coupling** — pairs of files that change together in a high share
     of commits despite (often) no static dependency. Flag pairs above ~30% as
     candidate hidden coupling / leaky abstractions or broken module boundaries.
   - **knowledge_map** — files with `bus_factor_risk: true` are understood by a
     single author. Combined with a high hotspot score, these are the riskiest
     files in the codebase.

3. Present a ranked, actionable list. For the top hotspots, propose concrete
   steps (extract methods to lower complexity, add characterization tests
   before refactoring, pair-program to spread knowledge on bus-factor-1 files).

Note: results require git history. A shallow clone limits the window — fetch
full history (`git fetch --unshallow`) for accurate churn.
