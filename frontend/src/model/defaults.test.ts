import { describe, expect, it } from "vitest";
import example from "../../../guide/samples/model.json";
import stopPage from "@/model/stop-page.fixture.json";
import { fallbackDetail } from "@/model/defaults";
import type { EngineModel } from "@/types";

const guide = example as unknown as EngineModel;

describe("the page a type gets when its application declares none (0.13 RL)", () => {
  it("is the page the server generates for the stop of the guide's example model", () => {
    // frontend/src/model/stop-page.fixture.json is what `layout.detail_page` writes for it; the server's
    // test fails when it drifts. The undeclared page adds only what the browser draws itself.
    const stop = guide.objectTypes.find((type) => type.key === "stop")!;
    const panels = fallbackDetail(stop, guide).panels.map(({ visible: _visible, ...panel }) => panel);
    const generated = stopPage.panels.map((panel) =>
      panel.type === "hierarchy" ? { ...panel, config: { showParent: true, showAncestors: true } } : panel,
    );
    expect(panels).toEqual(generated);
  });

  it("gives a type without a parent no hierarchy and one relations panel per direction held", () => {
    const operator = guide.objectTypes.find((type) => type.key === "operator")!;
    const keys = fallbackDetail(operator, guide).panels.map((panel) => [panel.key, panel.region]);
    expect(keys).toEqual([
      ["attributes", "side"],
      ["operator-operates-stop", "main"],
      ["object-has-translation", "main"],
    ]);
  });
});
