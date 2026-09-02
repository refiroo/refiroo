import type { EngineModel, ObjectItem, ObjectPage, RelationItem } from "./types";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const body = await response.text();
    let message = body;
    try {
      message = JSON.parse(body).detail ?? body;
    } catch {
      // Keep a non-JSON error body intact.
    }
    throw new Error(message || `Request failed with ${response.status}`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export interface ObjectQuery {
  applicationKey: string;
  search?: string;
  cursor?: string;
  pageSize?: number;
  parentObjectId?: string;
}

function objectQueryPath(objectTypeKey: string, query: ObjectQuery) {
  const params = new URLSearchParams({
    applicationKey: query.applicationKey,
    pageSize: String(query.pageSize ?? 20),
  });
  if (query.search) params.set("search", query.search);
  if (query.cursor) params.set("cursor", query.cursor);
  if (query.parentObjectId) params.set("parentObjectId", query.parentObjectId);
  return `/api/v1/objects/${encodeURIComponent(objectTypeKey)}?${params}`;
}

export const api = {
  model: () => request<EngineModel>("/api/v1/model"),
  objects: (objectTypeKey: string, query: ObjectQuery) =>
    request<ObjectPage>(objectQueryPath(objectTypeKey, query)),
  object: (objectTypeKey: string, objectId: string) =>
    request<ObjectItem>(
      `/api/v1/objects/${encodeURIComponent(objectTypeKey)}/${encodeURIComponent(objectId)}`,
    ),
  createObject: (
    objectTypeKey: string,
    payload: {
      applicationKey: string;
      name: string;
      parentObjectId?: string;
      attributes: Record<string, unknown>;
    },
  ) =>
    request<ObjectItem>(`/api/v1/objects/${encodeURIComponent(objectTypeKey)}`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateObject: (
    objectTypeKey: string,
    objectId: string,
    payload: {
      name: string;
      parentObjectId: string | null;
      attributes: Record<string, unknown>;
      expectedVersion: number;
    },
  ) =>
    request<ObjectItem>(
      `/api/v1/objects/${encodeURIComponent(objectTypeKey)}/${encodeURIComponent(objectId)}`,
      { method: "PATCH", body: JSON.stringify(payload) },
    ),
  relations: (objectId: string) =>
    request<RelationItem[]>(`/api/v1/relations?objectId=${encodeURIComponent(objectId)}`),
};
