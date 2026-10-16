// The person at the browser in a composed runner, by keyboard alone or by clicking, and the errors
// they would see. Shared by the checkpoint runners (0.10 T1, 0.11 M6).
import assert from "node:assert/strict";

export const escape = (text) => text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

/**
 * The person at the browser, by keyboard alone or by clicking. Both modes type text with the
 * keyboard; they differ in how a control is reached and worked. Keyboard mode never clicks, fills
 * or selects programmatically: Tab reaches the control, and Enter, Space, the arrow keys or typing
 * work it. A control Tab cannot reach is a failure, named.
 */
export function person(page, mode) {
  const keyboard = mode === "keyboard";
  const isFocused = (locator) => locator.evaluate((element) => element === document.activeElement);

  async function tabTo(locator, what) {
    await locator.waitFor();
    for (let step = 0; step < 300; step += 1) {
      // Found again each step, since a re-render replaces the element. Briefly, since a popup Tab
      // opens on its way (a combo box's list) hides the rest of the page until Tab moves on.
      const focused = await locator
        .evaluate((element) => element === document.activeElement, undefined, { timeout: 500 })
        .catch(() => false);
      if (focused) return;
      await page.keyboard.press("Tab");
    }
    throw new Error(`keyboard: Tab never reached ${what}`);
  }

  async function typeInto(locator, text, what) {
    if (keyboard) await tabTo(locator, what);
    else await locator.click();
    await page.keyboard.press("ControlOrMeta+a");
    await page.keyboard.type(text);
  }

  return {
    mode,
    tabTo,
    /** A button or link: clicked, or reached by Tab and pressed with Enter. */
    async press(locator, what) {
      if (!keyboard) return locator.click();
      await tabTo(locator, what);
      await page.keyboard.press("Enter");
    },
    /** A checkbox or switch: clicked, or reached by Tab and toggled with Space. */
    async toggle(locator, what) {
      if (!keyboard) return locator.click();
      await tabTo(locator, what);
      await page.keyboard.press("Space");
    },
    fill: typeInto,
    /**
     * A native select. Its list is the browser's own, which no click reaches. By keyboard the option
     * is chosen by typing its name into the focused select, as on macOS, where the arrows open the list.
     */
    async choose(locator, label, what) {
      if (!keyboard) return locator.selectOption({ label });
      await tabTo(locator, what);
      const labels = (await locator.locator("option").allTextContents()).map((text) => text.trim());
      const target = labels.indexOf(label);
      assert.ok(target >= 0, `${what} offers ${label}: ${labels.join(", ")}`);
      await page.keyboard.type(label);
      const current = await locator.evaluate((select) => select.selectedIndex);
      if (current !== target) throw new Error(`keyboard: typing ${label} chose ${labels[current]} in ${what}`);
    },
    /** A menu button and one of its items. */
    async menu(button, item, what) {
      if (!keyboard) {
        await button.click();
        return page.getByRole("menuitem", { name: new RegExp(`^${item}`) }).click();
      }
      await tabTo(button, what);
      await page.keyboard.press("Enter");
      await page.getByRole("menu").last().waitFor();
      for (let step = 0; step < 25; step += 1) {
        const text = await page.evaluate(() => document.activeElement?.textContent ?? "");
        if (text.startsWith(item)) return page.keyboard.press("Enter");
        await page.keyboard.press("ArrowDown");
      }
      throw new Error(`keyboard: ${item} is not in the menu of ${what}`);
    },
    /**
     * A tree's row, matched by its own label: clicked, or the tree reached by Tab and the row by the
     * arrow keys (Home first, a folded section opened with ArrowRight on the way), then Enter.
     */
    async treeRow(tree, name) {
      if (!keyboard)
        return tree
          .getByRole("treeitem")
          .filter({ has: page.locator(".model-pane-label", { hasText: new RegExp(`^${escape(name)}$`) }) })
          .first()
          .click();
      await tabTo(tree.locator('[role="treeitem"][tabindex="0"]').first(), `the tree ${name} is in`);
      await page.keyboard.press("Home");
      for (let step = 0; step < 200; step += 1) {
        const at = await page.evaluate(() => ({
          label: document.activeElement?.querySelector(".model-pane-label")?.textContent ?? "",
          folded: document.activeElement?.getAttribute("aria-expanded") === "false",
        }));
        if (at.label === name) return page.keyboard.press("Enter");
        if (at.folded) await page.keyboard.press("ArrowRight");
        const before = await page.evaluate(() => document.activeElement?.getAttribute("data-row"));
        await page.keyboard.press("ArrowDown");
        if ((await page.evaluate(() => document.activeElement?.getAttribute("data-row"))) === before) break;
      }
      throw new Error(`keyboard: the arrows did not reach ${name} in the tree`);
    },
    /** One of a tablist's tabs: clicked, or the tablist reached by Tab and the tab by the arrow keys. */
    async tab(tablist, name) {
      const tab = tablist.getByRole("tab", { name: new RegExp(`^${name}`) }).first();
      if (!keyboard) return tab.click();
      if ((await tab.getAttribute("aria-selected")) === "true") return;
      await tabTo(tablist.getByRole("tab", { selected: true }).first(), `the tabs holding ${name}`);
      for (let step = 0; step < 10; step += 1) {
        if (await isFocused(tab)) {
          await page.keyboard.press("Enter");
          return;
        }
        await page.keyboard.press("ArrowRight");
      }
      throw new Error(`keyboard: the arrows did not reach the tab ${name}`);
    },
    /** A cell of the relationship matrix: clicked, or reached from the grid's tab stop by the arrows. */
    async matrixCell(grid, row, column) {
      const cell = grid.locator(`[data-cell="${row}-${column}"]`);
      if (!keyboard) return cell.click();
      await tabTo(grid.locator('[data-cell][tabindex="0"]').first(), "the relationship matrix");
      for (let step = 0; step < 200; step += 1) {
        const at = await page.evaluate(() => document.activeElement?.getAttribute("data-cell") ?? "");
        const [r, c] = at.split("-").map(Number);
        if (r === row && c === column) return page.keyboard.press("Enter");
        await page.keyboard.press(r < row ? "ArrowDown" : r > row ? "ArrowUp" : c < column ? "ArrowRight" : "ArrowLeft");
      }
      throw new Error(`keyboard: the arrows did not reach the matrix cell ${row}-${column}`);
    },
  };
}

