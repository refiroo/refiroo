import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import type { ObjectItem } from "../types";
import { InlineError } from "./AsyncState";

export function ObjectLookup({
  objectTypeKey,
  applicationKey,
  workspaceKey,
  excludeId,
  value,
  selectedId,
  selectedLabel,
  required,
  onChange,
}: {
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
  const [error, setError] = useState("");
  const [errorMode, setErrorMode] = useState<"load" | "more">("load");
  const [retryToken, setRetryToken] = useState(0);
  const priorWorkspace = useRef(workspaceKey);

  useEffect(() => {
    const timer = window.setTimeout(() => setSearch(input.trim()), 250);
    return () => clearTimeout(timer);
  }, [input]);
  useEffect(() => {
    if (priorWorkspace.current === workspaceKey) return;
    priorWorkspace.current = workspaceKey;
    setItems([]);
    setCursor(undefined);
    onChange(undefined);
  }, [workspaceKey, onChange]);
  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    api
      .objects(objectTypeKey, { applicationKey, workspaceKey, search, pageSize: 20 })
      .then((page) => {
        if (!active) return;
        setItems(page.items.filter((item) => item.id !== excludeId));
        setCursor(page.nextCursor ?? undefined);
        setError("");
      })
      .catch((cause) => {
        if (active) {
          setErrorMode("load");
          setError(cause instanceof Error ? cause.message : String(cause));
        }
      })
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [applicationKey, excludeId, objectTypeKey, retryToken, search, workspaceKey]);

  async function loadMore() {
    if (!cursor) return;
    setLoading(true);
    setError("");
    try {
      const page = await api.objects(objectTypeKey, { applicationKey, workspaceKey, search, cursor, pageSize: 20 });
      setItems((current) => [
        ...current,
        ...page.items.filter((item) => item.id !== excludeId && !current.some((existing) => existing.id === item.id)),
      ]);
      setCursor(page.nextCursor ?? undefined);
      setError("");
    } catch (cause) {
      setErrorMode("more");
      setError(cause instanceof Error ? cause.message : String(cause));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="object-lookup">
      <input
        aria-label="Search objects"
        value={input}
        onChange={(event) => setInput(event.target.value)}
        placeholder="Search by name or attribute…"
      />
      <select
        aria-label="Select object"
        required={required}
        disabled={Boolean(error)}
        value={value?.id ?? selectedId ?? ""}
        onChange={(event) => onChange(items.find((item) => item.id === event.target.value))}
      >
        <option value="">{loading && !items.length ? "Loading…" : "Select an object…"}</option>
        {(value?.id ?? selectedId) && !items.some((item) => item.id === (value?.id ?? selectedId)) && (
          <option value={value?.id ?? selectedId ?? ""}>
            {value ? `${value.name} — ${value.applicationKey}` : (selectedLabel ?? `Current object (${selectedId})`)}
          </option>
        )}
        {items.map((item) => (
          <option key={item.id} value={item.id}>
            {item.name} — {item.applicationKey} / {item.path.map((part) => part.name).join(" / ")}
          </option>
        ))}
      </select>
      {error && (
        <InlineError
          message={error}
          onRetry={() => (errorMode === "more" ? void loadMore() : setRetryToken((current) => current + 1))}
        />
      )}
      {cursor && !error && (
        <button type="button" className="load-more inline" disabled={loading} onClick={loadMore}>
          Load more results
        </button>
      )}
    </div>
  );
}
