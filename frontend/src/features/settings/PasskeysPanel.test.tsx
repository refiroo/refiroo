import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { addPasskey } from "@/api/session";
import { ToastProvider } from "@/ui/Toast";
import { PasskeysPanel } from "./PasskeysPanel";

vi.mock("@/api/client", () => ({
  api: {
    myPasskeys: vi.fn(),
    renamePasskey: vi.fn(),
    removePasskey: vi.fn(),
  },
}));
vi.mock("@/api/session", () => ({ addPasskey: vi.fn(() => new Promise(() => undefined)) }));

const laptop = {
  id: "p1",
  name: "MacBook Touch ID",
  createdAt: "2026-10-25T08:00:00Z",
  lastUsedAt: "2026-10-25T09:00:00Z",
};
const key = { id: "p2", name: "YubiKey 5C", createdAt: "2026-10-25T08:30:00Z", lastUsedAt: null };

function show() {
  render(
    <ToastProvider>
      <PasskeysPanel />
    </ToastProvider>,
  );
}

beforeEach(() => vi.clearAllMocks());

describe("Account's passkeys (0.12 I4c)", () => {
  it("lists them by name, says which were never used, and leaves for the engine's page to add one", async () => {
    vi.mocked(api.myPasskeys).mockResolvedValue([laptop, key]);
    show();
    const list = await screen.findByRole("list", { name: "Your passkeys" });
    expect(within(list).getByText("MacBook Touch ID")).toBeInTheDocument();
    expect(within(list).getByText(/not used yet/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Add a passkey/ }));
    expect(addPasskey).toHaveBeenCalledTimes(1);
  });

  it("renames one, and removes one after a confirmation", async () => {
    vi.mocked(api.myPasskeys).mockResolvedValue([laptop]);
    vi.mocked(api.renamePasskey).mockResolvedValue({ ...laptop, name: "Work laptop" });
    vi.mocked(api.removePasskey).mockResolvedValue(undefined);
    show();
    fireEvent.click(await screen.findByRole("button", { name: "Rename MacBook Touch ID" }));
    const dialog = screen.getByRole("dialog", { name: "Rename MacBook Touch ID" });
    fireEvent.change(within(dialog).getByLabelText("Name"), { target: { value: "Work laptop" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Save" }));
    await waitFor(() => expect(api.renamePasskey).toHaveBeenCalledWith("p1", "Work laptop"));

    fireEvent.click(await screen.findByRole("button", { name: "Remove MacBook Touch ID" }));
    const removal = screen.getByRole("dialog", { name: "Remove MacBook Touch ID?" });
    expect(within(removal).getByRole("button", { name: "Remove passkey" })).toBeDisabled();
    fireEvent.change(within(removal).getByLabelText(/Your password, or a code/), { target: { value: "secret" } });
    fireEvent.click(within(removal).getByRole("button", { name: "Remove passkey" }));
    await waitFor(() => expect(api.removePasskey).toHaveBeenCalledWith("p1", "secret"));
  });
});
