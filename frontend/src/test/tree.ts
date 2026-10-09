import { fireEvent, screen, waitFor } from "@testing-library/react";

/**
 * Opens the first type group drawn folded right now, by its heading's chevron, as a user would; a
 * caller repeating it opens them all. The record tree's groups start folded (UA9, U-D21), and a
 * folded group draws no records. One per call, so each click reads the choices the last one saved.
 */
export function openFoldedGroups() {
  const chevron = document.querySelector<HTMLElement>(
    '.tree-heading[aria-expanded="false"] > .tree-row > .tree-toggle',
  );
  if (chevron) fireEvent.click(chevron);
}

/** A tree item by its accessible name, opening folded groups on the way. */
export const findTreeItem = (name: string | RegExp) =>
  waitFor(() => {
    openFoldedGroups();
    return screen.getByRole("treeitem", { name });
  });
