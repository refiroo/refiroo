/**
 * Keeping a tab bar where it was when another tab is chosen. A tab's panel can be taller or
 * shorter than the one before, and the page then scrolls with it; the person's eyes are on the tab
 * bar, so the page is scrolled by however far the bar moved.
 */

/**
 * How far to scroll to bring a tab bar back to where it was. `before` and `after` are the bar's
 * distance from the top of the viewport. A bar that was scrolled out above the viewport is left
 * alone: nothing there was being looked at.
 */
export function scrollDelta(before: number, after: number): number {
  return before < 0 ? 0 : after - before;
}

/** The nearest ancestor that scrolls, or the page itself. */
export function scrollContainer(element: Element): Element {
  for (let parent = element.parentElement; parent; parent = parent.parentElement) {
    const { overflowY } = getComputedStyle(parent);
    if ((overflowY === "auto" || overflowY === "scroll") && parent.scrollHeight > parent.clientHeight) return parent;
  }
  return document.scrollingElement ?? document.documentElement;
}

/** Scroll so that `bar` is `before` pixels from the top of the viewport again, if it can be. */
export function restoreTabBar(bar: Element, before: number) {
  const delta = scrollDelta(before, bar.getBoundingClientRect().top);
  if (delta) scrollContainer(bar).scrollTop += delta;
}

/**
 * The height to keep for a tab area: the tallest it has been. A short panel chosen after a tall
 * one would otherwise make the page shorter than the viewport and the browser would clamp the scroll
 * position to the top, where `restoreTabBar` can no longer scroll back to it.
 */
export function tallestHeight(tallest: number, measured: number): number {
  return Number.isFinite(measured) && measured > tallest ? measured : tallest;
}

/** Keeps `element` at least as tall as it has been while it is observed; returns the stop function. */
export function holdTallest(element: HTMLElement): () => void {
  if (typeof ResizeObserver === "undefined") return () => undefined;
  let tallest = 0;
  const hold = () => {
    const next = tallestHeight(tallest, element.offsetHeight);
    if (next === tallest) return;
    tallest = next;
    element.style.minHeight = `${tallest}px`;
  };
  hold();
  const observer = new ResizeObserver(hold);
  observer.observe(element);
  return () => observer.disconnect();
}
