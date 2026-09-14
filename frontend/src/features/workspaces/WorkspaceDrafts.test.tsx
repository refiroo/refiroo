import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DraftDiagnostics } from "@/features/workspaces/WorkspaceDrafts";

describe("draft mapping activation diagnostics", () => {
  it.each(["outgoing", "incoming"])("shows the recovery message and anchor for %s conflicts", (direction) => {
    const anchor = `${direction}-anchor`;
    const message =
      "Mapping relationships changed live since this draft's source. Review live mappings and reapply the intended changes in a draft created from current live data before retrying activation.";
    render(
      <DraftDiagnostics
        items={[
          {
            kind: "mapping-set",
            code: "mapping_set_changed",
            id: anchor,
            anchorObjectId: anchor,
            direction,
            message,
            expectedTargetCount: 0,
            actualTargetCount: 1,
          },
        ]}
      />,
    );
    expect(screen.getByRole("listitem")).toHaveTextContent(message);
    expect(screen.getByRole("listitem")).toHaveTextContent(anchor);
    expect(screen.getByRole("listitem")).not.toHaveTextContent("mapping_set_changed");
  });
});
