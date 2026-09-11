import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { CollectionPanelTable } from "@/features/objects/panels/CollectionPanelTable";
import { codelistObject, domainObject, testModel } from "@/test/fixtures";

afterEach(() => vi.restoreAllMocks());

describe("embedded collection reads", () => {
  it.each([domainObject, codelistObject])("keeps $objectTypeKey content on a failed next page", async (row) => {
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

    fireEvent.click(screen.getByRole("button", { name: "Next page" }));
    await screen.findByText("Children unavailable");
    expect(screen.getByRole("button", { name: row.name })).toBeInTheDocument();
    expect(screen.queryByText("Nothing to show yet.")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    await screen.findByRole("button", { name: "Next record" });
    expect(read.mock.calls.map(([, query]) => query.cursor)).toEqual([undefined, "second", "second"]);
    await waitFor(() =>
      expect(read).toHaveBeenLastCalledWith(
        row.objectTypeKey,
        expect.objectContaining({
          workspaceKey: "west",
          parentObjectId: domainObject.id,
        }),
      ),
    );
  });
});
