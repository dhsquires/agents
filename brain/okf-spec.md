---
type: Reference
title: Open Knowledge Format (OKF) v0.1 — In-Repo Summary
description: A concise local summary of the OKF v0.1 conventions used by this bundle, plus the Engram extension keys.
timestamp: 2026-06-22
tags:
  - okf
  - reference
  - spec
  - engram
engram_visibility: private
---

# Open Knowledge Format v0.1 (summary)

> _A short, working summary of the format this bundle follows. The canonical spec lives upstream; this file captures what a consumer of this repo needs to know._

## Core idea

OKF is a **directory of markdown files**, each carrying **YAML frontmatter**, that together describe a body of knowledge. It is designed for **permissive consumption**: any tool that can read text can read it, and richer tools can use the graph and metadata.

## Required frontmatter keys

Every concept file MUST include:

- `type:` — a non-empty OKF type string (e.g. `Index`, `Reference`, `Identity`, `Playbook`, `BootContext`, `Log`).
- `title:` — a human-readable title.
- `description:` — a one-sentence summary.
- `timestamp:` — last-meaningful-update date.

## Conventions

- **Concept ID** = the file's path with the `.md` extension removed (e.g. `core/values`). IDs are how concepts reference one another.
- **Links form the graph.** Standard markdown links between files are the edges; following them is how an agent navigates.
- **`index.md`** files provide **progressive disclosure**: start at the index, drill down only as far as a task requires.
- **`log.md`** holds **history**, newest-first, with ISO 8601 date headings.
- **`# Citations` section** — when a concept asserts something sourced externally, add a Citations section recording **provenance** (where the claim came from).

## Engram extension keys

This bundle uses the Engram extension, which adds optional frontmatter keys:

- `engram_node_id` — stable unique identifier for the concept node.
- `engram_visibility` — `private` | (other levels) controlling who/what may read it.
- `engram_confidence` — how sure the author is of the content.
- `engram_version` — version of the concept's content.
- `provenance` — structured origin metadata (complements the `# Citations` section).

> _Only `engram_visibility: private` is set across this template; the rest are added as content matures._
