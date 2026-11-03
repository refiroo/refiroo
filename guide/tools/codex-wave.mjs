#!/usr/bin/env node
// Drives Codex (OpenAI CLI, `codex exec`) for the guide-writing waves. See CODEX_TOOL.md.
// Node only, no dependencies. Never uses --dangerously-* flags or --worktree.
import { spawn, spawnSync } from 'node:child_process';
import crypto from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const GUIDE = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const REPO = path.resolve(GUIDE, '..');
const WAVES = path.join(GUIDE, '_waves');
const RUNS = path.join(WAVES, 'runs');
// One lock per package: different waves may run side by side (each builds into _build/<PACKAGE>).
let LOCK = path.join(RUNS, '.lock');
const lockFor = (pkg) => { LOCK = path.join(RUNS, `.lock-${pkg}`); };
const LOG_CAP = 20 * 1024 * 1024;
const STDERR_CAP = 1024 * 1024;
const TAIL_LINES = 60;

// ---------------------------------------------------------------- helpers
function die(msg, code = 2) {
  console.error(`codex-wave: ${msg}`);
  process.exit(code);
}
function parseArgs(argv) {
  const pos = [];
  const opt = {};
  const valued = new Set(['model', 'run', 'codex-bin', 'timeout', 'images']);
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a.startsWith('--')) {
      const k = a.slice(2);
      if (valued.has(k)) {
        if (i + 1 >= argv.length) die(`--${k} needs a value`);
        opt[k] = argv[++i];
      } else opt[k] = true;
    } else pos.push(a);
  }
  return { pos, opt };
}
const rel = (p) => path.relative(REPO, p).split(path.sep).join('/');
const stamp = () => new Date().toISOString().replace(/[:.]/g, '-').replace(/-\d{3}Z$/, 'Z');
const readJson = (p) => JSON.parse(fs.readFileSync(p, 'utf8'));
const writeJson = (p, v) => fs.writeFileSync(p, JSON.stringify(v, null, 2) + '\n');
const fmtDur = (ms) => (ms == null ? '-' : ms < 60000 ? `${(ms / 1000).toFixed(1)}s` : `${Math.floor(ms / 60000)}m${Math.round((ms % 60000) / 1000)}s`);

function findCodex(opt) {
  const cands = [opt['codex-bin'], process.env.CODEX_BIN].filter(Boolean);
  if (cands.length) return cands[0];
  const w = spawnSync('which', ['codex'], { encoding: 'utf8' });
  if (w.status === 0 && w.stdout.trim()) return w.stdout.trim();
  const home = path.join(os.homedir(), '.local/bin/codex');
  if (fs.existsSync(home)) return home;
  die('codex not found: use --codex-bin, CODEX_BIN, put codex on PATH, or install ~/.local/bin/codex');
}
function configuredModel() {
  for (const f of [path.join(REPO, '.codex/config.toml'), path.join(os.homedir(), '.codex/config.toml')]) {
    try {
      const top = fs.readFileSync(f, 'utf8').split(/^\s*\[/m)[0];
      const m = top.match(/^\s*model\s*=\s*"([^"]+)"/m);
      if (m) return `${m[1]} (${f.replace(os.homedir(), '~')})`;
    } catch {}
  }
  return null;
}

