// Thin git helpers. The OKF bundle is the system of record; a memory version is
// a commit SHA. Rollback is a git operation. All commands are scoped to the
// bundle's repository root.

import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

function findRepoRoot(startDir: string): string | null {
  let dir = path.resolve(startDir);
  for (;;) {
    if (fs.existsSync(path.join(dir, ".git"))) return dir;
    const parent = path.dirname(dir);
    if (parent === dir) return null;
    dir = parent;
  }
}

export class Git {
  readonly root: string | null;
  constructor(public readonly brainDir: string) {
    this.root = findRepoRoot(brainDir);
  }

  get available(): boolean {
    return this.root !== null;
  }

  private run(args: string[]): string {
    if (!this.root) throw new Error("not a git repository");
    return execFileSync("git", args, { cwd: this.root, encoding: "utf8" }).trim();
  }

  private tryRun(args: string[]): string | null {
    try {
      return this.run(args);
    } catch {
      return null;
    }
  }

  /** Current HEAD commit SHA (the served memory version), or null. */
  headSha(): string | null {
    return this.tryRun(["rev-parse", "HEAD"]);
  }

  isDirty(): boolean {
    const out = this.tryRun(["status", "--porcelain"]);
    return out !== null && out.length > 0;
  }

  /** Stage paths (relative to repo root) and commit. Returns the new SHA. */
  commit(paths: string[], message: string): string | null {
    if (!this.root) return null;
    try {
      this.run(["add", ...paths]);
      // Nothing staged → no commit.
      const staged = this.tryRun(["diff", "--cached", "--name-only"]);
      if (!staged) return this.headSha();
      this.run(["commit", "-m", message, "--no-verify"]);
      return this.headSha();
    } catch {
      return null;
    }
  }

  /** Restore the bundle to a prior commit (rollback). Hard reset of the bundle path. */
  revertTo(sha: string, bundleRelPath: string): boolean {
    if (!this.root) return false;
    try {
      this.run(["checkout", sha, "--", bundleRelPath]);
      return true;
    } catch {
      return false;
    }
  }

  /** Read a file at a specific commit (for version-pinned retrieval). */
  showAt(sha: string, repoRelPath: string): string | null {
    return this.tryRun(["show", `${sha}:${repoRelPath}`]);
  }

  /** Relative path of the bundle inside the repo, e.g. "brain". */
  bundleRelPath(): string {
    if (!this.root) return this.brainDir;
    return path.relative(this.root, this.brainDir) || ".";
  }
}
