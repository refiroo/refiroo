import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { ProposeDialog } from "@/features/model-editor/ProposeDialog";
import { heldAnywhereFixture } from "@/test/permissions";
import type { AiSystemInfo, SystemResponse } from "@/types";

vi.mock("@/api/client", async (load) => {
  const actual = await load<typeof import("@/api/client")>();
  return { ...actual, api: Object.fromEntries(Object.keys(actual.api).map((key) => [key, vi.fn()])) };
});

function open(aiInfo: AiSystemInfo, groups: string[]) {
  vi.mocked(api.system).mockResolvedValue({ ai: aiInfo } as SystemResponse);
  vi.mocked(api.myActionGroups).mockResolvedValue(heldAnywhereFixture(groups));
  const onPropose = vi.fn();
  render(<ProposeDialog fileName="items.xlsx" onPropose={onPropose} onClose={() => undefined} />);
  return onPropose;
}

const label = "Also ask the AI assistant for clearer names";

describe("Propose again › the AI assistant (0.16 AP1)", () => {
  beforeEach(() => vi.resetAllMocks());

  it("offers it, checked, to a person who holds ai-proposals when a provider is set, and sends the choice", async () => {
    const onPropose = open({ configured: true, provider: "anthropic", sendLevel: "structure" }, ["ai-proposals"]);
    const box = await screen.findByLabelText(label);
    expect((box as HTMLInputElement).checked).toBe(true);
    expect(screen.getByText("Sends the sheets' names and headers to anthropic")).toBeTruthy();
    fireEvent.click(box);
    fireEvent.click(screen.getByRole("button", { name: "Propose" }));
    expect(onPropose).toHaveBeenCalledWith(expect.objectContaining({ assistant: false }));
  });

  it("says first rows are sent at the samples level, and sends true by default", async () => {
    const onPropose = open({ configured: true, provider: "anthropic", sendLevel: "samples" }, ["ai-proposals"]);
    await screen.findByText("Sends the sheets' names, headers and first rows to anthropic");
    fireEvent.click(screen.getByRole("button", { name: "Propose" }));
    expect(onPropose).toHaveBeenCalledWith(expect.objectContaining({ assistant: true }));
  });

  it.each([
    ["no provider is set", { configured: false, provider: null, sendLevel: "structure" as const }, ["ai-proposals"]],
    [
      "the person lacks the group",
      { configured: true, provider: "anthropic", sendLevel: "structure" as const },
      ["browse"],
    ],
  ])("renders no checkbox and sends no assistant when %s", async (_name, info, groups) => {
    const onPropose = open(info, groups);
    await vi.waitFor(() => expect(api.myActionGroups).toHaveBeenCalled());
    await vi.waitFor(() => expect(api.system).toHaveBeenCalled());
    await new Promise((done) => setTimeout(done, 20));
    expect(screen.queryByLabelText(label)).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Propose" }));
    expect(onPropose.mock.calls[0][0]).not.toHaveProperty("assistant");
  });
});
