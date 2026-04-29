/**
 * Q&A wiring. Routes to droplet API if available, falls back to direct OpenRouter.
 *
 * Two paths:
 *   1. POST /api/ask (droplet) — preferred when /api/health responds.
 *   2. Direct OpenRouter call with disposable event key + qa-context.json.
 *
 * The static site is presentation-safe regardless of droplet availability.
 */

import { loadQAContext } from './manifest.js';
import { logQuestion } from './decisions.js';

// Disposable event key. Capped at $50 in OpenRouter dashboard. Rotated post-event.
// Loaded from /env.json at runtime so it can be rotated without a rebuild.
let _eventKey = null;

const MODELS = {
  sonnet: { id: 'anthropic/claude-sonnet-4.5', label: 'Claude Sonnet 4.5', country: 'US' },
  opus:   { id: 'anthropic/claude-opus-4.1',   label: 'Claude Opus 4.1',   country: 'US' },
  cohere: { id: 'cohere/command-a',            label: 'Cohere Command A',  country: 'CA', sovereign: true },
};

const DEFAULT_MODEL = 'sonnet';

let _dropletReachable = null;

async function loadEventKey() {
  if (_eventKey !== null) return _eventKey;
  try {
    const res = await fetch('/env.json', { cache: 'no-store' });
    if (res.ok) {
      const env = await res.json();
      _eventKey = env.openrouter_key || '';
    } else {
      _eventKey = '';
    }
  } catch {
    _eventKey = '';
  }
  return _eventKey;
}

export async function checkDroplet() {
  if (_dropletReachable !== null) return _dropletReachable;
  try {
    const ctrl = new AbortController();
    setTimeout(() => ctrl.abort(), 1500);
    const res = await fetch('/api/health', { signal: ctrl.signal, cache: 'no-store' });
    _dropletReachable = res.ok;
  } catch {
    _dropletReachable = false;
  }
  return _dropletReachable;
}

export function listModels() { return MODELS; }

export function modelMeta(key) { return MODELS[key] || MODELS[DEFAULT_MODEL]; }

/**
 * Ask a question. Returns { answer, model, tokens_in, tokens_out, cost_usd, citations, refused }.
 * If onChunk is provided, streams chunks of the answer as they arrive.
 */
export async function ask({ question, scope = 'home', model = DEFAULT_MODEL, onChunk = null, decisionsSnapshot = null }) {
  if (!question || !question.trim()) {
    throw new Error('Question is empty.');
  }

  const useDroplet = await checkDroplet();
  const result = useDroplet
    ? await askDroplet({ question, scope, model, decisionsSnapshot, onChunk })
    : await askDirect({ question, scope, model, onChunk });

  // Log to judge's session
  logQuestion(
    result.model,
    question,
    result.answer,
    result.cost_usd,
    { in: result.tokens_in, out: result.tokens_out },
  );
  return result;
}

async function askDroplet({ question, scope, model, decisionsSnapshot, onChunk }) {
  const res = await fetch('/api/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, scope, model, decisions_so_far: decisionsSnapshot }),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`Droplet /api/ask failed (${res.status}): ${text}`);
  }
  const data = await res.json();
  // Non-streaming through droplet for simplicity. Stream emulation:
  if (onChunk && data.answer) onChunk(data.answer);
  return {
    answer: data.answer || '',
    model: data.model || modelMeta(model).id,
    tokens_in: data.tokens_in || 0,
    tokens_out: data.tokens_out || 0,
    cost_usd: data.cost_usd || 0,
    citations: data.citations || [],
    refused: !!data.refused,
    refusal_reason: data.refusal_reason || null,
    via: 'droplet',
  };
}

