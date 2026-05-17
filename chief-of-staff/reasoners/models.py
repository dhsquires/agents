"""Pydantic schemas for every reasoner in the system.

Every .ai() gate carries a `confident: bool`. Every structured output is flat
(≤4 attributes where possible). Lists of nested structures are kept shallow.
"""
from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field


# ---- Intake ----

Intent = Literal["new_idea", "status_check", "modify", "knowledge_update", "strategic"]


class IntentClassification(BaseModel):
    intent: Intent
    rationale: str
    confident: bool


class EntityExtraction(BaseModel):
    initiative_refs: list[str] = Field(default_factory=list)
    project_refs: list[str] = Field(default_factory=list)
    issue_refs: list[str] = Field(default_factory=list)
    people_or_team_refs: list[str] = Field(default_factory=list)
    confident: bool = True


# ---- Context ----

class KnowledgeHit(BaseModel):
    ref_id: str
    topic: str
    excerpt: str


class KnowledgeRetrieval(BaseModel):
    hits: list[KnowledgeHit] = Field(default_factory=list)
    confident: bool = True


class TeamOwnership(BaseModel):
    team: str
    owns: str
    rationale: str


class TeamTopology(BaseModel):
    ownerships: list[TeamOwnership] = Field(default_factory=list)
    confident: bool = True


# ---- Initiative planning (new_idea) ----

class InitiativeScope(BaseModel):
    name: str
    one_paragraph_scope: str
    success_criteria: list[str]
    confident: bool


class ProjectSpec(BaseModel):
    name: str
    scope: str
    sequence_hint: int = 1


class ProjectDecomposition(BaseModel):
    projects: list[ProjectSpec] = Field(default_factory=list)
    confident: bool = True


class IssueSpec(BaseModel):
    title: str
    scope: str


class IssueDraftPlan(BaseModel):
    issues: list[IssueSpec] = Field(default_factory=list)
    confident: bool = True


class IssueBody(BaseModel):
    title: str
    description: str
    labels: list[str] = Field(default_factory=list)
    confident: bool = True


class OwnerSuggestion(BaseModel):
    team_or_person: str
    rationale: str
    confident: bool = True


class DraftedIssue(BaseModel):
    title: str
    description: str
    labels: list[str]
    owner_suggestion: str
    owner_rationale: str


class DependencyEdge(BaseModel):
    from_issue_title: str
    to_issue_title: str
    rationale: str


class DependencyPlan(BaseModel):
    edges: list[DependencyEdge] = Field(default_factory=list)
    confident: bool = True


class Risk(BaseModel):
    risk: str
    severity: Literal["low", "medium", "high"]
    mitigation: str


class RiskAnalysis(BaseModel):
    risks: list[Risk] = Field(default_factory=list)
    confident: bool = True


class PlannedProject(BaseModel):
    name: str
    scope: str
    sequence_hint: int
    drafted_issues: list[DraftedIssue]
    dependencies: list[DependencyEdge]


class InitiativePlan(BaseModel):
    initiative_name: str
    one_paragraph_scope: str
    success_criteria: list[str]
    planned_projects: list[PlannedProject]
    risks: list[Risk]
    citations: list[str] = Field(default_factory=list)


# ---- Status ----

class VelocityJudgment(BaseModel):
    trend: Literal["accelerating", "steady", "slowing", "stalled", "unknown"]
    rationale: str
    confident: bool


class Blocker(BaseModel):
    issue_ref: str
    summary: str
    severity: Literal["low", "medium", "high"]


class BlockerScan(BaseModel):
    blockers: list[Blocker] = Field(default_factory=list)
    confident: bool = True


class InitiativeProgress(BaseModel):
    initiative_ref: str
    name: str
    percent_complete: int = Field(ge=0, le=100)
    velocity_trend: str
    velocity_rationale: str
    blockers: list[Blocker]
    citations: list[str] = Field(default_factory=list)


class StatusSynthesis(BaseModel):
    initiatives: list[InitiativeProgress]
    narrative: str
    citations: list[str] = Field(default_factory=list)


# ---- Change ----

class ImpactedEntity(BaseModel):
    entity_kind: Literal["initiative", "project", "issue"]
    entity_ref: str
    rationale: str


class ImpactScope(BaseModel):
    impacted_entities: list[ImpactedEntity] = Field(default_factory=list)
    confident: bool = True


class FieldChange(BaseModel):
    field: str
    from_value: str
    to_value: str


class UpdateSpec(BaseModel):
    entity_kind: Literal["initiative", "project", "issue"]
    entity_ref: str
    field_changes: list[FieldChange] = Field(default_factory=list)
    rationale: str
    confident: bool = True


class ChangePlan(BaseModel):
    updates: list[UpdateSpec]
    summary: str
    citations: list[str] = Field(default_factory=list)


# ---- Knowledge ----

class ConflictCheck(BaseModel):
    conflicts_with_ref_ids: list[str] = Field(default_factory=list)
    rationale: str
    confident: bool = True


class CanonicalTopic(BaseModel):
    topic: str
    rationale: str
    confident: bool


class CanonicalNote(BaseModel):
    topic: str
    body: str
    references: list[str] = Field(default_factory=list)
    confident: bool


class KnowledgeUpdate(BaseModel):
    note: CanonicalNote
    conflicts: list[str]
    citations: list[str] = Field(default_factory=list)


# ---- Strategy ----

class Stakeholder(BaseModel):
    team_or_person: str
    interest: str


class StakeholderMap(BaseModel):
    stakeholders: list[Stakeholder] = Field(default_factory=list)
    confident: bool = True


class AlignmentCheck(BaseModel):
    stakeholder: str
    alignment: Literal["aligned", "partial", "misaligned", "unknown"]
    gap: str
    confident: bool


class CommunicationDraft(BaseModel):
    audience: str
    medium: str
    message: str


class CommunicationDrafts(BaseModel):
    drafts: list[CommunicationDraft] = Field(default_factory=list)
    confident: bool = True


class StrategicPlan(BaseModel):
    stakeholders: list[Stakeholder]
    alignment_checks: list[AlignmentCheck]
    communications: list[CommunicationDraft]
    follow_on_initiative: InitiativePlan | None = None
    citations: list[str] = Field(default_factory=list)


# ---- Final response ----

class HumanResponse(BaseModel):
    headline: str
    summary: str
    actions_taken: list[str]
    proposed_next_steps: list[str]
    citations: list[str] = Field(default_factory=list)
    confident: bool = True
