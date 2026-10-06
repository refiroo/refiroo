import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { testModel } from "@/test/fixtures";
import { SettingsShell } from "@/app/SettingsShell";
import { AboutPage } from "@/features/settings/AboutPage";
import { AppearancePage } from "@/features/settings/AppearancePage";
import { DeploymentPage } from "@/features/settings/DeploymentPage";
import { TABLE_DENSITY_STORAGE_KEY } from "@/lib/tableDensity";
import { resetThemePreference, THEME_STORAGE_KEY } from "@/lib/theme";
import { capabilitiesFixture } from "@/test/capabilities";
import type { SystemResponse, SystemSetting } from "@/types";

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
  engine: { version: "0.9.0-alpha.1", managementApi: "v1" },
  schemaLanguages: ["0.7", "0.8"],
  activeModelRelease: {
    id: "r1",
    key: "starter",
    name: "Starter",
    version: "0.9.0",
    schemaVersion: "0.8",
    activatedAt: "2026-10-06T08:00:00Z",
  },
  database: { revision: "20261005_02" },
  settings: [
    setting("DATABASE_URL", "runtime", "postgresql+psycopg://rdm@db:5432/rdm", "environment"),
    { ...setting("RDM_CURSOR_SIGNING_KEY", "runtime", null, "default") },
    { ...setting("CORS_ORIGINS", "runtime", ["https://a.example", "https://b.example"], "environment") },
    { ...setting("MODEL_ADMIN_MUTATIONS_ENABLED", "capabilities", true, "environment"), default: false },
    setting("FEED_RETENTION_DAYS", "limits", 30, "default"),
    { ...setting("CONSUMER_WEBHOOK_KEY_ENCRYPTION_KEY", "webhooks", null, "environment") },
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
  // The navigation drawer asks whether the screen is narrow; these tests render the wide layout.
  vi.stubGlobal(
    "matchMedia",
    vi.fn(() => ({ matches: false, addEventListener: vi.fn(), removeEventListener: vi.fn() })),
  );
  vi.mocked(api.system).mockResolvedValue(system);
  vi.mocked(api.capabilities).mockResolvedValue(capabilitiesFixture({ manageModel: true }));
});
afterEach(() => {
  delete document.documentElement.dataset.theme;
  vi.unstubAllGlobals();
});

describe("SettingsShell", () => {
  function renderShell(onNavigate = vi.fn(), onSelectApplication = vi.fn(), onHome = vi.fn()) {
    render(
      <SettingsShell
        model={testModel}
        page="deployment"
        onHome={onHome}
        onSelectApplication={onSelectApplication}
        onNavigate={onNavigate}
      >
        <p>Page</p>
      </SettingsShell>,
    );
    return { onNavigate, onSelectApplication, onHome };
  }

  it("lists the built pages by group and marks the current one", () => {
    const { onNavigate } = renderShell();
    const navigation = screen.getByRole("navigation", { name: "Settings" });
    expect(
      within(navigation)
        .getAllByRole("heading")
        .map((heading) => heading.textContent),
    ).toEqual(["General", "Administration"]);
    expect(
      within(navigation)
        .getAllByRole("link")
        .map((link) => link.textContent),
    ).toEqual(["About", "Appearance", "Workspaces", "Model", "Deployment"]);
    expect(within(navigation).getByRole("link", { name: "Deployment" })).toHaveAttribute("aria-current", "page");
    expect(within(navigation).getByRole("link", { name: "About" })).not.toHaveAttribute("aria-current");
    fireEvent.click(within(navigation).getByRole("link", { name: "Model" }));
    expect(onNavigate).toHaveBeenCalledWith({ kind: "settings", page: "model" });
  });

  it("shows the application pages' top bar: home, the applications with none current, Settings current", () => {
    const { onSelectApplication, onHome } = renderShell();
    const toggle = screen.getByRole("button", { name: "Settings: Deployment" });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(toggle).toHaveAttribute("aria-controls", "settings-navigation");
    const tabs = within(screen.getByRole("navigation", { name: "Applications" })).getAllByRole("button");
    expect(tabs.map((tab) => tab.textContent)).toEqual(testModel.applications.map((item) => item.name));
    expect(tabs.every((tab) => !tab.hasAttribute("aria-current"))).toBe(true);
    expect(screen.getByRole("link", { name: "Settings" })).toHaveAttribute("aria-current", "page");
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
    const release = screen.getByRole("region", { name: "Active model release" });
    expect(release).toHaveTextContent(/Starter.*starter.*0\.9\.0.*0\.8/);
    expect(screen.getByRole("region", { name: "Database" })).toHaveTextContent("20261005_02");
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
    expect(within(groups).getByText("Model administration").closest("li")).toHaveTextContent(
      /On\s*MODEL_ADMIN_MUTATIONS_ENABLED/,
    );
    expect(within(groups).getByText("Webhook subscriptions").closest("li")).toHaveTextContent(
      /Off\s*CONSUMER_SUBSCRIPTIONS_ENABLED/,
    );
    expect(within(groups).getByText("Integration jobs").closest("li")).toHaveTextContent("1,000 items, 5 MB");
    const runtime = screen.getByRole("region", { name: "Runtime" });
    const row = (region: HTMLElement, name: string) => within(region).getByRole("row", { name: new RegExp(name) });
    expect(row(runtime, "CORS_ORIGINS")).toHaveTextContent(/https:\/\/a\.example, https:\/\/b\.example.*Environment/);
    expect(row(runtime, "DATABASE_URL")).toHaveTextContent("postgresql+psycopg://rdm@db:5432/rdm");
    const capabilitySettings = screen.getByRole("region", { name: "Capability settings" });
    expect(row(capabilitySettings, "MODEL_ADMIN")).toHaveTextContent(/On\s*Off\s*Environment/);
    expect(row(screen.getByRole("region", { name: "Batch and job limits" }), "FEED")).toHaveTextContent(
      /30\s*30\s*Default/,
    );
    expect(screen.getByText(/Values come from|values come from/)).toBeInTheDocument();
    expect(screen.getByText("VITE_API_URL")).toBeInTheDocument();
  });

  it("shows a secret only as set or not set, and warns about an ephemeral cursor key", async () => {
    render(<DeploymentPage />);
    const runtime = await screen.findByRole("region", { name: "Runtime" });
    expect(within(runtime).getByRole("row", { name: /RDM_CURSOR_SIGNING_KEY/ })).toHaveTextContent(
      /Not set\s*None\s*Default/,
    );
    expect(within(runtime).getByText("Cursors do not survive a restart")).toBeInTheDocument();
    const webhooks = screen.getByRole("region", { name: "Webhook subscriptions" });
    expect(within(webhooks).getByRole("row", { name: /KEY_ENCRYPTION_KEY/ })).toHaveTextContent(
      /Set\s*None\s*Environment/,
    );
  });

  it("leaves out the warning once the cursor key is set", async () => {
    vi.mocked(api.system).mockResolvedValue({
      ...system,
      settings: system.settings.map((item) =>
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
    const theme = screen.getByRole("group", { name: "Theme" });
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
});
