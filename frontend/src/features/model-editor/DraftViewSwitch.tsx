/**
 * Editor | Canvas (0.17 CE1, PP-D80): the two structured views of one model draft, a control for the top of
 * both pages. The current view is pressed. The view a person used last on a draft is remembered in this
 * browser (`rdm:model-draft:view:v1`, a map of draft to view), and `draftOpensOn` answers which one a draft
 * opens on: the canvas from a workbook flow, else the last used, else the editor.
 */

import { useEffect } from "react";
import type { JourneyRef, RouteState } from "@/types";
import { readLocalPreference, writeLocalPreference } from "@/lib/localPreference";

export type DraftView = "editor" | "canvas";

export const DRAFT_VIEW_KEY = "rdm:model-draft:view:v1";
/** Drafts remembered; the oldest leave first. */
const REMEMBERED = 60;

type Remembered = Record<string, DraftView>;

const isRemembered = (value: unknown): value is Remembered =>
  typeof value === "object" &&
  value !== null &&
  !Array.isArray(value) &&
  Object.values(value).every((view) => view === "editor" || view === "canvas");

const readAll = (): Remembered => readLocalPreference(DRAFT_VIEW_KEY, {}, isRemembered);

/** The view last used on a draft in this browser, if any. */
export function lastDraftView(draftId: string): DraftView | undefined {
  return readAll()[draftId];
}

export function rememberDraftView(draftId: string, view: DraftView) {
  const all = readAll();
  if (all[draftId] === view) return;
  // Re-inserted last, so the entries that leave are the ones not used for longest.
  delete all[draftId];
  const kept = Object.entries({ ...all, [draftId]: view }).slice(-REMEMBERED);
  writeLocalPreference(DRAFT_VIEW_KEY, Object.fromEntries(kept));
}

/** Which view a draft opens on: the canvas from a workbook flow, else the one used last, else the editor. */
export function draftOpensOn(draftId: string, { fromWorkbook = false }: { fromWorkbook?: boolean } = {}): DraftView {
  return fromWorkbook ? "canvas" : (lastDraftView(draftId) ?? "editor");
}

/** The address of a draft's view, keeping the workspace and journey it was opened from. */
export function draftViewRoute(
  draftId: string,
  view: DraftView,
  from: { forWorkspace?: string; journey?: JourneyRef } = {},
): RouteState {
  return {
    kind: "settings",
    page: "model",
    draftId,
    editor: view === "canvas" ? { show: "canvas" } : {},
    ...(from.forWorkspace ? { forWorkspace: from.forWorkspace } : {}),
    ...(from.journey ? { journey: from.journey } : {}),
  };
}

export function DraftViewSwitch({
  draftId,
  view,
  onChange,
}: {
  draftId: string;
  /** The view this page is. */
  view: DraftView;
  /** Goes to the other view; the page navigates. */
  onChange: (view: DraftView) => void;
}) {
  // Being on a view is using it, however it was opened (the switch, the address or a journey).
  useEffect(() => rememberDraftView(draftId, view), [draftId, view]);
  return (
    <div className="segmented draft-view-switch" role="group" aria-label="View of this draft">
      {(
        [
          ["editor", "Editor"],
          ["canvas", "Canvas"],
        ] as const
      ).map(([id, label]) => (
        <button
          key={id}
          type="button"
          aria-pressed={view === id}
          onClick={() => {
            if (view === id) return;
            rememberDraftView(draftId, id);
            onChange(id);
          }}
        >
          {label}
        </button>
      ))}
    </div>
  );
}
