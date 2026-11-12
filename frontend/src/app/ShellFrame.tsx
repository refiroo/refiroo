/**
 * The one page frame every area uses: the skip link, the top bar, the rail at the left (resizable,
 * its width remembered in this browser) and the main content. Below 760px the rail moves into the
 * navigation drawer, opened from a bar that names what it holds. Areas differ only in what they
 * put in the rail and the content. A page that lays out panes of its own (the model editor, 0.10
 * A4a, D37) has no rail and takes the full width. A page whose content is fitted to the window
 * (`main.fill`: a collection's table, 0.12 LS1, D371) does not scroll: the frame is the window's
 * height, the rail scrolls on its own, and the content's own part scrolls inside it.
 *
 * A theme arranges these parts (0.17 UX1, PP-D39; `lib/scheme`): `bars` as described; `sheet` with one side
 * column holding the mark, the applications and the rail, beside a raised page; `rail` with a narrow strip for
 * the mark, the applications and the account, the rail as a panel beside it, and the data context as a status
 * line. The side column exists from 761px up; on a phone every theme keeps the bar and the drawer.
 */

import { useMemo, useState, type CSSProperties, type ReactNode } from "react";
import { FrameSlotsContext } from "@/app/frameSlots";
import { PHONE_WIDTH, useMediaQuery } from "@/lib/hooks/useMediaQuery";
import { useLocalNumberPreference } from "@/lib/localPreference";
import { useFrameArrangement } from "@/lib/scheme";
import { ErrorBoundary } from "@/ui/ErrorBoundary";
import { Icon } from "@/ui/Icon";
import { NavigationDrawer } from "@/ui/NavigationDrawer";
import { ResizeHandle } from "@/ui/ResizeHandle";

export function ShellFrame({
  topBar,
  journey,
  rail,
  main,
  children,
}: {
  topBar: ReactNode;
  /** A user journey's bar, right below the top bar and across the full width (`JourneyBar`). */
  journey?: ReactNode;
  rail?: {
    id: string;
    /** `aside` for a browser beside the content, `nav` for a list of pages. */
    as: "aside" | "nav";
    label: string;
    className?: string;
    /** The phone bar's text, which opens the drawer. */
    toggleLabel: string;
    drawerTitle: string;
    resizeLabel: string;
    /**
     * What the rail's scroll position belongs to (`ui/navigationRail`): kept while it stays the
     * same, the rail opens at its top when it changes. Defaults to the rail's id.
     */
    scrollScope?: string;
    /** The rail's content; `close` shuts the drawer after a choice on a phone. */
    content: (close: () => void) => ReactNode;
  };
  main?: { className?: string; fill?: boolean };
  children: ReactNode;
}) {
  const width = useLocalNumberPreference("rdm:layout:navigation-width:v1", 248, 210, 380);
  const [navigationOpen, setNavigationOpen] = useState(false);
  const close = () => setNavigationOpen(false);
  const Rail = rail?.as ?? "nav";
  const frame = useFrameArrangement();
  const phone = useMediaQuery(PHONE_WIDTH);
  // The side column: always in `rail` (its strip is the way to the areas), with a rail only in `sheet`.
  const sided = !phone && (frame === "rail" || (frame === "sheet" && Boolean(rail)));
  const [sideHead, setSideHead] = useState<HTMLElement | null>(null);
  const [sideFoot, setSideFoot] = useState<HTMLElement | null>(null);
  const slots = useMemo(
    () => (sided ? { sideHead, sideFoot } : { sideHead: null, sideFoot: null }),
    [sided, sideHead, sideFoot],
  );
  const navigation = rail && (
    <>
      <button
        type="button"
        className="navigation-toggle"
        aria-haspopup="dialog"
        aria-controls={rail.id}
        aria-expanded={navigationOpen}
        onClick={() => setNavigationOpen(true)}
      >
        <Icon name="menu" /> {rail.toggleLabel}
      </button>
      <NavigationDrawer
        open={navigationOpen}
        onClose={close}
        title={rail.drawerTitle}
        scrollScope={rail.scrollScope ?? rail.id}
      >
        <Rail id={rail.id} className={rail.className} aria-label={rail.label}>
          {rail.content(close)}
          {/* Fixed-position, so it stays inside the navigation landmark without affecting layout. */}
          <ResizeHandle
            className="navigation-resizer"
            label={rail.resizeLabel}
            value={width.value}
            min={210}
            max={380}
            onChange={width.change}
            onReset={width.reset}
          />
        </Rail>
      </NavigationDrawer>
    </>
  );
  return (
    <div
      className={`app-shell${rail ? "" : " app-shell-full"}${main?.fill ? " app-shell-fill" : ""}${journey ? " app-shell-journey" : ""}${frame === "bars" ? "" : ` frame-${frame}`}${sided ? " app-shell-sided" : ""}`}
      style={rail ? ({ "--sidebar": `${width.value}px` } as CSSProperties) : undefined}
    >
      <a className="skip-link" href="#main-content">
        Skip to main content
      </a>
      <FrameSlotsContext.Provider value={slots}>
        {sided && (
          <div className="frame-side">
            <div className="frame-strip">
              <div className="frame-side-head" ref={setSideHead} />
              <div className="frame-side-foot" ref={setSideFoot} />
            </div>
            {navigation}
          </div>
        )}
        {topBar}
        {journey}
        {!sided && navigation}
      </FrameSlotsContext.Provider>
      <main
        id="main-content"
        className={`workspace-main${main?.fill ? " fill-main" : ""}${main?.className ? ` ${main.className}` : ""}`}
        tabIndex={-1}
      >
        <ErrorBoundary resetKey={window.location.pathname + window.location.search}>{children}</ErrorBoundary>
      </main>
    </div>
  );
}
