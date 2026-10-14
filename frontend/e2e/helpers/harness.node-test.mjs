import assert from "node:assert/strict";
import { test } from "node:test";
import { chromium } from "playwright";
import { watchPageErrors } from "./harness.mjs";

test("a run hears a page's uncaught error and a part the error boundary replaced, not other console errors", async () => {
  const browser = await chromium.launch({
    headless: true,
    ...(process.env.PLAYWRIGHT_EXECUTABLE_PATH ? { executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH } : {}),
  });
  try {
    const context = await browser.newContext();
    const heard = [];
    watchPageErrors(context, (error) => heard.push(error));
    watchPageErrors(context, (error) => heard.push(`twice: ${error}`));
    const page = await context.newPage();
    await page.setContent(`<script>
      console.error("This page stopped working:", "reading 'length'");
      console.error("a failed request the page handles");
      setTimeout(() => { throw new TypeError("Cannot read properties of undefined"); });
    </script>`);
    await page.waitForTimeout(200);
    assert.equal(heard.length, 2, heard.join("\n"));
    assert.match(heard[0], /^This page stopped working/);
    assert.match(heard[1], /Cannot read properties of undefined/);
  } finally {
    await browser.close();
  }
});
