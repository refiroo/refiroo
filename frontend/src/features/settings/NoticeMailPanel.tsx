/**
 * Settings › Account › Email (0.12 M2, D432, D433): one switch, "Email me when something arrives in
 * my inbox", with the address the mail goes to. Off until the person switches it on. Where it cannot
 * work (mail is not set up, the person has no address, a client) the engine says so and the panel is
 * not shown at all: nothing here is disabled with a reason.
 */

import { useEffect, useState } from "react";
import { api } from "@/api/client";
import { errorMessage } from "@/api/errors";
import type { NoticeMail } from "@/types";
import { Icon } from "@/ui/Icon";
import { Notice } from "@/ui/Notice";
import { Section } from "@/ui/Section";
import { Switch } from "@/ui/Switch";

export function NoticeMailPanel() {
  const [state, setState] = useState<NoticeMail>();
  const [pending, setPending] = useState(false);
  const [failure, setFailure] = useState("");

  useEffect(() => {
    let active = true;
    // A page that cannot read it simply does not offer it.
    api
      .myNoticeMail()
      .then((loaded) => active && setState(loaded))
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, []);

  async function change(enabled: boolean) {
    setPending(true);
    setFailure("");
    try {
      setState(await api.setMyNoticeMail(enabled));
    } catch (cause) {
      setFailure(errorMessage(cause));
    } finally {
      setPending(false);
    }
  }

  // Where it is on, it stays shown so it can be switched off even if mail has since been removed.
  if (!state || !(state.available || state.enabled)) return null;
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
            onChange={(enabled) => void change(enabled)}
          />
        </div>
      </div>
    </Section>
  );
}
