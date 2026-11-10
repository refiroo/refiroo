/**
 * The engine's sign-in steps for the application's own screen (0.12 I5, D416): the same checks as
 * the engine's sign-in pages, answering in JSON. Each call returns what happened; a refusal is data
 * (`error`, and `waitSeconds` while a wait runs), not an exception. Only an engine that cannot be
 * reached rejects.
 */

import { API_URL } from "@/api/address";
import type { SignInRequest } from "@/api/session";

export interface SignInOptions {
  /** The name the screen carries: the default workspace's product. */
  product: string;
  /** Whether a password is accepted (off once the organisation signs in with a provider, D365). */
  local: boolean;
  passkey: boolean;
  /** A forgotten password can be asked for here: mail is set up and local sign-in is on (I6). */
  reset: boolean;
  providers: { key: string; name: string; start: string }[];
  /** What the screen's small footer names: the version, and the tag and commit when known (0.13 BR). */
  build: { version: string; commit: string | null; tag: string | null };
}

export interface SecondStep {
  status: "second_factor";
  step: string;
  stage: "code" | "setup";
  /** The person has an authenticator app, and/or passkeys. */
  app: boolean;
  passkey: boolean;
  username: string;
  setup?: { secret: string; svg: string };
}

export type SignInAnswer =
  | { kind: "signed-in"; redirect: string }
  | { kind: "second-factor"; step: SecondStep }
  | { kind: "recovery-codes"; codes: string[] }
  | { kind: "refused"; error: string; message: string; waitSeconds: number; status: number };

interface Body {
  status?: string;
  redirect?: string;
  codes?: string[];
  error?: string;
  message?: string;
  waitSeconds?: number;
}

async function call(path: string, init?: RequestInit): Promise<{ status: number; body: Body }> {
  const response = await fetch(`${API_URL}${path}`, {
    credentials: "include",
    ...init,
    headers: { ...(init?.body ? { "Content-Type": "application/json" } : {}), ...init?.headers },
  });
  const body = (await response.json().catch(() => ({}))) as Body;
  return { status: response.status, body };
}

function answer({ status, body }: { status: number; body: Body }): SignInAnswer {
  if (status === 200 && body.status === "signed_in" && body.redirect)
    return { kind: "signed-in", redirect: body.redirect };
  if (status === 200 && body.status === "second_factor")
    return { kind: "second-factor", step: body as unknown as SecondStep };
  if (status === 200 && body.status === "recovery_codes" && body.codes)
    return { kind: "recovery-codes", codes: body.codes };
  return {
    kind: "refused",
    error: body.error ?? "unexpected",
    message: body.message ?? "The engine did not accept that.",
    waitSeconds: body.waitSeconds ?? 0,
    status,
  };
}

export async function signInOptions(
  request: SignInRequest,
): Promise<{ options: SignInOptions } | { error: string; message: string }> {
  const { status, body } = await call(`/oauth/sign-in/options?${new URLSearchParams({ ...request })}`);
  if (status === 200) return { options: body as unknown as SignInOptions };
  return { error: body.error ?? "unexpected", message: body.message ?? "The engine did not accept this sign-in." };
}

export async function signInWithPassword(request: SignInRequest, username: string, password: string) {
  return answer(
    await call("/oauth/sign-in/password", { method: "POST", body: JSON.stringify({ request, username, password }) }),
  );
}

/** The second step: a code, a recovery code, or neither to go on after the recovery codes. */
export async function signInSecondFactor(step: string, fields: { code?: string; recovery?: string } = {}) {
  return answer(
    await call("/oauth/sign-in/second-factor", { method: "POST", body: JSON.stringify({ step, ...fields }) }),
  );
}

/** What a refusal of the reset steps carries: the engine's own words, never kept twice. */
export interface ResetRefused {
  ok: false;
  error: string;
  message: string;
  waitSeconds: number;
}

/** What the reset page needs; with a token, who the link is for and the password rule. */
export type ResetPage =
  | { ok: true; product: string; available: boolean }
  | { ok: true; product: string; username: string; minLength: number }
  | ResetRefused;

function refusal({ body }: { body: Body }): ResetRefused {
  return {
    ok: false,
    error: body.error ?? "unexpected",
    message: body.message ?? "The engine did not accept that.",
    waitSeconds: body.waitSeconds ?? 0,
  };
}

export async function resetPage(token = ""): Promise<ResetPage> {
  const result = await call(`/oauth/sign-in/reset${token ? `?${new URLSearchParams({ token })}` : ""}`);
  if (result.status === 200) return { ok: true, ...(result.body as { product: string; available: boolean }) };
  return refusal(result);
}

/** Ask for a link by username or e-mail address; the same answer whoever is named (D420). */
export async function requestReset(identifier: string): Promise<{ ok: true; message: string } | ResetRefused> {
  const result = await call("/oauth/sign-in/reset-request", { method: "POST", body: JSON.stringify({ identifier }) });
  if (result.status === 202) return { ok: true, message: result.body.message ?? "" };
  return refusal(result);
}

export async function setPasswordWithLink(
  token: string,
  password: string,
  repeat: string,
): Promise<{ ok: true } | ResetRefused> {
  const result = await call("/oauth/sign-in/reset", {
    method: "POST",
    body: JSON.stringify({ token, password, repeat }),
  });
  if (result.status === 200) return { ok: true };
  return refusal(result);
}
