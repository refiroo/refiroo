import { describe, expect, it } from "vitest";
import { possibleTypes } from "@/model/placements";
import { parentTypeOf, placeTypes, restructuringChoices, typeNames } from "@/model/restructuring";
import { applicationPlacements, starterModel } from "@/test/placements";
import type { ApplicationDefinition, EngineModel, ObjectItem, TreeViewDefinition } from "@/types";
const application = (model: EngineModel, key: string) =>
  model.applications.find((candidate) => candidate.key === key) as ApplicationDefinition;
const tree = (app: ApplicationDefinition) => {
  const view = app.views.find((candidate) => candidate.type === "tree") as TreeViewDefinition;
  return { nodeTypes: new Set(view.config.objectTypeKeys), rootTypes: view.config.rootObjectTypeKeys };
};

type Placed = Pick<ObjectItem, "objectTypeKey" | "path">;
/** A record of `objectTypeKey` under records of the `ancestors` types, outermost first. */
function placed(objectTypeKey: string, ...ancestors: string[]): Placed {
  return {
    objectTypeKey,
    path: [...ancestors, objectTypeKey].map((key, index) => ({ id: `${index}`, name: key, objectTypeKey: key })),
  };
}

const master = application(starterModel, "rdm-master");
const systems = application(starterModel, "rdm-systems");

describe("possibleTypes", () => {
  it("reads the served placements: the types at the top, and those a parent's type can hold", () => {
    expect(possibleTypes(starterModel, master, null)).toEqual(["domain"]);
    expect(possibleTypes(starterModel, master, "domain")).toEqual(["codelist"]);
    expect(possibleTypes(starterModel, master, "master-value")).toEqual(["master-value"]);
    expect(possibleTypes(starterModel, systems, "system-group")).toEqual(["system-group", "system-value"]);
    expect(possibleTypes(starterModel, systems, null)).toEqual(["system"]);
  });

  it("offers no place for a model loaded without placements", () => {
    const bare: EngineModel = { ...starterModel, placements: undefined };
    expect(possibleTypes(bare, master, null)).toEqual([]);
    expect(possibleTypes(bare, master, "domain")).toEqual([]);
  });
});

describe("placeTypes", () => {
  it("keeps the types the tree shows at the place: its root types at the top", () => {
    // A model where codelists may also stand at the top.
    const model: EngineModel = {
      ...starterModel,
      placements: {
        applications: [
          applicationPlacements("rdm-master", ["domain", "codelist"], {
            domain: ["codelist"],
            codelist: ["master-value"],
            "master-value": ["master-value"],
          }),
        ],
      },
    };
    expect(possibleTypes(model, master, null)).toEqual(["domain", "codelist"]);
    expect(placeTypes(model, master, tree(master), null)).toEqual(["domain"]);
    expect(placeTypes(model, master, { ...tree(master), nodeTypes: new Set(["domain"]) }, "domain")).toEqual([]);
  });
});

describe("restructuringChoices", () => {
  it("offers what the domain hierarchy makes possible: levels, no other type in place", () => {
    const codelist = restructuringChoices(starterModel, master, tree(master), placed("codelist", "domain"));
    expect(codelist).toEqual({ changeType: [], insertLevel: ["codelist"], removeLevel: true, changeTypeUnder: [] });
    const value = restructuringChoices(
      starterModel,
      master,
      tree(master),
      placed("master-value", "domain", "codelist"),
    );
    expect(value.insertLevel).toEqual(["master-value"]);
    expect(value.removeLevel).toBe(true);
    const domain = restructuringChoices(starterModel, master, tree(master), placed("domain"));
    expect(domain.changeType).toEqual([]);
    expect(domain.insertLevel).toEqual(["domain"]);
  });

  it("offers type changes where the system hierarchy holds two types at a place", () => {
    const value = restructuringChoices(
      starterModel,
      systems,
      tree(systems),
      placed("system-value", "system", "system-group"),
    );
    expect(value.changeType).toEqual(["system-group"]);
    expect(value.removeLevel).toBe(false);
    const system = restructuringChoices(starterModel, systems, tree(systems), placed("system"));
    expect(system.changeTypeUnder).toEqual([
      { fromObjectTypeKey: "system-group", objectTypeKeys: ["system-value"] },
      { fromObjectTypeKey: "system-value", objectTypeKeys: ["system-group"] },
    ]);
    expect(system.changeType).toEqual([]);
  });
});

describe("helpers", () => {
  it("names types as a sentence and reads the parent's type from the path", () => {
    expect(typeNames(starterModel, ["domain"])).toBe("Domain");
    expect(typeNames(starterModel, ["system-group", "system-value"])).toBe("System group or System value");
    expect(typeNames(starterModel, ["domain", "codelist", "master-value"])).toBe("Domain, Codelist or Master value");
    expect(parentTypeOf(placed("codelist", "domain"))).toBe("domain");
    expect(parentTypeOf(placed("domain"))).toBeNull();
  });
});
