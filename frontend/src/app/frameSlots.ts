/**
 * Where the frame lets the top bar put its parts (0.17 UX1, PP-D39). A theme arranges the frame: with the top
 * bar and sidebar (`bars`) the top bar keeps everything; with a side column (`sheet`, `rail`) the frame offers
 * the column's head and foot, and the top bar moves its mark and applications, and for `rail` its actions, into
 * them. A page never reads this: it hands the frame a top bar and a rail, as before.
 */

import { createContext } from "react";

export type FrameSlots = {
  /** The side column's head: the product mark and the applications. Null when the frame has no side column. */
  sideHead: HTMLElement | null;
  /** The side column's foot: Help, Inbox, Settings and the account, in the `rail` arrangement. */
  sideFoot: HTMLElement | null;
};

export const FrameSlotsContext = createContext<FrameSlots>({ sideHead: null, sideFoot: null });
