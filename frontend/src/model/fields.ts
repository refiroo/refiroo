/**
 * Projection of an object onto the field keys a view or panel declares.
 *
 * `attributeName` labels a key and `fieldValue` reads it, both handling the built-in keys (name,
 * state, path, ancestors, timestamps) alongside attached attribute types. `formatValue` renders a
 * read value; it renders JSX and so lives in `ui/formatValue` rather than here, keeping this
 * module free of presentation.
 */

import type { EngineModel, ObjectItem } from "@/types";
import { objectTypeFor } from "@/model/lookup";

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

export function fieldValue(item: ObjectItem, key: string, model: EngineModel): unknown {
  if (key.startsWith("ancestor:")) {
    const objectTypeKey = key.slice("ancestor:".length);
    return item.path.find((part) => part.objectTypeKey === objectTypeKey)?.name;
  }
  if (key === "name") return item.name;
  if (key === "state") return item.state;
  if (key === "path") return item.path.map((part) => part.name).join(" / ");
  if (key === "objectType") return objectTypeFor(model, item.objectTypeKey)?.name ?? item.objectTypeKey;
  if (key === "id") return item.id;
  if (key === "createdAt") return item.createdAt;
  if (key === "updatedAt") return item.updatedAt;
  return item.attributes.find((attribute) => attribute.attributeTypeKey === key)?.value;
}
