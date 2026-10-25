// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

type Session = typeof import("./session");

const API = "http://localhost:8000";

function tokenAnswer(token: string) {
  return new Response(JSON.stringify({ access_token: token, token_type: "Bearer", expires_in: 3600 }), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

const refused = () => new Response(JSON.stringify({ error: "invalid_grant" }), { status: 400 });

async function load(): Promise<Session> {
  vi.resetModules();
  return import("./session");
}

function formOf(init: RequestInit | undefined) {
  return new URLSearchParams(String(init?.body));
}

describe("the browser's session (0.12 I2)", () => {
  let fetchMock: ReturnType<typeof vi.fn>;
  beforeEach(() => {
    fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    window.sessionStorage.clear();
    window.history.replaceState(null, "", "/w/default/records?view=table");
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("starts by renewing from the cookie, then sends the token", async () => {
    const session = await load();
    fetchMock.mockResolvedValueOnce(tokenAnswer("first")).mockResolvedValueOnce(new Response("{}"));
    await session.startSession();
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe(`${API}/oauth/token`);
    expect(init.credentials).toBe("include");
    expect(Object.fromEntries(formOf(init))).toEqual({ client_id: "browser", grant_type: "refresh_token" });
    await session.authorizedFetch(`${API}/api/v1/me`);
    expect(new Headers(fetchMock.mock.calls[1][1].headers).get("Authorization")).toBe("Bearer first");
  });

  it("without a session asks for the sign-in screen with a PKCE challenge and comes back where it was", async () => {
    const session = await load();
    const go = vi.spyOn(session.browserNavigation, "go").mockImplementation(() => undefined);
    fetchMock.mockResolvedValueOnce(refused());
    expect(await session.startSession()).toBe("sign-in");
    expect(go).not.toHaveBeenCalled();

    // The screen prepares its sign-in: the request the engine checks, the verifier kept for the exchange.
    const { request, ended } = await session.prepareSignIn();
    expect(ended).toBe(false);
    expect(request.client_id).toBe("browser");
    expect(request.redirect_uri).toBe(`${window.location.origin}/signed-in`);
    expect(request.code_challenge_method).toBe("S256");
    expect(request.code_challenge).toMatch(/^[A-Za-z0-9_-]{43}$/);
    const pending = JSON.parse(window.sessionStorage.getItem("rdm.signIn")!);
    expect(pending.state).toBe(request.state);
    expect(pending.returnTo).toBe("/w/default/records?view=table");

    // The engine returns the browser with the code: it is exchanged with the verifier, and the address restored.
    const finishing = await load();
    window.history.replaceState(null, "", `/signed-in?code=c1&state=${pending.state}`);
    fetchMock.mockResolvedValueOnce(tokenAnswer("signed-in"));
    expect(await finishing.startSession()).toBe("signed-in");
    const form = formOf(fetchMock.mock.calls[1][1]);
    expect(form.get("grant_type")).toBe("authorization_code");
    expect(form.get("code")).toBe("c1");
    expect(form.get("code_verifier")).toBe(pending.verifier);
    expect(window.location.pathname + window.location.search).toBe("/w/default/records?view=table");
  });

  it("keeps the return address through a restarted screen", async () => {
    const session = await load();
    fetchMock.mockResolvedValueOnce(refused());
    await session.startSession();
    await session.prepareSignIn();
    const again = await session.prepareSignIn();
    expect(again.request.state).toBe(JSON.parse(window.sessionStorage.getItem("rdm.signIn")!).state);
    expect(JSON.parse(window.sessionStorage.getItem("rdm.signIn")!).returnTo).toBe("/w/default/records?view=table");
  });

  it("renews once for requests refused together, under the lock, and sends them again", async () => {
    const session = await load();
    const request = vi.fn((_name: string, run: () => Promise<unknown>) => run());
    vi.stubGlobal("navigator", { ...navigator, locks: { request } });
    fetchMock.mockResolvedValueOnce(tokenAnswer("first"));
    await session.startSession();
    fetchMock.mockClear();
    fetchMock.mockImplementation(async (url: string, init?: RequestInit) => {
      if (url.endsWith("/oauth/token")) return tokenAnswer("second");
      const sent = new Headers(init?.headers).get("Authorization");
      return new Response("{}", { status: sent === "Bearer second" ? 200 : 401 });
    });
    const answers = await Promise.all([
      session.authorizedFetch(`${API}/api/v1/a`),
      session.authorizedFetch(`${API}/api/v1/b`),
    ]);
    expect(answers.map((answer) => answer.status)).toEqual([200, 200]);
    const renewals = fetchMock.mock.calls.filter(([url]) => String(url).endsWith("/oauth/token"));
    expect(renewals).toHaveLength(1);
    expect(request).toHaveBeenCalledWith("oauth-renew", expect.any(Function));
  });

  it("shows the sign-in screen again to a person whose session has ended, saying so", async () => {
    const session = await load();
    const go = vi.spyOn(session.browserNavigation, "go").mockImplementation(() => undefined);
    fetchMock.mockResolvedValueOnce(tokenAnswer("first"));
    await session.startSession();
    fetchMock.mockImplementation(async (url: string) =>
      url.endsWith("/oauth/token") ? refused() : new Response("{}", { status: 401 }),
    );
    void session.authorizedFetch(`${API}/api/v1/me`);
    await vi.waitFor(() => expect(go).toHaveBeenCalledTimes(1));
    expect(go.mock.calls[0][0]).toBe("/w/default/records?view=table");
    // The page loads again, finds no session, and the screen says why.
    const reloaded = await load();
    fetchMock.mockReset();
    fetchMock.mockResolvedValueOnce(refused());
    expect(await reloaded.startSession()).toBe("sign-in");
    expect((await reloaded.prepareSignIn()).ended).toBe(true);
  });

  it("reports an engine out of reach instead of showing the sign-in screen", async () => {
    const session = await load();
    const go = vi.spyOn(session.browserNavigation, "go");
    fetchMock.mockRejectedValueOnce(new TypeError("Failed to fetch"));
    await expect(session.startSession()).rejects.toThrow();
    expect(go).not.toHaveBeenCalled();
  });

  it("signs out by opening the engine's sign-out address, returning to the app", async () => {
    const session = await load();
    const go = vi.spyOn(session.browserNavigation, "go").mockImplementation(() => undefined);
    void session.signOut();
    expect(go).toHaveBeenCalledTimes(1);
    const address = new URL(go.mock.calls[0][0]);
    expect(`${address.origin}${address.pathname}`).toBe(`${API}/oauth/sign-out`);
    expect(address.searchParams.get("return")).toBe(`${window.location.origin}/`);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
