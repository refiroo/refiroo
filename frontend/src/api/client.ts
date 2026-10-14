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
  ConsumerApiDefinition,
  ConsumerApiDocument,
  ConsumerApiIndexPage,
  BatchRequest,
  BatchResult,
  Job,
  JobItemOutcome,
  JobItemPage,
  JobPage,
  JobRow,
  JobRowPage,
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
  DraftProfile,
  DryRun,
  Inference,
  InferenceRequest,
  Proposal,
  SourceColumn,
  SourceFile,
  SourceFileUpload,
  SourcePage,
  SourceSheet,
} from "@/types";

import { ApiError } from "@/api/errors";

// `ApiError` is re-exported because it is what `request` throws; `errorMessage` and
// `isApiError` live in ./errors so that a test mocking this module does not shadow them.
export { ApiError } from "@/api/errors";

/** The engine this browser application calls (`VITE_API_URL`, set when the frontend is built). */
export const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

/** A completed export's file, as a link the browser downloads (0.9 J1). */
export const jobOutputUrl = (jobId: string) => `${API_URL}/api/v1/jobs/${encodeURIComponent(jobId)}/output`;

/** A job's server-sent event stream (0.9 J1u): the job now and after each change, until it ends. */
export const jobEventsUrl = (jobId: string) => `${API_URL}/api/v1/jobs/${encodeURIComponent(jobId)}/events`;

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  return requestUrl<T>(`${API_URL}${path}`, path, init);
}

/** A request to an address the API gave whole, such as a document the consumer API index names. */
async function requestUrl<T>(url: string, path: string, init?: RequestInit): Promise<T> {
  // A form body (a file upload) sets its own multipart content type with its boundary.
  const json = !(init?.body instanceof FormData);
  const response = await fetch(url, {
    ...init,
    headers: { ...(json ? { "Content-Type": "application/json" } : {}), ...init?.headers },
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
  query.expand?.forEach((key) => params.append("expand", key));
  if (query.expandLimit != null) params.set("expandLimit", String(query.expandLimit));
  if (query.candidateFor) params.set("candidateFor", query.candidateFor);
  if (query.anchorTypeKey) params.set("anchorTypeKey", query.anchorTypeKey);
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
  /** A consumer API definition of the active model, expanded with every default (C18). */
  consumerApiDefinition: (consumerApi: string) =>
    request<ConsumerApiDefinition>(`/api/v1/model/consumer-apis/${encodeURIComponent(consumerApi)}`),
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
  /** An import's rows with their outcomes, in sheet and row order (0.9 J3, D84). */
  jobRows: (jobId: string, query: PageSelector & { status?: JobRow["status"]; pageSize?: number } = {}) => {
    const params = new URLSearchParams({ pageSize: String(query.pageSize ?? 50) });
    if (query.status) params.set("status", query.status);
    setPaging(params, query);
    return request<JobRowPage>(`/api/v1/jobs/${encodeURIComponent(jobId)}/rows?${params}`);
  },
  /** Stored import profiles in key order, one page (0.9 J2). */
  importProfiles: (cursor?: string) => {
    const params = new URLSearchParams({ pageSize: "100" });
    if (cursor) params.set("cursor", cursor);
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
  importProfile: (key: string) => request<ImportProfile>(`/api/v1/import-profiles/${encodeURIComponent(key)}`),
  /** Replace a stored profile at its version (0.9 J2): every member but the key. */
  updateImportProfile: (profile: ImportProfile, sources: ImportProfileSource[]) =>
    request<ImportProfile>(`/api/v1/import-profiles/${encodeURIComponent(profile.key)}`, {
      method: "PUT",
      body: JSON.stringify({
        name: profile.name,
        ...(profile.csv ? { csv: profile.csv } : {}),
        sources,
        valueMaps: profile.valueMaps,
        expectedVersion: profile.version,
      }),
    }),
  /** The check of a profile's latest file (0.10 A5c, D83). */
  profileCheck: (key: string) => request<ProfileCheck>(`/api/v1/import-profiles/${encodeURIComponent(key)}/check`),
  /** Check the profile's current file again, after the profile changed. */
  runProfileCheck: (key: string) =>
    request<ProfileCheck>(`/api/v1/import-profiles/${encodeURIComponent(key)}/check`, { method: "POST" }),
  /** One of the check's lists, a page: new values, drifting names, records missing from the file. */
  profileCheckList: <Item extends CheckNewValue | CheckDrift | CheckMissingRecord>(
    key: string,
    list: "new-values" | "drift" | "missing-records",
    query: PageSelector & { source?: number; pageSize?: number },
  ) => {
    const params = new URLSearchParams({ pageSize: String(query.pageSize ?? 50) });
    if (query.source !== undefined) params.set("source", String(query.source));
    setPaging(params, query);
    return request<SourcePage<Item>>(`/api/v1/import-profiles/${encodeURIComponent(key)}/check/${list}?${params}`);
  },
  /** The rows behind the check's figures, as a dry run's. */
  profileCheckRows: (
    key: string,
    query: PageSelector & { source?: number; status?: JobRow["status"]; code?: string; pageSize?: number },
  ) => {
    const params = new URLSearchParams({ pageSize: String(query.pageSize ?? 50) });
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
  modelDraftInference: (draftId: string) =>
    request<Inference>(`/api/v1/model-drafts/${encodeURIComponent(draftId)}/inference`),
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
  /** Queue an export (0.9 J1); the answer is the queued job. */
  createExport: (body: ExportRequest) =>
    request<Job>("/api/v1/exports", { method: "POST", body: JSON.stringify(body) }),
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
    request<ModelInstallation>(`/api/v1/model-drafts/${encodeURIComponent(draftId)}/installation`, {
      method: "POST",
      body: JSON.stringify({ expectedVersion }),
    }),
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

/** Where a draft's consumer API document is served, for a request or a download link (0.10 A4c). */
export function consumerApiDocumentPath(
  draftId: string,
  consumerApi: string,
  document: ConsumerApiDocumentKind,
): string {
  return `/api/v1/model-drafts/${encodeURIComponent(draftId)}/consumer-apis/${encodeURIComponent(consumerApi)}/${document}.json`;
}
