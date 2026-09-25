// Base 0.7 WP-9 acceptance data: model variants and records for SC-07 and SC-15, created through
// the real API on top of the harness seed. The browser runners use starter keys as fixtures only.

/**
 * An independent relation binding with its own labels, direction and typed relation attribute
 * (SC-07 "repeat with another relationship configuration"), declared as a second mapping lens on
 * master values. It is not the reverse view of the starter mapping binding.
 */
export function addAlignmentBinding(model) {
  model.attributeTypes.push({
    key: "qa-confidence",
    name: "Confidence",
    valueType: "integer",
    validation: { minimum: 0, maximum: 10 },
  });
  model.relationTypes.push({
    key: "qa-master-aligns-to-system",
    reverseKey: "qa-system-aligned-from-master",
    name: "Aligns to system value",
    reverseName: "Aligned from master value",
    features: { searchable: true },
  });
  model.objectTypeRelations.push({
    relationTypeKey: "qa-master-aligns-to-system",
    fromObjectTypeKey: "master-value",
    toObjectTypeKey: "system-value",
    cardinality: "many-to-many",
    attributeTypeKeys: ["qa-confidence"],
  });
  model.applications
    .find((application) => application.key === "rdm-master")
    .views.push({
      key: "qa-alignment",
      name: "Master alignment",
      type: "mappingGrid",
      config: {
        relationTypeKey: "qa-master-aligns-to-system",
        fromObjectTypeKey: "master-value",
        toObjectTypeKey: "system-value",
        direction: "outgoing",
        sourceColumns: ["value-code"],
        targetDisplayColumns: ["value-code"],
        candidateSearchFields: ["name", "value-code"],
        pageSize: 20,
      },
    });
}

/**
 * SC-15 candidate release on the same schema: a new bounded field (a rule the active release does
 * not have) shown in a renamed system-value table view. Existing content already fits it.
 */
export function nextReleaseModel(active, version) {
  const model = structuredClone(active);
  model.release = { ...model.release, version };
  model.attributeTypes.push({
    key: "qa-priority",
    name: "Priority",
    valueType: "integer",
    validation: { minimum: 1, maximum: 5 },
    features: { filterable: true, sortable: true },
  });
  model.objectTypes.find((type) => type.key === "system-value").attributes.push({ attributeTypeKey: "qa-priority", order: 50 });
  const systems = model.applications.find((application) => application.key === "rdm-systems");
  const view = systems.views.find((item) => item.key === "system-values");
  view.name = "Prioritised values";
  view.config.columns.push("qa-priority");
  for (const detail of systems.details?.filter((item) => item.objectTypeKey === "system-value") ?? []) {
    detail.panels.find((panel) => panel.type === "attributes")?.config.fields.push("qa-priority");
  }
  return model;
}

/** SC-15 incompatible candidate: a newly required field that existing system values lack. */
export function incompatibleReleaseModel(active, version) {
  const model = structuredClone(active);
  model.release = { ...model.release, version };
  model.objectTypes
    .find((type) => type.key === "system-value")
    .attributes.find((binding) => binding.attributeTypeKey === "external-id").required = true;
  return model;
}

/** Install a model as an inactive release through the model-draft workbench API. */
export async function installRelease(api, name, model) {
  const draft = await api("/model-drafts", { name, model });
  return api(`/model-drafts/${draft.id}/installation`, { expectedVersion: draft.version });
}

/**
 * SC-07 records: canonical master values (with enough fillers that some candidates are beyond the
 * first page of 20), and system values that are unmapped (PICKUP), mapped to a different target
 * (HOME) and ambiguous across a set larger than the inline preview (MULTI).
 */
export async function seedMappingData(api, records) {
  const codelists = await api("/objects/codelist?workspaceKey=default&applicationKey=rdm-master&pageSize=20");
  const codelist = codelists.items.find((item) => item.name === "Codelist Alpha");
  const masters = {};
  async function master(name, code) {
    masters[name] = await api("/objects", {
      applicationKey: "rdm-master",
      workspaceKey: "default",
      objectTypeKey: "master-value",
      name,
      parentObjectId: codelist.id,
      attributes: [
        { attributeTypeKey: "master-id", value: `MV-${code}` },
        { attributeTypeKey: "value-code", value: code },
        { attributeTypeKey: "value-name", value: name },
      ],
    });
    return masters[name];
  }
  await master("Collection", "COLLECT");
  await master("Home delivery", "HOME");
  await master("Parcel locker", "LOCKER");
  const fillers = [];
  for (let i = 1; i <= 24; i++) fillers.push(await master(`Filler ${String(i).padStart(2, "0")}`, `F${i}`));

  const systemValues = {};
  for (const code of ["PICKUP", "HOME", "MULTI"]) {
    systemValues[code] = await api("/objects", {
      applicationKey: "rdm-systems",
      workspaceKey: "default",
      objectTypeKey: "system-value",
      name: code,
      parentObjectId: records.system[0].id,
      attributes: [
        { attributeTypeKey: "value-code", value: code },
        { attributeTypeKey: "value-name", value: code },
      ],
    });
  }
  const relate = (relationTypeKey, from, to, attributes) =>
    api("/relations", { relationTypeKey, fromObjectId: from.id, toObjectId: to.id, ...(attributes ? { attributes } : {}) });
  const mapping = "system-value-maps-to-master";
  await relate(mapping, systemValues.HOME, masters["Parcel locker"]);
  const multiCollection = await relate(mapping, systemValues.MULTI, masters.Collection);
  for (const filler of fillers) await relate(mapping, systemValues.MULTI, filler);

  const alignment = "qa-master-aligns-to-system";
  const aligned = {
    home: await relate(alignment, masters.Collection, systemValues.HOME, { "qa-confidence": 7 }),
    pickup: await relate(alignment, masters.Collection, systemValues.PICKUP, { "qa-confidence": 3 }),
  };
  return { codelist, masters, fillers, systemValues, multiCollection, aligned };
}
