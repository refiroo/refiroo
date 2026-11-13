import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ai } from "@/api/aiClient";
import { WhatChanged } from "@/ui/WhatChanged";
import type { HistoryAccount, HistoryFact } from "@/types";

const offer = vi.hoisted(() => ({ value: undefined as unknown }));
vi.mock("@/state/useWorkspaceAiOffer", () => ({ useHistoryAccountOffer: () => offer.value }));
vi.mock("@/api/aiClient", () => ({ ai: { explainWorkspaceHistory: vi.fn(), explainRecordHistory: vi.fn() } }));

const fact = (n: number, link: HistoryFact["link"] = null): HistoryFact => ({
  id: `rc-${n}`,
  kind: "records",
  text: `Fact number ${n}`,
  count: n,
  keys: {},
  link,
});
const changes: HistoryFact["link"] = {
  kind: "changes",
  id: null,
  query: { kind: ["record"], objectTypeKey: "ledger", live: true },
};
const account = (extra: Partial<HistoryAccount> = {}): HistoryAccount => ({
  scope: "workspace",
  since: "2026-10-25T00:00:00Z",
  until: "2026-11-01T12:00:00Z",
  timeZone: "UTC",
  facts: [fact(1, changes), fact(2, { kind: "job", id: "job-1", query: null }), fact(3)],
  statements: [{ text: "Two things changed.", factIds: ["rc-1", "rc-3"] }],
  removedStatements: 0,
  failure: null,
  cached: false,
  callId: "call-1",
  ...extra,
});

const mounted = (props: Partial<Parameters<typeof WhatChanged>[0]> = {}) =>
  render(<WhatChanged workspaceKey="north" application="shop" onShow={vi.fn()} onNavigate={vi.fn()} {...props} />);

