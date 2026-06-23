---
name: code-metrics
description: >-
  Compute and interpret software maintainability & complexity metrics
  (cyclomatic/cognitive complexity, Maintainability Index, Halstead volume,
  coupling/instability, SQALE technical-debt ratio, and git-history hotspots /
  change coupling / bus-factor). Use when the user asks to measure code quality,
  find refactoring targets, assess technical debt, review complexity, or set up
  quality gates for commits/PRs/CI.
---

# Code metrics skill

This skill measures the maintainability and complexity of a codebase using the
metric portfolio that elite engineering teams rely on, and — crucially — helps
interpret the numbers into prioritized, actionable advice.

## The engine

A dependency-free analyzer ships with this plugin at
`scripts/code-quality.py` (Python 3.9+ stdlib only). Subcommands:

```bash
# Static metrics + quality gate (text | md | json)
python3 scripts/code-quality.py analyze <paths> [--changed-only --base REF]
        [--staged] [--gate] [--format md|json|text] [--output FILE]
        [--coverage-file FILE] [--behavioral]

# Git-history behavioural metrics
python3 scripts/code-quality.py hotspots <paths> [--format json]
```

When invoked inside a plugin context the engine is at
`${CLAUDE_PLUGIN_ROOT}/scripts/code-quality.py`.

## What gets measured and why it matters

| Metric | Layer | What it tells you |
|---|---|---|
| **Cyclomatic complexity** | function | Number of independent paths; testability/branch load. |
| **Cognitive complexity** | function | How hard the code is to *understand* (nesting penalized). The primary readability signal. |
| **Maintainability Index** | file | Composite of Halstead volume + complexity + LOC. Trendable health score. |
| **Halstead volume/effort** | file | Information content & mental effort; feeds the MI. |
| **Efferent coupling (Ce) / instability** | file/module | Fan-out and `I = Ce/(Ce+Ca)`; change-propagation risk. |
| **Technical Debt Ratio (SQALE)** | codebase | Remediation cost ÷ development cost → A–E grade; the business-facing number. |
| **Hotspots** | file | churn × complexity — where debt costs the most (highest refactoring ROI). |
| **Change coupling** | file pairs | Files that change together → hidden logical dependencies / leaky boundaries. |
| **Bus factor** | file | Single-author files → knowledge-loss risk. |

## Thresholds (defaults — override in `code-quality.toml`)

- **Cyclomatic:** <10 green · 10–15 review · >15 refactor · >25 high-risk
- **Cognitive:** warn >15 · error >30
- **Maintainability Index:** uses the standard *normalised* formula
  `MI = max(0, (171 − 5.2·ln(HV) − 0.23·CC − 16.2·ln(LOC)) · 100/171)`, the same
  one Radon implements. On this scale ≥20 is healthy (grade A), 10–19 moderate
  (B), <10 a debt hotspot (C). (The often-quoted Visual Studio "85/65" figures
  assume VS's *per-member* rollup and a different Halstead computation — they do
  not apply to this file-level formula.)
- **Efferent coupling:** investigate >14
- **Technical Debt Ratio:** A ≤5% · B ≤10% · C ≤20% · D ≤50% · E >50%
- **Coverage:** ≥80% on core logic (pass `--coverage-file`)

## How to interpret results (be useful, not noisy)

1. **Lead with impact.** Rank by: gate errors → hotspots (churn × complexity) →
   low-MI files → high coupling. A complex file nobody touches matters far less
   than a moderately complex file changed every sprint.
2. **No single metric decides.** Research (TU Munich SANER) shows no one static
   metric is reliable across all projects — overlay complexity + churn +
   coverage to find where risk compounds.
3. **Give a concrete fix per finding:** extract method / guard-clause to cut
   nesting (cognitive), split a low-cohesion module, depend on abstractions to
   cut efferent coupling, break a change-coupled pair, add characterization
   tests before refactoring a bus-factor-1 hotspot.
4. **For PRs, prefer deltas.** Use `--changed-only` so you judge what the change
   introduces, not the whole legacy codebase.

## Caveats

- Python is analyzed with a real AST (accurate per-function metrics). Other
  languages (JS/TS/Go/Java/…) use a token heuristic and report a single
  file-level aggregate; install `lizard` for per-function metrics there.
- Behavioural metrics need real git history; unshallow shallow clones first.
