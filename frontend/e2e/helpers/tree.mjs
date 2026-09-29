// Keyboard driver for the tree lens (Base 0.8 B3), shared by the B3 and B4 runners. Every move is a
// key press: focus reaches the tree with Tab or Shift+Tab, travels by arrows and type-ahead, and
// opens menus with Shift+F10.

export const escapeRegExp = (text) => text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

/**
 * The tree lens's keyboard helpers over `page`. `fail` records a failed expectation without
 * stopping the journey; a helper that cannot continue throws instead.
 */
export function treeDriver(page, fail) {
  const lens = page.locator(".tree-lens");
  const focused = () =>
    page.evaluate(() => ({
      role: document.activeElement?.closest(".tree-lens")
        ? (document.activeElement.getAttribute("role") ?? document.activeElement.tagName.toLowerCase())
        : "outside the lens",
      label: document.activeElement?.getAttribute("aria-label") ?? document.activeElement?.textContent ?? "",
    }));

  /** Presses `key` until focus is on a tree item: the keyboard path back into the tree. */
  async function keyIntoTree(key = "Shift+Tab", limit = 60) {
    for (let step = 0; step < limit; step++) {
      if ((await focused()).role === "treeitem") return;
      await page.keyboard.press(key);
    }
    throw new Error(`${key} never reached the tree`);
  }

  /** Moves focus through the tree with Up and Down until the item's label starts with `name`. */
  async function arrowTo(name, limit = 120) {
    const start = await focused();
    if (start.role === "treeitem" && !start.label.startsWith(name)) {
      // Type-ahead first: typing the label's start moves to the next loaded record it begins.
      await page.keyboard.type(name.toLowerCase());
      await page.waitForTimeout(750);
    }
    for (let step = 0; step < limit; step++) {
      const at = await focused();
      if (at.role !== "treeitem") throw new Error(`focus left the tree looking for ${name}`);
      if (at.label.startsWith(name)) return;
      const below = await page.evaluate((prefix) => {
        const target = Array.from(document.querySelectorAll(".tree-lens [role='treeitem']")).find((item) =>
          (item.getAttribute("aria-label") ?? "").startsWith(prefix),
        );
        // Not drawn yet: it lies further down a branch that loads as focus moves on.
        return !target || Boolean(document.activeElement.compareDocumentPosition(target) & Node.DOCUMENT_POSITION_FOLLOWING);
      }, name);
      await page.keyboard.press(below ? "ArrowDown" : "ArrowUp");
      await page.waitForTimeout(30);
    }
    throw new Error(`the arrow keys never reached ${name} from ${start.label}; focus is on ${JSON.stringify(await focused())}`);
  }

  /** Types into the lens search, arrows to the match and opens it with Enter. */
  async function findBySearch(search, name) {
    await lens.getByRole("textbox", { name: /^Search / }).focus();
    await page.keyboard.type(search);
    await lens.getByRole("treeitem", { name: new RegExp(`^${escapeRegExp(name)}, in `) }).first().waitFor();
    await page.keyboard.press("Tab");
    await arrowTo(name);
    await page.keyboard.press("Enter");
  }

  /** Opens the focused item's menu with Shift+F10 and chooses `item` by arrowing to it. */
  async function menu(item) {
    await page.keyboard.press("Shift+F10");
    const opened = page.getByRole("menu");
    await opened.waitFor();
    // A change set's node menu adds the restructurings (C4), so it can be long.
    for (let step = 0; step < 20; step++) {
      const text = await page.evaluate(() => document.activeElement?.textContent ?? "");
      if (text.startsWith(item)) {
        await page.keyboard.press("Enter");
        await opened.waitFor({ state: "detached" });
        return;
      }
      await page.keyboard.press("ArrowDown");
    }
    throw new Error(`the menu has no ${item}`);
  }

  async function expectFocus(name, label) {
    await page
      .waitForFunction(
        (prefix) =>
          document.activeElement?.getAttribute("role") === "treeitem" &&
          document.activeElement.closest(".tree-lens") &&
          (document.activeElement.getAttribute("aria-label") ?? "").startsWith(prefix),
        name,
        { timeout: 10000 },
      )
      .catch(async () => fail(`${label}: focus is on ${JSON.stringify(await focused())}, not ${name}`));
  }

  /** From the focused item, Add `childType` with `name` and the form's next `fields` in Tab order. */
  async function addChild(childType, name, fields) {
    await menu(`Add ${childType}`);
    const form = page.getByRole("dialog", { name: new RegExp(`New ${childType}`, "i") });
    await form.waitFor();
    await page.keyboard.type(name);
    for (const value of fields) {
      await page.keyboard.press("Tab");
      await page.keyboard.type(value);
    }
    await page.keyboard.press("Enter");
    await form.waitFor({ state: "detached" });
    await expectFocus(name, `new ${childType} ${name}`);
  }

  /**
   * Replaces the open move dialog's search with `text` and waits for the list it asks for: the
   * dialog searches once typing pauses, and until then the previous list is still shown.
   */
  async function searchCandidates(dialog, text) {
    const listed = page.waitForResponse(
      (response) =>
        response.url().includes("/parent-candidates") && new URL(response.url()).searchParams.get("search") === text,
    );
    await page.keyboard.press("ControlOrMeta+A");
    await page.keyboard.type(text);
    await listed;
    await dialog.locator("fieldset:not([aria-busy])").waitFor();
  }

  /**
   * In the open move dialog, searches `name`, chooses its radio with Tab and Space and confirms
   * with the move button, then waits for the dialog to close.
   */
  async function chooseAndMove(dialog, name) {
    await searchCandidates(dialog, name);
    const choice = dialog.getByRole("radio", { name: new RegExp(`^${escapeRegExp(name)}\\b`) }).first();
    await choice.waitFor();
    const isFocused = () => choice.evaluate((radio) => radio === document.activeElement);
    for (let step = 0; step < 8 && !(await isFocused()); step++) await page.keyboard.press("Tab");
    if (!(await isFocused()))
      throw new Error(
        `Tab never reached ${name} in the move dialog; focus is on ${await page.evaluate(() => document.activeElement?.outerHTML.slice(0, 160))}`,
      );
    await page.keyboard.press("Space");
    if (!(await choice.isChecked())) fail(`the keyboard did not choose ${name}`);
    const confirm = dialog.getByRole("button", { name: `Move to ${name}` });
    for (let step = 0; step < 6 && !(await confirm.evaluate((button) => button === document.activeElement)); step++)
      await page.keyboard.press("Tab");
    await page.keyboard.press("Enter");
    await dialog.waitFor({ state: "detached", timeout: 20000 });
  }

  /** The tree item for `name` (label start) in the lens. */
  const item = (name) => lens.getByRole("treeitem", { name: new RegExp(`^${escapeRegExp(name)}(,|$)`) }).first();

  return { lens, item, focused, keyIntoTree, arrowTo, findBySearch, menu, expectFocus, addChild, searchCandidates, chooseAndMove };
}

