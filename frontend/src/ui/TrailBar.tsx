import type { ReactNode } from "react";

/**
 * The bar over an opened item in Settings: a button back to where the person came from and the
 * trail of where they are, "Workspaces › Production". The last trail item is the current page; the
 * others may be buttons that go back up. Shared by Settings › Workspaces and Settings › Model.
 */
export function TrailBar({ back, trail }: { back: { label: string; onClick: () => void }; trail: ReactNode[] }) {
  return (
    <div className="model-trail-bar">
      <button type="button" className="secondary" onClick={back.onClick}>
        {back.label}
      </button>
      <nav aria-label="Where you are">
        <ol className="model-trail">
          {trail.map((item, index) => (
            <li key={index} aria-current={index === trail.length - 1 ? "page" : undefined}>
              {item}
            </li>
          ))}
        </ol>
      </nav>
    </div>
  );
}

/** A trail item that goes up to the list it names. */
export function TrailLink({ onClick, children }: { onClick: () => void; children: ReactNode }) {
  return (
    <button type="button" className="link-button" onClick={onClick}>
      {children}
    </button>
  );
}
