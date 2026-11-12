import type { ReactNode, Ref } from "react";
import type { Hue } from "@/model/hues";
import type { IconName } from "@/ui/Icon";
import { PageHeader } from "@/ui/PageHeader";
import { SettingsTile } from "@/ui/SettingsParts";

/**
 * A settings page (Track U U3, ADR-039 `B-Settings`; one shape since 0.17 ST1, PP-D60): the page header with its
 * group as the eyebrow and the page's glyph on a tile in the group's colour (`settingsHead(page)` gives the
 * three), the page's one main action at the title's right, then the page's groups (`ui/SettingsParts`). A page
 * under another (a job, an import profile, a person) shows its `trail` above; one that brings its own header
 * (`ItemHeader`) passes `header` in place of the title.
 */
export function SettingsLayout({
  eyebrow,
  hue,
  icon,
  trail,
  title,
  titleRef,
  description,
  actions,
  header,
  children,
}: {
  eyebrow?: ReactNode;
  /** The colour of the page's group (PP-D67). */
  hue?: Hue;
  /** The page's glyph, shown on a tile in `hue`. */
  icon?: IconName;
  /** `ui/Trail`: the group, the list the page belongs to, the page (0.10 A5c). */
  trail?: ReactNode;
  title?: ReactNode;
  titleRef?: Ref<HTMLHeadingElement>;
  description?: ReactNode;
  actions?: ReactNode;
  /** An opened item's own header, in place of the page header. */
  header?: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="settings-page">
      {trail}
      {header ?? (
        <PageHeader
          variant="detail"
          eyebrow={eyebrow}
          icon={icon && <SettingsTile icon={icon} hue={hue} size={48} />}
          title={title}
          titleRef={titleRef}
          description={description}
          actions={actions}
        />
      )}
      {children}
    </div>
  );
}
