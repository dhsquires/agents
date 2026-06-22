// End-to-end smoke tests for Engram. Run after `npm run build`.
// Exercises: OKF round-trip, indexing, hybrid retrieval, the write→consolidate
// →eval-gate→promote loop, contradiction quarantine, and bundle export/import.

import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "engram-test-"));
const brainSrc = path.resolve("brain");
const brainDir = path.join(tmp, "brain");
fs.cpSync(brainSrc, brainDir, { recursive: true });

process.env.ENGRAM_BRAIN_DIR = brainDir;
process.env.ENGRAM_DB_PATH = path.join(tmp, "engram.sqlite");

const okf = await import("../dist/okf.js");
const { createEngram } = await import("../dist/context.js");
const { search, getContextPack } = await import("../dist/retrieval.js");
const { remember, recordOutcome, correct, forget, trace } = await import("../dist/memory.js");
const { consolidate } = await import("../dist/consolidation.js");
const { exportBundle, importBundle } = await import("../dist/bundle.js");

test("OKF parse/serialize round-trips frontmatter + body", () => {
  const doc = { frontmatter: { type: "Playbook", title: "X", description: "d", timestamp: "2026-06-22", tags: ["a"] }, body: "# Hello\n\nbody" };
  const round = okf.parseOkf(okf.serializeOkf(doc));
  assert.equal(round.frontmatter.type, "Playbook");
  assert.equal(round.frontmatter.title, "X");
  assert.ok(round.body.includes("Hello"));
});

test("concept id <-> path and required keys", () => {
  assert.equal(okf.conceptIdFromPath("core/identity.md"), "core/identity");
  assert.equal(okf.pathFromConceptId("core/identity"), "core/identity.md");
  assert.ok(okf.hasRequiredKeys({ type: "X", title: "t", description: "d", timestamp: "2026-06-22" }));
  assert.ok(!okf.hasRequiredKeys({ title: "t" }));
});

test("index builds and hybrid search returns provenance-tagged items", async () => {
  const e = await createEngram(true);
  const nodes = e.db.get("SELECT COUNT(*) AS c FROM semantic_nodes").c;
  assert.ok(nodes >= 20, `expected indexed concepts, got ${nodes}`);
  const res = await search(e.cfg, e.db, e.embed, "how should AI talk to me about work", { limit: 5 });
  assert.ok(res.length > 0);
  assert.ok(res[0].via.length > 0);
  e.db.close();
});

test("context pack never exceeds its token budget", async () => {
  const e = await createEngram(false);
  const budget = 300;
  const pack = await getContextPack(e.cfg, e.db, e.embed, "values and goals", budget);
  assert.ok(pack.tokens_used <= budget, `used ${pack.tokens_used} > ${budget}`);
  e.db.close();
});

test("write→consolidate promotes a provenanced procedure and passes the eval gate", async () => {
  const e = await createEngram(false);
  remember(e.cfg, e.db, { content: "Use ripgrep, not grep, on big repos", task_id: "search-codebase" });
  remember(e.cfg, e.db, { content: "find -name was a dead end", task_id: "search-codebase" });
  recordOutcome(e.cfg, e.db, { task_id: "search-codebase", status: "success", summary: "ripgrep won" });
  const report = await consolidate(e.cfg, e.db, e.embed, e.chat, { noCommit: true });
  assert.equal(report.status, "promoted");
  assert.equal(report.metrics.provenance_coverage, 1);
  assert.ok(fs.existsSync(path.join(brainDir, "procedures", "search-codebase.md")));
  // promoted concept must have traceable provenance
  const tr = trace(e.cfg, e.db, "procedures/search-codebase");
  assert.ok(tr.provenance.length > 0, "promoted memory must carry provenance");
  e.db.close();
});

test("contradictory correction is quarantined, not silently applied", async () => {
  const e = await createEngram(false);
  correct(e.cfg, e.db, { target: "core/values", correction: "Actually that is wrong, I value pragmatism" });
  const report = await consolidate(e.cfg, e.db, e.embed, e.chat, { noCommit: true });
  assert.ok(report.quarantined >= 1, "contradiction should be quarantined");
  const q = e.db.get("SELECT COUNT(*) AS c FROM quarantine WHERE status='pending'").c;
  assert.ok(q >= 1);
  e.db.close();
});

test("export produces an OKF bundle with okf_version; import ingests as a source", async () => {
  const e = await createEngram(false);
  const dest = path.join(tmp, "exported");
  const r = exportBundle(e.cfg, e.db, dest, "private");
  assert.ok(r.files >= 20);
  const root = okf.parseOkf(fs.readFileSync(path.join(dest, "index.md"), "utf8"));
  assert.equal(String(root.frontmatter.okf_version), "0.1");
  const imp = importBundle(e.cfg, e.db, dest);
  assert.ok(imp.ingested > 0);
  e.db.close();
});

test("forget cascades over episodic memory", async () => {
  const e = await createEngram(false);
  remember(e.cfg, e.db, { content: "secret token ABC123", task_id: "secret-task" });
  const r = forget(e.cfg, e.db, { selector: { task_id: "secret-task" }, reason: "test rtbf" });
  assert.ok(r.removed_episodic >= 1);
  const left = e.db.get("SELECT COUNT(*) AS c FROM episodic_events WHERE task_id='secret-task' AND redacted=0").c;
  assert.equal(left, 0);
  e.db.close();
});

test("audit log is append-only (immutable)", async () => {
  const e = await createEngram(false);
  e.db.audit("local", "me", "test", "t");
  assert.throws(() => e.db.run("UPDATE audit_log SET action='x'"), /append-only/);
  e.db.close();
});
