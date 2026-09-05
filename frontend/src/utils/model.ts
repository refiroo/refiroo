import type {
  ApplicationDefinition,
  DetailViewDefinition,
  EngineModel,
  ObjectItem,
  ObjectTypeDefinition,
  ObjectTypeRelationDefinition,
  RelationsPanelDefinition,
  RouteState,
  ObjectSort,
} from "../types";

export const DEFAULT_WORKSPACE = "default";
export const DEFAULT_COLLECTION_QUERY = {
  search: "",
  states: [] as string[],
  sort: "name" as ObjectSort,
  pageSize: 20,
};
const OBJECT_SORTS = new Set<ObjectSort>([
  "name",
  "-name",
  "state",
  "-state",
  "createdAt",
  "-createdAt",
  "updatedAt",
  "-updatedAt",
]);

export function objectTypeFor(model: EngineModel, key: string) {
  return model.objectTypes.find((item) => item.key === key);
}

export interface RelationChoice {
  direction: "outgoing" | "incoming";
  relation: ObjectTypeRelationDefinition;
  otherObjectTypeKey: string;
  label: string;
}

export function isManagedRelation(model: EngineModel, relation: ObjectTypeRelationDefinition) {
  const target = objectTypeFor(model, relation.toObjectTypeKey);
  return (target?.behavior.parentRelationTypeKeys ?? []).includes(relation.relationTypeKey);
}

export function relationChoices(
  model: EngineModel,
  objectTypeKey: string,
  panel: RelationsPanelDefinition,
): RelationChoice[] {
  const allowedKeys = new Set(panel.config.relationTypeKeys);
  const choices: RelationChoice[] = [];
  for (const relation of model.objectTypeRelations) {
    if (!allowedKeys.has(relation.relationTypeKey) || relation.required || isManagedRelation(model, relation)) continue;
    const definition = model.relationTypes.find((item) => item.key === relation.relationTypeKey);
    if (!definition) continue;
    if (
      (panel.config.direction === "outgoing" || panel.config.direction === "both") &&
      relation.fromObjectTypeKey === objectTypeKey
    ) {
      choices.push({
        direction: "outgoing",
        relation,
        otherObjectTypeKey: relation.toObjectTypeKey,
        label: definition.name,
      });
    }
    if (
      (panel.config.direction === "incoming" || panel.config.direction === "both") &&
      relation.toObjectTypeKey === objectTypeKey
    ) {
      choices.push({
        direction: "incoming",
        relation,
        otherObjectTypeKey: relation.fromObjectTypeKey,
        label: definition.reverseName,
      });
    }
  }
  return choices;
}

export function attributeName(model: EngineModel, key: string) {
  if (key.startsWith("ancestor:")) {
    const objectTypeKey = key.slice("ancestor:".length);
    return objectTypeFor(model, objectTypeKey)?.name ?? objectTypeKey;
  }
  if (key === "name") return "Name";
  if (key === "state") return "State";
  if (key === "path") return "Path";
  if (key === "objectType") return "Type";
  if (key === "id") return "ID";
  if (key === "createdAt") return "Created";
  if (key === "updatedAt") return "Updated";
  return model.attributeTypes.find((item) => item.key === key)?.name ?? key;
}

export function fieldValue(item: ObjectItem, key: string, model?: EngineModel): unknown {
  if (key.startsWith("ancestor:")) {
    const objectTypeKey = key.slice("ancestor:".length);
    return item.path.find((part) => part.objectTypeKey === objectTypeKey)?.name;
  }
  if (key === "name") return item.name;
  if (key === "state") return item.state;
  if (key === "path") return item.path.map((part) => part.name).join(" / ");
  if (key === "objectType") return objectTypeFor(model!, item.objectTypeKey)?.name ?? item.objectTypeKey;
  if (key === "id") return item.id;
  if (key === "createdAt") return item.createdAt;
  if (key === "updatedAt") return item.updatedAt;
  return item.attributes.find((attribute) => attribute.attributeTypeKey === key)?.value;
}

export function applicationFor(model: EngineModel, key: string) {
  return model.applications.find((item) => item.key === key);
}

export function defaultRoute(model: EngineModel): Extract<RouteState, { kind: "list" }> {
  const application = model.applications[0];
  return {
    kind: "list",
    applicationKey: application?.key ?? "",
    viewKey: application?.defaultView ?? "",
    workspaceKey: DEFAULT_WORKSPACE,
    ...DEFAULT_COLLECTION_QUERY,
  };
}

