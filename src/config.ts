// Configuration resolved from environment variables with sensible local defaults.
// Engram is local-first: everything works offline with zero API keys.

import path from "node:path";
import os from "node:os";
import fs from "node:fs";

export interface EngramConfig {
  /** Root of the git-versioned OKF bundle (the system of record). */
  brainDir: string;
  /** Path to the derived SQLite index (rebuildable from brainDir). */
  dbPath: string;
  /** Logical tenant. Local installs use a single org/user. */
  orgId: string;
  userId: string;
  /** Recency decay half-life in days. */
  halfLifeDays: number;
  /** Default token budget for context packs. */
  defaultTokenBudget: number;
  /** Episodic time-to-live in days before it is eligible for decay. */
  episodicTtlDays: number;
  /** Usefulness threshold below which decayed episodic memory is forgotten. */
  forgetThreshold: number;
  /** Embedding model config (provider-agnostic gateway). */
  embeddings: {
    provider: "local" | "openai";
    model: string;
    dim: number;
    baseUrl?: string;
    apiKey?: string;
  };
  /** Chat model config used by consolidation extract/grade steps. */
  chat: {
    provider: "heuristic" | "openai" | "anthropic";
    model: string;
    baseUrl?: string;
    apiKey?: string;
  };
  /** Per-run token cost cap for consolidation. */
  runTokenCap: number;
  /** Eval-gate regression thresholds (max allowed drop, fraction). */
  evalThresholds: { correctness: number; recall: number; cost: number };
}

function firstExisting(...candidates: string[]): string | null {
  for (const c of candidates) {
    try {
      if (fs.existsSync(c)) return c;
    } catch {
      /* ignore */
    }
  }
  return null;
}

/** Resolve the brain bundle directory: env override → repo ./brain → ~/.engram/brain. */
function resolveBrainDir(): string {
  if (process.env.ENGRAM_BRAIN_DIR) {
    return path.resolve(process.env.ENGRAM_BRAIN_DIR);
  }
  // When installed/run from this repo, the bundle ships alongside the code.
  const here = path.dirname(new URL(import.meta.url).pathname);
  const repoBrain = path.resolve(here, "..", "brain");
  const cwdBrain = path.resolve(process.cwd(), "brain");
  const found = firstExisting(cwdBrain, repoBrain);
  if (found) return found;
  // Fallback to a user-local bundle.
  return path.join(os.homedir(), ".engram", "brain");
}

export function loadConfig(): EngramConfig {
  const brainDir = resolveBrainDir();
  const dbPath =
    process.env.ENGRAM_DB_PATH ??
    path.join(os.homedir(), ".engram", "engram.sqlite");

  return {
    brainDir,
    dbPath,
    orgId: process.env.ENGRAM_ORG_ID ?? "local",
    userId: process.env.ENGRAM_USER_ID ?? "me",
    halfLifeDays: numEnv("ENGRAM_HALF_LIFE_DAYS", 60),
    defaultTokenBudget: numEnv("ENGRAM_TOKEN_BUDGET", 2000),
    episodicTtlDays: numEnv("ENGRAM_EPISODIC_TTL_DAYS", 90),
    forgetThreshold: numEnv("ENGRAM_FORGET_THRESHOLD", 0.15),
    embeddings: {
      provider: (process.env.ENGRAM_EMBEDDINGS_PROVIDER as "local" | "openai") ?? "local",
      model: process.env.ENGRAM_EMBEDDINGS_MODEL ?? "local-hashed-256",
      dim: numEnv("ENGRAM_EMBEDDINGS_DIM", 256),
      baseUrl: process.env.ENGRAM_EMBEDDINGS_BASE_URL,
      apiKey: process.env.ENGRAM_EMBEDDINGS_API_KEY ?? process.env.OPENAI_API_KEY,
    },
    chat: {
      provider:
        (process.env.ENGRAM_CHAT_PROVIDER as "heuristic" | "openai" | "anthropic") ??
        "heuristic",
      model: process.env.ENGRAM_CHAT_MODEL ?? "heuristic-extractor",
      baseUrl: process.env.ENGRAM_CHAT_BASE_URL,
      apiKey: process.env.ENGRAM_CHAT_API_KEY ?? process.env.OPENAI_API_KEY,
    },
    runTokenCap: numEnv("ENGRAM_RUN_TOKEN_CAP", 200000),
    evalThresholds: {
      correctness: numEnv("ENGRAM_EVAL_MAX_DROP_CORRECTNESS", 0.0),
      recall: numEnv("ENGRAM_EVAL_MAX_DROP_RECALL", 0.0),
      cost: numEnv("ENGRAM_EVAL_MAX_INCREASE_COST", 0.25),
    },
  };
}

function numEnv(key: string, fallback: number): number {
  const v = process.env[key];
  if (v === undefined) return fallback;
  const n = Number(v);
  return Number.isFinite(n) ? n : fallback;
}

export function ensureDir(p: string): void {
  fs.mkdirSync(p, { recursive: true });
}
