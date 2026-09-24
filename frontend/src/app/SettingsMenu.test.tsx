import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { SettingsMenu } from "@/app/SettingsMenu";
import { THEME_STORAGE_KEY } from "@/lib/theme";

beforeEach(() => {
  const values = new Map<string, string>();
  vi.stubGlobal("localStorage", {
    getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => values.set(key, value),
    removeItem: (key: string) => values.delete(key),
  });
});
afterEach(() => {
  delete document.documentElement.dataset.theme;
  vi.unstubAllGlobals();
});

describe("SettingsMenu", () => {
  it("offers an account placeholder and persists the appearance choice", async () => {
    render(<SettingsMenu />);
    fireEvent.click(screen.getByRole("button", { name: "Settings" }));
    await screen.findByRole("dialog", { name: "Settings" });
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
    const { unmount } = render(<SettingsMenu />);
    fireEvent.click(screen.getByRole("button", { name: "Settings" }));
    expect(await screen.findByRole("radio", { name: "Light" })).toBeChecked();
    unmount();
    window.localStorage.setItem(THEME_STORAGE_KEY, '"sepia"');
    render(<SettingsMenu />);
    fireEvent.click(screen.getByRole("button", { name: "Settings" }));
    expect(await screen.findByRole("radio", { name: "System" })).toBeChecked();
  });
});
