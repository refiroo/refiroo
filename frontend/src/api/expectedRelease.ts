/**
 * The release the shown page was built on, named on its data writes (0.11 M6a, D63–D66).
 *
 * The page's data provider sets it for the context it shows: a workspace's live data names the
 * release its model was served from, a change set its pinned release; a publication, Settings and
 * the model editor name none. The client sends it in `X-Expected-Model-Release-Id` on writes over
 * records, relations and values, and on batches and imports, so a page built before an activation
 * cannot save under a release it never showed. A refusal is told to the listener (the shell's
 * toast); the form still shows it in place, as every refusal. So is a read refused because its
 * workspace or change set moved to another release while it was read (0.11 N1, D166).
 */
import type { ApiError } from "@/api/errors";

export const EXPECTED_RELEASE_HEADER = "X-Expected-Model-Release-Id";

let expected: string | undefined;
const listeners = new Set<(refusal: ApiError, read: boolean) => void>();

// The writes D65 names: records, relations and their values, moves and deletes, live and in a
// change set; batches, imports and type changes in a change set.
const DATA_WRITE =
  /^\/api\/v1\/(objects|relations|batches|imports)(\/|\?|$)|^\/api\/v1\/change-sets\/[^/]+\/restructurings/;

/** Name `releaseId` on the shown page's data writes from now on; `undefined` names none. */
export function setExpectedRelease(releaseId: string | undefined) {
  expected = releaseId;
}

/** The header a request to `path` carries, if any. */
export function expectedReleaseHeader(path: string, method: string | undefined): Record<string, string> {
  if (!expected || !method || method.toUpperCase() === "GET" || !DATA_WRITE.test(path)) return {};
  return { [EXPECTED_RELEASE_HEADER]: expected };
}

/** Called with each data write, or read (`read`), refused because its context now runs another
 * release. */
export function onModelReleaseChanged(listener: (refusal: ApiError, read: boolean) => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function reportModelReleaseChanged(refusal: ApiError, read = false) {
  for (const listener of listeners) listener(refusal, read);
}
