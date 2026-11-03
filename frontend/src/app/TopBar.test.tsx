import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { TopBar } from "@/app/TopBar";
import type { EngineModel } from "@/types";

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