// Pointer drags in the tree lens (Base 0.8 B5). A drag is pressed on a row, moved over a target in
// steps as a hand would, and released by the caller, so the drag's state can be checked first.

/** The row a tree item draws for itself, not the rows of its open branch. */
const ownRow = (item) => item.locator(".tree-row").first();

/** Where on `item`'s row the pointer rests: its middle, or the gap just above or below it. */
async function pointOn(item, where = "middle") {
  const box = await ownRow(item).boundingBox();
  if (!box) throw new Error("the drag target has no box on the page");
  const y = where === "above" ? box.y + 2 : where === "below" ? box.y + box.height - 2 : box.y + box.height / 2;
  return { x: box.x + box.width * 0.6, y };
}

/**
 * Presses the mouse on `item`'s row and moves it far enough to start a drag. The row is measured
 * once the tree has settled (a write re-reads it and reveals the written record), and the drag must
 * be of that row's record.
 */
export async function dragFrom(page, item) {
  const node = item.locator(".tree-node").first();
  await page.waitForLoadState("networkidle");
  let box = await node.boundingBox();
  for (let attempt = 0; attempt < 20; attempt++) {
    await page.waitForTimeout(50);
    const again = await node.boundingBox();
    if (box && again && box.x === again.x && box.y === again.y) break;
    box = again;
  }
  if (!box) throw new Error("the dragged row has no box on the page");
  await page.mouse.move(box.x + box.width / 3, box.y + box.height / 2);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width / 3 + 10, box.y + box.height / 2 + 6, { steps: 3 });
  const preview = page.locator(".tree-drag-preview");
  await preview.waitFor();
  const name = (await item.getAttribute("aria-label"))?.split(",")[0] ?? "";
  const dragged = (await preview.textContent()) ?? "";
  if (!dragged.startsWith(name)) throw new Error(`pressed on ${name}, but the drag is of ${dragged}`);
}

/** Moves the held pointer over `item`'s row (`middle`) or the gap `above` or `below` it. */
export async function dragOver(page, item, where = "middle") {
  const { x, y } = await pointOn(item, where);
  await page.mouse.move(x, y, { steps: 8 });
}

/** The drag's state as the page shows it: the preview's tone and text, and the glowing rows. */
export function dragState(page) {
  return page.evaluate(() => {
    const preview = document.querySelector(".tree-drag-preview");
    return {
      dragging: Boolean(preview),
      tone: preview?.classList.contains("refused") ? "refused" : preview?.classList.contains("accepted") ? "accepted" : "",
      text: preview?.textContent ?? "",
      line: Boolean(document.querySelector(".tree-drop-line")),
      cursor: getComputedStyle(document.body).cursor,
      glowing: Array.from(document.querySelectorAll(".tree-row.drop-accepted, .tree-row.drop-refused")).map(
        (row) => row.closest("[role='treeitem']")?.getAttribute("aria-label") ?? "",
      ),
    };
  });
}

/** Ends a held drag with Escape and releases the mouse, so nothing is dropped. */
export async function cancelDrag(page) {
  await page.keyboard.press("Escape");
  await page.mouse.up();
  await page.locator(".tree-drag-preview").waitFor({ state: "detached" });
}
