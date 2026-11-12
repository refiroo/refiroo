/**
 * The search, Display and Sort controls of a record page's related panel (0.17 UX1, PP-D40). A panel
 * of five rows or fewer folds them behind one ⋯ menu so a one-row table is not topped by three
 * controls; each menu item brings its control into the toolbar, so nothing becomes unreachable. A
 * larger panel, and a panel whose search is in use, shows them as they are.
 */

import { useEffect, useRef, useState, type ReactNode } from "react";
import { ActionMenu } from "@/ui/ActionMenu";

/** A panel with this many rows or fewer, all of them held, folds its tools. */
export const FOLDED_PANEL_ROWS = 5;

type Tool = "search" | "display" | "sort";

/** Whether a panel's list is small enough to fold its tools: every row held, none searched for. */
export function panelFolds(
  list: { items: readonly unknown[]; hasNext: boolean; hasPrevious: boolean },
  searched: boolean,
) {
  return !searched && !list.hasNext && !list.hasPrevious && list.items.length <= FOLDED_PANEL_ROWS;
}

export function PanelTools({
  folded,
  search,
  display,
  sort,
  sortable,
}: {
  folded: boolean;
  search: ReactNode;
  display: ReactNode;
  sort: ReactNode;
  /** The panel has fields to sort by; without them the menu has no Sort. */
  sortable: boolean;
}) {
  const [shown, setShown] = useState<ReadonlySet<Tool>>(new Set());
  const revealed = useRef<HTMLDivElement>(null);
  const [latest, setLatest] = useState<Tool>();
  // The control a menu item brought in takes focus, so the next key or press acts on it.
  useEffect(() => {
    if (latest)
      revealed.current
        ?.querySelector<HTMLElement>(`[data-panel-tool="${latest}"] input, [data-panel-tool="${latest}"] button`)
        ?.focus();
  }, [latest]);
  if (!folded)
    return (
      <>
        {search}
        {display}
        {sort}
      </>
    );
  const show = (tool: Tool) => {
    setShown((current) => new Set(current).add(tool));
    setLatest(tool);
  };
  return (
    <>
      <div ref={revealed} className="panel-tools">
        {shown.has("search") && <div data-panel-tool="search">{search}</div>}
        {shown.has("display") && <div data-panel-tool="display">{display}</div>}
        {shown.has("sort") && <div data-panel-tool="sort">{sort}</div>}
      </div>
      <ActionMenu
        label="Search, display and sort"
        tooltip="Search, display and sort"
        items={[
          {
            id: "search",
            label: "Search",
            icon: "search",
            disabled: shown.has("search"),
            onAction: () => show("search"),
          },
          {
            id: "display",
            label: "Display",
            icon: "sliders",
            disabled: shown.has("display"),
            onAction: () => show("display"),
          },
          ...(sortable
            ? [
                {
                  id: "sort",
                  label: "Sort",
                  icon: "sort" as const,
                  disabled: shown.has("sort"),
                  onAction: () => show("sort"),
                },
              ]
            : []),
        ]}
      />
    </>
  );
}
