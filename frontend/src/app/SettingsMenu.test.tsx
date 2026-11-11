import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { signOut } from "@/api/session";
import { AccountMenu } from "@/app/SettingsMenu";
import { resetThemePreference, THEME_STORAGE_KEY } from "@/lib/theme";

vi.mock("@/api/client", () => ({
  api: {
    me: vi.fn(async () => ({
      id: "u1",
      kind: "user",
      name: "Ana Ferreira",
      email: "ana@example.org",
      lastSignInAt: null,
      signedInWith: "password",
      sessionId: "s1",
      signInManaged: false,
    })),
    system: vi.fn(async () => ({
      engine: {
        version: "0.16.0",
        managementApi: "v1",
        license: "AGPL-3.0-or-later",
        sourceCode: "https://github.com/refiroo/refiroo/tree/v0.16.0",
      },
    })),
    myPermissions: vi.fn(async (workspaceKey?: string) => ({
      workspaceKey: workspaceKey ?? "default",
      workspaceLabel: workspaceKey === "field" ? "Field stations" : "Herbarium",
      roles: workspaceKey === "field" ? [] : [{ key: "steward", name: "Data steward" }],
      actionGroups: [],
    })),
  },
}));
vi.mock("@/api/session", () => ({ signOut: vi.fn(async () => undefined) }));

beforeEach(() => {
  const values = new Map<string, string>();
  vi.stubGlobal("localStorage", {
    getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => values.set(key, value),
    removeItem: (key: string) => values.delete(key),
  });
  resetThemePreference();
});
afterEach(() => {
  delete document.documentElement.dataset.theme;
  vi.unstubAllGlobals();
});

/** A pointer press as a browser makes it: focus moves to the button before the click. */
function press(button: HTMLElement) {
  fireEvent.pointerDown(button);
  act(() => button.focus());
  fireEvent.click(button);
}

function openMenu(
  onOpenSettings = vi.fn(),
  onOpenAccount = vi.fn(),
  workspaceKey?: string,
  onOpenNotifications = vi.fn(),
) {
  render(
    <AccountMenu
      workspaceKey={workspaceKey}
      settingsHref="/settings/about"
      accountHref="/settings/account"
      notificationsHref="/notifications"
      onOpenSettings={onOpenSettings}
      onOpenAccount={onOpenAccount}
      onOpenNotifications={onOpenNotifications}
    />,
  );
  fireEvent.click(screen.getByRole("button", { name: "Account" }));
  return onOpenSettings;
}

