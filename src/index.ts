#!/usr/bin/env node
// Default entry point: run the Engram MCP server over stdio. This is what a
// coding agent spawns (see README for client config).

import { createEngram } from "./context.js";
import { runStdio } from "./server.js";

async function main(): Promise<void> {
  const engram = await createEngram(true);
  // IMPORTANT: never write logs to stdout — it is the MCP transport. Use stderr.
  process.stderr.write(
    `[engram] ready • bundle=${engram.cfg.brainDir} • db=${engram.cfg.dbPath} • embeddings=${engram.embed.id}\n`,
  );
  await runStdio(engram);
}

main().catch((err) => {
  process.stderr.write(`[engram] fatal: ${err?.stack ?? err}\n`);
  process.exit(1);
});
