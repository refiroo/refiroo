/**
 * Structured error carried by every failing API call.
 *
 * `code` is the machine-readable identifier the backend returns in `error.code`; `details` is the
 * matching `error.details` payload, used by callers that act on a specific failure such as
 * `OBJECT_HAS_DEPENDANTS`.
 */
export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
    public readonly details?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/**
 * Narrows an unknown rejection to an `ApiError`, optionally requiring a specific error code.
 *
 * Prefer this over reading `code` off an untyped cast. Optimistic concurrency is a product
 * invariant, so `isApiError(cause, "VERSION_CONFLICT")` is the single way the UI recognises a
 * stale write.
 */
export function isApiError(cause: unknown, code?: string): cause is ApiError {
  return cause instanceof ApiError && (code === undefined || cause.code === code);
}

/**
 * The message to show a user for an unknown rejection.
 *
 * `String(cause)` on an `Error` yields `"Error: …"`, which leaks the class name into the UI. This
 * returns the message alone and falls back to string conversion for values that are not errors.
 */
export function errorMessage(cause: unknown): string {
  return cause instanceof Error ? cause.message : String(cause);
}

/**
 * The type a record has now, when a request named another (D42, `409 object_type_changed`): its
 * type changed in the selected change set. A route follows the record to this type.
 */
export function changedObjectType(cause: unknown): string | undefined {
  if (!isApiError(cause, "OBJECT_TYPE_CHANGED")) return undefined;
  const current = (cause.details as { objectTypeKey?: unknown } | undefined)?.objectTypeKey;
  return typeof current === "string" ? current : undefined;
}

/**
 * The body fields a `422 REQUEST_VALIDATION_ERROR` refused, each with the engine's reason, keyed by
 * the field's name (`username`, `email`); empty for any other failure. A dialog shows each under its
 * field instead of the bare "Request validation failed".
 */
export function invalidFields(cause: unknown): Record<string, string> {
  if (!isApiError(cause, "REQUEST_VALIDATION_ERROR") || !Array.isArray(cause.details)) return {};
  const fields: Record<string, string> = {};
  for (const item of cause.details as { loc?: unknown[]; msg?: unknown }[]) {
    const loc = Array.isArray(item.loc) ? item.loc : [];
    const field = loc[0] === "body" ? loc[1] : undefined;
    if (typeof field === "string" && typeof item.msg === "string") fields[field] ??= item.msg;
  }
  return fields;
}

/**
 * `errorMessage`, naming each refused field by its label for a `422 REQUEST_VALIDATION_ERROR`
 * ("Name: String should have at most 200 characters") instead of "Request validation failed".
 */
export function refusalMessage(cause: unknown, labels: Record<string, string>): string {
  const fields = Object.entries(invalidFields(cause));
  if (!fields.length) return errorMessage(cause);
  return fields.map(([field, reason]) => `${labels[field] ?? field}: ${reason}.`).join(" ");
}
