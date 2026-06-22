// Open Knowledge Format (OKF v0.1) read/write.
// A concept is one markdown file with YAML frontmatter. The concept ID is the
// bundle-relative path with the `.md` suffix removed.

import fs from "node:fs";
import path from "node:path";
import YAML from "yaml";
import type { ProvenanceLink, Visibility } from "./types.js";

export const OKF_VERSION = "0.1";
export const SLUG_RE = /^[A-Za-z0-9_][A-Za-z0-9_.\-/]*$/;

export interface OkfDoc {
  frontmatter: Record<string, unknown>;
  body: string;
}

const FM_DELIM = /^---\r?\n/;

/** Parse a markdown string into frontmatter + body. Permissive: missing/invalid
 * frontmatter yields an empty object rather than throwing. */
export function parseOkf(raw: string): OkfDoc {
  if (!FM_DELIM.test(raw)) {
    return { frontmatter: {}, body: raw.trim() };
  }
  const rest = raw.replace(FM_DELIM, "");
  const end = rest.indexOf("\n---");
  if (end === -1) return { frontmatter: {}, body: raw.trim() };
  const fmText = rest.slice(0, end);
  let body = rest.slice(end + 4);
  body = body.replace(/^\r?\n/, "");
  let frontmatter: Record<string, unknown> = {};
  try {
    const parsed = YAML.parse(fmText);
    if (parsed && typeof parsed === "object") frontmatter = parsed as Record<string, unknown>;
  } catch {
    frontmatter = {};
  }
  return { frontmatter, body: body.trim() };
}

/** Serialize frontmatter + body back into an OKF markdown string. */
export function serializeOkf(doc: OkfDoc): string {
  const fm = YAML.stringify(doc.frontmatter).trimEnd();
  return `---\n${fm}\n---\n\n${doc.body.trim()}\n`;
}

/** concept id from a bundle-relative file path. */
export function conceptIdFromPath(relPath: string): string {
  return relPath.replace(/\\/g, "/").replace(/\.md$/i, "");
}

/** bundle-relative file path from a concept id. */
export function pathFromConceptId(conceptId: string): string {
  return `${conceptId}.md`;
}

export function isValidConceptId(id: string): boolean {
  return SLUG_RE.test(id);
}

/** Recursively list every `.md` concept file under a bundle, returning ids. */
export function walkBundle(brainDir: string): string[] {
  const out: string[] = [];
  function walk(dir: string) {
    let entries: fs.Dirent[] = [];
    try {
      entries = fs.readdirSync(dir, { withFileTypes: true });
    } catch {
      return;
    }
    for (const e of entries) {
      const full = path.join(dir, e.name);
      if (e.isDirectory()) {
        if (e.name === ".git" || e.name === "node_modules") continue;
        walk(full);
      } else if (e.isFile() && e.name.endsWith(".md")) {
        const rel = path.relative(brainDir, full);
        out.push(conceptIdFromPath(rel));
      }
    }
  }
  walk(brainDir);
  return out.sort();
}

export function readConcept(brainDir: string, conceptId: string): OkfDoc | null {
  const full = path.join(brainDir, pathFromConceptId(conceptId));
  if (!fs.existsSync(full)) return null;
  return parseOkf(fs.readFileSync(full, "utf8"));
}

export function writeConcept(brainDir: string, conceptId: string, doc: OkfDoc): string {
  const full = path.join(brainDir, pathFromConceptId(conceptId));
  fs.mkdirSync(path.dirname(full), { recursive: true });
  fs.writeFileSync(full, serializeOkf(doc), "utf8");
  return full;
}

/** Required OKF keys for reference-validator conformance. */
export function hasRequiredKeys(fm: Record<string, unknown>): boolean {
  return (
    typeof fm.type === "string" &&
    fm.type.length > 0 &&
    typeof fm.title === "string" &&
    typeof fm.description === "string" &&
    fm.timestamp !== undefined
  );
}

/** Render structured provenance as an OKF `# Citations` section. */
export function renderCitations(provenance: ProvenanceLink[]): string {
  if (!provenance.length) return "";
  const lines = provenance.map((p) => {
    const ref = p.source_uri
      ? p.source_uri
      : p.source_event_id
        ? `episodic:${p.source_event_id}`
        : "unknown";
    return `- ${ref} _(weight ${p.weight.toFixed(2)})_`;
  });
  return `\n\n# Citations\n\n${lines.join("\n")}\n`;
}

/** Build an OKF `index.md` listing for a directory of concepts (progressive disclosure). */
export function buildIndexDoc(
  title: string,
  description: string,
  entries: { conceptId: string; title: string; description: string }[],
  extraFrontmatter: Record<string, unknown> = {},
): OkfDoc {
  const rows = entries
    .map(
      (e) =>
        `| [${e.title}](${path.basename(e.conceptId)}.md) | ${e.description.replace(/\|/g, "\\|")} |`,
    )
    .join("\n");
  const body = `${description}\n\n| Concept | Description |\n|---|---|\n${rows}\n`;
  return {
    frontmatter: {
      type: "Index",
      title,
      description,
      timestamp: new Date().toISOString().slice(0, 10),
      ...extraFrontmatter,
    },
    body,
  };
}

export interface ConceptFrontmatter {
  type: string;
  title: string;
  description: string;
  timestamp: string;
  tags: string[];
  visibility: Visibility;
  confidence: number;
  version: number;
}

/** Normalize arbitrary OKF frontmatter into Engram's expected fields, permissively. */
export function normalizeFrontmatter(
  fm: Record<string, unknown>,
  fallbackTitle: string,
): ConceptFrontmatter {
  const tags = Array.isArray(fm.tags) ? (fm.tags as unknown[]).map(String) : [];
  const vis = (fm.engram_visibility as Visibility) ?? "private";
  return {
    type: typeof fm.type === "string" && fm.type ? fm.type : "concept",
    title: typeof fm.title === "string" && fm.title ? fm.title : fallbackTitle,
    description: typeof fm.description === "string" ? fm.description : "",
    timestamp:
      typeof fm.timestamp === "string"
        ? fm.timestamp
        : new Date().toISOString().slice(0, 10),
    tags,
    visibility: ["private", "team", "org"].includes(vis) ? vis : "private",
    confidence:
      typeof fm.engram_confidence === "number" ? (fm.engram_confidence as number) : 0.6,
    version: typeof fm.engram_version === "number" ? (fm.engram_version as number) : 1,
  };
}

/** Map an OKF `type` string to an internal node_kind (open: unknown → concept). */
export function okfTypeToNodeKind(t: string): import("./types.js").NodeKind {
  const m: Record<string, import("./types.js").NodeKind> = {
    person: "person",
    identity: "person",
    project: "project",
    goals: "project",
    connector: "connector",
    artifact: "artifact",
    playbook: "procedure",
    procedure: "procedure",
    reference: "source",
    source: "source",
    session: "session",
    task: "task",
  };
  return m[t.toLowerCase()] ?? "concept";
}
