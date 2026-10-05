/**
 * The space directly below the shell's data-context band (Track U U2). The band stays visible while
 * the page scrolls, so it holds only the context and its actions; what those actions report
 * (validation results, refusals, a model mismatch) is placed here, where it scrolls with the page.
 * Outside a shell (tests, embedding) the content renders in place.
 */

import { createContext, useContext, type ReactNode } from "react";
import { createPortal } from "react-dom";

export const ContextBandSlotContext = createContext<HTMLElement | null>(null);

export function BelowContextBand({ children }: { children: ReactNode }) {
  const slot = useContext(ContextBandSlotContext);
  return slot ? createPortal(children, slot) : children;
}
