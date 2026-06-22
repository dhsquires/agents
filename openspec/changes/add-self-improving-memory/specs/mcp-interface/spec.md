# mcp-interface

## ADDED Requirements

### Requirement: MCP server exposure
The system SHALL expose memory operations as a Model Context Protocol server over the
Streamable HTTP transport so that any MCP-enabled client can attach without bespoke
integration.

#### Scenario: Any MCP client can connect
- **WHEN** a compliant MCP client initializes a session against the server URL with a valid
  token
- **THEN** the server SHALL advertise its tools, resources, and prompts and SHALL accept
  tool calls

### Requirement: Read tools
The system SHALL provide read tools `search`, `get_context_pack`, and `trace`.

#### Scenario: Context pack assembled for a task
- **WHEN** a client calls `get_context_pack` with a task descriptor and a token budget
- **THEN** the server SHALL return a ranked, deduplicated set of memories within the budget,
  each annotated with provenance and a freshness/usefulness score

### Requirement: Write tools
The system SHALL provide write tools `remember`, `record_outcome`, `correct`, and `link`
that append episodic memory and feedback during a task.

#### Scenario: Outcome feedback closes the loop
- **WHEN** a client calls `record_outcome` with a task id, status, and the sources it used
- **THEN** the server SHALL persist the outcome and SHALL update the usefulness of each cited
  source so future retrieval reflects it

### Requirement: Governance tool
The system SHALL provide a `forget` tool that enqueues a redaction request.

#### Scenario: Forget request is enqueued
- **WHEN** a client calls `forget` with a selector and reason
- **THEN** the server SHALL create a redaction request, SHALL record it in the audit log, and
  SHALL NOT confirm completion until the cascade has run

### Requirement: Scoped authorization
The system SHALL authenticate via OAuth 2.1 bearer tokens and SHALL enforce per-tool scopes
(`memory:read`, `memory:write`, `memory:forget`, `memory:admin`), setting row-level claims
before any data access.

#### Scenario: Missing scope is denied
- **WHEN** a client with only `memory:read` calls a write or forget tool
- **THEN** the server SHALL reject the call with an authorization error and SHALL NOT mutate
  any data

### Requirement: Wiki resources
The system SHALL expose semantic pages as MCP Resources addressable as
`engram://wiki/{entity_id}` and SHALL provide a `load_context` prompt.

#### Scenario: Wiki page is retrievable as a resource
- **WHEN** a client reads `engram://wiki/{entity_id}` for an entity it is authorized to see
- **THEN** the server SHALL return the rendered Markdown page with its provenance footer

### Requirement: OKF wiki resources and bundle tools
The wiki resource `engram://wiki/{concept_id}` SHALL return OKF-conformant markdown
(frontmatter + body + citations). The server SHALL additionally provide `export_bundle`
(scope `memory:read`) and `import_bundle` (scope `memory:admin`) tools, and a `get_index` tool
(scope `memory:read`) that returns an OKF `index.md` listing for progressive disclosure.

#### Scenario: Wiki resource is OKF-conformant
- **WHEN** a client reads `engram://wiki/{concept_id}`
- **THEN** the returned document SHALL parse as OKF with a non-empty `type` and SHALL include a
  `# Citations` section when the concept has provenance

#### Scenario: Import requires elevated scope
- **WHEN** a client without `memory:admin` calls `import_bundle`
- **THEN** the server SHALL reject the call and SHALL NOT ingest the bundle

### Requirement: Writes resolve to git
Episodic writes (`remember`) SHALL be accepted into Postgres immediately, while corrections and
promotions that become canonical knowledge SHALL be realized as commits to the git repository
via consolidation. The wiki resource MAY be pinned to a commit SHA for reproducible reads.

#### Scenario: A correction becomes canonical via a commit
- **WHEN** a correction is accepted and later promoted
- **THEN** its canonical form SHALL appear as a git commit, not solely as a mutable database row
