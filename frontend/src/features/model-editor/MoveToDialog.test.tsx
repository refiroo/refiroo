import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { outlineFixture } from "@/test/draftOutline";
import { MoveToDialog, moveChoices, topOf, typeIn } from "@/features/model-editor/MoveToDialog";
import type { ModelDraftOutline } from "@/types";

/** The fixture's shop, with its bins standing in a second application. */
function twoApplications(): ModelDraftOutline {
  const outline = outlineFixture();
  const shop = outline.applications[0];
  shop.objectTypeKeys = ["area", "shelf"];
  shop.tree = [{ objectType: "area", children: [{ objectType: "shelf", children: [] }] }];
  outline.applications.push({
    key: "depot",
    name: "Depot",
    objectTypeKeys: ["bin"],
    tree: [{ objectType: "bin", children: [] }],
    navigation: { groups: [], ungrouped: ["bin"] },
    mark: "new",
  });
  return outline;
}

async function moveTo(target: string) {
  const run = vi.fn().mockResolvedValue(undefined);
  render(
    <MoveToDialog
      subject={{ kind: "objectType", objectType: "area", application: "shop" }}
      outline={twoApplications()}
      initialTarget={target}
      run={run}
      onClose={() => undefined}
    />,
  );
  fireEvent.click(screen.getByRole("button", { name: /^Move to/ }));
  await waitFor(() => expect(run).toHaveBeenCalled());
  return run.mock.calls[0][0];
}

describe("Move to… a type in another application (found 2026-10-19)", () => {
  it("offers each application's top level and the types standing in it", () => {
    const choices = moveChoices({ kind: "objectType", objectType: "area" }, twoApplications());
    expect(choices.map((choice) => [choice.value, choice.name])).toEqual([
      [topOf("shop"), "Top level of Shop"],
      [typeIn("shop", "shelf"), "Shelf"],
      [topOf("depot"), "Top level of Depot"],
      [typeIn("depot", "bin"), "Bin"],
    ]);
    expect(choices[0].note).toBe("where it is");
  });

  it("moves a top-level type to another application's top by its application alone", async () => {
    expect(await moveTo(topOf("depot"))).toEqual([
      { kind: "setContainment", objectType: "area", application: "depot" },
    ]);
  });

  it("moves a type under a type of another application with its application and parent", async () => {
    expect(await moveTo(typeIn("depot", "bin"))).toEqual([
      {
        kind: "setContainment",
        objectType: "area",
        parent: { objectTypes: ["bin"], relationType: { name: "Contains Area", reverseName: "In Bin" } },
        application: "depot",
      },
    ]);
  });

  it("keeps a move within the application a parent change alone", async () => {
    expect(await moveTo(topOf("shop"))).toEqual([{ kind: "setContainment", objectType: "area", parent: null }]);
  });
});
