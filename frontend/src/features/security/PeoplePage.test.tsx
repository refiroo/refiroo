import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/api/errors";
import { security } from "@/api/securityClient";
import { ToastProvider } from "@/ui/Toast";
import { PeoplePage } from "./PeoplePage";

vi.mock("@/api/securityClient", () => ({
  security: {
    users: vi.fn(async () => ({ items: [], nextCursor: null, totalCount: 0 })),
    createUser: vi.fn(),
    passwordLink: vi.fn(),
  },
}));

function openNewPerson() {
  render(
    <ToastProvider>
      <PeoplePage route={{ kind: "settings", page: "people" }} onNavigate={vi.fn()} />
    </ToastProvider>,
  );
  fireEvent.click(screen.getByRole("button", { name: "New person" }));
  return screen.getByRole("dialog", { name: "New person" });
}

beforeEach(() => vi.clearAllMocks());

describe("New person (0.12 SP1: a refusal said only 'Request validation failed')", () => {
  it("says a username has no spaces as it is typed, and sends nothing", () => {
    const dialog = openNewPerson();
    fireEvent.change(within(dialog).getByLabelText("Username"), { target: { value: "user 1" } });
    fireEvent.change(within(dialog).getByLabelText("Name"), { target: { value: "User One" } });
    const username = within(dialog).getByLabelText("Username");
    expect(username).toHaveAttribute("aria-invalid", "true");
    expect(within(dialog).getByText(/A username has no spaces/)).toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: "Create and make a password link" })).toBeDisabled();
    expect(security.createUser).not.toHaveBeenCalled();
  });

  it("shows the engine's refusal under the field it names", async () => {
    vi.mocked(security.createUser).mockRejectedValue(
      new ApiError(422, "REQUEST_VALIDATION_ERROR", "Request validation failed", [
        { loc: ["body", "email"], msg: "String should match pattern '^[^@\\s]+@[^@\\s]+$'" },
      ]),
    );
    const dialog = openNewPerson();
    fireEvent.change(within(dialog).getByLabelText("Username"), { target: { value: "user1" } });
    fireEvent.change(within(dialog).getByLabelText("Name"), { target: { value: "User One" } });
    fireEvent.change(within(dialog).getByLabelText("E-mail (optional)"), { target: { value: "not an e-mail" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Create and make a password link" }));
    expect(await within(dialog).findByText("An e-mail address looks like name@example.org.")).toBeInTheDocument();
    expect(within(dialog).getByLabelText("E-mail (optional)")).toHaveAttribute("aria-invalid", "true");
    expect(within(dialog).queryByText("Request validation failed")).toBeNull();
  });
});