// ---------------------------------------------------------------- wave file
function parseWave(pkg) {
  if (!/^[A-Za-z0-9_-]+$/.test(pkg || '')) die('package name must be letters, digits, _ or -');
  const file = path.join(WAVES, `${pkg}.md`);
  if (!fs.existsSync(file)) die(`no wave file ${rel(file)}`);
  const lines = fs.readFileSync(file, 'utf8').split('\n');
  let inSection = false;
  let found = false;
  const allowed = [];
  for (const line of lines) {
    const h = line.match(/^#{1,6}\s+(.*)$/);
    if (h) {
      inSection = /files you may edit/i.test(h[1]);
      if (inSection) found = true;
      continue;
    }
    if (!inSection) continue;
    const b = line.match(/^\s*[-*]\s+`([^`]+)`/);
    if (b) allowed.push(b[1].trim().replace(/^\.?\//, '').replace(/^guide\//, ''));
  }
  if (!found) die(`${rel(file)} has no "Files you may edit" heading`);
  if (!allowed.length) die(`${rel(file)}: "Files you may edit" has no bullets of the form - \`path\``);
  for (const a of allowed) if (a.startsWith('/') || a.includes('..')) die(`bad allowed path: ${a}`);
  // Optional line "Screens file: `PILOT.screens.json`" (a name in _waves/ or a path under guide/).
  let screens = null;
  for (const line of lines) {
    const m = line.match(/^\s*Screens file:\s*`([^`]+)`/i);
    if (!m) continue;
    const name = m[1].trim().replace(/^\.?\//, '').replace(/^guide\//, '');
    if (name.startsWith('/') || name.includes('..')) die(`bad screens file path: ${name}`);
    const f = [path.join(WAVES, name), path.join(GUIDE, name)].find((c) => fs.existsSync(c));
    if (!f) die(`${rel(file)}: screens file ${name} not found`);
    screens = f;
  }
  return { file, allowed, screens };
}

// ---------------------------------------------------------------- images
const SCREENS_DIR = path.join(GUIDE, 'public', 'screens');
// The wave's screens file names each screenshot (guide/tools/screens.mjs writes public/screens/<name>.png).
function screenImages(screensFile) {
  if (!screensFile) return { images: [], described: [] };
  const spec = readJson(screensFile);
  const described = spec.screens.map((s) => ({ name: s.name, shows: s.shows }));
  const images = described.map((d) => path.join(SCREENS_DIR, `${d.name}.png`));
  const missing = images.filter((f) => !fs.existsSync(f));
  if (missing.length) die(`screenshots missing (run node guide/tools/screens.mjs): ${missing.map((m) => path.basename(m)).join(', ')}`);
  return { images, described };
}
// --images: a comma-separated list of files or globs (* and ?), relative to the current directory or to guide/public/screens.
function optionImages(spec) {
  if (spec == null) return [];
  if (spec === true) die('--images needs a value: a glob or a comma-separated list');
  const out = [];
  for (const tok of String(spec).split(',').map((t) => t.trim()).filter(Boolean)) {
    const cands = [path.resolve(tok), path.resolve(SCREENS_DIR, tok)];
    let hits = [];
    for (const c of cands) {
      const dir = path.dirname(c);
      if (/[*?]/.test(path.basename(c))) {
        const re = globToRe(path.basename(c));
        if (fs.existsSync(dir)) hits = fs.readdirSync(dir).filter((n) => re.test(n)).sort().map((n) => path.join(dir, n));
      } else if (fs.existsSync(c) && fs.statSync(c).isFile()) hits = [c];
      if (hits.length) break;
    }
    if (!hits.length) die(`--images: nothing matches ${tok}`);
    out.push(...hits);
  }
  for (const f of out) if (!/\.(png|jpe?g|gif|webp)$/i.test(f)) die(`--images: not an image: ${f}`);
  return out;
}
const uniq = (a) => [...new Set(a)];
const imageRecord = (files) => files.map((f) => ({ path: rel(f), sha1: crypto.createHash('sha1').update(fs.readFileSync(f)).digest('hex') }));
function globToRe(g) {
  let re = '';
  for (let i = 0; i < g.length; i++) {
    const c = g[i];
    if (c === '*') {
      if (g[i + 1] === '*') {
        i++;
        if (g[i + 1] === '/') { i++; re += '(?:.*/)?'; } else re += '.*';
      } else re += '[^/]*';
    } else if (c === '?') re += '[^/]';
    else re += c.replace(/[.+^${}()|[\]\\]/g, '\\$&');
  }
  return new RegExp(`^${re}$`);
}
// paths are relative to guide/
const allowedMatcher = (allowed) => {
  const res = allowed.map(globToRe);
  return (p) => res.some((r) => r.test(p));
};
const toGuideRel = (repoRel) => (repoRel.startsWith('guide/') ? repoRel.slice(6) : `../${repoRel}`);

// ---------------------------------------------------------------- snapshot
function snapshot() {
  const r = spawnSync('git', ['status', '--porcelain=v1', '-z', '-uall'], { cwd: REPO, encoding: 'utf8', maxBuffer: 256 * 1024 * 1024 });
  if (r.status !== 0) die(`git status failed: ${r.stderr}`);
  const parts = r.stdout.split('\0').filter(Boolean);
  const files = {};
  for (let i = 0; i < parts.length; i++) {
    const code = parts[i].slice(0, 2);
    const p = parts[i].slice(3);
    if (code[0] === 'R' || code[0] === 'C') i++; // skip the origin path
    let h = 'deleted';
    try {
      const st = fs.statSync(path.join(REPO, p));
      h = st.isFile() ? crypto.createHash('sha1').update(fs.readFileSync(path.join(REPO, p))).digest('hex') : 'dir';
    } catch {}
    files[p] = { status: code.trim() || code, hash: h };
  }
  return { at: new Date().toISOString(), head: spawnSync('git', ['rev-parse', 'HEAD'], { cwd: REPO, encoding: 'utf8' }).stdout.trim(), files };
}
// Files whose state differs: present in either snapshot with a different hash
// (a file clean in a snapshot is absent from it; a clean-at-HEAD file that appears
// later is "modified", and one that disappears was committed or reverted).
function diffSnapshots(a, b) {
  const out = [];
  const keys = new Set([...Object.keys(a.files), ...Object.keys(b.files)]);
  for (const k of keys) {
    const x = a.files[k]?.hash;
    const y = b.files[k]?.hash;
    if (x !== y) out.push({ path: k, change: !x ? 'appeared' : !y ? 'left-the-status-list' : y === 'deleted' ? 'deleted' : 'modified' });
  }
  return out.sort((p, q) => p.path.localeCompare(q.path));
}

// ---------------------------------------------------------------- events
function parseEvents(file) {
  const info = { sessionId: null, usage: { input: 0, cachedInput: 0, output: 0, reasoning: 0, turns: 0 }, touched: new Set(), commands: [], errors: [], malformed: 0 };
  if (!fs.existsSync(file)) return info;
  for (const line of fs.readFileSync(file, 'utf8').split('\n')) {
    if (!line.startsWith('{')) continue;
    let ev;
    try { ev = JSON.parse(line); } catch { info.malformed++; continue; }
    const sid = ev.thread_id ?? ev.session_id ?? ev.msg?.session_id;
    if (!info.sessionId && sid && /^[0-9a-f-]{36}$/i.test(sid)) info.sessionId = sid;
    if (ev.type === 'turn.completed' && ev.usage) {
      info.usage.turns++;
      info.usage.input += ev.usage.input_tokens ?? 0;
      info.usage.cachedInput += ev.usage.cached_input_tokens ?? 0;
      info.usage.output += ev.usage.output_tokens ?? 0;
      info.usage.reasoning += ev.usage.reasoning_output_tokens ?? 0;
    }
    if (ev.type === 'error' || ev.type === 'turn.failed') info.errors.push(String(ev.message ?? ev.error?.message ?? 'error').slice(0, 300));
    const it = ev.item;
    if (it && ev.type === 'item.completed') {
      if (it.type === 'file_change') for (const c of it.changes ?? []) info.touched.add(path.resolve(REPO, c.path));
      if (it.type === 'command_execution') info.commands.push(String(it.command ?? ''));
    }
  }
  info.touched = [...info.touched].map((p) => rel(p));
  return info;
}

// ---------------------------------------------------------------- lock
function pidAlive(pid) {
  try { process.kill(pid, 0); return true; } catch (e) { return e.code === 'EPERM'; }
}
function acquireLock(what) {
  fs.mkdirSync(RUNS, { recursive: true });
  if (fs.existsSync(LOCK)) {
    let cur = {};
    try { cur = readJson(LOCK); } catch {}
    if (cur.pid && pidAlive(cur.pid)) die(`another codex-wave run is active (pid ${cur.pid}: ${cur.what}); refusing to start`);
    console.error(`codex-wave: removing stale lock (pid ${cur.pid} not running)`);
    fs.rmSync(LOCK, { force: true });
  }
  try {
    fs.writeFileSync(LOCK, JSON.stringify({ pid: process.pid, what, since: new Date().toISOString() }), { flag: 'wx' });
  } catch { die('lost the lock race; another run just started'); }
  const release = () => { try { if (readJson(LOCK).pid === process.pid) fs.rmSync(LOCK, { force: true }); } catch {} };
  process.on('exit', release);
  for (const s of ['SIGINT', 'SIGTERM', 'SIGHUP']) process.on(s, () => process.exit(130));
}

function releaseLockQuietly() {
  try { if (readJson(LOCK).pid === process.pid) fs.rmSync(LOCK, { force: true }); } catch {}
}

// ---------------------------------------------------------------- run folders
function listRuns(pkg) {
  const d = path.join(RUNS, pkg);
  if (!fs.existsSync(d)) return [];
  return fs.readdirSync(d).filter((n) => fs.existsSync(path.join(d, n, 'run.json'))).sort();
}
function pickRun(pkg, opt) {
  const runs = listRuns(pkg);
  if (!runs.length) die(`no runs for ${pkg}`);
  const ts = opt.run ?? runs[runs.length - 1];
  if (!runs.includes(ts)) die(`no run ${ts} for ${pkg}; have: ${runs.join(', ')}`);
  const dir = path.join(RUNS, pkg, ts);
  return { ts, dir, meta: readJson(path.join(dir, 'run.json')) };
}

// ---------------------------------------------------------------- one turn
function runTurn({ codex, dir, meta, turn, prompt, opt, resume, images = [] }) {
  const n = turn;
  const p = (s) => path.join(dir, `turn-${n}.${s}`);
  fs.writeFileSync(p('prompt.md'), prompt);
  const before = snapshot();
  writeJson(p('before.json'), before);
  const args = ['exec'];
  if (resume) args.push('resume', meta.sessionId);
  // One -i per image, before --json: -i takes a list and must not run into the prompt argument "-".
  for (const f of images) args.push('-i', f);
  args.push('--json', '-o', p('last-message.md'));
  if (resume) args.push('-c', 'sandbox_mode="workspace-write"');
  else args.push('-C', REPO, '-s', 'workspace-write');
  if (meta.model) args.push('-m', meta.model);
  args.push('-');
  const t = { n, started: new Date().toISOString(), cmd: [codex, ...args].join(' '), images: imageRecord(images) };
  fs.writeFileSync(p('images.txt'), images.map((f) => rel(f)).join('\n') + (images.length ? '\n' : ''));
  console.log(`turn ${n}: ${t.cmd}`);
  const t0 = Date.now();
  const log = fs.createWriteStream(p('events.jsonl'));
  const errLog = fs.createWriteStream(p('stderr.log'));
  let written = 0, errWritten = 0, truncated = false;
  const timeoutMs = (Number(opt.timeout) || 90) * 60000;
  return new Promise((resolve) => {
    const child = spawn(codex, args, { cwd: REPO, stdio: ['pipe', 'pipe', 'pipe'], env: process.env });
    const killer = setTimeout(() => { t.timedOut = true; child.kill('SIGTERM'); setTimeout(() => child.kill('SIGKILL'), 10000).unref(); }, timeoutMs);
    child.stdin.on('error', () => {});
    child.stdin.end(prompt);
    child.stdout.on('data', (b) => {
      if (written >= LOG_CAP) return;
      if (written + b.length > LOG_CAP) {
        log.write(b.subarray(0, LOG_CAP - written));
        log.write(`\n{"type":"codex-wave.truncated","note":"event log stopped at ${LOG_CAP} bytes"}\n`);
        written = LOG_CAP; truncated = true; return;
      }
      written += b.length; log.write(b);
    });
    child.stderr.on('data', (b) => {
      if (errWritten >= STDERR_CAP) return;
      errWritten += b.length; errLog.write(b.subarray(0, Math.max(0, STDERR_CAP - (errWritten - b.length))));
    });
    child.on('error', (e) => { t.spawnError = String(e); });
    child.on('close', (code, sig) => {
      clearTimeout(killer);
      log.end(); errLog.end();
      const after = snapshot();
      writeJson(p('after.json'), after);
      const ev = parseEvents(p('events.jsonl'));
      Object.assign(t, {
        ended: new Date().toISOString(), durationMs: Date.now() - t0, exitCode: code, signal: sig,
        usage: ev.usage, errors: ev.errors.slice(0, 5), logTruncated: truncated, touchedByCodex: ev.touched,
      });
      if (!meta.sessionId && ev.sessionId) meta.sessionId = ev.sessionId;
      meta.turns.push(t);
      writeJson(path.join(dir, 'run.json'), meta);
      const u = ev.usage;
      console.log(`turn ${n} done: exit ${code}${sig ? ` (${sig})` : ''}, ${fmtDur(t.durationMs)}, session ${meta.sessionId ?? 'NOT FOUND'}, tokens in ${u.input} (cached ${u.cachedInput}) out ${u.output} (reasoning ${u.reasoning})`);
      if (truncated) console.log('event log hit the size cap and was truncated');
      if (ev.errors.length) console.log(`errors: ${ev.errors.slice(0, 3).join(' | ')}`);
      const limit = ev.errors.find((e) => /usage limit/i.test(e));
      if (limit) {
        t.usageLimit = limit;
        writeJson(path.join(dir, 'run.json'), meta);
        console.log(`USAGE LIMIT: ${limit}`);
      }
      resolve(t);
    });
  });
}

// ---------------------------------------------------------------- commands
function buildPrompt(pkg, wave, allowed, described = []) {
  return `You are Codex, asked to write part of the refiroo guide. Your assignment is the wave file ${rel(wave)}.

1. Read guide/AGENTS.md first. It is the complete instruction set for writing guide pages and holds the writing rules and the checks. The repository's top-level AGENTS.md does not apply to this task.
2. Then read ${rel(wave)}. It names the pages you write and the report to end with.
3. Edit only the files listed under "Files you may edit" in the wave file:
${allowed.map((a) => `   - guide/${a}`).join('\n')}
   - guide/_waves/progress/${pkg}.md (your progress, see 5)
   - guide/_coverage/notes/${pkg}/ (working notes)
   Edit nothing else. Never commit, never run git commands that change state, never touch other working-tree changes.
4. Work in small units and write each finished unit into your files before starting the next, so that a stop (a usage limit, a timeout) loses at most the unit in progress. Keep working notes only under guide/_coverage/notes/${pkg}/, never in /tmp. If your files show that part of the assignment is already done (an earlier run of this wave stopped), continue from there.
5. Show your progress as you go, so the person who owns refiroo can follow and steer. After each finished unit (a page, a release, a group of rows) append to guide/_waves/progress/${pkg}.md: the time, what you finished (page path), in one or two sentences what it covers, and anything you were unsure of. Before each unit, read guide/_waves/steer/${pkg}.md if it exists: it holds corrections written while you work; follow them, from the next unit on, and say in the progress file which you applied.
6. Build with \`GUIDE_OUT=_build/${pkg} npm run build\` in guide/ (never a plain \`npm run build\`: other waves build at the same time) until it passes.
7. End with the report the wave file asks for, as your final message.
${described.length ? `
Screenshots of the reference instance are attached to this message, in this order. They show the real screens of refiroo. Reference them on the pages as ![What the screen shows](/docs/screens/<name>.png) with the name given here; their files are in guide/public/screens/.
${described.map((d, i) => `${i + 1}. ${d.name}.png: ${d.shows}`).join('\n')}
` : ''}`;
}

