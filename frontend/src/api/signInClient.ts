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
  providers: { key: string; name: string; start: string }[];
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
