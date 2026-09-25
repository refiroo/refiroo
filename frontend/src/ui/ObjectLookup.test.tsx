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

  it("moves through options across a page boundary by keyboard and retries a failed page", async () => {
    vi.mocked(api.objects)
      .mockResolvedValueOnce({ items: [domainObject], nextCursor: "next", totalCount: 2, startIndex: 0 })
      .mockRejectedValueOnce(new Error("Lookup page unavailable"))
      .mockResolvedValueOnce({ items: [{ ...domainObject, id: "other", name: "Finance" }], nextCursor: null });
    const onChange = vi.fn();
    render(<ObjectLookup objectTypeKey="domain" workspaceKey="default" label="Parent" onChange={onChange} />);
    const field = screen.getByRole("combobox", { name: "Search: Parent" });
    await screen.findByRole("option", { name: /Connections/ });
    expect(screen.getByRole("option", { name: /Connections/ })).toHaveAttribute("aria-setsize", "2");
    fireEvent.keyDown(field, { key: "ArrowDown" });
    expect(field).toHaveAttribute("aria-activedescendant", screen.getByRole("option", { name: /Connections/ }).id);
    fireEvent.keyDown(field, { key: "ArrowDown" });
    fireEvent.click(await screen.findByRole("button", { name: "Retry" }));
    const finance = await screen.findByRole("option", { name: /Finance/ });
    expect(api.objects).toHaveBeenLastCalledWith(
      "domain",
      expect.objectContaining({ workspaceKey: "default", cursor: "next" }),
    );
    await waitFor(() => expect(field).toHaveAttribute("aria-activedescendant", finance.id));
    fireEvent.keyDown(field, { key: "Enter" });
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ id: "other" }));
  });
});
