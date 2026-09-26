/**
 * The one sort element of table-shaped lists (S4R3, revised). Every data column sorts from its
 * header, and every list with sort fields shows the same icon-only Sort menu in its toolbar,
 * offering those columns plus any further fields the model declares. The fields come from the
 * model (`model/fields.listSortFields`), never from the component.
 */

import { useState } from "react";
import { ActionMenu } from "@/ui/ActionMenu";
import { Icon } from "@/ui/Icon";

export type SortDirection = "ascending" | "descending";

/** The direction `sort` orders `field` in, or undefined when the list is sorted by another field. */
export function sortDirection(sort: string | undefined, field: string): SortDirection | undefined {
  if (!sort || sort.replace(/^-/, "") !== field) return undefined;
  return sort.startsWith("-") ? "descending" : "ascending";
}

/**
 * A list's sort state and the model-declared fields it may sort by. Every change goes through
 * `choose`, which also words the polite announcement of the new order.
 */
export function useTableSort({
  sort,
  fields,
  onSort,
  labelFor,
}: {
  sort: string | undefined;
  fields: readonly string[];
  onSort?: (sort: string) => void;
  labelFor: (field: string) => string;
}) {
  const [announcement, setAnnouncement] = useState("");
  const enabled = Boolean(onSort) && fields.length > 0;
  return {
    sort,
    fields: enabled ? fields : [],
    labelFor,
    announcement,
    choose(next: string) {
      onSort?.(next);
      const field = next.replace(/^-/, "");
      setAnnouncement(`Sorted by ${labelFor(field)}, ${sortDirection(next, field)}`);
    },
  };
}

export type TableSort = ReturnType<typeof useTableSort>;

/** Header content for `field`: a toggle when the field is sortable, otherwise its plain label. */
export function SortHeader({ field, label, sorting }: { field: string; label: string; sorting: TableSort }) {
  if (!sorting.fields.includes(field)) return <>{label}</>;
  const direction = sortDirection(sorting.sort, field);
  return (
    <button
      type="button"
      className={`column-sort${direction ? " is-sorted" : ""}`}
      aria-label={direction ? `${label}, sorted ${direction}` : undefined}
      onClick={() => sorting.choose(direction === "ascending" ? `-${field}` : field)}
    >
      {label}
      <span className="column-sort-icon" aria-hidden="true">
        <Icon
          name={direction === "ascending" ? "sort-ascending" : direction === "descending" ? "sort-descending" : "sort"}
          size={12}
        />
      </span>
    </button>
  );
}

/** The `aria-sort` of a sortable column header; undefined for columns the list is not sorted by. */
export function headerSort(sorting: TableSort, field: string): SortDirection | undefined {
  return sorting.fields.includes(field) ? sortDirection(sorting.sort, field) : undefined;
}

/** The icon-only menu: one radio item per sortable field, plus the direction; absent without fields. */
export function SortMenu({ sorting }: { sorting: TableSort }) {
  if (sorting.fields.length === 0) return null;
  const current = sorting.sort?.replace(/^-/, "") ?? "";
  const descending = sorting.sort?.startsWith("-") ?? false;
  const withField = (field: string) => (descending ? `-${field}` : field);
  const label = sorting.fields.includes(current)
    ? `Sort: ${sorting.labelFor(current)}, ${descending ? "descending" : "ascending"}`
    : "Sort";
  return (
    <div className="sort-menu">
      <ActionMenu
        label={label}
        icon="sort"
        tooltip="Sort"
        choices={[
          {
            id: "field",
            label: "Sort by",
            selected: `field:${current}`,
            options: sorting.fields.map((field) => ({ id: `field:${field}`, label: sorting.labelFor(field) })),
            onSelect: (id) => sorting.choose(withField(id.slice("field:".length))),
          },
          {
            id: "order",
            label: "Order",
            selected: descending ? "order:descending" : "order:ascending",
            options: [
              { id: "order:ascending", label: "Ascending" },
              { id: "order:descending", label: "Descending" },
            ],
            onSelect: (id) => sorting.choose(id === "order:descending" ? `-${current}` : current),
          },
        ]}
      />
    </div>
  );
}

/** Announces a changed order to screen readers; the list itself changes silently otherwise. */
export function SortAnnouncement({ sorting }: { sorting: TableSort }) {
  return (
    <span className="visually-hidden" role="status" aria-live="polite">
      {sorting.announcement}
    </span>
  );
}
