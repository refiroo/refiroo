import { useEffect, useState } from "react";
import type { CollectionQueryState, ObjectSort } from "@/types";
import { Icon } from "@/ui/Icon";
import { SelectField } from "@/ui/Selection";

const SORTS: Array<{ value: ObjectSort; label: string }> = [
  { value: "name", label: "Name (A–Z)" },
  { value: "-name", label: "Name (Z–A)" },
  { value: "state", label: "State (A–Z)" },
  { value: "-state", label: "State (Z–A)" },
  { value: "createdAt", label: "Created (oldest)" },
  { value: "-createdAt", label: "Created (newest)" },
  { value: "updatedAt", label: "Updated (oldest)" },
  { value: "-updatedAt", label: "Updated (newest)" },
];

export function ObjectToolbar({
  query,
  placeholder,
  onChange,
}: {
  query: CollectionQueryState;
  placeholder: string;
  onChange: (query: CollectionQueryState) => void;
}) {
  const [searchInput, setSearchInput] = useState(query.search);
  const [stateInput, setStateInput] = useState(query.states.join(", "));

  useEffect(() => setSearchInput(query.search), [query.search]);
  useEffect(() => setStateInput(query.states.join(", ")), [query.states]);
  useEffect(() => {
    const timer = window.setTimeout(() => {
      const search = searchInput.trim();
      if (search !== query.search) onChange({ ...query, search });
    }, 250);
    return () => window.clearTimeout(timer);
  }, [searchInput, query, onChange]);

  function applyStates() {
    const states = Array.from(
      new Set(
        stateInput
          .split(",")
          .map((value) => value.trim())
          .filter(Boolean),
      ),
    );
    if (states.join("\0") !== query.states.join("\0")) onChange({ ...query, states });
  }

  return (
    <div className="collection-toolbar object-toolbar">
      <label className="search-box">
        <Icon name="search" />
        <input
          aria-label="Search"
          value={searchInput}
          onChange={(event) => setSearchInput(event.target.value)}
          placeholder={placeholder}
        />
      </label>
      <label className="toolbar-field">
        States
        <input
          aria-label="States"
          value={stateInput}
          onChange={(event) => setStateInput(event.target.value)}
          onBlur={applyStates}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              applyStates();
            }
          }}
          placeholder="active, draft"
        />
      </label>
      <SelectField
        className="toolbar-field"
        label="Sort"
        value={query.sort}
        options={SORTS.map((sort) => ({ id: sort.value, label: sort.label }))}
        onChange={(sort) => onChange({ ...query, sort: sort as ObjectSort })}
      />
      <SelectField
        className="toolbar-field"
        label="Per page"
        value={String(query.pageSize)}
        options={Array.from(new Set([10, 20, 50, 100, query.pageSize]))
          .sort((a, b) => a - b)
          .map((size) => ({ id: String(size), label: String(size) }))}
        onChange={(pageSize) => onChange({ ...query, pageSize: Number(pageSize) })}
      />
    </div>
  );
}
