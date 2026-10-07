import type { ReactNode } from "react";
import { Card } from "@/ui/Card";
import { Icon, type IconName } from "@/ui/Icon";

/**
 * A settings catalogue beside its selected entry (U-D10 as revised): Workspaces, Model and Webhooks.
 * Each entry has its own address; below 760px the catalogue and the selection take turns, and the
 * selection carries a way back to the catalogue.
 */
export function CatalogueLayout({
  catalogue,
  hasSelection,
  backLabel,
  onBack,
  children,
}: {
  /** The catalogue: a `nav` of `CatalogueEntry` sections. */
  catalogue: ReactNode;
  /** Whether the address names an entry, so the narrow layout shows the selection. */
  hasSelection: boolean;
  backLabel: string;
  onBack: () => void;
  /** The selected entry, or what to say without one. */
  children: ReactNode;
}) {
  return (
    <div className={`catalogue-layout${hasSelection ? " has-selection" : ""}`}>
      {catalogue}
      <div className="catalogue-selection">
        {hasSelection && (
          <button type="button" className="secondary catalogue-back" onClick={onBack}>
            <Icon name="arrow-left" /> {backLabel}
          </button>
        )}
        <Card as="section" flush className="model-detail">
          {children}
        </Card>
      </div>
    </div>
  );
}

/** One entry of a catalogue: its icon, title, subtitle and a pill, marked current when selected. */
export function CatalogueEntry({
  icon,
  title,
  subtitle,
  pill,
  current,
  onSelect,
}: {
  icon: IconName;
  title: ReactNode;
  subtitle?: ReactNode;
  pill?: ReactNode;
  current: boolean;
  onSelect: () => void;
}) {
  return (
    <button className={current ? "active" : ""} aria-current={current ? "page" : undefined} onClick={onSelect}>
      <Icon name={icon} />
      <span className="catalogue-text">
        <strong>{title}</strong>
        {subtitle && <small>{subtitle}</small>}
      </span>
      {pill}
    </button>
  );
}
