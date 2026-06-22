# memory-model

## ADDED Requirements

### Requirement: Three-layer memory
The system SHALL represent memory in three layers — episodic (raw per-session events),
semantic (consolidated entities and facts), and procedural (learned task recipes) — over a
single typed graph of nodes and edges.

#### Scenario: Episodic event is recorded
- **WHEN** an agent reports an observation, tool call, outcome, correction, or source use
- **THEN** the system SHALL persist it as an append-only episodic event scoped by `org_id`,
  `user_id`, and `visibility`, with a `decay_at` timestamp

#### Scenario: Semantic node carries a version
- **WHEN** consolidation promotes a fact about a person, project, connector, artifact, or
  concept
- **THEN** the system SHALL store it as a versioned semantic node and SHALL mark any node it
  replaces as `superseded_by` the new version rather than deleting it

#### Scenario: Procedure captures what worked and what failed
- **WHEN** consolidation distills how a recurring task type was done
- **THEN** the resulting procedure SHALL record the recipe, preferred sources, and known
  dead ends as a versioned, provenance-linked record

### Requirement: Typed graph relationships
The system SHALL connect memory nodes with typed edges
(`authored_by`, `part_of`, `derived_from`, `corrects`, `supersedes`, `cites`,
`used_source`, `contradicts`, `relates_to`), each carrying `confidence`, `recency`, and
`usefulness` attributes.

#### Scenario: Correction creates a high-signal edge
- **WHEN** a user corrects a prior memory
- **THEN** the system SHALL create a `corrects` edge from the correction to the target and
  SHALL raise the correction's weight above ordinary observations during retrieval and
  consolidation

### Requirement: Provenance on derived memory
The system SHALL attach provenance to every semantic and procedural memory linking it to the
episodic events, sources, or corrections it was derived from. Memory without provenance
SHALL NOT be promotable.

#### Scenario: Unprovenanced candidate is blocked
- **WHEN** a consolidation candidate cannot be linked to at least one source event, source
  document, or correction
- **THEN** the system SHALL refuse to promote it and SHALL record the rejection reason

#### Scenario: Provenance is traceable on demand
- **WHEN** a caller requests the provenance of a memory id
- **THEN** the system SHALL return the full chain of contributing events and sources

### Requirement: Decay and forgetting
The system SHALL decay episodic memory over time using a configurable half-life and SHALL
remove memories that fall below a usefulness threshold, except where retention is required
by policy.

#### Scenario: Stale low-value memory is forgotten
- **WHEN** an episodic event passes its `decay_at` and its usefulness is below threshold and
  no retention hold applies
- **THEN** the consolidation run SHALL remove it and SHALL log the removal in the audit log

### Requirement: OKF concept mapping
Semantic and procedural memories SHALL be representable as OKF concepts — one markdown
document with YAML frontmatter per concept — addressed by concept ID. The internal
`node_kind` enum SHALL be retained for graph semantics and mapped to an open OKF `type`
string at the interchange boundary. Typed, weighted graph edges remain the source of truth and
SHALL be rendered as standard markdown links (an untyped directed relationship) on export.

#### Scenario: Procedural memory exports as a Playbook concept
- **WHEN** a procedure is exported
- **THEN** it SHALL serialize as an OKF concept whose `type` reflects a procedural kind (for
  example `Playbook`) with the recipe and known dead ends in the markdown body

### Requirement: Git-canonical knowledge, derived index
The canonical representation of semantic and procedural memory SHALL be OKF bundles in a git
repository; a memory version SHALL be identified by a git commit SHA. Postgres (graph edges,
embeddings, FTS) SHALL be a derived projection that the system can rebuild from the bundles at
any commit. Episodic memory SHALL remain Postgres-only and SHALL NOT be committed to git.
Edge weights (confidence, recency, usefulness) are derived and SHALL be recomputed by the
indexer rather than stored in git.

#### Scenario: Derived index rebuilds from a commit
- **WHEN** the derived index is dropped and rebuilt from a given commit SHA
- **THEN** retrieval results for that version SHALL match what the bundles at that commit
  describe, and no canonical knowledge SHALL be lost
