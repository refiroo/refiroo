import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { Explorer } from "@/features/objects/Explorer";
import { domainObject, testModel } from "@/test/fixtures";

afterEach(() => vi.restoreAllMocks());

describe("Explorer", () => {
  it("retains loaded objects and retries the failed continuation", async () => {
    const read = vi
      .spyOn(api, "objects")
      .mockResolvedValueOnce({ items: [domainObject], nextCursor: "next" })
      .mockRejectedValueOnce(new Error("Explorer page unavailable"))
      .mockResolvedValueOnce({ items: [{ ...domainObject, id: "other", name: "Finance" }], nextCursor: null });
    render(
      <Explorer
        model={testModel}
        application={{ ...testModel.applications[0], objectTypeKeys: ["domain"] }}
        workspaceKey="west"
        refreshToken={0}
        onOpen={vi.fn()}
      />,
    );
    fireEvent.click(await screen.findByRole("button", { name: "Load more objects" }));
    await screen.findByText("Explorer page unavailable");
    expect(screen.getByRole("button", { name: /Connections/ })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    await screen.findByRole("button", { name: /Finance/ });
    expect(screen.getByRole("button", { name: /Connections/ })).toBeInTheDocument();
    expect(read.mock.calls.map(([, query]) => query.cursor)).toEqual([undefined, "next", "next"]);
    expect(read).toHaveBeenLastCalledWith("domain", expect.objectContaining({ workspaceKey: "west" }));
  });
});
