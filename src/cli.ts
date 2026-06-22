#!/usr/bin/env node
// Engram CLI — manage the local brain without an MCP client.
//   engram doctor                  check environment + bundle health
//   engram index                   rebuild the derived index from the OKF bundle
//   engram search "<query>"        hybrid search
//   engram pack "<task>" [budget]  assemble a context pack
//   engram remember "<text>" [--task ID] [--kind K]
//   engram consolidate [--dry-run] run the self-improvement pipeline
//   engram export <dir> [--vis V]  export an OKF bundle
//   engram import <dir>            import an external OKF bundle
//   engram serve                   run the MCP server over stdio

import fs from "node:fs";
import { createEngram } from "./context.js";
import { rebuildIndex } from "./indexer.js";
import { search, getContextPack } from "./retrieval.js";
import { remember, recordOutcome, correct } from "./memory.js";
import { exportBundle, importBundle } from "./bundle.js";
import { consolidate } from "./consolidation.js";
import { runStdio } from "./server.js";
import { walkBundle } from "./okf.js";
import { Git } from "./git.js";

function flag(args: string[], name: string): string | undefined {
  const i = args.indexOf(name);
  return i !== -1 ? args[i + 1] : undefined;
}
function has(args: string[], name: string): boolean {
  return args.includes(name);
}
function out(obj: unknown): void {
  console.log(typeof obj === "string" ? obj : JSON.stringify(obj, null, 2));
}

async function main(): Promise<void> {
  const [cmd, ...args] = process.argv.slice(2);

  if (!cmd || cmd === "help" || cmd === "--help" || cmd === "-h") {
    out(
      [
        "engram <command>",
        "  doctor                          check environment + bundle health",
        "  index                           rebuild the derived index from the OKF bundle",
        "  search \"<query>\" [--limit N]   hybrid lexical+vector+graph search",
        "  pack \"<task>\" [budget]         assemble a token-budgeted context pack",
        "  remember \"<text>\" [--task ID] [--kind K]",
        "  outcome <task> <success|failure|partial> [--summary S]",
        "  correct <target> \"<text>\" [--reason R]",
        "  consolidate [--dry-run] [--no-commit]",
        "  export <dir> [--vis private|team|org]",
        "  import <dir>",
        "  serve                           run the MCP server (stdio)",
      ].join("\n"),
    );
    return;
  }

  if (cmd === "serve") {
    const engram = await createEngram(true);
    process.stderr.write(`[engram] serving over stdio • bundle=${engram.cfg.brainDir}\n`);
    await runStdio(engram);
    return;
  }

  const engram = await createEngram(cmd !== "index");
  const { cfg, db, embed, chat } = engram;

  switch (cmd) {
    case "doctor": {
      const git = new Git(cfg.brainDir);
      const concepts = fs.existsSync(cfg.brainDir) ? walkBundle(cfg.brainDir).length : 0;
      const nodes = db.get<{ c: number }>("SELECT COUNT(*) AS c FROM semantic_nodes")?.c ?? 0;
      const edges = db.get<{ c: number }>("SELECT COUNT(*) AS c FROM semantic_edges")?.c ?? 0;
      const episodic = db.get<{ c: number }>("SELECT COUNT(*) AS c FROM episodic_events")?.c ?? 0;
      out({
        node_version: process.version,
        bundle_dir: cfg.brainDir,
        bundle_exists: fs.existsSync(cfg.brainDir),
        db_path: cfg.dbPath,
        git_repo: git.available,
        memory_version: db.getMeta("memory_version"),
        embedding_model: embed.id,
        chat_model: chat.id,
        counts: { concepts, indexed_nodes: nodes, edges, episodic },
        ok: fs.existsSync(cfg.brainDir) && nodes > 0,
      });
      break;
    }
    case "index": {
      const r = await rebuildIndex(cfg, db, embed);
      out({ reindexed: r, memory_version: db.getMeta("memory_version") });
      break;
    }
    case "search": {
      const query = args[0] ?? "";
      const limit = Number(flag(args, "--limit") ?? 10);
      const res = await search(cfg, db, embed, query, { limit });
      out(res.map((r) => ({ concept_id: r.concept_id, title: r.title, score: Number(r.score.toFixed(4)), via: r.via })));
      break;
    }
    case "pack": {
      const task = args[0] ?? "";
      const budget = Number(args[1] ?? cfg.defaultTokenBudget);
      const pack = await getContextPack(cfg, db, embed, task, Number.isFinite(budget) ? budget : cfg.defaultTokenBudget);
      out(pack);
      break;
    }
    case "remember": {
      out(remember(cfg, db, { content: args[0] ?? "", task_id: flag(args, "--task"), kind: flag(args, "--kind") as any }));
      break;
    }
    case "outcome": {
      out(recordOutcome(cfg, db, { task_id: args[0], status: args[1] as any, summary: flag(args, "--summary") }));
      break;
    }
    case "correct": {
      out(correct(cfg, db, { target: args[0], correction: args[1] ?? "", reason: flag(args, "--reason") }));
      break;
    }
    case "consolidate": {
      const report = await consolidate(cfg, db, embed, chat, { dryRun: has(args, "--dry-run"), noCommit: has(args, "--no-commit") });
      out(report);
      break;
    }
    case "export": {
      out(exportBundle(cfg, db, args[0], (flag(args, "--vis") as any) ?? "private"));
      break;
    }
    case "import": {
      out(importBundle(cfg, db, args[0]));
      break;
    }
    default:
      out(`unknown command: ${cmd} (try 'engram help')`);
      process.exitCode = 1;
  }
  db.close();
}

main().catch((err) => {
  process.stderr.write(`[engram] error: ${err?.stack ?? err}\n`);
  process.exit(1);
});
