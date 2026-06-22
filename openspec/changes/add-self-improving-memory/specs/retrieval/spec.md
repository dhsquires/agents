# retrieval

## ADDED Requirements

### Requirement: Hybrid retrieval
The system SHALL retrieve memory by fusing lexical (full-text), vector (pgvector kNN), and
graph-expansion results into a single ranked set.

#### Scenario: All three retrievers contribute
- **WHEN** a context pack is requested
- **THEN** the system SHALL run lexical, vector, and graph retrieval, SHALL fuse them with
  rank fusion, and SHALL rerank and deduplicate before returning

#### Scenario: Graph expansion is bounded
- **WHEN** the graph expander traverses from seed nodes
- **THEN** it SHALL follow only high-weight edges and SHALL stop within two hops

### Requirement: Budgeted context pack
The system SHALL assemble retrieved memory into a context pack that fits a caller-supplied
token budget.

#### Scenario: Budget is respected
- **WHEN** the assembled candidates exceed the token budget
- **THEN** the system SHALL drop the lowest-scoring items until the pack fits and SHALL never
  return a pack that exceeds the budget

### Requirement: Recency and usefulness weighting
The system SHALL weight retrieval by an exponential recency decay (configurable half-life)
and by usefulness updated from outcome feedback.

#### Scenario: Corrected guidance outranks the superseded version
- **WHEN** a query matches both a superseded memory and the correction that replaced it
- **THEN** the system SHALL rank the correction higher and SHALL exclude the superseded
  version unless explicitly requested

### Requirement: Provenance and isolation on every result
The system SHALL return provenance with every retrieved item and SHALL only return memory
the caller is authorized to see under org and visibility scoping.

#### Scenario: Cross-user private memory is never returned
- **WHEN** user A requests a context pack
- **THEN** the system SHALL exclude any `private` memory owned by another user

### Requirement: Index-first retrieval and OKF rendering
The system SHALL support an index-first retrieval mode that returns directory `index.md`
listings before full concept bodies, and retrieved concepts SHALL be renderable in OKF form
with their citations so the same artifact serves agents, the Console, and external OKF tools.

#### Scenario: Drill-down avoids loading the whole bundle
- **WHEN** an agent retrieves under a budget using index-first mode
- **THEN** the system SHALL return index listings first and SHALL load full bodies only for
  concepts the agent selects
