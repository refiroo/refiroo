/**
 * UI state contracts.
 *
 * These describe what the browser holds and encodes in the URL. They are not part of the
 * declarative model the engine serves, and no backend response carries them.
 */

import type { ChangeEntryKind, ChangeKind } from "@/types/runtime";
import type { JobState } from "@/types/integration";

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
  /** Mapping-only, in a change set: only the sources whose target the AI proposed (0.16 AP2). */
  mappingProposed?: boolean;
  /** Relation-matrix-only: the column records shown, in order; absent pages the column type. */
  matrixColumnIds?: string[];
  /** Relation-matrix-only: rows with a cell in this state in any shown column. */
  matrixState?: "one" | "several" | "inactive" | "historyOnly" | "none";
  /** Relationships-grid-only: the `to` records shown as column groups; absent shows those the filters select. */
  gridColumnIds?: string[];
  /** Relationships-grid-only: the search over the column records. */
  gridSearch?: string;
  /** Cursor that reopens the page at the top of the list (ADR-030); omitted on the first page. */
  anchor?: string;
}

/** A tab of one model's page in Settings › Model. */
export type ModelTab = "overview" | "releases" | "drafts" | "structure";

/** A tab of one workspace's page in Settings › Workspaces. */
export type WorkspaceTab = "overview" | "access" | "approval" | "activity";

