/**
 * The whole value of a table cell the column cuts off (0.10 A4a, the user's request): every cell of
 * `ui/DataTable` ends in an ellipsis when its value is wider than its column. Pointing at such a cell
 * shows its value just below it, wrapped over as many lines as it needs; so does moving focus into
 * it. A cell being edited in place shows nothing. On a touch screen a long press shows it, and a tap on the cell's text (not on a link or
 * button in it) shows and hides it. A cell whose value fits shows nothing. Escape, scrolling and
 * leaving the cell close it.
 *
 * The box repeats what the cell already says, so it is hidden from assistive technology, which reads
 * the cell whole.
 */

import { useCallback, useEffect, useState, type FocusEvent, type MouseEvent, type PointerEvent } from "react";
import { createPortal } from "react-dom";

type Reveal = { cell: HTMLElement; text: string; left: number; top: number; above: boolean; width: number };

const INTERACTIVE = "button, a, input, select, textarea, [role='menu'], [role='button']";

/**
 * Whether the cell's text runs past the cell's content box: measured on the text itself, so a
 * control's own padding or negative margin (the in-place edit pencil) is not taken for a cut. Where
 * the browser cannot measure text (a test DOM), the content's scroll width decides.
 */
function isCut(cell: HTMLElement) {
  const hidden = ".visually-hidden, [aria-hidden='true']";
  if (typeof document.createRange === "function" && typeof Range.prototype.getBoundingClientRect === "function") {
    const box = cell.getBoundingClientRect();
    const right = box.right - parseFloat(window.getComputedStyle(cell).paddingRight || "0");
    const walker = document.createTreeWalker(cell, NodeFilter.SHOW_TEXT);
    let measured = false;
    for (let node = walker.nextNode(); node; node = walker.nextNode()) {
      if (!node.textContent?.trim() || node.parentElement?.closest(hidden)) continue;
      const range = document.createRange();
      range.selectNodeContents(node);
      const text = range.getBoundingClientRect();
      if (!text.width) continue;
      measured = true;
      if (text.right > right + 1) return true;
    }
    if (measured) return false;
  }
  if (cell.scrollWidth > cell.clientWidth + 1) return true;
  return Array.from(cell.querySelectorAll<HTMLElement>("*")).some(
    (inner) => inner.clientWidth > 0 && inner.scrollWidth > inner.clientWidth + 1,
  );
}

/** The text a reader sees in the cell: without words only assistive technology gets. */
function visibleText(cell: HTMLElement) {
  const copy = cell.cloneNode(true) as HTMLElement;
  copy.querySelectorAll(".visually-hidden, [aria-hidden='true']").forEach((node) => node.remove());
  return (copy.textContent ?? "").replace(/\s+/g, " ").trim();
}

function placeFor(cell: HTMLElement, text: string): Reveal {
  const box = cell.getBoundingClientRect();
  const width = Math.min(Math.max(box.width, 240), 440, window.innerWidth - 24);
  const left = Math.min(Math.max(12, box.left), window.innerWidth - width - 12);
  const above = box.bottom + 120 > window.innerHeight && box.top > 140;
  return { cell, text, left, top: above ? box.top - 4 : box.bottom + 4, above, width };
}

export function useCellReveal() {
  const [reveal, setReveal] = useState<Reveal>();
  const close = useCallback(() => setReveal(undefined), []);

  const show = useCallback((cell: HTMLElement | null) => {
    // A cell being edited in place holds its own form, which says everything already.
    if (!cell || cell.querySelector("form") || !isCut(cell)) return false;
    const text = visibleText(cell);
    if (!text) return false;
    setReveal(placeFor(cell, text));
    return true;
  }, []);

  useEffect(() => {
    if (!reveal) return;
    const onKey = (event: KeyboardEvent) => event.key === "Escape" && close();
    const onPress = (event: Event) => {
      if (!reveal.cell.contains(event.target as Node)) close();
    };
    window.addEventListener("keydown", onKey);
    window.addEventListener("scroll", close, true);
    window.addEventListener("resize", close);
    document.addEventListener("pointerdown", onPress);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("scroll", close, true);
      window.removeEventListener("resize", close);
      document.removeEventListener("pointerdown", onPress);
    };
  }, [reveal, close]);

  const cellOf = (target: EventTarget | null) =>
    (target as HTMLElement | null)?.closest?.<HTMLElement>("td[data-reveal]") ?? null;

  /** Event handlers for the table body: the cells that may reveal carry `data-reveal`. */
  const handlers = {
    onPointerOver: (event: PointerEvent<HTMLElement>) => {
      if (event.pointerType !== "mouse") return;
      const cell = cellOf(event.target);
      if (!cell) return close();
      if (cell !== reveal?.cell && !show(cell)) close();
    },
    onPointerLeave: (event: PointerEvent<HTMLElement>) => {
      if (event.pointerType === "mouse") close();
    },
    onFocus: (event: FocusEvent<HTMLElement>) => {
      const cell = cellOf(event.target);
      if (cell && !show(cell)) close();
    },
    onBlur: close,
    // A long press on a touch screen opens the context menu; on a cut-off cell it reveals instead.
    onContextMenu: (event: MouseEvent<HTMLElement>) => {
      const cell = cellOf(event.target);
      if (cell && show(cell)) event.preventDefault();
    },
    onPointerUp: (event: PointerEvent<HTMLElement>) => {
      if (event.pointerType === "mouse") return;
      const cell = cellOf(event.target);
      if (!cell || (event.target as HTMLElement).closest(INTERACTIVE)) return;
      if (reveal?.cell === cell) close();
      else show(cell);
    },
  };

  const overlay =
    reveal &&
    createPortal(
      <div
        className={`cell-reveal${reveal.above ? " cell-reveal-above" : ""}`}
        aria-hidden="true"
        style={{ left: reveal.left, top: reveal.top, width: reveal.width }}
      >
        {reveal.text}
      </div>,
      document.body,
    );

  return { handlers, overlay };
}
