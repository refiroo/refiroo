// Base 0.7 WP-9 acceptance data: model variants and records for SC-07 and SC-15, created through
// the real API on top of the harness seed. The browser runners use starter keys as fixtures only.
import { dragFrom, dragOver } from "./tree.mjs";

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
  // A matrix that creates system values must now ask for the field too, or the release is refused
  // as a model before its data is ever compared (schema 0.7 `cellActions`).
  for (const view of model.applications.flatMap((application) => application.views ?? [])) {
    const config = view.type === "relationMatrix" ? view.config : undefined;
    if (config?.cellObjectTypeKey === "system-value" && config.cellActions?.includes("create")) {
      config.cellFields = [...new Set([...config.cellFields, "external-id"])];
    }
  }
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

/**
 * Base 0.8 S7 gate data: 60 codelists under the last seeded domain, so the codelist lens at ten a
 * page holds part of its list (window scrollbar, page field) and the domain's tree branch scrolls.
 * Records elsewhere, and so the other gate pages, are unchanged.
 */
export async function seedLongList(api, records) {
  const domain = records.domain.at(-1);
  for (let index = 0; index < 60; index++)
    await api("/objects", {
      applicationKey: "rdm-master",
      workspaceKey: "default",
      objectTypeKey: "codelist",
      name: `Long codelist ${String(index).padStart(2, "0")}`,
      parentObjectId: domain.id,
      attributes: [{ attributeTypeKey: "codelist-code", value: `long-${index}` }],
    });
  return domain;
}

/**
 * Opens the codelist lens at page 3 of 10-row pages (the middle of the list) with the long domain's
 * tree branch expanded and focus on a codelist row inside it: one state for the scrolling list and
 * the tree.
 */
export async function openLongList(page, uiUrl, domain) {
  await page.goto(`${uiUrl}/apps/rdm-master/views/codelists?workspaceKey=default&pageSize=10`);
  const table = page.getByRole("region", { name: "Codelists table" });
  await table.locator("[data-row-focus]").first().waitFor();
  const field = page.getByRole("spinbutton", { name: "Page", exact: true });
  await field.fill("3");
  await field.press("Enter");
  await table.getByRole("button", { name: "Long codelist 18", exact: true }).waitFor();
  const tree = page.getByRole("tree", { name: "Browse records", exact: true }).first();
  const row = tree.getByRole("treeitem", { name: domain.name, exact: true });
  await row.focus();
  if ((await row.getAttribute("aria-expanded")) === "false") await page.keyboard.press("ArrowRight");
  await tree.getByRole("treeitem", { name: `Codelists within ${domain.name}, 60`, exact: true }).waitFor();
  await page.keyboard.press("ArrowRight");
  await page.keyboard.press("ArrowDown");
  await page.waitForFunction(() => document.activeElement?.getAttribute("aria-label") === "Long codelist 00");
  await page.waitForLoadState("networkidle");
  return { table, tree };
}

/**
 * Base 0.8 A5 SC-09 translation half: Delivery Methods under the first seeded domain, with Czech,
 * English and German columns in the codelist translation matrix. Czech holds a current translation
 * and a superseded inactive one; English is empty; German was published (publication `number`) and
 * then deleted live, so its cell is history only. Everything goes through the real API.
 */
