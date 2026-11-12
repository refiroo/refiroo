import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { TopBar, fittingCount } from "@/app/TopBar";
import type { EngineModel } from "@/types";

vi.mock("@/features/workspaces/WorkspaceSearch", () => ({
  WorkspaceSearch: ({ workspaceKey }: { workspaceKey: string }) => <input aria-label={`Find in ${workspaceKey}`} />,
}));
vi.mock("@/features/inbox/InboxButton", () => ({ InboxButton: () => <span /> }));
vi.mock("@/app/SettingsMenu", () => ({ AccountMenu: () => <span /> }));
vi.mock("@/app/instanceProduct", () => ({
  useInstanceProduct: () => ({ name: "refiroo", description: "" }),
}));

afterEach(cleanup);

describe("the top bar's help link (HD)", () => {
  it("opens the documentation in a new tab without handing the page over", () => {
    const model = { applications: [], product: { name: "refiroo" } } as unknown as EngineModel;
    render(<TopBar model={model} onHome={vi.fn()} onSelectApplication={vi.fn()} onNavigate={vi.fn()} />);
    const help = screen.getByRole("link", { name: /^Help/ });
    expect(help.getAttribute("href")).toMatch(/\/docs\/$/);
    expect(help.getAttribute("target")).toBe("_blank");
    expect(help.getAttribute("rel")).toContain("noopener");
  });
});

const applications = ["Catalogue", "Stations", "Systems"].map((name) => ({
  key: name.toLowerCase(),
  name,
  views: [],
})) as unknown as EngineModel["applications"];
const model = { applications, product: { name: "refiroo" } } as unknown as EngineModel;

describe("the top bar (0.17 SH1)", () => {
  it("shows the applications as tabs with the current one marked, and the workspace search", () => {
    render(
      <TopBar
        model={model}
        currentApplicationKey="stations"
        workspaceKey="stops"
        onHome={vi.fn()}
        onSelectApplication={vi.fn()}
        onNavigate={vi.fn()}
      />,
    );
    const tabs = within(screen.getByRole("navigation", { name: "Applications" }));
    expect(tabs.getAllByRole("button").map((tab) => tab.textContent)).toEqual(["Catalogue", "Stations", "Systems"]);
    expect(tabs.getByRole("button", { name: "Stations" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("textbox", { name: "Find in stops" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "More applications" })).not.toBeInTheDocument();
  });

  it("shows no search outside a workspace", () => {
    render(<TopBar model={model} onHome={vi.fn()} onSelectApplication={vi.fn()} onNavigate={vi.fn()} />);
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
  });

  it("offers Back to the workspace in Settings, in place of the application tabs, and keeps Settings current", () => {
    const onBack = vi.fn();
    render(
      <TopBar
        model={model}
        inSettings
        backTo={{ label: "Back to STOPS Reference Data", href: "/workspace?workspaceKey=stops", onBack }}
        onHome={vi.fn()}
        onSelectApplication={vi.fn()}
        onNavigate={vi.fn()}
      />,
    );
    expect(screen.queryByRole("button", { name: "Stations" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("link", { name: "Back to STOPS Reference Data" }));
    expect(onBack).toHaveBeenCalled();
    expect(screen.getByRole("link", { name: "Settings" })).toHaveAttribute("aria-current", "page");
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
  });

  it("shows no tabs on the workspace's own page, which lists the applications itself", () => {
    render(
      <TopBar
        model={model}
        workspaceKey="stops"
        tabs={false}
        onHome={vi.fn()}
        onSelectApplication={vi.fn()}
        onNavigate={vi.fn()}
      />,
    );
    expect(screen.queryByRole("button", { name: "Stations" })).not.toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Find in stops" })).toBeInTheDocument();
  });
});

describe("fittingCount (the tabs that fit before More)", () => {
  it("keeps every tab when they fit, and at least one when none does", () => {
    expect(fittingCount([100, 100, 100], 20, 340, 60)).toBe(3);
    expect(fittingCount([100, 100, 100], 20, 300, 60)).toBe(2);
    expect(fittingCount([100, 100, 100], 20, 30, 60)).toBe(1);
  });
});
