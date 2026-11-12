/**
 * A type's preview and layout editor, mountable by any page that edits a draft (0.17 CE1, PP-D79): the
 * model editor's centre and the canvas's inspector show this one component. It takes the draft's editing
 * (`useDraftEditing`: the draft, its outline and its steps), the type, the mode and the records' source,
 * and nothing of the editor's panes or tabs. Layout changes go through `layout.ts` as one step each; a
 * layout form opens in the page's `DraftEditingDialogs`.
 */

import type { ReactNode } from "react";
import type { EditorMode, EngineModel } from "@/types";
import type { DraftEditing } from "@/features/model-editor/useDraftEditing";
import { TypePreview } from "@/features/model-editor/TypePreview";

export function DraftPreview({
  editing,
  mode,
  objectTypeKey,
  applicationKey,
  onApplication,
  activeModel,
  workspaceKey,
  onShowIssues,
  actions,
  compact,
  bandIn,
}: {
  editing: DraftEditing;
  /** The preview, read only, or the layout editor, where the page and table are laid out in place. */
  mode: EditorMode;
  objectTypeKey: string;
  /** The application the type was opened from; another that lists it stands in when this one does not. */
  applicationKey?: string;
  /** Switches to another application that holds the type (a selection changed). */
  onApplication?: (applicationKey: string) => void;
  /** The running model: the preview reads its records through it. */
  activeModel: EngineModel;
  /** The workspace the preview reads records from first. */
  workspaceKey: string;
  onShowIssues: () => void;
  /** The band's actions: where to go next, and in the layout editor undo and redo. */
  actions: ReactNode;
  /** One line, without the application and workspace choices (the canvas). */
  compact?: boolean;
  /** Where the page wants the band drawn, in place of its own bar. */
  bandIn?: HTMLElement | null;
}) {
  const { outline } = editing;
  if (!outline) return null;
  return (
    <TypePreview
      mode={mode}
      draftId={editing.draftId}
      version={outline.version}
      objectTypeKey={objectTypeKey}
      applicationKey={applicationKey}
      onApplication={onApplication}
      activeModel={activeModel}
      workspaceKey={workspaceKey}
      send={editing.runGuarded}
      onDialog={(operation, objectType) =>
        editing.openDialog({
          kind: "operation",
          operation,
          target: { on: "objectType", objectType },
          anchor: editing.anchor(),
        })
      }
      onShowIssues={onShowIssues}
      actions={actions}
      compact={compact}
      bandIn={bandIn}
    />
  );
}
