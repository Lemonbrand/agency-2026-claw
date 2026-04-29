import { createServer } from 'node:http';
import { readFileSync, existsSync, statSync } from 'node:fs';
import { join, extname, normalize } from 'node:path';
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';

const __dirname = fileURLToPath(new URL('.', import.meta.url));
const root = __dirname;
const dist = join(root, 'dist');
const publicDir = join(root, 'public');
const repoRoot = join(root, '..');
const port = Number(process.env.PORT || 4173);

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon',
  '.md': 'text/markdown; charset=utf-8',
};

const MODEL = {
  kimi: { id: 'moonshotai/kimi-k2.6', in: 0.75, out: 3.50 },
  sonnet: { id: 'anthropic/claude-sonnet-4.5', in: 3.00, out: 15.00 },
  opus: { id: 'anthropic/claude-opus-4.1', in: 15.00, out: 75.00 },
  cohere: { id: 'cohere/command-a', in: 2.50, out: 10.00 },
};

function json(res, status, payload) {
  const body = JSON.stringify(payload);
  res.writeHead(status, {
    'content-type': 'application/json; charset=utf-8',
    'content-length': String(Buffer.byteLength(body)),
    'cache-control': 'no-store',
  });
  res.end(body);
}

function loadJson(paths, fallback) {
  for (const path of paths) {
    try {
      if (existsSync(path)) return JSON.parse(readFileSync(path, 'utf8'));
    } catch {
      // Keep the demo server tolerant of partial exports.
    }
  }
  return fallback;
}

function loadData(name, fallback) {
  return loadJson([join(publicDir, 'data', name), join(dist, 'data', name)], fallback);
}

