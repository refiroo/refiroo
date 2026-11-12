import { useCallback, useEffect, useRef } from "react";

/** What a press or focus lands on: the control itself rather than a label or icon inside it. */
const CONTROL = "button, a, input, select, textarea, [role='button'], [role='row'], [role='treeitem'], [tabindex]";

/** Surfaces a press or focus inside them says nothing about where an operation was started. */
const SURFACES = "[role='menu'], [role='menuitem'], [role='dialog'], [role='listbox'], [data-trigger]";

/**
 * The control an operation was started from (UX1): the last control pressed or focused outside a
 * menu or popover. A menu closes as its item is chosen, so the item cannot anchor the popover the
 * operation opens; the button that opened the menu, or the row a shortcut was pressed on, can. The
 * read returns `null` when that control has left the page, and the operation opens as a sheet.
 */
export function useOperationAnchor() {
  const last = useRef<HTMLElement | null>(null);
  useEffect(() => {
    const note = (event: Event) => {
      const element = event.target instanceof Element ? event.target : null;
      if (!element || element.closest(SURFACES)) return;
      last.current = (element.closest(CONTROL) as HTMLElement | null) ?? (element as HTMLElement);
    };
    document.addEventListener("pointerdown", note, true);
    document.addEventListener("focusin", note, true);
    return () => {
      document.removeEventListener("pointerdown", note, true);
      document.removeEventListener("focusin", note, true);
    };
  }, []);
  return useCallback(() => (last.current?.isConnected ? last.current : null), []);
}
