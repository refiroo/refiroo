import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { security } from "@/api/securityClient";
import type { SignInProvider } from "@/types";
import { ToastProvider } from "@/ui/Toast";
import { SignInPage } from "./SignInPage";

vi.mock("@/api/securityClient", () => ({
  security: {
    signInProviders: vi.fn(),
    signInProvider: vi.fn(),
    localSignIn: vi.fn(),
  },
}));

const provider = {
  key: "northfield",
  name: "Northfield Entra ID",
  enabled: true,
  people: 3,
  lastSignInAt: null,
  version: 1,
} as unknown as SignInProvider;

function open(providerKey?: string, onNavigate = vi.fn()) {
  render(
    <ToastProvider>
      <SignInPage route={{ kind: "settings", page: "sign-in", providerKey }} onNavigate={onNavigate} />
    </ToastProvider>,
  );
  return onNavigate;
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(security.signInProviders).mockResolvedValue({ items: [provider], nextCursor: null } as never);
  vi.mocked(security.localSignIn).mockResolvedValue({
    enabled: true,
    keptPeople: 1,
    secondFactorRequired: false,
    version: 1,
  } as never);
});

describe("Sign-in as a list and pages (0.17 ST1)", () => {
  it("lists local accounts and each provider as rows, and a row opens its page", async () => {
    const onNavigate = open();
    fireEvent.click(await screen.findByRole("button", { name: /Northfield Entra ID/ }));
    expect(onNavigate).toHaveBeenCalledWith({ kind: "settings", page: "sign-in", providerKey: "northfield" });
    fireEvent.click(screen.getByRole("button", { name: /Local accounts/ }));
    expect(onNavigate).toHaveBeenCalledWith({ kind: "settings", page: "sign-in", providerKey: "local" });
  });

  it("opens local accounts as a page whose trail goes back", async () => {
    const onNavigate = open("local");
    expect(await screen.findByRole("switch", { name: "Require a second factor with a password" })).not.toBeChecked();
    expect(screen.getByRole("heading", { level: 1, name: "Local accounts" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("link", { name: "Sign-in" }));
    expect(onNavigate).toHaveBeenCalledWith({ kind: "settings", page: "sign-in" });
  });
});
