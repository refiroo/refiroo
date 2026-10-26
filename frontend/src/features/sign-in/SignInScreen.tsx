/**
 * The application's own sign-in screen (0.12 I5, D415, D416): every way in on one screen that follows
 * the saved theme: a passkey, a password, a sign-in provider's button, and the second step after a
 * password (an authenticator app's code, a recovery code, a passkey, or the set-up when the
 * organisation requires one). The engine decides every step through its sign-in routes; this only
 * draws what it answers. A sign-in ends at the address the engine returns, where the session starts
 * (`api/session`). The engine's own pages stay for outside applications.
 */

import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import {
  signInOptions,
  signInSecondFactor,
  signInWithPassword,
  type SecondStep,
  type SignInAnswer,
  type SignInOptions,
} from "@/api/signInClient";
import { API_URL } from "@/api/address";
import { browserNavigation, prepareSignIn, type SignInRequest } from "@/api/session";
import { PasskeyError, signInWithPasskey } from "@/lib/passkeySignIn";
import { FormField } from "@/ui/FormField";
import { Icon } from "@/ui/Icon";
import { Notice } from "@/ui/Notice";
import { SignInFrame } from "./SignInFrame";

type View =
  | { kind: "start" }
  | { kind: "second"; step: SecondStep; recovery: boolean }
  | { kind: "codes"; step: SecondStep; codes: string[] };

export function waitText(seconds: number): string {
  if (seconds < 90) return `${seconds} second${seconds === 1 ? "" : "s"}`;
  const minutes = Math.ceil(seconds / 60);
  return `${minutes} minute${minutes === 1 ? "" : "s"}`;
}

/** The words for a refusal: the engine's own, so a wording is never kept twice (D415). */
export function refusalText(answer: Extract<SignInAnswer, { kind: "refused" }>): string {
  if (answer.error === "foreign_origin")
    return "The engine does not accept sign-ins from this address. Ask an administrator to add it to CORS_ORIGINS.";
  return answer.message;
}

function QrCode({ svg }: { svg: string }) {
  return (
    <img
      className="sign-in-qr"
      alt="QR code for the authenticator app"
      src={`data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`}
    />
  );
}

