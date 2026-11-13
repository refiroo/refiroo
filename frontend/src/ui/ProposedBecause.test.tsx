import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ProposedBecause } from "@/ui/ProposedBecause";
import type { Proposal } from "@/types";

const proposal = (evidence: Proposal["evidence"]) =>
  ({
    id: "p1",
    position: 1,
    pattern: "mappingTarget",
    summary: "Rename Items",
    evidence,
    alternatives: [],
  }) as unknown as Proposal;

describe("Proposed because › an AI proposal", () => {
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

  it("says nothing of an assistant for a proposal of the patterns", () => {
    render(<ProposedBecause busy={false} run={() => undefined} proposal={proposal({ groups: 3 })} />);
    expect(screen.queryByText(/AI assistant/)).toBeNull();
  });
});
