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
import { Modal } from "@/ui/Modal";
import { Notice } from "@/ui/Notice";
import {
  initialValues,
  missingField,
  visibleFields,
  type FieldValues,
  type OperationSpec,
  type OperationTarget,
} from "@/features/model-editor/operations";
import { elementLabel } from "@/features/model-editor/outline";
import { CandidatesField } from "@/features/model-editor/CandidatesField";

/** What the editor did with a step: applied, or held back because the draft moved on (D41). */
export type StepOutcome = "applied" | "stale";

export type RunStep = (operations: DraftOperation[]) => Promise<StepOutcome>;

/** A refusal in words: the migration a released element would need and what it would touch (D39). */
export function refusalText(cause: unknown, outline: ModelDraftOutline): string {
  if (isApiError(cause, "OPERATION_REQUIRES_MIGRATION")) {
    const details = (cause.details ?? {}) as {
      element?: Record<string, string>;
      impact?: { records?: number | string; values?: number | string; relationships?: number | string };
    };
    const impact = details.impact ?? {};
    const name = details.element ? elementLabel(outline, details.element) : "The element";
    return (
      `${name} is released, so this change needs a migration (planned for 1.0). ` +
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
  const fields = visibleFields(operation, target, outline, values);
  const set = (name: string, value: FieldValues[string]) => setValues((current) => ({ ...current, [name]: value }));
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!missing) void send();
  };
  return (
    <Modal title={title} eyebrow="Change the model" size="compact" busy={pending} onClose={onClose}>
      <form className="dialog-body operation-form" onSubmit={submit}>
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
                  <div className="operation-checkboxes">
                    {field.options.map((option) => (
                      <label key={option.value} className="checkbox">
                        <input
                          type="checkbox"
                          checked={chosen.includes(option.value)}
                          onChange={(event) =>
                            set(
                              field.name,
                              event.target.checked
                                ? [...chosen, option.value]
                                : chosen.filter((item) => item !== option.value),
                            )
                          }
                        />
                        {option.label}
                      </label>
                    ))}
                  </div>
                )}
              </FormField>
            );
          }
          return (
            <FormField key={field.name} label={field.label} help={field.hint}>
              {(control) =>
                field.type === "select" ? (
                  <select
                    {...control}
                    value={String(values[field.name] ?? "")}
                    onChange={(event) => set(field.name, event.target.value)}
                  >
                    {field.options.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
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
            {pending ? "Applying…" : "Apply"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
