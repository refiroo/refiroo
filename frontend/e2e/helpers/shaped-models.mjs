// The two models the 0.12 runners walk (R-F13): the starter, and the journey configuration
// generated-b (backend/tests/journeys/configurations.py), which differs in keys, names and shape.
// A runner reads what it needs from the model it booted on (`startingPoint`), never a key of either.
import { writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { bootHarness } from "./harness.mjs";
import { cloneDatabase } from "./database.mjs";
import { python } from "./moves.mjs";

let generatedB;
function generatedModel() {
  generatedB ??= python(
    "import json, sys; sys.path.insert(0, 'tests/journeys'); from configurations import generated; print(json.dumps(generated('b').model))",
  );
  const model = structuredClone(generatedB);
  model.schemaVersion = "0.10";
  return model;
}

/** The walks, one boot each: a runner loops over these. */
export const SHAPED_MODELS = [{ name: "starter" }, { name: "generated-b", generated: true }];

/** `bootHarness` on the configuration's model: the starter with its records, or generated-b on the empty database. */
export function bootShaped(configuration, options = {}) {
  if (!configuration.generated) return bootHarness(options);
  return bootHarness({
    ...options,
    prepare: async (output) => {
      const modelPath = resolve(output, "model.json");
      await writeFile(modelPath, JSON.stringify(generatedModel()));
      return { modelPath, database: cloneDatabase("schema") };
    },
  });
}

/** Every table view over an object type, in model order, with what seeding it would take (or `undefined`). */
function tablesOf(model) {
  const found = [];
  for (const application of model.applications)
    for (const view of application.views) {
      if (view.type !== "table" || !view.objectTypeKey) continue;
      const type = model.objectTypes.find((item) => item.key === view.objectTypeKey);
      if (!type) continue;
      const attributes = (type.attributes ?? []).filter((item) => item.required);
      const kinds = attributes.map((item) => model.attributeTypes.find((a) => a.key === item.attributeTypeKey));
      const seedable =
        type.features?.rootCreatable &&
        !type.validation?.atLeastOneOf &&
        kinds.every((kind) => kind?.valueType === "text");
      found.push({ application, view, type, attributes, seedable });
    }
  return found;
}

/** The table's records, `count` at least (made through the API where the model has fewer); undefined if it cannot. */
async function withRecords(api, model, { application, view, type, attributes, seedable }, count) {
  const read = () =>
    api(`/objects/${type.key}?workspaceKey=default&pageSize=${Math.max(count, 5)}&applicationKey=${application.key}`);
  let { items } = await read();
  if (items.length < count && !seedable) return undefined;
  for (let index = items.length; index < count; index++)
    await api("/objects", {
      applicationKey: application.key,
      workspaceKey: "default",
      objectTypeKey: type.key,
      name: `${type.name} ${String(index).padStart(2, "0")}`,
      attributes: attributes.map((item) => ({
        attributeTypeKey: item.attributeTypeKey,
        value: `${item.attributeTypeKey}-${index}`,
      })),
    });
  if (items.length < count) items = (await read()).items;
  return {
    model,
    application,
    view,
    type,
    records: items,
    heading: view.name,
    path: `/apps/${application.key}/views/${view.key}?workspaceKey=default`,
  };
}

/**
 * The first table view of the default workspace's model that has at least `count` records or can be given
 * them. Returns the application, view, type, the page's heading and path, the model and the records.
 */
export async function startingPoint(api, { count = 3 } = {}) {
  const model = await api("/model?workspaceKey=default");
  for (const table of tablesOf(model)) {
    const found = await withRecords(api, model, table, count);
    if (found) return found;
  }
  throw new Error("the model has no table with records or one that can be given some");
}

/** The first `tables` such tables of one application (the first that has that many), each with records. */
export async function startingPoints(api, { tables = 2, count = 2 } = {}) {
  const model = await api("/model?workspaceKey=default");
  const all = tablesOf(model);
  for (const { application } of all) {
    const found = [];
    for (const table of all.filter((item) => item.application.key === application.key)) {
      const withThem = found.length < tables ? await withRecords(api, model, table, count) : undefined;
      if (withThem) found.push(withThem);
    }
    if (found.length >= tables) return found;
  }
  throw new Error(`no application has ${tables} tables with records`);
}
