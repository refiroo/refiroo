import { useLayoutEffect, useRef } from "react";

interface Guard {
  dirty: boolean;
  busy: boolean;
  discard: () => void;
}
const guards = new Set<Guard>();

/** Called before changing either route or history. Successful writes release their own guard. */
export function allowNavigation(): boolean {
  const active = [...guards];
  if (active.some((guard) => guard.busy)) {
    window.alert("A request is still in progress. Wait for it to finish before leaving.");
    return false;
  }
  if (active.some((guard) => guard.dirty) && !window.confirm("Discard your unsaved changes?")) return false;
  for (const guard of active) {
    guards.delete(guard);
    guard.discard();
  }
  return true;
}

/** Protect record editors on router navigation and native reload/tab close. No form data is stored. */
export function useNavigationGuard(dirty: boolean, busy: boolean, discard: () => void): () => void {
  const release = useRef<() => void>(() => undefined);
  useLayoutEffect(() => {
    const guard = { dirty, busy, discard };
    guards.add(guard);
    const unload = (event: BeforeUnloadEvent) => {
      if (!guards.has(guard) || (!guard.dirty && !guard.busy)) return;
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", unload);
    const remove = () => {
      guards.delete(guard);
      window.removeEventListener("beforeunload", unload);
    };
    release.current = remove;
    return remove;
  }, [dirty, busy, discard]);
  return () => release.current();
}
