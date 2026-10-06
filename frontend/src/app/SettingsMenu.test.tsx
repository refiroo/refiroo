import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AccountMenu } from "@/app/SettingsMenu";
import { resetThemePreference, THEME_STORAGE_KEY } from "@/lib/theme";

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

function openMenu(onOpenSettings = vi.fn()) {
  render(<AccountMenu settingsHref="/settings/about" onOpenSettings={onOpenSettings} />);
  fireEvent.click(screen.getByRole("button", { name: "Account" }));
  return onOpenSettings;
}

describe("AccountMenu", () => {
  it("offers an account placeholder and persists the theme choice", async () => {
    openMenu();
    await screen.findByRole("dialog", { name: "Account" });
    expect(screen.getByRole("button", { name: "Sign in" })).toBeDisabled();
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

  it("links to all settings and closes when it is followed", async () => {
    const onOpenSettings = openMenu();
    const link = await screen.findByRole("link", { name: "All settings" });
    expect(link).toHaveAttribute("href", "/settings/about");
    fireEvent.click(link);
    expect(onOpenSettings).toHaveBeenCalledTimes(1);
    await waitFor(() => expect(screen.queryByRole("dialog", { name: "Account" })).not.toBeInTheDocument());
  });
});
