---
description: Run code maintainability & complexity metrics on the repo (or changed files) and summarize the results.
argument-hint: "[path | --changed | --staged] (default: whole repo)"
allowed-tools: Bash, Read, Glob, Grep
---

# Code metrics

Run the bundled metrics engine and report on maintainability and complexity.

## What to do

1. Locate the engine. It lives at `${CLAUDE_PLUGIN_ROOT}/scripts/code-quality.py`
   and needs only Python 3.9+ standard library. Determine the scope from the
   user's argument `$ARGUMENTS`:
   - empty            → analyse the whole repo: `analyze . --behavioral`
   - `--changed`      → `analyze --changed-only --base origin/main`
   - `--staged`       → `analyze --staged`
   - a path           → `analyze <path>`

2. Run it as JSON so you can reason about the numbers precisely:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/code-quality.py" analyze \
       <scope> --format json
   ```

   (Add `--behavioral` for whole-repo runs to include git hotspots & change
   coupling. Add `--coverage-file <file>` if a coverage report exists.)

3. Read the JSON and present a concise, prioritized summary:
   - Overall verdict (gate pass/fail), Technical Debt Ratio grade, average
     Maintainability Index.
   - The top offenders: functions over the cognitive/cyclomatic thresholds,
     files with low Maintainability Index, high efferent coupling, and any
     hotspots (high churn × complexity).
   - For each top offender, give a specific, actionable refactoring suggestion
     (extract method, reduce nesting, split a low-cohesion module, break a
     change-coupled pair, add tests to a bus-factor-1 hotspot).

4. Do NOT just dump the raw JSON. Lead with the 3–5 things most worth fixing,
   ordered by impact (hotspots and gate errors first).

## Reference thresholds (defaults; configurable in `code-quality.toml`)

- Cyclomatic complexity: <10 green, 10–15 review, >15 refactor, >25 high-risk
- Cognitive complexity: warn >15, error >30
- Maintainability Index (normalised formula): ≥20 healthy, 10–19 moderate, <10 hotspot
- Efferent coupling: investigate >14
- Technical Debt Ratio: A ≤5%, B ≤10%, C ≤20%, D ≤50%, E >50%
