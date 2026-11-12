/**
 * The one top bar (ADR-039, ADR-040): the product mark, which goes home, the applications as tabs,
 * each with a tile in its hue (`model/hues`), then the Settings icon and the account at the right.
 * Every page shows the same bar, its items in the same places at the same widths (the user,
 * 2026-10-15): an area changes only which item is current, marked by the same ink underline, the
 * application's tab or, on a settings page, the Settings icon. What belongs to one page goes in the
 * band under the bar, never in the bar.
 *
 * Left of the bell, the "?" opens the documentation in a new tab (HD); the guide and the API reference
 * carry the same bar (`public/brand/refiroo-header.css`).
 *
 * On a phone the tabs are left out in every area (0.10 N1): an application page's data-context band
 * chooses the application; from Settings the product mark goes home.
 */

import { useContext, useLayoutEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { API_URL } from "@/api/address";
import { InboxButton } from "@/features/inbox/InboxButton";
import { WorkspaceSearch } from "@/features/workspaces/WorkspaceSearch";
import { applicationHue } from "@/model/hues";
import { NOTIFICATIONS, routePath, viewRoute, workspaceRoute } from "@/routing/routes";
import type { ApplicationDefinition, EngineModel, ObjectItem, RouteState } from "@/types";
import { ControlPopover } from "@/ui/ControlPopover";
import { HueTile } from "@/ui/HueTile";
import { Icon } from "@/ui/Icon";
import { ProductMark } from "@/ui/ProductMark";
import { RouteLink } from "@/ui/RouteLink";
import { AccountMenu } from "./SettingsMenu";
import { useFrameArrangement } from "@/lib/scheme";
import { FrameSlotsContext } from "./frameSlots";
import { useInstanceProduct } from "./instanceProduct";

const SETTINGS: RouteState = { kind: "settings", page: "index" };
const ACCOUNT: RouteState = { kind: "settings", page: "account" };

/** The applications as buttons, each with its tile; the top bar's tabs and the phone band's menu (0.10 N1). */
export function ApplicationButtons({
  model,
  applications = model.applications,
  currentApplicationKey,
  onSelectApplication,
}: {
  model: EngineModel;
  /** The applications to show, in order; every one of the model's when omitted. */
  applications?: readonly ApplicationDefinition[];
  currentApplicationKey?: string;
  onSelectApplication: (application: ApplicationDefinition) => void;
}) {
  return applications.map((item) => (
    <button
      key={item.key}
      type="button"
      className="application-tab"
      aria-current={item.key === currentApplicationKey ? "page" : undefined}
      title={item.description ? `${item.name}: ${item.description}` : item.name}
      onClick={() => onSelectApplication(item)}
    >
      <HueTile hue={applicationHue(model, item.key)} icon={item.icon} size={20} />
      <span className="application-name">{item.name}</span>
    </button>
  ));
}

/** How many of the applications fit the room the tabs have (0.17 SH1); the rest go under More. */
export function fittingCount(widths: readonly number[], gap: number, available: number, moreWidth: number) {
  const all = widths.reduce((sum, width) => sum + width, 0) + gap * Math.max(widths.length - 1, 0);
  if (all <= available) return widths.length;
  let used = 0;
  let count = 0;
  for (const width of widths) {
    const next = used + (count ? gap : 0) + width;
    if (next + gap + moreWidth > available) break;
    used = next;
    count += 1;
  }
  return Math.max(count, 1);
}

/**
 * The applications as tabs. The ones that do not fit the bar go into a More menu; the current
 * application always stays among the tabs, in the place of the last one that fits (0.17 SH1, U-D14).
 */
function ApplicationTabs({
  model,
  currentApplicationKey,
  stacked = false,
  onSelectApplication,
}: {
  model: EngineModel;
  currentApplicationKey?: string;
  /** In a side column (0.17 UX1): one under the other, every one shown, none under More. */
  stacked?: boolean;
  onSelectApplication: (application: ApplicationDefinition) => void;
}) {
  const nav = useRef<HTMLElement>(null);
  const measure = useRef<HTMLDivElement>(null);
  const [fit, setFit] = useState<number>(model.applications.length);
  const count = model.applications.length;
  useLayoutEffect(() => {
    const element = nav.current;
    const ruler = measure.current;
    if (!element || !ruler) return;
    const update = () => {
      const tabs = [...ruler.querySelectorAll<HTMLElement>(".application-tab")];
      const more = tabs.pop();
      const gap = parseFloat(getComputedStyle(element).columnGap) || 0;
      setFit(
        fittingCount(
          tabs.map((tab) => tab.getBoundingClientRect().width),
          gap,
          element.clientWidth,
          more?.getBoundingClientRect().width ?? 0,
        ),
      );
    };
    update();
    if (typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(update);
    observer.observe(element);
    return () => observer.disconnect();
  }, [model.applications, count]);
  const { tabs, more } = useMemo(() => {
    const all = model.applications;
    if (stacked || fit >= all.length) return { tabs: all, more: [] as ApplicationDefinition[] };
    const current = all.findIndex((item) => item.key === currentApplicationKey);
    const shown = all.slice(0, fit);
    if (current >= fit) shown[fit - 1] = all[current];
    const keys = new Set(shown.map((item) => item.key));
    return { tabs: shown, more: all.filter((item) => !keys.has(item.key)) };
  }, [model.applications, fit, currentApplicationKey, stacked]);
  return (
    <nav ref={nav} className="application-nav" aria-label="Applications">
      <ApplicationButtons
        model={model}
        applications={tabs}
        currentApplicationKey={currentApplicationKey}
        onSelectApplication={onSelectApplication}
      />
      {more.length > 0 && (
        <ControlPopover
          label="More applications"
          trigger={
            <>
              More <Icon name="chevron-down" size={13} />
            </>
          }
          triggerClassName="application-tab application-more"
          placement="bottom start"
          className="band-popover"
          header={false}
        >
          {(close) => (
            <div className="band-applications" role="group" aria-label="More applications">
              <ApplicationButtons
                model={model}
                applications={more}
                currentApplicationKey={currentApplicationKey}
                onSelectApplication={(item) => {
                  close();
                  onSelectApplication(item);
                }}
              />
            </div>
          )}
        </ControlPopover>
      )}
      {/* Out of sight and of the tab order: the widths the tabs would take, and More's. */}
      <div ref={measure} className="application-nav-ruler" aria-hidden="true">
        {model.applications.map((item) => (
          <span key={item.key} className="application-tab">
            <HueTile hue={applicationHue(model, item.key)} icon={item.icon} size={20} />
            {item.name}
          </span>
        ))}
        <span className="application-tab">
          More <Icon name="chevron-down" size={13} />
        </span>
      </div>
    </nav>
  );
}

export function TopBar({
  model,
  currentApplicationKey,
  workspaceKey,
  dataContext,
  inSettings = false,
  tabs = true,
  backTo,
  onHome,
  onSelectApplication,
  onNavigate,
}: {
  model: EngineModel;
  /** The application whose tab is current; none on a settings page. */
  currentApplicationKey?: string;
  /**
   * The workspace open now: the account menu names the roles in it and the search looks across it.
   * None on a settings page and on Home.
   */
  workspaceKey?: string;
  /** The change set or publication the page shows: a record opened from the search stays in it. */
  dataContext?: { changeSetId?: string; publicationId?: string };
  inSettings?: boolean;
  /** The applications as tabs; the workspace's own page lists them itself and shows none. */
  tabs?: boolean;
  /** Settings only: the way back to the workspace the person came from, in place of the application tabs. */
  backTo?: { label: string; onBack: () => void; href: string };
  onHome: () => void;
  onSelectApplication: (application: ApplicationDefinition) => void;
  onNavigate: (route: RouteState) => void;
}) {
  const product = useInstanceProduct(model.product);
  // A theme with a side column takes the mark and the applications into its head, and in the `rail`
  // arrangement the actions into its foot (0.17 UX1, PP-D39); otherwise they stay in the bar.
  const { sideHead, sideFoot } = useContext(FrameSlotsContext);
  const actionsHost = useFrameArrangement() === "rail" ? sideFoot : null;
  const lead = (
    <>
      <button
        className="product-mark"
        onClick={() => onHome()}
        aria-label={`${product.name} home`}
        title={product.description}
      >
        <ProductMark name={product.name} />
      </button>
      {backTo ? (
        <nav className="application-nav" aria-label="Back to the workspace">
          <RouteLink className="topbar-back" href={backTo.href} title={backTo.label} onNavigate={backTo.onBack}>
            <Icon name="arrow-left" size={15} />
            {backTo.label}
          </RouteLink>
        </nav>
      ) : tabs ? (
        <ApplicationTabs
          model={model}
          currentApplicationKey={currentApplicationKey}
          stacked={sideHead !== null}
          onSelectApplication={onSelectApplication}
        />
      ) : (
        <nav className="application-nav" aria-label="Applications" />
      )}
    </>
  );
  const actions = (
    <div className="topbar-actions">
      <a
        className="topbar-icon-button topbar-help"
        href={`${API_URL}/docs/`}
        target="_blank"
        rel="noopener"
        aria-label="Help (opens the documentation in a new tab)"
        title="Help: the documentation"
      >
        <Icon name="help" size={18} />
      </a>
      <InboxButton applicationKey={currentApplicationKey ?? model.applications[0]?.key} onNavigate={onNavigate} />
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
      <AccountMenu
        workspaceKey={workspaceKey}
        settingsHref={routePath(SETTINGS)}
        accountHref={routePath(ACCOUNT)}
        notificationsHref={routePath(NOTIFICATIONS)}
        onOpenSettings={() => onNavigate(SETTINGS)}
        onOpenAccount={() => onNavigate(ACCOUNT)}
        onOpenNotifications={() => onNavigate(NOTIFICATIONS)}
      />
    </div>
  );
  return (
    <header className="global-header">
      {sideHead ? createPortal(lead, sideHead) : lead}
      <div className="topbar-spacer" />
      {workspaceKey && !inSettings && (
        <WorkspaceSearch
          workspaceKey={workspaceKey}
          model={model}
          label="Find a record in this workspace"
          placeholder="Find a record, a list or a place (⌘K)"
          destinations={[
            { label: "Home", hint: "Your workspaces", onOpen: onHome },
            {
              label: "This workspace's page",
              hint: "Your shelf, the applications, what changed",
              onOpen: () => onNavigate(workspaceRoute(workspaceKey)),
            },
            ...(currentApplicationKey
              ? [
                  {
                    label: "Change sets",
                    hint: "Of this workspace",
                    onOpen: () =>
                      onNavigate({ kind: "changeSets", applicationKey: currentApplicationKey, workspaceKey }),
                  },
                  {
                    label: "Publications",
                    hint: "Of this workspace",
                    onOpen: () =>
                      onNavigate({ kind: "publications", applicationKey: currentApplicationKey, workspaceKey }),
                  },
                ]
              : []),
            { label: "Inbox", hint: "Notifications", onOpen: () => onNavigate(NOTIFICATIONS) },
            { label: "Settings", hint: "Every page by task", onOpen: () => onNavigate(SETTINGS) },
            {
              label: "Appearance",
              hint: "Theme, light or dark",
              onOpen: () => onNavigate({ kind: "settings", page: "appearance" }),
            },
            { label: "Account", hint: "Your sign-in", onOpen: () => onNavigate(ACCOUNT) },
          ]}
          onOpenList={(list) => {
            const application = model.applications.find((item) => item.key === list.applicationKey);
            if (application) onNavigate(viewRoute(application, list.viewKey, workspaceKey));
          }}
          onOpen={(item: ObjectItem) =>
            onNavigate({
              kind: "detail",
              applicationKey: item.applicationKey,
              objectTypeKey: item.objectTypeKey,
              objectId: item.id,
              workspaceKey,
              ...dataContext,
            })
          }
        />
      )}
      {actionsHost ? createPortal(actions, actionsHost) : actions}
    </header>
  );
}
