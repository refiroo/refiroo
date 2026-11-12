import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ShellFrame } from "@/app/ShellFrame";
import { TopBar } from "@/app/TopBar";
import { applyScheme, resetSchemePreference, SCHEME_STORAGE_KEY, type ColourScheme } from "@/lib/scheme";
import type { EngineModel } from "@/types";

vi.mock("@/features/workspaces/WorkspaceSearch", () => ({
  WorkspaceSearch: ({ workspaceKey }: { workspaceKey: string }) => <input aria-label={`Find in ${workspaceKey}`} />,
}));
vi.mock("@/features/inbox/InboxButton", () => ({ InboxButton: () => <span /> }));
vi.mock("@/app/SettingsMenu", () => ({ AccountMenu: () => <span /> }));
vi.mock("@/app/instanceProduct", () => ({
  useInstanceProduct: () => ({ name: "refiroo", description: "" }),
}));

const applications = ["Catalogue", "Stations"].map((name) => ({
  key: name.toLowerCase(),
  name,
  views: [],
})) as unknown as EngineModel["applications"];
const model = { applications, product: { name: "refiroo" } } as unknown as EngineModel;

const rail = {
  id: "side",
  as: "nav" as const,
  label: "Pages",
  toggleLabel: "Pages",
  drawerTitle: "Pages",
  resizeLabel: "Resize",
  content: () => <span>rail content</span>,
};

function choose(scheme: ColourScheme, phone = false) {
  const stored = new Map<string, string>([[SCHEME_STORAGE_KEY, JSON.stringify(scheme)]]);
  vi.stubGlobal("localStorage", {
    getItem: (key: string) => stored.get(key) ?? null,
    setItem: (key: string, value: string) => stored.set(key, value),
    removeItem: (key: string) => stored.delete(key),
  });
  resetSchemePreference();
  applyScheme(scheme);
  vi.stubGlobal(
    "matchMedia",
    vi.fn(() => ({ matches: phone, addEventListener: vi.fn(), removeEventListener: vi.fn() })),
  );
}

function frame(withRail: boolean) {
  return render(
    <ShellFrame
      rail={withRail ? rail : undefined}
      topBar={<TopBar model={model} onHome={vi.fn()} onSelectApplication={vi.fn()} onNavigate={vi.fn()} />}
    >
      <p>page</p>
    </ShellFrame>,
  );
}

beforeEach(() => resetSchemePreference());
afterEach(() => {
  cleanup();
  resetSchemePreference();
  delete document.documentElement.dataset.scheme;
  delete document.documentElement.dataset.frame;
  vi.unstubAllGlobals();
});

describe("the frame's side column (0.17 UX1, PP-D39)", () => {
  it("holds the applications in its head for Studio with a rail", () => {
    choose("studio");
    const { container } = frame(true);
    const head = container.querySelector<HTMLElement>(".frame-side-head");
    expect(head).not.toBeNull();
    expect(within(head!).getByRole("navigation", { name: "Applications" })).toBeInTheDocument();
  });

  it("has no side column for Studio without a rail", () => {
    choose("studio");
    const { container } = frame(false);
    expect(container.querySelector(".frame-side")).toBeNull();
    expect(screen.getByRole("navigation", { name: "Applications" })).toBeInTheDocument();
  });

  it("holds the actions in its foot for Instrument", () => {
    choose("instrument");
    const { container } = frame(false);
    const foot = container.querySelector<HTMLElement>(".frame-side-foot");
    expect(foot).not.toBeNull();
    expect(within(foot!).getByRole("link", { name: "Settings" })).toBeInTheDocument();
  });

  it("keeps the side column for a page without a workspace search in the rail arrangement", () => {
    choose("instrument");
    const { container } = frame(true);
    expect(container.querySelector(".app-shell")).toHaveClass("frame-rail", "app-shell-sided");
    expect(container.querySelector(".frame-side")).not.toBeNull();
    expect(container.querySelector(".frame-side-head")).not.toBeNull();
    expect(container.querySelector(".frame-side-foot")).not.toBeNull();
    expect(screen.queryByRole("textbox", { name: /Find in/ })).toBeNull();
    expect(screen.getByText("rail content")).toBeInTheDocument();
  });

  it.each<ColourScheme>(["studio", "instrument"])("keeps everything out of a side column on a phone, %s", (scheme) => {
    choose(scheme, true);
    const { container } = frame(true);
    expect(container.querySelector(".frame-side")).toBeNull();
    expect(container.querySelector(".frame-side-head")).toBeNull();
    expect(container.querySelector(".frame-side-foot")).toBeNull();
  });
});
