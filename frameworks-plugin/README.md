# Master Framework Compendium — Claude Code Plugin

A Claude Code plugin that packages **28 field-tested thinking frameworks** — each authored by a named practitioner — as installable **skills**, **orchestrator agents**, **slash commands**, and a **framework-suggestion hook**.

Instead of answering strategy, decision, communication, product, org, and productivity questions ad hoc, Claude reaches for the right battle-tested tool: the Rumelt Kernel for strategy, Tactical Empathy for negotiation, the Kano Model for feature prioritization, and so on.

## What's inside

| Component | Count | What it does |
|-----------|-------|--------------|
| **Skills** | 28 | One per framework. Auto-activate on relevant requests; each walks the framework step by step with an output template. |
| **Agents** | 7 | Orchestrators that select and sequence skills for a scenario (strategy, decisions, communication, product, org/people, productivity, plus a meta selector). |
| **Commands** | 4 | `/list`, `/recommend`, `/apply`, `/sequence`. |
| **Hooks** | 2 | `SessionStart` orientation note + `UserPromptSubmit` framework suggester. |

## The 28 frameworks

**Strategy & diagnosis:** Rumelt Kernel · First Principles · Inversion · MECE Issue Tree
**Communication & influence:** SSI · SCQA/Pyramid · SCR · SPIN Selling
**Decision-making:** OODA Loop · Recognition-Primed Decision · Second-Order Thinking · Integrative Thinking
**Organizational & people:** 4P Audit · Wartime/Peacetime CEO · Trust Equation · Tactical Empathy · Give and Take
**Product & prioritization:** Jobs to Be Done · LNO · Kano Model · North Star Metric · PR/FAQ Working Backwards · PLG/PLS
**Productivity & knowledge:** PARA · OKRs · Tacit Knowledge (Commoncog) · Cognitive Load (Team Topologies) · Schlep Blindness

## Installation

This is a standard Claude Code plugin. Add it via a marketplace or local path.

**From a local clone:**
```bash
git clone https://github.com/dhsquires/frameworks-plugin.git
```
Then in Claude Code add it as a local plugin (point your plugin/marketplace config at the cloned directory), or symlink it into your plugins directory and restart Claude Code.

Once installed, skills auto-activate when relevant, and the commands appear namespaced as `/frameworks-plugin:<command>`.

## Usage

```text
/frameworks-plugin:list                         # browse all frameworks by scenario
/frameworks-plugin:recommend our churn is up but the team blames the product   # get a recommendation
/frameworks-plugin:apply rumelt our enterprise deals keep stalling at legal     # apply one framework
/frameworks-plugin:sequence should we rebuild the onboarding from scratch       # compounding analysis
```

Or just describe your problem — the `UserPromptSubmit` hook nudges Claude toward the matching framework, and you can invoke an orchestrator agent (e.g. `strategy-advisor`, `decision-coach`, `product-strategist`) for a guided multi-framework session.

## How skills work

Each skill lives in `skills/<name>/SKILL.md` with frontmatter (`name`, `description`) and a body covering: when to use it, the framework itself, step-by-step instructions, how Claude should facilitate, an output template, pitfalls, and source resources. The `description` is written to trigger auto-activation on the right kind of request.

## Layout

```
frameworks-plugin/
├── .claude-plugin/plugin.json
├── skills/<28 skills>/SKILL.md
├── agents/<7 orchestrators>.md
├── commands/{list,recommend,apply,sequence}.md
├── hooks/
│   ├── hooks.json
│   └── scripts/{session_start.py,suggest_frameworks.py}
└── README.md
```

## Credits

Frameworks are the work of their named authors (Rumelt, Munger, Minto, Rackham, Boyd, Klein, Dalio, Martin, Horowitz, Maister, Voss, Grant, Christensen/Moesta, Doshi, Kano, Rachitsky, Bezos/Amazon, Forte, Grove, Chin, Skelton/Pais, Graham, Verna, and others). This plugin operationalizes them for AI-assisted thinking; see each skill's **Resources** section for primary sources.

## License

MIT — see [LICENSE](./LICENSE).