export function SignInScreen() {
  const [request, setRequest] = useState<SignInRequest>();
  const [ended, setEnded] = useState(false);
  const [options, setOptions] = useState<SignInOptions>();
  const [loadError, setLoadError] = useState("");
  const [view, setView] = useState<View>({ kind: "start" });
  const [showLocal, setShowLocal] = useState(false);
  const [message, setMessage] = useState("");
  const [pending, setPending] = useState(false);
  const [leaving, setLeaving] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");

  const passwordRef = useRef<HTMLInputElement>(null);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let current = true;
    (async () => {
      try {
        const prepared = await prepareSignIn();
        const answer = await signInOptions(prepared.request);
        if (!current) return;
        setRequest(prepared.request);
        setEnded(prepared.ended);
        if ("options" in answer) setOptions(answer.options);
        else setLoadError(answer.message);
      } catch {
        if (current) setLoadError(`The engine at ${API_URL} did not answer. Check that it is running, then try again.`);
      }
    })();
    return () => {
      current = false;
    };
  }, [attempt]);

  function finish(redirect: string) {
    setLeaving(true);
    browserNavigation.go(redirect);
  }

  function handle(answer: SignInAnswer) {
    setMessage("");
    setCode("");
    if (answer.kind === "signed-in") finish(answer.redirect);
    else if (answer.kind === "second-factor") setView({ kind: "second", step: answer.step, recovery: false });
    else if (answer.kind === "recovery-codes" && view.kind === "second")
      setView({ kind: "codes", step: view.step, codes: answer.codes });
    else if (answer.kind === "refused") {
      setMessage(refusalText(answer));
      if (answer.error === "step_gone") setView({ kind: "start" });
      if (answer.error === "wrong_credentials" || answer.error === "slowed") {
        // The username stays; the password is typed again.
        setPassword("");
        passwordRef.current?.focus();
      }
    }
  }

  async function run(action: () => Promise<SignInAnswer>) {
    setPending(true);
    try {
      handle(await action());
    } catch {
      setMessage(`The engine at ${API_URL} did not answer. Try again.`);
    } finally {
      setPending(false);
    }
  }

  function submitPassword(event: FormEvent) {
    event.preventDefault();
    if (request) void run(() => signInWithPassword(request, username, password));
  }

  function submitCode(event: FormEvent, step: SecondStep, recovery: boolean) {
    event.preventDefault();
    void run(() => signInSecondFactor(step.step, recovery ? { recovery: code } : { code }));
  }

  async function passkey(by: { request: SignInRequest } | { step: string }) {
    setPending(true);
    setMessage("");
    try {
      finish(await signInWithPasskey(by));
    } catch (error) {
      const failure = error instanceof PasskeyError ? error : undefined;
      const wait = failure?.waitSeconds ? ` You can try again in ${waitText(failure.waitSeconds)}.` : "";
      setMessage((failure?.message ?? "The passkey could not be used.") + wait);
    } finally {
      setPending(false);
    }
  }

  const product = options?.product ?? "refiroo";
  const title =
    view.kind === "codes"
      ? "Keep your recovery codes"
      : view.kind === "second"
        ? view.step.stage === "setup"
          ? "Set up a second factor"
          : view.recovery
            ? "Use a recovery code"
            : view.step.passkey
              ? "Confirm it is you"
              : "Enter your code"
        : "Sign in";

  return (
    <SignInFrame
      product={product}
      named={!!options || !!loadError}
      busy={leaving || (!options && !loadError)}
      title={title}
    >
      {loadError ? (
        <>
          <Notice tone="error" title="Signing in is not possible right now">
            {loadError}
          </Notice>
          <button
            type="button"
            className="primary"
            onClick={() => {
              setLoadError("");
              setAttempt((count) => count + 1);
            }}
          >
            Try again
          </button>
        </>
      ) : !options ? (
        <p className="sign-in-aside">Loading…</p>
      ) : (
        <>
          {ended && view.kind === "start" && (
            <Notice tone="info">Your session ended. Sign in again to return to where you were.</Notice>
          )}
          {message && <Notice tone={message.startsWith("Too many") ? "warning" : "error"}>{message}</Notice>}
          {view.kind === "start" && request && (
            <>
              {options.passkey && (
                <>
                  <button
                    type="button"
                    className="primary"
                    disabled={pending || leaving}
                    onClick={() => void passkey({ request })}
                  >
                    <Icon name="lock" /> Sign in with a passkey
                  </button>
                  {(options.local || showLocal) && <p className="sign-in-or">or with a password</p>}
                </>
              )}
              {(options.local || showLocal) && (
                <form className="sign-in-form" noValidate onSubmit={submitPassword}>
                  <FormField label="Username">
                    {(control) => (
                      <input
                        {...control}
                        autoFocus={!options.passkey}
                        required
                        autoComplete="username"
                        autoCapitalize="none"
                        spellCheck={false}
                        value={username}
                        onChange={(event) => setUsername(event.target.value)}
                      />
                    )}
                  </FormField>
                  <FormField label="Password">
                    {(control) => (
                      <input
                        {...control}
                        ref={passwordRef}
                        required
                        type="password"
                        autoComplete="current-password"
                        value={password}
                        onChange={(event) => setPassword(event.target.value)}
                      />
                    )}
                  </FormField>
                  <button type="submit" className="primary" disabled={pending || leaving || !username || !password}>
                    {pending ? "Signing in…" : "Sign in"}
                  </button>
                </form>
              )}
              {options.providers.length > 0 && (
                <>
                  {(options.local || showLocal || options.passkey) && <p className="sign-in-or">or</p>}
                  {options.providers.map((provider) => (
                    <button
                      key={provider.key}
                      type="button"
                      className={options.local || showLocal ? undefined : "primary"}
                      disabled={leaving}
                      onClick={() => {
                        setLeaving(true);
                        browserNavigation.go(`${API_URL}${provider.start}`);
                      }}
                    >
                      Continue with {provider.name}
                    </button>
                  ))}
                </>
              )}
              {!options.local && !showLocal && (
                <p className="sign-in-aside">
                  <button type="button" className="link-button" onClick={() => setShowLocal(true)}>
                    Sign in with a local administrator account
                  </button>
                </p>
              )}
              {options.local && (
                <p className="sign-in-aside">
                  {options.reset ? (
                    <a href="/reset-password">Forgotten your password?</a>
                  ) : (
                    "Forgotten your password? Ask a security administrator for a reset link."
                  )}
                </p>
              )}
              {!options.local && showLocal && (
                <p className="sign-in-aside">Only administrators made on the server sign in with a password here.</p>
              )}
            </>
          )}
          {view.kind === "second" && (
            <SecondStepView
              step={view.step}
              recovery={view.recovery}
              product={product}
              code={code}
              pending={pending || leaving}
              onCode={setCode}
              onSubmit={(event) => submitCode(event, view.step, view.recovery)}
              onPasskey={() => void passkey({ step: view.step.step })}
              onRecovery={(on) => {
                setView({ ...view, recovery: on });
                setMessage("");
                setCode("");
              }}
              onStartAgain={() => {
                setView({ kind: "start" });
                setMessage("");
                setCode("");
                setPassword("");
              }}
            />
          )}
          {view.kind === "codes" && (
            <>
              <p className="sign-in-aside">
                If you lose your phone, each code signs you in once. They are shown only now: save them in a password
                manager or print them.
              </p>
              <div className="sign-in-codes mono">
                {view.codes.map((item) => (
                  <span key={item}>{item}</span>
                ))}
              </div>
              <button
                type="button"
                className="primary"
                disabled={pending || leaving}
                onClick={() => void run(() => signInSecondFactor(view.step.step))}
              >
                I have kept them; continue
              </button>
            </>
          )}
        </>
      )}
    </SignInFrame>
  );
}

