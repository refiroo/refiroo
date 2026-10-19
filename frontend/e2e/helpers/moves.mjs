// The copy and move editor as the runners read it (0.11 X4, X5): the dry run shown, its figures
// once they have settled, and the mapping's version. Shared by `workspace-x4` and `workspace-x5`.
import { execFileSync } from "node:child_process";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..", "..", "..");

/** Run Python in the backend's environment and read the JSON it prints. */
export function python(code) {
  return JSON.parse(
    execFileSync(resolve(root, "backend/.venv/bin/python"), ["-c", code], { cwd: resolve(root, "backend") }).toString(),
  );
}

export function moveEditor(page) {
  const jobInAddress = () => new URL(page.url()).searchParams.get("job");

  /**
   * The figures of the dry run of the shown state, once it has finished. After a step, `after` names
   * the run shown before it, so the figures read are the next run's.
   */
  async function settledFigures(after, timeout = 60_000) {
    if (after !== undefined)
      await page.waitForFunction(
        (previous) => new URL(window.location.href).searchParams.get("job") !== previous,
        after,
        { timeout },
      );
    await page.locator('section.move-figures[aria-busy="false"]').waitFor({ timeout });
    await page.waitForFunction(() => document.querySelector(".move-figure-number")?.textContent?.trim() !== "…", null, {
      timeout,
    });
    const values = {};
    for (const figure of await page.locator(".move-figure").all()) {
      const label = (await figure.locator(".muted").first().textContent()).trim();
      const value = (await figure.locator(".move-figure-number").textContent()).trim();
      values[label] = Number(value.replaceAll(",", ""));
    }
    return values;
  }

  const mappingVersion = async () => {
    const text = await page.locator(".move-head-mapping").textContent();
    return Number(/version (\d+)/.exec(text)[1]);
  };

  return { jobInAddress, settledFigures, mappingVersion };
}
