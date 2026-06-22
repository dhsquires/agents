// OKF bundle interchange: export_bundle, import_bundle, get_index.

import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import type { EngramConfig } from "./config.js";
import type { Db } from "./db.js";
import {
  OKF_VERSION,
  walkBundle,
  readConcept,
  parseOkf,
  serializeOkf,
  buildIndexDoc,
  normalizeFrontmatter,
  renderCitations,
  conceptIdFromPath,
  type OkfDoc,
} from "./okf.js";
import type { ProvenanceLink, Visibility } from "./types.js";

function uid(p: string): string {
  return `${p}_${crypto.randomBytes(6).toString("hex")}`;
}

const VIS_RANK: Record<Visibility, number> = { org: 0, team: 1, private: 2 };

/** Export an OKF bundle filtered to a max visibility, with okf_version in root
 * index.md and rendered `# Citations` from provenance. */
export function exportBundle(
  cfg: EngramConfig,
  db: Db,
  destDir: string,
  maxVisibility: Visibility = "private",
): { files: number; dir: string } {
  fs.mkdirSync(destDir, { recursive: true });
  const ids = walkBundle(cfg.brainDir);
  const dirs = new Map<string, { conceptId: string; title: string; description: string }[]>();
  let count = 0;

  for (const id of ids) {
    const doc = readConcept(cfg.brainDir, id);
    if (!doc) continue;
    const fm = normalizeFrontmatter(doc.frontmatter, path.posix.basename(id));
    // Visibility filter: never serialize memory above the requested level.
    if (VIS_RANK[fm.visibility] > VIS_RANK[maxVisibility]) continue;

    const prov = db.all<ProvenanceLink>(
      "SELECT memory_id, memory_type, source_event_id, source_uri, weight, created_at FROM provenance WHERE memory_id = ?",
      id,
    );
    const citations = renderCitations(prov);
    const out: OkfDoc = {
      frontmatter: { ...doc.frontmatter },
      body: citations ? `${doc.body}${citations}` : doc.body,
    };
    const dest = path.join(destDir, `${id}.md`);
    fs.mkdirSync(path.dirname(dest), { recursive: true });
    fs.writeFileSync(dest, serializeOkf(out), "utf8");
    count++;

    const dir = path.posix.dirname(id);
    const list = dirs.get(dir) ?? [];
    if (path.posix.basename(id) !== "index") {
      list.push({ conceptId: id, title: fm.title, description: fm.description });
    }
    dirs.set(dir, list);
  }

  // Generate index.md per directory (progressive disclosure).
  for (const [dir, entries] of dirs) {
    if (entries.length === 0) continue;
    const idxPath = path.join(destDir, dir === "." ? "" : dir, "index.md");
    const isRoot = dir === ".";
    const idxDoc = buildIndexDoc(
      isRoot ? "Brain Bundle" : `${dir} index`,
      isRoot ? "Root index for this exported OKF brain bundle." : `Concepts under ${dir}.`,
      entries,
      isRoot ? { okf_version: OKF_VERSION } : {},
    );
    fs.mkdirSync(path.dirname(idxPath), { recursive: true });
    fs.writeFileSync(idxPath, serializeOkf(idxDoc), "utf8");
  }

  db.audit(cfg.orgId, cfg.userId, "export_bundle", destDir, maxVisibility);
  return { files: count, dir: destDir };
}

/** Import an external OKF bundle as a provenance-tagged SOURCE feeding the next
 * consolidation run (permissive; not promoted unreviewed). */
export function importBundle(cfg: EngramConfig, db: Db, srcDir: string): { ingested: number; bundle_id: string } {
  if (!fs.existsSync(srcDir)) throw new Error(`bundle not found: ${srcDir}`);
  const bundleId = uid("bundle");
  const now = new Date().toISOString();
  let ingested = 0;

  const files: string[] = [];
  const walk = (dir: string) => {
    for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
      const full = path.join(dir, e.name);
      if (e.isDirectory()) walk(full);
      else if (e.name.endsWith(".md")) files.push(full);
    }
  };
  walk(srcDir);

  // Register the bundle as a source.
  db.run(
    "INSERT INTO sources(id, org_id, uri, last_seen_at) VALUES(?,?,?,?)",
    bundleId,
    cfg.orgId,
    `bundle://${path.resolve(srcDir)}`,
    now,
  );

  for (const f of files) {
    const rel = conceptIdFromPath(path.relative(srcDir, f));
    if (path.posix.basename(rel) === "index") continue;
    const doc = parseOkf(fs.readFileSync(f, "utf8"));
    const fm = normalizeFrontmatter(doc.frontmatter, path.posix.basename(rel));
    const epId = uid("ep");
    db.run(
      `INSERT INTO episodic_events(id, org_id, user_id, session_id, task_id, kind, payload, visibility, created_at, decay_at, usefulness)
       VALUES(?,?,?,?,?,?,?,?,?,?,?)`,
      epId,
      cfg.orgId,
      cfg.userId,
      null,
      `import:${bundleId}`,
      "source_use",
      JSON.stringify({
        content: `${fm.title}\n${fm.description}\n${doc.body}`,
        metadata: { imported_concept: rel, okf_type: fm.type, bundle_id: bundleId },
        _untrusted: true,
      }),
      "private",
      now,
      now,
      0.5,
    );
    // Provenance: this candidate's source is the imported bundle.
    db.run(
      "INSERT INTO provenance(memory_id, memory_type, source_event_id, source_uri, weight, created_at) VALUES(?,?,?,?,?,?)",
      epId,
      "episodic",
      epId,
      `bundle://${path.resolve(srcDir)}/${rel}.md`,
      1.0,
      now,
    );
    ingested++;
  }

  db.audit(cfg.orgId, cfg.userId, "import_bundle", bundleId, "admin");
  return { ingested, bundle_id: bundleId };
}

/** Return an OKF index.md listing for a bundle directory (generated on the fly). */
export function getIndex(cfg: EngramConfig, db: Db, dir = ""): string {
  const norm = dir.replace(/^\/+|\/+$/g, "");
  const ids = walkBundle(cfg.brainDir).filter((id) => {
    const d = path.posix.dirname(id);
    return norm === "" ? d === "." || !d.includes("/") : d === norm;
  });
  // If a real index.md exists, prefer it.
  const existing = readConcept(cfg.brainDir, norm === "" ? "index" : `${norm}/index`);
  if (existing) return serializeOkf(existing);

  const entries = ids
    .filter((id) => path.posix.basename(id) !== "index")
    .map((id) => {
      const doc = readConcept(cfg.brainDir, id);
      const fm = normalizeFrontmatter(doc?.frontmatter ?? {}, path.posix.basename(id));
      return { conceptId: id, title: fm.title, description: fm.description };
    });
  const idx = buildIndexDoc(
    norm === "" ? "Brain Bundle" : `${norm} index`,
    norm === "" ? "Root index for this OKF brain bundle." : `Concepts under ${norm}.`,
    entries,
    norm === "" ? { okf_version: OKF_VERSION } : {},
  );
  return serializeOkf(idx);
}