function SecondStepView({
  step,
  recovery,
  product,
  code,
  pending,
  onCode,
  onSubmit,
  onPasskey,
  onRecovery,
  onStartAgain,
}: {
  step: SecondStep;
  recovery: boolean;
  product: string;
  code: string;
  pending: boolean;
  onCode: (code: string) => void;
  onSubmit: (event: FormEvent) => void;
  onPasskey: () => void;
  onRecovery: (on: boolean) => void;
  onStartAgain: () => void;
}) {
  const setup = step.stage === "setup";
  const key = step.setup ? (step.setup.secret.match(/.{1,4}/g) ?? []).join(" ") : "";
  return (
    <>
      {setup && step.setup ? (
        <>
          <p className="sign-in-aside">
            This instance asks for a code from an authenticator app with every password. Scan the code with the app,
            then type the six digits it shows.
          </p>
          <div className="sign-in-setup">
            <QrCode svg={step.setup.svg} />
            <p className="sign-in-aside">
              Cannot scan? Type this key into the app:
              <code id="key">{key}</code>
            </p>
          </div>
        </>
      ) : (
        <p className="sign-in-aside">
          Signing in as <strong>{step.username}</strong>.{" "}
          {recovery
            ? "Type one of your recovery codes. Each works once."
            : step.passkey
              ? step.app
                ? "Use one of your passkeys, or the code from your authenticator app."
                : "Use one of your passkeys."
              : `Open your authenticator app and type the six-digit code for ${product}.`}
        </p>
      )}
      {!setup && !recovery && step.passkey && (
        <>
          <button type="button" className="primary" disabled={pending} onClick={onPasskey}>
            <Icon name="lock" /> Use a passkey
          </button>
          {step.app && <p className="sign-in-or">or</p>}
        </>
      )}
      {(setup || step.app || recovery) && (
        <form className="sign-in-form" noValidate onSubmit={onSubmit}>
          <FormField label={recovery ? "Recovery code" : step.passkey || setup ? "Code from the app" : "Code"}>
            {(control) => (
              <input
                {...control}
                autoFocus={!step.passkey || setup || recovery}
                required
                inputMode={recovery ? "text" : "numeric"}
                autoComplete="one-time-code"
                autoCapitalize="none"
                spellCheck={false}
                placeholder={setup ? "000 000" : undefined}
                value={code}
                onChange={(event) => onCode(event.target.value)}
              />
            )}
          </FormField>
          <button
            type="submit"
            className={step.passkey && !setup && !recovery ? undefined : "primary"}
            disabled={pending || !code.trim()}
          >
            {setup ? "Confirm and continue" : step.passkey && !recovery ? "Sign in with the code" : "Sign in"}
          </button>
        </form>
      )}
      <p className="sign-in-aside">
        {!setup && step.app && (
          <>
            <button type="button" className="link-button" onClick={() => onRecovery(!recovery)}>
              {recovery ? "Use the app's code" : "Use a recovery code instead"}
            </button>
            {" · "}
          </>
        )}
        <button type="button" className="link-button" onClick={onStartAgain}>
          Start again
        </button>
      </p>
      {recovery && (
        <p className="sign-in-aside">Lost the codes too? A security administrator can remove your second factor.</p>
      )}
    </>
  );
}
