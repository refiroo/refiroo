import type {
  EngineModel,
  ChangeSet,
  ChangeSetPage,
  Publication,
  PublicationPage,
  ChangeSetValidation,
  ChangeKind,
  ObjectChangePage,
  RelationChangePage,
  InitialRelationInput,
  ObjectAttributeInput,
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
  ObjectSort,
  CollectionFilter,
  CapabilitiesResponse,
  SystemResponse,
  ConsumerApiDocument,
  ConsumerApiIndexPage,
  Job,
  JobPage,
  DeliveryDetail,
  DeliveryRowPage,
  DeliveryStatus,
  Subscription,
  SubscriptionCreate,
  SubscriptionPage,
  SubscriptionUpdate,
  ModelCompilation,
  ModelDraft,
  ModelDraftPage,
  ModelRelease,
  ModelReleaseActivationPage,
  ModelReleaseDiff,
  ModelReleasePage,
  ModelRuntimeState,
  ModelValidation,
  Workspace,
  WorkspaceDetail,
  WorkspacePage,
  WorkspaceRuntimeState,
  MappingCoveragePage,
  MappingTargetPage,
  MappingCandidatePage,
  MappingReplacementRequest,
  MappingReplacementResponse,
  RelationMatrixPage,
  RelationMatrixContainerPage,
  RelationMatrixLinkCandidatePage,
  RelationSetClaim,
  RestructuringOutcomeFilter,
  RestructuringPreview,
  RestructuringRequest,
  RestructuringResult,
} from "@/types";

import { ApiError } from "@/api/errors";

// `ApiError` is re-exported because it is what `request` throws; `errorMessage` and
// `isApiError` live in ./errors so that a test mocking this module does not shadow them.
export { ApiError } from "@/api/errors";

/** The engine this browser application calls (`VITE_API_URL`, set when the frontend is built). */
export const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  return requestUrl<T>(`${API_URL}${path}`, path, init);
}

