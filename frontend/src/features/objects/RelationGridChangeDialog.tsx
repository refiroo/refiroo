/**
 * Change relationship values of the selected rows of a relationships grid (0.13 RG), built as the
 * collection's Change values is: the same dialog shell, the attribute's own field control, "Set to" or
 * "Clear", a preview of what applying would do and the refusals listed. The preview is the engine's
 * dry run (`POST /relations/grid-change`), read when the choices change, never before the dialog is
 * opened: how many relationships change, already hold the value and are not linked (which can be
 * linked too). Apply is all or none.
 */

import { useEffect, useRef, useState } from "react";
import { errorMessage, isApiError } from "@/api/errors";
import type { Noun } from "@/features/jobs/BatchOutcome";
import { targetText } from "@/features/objects/BulkJobDialog";
import { useDataApi } from "@/features/workspaces/WorkspaceDataContext";
import type { RecordSelection } from "@/lib/recordSelection";
import type {
  AttributeTypeDefinition,
  CollectionFilter,
  RelationGridChangeInput,
  RelationGridChangeResult,
  RelationGridColumn,
} from "@/types";
import { AttributeField } from "@/ui/AttributeField";
import { attributeValueFromForm } from "@/ui/attributeForm";
import { Choice } from "@/ui/Choice";
import { DescriptionList } from "@/ui/DescriptionList";
import { FormField } from "@/ui/FormField";
import { Modal } from "@/ui/Modal";
import { Notice } from "@/ui/Notice";
import { Section } from "@/ui/Section";

const count = (value: number) => value.toLocaleString("en");

interface Preview {
  key: string;
  result?: RelationGridChangeResult;
  error?: string;
}

