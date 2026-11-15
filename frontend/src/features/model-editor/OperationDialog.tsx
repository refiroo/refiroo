/**
 * The one surface for every editor operation (0.10 A4a, D38): the descriptor's fields as a form, or
 * its question for a removal. Sending applies the operations as one step; a refusal stays on the
 * surface with the server's reason, and for a released element the records it would affect (D39).
 * A stale version closes it: the editor asks what to do with the change (D41).
 *
 * One or two plain controls open as a popover under the control that started them (UX1, PP-D40),
 * holding the same fields and the same send; three or more, a preview or a field that needs room
 * keep the side sheet, as does an operation started from nowhere (no anchor).
 */

import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { errorMessage, isApiError } from "@/api/errors";
import type { DraftOperation, ModelDraftOutline } from "@/types";
import { AnchoredPopover } from "@/ui/AnchoredPopover";
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
  submitLabel,
  surfaceOf,
  visibleFields,
  type FieldValues,
  type OperationField,
  type OperationSurface,
  type OperationSpec,
  type OperationTarget,
} from "@/features/model-editor/operations";
import { CandidatesField } from "@/features/model-editor/CandidatesField";
import { ChoiceListField, type ChoiceOption } from "@/features/model-editor/ChoiceListField";
import { PairsField } from "@/features/model-editor/PairsField";

/** What the editor did with a step: applied, or held back because the draft moved on (D41). */
export type StepOutcome = "applied" | "stale";

export type RunStep = (operations: DraftOperation[]) => Promise<StepOutcome>;

/** A refusal in words (a step that cannot apply, or depends on another). */
export function refusalText(cause: unknown, _outline?: ModelDraftOutline): string {
  if (isApiError(cause, "OPERATION_HAS_DEPENDANTS")) {
    const dependants = ((cause.details ?? {}) as { dependants?: number[] }).dependants ?? [];
    return `Later steps (${dependants.join(", ")}) depend on this one.`;
  }
  return errorMessage(cause);
}

/** The values, the send and the refusal of one operation's form, whichever surface shows it. */
function useOperationForm({
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

  const preview = operation.preview?.(values, target as never, outline);
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
  return { values, set, pending, error, send, title, preview, missing, fields, submit };
}

export function OperationDialog({
  operation,
  target,
  outline,
  preset,
  anchor,
  run,
  onClose,
}: {
  operation: OperationSpec;
  target: OperationTarget;
  outline: ModelDraftOutline;
  /** Values chosen before the dialog opened, such as the matrix cell's column type. */
  preset?: FieldValues;
  /** The control the operation was started from; a small operation opens under it. */
  anchor?: HTMLElement | null;
  run: RunStep;
  onClose: () => void;
}) {
  // Settled when it opens: a popover whose control has gone from the page becomes the sheet.
  const [surface] = useState<OperationSurface>(() =>
    anchor?.isConnected && surfaceOf(operation, target, outline) === "popover" ? "popover" : "sheet",
  );
  // Focus goes back to the control once the popover has left: while it is open its focus scope holds
  // focus in, and the menu item the operation came from may be gone.
  const leave = () => {
    onClose();
    if (surface === "popover" && anchor)
      requestAnimationFrame(() => {
        if (anchor.isConnected) anchor.focus({ preventScroll: true });
      });
  };
  const form = useOperationForm({ operation, target, outline, preset, run, onClose: leave });
  const { values, set, pending, error, send, title, preview, missing, fields, submit } = form;
  const words = submitLabel(operation, target, outline, values, surface);

  if (operation.confirm)
    return (
      <ConfirmDialog
        title={title}
        confirmLabel={operation.label(target as never, outline)}
        pending={pending}
        error={error}
        onCancel={leave}
        onConfirm={() => void send()}
      >
        <p>{operation.confirm(target as never, outline)}</p>
      </ConfirmDialog>
    );

  const body = (
    <>
      {preview && <MatrixPreviewPane preview={preview} />}
      <OperationFields fields={fields} values={values} outline={outline} set={set} />
      {error && (
        <Notice tone="error" title="Not applied">
          {error}
        </Notice>
      )}
    </>
  );

  if (surface === "popover" && anchor)
    return (
      <OperationPopover
        anchor={anchor}
        title={title}
        wide={fields.some((field) => field.type === "checkboxes")}
        pending={pending}
        blocked={Boolean(missing)}
        submitWords={words}
        onSubmit={submit}
        onClose={leave}
      >
        {body}
      </OperationPopover>
    );

  return (
    <Modal title={title} eyebrow="Change the model" size={preview ? "wide" : "compact"} busy={pending} onClose={leave}>
      <form className={`dialog-body operation-form${preview ? " operation-form-beside" : ""}`} onSubmit={submit}>
        {body}
        <div className="dialog-actions">
          <button type="button" className="secondary" onClick={leave} disabled={pending}>
            Cancel
          </button>
          <button type="submit" className="primary" disabled={pending || Boolean(missing)}>
            {pending ? "Applying…" : words}
          </button>
        </div>
      </form>
    </Modal>
  );
}

/**
 * A small operation under the control that started it (UX1): the same form as the sheet in a popover,
 * Enter sends, Escape or a press outside closes, and focus goes back to the control. Not dismissed
 * while it is sending.
 */
function OperationPopover({
  anchor,
  title,
  wide,
  pending,
  blocked,
  submitWords,
  onSubmit,
  onClose,
  children,
}: {
  anchor: HTMLElement;
  title: string;
  wide: boolean;
  pending: boolean;
  blocked: boolean;
  submitWords: string;
  onSubmit: (event: FormEvent) => void;
  onClose: () => void;
  children: ReactNode;
}) {
  const formRef = useRef<HTMLFormElement>(null);
  useEffect(() => {
    formRef.current
      ?.querySelector<HTMLElement>("input:not([type='hidden']), select, textarea, button")
      ?.focus({ preventScroll: true });
  }, []);
  return (
    <AnchoredPopover
      anchor={anchor}
      title={title}
      onClose={onClose}
      dismissible={!pending}
      className={`popover control-popover editor-popover${wide ? " editor-popover-wide" : ""}`}
      titleClassName="editor-popover-title"
    >
      <form ref={formRef} className="editor-popover-form" onSubmit={onSubmit}>
        {children}
        <div className="editor-popover-actions">
          <button type="button" className="secondary" onClick={onClose} disabled={pending}>
            Cancel
          </button>
          <button type="submit" className="primary" disabled={pending || blocked}>
            {pending ? "Applying…" : submitWords}
          </button>
        </div>
      </form>
    </AnchoredPopover>
  );
}

/** The fields of an operation's form, each as its own control; the same in the popover and the sheet. */
function OperationFields({
  fields,
  values,
  outline,
  set,
}: {
  fields: (OperationField & { hint?: string })[];
  values: FieldValues;
  outline: ModelDraftOutline;
  set: (name: string, value: FieldValues[string]) => void;
}) {
  return (
    <>
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
                  {...(field.type === "text" && field.markEmpty && !String(values[field.name] ?? "").trim()
                    ? { "aria-invalid": true }
                    : {})}
                  value={String(values[field.name] ?? "")}
                  onChange={(event) => set(field.name, event.target.value)}
                />
              )
            }
          </FormField>
        );
      })}
    </>
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
