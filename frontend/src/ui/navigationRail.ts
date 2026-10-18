/**
 * How the navigation rail scrolls and holds focus, the same on every page (`ShellFrame`,
 * `NavigationDrawer`):
 *
 * - The rail's position belongs to its scope (an application in a workspace, or Settings). Moving
 *   between pages, views and records of the scope, or into and out of a change set or publication,
 *   keeps it where the reader left it, even though some of those moves mount the frame afresh.
 * - Another scope (application or workspace) opens the rail at its top.
 * - Nothing that loads scrolls the rail; only keyboard movement in the rail's tree does, and only
 *   the rail (`RecordTree`).
 * - A choice made in the rail leaves focus in the rail; the page it opens does not take it
 *   (`focusInNavigationRail`).
 */

import { useLayoutEffect } from "react";

/** Marks the element that holds the rail's content, on a desktop rail and in the phone drawer. */
export const NAVIGATION_RAIL_ATTRIBUTE = "data-navigation-rail";

/** Whether the reader is working in the rail, so a page that opened should leave focus there. */
export function focusInNavigationRail() {
  return Boolean(document.activeElement?.closest(`[${NAVIGATION_RAIL_ATTRIBUTE}]`));
}

/** The last scope's position; module state, so it outlives a frame mounted afresh. */
let remembered: { scope: string; top: number } | undefined;

/**
 * Keeps `container`'s scroll position for `scope` (see above). A position restored into a frame
 * mounted afresh waits for the rail's content to load and grow; any scroll, key or pointer from the
 * reader ends the wait, so the rail never moves under them.
 */
export function useRailScroll(container: HTMLElement | null, scope: string) {
  useLayoutEffect(() => (container ? keepRailScroll(container, scope) : undefined), [container, scope]);
}

/** `useRailScroll`'s work on one container for one scope; returns its cleanup. */
function keepRailScroll(container: HTMLElement, scope: string) {
  const target = remembered?.scope === scope ? remembered.top : 0;
  remembered = { scope, top: target };
  let restoring = true;
  const restore = () => {
    if (!restoring) return;
    container.scrollTop = target;
    if (container.scrollTop >= target - 1) restoring = false;
  };
  const stop = () => {
    restoring = false;
  };
  const keep = () => {
    if (!restoring) remembered = { scope, top: container.scrollTop };
  };
  restore();
  const growing = typeof ResizeObserver === "undefined" ? undefined : new ResizeObserver(restore);
  for (const child of Array.from(container.children)) growing?.observe(child);
  const ends = ["wheel", "touchstart", "pointerdown", "keydown"] as const;
  for (const event of ends) container.addEventListener(event, stop, { passive: true });
  container.addEventListener("scroll", keep, { passive: true });
  return () => {
    growing?.disconnect();
    for (const event of ends) container.removeEventListener(event, stop);
    container.removeEventListener("scroll", keep);
  };
}
