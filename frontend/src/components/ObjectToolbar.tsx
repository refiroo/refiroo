import { useEffect, useState } from "react";
import type { CollectionQueryState, ObjectSort } from "../types";

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

export function ObjectToolbar({ query, placeholder, onChange }: {
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
    const states = Array.from(new Set(stateInput.split(",").map((value) => value.trim()).filter(Boolean)));
    if (states.join("\0") !== query.states.join("\0")) onChange({ ...query, states });
  }

  return <div className="collection-toolbar object-toolbar">
    <label className="search-box"><span>⌕</span><input aria-label="Search" value={searchInput} onChange={(event) => setSearchInput(event.target.value)} placeholder={placeholder} /></label>
    <label className="toolbar-field">States<input aria-label="States" value={stateInput} onChange={(event) => setStateInput(event.target.value)} onBlur={applyStates} onKeyDown={(event) => { if (event.key === "Enter") { event.preventDefault(); applyStates(); } }} placeholder="active, draft" /></label>
    <label className="toolbar-field">Sort<select aria-label="Sort" value={query.sort} onChange={(event) => onChange({ ...query, sort: event.target.value as ObjectSort })}>{SORTS.map((sort) => <option key={sort.value} value={sort.value}>{sort.label}</option>)}</select></label>
    <label className="toolbar-field">Per page<select aria-label="Page size" value={query.pageSize} onChange={(event) => onChange({ ...query, pageSize: Number(event.target.value) })}>{Array.from(new Set([10, 20, 50, 100, query.pageSize])).sort((a, b) => a - b).map((size) => <option key={size} value={size}>{size}</option>)}</select></label>
  </div>;
}
