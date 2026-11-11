/**
 * Hands what a list view shows to the shell, for its Export (0.9 J1u, 0.17 EX1): one hook for every
 * view kind, called by the view host, so a page's Export knows its view and what the page narrowed
 * it to. A kind's own state (a table's columns) comes through `extra`, which that view fills through `extraRef`.
 */

import { useEffect, type MutableRefObject } from "react";
import type { ExportStart } from "@/features/jobs/ExportDialog";
import { exportViewStart } from "@/features/jobs/exportRequest";
import { useWorkspaceData } from "@/features/workspaces/WorkspaceDataContext";
import type { ViewComponentProps } from "./types";

/** What only one kind of view knows: a table's columns as its Display shows them. */
export interface ExportViewExtra {
  columns?: { shown: readonly string[]; hidden: readonly string[] };
  /**
   * What the page holds of the file, for the dialog's count line: rows and columns, or records where
   * the kind has no columns. A part the page does not know yet is absent.
   */
  size?: ExportViewSize;
}

/** The size of the file "This view" writes: the page's total, not what it has loaded. */
export interface ExportViewSize {
  rows?: number;
  columns?: number;
  /** A view of records (a tree, a mapping grid): the line says records, not rows. */
  records?: number;
}

/** What a list's total is, once it is read: undefined while loading or when the list does not know it. */
export function windowTotal(list: {
  loading: boolean;
  totalCount: number | null;
  hasNext: boolean;
  startIndex: number;
  items: readonly unknown[];
}) {
  if (list.loading) return undefined;
  if (list.totalCount !== null) return list.totalCount;
  return list.hasNext ? undefined : list.startIndex + list.items.length;
}

/** A view hands up what only it knows (its extra) for the page's Export; cleared when it goes. */
export function useExportExtra(ref: MutableRefObject<ExportViewExtra | undefined> | undefined, extra: ExportViewExtra) {
  useEffect(() => {
    if (!ref) return;
    ref.current = extra;
    return () => {
      ref.current = undefined;
    };
  });
}

export function useViewExport(
  props: Pick<ViewComponentProps, "onExportContext" | "application" | "view" | "workspaceKey" | "query" | "model">,
  extraRef: MutableRefObject<ExportViewExtra | undefined>,
) {
  const { onExportContext, application, view, workspaceKey, query } = props;
  const { changeSet, publication } = useWorkspaceData();
  useEffect(() => {
    if (!onExportContext) return;
    onExportContext((): ExportStart => {
      const columns = extraRef.current?.columns;
      const viewStart = exportViewStart(application, view, query, columns?.shown);
      return {
        workspaceKey,
        changeSetId: changeSet?.id,
        publicationId: publication?.id,
        objectTypeKeys: application.objectTypeKeys,
        selected: [viewStart.typeKey],
        view: viewStart,
        size: extraRef.current?.size,
        changeSetName: changeSet?.name ?? undefined,
        // A table also hands over its columns, for the workbook's Advanced (0.9 J6).
        ...(view.type === "table"
          ? {
              filters: { objectTypeKey: viewStart.typeKey, filters: query.filters },
              search: query.search || undefined,
              parentObjectId: query.parentObjectId,
              columns,
            }
          : {}),
      };
    });
    return () => onExportContext(undefined);
  });
}
