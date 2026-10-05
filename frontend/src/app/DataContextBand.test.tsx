import type { ReactNode } from "react";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { DataContextBand } from "@/app/DataContextBand";
import { viewRoute } from "@/routing/routes";
import type { ApplicationDefinition } from "@/types";

const application = {
  key: "catalogue",
  name: "Catalogue",
  state: "active",
  objectTypeKeys: ["item"],
  defaultView: "items",
  views: [{ key: "items", name: "Items", type: "table", objectTypeKey: "item", config: {} }],
  details: [],
  settings: {},
} as unknown as ApplicationDefinition;

function band(route: Parameters<typeof DataContextBand>[0]["route"], contextActions?: ReactNode) {
  const onNavigate = vi.fn();
  const { container } = render(
    <DataContextBand
      application={application}
      route={route}
      workspaceLabel="North"
      contextActions={contextActions}
      onNavigate={onNavigate}
    />,
  );
  return { onNavigate, root: container.firstElementChild as HTMLElement };
}

const list = viewRoute(application, "items", "north");
const switcher = () => within(screen.getByRole("navigation", { name: "Workspace data context" }));

describe("DataContextBand", () => {
  it("names live data with a pill and an explanation", () => {
    const { root } = band(list);
    expect(root).toHaveClass("band-live");
    expect(screen.getByRole("group", { name: "Current context" })).toHaveTextContent("North / CatalogueLive");
    expect(screen.getByText("Edits apply immediately in this workspace.")).toBeInTheDocument();
    expect(switcher().getByRole("button", { name: "Live" })).toHaveAttribute("aria-current", "page");
  });

  it("turns amber in a change set, carries its actions and returns to live", () => {
    const { root, onNavigate } = band(
      { ...list, changeSetId: "cs-1" },
      <button type="button">Validate change set</button>,
    );
    expect(root).toHaveClass("band-change-set");
    expect(screen.getByRole("group", { name: "Current context" })).toHaveTextContent("Change set · ");
    expect(screen.queryByText("Edits apply immediately in this workspace.")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Validate change set" })).toBeInTheDocument();
    expect(switcher().getByRole("button", { name: "Change sets" })).toHaveAttribute("aria-current", "page");
    fireEvent.click(switcher().getByRole("button", { name: "Live" }));
    expect(onNavigate).toHaveBeenCalledWith(
      expect.objectContaining({ kind: "list", viewKey: "items", workspaceKey: "north" }),
    );
    expect(onNavigate.mock.calls[0][0].changeSetId).toBeUndefined();
  });

  it("turns violet in a publication", () => {
    const { root } = band({ ...list, publicationId: "p-1" }, <p>Viewing Publication 3</p>);
    expect(root).toHaveClass("band-publication");
    expect(screen.getByRole("group", { name: "Current context" })).toHaveTextContent("Publication");
    expect(screen.getByText("Viewing Publication 3")).toBeInTheDocument();
    expect(switcher().getByRole("button", { name: "Publications" })).toHaveAttribute("aria-current", "page");
  });

  it("shows no pill on the change set and publication lists, which are about a context rather than in one", () => {
    band({ kind: "changeSets", applicationKey: "catalogue", workspaceKey: "north" });
    expect(screen.getByRole("group", { name: "Current context" })).toHaveTextContent(/^North \/ Catalogue$/);
    expect(switcher().getByRole("button", { name: "Change sets" })).toHaveAttribute("aria-current", "page");
    expect(switcher().getByRole("button", { name: "Live" })).not.toHaveAttribute("aria-current");
  });
});
