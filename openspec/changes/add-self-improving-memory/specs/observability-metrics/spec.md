# observability-metrics

## ADDED Requirements

### Requirement: KPI tracking
The system SHALL track answer correctness on previously seen tasks, recall, cost per
historical-context task, turns per task, model calls per task, retrieval precision@k,
provenance coverage, and contradiction rate.

#### Scenario: Metrics persist per run
- **WHEN** a consolidation run finishes
- **THEN** the system SHALL persist its KPI values linked to the run id

### Requirement: Provenance coverage guarantee
The system SHALL report provenance coverage and SHALL treat any coverage below 100% for
promoted memory as a defect.

#### Scenario: Coverage gap is flagged
- **WHEN** provenance coverage for promoted memory drops below 100%
- **THEN** the system SHALL raise an alert identifying the unprovenanced memory

### Requirement: Run reports
The system SHALL produce a per-run report (candidates, promoted, quarantined, rolled-back,
cost) and SHALL surface it in the Console.

#### Scenario: Operator reviews a run
- **WHEN** an operator opens a completed run in the Console
- **THEN** the system SHALL show counts, KPI deltas, cost, and any rollback with its reason

### Requirement: Operational alerting
The system SHALL alert on eval-gate failure, cost-cap trips, and contradiction-rate spikes.

#### Scenario: Gate failure pages operators
- **WHEN** the eval gate fails and a batch is rolled back
- **THEN** the system SHALL emit an alert containing the run id and the regressed metric

### Requirement: Interchange conformance
The system SHALL verify that exported bundles pass OKF conformance (including the reference
validator's required keys) and SHALL track round-trip fidelity across export then re-import.

#### Scenario: Non-conformant export is flagged
- **WHEN** an exported bundle fails OKF conformance
- **THEN** the system SHALL raise a defect identifying the offending concept

### Requirement: Index freshness and rebuild fidelity
The system SHALL track index freshness (lag between a canonical commit and its appearance in
the derived index) and SHALL verify rebuild fidelity (a freshly rebuilt index matches the
bundles at the same commit). Provenance SHALL include the commit SHA a concept was served from.

#### Scenario: Stale index is flagged
- **WHEN** index lag exceeds its configured threshold after a commit
- **THEN** the system SHALL raise an alert identifying the unindexed commit
