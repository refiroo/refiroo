import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { ObjectItem } from "../types";

export function ObjectLookup({ objectTypeKey, applicationKey, workspaceKey, excludeId, value, selectedId, selectedLabel, required, onChange }: {
  objectTypeKey: string;
  applicationKey?: string;
  workspaceKey?: string;
  excludeId?: string;
  value?: ObjectItem;
  selectedId?: string | null;
  selectedLabel?: string;
  required?: boolean;
  onChange: (item: ObjectItem | undefined) => void;
}) {
  const [input, setInput] = useState("");
  const [search, setSearch] = useState("");
  const [items, setItems] = useState<ObjectItem[]>(value ? [value] : []);
  const [cursor, setCursor] = useState<string>();
  const [loading, setLoading] = useState(false);

  useEffect(() => { const timer = window.setTimeout(() => setSearch(input.trim()), 250); return () => clearTimeout(timer); }, [input]);
  useEffect(() => {
    let active = true;
    setLoading(true);
    api.objects(objectTypeKey, { applicationKey, workspaceKey, search, pageSize: 20 }).then((page) => {
      if (!active) return;
      setItems(page.items.filter((item) => item.id !== excludeId));
      setCursor(page.nextCursor ?? undefined);
    }).finally(() => active && setLoading(false));
    return () => { active = false; };
  }, [applicationKey, excludeId, objectTypeKey, search, workspaceKey]);

  async function loadMore() {
    if (!cursor) return;
    setLoading(true);
    try {
      const page = await api.objects(objectTypeKey, { applicationKey, workspaceKey, search, cursor, pageSize: 20 });
      setItems((current) => [...current, ...page.items.filter((item) => item.id !== excludeId && !current.some((existing) => existing.id === item.id))]);
      setCursor(page.nextCursor ?? undefined);
    } finally { setLoading(false); }
  }

  return <div className="object-lookup">
    <input aria-label="Search objects" value={input} onChange={(event) => setInput(event.target.value)} placeholder="Search by name or attribute…" />
    <select aria-label="Select object" required={required} value={value?.id ?? selectedId ?? ""} onChange={(event) => onChange(items.find((item) => item.id === event.target.value))}>
      <option value="">{loading && !items.length ? "Loading…" : "Select an object…"}</option>
      {(value?.id ?? selectedId) && !items.some((item) => item.id === (value?.id ?? selectedId)) && <option value={value?.id ?? selectedId ?? ""}>{value ? `${value.name} — ${value.applicationKey}` : selectedLabel ?? `Current object (${selectedId})`}</option>}
      {items.map((item) => <option key={item.id} value={item.id}>{item.name} — {item.applicationKey} / {item.path.map((part) => part.name).join(" / ")}</option>)}
    </select>
    {cursor && <button type="button" className="load-more inline" disabled={loading} onClick={loadMore}>Load more results</button>}
  </div>;
}
