/**
 * Settings › Notifications › Email (0.12 M2, D432, D433; kinds D434, D435): the switch "Email me
 * when something arrives in my inbox", with the address the mail goes to, and under it one switch for
 * each kind of notice the engine makes (its list and its labels; nothing is listed here). Everything
 * is on until switched off; a kind switched off stops the e-mail only. The page decides whether to
 * show the panel at all: nothing here is disabled with a reason.
 */

import { useState } from "react";
import { api } from "@/api/client";
import { errorMessage } from "@/api/errors";
import type { NoticeMail } from "@/types";
import { Icon } from "@/ui/Icon";
import { Notice } from "@/ui/Notice";
import { Section } from "@/ui/Section";
import { Switch } from "@/ui/Switch";

export function NoticeMailPanel({ state, onChange }: { state: NoticeMail; onChange: (next: NoticeMail) => void }) {
  const [pending, setPending] = useState(false);
  const [failure, setFailure] = useState("");

  async function save(change: { enabled?: boolean; kinds?: Record<string, boolean> }) {
    setPending(true);
    setFailure("");
    try {
      onChange(await api.setMyNoticeMail(change));
    } catch (cause) {
      setFailure(errorMessage(cause));
    } finally {
      setPending(false);
    }
  }

  return (
    <Section title="Email">
      <div className="account-panel">
        {failure && <Notice tone="error">{failure}</Notice>}
        <div className="account-row">
          <span className="account-tile" aria-hidden="true">
            <Icon name="bell" size={20} />
          </span>
          <div className="account-row-text">
            <strong>Email me when something arrives in my inbox</strong>
            <span className="account-muted">
              One short message for each notice, sent to {state.email ?? "your address"}. It says what kind of notice it
              is and links here; it never names a record or a change set.
            </span>
          </div>
          <Switch
            label="Email me when something arrives in my inbox"
            checked={state.enabled}
            disabled={pending}
            onChange={(enabled) => void save({ enabled })}
          />
        </div>
        <fieldset className="account-kinds" disabled={!state.enabled}>
          <legend>Send me an email for</legend>
          {state.kinds.map((item) => (
            <div className="account-row" key={item.kind}>
              <div className="account-row-text">
                <span>{item.label}</span>
              </div>
              <Switch
                label={item.label}
                checked={item.enabled}
                disabled={pending || !state.enabled}
                onChange={(enabled) => void save({ kinds: { [item.kind]: enabled } })}
              />
            </div>
          ))}
          <p className="account-muted account-kinds-note">
            A kind you switch off is not mailed. It still arrives in your inbox. These choices apply only while the
            switch above is on.
          </p>
        </fieldset>
      </div>
    </Section>
  );
}
