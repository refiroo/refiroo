import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { Explorer } from "@/features/objects/Explorer";
import * as workspaceContext from "@/features/workspaces/WorkspaceDataContext";
import { permissionsFixture } from "@/test/permissions";
import { testModel } from "@/test/fixtures";
import type { EngineModel } from "@/types";

const NAMES = [
  "Eye colours",
  "Hair colours",
  "Skin colours",
  "Languages",
  "Countries",
  "Regions",
  "Documents",
  "Visit reasons",
  "Stations",
  "Funding streams",
  "Tariff sources",
  "Timetable types",
];
const stored = new Map<string, string>();

beforeEach(() => {
  stored.clear();
  vi.spyOn(workspaceContext, "useWorkspaceData").mockReturnValue({
    api,
    warning: "",
    permissions: permissionsFixture("west"),
  });
  vi.spyOn(api, "objects").mockResolvedValue({ items: [], nextCursor: null, totalCount: 0, startIndex: 0 });
  vi.stubGlobal("localStorage", {
    getItem: (key: string) => stored.get(key) ?? null,
    setItem: (key: string, value: string) => stored.set(key, value),
  });
});
afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

/** An application listing `NAMES.length` types: the first six in two groups, the last two ungrouped. */
function bigModel(count = NAMES.length): EngineModel {
  const model = structuredClone(testModel);
  const base = model.objectTypes[0];
  const names = NAMES.slice(0, count);
  model.objectTypes = names.map((name, index) => ({ ...base, key: `t${index}`, name, pluralName: name }));
  const view = model.applications[0].views[0];
  if (view.type !== "table") throw new Error("Expected table fixture");
  const application = model.applications[0];
  application.objectTypeKeys = names.map((_, index) => `t${index}`);
  application.views = names.map((name, index) => ({ ...view, key: `v${index}`, name, objectTypeKey: `t${index}` }));
  application.defaultView = "v0";
  application.navigation = {
    groups: [
      { key: "traits", label: "Physical traits", collections: ["t0", "t1", "t2"] },
      { key: "places", label: "Places", collections: ["t3", "t4", "t5"], collapsed: true },
    ],
  };
  model.placements = { applications: [] };
  return model;
}

function sidebar(model: EngineModel, onOpenCollection = vi.fn()) {
  render(
    <Explorer
      model={model}
      application={model.applications[0]}
      workspaceKey="west"
      refreshToken={0}
      onOpen={vi.fn()}
      onOpenCollection={onOpenCollection}
    />,
  );
  return onOpenCollection;
}
const collections = () => screen.getByRole("navigation", { name: "Test App collections" });
const entries = () =>
  within(collections())
    .getAllByRole("button")
    .map((button) => button.textContent);

describe("Find a list in the sidebar (0.13 LB)", () => {
  it("is offered only when the application has more than ten entries", () => {
    sidebar(bigModel(10));
    expect(screen.queryByRole("textbox", { name: "Find a list" })).not.toBeInTheDocument();
  });

  it("narrows every group and the ungrouped entries to the matches, with the matched text in bold", () => {
    sidebar(bigModel());
    const find = screen.getByRole("textbox", { name: "Find a list" });
    expect(within(collections()).getByRole("status")).toHaveTextContent("12 lists");
    fireEvent.change(find, { target: { value: "COLO" } });

    expect(within(collections()).getByRole("status")).toHaveTextContent("3 of 12");
    // The group the reader folded or not, and every group without a match, does not matter: matches show.
    expect(entries()).toEqual(["Physical traits", "Eye colours", "Hair colours", "Skin colours"]);
    const eye = within(collections()).getByRole("button", { name: "Eye colours" });
    expect(Array.from(eye.querySelectorAll("b")).map((bold) => bold.textContent)).toEqual(["colo"]);

    fireEvent.change(find, { target: { value: "ref" } });
    expect(entries()).toEqual(["Tariff sources"]);
    fireEvent.change(find, { target: { value: "nothing like it" } });
    expect(within(collections()).getByRole("status")).toHaveTextContent("0 of 12");
    expect(screen.getByText("No list matches")).toBeVisible();
  });

  it("shows a group that has a match open, whatever its fold, and keeps the reader's folds", () => {
    sidebar(bigModel());
    const find = screen.getByRole("textbox", { name: "Find a list" });
    // Places is folded by the model; the reader opens it and folds Physical traits.
    fireEvent.click(within(collections()).getByRole("button", { name: "Show Places" }));
    fireEvent.click(within(collections()).getByRole("button", { name: "Hide Physical traits" }));
    const folds = stored.get('rdm:navigation-groups:v1:"test-app"');
    expect(JSON.parse(folds ?? "{}")).toEqual({ places: false, traits: true });

    fireEvent.change(find, { target: { value: "colo" } });
    expect(within(collections()).getByRole("button", { name: "Eye colours" })).toBeVisible();
    expect(within(collections()).queryByRole("button", { name: /Places/ })).not.toBeInTheDocument();
    expect(stored.get('rdm:navigation-groups:v1:"test-app"')).toBe(folds);

    fireEvent.change(find, { target: { value: "" } });
    expect(within(collections()).getByRole("button", { name: "Show Physical traits" })).toHaveAttribute(
      "aria-expanded",
      "false",
    );
    expect(within(collections()).getByRole("button", { name: "Hide Places" })).toHaveAttribute("aria-expanded", "true");
    expect(stored.get('rdm:navigation-groups:v1:"test-app"')).toBe(folds);
  });

  it("opens the first match on Enter and clears on Escape", () => {
    const onOpenCollection = sidebar(bigModel());
    const find = screen.getByRole("textbox", { name: "Find a list" });
    fireEvent.change(find, { target: { value: "s" } });
    fireEvent.change(find, { target: { value: "colo" } });
    fireEvent.keyDown(find, { key: "Enter" });
    expect(onOpenCollection).toHaveBeenCalledWith("v0");

    fireEvent.keyDown(find, { key: "Escape" });
    expect(find).toHaveValue("");
    expect(entries()).toContain("Stations");
  });

  it("lists a typed name in the ungrouped entries too", () => {
    const model = bigModel();
    sidebar(model);
    fireEvent.change(screen.getByRole("textbox", { name: "Find a list" }), { target: { value: "clin" } });
    expect(entries()).toEqual(["Stations"]);
  });
});
