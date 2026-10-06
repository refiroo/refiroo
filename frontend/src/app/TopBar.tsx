/**
 * The one top bar (ADR-039, ADR-040): the product mark, which goes home, the applications as tabs,
 * then the link to Settings and the account at the right. Application pages and Settings show the
 * same bar, and exactly one item in it is current, marked the same way: the application's tab, or
 * on a settings page the Settings link, which then reads as a tab (icon, name, underline).
 */

import { routePath } from "@/routing/routes";
import type { ApplicationDefinition, EngineModel, RouteState } from "@/types";
import { Icon, ModelIcon } from "@/ui/Icon";
import { RouteLink } from "@/ui/RouteLink";
import { AccountMenu } from "./SettingsMenu";

const SETTINGS: RouteState = { kind: "settings", page: "about" };

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
        {model.applications.map((item) => (
          <button
            key={item.key}
            className="application-tab"
            aria-current={item.key === currentApplicationKey ? "page" : undefined}
            title={item.description}
            onClick={() => onSelectApplication(item)}
          >
            <span className="application-glyph">
              <ModelIcon name={item.icon} size={15} />
            </span>
            {item.name}
          </button>
        ))}
      </nav>
      <div className="topbar-spacer" />
      <div className="topbar-actions">
        {inSettings ? (
          <RouteLink
            className="application-tab settings-tab"
            href={routePath(SETTINGS)}
            aria-current="page"
            onNavigate={() => onNavigate(SETTINGS)}
          >
            <span className="application-glyph">
              <Icon name="gear" size={15} />
            </span>
            Settings
          </RouteLink>
        ) : (
          <RouteLink
            className="topbar-icon-button"
            href={routePath(SETTINGS)}
            aria-label="Settings"
            title="Settings"
            onNavigate={() => onNavigate(SETTINGS)}
          >
            <Icon name="gear" size={18} />
          </RouteLink>
        )}
        <AccountMenu settingsHref={routePath(SETTINGS)} onOpenSettings={() => onNavigate(SETTINGS)} />
      </div>
    </header>
  );
}
