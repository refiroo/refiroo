// The guide served by the engine at /docs (0.13 DOC1), in the accessibility gate (`--only guide`):
// the first page and its search dialog, light and dark, at 1440px and 390px. The pages are the
// engine's own: the browser reaches `/docs` at the interface's address and the engine answers
// (`oneAddress`), so what runs here is what an installation serves. It needs the built guide
// (`npm run build` in `guide/`). Every request the page makes is recorded: a request to any other
// origin fails the run, since the guide must work offline.
import { bootHarness } from "./harness.mjs";
import { goDark } from "./theme.mjs";

const PAGES = [
  { name: "docs-page", path: "/docs/use/records/", heading: "Records" },
  { name: "guide-page", path: "/docs/guide/use/find-records/", heading: "Find records" },
];

/**
 * Opens each page in turn, light then dark, and calls `visit({ page, name, axe })`; `name` ends in the
 * theme (and `-phone` at 390px). Resolves with the origins every request went to.
 */
export async function visitGuideSurfaces(visit) {
  const harness = await bootHarness({ oneAddress: true });
  const { browser, uiUrl } = harness;
  const origins = new Set();
  let requests = 0;
  try {
    for (const phone of [false, true]) {
      const context = await browser.newContext({
        viewport: phone ? { width: 390, height: 844 } : { width: 1440, height: 900 },
      });
      const page = await context.newPage();
      page.setDefaultTimeout(15000);
      page.on("request", (request) => {
        if (request.url().startsWith("data:") || request.url().startsWith("blob:")) return;
        requests += 1;
        origins.add(new URL(request.url()).origin);
      });
      try {
        for (const { name, path, heading } of PAGES) {
          // The previous page ended dark from the device; each page starts light (HD: the theme follows the device).
          await page.emulateMedia({ colorScheme: "light" });
          const response = await page.goto(`${uiUrl}${path}`, { waitUntil: "networkidle" });
          if (!response?.ok()) throw new Error(`${path}: ${response?.status()}`);
          await page.getByRole("heading", { level: 1, name: heading }).waitFor();
          const suffix = phone ? "-phone" : "";
          await visit({ page, name: `${name}-light${suffix}`, axe: true });
          // The search dialog opens from the top bar, or from the menu on a phone.
          await page.getByRole("button", { name: "Search" }).first().click();
          await page.locator("dialog[open] input").first().waitFor();
          await page.locator("dialog[open] input").first().fill("change set");
          await page.locator("dialog[open] a").first().waitFor();
          await visit({ page, name: `${name}-search-light${suffix}`, axe: true });
          await page.keyboard.press("Escape");
          await goDark(page);
          await visit({ page, name: `${name}-dark${suffix}`, axe: true });
        }
      } finally {
        await context.close();
      }
    }
    return { origins: [...origins], requests, uiOrigin: new URL(uiUrl).origin };
  } finally {
    harness.cleanup();
  }
}
