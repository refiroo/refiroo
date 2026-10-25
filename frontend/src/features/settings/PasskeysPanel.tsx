/**
 * Settings › Account › Passkeys (0.12 I4c, D389–D394): a person's passkeys by the name they gave
 * them, with when each was added and last used; rename and remove (a confirmation). A passkey is
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
import { Modal } from "@/ui/Modal";
import { Notice } from "@/ui/Notice";
import { Section } from "@/ui/Section";
import { Skeleton } from "@/ui/Skeleton";
import { useToast } from "@/ui/Toast";
import { useSettingsRead } from "./useSystem";

export function PasskeysPanel() {
  const { data: passkeys, error, retry } = useSettingsRead<Passkey[]>(api.myPasskeys);
  const [renaming, setRenaming] = useState<Passkey>();
  const [removing, setRemoving] = useState<Passkey>();
  const toast = useToast();

  return (
    <Section
      title="Passkeys"
      actions={
        <button type="button" className="primary" onClick={() => void addPasskey()}>
          <Icon name="plus" /> Add a passkey
        </button>
      }
    >
      {error ? (
        <InlineError message={error} onRetry={retry} />
      ) : !passkeys ? (
        <Skeleton label="Loading your passkeys" lines={2} />
      ) : (
        <div className="account-panel">
          <p className="account-muted account-panel-note">
            Sign in with your fingerprint, face or device PIN instead of a password, or after it as the second step. A
            passkey cannot be stolen by a look-alike page.
          </p>
          {passkeys.length > 0 && (
            <ul className="account-list" aria-label="Your passkeys">
              {passkeys.map((passkey) => (
                <li key={passkey.id} className="account-row">
                  <span className="account-tile" aria-hidden="true">
                    <Icon name="lock" size={20} />
                  </span>
                  <div className="account-row-text">
                    <strong>{passkey.name}</strong>
                    <span className="account-muted">
                      Added {formatServerDayTime(passkey.createdAt)} ·{" "}
                      {passkey.lastUsedAt ? `last used ${formatServerAgo(passkey.lastUsedAt)}` : "not used yet"}
                    </span>
                  </div>
                  <button
                    type="button"
                    className="ghost"
                    aria-label={`Rename ${passkey.name}`}
                    onClick={() => setRenaming(passkey)}
                  >
                    Rename
                  </button>
                  <button
                    type="button"
                    className="danger-ghost"
                    aria-label={`Remove ${passkey.name}`}
                    onClick={() => setRemoving(passkey)}
                  >
                    Remove…
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
      {renaming && (
        <RenameDialog
          passkey={renaming}
          onClose={() => setRenaming(undefined)}
          onRenamed={() => {
            setRenaming(undefined);
            toast("Saved.");
            retry();
          }}
        />
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
    </Section>
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
    <Modal title={`Remove ${passkey.name}?`} eyebrow="Passkey" size="compact" busy={pending} onClose={onClose}>
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
          <button type="button" className="secondary" disabled={pending} onClick={onClose}>
            Cancel
          </button>
          <button className="danger" disabled={pending || !proof}>
            {pending ? "Removing…" : "Remove passkey"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

function RenameDialog({
  passkey,
  onClose,
  onRenamed,
}: {
  passkey: Passkey;
  onClose: () => void;
  onRenamed: () => void;
}) {
  const [name, setName] = useState(passkey.name);
  const [problem, setProblem] = useState("");
  const [pending, setPending] = useState(false);

  async function save(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setProblem("");
    try {
      await api.renamePasskey(passkey.id, name.trim());
      onRenamed();
    } catch (cause) {
      setProblem(errorMessage(cause));
      setPending(false);
    }
  }

  return (
    <Modal title={`Rename ${passkey.name}`} eyebrow="Passkey" size="compact" busy={pending} onClose={onClose}>
      <form noValidate onSubmit={(event) => void save(event)}>
        <FormField label="Name" help="So you can tell your passkeys apart." error={problem || undefined}>
          {(control) => (
            <input
              {...control}
              required
              maxLength={100}
              autoFocus
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
          )}
        </FormField>
        {problem && <Notice tone="error">{problem}</Notice>}
        <div className="dialog-actions">
          <button type="button" className="secondary" disabled={pending} onClick={onClose}>
            Cancel
          </button>
          <button className="primary" disabled={pending || !name.trim() || name.trim() === passkey.name}>
            {pending ? "Saving…" : "Save"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