function loadEnvValue(key) {
  if (process.env[key]) return process.env[key];
  const envPath = join(repoRoot, '.env');
  if (!existsSync(envPath)) return '';
  for (const line of readFileSync(envPath, 'utf8').split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#') || !trimmed.includes('=')) continue;
    const [name, ...rest] = trimmed.split('=');
    if (name === key) return rest.join('=').trim().replace(/^["']|["']$/g, '');
  }
  return '';
}

function loadOpenRouterKey() {
  const env = process.env.OPENROUTER_API_KEY || process.env.OPENROUTER_KEY;
  if (env) return env;
  const local = loadJson([join(publicDir, 'env.local.json'), join(dist, 'env.local.json')], {});
  return local.openrouter_key || '';
}

function sha(sql) {
  return createHash('sha256').update(sql.trim()).digest('hex');
}

function safeSql(sql) {
  const stripped = sql.trim().replace(/;+\s*$/, '');
  const lowered = stripped.replace(/\s+/g, ' ').toLowerCase();
  if (!(lowered.startsWith('select ') || lowered.startsWith('with '))) {
    throw new Error('Only SELECT/WITH SQL is allowed.');
  }
  const forbidden = ['insert', 'update', 'delete', 'drop', 'create', 'alter', 'copy', 'truncate', 'attach', 'detach', 'install', 'load', 'call', 'pragma'];
  for (const token of forbidden) {
    if (new RegExp(`\\b${token}\\b`).test(lowered)) throw new Error(`Forbidden SQL token: ${token}`);
  }
  return stripped;
}

function pgArgs(urlText) {
  const url = new URL(urlText);
  return {
    args: ['-X', '-q', '-t', '-A', '-h', url.hostname, '-p', url.port || '5432', '-U', decodeURIComponent(url.username), '-d', url.pathname.slice(1)],
    env: { ...process.env, PGPASSWORD: decodeURIComponent(url.password || '') },
  };
}

function queryPostgres(sql, { maxRows = 8, timeoutS = 12 } = {}) {
  const url = loadEnvValue('HACKATHON_PG');
  const safe = safeSql(sql);
  if (!url) {
    return { ok: false, sql: safe, sql_hash: sha(safe), rows: [], rows_returned: 0, error: 'HACKATHON_PG is not configured.' };
  }
  const wrapped = `
SET statement_timeout = ${Math.max(1, timeoutS * 1000)};
WITH __lc_rows AS (
  SELECT * FROM (
${safe}
  ) AS __lc_inner
  LIMIT ${maxRows + 1}
)
SELECT COALESCE(json_agg(row_to_json(__lc_rows)), '[]'::json)::text
FROM __lc_rows;`.trim();
  const started = Date.now();
  const { args, env } = pgArgs(url);
  const result = spawnSync('psql', [...args, '-c', wrapped], {
    cwd: repoRoot,
    env,
    encoding: 'utf8',
    timeout: (timeoutS + 2) * 1000,
  });
  if (result.error || result.status !== 0) {
    return {
      ok: false,
      sql: safe,
      sql_hash: sha(safe),
      rows: [],
      rows_returned: 0,
      elapsed_ms: Date.now() - started,
      error: result.error?.message || result.stderr || result.stdout || 'psql failed',
    };
  }
  let rows = [];
  try {
    rows = JSON.parse((result.stdout || '[]').trim() || '[]');
  } catch (err) {
    return { ok: false, sql: safe, sql_hash: sha(safe), rows: [], rows_returned: 0, elapsed_ms: Date.now() - started, error: err.message };
  }
  const truncated = rows.length > maxRows;
  rows = rows.slice(0, maxRows);
  return { ok: true, sql: safe, sql_hash: sha(safe), rows, rows_returned: rows.length, truncated, elapsed_ms: Date.now() - started };
}

function classify(question) {
  const q = question.toLowerCase();
  if (/cra|federal|alberta|three|3|jurisdiction|levels|all three/.test(q)) return 'three_level';
  if (/vendor|concentrat|supplier|depend/.test(q)) return 'vendor_concentration';
  if (/query|sql|ran|replay/.test(q)) return 'replay_query';
  if (/refus|missing|cannot|could not|not answer/.test(q)) return 'refusals';
  if (/counter|disprov|weaken|funding.?cycle|loop/.test(q)) return 'countercheck';
  return 'strongest';
}

function sqlForIntent(intent) {
  if (intent === 'three_level') {
    return `
SELECT canonical_name, bn_root,
       COALESCE((fed_profile->>'total_grants')::numeric, 0) AS federal_total,
       COALESCE((fed_profile->>'grant_count')::numeric, 0) AS federal_grants,
       COALESCE((ab_profile->>'total_grants')::numeric, 0) AS alberta_total,
       COALESCE((ab_profile->>'payment_count')::numeric, 0) AS alberta_payments,
       source_link_count
FROM general.entity_golden_records
WHERE fed_profile IS NOT NULL
  AND ab_profile IS NOT NULL
  AND bn_root IS NOT NULL
  AND dataset_sources::text ILIKE '%cra%'
  AND dataset_sources::text ILIKE '%fed%'
  AND dataset_sources::text ILIKE '%ab%'
  AND COALESCE((fed_profile->>'total_grants')::numeric, 0) >= 10000
  AND COALESCE((ab_profile->>'total_grants')::numeric, 0) >= 10000
ORDER BY COALESCE((fed_profile->>'total_grants')::numeric, 0)
       + COALESCE((ab_profile->>'total_grants')::numeric, 0) DESC
LIMIT 8`;
  }
  if (intent === 'vendor_concentration') {
    return `
WITH spend AS (
  SELECT ministry, vendor, SUM(amount::numeric) AS vendor_total
  FROM ab.ab_sole_source
  WHERE amount IS NOT NULL
    AND vendor IS NOT NULL
    AND ministry IS NOT NULL
  GROUP BY ministry, vendor
),
totals AS (
  SELECT ministry, SUM(vendor_total) AS ministry_total, COUNT(*) AS vendor_count
  FROM spend
  GROUP BY ministry
),
ranked AS (
  SELECT spend.*, totals.ministry_total, totals.vendor_count,
         vendor_total / NULLIF(totals.ministry_total, 0) AS vendor_share,
         ROW_NUMBER() OVER (PARTITION BY spend.ministry ORDER BY vendor_total DESC) AS rn
  FROM spend
  JOIN totals USING (ministry)
)
SELECT ministry, vendor AS top_vendor, vendor_total AS top_vendor_total,
       ministry_total, vendor_count, vendor_share
FROM ranked
WHERE rn = 1
  AND ministry_total >= 100000
ORDER BY vendor_share DESC, ministry_total DESC
LIMIT 8`;
  }
  return '';
}

function challengeFromScope(scope, challenges) {
  const raw = String(scope || '').replace(/^challenge:/, '');
  if (!raw || raw === 'home') return null;
  return challenges.find(c => c.id === raw || c.slug === raw || `${c.id}-${c.slug}` === raw) || null;
}

function compactEvidence(intent, data, sqlResult, scope = 'home') {
  const findings = data.findings.findings || data.findings || [];
  const challenges = data.qa.challenges || data.challenges || [];
  const stories = data.qa.review_stories || [];
  const proofs = data.proofs || [];
  const scopedChallenge = challengeFromScope(scope, challenges);
  const selectedChallenge = scopedChallenge || (
    intent === 'three_level' ? challenges.find(c => c.id === '08a') :
    intent === 'vendor_concentration' ? challenges.find(c => c.id === '05') :
    intent === 'countercheck' ? challenges.find(c => c.id === '03') :
    null
  );
  const challengeKeys = selectedChallenge
    ? new Set([selectedChallenge.id, selectedChallenge.slug, `${selectedChallenge.id}-${selectedChallenge.slug}`].filter(Boolean))
    : null;
  const scopedFindings = challengeKeys
    ? findings.filter(f => challengeKeys.has(f.challenge_id) || challengeKeys.has(String(f.challenge_id || '').replace(/^\d+[a-z]?[-_]/, '')))
    : findings;
  const scopedProofs = challengeKeys
    ? proofs.filter(p => challengeKeys.has(p.challenge_id) || challengeKeys.has(String(p.challenge_id || '')))
    : proofs;
  const scopedStories = selectedChallenge
    ? stories.filter(s => String(s.finding_id || '').toLowerCase().includes(String(selectedChallenge.slug || selectedChallenge.id).replace(/-/g, '_').toLowerCase()))
    : stories;
  return {
    intent,
    scope,
    matching_challenge: selectedChallenge ? {
      id: selectedChallenge.id,
      title: selectedChallenge.title,
      presentation_sentence: selectedChallenge.presentation_sentence,
      hero_finding: selectedChallenge.hero_finding,
      proof_levels: selectedChallenge.proof_levels,
      roadblocks: selectedChallenge.roadblocks,
      disconfirm_check: selectedChallenge.disconfirm_check,
    } : null,
    top_findings: (scopedFindings.length ? scopedFindings : (data.qa.top_findings || findings)).slice(0, 12),
    relevant_stories: (scopedStories.length ? scopedStories : stories).slice(0, 8),
    runnable_checks: challenges.map(c => ({
      id: c.id,
      title: c.title,
      status: c.execution_status?.label,
      hero_entity: c.hero_finding?.entity,
      hero_metric: c.hero_finding?.metric,
      missing: c.roadblocks?.slice?.(0, 2) || [],
    })),
    executed_sql_probe: sqlResult && sqlResult.sql ? {
      ok: sqlResult.ok,
      sql_hash: sqlResult.sql_hash,
      rows_returned: sqlResult.rows_returned,
      elapsed_ms: sqlResult.elapsed_ms,
      rows: sqlResult.rows,
      error: sqlResult.error,
    } : null,
    proof_examples: (scopedProofs.length ? scopedProofs : proofs).slice(0, 6).map(p => ({
      challenge_id: p.challenge_id,
      probe: p.probe,
      proof_level: p.proof_level,
      sql_hash: p.sql_hash,
      row_count: p.row_count,
      tables_touched: p.tables_touched,
      preview: p.result_preview?.slice?.(0, 3) || [],
    })),
  };
}

function money(value) {
  const n = Number(value || 0);
  if (!Number.isFinite(n)) return 'not reported';
  const abs = Math.abs(n);
  if (abs >= 1_000_000_000) return `$${(n / 1_000_000_000).toFixed(1).replace(/\.0$/, '')}B`;
  if (abs >= 1_000_000) return `$${(n / 1_000_000).toFixed(1).replace(/\.0$/, '')}M`;
  if (abs >= 1_000) return `$${(n / 1_000).toFixed(1).replace(/\.0$/, '')}K`;
  return `$${n.toLocaleString('en-US', { maximumFractionDigits: 0 })}`;
}

function pct(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return 'not reported';
  return `${(n * 100).toFixed(1)}%`;
}

function deterministicAnswer({ question, evidence }) {
  const rows = evidence.executed_sql_probe?.rows || [];
  const hash = evidence.executed_sql_probe?.sql_hash || '';
  const challenge = evidence.matching_challenge;
  if (evidence.intent === 'vendor_concentration' && rows.length) {
    const multiVendor = rows.find(row => Number(row.vendor_count || 0) > 1) || rows[0];
    const singleVendor = rows.filter(row => Number(row.vendor_count || 0) === 1);
    return [
      `The strongest review lead is **${multiVendor.ministry}**.`,
      '',
      `- Top vendor: **${multiVendor.top_vendor}**`,
      `- Top vendor total: **${money(multiVendor.top_vendor_total)}**`,
      `- Ministry total in this probe: **${money(multiVendor.ministry_total)}**`,
      `- Vendor count: **${multiVendor.vendor_count}**`,
      `- Top vendor share: **${pct(multiVendor.vendor_share)}**`,
      `- Source table: \`ab.ab_sole_source\``,
      `- SQL hash: \`${hash}\``,
      '',
      singleVendor.length
        ? `The query also found ${singleVendor.length} one-vendor ministry cohort(s) at 100% concentration. Those are useful review leads, but a human should first confirm whether the ministry cohort is too narrow before treating it as dependency.`
        : 'No one-vendor cohort appeared in the preview rows.',
      '',
      'This is not a wrongdoing claim. It is a vendor-dependence review lead.'
    ].join('\n');
  }
  if (evidence.intent === 'three_level' && rows.length) {
    const row = rows.find(item => /Calgary Roman Catholic/i.test(item.canonical_name || '')) || rows[0];
    return [
      `**${row.canonical_name}** appears in CRA, federal, and Alberta-linked records.`,
      '',
      `- BN root: **${row.bn_root || 'not reported'}**`,
      `- Federal funding in the probe: **${money(row.federal_total)}** across **${row.federal_grants || 0}** grants`,
      `- Alberta funding in the probe: **${money(row.alberta_total)}** across **${row.alberta_payments || 0}** payments`,
      `- Source table: \`general.entity_golden_records\``,
      `- SQL hash: \`${hash}\``,
      '',
      'This supports a cross-jurisdiction overlap review lead. It does not prove duplication by itself; purpose and period still need review.'
    ].join('\n');
  }
  if (evidence.intent === 'replay_query') {
    const proof = evidence.proof_examples?.[0];
    if (proof) {
      return [
        `One successful source-data query was **${proof.probe}**.`,
        '',
        `- Challenge: **${proof.challenge_id}**`,
        `- Proof level: **${proof.proof_level}**`,
        `- Row count: **${proof.row_count}**`,
        `- SQL hash: \`${proof.sql_hash}\``,
        `- Tables touched: ${(proof.tables_touched || []).map(t => `\`${t}\``).join(', ') || 'not reported'}`,
        '',
        'That is the receipt: the query ran, returned rows, and has a stable hash for replay.'
      ].join('\n');
    }
  }
  if (evidence.intent === 'refusals') {
    const blocked = (evidence.runnable_checks || []).filter(item => (item.missing || []).length).slice(0, 4);
    return [
      'The system refused or constrained claims where the supplied database did not contain the needed proof.',
      '',
      ...blocked.flatMap(item => [
        `- **${item.id} ${item.title || ''}**: ${item.missing.join(' ')}`,
      ]),
      '',
      'That refusal is part of the product: missing evidence is shown instead of hidden.'
    ].join('\n');
  }
  if (evidence.intent === 'countercheck' && challenge) {
    return [
      `For **${challenge.id} ${challenge.title || 'this check'}**, the countercheck is:`,
      '',
      `- ${challenge.disconfirm_check || 'Ask what fact would weaken the review lead, then run or attach that source before escalation.'}`,
      '',
      challenge.hero_finding?.entity ? `Current hero entity: **${challenge.hero_finding.entity}**.` : '',
      challenge.hero_finding?.metric ? `Metric: **${challenge.hero_finding.metric.label}: ${challenge.hero_finding.metric.value}**.` : '',
    ].filter(Boolean).join('\n');
  }
  if (challenge?.hero_finding) {
    const hero = challenge.hero_finding;
    const metric = hero.metric;
    return [
      `For **${challenge.id} ${challenge.title || 'this check'}**, the current packet points to **${hero.entity || 'a prepared review lead'}**.`,
      '',
      hero.pattern ? `- Pattern: ${hero.pattern}` : '',
      metric ? `- Metric: **${metric.label}: ${metric.value}**` : '',
      ...(hero.bullets || []).slice(0, 4).map(item => `- ${item}`),
      challenge.execution_status?.sql_hash ? `- SQL hash: \`${challenge.execution_status.sql_hash}\`` : '',
      '',
      'This is a review lead. A human should inspect the receipt and the listed roadblocks before escalation.'
    ].filter(Boolean).join('\n');
  }
  const top = evidence.top_findings?.[0];
  if (top) {
    return [
      `The strongest prepared review lead is **${top.entity || 'the top finding'}**.`,
      '',
      `- Claim: ${top.claim || top.headline || 'not reported'}`,
      `- Finding ID: \`${top.finding_id || 'not reported'}\``,
      `- Source table: \`${top.evidence?.table || (top.source_tables || []).join(', ') || 'not reported'}\``,
      `- SQL hash: \`${top.evidence?.sql_hash || top.sha || 'not reported'}\``,
      '',
      'This is a review lead, not a final allegation.'
    ].join('\n');
  }
  return `I could not find a supported answer for: "${question}". The next step is to attach a source table or proof packet that contains the missing evidence.`;
}

async function askModel({ question, model, evidence }) {
  const key = loadOpenRouterKey();
  const meta = MODEL[model] || MODEL.kimi;
  if (!key) throw new Error('OpenRouter key is not configured.');
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 60_000);
  try {
    const response = await fetch('https://openrouter.ai/api/v1/chat/completions', {
      method: 'POST',
      signal: controller.signal,
      headers: {
        'content-type': 'application/json',
        authorization: `Bearer ${key}`,
        'HTTP-Referer': 'https://agency2026.lemonbrand.io',
        'X-Title': 'Agency 2026 LemonClaw',
      },
      body: JSON.stringify({
        model: meta.id,
        temperature: 0.15,
        max_tokens: 900,
        messages: [
          {
            role: 'system',
            content: [
              'You answer as the Agency 2026 evidence assistant.',
              'Use only the supplied evidence JSON and SQL probe rows.',
              'Do not reveal private chain of thought. It is fine to mention the public work trace: evidence loaded, SQL probed, answer assembled.',
              'Use review lead language. Do not claim fraud, illegality, corruption, intent, legal dissolution, or adverse media unless supplied evidence proves it.',
              'If the evidence contains an answer, answer directly. If not, say what source would be needed.',
              'Cite challenge IDs, finding IDs, SQL hashes, and table names when possible.',
            ].join(' '),
          },
          { role: 'system', content: `Evidence JSON:\n${JSON.stringify(evidence).slice(0, 180_000)}` },
          { role: 'user', content: question },
        ],
      }),
    });
    if (!response.ok) {
      const text = await response.text().catch(() => response.statusText);
      throw new Error(`OpenRouter ${response.status}: ${text}`);
    }
    const body = await response.json();
    const message = body.choices?.[0]?.message || {};
    const answer = typeof message.content === 'string' ? message.content : '';
    const tokensIn = body.usage?.prompt_tokens || 0;
    const tokensOut = body.usage?.completion_tokens || 0;
    const cost = ((tokensIn * meta.in) + (tokensOut * meta.out)) / 1_000_000;
    return { answer, model: meta.id, tokens_in: tokensIn, tokens_out: tokensOut, cost_usd: cost };
  } catch (err) {
    if (err.name === 'AbortError') throw new Error('Model request timed out after 60 seconds.');
    throw err;
  } finally {
    clearTimeout(timeout);
  }
}

