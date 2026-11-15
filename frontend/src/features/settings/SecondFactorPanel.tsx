/**
 * Settings › Account › Second factor (0.12 I4b, D383–D388): an authenticator app a person sets up
 * for their password. Set up: the QR code the engine draws, the key to type, and a code to confirm,
 * then ten recovery codes shown once. Set up already: new recovery codes and removing it, each
 * asking for a code from the app (or a recovery code); removing is not offered while the instance
 * requires a second factor.
 */

import { useState, type FormEvent } from "react";
import { api } from "@/api/client";
import { errorMessage } from "@/api/errors";
import { formatServerDayTime } from "@/lib/dates";
import type { MySecondFactor, SecondFactorEnrolment } from "@/types";
import { CopyValue } from "@/ui/CopyValue";
import { FormField } from "@/ui/FormField";
import { InlineError } from "@/ui/InlineError";
import { Modal } from "@/ui/Modal";
import { Notice } from "@/ui/Notice";
import { SettingRow, SettingsGroup, SettingsPanel, SettingsTile } from "@/ui/SettingsParts";
import { StatusPill } from "@/ui/StatusPill";
import { Skeleton } from "@/ui/Skeleton";
import { useToast } from "@/ui/Toast";
import { settingsHead } from "@/ui/settingsNavigation";
import { useSettingsRead } from "@/state/useSystem";
import { copyText } from "@/lib/copyText";
import { saveBlob } from "@/lib/download";

type Mode =
  { kind: "idle" } | { kind: "setting-up"; enrolment: SecondFactorEnrolment } | { kind: "codes"; codes: string[] };

/** The key in groups of four, as an authenticator app shows it. */
export const groupedKey = (secret: string) => secret.replace(/(.{4})(?=.)/g, "$1 ");

export function SecondFactorPanel() {
  const { data, error, retry } = useSettingsRead<MySecondFactor>(api.mySecondFactor);
  const [mode, setMode] = useState<Mode>({ kind: "idle" });
  const [asking, setAsking] = useState<"codes" | "remove">();
  const [pending, setPending] = useState(false);
  const [failure, setFailure] = useState("");
  const toast = useToast();

  async function start() {
    setPending(true);
    setFailure("");
    try {
      setMode({ kind: "setting-up", enrolment: await api.startSecondFactor() });
    } catch (cause) {
      setFailure(errorMessage(cause));
    } finally {
      setPending(false);
    }
  }

  const hue = settingsHead("account").hue;
  return (
    <SettingsGroup
      title="Authenticator app"
      description="A second step after your password: a six-digit code from an app on your phone."
      action={
        data && !data.enabled && mode.kind === "idle" ? (
          <button type="button" className="secondary" disabled={pending} onClick={() => void start()}>
            {pending ? "Starting…" : "Set up an authenticator app"}
          </button>
        ) : undefined
      }
    >
      {error ? (
        <InlineError message={error} onRetry={retry} />
      ) : !data ? (
        <Skeleton label="Loading your second factor" lines={2} />
      ) : (
        <>
          {failure && <Notice tone="error">{failure}</Notice>}
          {mode.kind === "setting-up" ? (
            <SettingUp
              enrolment={mode.enrolment}
              onCancel={() => setMode({ kind: "idle" })}
              onConfirmed={(codes) => setMode({ kind: "codes", codes })}
            />
          ) : mode.kind === "codes" ? (
            <RecoveryCodes
              codes={mode.codes}
              onKept={() => {
                setMode({ kind: "idle" });
                retry();
              }}
            />
          ) : data.enabled ? (
            <SettingsPanel>
              <SettingRow
                lead={<SettingsTile icon="lock" hue={hue} />}
                name="Authenticator app"
                help={
                  <>
                    Set up {data.confirmedAt ? formatServerDayTime(data.confirmedAt) : ""} · {data.recoveryCodesLeft} of
                    10 recovery codes left{data.passkeys > 0 ? "; they work for passkeys too" : ""}.{" "}
                    {data.required && data.passkeys === 0
                      ? "This instance requires a second factor with a password, so a security administrator removes it, or you add a passkey first."
                      : "Both actions ask for a code from the app."}
                  </>
                }
              >
                <StatusPill tone="success">On · authenticator app</StatusPill>
                <button type="button" className="secondary" onClick={() => setAsking("codes")}>
                  New recovery codes…
                </button>
                {(!data.required || data.passkeys > 0) && (
                  <button type="button" className="danger-ghost" onClick={() => setAsking("remove")}>
                    Remove…
                  </button>
                )}
              </SettingRow>
            </SettingsPanel>
          ) : (
            <SettingsPanel>
              <SettingRow
                lead={<SettingsTile icon="lock" hue={hue} />}
                name="Not set up"
                help="With a second factor, your password alone does not sign you in: you also type a code from an authenticator app on your phone (Microsoft Authenticator, Google Authenticator, 1Password and others)."
              />
            </SettingsPanel>
          )}
        </>
      )}
      {asking === "codes" && (
        <CodeDialog
          title="New recovery codes"
          help="The old recovery codes stop working."
          confirmLabel="Rotate recovery codes"
          onClose={() => setAsking(undefined)}
          onSubmit={async (code) => {
            const made = await api.newRecoveryCodes(code);
            setAsking(undefined);
            setMode({ kind: "codes", codes: made.recoveryCodes });
          }}
        />
      )}
      {asking === "remove" && (
        <CodeDialog
          title="Remove the second factor"
          help="Your password alone signs you in again, and your recovery codes stop working."
          confirmLabel="Remove second factor"
          danger
          onClose={() => setAsking(undefined)}
          onSubmit={async (code) => {
            await api.removeMySecondFactor(code);
            setAsking(undefined);
            toast("Your second factor was removed.");
            retry();
          }}
        />
      )}
    </SettingsGroup>
  );
}