async function cmdRun(pkg, opt) {
  const { file, allowed: listed, screens } = parseWave(pkg);
  const allowed = uniq([...listed, `_waves/progress/${pkg}.md`, `_coverage/notes/${pkg}/**`]);
  const codex = findCodex(opt);
  const ts = stamp();
  const dir = path.join(RUNS, pkg, ts);
  const fromWave = screenImages(screens);
  const images = uniq([...fromWave.images, ...optionImages(opt.images)]);
  const prompt = buildPrompt(pkg, file, allowed, fromWave.described);
  const model = opt.model ?? null;
  const configured = configuredModel();
  if (opt['dry-run']) {
    console.log(`wave file : ${rel(file)}\nallowed   :\n${allowed.map((a) => `  guide/${a}`).join('\n')}\ncodex     : ${codex}\nmodel     : ${model ?? configured ?? 'codex default'}\nrun folder: ${rel(dir)}\nscreens   : ${screens ? rel(screens) : 'none'}\nimages    : ${images.length ? `${images.length} (sent with -i)\n${images.map((f) => `  ${rel(f)}`).join('\n')}` : 'none'}\n\n--- prompt ---\n${prompt}`);
    return 0;
  }
  lockFor(pkg);
  acquireLock(`run ${pkg}`);
  fs.mkdirSync(dir, { recursive: true });
  const version = spawnSync(codex, ['--version'], { encoding: 'utf8' }).stdout?.trim();
  const meta = { package: pkg, timestamp: ts, waveFile: rel(file), screensFile: screens ? rel(screens) : null, allowed, codex, codexVersion: version, model, configuredModel: configured, sessionId: null, turns: [], check: null };
  writeJson(path.join(dir, 'run.json'), meta);
  fs.writeFileSync(path.join(dir, 'prompt.md'), prompt);
  console.log(`run ${pkg}/${ts}; model ${model ?? configured ?? 'codex default'}`);
  const t = await runTurn({ codex, dir, meta, turn: 1, prompt, opt, resume: false, images });
  try { fs.copyFileSync(path.join(dir, 'turn-1.last-message.md'), path.join(dir, 'last-message.md')); } catch {}
  if (t.usageLimit) return 75;
  return t.exitCode === 0 ? 0 : 1;
}

