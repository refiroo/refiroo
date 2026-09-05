/**
 * Structured error carried by every failing API call.
 *
 * `code` is the machine-readable identifier the backend returns in `error.code`; `details` is the
 * matching `error.details` payload, used by callers that act on a specific failure such as
 * `object_has_dependents`.
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
 * invariant, so `isApiError(cause, "version_conflict")` is the single way the UI recognises a
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
