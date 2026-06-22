// Derived index over the OKF bundle, plus the Postgres-only runtime state
// (episodic events, runs, audit). Backed by Node's built-in SQLite so the whole
// thing installs anywhere with zero native compilation.
//
// This SQLite database is a DERIVED, REBUILDABLE index: it can be dropped and
// reconstructed from the git-versioned OKF bundle at any commit (see indexer.ts).

// @ts-ignore - node:sqlite is a built-in (experimental) module; types may lag.
import { DatabaseSync } from "node:sqlite";
import fs from "node:fs";
import path from "node:path";

const SCHEMA = `
CREATE TABLE IF NOT EXISTS meta (
  key TEXT PRIMARY KEY,
  value TEXT
);

CREATE TABLE IF NOT EXISTS episodic_events (
  id TEXT PRIMARY KEY,
  org_id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  session_id TEXT,
  task_id TEXT,
  kind TEXT NOT NULL,
  payload TEXT NOT NULL,
  visibility TEXT NOT NULL DEFAULT 'private',
  created_at TEXT NOT NULL,
  decay_at TEXT NOT NULL,
  usefulness REAL NOT NULL DEFAULT 0.5,
  consolidated INTEGER NOT NULL DEFAULT 0,
  redacted INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_episodic_task ON episodic_events(task_id);
CREATE INDEX IF NOT EXISTS idx_episodic_scope ON episodic_events(org_id, user_id, visibility);

CREATE TABLE IF NOT EXISTS semantic_nodes (
  id TEXT PRIMARY KEY,            -- concept id == bundle path minus .md
  org_id TEXT NOT NULL,
  node_kind TEXT NOT NULL,
  okf_type TEXT NOT NULL,
  title TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  body_md TEXT NOT NULL DEFAULT '',
  visibility TEXT NOT NULL DEFAULT 'private',
  version INTEGER NOT NULL DEFAULT 1,
  superseded_by TEXT,
  confidence REAL NOT NULL DEFAULT 0.6,
  tags TEXT NOT NULL DEFAULT '[]',
  source_path TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_nodes_scope ON semantic_nodes(org_id, visibility);
CREATE INDEX IF NOT EXISTS idx_nodes_kind ON semantic_nodes(node_kind);

CREATE TABLE IF NOT EXISTS semantic_edges (
  id TEXT PRIMARY KEY,
  org_id TEXT NOT NULL,
  src_id TEXT NOT NULL,
  dst_id TEXT NOT NULL,
  edge_kind TEXT NOT NULL,
  confidence REAL NOT NULL DEFAULT 0.6,
  usefulness REAL NOT NULL DEFAULT 0.5,
  recency REAL NOT NULL DEFAULT 1.0,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_edges_src ON semantic_edges(src_id);
CREATE INDEX IF NOT EXISTS idx_edges_dst ON semantic_edges(dst_id);

CREATE TABLE IF NOT EXISTS embeddings (
  owner_id TEXT NOT NULL,
  owner_type TEXT NOT NULL,       -- node | episodic
  org_id TEXT NOT NULL,
  dim INTEGER NOT NULL,
  model TEXT NOT NULL,
  vec TEXT NOT NULL,              -- JSON array
  created_at TEXT NOT NULL,
  PRIMARY KEY (owner_id, owner_type)
);

CREATE TABLE IF NOT EXISTS provenance (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  memory_id TEXT NOT NULL,
  memory_type TEXT NOT NULL,      -- node | procedure | episodic
  source_event_id TEXT,
  source_uri TEXT,
  weight REAL NOT NULL DEFAULT 1.0,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_prov_memory ON provenance(memory_id);

CREATE TABLE IF NOT EXISTS corrections (
  id TEXT PRIMARY KEY,
  org_id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  target_id TEXT,
  target_type TEXT,
  reason TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sources (
  id TEXT PRIMARY KEY,
  org_id TEXT NOT NULL,
  uri TEXT NOT NULL,
  content_hash TEXT,
  snapshot_path TEXT,
  last_seen_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS consolidation_runs (
  id TEXT PRIMARY KEY,
  org_id TEXT NOT NULL,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  status TEXT NOT NULL,
  token_cost REAL NOT NULL DEFAULT 0,
  candidates INTEGER NOT NULL DEFAULT 0,
  promoted INTEGER NOT NULL DEFAULT 0,
  quarantined INTEGER NOT NULL DEFAULT 0,
  rolled_back INTEGER NOT NULL DEFAULT 0,
  memory_version_before TEXT,
  memory_version_after TEXT,
  notes TEXT NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS run_metrics (
  run_id TEXT NOT NULL,
  metric TEXT NOT NULL,
  value REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS quarantine (
  id TEXT PRIMARY KEY,
  org_id TEXT NOT NULL,
  run_id TEXT,
  concept_id TEXT,
  candidate TEXT NOT NULL,         -- JSON
  contradicts TEXT,
  reason TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',  -- pending | approved | rejected
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  org_id TEXT NOT NULL,
  actor TEXT NOT NULL,
  action TEXT NOT NULL,
  target TEXT,
  scope TEXT,
  at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS redactions (
  id TEXT PRIMARY KEY,
  org_id TEXT NOT NULL,
  selector TEXT NOT NULL,          -- JSON
  reason TEXT NOT NULL,
  requested_by TEXT NOT NULL,
  requested_at TEXT NOT NULL,
  completed_at TEXT
);
`;

export class Db {
  readonly raw: any;
  constructor(public readonly dbPath: string) {
    fs.mkdirSync(path.dirname(dbPath), { recursive: true });
    this.raw = new DatabaseSync(dbPath);
    this.raw.exec("PRAGMA journal_mode = WAL;");
    this.raw.exec("PRAGMA foreign_keys = ON;");
    this.raw.exec(SCHEMA);
    // Append-only enforcement for audit_log and provenance.
    this.raw.exec(`
      CREATE TRIGGER IF NOT EXISTS audit_no_update BEFORE UPDATE ON audit_log
        BEGIN SELECT RAISE(ABORT, 'audit_log is append-only'); END;
      CREATE TRIGGER IF NOT EXISTS audit_no_delete BEFORE DELETE ON audit_log
        BEGIN SELECT RAISE(ABORT, 'audit_log is append-only'); END;
    `);
  }

  exec(sql: string): void {
    this.raw.exec(sql);
  }
  run(sql: string, ...params: unknown[]): any {
    return this.raw.prepare(sql).run(...params);
  }
  get<T = any>(sql: string, ...params: unknown[]): T | undefined {
    return this.raw.prepare(sql).get(...params) as T | undefined;
  }
  all<T = any>(sql: string, ...params: unknown[]): T[] {
    return this.raw.prepare(sql).all(...params) as T[];
  }
  getMeta(key: string): string | null {
    const row = this.get<{ value: string }>("SELECT value FROM meta WHERE key = ?", key);
    return row?.value ?? null;
  }
  setMeta(key: string, value: string): void {
    this.run(
      "INSERT INTO meta(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
      key,
      value,
    );
  }
  audit(orgId: string, actor: string, action: string, target?: string, scope?: string): void {
    this.run(
      "INSERT INTO audit_log(org_id, actor, action, target, scope, at) VALUES(?,?,?,?,?,?)",
      orgId,
      actor,
      action,
      target ?? null,
      scope ?? null,
      new Date().toISOString(),
    );
  }
  close(): void {
    try {
      this.raw.close();
    } catch {
      /* ignore */
    }
  }
}

export function openDb(dbPath: string): Db {
  return new Db(dbPath);
}
