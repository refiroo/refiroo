import { describe, expect, it } from "vitest";
import type { ActionGroup, Grant, UserRole } from "@/types";
import { grantHeld, grantSentence, staleNote, userRoleLine } from "./securityText";

const group = (
  key: string,
  name: string,
  grantableAt: ActionGroup["grantableAt"],
  narrowable = false,
): ActionGroup => ({
  key,
  name,
  description: "",
  grantableAt,
  narrowable,
});

const CATALOGUE = [
  group("browse", "Browse", "workspace"),
  group("edit-live", "Edit live", "workspace", true),
  group("change-sets", "Work in change sets", "workspace", true),
  group("model-authoring", "Model authoring", "instance"),
  group("model-release", "Model release", "workspace"),
  group("security-admin", "Security administration", "instance"),
];

const role = (name: string, instance: boolean, ...labels: string[]): UserRole => ({
  key: name.toLowerCase(),
  name,
  instance,
  workspaces: labels.map((label) => ({ key: label.toLowerCase(), label })),
});

describe("userRoleLine (D298)", () => {
  it("names each role with where it applies, an instance role alone", () => {
    expect(userRoleLine([role("Data steward", false, "Herbarium"), role("Reader", false, "Field stations")])).toBe(
      "Data steward · Herbarium; Reader · Field stations",
    );
    expect(userRoleLine([role("Security administrator", true)])).toBe("Security administrator");
    expect(userRoleLine([role("Data owner", false, "Herbarium", "Field stations")])).toBe(
      "Data owner · Herbarium, Field stations",
    );
  });

  it("counts many workspaces and many roles, and says when there are none", () => {
    expect(userRoleLine([role("Reader", false, "A", "B", "C")])).toBe("Reader · 3 workspaces");
    expect(userRoleLine([role("Reader", false, "A"), role("Operator", true), role("Contributor", false, "B")])).toBe(
      "Reader · A; Operator; and 1 more",
    );
    expect(userRoleLine([])).toBe("No roles yet");
  });
});

describe("grantSentence", () => {
  it("says what a narrowed workspace grant allows", () => {
    expect(
      grantSentence({
        who: "Jonah",
        groups: ["browse", "change-sets"],
        catalogue: CATALOGUE,
        where: "Herbarium",
        narrowedTo: ["Collections", "Determination"],
      }),
    ).toBe(
      "Jonah will read everything and change records in change sets in Herbarium, changing only Collections and Determination.",
    );
  });

  it("names the groups a workspace grant leaves out because they are held only at the instance (D302)", () => {
    expect(
      grantSentence({
        who: "Tomás",
        groups: ["model-authoring", "model-release"],
        catalogue: CATALOGUE,
        where: "Herbarium",
        narrowedTo: [],
      }),
    ).toBe(
      "Tomás will install, activate and migrate model releases in Herbarium. Model authoring is held only for the whole instance, so this grant does not give it.",
    );
  });

  it("covers every workspace at the instance and warns of writes without reading", () => {
    expect(grantSentence({ who: "Mei", groups: ["security-admin"], catalogue: CATALOGUE, narrowedTo: [] })).toBe(
      "Mei will manage people, groups, roles and clients across the whole instance.",
    );
    expect(
      grantSentence({ who: "Ana", groups: ["edit-live"], catalogue: CATALOGUE, where: "Herbarium", narrowedTo: [] }),
    ).toBe("Ana will change records live in Herbarium. Without Browse they cannot read the records they change.");
  });
});

describe("a consumer API grant (Z3, D306)", () => {
  const consumer = (name: string | null): Grant => ({
    id: "g1",
    principal: { kind: "client", id: "c1", name: "Catalogue sync" },
    role: null,
    consumerApi: { key: "catalogue", name },
    scope: {
      instance: false,
      workspaceKey: "herbarium",
      applications: [],
      recordTypes: [],
      applicationNames: [],
      recordTypeNames: [],
    },
    stale: name === null,
    createdAt: "2026-10-24T09:00:00Z",
  });

  it("is named by its API, and by its key once the model no longer declares it", () => {
    expect(grantHeld(consumer("Catalogue"))).toBe("Consumer API: Catalogue");
    expect(staleNote(consumer("Catalogue"))).toBe("");
    expect(grantHeld(consumer(null))).toBe("Consumer API: catalogue");
    expect(staleNote(consumer(null))).toBe(
      "Stale: consumer API “catalogue” is no longer in this workspace’s model, and allows nothing.",
    );
  });
});