export function RelationGridChangeDialog({
  applicationKey,
  viewKey,
  workspaceKey,
  noun,
  toNoun,
  attributes,
  columns,
  selection,
  selected,
  search,
  filters,
  onClose,
  onApplied,
}: {
  applicationKey: string;
  viewKey: string;
  workspaceKey: string;
  /** The rows' type, singular and plural. */
  noun: Noun;
  /** The related records' type, singular and plural. */
  toNoun: Noun;
  /** The attributes a value can be set on. */
  attributes: AttributeTypeDefinition[];
  /** The column records shown. */
  columns: RelationGridColumn[];
  selection: RecordSelection;
  selected: number;
  search: string;
  filters: CollectionFilter[];
  onClose: () => void;
  onApplied: () => void;
}) {
  const api = useDataApi();
  const form = useRef<HTMLFormElement>(null);
  const [attributeKey, setAttributeKey] = useState(attributes[0]?.key ?? "");
  const [where, setWhere] = useState("all");
  const [mode, setMode] = useState<"set" | "clear">("set");
  const [typed, setTyped] = useState<Record<string, unknown>>({});
  const [invalid, setInvalid] = useState(false);
  const [link, setLink] = useState(false);
  const [preview, setPreview] = useState<Preview>();
  const [applying, setApplying] = useState(false);
  const [refusal, setRefusal] = useState<{ message: string; lines: string[] }>();

  const attribute = attributes.find((item) => item.key === attributeKey) ?? attributes[0];
  const value: unknown =
    mode === "clear" ? null : (typed[attribute?.key ?? ""] ?? (attribute?.valueType === "boolean" ? false : undefined));
  const toObjectIds = where === "all" ? columns.map((column) => column.id) : [where];
  const body: RelationGridChangeInput | undefined =
    attribute && value !== undefined && !invalid && toObjectIds.length > 0
      ? {
          applicationKey,
          viewKey,
          workspaceKey,
          ...(selection.mode === "ids"
            ? { fromObjectIds: [...selection.ids.keys()] }
            : {
                allMatching: true,
                exceptObjectIds: [...selection.except],
                search: search || undefined,
                filters: filters.map(({ field, operator, value: wanted }) => ({ field, operator, value: wanted })),
              }),
          toObjectIds,
          attributeTypeKey: attribute.key,
          value,
          linkMissing: link,
        }
      : undefined;
  const key = JSON.stringify(body ?? null);

  // The dry run follows the choices, a moment after the last one.
  useEffect(() => {
    if (!body) return;
    let current = true;
    const timer = window.setTimeout(() => {
      api
        .relationGridChange({ ...body, dryRun: true })
        .then((result) => current && setPreview({ key, result }))
        .catch((cause) => current && setPreview({ key, error: errorMessage(cause) }));
    }, 300);
    return () => {
      current = false;
      window.clearTimeout(timer);
    };
    // `key` stands for the body; the api is stable for the mounted data.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  const counted = preview?.key === key ? preview : undefined;
  const result = counted?.result;
  const writes = result ? result.change + (link ? result.missing : 0) : 0;
  const blocked = !body || !result || writes === 0 || result.refused.length > 0 || applying;

  function read() {
    if (!form.current || !attribute || mode === "clear") return;
    try {
      const next = attributeValueFromForm(form.current, attribute);
      setInvalid(false);
      setTyped((current) => ({ ...current, [attribute.key]: next === null ? undefined : next }));
    } catch {
      setInvalid(true);
    }
  }

  async function apply() {
    if (!body || blocked) return;
    setApplying(true);
    setRefusal(undefined);
    try {
      await api.relationGridChange({ ...body, dryRun: false });
      onApplied();
      onClose();
    } catch (cause) {
      const refused = isApiError(cause, "RELATION_BATCH_REFUSED")
        ? (cause.details as { items?: { message: string }[] } | undefined)?.items
        : undefined;
      setRefusal({ message: errorMessage(cause), lines: refused?.map((item) => item.message) ?? [] });
      setApplying(false);
    }
  }

  const shown = value === true ? "Yes" : value === false ? "No" : value === null ? "empty" : String(value ?? "");
  return (
    <Modal
      title="Change relationship values"
      icon="pencil"
      description={targetText(selection, selected, noun)}
      size="wide"
      busy={applying}
      onClose={onClose}
    >
      <form
        ref={form}
        aria-label="Change relationship values"
        className="dialog-form"
        onChange={read}
        onSubmit={(event) => {
          event.preventDefault();
          void apply();
        }}
      >
        <section className="bulk-changes" aria-label="Value to change">
          <fieldset className="bulk-change-card" disabled={applying}>
            <legend>Value</legend>
            <FormField label="Attribute of the relationship">
              {(control) => (
                <select {...control} value={attribute?.key} onChange={(event) => setAttributeKey(event.target.value)}>
                  {attributes.map((item) => (
                    <option key={item.key} value={item.key}>
                      {item.name}
                    </option>
                  ))}
                </select>
              )}
            </FormField>
            <FormField label={`At ${toNoun[1]}`}>
              {(control) => (
                <select {...control} value={where} onChange={(event) => setWhere(event.target.value)}>
                  <option value="all">
                    All {count(columns.length)} shown {toNoun[1]}
                  </option>
                  {columns.map((column) => (
                    <option key={column.id} value={column.id}>
                      {column.label}
                    </option>
                  ))}
                </select>
              )}
            </FormField>
            <div className="bulk-change-head">
              <Choice
                name="grid-change-mode"
                value={mode}
                options={[
                  ["set", "Set to"],
                  ["clear", "Clear"],
                ]}
                onChange={setMode}
              />
            </div>
            {attribute &&
              (mode === "set" ? (
                <AttributeField key={attribute.key} attribute={attribute} value={typed[attribute.key]} />
              ) : (
                <p className="bulk-change-note">
                  {attribute.name} is emptied at the chosen {toNoun[1]}.
                </p>
              ))}
          </fieldset>
        </section>
        <Section title="The preview" description="Nothing is written until you apply.">
          {value === undefined && attribute && <p className="bulk-hint">Enter a value, or choose Clear.</p>}
          {invalid && <Notice tone="error">That is not a valid value.</Notice>}
          {counted?.error && <Notice tone="error">{counted.error}</Notice>}
          {body && !result && !counted?.error && <p className="bulk-hint">Counting…</p>}
          {result && (
            <>
              <DescriptionList
                className="compact"
                items={[
                  { term: "Would change", value: count(result.change) },
                  { term: `Already ${shown}`, value: count(result.same) },
                  { term: `Not linked to the ${toNoun[0]}`, value: count(result.missing) },
                ]}
              />
              {result.missing > 0 && (
                <label className="checkbox">
                  <input type="checkbox" checked={link} onChange={(event) => setLink(event.target.checked)} />
                  <span>
                    Also link them, with {attribute?.name} {shown}
                  </span>
                </label>
              )}
              {result.refused.length > 0 && (
                <Notice
                  tone="error"
                  title={`${count(result.refused.length)} would be refused, so nothing can be changed yet`}
                >
                  <ul>
                    {result.refused.slice(0, 5).map((item) => (
                      <li key={`${item.index}:${item.relationId ?? item.toObjectId}`}>{item.message}</li>
                    ))}
                  </ul>
                </Notice>
              )}
            </>
          )}
        </Section>
        {refusal && (
          <Notice tone="error" title="Nothing was changed" focusOnMount>
            <p>{refusal.message}</p>
            {refusal.lines.length > 0 && (
              <ul>
                {refusal.lines.slice(0, 5).map((line) => (
                  <li key={line}>{line}</li>
                ))}
              </ul>
            )}
          </Notice>
        )}
        <div className="dialog-actions bulk-actions">
          <span className="bulk-summary" aria-live="polite">
            {result ? `Applying changes ${count(writes)} ${writes === 1 ? "relationship" : "relationships"}` : ""}
          </span>
          <button type="button" className="ghost" disabled={applying} onClick={onClose}>
            Cancel
          </button>
          <button className="primary" disabled={blocked}>
            {applying ? "Applying…" : "Apply"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
