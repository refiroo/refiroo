#!/usr/bin/env node
// Captures the guide's screenshots from the reference instance (guide/reference). See _waves/*.screens.json.
// Usage: node guide/tools/screens.mjs [--file PILOT.screens.json] [--only a,b] [--list]
// Reuses the Playwright installed in frontend/ (no second framework). Signs in through the engine's own
// sign-in form as the reference administrator (GUIDE_ADMIN_USERNAME / GUIDE_ADMIN_PASSWORD in
// guide/reference/.env). A screen with "as": "<role>" signs in with GUIDE_<ROLE>_USERNAME / GUIDE_<ROLE>_PASSWORD
// instead ("approver", "contributor", ...); one session per role is reused. Light theme; 1440 px wide unless a screen names another width.
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const GUIDE = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const REPO = path.resolve(GUIDE, '..');
const OUT = path.join(GUIDE, 'public', 'screens');
const { chromium } = createRequire(path.join(REPO, 'frontend', 'package.json'))('playwright');

const args = process.argv.slice(2);
const opt = (k) => { const i = args.indexOf(`--${k}`); return i < 0 ? null : args[i + 1] ?? true; };
const file = path.resolve(path.join(GUIDE, '_waves'), opt('file') || 'PILOT.screens.json');
const only = opt('only') ? String(opt('only')).split(',') : null;
const spec = JSON.parse(fs.readFileSync(file, 'utf8'));
const screens = spec.screens.filter((s) => !only || only.includes(s.name));
if (args.includes('--list')) { for (const s of spec.screens) console.log(`${s.name}\t${s.width ?? 1440}\t${s.shows}`); process.exit(0); }

const env = Object.fromEntries(fs.readFileSync(path.join(GUIDE, 'reference', '.env'), 'utf8').split('\n')
  .filter((l) => l.includes('=') && !l.startsWith('#')).map((l) => [l.slice(0, l.indexOf('=')), l.slice(l.indexOf('=') + 1)]));
const BASE = spec.base || env.PUBLIC_URL || 'http://localhost:8480';

// Locator spec: {role,name,exact} | {text,exact} | {label} | {placeholder} | {css}; "in" scopes it; "nth" picks one.
function locate(page, s) {
  let root = s.in ? locate(page, s.in) : page;
  let l;
  if (s.role) l = root.getByRole(s.role, { name: s.name, exact: s.exact });
  else if (s.text) l = root.getByText(s.text, { exact: s.exact });
  else if (s.label) l = root.getByLabel(s.label, { exact: s.exact });
  else if (s.placeholder) l = root.getByPlaceholder(s.placeholder);
  else if (s.css) l = root.locator(s.css);
  else throw new Error(`bad locator ${JSON.stringify(s)}`);
  return s.nth != null ? l.nth(s.nth) : l.first();
}

async function newSession(browser, width, height, who = 'ADMIN') {
  const context = await browser.newContext({ viewport: { width, height: height ?? (width < 600 ? 844 : 900) }, colorScheme: 'light', locale: 'en-US' });
  const page = await context.newPage();
  page.setDefaultTimeout(15000);
  await page.goto(BASE + '/');
  await page.getByLabel('Username').fill(env[`GUIDE_${who}_USERNAME`]);
  await page.getByLabel('Password').fill(env[`GUIDE_${who}_PASSWORD`]);
  await page.getByRole('button', { name: 'Sign in' }).click();
  // Signed in once the form is gone: a person with one workspace may land elsewhere than the workspace list.
  await page.getByLabel('Password').waitFor({ state: 'detached' });
  await page.waitForTimeout(1500);
  return { context, page };
}

async function act(page, a) {
  if (a.goto) await page.goto(BASE + a.goto);
  else if (a.click) await locate(page, a.click).click(a.modifiers ? { modifiers: a.modifiers } : {});
  else if (a.rightClick) await locate(page, a.rightClick).click({ button: 'right' });
  else if (a.hover) await locate(page, a.hover).hover();
  else if (a.drag) await locate(page, a.drag).dragTo(locate(page, a.to));
  else if (a.check) await locate(page, a.check).check();
  else if (a.fill) await locate(page, a.fill).fill(a.value);
  else if (a.focusedFill != null) await page.locator('input:focus').fill(a.focusedFill);
  else if (a.select) await locate(page, a.select).selectOption({ label: a.value });
  else if (a.upload) await locate(page, a.upload).setInputFiles(path.resolve(REPO, a.value)); // a file chooser; value is a path from the repo root
  else if (a.press) await page.keyboard.press(a.press);
  else if (a.waitFor) await locate(page, a.waitFor).waitFor();
  else if (a.scrollTo) {
    await locate(page, a.scrollTo).evaluate((e, off) => { e.scrollIntoView({ block: 'start' }); window.scrollBy(0, -(off ?? 0)); }, a.offset ?? 90);
  } else if (a.scrollEnd) await locate(page, a.scrollEnd).evaluate((e) => e.scrollIntoView({ block: 'end' }));
  else if (a.wait) await page.waitForTimeout(a.wait);
  else throw new Error(`bad action ${JSON.stringify(a)}`);
}

fs.mkdirSync(OUT, { recursive: true });
const browser = await chromium.launch();
const sessions = {};
const results = [];
try {
  for (const s of screens) {
    const width = s.width ?? 1440;
    const key = (id) => `${id}:${width}:${s.height ?? ''}:${s.as ?? ''}`;
    const get = async (id = 'a') => (sessions[key(id)] ??= await newSession(browser, width, s.height, (s.as || 'admin').toUpperCase()));
    try {
      const a = await get('a');
      for (const step of s.actions ?? []) {
        const who = await get(step.session ?? 'a');
        try { await act(who.page, step); } catch (e) { throw new Error(`step ${JSON.stringify(step)}: ${e.message.split('\n')[0]}`); }
        if (!step.wait && !step.waitFor) await who.page.waitForTimeout(step.settle ?? 400);
      }
      await a.page.mouse.move(width - 5, 5); // no hover state on the picture
      await a.page.waitForTimeout(700);
      const missing = [];
      for (const t of s.expect ?? []) {
        const l = a.page.getByText(t, { exact: false }).filter({ visible: true });
        if (!(await l.count().catch(() => 0))) missing.push(t);
      }
      await a.page.screenshot({ path: path.join(OUT, `${s.name}.png`) });
      for (const step of s.after ?? []) { const who = await get(step.session ?? 'a'); await act(who.page, step); await who.page.waitForTimeout(step.settle ?? 400); }
      results.push({ name: s.name, ok: !missing.length, note: missing.length ? `not visible: ${missing.join(' | ')}` : '' });
    } catch (e) {
      results.push({ name: s.name, ok: false, note: String(e.message).split('\n')[0] });
    }
  }
} finally {
  await browser.close();
}
for (const r of results) console.log(`${r.ok ? 'ok  ' : 'FAIL'} ${r.name}${r.note ? ` - ${r.note}` : ''}`);
process.exit(results.every((r) => r.ok) ? 0 : 1);