export function parseRoute(model: EngineModel): RouteState {
  const parts = window.location.pathname.split("/").filter(Boolean).map(decodeURIComponent);
  const query = new URLSearchParams(window.location.search);
  const workspaceKey = query.get("workspaceKey")?.trim() || DEFAULT_WORKSPACE;
  if (parts[0] === "models") {
    const releaseId = query.get("releaseId")?.trim() || undefined;
    const draftId = query.get("draftId")?.trim() || undefined;
    return draftId ? { kind: "models", draftId } : { kind: "models", ...(releaseId ? { releaseId } : {}) };
  }
  if (parts[0] === "apps" && parts[2] === "views" && parts[3]) {
    const application = applicationFor(model, parts[1]);
    if (application?.views.some((view) => view.key === parts[3])) {
      const candidateSort = query.get("sort") as ObjectSort | null;
      const requestedPageSize = Number(query.get("pageSize"));
      return {
        kind: "list",
        applicationKey: parts[1],
        viewKey: parts[3],
        workspaceKey,
        search: query.get("search") ?? "",
        states: query
          .getAll("state")
          .map((value) => value.trim())
          .filter(Boolean),
        sort: candidateSort && OBJECT_SORTS.has(candidateSort) ? candidateSort : DEFAULT_COLLECTION_QUERY.sort,
        pageSize:
          Number.isInteger(requestedPageSize) && requestedPageSize >= 1 && requestedPageSize <= 500
            ? requestedPageSize
            : DEFAULT_COLLECTION_QUERY.pageSize,
      };
    }
  }
  if (parts[0] === "apps" && parts[2] === "objects" && parts[3] && parts[4]) {
    const application = applicationFor(model, parts[1]);
    if (application?.objectTypeKeys.includes(parts[3])) {
      return {
        kind: "detail",
        applicationKey: parts[1],
        objectTypeKey: parts[3],
        objectId: parts[4],
        workspaceKey,
      };
    }
  }
  return { ...defaultRoute(model), workspaceKey };
}

export function routePath(route: RouteState) {
  if (route.kind === "models") {
    const query = new URLSearchParams();
    if (route.releaseId) query.set("releaseId", route.releaseId);
    if (route.draftId) query.set("draftId", route.draftId);
    return `/models${query.size ? `?${query}` : ""}`;
  }
  const app = encodeURIComponent(route.applicationKey);
  const query = new URLSearchParams({ workspaceKey: route.workspaceKey });
  if (route.kind === "list") {
    if (route.search) query.set("search", route.search);
    route.states.forEach((state) => query.append("state", state));
    query.set("sort", route.sort);
    query.set("pageSize", String(route.pageSize));
    return `/apps/${app}/views/${encodeURIComponent(route.viewKey)}?${query}`;
  }
  return `/apps/${app}/objects/${encodeURIComponent(route.objectTypeKey)}/${encodeURIComponent(route.objectId)}?${query}`;
}

export function fallbackDetail(objectType: ObjectTypeDefinition): DetailViewDefinition {
  return {
    objectTypeKey: objectType.key,
    breadcrumbs: { showApplication: true, showObjectType: true, showAncestors: true },
    header: {
      titleField: "name",
      subtitleField: objectType.displayAttributeTypeKey,
      showObjectType: true,
    },
    panels: [
      {
        key: "attributes",
        title: `${objectType.name} details`,
        type: "attributes",
        region: "main",
        order: 10,
        visible: true,
        config: {
          fields: objectType.attributes
            .slice()
            .sort((a, b) => a.order - b.order)
            .map((binding) => binding.attributeTypeKey),
        },
      },
      {
        key: "hierarchy",
        title: "Hierarchy",
        type: "hierarchy",
        region: "side",
        order: 10,
        visible: true,
        config: { showParent: true, showAncestors: true },
      },
    ],
  };
}

export function viewRoute(
  application: ApplicationDefinition,
  viewKey: string,
  workspaceKey = DEFAULT_WORKSPACE,
): Extract<RouteState, { kind: "list" }> {
  return { kind: "list", applicationKey: application.key, viewKey, workspaceKey, ...DEFAULT_COLLECTION_QUERY };
}
