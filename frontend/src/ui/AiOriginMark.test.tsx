import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { AgentOrigin, ProposalOrigin } from "@/types";
import { AiOriginMark } from "@/ui/AiOriginMark";

const agent: AgentOrigin = {
  kind: "agent",
  application: "Claude Desktop",
  proposedBy: "p1",
  proposedByName: "Ana Varga",
  editedByName: "Bo Kiss",
};

const ai: ProposalOrigin = {
  kind: "ai",
  provider: "fake",
  model: "fake-1",
  promptVersion: "1",
  confidence: 0.86,
  reason: "The name says so.",
  proposedByName: "Ana Varga",
};

afterEach(() => vi.unstubAllGlobals());

describe("AiOriginMark", () => {
  it("keeps the AI wording on both variants", () => {
    const { unmount } = render(<AiOriginMark origin={ai} variant="history" />);
    expect(screen.getByText("Proposed by the AI assistant (fake-1), 86% confident")).toBeInTheDocument();
    expect(screen.getByText("The name says so. Asked for by Ana Varga.")).toBeInTheDocument();
    unmount();
    render(<AiOriginMark origin={ai} variant="target" />);
    expect(screen.getByText("Proposed by the AI · 86%")).toBeInTheDocument();
  });

  it("names the assistant, who asked, who edited, and that the name is its own, on a history entry", () => {
    render(<AiOriginMark origin={agent} variant="history" />);
    expect(screen.getByText("Prepared by an assistant: Claude Desktop")).toBeInTheDocument();
    expect(
      screen.getByText("Asked for by Ana Varga. Edited by Bo Kiss. (the name is the one the assistant gave itself)"),
    ).toBeInTheDocument();
  });

  it("leaves out Asked for by when the client acted for itself", () => {
    render(
      <AiOriginMark
        origin={{ kind: "agent", application: "Nightly sync", proposedByName: "Nightly sync" }}
        variant="history"
      />,
    );
    expect(screen.getByText("Prepared by an assistant: Nightly sync")).toBeInTheDocument();
    expect(screen.queryByText(/Asked for by/)).toBeNull();
    expect(screen.getByText("(the name is the one the assistant gave itself)")).toBeInTheDocument();
  });

  it("uses the short pill on a target, without the self-given note", () => {
    render(<AiOriginMark origin={agent} variant="target" />);
    expect(screen.getByText("Prepared by an assistant")).toBeInTheDocument();
    expect(screen.getByText("Asked for by Ana Varga. Edited by Bo Kiss.")).toBeInTheDocument();
    expect(screen.queryByText(/gave itself/)).toBeNull();
  });

  it("folds the reason under Why? on a phone", () => {
    vi.stubGlobal("matchMedia", () => ({ matches: true, addEventListener() {}, removeEventListener() {} }));
    const { container } = render(<AiOriginMark origin={agent} variant="target" />);
    expect(container.querySelector("details.ai-origin-fold")).not.toBeNull();
    expect(screen.getByText("Why?")).toBeInTheDocument();
  });
});
