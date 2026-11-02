// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { testModel } from "@/test/fixtures";
import type { Grant, HeldAnywhere, OwnWorkspace } from "@/types";
import { continueAddressFor, continueLines, readContinueAddress, rememberContinueAddress } from "./continueAddress";
import { greeting, quietNote, rolePills, roleLine, summary, tileLetters, workspaceHue } from "./homeText";

const application = testModel.applications[0];

function workspace(key: string, label: string, own: number, open: number | null): OwnWorkspace {
  return {
    key,
    label,
    isDefault: key === "default",
    model: {
      releaseId: "r",
      releaseKey: "k",
      releaseName: "Model",
      releaseVersion: "1.0.0",
      schemaVersion: "1",
      modelHash: "h",
      version: 1,
      updatedAt: "",
    },
    applications: [],
    ownChangeSets: own,
    openChangeSets: open,
    following: false,
  };
}

function grant(role: string, scope: { instance?: boolean; workspaceKey?: string }): Grant {
  return {
    id: `${role}-${scope.workspaceKey ?? "instance"}`,
    principal: { kind: "user", id: "p", name: "P" },
    role: { key: role.toLowerCase(), name: role } as Grant["role"],
    scope: {
      instance: Boolean(scope.instance),
      workspaceKey: scope.workspaceKey ?? null,
      applications: [],
      recordTypes: [],
      applicationNames: [],
      recordTypeNames: [],
    },
    createdAt: "",
  };
}

beforeEach(() => {
  const values = new Map<string, string>();
  vi.stubGlobal("localStorage", {
    getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => values.set(key, value),
    removeItem: (key: string) => values.delete(key),
  });
});
afterEach(() => vi.unstubAllGlobals());

describe("Continue where you left off (D334)", () => {
  it("is kept per person, and another person's or a broken entry is not read", () => {
    const route = {
      kind: "detail" as const,
      applicationKey: application.key,
      objectTypeKey: application.objectTypeKeys[0],
      objectId: "o-1",
      workspaceKey: "north",
    };
    const address = continueAddressFor(testModel, route, "North", "Spring work");
    rememberContinueAddress("ana", address);
    expect(readContinueAddress("ana")).toEqual(address);
    expect(readContinueAddress("ben")).toBeUndefined();
    expect(address.record).toEqual({ objectTypeKey: route.objectTypeKey, objectId: "o-1" });
    window.localStorage.setItem("rdm:home:continue:v1:ana", "{not json");
    expect(readContinueAddress("ana")).toBeUndefined();
    window.localStorage.setItem("rdm:home:continue:v1:ana", JSON.stringify({ path: "/settings/about" }));
    expect(readContinueAddress("ana")).toBeUndefined();
  });

  it("names the record and where it is, or the view", () => {
    const record = continueAddressFor(
      testModel,
      {
        kind: "detail",
        applicationKey: application.key,
        objectTypeKey: application.objectTypeKeys[0],
        objectId: "o-1",
        workspaceKey: "north",
      },
      "North",
      "Spring work",
    );
    const type = testModel.objectTypes.find((item) => item.key === application.objectTypeKeys[0])!.name;
    expect(continueLines(record, "Oak")).toEqual({
      title: "Oak",
      where: `${type} in North, in the change set “Spring work”`,
    });
    expect(continueLines(record).title).toBe(type);
    const list = continueAddressFor(
      testModel,
      {
        kind: "list",
        applicationKey: application.key,
        viewKey: application.defaultView,
        workspaceKey: "north",
        search: "",
        sort: "name",
        pageSize: 50,
        filters: [],
      },
      "North",
    );
    const view = application.views.find((item) => item.key === application.defaultView)!.name;
    expect(continueLines(list)).toEqual({ title: view, where: "North" });
  });
});

describe("What Home says (D337)", () => {
  it("greets by first name and part of the day", () => {
    expect(greeting("Ana Varga", 9)).toBe("Good morning, Ana");
    expect(greeting("Ana Varga", 14)).toBe("Good afternoon, Ana");
    expect(greeting("Ana Varga", 20)).toBe("Good evening, Ana");
  });

  it("sums up the workspaces, the person's change sets and those waiting to be published", () => {
    expect(summary([workspace("a", "A", 0, null)])).toBe(
      "One workspace is open to you. Open an application below, or pick up where you were.",
    );
    expect(summary([workspace("a", "A", 1, 4), workspace("b", "B", 1, 1), workspace("c", "C", 0, null)])).toBe(
      "Three workspaces are open to you. Two of your change sets are open, and five change sets wait for someone to publish them.",
    );
    expect(summary([workspace("a", "A", 0, 1), workspace("b", "B", 0, null)])).toBe(
      "Two workspaces are open to you. One change set waits for someone to publish it.",
    );
  });

  it("names roles per card and as pills; an instance role applies everywhere", () => {
    const cards = [
      workspace("a", "Main", 0, null),
      workspace("b", "Digitisation", 0, null),
      workspace("c", "Field", 0, null),
    ];
    const grants = [
      grant("Data steward", { workspaceKey: "a" }),
      grant("Data steward", { workspaceKey: "b" }),
      grant("Contributor", { workspaceKey: "c" }),
      grant("Reader", { instance: true }),
    ];
    expect(rolePills(grants, cards)).toEqual(["Contributor in Field", "Data steward in 2 workspaces", "Reader"]);
    expect(roleLine(grants, "a")).toBe("Data steward and Reader");
    expect(roleLine([], "a")).toBe("");
  });

  it("gives a tile two letters and a hue that stays", () => {
    expect(tileLetters("Main collection")).toBe("MC");
    expect(tileLetters("Digitisation 2026")).toBe("D2");
    expect(tileLetters("sandbox")).toBe("SA");
    expect(workspaceHue("north")).toBe(workspaceHue("north"));
    expect(workspaceHue("north")).toBeGreaterThanOrEqual(1);
    expect(workspaceHue("north")).toBeLessThanOrEqual(8);
  });

  it("says what a quiet card's role can do", () => {
    const held = (key: string, workspaces: string[]): HeldAnywhere => ({
      key,
      name: key,
      instance: false,
      workspaces: workspaces.map((item) => ({ key: item, label: item })),
    });
    const groups = [held("browse", ["a", "b", "c"]), held("change-sets", ["b"]), held("edit-live", ["c"])];
    expect(quietNote(groups, "a")).toBe("You can read this workspace.");
    expect(quietNote(groups, "b")).toBe("Propose a change from any record.");
    expect(quietNote(groups, "c")).toBeUndefined();
    expect(quietNote(undefined, "a")).toBeUndefined();
  });
});
