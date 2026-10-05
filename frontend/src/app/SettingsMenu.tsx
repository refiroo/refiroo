/**
 * Personal settings, opened from the gear at the right of the top bar (ADR-039). Account is a
 * placeholder for the planned multi-user authentication; appearance is a per-browser preference.
 * U3 turns the gear into the link to the Settings area.
 */

import { ControlPopover } from "@/ui/ControlPopover";
import { Icon, type IconName } from "@/ui/Icon";
import { useThemePreference, type ThemePreference } from "@/lib/theme";

const THEMES: { value: ThemePreference; label: string; icon: IconName }[] = [
  { value: "system", label: "System", icon: "monitor" },
  { value: "light", label: "Light", icon: "sun" },
  { value: "dark", label: "Dark", icon: "moon" },
];

export function SettingsMenu() {
  const { theme, setTheme } = useThemePreference();
  return (
    <ControlPopover
      label="Settings"
      className="settings-popover"
      placement="bottom end"
      triggerClassName="topbar-icon-button"
      trigger={<Icon name="gear" size={18} />}
    >
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
        <legend>Appearance</legend>
        <div className="theme-choice">
          {THEMES.map((option) => (
            <label key={option.value} className={theme === option.value ? "selected" : undefined}>
              <input
                type="radio"
                name="theme"
                value={option.value}
                checked={theme === option.value}
                onChange={() => setTheme(option.value)}
              />
              <Icon name={option.icon} size={15} />
              {option.label}
            </label>
          ))}
        </div>
        <p className="settings-note">System follows your device. The choice is saved in this browser.</p>
      </fieldset>
    </ControlPopover>
  );
}
