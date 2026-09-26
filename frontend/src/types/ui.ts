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
  /** Optional direct-parent collection scope, kept in the URL across compatible lenses. */
  parentObjectId?: string;
  parentObjectTypeKey?: string;
  /** Mapping-only coverage state; ignored by other renderer types. */
  mappingState?: "mapped" | "unmapped" | "ambiguous";
  /** Cursor that reopens the page at the top of the list (ADR-030); omitted on the first page. */
  anchor?: string;
}

export type RouteState =
  | ({
      kind: "list";
      applicationKey: string;
      viewKey: string;
      workspaceKey: string;
      changeSetId?: string;
      publicationId?: string;
    } & CollectionQueryState)
  | {
      kind: "detail";
      applicationKey: string;
      objectTypeKey: string;
      objectId: string;
      /** Browser-history context, deliberately absent from the shareable record URL. */
      collectionOrigin?: Extract<RouteState, { kind: "list" }> | null;
      /** Presentation belongs to the history entry, not the canonical record link. */
      fullPage?: boolean;
      /** One-shot row action; never restored from history or a copied link. */
      actionRequest?: { action: "edit" | "delete"; key: number };
      workspaceKey: string;
      changeSetId?: string;
      publicationId?: string;
    }
  | { kind: "changeSets"; applicationKey: string; workspaceKey: string; changeSetId?: undefined }
  | { kind: "publications"; applicationKey: string; workspaceKey: string }
  | { kind: "models"; releaseId?: string; draftId?: string };
