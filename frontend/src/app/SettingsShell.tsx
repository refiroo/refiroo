/**
 * The Settings pages in the shared frame (`ShellFrame`, `TopBar`; Track U U3): the same top bar as
 * the application pages, with the Settings icon current and no application tab, the settings
 * navigation in the rail, and the page. Settings are not workspace data, so there is no workspace
 * switcher, no data-context band and no way back: the product mark goes home, as on every page
 * (the user, 2026-10-15: the bar itself never changes). Below 760px the navigation moves into the drawer, opened from
 * a bar naming the current page. A page with panes of its own (the model editor) asks for the
 * full width: no settings navigation, the top bar the same (0.10 A4a, D37).
 */

import type { ReactNode } from "react";
import { SETTINGS_NAVIGATION, navigationFor } from "@/features/settings/navigation";
import { useHeldAnywhere } from "@/features/security/permissions";
import { routePath } from "@/routing/routes";
import type { ApplicationDefinition, EngineModel, RouteState, SettingsPage } from "@/types";
import { RouteLink } from "@/ui/RouteLink";
import { ShellFrame } from "./ShellFrame";
import { TopBar } from "./TopBar";

export function SettingsShell({
  model,
  page,
  onHome,
  onSelectApplication,
  onNavigate,
  fullWidth = false,
  children,
}: {
  model: EngineModel;
  page: SettingsPage;
  onHome: () => void;
  onSelectApplication: (application: ApplicationDefinition) => void;
  onNavigate: (route: RouteState) => void;
  fullWidth?: boolean;
  children: ReactNode;
}) {
  const navigation = navigationFor(useHeldAnywhere());
  const current = SETTINGS_NAVIGATION.flatMap((group) => group.pages).find((item) => item.page === page);
  return (
    <ShellFrame
      topBar={
        <TopBar
          model={model}
          inSettings
          onHome={onHome}
          onSelectApplication={onSelectApplication}
          onNavigate={onNavigate}
        />
      }
      rail={
        fullWidth
          ? undefined
          : {
              id: "settings-navigation",
              as: "nav",
              label: "Settings",
              className: "settings-rail",
              toggleLabel: `Settings: ${current?.label ?? ""}`,
              drawerTitle: "Settings navigation",
              resizeLabel: "Resize settings navigation",
              content: (close) =>
                navigation.map((group) => (
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
            }
      }
      main={{ className: fullWidth ? "settings-main model-editor-main" : "settings-main" }}
    >
      {children}
    </ShellFrame>
  );
}
