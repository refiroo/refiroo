import { fireEvent, screen, within } from "@testing-library/react";

/**
 * Brings a folded related panel's control into its toolbar (`PanelTools`): a small panel hides them behind ⋯.
 * `panel` names the panel when a page holds several.
 */
export async function unfoldPanelTool(tool: "Search" | "Display" | "Sort", panel?: HTMLElement) {
  const scope = panel ? within(panel) : screen;
  fireEvent.click(await scope.findByRole("button", { name: "Search, display and sort" }));
  fireEvent.click(await screen.findByRole("menuitem", { name: tool }));
}