async function handleAsk(req, res) {
  const started = Date.now();
  const trace = [];
  const add = (status, title, detail = '') => trace.push({ status, title, detail, elapsed_ms: Date.now() - started });
  let payload = '';
  req.on('data', chunk => { payload += chunk; if (payload.length > 2_000_000) req.destroy(); });
  req.on('end', async () => {
    try {
      const body = JSON.parse(payload || '{}');
      const question = String(body.question || '').trim();
      if (!question) return json(res, 400, { error: 'Question is empty.', trace });

      add('done', 'Received question', 'Classified the request and opened the evidence bundle.');
      const data = {
        qa: loadData('qa-context.json', {}),
        findings: loadData('findings-index.json', []),
        challenges: loadData('challenges.json', []),
        proofs: loadData('execution-proof.json', []),
      };
      add('done', 'Loaded exported evidence', 'Read challenges, review leads, SQL proof records, and finding summaries.');

      const intent = classify(question);
      const sql = sqlForIntent(intent);
      let sqlResult = null;
      if (sql) {
        add('active', 'Ran read-only source-data probe', 'Used Postgres with a row cap and statement timeout.');
        sqlResult = queryPostgres(sql, { maxRows: 8, timeoutS: 12 });
        trace[trace.length - 1].status = sqlResult.ok ? 'done' : 'warning';
        trace[trace.length - 1].elapsed_ms = Date.now() - started;
        trace[trace.length - 1].detail = sqlResult.ok
          ? `Returned ${sqlResult.rows_returned} preview row(s). SQL hash ${sqlResult.sql_hash.slice(0, 10)}.`
          : `Probe did not complete: ${sqlResult.error}`;
      } else {
        add('done', 'Searched prepared review leads', 'No live SQL probe was needed for this question.');
      }

      const scope = String(body.scope || 'home');
      const evidence = compactEvidence(intent, data, sqlResult, scope);
      add('done', 'Built answer packet', 'Compressed the data into citations, rows, proof levels, and roadblocks.');
      add('active', 'Asked Kimi to write the answer', 'The model receives the evidence packet, not raw unrestricted data.');
      let modelResult;
      let modelWarning = false;
      try {
        modelResult = await askModel({ question, model: body.model || 'kimi', evidence });
      } catch (err) {
        const meta = MODEL[body.model || 'kimi'] || MODEL.kimi;
        modelResult = {
          answer: deterministicAnswer({ question, evidence }),
          model: meta.id,
          tokens_in: 0,
          tokens_out: 0,
          cost_usd: 0,
        };
        modelWarning = true;
        trace[trace.length - 1].status = 'warning';
        trace[trace.length - 1].detail = `Model call did not complete: ${err.message}. Used deterministic answer from verified rows.`;
      }
      if (!modelWarning) {
        trace[trace.length - 1].status = 'done';
        trace[trace.length - 1].detail = `Returned ${modelResult.tokens_out || 0} output tokens.`;
      }
      if (!String(modelResult.answer || '').trim()) {
        trace[trace.length - 1].status = 'warning';
        trace[trace.length - 1].detail = `Model returned ${modelResult.tokens_out || 0} output tokens but no displayable answer. Used deterministic answer from verified rows.`;
        modelResult.answer = deterministicAnswer({ question, evidence });
      }
      add('done', 'Attached receipt', 'Returned model, token count, cost estimate, SQL hash, and public work trace.');

      json(res, 200, {
        ...modelResult,
        via: 'local-data-api',
        refused: /\b(do not know|cannot answer|insufficient|missing|outside source)\b/i.test(modelResult.answer),
        citations: [sqlResult?.sql_hash ? { ref: `sha ${sqlResult.sql_hash.slice(0, 12)}`, kind: 'sql' } : null].filter(Boolean),
        trace,
        evidence: {
          intent,
          sql_hash: sqlResult?.sql_hash || null,
          rows_returned: sqlResult?.rows_returned || 0,
          rows: sqlResult?.rows || [],
        },
      });
    } catch (err) {
      add('error', 'Ask failed visibly', err.message);
      json(res, 500, { error: err.message, trace });
    }
  });
}

