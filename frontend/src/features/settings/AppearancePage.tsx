/**
 * Settings › Appearance (Track U U3): the theme (Normal or Website purple, TH), the light and dark choice, the default table density, the type palette and how
 * editable fields show their pencil (UA4 revision), all saved in this browser. Theme is the account popover's
 * preference; density is the default every table starts from, which a view's own choice overrides.
 */

import { ThemeChoice } from "@/app/SettingsMenu";
import { useThemePreference } from "@/lib/theme";
import { useDefaultTableDensity, type TableDensity } from "@/lib/tableDensity";
import { useEditHint, type EditHint } from "@/lib/editHint";
import { useSchemePreference, type ColourScheme } from "@/lib/scheme";
import { usePalettePreference, type TypePalette } from "@/lib/palette";
import { FormField } from "@/ui/FormField";
import { Section } from "@/ui/Section";
import { SettingsLayout } from "@/ui/SettingsLayout";

const DENSITIES: { value: TableDensity; label: string }[] = [
  { value: "comfortable", label: "Comfortable" },
  { value: "compact", label: "Compact" },
];

const SCHEMES: { value: ColourScheme; label: string }[] = [
  { value: "normal", label: "Normal" },
  { value: "purple", label: "Website purple" },
];

const PALETTES: { value: TypePalette; label: string }[] = [
  { value: "b", label: "B: magenta and olive" },
  { value: "a", label: "A: plum and gold" },
];

const EDIT_HINTS: { value: EditHint; label: string }[] = [
  { value: "hover", label: "On hover and focus" },
  { value: "always", label: "Always, faintly" },
];

export function AppearancePage() {
  const { theme, setTheme } = useThemePreference();
  const { density, setDensity } = useDefaultTableDensity();
  const { hint, setHint } = useEditHint();
  const { palette, setPalette } = usePalettePreference();
  const { scheme, setScheme } = useSchemePreference();
  return (
    <SettingsLayout
      eyebrow="General"
      title="Appearance"
      description="These choices are saved in this browser. Other browsers and devices keep their own."
    >
      <Section title="Display">
        <FormField
          group
          label="Theme"
          help="Normal, or the colours of the refiroo website. Light and dark below apply to either."
        >
          {() => (
            <div className="theme-choice">
              {SCHEMES.map((option) => (
                <label key={option.value} className={scheme === option.value ? "selected" : undefined}>
                  <input
                    type="radio"
                    name="appearance-scheme"
                    value={option.value}
                    checked={scheme === option.value}
                    onChange={() => setScheme(option.value)}
                  />
                  {option.label}
                </label>
              ))}
            </div>
          )}
        </FormField>
        <FormField group label="Light or dark" help="System follows your device's light or dark setting.">
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
        <FormField
          group
          label="Type colours"
          help="The palette that colours each kind of record. The two differ in the third and fourth colours only."
        >
          {() => (
            <div className="theme-choice">
              {PALETTES.map((option) => (
                <label key={option.value} className={palette === option.value ? "selected" : undefined}>
                  <input
                    type="radio"
                    name="appearance-palette"
                    value={option.value}
                    checked={palette === option.value}
                    onChange={() => setPalette(option.value)}
                  />
                  {option.label}
                </label>
              ))}
            </div>
          )}
        </FormField>
        <FormField
          group
          label="Edit pencil"
          help="When a record's editable fields show their pencil. Touch screens always show it."
        >
          {() => (
            <div className="theme-choice">
              {EDIT_HINTS.map((option) => (
                <label key={option.value} className={hint === option.value ? "selected" : undefined}>
                  <input
                    type="radio"
                    name="appearance-edit-hint"
                    value={option.value}
                    checked={hint === option.value}
                    onChange={() => setHint(option.value)}
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
