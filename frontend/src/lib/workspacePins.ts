/**
 * A person's shelf on a workspace's page (0.17 UX1): the lists they brought there, in their order. Kept in this
 * browser per workspace, as the other appearance choices are; a pin names an application and one of its views,
 * so it knows no type or key of any model, and a pin whose view the model no longer has is simply not drawn.
 */

import { useCallback, useState } from "react";
import { readLocalPreference, writeLocalPreference } from "@/lib/localPreference";

export type WorkspacePin = { applicationKey: string; viewKey: string };

const isPins = (value: unknown): value is WorkspacePin[] =>
  Array.isArray(value) &&
  value.every(
    (item) =>
      typeof item === "object" &&
      item !== null &&
      typeof (item as WorkspacePin).applicationKey === "string" &&
      typeof (item as WorkspacePin).viewKey === "string",
  );

export const pinKey = (pin: WorkspacePin) => `${pin.applicationKey}/${pin.viewKey}`;

const storageKey = (workspaceKey: string) => `rdm:workspace-pins:v1:${workspaceKey}`;

/** `pins` with the one at `from` moved to stand at `to`. */
export function movePin(pins: readonly WorkspacePin[], from: number, to: number): WorkspacePin[] {
  const next = [...pins];
  if (from < 0 || from >= next.length || to < 0 || to >= next.length || from === to) return next;
  const [moved] = next.splice(from, 1);
  next.splice(to, 0, moved);
  return next;
}

export function useWorkspacePins(workspaceKey: string) {
  const [state, setState] = useState(() => ({
    workspaceKey,
    pins: readLocalPreference<WorkspacePin[]>(storageKey(workspaceKey), [], isPins),
  }));
  // Another workspace's page: its own shelf, read when the key changes.
  const pins =
    state.workspaceKey === workspaceKey
      ? state.pins
      : readLocalPreference<WorkspacePin[]>(storageKey(workspaceKey), [], isPins);
  if (state.workspaceKey !== workspaceKey) setState({ workspaceKey, pins });
  const save = useCallback(
    (next: WorkspacePin[]) => {
      setState({ workspaceKey, pins: next });
      writeLocalPreference(storageKey(workspaceKey), next);
    },
    [workspaceKey],
  );
  return {
    pins,
    isPinned: (pin: WorkspacePin) => pins.some((item) => pinKey(item) === pinKey(pin)),
    toggle: (pin: WorkspacePin) =>
      save(
        pins.some((item) => pinKey(item) === pinKey(pin))
          ? pins.filter((item) => pinKey(item) !== pinKey(pin))
          : [...pins, pin],
      ),
    move: (from: number, to: number) => save(movePin(pins, from, to)),
  };
}