export type RouteState =
  | ({
      kind: "list";
      applicationKey: string;
      viewKey: string;
      workspaceKey: string;
      changeSetId?: string;
      publicationId?: string;
      /** One-shot: open the collection's create form (0.12 Z5, a proposed new record); never restored. */
      createRequest?: { key: number };
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
      /** The user journey this page is a step of; its bar shows under the top bar. */
      journey?: JourneyRef;
    }
  | { kind: "publications"; applicationKey: string; workspaceKey: string }
  | {
      /** A navigation group's page: its collections with a search over their names (0.10 N1). */
      kind: "group";
      applicationKey: string;
      groupKey: string;
      workspaceKey: string;
      changeSetId?: string;
      publicationId?: string;
    }
  | HomeRoute
  | ChangesRoute
  | NotificationsRoute
  | SettingsRoute;

/** The home page after sign-in (0.12 HM1, D331): the bare address, outside any workspace. */
export interface HomeRoute {
  kind: "home";
}

/** The person's notices of the last 90 days (0.12 NT1, D463): `/notifications`, outside any workspace. */
export interface NotificationsRoute {
  kind: "notifications";
  /** A notice a digest's link names (`?notice=<id>`, 0.16 AO3): opened when the page loads. */
  noticeId?: string;
}

/** How far back a person's changes are shown (0.12 Z6, D344); none is any time. */
export type ChangePeriod = "day" | "week" | "month";

/**
 * One person's or client's changes across workspaces (0.12 Z6, D345), outside any workspace as
 * Home is. The filters are the page's: a workspace, a kind of change and a period. `actorName` is
 * the name the link knew, shown until the first page names the actor; it is not in the address.
 */
export interface ChangesRoute {
  kind: "changes";
  actorId: string;
  actorName?: string;
  inWorkspace?: string;
  what?: ChangeEntryKind;
  period?: ChangePeriod;
}

/**
 * The Settings area (Track U U3): pages outside any workspace and application, each with its own
 * URL under `/settings`. Workspaces and Model are a list page with a detail page per entry (U-D10).
 */
export type SettingsRoute =
  | {
      kind: "settings";
      page: "about" | "appearance" | "account" | "notifications" | "deployment" | "operations";
    }
  /** The consumer APIs and their reference: the workspace whose APIs they show (none is the default). */
  | { kind: "settings"; page: "consumer-apis"; workspaceKey?: string }
  | { kind: "settings"; page: "api-reference"; workspaceKey?: string }
  /** Jobs, or one job's page (0.9 J1u). */
  | {
      kind: "settings";
      page: "jobs";
      jobId?: string;
      /** Related jobs opened as a group (0.13 JG): the jobs list, or the trail a job was opened from. */
      group?: { kind: "aiTask" | "modelDraft"; id: string };
      /** The state a group's jobs are narrowed to. */
      state?: JobState;
    }
  /** A load of a workbook with the AI assistant: the reading, the check and the load of one task (0.16 AP6a). */
  | { kind: "settings"; page: "ai-tasks"; taskId?: string }
  /** Moves between workspaces, or the move editor of one mapping between two workspaces (0.11 X4). */
  | { kind: "settings"; page: "moves"; move?: MoveAddress }
  /** Stored import profiles, or one profile's page with its next file's check (0.10 A5c, D85). */
  | { kind: "settings"; page: "import-profiles"; profileKey?: string }
  /** The workspaces catalogue, one workspace's page, or one of its tabs (none is Overview). */
  | { kind: "settings"; page: "workspaces"; workspaceKey?: string; workspaceTab?: WorkspaceTab }
  /** Security › People and Groups, or one person's or group's page; Roles (0.12 SP1). */
  | { kind: "settings"; page: "people"; userId?: string }
  | { kind: "settings"; page: "groups"; groupId?: string }
  | { kind: "settings"; page: "roles" }
  /** Security › Clients, or one client's page; Signing keys (0.12 SP2). */
  | { kind: "settings"; page: "clients"; clientId?: string }
  | { kind: "settings"; page: "sign-in"; providerKey?: string }
  | { kind: "settings"; page: "signing-keys" }
  /** Integration › Mail: the SMTP connection and the outbox (0.12 M1). */
  | { kind: "settings"; page: "mail" }
  | { kind: "settings"; page: "ai" }
  /** Security › Agent access (0.16 AG1). */
  | { kind: "settings"; page: "agent-access" }
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
  | {
      kind: "settings";
      page: "model";
      releaseId?: string;
      draftId?: string;
      /** A model's page, by its key: who runs it, its releases and its drafts (0.11 M6). */
      modelKey?: string;
      /**
       * The tab of the model's page (none is Overview). On an opened release or draft it is the tab
       * the person came from, which Back returns to.
       */
      modelTab?: ModelTab;
      /** A workspace's migration to another release, by its job (0.11 V1). */
      migrationJobId?: string;
      /** The draft opened in the model editor (0.10 A4a, D7), with what its centre shows. */
      editor?: EditorSelection;
      /** The user journey the editor is a step of: Close returns to it. */
      journey?: JourneyRef;
      /** The editor or migration was opened from this workspace, and returns to it (0.16 WM1). */
      forWorkspace?: string;
    };

/** A user journey across pages (the journey bar): today the assistant's load of a workbook. */
export type JourneyRef =
  | { kind: "aiTask"; taskId: string }
  /** A change set moved to a newer model on the way to publishing it: the migration page leads back. */
  | { kind: "changeSet"; changeSetId: string; workspaceKey: string; applicationKey: string };

/**
 * What the model editor's centre shows: an element by its key, or the relationship matrix. A type
 * may be shown as its preview, or laid out in the layout editor, which takes the whole editor
 * (0.10 A4b). A consumer API opens on one of its tabs (0.10 A4c).
 */
export type EditorSelection =
  | { show?: undefined }
  | { show: "matrix" }
  | { show: "type"; key: string; mode?: EditorMode; application?: string }
  | { show: "application" | "relationType" | "attributeType"; key: string }
  | { show: "consumerApi"; key: string; tab?: ConsumerApiTab }
  /** A navigation group of an application, by its key (the group panel). */
  | { show: "group"; application: string; key: string }
  /** A column of the draft's source file, by its sheet and header (0.10 A5b). */
  | { show: "column"; sheet: string; key: string }
  /** A list of a sheet laid out for reading, by its sheet and its block's index (0.10 A8b, D123). */
  | { show: "list"; sheet: string; block: number };

/**
 * What moves, as the move editor's dialog chooses it (D142): the whole workspace, chosen types each
 * with the filters a collection's filter bar edits, or one record with everything under it.
 */
export type MoveChoice =
  | { kind: "all" }
  | { kind: "types"; types: { objectTypeKey: string; filters: CollectionFilter[] }[] }
  | { kind: "subtree"; objectId: string; objectTypeKey: string; name?: string };

/**
 * The move editor's address (0.11 X4, D138): the mapping, the two workspaces, the dry run it shows
 * (followed again after a reload), what moves (absent: every mapped type, D142), copy or move, and
 * the report of what cannot move with its reason.
 */
export interface MoveAddress {
  mappingKey: string;
  from: string;
  to: string;
  jobId?: string;
  selection?: MoveChoice;
  mode?: "copy" | "move";
  view?: "report";
  reason?: string;
  /** The mapping row selected, by its key (`type`, `attribute:{key}`, …) under its source type. */
  row?: string;
}

/** How a type is shown in the model editor: its definition (the default), its preview, its layout. */
export type EditorMode = "preview" | "layout";

/** The tabs of a consumer API in the model editor (0.10 A4c). */
export type ConsumerApiTab = "types" | "fields" | "operations" | "filters" | "schema" | "example";

export type SettingsPage = SettingsRoute["page"];

/** Every route that is neither a settings page nor home: an application's data, in a workspace. */
export type ApplicationRoute = Exclude<RouteState, SettingsRoute | HomeRoute | ChangesRoute | NotificationsRoute>;
