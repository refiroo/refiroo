/**
 * The one top bar (ADR-039, ADR-040): the product mark, which goes home, the applications as tabs,
 * each with a tile in its hue (`model/hues`), then the Settings icon and the account at the right.
 * Every page shows the same bar, its items in the same places at the same widths (the user,
 * 2026-10-15): an area changes only which item is current, marked by the same ink underline, the
 * application's tab or, on a settings page, the Settings icon. What belongs to one page goes in the
 * band under the bar, never in the bar.
 *
 * On a phone the tabs are left out in every area (0.10 N1): an application page's data-context band
 * chooses the application; from Settings the product mark goes home.
 */

import { applicationHue } from "@/model/hues";
import { routePath } from "@/routing/routes";
import type { ApplicationDefinition, EngineModel, RouteState } from "@/types";
import { HueTile } from "@/ui/HueTile";
import { Icon } from "@/ui/Icon";
import { RouteLink } from "@/ui/RouteLink";
import { AccountMenu } from "./SettingsMenu";

const SETTINGS: RouteState = { kind: "settings", page: "about" };

/** The applications as buttons, each with its tile; the top bar's tabs and the phone band's menu (0.10 N1). */
export function ApplicationButtons({
  model,
  currentApplicationKey,
  onSelectApplication,
}: {
  model: EngineModel;
  currentApplicationKey?: string;
  onSelectApplication: (application: ApplicationDefinition) => void;
}) {
  return model.applications.map((item) => (
    <button
      key={item.key}
      type="button"
      className="application-tab"
      aria-current={item.key === currentApplicationKey ? "page" : undefined}
      title={item.description}
      onClick={() => onSelectApplication(item)}
    >
      <HueTile hue={applicationHue(model, item.key)} icon={item.icon} size={20} />
      {item.name}
    </button>
  ));
}

export function TopBar({
  model,
  currentApplicationKey,
  inSettings = false,
  onHome,
  onSelectApplication,
  onNavigate,
}: {
  model: EngineModel;
  /** The application whose tab is current; none on a settings page. */
  currentApplicationKey?: string;
  inSettings?: boolean;
  onHome: () => void;
  onSelectApplication: (application: ApplicationDefinition) => void;
  onNavigate: (route: RouteState) => void;
}) {
  return (
    <header className="global-header">
      <button className="product-mark" onClick={() => onHome()} aria-label={`${model.product.name} home`}>
        <span>{model.product.name.slice(0, 1)}</span>
        <strong>{model.product.name}</strong>
      </button>
      <nav className="application-nav" aria-label="Applications">
        <ApplicationButtons
          model={model}
          currentApplicationKey={currentApplicationKey}
          onSelectApplication={onSelectApplication}
        />
      </nav>
      <div className="topbar-spacer" />
      <div className="topbar-actions">
        <RouteLink
          className="topbar-icon-button topbar-settings"
          href={routePath(SETTINGS)}
          aria-label="Settings"
          aria-current={inSettings ? "page" : undefined}
          title="Settings"
          onNavigate={() => onNavigate(SETTINGS)}
        >
          <Icon name="gear" size={18} />
        </RouteLink>
        <AccountMenu settingsHref={routePath(SETTINGS)} onOpenSettings={() => onNavigate(SETTINGS)} />
      </div>
    </header>
  );
}
