import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ProposedBecause } from "@/features/model-editor/ProposedBecause";
import type { Proposal } from "@/types";

const proposal = (evidence: Proposal["evidence"]) =>
  ({
    id: "p1",
    position: 1,
    pattern: "assistant",
    summary: "Rename Items",
    evidence,
    alternatives: [],
  }) as unknown as Proposal;

describe("Proposed because › the AI assistant (0.16 AP1)", () => {
  it("says who proposed it, how confident it was and why", () => {
    render(
      <ProposedBecause
        busy={false}
        run={() => undefined}
        proposal={proposal({
          origin: {
            kind: "ai",
            provider: "anthropic",
            model: "claude-test",
            promptVersion: "1",
            confidence: 0.8,
            reason: "Written out from the header",
          },
        })}
      />,
    );
    expect(
      screen.getByText("Proposed by the AI assistant (claude-test), 80% confident. Written out from the header"),
    ).toBeTruthy();
    expect(screen.queryByText(/^Origin:/)).toBeNull();
  });

  it("says it for a type the assistant named, beside the rules' own proposal", () => {
    const named = proposal({
      origin: { kind: "ai", provider: "p", model: null, promptVersion: "1", confidence: 0.55, reason: "Clearer" },
    });
    render(<ProposedBecause busy={false} run={() => undefined} proposal={proposal({ groups: 3 })} assistant={named} />);
    expect(screen.getByText("Proposed by the AI assistant, 55% confident. Clearer")).toBeTruthy();
  });

  it("says nothing of an assistant for a proposal of the patterns", () => {
    render(<ProposedBecause busy={false} run={() => undefined} proposal={proposal({ groups: 3 })} />);
    expect(screen.queryByText(/AI assistant/)).toBeNull();
  });
});
