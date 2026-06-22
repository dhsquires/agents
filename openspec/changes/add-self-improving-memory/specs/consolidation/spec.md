# consolidation

## ADDED Requirements

### Requirement: Scheduled durable consolidation
The system SHALL run a scheduled consolidation pipeline on an external durable worker that
fans out per `(org_id, user_id)` and executes idempotent, retryable steps: collect, extract,
resolve, reflect/grade, update, eval-gate, emit.

#### Scenario: Partial failure resumes safely
- **WHEN** a consolidation step fails mid-run
- **THEN** the orchestrator SHALL retry from the failed step using its idempotency key
  without duplicating already-committed work

### Requirement: Reflection and contradiction quarantine
The system SHALL grade every candidate for confidence and value and SHALL detect
contradictions with existing memory. Contradicted candidates SHALL be quarantined for human
review and SHALL NOT silently overwrite existing memory.

#### Scenario: Contradiction is quarantined
- **WHEN** a candidate contradicts a current semantic node
- **THEN** the system SHALL place it in a review queue, SHALL leave the existing memory
  intact, and SHALL surface it in the Console

### Requirement: Eval gate
The system SHALL evaluate each consolidation batch against a held-out task set and synthetic
probes and SHALL compute correctness, recall, and cost deltas before the batch goes live.

#### Scenario: Regression blocks promotion
- **WHEN** any guarded metric regresses beyond its configured threshold
- **THEN** the system SHALL NOT promote the batch and SHALL trigger rollback

### Requirement: Versioned rollback
The system SHALL version memory per run and SHALL be able to restore the prior memory version
atomically.

#### Scenario: Failed gate rolls back
- **WHEN** the eval gate fails for a run
- **THEN** the system SHALL restore `memory_version_before`, SHALL mark the run
  `rolled_back`, and SHALL alert operators

### Requirement: Cost caps
The system SHALL enforce a per-run token/cost cap.

#### Scenario: Cost cap halts a run
- **WHEN** a run's accumulated token cost reaches its cap
- **THEN** the system SHALL stop further model calls, SHALL mark the run `capped`, and SHALL
  preserve any safely committed work

### Requirement: Untrusted content handling
The consolidation pipeline SHALL treat all ingested session, document, and connector content
as data and SHALL NOT execute instructions found within it.

#### Scenario: Embedded instruction is ignored
- **WHEN** ingested content contains text that resembles instructions to the agent
- **THEN** the pipeline SHALL process it only as data for extraction and SHALL NOT act on it

### Requirement: OKF emission and ingestion
The update step SHALL write promoted semantic and procedural memory in OKF form and the emit
step SHALL maintain the scope's `log.md`. The collect step SHALL accept imported OKF bundles
as a source feeding extraction.

#### Scenario: Promotion produces OKF and a log entry
- **WHEN** a run promotes a batch
- **THEN** the affected concepts SHALL be written as OKF documents and the scope's `log.md`
  SHALL record the change with an ISO 8601 dated entry

### Requirement: Commit-and-reindex pipeline
After the eval gate passes, the update step SHALL write OKF files and **commit them to the
canonical git repository**, the emit step SHALL commit the updated `log.md`, and the system
SHALL then **reindex** the derived store from the new commit. The eval gate SHALL run against a
candidate commit or branch before it is merged to the canonical branch.

#### Scenario: Promotion lands as a commit and a reindex
- **WHEN** a run passes the eval gate
- **THEN** the promoted concepts SHALL be committed to git and the derived index SHALL be
  rebuilt from that commit before the version is served

### Requirement: Rollback is a git operation
A memory version SHALL be a commit SHA, and rollback SHALL restore the prior commit (via revert
or reset to `memory_version_before`) and reindex.

#### Scenario: Failed gate reverts the commit
- **WHEN** the eval gate fails for a candidate commit
- **THEN** the system SHALL NOT merge it to the canonical branch (or SHALL revert it) and the
  served version SHALL remain the prior commit SHA
