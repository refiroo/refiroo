import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { domainObject } from "@/test/fixtures";
import { ObjectLookup } from "@/ui/ObjectLookup";

vi.mock("@/api/client", () => ({ api: { objects: vi.fn() } }));

describe("ObjectLookup", () => {
  it("shows lookup failure and can retry in the same workspace", async () => {
    vi.mocked(api.objects)
      .mockRejectedValueOnce(new Error("Lookup unavailable"))
      .mockResolvedValueOnce({ items: [{ ...domainObject, workspaceKey: "west" }], nextCursor: null });
    render(<ObjectLookup objectTypeKey="domain" workspaceKey="west" onChange={vi.fn()} />);
    expect(await screen.findByText("Lookup unavailable")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    await waitFor(() =>
      expect(api.objects).toHaveBeenLastCalledWith("domain", expect.objectContaining({ workspaceKey: "west" })),
    );
    expect(await screen.findByRole("option", { name: /Connections/ })).toBeInTheDocument();
  });

  it("clears a candidate when the workspace changes", async () => {
    vi.mocked(api.objects).mockResolvedValue({ items: [domainObject], nextCursor: null });
    const onChange = vi.fn();
    const { rerender } = render(
      <ObjectLookup objectTypeKey="domain" workspaceKey="default" value={domainObject} onChange={onChange} />,
    );
    await screen.findByRole("option", { name: /Connections/ });
    rerender(<ObjectLookup objectTypeKey="domain" workspaceKey="west" value={domainObject} onChange={onChange} />);
    expect(onChange).toHaveBeenCalledWith(undefined);
  });

  it("retries the same lookup cursor after a load-more failure", async () => {
    vi.mocked(api.objects)
      .mockResolvedValueOnce({ items: [domainObject], nextCursor: "next" })
      .mockRejectedValueOnce(new Error("Lookup page unavailable"))
      .mockResolvedValueOnce({ items: [{ ...domainObject, id: "other", name: "Finance" }], nextCursor: null });
    render(<ObjectLookup objectTypeKey="domain" workspaceKey="default" onChange={vi.fn()} />);
    fireEvent.click(await screen.findByRole("button", { name: "Load more results" }));
    fireEvent.click(await screen.findByRole("button", { name: "Retry" }));
    expect(await screen.findByRole("option", { name: /Finance/ })).toBeInTheDocument();
    expect(api.objects).toHaveBeenLastCalledWith(
      "domain",
      expect.objectContaining({ workspaceKey: "default", cursor: "next" }),
    );
  });
});
