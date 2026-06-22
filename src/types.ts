// Shared types for Engram local memory.

export type Visibility = "private" | "team" | "org";

export type NodeKind =
  | "person"
  | "project"
  | "connector"
  | "artifact"
  | "concept"
  | "procedure"
  | "source"
  | "session"
  | "task";

export type EdgeKind =
  | "authored_by"
  | "part_of"
  | "derived_from"
  | "corrects"
  | "supersedes"
  | "cites"
  | "used_source"
  | "contradicts"
  | "relates_to";

export type EpisodicKind =
  | "observation"
  | "tool_call"
  | "outcome"
  | "correction"
  | "source_use";

export interface EpisodicEvent {
  id: string;
  org_id: string;
  user_id: string;
  session_id: string | null;
  task_id: string | null;
  kind: EpisodicKind;
  payload: Record<string, unknown>;
  visibility: Visibility;
  created_at: string;
  decay_at: string;
  usefulness: number;
  redacted: number;
}

export interface SemanticNode {
  id: string; // concept id == bundle path without .md
  org_id: string;
  node_kind: NodeKind;
  okf_type: string;
  title: string;
  description: string;
  body_md: string;
  visibility: Visibility;
  version: number;
  superseded_by: string | null;
  confidence: number;
  tags: string[];
  source_path: string; // path inside the bundle, e.g. core/identity.md
  created_at: string;
  updated_at: string;
}

export interface SemanticEdge {
  id: string;
  org_id: string;
  src_id: string;
  dst_id: string;
  edge_kind: EdgeKind;
  confidence: number;
  usefulness: number;
  recency: number;
  created_at: string;
}

export interface ProvenanceLink {
  memory_id: string;
  memory_type: "node" | "procedure" | "episodic";
  source_event_id: string | null;
  source_uri: string | null;
  weight: number;
  created_at: string;
}

export interface RetrievedItem {
  concept_id: string;
  title: string;
  okf_type: string;
  body_md: string;
  score: number;
  lexical: number;
  vector: number;
  graph: number;
  freshness: number;
  usefulness: number;
  visibility: Visibility;
  provenance: ProvenanceLink[];
  via: ("lexical" | "vector" | "graph")[];
}

export interface ContextPack {
  task: string;
  token_budget: number;
  tokens_used: number;
  memory_version: string | null;
  items: RetrievedItem[];
  index_first: boolean;
}

export interface RunReport {
  run_id: string;
  started_at: string;
  finished_at: string | null;
  status:
    | "running"
    | "promoted"
    | "no_changes"
    | "rolled_back"
    | "capped"
    | "failed";
  candidates: number;
  promoted: number;
  quarantined: number;
  rolled_back: boolean;
  token_cost: number;
  memory_version_before: string | null;
  memory_version_after: string | null;
  metrics: Record<string, number>;
  notes: string[];
}