function SettingUp({
  enrolment,
  onCancel,
  onConfirmed,
}: {
  enrolment: SecondFactorEnrolment;
  onCancel: () => void;
  onConfirmed: (codes: string[]) => void;
}) {
  const [code, setCode] = useState("");
  const [problem, setProblem] = useState("");
  const [pending, setPending] = useState(false);

  async function confirm(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setProblem("");
    try {
      onConfirmed((await api.confirmSecondFactor(code)).recoveryCodes);
    } catch (cause) {
      setProblem(errorMessage(cause));
      setPending(false);
    }
  }

  return (
    <form onSubmit={(event) => void confirm(event)}>
      <SettingsPanel
        foot={
          <>
            <button type="button" className="ghost" disabled={pending} onClick={onCancel}>
              Cancel
            </button>
            <button className="primary" disabled={pending || !code.trim()}>
              {pending ? "Confirming…" : "Confirm"}
            </button>
          </>
        }
      >
        <div className="settings-panel-pad account-second-factor">
          <p>1. Scan the code with the app. 2. Type the six digits it shows.</p>
          <div className="second-factor-setup">
            <img
              className="second-factor-qr"
              alt="QR code for the authenticator app"
              width={160}
              height={160}
              src={`data:image/svg+xml;charset=utf-8,${encodeURIComponent(enrolment.qrSvg)}`}
            />
            <div className="second-factor-fields security-settings-form">
              <p className="account-muted">Cannot scan? Type this key:</p>
              <p className="webhook-secret">
                <CopyValue label="Key" value={groupedKey(enrolment.secret)} />
              </p>
              <FormField label="Code from the app" error={problem || undefined}>
                {(control) => (
                  <input
                    {...control}
                    className="mono"
                    inputMode="numeric"
                    autoComplete="one-time-code"
                    placeholder="000 000"
                    required
                    autoFocus
                    value={code}
                    onChange={(event) => setCode(event.target.value)}
                  />
                )}
              </FormField>
            </div>
          </div>
        </div>
      </SettingsPanel>
    </form>
  );
}

function RecoveryCodes({ codes, onKept }: { codes: string[]; onKept: () => void }) {
  const toast = useToast();

  async function copy() {
    toast(
      (await copyText(codes.join("\n")))
        ? "The recovery codes were copied."
        : "Could not copy them. Select them and copy by hand.",
    );
  }

  function download() {
    saveBlob("recovery-codes.txt", new Blob([`${codes.join("\n")}\n`], { type: "text/plain" }));
  }

  return (
    <SettingsPanel
      foot={
        <>
          <button type="button" className="secondary" onClick={() => void copy()}>
            Copy all
          </button>
          <button type="button" className="secondary" onClick={download}>
            Download as text
          </button>
          <button type="button" className="primary" onClick={onKept}>
            I have kept them
          </button>
        </>
      }
    >
      <div className="settings-panel-pad account-second-factor">
        <p>
          Your second factor is on. Keep these recovery codes: each signs you in once if you lose your phone. They are
          shown only now.
        </p>
        <ul className="second-factor-codes" aria-label="Recovery codes">
          {codes.map((code) => (
            <li key={code} className="mono">
              {code}
            </li>
          ))}
        </ul>
      </div>
    </SettingsPanel>
  );
}

/** Asks for a code from the app, or a recovery code, before an action that needs one. */
function CodeDialog({
  title,
  help,
  confirmLabel,
  danger,
  onClose,
  onSubmit,
}: {
  title: string;
  help: string;
  confirmLabel: string;
  danger?: boolean;
  onClose: () => void;
  onSubmit: (code: string) => Promise<void>;
}) {
  const [code, setCode] = useState("");
  const [problem, setProblem] = useState("");
  const [pending, setPending] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setProblem("");
    try {
      await onSubmit(code.trim());
    } catch (cause) {
      setProblem(errorMessage(cause));
      setPending(false);
    }
  }

  return (
    <Modal title={title} eyebrow="You" size="compact" busy={pending} onClose={onClose}>
      <form noValidate onSubmit={(event) => void submit(event)}>
        <p>{help}</p>
        <FormField label="Code from the app, or a recovery code" error={problem || undefined}>
          {(control) => (
            <input
              {...control}
              className="mono"
              autoComplete="one-time-code"
              autoCapitalize="none"
              spellCheck={false}
              required
              autoFocus
              value={code}
              onChange={(event) => setCode(event.target.value)}
            />
          )}
        </FormField>
        <div className="dialog-actions">
          <button type="button" className="secondary" disabled={pending} onClick={onClose}>
            Cancel
          </button>
          <button className={danger ? "danger" : "primary"} disabled={pending || !code.trim()}>
            {pending ? "Working…" : confirmLabel}
          </button>
        </div>
      </form>
    </Modal>
  );
}