function staticFile(req, res) {
  const url = new URL(req.url, `http://${req.headers.host}`);
  let pathname = decodeURIComponent(url.pathname);
  if (pathname === '/') pathname = '/index.html';
  if (pathname === '/env.local.json' || pathname.includes('/env.local.json') || pathname.includes('/.env')) {
    const body = 'Not found';
    res.writeHead(404, {
      'content-type': 'text/plain; charset=utf-8',
      'content-length': String(Buffer.byteLength(body)),
      'cache-control': 'no-store',
    });
    res.end(body);
    return;
  }
  const candidate = (base, path) => {
    const file = normalize(join(base, path));
    if (!file.startsWith(base) || !existsSync(file) || statSync(file).isDirectory()) return null;
    return file;
  };
  const isHtmlRoute = pathname.endsWith('.html') || !extname(pathname);
  let file = candidate(dist, pathname) || candidate(publicDir, pathname);
  if (!file && pathname.startsWith('/src/')) file = candidate(root, pathname);
  if (!file && isHtmlRoute) file = candidate(dist, '/index.html');
  if (!file) {
    const body = 'Not found';
    res.writeHead(404, {
      'content-type': 'text/plain; charset=utf-8',
      'content-length': String(Buffer.byteLength(body)),
      'cache-control': 'no-store',
    });
    res.end(body);
    return;
  }
  const body = readFileSync(file);
  const ext = extname(file);
  res.writeHead(200, {
    'content-type': MIME[ext] || 'application/octet-stream',
    'content-length': String(body.length),
  });
  res.end(body);
}

createServer((req, res) => {
  const url = new URL(req.url, `http://${req.headers.host}`);
  if (url.pathname === '/api/health') {
    return json(res, 200, { ok: true, service: 'agency-local-data-api', has_db: !!loadEnvValue('HACKATHON_PG'), has_openrouter_key: !!loadOpenRouterKey() });
  }
  if (url.pathname === '/api/ask' && req.method === 'POST') return handleAsk(req, res);
  if (url.pathname.startsWith('/api/')) return json(res, 404, { ok: false, error: 'Not found' });
  return staticFile(req, res);
}).listen(port, '0.0.0.0', () => {
  console.log(`Agency 2026 app running at http://localhost:${port}`);
});
