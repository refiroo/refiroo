import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { ApiError } from "@/api/errors";
import { FollowToggle } from "@/features/home/HomePage";
import type { OwnWorkspace } from "@/types";

vi.mock("@/api/client", () => ({ api: { followWorkspace: vi.fn(), unfollowWorkspace: vi.fn() } }));

const workspace = (following: boolean) => ({ key: "default", label: "Master data", following }) as OwnWorkspace;

describe("Follow on a workspace card (0.16 AO3, AO-D38)", () => {
  beforeEach(() => vi.resetAllMocks());

  it("follows at once, shows Following as pressed, and stops following again", async () => {
    vi.mocked(api.followWorkspace).mockResolvedValue({ workspaceKey: "default", label: "Master data", since: "" });
    vi.mocked(api.unfollowWorkspace).mockResolvedValue(undefined);
    render(<FollowToggle workspace={workspace(false)} />);
    const button = screen.getByRole("button", { name: "Follow Master data" });
    expect(button).toHaveAttribute("aria-pressed", "false");
    expect(button).toHaveTextContent("Follow");
    fireEvent.click(button);
    await waitFor(() => expect(api.followWorkspace).toHaveBeenCalledWith("default"));
    await waitFor(() => expect(button).toHaveAttribute("aria-pressed", "true"));
    expect(button).toHaveTextContent("Following");
    fireEvent.click(button);
    await waitFor(() => expect(api.unfollowWorkspace).toHaveBeenCalledWith("default"));
    await waitFor(() => expect(button).toHaveAttribute("aria-pressed", "false"));
  });

  it("starts as Following for a followed workspace", () => {
    render(<FollowToggle workspace={workspace(true)} />);
    // The name holds the visible word, then the workspace.
    expect(screen.getByRole("button", { name: "Following Master data" })).toHaveAttribute("aria-pressed", "true");
  });

  it("says why it could not and stays as it was", async () => {
    vi.mocked(api.followWorkspace).mockRejectedValue(
      new ApiError(404, "NOT_FOUND", "There is no such workspace you may browse"),
    );
    render(<FollowToggle workspace={workspace(false)} />);
    fireEvent.click(screen.getByRole("button", { name: "Follow Master data" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("no such workspace");
    expect(screen.getByRole("button", { name: "Follow Master data" })).toHaveAttribute("aria-pressed", "false");
  });
});
