/**
 * Signing in with a passkey (0.12 I5, I4c): the browser's prompt, with the engine's passkey
 * ceremony. The engine verifies everything; this only moves the browser's answer to it. The
 * ceremony is the engine's own (`/oauth/passkeys/authentication/*`), shared with its sign-in pages.
 */

import { API_URL } from "@/api/address";
import type { SignInRequest } from "@/api/session";

/** A refusal with words for the person, from the engine or from the browser's prompt. */
export class PasskeyError extends Error {
  constructor(
    message: string,
    readonly waitSeconds = 0,
  ) {
    super(message);
  }
}

function toBytes(text: string): ArrayBuffer {
  const base64 = text
    .replace(/-/g, "+")
    .replace(/_/g, "/")
    .padEnd(Math.ceil(text.length / 4) * 4, "=");
  return Uint8Array.from(atob(base64), (char) => char.charCodeAt(0)).buffer;
}

function toText(buffer: ArrayBuffer): string {
  let raw = "";
  for (const byte of new Uint8Array(buffer)) raw += String.fromCharCode(byte);
  return btoa(raw).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

async function post(path: string, body: object): Promise<{ ok: boolean; data: Record<string, unknown> }> {
  const response = await fetch(`${API_URL}${path}`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return { ok: response.ok, data: (await response.json().catch(() => ({}))) as Record<string, unknown> };
}

function refusal(answer: { data: Record<string, unknown> }) {
  const wait = typeof answer.data.waitSeconds === "number" ? answer.data.waitSeconds : 0;
  return new PasskeyError(String(answer.data.error ?? "The engine refused the passkey."), wait);
}

function describe(error: unknown): PasskeyError {
  if (error instanceof PasskeyError) return error;
  const name = error instanceof Error ? error.name : "";
  if (name === "NotAllowedError") return new PasskeyError("The passkey was cancelled or took too long. Try again.");
  return new PasskeyError("This browser could not use a passkey here. Try again, or sign in another way.");
}

/**
 * The passkey ceremony: alone for the browser's request, or as the second step of a password
 * sign-in (`step`). Resolves with the address the sign-in ends at.
 */
export async function signInWithPasskey(by: { request: SignInRequest } | { step: string }): Promise<string> {
  if (!window.PublicKeyCredential || !navigator.credentials) {
    throw new PasskeyError("This browser does not support passkeys. Sign in another way.");
  }
  try {
    const started = await post("/oauth/passkeys/authentication/options", "step" in by ? { step: by.step } : by.request);
    if (!started.ok) throw refusal(started);
    const options = started.data.options as {
      challenge: string;
      allowCredentials?: { id: string; type: string }[];
    };
    const credential = (await navigator.credentials.get({
      publicKey: {
        ...options,
        challenge: toBytes(options.challenge),
        allowCredentials: options.allowCredentials?.map((item) => ({ ...item, id: toBytes(item.id) })),
      } as PublicKeyCredentialRequestOptions,
    })) as PublicKeyCredential | null;
    if (!credential) throw new PasskeyError("The passkey was cancelled or took too long. Try again.");
    const response = credential.response as AuthenticatorAssertionResponse;
    const done = await post("/oauth/passkeys/authentication/verify", {
      ceremony: started.data.ceremony,
      credential: {
        id: credential.id,
        rawId: toText(credential.rawId),
        type: credential.type,
        authenticatorAttachment: credential.authenticatorAttachment ?? null,
        clientExtensionResults: credential.getClientExtensionResults(),
        response: {
          clientDataJSON: toText(response.clientDataJSON),
          authenticatorData: toText(response.authenticatorData),
          signature: toText(response.signature),
          userHandle: response.userHandle ? toText(response.userHandle) : null,
        },
      },
    });
    if (!done.ok) throw refusal(done);
    return String(done.data.redirect);
  } catch (error) {
    throw describe(error);
  }
}
