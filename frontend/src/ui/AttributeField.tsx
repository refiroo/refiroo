import type { AttributeTypeDefinition, ObjectTypeAttributeDefinition } from "@/types";

export function AttributeField({
  attribute,
  binding,
  value,
  autoFocus = false,
}: {
  attribute: AttributeTypeDefinition;
  binding?: ObjectTypeAttributeDefinition;
  value?: unknown;
  autoFocus?: boolean;
}) {
  const helpText = String(binding?.ui?.helpText ?? attribute.ui?.helpText ?? "");
  const name = attribute.key;
  if (attribute.valueType === "boolean") {
    return (
      <label className="checkbox">
        <input
          name={name}
          type="checkbox"
          autoFocus={autoFocus}
          defaultChecked={value === undefined ? attribute.default === true : value === true}
          disabled={binding?.readOnly}
        />
        <span>
          {attribute.name}
          {helpText && <small>{helpText}</small>}
        </span>
      </label>
    );
  }
  const common = {
    name,
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
    <label>
      {attribute.name}
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
    </label>
  );
}
