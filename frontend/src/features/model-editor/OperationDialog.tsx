/**
 * The one dialog for every editor operation (0.10 A4a, D38): the descriptor's fields as a form, or
 * its question for a removal. Sending applies the operations as one step; a refusal stays in the
 * dialog with the server's reason, and for a released element the records it would affect (D39).
 * A stale version closes the dialog: the editor asks what to do with the change (D41).
 */

import { useState, type FormEvent } from "react";
import { errorMessage, isApiError } from "@/api/errors";
import type { DraftOperation, ModelDraftOutline } from "@/types";
import { ConfirmDialog } from "@/ui/ConfirmDialog";
import { FormField } from "@/ui/FormField";
import { MatrixPreviewPane } from "@/features/model-editor/MatrixPreviewPane";
import { Modal } from "@/ui/Modal";
import { Notice } from "@/ui/Notice";
import { SearchField } from "@/ui/SearchField";
import {
  fieldOptions,
  initialValues,
  missingField,
  visibleFields,
  type FieldValues,
  type OperationSpec,
  type OperationTarget,
} from "@/features/model-editor/operations";
import { elementLabel } from "@/features/model-editor/outline";
import { CandidatesField } from "@/features/model-editor/CandidatesField";
import { ChoiceListField, type ChoiceOption } from "@/features/model-editor/ChoiceListField";
import { PairsField } from "@/features/model-editor/PairsField";

/** What the editor did with a step: applied, or held back because the draft moved on (D41). */
export type StepOutcome = "applied" | "stale";

export type RunStep = (operations: DraftOperation[]) => Promise<StepOutcome>;

/** A refusal in words: what holds a released element, or that its key is fixed (D39, AP-D28). */
export function refusalText(cause: unknown, outline: ModelDraftOutline): string {
  if (isApiError(cause, "OPERATION_REQUIRES_MIGRATION")) {
    const details = (cause.details ?? {}) as {
      element?: Record<string, string>;
      impact?: { records?: number | string; values?: number | string; relationships?: number | string };
    };
    const impact = details.impact ?? {};
    const name = details.element ? elementLabel(outline, details.element) : "The element";
    const held = [impact.records, impact.values, impact.relationships].some((count) => count && count !== 0);
    if (!held) return `${name} is released, so its key is fixed: integrations name it by its key. Nothing was applied.`;
    return (
      `${name} is released, so this change needs a migration: make it in the JSON view, and installing the release shows the migration to review. ` +
      `It would affect ${impact.records ?? 0} records, ${impact.values ?? 0} values and ` +
      `${impact.relationships ?? 0} relationships. Nothing was applied.`
    );
  }
  if (isApiError(cause, "OPERATION_HAS_DEPENDANTS")) {
    const dependants = ((cause.details ?? {}) as { dependants?: number[] }).dependants ?? [];
    return `Later steps (${dependants.join(", ")}) depend on this one.`;
  }
  return errorMessage(cause);
}

