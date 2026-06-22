# security-governance

## ADDED Requirements

### Requirement: Row-level tenant and visibility isolation
The system SHALL enforce Postgres Row-Level Security on every memory table, scoping access by
`org_id` and by `visibility` (`private`, `team`, `org`).

#### Scenario: Team memory is invisible outside the team
- **WHEN** a user who is not a member of a team requests `team`-scoped memory for that team
- **THEN** the system SHALL return no rows for it

### Requirement: Least-privilege service access
The system SHALL restrict the database service role to the background worker and SHALL forbid
request-path code from using it.

#### Scenario: Request path cannot escalate
- **WHEN** request-path code attempts a query with elevated privileges
- **THEN** the system SHALL deny it and the data SHALL remain governed by the caller's RLS
  claims

### Requirement: Right-to-be-forgotten cascade
The system SHALL support redaction that cascades across episodic, semantic, procedural, and
embedding records derived from the redacted data.

#### Scenario: Forgetting removes derivatives
- **WHEN** a redaction request completes
- **THEN** the system SHALL remove or anonymize the source episodic data and every semantic,
  procedural, and embedding record derived solely from it, and SHALL record completion

### Requirement: PII classification
The system SHALL classify extracted content for personal data and SHALL apply the configured
handling policy to classified items.

#### Scenario: Detected PII follows policy
- **WHEN** extraction detects personal data in a candidate
- **THEN** the system SHALL tag it and SHALL apply the retention and access policy for that
  classification

### Requirement: Memory-poisoning defense
The system SHALL constrain who may write `org`-scoped memory and SHALL require provenance and
grading before any cross-user promotion, to resist memory poisoning and indirect prompt
injection.

#### Scenario: Unauthorized org write is rejected
- **WHEN** a caller without `memory:admin` attempts to write `org`-scoped memory directly
- **THEN** the system SHALL reject the write and SHALL log the attempt

### Requirement: Immutable audit log
The system SHALL append an audit record for every write, redaction, and sensitive read, and
the audit log and provenance records SHALL be immutable.

#### Scenario: Audit entries cannot be altered
- **WHEN** any actor attempts to update or delete an audit or provenance row
- **THEN** the system SHALL reject the operation

### Requirement: Visibility-safe interchange
OKF export SHALL be filtered to the caller's authorization, private memory SHALL never be
serialized into a bundle shared beyond its owner, and a right-to-be-forgotten cascade SHALL
also purge derived bundle artifacts and snapshots.

#### Scenario: Redaction reaches exported artifacts
- **WHEN** a redaction completes for data that was previously exported into a bundle
- **THEN** the system SHALL remove or anonymize the corresponding concepts and citations in
  any retained bundle artifacts it controls

### Requirement: Visibility via repository routing
Canonical access control SHALL be enforced by git repository/namespace permissions per
visibility (a private namespace per user, team namespaces, an org namespace), and the derived
index SHALL additionally enforce RLS at query time. A concept SHALL be committed only to a
repository/namespace matching its visibility; the indexer SHALL tag each derived row with the
scope of the repository it came from so canonical and query-time access agree.

#### Scenario: Private knowledge is never committed to a shared repo
- **WHEN** consolidation promotes a concept whose visibility is private
- **THEN** the system SHALL commit it only to that user's private namespace and SHALL NOT place
  it in a team or org repository

### Requirement: Right-to-be-forgotten under git-canonical storage
Because the system of record is git, redaction SHALL prevent classified personal data from
being committed into bundles in the first place (such data stays in purgeable episodic state),
and where redaction of already-committed content is required, the system SHALL perform a git
history rewrite (for example via history-filtering) on the affected repository and SHALL
reindex.

#### Scenario: Forgetting committed content rewrites history
- **WHEN** a redaction targets content already committed to a bundle
- **THEN** the system SHALL rewrite the repository history to remove it and SHALL rebuild the
  derived index so the content is absent from both the record and the index