describe("AccountMenu", () => {
  it("names the person, signs out, and persists the theme choice (0.12 I2)", async () => {
    openMenu();
    await screen.findByRole("dialog", { name: "Account" });
    expect(await screen.findByText("Ana Ferreira")).toBeInTheDocument();
    expect(screen.getByText("ana@example.org")).toBeInTheDocument();
    expect(api.me).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole("button", { name: "Sign out" }));
    expect(signOut).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("radio", { name: "System" })).toBeChecked();

    fireEvent.click(screen.getByRole("radio", { name: "Dark" }));
    expect(document.documentElement.dataset.theme).toBe("dark");
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe('"dark"');

    fireEvent.click(screen.getByRole("radio", { name: "System" }));
    expect(document.documentElement.dataset.theme).toBeUndefined();
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe('"system"');
  });

  it("restores a saved choice and ignores an invalid one", async () => {
    window.localStorage.setItem(THEME_STORAGE_KEY, '"light"');
    openMenu();
    expect(await screen.findByRole("radio", { name: "Light" })).toBeChecked();
    cleanup();
    resetThemePreference();
    window.localStorage.setItem(THEME_STORAGE_KEY, '"sepia"');
    openMenu();
    expect(await screen.findByRole("radio", { name: "System" })).toBeChecked();
  });

  it("links to the person's Account page and closes when it is followed", async () => {
    const onOpenAccount = vi.fn();
    openMenu(vi.fn(), onOpenAccount);
    const link = await screen.findByRole("link", { name: "Account" });
    expect(link).toHaveAttribute("href", "/settings/account");
    fireEvent.click(link);
    expect(onOpenAccount).toHaveBeenCalledTimes(1);
    await waitFor(() => expect(screen.queryByRole("dialog", { name: "Account" })).not.toBeInTheDocument());
  });

  it("links a person to their Notifications and closes when it is followed (0.12 NT1)", async () => {
    const onOpenNotifications = vi.fn();
    openMenu(vi.fn(), vi.fn(), undefined, onOpenNotifications);
    const link = await screen.findByRole("link", { name: /^Notifications/ });
    expect(link).toHaveAttribute("href", "/notifications");
    expect(link).toHaveClass("secondary", "account-menu-action");
    fireEvent.click(link);
    expect(onOpenNotifications).toHaveBeenCalledTimes(1);
    await waitFor(() => expect(screen.queryByRole("dialog", { name: "Account" })).not.toBeInTheDocument());
  });

  it("offers the source and the licence from every page (AGPL section 13, 0.12 L1)", async () => {
    openMenu();
    const link = await screen.findByRole("link", { name: "Source code" });
    expect(link).toHaveAttribute("href", "https://github.com/refiroo/refiroo/tree/v0.16.0");
    expect(link.closest("p")).toHaveTextContent("AGPL-3.0-or-later");
  });

  it("links to all settings and closes when it is followed", async () => {
    const onOpenSettings = openMenu();
    const link = await screen.findByRole("link", { name: "All settings" });
    expect(link).toHaveAttribute("href", "/settings/about");
    fireEvent.click(link);
    expect(onOpenSettings).toHaveBeenCalledTimes(1);
    await waitFor(() => expect(screen.queryByRole("dialog", { name: "Account" })).not.toBeInTheDocument());
  });

  it("leaves the page live: a press outside closes it and reaches its target (UA0)", async () => {
    const onPress = vi.fn();
    render(
      <button type="button" onClick={onPress}>
        Outside
      </button>,
    );
    openMenu();
    await screen.findByRole("dialog", { name: "Account" });
    const outside = screen.getByRole("button", { name: "Outside" });
    expect(outside.closest("[inert]")).toBeNull();
    fireEvent.pointerDown(outside);
    fireEvent.click(outside);
    expect(onPress).toHaveBeenCalledTimes(1);
    await waitFor(() => expect(screen.queryByRole("dialog", { name: "Account" })).not.toBeInTheDocument());
  });

  it("closes on a second press of its button (the user, 2026-10-28)", async () => {
    openMenu();
    // Opened, the menu holds focus, as in a browser; the second press takes it to the button.
    const menu = await screen.findByRole("dialog", { name: "Account" });
    act(() => menu.focus());
    const button = screen.getByRole("button", { name: "Account" });
    press(button);
    await waitFor(() => expect(screen.queryByRole("dialog", { name: "Account" })).not.toBeInTheDocument());
    press(button);
    expect(await screen.findByRole("dialog", { name: "Account" })).toBeInTheDocument();
  });

  it("stays open for a press inside and closes on Escape", async () => {
    openMenu();
    const dialog = await screen.findByRole("dialog", { name: "Account" });
    fireEvent.pointerDown(screen.getByRole("radio", { name: "Dark" }));
    expect(dialog).toBeInTheDocument();
    fireEvent.keyDown(dialog, { key: "Escape" });
    await waitFor(() => expect(screen.queryByRole("dialog", { name: "Account" })).not.toBeInTheDocument());
  });

  it("stays open through a scroll the layout causes and closes on the user's own (UA0)", async () => {
    render(<p>Page</p>);
    openMenu();
    const dialog = await screen.findByRole("dialog", { name: "Account" });
    fireEvent.scroll(document);
    expect(dialog).toBeInTheDocument();
    fireEvent.wheel(screen.getByText("Page"));
    await waitFor(() => expect(screen.queryByRole("dialog", { name: "Account" })).not.toBeInTheDocument());
  });
});

describe("the account menu's roles and actions (0.12 Z1)", () => {
  it("names the roles held in the workspace open now", async () => {
    openMenu();
    expect(await screen.findByText("Data steward in Herbarium")).toBeInTheDocument();
    expect(api.myPermissions).toHaveBeenCalledWith(undefined);
    cleanup();
    openMenu(vi.fn(), vi.fn(), "field");
    expect(await screen.findByText("No role in Field stations")).toBeInTheDocument();
  });

  it("draws Account, All settings and Sign out alike, as buttons", async () => {
    openMenu();
    const actions = [
      await screen.findByRole("link", { name: "Account" }),
      screen.getByRole("link", { name: "All settings" }),
      screen.getByRole("button", { name: "Sign out" }),
    ];
    for (const action of actions) expect(action).toHaveClass("secondary", "account-menu-action");
  });
});
