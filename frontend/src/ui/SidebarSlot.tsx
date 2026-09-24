/**
 * Lets a page place its own navigation in the shell sidebar, so every destination keeps the same
 * rail-and-content frame. Outside a shell (tests, embedding) the content renders in place.
 */

import { createContext, useContext, type ReactNode } from "react";
import { createPortal } from "react-dom";

export const SidebarSlotContext = createContext<HTMLElement | null>(null);

export function SidebarPortal({ children }: { children: ReactNode }) {
  const slot = useContext(SidebarSlotContext);
  return slot ? createPortal(children, slot) : children;
}
