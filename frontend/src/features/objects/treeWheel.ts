/**
 * Where a wheel step goes in the record tree, whose type groups scroll in nested windows (UA2
 * revision). The group under the pointer owns the step, its heading included: the heading sits
 * outside the group's window, so the browser alone would scroll the window around it. The owner
 * scrolls first. At its end, the step moves an enclosing scroller (a parent group's window, or the
 * page) only as far as part of the owner's frame is still hidden behind that scroller's edge, so the
 * whole group can always be brought into view; then it stops, and never carries on beyond that.
 */

/** A scroller enclosing the owner: how far the owner's frame is hidden past its edge in the step's
 * direction, and how far it can still scroll that way. */
export interface EnclosingScroller {
  hidden: number;
  room: number;
}

export type WheelStep =
  /** The owner scrolls by `by` (signed). */
  | { kind: "own"; by: number }
  /** The enclosing scroller at `index` (nearest first) scrolls by `by` (signed). */
  | { kind: "enclosing"; index: number; by: number }
  /** Nothing moves: the owner is at its end and its frame is in full view. */
  | { kind: "stop" };

/**
 * `delta` is the step in pixels (negative up); `ownRoom` is how far the owner can scroll in its
 * direction; `enclosing` lists the scrollers around the owner, nearest first.
 */
export function planWheel(delta: number, ownRoom: number, enclosing: EnclosingScroller[]): WheelStep {
  const sign = Math.sign(delta);
  const size = Math.abs(delta);
  if (ownRoom > 0) return { kind: "own", by: sign * Math.min(size, ownRoom) };
  const index = enclosing.findIndex((scroller) => scroller.hidden > 0 && scroller.room > 0);
  if (index < 0) return { kind: "stop" };
  const { hidden, room } = enclosing[index];
  return { kind: "enclosing", index, by: sign * Math.min(size, hidden, room) };
}

/** A wheel event's vertical step in pixels, whatever unit the device reported it in. */
export function wheelPixels(event: Pick<WheelEvent, "deltaY" | "deltaMode">, pageHeight: number): number {
  if (event.deltaMode === 1) return event.deltaY * 16;
  if (event.deltaMode === 2) return event.deltaY * pageHeight;
  return event.deltaY;
}