// A draft without a workbook has no dry run and no inference: the editor reads both since A5 and A6
// and takes the 404 as "none" (DRY_RUN_NOT_FOUND, INFERENCE_NOT_FOUND), as API.md says (0.10 R).
const absent = (url) => /\/model-drafts\/[^/]+\/(dry-run|inference)$/.test(new URL(url).pathname);

/**
 * Errors a person would see: console errors, uncaught errors, a 4xx or 5xx response and an `Error:`
 * text on the page, beyond the editor's "none" answers. `allowResponse` and `allowConsole` excuse a
 * response or console line the walk expects.
 */
export function watchErrors(page, { allowResponse = () => false, allowConsole = () => false } = {}) {
  const seen = [];
  page.on("console", (message) => {
    if (message.type() !== "error" || allowConsole(message)) return;
    if (message.text().includes("status of 404") && absent(message.location().url || "http://x/")) return;
    seen.push(`console: ${message.text()}`);
  });
  page.on("pageerror", (error) => seen.push(`page: ${error.message}`));
  page.on("response", (response) => {
    if (response.status() === 404 && response.request().method() === "GET" && absent(response.url())) return;
    if (response.status() >= 400 && !allowResponse(response))
      seen.push(`response: ${response.status()} ${response.request().method()} ${response.url()}`);
  });
  return async (where) => {
    const shown = await page.getByText(/^Error:/).count();
    assert.equal(shown, 0, `${where}: the page shows an Error: text`);
    assert.deepEqual(seen, [], `${where}: ${seen.join("; ")}`);
  };
}
