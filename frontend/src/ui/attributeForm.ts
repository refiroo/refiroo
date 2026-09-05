/**
 * Reads a typed attribute value back out of a submitted form.
 *
 * Attribute values keep their declared types, so this converts the string a form control yields
 * into the boolean, number, JSON or text the model declares. An empty control means unset, which
 * is null rather than an empty string.
 */

import type { AttributeTypeDefinition } from "@/types";

export function parseAttributeValue(
  attribute: AttributeTypeDefinition,
  raw: FormDataEntryValue | null,
  checked = false,
): unknown {
  if (attribute.valueType === "boolean") return checked;
  if (raw === null || raw === "") return null;
  if (attribute.valueType === "integer" || attribute.valueType === "decimal") return Number(raw);
  if (attribute.valueType === "json") return JSON.parse(String(raw));
  return String(raw);
}

export function attributeValueFromForm(form: HTMLFormElement, attribute: AttributeTypeDefinition) {
  const input = form.elements.namedItem(attribute.key) as HTMLInputElement | HTMLTextAreaElement | null;
  return parseAttributeValue(
    attribute,
    input?.value ?? null,
    input instanceof HTMLInputElement && input.type === "checkbox" && input.checked,
  );
}
