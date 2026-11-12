/**
 * Settings › Security › Signing keys (0.12 SP2, D356): the keys the engine signs access tokens
 * with, newest first. A new key starts every 30 days on its own and the previous one verifies its
 * tokens until they expire, so nobody acts on a rotation (D254). "Start a new key" rotates now;
 * "Retire the current key now", for a key that may have leaked, refuses its tokens at once.
 */

import { useRef, useState } from "react";
import { errorMessage } from "@/api/errors";
import { security } from "@/api/securityClient";
import { formatServerDayTime, formatServerTime } from "@/lib/dates";
import { useCursorFeed } from "@/lib/hooks/useCursorFeed";
import { ConfirmDialog } from "@/ui/ConfirmDialog";
import { InlineError } from "@/ui/InlineError";
import { Notice } from "@/ui/Notice";
import { SettingsLayout } from "@/ui/SettingsLayout";
import { LogFoot, SettingsEmpty, SettingsGroup, SettingsPanel } from "@/ui/SettingsParts";
import { SettingsTable } from "@/ui/SettingsTable";
import { Skeleton } from "@/ui/Skeleton";
import { StatusPill } from "@/ui/StatusPill";
import { useToast } from "@/ui/Toast";
import { settingsHead } from "@/features/settings/navigation";
import { signingKeyState } from "./securityText";

const TONE = { current: "success", verifying: "warning", retired: "neutral" } as const;

export function SigningKeysPage() {
  const feed = useCursorFeed((cursor) => security.signingKeys(cursor), []);
  const [confirming, setConfirming] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const retireRef = useRef<HTMLButtonElement>(null);
  const toast = useToast();
  const head = settingsHead("signing-keys");

  async function rotate(immediate: boolean) {
    setPending(true);
    setError("");
    try {
      const key = await security.rotateSigningKey(immediate);
      setConfirming(false);
      feed.reload();
      toast(
        immediate
          ? `Key ${key.kid} signs from now on; the tokens of the retired key are refused.`
          : `Key ${key.kid} signs from now on; the previous key verifies its tokens until they expire.`,
      );
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setPending(false);
    }
  }

  return (
    <SettingsLayout
      {...head}
      title="Signing keys"
      description="The engine signs every access token with its current key and starts a new one every 30 days on its own. A replaced key keeps verifying the tokens it signed until they expire. Nobody has to act on a rotation: sessions and clients move to the new key by themselves."
      actions={
        <>
          <button className="secondary" disabled={pending} onClick={() => void rotate(false)}>
            Start a new key
          </button>
          <button ref={retireRef} className="danger-ghost" disabled={pending} onClick={() => setConfirming(true)}>
            Retire the current key now
          </button>
        </>
      }
    >
      {error && !confirming && (
        <Notice tone="error" title="No new key was started">
          {error}
        </Notice>
      )}
      <SettingsGroup
        stacked
        title="Keys"
        description="Newest first. The current key signs; a replaced key verifies until its tokens expire; a retired key is refused."
      >
        {feed.error ? (
          <InlineError message={feed.error} onRetry={feed.retry} />
        ) : !feed.items.length ? (
          feed.loading ? (
            <Skeleton label="Loading keys" lines={3} />
          ) : (
            <SettingsPanel>
              <SettingsEmpty icon="key" hue={head.hue}>
                No key yet: one is made with the first token.
              </SettingsEmpty>
            </SettingsPanel>
          )
        ) : (
          <SettingsPanel>
            <SettingsTable label="Signing keys" columns={["Key ID", "State", "Created", "Replaced", "Retired"]}>
              {feed.items.map((key) => (
                <tr key={key.kid}>
                  <th scope="row" className="mono">
                    {key.kid}
                  </th>
                  <td data-label="State">
                    <StatusPill tone={TONE[key.state]}>{signingKeyState(key)}</StatusPill>
                  </td>
                  <td data-label="Created" className="when" title={formatServerTime(key.createdAt)}>
                    {formatServerDayTime(key.createdAt)}
                  </td>
                  <td
                    data-label="Replaced"
                    className="when"
                    title={key.rotatedAt ? formatServerTime(key.rotatedAt) : undefined}
                  >
                    {key.rotatedAt ? formatServerDayTime(key.rotatedAt) : "—"}
                  </td>
                  <td
                    data-label="Retired"
                    className="when"
                    title={key.state === "retired" && key.retiredAt ? formatServerTime(key.retiredAt) : undefined}
                  >
                    {key.state === "retired" && key.retiredAt ? formatServerDayTime(key.retiredAt) : "—"}
                  </td>
                </tr>
              ))}
            </SettingsTable>
            <LogFoot
              shown={feed.items.length}
              noun="keys"
              onMore={feed.hasMore ? feed.loadMore : undefined}
              loading={feed.loading}
            />
          </SettingsPanel>
        )}
      </SettingsGroup>
      {confirming && (
        <ConfirmDialog
          title="Retire the current key now?"
          confirmLabel="Retire it now"
          pending={pending}
          error={error}
          onCancel={() => {
            setConfirming(false);
            setError("");
            retireRef.current?.focus();
          }}
          onConfirm={() => void rotate(true)}
        >
          <p>
            For a key that may have leaked. Every token it signed is refused from the next request. People’s sessions
            renew without signing in again; each client is refused once and fetches a new token with its unchanged
            secret.
          </p>
        </ConfirmDialog>
      )}
    </SettingsLayout>
  );
}
