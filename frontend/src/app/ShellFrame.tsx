/**
 * The one page frame every area uses: the skip link, the top bar, the rail at the left (resizable,
 * its width remembered in this browser) and the main content. Below 760px the rail moves into the
 * navigation drawer, opened from a bar that names what it holds. Areas differ only in what they
 * put in the rail and the content.
 */

import { useState, type CSSProperties, type ReactNode } from "react";
import { useLocalNumberPreference } from "@/lib/localPreference";
import { Icon } from "@/ui/Icon";
import { NavigationDrawer } from "@/ui/NavigationDrawer";
import { ResizeHandle } from "@/ui/ResizeHandle";

export function ShellFrame({
  topBar,
  rail,
  main,
  children,
}: {
  topBar: ReactNode;
  rail: {
    id: string;
    /** `aside` for a browser beside the content, `nav` for a list of pages. */
    as: "aside" | "nav";
    label: string;
    className?: string;
    /** The phone bar's text, which opens the drawer. */
    toggleLabel: string;
    drawerTitle: string;
    resizeLabel: string;
    /** The rail's content; `close` shuts the drawer after a choice on a phone. */
    content: (close: () => void) => ReactNode;
  };
  main?: { className?: string };
  children: ReactNode;
}) {
  const width = useLocalNumberPreference("rdm:layout:navigation-width:v1", 248, 210, 380);
  const [navigationOpen, setNavigationOpen] = useState(false);
  const close = () => setNavigationOpen(false);
  const Rail = rail.as;
  return (
    <div className="app-shell" style={{ "--sidebar": `${width.value}px` } as CSSProperties}>
      <a className="skip-link" href="#main-content">
        Skip to main content
      </a>
      {topBar}
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
      <NavigationDrawer open={navigationOpen} onClose={close} title={rail.drawerTitle}>
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
      <main id="main-content" className={`workspace-main${main?.className ? ` ${main.className}` : ""}`} tabIndex={-1}>
        {children}
      </main>
    </div>
  );
}
