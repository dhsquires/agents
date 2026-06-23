---
description: Run the quality gate on changed/staged code before committing or opening a PR; report pass/fail and what to fix.
argument-hint: "[--staged | --changed] (default: --staged)"
allowed-tools: Bash, Read, Edit
---

# Quality gate

Enforce the maintainability/complexity thresholds the same way the CI workflow
does — useful right before a commit or PR.

## What to do

1. Choose scope from `$ARGUMENTS` (default `--staged`):
   - `--staged`  → files staged in the git index (pre-commit)
   - `--changed` → files changed vs `origin/main` (pre-PR)

2. Run the gate:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/code-quality.py" analyze \
       <scope> --gate --format text
   ```

   Exit code `0` = pass (warnings allowed), `1` = gate failed (error-level
   violations).

3. If it **passed**, say so and list any warnings worth addressing.

4. If it **failed**, for each error-level finding:
   - Open the cited file/line, explain *why* it trips the threshold
     (e.g. deep nesting drives cognitive complexity).
   - Offer a concrete fix and, if the user agrees, apply it with Edit.
   - Re-run the gate to confirm it now passes.

Keep the loop tight: fix the error-level findings first, re-run, repeat until
the gate is green.
