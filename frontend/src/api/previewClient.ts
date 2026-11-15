/**
 * The data client of the model editor's preview (0.10 A4b, D44, D45).
 *
 * The preview renders a draft's layout with the record screen's renderers over records of the
 * active model, read live. This client lets through the reads those renderers make and refuses
 * every other call in the browser, before a request is sent, so nothing the preview shows can write.
 * A read the active model cannot answer is adjusted or answered here instead of failing:
 *
 * - the empty record of a new type (`PREVIEW_EMPTY_ID`) is answered without the server;
 * - a type the active model does not hold has no records yet, so its lists are empty;
 * - a sort, filter or relation column naming a field the active type lacks is left out;
 * - a picker's choice rule that the draft adds or changes is not applied (D45).
 */

import { api } from "@/api/client";
import { objectTypeFor, RELATED_FIELD_PREFIX, relatedColumn } from "@/model/lookup";
import type { EngineModel, ObjectItem, ObjectTypeRelationDefinition } from "@/types";

/** The ID of the empty record a new type's preview shows. */
export const PREVIEW_EMPTY_ID = "preview-empty-record";

/** Why a call the preview did not let through was refused. */
export class PreviewWriteRefused extends Error {
  constructor() {
    super("The preview writes nothing. Install and activate the draft to change records.");
    this.name = "PreviewWriteRefused";
  }
}

type Client = typeof api;

/** The reads the record screen's renderers make; every other client call is refused. */
const READS = [
  "capabilities",
  "workspaces",
  "workspace",
  "workspaceRuntimeState",
  "workspaceModel",
  "objects",
  "object",
  "attribute",
  "heldRecords",
  "relations",
  "relation",
  "objectHistory",
  "mappingCoverage",
  "mappingCandidates",
  "mappingTargets",
  "relationTable",
  "relationGrid",
  "relationMatrix",
  "relationMatrixContainers",
  "relationMatrixLinkCandidates",
] as const satisfies readonly (keyof Client)[];

const emptyPage = { items: [], nextCursor: null, prevCursor: null, totalCount: 0, startIndex: 0 };

/** The empty record of a new type, as the record screen reads one. */
export function emptyRecord(applicationKey: string, objectTypeKey: string, workspaceKey: string): ObjectItem {
  return {
    id: PREVIEW_EMPTY_ID,
    workspaceKey,
    applicationKey,
    objectTypeKey,
    parentObjectId: null,
    name: "",
    path: [],
    attributes: [],
    version: 0,
    createdAt: null,
    updatedAt: null,
  };
}

/**
 * The relations of `objectTypeKey` whose pickers list the far type unlimited in the preview: the
 * draft allows them anew or changes their choice rule, which the active model cannot apply (D45).
 */
export function relaxedPickerRelations(active: EngineModel, draft: EngineModel, objectTypeKey: string) {
  const rule = (binding: ObjectTypeRelationDefinition) => JSON.stringify(binding.candidates ?? null);
  const keys = new Set<string>();
  for (const binding of draft.objectTypeRelations) {
    if (binding.fromObjectTypeKey !== objectTypeKey && binding.toObjectTypeKey !== objectTypeKey) continue;
    const held = active.objectTypeRelations.find(
      (item) =>
        item.relationTypeKey === binding.relationTypeKey &&
        item.fromObjectTypeKey === binding.fromObjectTypeKey &&
        item.toObjectTypeKey === binding.toObjectTypeKey,
    );
    if (!held || rule(held) !== rule(binding)) keys.add(binding.relationTypeKey);
  }
  return [...keys];
}

/** The fields of the draft's type that the active model's type does not hold. */
function unknownFields(active: EngineModel, draft: EngineModel, objectTypeKey: string) {
  const activeType = objectTypeFor(active, objectTypeKey);
  const draftType = objectTypeFor(draft, objectTypeKey);
  const held = new Set(activeType?.attributes.map((item) => item.attributeTypeKey) ?? []);
  return new Set((draftType?.attributes ?? []).map((item) => item.attributeTypeKey).filter((key) => !held.has(key)));
}

/**
 * Whether the active model answers an `expand` entry: a relation key or reverse key, alone or with a
 * field of the related records (`<key>.<field>`, `<key>.ancestor:<type>.<field>`, 0.9 K5a), where the
 * field is the name or an attribute the active model has and the ancestor type is one it holds.
 */
function answersExpand(active: EngineModel, entry: string) {
  const column = relatedColumn(active, RELATED_FIELD_PREFIX + entry);
  if (!column) return false;
  if (!column.field) return true;
  const attributes = new Set(active.attributeTypes.map((item) => item.key));
  const known = (field: string) => field === "name" || attributes.has(field);
  if (!column.field.startsWith("ancestor:")) return known(column.field);
  const rest = column.field.slice("ancestor:".length);
  const dot = rest.indexOf(".");
  const typeKey = dot < 0 ? rest : rest.slice(0, dot);
  return active.objectTypes.some((item) => item.key === typeKey) && (dot < 0 || known(rest.slice(dot + 1)));
}

function namesSample(args: unknown[]) {
  return JSON.stringify(args).includes(PREVIEW_EMPTY_ID);
}

/** A client for the preview of `draft` over the records of the `active` model. */
export function createPreviewClient(active: EngineModel, draft: EngineModel, sample?: ObjectItem): Client {
  const activeTypes = new Set(active.objectTypes.map((item) => item.key));
  const refused = new Proxy({} as Client, {
    get: () => () => Promise.reject(new PreviewWriteRefused()),
  });
  const reads = Object.fromEntries(
    READS.map((name) => [
      name,
      (...args: unknown[]) =>
        namesSample(args)
          ? Promise.resolve(emptyPage)
          : (api[name] as (...values: unknown[]) => Promise<unknown>)(...args),
    ]),
  ) as Partial<Client>;
  const client: Partial<Client> = {
    ...reads,
    object: (objectTypeKey, objectId, ...rest) =>
      objectId === PREVIEW_EMPTY_ID && sample
        ? Promise.resolve({ ...sample, objectTypeKey })
        : api.object(objectTypeKey, objectId, ...rest),
    objects: (objectTypeKey, query) => {
      if (!activeTypes.has(objectTypeKey) || namesSample([query])) return Promise.resolve(emptyPage);
      const unknown = unknownFields(active, draft, objectTypeKey);
      const sortField = query.sort?.replace(/^-/, "");
      const adjusted = {
        ...query,
        sort: sortField && unknown.has(sortField) ? undefined : query.sort,
        filters: query.filters?.filter((filter) => !unknown.has(filter.field)),
        expand: query.expand?.filter((entry) => answersExpand(active, entry)),
      };
      if (adjusted.candidateFor && adjusted.anchorTypeKey) {
        const relaxed = relaxedPickerRelations(active, draft, adjusted.anchorTypeKey);
        const relation = draft.relationTypes.find(
          (item) => item.key === adjusted.candidateFor || item.reverseKey === adjusted.candidateFor,
        );
        if (relation && relaxed.includes(relation.key)) {
          delete adjusted.candidateFor;
          delete adjusted.anchorTypeKey;
        }
      }
      return api.objects(objectTypeKey, adjusted);
    },
  };
  return new Proxy(client as Client, {
    get: (target, name: string) => (name in target ? target[name as keyof Client] : refused[name as keyof Client]),
  });
}
