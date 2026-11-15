/**
 * Reading a value of unknown shape (SR4, F7): the engine's JSON documents (a model definition, a profile, a
 * job's parameters) are read into the shape a screen needs, and a missing or wrong-typed part reads as empty.
 * Only helpers that behave identically live here; a variant that differs is named for the difference.
 * Kept apart on purpose: `TreeView`'s label text (booleans spelt "Yes"/"No"), `operations.ts`' form-value
 * `text(values, name)`, `WebhooksPage`'s `String` conversion and `structureParse`'s type guard.
 */

/** A string, else "". */
export function text(value: unknown): string {
  return typeof value === "string" ? value : "";
}

/** A string trimmed, else "". */
export function trimmedText(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

/** A string that is not empty, else undefined: an empty text reads as absent. */
export function presentText(value: unknown): string | undefined {
  return typeof value === "string" && value ? value : undefined;
}

/** An array, else an empty one. */
export function list(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

/** An array read as a list of strings (its items are not checked), else an empty one. */
export function stringList(value: unknown): string[] {
  return Array.isArray(value) ? (value as string[]) : [];
}

/** A plain object, else an empty one (an array is not one). */
export function record(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}
