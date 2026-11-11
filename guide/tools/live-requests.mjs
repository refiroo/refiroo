#!/usr/bin/env node
// Runs the documentation's example requests against the reference instance (guide/reference) and keeps the
// real responses in guide/_coverage/live/<name>.json, so pages can be checked against what the engine answers.
// Usage: node guide/tools/live-requests.mjs [--file C12.requests.json] [--only a,b] [--list] [--allow-writes]
// The file is guide/_waves/<FILE>: { "requests": [ { "name", "auth": "consumer"|"admin"|"none", "method",
//   "path", "query"?: {..}, "headers"?: {..}, "body"?: any, "expectStatus"?: 404, "write"?: true, "note"? } ] }
// Auth (credentials in guide/reference/.env, never printed):
//   consumer  OAuth client credentials (GUIDE_CONSUMER_CLIENT_ID / _SECRET) at POST /oauth/token, scope consumer.
//   admin     the management API takes a bearer token; a person gets one only through the sign-in, so this signs
//             in as GUIDE_ADMIN_EMAIL / GUIDE_ADMIN_PASSWORD as the browser does (POST /oauth/sign-in/password,
//             then the authorization-code exchange with PKCE for client "browser"). No client is created.
//   none      no Authorization header.
// Tokens are reused for the run (and renewed once on a 401).
// Safety: only GET and HEAD, and POST to paths that only read (consumer resolve/xref, paths ending in
// lookup, preview, dry-run or validate), run. Anything else needs "write": true and is only printed and skipped
// unless --allow-writes is given.
// Output per request: method, url, status, the headers that matter (ETag, Content-Type, Location, Retry-After,
// rdm-* and signature headers ...) and the body (JSON parsed, else text; cut at 200 KB).
// A summary line per request ("ok 200 name", "FAIL 404 name - message"); exit 1 if any failed unexpectedly.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';

const GUIDE = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const OUT = path.join(GUIDE, '_coverage', 'live');
const MAX = 200 * 1024;

const args = process.argv.slice(2);
const opt = (k) => { const i = args.indexOf(`--${k}`); return i < 0 ? null : args[i + 1] ?? true; };
const file = path.resolve(path.join(GUIDE, '_waves'), opt('file') || 'C12.requests.json');
const only = opt('only') ? String(opt('only')).split(',') : null;
const spec = JSON.parse(fs.readFileSync(file, 'utf8'));
const requests = spec.requests.filter((r) => !only || only.includes(r.name));
if (args.includes('--list')) { for (const r of spec.requests) console.log(`${r.name}\t${r.auth ?? 'none'}\t${r.method ?? 'GET'} ${r.path}${r.write ? '\t(write)' : ''}`); process.exit(0); }

const env = Object.fromEntries(fs.readFileSync(path.join(GUIDE, 'reference', '.env'), 'utf8').split('\n')
  .filter((l) => l.includes('=') && !l.startsWith('#')).map((l) => [l.slice(0, l.indexOf('=')), l.slice(l.indexOf('=') + 1)]));
const BASE = (spec.base || env.PUBLIC_URL || 'http://localhost:8480').replace(/\/$/, '');

const READ_POST = /\/(resolve|xref|lookup|preview|dry-run|validate)\/?$/;
const isReadOnly = (r) => {
  const m = (r.method || 'GET').toUpperCase();
  return m === 'GET' || m === 'HEAD' || (m === 'POST' && READ_POST.test(r.path.split('?')[0]));
};

