/**
 * Settings › Appearance (Track U U3): the theme and the default table density, both saved in this
 * browser. Theme is the account popover's preference; density is the default every table starts
 * from, which a view's own choice overrides.
 */

import { ThemeChoice } from "@/app/SettingsMenu";
import { useThemePreference } from "@/lib/theme";
import { useDefaultTableDensity, type TableDensity } from "@/lib/tableDensity";
import { FormField } from "@/ui/FormField";
import { Section } from "@/ui/Section";
import { SettingsLayout } from "@/ui/SettingsLayout";

const DENSITIES: { value: TableDensity; label: string }[] = [
  { value: "comfortable", label: "Comfortable" },
  { value: "compact", label: "Compact" },
];

export function AppearancePage() {
  const { theme, setTheme } = useThemePreference();
  const { density, setDensity } = useDefaultTableDensity();
  return (
    <SettingsLayout
      eyebrow="General"
      title="Appearance"
      description="These choices are saved in this browser. Other browsers and devices keep their own."
    >
      <Section title="Display">
        <FormField group label="Theme" help="System follows your device's light or dark setting.">
          {() => <ThemeChoice theme={theme} onChange={setTheme} name="appearance-theme" />}
        </FormField>
        <FormField
          group
          label="Table density"
          help="The default for every table. A table's own choice in its Display menu overrides it."
        >
          {() => (
            <div className="theme-choice">
              {DENSITIES.map((option) => (
                <label key={option.value} className={density === option.value ? "selected" : undefined}>
                  <input
                    type="radio"
                    name="appearance-density"
                    value={option.value}
                    checked={density === option.value}
                    onChange={() => setDensity(option.value)}
                  />
                  {option.label}
                </label>
              ))}
            </div>
          )}
        </FormField>
      </Section>
    </SettingsLayout>
  );
}
