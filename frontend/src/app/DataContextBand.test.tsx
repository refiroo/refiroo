import type { ReactNode } from "react";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { DataContextBand } from "@/app/DataContextBand";
import { viewRoute } from "@/routing/routes";
import type { ApplicationDefinition, EngineModel } from "@/types";

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

const other = { ...application, key: "registry", name: "Registry" } as ApplicationDefinition;
const model = { applications: [application, other] } as unknown as EngineModel;

function band(route: Parameters<typeof DataContextBand>[0]["route"], contextActions?: ReactNode) {
  const onNavigate = vi.fn();
  const onSelectApplication = vi.fn();
  const { container } = render(
    <DataContextBand
      model={model}
      application={application}
      route={route}
      workspaceLabel="North"
      contextActions={contextActions}
      onNavigate={onNavigate}
      onSelectApplication={onSelectApplication}
      onChangeWorkspace={vi.fn()}
    />,
  );
  return { onNavigate, onSelectApplication, root: container.firstElementChild as HTMLElement };
}

const list = viewRoute(application, "items", "north");
const switcher = () => within(screen.getByRole("navigation", { name: "Workspace data context" }));

describe("DataContextBand", () => {
  it("names live data with a pill and an explanation", () => {
    const { root } = band(list);
    expect(root).toHaveClass("band-live");
    expect(screen.getByRole("group", { name: "Current context" })).toHaveTextContent(/^Live$/);
    expect(screen.getByText("Edits apply immediately in this workspace.")).toBeInTheDocument();
    expect(switcher().getByRole("button", { name: "Live" })).toHaveAttribute("aria-current", "page");
  });

  it("no longer says the workspace and the application on desktop: the sidebar and the top bar do (PP-D33)", () => {
    band(list);
    expect(screen.queryByText("North")).not.toBeInTheDocument();
    expect(screen.queryByText("Catalogue")).not.toBeInTheDocument();
  });

  it("is an amber strip in a change set, carries its actions and returns to live", () => {
    const { root, onNavigate } = band(
      { ...list, changeSetId: "cs-1" },
      <button type="button">Validate change set</button>,
    );
    expect(root).toHaveClass("band-change-set");
    expect(screen.getByRole("group", { name: "Current context" })).toHaveTextContent(/^Change set$/);
    expect(screen.queryByText("Edits apply immediately in this workspace.")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Validate change set" })).toBeInTheDocument();
    expect(switcher().getByRole("button", { name: "Change sets" })).toHaveAttribute("aria-current", "page");
    fireEvent.click(switcher().getByRole("button", { name: "Live" }));
    expect(onNavigate).toHaveBeenCalledWith(
      expect.objectContaining({ kind: "list", viewKey: "items", workspaceKey: "north" }),
    );
    expect(onNavigate.mock.calls[0][0].changeSetId).toBeUndefined();
  });

  it("is a violet strip in a publication and says it is read-only", () => {
    const { root } = band({ ...list, publicationId: "p-1" }, <p>Viewing Publication 3</p>);
    expect(root).toHaveClass("band-publication");
    expect(screen.getByRole("group", { name: "Current context" })).toHaveTextContent("Publication");
    expect(screen.getByText("Viewing Publication 3")).toBeInTheDocument();
    expect(screen.getByText("Read-only. A publication's records never change.")).toBeInTheDocument();
    expect(switcher().getByRole("button", { name: "Publications" })).toHaveAttribute("aria-current", "page");
  });

  it("shows no pill on the change set and publication lists, which are about a context rather than in one", () => {
    const { root } = band({ kind: "changeSets", applicationKey: "catalogue", workspaceKey: "north" });
    expect(root).toHaveClass("band-neutral");
    expect(screen.getByRole("group", { name: "Current context" })).toHaveTextContent(/^Change sets$/);
    expect(switcher().getByRole("button", { name: "Change sets" })).toHaveAttribute("aria-current", "page");
    expect(switcher().getByRole("button", { name: "Live" })).not.toHaveAttribute("aria-current");
  });

  describe("on a phone (0.10 N1)", () => {
    beforeEach(() => {
      vi.stubGlobal(
        "matchMedia",
        (query: string) =>
          ({
            matches: true,
            media: query,
            addEventListener: vi.fn(),
            removeEventListener: vi.fn(),
          }) as unknown as MediaQueryList,
      );
    });
    afterEach(() => vi.unstubAllGlobals());

    it("is one line whose workspace, application and data context each open their choice", async () => {
      const { onNavigate, onSelectApplication } = band(list);
      const line = within(screen.getByRole("group", { name: "Current context" }));
      expect(line.getByRole("button", { name: "Workspace: North" })).toBeVisible();
      expect(screen.queryByText("Edits apply immediately in this workspace.")).not.toBeInTheDocument();

      fireEvent.click(line.getByRole("button", { name: "Application: Catalogue" }));
      const applications = within(await screen.findByRole("navigation", { name: "Applications" }));
      expect(applications.getByRole("button", { name: "Catalogue" })).toHaveAttribute("aria-current", "page");
      fireEvent.click(applications.getByRole("button", { name: "Registry" }));
      expect(onSelectApplication).toHaveBeenCalledWith(other);

      fireEvent.click(line.getByRole("button", { name: "Data: Live" }));
      expect(await screen.findByText("Edits apply immediately in this workspace.")).toBeVisible();
      fireEvent.click(switcher().getByRole("button", { name: /Change sets/ }));
      expect(onNavigate).toHaveBeenCalledWith({
        kind: "changeSets",
        applicationKey: "catalogue",
        workspaceKey: "north",
      });
    });
  });
});
