/**
 * UI state contracts.
 *
 * These describe what the browser holds and encodes in the URL. They are not part of the
 * declarative model the engine serves, and no backend response carries them.
 */

import type { ChangeKind } from "@/types/runtime";

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
  /** Relation-matrix-only: the column records shown, in order; absent pages the column type. */
  matrixColumnIds?: string[];
  /** Relation-matrix-only: rows with a cell in this state in any shown column. */
  matrixState?: "one" | "several" | "inactive" | "historyOnly" | "none";
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
  | {
      /** A change set's review: the records and relationships it changes (Base 0.8 P2b). */
      kind: "changeSetChanges";
      applicationKey: string;
      workspaceKey: string;
      changeSetId: string;
      tab: "records" | "relationships";
      /** Only these kinds; every kind when empty. */
      changeKinds: ChangeKind[];
      /** Only this object type (records) or relation type (relationships). */
      typeKey?: string;
      /** Relationships: also list engine-maintained parent links, hidden by default (D32). */
      containment?: boolean;
      /** Cursor that reopens the shown list at the top of the viewport (ADR-030). */
      anchor?: string;
    }
  | { kind: "publications"; applicationKey: string; workspaceKey: string }
  | SettingsRoute;

/**
 * The Settings area (Track U U3): pages outside any workspace and application, each with its own
 * URL under `/settings`. Workspaces and Model are a list page with a detail page per entry (U-D10).
 */
export type SettingsRoute =
  | { kind: "settings"; page: "about" | "appearance" | "deployment" | "consumer-apis" | "jobs" | "api-reference" }
  | { kind: "settings"; page: "workspaces"; workspaceKey?: string }
  | {
      kind: "settings";
      page: "webhooks";
      subscriptionId?: string;
      /** The detail's tab; Configuration without one. */
      tab?: "deliveries";
      /** An opened delivery: its request, and the event within it (none for a notice). */
      deliveryId?: string;
      eventId?: string;
    }
  | { kind: "settings"; page: "model"; releaseId?: string; draftId?: string };

export type SettingsPage = SettingsRoute["page"];

/** Every route that is not a settings page: an application's data, in a workspace. */
export type ApplicationRoute = Exclude<RouteState, SettingsRoute>;
