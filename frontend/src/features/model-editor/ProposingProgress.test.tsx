import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { phaseText, ProposingProgress } from "@/features/model-editor/ProposingProgress";

describe("the editor while the engine proposes", () => {
  it("names each phase in plain words", () => {
    expect(phaseText("profiling")).toBe("Reading the workbook…");
    expect(phaseText("reading")).toBe("Finding the model in every sheet…");
    expect(phaseText("applying")).toBe("Applying the proposals, one step each…");
  });

  it("says editing is paused and stops the run on Stop", async () => {
    const onStop = vi.fn();
    render(<ProposingProgress phase="reading" onStop={onStop} />);
    expect(await screen.findByText("Finding the model in every sheet…")).toBeTruthy();
    expect(
      screen.getByText("Editing is paused until the proposals are applied, so nothing you change is lost."),
    ).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Stop" }));
    expect(onStop).toHaveBeenCalledTimes(1);
  });

  it("offers no Stop while the proposals are being applied", () => {
    render(<ProposingProgress phase="applying" onStop={vi.fn()} />);
    expect(screen.getByText("Applying the proposals, one step each…")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Stop" })).toBeNull();
  });
});
