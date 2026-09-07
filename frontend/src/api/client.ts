import type {
  EngineModel,
  InitialRelationInput,
  ObjectAttributeInput,
  ObjectItem,
  ObjectPage,
  AttributeValueResponse,
  RelationCreateInput,
  RelationPage,
  RelationRecord,
  RelationUpdateInput,
  AuditEventPage,
  ObjectSort,
  CollectionFilter,
  CapabilitiesResponse,
  ModelCompilation,
  ModelDraft,
  ModelDraftPage,
  ModelRelease,
  ModelReleaseDiff,
  ModelReleasePage,
  ModelRuntimeState,
  ModelValidation,
  Workspace,
  WorkspacePage,
  WorkspaceRuntimeState,
} from "@/types";

import { ApiError } from "@/api/errors";

// `ApiError` is re-exported because it is what `request` throws; `errorMessage` and
// `isApiError` live in ./errors so that a test mocking this module does not shadow them.
export { ApiError } from "@/api/errors";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const body = await response.text();
    let message = body || `Request failed with ${response.status}`;
    let code = "http_error";
    let details: unknown;
    try {
      const parsed = JSON.parse(body);
      message = parsed.error?.message ?? parsed.detail ?? body;
      code = parsed.error?.code ?? code;
      details = parsed.error?.details;
    } catch {
      // Keep a non-JSON error body intact.
    }
    throw new ApiError(response.status, code, message, details);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export interface ObjectQuery {
  applicationKey?: string;
  workspaceKey?: string;
  search?: string;
  cursor?: string;
  pageSize?: number;
  parentObjectId?: string;
  sort?: ObjectSort;
  filters?: CollectionFilter[];
}

function objectQueryPath(objectTypeKey: string, query: ObjectQuery) {
  const params = new URLSearchParams({ pageSize: String(query.pageSize ?? 20) });
  if (query.applicationKey) params.set("applicationKey", query.applicationKey);
  if (query.workspaceKey) params.set("workspaceKey", query.workspaceKey);
  if (query.search) params.set("search", query.search);
  if (query.cursor) params.set("cursor", query.cursor);
  if (query.parentObjectId) params.set("parentObjectId", query.parentObjectId);
  if (query.sort) params.set("sort", query.sort);
  query.filters?.forEach(({ field, operator, value }) => params.append(`filter.${field}.${operator}`, value));
  return `/api/v1/objects/${encodeURIComponent(objectTypeKey)}?${params}`;
}

export const api = {
  model: () => request<EngineModel>("/api/v1/model"),
  capabilities: () => request<CapabilitiesResponse>("/api/v1/capabilities"),
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
  workspace: (workspaceKey: string) => request<Workspace>(`/api/v1/workspaces/${encodeURIComponent(workspaceKey)}`),
  workspaceRuntimeState: () => request<WorkspaceRuntimeState>("/api/v1/workspace-runtime-state"),
  modelReleases: (options: { cursor?: string; pageSize?: number } = {}) => {
    const params = new URLSearchParams({ pageSize: String(options.pageSize ?? 100) });
    if (options.cursor) params.set("cursor", options.cursor);
    return request<ModelReleasePage>(`/api/v1/model-releases?${params}`);
  },
  modelRelease: (releaseId: string, includeModel = false) =>
    request<ModelRelease>(`/api/v1/model-releases/${encodeURIComponent(releaseId)}?includeModel=${includeModel}`),
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
  object: (objectTypeKey: string, objectId: string) =>
    request<ObjectItem>(`/api/v1/objects/${encodeURIComponent(objectTypeKey)}/${encodeURIComponent(objectId)}`),
  createObject: (
    objectTypeKey: string,
    payload: {
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
    payload: {
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
  deleteObject: (objectTypeKey: string, objectId: string, expectedVersion: number, cascade = false) => {
    const params = new URLSearchParams({ expectedVersion: String(expectedVersion) });
    if (cascade) params.set("cascade", "true");
    return request<void>(
      `/api/v1/objects/${encodeURIComponent(objectTypeKey)}/${encodeURIComponent(objectId)}?${params}`,
      { method: "DELETE" },
    );
  },
  attribute: (objectTypeKey: string, objectId: string, attributeTypeKey: string) =>
    request<AttributeValueResponse>(attributePath(objectTypeKey, objectId, attributeTypeKey)),
  createAttribute: (
    objectTypeKey: string,
    objectId: string,
    attributeTypeKey: string,
    value: unknown,
    expectedVersion: number,
  ) =>
    request<ObjectItem>(attributePath(objectTypeKey, objectId, attributeTypeKey), {
      method: "POST",
      body: JSON.stringify({ value, expectedVersion }),
    }),
  updateAttribute: (
    objectTypeKey: string,
    objectId: string,
    attributeTypeKey: string,
    value: unknown,
    expectedVersion: number,
  ) =>
    request<ObjectItem>(attributePath(objectTypeKey, objectId, attributeTypeKey), {
      method: "PATCH",
      body: JSON.stringify({ value, expectedVersion }),
    }),
  deleteAttribute: (objectTypeKey: string, objectId: string, attributeTypeKey: string, expectedVersion: number) =>
    request<void>(`${attributePath(objectTypeKey, objectId, attributeTypeKey)}?expectedVersion=${expectedVersion}`, {
      method: "DELETE",
    }),
  relations: (
    objectId: string,
    options: {
      direction?: "incoming" | "outgoing" | "both";
      relationTypeKey?: string;
      cursor?: string;
      pageSize?: number;
    } = {},
  ) => {
    const params = new URLSearchParams({ objectId });
    if (options.direction) params.set("direction", options.direction);
    if (options.relationTypeKey) params.set("relationTypeKey", options.relationTypeKey);
    if (options.cursor) params.set("cursor", options.cursor);
    params.set("pageSize", String(options.pageSize ?? 100));
    return request<RelationPage>(`/api/v1/relations?${params}`);
  },
  createRelation: (payload: RelationCreateInput) =>
    request<RelationRecord>("/api/v1/relations", { method: "POST", body: JSON.stringify(payload) }),
  relation: (relationId: string) => request<RelationRecord>(`/api/v1/relations/${encodeURIComponent(relationId)}`),
  updateRelation: (relationId: string, payload: RelationUpdateInput) =>
    request<RelationRecord>(`/api/v1/relations/${encodeURIComponent(relationId)}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  deleteRelation: (relationId: string, expectedVersion: number) =>
    request<void>(`/api/v1/relations/${encodeURIComponent(relationId)}?expectedVersion=${expectedVersion}`, {
      method: "DELETE",
    }),
  objectHistory: (objectTypeKey: string, objectId: string, options: { cursor?: string; pageSize?: number } = {}) => {
    const params = new URLSearchParams({ pageSize: String(options.pageSize ?? 20) });
    if (options.cursor) params.set("cursor", options.cursor);
    return request<AuditEventPage>(
      `/api/v1/objects/${encodeURIComponent(objectTypeKey)}/${encodeURIComponent(objectId)}/history?${params}`,
    );
  },
};

function attributePath(objectTypeKey: string, objectId: string, attributeTypeKey: string) {
  return `/api/v1/objects/${encodeURIComponent(objectTypeKey)}/${encodeURIComponent(objectId)}/attributes/${encodeURIComponent(attributeTypeKey)}`;
}
