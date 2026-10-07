/**
 * The one top bar (ADR-039, ADR-040): the product mark, which goes home, the applications as tabs,
 * each with a tile in its hue (`model/hues`), then the link to Settings and the account at the
 * right. Application pages and Settings show the same bar, and exactly one item in it is current,
 * marked the same way: the application's tab, or on a settings page the Settings link, which then
 * reads as a tab (icon, name, underline).
 *
 * `back` puts a way back after the product mark: an area that is a detour from where the user was
 * (Settings) returns there with it. Any area may pass one; the bar knows only its label and target.
 */

import { applicationHue } from "@/model/hues";
import { routePath } from "@/routing/routes";
import type { ApplicationDefinition, EngineModel, RouteState } from "@/types";
import { HueTile } from "@/ui/HueTile";
import { Icon } from "@/ui/Icon";
import { RouteLink } from "@/ui/RouteLink";
import { AccountMenu } from "./SettingsMenu";

const SETTINGS: RouteState = { kind: "settings", page: "about" };

/** A way back from the current area: what it returns to, its address and how to go there. */
export interface TopBarBack {
  label: string;
  href: string;
  onNavigate: () => void;
}

export function TopBar({
  model,
  currentApplicationKey,
  inSettings = false,
  back,
  onHome,
  onSelectApplication,
  onNavigate,
}: {
  model: EngineModel;
  /** The application whose tab is current; none on a settings page. */
  currentApplicationKey?: string;
  inSettings?: boolean;
  back?: TopBarBack;
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
      {back && (
        <RouteLink className="topbar-back" href={back.href} title={back.label} onNavigate={back.onNavigate}>
          <Icon name="arrow-left" size={15} />
          <span className="topbar-back-label">{back.label}</span>
        </RouteLink>
      )}
      <nav className="application-nav" aria-label="Applications">
        {model.applications.map((item) => (
          <button
            key={item.key}
            className="application-tab"
            aria-current={item.key === currentApplicationKey ? "page" : undefined}
            title={item.description}
            onClick={() => onSelectApplication(item)}
          >
            <HueTile hue={applicationHue(model, item.key)} icon={item.icon} size={20} />
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
