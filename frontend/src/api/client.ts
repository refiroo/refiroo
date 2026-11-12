import type {
  ChangeEntryKind,
  ChangeEntryPage,
  MappingInference,
  MappingOperation,
  MappingProposal,
  ModelMapping,
  ModelMappingOperationEntry,
  ModelMappingPage,
  ModelMappingStep,
  MoveOutcome,
  MoveRequest,
  MoveRowPage,
  EngineModel,
  ChangeSet,
  ChangeSetPage,
  ApprovalPolicy,
  PublicationRequest,
  PublicationRequestPage,
  Publication,
  PublicationPage,
  ChangeSetValidation,
  ChangeKind,
  ObjectChangePage,
  RelationChangePage,
  InitialRelationInput,
  ObjectAttributeInput,
  ObjectDeletionImpact,
  ObjectItem,
  ObjectPage,
  ParentCandidatePage,
  ModelPlacements,
  AttributeValueResponse,
  RelationCreateInput,
  RelationPage,
  RelationRecord,
  RelationUpdateInput,
  AuditEventPage,
  HistoryKind,
  ObjectSort,
  CollectionFilter,
  CapabilitiesResponse,
  SystemConfiguration,
  SystemResponse,
  SystemSummary,
  EngineProcess,
  WorkspaceReadiness,
  BackupRehearsalPage,
  Me,
  Notification as InboxNotice,
  NotificationPage,
  NotificationQuery,
  NotificationSelection,
  NotificationsReadResult,
  NotificationsRemovalResult,
  SignInSession,
  MySecondFactor,
  FollowedWorkspace,
  NoticeDelivery,
  NoticeMail,
  Passkey,
  SecondFactorEnrolment,
  Grant,
  HeldAnywhereList,
  OwnChangeSetPage,
  OwnWorkspace,
  MyPermissions,
  PageNavigation,
  ConsumerApiDefinition,
  ConsumerApiDocument,
  ConsumerApiIndexPage,
  BatchRequest,
  BatchResult,
  Job,
  JobItemOutcome,
  JobItemPage,
  JobGroupPage,
  JobPage,
  JobState,
  JobRow,
  JobRowPage,
  MigrationListConversion,
  MigrationOutcome,
  MigrationRelationTypeMapping,
  MigrationRowPage,
  MigrationSplit,
  MigrationTypeMapping,
  ImportProfile,
  ImportProfilePage,
  ImportProfileSource,
  ProfileCheck,
  CheckDrift,
  CheckMissingRecord,
  CheckNewValue,
  ImportRequest,
  ExportRequest,
  DeliveryDetail,
  DeliveryRowPage,
  DeliveryStatus,
  Subscription,
  SubscriptionCreate,
  SubscriptionPage,
  SubscriptionUpdate,
  ConsumerApiDocumentKind,
  DraftMigration,
  ModelCompilation,
  ModelDraftConsumerApi,
  DraftOperation,
  ModelDraft,
  ModelDraftOperationPage,
  ModelDraftModel,
  ModelDraftOutline,
  ModelDraftPage,
  ModelDraftStep,
  ModelInstallation,
  ModelRelease,
  ModelReleaseActivationPage,
  ModelReleaseDiff,
  ModelReleasePage,
  ModelReleaseRaising,
  ModelReleaseSummary,
  WorkspaceModel,
  WorkspaceModelActivation,
  ModelValidation,
  Workspace,
  WorkspaceDetail,
  WorkspaceFromWorkbook,
  WorkspacePage,
  WorkspaceRuntimeState,
  MappingCoveragePage,
  MappingTargetPage,
  MappingCandidatePage,
  MappingReplacementRequest,
  MappingReplacementResponse,
  RelationMatrixPage,
  RelationGridChangeInput,
  RelationGridChangeResult,
  RelationGridPage,
  RelationTablePage,
  RelationBatchInput,
  RelationBatchResult,
  RelationMatrixContainerPage,
  RelationMatrixLinkCandidatePage,
  RelationSetClaim,
  RestructuringOutcomeFilter,
  RestructuringPreview,
  RestructuringRequest,
  RestructuringResult,
  DraftProfile,
  DryRun,
  Inference,
  InferenceRequest,
  JoinCandidates,
  JoinCandidatesRequest,
  Canvas,
  CanvasPosition,
  CanvasUpdate,
  ListProposal,
  Proposal,
  SourceCellRow,
  SourceColumn,
  SourceFile,
  SourceFileUpload,
  SourcePage,
  SourceRectangle,
  SourceSheet,
  MappingProposalRequest,
} from "@/types";

import { API_URL } from "@/api/address";
import { ApiError } from "@/api/errors";
import { authorizedFetch } from "@/api/session";
import { everyPage } from "@/lib/everyPage";
import { expectedReleaseHeader, reportModelReleaseChanged } from "@/api/expectedRelease";
import { reportForbidden } from "@/api/forbidden";

// `ApiError` is re-exported because it is what `request` throws; `errorMessage` and
// `isApiError` live in ./errors so that a test mocking this module does not shadow them.
export { ApiError } from "@/api/errors";

export { API_URL } from "@/api/address";

/** A completed export's file, as a link the browser downloads (0.9 J1). */
export const jobOutputUrl = (jobId: string) => `${API_URL}/api/v1/jobs/${encodeURIComponent(jobId)}/output`;

/** A job's server-sent event stream (0.9 J1u): the job now and after each change, until it ends. */
export const jobEventsUrl = (jobId: string) => `${API_URL}/api/v1/jobs/${encodeURIComponent(jobId)}/events`;

/** The signed-in person's inbox stream (0.12 A2): the unread count and each new notice. */
export const notificationEventsUrl = () => `${API_URL}/api/v1/me/notifications/events`;

export async function request<T>(
  path: string,
  init?: RequestInit,
  onResponse?: (response: Response) => void,
): Promise<T> {
  return requestUrl<T>(`${API_URL}${path}`, path, init, onResponse);
}

/**
 * Identical reads still in flight, by address and headers (0.11 X6, D157). A component mounted
 * twice (React's StrictMode in development) or two parts of a page asking for the same thing share
 * the one request and its answer. Nothing is cached: once the answer arrives the entry goes, and
 * the next identical call makes a new request. Writes, and reads a caller can abort, never share.
 */
const pendingReads = new Map<string, Promise<{ response: Response; body: string | undefined }>>();

/** A request to an address the API gave whole, such as a document the consumer API index names. */
async function requestUrl<T>(
  url: string,
  path: string,
  init?: RequestInit,
  onResponse?: (response: Response) => void,
): Promise<T> {
  // A form body (a file upload) sets its own multipart content type with its boundary.
  const json = !(init?.body instanceof FormData);
  const headers = {
    ...(json ? { "Content-Type": "application/json" } : {}),
    ...expectedReleaseHeader(path, init?.method),
    ...init?.headers,
  };
  const shared = (init?.method ?? "GET").toUpperCase() === "GET" && !init?.body && !init?.signal;
  const key = JSON.stringify([url, headers]);
  let read = shared ? pendingReads.get(key) : undefined;
  if (!read) {
    read = send(url, path, { ...init, headers });
    if (shared) {
      pendingReads.set(key, read);
      void read.then(
        () => pendingReads.delete(key),
        () => pendingReads.delete(key),
      );
    }
  }
  const { response, body } = await read;
  onResponse?.(response);
  // Each caller parses its own copy, so one changing what it received cannot change another's.
  return (body === undefined ? undefined : JSON.parse(body)) as T;
}

async function send(
  url: string,
  path: string,
  init: RequestInit,
): Promise<{ response: Response; body: string | undefined }> {
  const response = await authorizedFetch(url, init);
  if (!response.ok) {
    const body = await response.text();
    let message = failedResponseMessage(path, response.status);
    let code = "HTTP_ERROR";
    let details: unknown;
    try {
      const parsed = JSON.parse(body);
      message = parsed.error?.message ?? parsed.detail ?? message;
      code = parsed.error?.code ?? code;
      details = parsed.error?.details;
    } catch {
      // Non-JSON response evidence belongs in controlled server diagnostics, not the rendered UI.
    }
    const failure = new ApiError(response.status, code, message, details);
    const read = !init.method || init.method.toUpperCase() === "GET";
    if (code === "MODEL_RELEASE_CHANGED" && (read || expectedReleaseHeader(path, init.method)))
      reportModelReleaseChanged(failure, read);
    if (code === "FORBIDDEN") reportForbidden();
    throw failure;
  }
  if (response.status === 204) return { response, body: undefined };
  const contentType = response.headers.get("content-type") ?? "";
  if (!contentType.includes("application/json")) {
    throw new ApiError(
      response.status,
      "UNEXPECTED_RESPONSE",
      `The request to ${path} returned ${contentType || "an unknown content type"} instead of JSON. Retry or contact support if the problem continues.`,
    );
  }
  return { response, body: await response.text() };
}

function failedResponseMessage(path: string, status: number): string {
  return `The request to ${path} failed with status ${status}. Retry or contact support if the problem continues.`;
}

export interface ChangeSetWriteContext {
  changeSetId?: string;
  expectedChangeSetVersion?: number;
}

/**
 * Selects one page of a collection (ADR-030): a cursor, a position, the end or a seek value, at
 * most one of them; none reads the first page. `includeTotal` adds `totalCount` and `startIndex`.
 */
export interface PageSelector {
  cursor?: string;
  position?: number;
  fromEnd?: boolean;
  seek?: string;
  includeTotal?: boolean;
}

function restructuringsPath(changeSetId: string | undefined) {
  if (!changeSetId)
    throw new Error("A type change or restructuring is made in a change set. Open one, then try again.");
  return `/api/v1/change-sets/${encodeURIComponent(changeSetId)}/restructurings`;
}

function setPaging(params: URLSearchParams, selector: PageSelector) {
  if (selector.cursor) params.set("cursor", selector.cursor);
  if (selector.position !== undefined) params.set("position", String(selector.position));
  if (selector.fromEnd) params.set("from", "end");
  if (selector.seek !== undefined) params.set("seek", selector.seek);
  if (selector.includeTotal) params.set("includeTotal", "true");
}

export interface ObjectQuery extends PageSelector {
  changeSetId?: string;
  publicationId?: string;
  applicationKey?: string;
  workspaceKey?: string;
  search?: string;
  pageSize?: number;
  parentObjectId?: string;
  /** Only records without a parent; refused beside `parentObjectId`. */
  topLevel?: boolean;
  sort?: ObjectSort;
  filters?: CollectionFilter[];
  /** Relation keys or reverse keys whose related records each row carries (0.9 K5, D142). */
  expand?: string[];
  /** How many related records each `expand` entry carries, 1–20 (3 when omitted). */
  expandLimit?: number;
  /** Only the records a record of `anchorTypeKey` may choose through this relation key or reverse
   * key, by the binding's candidates (0.9 K7, D173). */
  candidateFor?: string;
  anchorTypeKey?: string;
}

export interface ChangeListQuery extends PageSelector {
  kinds?: ChangeKind[];
  pageSize?: number;
}

function changeListParams(query: ChangeListQuery) {
  const params = new URLSearchParams();
  query.kinds?.forEach((kind) => params.append("kind", kind));
  if (query.pageSize != null) params.set("pageSize", String(query.pageSize));
  setPaging(params, query);
  return params;
}

export interface ObjectDeleteOptions {
  cascade?: boolean;
  deletionPreviewToken?: string;
  changeSetId?: string;
  expectedChangeSetVersion?: number;
}

export interface MappingCoverageQuery extends PageSelector {
  workspaceKey: string;
  applicationKey: string;
  viewKey: string;
  relationTypeKey: string;
  fromObjectTypeKey: string;
  toObjectTypeKey: string;
  direction: "outgoing" | "incoming";
  changeSetId?: string;
  publicationId?: string;
  search?: string;
  pageSize?: number;
  parentObjectId?: string;
  state?: "mapped" | "unmapped" | "ambiguous";
  /** Only the sources whose target the AI proposed; needs `changeSetId` (0.16 AP2). */
  proposed?: boolean;
}