// "try again at 3:59 AM" -> milliseconds until then (+2 minutes), at most 20 minutes; unknown -> 30 minutes.
function limitWaitMs(message) {
  const m = /try again at (\d{1,2}):(\d{2})\s*(AM|PM)?/i.exec(message ?? '');
  if (!m) return 30 * 60e3;
  let h = Number(m[1]) % 12;
  if (!m[3]) h = Number(m[1]);
  else if (m[3].toUpperCase() === 'PM') h += 12;
  const at = new Date();
  at.setHours(h, Number(m[2]), 0, 0);
  if (at <= new Date()) at.setDate(at.getDate() + 1);
  // Retry at least every 20 minutes: the limit can be lifted earlier (credits bought, plan changed), and a
  // run that is still limited stops at once.
  return Math.min(at - Date.now() + 2 * 60e3, 20 * 60e3);
}

// run --wait-on-limit: when Codex reports its usage limit, wait until the time it names and start the
// wave again in a fresh session (the wave continues from what its files already hold).
async function cmdRunWaiting(pkg, opt) {
  for (let attempt = 1; ; attempt++) {
    const code = await cmdRun(pkg, opt);
    releaseLockQuietly();
    if (code !== 75 || attempt >= Number(opt['max-restarts'] ?? 6)) return code;
    const { meta } = pickRun(pkg, {});
    const ms = limitWaitMs(meta.turns.at(-1)?.usageLimit);
    console.log(`waiting ${Math.round(ms / 60e3)} min for the usage limit, then a fresh run (restart ${attempt})`);
    await new Promise((r) => setTimeout(r, ms));
  }
}

