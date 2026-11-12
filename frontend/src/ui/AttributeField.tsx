import { useId } from "react";
import type { AttributeTypeDefinition, ObjectTypeAttributeDefinition } from "@/types";

export function AttributeField({
  attribute,
  binding,
  value,
  autoFocus = false,
  prefix = "",
  mark,
  error,
}: {
  attribute: AttributeTypeDefinition;
  binding?: ObjectTypeAttributeDefinition;
  value?: unknown;
  autoFocus?: boolean;
  /** Put before the control's name, so two sets of attributes in one form do not share a name. */
  prefix?: string;
  /** Says on the label whether the field is needed: `*` for required, "(optional)" for the rest (0.17 PL2). */
  mark?: "required" | "optional";
  /** What is wrong with the value, in words, shown under the field instead of the browser's bubble. */
  error?: string;
}) {
  const errorId = useId();
  const markEl =
    mark === "required" ? (
      <span className="field-mark" aria-hidden="true">
        *
      </span>
    ) : mark === "optional" ? (
      <span className="field-optional">(optional)</span>
    ) : null;
  const errorEl = error ? (
    <p className="field-error" id={errorId} role="alert">
      {error}
    </p>
  ) : null;
  const helpText = String(binding?.ui?.helpText ?? attribute.ui?.helpText ?? "");
  const name = `${prefix}${attribute.key}`;
  if (attribute.valueType === "boolean") {
    return (
      <label className={error ? "checkbox field-has-error" : "checkbox"}>
        <input
          name={name}
          aria-label={attribute.name}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? errorId : undefined}
          type="checkbox"
          autoFocus={autoFocus}
          defaultChecked={value === undefined ? attribute.default === true : value === true}
          disabled={binding?.readOnly}
        />
        <span>
          {attribute.name}
          {markEl}
          {helpText && <small>{helpText}</small>}
          {errorEl}
        </span>
      </label>
    );
  }
  const common = {
    name,
    "aria-label": attribute.name,
    "aria-invalid": error ? true : undefined,
    "aria-describedby": error ? errorId : undefined,
    required: binding?.required,
    disabled: binding?.readOnly,
    autoFocus,
    defaultValue:
      value === undefined || value === null
        ? ""
        : attribute.valueType === "json"
          ? JSON.stringify(value, null, 2)
          : String(value),
  };
  return (
    <label className={error ? "field-has-error" : undefined}>
      {attribute.name}
      {markEl}
      {attribute.valueType === "longText" || attribute.valueType === "json" ? (
        <textarea {...common} rows={attribute.valueType === "json" ? 5 : 3} />
      ) : (
        <input
          {...common}
          type={
            attribute.valueType === "integer" || attribute.valueType === "decimal"
              ? "number"
              : attribute.valueType === "date"
                ? "date"
                : attribute.valueType === "dateTime"
                  ? "datetime-local"
                  : "text"
          }
          step={attribute.valueType === "decimal" ? "any" : undefined}
          min={attribute.validation?.minimum as number | undefined}
          max={attribute.validation?.maximum as number | undefined}
        />
      )}
      {helpText && <small>{helpText}</small>}
      {errorEl}
    </label>
  );
}
