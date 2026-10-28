import type { ReactNode } from "react";
import type { CursorWindow } from "@/lib/hooks/useCursorWindow";
import { InlineError } from "@/ui/InlineError";
import { ScrollWindow, WindowPlaceholder, WindowSpacer } from "@/ui/ScrollWindow";

/**
 * The entries of a settings catalogue that a person scrolls and searches (ADR-030): people, groups
 * and clients. A `CursorWindow` holds the pages and `ScrollWindow` draws the entries by row number,
 * so a long catalogue is neither cut off nor loaded whole. `entry` draws one entry, normally a
 * `CatalogueEntry`; it is placed in the list item this component measures.
 */
export function CatalogueWindow<T extends { id: string }>({
  list,
  label,
  noun,
  pageSize,
  loadingText,
  emptyText,
  entry,
}: {
  list: CursorWindow<T>;
  /** Accessible name of the scrolling list. */
  label: string;
  noun: [string, string];
  pageSize: number;
  loadingText: string;
  emptyText: string;
  entry: (item: T) => ReactNode;
}) {
  const empty = !list.items.length;
  return (
    <div className="catalogue-window">
      {list.error && (
        <div className="catalogue-error">
          <InlineError message={list.error} onRetry={list.retry} />
        </div>
      )}
      {empty && !list.error && <p className="explorer-empty">{list.loading ? loadingText : emptyText}</p>}
      {!empty && (
        <ScrollWindow list={list} label={label} noun={noun} pageSize={pageSize} footer={false} edgeMarkers="partial">
          {(drawn) => (
            <ul className="catalogue-window-list" aria-label={label}>
              <WindowSpacer as="li" edge="before" height={drawn.before} />
              {drawn.rows.map(({ index, item, size }) =>
                item === undefined ? (
                  <WindowPlaceholder key={`placeholder-${index}`} as="li" index={index} size={size} />
                ) : (
                  <li key={item.id} ref={drawn.measure} data-row-key={item.id} data-row-index={index}>
                    {entry(item)}
                  </li>
                ),
              )}
              <WindowSpacer as="li" edge="after" height={drawn.after} />
            </ul>
          )}
        </ScrollWindow>
      )}
    </div>
  );
}