async function cmdReply(pkg, msgFile, opt) {
  if (!msgFile || !fs.existsSync(msgFile)) die('reply needs an existing message file');
  const { dir, meta, ts } = pickRun(pkg, opt);
  if (!meta.sessionId) die(`run ${ts} has no session id (turn 1 never reported one); cannot resume`);
  const codex = findCodex(opt);
  lockFor(pkg);
  acquireLock(`reply ${pkg}`);
  const n = meta.turns.length + 1;
  const images = uniq(optionImages(opt.images));
  console.log(`reply to ${pkg}/${ts}, session ${meta.sessionId}${images.length ? `, ${images.length} image(s)` : ''}`);
  const t = await runTurn({ codex, dir, meta, turn: n, prompt: fs.readFileSync(msgFile, 'utf8'), opt, resume: true, images });
  try { fs.copyFileSync(path.join(dir, `turn-${n}.last-message.md`), path.join(dir, 'last-message.md')); } catch {}
  if (t.usageLimit) return 75;
  return t.exitCode === 0 ? 0 : 1;
}

function tail(s) {
  const l = s.trimEnd().split('\n');
  return l.slice(-TAIL_LINES).join('\n');
}
function sh(cmd, cwd) {
  const r = spawnSync('bash', ['-lc', cmd], { cwd, encoding: 'utf8', maxBuffer: 256 * 1024 * 1024 });
  return { ok: r.status === 0, out: `${r.stdout ?? ''}${r.stderr ?? ''}`, code: r.status };
}

