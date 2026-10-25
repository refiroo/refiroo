/**
 * The person's session in this browser (0.12 I2, ADR-043, D234). The person signs in on the
 * application's own screen (0.12 I5) with the authorization code flow and PKCE, the engine checking
 * every step; the access token lives here, in memory
 * only, and is renewed through the session's refresh token, an `HttpOnly` cookie this code never
 * sees. Renewals run one tab at a time under a Web Lock (D269): each refresh token is used once,
 * and two tabs presenting the same one would end the session. A request refused with `401` is sent
 * again once after a renewal; when the session cannot be renewed the sign-in screen is shown and the
 * person comes back to the same address.
 */

import { API_URL } from "@/api/address";

const CLIENT_ID = "browser";
const PENDING_KEY = "rdm.signIn";
const RETURN_KEY = "rdm.signInReturn";
const RENEW_LOCK = "oauth-renew";

/** Leaving for another address (a provider's sign-in, the end of a sign-in); tests observe it. */
export const browserNavigation = { go: (url: string) => window.location.assign(url) };

/** Where a sign-in returns to, at the app's origin (D267). */
export const redirectUri = () => `${window.location.origin}/signed-in`;

let accessToken: string | undefined;
// Set once the app has started its session; until then (as in unit tests) a `401` is only reported.
let active = false;
let renewing: Promise<string | undefined> | undefined;

interface PendingSignIn {
  verifier: string;
  state: string;
  returnTo: string;
}

function base64Url(bytes: Uint8Array): string {
  let text = "";
  for (const byte of bytes) text += String.fromCharCode(byte);
  return btoa(text).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function randomText(length: number): string {
  return base64Url(crypto.getRandomValues(new Uint8Array(length)));
}

async function challengeOf(verifier: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier));
  return base64Url(new Uint8Array(digest));
}

const here = () => `${window.location.pathname}${window.location.search}${window.location.hash}`;

interface SignInReturn {
  returnTo: string;
  ended: boolean;
}

function keepReturn(value: SignInReturn) {
  try {
    window.sessionStorage.setItem(RETURN_KEY, JSON.stringify(value));
  } catch {
    // Without session storage the person still signs in; they return to the start page.
  }
}

function hasReturn(): boolean {
  try {
    return window.sessionStorage.getItem(RETURN_KEY) !== null;
  } catch {
    return false;
  }
}

function takeReturn(): SignInReturn | undefined {
  try {
    const stored = window.sessionStorage.getItem(RETURN_KEY);
    window.sessionStorage.removeItem(RETURN_KEY);
    return stored ? (JSON.parse(stored) as SignInReturn) : undefined;
  } catch {
    return undefined;
  }
}

/** The authorization request the engine checks at every step of a sign-in. */
export interface SignInRequest {
  response_type: string;
  client_id: string;
  redirect_uri: string;
  code_challenge: string;
  code_challenge_method: string;
  state: string;
}

/**
 * A new sign-in for the screen to carry out: a PKCE verifier kept for the exchange and the request
 * the engine checks. `ended` says the person's session ended (D270: without naming the page).
 */
export async function prepareSignIn(): Promise<{ request: SignInRequest; ended: boolean }> {
  const kept = takeReturn();
  const verifier = randomText(48);
  const pending: PendingSignIn = { verifier, state: randomText(24), returnTo: kept?.returnTo ?? "/" };
  try {
    window.sessionStorage.setItem(PENDING_KEY, JSON.stringify(pending));
  } catch {
    // Without session storage the person still signs in; they return to the start page.
  }
  if (kept) keepReturn(kept);
  return {
    ended: !!kept?.ended,
    request: {
      response_type: "code",
      client_id: CLIENT_ID,
      redirect_uri: redirectUri(),
      code_challenge: await challengeOf(verifier),
      code_challenge_method: "S256",
      state: pending.state,
    },
  };
}

/**
 * Show the sign-in screen again at `returnTo` after the session ended; the person comes back there.
 */
export function signIn(returnTo = here(), ended = false): Promise<never> {
  keepReturn({ returnTo, ended });
  browserNavigation.go(returnTo);
  // The page is leaving; nothing after this should run.
  return new Promise<never>(() => undefined);
}

