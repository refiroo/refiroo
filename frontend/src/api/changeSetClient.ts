import { api, type ChangeSetWriteContext } from "@/api/client";
import { errorMessage, isApiError } from "@/api/errors";
import type { ChangeSet } from "@/types";

/** One mounted change set owns its aggregate token. Record versions remain the forms' responsibility. */
export function createChangeSetClient(
  initial: ChangeSet,
  changed: (changeSet: ChangeSet) => void | Promise<void>,
  warning: (message: string) => void,
) {
  let changeSet: ChangeSet | undefined = initial;
  let pending = false;
  async function refresh() {
    changeSet = undefined;
    const current = await api.changeSet(initial.id);
    await changed(current);
    changeSet = current;
    warning("");
    return current;
  }
  async function write<T>(perform: (context: ChangeSetWriteContext) => Promise<T>): Promise<T> {
    if (pending) throw new Error("Another change set change is still being saved. Wait, then try again.");
    if (!changeSet)
      throw new Error(
        "The current change set version is unavailable. Refresh the change set version before saving again. Your input is preserved.",
      );
    pending = true;
    try {
      const result = await perform({ changeSetId: initial.id, expectedChangeSetVersion: changeSet.version });
      // A committed save must not look like a failed write if the subsequent version read fails.
      changeSet = undefined;
      try {
        await refresh();
      } catch (cause) {
        warning(`Saved, but the change set version could not be refreshed. ${errorMessage(cause)}`);
      }
      return result;
    } catch (cause) {
      if (
        isApiError(cause, "change_set_version_conflict") ||
        isApiError(cause, "version_conflict") ||
        isApiError(cause, "deletion_preview_changed")
      ) {
        changeSet = undefined;
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
    objects: (type, query) => api.objects(type, { ...query, changeSetId: initial.id }),
    object: (type, id, workspace) => api.object(type, id, workspace, initial.id),
    attribute: (type, id, key) => api.attribute(type, id, key, initial.id),
    relations: (id, options) => api.relations(id, { ...options, changeSetId: initial.id }),
    relation: (id, workspace) => api.relation(id, workspace, initial.id),
    mappingCoverage: (query) => api.mappingCoverage({ ...query, changeSetId: initial.id }),
    mappingTargets: (query) => api.mappingTargets({ ...query, changeSetId: initial.id }),
    mappingCandidates: (query) => api.mappingCandidates({ ...query, changeSetId: initial.id }),
    replaceMapping: (workspaceKey, body) =>
      write((context) => api.replaceMapping(workspaceKey, { ...body, ...context })),
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