function cmdCheck(pkg, opt) {
  const { dir, meta, ts } = pickRun(pkg, opt);
  if (!meta.turns.length) die(`run ${ts} has no completed turn`);
  const first = readJson(path.join(dir, 'turn-1.before.json'));
  const last = readJson(path.join(dir, `turn-${meta.turns.length}.after.json`));
  const changed = diffSnapshots(first, last);
  const touched = new Set(meta.turns.flatMap((t) => t.touchedByCodex ?? []));
  const cmds = meta.turns.flatMap((t, i) => parseEvents(path.join(dir, `turn-${i + 1}.events.jsonl`)).commands);
  const ok = allowedMatcher(meta.allowed);
  const inside = [], outside = [];
  for (const c of changed) {
    const g = toGuideRel(c.path);
    const how = touched.has(c.path) ? 'in Codex file-change events' : cmds.some((x) => x.includes(path.basename(c.path))) ? 'named in a Codex command only' : 'NOT in Codex events (probably another session)';
    (ok(g) ? inside : outside).push({ ...c, how });
  }
  const noChangeIssues = meta.turns.filter((t) => t.exitCode !== 0).map((t) => `turn ${t.n} exit code ${t.exitCode}${t.timedOut ? ' (timed out)' : ''}`);
  const missing = [];
  const lines = [`# Check: ${pkg} run ${ts}`, '', `Session ${meta.sessionId}, ${meta.turns.length} turn(s). Compared turn-1 before with turn-${meta.turns.length} after.`, ''];
  lines.push(`## Files changed inside the allowed list (${inside.length})`, ...(inside.length ? inside.map((c) => `- ${c.path} (${c.change}; ${c.how})`) : ['- none']), '');
  lines.push(`## Files changed OUTSIDE the allowed list (${outside.length})`);
  if (outside.length) {
    lines.push('Never reverted. Entries marked "NOT in Codex events" were most likely changed by another session; the others need a look.');
    lines.push(...outside.map((c) => `- ${c.path} (${c.change}; ${c.how})`));
  } else lines.push('- none');
  lines.push('');
  const codexOutside = outside.filter((c) => !c.how.startsWith('NOT'));
  for (const a of meta.allowed) {
    if (!/[*?]/.test(a) && !fs.existsSync(path.join(GUIDE, a))) missing.push(a);
  }
  lines.push(`## Allowed files that do not exist (${missing.length})`, ...(missing.length ? missing.map((m) => `- guide/${m}`) : ['- none']), '');

  const results = [];
  const run = (name, cmd, cwd) => {
    console.log(`check: ${name} ...`);
    const t0 = Date.now();
    const r = sh(cmd, cwd);
    results.push({ name, ok: r.ok, ms: Date.now() - t0 });
    lines.push(`## ${name}: ${r.ok ? 'PASS' : `FAIL (exit ${r.code})`} (${fmtDur(Date.now() - t0)})`, '```', tail(r.out), '```', '');
    console.log(`check: ${name} ${r.ok ? 'PASS' : 'FAIL'}`);
  };
  if (!opt['no-guide-checks']) {
    const out = `GUIDE_OUT=_build/${pkg}`;
    run('npm run verify', `${out} npm run verify`, GUIDE);
    run('npm run check:links', `${out} npm run check:links`, GUIDE);
  }
  const wantsDocs = opt['docs-tests'] ? true : opt['no-docs-tests'] ? false : pagesHaveExamples(inside.map((c) => c.path).concat(meta.allowed.filter((a) => !/[*?]/.test(a)).map((a) => `guide/${a}`)));
  if (wantsDocs) run('pytest -m docs', 'cd backend && .venv/bin/python -m pytest -m docs -q', REPO);
  else lines.push('## pytest -m docs: skipped (no api/model examples in the wave pages)', '');

  const failed = results.filter((r) => !r.ok).length;
  const exit = failed || outside.length || missing.length || noChangeIssues.length ? 1 : 0;
  lines.push('## Verdict', `- guide checks failed: ${failed}`, `- outside-list changes: ${outside.length} (${codexOutside.length} attributable to Codex)`, `- turn problems: ${noChangeIssues.join('; ') || 'none'}`, `- result: ${exit ? 'FAIL' : 'PASS'}`, '');
  fs.writeFileSync(path.join(dir, 'check.md'), lines.join('\n'));
  meta.check = { at: new Date().toISOString(), pass: !exit, failedChecks: failed, outside: outside.length, inside: inside.length };
  writeJson(path.join(dir, 'run.json'), meta);
  console.log(`inside: ${inside.length}, outside: ${outside.length} (${codexOutside.length} attributable to Codex), checks failed: ${failed}; ${rel(path.join(dir, 'check.md'))}`);
  for (const c of outside) console.log(`  OUTSIDE ${c.path} (${c.change}; ${c.how})`);
  return exit;
}
function pagesHaveExamples(paths) {
  for (const p of paths) {
    if (!/\.mdx?$/.test(p)) continue;
    try {
      const fm = fs.readFileSync(path.join(REPO, p), 'utf8').match(/^---\n([\s\S]*?)\n---/);
      const ex = fm?.[1].match(/^examples:\s*\[(.*)\]/m);
      if (ex && /\b(api|model)\b/.test(ex[1])) return true;
    } catch {}
  }
  return false;
}

