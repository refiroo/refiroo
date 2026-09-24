/**
 * Personal settings, anchored to the bottom of the navigation rail. Account is a placeholder for
 * the planned multi-user authentication; appearance is a per-browser preference.
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
    <div className="sidebar-footer">
      <ControlPopover
        label="Settings"
        className="settings-popover"
        placement="top start"
        triggerClassName="settings-trigger"
        trigger={
          <>
            <span className="account-avatar" aria-hidden="true">
              <Icon name="user" size={16} />
            </span>
            <span className="settings-trigger-text">
              <strong>Local session</strong>
              <small>Settings</small>
            </span>
            <Icon name="gear" size={16} />
          </>
        }
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
    </div>
  );
}