/** A request to an address the API gave whole, such as a document the consumer API index names. */
async function requestUrl<T>(url: string, path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
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
    throw new ApiError(response.status, code, message, details);
  }
  if (response.status === 204) return undefined as T;
  const contentType = response.headers.get("content-type") ?? "";
  if (!contentType.includes("application/json")) {
    throw new ApiError(
      response.status,
      "UNEXPECTED_RESPONSE",
      `The request to ${path} returned ${contentType || "an unknown content type"} instead of JSON. Retry or contact support if the problem continues.`,
    );
  }
  return response.json() as Promise<T>;
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
  return `/api/v1/objects/${encodeURIComponent(objectTypeKey)}?${params}`;
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
    const [model, placements] = await Promise.all([
      request<EngineModel>(`/api/v1/model${query}`),
      request<ModelPlacements>(`/api/v1/model/placements${query}`),
    ]);
    return { ...model, placements };
  },
  capabilities: () => request<CapabilitiesResponse>("/api/v1/capabilities"),
  system: () => request<SystemResponse>("/api/v1/system"),
  /** The consumer API index (`GET /api/consumer`), one page. */
  consumerApis: (cursor?: string) => {
    const params = new URLSearchParams({ pageSize: "100" });
    if (cursor) params.set("cursor", cursor);
    return request<ConsumerApiIndexPage>(`/api/consumer?${params}`);
  },
  /** A consumer API's OpenAPI document, at the address its index entry names (resolved whole). */
  consumerApiDocument: (url: string) => requestUrl<ConsumerApiDocument>(url, new URL(url).pathname),
  /** Jobs in every workspace, newest first. */
  jobs: (cursor?: string) => {
    const params = new URLSearchParams({ pageSize: "50" });
    if (cursor) params.set("cursor", cursor);
    return request<JobPage>(`/api/v1/jobs?${params}`);
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
  /** Send an event (or a notice) of a delivered request again, by hand; the new request. */
  resendDelivery: (id: string, deliveryId: string, eventId?: string) =>
    request<DeliveryDetail>(
      `/api/v1/consumer-subscriptions/${encodeURIComponent(id)}/deliveries/${encodeURIComponent(deliveryId)}/resend`,
      { method: "POST", body: JSON.stringify(eventId ? { eventId } : {}) },
    ),
  deleteSubscription: (id: string, expectedVersion: number) =>
    request<void>(`/api/v1/consumer-subscriptions/${encodeURIComponent(id)}?expectedVersion=${expectedVersion}`, {
      method: "DELETE",
    }),
  cancelJob: (jobId: string) => request<Job>(`/api/v1/jobs/${encodeURIComponent(jobId)}/cancel`, { method: "POST" }),
  workspaces: (
    options: {
      search?: string;
      status?: "active" | "retired" | "all";
      cursor?: string;
      pageSize?: number;
    } = {},
  ) => {
    const params = new URLSearchParams({
      status: options.status ?? "active",
      pageSize: String(options.pageSize ?? 100),
    });
    if (options.search) params.set("search", options.search);
    if (options.cursor) params.set("cursor", options.cursor);
    return request<WorkspacePage>(`/api/v1/workspaces?${params}`);
  },
  workspace: (workspaceKey: string) =>
    request<WorkspaceDetail>(`/api/v1/workspaces/${encodeURIComponent(workspaceKey)}`),
  createWorkspace: (body: { key: string; label: string }) =>
    request<WorkspaceDetail>("/api/v1/workspaces", { method: "POST", body: JSON.stringify(body) }),
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
  changeSets: (workspaceKey: string, cursor?: string) => {
    const query = new URLSearchParams({ pageSize: "50" });
    if (cursor) query.set("cursor", cursor);
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
  modelReleases: (options: { cursor?: string; pageSize?: number } = {}) => {
    const params = new URLSearchParams({ pageSize: String(options.pageSize ?? 100) });
    if (options.cursor) params.set("cursor", options.cursor);
    return request<ModelReleasePage>(`/api/v1/model-releases?${params}`);
  },
  modelRelease: (releaseId: string, includeModel = false) =>
    request<ModelRelease>(`/api/v1/model-releases/${encodeURIComponent(releaseId)}?includeModel=${includeModel}`),
  modelReleaseActivations: (releaseId: string, options: { cursor?: string; pageSize?: number } = {}) => {
    const params = new URLSearchParams({ pageSize: String(options.pageSize ?? 100) });
    if (options.cursor) params.set("cursor", options.cursor);
    return request<ModelReleaseActivationPage>(
      `/api/v1/model-releases/${encodeURIComponent(releaseId)}/activations?${params}`,
    );
  },
  modelReleaseDiff: (releaseId: string, againstReleaseId: string) =>
    request<ModelReleaseDiff>(
      `/api/v1/model-releases/${encodeURIComponent(releaseId)}/diff?againstReleaseId=${encodeURIComponent(againstReleaseId)}`,
    ),
  modelRuntimeState: () => request<ModelRuntimeState>("/api/v1/model-runtime-state"),
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
  installModelDraft: (draftId: string, expectedVersion: number) =>
    request<ModelRelease>(`/api/v1/model-drafts/${encodeURIComponent(draftId)}/installation`, {
      method: "POST",
      body: JSON.stringify({ expectedVersion }),
    }),
  activateModelRelease: (releaseId: string, state: ModelRuntimeState) =>
    request<ModelRuntimeState>(`/api/v1/model-releases/${encodeURIComponent(releaseId)}/activation`, {
      method: "POST",
      body: JSON.stringify({ expectedRuntimeVersion: state.version, expectedActiveReleaseId: state.activeReleaseId }),
    }),
  objects: (objectTypeKey: string, query: ObjectQuery) => request<ObjectPage>(objectQueryPath(objectTypeKey, query)),
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
  objectHistory: (objectTypeKey: string, objectId: string, options: { cursor?: string; pageSize?: number } = {}) => {
    const params = new URLSearchParams({ pageSize: String(options.pageSize ?? 20) });
    if (options.cursor) params.set("cursor", options.cursor);
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
    setPaging(params, query);
    if (query.pageSize != null) params.set("pageSize", String(query.pageSize));
    return request<MappingCoveragePage>(
      `/api/v1/workspaces/${encodeURIComponent(query.workspaceKey)}/mapping-coverage?${params}`,
    );
  },
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
