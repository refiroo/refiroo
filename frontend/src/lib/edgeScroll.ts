/**
 * Scrolling while something is dragged near a scroller's top or bottom edge (0.9 UA9), shared by
 * the record tree's pointer drags and the model editor's pane (found 2026-10-19: its drags could not
 * reach rows out of view).
 */

/** The band along a scroller's top and bottom edges that scrolls it, and the fastest step. */
export const EDGE = 40;
export const MAX_STEP = 16;
/** The band for a finger, which covers more than a mouse pointer does (0.11 U1, D211). */
export const TOUCH_EDGE = 56;

/** The nearest ancestor of `root` that scrolls vertically, else the document's scroller. */
export function scrollerOf(root: HTMLElement): HTMLElement {
  for (let element = root.parentElement; element; element = element.parentElement) {
    const overflow = getComputedStyle(element).overflowY;
    if ((overflow === "auto" || overflow === "scroll") && element.scrollHeight > element.clientHeight) return element;
  }
  return (document.scrollingElement as HTMLElement | null) ?? document.documentElement;
}

/**
 * Scrolls `viewport` one step when `y` is within its edge band and it can move that way. The band
 * starts below what covers the scroller's top, which a sticky bar declares as `scroll-padding-top`
 * (the document under the top bar, U1); a point over that cover is in the band too.
 */
export function scrollAtEdge(viewport: HTMLElement, y: number, band = EDGE): boolean {
  const box =
    viewport === document.scrollingElement ? { top: 0, bottom: window.innerHeight } : viewport.getBoundingClientRect();
  const covered = parseFloat(getComputedStyle(viewport).scrollPaddingTop) || 0;
  const rect = { top: box.top + covered, bottom: box.bottom };
  const up = rect.top + band - y;
  const down = y - (rect.bottom - band);
  const step = (depth: number) => Math.min(MAX_STEP, Math.ceil((Math.min(depth, band) / band) * MAX_STEP));
  const delta =
    up > 0 && viewport.scrollTop > 0
      ? -step(up)
      : down > 0 && viewport.scrollTop + viewport.clientHeight < viewport.scrollHeight - 1
        ? step(down)
        : 0;
  if (delta) viewport.scrollTop += delta;
  return Boolean(delta);
}
