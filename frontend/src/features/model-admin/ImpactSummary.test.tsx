import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/api/errors";
import { ImpactSummary } from "@/features/model-admin/ImpactSummary";
import type { ImpactSummary as Summary } from "@/types";

const offer = vi.hoisted(() => ({ value: undefined as unknown }));
vi.mock("@/features/settings/useWorkspaceAiOffer", () => ({ useImpactSummaryOffer: () => offer.value }));

const fact = (n: number, kind: Summary["facts"][number]["kind"] = "change") => ({
  id: `ch-${n}`,
  kind,
  text: `Fact number ${n}`,
  path: null,
  count: null,
});
const summary = (extra: Partial<Summary> = {}): Summary => ({
  facts: [fact(1), fact(2), fact(3)],
  statements: [{ text: "Two things change.", factIds: ["ch-1", "ch-3"] }],
  removedStatements: 0,
  failure: null,
  cached: false,
  callId: "call-1",
  ...extra,
});

describe("ImpactSummary (0.16 AO1)", () => {
  beforeEach(() => {
    offer.value = { configured: true, provider: "Claude", sendLevel: "structure" };
  });

  it("draws nothing without the offer", () => {
    offer.value = undefined;
    const { container } = render(<ImpactSummary workspaceKey="north" ask={vi.fn()} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("sends nothing until asked, then words the facts and leads each number to its fact", async () => {
    const ask = vi.fn().mockResolvedValue(summary());
    render(<ImpactSummary workspaceKey="north" ask={ask} />);
    expect(screen.getByText(/go to Claude. No record value is sent/)).toBeInTheDocument();
    expect(ask).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Explain this change" }));
    expect(await screen.findByText(/Two things change/)).toBeInTheDocument();
    expect(ask).toHaveBeenCalledTimes(1);
    expect(screen.getByText(/Written by AI from the facts below, by Claude. It can be wrong/)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "The facts (3, all of them)" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Fact 3" }));
    await waitFor(() => expect(screen.getByText("Fact number 3")).toHaveFocus());
  });

  it("counts a statement removed for having no source", async () => {
    render(<ImpactSummary workspaceKey="north" ask={vi.fn().mockResolvedValue(summary({ removedStatements: 1 }))} />);
    fireEvent.click(screen.getByRole("button", { name: "Explain this change" }));
    expect(await screen.findByText(/1 statement removed: no source\./)).toBeInTheDocument();
  });

  it("shows the facts alone with the failure and asks again on request", async () => {
    const ask = vi
      .fn()
      .mockResolvedValueOnce(summary({ statements: [], failure: "The provider did not answer" }))
      .mockResolvedValueOnce(summary());
    render(<ImpactSummary workspaceKey="north" ask={ask} />);
    fireEvent.click(screen.getByRole("button", { name: "Explain this change" }));
    const warning = await screen.findByText(/The provider did not answer. The facts below do not depend on it/);
    expect(warning).toBeInTheDocument();
    expect(screen.getByText("Fact number 2")).toBeInTheDocument();
    expect(screen.queryByText(/Written by AI/)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByText(/Two things change/)).toBeInTheDocument();
  });

  it("lists ten facts, then the rest on request, and a citation below the fold opens them", async () => {
    const facts = Array.from({ length: 214 }, (_, index) => fact(index + 1));
    const ask = vi
      .fn()
      .mockResolvedValue(summary({ facts, statements: [{ text: "Many change.", factIds: ["ch-1", "ch-200"] }] }));
    render(<ImpactSummary workspaceKey="north" ask={ask} />);
    fireEvent.click(screen.getByRole("button", { name: "Explain this change" }));
    await screen.findByText(/Many change/);
    expect(screen.getAllByRole("listitem").filter((item) => item.hasAttribute("data-kind"))).toHaveLength(10);
    fireEvent.click(screen.getByRole("button", { name: "Fact 200" }));
    await waitFor(() => expect(screen.getByText("Fact number 200")).toHaveFocus());
    expect(screen.queryByRole("button", { name: /^Show the other/ })).not.toBeInTheDocument();
  });

  it("names a refused request and keeps the way back", async () => {
    const ask = vi.fn().mockRejectedValue(new ApiError(409, "AI_NOT_CONFIGURED", "No AI provider is set up"));
    render(<ImpactSummary workspaceKey="north" ask={ask} />);
    fireEvent.click(screen.getByRole("button", { name: "Explain this change" }));
    const notice = await screen.findByRole("alert");
    expect(within(notice).getByText(/No AI provider is set up/)).toBeInTheDocument();
    expect(within(notice).getByRole("button", { name: "Try again" })).toBeInTheDocument();
  });

  it("is cleared by a new check, which remounts it under another key", async () => {
    const ask = vi.fn().mockResolvedValue(summary());
    const { rerender } = render(<ImpactSummary key="north:a" workspaceKey="north" ask={ask} />);
    fireEvent.click(screen.getByRole("button", { name: "Explain this change" }));
    await screen.findByText(/Two things change/);
    rerender(<ImpactSummary key="north:b" workspaceKey="north" ask={ask} />);
    expect(screen.queryByText(/Two things change/)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Explain this change" })).toBeInTheDocument();
  });
});
