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
  states: string[];
  sort: ObjectSort;
  pageSize: number;
  filters: CollectionFilter[];
}

export type RouteState =
  | ({ kind: "list"; applicationKey: string; viewKey: string; workspaceKey: string } & CollectionQueryState)
  | { kind: "detail"; applicationKey: string; objectTypeKey: string; objectId: string; workspaceKey: string }
  | { kind: "models"; releaseId?: string; draftId?: string };
