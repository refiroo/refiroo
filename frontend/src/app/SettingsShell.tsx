/**
 * The Settings pages in the shared frame (`ShellFrame`, `TopBar`; Track U U3): the same top bar as
 * the application pages, with the Settings icon current, "← Back to ‹workspace›" in place of the
 * application tabs (0.17 SH1: the workspace the person came from, the default one when Settings
 * was opened directly), the settings navigation in the rail, and the page. Settings are not
 * workspace data, so there is no workspace switcher and no data-context band. Below 760px the navigation moves into the drawer, opened from
 * a bar naming the current page. A page with panes of its own (the model editor) asks for the
 * full width: no settings navigation, the top bar the same (0.10 A4a, D37).
 */

import { useEffect, useState, type ReactNode } from "react";
import { api } from "@/api/client";
import { SETTINGS_NAVIGATION, navigationFor } from "@/ui/settingsNavigation";
import { useHeldAnywhere } from "@/state/permissions";
import { routePath, workspaceRoute } from "@/routing/routes";
import type { ApplicationDefinition, EngineModel, RouteState, SettingsPage } from "@/types";
import { RouteLink } from "@/ui/RouteLink";
import { ShellFrame } from "./ShellFrame";
import { TopBar } from "./TopBar";

/** The label of the workspace Settings goes back to; its key until it is read. */
function useWorkspaceLabel(workspaceKey: string | undefined) {
  const [read, setRead] = useState<{ key: string; label: string }>();
  useEffect(() => {
    if (!workspaceKey) return;
    let active = true;
    Promise.resolve()
      .then(() => api.workspace(workspaceKey))
      .then(
        (workspace) => active && setRead({ key: workspaceKey, label: workspace.label }),
        () => undefined,
      );
    return () => {
      active = false;
    };
  }, [workspaceKey]);
  return read && read.key === workspaceKey ? read.label : undefined;
}

export function SettingsShell({
  model,
  page,
  workspaceKey,
  onHome,
  onSelectApplication,
  onNavigate,
  fullWidth = false,
  journey,
  children,
}: {
  model: EngineModel;
  page: SettingsPage;
  /** The workspace Back to the workspace returns to: where the person came from, else the default one. */
  workspaceKey?: string;
  onHome: () => void;
  onSelectApplication: (application: ApplicationDefinition) => void;
  onNavigate: (route: RouteState) => void;
  fullWidth?: boolean;
  /** The bar of the user journey this page is a step of, right below the top bar. */
  journey?: ReactNode;
  children: ReactNode;
}) {
  const navigation = navigationFor(useHeldAnywhere());
  const current = SETTINGS_NAVIGATION.flatMap((group) => group.pages).find((item) => item.page === page);
  const workspaceLabel = useWorkspaceLabel(workspaceKey);
  const workspace = workspaceKey ? workspaceRoute(workspaceKey) : undefined;
  return (
    <ShellFrame
      journey={journey}
      topBar={
        <TopBar
          model={model}
          inSettings
          backTo={
            workspace
              ? {
                  label: workspaceLabel ? `Back to ${workspaceLabel}` : "Back to the workspace",
                  href: routePath(workspace),
                  onBack: () => onNavigate(workspace),
                }
              : undefined
          }
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
              toggleLabel: `Settings: ${page === "index" ? "All pages" : (current?.label ?? "")}`,
              drawerTitle: "Settings navigation",
              resizeLabel: "Resize settings navigation",
              content: (close) => (
                <>
                  {/* On a phone the top bar has no room for it, so the drawer leads back (CSS shows it there only). */}
                  {workspace && (
                    <RouteLink
                      className="settings-nav-link settings-nav-back"
                      href={routePath(workspace)}
                      onNavigate={() => {
                        close();
                        onNavigate(workspace);
                      }}
                    >
                      ← {workspaceLabel ? `Back to ${workspaceLabel}` : "Back to the workspace"}
                    </RouteLink>
                  )}
                  <RouteLink
                    className="settings-nav-link settings-nav-index"
                    href={routePath({ kind: "settings", page: "index" })}
                    aria-current={page === "index" ? "page" : undefined}
                    onNavigate={() => {
                      close();
                      onNavigate({ kind: "settings", page: "index" });
                    }}
                  >
                    Settings
                  </RouteLink>
                  {navigation.map((group) => (
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
                  ))}
                </>
              ),
            }
      }
      main={{ className: fullWidth ? "settings-main model-editor-main" : "settings-main" }}
    >
      {children}
    </ShellFrame>
  );
}
