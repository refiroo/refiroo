/**
 * Settings › Notification email (0.12 M2 follow-up, D434; renamed in NT1, D463; digests and followed workspaces 0.16 AO3): what reaches the
 * person by e-mail. The notices themselves are on the Notifications page; this page only chooses
 * the mail. Where nothing can be chosen (mail is not set up, the person has no address, a client) it
 * says so in one sentence and offers no control.
 */

import { useEffect, useState } from "react";
import { api } from "@/api/client";
import { errorMessage } from "@/api/errors";
import type { NoticeMail } from "@/types";
import { InlineError } from "@/ui/InlineError";
import { SettingsLayout } from "@/ui/SettingsLayout";
import { SettingsEmpty, SettingsGroup, SettingsPanel } from "@/ui/SettingsParts";
import { Skeleton } from "@/ui/Skeleton";
import { settingsHead } from "./navigation";
import { FollowedWorkspaces } from "./FollowedWorkspaces";
import { NoticeMailPanel } from "./NoticeMailPanel";

const NOTHING_TO_CHOOSE: Record<string, string> = {
  "mail-not-set-up": "Email is not set up for this installation, so there is nothing to choose here.",
  "no-email": "Your account has no email address, so there is nothing to choose here.",
  "not-a-person": "Only people receive email, so there is nothing to choose here.",
};

export function NotificationsPage() {
  const [state, setState] = useState<NoticeMail>();
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let active = true;
    api
      .myNoticeMail()
      .then((loaded) => active && setState(loaded))
      .catch((cause) => active && setError(errorMessage(cause)));
    return () => {
      active = false;
    };
  }, [attempt]);

  const head = settingsHead("notifications");
  // Where it is on, it stays shown so it can be switched off even if mail has since been removed.
  const shown = state && (state.available || state.enabled);
  return (
    <SettingsLayout
      {...head}
      title="Notification email"
      description="Choose which notices reach you by email, and which workspaces you follow. Your inbox keeps all notices."
    >
      {error ? (
        <InlineError
          message={error}
          onRetry={() => {
            setError("");
            setAttempt((value) => value + 1);
          }}
        />
      ) : !state ? (
        <Skeleton label="Loading your notification settings" lines={3} />
      ) : shown ? (
        <>
          <NoticeMailPanel state={state} onChange={setState} hue={head.hue} />
          <FollowedWorkspaces hue={head.hue} />
        </>
      ) : (
        <>
          <SettingsGroup title="Email">
            <SettingsPanel>
              <SettingsEmpty icon="bell" hue={head.hue}>
                {NOTHING_TO_CHOOSE[state.reason ?? ""] ?? "There is nothing to choose here."}
              </SettingsEmpty>
            </SettingsPanel>
          </SettingsGroup>
          {state.reason !== "not-a-person" && <FollowedWorkspaces hue={head.hue} />}
        </>
      )}
    </SettingsLayout>
  );
}
