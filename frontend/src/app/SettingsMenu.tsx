/**
 * The account popover at the right of both top bars (ADR-039, Track U U3, 0.12 I2): who is signed
 * in and the roles they hold in the workspace open now (Z1), their Account page, all settings, the
 * theme, and signing out, each action a button (the user, 2026-10-23). Theme is the same per-browser
 * preference Settings › Appearance writes.
 */

import { signOut } from "@/api/session";
import { ControlPopover } from "@/ui/ControlPopover";
import { Icon, type IconName } from "@/ui/Icon";
import { RouteLink } from "@/ui/RouteLink";
import { useThemePreference, type ThemePreference } from "@/lib/theme";
import { initials, useMe, useRoleLine, useSourceOffer } from "./useMe";

export const THEMES: { value: ThemePreference; label: string; icon: IconName }[] = [
  { value: "system", label: "System", icon: "monitor" },
  { value: "light", label: "Light", icon: "sun" },
  { value: "dark", label: "Dark", icon: "moon" },
];

export function AccountMenu({
  workspaceKey,
  settingsHref,
  accountHref,
  onOpenSettings,
  onOpenAccount,
}: {
  /** The workspace open now, whose roles the menu names; the default one in Settings. */
  workspaceKey?: string;
  settingsHref: string;
  accountHref: string;
  onOpenSettings: () => void;
  onOpenAccount: () => void;
}) {
  const { theme, setTheme } = useThemePreference();
  const me = useMe();
  const roleLine = useRoleLine(workspaceKey);
  const source = useSourceOffer();
  const avatar = me ? (
    <span className="account-avatar account-initials" aria-hidden="true">
      {initials(me.name)}
    </span>
  ) : (
    <span className="account-avatar" aria-hidden="true">
      <Icon name="user" size={16} />
    </span>
  );
  return (
    <ControlPopover
      label="Account"
      className="settings-popover"
      placement="bottom end"
      triggerClassName="topbar-icon-button account-button"
      trigger={avatar}
    >
      {(close) => (
        <>
          <section className="settings-section" aria-labelledby="settings-account">
            <h3 id="settings-account" className="visually-hidden">
              Signed in as
            </h3>
            <div className="account-card">
              {avatar}
              <div>
                <strong>{me?.name ?? "Signed in"}</strong>
                {me?.email && <small>{me.email}</small>}
                {roleLine && <small className="account-role-line">{roleLine}</small>}
              </div>
            </div>
            <RouteLink
              className="secondary account-menu-action"
              href={accountHref}
              onNavigate={() => {
                close();
                onOpenAccount();
              }}
            >
              <Icon name="user" size={15} /> Account
            </RouteLink>
            <RouteLink
              className="secondary account-menu-action"
              href={settingsHref}
              onNavigate={() => {
                close();
                onOpenSettings();
              }}
            >
              <Icon name="gear" size={15} /> All settings
            </RouteLink>
          </section>
          <fieldset className="settings-section">
            <legend>Theme</legend>
            <ThemeChoice theme={theme} onChange={setTheme} name="account-theme" />
            <p className="settings-note">System follows your device. The choice is saved in this browser.</p>
          </fieldset>
          <div className="settings-section">
            <button type="button" className="secondary account-menu-action" onClick={() => void signOut()}>
              Sign out
            </button>
          </div>
          {source && (
            <p className="settings-note account-source">
              <a href={source.sourceCode} target="_blank" rel="noreferrer">
                Source code
              </a>{" "}
              · {source.license}
            </p>
          )}
        </>
      )}
    </ControlPopover>
  );
}

/** The three themes as radio buttons; `name` keeps two groups on one page apart. */
export function ThemeChoice({
  theme,
  onChange,
  name,
  describedBy,
}: {
  theme: ThemePreference;
  onChange: (theme: ThemePreference) => void;
  name: string;
  describedBy?: string;
}) {
  return (
    <div className="theme-choice">
      {THEMES.map((option) => (
        <label key={option.value} className={theme === option.value ? "selected" : undefined}>
          <input
            type="radio"
            name={name}
            value={option.value}
            checked={theme === option.value}
            aria-describedby={describedBy}
            onChange={() => onChange(option.value)}
          />
          <Icon name={option.icon} size={15} />
          {option.label}
        </label>
      ))}
    </div>
  );
}