export function OperationDialog({
  operation,
  target,
  outline,
  preset,
  run,
  onClose,
}: {
  operation: OperationSpec;
  target: OperationTarget;
  outline: ModelDraftOutline;
  /** Values chosen before the dialog opened, such as the matrix cell's column type. */
  preset?: FieldValues;
  run: RunStep;
  onClose: () => void;
}) {
  const [values, setValues] = useState<FieldValues>(() => ({
    ...initialValues(operation, target, outline),
    ...preset,
  }));
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const title =
    operation.title?.(target as never, outline) ?? operation.label(target as never, outline).replace(/…$/, "");

  async function send() {
    setPending(true);
    setError("");
    try {
      await run(operation.build(values, target as never, outline));
      onClose();
    } catch (cause) {
      setError(refusalText(cause, outline));
    } finally {
      setPending(false);
    }
  }

  if (operation.confirm)
    return (
      <ConfirmDialog
        title={title}
        confirmLabel={operation.label(target as never, outline)}
        pending={pending}
        error={error}
        onCancel={onClose}
        onConfirm={() => void send()}
      >
        <p>{operation.confirm(target as never, outline)}</p>
      </ConfirmDialog>
    );

  const missing = missingField(operation, target, outline, values);
  const fields = visibleFields(operation, target, outline, values).map((field) => ({
    ...field,
    hint: typeof field.hint === "function" ? field.hint(values) : field.hint,
  }));
  // A select whose options follow an earlier choice moves to its first option when its value is no
  // longer offered (a related record's field after another block is chosen).
  const set = (name: string, value: FieldValues[string]) =>
    setValues((current) => {
      const next = operation.follow?.({ ...current, [name]: value }, current, name, outline) ?? {
        ...current,
        [name]: value,
      };
      for (const field of operation.fields?.(target as never, outline) ?? [])
        if (field.type === "select" && typeof field.options === "function" && field.name !== name) {
          const offered = field.options(next);
          if (!offered.some((option) => option.value === next[field.name])) next[field.name] = offered[0]?.value ?? "";
        }
      return next;
    });
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!missing) void send();
  };
  return (
    <Modal
      title={title}
      eyebrow="Change the model"
      size={operation.preview ? "wide" : "compact"}
      busy={pending}
      onClose={onClose}
    >
      <form
        className={`dialog-body operation-form${operation.preview ? " operation-form-beside" : ""}`}
        onSubmit={submit}
      >
        {operation.preview && <MatrixPreviewPane preview={operation.preview(values, target as never, outline)} />}
        {fields.map((field, index) => {
          if (field.type === "checkbox")
            return (
              <label key={field.name} className="checkbox">
                <input
                  type="checkbox"
                  checked={values[field.name] === true}
                  onChange={(event) => set(field.name, event.target.checked)}
                />
                {field.label}
              </label>
            );
          if (field.type === "criteria") {
            const current = values[field.name];
            return (
              <CandidatesField
                key={field.name}
                outline={outline}
                ends={field.ends}
                value={current && typeof current === "object" && !Array.isArray(current) ? current : {}}
                onChange={(next) => set(field.name, next)}
              />
            );
          }
          if (field.type === "checkboxes") {
            const chosen = Array.isArray(values[field.name]) ? (values[field.name] as string[]) : [];
            return (
              <FormField key={field.name} label={field.label} help={field.hint} group>
                {() => (
                  <SearchableCheckboxes
                    options={fieldOptions(field, values)}
                    chosen={chosen}
                    search={field.search}
                    onChange={(next) => set(field.name, next)}
                  />
                )}
              </FormField>
            );
          }
          const list = Array.isArray(values[field.name]) ? (values[field.name] as string[]) : [];
          if (field.type === "choices")
            return (
              <ChoiceListField
                key={field.name}
                label={field.label}
                hint={field.hint}
                ordered={field.ordered}
                empty={field.empty}
                options={fieldOptions(field, values)}
                value={list}
                onChange={(next) => set(field.name, next)}
              />
            );
          if (field.type === "pairs")
            return (
              <PairsField
                key={field.name}
                label={field.label}
                hint={field.hint}
                options={fieldOptions(field, values)}
                value={list}
                onChange={(next) => set(field.name, next)}
              />
            );
          if (field.type === "json")
            return (
              <FormField key={field.name} label={field.label} help={field.hint}>
                {(control) => (
                  <textarea
                    {...control}
                    className="mono operation-json"
                    rows={16}
                    spellCheck={false}
                    autoFocus={index === 0}
                    value={String(values[field.name] ?? "")}
                    onChange={(event) => set(field.name, event.target.value)}
                  />
                )}
              </FormField>
            );
          return (
            <FormField key={field.name} label={field.label} help={field.hint}>
              {(control) =>
                field.type === "select" ? (
                  <select
                    {...control}
                    value={String(values[field.name] ?? "")}
                    onChange={(event) => set(field.name, event.target.value)}
                  >
                    {groupedOptions(fieldOptions(field, values))}
                  </select>
                ) : (
                  <input
                    {...control}
                    autoFocus={index === 0}
                    required={field.required}
                    value={String(values[field.name] ?? "")}
                    onChange={(event) => set(field.name, event.target.value)}
                  />
                )
              }
            </FormField>
          );
        })}
        {error && (
          <Notice tone="error" title="Not applied">
            {error}
          </Notice>
        )}
        <div className="dialog-actions">
          <button type="button" className="secondary" onClick={onClose} disabled={pending}>
            Cancel
          </button>
          <button type="submit" className="primary" disabled={pending || Boolean(missing)}>
            {pending ? "Applying…" : (operation.submit?.(values) ?? "Apply")}
          </button>
        </div>
      </form>
    </Modal>
  );
}

