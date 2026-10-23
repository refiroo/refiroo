import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
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
      username: "ana",
      email: "ana@example.org",
      lastSignInAt: null,
      signedInWith: "password",
      sessionId: "s1",
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

function openMenu(onOpenSettings = vi.fn(), onOpenAccount = vi.fn()) {
  render(
    <AccountMenu
      settingsHref="/settings/about"
      accountHref="/settings/account"
      onOpenSettings={onOpenSettings}
      onOpenAccount={onOpenAccount}
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
