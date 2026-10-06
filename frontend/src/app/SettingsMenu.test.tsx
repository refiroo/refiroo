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
