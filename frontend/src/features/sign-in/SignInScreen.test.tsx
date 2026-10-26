// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { SecondStep, SignInOptions } from "@/api/signInClient";

const go = vi.fn();
const request = {
  response_type: "code",
  client_id: "browser",
  redirect_uri: "http://localhost:5173/signed-in",
  code_challenge: "c".repeat(43),
  code_challenge_method: "S256",
  state: "s",
};

vi.mock("@/api/session", () => ({
  browserNavigation: { go: (url: string) => go(url) },
  prepareSignIn: vi.fn(async () => ({ request, ended: false })),
}));
const client = vi.hoisted(() => ({
  signInOptions: vi.fn(),
  signInWithPassword: vi.fn(),
  signInSecondFactor: vi.fn(),
}));
vi.mock("@/api/signInClient", () => client);
const passkey = vi.hoisted(() => ({ signInWithPasskey: vi.fn() }));
vi.mock("@/lib/passkeySignIn", () => ({
  ...passkey,
  PasskeyError: class extends Error {
    constructor(
      message: string,
      readonly waitSeconds = 0,
    ) {
      super(message);
    }
  },
}));

const { SignInScreen, refusalText, waitText } = await import("./SignInScreen");

const OPTIONS: SignInOptions = { product: "refiroo", local: true, passkey: false, reset: false, providers: [] };
const SECOND: SecondStep = {
  status: "second_factor",
  step: "tok",
  stage: "code",
  app: true,
  passkey: false,
  username: "mei",
};

function open(options: Partial<SignInOptions> = {}) {
  client.signInOptions.mockResolvedValue({ options: { ...OPTIONS, ...options } });
  return render(<SignInScreen />);
}

async function typeCredentials() {
  fireEvent.change(await screen.findByLabelText("Username"), { target: { value: "mei" } });
  fireEvent.change(screen.getByLabelText("Password"), { target: { value: "secret" } });
}

