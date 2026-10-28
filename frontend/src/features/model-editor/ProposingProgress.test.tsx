import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { assistantOutcomeText, phaseText, ProposingProgress } from "@/features/model-editor/ProposingProgress";

vi.mock("@/api/client", async (load) => {
  const actual = await load<typeof import("@/api/client")>();
  return { ...actual, api: Object.fromEntries(Object.keys(actual.api).map((key) => [key, vi.fn()])) };
});

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.system).mockResolvedValue({ ai: { configured: true, provider: "ollama", model: "qwen3:8b" } } as never);
});

describe("the editor while the engine proposes", () => {
  it("names each phase in plain words", () => {
    expect(phaseText("profiling")).toBe("Reading the workbook…");
    expect(phaseText("reading")).toBe("Finding the model in every sheet…");
    expect(phaseText("applying")).toBe("Applying the proposals, one step each…");
    expect(phaseText("assistant", "qwen3:8b")).toBe(
      "Asking the AI assistant (qwen3:8b) for clearer names. A model run on your own machine can take a few minutes.",
    );
    expect(phaseText("assistant", null)).toMatch(/^Asking the AI assistant for clearer names\./);
  });

  it("says editing is paused and stops the run on Stop", async () => {
    const onStop = vi.fn();
    render(<ProposingProgress phase="assistant" onStop={onStop} />);
    expect(await screen.findByText(/Asking the AI assistant \(qwen3:8b\)/)).toBeTruthy();
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

describe("what the AI assistant did", () => {
  it("tells the clearer names it offered", () => {
    expect(assistantOutcomeText({ model: "fake-1", suggested: 4, offered: 4, failure: null })?.text).toBe(
      "The AI assistant (fake-1) suggested 4 clearer names.",
    );
  });
  it("tells what was left out", () => {
    expect(assistantOutcomeText({ model: "fake-1", suggested: 5, offered: 3, failure: null })?.text).toBe(
      "The AI assistant (fake-1) suggested 3 clearer names; 2 were left out (below the confidence floor or the same name).",
    );
  });
  it("tells the names were good as they are", () => {
    expect(assistantOutcomeText({ model: "fake-1", suggested: 0, offered: 0, failure: null })?.text).toBe(
      "The AI assistant (fake-1) found the names good as they are.",
    );
  });
  it("keeps a failure visible and says nothing when the assistant was not asked", () => {
    expect(assistantOutcomeText({ model: null, suggested: 0, offered: 0, failure: "timed out" })).toEqual({
      tone: "warning",
      text: "The AI assistant could not help: timed out",
    });
    expect(assistantOutcomeText(undefined)).toBeUndefined();
  });
});