export async function seedTranslationMatrix(api, records) {
  async function create(applicationKey, objectTypeKey, name, attributes, extra = {}) {
    return api("/objects", {
      applicationKey,
      workspaceKey: "default",
      objectTypeKey,
      name,
      attributes: Object.entries(attributes).map(([attributeTypeKey, value]) => ({ attributeTypeKey, value })),
      ...extra,
    });
  }
  const deliveryMethods = await create(
    "rdm-master",
    "codelist",
    "Delivery Methods",
    { "codelist-code": "delivery-methods" },
    { parentObjectId: records.domain[0].id },
  );
  const languages = {};
  const groups = {};
  for (const [label, code] of [["Czech", "cs"], ["English", "en"], ["German", "de"]]) {
    languages[code] = await create("rdm-translations", "language", label, { "language-code": code });
    groups[code] = await create("rdm-translations", "translation-group", `${code.toUpperCase()} core`, {
      "group-code": `${code}-core`,
    }, { parentObjectId: languages[code].id });
  }
  const translate = (code, name, text, active) =>
    create("rdm-translations", "translation", name, { "translated-name": text, active }, {
      parentObjectId: groups[code].id,
      initialRelations: [
        { relationTypeKey: "object-has-translation", direction: "incoming", otherObjectId: deliveryMethods.id },
      ],
    });
  const czech = await translate("cs", "Delivery Methods cs", "Způsoby doručení", true);
  const superseded = await translate("cs", "Delivery Methods cs (old)", "Doprava", false);
  const german = await translate("de", "Delivery Methods de", "Lieferarten", true);
  // Publish the German translation, then delete it live: only history holds it.
  const changeSet = await api("/workspaces/default/change-sets", { name: "Translations baseline", source: "currentLive" });
  await api(`/change-sets/${changeSet.id}/validation`, undefined, "POST");
  const current = await api(`/change-sets/${changeSet.id}`);
  const latest = (await api("/workspaces/default/publications?pageSize=1")).items[0];
  const publication = await api(`/change-sets/${changeSet.id}/publication`, {
    expectedChangeSetVersion: current.version,
    expectedActivePublicationId: latest?.status === "active" ? latest.id : null,
  });
  // A live deletion that removes relations is previewed first (409 with a token), then confirmed.
  const deletion = `/objects/translation/${german.id}?expectedVersion=${german.version}`;
  const preview = await api(deletion, undefined, "DELETE").then(
    () => {
      throw new Error("deleting a related translation was not previewed");
    },
    (error) => JSON.parse(error.message.slice(error.message.indexOf("{"))).error.details.deletionPreviewToken,
  );
  await api(`${deletion}&cascade=true&deletionPreviewToken=${encodeURIComponent(preview)}`, undefined, "DELETE");
  return { deliveryMethods, languages, groups, czech, superseded, german, publication };
}

/** Opens the codelist translation matrix searched to Delivery Methods, with its cells loaded. */
export async function openTranslationMatrix(page, uiUrl, query = "") {
  await page.goto(
    `${uiUrl}/apps/rdm-translations/views/codelist-translations?workspaceKey=default&search=Delivery${query}`,
  );
  await page.getByRole("rowheader", { name: /Delivery Methods/ }).waitFor();
  await page.waitForFunction(() => !document.querySelector('[role="grid"][aria-busy="true"]'));
  return page.getByRole("grid");
}

/** Opens the Delivery Methods cell under the language column labelled `code`; returns its dialog. */
export async function openTranslationCell(page, code) {
  const column = await page.evaluate((label) => {
    const headers = Array.from(document.querySelectorAll('[role="grid"] thead th'));
    return headers.findIndex((th) => th.querySelector(".matrix-column-label")?.textContent === label);
  }, code);
  await page.locator(`[role="grid"] tbody tr:has(.matrix-row-name) [data-grid-col="${column}"]`).first().click();
  const dialog = page.getByRole("dialog", { name: `Delivery Methods · ${code}` });
  await dialog.waitFor();
  return dialog;
}

/**
 * Base 0.8 B4 SC-09 hierarchy half, on the harness seed. Under System 00: Lab group › Chemistry ›
 * Electrolytes (the nested system group, holding Sodium) and Lab group › Haematology, beside Boat.
 * Under Domain 00's codelists: Codelist Alpha › Courier › Same day (a nested master value) and
 * Codelist Beta › Pickup point. Everything goes through the real API.
 */
