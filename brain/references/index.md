---
type: Index
title: References Index
description: Materialized external sources cited as provenance elsewhere in the bundle.
timestamp: 2026-06-22
tags:
  - okf
  - index
  - references
  - provenance
engram_visibility: private
---

# References

> _When a concept elsewhere in the bundle cites an external source (in a `# Citations` section or via a `provenance` key), that source gets **materialized here as its own concept** at `references/<slug>.md`. This turns provenance into first-class, linkable nodes in the OKF graph._

## How references work

- A reference file uses `type: Reference` and frontmatter describing the source (title, description, timestamp; optionally `provenance`).
- The **concept ID** is `references/<slug>` (path minus `.md`), which is what citing files link to.
- Citing files link here from their `# Citations` section so a reader can follow a claim back to its origin.

## Naming

- Use a short, stable, kebab-case slug derived from the source (e.g. `references/okf-spec-v0-1.md`).

## Current references

> _None yet. References will be added here as sources are cited during interviews and updates._

| Reference | Cited by |
|-----------|----------|
| _(none yet)_ | _(none yet)_ |

_Up: [../index.md](../index.md)_