/** A relationships table's rows: the workspace edge list read through the view (0.13 RV). */
export interface RelationTableQuery extends PageSelector {
  workspaceKey: string;
  applicationKey: string;
  viewKey: string;
  changeSetId?: string;
  publicationId?: string;
  search?: string;
  pageSize?: number;
  fromObjectId?: string;
  toObjectId?: string;
  /** One of the view's `sortFields`, `-` for descending. */
  sort?: string;
  /** Equalities on the view's `filterFields`, by field reference (`from:name`, `relation:<attribute>`). */
  filters?: { field: string; value: string }[];
}

/** A relationships grid's rows and column groups: the view read as a grid (0.13 RG). */
export interface RelationGridQuery extends PageSelector {
  workspaceKey: string;
  applicationKey: string;
  viewKey: string;
  changeSetId?: string;
  publicationId?: string;
  search?: string;
  pageSize?: number;
  /** The column records to show; none shows those the `to:` filters select, at most 50. */
  toObjectIds?: string[];
  /** Searches the column records as their type's list does. */
  toSearch?: string;
  /** Only these relationship attributes are returned; none returns every stored value. */
  attributes?: string[];
  sort?: string;
  filters?: { field: string; operator?: string; value: string }[];
}

export interface MappingTargetQuery {
  workspaceKey: string;
  relationTypeKey: string;
  fromObjectTypeKey: string;
  toObjectTypeKey: string;
  direction: "outgoing" | "incoming";
  applicationKey?: string;
  viewKey?: string;
  changeSetId?: string;
  publicationId?: string;
  sourceObjectId: string;
  mappingVersion: number;
  cursor?: string;
  pageSize?: number;
}

export interface MappingCandidateQuery extends PageSelector {
  workspaceKey: string;
  applicationKey: string;
  viewKey: string;
  objectTypeKey: string;
  changeSetId?: string;
  publicationId?: string;
  search?: string;
  pageSize?: number;
}

/** What every relation matrix read names: the view and, optionally, a change set or publication. */
export interface RelationMatrixViewQuery {
  workspaceKey: string;
  applicationKey: string;
  viewKey: string;
  changeSetId?: string;
  publicationId?: string;
}

export interface RelationMatrixQuery extends RelationMatrixViewQuery, PageSelector {
  parentObjectId?: string;
  search?: string;
  sort?: string;
  /** The column records to show, at most 20; without them the column type pages by `columnCursor`. */
  columnIds?: string[];
  columnCursor?: string;
  state?: "one" | "several" | "inactive" | "historyOnly" | "none";
  /** Skip the columns with no related record in any row the search and parent leave (0.13 LB-D8). */
  hideEmptyColumns?: boolean;
  pageSize?: number;
}

export interface RelationMatrixCellQuery extends RelationMatrixViewQuery, PageSelector {
  columnId: string;
  search?: string;
  pageSize?: number;
}

function relationMatrixPath(route: string, query: RelationMatrixViewQuery, params: URLSearchParams) {
  params.set("applicationKey", query.applicationKey);
  params.set("viewKey", query.viewKey);
  if (query.changeSetId) params.set("changeSetId", query.changeSetId);
  if (query.publicationId) params.set("publicationId", query.publicationId);
  return `/api/v1/workspaces/${encodeURIComponent(query.workspaceKey)}/relation-matrix${route}?${params}`;
}

function relationMatrixCellParams(query: RelationMatrixCellQuery) {
  const params = new URLSearchParams({ columnId: query.columnId });
  if (query.search) params.set("search", query.search);
  setPaging(params, query);
  if (query.pageSize != null) params.set("pageSize", String(query.pageSize));
  return params;
}

function objectQueryPath(objectTypeKey: string, query: ObjectQuery) {
  const params = new URLSearchParams({ pageSize: String(query.pageSize ?? 20) });
  if (query.applicationKey) params.set("applicationKey", query.applicationKey);
  if (query.changeSetId) params.set("changeSetId", query.changeSetId);
  if (query.publicationId) params.set("publicationId", query.publicationId);
  if (query.workspaceKey) params.set("workspaceKey", query.workspaceKey);
  if (query.search) params.set("search", query.search);
  setPaging(params, query);
  if (query.parentObjectId) params.set("parentObjectId", query.parentObjectId);
  if (query.topLevel) params.set("topLevel", "true");
  if (query.sort) params.set("sort", query.sort);
  query.filters?.forEach(({ field, operator, value }) => params.append(`filter.${field}.${operator}`, value));
  query.expand?.forEach((key) => params.append("expand", key));
  if (query.expandLimit != null) params.set("expandLimit", String(query.expandLimit));
  if (query.candidateFor) params.set("candidateFor", query.candidateFor);
  if (query.anchorTypeKey) params.set("anchorTypeKey", query.anchorTypeKey);
  return `/api/v1/objects/${encodeURIComponent(objectTypeKey)}?${params}`;
}

/** Every item of a paged collection, page after page (for the short operational lists). */
async function allPages<Item>(path: string): Promise<Item[]> {
  const items: Item[] = [];
  let cursor: string | null = null;
  do {
    const params = new URLSearchParams({ pageSize: "500" });
    if (cursor) params.set("cursor", cursor);
    const page: { items: Item[] } & PageNavigation = await request(`${path}?${params}`);
    items.push(...page.items);
    cursor = page.nextCursor;
  } while (cursor);
  return items;
}

