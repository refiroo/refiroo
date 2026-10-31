/**
 * A preview's outcomes as cards (0.11 V1's migration page, X4's report of what cannot move): each
 * a count, a label and a hint, pressed when its items are the ones listed below; a card with items
 * of a warning or error tone is tinted so. Without `onSelect` the cards are plain figures, not
 * buttons (0.16 AP6a's check of a load).
 */

export interface OutcomeCard {
  key: string;
  count: number;
  label: string;
  hint?: string;
  tone?: "warning" | "error";
}

export function OutcomeCards({
  label,
  items,
  selected,
  onSelect,
}: {
  label: string;
  items: readonly OutcomeCard[];
  selected?: string;
  onSelect?: (key: string) => void;
}) {
  return (
    <div role="group" aria-label={label} className="migration-outcomes">
      {items.map((item) => {
        const className = `migration-outcome${item.tone ? ` is-${item.tone}` : ""}${item.count ? " has-items" : ""}`;
        const body = (
          <>
            <span className="migration-outcome-count">{item.count.toLocaleString("en-GB")}</span>
            <span className="migration-outcome-label">{item.label}</span>
            {item.hint && <small>{item.hint}</small>}
          </>
        );
        return onSelect ? (
          <button
            key={item.key}
            type="button"
            aria-pressed={selected === item.key}
            className={className}
            onClick={() => onSelect(item.key)}
          >
            {body}
          </button>
        ) : (
          <div key={item.key} className={className}>
            {body}
          </div>
        );
      })}
    </div>
  );
}
