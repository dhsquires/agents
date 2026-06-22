// Shared runtime context wiring config, the derived index, and the model gateway.

import fs from "node:fs";
import { loadConfig, type EngramConfig } from "./config.js";
import { openDb, type Db } from "./db.js";
import { makeChatModel, makeEmbeddingModel, type ChatModel, type EmbeddingModel } from "./gateway.js";
import { rebuildIndex } from "./indexer.js";

export interface Engram {
  cfg: EngramConfig;
  db: Db;
  embed: EmbeddingModel;
  chat: ChatModel;
}

export async function createEngram(autoIndex = true): Promise<Engram> {
  const cfg = loadConfig();
  const db = openDb(cfg.dbPath);
  const embed = makeEmbeddingModel(cfg);
  const chat = makeChatModel(cfg);

  // First run (or model change): build the derived index from the OKF bundle.
  const indexed = db.getMeta("indexed_at");
  const model = db.getMeta("embedding_model");
  const nodeCount = db.get<{ c: number }>("SELECT COUNT(*) AS c FROM semantic_nodes")?.c ?? 0;
  if (autoIndex && fs.existsSync(cfg.brainDir) && (!indexed || model !== embed.id || nodeCount === 0)) {
    await rebuildIndex(cfg, db, embed);
  }
  return { cfg, db, embed, chat };
}
