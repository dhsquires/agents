// Provider-agnostic model gateway (ADR-6). Default implementations are fully
// local so Engram works offline with no API keys; remote providers are opt-in
// via environment variables.

import crypto from "node:crypto";
import type { EngramConfig } from "./config.js";

export interface EmbeddingModel {
  readonly dim: number;
  readonly id: string;
  embed(texts: string[]): Promise<number[][]>;
}

export interface ChatModel {
  readonly id: string;
  /** Returns text completion + an approximate token count for cost accounting. */
  complete(prompt: string, system?: string): Promise<{ text: string; tokens: number }>;
}

const TOKEN_RE = /[a-z0-9]+/g;

export function tokenize(text: string): string[] {
  return (text.toLowerCase().match(TOKEN_RE) ?? []).filter((t) => t.length > 1);
}

export function approxTokens(text: string): number {
  return Math.ceil(text.length / 4);
}

/** Deterministic, dependency-free hashed bag-of-words embedding. Captures lexical
 * overlap well enough for a personal-scale brain and requires no network. */
export class LocalHashedEmbedding implements EmbeddingModel {
  readonly dim: number;
  readonly id: string;
  constructor(dim: number) {
    this.dim = dim;
    this.id = `local-hashed-${dim}`;
  }
  private hash(token: string): number {
    const h = crypto.createHash("md5").update(token).digest();
    return ((h[0] << 24) | (h[1] << 16) | (h[2] << 8) | h[3]) >>> 0;
  }
  private one(text: string): number[] {
    const vec = new Array<number>(this.dim).fill(0);
    const toks = tokenize(text);
    const tf = new Map<string, number>();
    for (const t of toks) tf.set(t, (tf.get(t) ?? 0) + 1);
    for (const [t, count] of tf) {
      const idx = this.hash(t) % this.dim;
      const sign = (this.hash(t + "#") & 1) === 0 ? 1 : -1;
      vec[idx] += sign * (1 + Math.log(count));
    }
    // L2 normalize.
    let norm = 0;
    for (const v of vec) norm += v * v;
    norm = Math.sqrt(norm) || 1;
    return vec.map((v) => v / norm);
  }
  async embed(texts: string[]): Promise<number[][]> {
    return texts.map((t) => this.one(t));
  }
}

/** OpenAI-compatible embeddings endpoint (also works with local gateways that
 * implement the same shape). */
class OpenAIEmbedding implements EmbeddingModel {
  readonly dim: number;
  readonly id: string;
  constructor(
    private model: string,
    dim: number,
    private baseUrl: string,
    private apiKey: string,
  ) {
    this.dim = dim;
    this.id = `openai:${model}`;
  }
  async embed(texts: string[]): Promise<number[][]> {
    const res = await fetch(`${this.baseUrl.replace(/\/$/, "")}/embeddings`, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        authorization: `Bearer ${this.apiKey}`,
      },
      body: JSON.stringify({ model: this.model, input: texts }),
    });
    if (!res.ok) throw new Error(`embeddings provider error ${res.status}: ${await res.text()}`);
    const json = (await res.json()) as { data: { embedding: number[] }[] };
    return json.data.map((d) => d.embedding);
  }
}

export function makeEmbeddingModel(cfg: EngramConfig): EmbeddingModel {
  if (cfg.embeddings.provider === "openai" && cfg.embeddings.apiKey) {
    return new OpenAIEmbedding(
      cfg.embeddings.model,
      cfg.embeddings.dim,
      cfg.embeddings.baseUrl ?? "https://api.openai.com/v1",
      cfg.embeddings.apiKey,
    );
  }
  return new LocalHashedEmbedding(cfg.embeddings.dim);
}

/** Heuristic chat model: no network, deterministic. Consolidation uses the
 * ChatModel only as an optional refiner; the pipeline's extraction is
 * heuristic-first so it always works offline. */
class HeuristicChat implements ChatModel {
  readonly id = "heuristic-extractor";
  async complete(prompt: string): Promise<{ text: string; tokens: number }> {
    return { text: "", tokens: approxTokens(prompt) };
  }
}

class OpenAIChat implements ChatModel {
  readonly id: string;
  constructor(
    private model: string,
    private baseUrl: string,
    private apiKey: string,
  ) {
    this.id = `openai:${model}`;
  }
  async complete(prompt: string, system?: string): Promise<{ text: string; tokens: number }> {
    const res = await fetch(`${this.baseUrl.replace(/\/$/, "")}/chat/completions`, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        authorization: `Bearer ${this.apiKey}`,
      },
      body: JSON.stringify({
        model: this.model,
        messages: [
          ...(system ? [{ role: "system", content: system }] : []),
          { role: "user", content: prompt },
        ],
      }),
    });
    if (!res.ok) throw new Error(`chat provider error ${res.status}: ${await res.text()}`);
    const json = (await res.json()) as {
      choices: { message: { content: string } }[];
      usage?: { total_tokens?: number };
    };
    return {
      text: json.choices[0]?.message?.content ?? "",
      tokens: json.usage?.total_tokens ?? approxTokens(prompt),
    };
  }
}

export function makeChatModel(cfg: EngramConfig): ChatModel {
  if (cfg.chat.provider === "openai" && cfg.chat.apiKey) {
    return new OpenAIChat(
      cfg.chat.model,
      cfg.chat.baseUrl ?? "https://api.openai.com/v1",
      cfg.chat.apiKey,
    );
  }
  return new HeuristicChat();
}

export function cosine(a: number[], b: number[]): number {
  let dot = 0;
  const n = Math.min(a.length, b.length);
  for (let i = 0; i < n; i++) dot += a[i] * b[i];
  return dot; // inputs are L2-normalized
}
