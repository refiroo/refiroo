import type {
  ApplicationDefinition,
  DetailViewDefinition,
  EngineModel,
  ObjectItem,
  ObjectTypeDefinition,
  RouteState,
} from "../types";

export function objectTypeFor(model: EngineModel, key: string) {
  return model.objectTypes.find((item) => item.key === key);
}

export function attributeName(model: EngineModel, key: string) {
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
  if (key === "name") return item.name;
  if (key === "state") return item.state;
  if (key === "path") return item.path.map((part) => part.name).join(" / ");
  if (key === "objectType") return objectTypeFor(model!, item.objectTypeKey)?.name ?? item.objectTypeKey;
  if (key === "id") return item.id;
  if (key === "createdAt") return item.createdAt;
  if (key === "updatedAt") return item.updatedAt;
  return item.attributes[key];
}

export function applicationFor(model: EngineModel, key: string) {
  return model.applications.find((item) => item.key === key);
}

export function defaultRoute(model: EngineModel): RouteState {
  const application = model.applications[0];
  return {
    kind: "list",
    applicationKey: application?.key ?? "",
    viewKey: application?.defaultView ?? "",
  };
}

export function parseRoute(model: EngineModel): RouteState {
  const parts = window.location.pathname.split("/").filter(Boolean).map(decodeURIComponent);
  if (parts[0] === "apps" && parts[2] === "views" && parts[3]) {
    const application = applicationFor(model, parts[1]);
    if (application?.views.some((view) => view.key === parts[3])) {
      return { kind: "list", applicationKey: parts[1], viewKey: parts[3] };
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
      };
    }
  }
  return defaultRoute(model);
}

export function routePath(route: RouteState) {
  const app = encodeURIComponent(route.applicationKey);
  if (route.kind === "list") {
    return `/apps/${app}/views/${encodeURIComponent(route.viewKey)}`;
  }
  return `/apps/${app}/objects/${encodeURIComponent(route.objectTypeKey)}/${encodeURIComponent(route.objectId)}`;
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

export function viewRoute(application: ApplicationDefinition, viewKey: string): RouteState {
  return { kind: "list", applicationKey: application.key, viewKey };
}
