/**
 * Settings › Notifications › Email (0.12 M2, D432, D433; kinds D434, D435; digests 0.16 AO3): the
 * switch "Email me when something arrives in my inbox", with the address the mail goes to, and under
 * it one three-way choice for each kind of notice the engine makes (its list and its labels; nothing
 * is listed here): mailed at once (until changed), in the digest, or no mail. The digest comes every
 * morning or on Mondays at 07:00 in the time zone the browser reports, and the page says when the next
 * is due. Only the mail changes: the inbox keeps every notice. The page decides whether to show the
 * panel at all: nothing here is disabled with a reason.
 */

import { useState } from "react";
import { api } from "@/api/client";
import { errorMessage } from "@/api/errors";
import type { Hue } from "@/model/hues";
import type { NoticeDelivery, NoticeMail } from "@/types";
import { Choice } from "@/ui/Choice";
import { Notice } from "@/ui/Notice";
import { SettingRow, SettingsGroup, SettingsPanel, SettingsTile } from "@/ui/SettingsParts";
import { Switch } from "@/ui/Switch";

const DELIVERIES = [
  ["now", "At once"],
  ["digest", "Digest"],
  ["off", "Off"],
] as const;
const FREQUENCIES = [
  ["daily", "Every morning at 07:00"],
  ["weekly", "Mondays at 07:00"],
] as const;

/** The time zone the browser reports, which the digest's 07:00 is read in. */
export function browserTimeZone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
  } catch {
    return "UTC";
  }
}

/** "Tuesday 3 November, 07:00" in the given zone. */
export function digestTime(at: string, timeZone: string): string {
  const moment = new Date(at);
  try {
    const day = new Intl.DateTimeFormat("en-GB", { weekday: "long", day: "numeric", month: "long", timeZone }).format(
      moment,
    );
    const time = new Intl.DateTimeFormat("en-GB", {
      hour: "2-digit",
      minute: "2-digit",
      hourCycle: "h23",
      timeZone,
    }).format(moment);
    return `${day.replace(",", "")}, ${time}`;
  } catch {
    return moment.toISOString();
  }
}

export function NoticeMailPanel({
  state,
  onChange,
  hue,
}: {
  state: NoticeMail;
  onChange: (next: NoticeMail) => void;
  /** The page's colour, for the row's tile. */
  hue?: Hue;
}) {
  const [pending, setPending] = useState(false);
  const [failure, setFailure] = useState("");

  async function save(change: Parameters<typeof api.setMyNoticeMail>[0]) {
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

  /** The first kind put in the digest starts one, daily, in the browser's time zone. */
  const choose = (kind: string, delivery: NoticeDelivery) =>
    void save({
      kinds: { [kind]: delivery },
      ...(delivery === "digest" && !state.digest ? { digest: { every: "daily", timeZone: browserTimeZone() } } : {}),
    });
  const every = state.digest?.every ?? "daily";

  return (
    <SettingsGroup
      title="Email"
      description={
        <p>
          Sent to {state.email ?? "your address"}. A mail says what kind of notice it is and links here; it never names
          a record or a change set.
        </p>
      }
    >
      {failure && <Notice tone="error">{failure}</Notice>}
      <SettingsPanel>
        <SettingRow
          keep
          lead={<SettingsTile icon="bell" hue={hue} />}
          name="Email me when something arrives in my inbox"
          help="Off: nothing is mailed, whatever is chosen below. Your inbox keeps every notice either way."
        >
          <Switch
            label="Email me when something arrives in my inbox"
            checked={state.enabled}
            disabled={pending}
            onChange={(enabled) => void save({ enabled })}
          />
        </SettingRow>
      </SettingsPanel>
      <SettingsPanel>
        <fieldset className="settings-fieldset" disabled={!state.enabled}>
          <legend>How each kind reaches me</legend>
          {state.kinds.map((item) => (
            <SettingRow key={item.kind} name={<span className="setting-row-plain">{item.label}</span>}>
              <div role="radiogroup" aria-label={item.label}>
                <Choice
                  name={`delivery-${item.kind}`}
                  value={item.delivery}
                  options={DELIVERIES}
                  onChange={(delivery) => !pending && choose(item.kind, delivery)}
                />
              </div>
            </SettingRow>
          ))}
        </fieldset>
      </SettingsPanel>
      <SettingsPanel>
        <fieldset className="settings-fieldset" disabled={!state.enabled}>
          <legend>The digest</legend>
          <SettingRow
            name={<span className="setting-row-plain">One mail with everything set to Digest</span>}
            help={
              <>
                {state.digest
                  ? `In your time zone, ${state.digest.timeZone}.${
                      state.digest.nextAt
                        ? ` Next digest: ${digestTime(state.digest.nextAt, state.digest.timeZone)}.`
                        : ""
                    }`
                  : "Choose Digest for a kind to start one."}{" "}
                No mail when there is nothing new; a notice you read before then is left out.
              </>
            }
          >
            <div role="radiogroup" aria-label="How often the digest comes">
              <Choice
                name="digest-every"
                value={every}
                options={FREQUENCIES}
                onChange={(next) => !pending && void save({ digest: { every: next, timeZone: browserTimeZone() } })}
              />
            </div>
          </SettingRow>
        </fieldset>
      </SettingsPanel>
    </SettingsGroup>
  );
}
