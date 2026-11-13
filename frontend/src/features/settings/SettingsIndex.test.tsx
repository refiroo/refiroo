import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { SettingsIndex } from "@/features/settings/SettingsIndex";
import { resetPermissionsForTests } from "@/state/permissions";
import { EVERY_GROUP, heldAnywhereFixture } from "@/test/permissions";

afterEach(() => {
  vi.restoreAllMocks();
  resetPermissionsForTests();
});

describe("SettingsIndex (0.17 SH1)", () => {
  it("lists every page by task, with About last in This instance", async () => {
    vi.spyOn(api, "myActionGroups").mockResolvedValue(heldAnywhereFixture(EVERY_GROUP));
    render(<SettingsIndex onNavigate={vi.fn()} />);
    const instance = await screen.findByRole("region", { name: "This instance" });
    const links = within(instance).getAllByRole("link");
    expect(links.at(-1)).toHaveTextContent("About");
    expect(screen.getAllByRole("heading", { level: 2 }).map((heading) => heading.textContent)).toEqual([
      "You",
      "Workspaces and models",
      "People and access",
      "Connections",
      "This instance",
    ]);
    expect(within(await screen.findByRole("region", { name: "Connections" })).getAllByRole("link")).toHaveLength(5);
  });

  it("leaves out a page the person may not open and a group left with none", async () => {
    vi.spyOn(api, "myActionGroups").mockResolvedValue(heldAnywhereFixture(["browse"]));
    const onNavigate = vi.fn();
    render(<SettingsIndex onNavigate={onNavigate} />);
    await screen.findByRole("region", { name: "You" });
    expect(screen.queryByRole("region", { name: "People and access" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Model" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("link", { name: "Appearance" }));
    expect(onNavigate).toHaveBeenCalledWith({ kind: "settings", page: "appearance" });
  });
});
