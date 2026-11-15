import { useEffect, useState, type ReactNode, type RefObject } from "react";
import { plural } from "@/lib/count";
import { useCursorFeed, type CursorPage } from "@/lib/hooks/useCursorFeed";
import { useDebouncedValue } from "@/lib/hooks/useDebouncedValue";
import { EntityList, type EntityRow } from "@/ui/EntityList";
import { Icon } from "@/ui/Icon";
import { SearchField } from "@/ui/SearchField";
import { SettingsLayout } from "@/ui/SettingsLayout";
import { FilterChip, SettingsPanel, SettingsTools } from "@/ui/SettingsParts";
import { settingsHead, type ListedPage } from "@/ui/settingsNavigation";

/** Entities read in a page of this size. */
const LIST_PAGE = 50;

/** The read of one page of an entity list; `includeTotal` asks for the count of the filter's matches. */
export type EntityRead<T> = (options: {
  q: string;
  active?: boolean;
  cursor?: string;
  pageSize: number;
  includeTotal?: boolean;
}) => Promise<CursorPage<T> & { totalCount?: number }>;

/**
 * The list an administration page opens with (people, clients, groups): a title, a search, with
 * `states` the Active and Deactivated chips with their counts, and the rows. The page names what it
 * lists and how a row reads; the search, the counts, the paging and the empty text are one.
 */
export function EntityListPage<T extends { id: string }>({
  page,
  title,
  description,
  noun,
  searchPlaceholder,
  states = false,
  read,
  row,
  onOpen,
  newLabel,
  newButtonRef,
  onNew,
  statusTrack = "0px",
}: {
  page: ListedPage;
  title: string;
  description: string;
  /** What is listed, in words: the count, the group title and the empty text are made of them. */
  noun: { one: string; many: string };
  searchPlaceholder: string;
  /** The entities are deactivated, never deleted: Active or Deactivated, each with its count. */
  states?: boolean;
  read: EntityRead<T>;
  /** What a row shows beyond its key and its opening. */
  row: (item: T) => Omit<EntityRow, "key" | "onOpen">;
  onOpen: (item: T) => void;
  /** The button that makes one; absent where the person cannot (no button is shown). */
  newLabel?: string;
  newButtonRef?: RefObject<HTMLButtonElement | null>;
  onNew?: () => void;
  /** The width of the last column where rows hold a pill. */
  statusTrack?: string;
}) {
  const [search, setSearch] = useState("");
  const [active, setActive] = useState(true);
  const [counts, setCounts] = useState<{ active?: number; deactivated?: number }>({});
  const q = useDebouncedValue(search.trim());
  const feed = useCursorFeed<T>(
    (cursor) => read({ q, active: states ? active : undefined, cursor, pageSize: LIST_PAGE }),
    [q, active],
  );
  const head = settingsHead(page);

  useEffect(() => {
    if (!states) return;
    let current = true;
    Promise.all([
      read({ q: "", active: true, pageSize: 1, includeTotal: true }),
      read({ q: "", active: false, pageSize: 1, includeTotal: true }),
    ]).then(
      ([on, off]) => current && setCounts({ active: on.totalCount, deactivated: off.totalCount }),
      () => undefined,
    );
    return () => {
      current = false;
    };
    // The counts are read once, as the page opens.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const total = !states || q ? undefined : active ? counts.active : counts.deactivated;
  const shown = feed.items.length;
  const count = total ?? shown;
  const state = active ? "active" : "deactivated";
  const heading = states
    ? `${active ? "Active" : "Deactivated"} ${noun.many}`
    : `${noun.many[0].toUpperCase()}${noun.many.slice(1)}`;
  const nothing = states
    ? q
      ? `No ${state} ${noun.one} matches “${q}”.`
      : `No ${state} ${noun.many}.`
    : q
      ? `No ${noun.one} matches “${q}”.`
      : `No ${noun.many} yet.`;
  return (
    <SettingsLayout
      {...head}
      title={title}
      description={description}
      actions={
        newLabel && (
          <button ref={newButtonRef} className="primary" onClick={onNew}>
            <Icon name="plus" /> {newLabel}
          </button>
        )
      }
    >
      <SettingsTools
        count={
          feed.loading && !shown
            ? undefined
            : `${count}${total === undefined && feed.hasMore ? "+" : ""} ${plural(count, noun.one, noun.many)}`
        }
      >
        <SearchField
          label={`Search ${noun.many}`}
          placeholder={searchPlaceholder}
          value={search}
          onChange={setSearch}
          clearOnEscape
        />
        {states && (
          <span className="filter-chips" role="group" aria-label="Show">
            <FilterChip selected={active} onSelect={() => setActive(true)}>
              Active{counts.active !== undefined && ` · ${counts.active}`}
            </FilterChip>
            <FilterChip selected={!active} onSelect={() => setActive(false)}>
              Deactivated{counts.deactivated !== undefined && ` · ${counts.deactivated}`}
            </FilterChip>
          </span>
        )}
      </SettingsTools>
      <SettingsPanel>
        <EntityList
          label={noun.many}
          statusTrack={statusTrack}
          groups={[
            {
              key: noun.many,
              title: heading,
              count: states ? count : `${shown}${feed.hasMore ? "+" : ""}`,
              loading: feed.loading && !shown,
              error: feed.error && !shown ? feed.error : undefined,
              onRetry: feed.retry,
              onEnd: feed.hasMore ? feed.loadMore : undefined,
              loadingMore: feed.loading && shown > 0,
              rows: feed.items.map((item) => ({ ...row(item), key: item.id, onOpen: () => onOpen(item) })),
            },
          ]}
          empty={nothing as ReactNode}
        />
      </SettingsPanel>
    </SettingsLayout>
  );
}
