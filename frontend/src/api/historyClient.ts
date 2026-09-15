import { api } from "@/api/client";

/** Read-only adapter that carries one immutable revision through every shared record read. */
export function createHistoryClient(revisionId: string): typeof api {
  return {
    ...api,
    objects: (type, query) =>
      api.objects(type, { ...query, workspaceDraftId: undefined, workspaceRevisionId: revisionId }),
    object: (type, id, workspace) => api.object(type, id, workspace, undefined, revisionId),
    attribute: (type, id, key) => api.attribute(type, id, key, undefined, revisionId),
    relations: (id, options) =>
      api.relations(id, { ...options, workspaceDraftId: undefined, workspaceRevisionId: revisionId }),
    relation: (id, workspace) => api.relation(id, workspace, undefined, revisionId),
    mappingCoverage: (query) =>
      api.mappingCoverage({ ...query, workspaceDraftId: undefined, workspaceRevisionId: revisionId }),
    mappingTargets: (query) =>
      api.mappingTargets({ ...query, workspaceDraftId: undefined, workspaceRevisionId: revisionId }),
    mappingCandidates: (query) =>
      api.mappingCandidates({ ...query, workspaceDraftId: undefined, workspaceRevisionId: revisionId }),
  };
}
