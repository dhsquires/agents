# knowledge-interchange

## ADDED Requirements

### Requirement: OKF as the interchange format
The system SHALL use the Open Knowledge Format (OKF) — markdown files with YAML frontmatter
organized as a hierarchical bundle — as its canonical serialization for semantic and
procedural memory at every system boundary (export, import, the MCP wiki resource, and the
Console viewer). The Postgres graph remains the secured, mutable runtime source of truth; OKF
is its portable projection.

#### Scenario: Semantic memory serializes to a conformant bundle
- **WHEN** a caller exports knowledge they are authorized to see
- **THEN** the system SHALL emit a directory of markdown documents with YAML frontmatter that
  is conformant with OKF v0.1, declaring `okf_version` in the bundle-root `index.md`

### Requirement: OKF-conformant frontmatter mapping
The system SHALL map each exported concept to OKF frontmatter with a non-empty `type` and
SHALL also populate `title`, `description`, and `timestamp` so that exported documents pass
the OKF reference validator, which requires those keys. Engram-specific fields SHALL be
carried as additive extension keys (for example `engram_node_id`, `engram_visibility`,
`engram_confidence`, `engram_version`, `provenance`) that conformant consumers ignore.

#### Scenario: Extension keys round-trip without breaking consumers
- **WHEN** a bundle containing Engram extension keys is read by a vendor-neutral OKF consumer
- **THEN** the consumer SHALL be able to render the document using only standard OKF fields,
  and a subsequent Engram import SHALL preserve the extension keys

#### Scenario: Open type strings are accepted on import
- **WHEN** an imported concept declares a `type` Engram does not recognize
- **THEN** the system SHALL ingest it as a generic concept, preserving the original `type`
  string, rather than rejecting the document

### Requirement: Concept-ID addressing
The system SHALL address concepts by their bundle path with the `.md` suffix removed (the OKF
concept ID), using path segments that match the slug grammar `[A-Za-z0-9_][A-Za-z0-9_.-]*`,
and the MCP resource URI `engram://wiki/{concept_id}` SHALL resolve to the same concept.

#### Scenario: Resource URI and bundle path agree
- **WHEN** a concept exported at bundle path `tables/orders.md` is requested as a resource
- **THEN** `engram://wiki/tables/orders` SHALL resolve to that concept

### Requirement: Bundle export tool
The system SHALL provide an `export_bundle` operation that produces an OKF bundle for a
requested scope, filtered to what the caller is authorized to see.

#### Scenario: Export is scoped to the caller
- **WHEN** a caller without access to another user's private memory exports a bundle
- **THEN** the produced bundle SHALL contain no documents derived from that private memory

### Requirement: Bundle import tool
The system SHALL provide an `import_bundle` operation that ingests an OKF bundle (hand-authored,
exported from another system, or produced by an external enrichment agent) as a knowledge
source feeding extraction and consolidation.

#### Scenario: Imported bundle enters the consolidation path
- **WHEN** a valid OKF bundle is imported
- **THEN** its concepts SHALL be recorded with provenance identifying the bundle as their
  source and SHALL become candidates for the next consolidation run rather than being promoted
  unreviewed

### Requirement: Progressive disclosure via index documents
The system SHALL generate `index.md` listings for directories in an exported bundle and SHALL
expose an index-first retrieval mode so an agent can navigate the hierarchy one level at a time
instead of loading an entire bundle.

#### Scenario: Index returned before full content
- **WHEN** an agent requests the contents of a bundle directory
- **THEN** the system SHALL return the directory's `index.md` enumerating child concepts with
  their descriptions, and SHALL fetch full concept bodies only when requested

### Requirement: Update history via log documents
The system SHALL render consolidation history for a scope as an OKF `log.md` document with
date-grouped, newest-first entries using ISO 8601 date headings.

#### Scenario: Consolidation run appears in the log
- **WHEN** a consolidation run promotes changes to a scope
- **THEN** the scope's `log.md` SHALL gain a dated entry describing the creations, updates, and
  deprecations from that run

### Requirement: Citations and references as concepts
The system SHALL render the structured provenance of a concept as an OKF `# Citations` section
and SHALL be able to materialize external sources as first-class `references/<slug>` concepts.
Structured provenance edges remain the source of truth; the rendered citations are their OKF
projection.

#### Scenario: Provenance becomes citations on export
- **WHEN** a concept with provenance is exported
- **THEN** the exported document SHALL list its sources under a `# Citations` heading

### Requirement: Permissive consumption
The system SHALL consume OKF bundles permissively: it SHALL NOT reject a bundle for missing
optional frontmatter fields, unknown `type` values, unknown extension keys, broken
cross-links, or missing `index.md` files.

#### Scenario: Broken cross-link is tolerated
- **WHEN** an imported concept links to a target absent from the bundle
- **THEN** the system SHALL ingest the concept and SHALL treat the dangling link as
  not-yet-written knowledge rather than an error

### Requirement: Bundles in git are the system of record
The git repository of OKF bundles SHALL be the authoritative store for semantic and procedural
memory. `export_bundle` SHALL therefore return repository content directly, and `import_bundle`
SHALL realize an import as a commit to the repository followed by a reindex.

#### Scenario: Import is a commit, not a hidden write
- **WHEN** a bundle is imported
- **THEN** the change SHALL appear as a git commit on the repository and the derived index
  SHALL be updated from that commit

#### Scenario: Retrieval can be pinned to a version
- **WHEN** a caller requests retrieval pinned to a commit SHA
- **THEN** the system SHALL serve results consistent with the bundles at that commit