const tokens = {};
async function tokenRequest(form) {
  const res = await fetch(BASE + '/oauth/token', { method: 'POST', headers: { 'content-type': 'application/x-www-form-urlencoded' }, body: new URLSearchParams(form) });
  const body = await res.json().catch(() => ({}));
  if (!res.ok || !body.access_token) throw new Error(`token request ${res.status} ${body.error ?? ''}`.trim());
  return body.access_token;
}
async function getToken(kind) {
  if (tokens[kind]) return tokens[kind];
  if (kind === 'consumer') {
    if (!env.GUIDE_CONSUMER_CLIENT_ID) throw new Error('GUIDE_CONSUMER_CLIENT_ID missing in guide/reference/.env');
    tokens[kind] = await tokenRequest({ grant_type: 'client_credentials', client_id: env.GUIDE_CONSUMER_CLIENT_ID, client_secret: env.GUIDE_CONSUMER_CLIENT_SECRET, scope: 'consumer' });
  } else if (kind === 'admin') {
    const verifier = crypto.randomBytes(48).toString('base64url');
    const redirect = BASE + '/signed-in';
    const request = {
      response_type: 'code', client_id: 'browser', redirect_uri: redirect,
      code_challenge: crypto.createHash('sha256').update(verifier).digest('base64url'),
      code_challenge_method: 'S256', state: crypto.randomBytes(12).toString('base64url'),
    };
    const res = await fetch(BASE + '/oauth/sign-in/password', {
      method: 'POST', headers: { 'content-type': 'application/json', origin: BASE },
      body: JSON.stringify({ request, email: env.GUIDE_ADMIN_EMAIL, password: env.GUIDE_ADMIN_PASSWORD }),
    });
    const out = await res.json().catch(() => ({}));
    if (res.status !== 200 || out.status !== 'signed_in') throw new Error(`admin sign-in ${res.status} ${out.error ?? out.status ?? ''}`.trim());
    const code = new URL(out.redirect).searchParams.get('code');
    tokens[kind] = await tokenRequest({ grant_type: 'authorization_code', client_id: 'browser', code, code_verifier: verifier, redirect_uri: redirect });
  } else throw new Error(`unknown auth "${kind}"`);
  return tokens[kind];
}

const KEEP = /^(etag|content-type|content-length|location|retry-after|cache-control|last-modified|link|www-authenticate|vary|deprecation|sunset|x-.*|rdm-.*|.*signature.*)$/i;

async function send(r, retry = true) {
  const url = new URL(BASE + r.path);
  for (const [k, v] of Object.entries(r.query ?? {})) url.searchParams.set(k, String(v));
  const headers = { accept: 'application/json', ...(r.headers ?? {}) };
  const auth = r.auth ?? 'none';
  if (auth !== 'none') headers.authorization = 'Bearer ' + await getToken(auth);
  const method = (r.method || 'GET').toUpperCase();
  let body;
  if (r.body !== undefined && r.body !== null && !['GET', 'HEAD'].includes(method)) { body = typeof r.body === 'string' ? r.body : JSON.stringify(r.body); if (!Object.keys(headers).some((h) => h.toLowerCase() === 'content-type')) headers['content-type'] = 'application/json'; }
  const res = await fetch(url, { method, headers, body, redirect: 'manual' });
  if (res.status === 401 && auth !== 'none' && retry) { delete tokens[auth]; return send(r, false); }
  const text = method === 'HEAD' ? '' : await res.text();
  let parsed = text, truncated = false;
  try { parsed = text ? JSON.parse(text) : ''; } catch { /* keep text */ }
  if (text.length > MAX) { truncated = true; parsed = typeof parsed === 'string' ? parsed.slice(0, MAX) : { truncated: true, note: 'JSON body over 200 KB', start: text.slice(0, MAX) }; }
  const outHeaders = {};
  res.headers.forEach((v, k) => { if (KEEP.test(k)) outHeaders[k] = v; });
  return { method, url: url.toString(), status: res.status, headers: outHeaders, ...(truncated ? { truncated: true } : {}), body: parsed };
}

fs.mkdirSync(OUT, { recursive: true });
const results = [];
for (const r of requests) {
  const label = r.name;
  try {
    if (!isReadOnly(r) && !r.write) throw new Error(`refused: ${r.method} ${r.path} is not a read; mark it "write": true`);
    if (r.write && !args.includes('--allow-writes')) { console.log(`skip ${label} - write, would run ${r.method} ${r.path} (use --allow-writes)`); continue; }
    const out = await send(r);
    out.note = r.note;
    fs.writeFileSync(path.join(OUT, `${label}.json`), JSON.stringify(out, null, 2) + '\n');
    const expected = r.expectStatus ?? null;
    const ok = expected ? out.status === expected : out.status >= 200 && out.status < 300;
    const msg = ok ? '' : (out.body?.error?.message ?? out.body?.message ?? out.body?.error ?? (expected ? `expected ${expected}` : ''));
    results.push({ name: label, ok, status: out.status, note: typeof msg === 'string' ? msg : JSON.stringify(msg) });
  } catch (e) {
    results.push({ name: label, ok: false, status: '---', note: String(e.message).split('\n')[0] });
  }
}
for (const x of results) console.log(`${x.ok ? 'ok  ' : 'FAIL'} ${x.status} ${x.name}${x.note ? ` - ${x.note}` : ''}`);
process.exit(results.every((x) => x.ok) ? 0 : 1);
