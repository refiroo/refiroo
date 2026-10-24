/**
 * Refusals for a missing permission (`403 FORBIDDEN`, 0.12 Z5, D321, D330). The interface offers
 * only what the caller's roles allow, read once; a refusal means a role changed since, so the
 * permissions are read again and the page follows. The refusal itself is shown where it happened.
 */

const listeners = new Set<() => void>();

/** Called after each `403 FORBIDDEN`. */
export function onForbidden(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function reportForbidden() {
  for (const listener of listeners) listener();
}