describe("WhatChanged (0.16 AO2)", () => {
  beforeEach(() => {
    vi.mocked(ai.explainWorkspaceHistory).mockReset();
    vi.mocked(ai.explainRecordHistory).mockReset();
    offer.value = { configured: true, provider: "Claude", sendLevel: "values" };
  });

  it("draws nothing without the offer", () => {
    offer.value = undefined;
    const { container } = mounted();
    expect(container).toBeEmptyDOMElement();
  });

  it("sends nothing until asked and says what goes at each send level", () => {
    mounted();
    expect(screen.getByText(/with the names of records, people and change sets/)).toBeInTheDocument();
    expect(ai.explainWorkspaceHistory).not.toHaveBeenCalled();
    expect(screen.getByRole("combobox", { name: "Period" })).toHaveValue("7");
  });

  it("is headed at the level its page leaves free (R17-F44: no skipped level under the page's h1)", () => {
    mounted();
    expect(screen.getByRole("heading", { name: "What changed", level: 3 })).toBeInTheDocument();
    mounted({ headingLevel: 2 });
    expect(screen.getByRole("heading", { name: "What changed", level: 2 })).toBeInTheDocument();
  });

  it("names no name at the send level structure", () => {
    offer.value = { configured: true, provider: "Claude", sendLevel: "structure" };
    mounted();
    expect(screen.getByText(/At the send level "structure"/)).toBeInTheDocument();
    expect(screen.getByText(/No names of records, people, change sets or files/)).toBeInTheDocument();
  });

  it("asks for the period in the person's time zone, words the facts and leads a number to its fact", async () => {
    vi.mocked(ai.explainWorkspaceHistory).mockResolvedValue(account());
    mounted();
    fireEvent.click(screen.getByRole("button", { name: "Explain this period" }));
    expect(await screen.findByText(/Two things changed/)).toBeInTheDocument();
    const [workspace, body] = vi.mocked(ai.explainWorkspaceHistory).mock.calls[0];
    expect(workspace).toBe("north");
    expect(new Date(body.until).getTime() - new Date(body.since).getTime()).toBeCloseTo(7 * 86_400_000, -4);
    expect(body.timeZone).toBeTruthy();
    expect(screen.getByRole("heading", { name: /The facts \(3, all of them\), .*live data/ })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Fact 3" }));
    await waitFor(() => expect(screen.getByText("Fact number 3")).toHaveFocus());
    expect(screen.getByRole("button", { name: "Explain again" })).toBeInTheDocument();
  });

  it("heads the account's facts one level below its own heading (R17-F44)", async () => {
    vi.mocked(ai.explainWorkspaceHistory).mockResolvedValue(account());
    mounted({ headingLevel: 2 });
    fireEvent.click(screen.getByRole("button", { name: "Explain this period" }));
    expect(await screen.findByRole("heading", { name: /^The facts \(3, all of them\)/, level: 3 })).toBeInTheDocument();
  });

  it("leads a fact to its changes, its job and its change set", async () => {
    vi.mocked(ai.explainWorkspaceHistory).mockResolvedValue(
      account({
        facts: [
          fact(1, changes),
          fact(2, { kind: "job", id: "job-1", query: null }),
          fact(4, { kind: "changeSet", id: "cs-1", query: null }),
        ],
      }),
    );
    const onShow = vi.fn();
    const onNavigate = vi.fn();
    mounted({ onShow, onNavigate });
    fireEvent.click(screen.getByRole("button", { name: "Explain this period" }));
    await screen.findByText(/Two things changed/);
    fireEvent.click(screen.getByRole("button", { name: "Show it" }));
    expect(onShow).toHaveBeenCalledWith(expect.objectContaining({ since: "2026-10-25T00:00:00Z" }));
    fireEvent.click(screen.getByRole("link", { name: "Open the job" }));
    expect(onNavigate).toHaveBeenCalledWith({ kind: "settings", page: "jobs", jobId: "job-1" });
    fireEvent.click(screen.getByRole("link", { name: "Open the change set" }));
    expect(onNavigate).toHaveBeenLastCalledWith(
      expect.objectContaining({ kind: "changeSetChanges", changeSetId: "cs-1" }),
    );
  });

  it("shows the facts alone when the provider fails, and asks again", async () => {
    vi.mocked(ai.explainWorkspaceHistory)
      .mockResolvedValueOnce(account({ statements: [], failure: "The provider did not answer" }))
      .mockResolvedValueOnce(account());
    mounted();
    fireEvent.click(screen.getByRole("button", { name: "Explain this period" }));
    expect(
      await screen.findByText(/The provider did not answer. The facts below do not depend on it/),
    ).toBeInTheDocument();
    expect(screen.getByText("Fact number 2")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByText(/Two things changed/)).toBeInTheDocument();
  });

  it("says a period without change sent nothing", async () => {
    vi.mocked(ai.explainWorkspaceHistory).mockResolvedValue(account({ facts: [], statements: [] }));
    mounted();
    fireEvent.click(screen.getByRole("button", { name: "Explain this period" }));
    expect(
      await screen.findByText(/Nothing changed in this workspace between .* Nothing was sent to the AI/),
    ).toBeInTheDocument();
  });

  it("clears the account when the period changes, and asks for chosen dates with the last day included", async () => {
    vi.mocked(ai.explainWorkspaceHistory).mockResolvedValue(account());
    mounted();
    fireEvent.click(screen.getByRole("button", { name: "Explain this period" }));
    await screen.findByText(/Two things changed/);
    fireEvent.change(screen.getByRole("combobox", { name: "Period" }), { target: { value: "dates" } });
    expect(screen.queryByText(/Two things changed/)).not.toBeInTheDocument();
    const ask = screen.getByRole("button", { name: "Explain this period" });
    expect(ask).toBeDisabled();
    fireEvent.change(screen.getByLabelText("From"), { target: { value: "2026-10-01" } });
    fireEvent.change(screen.getByLabelText("To, included"), { target: { value: "2026-10-15" } });
    expect(ask).toBeEnabled();
    fireEvent.click(ask);
    await screen.findByText(/Two things changed/);
    const body = vi.mocked(ai.explainWorkspaceHistory).mock.calls[1][1];
    expect(new Date(body.until).getTime() - new Date(body.since).getTime()).toBe(15 * 86_400_000);
  });

  it("asks for one record's account with a default period of 30 days", async () => {
    vi.mocked(ai.explainRecordHistory).mockResolvedValue(account({ scope: "record" }));
    mounted({ record: { objectTypeKey: "ledger", objectId: "r-1" } });
    expect(screen.getByRole("combobox", { name: "Period" })).toHaveValue("30");
    fireEvent.click(screen.getByRole("button", { name: "Explain this period" }));
    await screen.findByText(/Two things changed/);
    expect(vi.mocked(ai.explainRecordHistory).mock.calls[0].slice(0, 2)).toEqual(["ledger", "r-1"]);
  });

  it("explains a refusal and offers to try again", async () => {
    vi.mocked(ai.explainWorkspaceHistory).mockRejectedValue(new Error("Not allowed"));
    mounted();
    fireEvent.click(screen.getByRole("button", { name: "Explain this period" }));
    expect(await screen.findByText("The account could not be asked for")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
  });
});
