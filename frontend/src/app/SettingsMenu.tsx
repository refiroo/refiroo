/**
 * The account popover at the right of both top bars (ADR-039, Track U U3): the account (a
 * placeholder until multi-user authentication), the theme, and a link to all settings. Theme is
 * the same per-browser preference Settings › Appearance writes.
 */

import { ControlPopover } from "@/ui/ControlPopover";
import { Icon, type IconName } from "@/ui/Icon";
import { RouteLink } from "@/ui/RouteLink";
import { useThemePreference, type ThemePreference } from "@/lib/theme";

export const THEMES: { value: ThemePreference; label: string; icon: IconName }[] = [
  { value: "system", label: "System", icon: "monitor" },
  { value: "light", label: "Light", icon: "sun" },
  { value: "dark", label: "Dark", icon: "moon" },
];

export function AccountMenu({ settingsHref, onOpenSettings }: { settingsHref: string; onOpenSettings: () => void }) {
  const { theme, setTheme } = useThemePreference();
  return (
    <ControlPopover
      label="Account"
      className="settings-popover"
      placement="bottom end"
      triggerClassName="topbar-icon-button account-button"
      trigger={
        <span className="account-avatar" aria-hidden="true">
          <Icon name="user" size={16} />
        </span>
      }
    >
      {(close) => (
        <>
          <section className="settings-section" aria-labelledby="settings-account">
            <h3 id="settings-account">Account</h3>
            <div className="account-card">
              <span className="account-avatar" aria-hidden="true">
                <Icon name="user" size={18} />
              </span>
              <div>
                <strong>Local session</strong>
                <small>Single-user mode. No sign-in is required.</small>
              </div>
            </div>
            <button type="button" className="secondary" disabled aria-describedby="settings-auth-note">
              Sign in
            </button>
            <p id="settings-auth-note" className="settings-note">
              Multi-user authentication and per-user attribution are planned for a later release.
            </p>
          </section>
          <fieldset className="settings-section">
            <legend>Theme</legend>
            <ThemeChoice theme={theme} onChange={setTheme} name="account-theme" />
            <p className="settings-note">System follows your device. The choice is saved in this browser.</p>
          </fieldset>
          <div className="settings-section">
            <RouteLink
              className="settings-all-link"
              href={settingsHref}
              onNavigate={() => {
                close();
                onOpenSettings();
              }}
            >
              <Icon name="gear" size={15} /> All settings
            </RouteLink>
          </div>
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
