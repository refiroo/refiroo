import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ai } from "@/api/aiClient";
import { AiPage } from "@/features/settings/AiPage";
import { navigationFor } from "@/features/settings/navigation";
import type { AiCall, AiStatus } from "@/types";

vi.mock("@/api/aiClient", () => ({ ai: { status: vi.fn(), calls: vi.fn(), test: vi.fn() } }));

const off: AiStatus = {
  configured: false,
  assistant: false,
  provider: null,
  model: null,
  endpoint: null,
  keySet: false,
  sendLevel: "structure",
  sampleValues: 5,
  minConfidence: 0.6,
  logContent: false,
  logContentDays: 7,
  timeoutSeconds: 30,
  features: [],
  lastCall: null,
  totals: { days: 30, calls: 0, failed: 0, tokensIn: 0, tokensOut: 0, bytesIn: 0, bytesOut: 0, costUsd: 0 },
};
const on: AiStatus = {
  ...off,
  assistant: false,
  configured: true,
  provider: "anthropic",
  model: "claude-test",
  keySet: true,
  sendLevel: "samples",
  sampleValues: 5,
  logContent: true,
  logContentDays: 7,
  features: [
    {
      purpose: "mappingTarget",
      name: "Targets for the unmapped values of a mapping view",
      needs: "values",
      available: true,
    },
  ],
  totals: { days: 30, calls: 2, failed: 1, tokensIn: 1200, tokensOut: 300, bytesIn: 1, bytesOut: 1, costUsd: 1.26 },
};

const call = (overrides: Partial<AiCall>): AiCall => ({
  id: "c1",
  purpose: "connectionTest",
  provider: "anthropic",
  model: "claude-test",
  sendLevel: "samples",
  promptVersion: "1",
  requestedBy: { kind: "user", id: "u1", name: "Ada" },
  jobId: null,
  startedAt: "2026-10-27T10:00:00Z",
  durationMs: 420,
  bytesIn: 10,
  bytesOut: 10,
  tokensIn: 12,
  tokensOut: 3,
  costUsd: null,
  taskId: null,
  outcome: "answered",
  failureKind: null,
  failure: null,
  content: null,
  ...overrides,
});

function open(status: AiStatus, items: AiCall[] = []) {
  vi.mocked(ai.status).mockResolvedValue(status);
  vi.mocked(ai.calls).mockResolvedValue({ items, nextCursor: null } as never);
  render(<AiPage />);
}

describe("Settings › AI (0.16 AP1)", () => {
  beforeEach(() => vi.resetAllMocks());

  it("with neither switch set, says nothing is sent and names both settings", async () => {
    open(off);
    await screen.findByText("Neither the assistant nor an AI provider is set up");
    expect(screen.getByText("AI_AGENT_COMMAND")).toBeTruthy();
    expect(screen.getByText("AI_PROVIDER")).toBeTruthy();
    expect(screen.getByText(/no AI action is offered/)).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Send a test request" })).toBeNull();
    expect(ai.calls).not.toHaveBeenCalled();
  });

  it("with only the assistant on, shows it on and the provider not set, and the calls (AP-D38)", async () => {
    open({ ...off, assistant: true, sendLevel: "values" }, [
      call({ id: "s", purpose: "assistantSession", costUsd: 0.86, taskId: "t1" }),
    ]);
    const assistant = (await screen.findByText("Assistant")).closest("div")!;
    expect(within(assistant).getByText(/On/)).toBeTruthy();
    expect(within(assistant).getByText("AI_AGENT_COMMAND")).toBeTruthy();
    expect(within(assistant).getByText(/Reads workbooks and words, up to a change set/)).toBeTruthy();
    const provider = screen.getByText("Provider").closest("div")!;
    expect(within(provider).getByText(/Not set/)).toBeTruthy();
    expect(within(provider).getByText(/Mapping targets, search and summaries are not offered/)).toBeTruthy();
    expect(screen.queryByText("Neither the assistant nor an AI provider is set up")).toBeNull();
    expect(screen.queryByRole("button", { name: "Send a test request" })).toBeNull();
    const row = (await screen.findAllByRole("row")).find((r) => within(r).queryByText("Assistant session"))!;
    expect(within(row).getByText("$0.86")).toBeTruthy();
  });

  it("with only the provider set, shows the assistant not set and the provider's settings", async () => {
    open(on);
    const assistant = (await screen.findByText("Assistant")).closest("div")!;
    expect(within(assistant).getByText(/Not set/)).toBeTruthy();
    expect(within(assistant).getByText(/is not offered/)).toBeTruthy();
    expect(screen.getByText("claude-test", { selector: "dd" })).toBeTruthy();
  });

  it("shows the settings, the features and the calls, with the content on demand", async () => {
    open(on, [
      call({ id: "a" }),
      call({
        id: "b",
        purpose: "mappingTarget",
        outcome: "failed",
        failureKind: "unreachable",
        failure: "The provider could not be reached.",
        content: { instructions: "give names", context: {}, answer: null },
      }),
    ]);
    await screen.findByText("Also up to 5 values per column");
    expect(screen.getByText("claude-test", { selector: "dd" })).toBeTruthy();
    expect(screen.getByText("Set", { selector: "dd" })).toBeTruthy();
    expect(screen.getByText("60%")).toBeTruthy();
    expect(screen.getByText("For 7 days")).toBeTruthy();
    expect(screen.getByText("Available")).toBeTruthy();
    const rows = await screen.findAllByRole("row");
    const failed = rows.find((row) => within(row).queryByText("Targets for unmapped values"))!;
    expect(within(failed).getByText("Failed")).toBeTruthy();
    expect(within(failed).getByText("The provider could not be reached.")).toBeTruthy();
    expect(within(failed).getByText("Show what was sent and answered")).toBeTruthy();
    expect(screen.getByText(/1,200 tokens in, 300 out/)).toBeTruthy();
  });

  it("lists an assistant session's turn with its cost, and the cost in the totals (0.16 AP9)", async () => {
    open(on, [
      call({ id: "s", purpose: "assistantSession", costUsd: 0.86, taskId: "t1", tokensIn: 230, tokensOut: 40 }),
    ]);
    const row = (await screen.findAllByRole("row")).find((r) => within(r).queryByText("Assistant session"))!;
    expect(within(row).getByText("$0.86")).toBeTruthy();
    expect(screen.getByText(/1,200 tokens in, 300 out; \$1.26/)).toBeTruthy();
  });

  it("sends a test request and says it was answered, then reads the list again", async () => {
    open(on);
    vi.mocked(ai.test).mockResolvedValue(call({ durationMs: 321 }));
    fireEvent.click(await screen.findByRole("button", { name: "Send a test request" }));
    await screen.findByText("Answered in 321 ms by claude-test.");
    await waitFor(() => expect(ai.calls).toHaveBeenCalledTimes(2));
  });

  it("says what failed when the test request fails", async () => {
    open(on);
    vi.mocked(ai.test).mockResolvedValue(
      call({ outcome: "failed", failureKind: "unauthorized", failure: "The provider refused the key." }),
    );
    fireEvent.click(await screen.findByRole("button", { name: "Send a test request" }));
    await screen.findByText("The provider refused the key.", { selector: "[role=alert] *, p, div" });
  });

  it("is listed under Administration only to those who may follow operations", () => {
    const labels = (keys: string[]) =>
      navigationFor(keys.map((key) => ({ key })))
        .flatMap((group) => group.pages)
        .map((item) => item.label);
    expect(labels(["operations"])).toContain("AI");
    expect(labels(["browse"])).not.toContain("AI");
  });
});
