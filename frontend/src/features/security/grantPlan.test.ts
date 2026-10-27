import { describe, expect, it } from "vitest";
import type { Grant } from "@/types";
import {
  consumerPlanSentence,
  consumerRequests,
  heldConsumerApis,
  heldRoles,
  roleRequests,
  rolePlanSentence,
} from "./grantPlan";

const client = { kind: "client" as const, id: "c1" };

const grant = (over: Omit<Partial<Grant>, "scope"> & { scope?: Partial<Grant["scope"]> }): Grant =>
  ({
    id: "g",
    principal: { ...client, name: "Test client" },
    role: null,
    consumerApi: null,
    ...over,
    scope: { instance: false, workspaceKey: "default", applications: [], recordTypes: [], ...over.scope },
  }) as Grant;

describe("what a grant dialog's ticks come to (0.12 U9)", () => {
  it("makes a grant per ticked cell and leaves out those already held", () => {
    const held = heldConsumerApis([grant({ consumerApi: { key: "rdm", name: "RDM" } })]);
    const requests = consumerRequests(client, ["rdm|default", "rdm|pilot", "rdm-master|default"], held);
    expect(requests.map((request) => request.scope)).toEqual([{ workspaceKey: "pilot" }, { workspaceKey: "default" }]);
    expect(requests.map((request) => request.consumerApi)).toEqual(["rdm", "rdm-master"]);
  });

  it("grants every role in every workspace, skipping an unnarrowed one already held", () => {
    const held = heldRoles([
      grant({ role: { key: "reader", name: "Reader" }, scope: { workspaceKey: "pilot" } }),
      grant({ role: { key: "editor", name: "Editor" }, scope: { workspaceKey: "pilot", applications: ["a"] } }),
    ]);
    const requests = roleRequests(
      client,
      ["reader", "editor"],
      ["default", "pilot"],
      { applications: [], recordTypes: [] },
      held,
    );
    expect(
      requests.map(
        (request) => `${request.role}@${"workspaceKey" in request.scope ? request.scope.workspaceKey : "*"}`,
      ),
    ).toEqual(["reader@default", "editor@default", "editor@pilot"]);
  });

  it("grants a role at the instance once", () => {
    const held = heldRoles([
      grant({ role: { key: "reader", name: "Reader" }, scope: { instance: true, workspaceKey: null } }),
    ]);
    expect(roleRequests(client, ["reader", "editor"], "instance", { applications: [], recordTypes: [] }, held)).toEqual(
      [{ principal: client, role: "editor", scope: { instance: true } }],
    );
  });

  it("says what will be made in a sentence", () => {
    expect(
      consumerPlanSentence("Test client", [
        { api: "RDM", where: ["default", "pilot"] },
        { api: "Master data", where: ["default"] },
      ]),
    ).toBe(
      "3 grants will be made: Test client reads RDM in default and pilot and Master data in default. It changes nothing and opens nothing on the management API.",
    );
    expect(
      rolePlanSentence({ who: "Anna", roles: ["Reader", "Editor"], where: ["default", "pilot"], count: 3, skipped: 1 }),
    ).toBe(
      "3 grants will be made: Reader and Editor, each in default and pilot. Anna already holds one of them, so it is skipped.",
    );
  });
});
