import type { ReactNode } from "react";
import { Icon } from "@/ui/Icon";

/** One place in a trail: its content (a link or a button to go there), the current one last. */
export interface Crumb {
  key: string;
  content: ReactNode;
  current?: boolean;
}

/** Numbers a list of places and marks the last as the current one: `crumbs(<TrailLink/>, "Thing")`. */
export function crumbs(...places: ReactNode[]): Crumb[] {
  return places.map((content, index) => ({ key: String(index), content, current: index === places.length - 1 }));
}

/**
 * The one line that says where a page stands (0.17 SH1, replacing `Breadcrumbs` and `TrailBar`):
 * optionally "← where the person came from", then the places above the page separated by "›" (a
 * record's ancestors; a Settings page under its list). Left-out places are skipped. It carries no
 * button of its own beside it: going back is the first words of the line.
 */
export function Trail({
  items = [],
  back,
}: {
  items?: (Crumb | false | undefined)[];
  /** The place the person came from, as the first words of the line. */
  back?: { label: ReactNode; onClick: () => void; href?: string };
}) {
  const places = items.filter((item): item is Crumb => Boolean(item));
  if (!back && places.length === 0) return null;
  return (
    <nav className="breadcrumbs trail" aria-label="Where you are">
      {back &&
        (back.href ? (
          <a
            className="trail-back"
            href={back.href}
            onClick={(event) => {
              if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0) return;
              event.preventDefault();
              back.onClick();
            }}
          >
            <Icon name="arrow-left" size={14} />
            {back.label}
          </a>
        ) : (
          <button type="button" className="trail-back" onClick={back.onClick}>
            <Icon name="arrow-left" size={14} />
            {back.label}
          </button>
        ))}
      {places.length > 0 && (
        <ol>
          {places.map((item) => (
            <li key={item.key} {...(item.current ? { "aria-current": "location" as const } : {})}>
              {item.content}
            </li>
          ))}
        </ol>
      )}
    </nav>
  );
}

/** A trail place that goes up to the list it names. */
export function TrailLink({ onClick, children }: { onClick: () => void; children: ReactNode }) {
  return (
    <button type="button" className="link-button" onClick={onClick}>
      {children}
    </button>
  );
}
