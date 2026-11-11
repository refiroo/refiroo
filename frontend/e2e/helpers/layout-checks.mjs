// Measured layout checks for the browser runners (0.10 A4a, the user's request after A4a's first
// screenshots): what a screenshot shows but no assertion caught. Each returns nothing when the layout
// holds and throws naming every problem otherwise.
import assert from "node:assert/strict";

/** Pixel margins the design keeps; one place, so a runner never hard-codes its own. */
export const DIALOG = { edge: 16, labelToControl: 10, betweenFields: 12 };

/**
 * The open dialog (the last one): its actions stand clear of its frame; each labelled field's label
 * is right above its own control and further from the field before it; nothing is wider than the
 * dialog. `name` says which dialog in the message.
 */
export async function assertDialogLayout(page, name) {
  const problems = await page.evaluate((limits) => {
    const dialogs = [...document.querySelectorAll(".dialog")];
    const dialog = dialogs[dialogs.length - 1];
    if (!dialog) return ["no dialog is open"];
    const found = [];
    const frame = dialog.getBoundingClientRect();
    const buttons = [...dialog.querySelectorAll(".dialog-actions button, .dialog-actions a")].filter(
      (item) => item.getBoundingClientRect().height > 0,
    );
    if (!buttons.length) found.push("no actions");
    for (const button of buttons) {
      const box = button.getBoundingClientRect();
      const bottom = Math.round(frame.bottom - box.bottom);
      const right = Math.round(frame.right - box.right);
      if (bottom < limits.edge) found.push(`“${button.textContent.trim()}” is ${bottom}px from the bottom edge`);
      if (right < limits.edge) found.push(`“${button.textContent.trim()}” is ${right}px from the right edge`);
    }
    // The bottom of the row of fields above; fields side by side (a grid row) are one row.
    let previousBottom;
    let rowTop;
    let rowBottom;
    for (const field of dialog.querySelectorAll(".form-field")) {
      if (field.parentElement.closest(".form-field")) continue;
      const label = field.querySelector(":scope > label, :scope > legend");
      const control = field.querySelector(
        "input:not([type=checkbox]):not([type=radio]), select, textarea, [role=group]",
      );
      if (!label || !control || label.getBoundingClientRect().height === 0) continue;
      const labelBox = label.getBoundingClientRect();
      const controlBox = control.getBoundingClientRect();
      const text = label.textContent.trim();
      const gap = Math.round(controlBox.top - labelBox.bottom);
      if (gap < 0 || gap > limits.labelToControl) found.push(`“${text}” is ${gap}px above its control`);
      const fieldBox = field.getBoundingClientRect();
      if (rowTop !== undefined && Math.abs(fieldBox.top - rowTop) < 2) {
        rowBottom = Math.max(rowBottom, fieldBox.bottom);
        continue;
      }
      previousBottom = rowBottom;
      if (previousBottom !== undefined) {
        const above = Math.round(labelBox.top - previousBottom);
        if (above < limits.betweenFields) found.push(`“${text}” is ${above}px below the field before it`);
        if (above <= gap) found.push(`“${text}” is nearer the field before it than its own control`);
      }
      rowTop = fieldBox.top;
      rowBottom = fieldBox.bottom;
    }
    for (const element of dialog.querySelectorAll("input, select, textarea, button, [role=listbox]")) {
      // A visually hidden control (react-aria's form select behind its listbox) is clipped to nothing.
      if (element.closest('[style*="clip"]')) continue;
      const box = element.getBoundingClientRect();
      if (box.width && (box.left < frame.left - 1 || box.right > frame.right + 1))
        found.push(`a ${element.tagName.toLowerCase()} overflows the dialog sideways`);
    }
    return found;
  }, DIALOG);
  assert.deepEqual(problems, [], `${name}: ${problems.join("; ")}`);
}

/**
 * A full-height surface (the model editor): it is as wide as the window, the page does not scroll,
 * and the given panes end at the same line.
 */
export async function assertFullSurface(page, selector, paneSelectors, name) {
  const result = await page.evaluate(
    ({ selector, paneSelectors }) => {
      const surface = document.querySelector(selector)?.getBoundingClientRect();
      const bottoms = paneSelectors.map((item) =>
        Math.round(document.querySelector(item)?.getBoundingClientRect().bottom ?? -1),
      );
      return {
        width: Math.round(surface?.width ?? 0),
        window: window.innerWidth,
        pageScrolls: document.documentElement.scrollHeight > window.innerHeight + 1,
        bottoms,
      };
    },
    { selector, paneSelectors },
  );
  assert.ok(result.width >= result.window - 1, `${name}: ${result.width}px wide in a ${result.window}px window`);
  assert.equal(result.pageScrolls, false, `${name}: the page scrolls`);
  assert.equal(new Set(result.bottoms).size, 1, `${name}: panes end at different lines (${result.bottoms.join(", ")})`);
}

/**
 * An application page fills the main column (within its padding) at a wide window, not a fixed
 * width: `selector`'s box spans `.workspace-main`'s content box, to the pixel.
 */
export async function assertFillsMainColumn(page, selector, name) {
  const result = await page.evaluate((selector) => {
    const main = document.querySelector(".workspace-main");
    const style = getComputedStyle(main);
    const box = main.getBoundingClientRect();
    const inner = box.width - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight);
    return {
      width: document.querySelector(selector)?.getBoundingClientRect().width ?? 0,
      inner,
      window: window.innerWidth,
    };
  }, selector);
  assert.ok(
    result.inner > 1440,
    `${name}: the main column is only ${Math.round(result.inner)}px in a ${result.window}px window`,
  );
  assert.ok(
    Math.abs(result.width - result.inner) <= 1,
    `${name}: ${Math.round(result.width)}px wide, the main column's content is ${Math.round(result.inner)}px`,
  );
}
