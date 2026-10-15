import { fireEvent, render as renderBase, screen, waitFor, within } from "@testing-library/react";
import { ToastProvider } from "@/ui/Toast";
import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { CollectionPanelTable } from "@/features/objects/panels/CollectionPanelTable";
import { codelistObject, domainObject, testModel } from "@/test/fixtures";

/** A list's cells edited in place say where a save went in a toast (0.10 A9), as the app's provider shows it. */
const render: typeof renderBase = ((ui: Parameters<typeof renderBase>[0], options?: Parameters<typeof renderBase>[1]) =>
  renderBase(ui, { wrapper: ToastProvider, ...options })) as typeof renderBase;

afterEach(() => vi.restoreAllMocks());

describe("embedded collection reads", () => {
  it.each([domainObject, codelistObject])("keeps $objectTypeKey content when scrolling on fails", async (row) => {
    const read = vi
      .spyOn(api, "objects")
      .mockResolvedValueOnce({ items: [row], nextCursor: "second" })
      .mockRejectedValueOnce(new Error("Children unavailable"))
      .mockResolvedValueOnce({ items: [{ ...row, id: "next", name: "Next record" }], nextCursor: null });
    render(
      <CollectionPanelTable
        model={testModel}
        application={testModel.applications[0]}
        object={{ ...domainObject, workspaceKey: "west" }}
        objectTypeKey={row.objectTypeKey}
        panel={{
          key: "children",
          title: "Children",
          type: "children",
          region: "main",
          visible: true,
          order: 1,
          config: { objectTypeKeys: [row.objectTypeKey], columns: ["name"], pageSize: 1 },
        }}
        columns={["name", "code"]}
        pageSize={1}
        parentObjectId={domainObject.id}
        allowCreate={false}
        onOpen={vi.fn()}
        onChanged={vi.fn()}
        onObjectChanged={vi.fn()}
        onReload={vi.fn()}
        readOnly
      />,
    );
    await screen.findByRole("button", { name: row.name });
    fireEvent.click(screen.getByRole("button", { name: "Display" }));
    const display = await screen.findByRole("dialog", { name: "Display" });
    fireEvent.click(within(display).getByLabelText("Code"));
    fireEvent.change(within(display).getByLabelText("Density"), { target: { value: "compact" } });
    fireEvent.click(within(display).getByRole("button", { name: "Done" }));
    expect(screen.queryByRole("columnheader", { name: "Code" })).not.toBeInTheDocument();
    expect(read).toHaveBeenCalledTimes(1);

    // Moving down from the last loaded row reads the next page, as scrolling near the edge does.
    fireEvent.keyDown(screen.getByRole("button", { name: row.name }), { key: "ArrowDown" });
    await screen.findByText("Children unavailable");
    expect(screen.getByRole("button", { name: row.name })).toBeInTheDocument();
    expect(screen.queryByText("Nothing to show yet.")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    await screen.findByRole("button", { name: "Next record" });
    expect(screen.getByRole("button", { name: row.name })).toBeInTheDocument();
    expect(read.mock.calls.map(([, query]) => query.cursor)).toEqual([undefined, "second", "second"]);
    await waitFor(() => expect(screen.getByRole("button", { name: "Next record" })).toHaveFocus());
    await waitFor(() =>
      expect(read).toHaveBeenLastCalledWith(
        row.objectTypeKey,
        expect.objectContaining({
          workspaceKey: "west",
          parentObjectId: domainObject.id,
          sort: "name",
        }),
      ),
    );
  });
});

describe("relation columns in a panel (0.9 K5)", () => {
  it("asks for the shown relation columns only (D146)", async () => {
    const read = vi.spyOn(api, "objects").mockResolvedValue({ items: [domainObject], nextCursor: null });
    render(
      <CollectionPanelTable
        model={testModel}
        application={testModel.applications[0]}
        object={{ ...domainObject, workspaceKey: "west" }}
        objectTypeKey="domain"
        panel={{
          key: "table",
          title: "Domains",
          type: "table",
          region: "main",
          visible: true,
          order: 1,
          config: {
            objectTypeKey: "domain",
            columns: ["name", "related:domain-contains-codelist"],
            filterByParent: false,
            pageSize: 5,
          },
        }}
        columns={["name", "related:domain-contains-codelist"]}
        pageSize={5}
        allowCreate={false}
        onOpen={vi.fn()}
        onChanged={vi.fn()}
        onObjectChanged={vi.fn()}
        onReload={vi.fn()}
        readOnly
      />,
    );
    await screen.findByRole("columnheader", { name: "Contains" });
    expect(read.mock.calls[0][1].expand).toEqual(["domain-contains-codelist"]);
    fireEvent.click(screen.getByRole("button", { name: "Display" }));
    const display = await screen.findByRole("dialog", { name: "Display" });
    fireEvent.click(within(display).getByLabelText("Contains"));
    fireEvent.click(within(display).getByRole("button", { name: "Done" }));
    await waitFor(() => expect(read.mock.calls.at(-1)?.[1].expand).toEqual([]));
    expect(screen.queryByRole("columnheader", { name: "Contains" })).not.toBeInTheDocument();
  });
});
