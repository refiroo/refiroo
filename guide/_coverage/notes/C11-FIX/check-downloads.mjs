import { chromium } from '../../../../frontend/node_modules/playwright/index.mjs';
import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import assert from 'node:assert/strict';

const root = resolve(import.meta.dirname, '../../..');
const built = resolve(root, '_build/C11-FIX');
const csp = "default-src 'none'; script-src 'self' 'unsafe-inline' 'wasm-unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; manifest-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'self'; form-action 'none'";
const browser = await chromium.launch({ executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: true });
try {
  const context = await browser.newContext({ acceptDownloads: true });
  await context.route('**/*', async route => {
    const url = new URL(route.request().url());
    if (url.hostname !== 'guide.test') return route.abort();
    let path = url.pathname.replace(/^\/docs\//, '');
    if (path.endsWith('/')) path += 'index.html';
    const target = resolve(built, path);
    if (!target.startsWith(built + '/')) return route.abort();
    try {
      const body = await readFile(target);
      return route.fulfill({ status: 200, body, headers: {
        'Content-Type': target.endsWith('.html') ? 'text/html' : target.endsWith('.js') ? 'text/javascript' : target.endsWith('.css') ? 'text/css' : 'application/octet-stream',
        'Content-Security-Policy': csp,
      } });
    } catch { return route.abort(); }
  });
  const page = await context.newPage();
  for (const [slug, file, source] of [
    ['start-a-draft-from-a-workbook', 'Haltestellen_Busbetrieb_Nord.xlsx', 'samples/Haltestellen_Busbetrieb_Nord.xlsx'],
    ['propose-again-with-a-newer-workbook', 'Haltestellen_Busbetrieb_Nord_next.xlsx', '_coverage/notes/C10-SCREENS/Haltestellen_Busbetrieb_Nord_next.xlsx'],
  ]) {
    await page.goto(`http://guide.test/docs/guide/model/${slug}/`);
    const pending = page.waitForEvent('download', { timeout: 10000 });
    await page.locator(`a[download="${file}"]`).click();
    const download = await pending;
    assert.equal(download.suggestedFilename(), file);
    const chunks = [];
    for await (const chunk of await download.createReadStream()) chunks.push(chunk);
    const bytes = Buffer.concat(chunks);
    assert.deepEqual(bytes, await readFile(resolve(root, source)));
    console.log(`PASS: ${slug}: download ${file}, ${bytes.length} bytes match original, production guide CSP applied.`);
  }
  await context.close();
} finally { await browser.close(); }
