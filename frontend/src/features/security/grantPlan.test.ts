import { describe, expect, it } from "vitest";
import type { Grant } from "@/types";
import {
  changeSentence,
  consumerPlanSentence,
  grantCells,
  recreation,
  removals,
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

  it("grants the wanted role cells, skipping those already held, and a role at the instance once", () => {
    const held = heldRoles([
      grant({ role: { key: "reader", name: "Reader" }, scope: { workspaceKey: "pilot" } }),
      grant({ role: { key: "editor", name: "Editor" }, scope: { workspaceKey: "pilot", applications: ["a"] } }),
      grant({ role: { key: "owner", name: "Owner" }, scope: { instance: true, workspaceKey: null } }),
    ]);
    const none = { applications: [], recordTypes: [] };
    const requests = roleRequests(
      client,
      ["reader|default", "reader|pilot", "editor|pilot", "owner|*", "auditor|*"],
      held,
      none,
    );
    expect(requests).toEqual([
      { principal: client, role: "reader", scope: { workspaceKey: "default", applications: [], recordTypes: [] } },
      { principal: client, role: "editor", scope: { workspaceKey: "pilot", applications: [], recordTypes: [] } },
      { principal: client, role: "auditor", scope: { instance: true } },
    ]);
  });

  it("removes the held cells that are shown and no longer wanted, and never a narrowed role grant", () => {
    const cells = grantCells([
      grant({ id: "a1", consumerApi: { key: "rdm", name: "RDM" } }),
      grant({ id: "a2", consumerApi: { key: "rdm", name: "RDM" }, scope: { workspaceKey: "pilot" } }),
      grant({ id: "r1", role: { key: "editor", name: "Editor" }, scope: { applications: ["a"] } }),
    ]);
    expect(cells.roles.size).toBe(0);
    const shown = new Set(["rdm|default", "rdm|pilot"]);
    expect(removals(cells.apis, new Set(["rdm|default"]), shown).map((item) => item.id)).toEqual(["a2"]);
    // A held cell the grid does not show (the model no longer declares it) is not removed by unticking.
    expect(removals(cells.apis, new Set(), new Set(["rdm|default"])).map((item) => item.id)).toEqual(["a1"]);
  });

  it("makes a removed grant again in the same place with the same narrowing", () => {
    expect(
      recreation(
        grant({ role: { key: "editor", name: "Editor" }, scope: { workspaceKey: "pilot", applications: ["a"] } }),
      ),
    ).toEqual({
      principal: client,
      role: "editor",
      scope: { workspaceKey: "pilot", applications: ["a"] },
    });
    expect(recreation(grant({ consumerApi: { key: "rdm", name: "RDM" } }))).toEqual({
      principal: client,
      consumerApi: "rdm",
      scope: { workspaceKey: "default" },
    });
  });

  it("says what is added and what is removed", () => {
    expect(
      changeSentence({
        who: "client 1",
        verb: "read",
        added: ["RDM API in default"],
        removed: ["RDM Master API in another"],
      }),
    ).toBe("client 1 will read RDM API in default; RDM Master API in another is removed.");
    expect(changeSentence({ who: "client 1", verb: "read", added: [], removed: ["RDM API in default"] })).toBe(
      "client 1 will no longer read RDM API in default.",
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