async function tokenRequest(fields: Record<string, string>): Promise<string | undefined> {
  const response = await fetch(`${API_URL}/oauth/token`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ client_id: CLIENT_ID, ...fields }),
  });
  if (!response.ok) return undefined;
  const body = (await response.json()) as { access_token: string };
  return body.access_token;
}

function readPending(): PendingSignIn | undefined {
  try {
    const stored = window.sessionStorage.getItem(PENDING_KEY);
    window.sessionStorage.removeItem(PENDING_KEY);
    return stored ? (JSON.parse(stored) as PendingSignIn) : undefined;
  } catch {
    return undefined;
  }
}

/** The address the sign-in page returned to: exchange its code for the session. */
async function finishSignIn(): Promise<string | undefined> {
  const params = new URLSearchParams(window.location.search);
  const pending = readPending();
  const code = params.get("code");
  if (!pending || !code || params.get("state") !== pending.state) return undefined;
  const token = await tokenRequest({
    grant_type: "authorization_code",
    code,
    code_verifier: pending.verifier,
    redirect_uri: redirectUri(),
  });
  if (token) window.history.replaceState(null, "", pending.returnTo || "/");
  return token;
}

/**
 * A new access token from the session's cookie, one tab at a time; none when the session has
 * ended. Rejects when the engine cannot be reached, which is not the session's end.
 */
export function renew(): Promise<string | undefined> {
  renewing ??= (async () => {
    const request = () => tokenRequest({ grant_type: "refresh_token" });
    try {
      const token = navigator.locks ? await navigator.locks.request(RENEW_LOCK, request) : await request();
      accessToken = token;
      return token;
    } finally {
      renewing = undefined;
    }
  })();
  return renewing;
}

/**
 * Start the session before the app renders: finish a sign-in that has just returned, or renew the
 * one this browser holds; without either the sign-in screen is needed, and the address asked for is
 * kept to return to. Rejects when the engine cannot be reached.
 */
export async function startSession(): Promise<"signed-in" | "sign-in"> {
  active = true;
  if (window.location.pathname === "/signed-in") {
    accessToken = await finishSignIn();
    if (accessToken) return "signed-in";
    window.history.replaceState(null, "", "/");
  }
  if (await renew()) return "signed-in";
  if (!hasReturn()) keepReturn({ returnTo: here(), ended: false });
  return "sign-in";
}

/** `fetch` with the access token; a `401` renews the session once and sends the request again. */
export async function authorizedFetch(input: string, init: RequestInit = {}): Promise<Response> {
  const send = (token: string | undefined) => {
    const headers = new Headers(init.headers);
    if (token) headers.set("Authorization", `Bearer ${token}`);
    return fetch(input, { ...init, headers });
  };
  const sentWith = accessToken;
  const response = await send(sentWith);
  if (response.status !== 401 || !active) return response;
  // Another request may have renewed the token meanwhile.
  let token: string | undefined;
  try {
    token = accessToken && accessToken !== sentWith ? accessToken : await renew();
  } catch {
    // The engine cannot be reached now; the caller reports the refusal it has.
    return response;
  }
  if (token) return send(token);
  return signIn(here(), true);
}

/**
 * Add a passkey on the engine's own page (0.12 I4c, D392): a passkey belongs to the engine's host,
 * so the browser's prompt runs there, and the page returns here when it is done.
 */
export function addPasskey(): Promise<never> {
  const query = new URLSearchParams({ return: `${window.location.origin}/settings/account` });
  browserNavigation.go(`${API_URL}/oauth/passkeys/new?${query}`);
  // The page is leaving; nothing after this should run.
  return new Promise<never>(() => undefined);
}

/**
 * Sign out by navigation (0.12 I4a, D380): the engine ends the session from its cookie and sends the
 * browser back to the app, by way of the provider's own sign-out when the provider that started
 * the session signs people out too; the app then finds no session and shows the sign-in page.
 */
export function signOut(): Promise<never> {
  accessToken = undefined;
  const query = new URLSearchParams({ return: `${window.location.origin}/` });
  browserNavigation.go(`${API_URL}/oauth/sign-out?${query}`);
  // The page is leaving; nothing after this should run.
  return new Promise<never>(() => undefined);
}