function cmdStatus(pkg) {
  const pkgs = pkg ? [pkg] : fs.existsSync(RUNS) ? fs.readdirSync(RUNS).filter((n) => fs.statSync(path.join(RUNS, n)).isDirectory()) : [];
  let any = false;
  if (fs.existsSync(LOCK)) { try { const l = readJson(LOCK); console.log(`lock: pid ${l.pid} (${l.what}) ${pidAlive(l.pid) ? 'ACTIVE' : 'stale'}\n`); } catch {} }
  for (const k of pkgs) {
    for (const ts of listRuns(k)) {
      any = true;
      const m = readJson(path.join(RUNS, k, ts, 'run.json'));
      const sum = m.turns.reduce((a, t) => ({ i: a.i + t.usage.input, c: a.c + t.usage.cachedInput, o: a.o + t.usage.output, r: a.r + t.usage.reasoning, ms: a.ms + t.durationMs }), { i: 0, c: 0, o: 0, r: 0, ms: 0 });
      console.log(`${k}/${ts}  session ${m.sessionId ?? '-'}  model ${m.model ?? m.configuredModel ?? 'default'}`);
      console.log(`  turns ${m.turns.length}  exit [${m.turns.map((t) => t.exitCode).join(',')}]  duration ${fmtDur(sum.ms)}  tokens in ${sum.i} (cached ${sum.c}) out ${sum.o} (reasoning ${sum.r}) total ${sum.i + sum.o}`);
      console.log(`  check ${m.check ? `${m.check.pass ? 'PASS' : 'FAIL'} (inside ${m.check.inside}, outside ${m.check.outside}, failed ${m.check.failedChecks}) at ${m.check.at}` : 'not run'}`);
    }
  }
  if (!any) console.log('no runs');
  return 0;
}

// ---------------------------------------------------------------- main
const USAGE = `usage:
  codex-wave.mjs run <PACKAGE> [--wait-on-limit] [--max-restarts N] [--model M] [--images GLOB,FILE,...] [--dry-run] [--timeout MIN] [--codex-bin P]
  codex-wave.mjs check <PACKAGE> [--run TS] [--no-guide-checks] [--docs-tests|--no-docs-tests]
  codex-wave.mjs reply <PACKAGE> <message-file> [--images GLOB,FILE,...] [--run TS] [--codex-bin P]
  codex-wave.mjs status [<PACKAGE>]`;
const { pos, opt } = parseArgs(process.argv.slice(2));
const [cmd, a1, a2] = pos;
let code;
switch (cmd) {
  case 'run': code = await (opt['wait-on-limit'] ? cmdRunWaiting(a1, opt) : cmdRun(a1, opt)); break;
  case 'check': code = cmdCheck(a1, opt); break;
  case 'reply': code = await cmdReply(a1, a2, opt); break;
  case 'status': code = cmdStatus(a1); break;
  default: console.error(USAGE); code = 2;
}
process.exit(code);
