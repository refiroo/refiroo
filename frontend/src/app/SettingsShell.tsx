/**
 * The Settings pages in the shared frame (`ShellFrame`, `TopBar`; Track U U3): the same top bar as
 * the application pages, with the Settings link current and no application tab, the settings
 * navigation in the rail, and the page. Settings are not workspace data, so there is no workspace
 * switcher and no data-context band. Below 760px the navigation moves into the drawer, opened from
 * a bar naming the current page.
 */

import type { ReactNode } from "react";
import { SETTINGS_NAVIGATION } from "@/features/settings/navigation";
import { routePath } from "@/routing/routes";
import type { ApplicationDefinition, EngineModel, RouteState, SettingsPage } from "@/types";
import { RouteLink } from "@/ui/RouteLink";
import { ShellFrame } from "./ShellFrame";
import { TopBar, type TopBarBack } from "./TopBar";

export function SettingsShell({
  model,
  page,
  onHome,
  onSelectApplication,
  onNavigate,
  back,
  children,
}: {
  model: EngineModel;
  page: SettingsPage;
  onHome: () => void;
  onSelectApplication: (application: ApplicationDefinition) => void;
  onNavigate: (route: RouteState) => void;
  /** Back to the page the user opened Settings from. */
  back: TopBarBack;
  children: ReactNode;
}) {
  const current = SETTINGS_NAVIGATION.flatMap((group) => group.pages).find((item) => item.page === page);
  return (
    <ShellFrame
      topBar={
        <TopBar
          model={model}
          inSettings
          back={back}
          onHome={onHome}
          onSelectApplication={onSelectApplication}
          onNavigate={onNavigate}
        />
      }
      rail={{
        id: "settings-navigation",
        as: "nav",
        label: "Settings",
        className: "settings-rail",
        toggleLabel: `Settings: ${current?.label ?? ""}`,
        drawerTitle: "Settings navigation",
        resizeLabel: "Resize settings navigation",
        content: (close) =>
          SETTINGS_NAVIGATION.map((group) => (
            <div key={group.label} className="settings-nav-group">
              <h2 className="nav-label">{group.label}</h2>
              <ul>
                {group.pages.map((item) => (
                  <li key={item.page}>
                    <RouteLink
                      className="settings-nav-link"
                      href={routePath({ kind: "settings", page: item.page })}
                      aria-current={item.page === page ? "page" : undefined}
                      onNavigate={() => {
                        close();
                        onNavigate({ kind: "settings", page: item.page });
                      }}
                    >
                      {item.label}
                    </RouteLink>
                  </li>
                ))}
              </ul>
            </div>
          )),
      }}
      main={{ className: "settings-main" }}
    >
      {children}
    </ShellFrame>
  );
}
