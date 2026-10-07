/**
 * The record tree's wheel handling (UA2 revision): the decisions are `treeWheel`'s; this hook reads
 * the page they are made over and applies them. Not passive, so a step the tree takes over does not
 * also scroll what the browser would have picked. Touch and keyboard do not send wheel events.
 */

import { useEffect, type RefObject } from "react";
import { GESTURE_GAP_MS, outwardIndex, planWheel, wheelPixels } from "./treeWheel";

export function useTreeWheel(tree: RefObject<HTMLElement | null>) {
  useEffect(() => {
    const root = tree.current;
    if (!root) return;
    let lastStep = -Infinity;
    let latched: HTMLElement | undefined;
    const onWheel = (event: WheelEvent) => {
      if (event.ctrlKey || event.deltaY === 0) return;
      const fresh = event.timeStamp - lastStep > GESTURE_GAP_MS;
      lastStep = event.timeStamp;
      const target = event.target as HTMLElement;
      // A gesture keeps its scroller; a new one starts from the group under the pointer.
      let owner = !fresh && latched?.isConnected ? latched : owningWindow(target);
      if (!owner) {
        latched = undefined;
        return;
      }
      const delta = wheelPixels(event, owner.clientHeight);
      let scrollers = enclosingScrollers(owner);
      let enclosing = measure(owner, scrollers, delta);
      let step = planWheel(delta, roomOf(owner, delta), enclosing);
      if (fresh && step.kind === "stop") {
        const index = outwardIndex(enclosing);
        if (index >= 0) {
          owner = scrollers[index];
          scrollers = enclosingScrollers(owner);
          enclosing = measure(owner, scrollers, delta);
          step = planWheel(delta, roomOf(owner, delta), enclosing);
        }
      }
      latched = owner;
      // Over the owner's own rows the browser already scrolls the owner, smoothly; let it.
      if (step.kind === "own" && target.closest(".scroll-window-viewport") === owner) return;
      event.preventDefault();
      if (step.kind === "own") owner.scrollTop += step.by;
      else if (step.kind === "enclosing") scrollers[step.index].scrollTop += step.by;
    };
    root.addEventListener("wheel", onWheel, { passive: false });
    return () => root.removeEventListener("wheel", onWheel);
  }, [tree]);
}

/** The window of the innermost group around `element` whose window scrolls; its heading counts. */
function owningWindow(element: HTMLElement) {
  for (let group = element.closest<HTMLElement>(".tree-group"); group;) {
    const viewport = ownWindow(group);
    if (viewport && scrolls(viewport)) return viewport;
    group = group.parentElement?.closest<HTMLElement>(".tree-group") ?? null;
  }
  return undefined;
}

function ownWindow(group: HTMLElement) {
  return group.querySelector<HTMLElement>(".scroll-window-viewport");
}

function scrolls(element: HTMLElement) {
  return element.scrollHeight > element.clientHeight + 1;
}

/** The scrollers around a group's window, nearest first: the windows of the groups around it that
 * scroll, then whatever scrolls the page. A page scroller has none around it. */
function enclosingScrollers(scroller: HTMLElement) {
  if (!scroller.classList.contains("scroll-window-viewport")) return [];
  const scrollers: HTMLElement[] = [];
  for (let next = scroller.parentElement?.closest<HTMLElement>(".scroll-window-viewport"); next;) {
    if (scrolls(next)) scrollers.push(next);
    next = next.parentElement?.closest<HTMLElement>(".scroll-window-viewport");
  }
  let page: HTMLElement | null = (scrollers.at(-1) ?? scroller).parentElement;
  while (page && !(/(auto|scroll)/.test(getComputedStyle(page).overflowY) && scrolls(page))) page = page.parentElement;
  scrollers.push(page ?? (scroller.ownerDocument.scrollingElement as HTMLElement));
  return scrollers;
}

/** How far the owner's group is hidden past each scroller's edge in the step's direction, and how
 * far each can still move. */
function measure(owner: HTMLElement, scrollers: HTMLElement[], delta: number) {
  const frame = revealedArea(owner, delta);
  return scrollers.map((scroller) => {
    const box = visibleBox(scroller);
    const hidden = !frame ? 0 : delta > 0 ? frame.bottom - box.bottom : box.top - frame.top;
    return { hidden: Math.max(0, Math.round(hidden)), room: roomOf(scroller, delta) };
  });
}

/**
 * The area a step must bring into view around the owner's group: its frame and, going up, the row
 * of the record the group belongs to, so a heading is never shown without its owner.
 */
function revealedArea(owner: HTMLElement, delta: number) {
  const group = owner.closest<HTMLElement>(".tree-group");
  if (!group) return undefined;
  const frame = group.getBoundingClientRect();
  if (delta > 0) return { top: frame.top, bottom: frame.bottom };
  const record = group.parentElement?.closest<HTMLElement>("[role='treeitem'][data-object-id]");
  const row = record && Array.from(record.children).find((child) => child.classList.contains("tree-row"));
  const top = row ? Math.min(frame.top, row.getBoundingClientRect().top) : frame.top;
  return { top, bottom: frame.bottom };
}

/** The part of a scroller the user sees, on the screen. */
function visibleBox(scroller: HTMLElement) {
  if (scroller === scroller.ownerDocument.scrollingElement) return { top: 0, bottom: window.innerHeight };
  return scroller.getBoundingClientRect();
}

/** How far a scroller can still move in a step's direction. */
function roomOf(scroller: HTMLElement, delta: number) {
  const room = delta > 0 ? scroller.scrollHeight - scroller.clientHeight - scroller.scrollTop : scroller.scrollTop;
  return Math.max(0, Math.floor(room));
}