describe("the application's sign-in screen (0.12 I5)", () => {
  beforeEach(() => vi.clearAllMocks());
  afterEach(cleanup);

  it("is branded, and a right password ends at the address the engine answers", async () => {
    client.signInWithPassword.mockResolvedValue({
      kind: "signed-in",
      redirect: "http://localhost:5173/signed-in?code=x&state=s",
    });
    open();
    expect(await screen.findByRole("heading", { level: 1, name: "Sign in" })).toBeInTheDocument();
    expect(screen.getByText("Reference data that stays in step.")).toBeInTheDocument();
    expect(screen.getByAltText("refiroo")).toBeInTheDocument();
    await typeCredentials();
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
    await waitFor(() => expect(go).toHaveBeenCalledWith("http://localhost:5173/signed-in?code=x&state=s"));
    expect(client.signInWithPassword).toHaveBeenCalledWith(request, "mei", "secret");
  });

  it("says a wrong password without naming the part, and how long to wait when slowed", async () => {
    client.signInWithPassword
      .mockResolvedValueOnce({
        kind: "refused",
        error: "wrong_credentials",
        message: "The username or password is not right. Check both and try again.",
        waitSeconds: 0,
        status: 401,
      })
      .mockResolvedValueOnce({
        kind: "refused",
        error: "slowed",
        message: "Too many attempts for this account or from this address. You can try again in 40 seconds.",
        waitSeconds: 40,
        status: 429,
      });
    open();
    await typeCredentials();
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByText(/username or password is not right/)).toBeInTheDocument();
    // The username stays and the password field is cleared and focused.
    expect(screen.getByLabelText("Username")).toHaveValue("mei");
    expect(screen.getByLabelText("Password")).toHaveValue("");
    expect(screen.getByLabelText("Password")).toHaveFocus();
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "again" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByText(/try again in 40 seconds/)).toBeInTheDocument();
    expect(go).not.toHaveBeenCalled();
  });

  it("offers providers, and with local sign-in off only the administrators' link until it is used", async () => {
    open({
      local: false,
      providers: [{ key: "entra", name: "Entra ID", start: "/oauth/providers/entra/start?state=s" }],
    });
    expect(await screen.findByRole("button", { name: "Continue with Entra ID" })).toBeInTheDocument();
    expect(screen.queryByLabelText("Username")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Continue with Entra ID" }));
    expect(go).toHaveBeenCalledWith("http://localhost:8000/oauth/providers/entra/start?state=s");
    fireEvent.click(screen.getByRole("button", { name: "Sign in with a local administrator account" }));
    expect(await screen.findByLabelText("Username")).toBeInTheDocument();
  });

  it("links to the reset page only where a forgotten password can be asked for by e-mail", async () => {
    const first = open({ reset: true });
    expect((await screen.findByRole("link", { name: "Forgotten your password?" })).getAttribute("href")).toBe(
      "/reset-password",
    );
    first.unmount();
    open({ reset: false });
    await screen.findByLabelText("Username");
    expect(screen.queryByRole("link", { name: "Forgotten your password?" })).toBeNull();
    expect(screen.getByText(/Ask a security administrator for a reset link/)).toBeTruthy();
  });

  it("asks for the code after the password, refuses a wrong one and signs in with a right one", async () => {
    client.signInWithPassword.mockResolvedValue({ kind: "second-factor", step: SECOND });
    client.signInSecondFactor
      .mockResolvedValueOnce({
        kind: "refused",
        error: "wrong_code",
        message: "That code is not right, or was already used. Wait for the next one and try again.",
        waitSeconds: 0,
        status: 401,
      })
      .mockResolvedValueOnce({ kind: "signed-in", redirect: "http://localhost:5173/signed-in?code=y&state=s" });
    open();
    await typeCredentials();
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByRole("heading", { name: "Enter your code" })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Code"), { target: { value: "000000" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(
      await screen.findByText("That code is not right, or was already used. Wait for the next one and try again."),
    ).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Code"), { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
    await waitFor(() => expect(go).toHaveBeenCalledWith("http://localhost:5173/signed-in?code=y&state=s"));
    expect(client.signInSecondFactor).toHaveBeenLastCalledWith("tok", { code: "123456" });
  });

  it("takes a recovery code in place of the app's, and starts again", async () => {
    client.signInWithPassword.mockResolvedValue({ kind: "second-factor", step: SECOND });
    client.signInSecondFactor.mockResolvedValue({
      kind: "signed-in",
      redirect: "http://localhost:5173/signed-in?code=z",
    });
    open();
    await typeCredentials();
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
    fireEvent.click(await screen.findByRole("button", { name: "Use a recovery code instead" }));
    fireEvent.change(screen.getByLabelText("Recovery code"), { target: { value: "abcd-efgh-jklm" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
    await waitFor(() => expect(client.signInSecondFactor).toHaveBeenCalledWith("tok", { recovery: "abcd-efgh-jklm" }));
  });

  it("shows the set-up when it is required, then the recovery codes before going on", async () => {
    const setup: SecondStep = {
      ...SECOND,
      stage: "setup",
      app: false,
      setup: { secret: "ABCDEFGHJKLM", svg: "<svg></svg>" },
    };
    client.signInWithPassword.mockResolvedValue({ kind: "second-factor", step: setup });
    client.signInSecondFactor
      .mockResolvedValueOnce({ kind: "recovery-codes", codes: ["aaaa-bbbb-cccc", "dddd-eeee-ffff"] })
      .mockResolvedValueOnce({ kind: "signed-in", redirect: "http://localhost:5173/signed-in?code=n&state=s" });
    open();
    await typeCredentials();
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByRole("heading", { name: "Set up a second factor" })).toBeInTheDocument();
    expect(screen.getByText("ABCD EFGH JKLM")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Code from the app"), { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: "Confirm and continue" }));
    expect(await screen.findByText("aaaa-bbbb-cccc")).toBeInTheDocument();
    expect(go).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "I have kept them; continue" }));
    await waitFor(() => expect(go).toHaveBeenCalledWith("http://localhost:5173/signed-in?code=n&state=s"));
    expect(client.signInSecondFactor).toHaveBeenLastCalledWith("tok");
  });

  it("signs in with a passkey alone, and says why one failed", async () => {
    passkey.signInWithPasskey
      .mockRejectedValueOnce(new Error("The passkey was cancelled or took too long. Try again."))
      .mockResolvedValueOnce("http://localhost:5173/signed-in?code=p&state=s");
    open({ passkey: true });
    fireEvent.click(await screen.findByRole("button", { name: /Sign in with a passkey/ }));
    expect(await screen.findByText(/The passkey could not be used|cancelled/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Sign in with a passkey/ }));
    await waitFor(() => expect(go).toHaveBeenCalledWith("http://localhost:5173/signed-in?code=p&state=s"));
    expect(passkey.signInWithPasskey).toHaveBeenCalledWith({ request });
  });

  it("reports a request the engine does not serve, with a way to try again", async () => {
    client.signInOptions.mockResolvedValueOnce({
      error: "unknown_client",
      message: "This application is not one the engine signs people in to.",
    });
    render(<SignInScreen />);
    expect(await screen.findByText(/not one the engine signs people in to/)).toBeInTheDocument();
    client.signInOptions.mockResolvedValueOnce({ options: OPTIONS });
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByLabelText("Username")).toBeInTheDocument();
  });
});

describe("the words for a refusal", () => {
  it("counts a wait in seconds, then minutes, and shows the engine's own message", () => {
    expect(waitText(1)).toBe("1 second");
    expect(waitText(40)).toBe("40 seconds");
    expect(waitText(300)).toBe("5 minutes");
    expect(
      refusalText({ kind: "refused", error: "step_gone", message: "Start again.", waitSeconds: 0, status: 410 }),
    ).toBe("Start again.");
  });
});
