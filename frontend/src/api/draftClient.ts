import { api, type DraftWriteContext } from "@/api/client";
import { errorMessage, isApiError } from "@/api/errors";
import type { WorkspaceDraft } from "@/types";

/** One mounted draft owns its aggregate token. Record versions remain the forms' responsibility. */
export function createDraftClient(
  initial: WorkspaceDraft,
  changed: (draft: WorkspaceDraft) => void,
  warning: (message: string) => void,
) {
  let draft: WorkspaceDraft | undefined = initial;
  let pending = false;
  async function refresh() {
    const current = await api.workspaceDraft(initial.id);
    draft = current;
    changed(current);
    warning("");
    return current;
  }
  async function write<T>(perform: (context: DraftWriteContext) => Promise<T>): Promise<T> {
    if (pending) throw new Error("Another draft change is still being saved. Wait, then try again.");
    if (!draft)
      throw new Error(
        "The current draft version is unavailable. Refresh the draft version before saving again. Your input is preserved.",
      );
    pending = true;
    try {
      const result = await perform({ workspaceDraftId: initial.id, expectedWorkspaceDraftVersion: draft.version });
      // A committed save must not look like a failed write if the subsequent version read fails.
      draft = undefined;
      try {
        await refresh();
      } catch (cause) {
        warning(`Saved, but the draft version could not be refreshed. ${errorMessage(cause)}`);
      }
      return result;
    } catch (cause) {
      if (
        isApiError(cause, "workspace_draft_version_conflict") ||
        isApiError(cause, "version_conflict") ||
        isApiError(cause, "deletion_preview_changed")
      ) {
        draft = undefined;
        try {
          await refresh();
        } catch (refreshCause) {
          warning(errorMessage(refreshCause));
        }
      }
      throw cause;
    } finally {
      pending = false;
    }
  }
  const client: typeof api = {
    ...api,
    objects: (type, query) => api.objects(type, { ...query, workspaceDraftId: initial.id }),
    object: (type, id, workspace) => api.object(type, id, workspace, initial.id),
    attribute: (type, id, key) => api.attribute(type, id, key, initial.id),
    relations: (id, options) => api.relations(id, { ...options, workspaceDraftId: initial.id }),
    relation: (id, workspace) => api.relation(id, workspace, initial.id),
    createObject: (type, payload) => write((context) => api.createObject(type, { ...payload, ...context })),
    updateObject: (type, id, payload) => write((context) => api.updateObject(type, id, { ...payload, ...context })),
    deleteObject: (type, id, version, options) =>
      write((context) => api.deleteObject(type, id, version, { ...options, ...context })),
    createAttribute: (type, id, key, value, version) =>
      write((context) => api.createAttribute(type, id, key, value, version, context)),
    updateAttribute: (type, id, key, value, version) =>
      write((context) => api.updateAttribute(type, id, key, value, version, context)),
    deleteAttribute: (type, id, key, version) =>
      write((context) => api.deleteAttribute(type, id, key, version, context)),
    createRelation: (payload) => write((context) => api.createRelation({ ...payload, ...context })),
    updateRelation: (id, payload) => write((context) => api.updateRelation(id, { ...payload, ...context })),
    deleteRelation: (id, version) => write((context) => api.deleteRelation(id, version, context)),
  };
  return { client, refresh };
}
