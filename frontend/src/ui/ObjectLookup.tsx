import { useEffect, useRef, useState } from "react";
import { api } from "@/api/client";
import { useCursorFeed } from "@/lib/hooks/useCursorFeed";
import { useDebouncedValue } from "@/lib/hooks/useDebouncedValue";
import type { ObjectItem } from "@/types";
import { InlineError } from "@/ui/InlineError";

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
  const search = useDebouncedValue(input.trim());
  const { items, loading, error, hasMore, loadMore, retry } = useCursorFeed<ObjectItem>(
    (cursor) => api.objects(objectTypeKey, { applicationKey, workspaceKey, search, cursor, pageSize: 20 }),
    [applicationKey, excludeId, objectTypeKey, search, workspaceKey],
    (previous, incoming) => [
      ...previous,
      ...incoming.filter((item) => item.id !== excludeId && !previous.some((existing) => existing.id === item.id)),
    ],
  );
  const priorWorkspace = useRef(workspaceKey);

  useEffect(() => {
    if (priorWorkspace.current === workspaceKey) return;
    priorWorkspace.current = workspaceKey;
    onChange(undefined);
  }, [workspaceKey, onChange]);

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
      {error && <InlineError message={error} onRetry={retry} />}
      {hasMore && !error && (
        <button type="button" className="load-more inline" disabled={loading} onClick={loadMore}>
          Load more results
        </button>
      )}
    </div>
  );
}
