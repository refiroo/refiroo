// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const client = vi.hoisted(() => ({
  resetPage: vi.fn(),
  requestReset: vi.fn(),
  setPasswordWithLink: vi.fn(),
}));
vi.mock("@/api/signInClient", () => client);

const { ResetPasswordScreen } = await import("./ResetPasswordScreen");

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("the reset pages (0.12 I6)", () => {
  it("asks for a link by name and answers the same words the engine gave", async () => {
    client.resetPage.mockResolvedValue({ ok: true, product: "refiroo", available: true });
    client.requestReset.mockResolvedValue({ ok: true, message: "If there is an account, a link was sent." });
    render(<ResetPasswordScreen token="" />);
    fireEvent.change(await screen.findByLabelText("Username or e-mail address"), { target: { value: " ada " } });
    fireEvent.click(screen.getByRole("button", { name: "Mail me a link" }));
    await screen.findByText("If there is an account, a link was sent.");
    expect(client.requestReset).toHaveBeenCalledWith("ada");
    expect(screen.getByRole("link", { name: "Back to sign in" }).getAttribute("href")).toBe("/");
  });

  it("says how long to wait when the asks are slowed", async () => {
    client.resetPage.mockResolvedValue({ ok: true, product: "refiroo", available: true });
    client.requestReset.mockResolvedValue({
      ok: false,
      error: "slowed",
      message: "Too many requests for this account or from this address. You can try again in 5 seconds.",
      waitSeconds: 130,
    });
    render(<ResetPasswordScreen token="" />);
    fireEvent.change(await screen.findByLabelText("Username or e-mail address"), { target: { value: "ada" } });
    fireEvent.click(screen.getByRole("button", { name: "Mail me a link" }));
    await screen.findByText(/You can try again in 3 minutes\./);
  });

  it("offers no form where mail is not set up", async () => {
    client.resetPage.mockResolvedValue({ ok: true, product: "refiroo", available: false });
    render(<ResetPasswordScreen token="" />);
    await screen.findByText(/cannot be asked for by e-mail here/);
    expect(screen.queryByRole("button", { name: "Mail me a link" })).toBeNull();
  });

  it("sets a password with a link, shows the engine's refusal first, then the way back in", async () => {
    client.resetPage.mockResolvedValue({ ok: true, product: "refiroo", username: "ada", minLength: 12 });
    client.setPasswordWithLink
      .mockResolvedValueOnce({
        ok: false,
        error: "password_rejected",
        message: "A password needs at least 12 characters",
        waitSeconds: 0,
      })
      .mockResolvedValueOnce({ ok: true });
    render(<ResetPasswordScreen token="tok" />);
    await screen.findByText("ada");
    fireEvent.change(screen.getByLabelText("New password"), { target: { value: "short" } });
    fireEvent.change(screen.getByLabelText("Type it again"), { target: { value: "short" } });
    fireEvent.click(screen.getByRole("button", { name: "Set password" }));
    await screen.findByText("A password needs at least 12 characters");
    fireEvent.change(screen.getByLabelText("New password"), { target: { value: "a long enough one" } });
    fireEvent.change(screen.getByLabelText("Type it again"), { target: { value: "a long enough one" } });
    fireEvent.click(screen.getByRole("button", { name: "Set password" }));
    await screen.findByText(/Your password is set/);
    expect(client.setPasswordWithLink).toHaveBeenLastCalledWith("tok", "a long enough one", "a long enough one");
    expect(screen.getByRole("link", { name: "Sign in" }).getAttribute("href")).toBe("/");
  });

  it("explains a link that no longer works and offers a new one", async () => {
    client.resetPage.mockResolvedValue({
      ok: false,
      error: "link_gone",
      message: "This link has been used, replaced by a newer one, or has expired. Ask for a new one.",
      waitSeconds: 0,
    });
    render(<ResetPasswordScreen token="old" />);
    await screen.findByText(/has been used, replaced by a newer one/);
    expect(screen.getByRole("heading", { name: "This link no longer works" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Ask for a new link" }).getAttribute("href")).toBe("/reset-password");
    await waitFor(() => expect(client.resetPage).toHaveBeenCalledWith("old"));
  });

  it("reports an engine that cannot be reached", async () => {
    client.resetPage.mockRejectedValue(new Error("down"));
    render(<ResetPasswordScreen token="" />);
    await screen.findByText(/did not answer/);
  });
});
