/** The one question asked before unsaved input is thrown away: a dialog, a form, a route change. */
export const DISCARD_QUESTION = "Discard your unsaved changes?";

export function confirmDiscard(): boolean {
  return window.confirm(DISCARD_QUESTION);
}
