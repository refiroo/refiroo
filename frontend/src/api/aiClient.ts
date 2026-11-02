/** The AI routes Settings › AI reads and the test request it makes (0.16 AP1). */

import { request } from "@/api/client";
import type {
  AiCall,
  AiCallPage,
  AiTaskAnswerRequest,
  AiStatus,
  AiTask,
  AiTaskChangePage,
  AiTaskRequest,
  AiTaskRunRequest,
  HistoryAccount,
  HistoryAccountRequest,
  ImpactSummary,
  ImpactSummaryRequest,
  QueryTranslation,
  QueryTranslationRequest,
} from "@/types";

const taskPath = (id: string) => `/api/v1/ai/tasks/${encodeURIComponent(id)}`;
const post = (body: unknown) => ({ method: "POST", body: JSON.stringify(body) });

export const ai = {
  status: () => request<AiStatus>("/api/v1/ai/status"),
  /** The calls made, newest first. */
  calls: (options: { cursor?: string } = {}) => {
    const search = new URLSearchParams({ pageSize: "25" });
    if (options.cursor) search.set("cursor", options.cursor);
    return request<AiCallPage>(`/api/v1/ai/calls?${search}`);
  },
  /** A small request that sends no data of yours; answered or failed, either way it is a call. `409 AI_NOT_CONFIGURED` without a provider. */
  test: () => request<AiCall>("/api/v1/ai/test", { method: "POST", body: JSON.stringify({}) }),
  /**
   * Gives the assistant a workbook and the workspace it goes into (0.16 AP6a): `202` with the task, reading.
   * Without a file the words are the whole instruction and the task designs at once; `422
   * AI_TASK_NEEDS_WORDS` without either.
   */
  createTask: (file: File | undefined, body: AiTaskRequest) => {
    const form = new FormData();
    if (file) form.append("file", file);
    form.append("request", JSON.stringify(body));
    return request<AiTask>("/api/v1/ai/tasks", { method: "POST", body: form });
  },
  /**
   * Turns a question in words into the filters of a table view, answered directly (0.16 AG4); aborted by `signal`.
   * `502 QUERY_TRANSLATION_FAILED` when the provider fails or answers what the list cannot take.
   */
  translateQuery: (workspaceKey: string, body: QueryTranslationRequest, signal?: AbortSignal) =>
    request<QueryTranslation>(`/api/v1/workspaces/${encodeURIComponent(workspaceKey)}/query-translations`, {
      ...post(body),
      signal,
    }),
  /**
   * The facts of activating a release in a workspace, worded (0.16 AO1). A provider that fails is not an error:
   * `failure` is set and the facts stand alone. `409 AI_NOT_CONFIGURED`, `403 FORBIDDEN`.
   */
  explainRelease: (releaseId: string, body: ImpactSummaryRequest, signal?: AbortSignal) =>
    request<ImpactSummary>(`/api/v1/model-releases/${encodeURIComponent(releaseId)}/impact-summary`, {
      ...post(body),
      signal,
    }),
  /** The same for a draft at `expectedVersion`; `422 IMPACT_SUMMARY_DRAFT_INVALID` for an invalid draft. */
  explainDraft: (draftId: string, body: ImpactSummaryRequest, signal?: AbortSignal) =>
    request<ImpactSummary>(`/api/v1/model-drafts/${encodeURIComponent(draftId)}/impact-summary`, {
      ...post(body),
      signal,
    }),
  /**
   * The facts of what changed in a workspace over a period, worded (0.16 AO2). A provider that fails is not an
   * error: `failure` is set and the facts stand alone. `409 AI_NOT_CONFIGURED`, `403 FORBIDDEN`, `422 HISTORY_PERIOD_INVALID`.
   */
  explainWorkspaceHistory: (workspaceKey: string, body: HistoryAccountRequest, signal?: AbortSignal) =>
    request<HistoryAccount>(`/api/v1/workspaces/${encodeURIComponent(workspaceKey)}/history/account`, {
      ...post(body),
      signal,
    }),
  /** The same for one record's changes. */
  explainRecordHistory: (objectTypeKey: string, objectId: string, body: HistoryAccountRequest, signal?: AbortSignal) =>
    request<HistoryAccount>(
      `/api/v1/objects/${encodeURIComponent(objectTypeKey)}/${encodeURIComponent(objectId)}/history/account`,
      { ...post(body), signal },
    ),
  task: (id: string) => request<AiTask>(taskPath(id)),
  /** The records the latest check would change in a sheet (source) of the design, a page at a time. */
  taskChanges: (id: string, where: { source: number }, cursor?: string) => {
    const search = new URLSearchParams({ source: String(where.source), pageSize: "25" });
    if (cursor) search.set("cursor", cursor);
    return request<AiTaskChangePage>(`${taskPath(id)}/changes?${search}`);
  },
  runTask: (id: string, body: AiTaskRunRequest) => request<AiTask>(`${taskPath(id)}/run`, post(body)),
  /** Answers the assistant's questions; it designs again (`202`, state checking). */
  answerTask: (id: string, body: AiTaskAnswerRequest) => request<AiTask>(`${taskPath(id)}/answers`, post(body)),
  /** Tells the assistant what to change in the proposed model; it proposes again (`202`, state checking). */
  correctModel: (id: string, body: { expectedVersion: number; correction: string }) =>
    request<AiTask>(`${taskPath(id)}/model`, post(body)),
  /** Accepts the proposed model; the load stage maps the sheets and checks every row (`202`). */
  acceptModel: (id: string, body: { expectedVersion: number }) => request<AiTask>(`${taskPath(id)}/accept`, post(body)),
  /** Goes on with a task that stopped, from where it was, with the person's words when there are some (0.16 AP13). */
  retryTask: (id: string, body: { expectedVersion: number; words?: string }) =>
    request<AiTask>(`${taskPath(id)}/retry`, post(body)),
  /** From a saved layout's load stage back to its proposal (200, no job). */
  reopenProposal: (id: string, body: { expectedVersion: number }) =>
    request<AiTask>(`${taskPath(id)}/proposal`, post(body)),
  /** Ends the task: its draft goes, and a loaded task's change set with it. */
  discardTask: (id: string) => request<AiTask>(`${taskPath(id)}/discard`, post({})),
  /** Stops what the assistant is doing; the turn ends, not the task (0.16 AP13). */
  cancelTask: (id: string) => request<AiTask>(`${taskPath(id)}/cancel`, post({})),
};
