/**
 * The dialogs of a draft's workbook that its column and list panels open (0.17 CE1, PP-D3): Map to…,
 * a column's value map, the rows behind a dry run figure, and Adjust list… / Load as a list…. One hook
 * for the model editor and the canvas: the page calls `openMap`, `openValueMap`, `openRows` and
 * `openList` from the panel's callbacks and renders `dialogs` once.
 */

import { useState, type ReactNode } from "react";
import type { DraftSource } from "@/features/model-editor/useDraftSource";
import type { DraftEditing } from "@/features/model-editor/useDraftEditing";
import { AdjustListDialog } from "@/features/model-editor/AdjustListDialog";
import { DryRunRowsDialog, type DryRunRows } from "@/features/model-editor/DryRunPanel";
import { columnNumber, listHeader, sourceOfList } from "@/features/model-editor/lists";
import { MapColumnDialog, type MapStart } from "@/features/model-editor/MapColumnDialog";
import { dropChoice, usesOf, type ColumnUse } from "@/features/model-editor/mapping";
import { ValueMapDialog } from "@/features/model-editor/ValueMapDialog";
import { useToast } from "@/ui/Toast";

type SourceDialog =
  | { kind: "map"; start: MapStart }
  | { kind: "valueMap"; use: ColumnUse; header: string }
  | { kind: "rows"; rows: DryRunRows }
  | { kind: "list"; mode: "adjust" | "load"; sheet: string; block: number };

export interface SourceDialogs {
  /** Map to… a column; the target is the type it was dropped on (D76). */
  openMap: (sheet: string, header: string, target?: string) => void;
  openValueMap: (use: ColumnUse, header: string) => void;
  openRows: (rows: DryRunRows) => void;
  openList: (mode: "adjust" | "load", sheet: string, block: number) => void;
  /** The open dialog, to render once. */
  dialogs: ReactNode;
}

export function useSourceDialogs(editing: DraftEditing, source: DraftSource): SourceDialogs {
  const toast = useToast();
  const [dialog, setDialog] = useState<SourceDialog>();
  const { outline } = editing;
  const profile = source.profile?.profile;
  const close = () => setDialog(undefined);

  const openMap: SourceDialogs["openMap"] = (sheet, header, target) => {
    if (!outline) return;
    const used = usesOf(profile, sheet, header).find((use) => !use.binding.ignore);
    setDialog({
      kind: "map",
      start: target
        ? { sheet, header, ...dropChoice(profile, outline, sheet, target) }
        : { sheet, header, rowType: used?.source.objectTypeKey },
    });
  };

  let dialogs: ReactNode = null;
  if (outline && dialog?.kind === "map")
    dialogs = (
      <MapColumnDialog
        start={dialog.start}
        column={source.columns(dialog.start.sheet)?.find((item) => item.header === dialog.start.header)}
        headers={(source.columns(dialog.start.sheet) ?? []).flatMap((item) => (item.header ? [item.header] : []))}
        profile={profile}
        outline={outline}
        run={editing.run}
        onClose={close}
      />
    );
  else if (outline && dialog?.kind === "valueMap")
    dialogs = (
      <ValueMapDialog
        source={dialog.use.source.id}
        header={dialog.header}
        mapName={dialog.use.binding.valueMap}
        column={source.columns(dialog.use.source.sheet)?.find((item) => item.header === dialog.header)}
        profile={profile}
        outline={outline}
        run={editing.run}
        onClose={close}
      />
    );
  else if (dialog?.kind === "rows")
    dialogs = <DryRunRowsDialog draftId={editing.draftId} rows={dialog.rows} onClose={close} />;
  else if (dialog?.kind === "list") {
    const sheet = source.sheets.find((item) => item.name === dialog.sheet);
    const block = sheet?.blocks.find((item) => item.index === dialog.block);
    if (sheet && block) {
      const name = listHeader(block, source.columns(sheet.name));
      dialogs = (
        <AdjustListDialog
          mode={dialog.mode}
          draftId={editing.draftId}
          fileId={source.profile?.sourceFile?.id}
          sheet={sheet.name}
          header={name}
          block={block}
          listSource={sourceOfList(profile, sheet.name, block)}
          lastColumn={Math.max(...sheet.blocks.map((item) => columnNumber(item.lastColumn)))}
          send={editing.run}
          onDone={() => {
            close();
            toast(dialog.mode === "adjust" ? `${name} adjusted.` : `${name} loaded as a list.`);
          }}
          onClose={close}
        />
      );
    }
  }
  return {
    openMap,
    openValueMap: (use, header) => setDialog({ kind: "valueMap", use, header }),
    openRows: (rows) => setDialog({ kind: "rows", rows }),
    openList: (mode, sheet, block) => setDialog({ kind: "list", mode, sheet, block }),
    dialogs,
  };
}
