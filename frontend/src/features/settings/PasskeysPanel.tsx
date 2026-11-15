/**
 * Settings › Account › Passkeys (0.12 I4c, D389–D394): a person's passkeys by the name they gave
 * them, with when each was added and last used; rename in place and remove (a confirmation). A passkey is
 * made on the engine's own page, so **Add a passkey** leaves for it and comes back here: the
 * passkey belongs to the engine's host, where the sign-in page is. A passkey signs the person in
 * alone, or as the second step after a password.
 */

import { useState, type FormEvent } from "react";
import { api } from "@/api/client";
import { errorMessage } from "@/api/errors";
import { addPasskey } from "@/api/session";
import { formatServerAgo, formatServerDayTime } from "@/lib/dates";
import type { Passkey } from "@/types";
import { FormField } from "@/ui/FormField";
import { Icon } from "@/ui/Icon";
import { InlineError } from "@/ui/InlineError";
import { CancelButton, Modal } from "@/ui/Modal";
import { SettingRow, SettingsEmpty, SettingsGroup, SettingsPanel, SettingsTile } from "@/ui/SettingsParts";
import { Skeleton } from "@/ui/Skeleton";
import { TextInPlace } from "@/ui/TextInPlace";
import { useToast } from "@/ui/Toast";
import { settingsHead } from "@/ui/settingsNavigation";
import { useSettingsRead } from "@/state/useSystem";

export function PasskeysPanel() {
  const { data: passkeys, error, retry } = useSettingsRead<Passkey[]>(api.myPasskeys);
  const [removing, setRemoving] = useState<Passkey>();
  const toast = useToast();

  return (
    <SettingsGroup
      title="Passkeys"
      description="Sign in with your fingerprint, face or device PIN instead of a password, or after it as the second step. A passkey cannot be stolen by a look-alike page."
      action={
        <button type="button" className="secondary" onClick={() => void addPasskey()}>
          <Icon name="plus" /> Add a passkey
        </button>
      }
    >
      {error ? (
        <InlineError message={error} onRetry={retry} />
      ) : !passkeys ? (
        <Skeleton label="Loading your passkeys" lines={2} />
      ) : (
        <SettingsPanel>
          {passkeys.length === 0 ? (
            <SettingsEmpty icon="key" hue={settingsHead("account").hue}>
              You have no passkey yet.
            </SettingsEmpty>
          ) : (
            <ul className="account-list" aria-label="Your passkeys">
              {passkeys.map((passkey) => (
                <li key={passkey.id}>
                  <SettingRow
                    lead={<SettingsTile icon="key" hue={settingsHead("account").hue} />}
                    name={
                      <TextInPlace
                        value={passkey.name}
                        label={`Name of ${passkey.name}`}
                        maxLength={100}
                        onSave={async (name) => {
                          await api.renamePasskey(passkey.id, name);
                          retry();
                          return () => api.renamePasskey(passkey.id, passkey.name).then(retry);
                        }}
                      >
                        <strong>{passkey.name}</strong>
                      </TextInPlace>
                    }
                    help={`Added ${formatServerDayTime(passkey.createdAt)} · ${
                      passkey.lastUsedAt ? `last used ${formatServerAgo(passkey.lastUsedAt)}` : "not used yet"
                    }`}
                  >
                    <button
                      type="button"
                      className="danger-ghost"
                      aria-label={`Remove ${passkey.name}`}
                      onClick={() => setRemoving(passkey)}
                    >
                      Remove…
                    </button>
                  </SettingRow>
                </li>
              ))}
            </ul>
          )}
        </SettingsPanel>
      )}
      {removing && (
        <RemoveDialog
          passkey={removing}
          onClose={() => setRemoving(undefined)}
          onRemoved={() => {
            toast(`The passkey ${removing.name} was removed.`);
            setRemoving(undefined);
            retry();
          }}
        />
      )}
    </SettingsGroup>
  );
}

/** Removing a passkey asks for the password again (or a code), so a stolen session cannot do it. */
function RemoveDialog({
  passkey,
  onClose,
  onRemoved,
}: {
  passkey: Passkey;
  onClose: () => void;
  onRemoved: () => void;
}) {
  const [proof, setProof] = useState("");
  const [problem, setProblem] = useState("");
  const [pending, setPending] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setProblem("");
    try {
      await api.removePasskey(passkey.id, proof);
      onRemoved();
    } catch (cause) {
      setProblem(errorMessage(cause));
      setPending(false);
    }
  }

  return (
    <Modal
      title={`Remove ${passkey.name}?`}
      eyebrow="You"
      size="compact"
      busy={pending}
      dirty={Boolean(proof)}
      onClose={onClose}
    >
      <form noValidate onSubmit={(event) => void submit(event)}>
        <p>
          You can no longer sign in with {passkey.name}. Remove the passkey from your device or password manager as
          well, so it is not offered again.
        </p>
        <FormField label="Your password, or a code from your authenticator app" error={problem || undefined}>
          {(control) => (
            <input
              {...control}
              type="password"
              autoComplete="current-password"
              required
              autoFocus
              value={proof}
              onChange={(event) => setProof(event.target.value)}
            />
          )}
        </FormField>
        <div className="dialog-actions">
          <CancelButton disabled={pending} />
          <button className="danger" disabled={pending || !proof}>
            {pending ? "Removing…" : "Remove passkey"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
