# code-quality

**Maintainability & complexity metrics for any codebase — packaged as a Claude Code plugin and a GitHub workflow that runs locally, pre-commit, on pull requests, and in CI.**

This project implements the metric *portfolio* that elite engineering teams
(Google, Netflix, Spotify, Microsoft) and decades of empirical research
converge on — not a single number, but an interconnected system of structural,
behavioural and delivery signals. The analysis engine is **pure Python 3.9+
standard library** (zero third-party dependencies required), multi-language, and
runs the same way on your laptop, in a git hook, and in GitHub Actions.

---

## What it measures

### Static metrics (from the source)

| Metric | Layer | Notes |
|---|---|---|
| **Cyclomatic complexity** (McCabe) | function | Independent execution paths. |
| **Cognitive complexity** (SonarSource) | function | How hard code is to *understand*; nesting is penalised. |
| **Maintainability Index** | file | Composite of Halstead volume + complexity + LOC (normalised 0–100). |
| **Halstead volume / difficulty / effort** | file | Information content & mental effort; feeds the MI. |
| **Efferent coupling (Ce) & Instability** | file/module | Fan-out and `I = Ce / (Ce + Ca)` (Robert C. Martin). |
| **Comment ratio** | file | Documentation density. |
| **Technical Debt Ratio (SQALE)** | codebase | Remediation ÷ development cost → A–E grade. |

### Behavioural metrics (from git history)

| Metric | Notes |
|---|---|
| **Hotspots** | `churn × complexity` — where technical debt costs the most (Tornhill / CodeScene). |
| **Change coupling** | Files that change together → hidden logical dependencies / leaky module boundaries. |
| **Knowledge map / bus factor** | Single-author files → knowledge-loss risk. |

### Delivery hookup

- **Test coverage** is read from `coverage.xml` (Cobertura), coverage.py JSON,
  Istanbul/nyc JSON, or `lcov.info` via `--coverage-file`, and can be gated.

> These map directly onto the research portfolio for integration-heavy
> Python/JS codebases: cognitive complexity, Maintainability Index and SQALE
> debt ratio as the critical signals, with hotspots, coupling and coverage as
> high-value overlays.

---

## Quick start (CLI)

```bash
# Whole repo, human-readable report
python3 scripts/code-quality.py analyze .

# Whole repo + git-history hotspots & change coupling
python3 scripts/code-quality.py analyze . --behavioral

# Only what changed vs main, and fail on threshold violations (PR-style)
python3 scripts/code-quality.py analyze --changed-only --base origin/main --gate

# Only staged files (pre-commit-style)
python3 scripts/code-quality.py analyze --staged --gate

# Markdown report for a PR comment / JSON for tooling
python3 scripts/code-quality.py analyze . --format md  --output report.md
python3 scripts/code-quality.py analyze . --format json --output report.json

# Behavioural-only view
python3 scripts/code-quality.py hotspots .
```

Exit code is `0` when the gate passes (warnings allowed) and `1` when there are
error-level violations.

---

## Using it as a Claude Code plugin

The repo is also a Claude Code **plugin marketplace**. Install it with:

```
/plugin marketplace add dhsquires/code-quality
/plugin install code-quality@code-quality
```

(or, for local development, `/plugin marketplace add /path/to/code-quality`).

It provides:

**Slash commands**
- `/code-metrics [path | --changed | --staged]` — run metrics and get a
  prioritized, actionable summary.
- `/metrics-hotspots [path]` — git-history hotspots, change coupling, bus factor.
- `/metrics-gate [--staged | --changed]` — run the gate before a commit/PR and
  fix what fails.

**Skill** — `code-metrics`: domain knowledge so Claude computes *and correctly
interprets* the metrics (thresholds, how to prioritize, what fixes to suggest).

**Subagent** — `code-quality-reviewer`: a focused reviewer that quantifies a
change's maintainability and returns a ranked refactoring report.

**Hook** — a `PreToolUse` hook (`hooks/pre_commit_gate.sh`) that runs the gate on
staged files before any `git commit` Claude executes, blocking only on
error-level violations. Bypass with `git commit --no-verify`.

---

## Running before commits (git hook, no Claude required)

```bash
# Symlink the bundled hook into your repo
ln -sf ../../hooks/pre-commit .git/hooks/pre-commit

# …or use the pre-commit framework
pip install pre-commit && pre-commit install   # uses .pre-commit-config.yaml
```

---

## GitHub workflow (PR + CI + manual)

`.github/workflows/code-quality.yml` runs three ways:

- **Pull request** — analyses only the files the PR changes, posts/updates a
  sticky **report comment**, and fails the check on gate violations.
- **Push to `main`/`master`** — full-repo gate plus a JSON/Markdown trend
  artifact.
- **Manual (`workflow_dispatch`)** — run from the Actions tab over the full repo
  or changed-only, e.g. for a pre-release sweep.

It needs no secrets beyond the default `GITHUB_TOKEN` and no external actions
besides first-party `actions/*` and `actions/github-script`.

---

## Configuration

Drop a `code-quality.toml` at your repo root (see
[`config/code-quality.toml`](config/code-quality.toml) for the fully-commented
example), or use a `[tool.code-quality]` table in `pyproject.toml`. Every
threshold and the gate behaviour (`fail_on = "error" | "warning" | "never"`) is
tunable.

### Default thresholds

- **Cyclomatic:** `<10` green · `10–15` review · `>15` refactor · `>25` high-risk
- **Cognitive:** warn `>15` · error `>30`
- **Maintainability Index:** `≥20` healthy · `10–19` moderate · `<10` hotspot
- **Efferent coupling:** investigate `>14`
- **Technical Debt Ratio:** A `≤5%` · B `≤10%` · C `≤20%` · D `≤50%` · E `>50%`
- **Coverage:** `≥80%` on core logic (when a coverage file is supplied)

#### A note on the Maintainability Index scale

This tool uses the standard **normalised** formula, the same one
[Radon](https://radon.readthedocs.io) implements:

```
MI = max(0, (171 − 5.2·ln(HV) − 0.23·CC − 16.2·ln(LOC)) · 100 / 171)
```

On this file-level scale, **≥20 is healthy** (Radon grade A), 10–19 is moderate
(B), and <10 is a debt hotspot (C). The frequently-quoted **Visual Studio
"85/65"** figures come from VS's *per-member* rollup and a differently-computed
Halstead volume — they are not comparable to this file-level number, so we
calibrate the green/yellow/red bands to the formula we actually compute.

---

## Language support

- **Python** is parsed with a real AST → accurate per-function cyclomatic and
  cognitive complexity, imports/coupling, and Halstead metrics.
- **JavaScript/TypeScript, Go, Java, Ruby, PHP, C/C++, C#, Rust, Kotlin, Swift,
  Scala** use a token/keyword heuristic and report a **file-level** complexity
  aggregate (no per-function split without a real parser). For per-function
  metrics in these languages, install [`lizard`](https://pypi.org/project/lizard/).

Behavioural metrics require real git history; run `git fetch --unshallow` on
shallow clones for an accurate churn window.

---

## Development

```bash
python3 tests/test_metrics.py          # run the test suite (stdlib only)
python3 scripts/code-quality.py analyze scripts/ tests/   # dogfood the gate
```

## License

MIT — see [LICENSE](LICENSE).

---

<sub>Metric definitions and thresholds are grounded in the research summarised in
`docs/` and in SonarQube/SonarSource, Visual Studio Code Metrics, the SQALE
model, Robert C. Martin's package metrics, and CodeScene/Tornhill's behavioural
code analysis.</sub>
