import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { testModel } from "@/test/fixtures";
import { SettingsShell } from "@/app/SettingsShell";
import { AboutPage } from "@/features/settings/AboutPage";
import { AppearancePage } from "@/features/settings/AppearancePage";
import { EDIT_HINT_STORAGE_KEY } from "@/lib/editHint";
import { PALETTE_STORAGE_KEY, resetPalettePreference } from "@/lib/palette";
import { DeploymentPage } from "@/features/settings/DeploymentPage";
import { TABLE_DENSITY_STORAGE_KEY } from "@/lib/tableDensity";
import { resetSchemePreference, SCHEME_STORAGE_KEY } from "@/lib/scheme";
import { resetThemePreference, THEME_STORAGE_KEY } from "@/lib/theme";
import { capabilitiesFixture } from "@/test/capabilities";
import { EVERY_GROUP, heldAnywhereFixture } from "@/test/permissions";
import type { SystemConfiguration, SystemResponse, SystemSetting } from "@/types";

vi.mock("@/api/client", async (load) => {
  const actual = await load<typeof import("@/api/client")>();
  return { ...actual, api: Object.fromEntries(Object.keys(actual.api).map((key) => [key, vi.fn()])) };
});

const setting = (name: string, group: SystemSetting["group"], value: unknown, source: SystemSetting["source"]) => ({
  name,
  group,
  description: `What ${name} controls`,
  value,
  default: value,
  source,
});

const system: SystemResponse = {
  engine: {
    version: "0.9.0-alpha.1",
    managementApi: "v1",
    license: "AGPL-3.0-or-later",
    sourceCode: "https://github.com/refiroo/refiroo/tree/v0.9.0-alpha.1",
    build: { commit: "baf823b6", tag: "v0.9.0-alpha.1" },
  },
  schemaLanguages: ["0.7", "0.8"],
  activeModelRelease: {
    id: "r1",
    key: "starter",
    name: "Starter",
    version: "0.9.0",
    schemaVersion: "0.8",
    activatedAt: "2026-10-06T08:00:00Z",
  },
  ai: { configured: false, provider: null, sendLevel: "structure" },
  mcp: { enabled: false },
};

const configuration: SystemConfiguration = {
  database: { revision: "20261005_02" },
  settings: [
    setting("DATABASE_URL", "runtime", "postgresql+psycopg://rdm@db:5432/rdm", "environment"),
    { ...setting("RDM_CURSOR_SIGNING_KEY", "runtime", null, "default") },
    { ...setting("CORS_ORIGINS", "runtime", ["https://a.example", "https://b.example"], "environment") },
    { ...setting("MODEL_ADMIN_MUTATIONS_ENABLED", "capabilities", true, "environment"), default: false },
    setting("FEED_RETENTION_DAYS", "limits", 30, "default"),
    { ...setting("SECRETS_ENCRYPTION_KEY", "runtime", null, "environment") },
  ],
};

let stored: Map<string, string>;
beforeEach(() => {
  vi.clearAllMocks();
  stored = new Map();
  vi.stubGlobal("localStorage", {
    getItem: (key: string) => stored.get(key) ?? null,
    setItem: (key: string, value: string) => stored.set(key, value),
    removeItem: (key: string) => stored.delete(key),
  });
  resetThemePreference();
  resetSchemePreference();
  // The navigation drawer asks whether the screen is narrow; these tests render the wide layout.
  vi.stubGlobal(
    "matchMedia",
    vi.fn(() => ({ matches: false, addEventListener: vi.fn(), removeEventListener: vi.fn() })),
  );
  vi.mocked(api.system).mockResolvedValue(system);
  vi.mocked(api.systemConfiguration).mockResolvedValue(configuration);
  vi.mocked(api.capabilities).mockResolvedValue(capabilitiesFixture({ manageModel: true }));
  vi.mocked(api.myPermissions).mockResolvedValue(permissions([]));
  // Every group but Security administration somewhere (0.12 Z5, D328).
  vi.mocked(api.myActionGroups).mockResolvedValue(
    heldAnywhereFixture(EVERY_GROUP.filter((key) => key !== "security-admin")),
  );
});