export async function seedHierarchy(api, records) {
  const create = (applicationKey, objectTypeKey, name, parent, attributes) =>
    api("/objects", {
      applicationKey,
      workspaceKey: "default",
      objectTypeKey,
      name,
      parentObjectId: parent.id,
      attributes: Object.entries(attributes).map(([attributeTypeKey, value]) => ({ attributeTypeKey, value })),
    });
  const group = (name, parent, code) => create("rdm-systems", "system-group", name, parent, { "group-code": code });
  const master = (name, parent, code) =>
    create("rdm-master", "master-value", name, parent, {
      "master-id": `MV-${code}`,
      "value-code": code,
      "value-name": name,
    });
  const system = records.system[0];
  const lab = await group("Lab group", system, "LAB");
  const chemistry = await group("Chemistry", lab, "CHEM");
  const electrolytes = await group("Electrolytes", chemistry, "ELEC");
  const sodium = await create("rdm-systems", "system-value", "Sodium", electrolytes, {
    "value-code": "NA",
    "value-name": "Sodium",
  });
  const haematology = await group("Haematology", lab, "HAEM");
  const boat = await group("Boat", system, "IMG");
  const codelists = (await api("/objects/codelist?workspaceKey=default&applicationKey=rdm-master&pageSize=20")).items;
  const alpha = codelists.find((item) => item.name === "Codelist Alpha");
  const beta = codelists.find((item) => item.name === "Codelist Beta");
  const courier = await master("Courier", alpha, "COURIER");
  const sameDay = await master("Same day", courier, "SAME");
  const pickup = await master("Pickup point", beta, "PICKUP");
  return { system, lab, chemistry, electrolytes, sodium, haematology, boat, alpha, beta, courier, sameDay, pickup };
}

/**
 * Opens the system hierarchy tree lens with Electrolytes found through the lens search and open in
 * the inspector beside it: its ancestors' branches open, Boat closed.
 */
export async function openSystemHierarchy(page, uiUrl) {
  await page.goto(`${uiUrl}/apps/rdm-systems/views/system-hierarchy?workspaceKey=default`);
  const lens = page.locator(".tree-lens");
  await lens.getByRole("treeitem", { name: /^System 00/ }).waitFor();
  await lens.getByRole("textbox", { name: /^Search / }).fill("Electrolytes");
  await lens.getByRole("treeitem", { name: /^Electrolytes, in / }).click();
  await page.getByRole("heading", { level: 1, name: "Electrolytes" }).waitFor();
  // The matches give way to the tree once the cleared search settles; Chemistry is not a match.
  await lens.getByRole("treeitem", { name: /^Chemistry(,|$)/ }).waitFor();
  await lens.getByRole("treeitem", { name: /^Electrolytes(,|$)/ }).waitFor();
  await page.waitForLoadState("networkidle");
  return lens;
}

/** Opens the move dialog for `name` in the tree lens from the row's actions; returns the dialog. */
export async function openTreeMoveDialog(page, name) {
  const row = page.locator(".tree-lens").getByRole("treeitem", { name: new RegExp(`^${name}(,|$)`) });
  await row.locator(".tree-menu-trigger").first().click();
  await page.getByRole("menuitem", { name: "Move to…" }).click();
  const dialog = page.getByRole("dialog", { name: `Move ${name}` });
  await dialog.getByRole("radio").first().waitFor();
  return dialog;
}

/**
 * Base 0.8 P2b review data on the starter model, through the real API. Live: two master values in
 * Codelist Alpha (RDM Master), two system values under System 00 (RDM Systems) and a mapping between
 * them. Then one change set that makes a change of every kind in both applications: a master value
 * and a system value added with a mapping between them, a master value's name attribute changed, a
 * master value moved to Codelist Beta (a parent change plus a removed and an added parent link), a
 * system value removed, and the live mapping removed. Codes are prefixed so the seed sits beside
 * the other gate data, whose codes are unique per workspace.
 */
