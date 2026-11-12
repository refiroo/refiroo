/**
 * Settings › Appearance (Track U U3): the theme (Current, Hearth, Studio, Instrument or Website purple; TH, 0.17 UX1), the light and dark choice, the default table density, the type palette and how
 * editable fields show their pencil (UA4 revision), all saved in this browser. Theme is the account popover's
 * preference; density is the default every table starts from, which a view's own choice overrides.
 */

import { ThemeChoice } from "@/app/SettingsMenu";
import { useThemePreference } from "@/lib/theme";
import { useDefaultTableDensity, type TableDensity } from "@/lib/tableDensity";
import { useEditHint, type EditHint } from "@/lib/editHint";
import { useSchemePreference, type ColourScheme } from "@/lib/scheme";
import { usePalettePreference, type TypePalette } from "@/lib/palette";
import type { ReactNode } from "react";
import type { Hue } from "@/model/hues";
import type { IconName } from "@/ui/Icon";
import { Choice } from "@/ui/Choice";
import { SettingsLayout } from "@/ui/SettingsLayout";
import { SettingRow, SettingsGroup, SettingsPanel, SettingsTile } from "@/ui/SettingsParts";
import { settingsHead } from "./navigation";

const DENSITIES: [TableDensity, string][] = [
  ["comfortable", "Comfortable"],
  ["compact", "Compact"],
];

const SCHEMES: [ColourScheme, string][] = [
  ["normal", "Current"],
  ["hearth", "Hearth"],
  ["studio", "Studio"],
  ["instrument", "Instrument"],
  ["purple", "Website purple"],
];

const PALETTES: [TypePalette, string][] = [
  ["b", "B: magenta and olive"],
  ["a", "A: plum and gold"],
];

const EDIT_HINTS: [EditHint, string][] = [
  ["hover", "On hover and focus"],
  ["always", "Always, faintly"],
];

/** One choice as a row: its name and help at the left, the segmented choice at the right (under the text when wide). */
function ChoiceRow({
  id,
  name,
  help,
  icon,
  hue,
  under = false,
  children,
}: {
  id: string;
  name: string;
  help: ReactNode;
  icon: IconName;
  hue?: Hue;
  under?: boolean;
  /** The choice, given the id of the help text that describes it. */
  children: (describedBy: string) => ReactNode;
}) {
  const helpId = `${id}-help`;
  return (
    <SettingRow
      lead={<SettingsTile icon={icon} hue={hue} />}
      name={name}
      help={<span id={helpId}>{help}</span>}
      under={under}
    >
      <div role="group" aria-label={name}>
        {children(helpId)}
      </div>
    </SettingRow>
  );
}

export function AppearancePage() {
  const { theme, setTheme } = useThemePreference();
  const { density, setDensity } = useDefaultTableDensity();
  const { hint, setHint } = useEditHint();
  const { palette, setPalette } = usePalettePreference();
  const { scheme, setScheme } = useSchemePreference();
  const head = settingsHead("appearance");
  return (
    <SettingsLayout
      {...head}
      title="Appearance"
      description="These choices are saved in this browser. Other browsers and devices keep their own."
    >
      <SettingsGroup
        title="Theme and colours"
        description="How refiroo is coloured and drawn. Light and dark apply to every theme."
      >
        <SettingsPanel>
          <ChoiceRow
            id="appearance-scheme"
            name="Theme"
            icon="sun"
            hue={head.hue}
            under
            help="Each theme has its own colours, typeface, corners and arrangement of the frame. Current is the one refiroo has had; Website purple wears the colours of the refiroo website. Light and dark below apply to every theme."
          >
            {(describedBy) => (
              <Choice
                name="appearance-scheme"
                value={scheme}
                options={SCHEMES}
                onChange={setScheme}
                describedBy={describedBy}
              />
            )}
          </ChoiceRow>
          <ChoiceRow
            id="appearance-theme"
            name="Light or dark"
            icon="moon"
            hue={head.hue}
            help="System follows your device's light or dark setting."
          >
            {(describedBy) => (
              <ThemeChoice theme={theme} onChange={setTheme} name="appearance-theme" describedBy={describedBy} />
            )}
          </ChoiceRow>
          <ChoiceRow
            id="appearance-palette"
            name="Type colours"
            icon="sliders"
            hue={head.hue}
            under
            help="The palette that colours each kind of record. The two differ in the third and fourth colours only."
          >
            {(describedBy) => (
              <Choice
                name="appearance-palette"
                value={palette}
                options={PALETTES}
                onChange={setPalette}
                describedBy={describedBy}
              />
            )}
          </ChoiceRow>
        </SettingsPanel>
      </SettingsGroup>
      <SettingsGroup
        title="Tables and records"
        description="How tables are spaced and how a record shows that a field can be edited."
      >
        <SettingsPanel>
          <ChoiceRow
            id="appearance-density"
            name="Table density"
            icon="table"
            hue={head.hue}
            help="The default for every table. A table's own choice in its Display menu overrides it."
          >
            {(describedBy) => (
              <Choice
                name="appearance-density"
                value={density}
                options={DENSITIES}
                onChange={setDensity}
                describedBy={describedBy}
              />
            )}
          </ChoiceRow>
          <ChoiceRow
            id="appearance-edit-hint"
            name="Edit pencil"
            icon="pencil"
            hue={head.hue}
            help="When a record's editable fields show their pencil. Touch screens always show it."
          >
            {(describedBy) => (
              <Choice
                name="appearance-edit-hint"
                value={hint}
                options={EDIT_HINTS}
                onChange={setHint}
                describedBy={describedBy}
              />
            )}
          </ChoiceRow>
        </SettingsPanel>
      </SettingsGroup>
    </SettingsLayout>
  );
}
