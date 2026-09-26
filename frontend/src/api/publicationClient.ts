import { api } from "@/api/client";

/** Read-only adapter that carries one immutable publication through every shared record read. */
export function createPublicationClient(publicationId: string): typeof api {
  return {
    ...api,
    objects: (type, query) => api.objects(type, { ...query, changeSetId: undefined, publicationId: publicationId }),
    object: (type, id, workspace) => api.object(type, id, workspace, undefined, publicationId),
    attribute: (type, id, key) => api.attribute(type, id, key, undefined, publicationId),
    relations: (id, options) => api.relations(id, { ...options, changeSetId: undefined, publicationId: publicationId }),
    relation: (id, workspace) => api.relation(id, workspace, undefined, publicationId),
    mappingCoverage: (query) => api.mappingCoverage({ ...query, changeSetId: undefined, publicationId: publicationId }),
    mappingTargets: (query) => api.mappingTargets({ ...query, changeSetId: undefined, publicationId: publicationId }),
    mappingCandidates: (query) =>
      api.mappingCandidates({ ...query, changeSetId: undefined, publicationId: publicationId }),
  };
}