/** A checkbox list with a search over the options' names; what is chosen stays chosen while hidden. */
function SearchableCheckboxes({
  options,
  chosen,
  search,
  onChange,
}: {
  options: ChoiceOption[];
  chosen: string[];
  search?: string;
  onChange: (next: string[]) => void;
}) {
  const [query, setQuery] = useState("");
  const term = query.trim().toLocaleLowerCase();
  const shown = term ? options.filter((option) => option.label.toLocaleLowerCase().includes(term)) : options;
  return (
    <>
      {search && (
        // Enter in the box searches; it never sends the form.
        <SearchField
          value={query}
          onChange={setQuery}
          label={search}
          placeholder={search}
          onSubmit={() => undefined}
          className="candidate-search"
        />
      )}
      {term && shown.length === 0 ? (
        <p className="muted">{`Nothing matches “${query.trim()}”.`}</p>
      ) : (
        <CheckboxList options={shown} chosen={chosen} onChange={onChange} />
      )}
    </>
  );
}

/**
 * A checkbox list. Options that share a `group` stand under its heading; an option with others `under`
 * it unfolds them beneath it in a disclosure, open while one of them is checked.
 */
function CheckboxList({
  options,
  chosen,
  onChange,
  under,
}: {
  options: ChoiceOption[];
  chosen: string[];
  onChange: (next: string[]) => void;
  under?: string;
}) {
  const level = options.filter((option) => option.under === under);
  const groups = [...new Set(level.map((option) => option.group ?? ""))];
  const toggle = (value: string, on: boolean) =>
    onChange(on ? [...chosen, value] : chosen.filter((item) => item !== value));
  return (
    <div className="operation-checkboxes">
      {groups.map((group) => {
        const items = level
          .filter((option) => (option.group ?? "") === group)
          .map((option) => {
            const inside = options.filter((other) => other.under === option.value);
            return (
              <div key={option.value} className="operation-checkbox">
                <label className="checkbox">
                  <input
                    type="checkbox"
                    checked={chosen.includes(option.value)}
                    onChange={(event) => toggle(option.value, event.target.checked)}
                  />
                  {option.label}
                  {option.note && (
                    <>
                      {" "}
                      <span className="operation-checkbox-note">{option.note}</span>
                    </>
                  )}
                </label>
                {inside.length > 0 && (
                  <details
                    className="operation-unfold"
                    open={inside.some((item) => chosen.includes(item.value)) || undefined}
                  >
                    <summary>{`Fields of ${option.label}`}</summary>
                    <CheckboxList options={options} chosen={chosen} onChange={onChange} under={option.value} />
                  </details>
                )}
              </div>
            );
          });
        return group ? (
          <div key={group} className="operation-checkbox-group" role="group" aria-label={group}>
            <span className="operation-checkbox-heading">{group}</span>
            {items}
          </div>
        ) : (
          items
        );
      })}
    </div>
  );
}

/** A select's options, under their groups where they have one. */
function groupedOptions(options: { value: string; label: string; group?: string }[]) {
  const groups = [...new Set(options.map((option) => option.group ?? ""))];
  return groups.map((group) => {
    const items = options
      .filter((option) => (option.group ?? "") === group)
      .map((option) => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ));
    return group ? (
      <optgroup key={group} label={group}>
        {items}
      </optgroup>
    ) : (
      items
    );
  });
}
