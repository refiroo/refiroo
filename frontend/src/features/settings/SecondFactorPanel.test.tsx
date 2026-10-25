import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { ApiError } from "@/api/errors";
import { ToastProvider } from "@/ui/Toast";
import { SecondFactorPanel, groupedKey } from "./SecondFactorPanel";

vi.mock("@/api/client", () => ({
  api: {
    mySecondFactor: vi.fn(),
    startSecondFactor: vi.fn(),
    confirmSecondFactor: vi.fn(),
    newRecoveryCodes: vi.fn(),
    removeMySecondFactor: vi.fn(),
  },
}));

const off = { enabled: false, confirmedAt: null, recoveryCodesLeft: 0, passkeys: 0, required: false };
const on = {
  enabled: true,
  confirmedAt: "2026-10-25T10:00:00Z",
  recoveryCodesLeft: 8,
  passkeys: 0,
  required: false,
};

function show() {
  render(
    <ToastProvider>
      <SecondFactorPanel />
    </ToastProvider>,
  );
}

beforeEach(() => vi.clearAllMocks());

describe("Account's second factor (0.12 I4b)", () => {
  it("groups the key in fours, as an authenticator app shows it", () => {
    expect(groupedKey("JBSWY3DPEHPK3PXP4Q2M")).toBe("JBSW Y3DP EHPK 3PXP 4Q2M");
    expect(groupedKey("ABC")).toBe("ABC");
  });

  it("sets up with a code and shows the recovery codes once", async () => {
    vi.mocked(api.mySecondFactor).mockResolvedValue(off);
    vi.mocked(api.startSecondFactor).mockResolvedValue({
      secret: "JBSWY3DPEHPK3PXP4Q2M",
      otpauthUri: "otpauth://totp/x",
      qrSvg: "<svg xmlns='http://www.w3.org/2000/svg'/>",
    });
    vi.mocked(api.confirmSecondFactor)
      .mockRejectedValueOnce(new ApiError(422, "CODE_INCORRECT", "That code is not right, or was already used"))
      .mockResolvedValueOnce({ recoveryCodes: ["aaaa-bbbb-cccc", "dddd-eeee-ffff"] });
    show();
    fireEvent.click(await screen.findByRole("button", { name: "Set up an authenticator app" }));
    expect(await screen.findByText("JBSW Y3DP EHPK 3PXP 4Q2M")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "QR code for the authenticator app" })).toHaveAttribute(
      "src",
      expect.stringContaining("data:image/svg+xml"),
    );
    fireEvent.change(screen.getByLabelText("Code from the app"), { target: { value: "000000" } });
    fireEvent.click(screen.getByRole("button", { name: "Confirm" }));
    expect(await screen.findByText("That code is not right, or was already used")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Code from the app"), { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: "Confirm" }));
    expect(await screen.findByText("aaaa-bbbb-cccc")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "I have kept them" })).toBeInTheDocument();
  });

  it("asks for a code to remove it, and offers no removal while the instance requires one", async () => {
    vi.mocked(api.mySecondFactor).mockResolvedValue(on);
    vi.mocked(api.removeMySecondFactor).mockResolvedValue(undefined);
    show();
    expect(await screen.findByText(/8 of\s+10 recovery codes left/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Remove…" }));
    const dialog = screen.getByRole("dialog", { name: "Remove the second factor" });
    fireEvent.change(dialog.querySelector("input")!, { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: "Remove it" }));
    await waitFor(() => expect(api.removeMySecondFactor).toHaveBeenCalledWith("123456"));
  });

  it("hides Remove while the instance requires a second factor", async () => {
    vi.mocked(api.mySecondFactor).mockResolvedValue({ ...on, required: true });
    show();
    expect(await screen.findByRole("button", { name: "New recovery codes…" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Remove…" })).toBeNull();
    expect(screen.getByText(/security administrator removes it/)).toBeInTheDocument();
  });
});