export async function seedChangeReview(api, records) {
  const codelists = (await api("/objects/codelist?workspaceKey=default&applicationKey=rdm-master&pageSize=20")).items;
  const alpha = codelists.find((item) => item.name === "Codelist Alpha");
  const beta = codelists.find((item) => item.name === "Codelist Beta");
  const system = records.system[0];
  const attributes = (values) => Object.entries(values).map(([attributeTypeKey, value]) => ({ attributeTypeKey, value }));
  const master = (name, code) => ({
    applicationKey: "rdm-master",
    workspaceKey: "default",
    objectTypeKey: "master-value",
    name,
    parentObjectId: alpha.id,
    attributes: attributes({ "master-id": `RV-${code}`, "value-code": `RV-${code}`, "value-name": name }),
  });
  const systemValue = (name, code) => ({
    applicationKey: "rdm-systems",
    workspaceKey: "default",
    objectTypeKey: "system-value",
    name,
    parentObjectId: system.id,
    attributes: attributes({ "value-code": `RV-SV-${code}`, "value-name": name }),
  });
  const mapping = "system-value-maps-to-master";
  const collect = await api("/objects", master("Click and collect", "COLLECT"));
  const courier = await api("/objects", master("Home courier", "COURIER"));
  const pickup = await api("/objects", systemValue("SV Pickup", "PICKUP"));
  const home = await api("/objects", systemValue("SV Home", "HOME"));
  const liveMapping = await api("/relations", { relationTypeKey: mapping, fromObjectId: home.id, toObjectId: courier.id });

  const changeSet = await api("/workspaces/default/change-sets", { name: "Spring delivery review", source: "currentLive" });
  const claim = async () => ({
    changeSetId: changeSet.id,
    expectedChangeSetVersion: (await api(`/change-sets/${changeSet.id}`)).version,
  });
  const express = await api("/objects", { ...master("Express", "EXPRESS"), ...(await claim()) });
  const svExpress = await api("/objects", { ...systemValue("SV Express", "EXPRESS"), ...(await claim()) });
  const newMapping = await api("/relations", {
    relationTypeKey: mapping,
    fromObjectId: svExpress.id,
    toObjectId: express.id,
    ...(await claim()),
  });
  await api(
    `/objects/master-value/${collect.id}`,
    { ...(await claim()), expectedVersion: collect.version, attributes: attributes({ "value-name": "Collection point" }) },
    "PATCH",
  );
  await api(
    `/objects/master-value/${courier.id}`,
    { ...(await claim()), expectedVersion: courier.version, parentObjectId: beta.id },
    "PATCH",
  );
  let current = await claim();
  await api(
    `/relations/${liveMapping.id}?changeSetId=${changeSet.id}&expectedChangeSetVersion=${current.expectedChangeSetVersion}&expectedVersion=${liveMapping.version}`,
    undefined,
    "DELETE",
  );
  current = await claim();
  await api(
    `/objects/system-value/${pickup.id}?changeSetId=${changeSet.id}&expectedChangeSetVersion=${current.expectedChangeSetVersion}&expectedVersion=${pickup.version}`,
    undefined,
    "DELETE",
  );
  return { changeSet, alpha, beta, system, collect, courier, pickup, home, express, svExpress, liveMapping, newMapping };
}

/** Opens a change set's review, records first unless `query` says otherwise; waits for its rows. */
export async function openChangeReview(page, uiUrl, changeSet, query = "") {
  await page.goto(
    `${uiUrl}/apps/rdm-master/change-sets/${changeSet.id}/changes?workspaceKey=default${query ? `&${query}` : ""}`,
  );
  await page.getByRole("heading", { level: 1, name: "Review changes" }).waitFor();
  await page.locator(".change-row").first().waitFor();
  await page.waitForLoadState("networkidle");
}

/** Expands the named row of an open change set review; returns its before/after table. */
export async function expandChangeReviewRow(page, name) {
  await page.getByRole("button", { name: `Details of ${name}` }).click();
  const table = page.getByRole("table", { name: `Changes to ${name}` });
  await table.waitFor();
  return table;
}

/**
 * Holds a drag in the open system hierarchy (Base 0.8 B5): `name`'s row pressed and resting on
 * Chemistry, which is open already, so no branch opens under the pointer while a gate captures it.
 * Haematology is accepted there; Lab group, Chemistry's parent, is refused as inside the record.
 * End it with `cancelDrag` from `helpers/tree.mjs`.
 */
export async function holdTreeDrag(page, name) {
  const lens = page.locator(".tree-lens");
  const item = (label) => lens.getByRole("treeitem", { name: new RegExp(`^${label}(,|$)`) }).first();
  await dragFrom(page, item(name));
  await dragOver(page, item("Chemistry"));
  await page.locator(".tree-drag-preview.accepted, .tree-drag-preview.refused").waitFor();
}
