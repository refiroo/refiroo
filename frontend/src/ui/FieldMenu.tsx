/**
 * A short menu of fields to pick one from (0.9 K6a): grouped, each with a glyph for its kind and
 * "Active" on one already in use, with a search once the menu would scroll (D164). ＋ Filter and
 * Change values' ＋ Change a field open it.
 */

import { useState } from "react";
import { Icon, type IconName } from "@/ui/Icon";

export interface FieldMenuItem {
  key: string;
  label: string;
  icon: IconName;
  group: string;
  active?: boolean;
  /** Said at the row's end instead of Active, such as the field's kind. */
  hint?: string;
}

/** More fields than this, and the menu gets a search (D164). */
const SEARCH_FROM = 9;

export function FieldMenu({
  label,
  items,
  onPick,
}: {
  label: string;
  items: readonly FieldMenuItem[];
  onPick: (key: string) => void;
}) {
  const [query, setQuery] = useState("");
  const term = query.trim().toLowerCase();
  const shown = items.filter((item) => !term || item.label.toLowerCase().includes(term));
  const groups = [...new Set(items.map((item) => item.group))];
  const searchable = items.length >= SEARCH_FROM;
  const first = shown[0]?.key;
  return (
    <div className="filter-menu" role="group" aria-label={label}>
      {searchable && (
        <label className="record-checklist-search">
          <Icon name="search" size={15} />
          <input
            type="search"
            aria-label={label}
            placeholder={`${label}…`}
            value={query}
            autoFocus
            onChange={(event) => setQuery(event.target.value)}
          />
        </label>
      )}
      {groups.map((group) => {
        const inGroup = shown.filter((item) => item.group === group);
        if (!inGroup.length) return null;
        return (
          <div key={group} role="group" aria-label={group}>
            {groups.length > 1 && <p className="filter-menu-heading">{group}</p>}
            {inGroup.map((item) => (
              <button
                key={item.key}
                type="button"
                className="filter-menu-item"
                autoFocus={!searchable && item.key === first}
                onClick={() => onPick(item.key)}
              >
                <span className="filter-menu-icon" aria-hidden="true">
                  <Icon name={item.icon} size={14} />
                </span>
                <span className="filter-menu-label">{item.label}</span>
                {item.active ? (
                  <>
                    <span className="filter-menu-active" aria-hidden="true">
                      Active
                    </span>
                    <span className="visually-hidden">, applied</span>
                  </>
                ) : (
                  item.hint && <span className="filter-menu-hint">{item.hint}</span>
                )}
              </button>
            ))}
          </div>
        );
      })}
      {!shown.length && <p className="record-checklist-empty">Nothing matches “{query.trim()}”.</p>}
    </div>
  );
}