export const api = {
  /** The context's model, with where it lets records stand attached (`placements`, C4). */
  model: async (
    context: { workspaceKey?: string; changeSetId?: string; publicationId?: string } = {},
  ): Promise<EngineModel> => {
    const params = new URLSearchParams();
    if (context.workspaceKey) params.set("workspaceKey", context.workspaceKey);
    if (context.changeSetId) params.set("changeSetId", context.changeSetId);
    if (context.publicationId) params.set("publicationId", context.publicationId);
    const query = params.toString() ? `?${params}` : "";
    let releaseId: string | undefined;
    const [model, placements] = await Promise.all([
      request<EngineModel>(`/api/v1/model${query}`, undefined, (response) => {
        releaseId = response.headers.get("X-Model-Release-Id") ?? undefined;
      }),
      request<ModelPlacements>(`/api/v1/model/placements${query}`),
    ]);
    return { ...model, placements, ...(releaseId ? { releaseId } : {}) };
  },
  capabilities: () => request<CapabilitiesResponse>("/api/v1/capabilities"),
  system: () => request<SystemResponse>("/api/v1/system"),
  systemConfiguration: () => request<SystemConfiguration>("/api/v1/system/configuration"),
  /** The instance's figures counted now (0.11 O2). */
  systemSummary: () => request<SystemSummary>("/api/v1/system/summary"),
  /** Every engine process, every page (an instance has a handful). */
  processes: () => allPages<EngineProcess>("/api/v1/system/processes"),
  /** Whether each active workspace is served, every page. */
  readiness: () => allPages<WorkspaceReadiness>("/api/v1/system/readiness"),
  /** Who is signed in (0.12 I2). */
  me: () => request<Me>("/api/v1/me"),
  /** What the caller may do in a workspace, the default one without a key (0.12 Z1). */
  myPermissions: (workspaceKey?: string) =>
    request<MyPermissions>(
      `/api/v1/me/permissions${workspaceKey ? `?workspaceKey=${encodeURIComponent(workspaceKey)}` : ""}`,
    ),
  /** Every action group the caller holds, at the instance or in which workspaces (0.12 Z5, D328). */
  myActionGroups: () => request<HeldAnywhereList>("/api/v1/me/action-groups"),
  /** The caller's grants, direct and through their groups, every page (a caller has a handful). */
  myGrants: () => allPages<Grant>("/api/v1/me/grants"),
  /**
   * A page of the caller's inbox, newest first unless `sort` says otherwise, searched and filtered
   * on the server, with the count of all their unread notices (0.12 A2, NT1).
   */
  notifications: (query: NotificationQuery & PageSelector = {}) => {
    const params = new URLSearchParams({ pageSize: String(query.pageSize ?? 20) });
    if (query.q) params.set("q", query.q);
    if (query.kind) params.set("kind", query.kind);
    if (query.workspace) params.set("workspace", query.workspace);
    if (query.unread !== undefined) params.set("unread", String(query.unread));
    if (query.sort) params.set("sort", query.sort);
    setPaging(params, query);
    return request<NotificationPage>(`/api/v1/me/notifications?${params}`);
  },
  /** One of the caller's notices by ID: where a digest's link leads (0.16 AO3). */
  notification: (id: string) => request<InboxNotice>(`/api/v1/me/notifications/${encodeURIComponent(id)}`),
  /** Mark notices read, or unread with `read` false: by ID, by what they are about, or all; idempotent. */
  markNotificationsRead: (selection: NotificationSelection, read = true) =>
    request<NotificationsReadResult>("/api/v1/me/notifications/read", {
      method: "POST",
      body: JSON.stringify(read ? selection : { ...selection, read }),
    }),
  /** Delete notices for good, by ID or every read one (0.12 NT1, D461); what they were about stays. */
  removeNotifications: (selection: { ids: string[] } | { read: true }) =>
    request<NotificationsRemovalResult>("/api/v1/me/notifications/removal", {
      method: "POST",
      body: JSON.stringify(selection),
    }),
  /** The workspaces the caller may browse, with what waits there, every page (0.12 HM1, D332). */
  myWorkspaces: () => allPages<OwnWorkspace>("/api/v1/me/workspaces"),
  /** The workspaces the caller follows, every page (0.16 AO3, AO-D38). */
  followedWorkspaces: () => allPages<FollowedWorkspace>("/api/v1/me/followed-workspaces"),
  /** Follow a workspace the caller may browse: a notice when a change set is published there; repeating is harmless. */
  followWorkspace: (workspaceKey: string) =>
    request<FollowedWorkspace>(`/api/v1/me/followed-workspaces/${encodeURIComponent(workspaceKey)}`, {
      method: "PUT",
    }),
  /** Stop following a workspace; harmless when the caller did not. */
  unfollowWorkspace: (workspaceKey: string) =>
    request<void>(`/api/v1/me/followed-workspaces/${encodeURIComponent(workspaceKey)}`, { method: "DELETE" }),
  /** A page of the caller's open change sets across workspaces, newest change first (D333). */
  myChangeSets: (cursor?: string) => {
    const query = new URLSearchParams({ pageSize: "20" });
    if (cursor) query.set("cursor", cursor);
    return request<OwnChangeSetPage>(`/api/v1/me/change-sets?${query}`);
  },
  /**
   * A page of the data and model changes the caller may see, newest first (0.12 Z6, D340): one
   * person's or client's with `actorId`, narrowed by workspace, kind and time (`since` included).
   */
  changes: (filter: {
    actorId?: string;
    workspaceKey?: string;
    kinds?: ChangeEntryKind[];
    since?: string;
    /** Not included. */
    until?: string;
    /** What an account of history counted (0.16 AO2): the type, the cause, the action, an attribute, live data only. */
    objectTypeKey?: string;
    relationTypeKey?: string;
    causeId?: string;
    action?: string;
    attributeKey?: string;
    live?: boolean;
    cursor?: string;
    pageSize?: number;
  }) => {
    const query = new URLSearchParams({ pageSize: String(filter.pageSize ?? 50) });
    if (filter.actorId) query.set("actorId", filter.actorId);
    if (filter.workspaceKey) query.set("workspaceKey", filter.workspaceKey);
    filter.kinds?.forEach((kind) => query.append("kind", kind));
    if (filter.since) query.set("since", filter.since);
    if (filter.until) query.set("until", filter.until);
    if (filter.objectTypeKey) query.set("objectTypeKey", filter.objectTypeKey);
    if (filter.relationTypeKey) query.set("relationTypeKey", filter.relationTypeKey);
    if (filter.causeId) query.set("causeId", filter.causeId);
    if (filter.action) query.set("action", filter.action);
    if (filter.attributeKey) query.set("attributeKey", filter.attributeKey);
    if (filter.live) query.set("live", "true");
    if (filter.cursor) query.set("cursor", filter.cursor);
    return request<ChangeEntryPage>(`/api/v1/changes?${query}`);
  },
  /** Where the person is signed in: every open session (a person has a handful). */
  mySessions: () => allPages<SignInSession>("/api/v1/me/sessions"),
  /** Sign out one session, its tokens refused from the next request. */
  endMySession: (sessionId: string) =>
    request<void>(`/api/v1/me/sessions/${encodeURIComponent(sessionId)}`, { method: "DELETE" }),
  /** Sign out everywhere, this browser included. */
  endAllMySessions: () => request<void>("/api/v1/me/sessions", { method: "DELETE" }),
  /** A new password; the person's other sessions end. */
  changePassword: (currentPassword: string, newPassword: string) =>
    request<void>("/api/v1/me/password", {
      method: "POST",
      body: JSON.stringify({ currentPassword, newPassword }),
    }),
  /** Whether the caller is e-mailed for the notices in their inbox, and whether they can be (0.12 M2). */
  myNoticeMail: () => request<NoticeMail>("/api/v1/me/notification-mail"),
  /** Switch mail for the caller's inbox on or off; refused where mail is not set up or there is no address. */
  setMyNoticeMail: (
    change:
      | boolean
      | {
          enabled?: boolean;
          kinds?: Record<string, NoticeDelivery>;
          digest?: { every: "daily" | "weekly"; timeZone: string };
        },
  ) =>
    request<NoticeMail>("/api/v1/me/notification-mail", {
      method: "PUT",
      body: JSON.stringify(typeof change === "boolean" ? { enabled: change } : change),
    }),
  /** The caller's second factor: whether an authenticator app is set up, its recovery codes left and
   * whether the instance requires one (0.12 I4b). */
  mySecondFactor: () => request<MySecondFactor>("/api/v1/me/second-factor"),
  /** A new secret to set up, answered once: the key, the address and a drawn QR code (D386). */
  startSecondFactor: () => request<SecondFactorEnrolment>("/api/v1/me/second-factor", { method: "POST" }),
  /** A code from the app turns it on and answers ten recovery codes, once (D385). */
  confirmSecondFactor: (code: string) =>
    request<{ recoveryCodes: string[] }>("/api/v1/me/second-factor/confirmation", {
      method: "POST",
      body: JSON.stringify({ code }),
    }),
  /** Ten new recovery codes on a code from the app or a recovery code; the old ones stop working. */
  newRecoveryCodes: (code: string) =>
    request<{ recoveryCodes: string[] }>("/api/v1/me/second-factor/recovery-codes", {
      method: "POST",
      body: JSON.stringify({ code }),
    }),
  /** The caller's passkeys (I4c); one is added on the engine's own page, `addPasskey`. */
  myPasskeys: () => allPages<Passkey>("/api/v1/me/passkeys"),
  renamePasskey: (passkeyId: string, name: string) =>
    request<Passkey>(`/api/v1/me/passkeys/${encodeURIComponent(passkeyId)}`, {
      method: "PATCH",
      body: JSON.stringify({ name }),
    }),
  /** `proof` is the password, or a code from the app or a recovery code (asked again, I4 review). */
  removePasskey: (passkeyId: string, proof: string) =>
    request<void>(`/api/v1/me/passkeys/${encodeURIComponent(passkeyId)}`, {
      method: "DELETE",
      body: JSON.stringify({ proof }),
    }),
  removeMySecondFactor: (code: string) =>
    request<void>("/api/v1/me/second-factor", { method: "DELETE", body: JSON.stringify({ code }) }),
  /** Backup rehearsals, newest first, one page. */
  backupRehearsals: (cursor?: string) => {
    const params = new URLSearchParams({ pageSize: "20" });
    if (cursor) params.set("cursor", cursor);
    return request<BackupRehearsalPage>(`/api/v1/system/backup-rehearsals?${params}`);
  },
  /** A consumer API definition of the active model, expanded with every default (C18). */
  consumerApiDefinition: (consumerApi: string) =>
    request<ConsumerApiDefinition>(`/api/v1/model/consumer-apis/${encodeURIComponent(consumerApi)}`),
  /** The consumer API index (`GET /api/consumer`), one page, of the default workspace or of `workspaceKey`. */
  consumerApis: (cursor?: string, workspaceKey?: string) => {
    const params = new URLSearchParams({ pageSize: "100" });
    if (cursor) params.set("cursor", cursor);
    if (workspaceKey) params.set("workspace", workspaceKey);
    return request<ConsumerApiIndexPage>(`/api/consumer?${params}`);
  },
  /** A consumer API's OpenAPI document, at the address its index entry names (resolved whole). */
  consumerApiDocument: (url: string) => requestUrl<ConsumerApiDocument>(url, new URL(url).pathname),
  /** Jobs in every workspace, newest first. */
  jobs: (cursor?: string, options: { origin?: string; state?: JobState } = {}) => {
    const params = new URLSearchParams({ pageSize: "50" });
    if (cursor) params.set("cursor", cursor);
    if (options.origin) params.set("origin", options.origin);
    if (options.state) params.set("state", options.state);
    return request<JobPage>(`/api/v1/jobs?${params}`);
  },
  /** Jobs one row per assistant task or model draft and one per job of neither (0.13 JG), newest activity first. */
  jobGroups: (cursor?: string, options: { origin?: string } = {}) => {
    const params = new URLSearchParams({ pageSize: "50", grouped: "true" });
    if (cursor) params.set("cursor", cursor);
    if (options.origin) params.set("origin", options.origin);
    return request<JobGroupPage>(`/api/v1/jobs?${params}`);
  },
  /** Webhook subscriptions, newest first, optionally of one workspace. */
  subscriptions: (options: { cursor?: string; workspaceKey?: string } = {}) => {
    const params = new URLSearchParams({ pageSize: "50" });
    if (options.cursor) params.set("cursor", options.cursor);
    if (options.workspaceKey) params.set("workspaceKey", options.workspaceKey);
    return request<SubscriptionPage>(`/api/v1/consumer-subscriptions?${params}`);
  },
  subscription: (id: string) => request<Subscription>(`/api/v1/consumer-subscriptions/${encodeURIComponent(id)}`),
  /** The answer holds `signingSecret`, which no later read returns. */
  createSubscription: (body: SubscriptionCreate) =>
    request<Subscription>("/api/v1/consumer-subscriptions", { method: "POST", body: JSON.stringify(body) }),
  updateSubscription: (id: string, body: SubscriptionUpdate) =>
    request<Subscription>(`/api/v1/consumer-subscriptions/${encodeURIComponent(id)}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  suspendSubscription: (id: string, expectedVersion: number) =>
    request<Subscription>(`/api/v1/consumer-subscriptions/${encodeURIComponent(id)}/suspend`, {
      method: "POST",
      body: JSON.stringify({ expectedVersion }),
    }),
  /** A new signing key in `signingSecret`, which no later read returns; the old one signs beside it for `overlapHours`. */
  rotateSubscriptionSecret: (id: string, expectedVersion: number, overlapHours: number) =>
    request<Subscription>(`/api/v1/consumer-subscriptions/${encodeURIComponent(id)}/rotate-secret`, {
      method: "POST",
      body: JSON.stringify({ expectedVersion, overlapHours }),
    }),
  resumeSubscription: (id: string, expectedVersion: number, reset = false) =>
    request<Subscription>(`/api/v1/consumer-subscriptions/${encodeURIComponent(id)}/resume`, {
      method: "POST",
      body: JSON.stringify({ expectedVersion, reset }),
    }),
  /** What a subscription delivered, newest first: a row per event, or per notice. */
  deliveries: (id: string, options: { cursor?: string; status?: DeliveryStatus } = {}) => {
    const params = new URLSearchParams({ pageSize: "50" });
    if (options.cursor) params.set("cursor", options.cursor);
    if (options.status) params.set("status", options.status);
    return request<DeliveryRowPage>(`/api/v1/consumer-subscriptions/${encodeURIComponent(id)}/deliveries?${params}`);
  },
  delivery: (id: string, deliveryId: string) =>
    request<DeliveryDetail>(
      `/api/v1/consumer-subscriptions/${encodeURIComponent(id)}/deliveries/${encodeURIComponent(deliveryId)}`,
    ),
  /** Send an event of a delivered request again, by hand, as it was sent; the new request. */
  resendDelivery: (id: string, deliveryId: string, eventId: string) =>
    request<DeliveryDetail>(
      `/api/v1/consumer-subscriptions/${encodeURIComponent(id)}/deliveries/${encodeURIComponent(deliveryId)}/resend`,
      { method: "POST", body: JSON.stringify({ eventId }) },
    ),
  deleteSubscription: (id: string, expectedVersion: number) =>
    request<void>(`/api/v1/consumer-subscriptions/${encodeURIComponent(id)}?expectedVersion=${expectedVersion}`, {
      method: "DELETE",
    }),
  cancelJob: (jobId: string) => request<Job>(`/api/v1/jobs/${encodeURIComponent(jobId)}/cancel`, { method: "POST" }),
  job: (jobId: string) => request<Job>(`/api/v1/jobs/${encodeURIComponent(jobId)}`),
  /** Confirm a waiting preview: an import's file is bound again and loaded (0.9 J3), a batch's items
   * applied (0.9 K2). */
  confirmJob: (jobId: string) => request<Job>(`/api/v1/jobs/${encodeURIComponent(jobId)}/confirm`, { method: "POST" }),
  /** Read an import preview's file again with other fields for some columns (0.17 PP-D26): a new preview. */
  rereadImport: (jobId: string, readings: { source: number; column: string; field: string }[]) =>
    request<Job>(`/api/v1/jobs/${encodeURIComponent(jobId)}/reread`, {
      method: "POST",
      body: JSON.stringify({ readings }),
    }),
  /** A job's item outcomes in item order (`GET /jobs/{id}/items`). */
  jobItems: (jobId: string, query: PageSelector & { status?: JobItemOutcome["status"]; pageSize?: number } = {}) => {
    const params = new URLSearchParams({ pageSize: String(query.pageSize ?? 50) });
    if (query.status) params.set("status", query.status);
    setPaging(params, query);
    return request<JobItemPage>(`/api/v1/jobs/${encodeURIComponent(jobId)}/items?${params}`);
  },
  /**
   * Send a batch (0.9 K2: always a background preview); the answer is the queued job. The
   * idempotency key makes a retried request answer with the job the first one created.
   */
  /** Run a batch inline and answer with its outcomes (UA9: moving several records at once). */
  runBatch: (body: BatchRequest, idempotencyKey: string) =>
    request<BatchResult>("/api/v1/batches", {
      method: "POST",
      body: JSON.stringify(body),
      headers: { "Idempotency-Key": idempotencyKey },
    }),
  startBatch: (body: BatchRequest, idempotencyKey: string) =>
    request<Job>("/api/v1/batches", {
      method: "POST",
      body: JSON.stringify(body),
      headers: { "Idempotency-Key": idempotencyKey },
    }),
  /**
   * Preview a migration of the workspace's data to an installed release (0.11 V1); the answer is the
   * queued `migration` job, which changes nothing until it is confirmed. Naming a change set (V2)
   * migrates to its release and publishes it with the migration.
   */
  startWorkspaceMigration: (
    workspaceKey: string,
    body: {
      targetReleaseId?: string;
      expectedVersion: number;
      typeMappings?: MigrationTypeMapping[];
      /** What a model draft's steps imply (0.13 MG), with the draft that proposed them. */
      relationTypeMappings?: MigrationRelationTypeMapping[];
      splits?: MigrationSplit[];
      listConversions?: MigrationListConversion[];
      draftId?: string;
      changeSetId?: string;
      expectedChangeSetVersion?: number;
    },
  ) =>
    request<Job>(`/api/v1/workspaces/${encodeURIComponent(workspaceKey)}/model/migrations`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  /**
   * Preview moving a change set onto the release its workspace runs, converting its content where
   * that release differs (0.11 V3); the answer is the queued `migration` job, which changes nothing
   * until it is confirmed.
   */
  startChangeSetMigration: (
    changeSetId: string,
    body: { expectedChangeSetVersion: number; typeMappings?: MigrationTypeMapping[] },
  ) =>
    request<Job>(`/api/v1/change-sets/${encodeURIComponent(changeSetId)}/model-migrations`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  /** Confirm a previewed migration, binding the reviewed versions (D74). */
  confirmMigration: (
    jobId: string,
    body: { expectedVersion: number; expectedFeedPosition: number; acceptLoss: boolean },
  ) =>
    request<Job>(`/api/v1/jobs/${encodeURIComponent(jobId)}/confirm`, { method: "POST", body: JSON.stringify(body) }),
  /** A migration's items of one outcome, in item order (0.11 V1). */
  migrationRows: (jobId: string, query: PageSelector & { status?: MigrationOutcome; pageSize?: number } = {}) => {
    const params = new URLSearchParams({ pageSize: String(query.pageSize ?? 50) });
    if (query.status) params.set("status", query.status);
    setPaging(params, query);
    return request<MigrationRowPage>(`/api/v1/jobs/${encodeURIComponent(jobId)}/rows?${params}`);
  },
  /** An import's rows with their outcomes, in sheet and row order (0.9 J3, D84). */
  jobRows: (jobId: string, query: PageSelector & { status?: JobRow["status"]; pageSize?: number } = {}) => {
    const params = new URLSearchParams({ pageSize: String(query.pageSize ?? 50) });
    if (query.status) params.set("status", query.status);
    setPaging(params, query);
    return request<JobRowPage>(`/api/v1/jobs/${encodeURIComponent(jobId)}/rows?${params}`);
  },
  /** Stored import profiles in key order, one page (0.9 J2). */
  importProfiles: (cursor?: string, workspaceKey?: string) => {
    const params = new URLSearchParams({ pageSize: "100" });
    if (cursor) params.set("cursor", cursor);
    if (workspaceKey) params.set("workspaceKey", workspaceKey);
    return request<ImportProfilePage>(`/api/v1/import-profiles?${params}`);
  },
  /**
   * Send a file to import (0.9 J2, J3); the answer is the queued job. The idempotency key makes a
   * retried request answer with the job the first one created.
   */
  startImport: (file: File, body: ImportRequest, idempotencyKey: string) => {
    const form = new FormData();
    form.append("file", file);
    form.append("request", JSON.stringify(body));
    return request<Job>("/api/v1/imports", {
      method: "POST",
      body: form,
      headers: { "Idempotency-Key": idempotencyKey },
    });
  },
  /** Import a stored source file (0.10 A3, D5): the request alone, naming `sourceFileId`. */
  startImportOfSourceFile: (body: ImportRequest & { sourceFileId: string }, idempotencyKey: string) => {
    const form = new FormData();
    form.append("request", JSON.stringify(body));
    return request<Job>("/api/v1/imports", {
      method: "POST",
      body: form,
      headers: { "Idempotency-Key": idempotencyKey },
    });
  },
  /** Upload a workbook to a draft or a stored profile (0.10 A3); its profiling is queued. */
  uploadSourceFile: (file: File, body: SourceFileUpload) => {
    const form = new FormData();
    form.append("file", file);
    form.append("request", JSON.stringify(body));
    return request<SourceFile>("/api/v1/source-files", { method: "POST", body: form });
  },
  sourceFile: (id: string) => request<SourceFile>(`/api/v1/source-files/${encodeURIComponent(id)}`),
  /** A profile's latest file (0.10 A5c): the newest of its source files, or none. */
  latestProfileFile: async (profileKey: string) => {
    const params = new URLSearchParams({ profileKey, pageSize: "1" });
    const page = await request<SourcePage<SourceFile>>(`/api/v1/source-files?${params}`);
    return page.items[0] as SourceFile | undefined;
  },
  /** A profile, valid or not under the release of `workspaceKey` (the default workspace without it). */
  importProfile: (key: string, workspaceKey?: string) =>
    request<ImportProfile>(
      `/api/v1/import-profiles/${encodeURIComponent(key)}${workspaceKey ? `?${new URLSearchParams({ workspaceKey })}` : ""}`,
    ),
  /** Delete a stored profile at its version (0.13 ED). */
  deleteImportProfile: (key: string, expectedVersion: number) =>
    request<void>(`/api/v1/import-profiles/${encodeURIComponent(key)}?expectedVersion=${expectedVersion}`, {
      method: "DELETE",
    }),
  /** Delete a source file, its staged cells and its profile at its version (0.13 ED). */
  deleteSourceFile: (id: string, expectedVersion: number) =>
    request<void>(`/api/v1/source-files/${encodeURIComponent(id)}?expectedVersion=${expectedVersion}`, {
      method: "DELETE",
    }),
  /** Replace a stored profile at its version (0.9 J2): every member but the key. */
  updateImportProfile: (profile: ImportProfile, sources: ImportProfileSource[], workspaceKey?: string) =>
    request<ImportProfile>(`/api/v1/import-profiles/${encodeURIComponent(profile.key)}`, {
      method: "PUT",
      body: JSON.stringify({
        name: profile.name,
        ...(profile.csv ? { csv: profile.csv } : {}),
        sources,
        valueMaps: profile.valueMaps,
        expectedVersion: profile.version,
        ...(workspaceKey ? { workspaceKey } : {}),
      }),
    }),
  /** The check of a profile's latest file in a workspace (0.10 A5c, D83; the workspace 0.12 E1, F5). */
  profileCheck: (key: string, workspaceKey: string) =>
    request<ProfileCheck>(
      `/api/v1/import-profiles/${encodeURIComponent(key)}/check?${new URLSearchParams({ workspaceKey })}`,
    ),
  /** Check the profile's current file in a workspace again, after the profile changed. */
  runProfileCheck: (key: string, workspaceKey: string) =>
    request<ProfileCheck>(
      `/api/v1/import-profiles/${encodeURIComponent(key)}/check?${new URLSearchParams({ workspaceKey })}`,
      { method: "POST" },
    ),
  /** One of the check's lists, a page: new values, drifting names, records missing from the file. */
  profileCheckList: <Item extends CheckNewValue | CheckDrift | CheckMissingRecord>(
    key: string,
    workspaceKey: string,
    list: "new-values" | "drift" | "missing-records",
    query: PageSelector & { source?: number; pageSize?: number },
  ) => {
    const params = new URLSearchParams({ workspaceKey, pageSize: String(query.pageSize ?? 50) });
    if (query.source !== undefined) params.set("source", String(query.source));
    setPaging(params, query);
    return request<SourcePage<Item>>(`/api/v1/import-profiles/${encodeURIComponent(key)}/check/${list}?${params}`);
  },
  /** The rows behind the check's figures, as a dry run's. */
  profileCheckRows: (
    key: string,
    workspaceKey: string,
    query: PageSelector & { source?: number; status?: JobRow["status"]; code?: string; pageSize?: number },
  ) => {
    const params = new URLSearchParams({ workspaceKey, pageSize: String(query.pageSize ?? 50) });
    if (query.source !== undefined) params.set("source", String(query.source));
    if (query.status) params.set("status", query.status);
    if (query.code) params.set("code", query.code);
    setPaging(params, query);
    return request<JobRowPage>(`/api/v1/import-profiles/${encodeURIComponent(key)}/check/rows?${params}`);
  },
  /** A profiled file's sheets in workbook order, one page of up to 500. */
  sourceSheets: (id: string, cursor?: string) => {
    const params = new URLSearchParams({ pageSize: "500" });
    if (cursor) params.set("cursor", cursor);
    return request<SourcePage<SourceSheet>>(`/api/v1/source-files/${encodeURIComponent(id)}/profile/sheets?${params}`);
  },
  /** A sheet's profiled columns in column order, one page of up to 500. */
  sourceColumns: (id: string, sheet: string, cursor?: string) => {
    const params = new URLSearchParams({ pageSize: "500" });
    if (cursor) params.set("cursor", cursor);
    return request<SourcePage<SourceColumn>>(
      `/api/v1/source-files/${encodeURIComponent(id)}/profile/sheets/${encodeURIComponent(sheet)}/columns?${params}`,
    );
  },
  /** The rows of a range of a sheet holding a cell, one page (0.10 A8b, D124). */
  sourceCells: (id: string, sheet: string, range: string, cursor?: string) => {
    const params = new URLSearchParams({ pageSize: "500", range });
    if (cursor) params.set("cursor", cursor);
    return request<SourcePage<SourceCellRow>>(
      `/api/v1/source-files/${encodeURIComponent(id)}/profile/sheets/${encodeURIComponent(sheet)}/cells?${params}`,
    );
  },
  /** A rectangle of the draft's file read as a list, answered and not stored (0.10 A8b, D128). */
  proposeList: (draftId: string, body: { sheet: string } & SourceRectangle) =>
    request<ListProposal>(`/api/v1/model-drafts/${encodeURIComponent(draftId)}/inference/list`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  /** Which column of a table a column's values point at, over every row, answered and not stored (0.17 PP-D8). */
  joinCandidates: (draftId: string, body: JoinCandidatesRequest) =>
    request<JoinCandidates>(`/api/v1/model-drafts/${encodeURIComponent(draftId)}/join-candidates`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  /** Where the cards of the draft's workbook canvas sit; not part of the draft's version (0.17 PP-D54). */
  modelDraftCanvas: (draftId: string) => request<Canvas>(`/api/v1/model-drafts/${encodeURIComponent(draftId)}/canvas`),
  /** Merges card positions by key; `null` removes a card. */
  moveCanvasCards: (draftId: string, positions: Record<string, CanvasPosition | null>) =>
    request<Canvas>(`/api/v1/model-drafts/${encodeURIComponent(draftId)}/canvas`, {
      method: "PATCH",
      body: JSON.stringify({ positions }),
    }),
  /** Merges positions and folded cards by key and replaces the scope (0.17 CE1, PP-D81); a part left out stays. */
  arrangeCanvas: (draftId: string, update: CanvasUpdate) =>
    request<Canvas>(`/api/v1/model-drafts/${encodeURIComponent(draftId)}/canvas`, {
      method: "PATCH",
      body: JSON.stringify(update),
    }),
  /** The draft's import profile with its warnings and its source file (0.10 A5, D75). */
  modelDraftProfile: (draftId: string) =>
    request<DraftProfile>(`/api/v1/model-drafts/${encodeURIComponent(draftId)}/profile`),
  /** The draft's latest dry run (0.10 A3, D67). */
  modelDraftDryRun: (draftId: string) => request<DryRun>(`/api/v1/model-drafts/${encodeURIComponent(draftId)}/dry-run`),
  /** The latest dry run's rows behind a figure: a source's, by status or refusal code. */
  modelDraftDryRunRows: (
    draftId: string,
    query: PageSelector & { source?: number; status?: JobRow["status"]; code?: string; pageSize?: number },
  ) => {
    const params = new URLSearchParams({ pageSize: String(query.pageSize ?? 50) });
    if (query.source !== undefined) params.set("source", String(query.source));
    if (query.status) params.set("status", query.status);
    if (query.code) params.set("code", query.code);
    setPaging(params, query);
    return request<JobRowPage>(`/api/v1/model-drafts/${encodeURIComponent(draftId)}/dry-run/rows?${params}`);
  },
  /** Propose a model and its mapping from the draft's workbook (0.10 A6, D87); applies nothing. */
  proposeFromWorkbook: (draftId: string, body: InferenceRequest) =>
    request<Inference>(`/api/v1/model-drafts/${encodeURIComponent(draftId)}/inference`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  /** The draft's latest inference (D87). */
  /** The draft's latest inference. ``fresh`` makes a request of its own rather than joining an
   * identical read in flight (D157), whose answer may predate a change just announced. */
  modelDraftInference: (draftId: string, fresh = false) =>
    request<Inference>(
      `/api/v1/model-drafts/${encodeURIComponent(draftId)}/inference`,
      fresh ? { signal: new AbortController().signal } : undefined,
    ),
  /** Every proposal of the draft's latest inference, in the order they apply. */
  modelDraftProposals: async (draftId: string) => {
    const items: Proposal[] = [];
    let cursor: string | null = null;
    do {
      const params = new URLSearchParams({ pageSize: "500" });
      if (cursor) params.set("cursor", cursor);
      const page: SourcePage<Proposal> = await request<SourcePage<Proposal>>(
        `/api/v1/model-drafts/${encodeURIComponent(draftId)}/inference/proposals?${params}`,
      );
      items.push(...page.items);
      cursor = page.nextCursor;
    } while (cursor);
    return items;
  },
  /** Apply the latest inference's proposals (every open one by default), one step each (D89). */
  applyProposals: (draftId: string, expectedVersion: number, proposals?: string[]) =>
    request<ModelDraftStep>(`/api/v1/model-drafts/${encodeURIComponent(draftId)}/inference/application`, {
      method: "POST",
      body: JSON.stringify({ expectedVersion, ...(proposals ? { proposals } : {}) }),
    }),
  /** Model mappings in key order, optionally between two models (0.11 X1). */
  modelMappings: (query: { sourceModelKey?: string; targetModelKey?: string; cursor?: string } = {}) => {
    const params = new URLSearchParams({ pageSize: "100" });
    if (query.sourceModelKey) params.set("sourceModelKey", query.sourceModelKey);
    if (query.targetModelKey) params.set("targetModelKey", query.targetModelKey);
    if (query.cursor) params.set("cursor", query.cursor);
    return request<ModelMappingPage>(`/api/v1/model-mappings?${params}`);
  },
  /** A mapping with its problems and coverage against the releases the two workspaces run (D110). */
  modelMapping: (key: string, workspaces: { source?: string; target?: string } = {}) => {
    const params = new URLSearchParams();
    if (workspaces.source) params.set("sourceWorkspaceKey", workspaces.source);
    if (workspaces.target) params.set("targetWorkspaceKey", workspaces.target);
    return request<ModelMapping>(`/api/v1/model-mappings/${encodeURIComponent(key)}?${params}`);
  },
  /** A mapping between the releases two workspaces run, with no type mapped (D104). */
  /** Delete a mapping with its history and proposals at its version (0.13 ED). */
  deleteModelMapping: (key: string, expectedVersion: number) =>
    request<void>(`/api/v1/model-mappings/${encodeURIComponent(key)}?expectedVersion=${expectedVersion}`, {
      method: "DELETE",
    }),
  createModelMapping: (body: { key: string; name: string; sourceWorkspaceKey: string; targetWorkspaceKey: string }) =>
    request<ModelMapping>("/api/v1/model-mappings", { method: "POST", body: JSON.stringify(body) }),
  /** One step of a mapping's history (D107). */
  mappingOperations: (key: string, expectedVersion: number, operations: MappingOperation[]) =>
    request<ModelMappingStep>(`/api/v1/model-mappings/${encodeURIComponent(key)}/operations`, {
      method: "POST",
      body: JSON.stringify({ expectedVersion, operations }),
    }),
  /** A mapping's history in sequence order, every page (D105). */
  mappingHistory: (key: string) =>
    everyPage((cursor) => {
      const params = new URLSearchParams({ pageSize: "500" });
      if (cursor) params.set("cursor", cursor);
      return request<{ items: ModelMappingOperationEntry[]; nextCursor: string | null }>(
        `/api/v1/model-mappings/${encodeURIComponent(key)}/operations?${params}`,
      );
    }),
  undoMapping: (key: string, expectedVersion: number) =>
    request<ModelMappingStep>(`/api/v1/model-mappings/${encodeURIComponent(key)}/undo`, {
      method: "POST",
      body: JSON.stringify({ expectedVersion }),
    }),
  redoMapping: (key: string, expectedVersion: number) =>
    request<ModelMappingStep>(`/api/v1/model-mappings/${encodeURIComponent(key)}/redo`, {
      method: "POST",
      body: JSON.stringify({ expectedVersion }),
    }),
  /** Propose the mapping from its two models and the two workspaces' records (D108). */
  proposeMapping: (key: string, sourceWorkspaceKey: string, targetWorkspaceKey: string) =>
    request<MappingInference>(`/api/v1/model-mappings/${encodeURIComponent(key)}/inference`, {
      method: "POST",
      body: JSON.stringify({ sourceWorkspaceKey, targetWorkspaceKey }),
    }),
  mappingInference: (key: string) =>
    request<MappingInference>(`/api/v1/model-mappings/${encodeURIComponent(key)}/inference`),
  /** Every proposal of the mapping's latest inference, in the order they apply. */
  mappingProposals: async (key: string) => {
    const items: MappingProposal[] = [];
    let cursor: string | null = null;
    do {
      const params = new URLSearchParams({ pageSize: "500" });
      if (cursor) params.set("cursor", cursor);
      const page: SourcePage<MappingProposal> = await request<SourcePage<MappingProposal>>(
        `/api/v1/model-mappings/${encodeURIComponent(key)}/inference/proposals?${params}`,
      );
      items.push(...page.items);
      cursor = page.nextCursor;
    } while (cursor);
    return items;
  },
  /** Apply the latest inference's open proposals, each one step of origin `proposal`. */
  applyMappingProposals: (key: string, expectedVersion: number) =>
    request<ModelMappingStep>(`/api/v1/model-mappings/${encodeURIComponent(key)}/inference/application`, {
      method: "POST",
      body: JSON.stringify({ expectedVersion }),
    }),
  /** A move's dry run (0.11 X2), waiting for confirmation once it has run (X3, D128). */
  startMove: (body: MoveRequest) => request<Job>("/api/v1/moves", { method: "POST", body: JSON.stringify(body) }),
  /** A move's rows in their order, kept to an outcome, a reason's code or a source type (D119). */
  moveRows: (
    jobId: string,
    query: PageSelector & { outcome?: MoveOutcome; reason?: string; sourceType?: string; pageSize?: number } = {},
  ) => {
    const params = new URLSearchParams({ pageSize: String(query.pageSize ?? 50) });
    if (query.outcome) params.set("outcome", query.outcome);
    if (query.reason) params.set("reason", query.reason);
    if (query.sourceType) params.set("sourceType", query.sourceType);
    setPaging(params, query);
    return request<MoveRowPage>(`/api/v1/jobs/${encodeURIComponent(jobId)}/rows?${params}`);
  },
  /** Moves of every workspace, newest first. */
  moveJobs: (cursor?: string) => {
    const params = new URLSearchParams({ pageSize: "50", kind: "move" });
    if (cursor) params.set("cursor", cursor);
    return request<JobPage>(`/api/v1/jobs?${params}`);
  },
  renameChangeSet: (id: string, name: string, expectedVersion: number) =>
    request<ChangeSet>(`/api/v1/change-sets/${encodeURIComponent(id)}`, {
      method: "PATCH",
      body: JSON.stringify({ name, expectedVersion }),
    }),
  /** Queue an export (0.9 J1); the answer is the queued job. */
  createExport: (body: ExportRequest) =>
    request<Job>("/api/v1/exports", { method: "POST", body: JSON.stringify(body) }),
  workspaces: (
    options: {
      search?: string;
      status?: "active" | "retired" | "all";
      cursor?: string;
      pageSize?: number;
      /** Only those where the caller holds this action group (0.12 Z5, D327). */
      holding?: string;
    } = {},
  ) => {
    const params = new URLSearchParams({
      status: options.status ?? "active",
      pageSize: String(options.pageSize ?? 100),
    });
    if (options.search) params.set("search", options.search);
    if (options.holding) params.set("holding", options.holding);
    if (options.cursor) params.set("cursor", options.cursor);
    return request<WorkspacePage>(`/api/v1/workspaces?${params}`);
  },
  workspace: (workspaceKey: string) =>
    request<WorkspaceDetail>(`/api/v1/workspaces/${encodeURIComponent(workspaceKey)}`),
  /** A new workspace, on `modelReleaseId` or on the default workspace's release (0.11 M1, D54). */
  createWorkspace: (body: { key: string; label: string; modelReleaseId?: string }) =>
    request<WorkspaceDetail>("/api/v1/workspaces", { method: "POST", body: JSON.stringify(body) }),
  /** A workspace from the draft a workbook made: installed, created on its release, its workbook loading as a job. */
  createWorkspaceFromWorkbook: (body: { draftId: string; expectedVersion: number; name: string; key?: string }) =>
    request<WorkspaceFromWorkbook>("/api/v1/workspaces/from-workbook", { method: "POST", body: JSON.stringify(body) }),
  updateWorkspace: (
    workspaceKey: string,
    body: { expectedVersion: number; label?: string; status?: Workspace["status"] },
  ) =>
    request<WorkspaceDetail>(`/api/v1/workspaces/${encodeURIComponent(workspaceKey)}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  deleteWorkspace: (workspaceKey: string, expectedVersion: number) =>
    request<void>(`/api/v1/workspaces/${encodeURIComponent(workspaceKey)}?expectedVersion=${expectedVersion}`, {
      method: "DELETE",
    }),
  setDefaultWorkspace: (defaultWorkspaceKey: string, expectedVersion: number) =>
    request<WorkspaceRuntimeState>("/api/v1/workspace-runtime-state", {
      method: "PATCH",
      body: JSON.stringify({ defaultWorkspaceKey, expectedVersion }),
    }),
  /** A workspace's open change sets; `createdBy` keeps one person's or client's (0.12 Z5, D325). */
  changeSets: (workspaceKey: string, cursor?: string, createdBy?: string) => {
    const query = new URLSearchParams({ pageSize: "50" });
    if (cursor) query.set("cursor", cursor);
    if (createdBy) query.set("createdBy", createdBy);
    return request<ChangeSetPage>(`/api/v1/workspaces/${encodeURIComponent(workspaceKey)}/change-sets?${query}`);
  },
  changeSet: (id: string) => request<ChangeSet>(`/api/v1/change-sets/${encodeURIComponent(id)}`),
  createChangeSet: (workspaceKey: string, name: string, modelReleaseId?: string) =>
    request<ChangeSet>(`/api/v1/workspaces/${encodeURIComponent(workspaceKey)}/change-sets`, {
      method: "POST",
      body: JSON.stringify({ name, source: "currentLive", ...(modelReleaseId ? { modelReleaseId } : {}) }),
    }),
  createChangeSetFromPublication: (workspaceKey: string, name: string, publicationId: string) =>
    request<ChangeSet>(`/api/v1/workspaces/${encodeURIComponent(workspaceKey)}/change-sets`, {
      method: "POST",
      body: JSON.stringify({ name, source: "publication", derivedFromPublicationId: publicationId }),
    }),
  discardChangeSet: (id: string, expectedVersion: number) =>
    request<void>(`/api/v1/change-sets/${encodeURIComponent(id)}?expectedVersion=${expectedVersion}`, {
      method: "DELETE",
    }),
  validateChangeSet: (id: string) =>
    request<ChangeSetValidation>(`/api/v1/change-sets/${encodeURIComponent(id)}/validation`, {
      method: "POST",
    }),
  publishChangeSet: (id: string, expectedChangeSetVersion: number, expectedActivePublicationId: string | null) =>
    request<Publication>(`/api/v1/change-sets/${encodeURIComponent(id)}/publication`, {
      method: "POST",
      body: JSON.stringify({ expectedChangeSetVersion, expectedActivePublicationId }),
    }),
  /** Asks for the change set to be published (0.12 A3); the change set must validate. */
  submitChangeSet: (id: string, expectedChangeSetVersion: number, comment?: string) =>
    request<PublicationRequest>(`/api/v1/change-sets/${encodeURIComponent(id)}/submission`, {
      method: "POST",
      body: JSON.stringify({ expectedChangeSetVersion, ...(comment ? { comment } : {}) }),
    }),
  withdrawSubmission: (id: string) =>
    request<void>(`/api/v1/change-sets/${encodeURIComponent(id)}/submission`, { method: "DELETE" }),
  /** Approving publishes (answers the Publication); sending back returns the change set to open. */
  decideChangeSet: (
    id: string,
    decision: {
      outcome: "approve" | "sendBack";
      comment?: string;
      expectedChangeSetVersion: number;
      expectedActivePublicationId?: string | null;
    },
  ) =>
    request<Publication | ChangeSet>(`/api/v1/change-sets/${encodeURIComponent(id)}/decisions`, {
      method: "POST",
      body: JSON.stringify(decision),
    }),
  publicationRequests: (
    workspaceKey: string,
    options: { state?: PublicationRequest["state"]; cursor?: string } = {},
  ) => {
    const query = new URLSearchParams({ pageSize: "50" });
    if (options.state) query.set("state", options.state);
    if (options.cursor) query.set("cursor", options.cursor);
    return request<PublicationRequestPage>(
      `/api/v1/workspaces/${encodeURIComponent(workspaceKey)}/publication-requests?${query}`,
    );
  },
  approvalPolicy: (workspaceKey: string) =>
    request<ApprovalPolicy>(`/api/v1/workspaces/${encodeURIComponent(workspaceKey)}/approval-policy`),
  setApprovalPolicy: (
    workspaceKey: string,
    policy: { requireApproval: boolean; secondPerson: boolean; expectedVersion: number },
  ) =>
    request<ApprovalPolicy>(`/api/v1/workspaces/${encodeURIComponent(workspaceKey)}/approval-policy`, {
      method: "PUT",
      body: JSON.stringify(policy),
    }),
  setChangeSetModelRelease: (changeSetId: string, modelReleaseId: string, expectedChangeSetVersion: number) =>
    request<ChangeSet>(`/api/v1/change-sets/${encodeURIComponent(changeSetId)}/model-release`, {
      method: "PATCH",
      body: JSON.stringify({ modelReleaseId, expectedChangeSetVersion }),
    }),
  latestPublication: (workspaceKey: string) =>
    request<{ items: Publication[]; nextCursor: string | null }>(
      `/api/v1/workspaces/${encodeURIComponent(workspaceKey)}/publications?pageSize=1`,
    ),
  publications: (workspaceKey: string, cursor?: string) => {
    const query = new URLSearchParams({ pageSize: "50" });
    if (cursor) query.set("cursor", cursor);
    return request<PublicationPage>(`/api/v1/workspaces/${encodeURIComponent(workspaceKey)}/publications?${query}`);
  },
  /** What a change set adds, changes and removes against its source (Base 0.8 P2a). */
  objectChanges: (changeSetId: string, query: ChangeListQuery & { objectTypeKeys?: string[] }) => {
    const params = changeListParams(query);
    query.objectTypeKeys?.forEach((key) => params.append("objectTypeKey", key));
    return request<ObjectChangePage>(`/api/v1/change-sets/${encodeURIComponent(changeSetId)}/object-changes?${params}`);
  },
  relationChanges: (
    changeSetId: string,
    query: ChangeListQuery & { relationTypeKeys?: string[]; containment?: boolean },
  ) => {
    const params = changeListParams(query);
    query.relationTypeKeys?.forEach((key) => params.append("relationTypeKey", key));
    if (query.containment !== undefined) params.set("containment", String(query.containment));
    return request<RelationChangePage>(
      `/api/v1/change-sets/${encodeURIComponent(changeSetId)}/relation-changes?${params}`,
    );
  },
  publication: (id: string) => request<Publication>(`/api/v1/publications/${encodeURIComponent(id)}`),
  withdrawPublication: (publicationId: string) =>
    request<void>(`/api/v1/publications/${encodeURIComponent(publicationId)}/withdrawal`, { method: "POST" }),
  workspaceRuntimeState: () => request<WorkspaceRuntimeState>("/api/v1/workspace-runtime-state"),
  /** Installed releases; `usable` keeps those that may be chosen: active, of a schema this version reads (MR1). */
  modelReleases: (options: { cursor?: string; pageSize?: number; usable?: boolean } = {}) => {
    const params = new URLSearchParams({ pageSize: String(options.pageSize ?? 100) });
    if (options.cursor) params.set("cursor", options.cursor);
    if (options.usable) params.set("usable", "true");
    return request<ModelReleasePage>(`/api/v1/model-releases?${params}`);
  },
  /** Retire a release, or bring it back (0.12 MR1). */
  setModelReleaseStatus: (release: Pick<ModelReleaseSummary, "id" | "statusVersion">, status: "active" | "retired") =>
    request<ModelRelease>(`/api/v1/model-releases/${encodeURIComponent(release.id)}`, {
      method: "PATCH",
      body: JSON.stringify({ status, expectedStatusVersion: release.statusVersion }),
    }),
  /** Delete a release nothing refers to (0.12 MR1). */
  deleteModelRelease: (release: Pick<ModelReleaseSummary, "id" | "statusVersion">) =>
    request<void>(
      `/api/v1/model-releases/${encodeURIComponent(release.id)}?expectedStatusVersion=${release.statusVersion}`,
      { method: "DELETE" },
    ),
  modelRelease: (releaseId: string, includeModel = false) =>
    request<ModelRelease>(`/api/v1/model-releases/${encodeURIComponent(releaseId)}?includeModel=${includeModel}`),
  modelReleaseActivations: (releaseId: string, options: { cursor?: string; pageSize?: number } = {}) => {
    const params = new URLSearchParams({ pageSize: String(options.pageSize ?? 100) });
    if (options.cursor) params.set("cursor", options.cursor);
    return request<ModelReleaseActivationPage>(
      `/api/v1/model-releases/${encodeURIComponent(releaseId)}/activations?${params}`,
    );
  },
  /** `compatibility` describes activating into `workspaceKey`, the default workspace without it (D52). */
  modelReleaseDiff: (releaseId: string, againstReleaseId: string, workspaceKey?: string) => {
    const params = new URLSearchParams({ againstReleaseId });
    if (workspaceKey) params.set("workspaceKey", workspaceKey);
    return request<ModelReleaseDiff>(`/api/v1/model-releases/${encodeURIComponent(releaseId)}/diff?${params}`);
  },
  /** Preview raising a release to the window's schema language; nothing changes (0.12 UW1, D444). */
  previewModelReleaseRaising: (releaseId: string) =>
    request<ModelReleaseRaising>(`/api/v1/model-releases/${encodeURIComponent(releaseId)}/raising`, {
      method: "POST",
      body: JSON.stringify({ confirm: false }),
    }),
  /** Raise the release in place; `expectedModelHash` is the preview's `modelHash`. */
  raiseModelRelease: (releaseId: string, expectedModelHash: string) =>
    request<ModelReleaseRaising>(`/api/v1/model-releases/${encodeURIComponent(releaseId)}/raising`, {
      method: "POST",
      body: JSON.stringify({ confirm: true, expectedModelHash }),
    }),
  workspaceModel: (workspaceKey: string) =>
    request<WorkspaceModel>(`/api/v1/workspaces/${encodeURIComponent(workspaceKey)}/model`),
  validateModel: (model: Record<string, unknown>) =>
    request<ModelValidation>("/api/v1/model-validations", { method: "POST", body: JSON.stringify({ model }) }),
  modelDrafts: (options: { cursor?: string; pageSize?: number } = {}) => {
    const params = new URLSearchParams({ pageSize: String(options.pageSize ?? 100) });
    if (options.cursor) params.set("cursor", options.cursor);
    return request<ModelDraftPage>(`/api/v1/model-drafts?${params}`);
  },
  modelDraft: (draftId: string) => request<ModelDraft>(`/api/v1/model-drafts/${encodeURIComponent(draftId)}`),
  createModelDraft: (payload: { name: string; baseReleaseId?: string; model: Record<string, unknown> }) =>
    request<ModelDraft>("/api/v1/model-drafts", { method: "POST", body: JSON.stringify(payload) }),
  updateModelDraft: (
    draftId: string,
    payload: { expectedVersion: number; name?: string; model?: Record<string, unknown> },
  ) =>
    request<ModelDraft>(`/api/v1/model-drafts/${encodeURIComponent(draftId)}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  deleteModelDraft: (draftId: string, expectedVersion: number) =>
    request<void>(`/api/v1/model-drafts/${encodeURIComponent(draftId)}?expectedVersion=${expectedVersion}`, {
      method: "DELETE",
    }),
  compileModelDraft: (draftId: string, expectedVersion: number) =>
    request<ModelCompilation>(`/api/v1/model-drafts/${encodeURIComponent(draftId)}/compile`, {
      method: "POST",
      body: JSON.stringify({ expectedVersion }),
    }),
  /** The draft of the model a workspace runs, made when there is none (0.16 WM1). */
  openWorkspaceModelDraft: (workspaceKey: string) =>
    request<ModelDraft>(`/api/v1/workspaces/${encodeURIComponent(workspaceKey)}/model/draft`, { method: "POST" }),
  installModelDraft: (draftId: string, expectedVersion: number) =>
    request<ModelInstallation>(`/api/v1/model-drafts/${encodeURIComponent(draftId)}/installation`, {
      method: "POST",
      body: JSON.stringify({ expectedVersion }),
    }),
  /** The migration a draft states against its base release; with a workspace, what it would do to its records (0.13 MG). */
  modelDraftMigration: (
    draftId: string,
    workspaceKey?: string,
    between?: { againstReleaseId?: string; toReleaseId?: string },
  ) => {
    const params = new URLSearchParams();
    if (workspaceKey) params.set("workspaceKey", workspaceKey);
    if (between?.againstReleaseId) params.set("againstReleaseId", between.againstReleaseId);
    if (between?.toReleaseId) params.set("toReleaseId", between.toReleaseId);
    const query = params.toString();
    return request<DraftMigration>(
      `/api/v1/model-drafts/${encodeURIComponent(draftId)}/migration${query ? `?${query}` : ""}`,
    );
  },
  modelDraftOutline: (draftId: string) =>
    request<ModelDraftOutline>(`/api/v1/model-drafts/${encodeURIComponent(draftId)}/outline`),
  /** The draft compiled as `model` serves the active one, with its placements (0.10 A4b, D43). */
  modelDraftModel: (draftId: string) =>
    request<ModelDraftModel>(`/api/v1/model-drafts/${encodeURIComponent(draftId)}/model`),
  /** A consumer API definition of the draft, with its defaults and contract (0.10 A4c, D56). */
  modelDraftConsumerApi: (draftId: string, consumerApi: string) =>
    request<ModelDraftConsumerApi>(
      `/api/v1/model-drafts/${encodeURIComponent(draftId)}/consumer-apis/${encodeURIComponent(consumerApi)}`,
    ),
  /** Its schema, a message example or its OpenAPI document, from the draft (D56). */
  modelDraftConsumerApiDocument: (draftId: string, consumerApi: string, document: ConsumerApiDocumentKind) =>
    request<Record<string, unknown>>(consumerApiDocumentPath(draftId, consumerApi, document)),
  applyModelDraftOperations: (draftId: string, expectedVersion: number, operations: DraftOperation[]) =>
    request<ModelDraftStep>(`/api/v1/model-drafts/${encodeURIComponent(draftId)}/operations`, {
      method: "POST",
      body: JSON.stringify({ expectedVersion, operations }),
    }),
  /** The draft's history read from its end: `cursor` is a page's `prevCursor`, towards older steps. */
  modelDraftOperations: (draftId: string, options: { cursor?: string; pageSize?: number } = {}) => {
    const params = new URLSearchParams({ pageSize: String(options.pageSize ?? 100) });
    if (options.cursor) params.set("cursor", options.cursor);
    else params.set("from", "end");
    return request<ModelDraftOperationPage>(`/api/v1/model-drafts/${encodeURIComponent(draftId)}/operations?${params}`);
  },
  undoModelDraftStep: (draftId: string, expectedVersion: number, steps?: number[]) =>
    request<ModelDraftStep>(`/api/v1/model-drafts/${encodeURIComponent(draftId)}/undo`, {
      method: "POST",
      body: JSON.stringify({
        expectedVersion,
        ...(steps?.length === 1 ? { step: steps[0] } : steps?.length ? { steps } : {}),
      }),
    }),
  redoModelDraftStep: (draftId: string, expectedVersion: number) =>
    request<ModelDraftStep>(`/api/v1/model-drafts/${encodeURIComponent(draftId)}/redo`, {
      method: "POST",
      body: JSON.stringify({ expectedVersion }),
    }),
  /** ``releaseId`` activated into the workspace of ``current``, claiming its assignment (0.11 M1). */
  activateWorkspaceModel: (releaseId: string, current: WorkspaceModel) =>
    request<WorkspaceModelActivation>(
      `/api/v1/workspaces/${encodeURIComponent(current.workspaceKey)}/model/activation`,
      {
        method: "POST",
        body: JSON.stringify({ releaseId, expectedVersion: current.version, expectedReleaseId: current.releaseId }),
      },
    ),
  objects: (objectTypeKey: string, query: ObjectQuery) => request<ObjectPage>(objectQueryPath(objectTypeKey, query)),
  /**
   * Records of every type in a workspace whose name holds `search`, grouped by type (the cross-type
   * lookup, `GET /objects`; 0.17 SH1).
   */
  findRecords: (workspaceKey: string, search: string, pageSize = 30) =>
    request<ObjectPage>(
      `/api/v1/objects?${new URLSearchParams({ workspaceKey, search, sort: "objectType", pageSize: String(pageSize) })}`,
    ),
  /**
   * Records of every type whose name holds `search`, across several workspaces at once, each read under its
   * own workspace's model (the cross-type lookup with `workspaceKey` repeated; Home's search, 0.17 UX1).
   */
  findRecordsAcross: (workspaceKeys: readonly string[], search: string, pageSize = 40) => {
    const params = new URLSearchParams({ search, sort: "name", pageSize: String(pageSize) });
    for (const key of workspaceKeys) params.append("workspaceKey", key);
    return request<ObjectPage>(`/api/v1/objects?${params}`);
  },
  /** How many records of one type a workspace holds live (a list's size on the workspace's page, 0.17 UX1). */
  countRecords: (workspaceKey: string, objectTypeKey: string) =>
    request<ObjectPage>(
      `/api/v1/objects?${new URLSearchParams({ workspaceKey, objectTypeKey, pageSize: "1", includeTotal: "true" })}`,
    ).then((page) => page.totalCount),
  object: (
    objectTypeKey: string,
    objectId: string,
    workspaceKey?: string,
    changeSetId?: string,
    publicationId?: string,
  ) =>
    request<ObjectItem>(
      withWorkspace(
        `/api/v1/objects/${encodeURIComponent(objectTypeKey)}/${encodeURIComponent(objectId)}`,
        workspaceKey,
        changeSetId,
        publicationId,
      ),
    ),
  /** Where a record could move, live or in a change set; publications have no move targets. */
  parentCandidates: (
    objectTypeKey: string,
    objectId: string,
    query: PageSelector & {
      workspaceKey?: string;
      changeSetId?: string;
      parentObjectTypeKey?: string;
      search?: string;
      pageSize?: number;
      /** In a change set, also targets a type change makes possible (C3). */
      includeTypeChanges?: boolean;
      /** Keeps candidates, and the types the record would become, to these types (C4). */
      withinObjectTypeKeys?: readonly string[];
    },
  ) => {
    const params = new URLSearchParams();
    if (query.changeSetId) params.set("changeSetId", query.changeSetId);
    else if (query.workspaceKey) params.set("workspaceKey", query.workspaceKey);
    if (query.parentObjectTypeKey) params.set("parentObjectTypeKey", query.parentObjectTypeKey);
    if (query.includeTypeChanges) params.set("includeTypeChanges", "true");
    query.withinObjectTypeKeys?.forEach((key) => params.append("withinObjectTypeKey", key));
    if (query.search) params.set("search", query.search);
    if (query.pageSize != null) params.set("pageSize", String(query.pageSize));
    setPaging(params, query);
    return request<ParentCandidatePage>(
      `/api/v1/objects/${encodeURIComponent(objectTypeKey)}/${encodeURIComponent(objectId)}/parent-candidates?${params}`,
    );
  },
  /**
   * Plans a restructuring in a change set and returns a page of its records (Base 0.8 C3); writes
   * nothing. A restructuring has no live form (D38), so the change set is required.
   */
  previewRestructuring: (
    body: RestructuringRequest,
    query: PageSelector & {
      changeSetId?: string;
      expectedChangeSetVersion?: number;
      outcome?: RestructuringOutcomeFilter[];
      pageSize?: number;
    },
  ) =>
    request<RestructuringPreview>(`${restructuringsPath(query.changeSetId)}/preview`, {
      method: "POST",
      body: JSON.stringify({
        ...body,
        ...(query.expectedChangeSetVersion ? { expectedChangeSetVersion: query.expectedChangeSetVersion } : {}),
        ...(query.outcome?.length ? { outcome: query.outcome } : {}),
        ...(query.pageSize ? { pageSize: query.pageSize } : {}),
        ...(query.cursor ? { cursor: query.cursor } : {}),
        ...(query.position !== undefined ? { position: query.position } : {}),
        ...(query.fromEnd ? { from: "end" } : {}),
        ...(query.includeTotal ? { includeTotal: true } : {}),
      }),
    }),
  /** Applies a previewed restructuring, claimed by the version the preview read and its digest. */
  applyRestructuring: (
    body: RestructuringRequest & { expectedChangeSetVersion: number; planDigest: string },
    context: ChangeSetWriteContext = {},
  ) =>
    request<RestructuringResult>(restructuringsPath(context.changeSetId), {
      method: "POST",
      body: JSON.stringify(body),
    }),
  createObject: (
    objectTypeKey: string,
    payload: ChangeSetWriteContext & {
      applicationKey: string;
      workspaceKey: string;
      name: string;
      parentObjectId?: string;
      attributes: ObjectAttributeInput[];
      initialRelations?: InitialRelationInput[];
    },
  ) =>
    request<ObjectItem>("/api/v1/objects", {
      method: "POST",
      body: JSON.stringify({ ...payload, objectTypeKey }),
    }),
  /**
   * Creates a record in a place that does not exist yet, as one atomic change (0.17 PP-D24): the place
   * under its parent, then the record under the place, in the same context. A refusal of either item
   * is thrown with its own message and nothing is written.
   */
  createObjectInNewPlace: async (
    objectTypeKey: string,
    payload: ChangeSetWriteContext & {
      applicationKey: string;
      workspaceKey: string;
      name: string;
      attributes: ObjectAttributeInput[];
      initialRelations?: InitialRelationInput[];
    },
    place: {
      applicationKey: string;
      objectTypeKey: string;
      name: string;
      parentObjectId: string;
      attributes: ObjectAttributeInput[];
    },
  ) => {
    const placeId = crypto.randomUUID();
    const { initialRelations = [], changeSetId, expectedChangeSetVersion, workspaceKey, ...record } = payload;
    const result = await request<BatchResult>("/api/v1/batches", {
      method: "POST",
      headers: { "Idempotency-Key": crypto.randomUUID() },
      body: JSON.stringify({
        ...(changeSetId ? { changeSetId, expectedChangeSetVersion } : { workspaceKey }),
        policy: "atomic",
        run: "inline",
        stage: "execute",
        items: [
          {
            op: "create",
            id: placeId,
            applicationKey: place.applicationKey,
            objectTypeKey: place.objectTypeKey,
            name: place.name,
            parent: { id: place.parentObjectId },
            attributes: place.attributes,
          },
          {
            op: "create",
            ...record,
            objectTypeKey,
            parent: { id: placeId },
            initialRelations: initialRelations.map(({ otherObjectId, ...rest }) => ({
              ...rest,
              object: { id: otherObjectId },
            })),
          },
        ],
      }),
    });
    if (result.job.result !== "applied") {
      const refused = result.items.find((item) => item.status === "rejected" && item.error);
      throw new ApiError(
        422,
        refused?.error?.code ?? "BATCH_REFUSED",
        refused?.error?.message ?? result.job.error?.message ?? "Nothing was changed.",
        refused?.error?.details,
      );
    }
    return result;
  },
  updateObject: (
    objectTypeKey: string,
    objectId: string,
    payload: ChangeSetWriteContext & {
      expectedVersion: number;
      name?: string;
      parentObjectId?: string | null;
      attributes?: ObjectAttributeInput[];
    },
  ) =>
    request<ObjectItem>(`/api/v1/objects/${encodeURIComponent(objectTypeKey)}/${encodeURIComponent(objectId)}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  deleteObject: (
    objectTypeKey: string,
    objectId: string,
    expectedVersion: number,
    options: ObjectDeleteOptions = {},
  ) => {
    const params = new URLSearchParams({ expectedVersion: String(expectedVersion) });
    if (options.cascade) params.set("cascade", "true");
    if (options.deletionPreviewToken) params.set("deletionPreviewToken", options.deletionPreviewToken);
    if (options.changeSetId) params.set("changeSetId", options.changeSetId);
    if (options.expectedChangeSetVersion !== undefined) {
      params.set("expectedChangeSetVersion", String(options.expectedChangeSetVersion));
    }
    return request<void>(
      `/api/v1/objects/${encodeURIComponent(objectTypeKey)}/${encodeURIComponent(objectId)}?${params}`,
      { method: "DELETE" },
    );
  },
  /** What deleting the record would take with it, live or in a change set; deletes nothing. */
  objectDeletionImpact: (objectTypeKey: string, objectId: string, changeSetId?: string) =>
    request<ObjectDeletionImpact>(
      `/api/v1/objects/${encodeURIComponent(objectTypeKey)}/${encodeURIComponent(objectId)}/deletion-impact${
        changeSetId ? `?${new URLSearchParams({ changeSetId })}` : ""
      }`,
    ),
  attribute: (
    objectTypeKey: string,
    objectId: string,
    attributeTypeKey: string,
    changeSetId?: string,
    publicationId?: string,
  ) =>
    request<AttributeValueResponse>(
      withWorkspace(attributePath(objectTypeKey, objectId, attributeTypeKey), undefined, changeSetId, publicationId),
    ),
  createAttribute: (
    objectTypeKey: string,
    objectId: string,
    attributeTypeKey: string,
    value: unknown,
    expectedVersion: number,
    context: ChangeSetWriteContext = {},
  ) =>
    request<ObjectItem>(attributePath(objectTypeKey, objectId, attributeTypeKey), {
      method: "POST",
      body: JSON.stringify({ value, expectedVersion, ...context }),
    }),
  updateAttribute: (
    objectTypeKey: string,
    objectId: string,
    attributeTypeKey: string,
    value: unknown,
    expectedVersion: number,
    context: ChangeSetWriteContext = {},
  ) =>
    request<ObjectItem>(attributePath(objectTypeKey, objectId, attributeTypeKey), {
      method: "PATCH",
      body: JSON.stringify({ value, expectedVersion, ...context }),
    }),
  deleteAttribute: (
    objectTypeKey: string,
    objectId: string,
    attributeTypeKey: string,
    expectedVersion: number,
    context: ChangeSetWriteContext = {},
  ) =>
    request<void>(
      `${attributePath(objectTypeKey, objectId, attributeTypeKey)}?${writeQuery(expectedVersion, context)}`,
      {
        method: "DELETE",
      },
    ),
  /** What a set of records holds through one relationship, with counts (0.9 K6a, D165). */
  heldRecords: (query: {
    objectTypeKey: string;
    relationTypeKey: string;
    direction: "outgoing" | "incoming";
    objectIds: readonly string[];
    workspaceKey?: string;
    changeSetId?: string;
    publicationId?: string;
    cursor?: string;
    pageSize?: number;
  }) => {
    const params = new URLSearchParams({
      objectTypeKey: query.objectTypeKey,
      relationTypeKey: query.relationTypeKey,
      direction: query.direction,
      pageSize: String(query.pageSize ?? 500),
    });
    query.objectIds.forEach((id) => params.append("objectId", id));
    if (query.workspaceKey) params.set("workspaceKey", query.workspaceKey);
    if (query.changeSetId) params.set("changeSetId", query.changeSetId);
    if (query.publicationId) params.set("publicationId", query.publicationId);
    if (query.cursor) params.set("cursor", query.cursor);
    return request<{
      items: { object: { id: string; name: string; objectTypeKey: string }; count: number }[];
      nextCursor: string | null;
    }>(`/api/v1/relations/held?${params}`);
  },
  relations: (
    objectId: string,
    options: PageSelector & {
      workspaceKey?: string;
      changeSetId?: string;
      publicationId?: string;
      direction?: "incoming" | "outgoing" | "both";
      relationTypeKey?: string;
      search?: string;
      /** `name` or, live only, `createdAt`; prefix `-` for descending. */
      sort?: string;
      pageSize?: number;
    } = {},
  ) => {
    const params = new URLSearchParams({ objectId });
    if (options.changeSetId) params.set("changeSetId", options.changeSetId);
    if (options.publicationId) params.set("publicationId", options.publicationId);
    if (options.workspaceKey) params.set("workspaceKey", options.workspaceKey);
    if (options.direction) params.set("direction", options.direction);
    if (options.relationTypeKey) params.set("relationTypeKey", options.relationTypeKey);
    if (options.search) params.set("search", options.search);
    if (options.sort) params.set("sort", options.sort);
    setPaging(params, options);
    params.set("pageSize", String(options.pageSize ?? 100));
    return request<RelationPage>(`/api/v1/relations?${params}`);
  },
  createRelation: (payload: RelationCreateInput & ChangeSetWriteContext) =>
    request<RelationRecord>("/api/v1/relations", { method: "POST", body: JSON.stringify(payload) }),
  relation: (relationId: string, workspaceKey?: string, changeSetId?: string, publicationId?: string) =>
    request<RelationRecord>(
      withWorkspace(`/api/v1/relations/${encodeURIComponent(relationId)}`, workspaceKey, changeSetId, publicationId),
    ),
  updateRelation: (relationId: string, payload: RelationUpdateInput & ChangeSetWriteContext) =>
    request<RelationRecord>(`/api/v1/relations/${encodeURIComponent(relationId)}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  deleteRelation: (
    relationId: string,
    expectedVersion: number,
    context: ChangeSetWriteContext = {},
    claim?: RelationSetClaim,
  ) => {
    const params = writeQuery(expectedVersion, context);
    if (claim) {
      params.set("expectedRelationSetVersion", String(claim.expectedRelationSetVersion));
      params.set("relationSetDirection", claim.relationSetDirection);
    }
    return request<void>(`/api/v1/relations/${encodeURIComponent(relationId)}?${params}`, { method: "DELETE" });
  },
  objectHistory: (
    objectTypeKey: string,
    objectId: string,
    options: { cursor?: string; pageSize?: number; kind?: HistoryKind; actorId?: string; live?: boolean } = {},
  ) => {
    const params = new URLSearchParams({ pageSize: String(options.pageSize ?? 20) });
    if (options.cursor) params.set("cursor", options.cursor);
    if (options.kind) params.set("kind", options.kind);
    if (options.actorId) params.set("actorId", options.actorId);
    if (options.live) params.set("live", "true");
    return request<AuditEventPage>(
      `/api/v1/objects/${encodeURIComponent(objectTypeKey)}/${encodeURIComponent(objectId)}/history?${params}`,
    );
  },
  mappingCoverage: (query: MappingCoverageQuery) => {
    const params = new URLSearchParams({
      applicationKey: query.applicationKey,
      viewKey: query.viewKey,
      relationTypeKey: query.relationTypeKey,
      fromObjectTypeKey: query.fromObjectTypeKey,
      toObjectTypeKey: query.toObjectTypeKey,
      direction: query.direction,
    });
    if (query.changeSetId) params.set("changeSetId", query.changeSetId);
    if (query.publicationId) params.set("publicationId", query.publicationId);
    if (query.search) params.set("search", query.search);
    if (query.parentObjectId) params.set("parentObjectId", query.parentObjectId);
    if (query.state) params.set("state", query.state);
    if (query.proposed) params.set("proposed", "true");
    setPaging(params, query);
    if (query.pageSize != null) params.set("pageSize", String(query.pageSize));
    return request<MappingCoveragePage>(
      `/api/v1/workspaces/${encodeURIComponent(query.workspaceKey)}/mapping-coverage?${params}`,
    );
  },
  relationTable: (query: RelationTableQuery) => {
    const params = new URLSearchParams({ applicationKey: query.applicationKey, viewKey: query.viewKey });
    if (query.changeSetId) params.set("changeSetId", query.changeSetId);
    if (query.publicationId) params.set("publicationId", query.publicationId);
    if (query.search) params.set("search", query.search);
    if (query.fromObjectId) params.set("fromObjectId", query.fromObjectId);
    if (query.toObjectId) params.set("toObjectId", query.toObjectId);
    if (query.sort) params.set("sort", query.sort);
    for (const filter of query.filters ?? []) params.append(`filter.${filter.field}.eq`, filter.value);
    setPaging(params, query);
    if (query.pageSize != null) params.set("pageSize", String(query.pageSize));
    return request<RelationTablePage>(
      `/api/v1/workspaces/${encodeURIComponent(query.workspaceKey)}/relations?${params}`,
    );
  },
  relationGrid: (query: RelationGridQuery) => {
    const params = new URLSearchParams({ applicationKey: query.applicationKey, viewKey: query.viewKey });
    if (query.changeSetId) params.set("changeSetId", query.changeSetId);
    if (query.publicationId) params.set("publicationId", query.publicationId);
    if (query.search) params.set("search", query.search);
    if (query.sort) params.set("sort", query.sort);
    if (query.toSearch) params.set("toSearch", query.toSearch);
    for (const id of query.toObjectIds ?? []) params.append("toObjectId", id);
    for (const key of query.attributes ?? []) params.append("attribute", key);
    for (const filter of query.filters ?? [])
      params.append(`filter.${filter.field}.${filter.operator ?? "eq"}`, filter.value);
    setPaging(params, query);
    if (query.pageSize != null) params.set("pageSize", String(query.pageSize));
    return request<RelationGridPage>(
      `/api/v1/workspaces/${encodeURIComponent(query.workspaceKey)}/relation-grid?${params}`,
    );
  },
  /** One value set on the relationships a grid shows, or on a dry run only counted (0.13 RG). */
  relationGridChange: (payload: RelationGridChangeInput & ChangeSetWriteContext) =>
    request<RelationGridChangeResult>("/api/v1/relations/grid-change", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  /** Values set on many relationships as one write; any stale or invalid item refuses all (0.13 RV). */
  updateRelationBatch: (payload: RelationBatchInput & ChangeSetWriteContext) =>
    request<RelationBatchResult>("/api/v1/relations/batch", { method: "POST", body: JSON.stringify(payload) }),
  /** Asks the AI provider for targets for a view's unmapped sources: `202` with the queued `aiProposal` job (0.16 AP2). */
  proposeMappingTargets: (workspaceKey: string, body: MappingProposalRequest) =>
    request<Job>(`/api/v1/workspaces/${encodeURIComponent(workspaceKey)}/mapping-proposals`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  mappingCandidates: (query: MappingCandidateQuery) => {
    const params = new URLSearchParams({
      applicationKey: query.applicationKey,
      viewKey: query.viewKey,
      objectTypeKey: query.objectTypeKey,
    });
    if (query.changeSetId) params.set("changeSetId", query.changeSetId);
    if (query.publicationId) params.set("publicationId", query.publicationId);
    if (query.search) params.set("search", query.search);
    setPaging(params, query);
    if (query.pageSize != null) params.set("pageSize", String(query.pageSize));
    return request<MappingCandidatePage>(
      `/api/v1/workspaces/${encodeURIComponent(query.workspaceKey)}/mapping-candidates?${params}`,
    );
  },
  replaceMapping: (workspaceKey: string, body: MappingReplacementRequest) =>
    request<MappingReplacementResponse>(`/api/v1/workspaces/${encodeURIComponent(workspaceKey)}/mappings`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),
  relationMatrix: (query: RelationMatrixQuery) => {
    const params = new URLSearchParams();
    if (query.parentObjectId) params.set("parentObjectId", query.parentObjectId);
    if (query.search) params.set("search", query.search);
    if (query.sort) params.set("sort", query.sort);
    query.columnIds?.forEach((id) => params.append("columnIds", id));
    if (query.columnCursor) params.set("columnCursor", query.columnCursor);
    if (query.state) params.set("state", query.state);
    if (query.hideEmptyColumns && !query.columnIds?.length) params.set("hideEmptyColumns", "true");
    setPaging(params, query);
    if (query.pageSize != null) params.set("pageSize", String(query.pageSize));
    return request<RelationMatrixPage>(relationMatrixPath("", query, params));
  },
  relationMatrixContainers: (query: RelationMatrixCellQuery) =>
    request<RelationMatrixContainerPage>(relationMatrixPath("/containers", query, relationMatrixCellParams(query))),
  relationMatrixLinkCandidates: (query: RelationMatrixCellQuery & { rowId: string }) => {
    const params = relationMatrixCellParams(query);
    params.set("rowId", query.rowId);
    return request<RelationMatrixLinkCandidatePage>(relationMatrixPath("/link-candidates", query, params));
  },
  mappingTargets: (query: MappingTargetQuery) => {
    const params = new URLSearchParams({
      relationTypeKey: query.relationTypeKey,
      fromObjectTypeKey: query.fromObjectTypeKey,
      toObjectTypeKey: query.toObjectTypeKey,
      direction: query.direction,
      sourceObjectId: query.sourceObjectId,
      mappingVersion: String(query.mappingVersion),
    });
    if (query.applicationKey) params.set("applicationKey", query.applicationKey);
    if (query.viewKey) params.set("viewKey", query.viewKey);
    if (query.changeSetId) params.set("changeSetId", query.changeSetId);
    if (query.publicationId) params.set("publicationId", query.publicationId);
    if (query.cursor) params.set("cursor", query.cursor);
    if (query.pageSize != null) params.set("pageSize", String(query.pageSize));
    return request<MappingTargetPage>(
      `/api/v1/workspaces/${encodeURIComponent(query.workspaceKey)}/mapping-targets?${params}`,
    );
  },
};

function attributePath(objectTypeKey: string, objectId: string, attributeTypeKey: string) {
  return `/api/v1/objects/${encodeURIComponent(objectTypeKey)}/${encodeURIComponent(objectId)}/attributes/${encodeURIComponent(attributeTypeKey)}`;
}

function withWorkspace(path: string, workspaceKey?: string, changeSetId?: string, publicationId?: string) {
  const params = new URLSearchParams();
  if (workspaceKey) params.set("workspaceKey", workspaceKey);
  if (changeSetId) params.set("changeSetId", changeSetId);
  if (publicationId) params.set("publicationId", publicationId);
  return params.size ? `${path}?${params}` : path;
}

function writeQuery(expectedVersion: number, context: ChangeSetWriteContext) {
  const params = new URLSearchParams({ expectedVersion: String(expectedVersion) });
  if (context.changeSetId) params.set("changeSetId", context.changeSetId);
  if (context.expectedChangeSetVersion !== undefined)
    params.set("expectedChangeSetVersion", String(context.expectedChangeSetVersion));
  return params;
}

/** Where a draft's consumer API document is served, for a request or a download link (0.10 A4c). */
export function consumerApiDocumentPath(
  draftId: string,
  consumerApi: string,
  document: ConsumerApiDocumentKind,
): string {
  return `/api/v1/model-drafts/${encodeURIComponent(draftId)}/consumer-apis/${encodeURIComponent(consumerApi)}/${document}.json`;
}
