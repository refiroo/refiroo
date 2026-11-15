/**
 * The nearest ancestor that scrolls an element's box (SR4): the one walk behind the wheel hand-over of a
 * list, the tree's row reveal, the tab bar kept in place, a popover brought into room and the edge scroll of a
 * drag. The callers differ in four ways, each an option, and each caller names the ones it needs.
 */

export interface ScrollAncestorOptions {
  /** A `.dialog` is as far as an element in it carries the wheel: it is returned whether it scrolls or not. */
  dialog?: boolean;
  /** How many pixels the content must be taller than the box to count as scrolling (default 0). */
  tolerance?: number;
  /** Look at `<body>` and `<html>` too (default: stop before `<body>`, so only the page is left). */
  pastBody?: boolean;
}

function scrolls(node: Element, tolerance: number): boolean {
  const { overflowY } = getComputedStyle(node);
  return (overflowY === "auto" || overflowY === "scroll") && node.scrollHeight > node.clientHeight + tolerance;
}

/** The nearest ancestor of `element` that scrolls, or `null` where only the page does. */
export function scrollingAncestorOrNull(element: Element, options: ScrollAncestorOptions = {}): HTMLElement | null {
  const { dialog = false, tolerance = 0, pastBody = false } = options;
  for (let node = element.parentElement; node && (pastBody || node !== document.body); node = node.parentElement) {
    if (dialog && node.matches(".dialog")) return node;
    if (scrolls(node, tolerance)) return node;
  }
  return null;
}

/** The nearest ancestor of `element` that scrolls, else the page's scroller. */
export function scrollingAncestor(element: Element, options: ScrollAncestorOptions = {}): HTMLElement {
  return (
    scrollingAncestorOrNull(element, options) ??
    (document.scrollingElement as HTMLElement | null) ??
    document.documentElement
  );
}
