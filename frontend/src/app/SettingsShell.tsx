/**
 * The Settings frame (ADR-039 `B-Settings`, Track U U3): a top bar reading "{product} / Settings"
 * with Back to applications and the account at the right, the settings navigation in the rail, and
 * the page. Settings are not workspace data, so there is no workspace switcher, no application tabs
 * and no data-context band. Below 760px the navigation moves into the same drawer the application
 * pages use, opened from a bar naming the current page, and Back to applications keeps only its icon.
 */

import { useState, type CSSProperties, type ReactNode } from "react";
import { SETTINGS_NAVIGATION } from "@/features/settings/navigation";
import { useLocalNumberPreference } from "@/lib/localPreference";
import { routePath } from "@/routing/routes";
import type { SettingsPage, SettingsRoute } from "@/types";
import { Icon } from "@/ui/Icon";
import { NavigationDrawer } from "@/ui/NavigationDrawer";
import { ResizeHandle } from "@/ui/ResizeHandle";
import { RouteLink } from "@/ui/RouteLink";
import { AccountMenu } from "./SettingsMenu";

export function SettingsShell({
  productName,
  page,
  backHref,
  onBack,
  onNavigate,
  children,
}: {
  productName: string;
  page: SettingsPage;
  /** Where Back to applications goes, as a URL. */
  backHref: string;
  onBack: () => void;
  onNavigate: (route: SettingsRoute) => void;
  children: ReactNode;
}) {
  const rail = useLocalNumberPreference("rdm:layout:navigation-width:v1", 248, 210, 380);
  const [navigationOpen, setNavigationOpen] = useState(false);
  const open = (next: SettingsPage) => {
    setNavigationOpen(false);
    onNavigate({ kind: "settings", page: next });
  };
  const current = SETTINGS_NAVIGATION.flatMap((group) => group.pages).find((item) => item.page === page);
  return (
    <div className="app-shell settings-shell" style={{ "--sidebar": `${rail.value}px` } as CSSProperties}>
      <a className="skip-link" href="#main-content">
        Skip to main content
      </a>
      <header className="global-header settings-topbar">
        <span className="product-mark settings-mark">
          <span aria-hidden="true">{productName.slice(0, 1)}</span>
          <strong>{productName}</strong>
        </span>
        <span className="settings-topbar-separator" aria-hidden="true">
          /
        </span>
        <span className="settings-topbar-title">Settings</span>
        <div className="topbar-spacer" />
        <RouteLink className="header-link settings-back" href={backHref} onNavigate={onBack}>
          <Icon name="arrow-left" size={15} />
          <span className="settings-back-label">Back to applications</span>
        </RouteLink>
        <AccountMenu
          settingsHref={routePath({ kind: "settings", page: "about" })}
          onOpenSettings={() => open("about")}
        />
      </header>
      <button
        type="button"
        className="navigation-toggle"
        aria-haspopup="dialog"
        aria-controls="settings-navigation"
        aria-expanded={navigationOpen}
        onClick={() => setNavigationOpen(true)}
      >
        <Icon name="menu" /> Settings: {current?.label}
      </button>
      <NavigationDrawer open={navigationOpen} onClose={() => setNavigationOpen(false)} title="Settings navigation">
        <nav id="settings-navigation" className="settings-rail" aria-label="Settings">
          {SETTINGS_NAVIGATION.map((group) => (
            <div key={group.label} className="settings-nav-group">
              <h2 className="nav-label">{group.label}</h2>
              <ul>
                {group.pages.map((item) => (
                  <li key={item.page}>
                    <RouteLink
                      className="settings-nav-link"
                      href={routePath({ kind: "settings", page: item.page })}
                      aria-current={item.page === page ? "page" : undefined}
                      onNavigate={() => open(item.page)}
                    >
                      {item.label}
                    </RouteLink>
                  </li>
                ))}
              </ul>
            </div>
          ))}
          {/* Fixed-position, so it stays inside the navigation landmark without affecting layout. */}
          <ResizeHandle
            className="navigation-resizer"
            label="Resize settings navigation"
            value={rail.value}
            min={210}
            max={380}
            onChange={rail.change}
            onReset={rail.reset}
          />
        </nav>
      </NavigationDrawer>
      <main id="main-content" className="workspace-main settings-main" tabIndex={-1}>
        {children}
      </main>
    </div>
  );
}
