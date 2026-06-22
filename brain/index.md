---
type: Index
title: LLM Brain — Personal Context Bundle
description: Root index for an OKF v0.1 personal-context knowledge base populated via a structured interview.
timestamp: 2026-06-22
okf_version: 0.1
tags:
  - okf
  - index
  - personal-context
  - llm-brain
engram_visibility: private
---

# LLM Brain

This is an **OKF v0.1 personal-context bundle** — a portable, plain-text knowledge base about one person, designed to be loaded by AI agents so they can act with genuine context. It follows Google's Open Knowledge Format: every file is markdown with YAML frontmatter, files link to each other to form a graph, and `index.md` files provide progressive disclosure.

> _This bundle ships as a template. Populate it by running the interview in [interview/interview-questionnaire.md](../interview/interview-questionnaire.md), then keep it fresh per the cadence below._

## Concept files by layer

| Layer | File | Update frequency |
|-------|------|------------------|
| Boot | [boot-context.md](boot-context.md) | Monthly |
| Boot | [log.md](log.md) | On every change |
| Boot | [okf-spec.md](okf-spec.md) | As spec changes |
| Core | [core/identity.md](core/identity.md) | Quarterly |
| Core | [core/values.md](core/values.md) | Quarterly |
| Core | [core/goals.md](core/goals.md) | Quarterly |
| Professional | [professional/career.md](professional/career.md) | After milestones |
| Professional | [professional/work-style.md](professional/work-style.md) | After milestones |
| Professional | [professional/learning.md](professional/learning.md) | After milestones |
| Personal | [personal/relationships.md](personal/relationships.md) | Monthly |
| Personal | [personal/health.md](personal/health.md) | Monthly |
| Personal | [personal/finances.md](personal/finances.md) | Monthly |
| Personal | [personal/lifestyle.md](personal/lifestyle.md) | Monthly |
| Worldview | [worldview/philosophy.md](worldview/philosophy.md) | Annually |
| Worldview | [worldview/narrative.md](worldview/narrative.md) | Annually |
| Knowledge map | [knowledge/domains.md](knowledge/domains.md) | As stack changes |
| Knowledge map | [knowledge/tools.md](knowledge/tools.md) | As stack changes |
| Meta | [meta/ai-prefs.md](meta/ai-prefs.md) | As preferences evolve |
| References | [references/index.md](references/index.md) | As sources are cited |

## How to use

1. **Agents start here or at [boot-context.md](boot-context.md).** Boot context is the cheap, always-loaded summary; this index is the map.
2. **Follow links for depth.** Each layer's `index.md` lists its concept files. Drill down only as far as the task needs (progressive disclosure).
3. **Respect visibility.** Every file carries `engram_visibility`; treat `private` content accordingly.
4. **Record changes** in [log.md](log.md), newest-first.
5. **Cite sources.** External provenance is materialized under [references/](references/index.md).
