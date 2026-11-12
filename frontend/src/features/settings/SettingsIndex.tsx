/**
 * Where Settings opens (0.17 SH1, PP-D37; ST1, PP-D65 and PP-D67): every page a person may open, grouped by
 * task in a panel of the group's colour, each with one line saying what it is for, About last. A page the
 * person may not open is not listed, and a group left with no page is not shown.
 */

import { useHeldAnywhere } from "@/features/security/permissions";
import { navigationFor } from "@/features/settings/navigation";
import { routePath } from "@/routing/routes";
import type { RouteState } from "@/types";
import { Icon } from "@/ui/Icon";
import { RouteLink } from "@/ui/RouteLink";
import { SettingsLayout } from "@/ui/SettingsLayout";
import { SettingsTile } from "@/ui/SettingsParts";

export function SettingsIndex({ onNavigate }: { onNavigate: (route: RouteState) => void }) {
  const groups = navigationFor(useHeldAnywhere());
  return (
    <SettingsLayout
      title="Settings"
      description="Everything about you, the workspaces, the people and this instance. Each line says what the page is for."
    >
      <div className="settings-index">
        {groups.map((group) => {
          const slug = group.label.toLowerCase().replace(/\W+/g, "-");
          const headingId = `settings-index-${slug}`;
          return (
            <section
              className="settings-panel settings-index-group"
              key={group.label}
              aria-labelledby={headingId}
              data-hue={group.hue}
            >
              <header>
                <SettingsTile icon={group.pages[0]!.icon} size={44} />
                <div>
                  <h2 id={headingId}>{group.label}</h2>
                  <p>{group.description}</p>
                </div>
              </header>
              <ul>
                {group.pages.map((item) => {
                  const route: RouteState = { kind: "settings", page: item.page };
                  const nameId = `${headingId}-${item.page}`;
                  return (
                    <li key={item.page}>
                      <RouteLink
                        className="settings-index-link"
                        href={routePath(route)}
                        onNavigate={() => onNavigate(route)}
                        aria-labelledby={nameId}
                        aria-describedby={`${nameId}-line`}
                      >
                        <SettingsTile icon={item.icon} size={32} />
                        <span>
                          <strong id={nameId}>{item.label}</strong>
                          <small id={`${nameId}-line`}>{item.line}</small>
                        </span>
                        <Icon name="chevron-right" />
                      </RouteLink>
                    </li>
                  );
                })}
              </ul>
            </section>
          );
        })}
      </div>
    </SettingsLayout>
  );
}