/** The caller's permissions in the default workspace, holding `groups` (0.12 Z1). */
function permissions(groups: string[]) {
  return {
    workspaceKey: "default",
    workspaceLabel: "Default",
    roles: [],
    actionGroups: groups.map((key) => ({ key, name: key, applications: [], recordTypes: [], sources: [] })),
  };
}
afterEach(() => {
  delete document.documentElement.dataset.theme;
  delete document.documentElement.dataset.scheme;
  vi.unstubAllGlobals();
});

describe("SettingsShell", () => {
  function renderShell(onNavigate = vi.fn(), onSelectApplication = vi.fn(), onHome = vi.fn(), workspaceKey?: string) {
    render(
      <SettingsShell
        model={testModel}
        page="deployment"
        workspaceKey={workspaceKey}
        onHome={onHome}
        onSelectApplication={onSelectApplication}
        onNavigate={onNavigate}
      >
        <p>Page</p>
      </SettingsShell>,
    );
    return { onNavigate, onSelectApplication, onHome };
  }

  it("offers Back to the workspace in place of the application tabs, with the Settings icon current (0.17 SH1)", async () => {
    vi.spyOn(api, "workspace").mockResolvedValue({ key: "west", label: "West" } as never);
    const { onNavigate } = renderShell(undefined, undefined, undefined, "west");
    const banner = screen.getByRole("banner");
    const back = await within(banner).findByRole("link", { name: "Back to West" });
    expect(back).toHaveAttribute("href", "/workspace?workspaceKey=west");
    expect(within(banner).queryByRole("navigation", { name: "Applications" })).toBeNull();
    fireEvent.click(back);
    expect(onNavigate).toHaveBeenCalledWith({ kind: "workspace", workspaceKey: "west" });
    // The Settings icon is current in its own place, as the icon it is on every page.
    const settings = within(banner).getByRole("link", { name: "Settings" });
    expect(settings).toHaveAttribute("aria-current", "page");
    expect(settings).toHaveTextContent("");
  });

  it("lists the built pages by group and marks the current one", async () => {
    const { onNavigate } = renderShell();
    const navigation = screen.getByRole("navigation", { name: "Settings" });
    await within(navigation).findByRole("link", { name: "Webhooks" });
    expect(
      within(navigation)
        .getAllByRole("heading")
        .map((heading) => heading.textContent),
    ).toEqual(["You", "Workspaces and models", "Connections", "This instance"]);
    // The index first, then the pages by task, About last (0.17 SH1).
    expect(
      within(navigation)
        .getAllByRole("link")
        .map((link) => link.textContent),
    ).toEqual([
      "Settings",
      "Appearance",
      "Account",
      "Notification email",
      "Workspaces",
      "Model",
      "Import profiles",
      "Copy and move",
      "Consumer APIs",
      "Webhooks",
      "API reference",
      "Jobs",
      "Operations",
      "Deployment",
      "E-mail template",
      "AI",
      "About",
    ]);
    expect(within(navigation).getByRole("link", { name: "Deployment" })).toHaveAttribute("aria-current", "page");
    expect(within(navigation).getByRole("link", { name: "About" })).not.toHaveAttribute("aria-current");
    fireEvent.click(within(navigation).getByRole("link", { name: "Model" }));
    expect(onNavigate).toHaveBeenCalledWith({ kind: "settings", page: "model" });
  });

  it("lists only the pages of the groups a Reader holds (0.12 Z5, D328)", async () => {
    vi.mocked(api.myActionGroups).mockResolvedValue(heldAnywhereFixture(["browse"]));
    renderShell();
    const navigation = screen.getByRole("navigation", { name: "Settings" });
    await within(navigation).findByRole("link", { name: "Consumer APIs" });
    expect(
      within(navigation)
        .getAllByRole("link")
        .map((link) => link.textContent),
    ).toEqual([
      "Settings",
      "Appearance",
      "Account",
      "Notification email",
      "Workspaces",
      "Consumer APIs",
      "API reference",
      "Jobs",
      "About",
    ]);
    expect(
      within(navigation)
        .getAllByRole("heading")
        .map((heading) => heading.textContent),
    ).toEqual(["You", "Workspaces and models", "Connections", "This instance"]);
  });

  it("lists Security only to a person holding Security administration (0.12 SP1, D303)", async () => {
    vi.mocked(api.myActionGroups).mockResolvedValue(heldAnywhereFixture(["security-admin"]));
    renderShell();
    const navigation = screen.getByRole("navigation", { name: "Settings" });
    expect(await within(navigation).findByRole("heading", { name: "People and access" })).toBeInTheDocument();
    expect(within(navigation).getByRole("link", { name: "People" })).toHaveAttribute("href", "/settings/people");
    expect(within(navigation).getByRole("link", { name: "Groups" })).toBeInTheDocument();
    expect(within(navigation).getByRole("link", { name: "Roles" })).toBeInTheDocument();
  });

  it("shows the application tabs when no workspace is named: home, the applications with none current, Settings current", () => {
    const { onSelectApplication, onHome } = renderShell();
    const toggle = screen.getByRole("button", { name: "Settings: Deployment" });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(toggle).toHaveAttribute("aria-controls", "settings-navigation");
    const tabs = within(screen.getByRole("navigation", { name: "Applications" })).getAllByRole("button");
    expect(tabs.map((tab) => tab.textContent)).toEqual(testModel.applications.map((item) => item.name));
    expect(tabs.every((tab) => !tab.hasAttribute("aria-current"))).toBe(true);
    expect(within(screen.getByRole("banner")).getByRole("link", { name: "Settings" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    fireEvent.click(tabs[0]);
    expect(onSelectApplication).toHaveBeenCalledWith(testModel.applications[0]);
    fireEvent.click(screen.getByRole("button", { name: `${testModel.product.name} home` }));
    expect(onHome).toHaveBeenCalledTimes(1);
  });

  it("keeps the order skip link, top bar, navigation, content", () => {
    renderShell();
    const order = [
      screen.getByRole("link", { name: "Skip to main content" }),
      screen.getByRole("banner"),
      screen.getByRole("navigation", { name: "Settings" }),
      screen.getByRole("main"),
    ];
    for (let index = 1; index < order.length; index += 1)
      expect(order[index - 1].compareDocumentPosition(order[index]) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });
});

describe("About", () => {
  it("shows what the deployment runs and links to the active release", async () => {
    const onNavigate = vi.fn();
    render(<AboutPage onNavigate={onNavigate} />);
    expect(screen.getByRole("status", { name: /Loading/ })).toBeInTheDocument();
    const engine = await screen.findByRole("region", { name: "Engine" });
    expect(engine).toHaveTextContent("0.9.0-alpha.1");
    expect(engine).toHaveTextContent("0.7, 0.8");
    // The licence and where the source is (AGPL section 13, 0.12 L1).
    expect(engine).toHaveTextContent("AGPL-3.0-or-later");
    expect(within(engine).getByRole("link", { name: /github\.com\/refiroo\/refiroo/ })).toHaveAttribute(
      "href",
      "https://github.com/refiroo/refiroo/tree/v0.9.0-alpha.1",
    );
    // The build: the commit and tag, linked into the repository (0.13 BR).
    expect(within(engine).getByRole("link", { name: "baf823b6" })).toHaveAttribute(
      "href",
      "https://github.com/refiroo/refiroo/commit/baf823b6",
    );
    expect(within(engine).getByRole("link", { name: "v0.9.0-alpha.1" })).toHaveAttribute(
      "href",
      "https://github.com/refiroo/refiroo/releases/tag/v0.9.0-alpha.1",
    );
    // The help entry: the documentation the engine serves, then the API reference (0.13 DOC1).
    expect(screen.getByRole("link", { name: "documentation" })).toHaveAttribute(
      "href",
      expect.stringMatching(/\/docs\/$/),
    );
    expect(screen.getByRole("link", { name: "API reference" })).toHaveAttribute(
      "href",
      expect.stringMatching(/\/docs\/api$/),
    );
    const release = screen.getByRole("region", { name: "Active model release" });
    expect(release).toHaveTextContent(/Starter.*starter.*0\.9\.0.*0\.8/);
    // The migration revision is the operator's, on Deployment (0.12 D246).
    expect(screen.queryByRole("region", { name: "Database" })).toBeNull();
    fireEvent.click(within(release).getByRole("button", { name: "Open release" }));
    expect(onNavigate).toHaveBeenCalledWith({ kind: "settings", page: "model", releaseId: "r1" });
  });

  it("reports a failed read and retries it", async () => {
    vi.mocked(api.system).mockRejectedValueOnce(new Error("System unavailable"));
    render(<AboutPage onNavigate={vi.fn()} />);
    fireEvent.click(await screen.findByRole("button", { name: "Retry" }));
    expect(await screen.findByRole("region", { name: "Engine" })).toBeInTheDocument();
  });
});

describe("Deployment", () => {
  it("leads with the capability groups, then every setting by group with its source", async () => {
    render(<DeploymentPage />);
    const groups = await screen.findByRole("region", { name: "Capability groups" });
    const panel = (name: string) => within(groups).getByRole("group", { name });
    expect(panel("Model administration")).toHaveTextContent(/On\s*MODEL_ADMIN_MUTATIONS_ENABLED/);
    expect(panel("Webhook subscriptions")).toHaveTextContent(/Off\s*CONSUMER_SUBSCRIPTIONS_ENABLED/);
    expect(panel("Integration jobs")).toHaveTextContent("1,000 items, 5 MB");
    const runtime = screen.getByRole("region", { name: "Runtime" });
    // A setting is a row: its name and what it controls, its value, its default only where it differs, its source.
    const row = (region: HTMLElement, name: string) =>
      within(region).getByText(new RegExp(name), { selector: "code" }).closest(".setting-row") as HTMLElement;
    expect(row(runtime, "CORS_ORIGINS")).toHaveTextContent(/https:\/\/a\.example, https:\/\/b\.example.*Environment/);
    expect(row(runtime, "DATABASE_URL")).toHaveTextContent("postgresql+psycopg://rdm@db:5432/rdm");
    expect(screen.getByRole("region", { name: "Database" })).toHaveTextContent("20261005_02");
    const capabilitySettings = screen.getByRole("region", { name: "Capability settings" });
    expect(row(capabilitySettings, "MODEL_ADMIN")).toHaveTextContent(/On\s*Default Off\s*Environment/);
    // Where the value is the default, no default is shown.
    const limits = row(screen.getByRole("region", { name: "Batch and job limits" }), "FEED");
    expect(limits).toHaveTextContent(/30\s*Default/);
    expect(limits).not.toHaveTextContent(/Default 30/);
    expect(screen.getByText(/It calls the API at/)).toBeInTheDocument();
    expect(screen.getByText("VITE_API_URL")).toBeInTheDocument();
  });

  it("shows a secret only as set or not set, and warns about an ephemeral cursor key", async () => {
    render(<DeploymentPage />);
    const runtime = await screen.findByRole("region", { name: "Runtime" });
    const row = (name: string) =>
      within(runtime)
        .getAllByText(name, { selector: "code" })
        .map((code) => code.closest(".setting-row") as HTMLElement | null)
        .find(Boolean)!;
    expect(row("RDM_CURSOR_SIGNING_KEY")).toHaveTextContent(/Not set\s*Default/);
    expect(within(runtime).getByText("Cursors do not survive a restart")).toBeInTheDocument();
    expect(row("SECRETS_ENCRYPTION_KEY")).toHaveTextContent(/Set\s*Environment/);
    expect(row("SECRETS_ENCRYPTION_KEY")).not.toHaveTextContent(/Default None/);
  });

  it("leaves out the warning once the cursor key is set", async () => {
    vi.mocked(api.systemConfiguration).mockResolvedValue({
      ...configuration,
      settings: configuration.settings.map((item) =>
        item.name === "RDM_CURSOR_SIGNING_KEY" ? { ...item, source: "environment" } : item,
      ),
    });
    render(<DeploymentPage />);
    await screen.findByRole("region", { name: "Runtime" });
    expect(screen.queryByText("Cursors do not survive a restart")).not.toBeInTheDocument();
  });
});

describe("Appearance", () => {
  it("writes the theme and the default table density to this browser", () => {
    render(<AppearancePage />);
    // The colours are "Theme" (TH); light and dark are "Light or dark".
    const theme = screen.getByRole("group", { name: "Light or dark" });
    expect(within(theme).getByRole("radio", { name: "System" })).toBeChecked();
    fireEvent.click(within(theme).getByRole("radio", { name: "Dark" }));
    expect(stored.get(THEME_STORAGE_KEY)).toBe('"dark"');
    expect(document.documentElement.dataset.theme).toBe("dark");

    const density = screen.getByRole("group", { name: "Table density" });
    expect(within(density).getByRole("radio", { name: "Comfortable" })).toBeChecked();
    fireEvent.click(within(density).getByRole("radio", { name: "Compact" }));
    expect(stored.get(TABLE_DENSITY_STORAGE_KEY)).toBe('"compact"');
    expect(screen.getByText(/saved in this browser/)).toBeInTheDocument();
  });

  it("chooses Current or Website purple, saves it and sets data-scheme (TH)", () => {
    render(<AppearancePage />);
    const scheme = screen.getByRole("group", { name: "Theme" });
    expect(within(scheme).getByRole("radio", { name: "Current" })).toBeChecked();
    fireEvent.click(within(scheme).getByRole("radio", { name: "Website purple" }));
    expect(stored.get(SCHEME_STORAGE_KEY)).toBe('"purple"');
    expect(document.documentElement.dataset.scheme).toBe("purple");
    // The light and dark choice is its own.
    expect(
      within(screen.getByRole("group", { name: "Light or dark" })).getByRole("radio", { name: "System" }),
    ).toBeChecked();
    fireEvent.click(within(scheme).getByRole("radio", { name: "Current" }));
    expect(stored.get(SCHEME_STORAGE_KEY)).toBe('"normal"');
    expect(document.documentElement.dataset.scheme).toBeUndefined();
  });

  it("switches the type palette and saves it (UA4 revision)", () => {
    resetPalettePreference();
    render(<AppearancePage />);
    const palette = screen.getByRole("group", { name: "Type colours" });
    expect(within(palette).getByRole("radio", { name: "B: magenta and olive" })).toBeChecked();
    fireEvent.click(within(palette).getByRole("radio", { name: "A: plum and gold" }));
    expect(stored.get(PALETTE_STORAGE_KEY)).toBe('"a"');
    expect(document.documentElement.dataset.palette).toBe("a");
    fireEvent.click(within(palette).getByRole("radio", { name: "B: magenta and olive" }));
    expect(document.documentElement.dataset.palette).toBeUndefined();
    resetPalettePreference();
  });

  it("writes when editable fields show their pencil (UA4 revision)", () => {
    render(<AppearancePage />);
    const hint = screen.getByRole("group", { name: "Edit pencil" });
    expect(within(hint).getByRole("radio", { name: "On hover and focus" })).toBeChecked();
    fireEvent.click(within(hint).getByRole("radio", { name: "Always, faintly" }));
    expect(stored.get(EDIT_HINT_STORAGE_KEY)).toBe('"always"');
  });
});
