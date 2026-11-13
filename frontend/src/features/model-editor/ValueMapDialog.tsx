/**
 * A column's value map (0.10 A5b, D76 `setValueMap`): text found in the file and what it becomes
 * before it is converted or matched, empty meaning no value. A new map starts from the column's
 * placeholders (D70) sent to empty. Saving is one step; so is removing the map.
 */

import { useState } from "react";
import type { DraftProfileDocument, ModelDraftOutline, SourceColumn } from "@/types";
import { IconButton } from "@/ui/IconButton";
import { Modal } from "@/ui/Modal";
import { Notice } from "@/ui/Notice";
import { refusalText, type RunStep } from "@/features/model-editor/OperationDialog";
import { keyFromLabel } from "@/model/outline";

type Entry = { text: string; value: string };

export function ValueMapDialog({
  source,
  header,
  mapName,
  column,
  suggested,
  profile,
  outline,
  run,
  onClose,
}: {
  source: string;
  header: string;
  /** The map the column reads through, if any. */
  mapName: string | null | undefined;
  column: SourceColumn | undefined;
  /** Wrong values a refusal named (0.17 PL3b): the map starts from them, "Becomes" empty, with their rows. */
  suggested?: { text: string; rows?: number }[];
  profile: DraftProfileDocument | null | undefined;
  outline: ModelDraftOutline;
  run: RunStep;
  onClose: () => void;
}) {
  const maps = profile?.valueMaps ?? {};
  const name = mapName ?? keyFromLabel(header, new Set(Object.keys(maps)));
  const [entries, setEntries] = useState<Entry[]>(() => {
    const existing = mapName ? maps[mapName] : undefined;
    if (existing)
      return Object.entries(existing).map(([text, value]) => ({ text, value: value === null ? "" : String(value) }));
    const found =
      suggested?.map((item) => ({ text: item.text, value: "" })) ??
      column?.placeholders.map((item) => ({ text: item.value, value: "" })) ??
      [];
    return found.length ? found : [{ text: "", value: "" }];
  });
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const counts = new Map([
    ...(column?.placeholders.map((item): [string, number] => [item.value, item.count]) ?? []),
    ...(suggested ?? []).flatMap((item): [string, number][] => (item.rows ? [[item.text, item.rows]] : [])),
  ]);

  async function send(remove: boolean) {
    setPending(true);
    setError("");
    try {
      const filled = entries.filter((item) => item.text !== "");
      await run([
        remove
          ? { kind: "setValueMap", name, entries: null }
          : {
              kind: "setValueMap",
              name,
              entries: Object.fromEntries(filled.map((item) => [item.text, item.value === "" ? null : item.value])),
              source,
              column: header,
            },
      ]);
      onClose();
    } catch (cause) {
      setError(refusalText(cause, outline));
    } finally {
      setPending(false);
    }
  }

  const change = (index: number, part: Partial<Entry>) =>
    setEntries((current) => current.map((item, position) => (position === index ? { ...item, ...part } : item)));
  return (
    <Modal
      title={`Value map of “${header}”`}
      eyebrow="Map values"
      description="Text in the file and what it becomes before it is read. Leave “Becomes” empty for no value."
      busy={pending}
      size="compact"
      onClose={onClose}
    >
      <form
        className="dialog-body value-map"
        onSubmit={(event) => {
          event.preventDefault();
          if (!pending) void send(false);
        }}
      >
        <table className="value-map-entries">
          <thead>
            <tr>
              <th scope="col">Text in the file</th>
              <th scope="col">Becomes</th>
              <th scope="col">
                <span className="visually-hidden">Remove</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {entries.map((item, index) => (
              <tr key={index}>
                <td>
                  <input
                    aria-label={`Text ${index + 1}`}
                    value={item.text}
                    onChange={(event) => change(index, { text: event.target.value })}
                  />
                  {counts.has(item.text) && <span className="muted"> {counts.get(item.text)} rows</span>}
                </td>
                <td>
                  <input
                    aria-label={`Becomes ${index + 1}`}
                    value={item.value}
                    placeholder="empty"
                    onChange={(event) => change(index, { value: event.target.value })}
                  />
                </td>
                <td>
                  <IconButton
                    icon="close"
                    label={`Remove ${item.text || `entry ${index + 1}`}`}
                    onClick={() => setEntries((current) => current.filter((_, position) => position !== index))}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <button
          type="button"
          className="secondary"
          onClick={() => setEntries((current) => [...current, { text: "", value: "" }])}
        >
          Add a value
        </button>
        {error && (
          <Notice tone="error" title="Not saved">
            {error}
          </Notice>
        )}
        <div className="dialog-actions">
          {mapName && (
            <button type="button" className="danger-outline" disabled={pending} onClick={() => void send(true)}>
              Remove the map
            </button>
          )}
          <button type="button" className="secondary" onClick={onClose} disabled={pending}>
            Cancel
          </button>
          <button type="submit" className="primary" disabled={pending}>
            {pending ? "Saving…" : "Save"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