async function askDirect({ question, scope, model, onChunk }) {
  const key = await loadEventKey();
  if (!key) {
    throw new Error('Event key not configured. Q&A is offline. Backend droplet not reachable either.');
  }
  const ctx = await loadQAContext();
  const messages = buildMessages(question, scope, ctx);
  const modelId = modelMeta(model).id;

  const res = await fetch('https://openrouter.ai/api/v1/chat/completions', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${key}`,
      'HTTP-Referer': 'https://agency2026.lemonbrand.io',
      'X-Title': 'Agency 2026 LemonClaw',
    },
    body: JSON.stringify({
      model: modelId,
      messages,
      stream: !!onChunk,
      temperature: 0.2,
      max_tokens: 1200,
    }),
  });

  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    if (res.status === 401) throw new Error('Event key rejected. Try again later or ask Simon to rotate.');
    if (res.status === 429) throw new Error('Rate limited. Try again in a few seconds.');
    throw new Error(`OpenRouter error (${res.status}): ${text}`);
  }

  let answer = '';
  let usage = { in: 0, out: 0 };

  if (onChunk && res.body) {
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';
      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed.startsWith('data:')) continue;
        const payload = trimmed.slice(5).trim();
        if (payload === '[DONE]') break;
        try {
          const json = JSON.parse(payload);
          const delta = json.choices?.[0]?.delta?.content;
          if (delta) { answer += delta; onChunk(delta); }
          if (json.usage) {
            usage.in = json.usage.prompt_tokens || usage.in;
            usage.out = json.usage.completion_tokens || usage.out;
          }
        } catch { /* ignore bad chunk */ }
      }
    }
  } else {
    const data = await res.json();
    answer = data.choices?.[0]?.message?.content || '';
    usage.in = data.usage?.prompt_tokens || 0;
    usage.out = data.usage?.completion_tokens || 0;
  }

  // Best-effort cost derivation. OpenRouter posts cost in /api/v1/generation/{id} but we
  // do not block on it; estimate from list pricing.
  const cost = estimateCost(modelId, usage.in, usage.out);

  return {
    answer,
    model: modelId,
    tokens_in: usage.in,
    tokens_out: usage.out,
    cost_usd: cost,
    citations: extractCitations(answer, ctx),
    refused: detectRefusal(answer),
    refusal_reason: null,
    via: 'direct',
  };
}

function buildMessages(question, scope, ctx) {
  const sys = ctx.system_prompt || `You are the LemonClaw auditor for the Agency 2026 hackathon.
Voice: plain operator language. No em dashes (use periods or colons). No AI hype.
Cite findings by id, SHA, or source URL. Refuse to speculate past the evidence.
When you do not know, say so and name what data would change the answer.`;

  const ctxBundle = JSON.stringify({
    schema: ctx.schema,
    audit: ctx.audit,
    story_packets: ctx.story_packets,
    top_findings: ctx.top_findings,
    citations: ctx.citations,
    scope,
  }).slice(0, 240_000); // hard cap by character to dodge runaway context

  return [
    { role: 'system', content: sys },
    { role: 'system', content: `Curated evidence bundle:\n${ctxBundle}` },
    { role: 'user', content: question },
  ];
}

function estimateCost(modelId, tokensIn, tokensOut) {
  // Per-1M list rates. Direct OpenRouter pass-through pricing.
  const rates = {
    'anthropic/claude-sonnet-4.5': { in: 3.00, out: 15.00 },
    'anthropic/claude-opus-4.1':   { in: 15.00, out: 75.00 },
    'cohere/command-a':            { in: 2.50, out: 10.00 },
  };
  const r = rates[modelId] || { in: 3.00, out: 15.00 };
  return ((tokensIn * r.in) + (tokensOut * r.out)) / 1_000_000;
}

function extractCitations(text, ctx) {
  const cites = [];
  const re = /\b(F-\d+|C-\d+|A-\d+|sha[: ]+[a-f0-9]{6,12}|cite:[\w\-:]+)/gi;
  let m;
  while ((m = re.exec(text)) !== null) {
    cites.push({ ref: m[1], kind: m[1].startsWith('sha') ? 'sql' : 'finding' });
  }
  // Dedup
  const seen = new Set();
  return cites.filter(c => { if (seen.has(c.ref)) return false; seen.add(c.ref); return true; });
}

function detectRefusal(text) {
  const lower = (text || '').toLowerCase();
  return /\b(cannot answer|refuse|insufficient data|not in the (data|bundle)|external (data|source) needed)\b/.test(lower);
}
