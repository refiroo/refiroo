/**
 * UI state contracts.
 *
 * These describe what the browser holds and encodes in the URL. They are not part of the
 * declarative model the engine serves, and no backend response carries them.
 */

export type ObjectSort = string;

export interface CollectionFilter {
  field: string;
  operator: string;
  value: string;
}

export interface CollectionQueryState {
  search: string;
  sort: ObjectSort;
  pageSize: number;
  filters: CollectionFilter[];
  /** Cursor trail maintained by useCursorPages; omitted on the first page. */
  cursors?: string[];
}

export type RouteState =
  | ({
      kind: "list";
      applicationKey: string;
      viewKey: string;
      workspaceKey: string;
      workspaceDraftId?: string;
      workspaceRevisionId?: string;
    } & CollectionQueryState)
  | {
      kind: "detail";
      applicationKey: string;
      objectTypeKey: string;
      objectId: string;
      workspaceKey: string;
      workspaceDraftId?: string;
      workspaceRevisionId?: string;
    }
  | { kind: "drafts"; applicationKey: string; workspaceKey: string; workspaceDraftId?: undefined }
  | { kind: "history"; applicationKey: string; workspaceKey: string }
  | { kind: "models"; releaseId?: string; draftId?: string };
