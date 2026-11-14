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
 * invariant, so `isVersionConflict` is the single way the UI recognises a stale write.
 */
export function isApiError(cause: unknown, code?: string): cause is ApiError {
  return cause instanceof ApiError && (code === undefined || cause.code === code);
}

/** The refusals of a stale write (SR-D4): the one code, and the two that tell a second claim in one request apart. */
export const VERSION_CONFLICT_CODES = [
  "VERSION_CONFLICT",
  "CHANGE_SET_VERSION_CONFLICT",
  "RELATION_SET_VERSION_CONFLICT",
] as const;

/**
 * Whether a rejection is a stale write: any of the three version-conflict codes, or only those in
 * `codes` where a caller means one claim (the change set's, the relation set's). The mapping
 * targets read's `MAPPING_VERSION_CONFLICT` is a refused read, not a stale write, and is not one.
 */
export function isVersionConflict(
  cause: unknown,
  codes: readonly (typeof VERSION_CONFLICT_CODES)[number][] = VERSION_CONFLICT_CODES,
): cause is ApiError {
  return cause instanceof ApiError && isVersionConflictCode(cause.code, codes);
}

/** `isVersionConflict` for a code read off a refused item (a batch item's `code`) rather than a rejection. */
export function isVersionConflictCode(
  code: string | undefined,
  codes: readonly (typeof VERSION_CONFLICT_CODES)[number][] = VERSION_CONFLICT_CODES,
): boolean {
  return code !== undefined && (codes as readonly string[]).includes(code);
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
 * the field's name (`name`, `email`); empty for any other failure. A dialog shows each under its
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
