/**
 * A preview's outcomes as cards (0.11 V1's migration page, X4's report of what cannot move): each
 * a count, a label and a hint, pressed when its items are the ones listed below; a card with items
 * of a warning or error tone is tinted so.
 */

export interface OutcomeCard {
  key: string;
  count: number;
  label: string;
  hint: string;
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
  selected: string;
  onSelect: (key: string) => void;
}) {
  return (
    <div role="group" aria-label={label} className="migration-outcomes">
      {items.map((item) => (
        <button
          key={item.key}
          type="button"
          aria-pressed={selected === item.key}
          className={`migration-outcome${item.tone ? ` is-${item.tone}` : ""}${item.count ? " has-items" : ""}`}
          onClick={() => onSelect(item.key)}
        >
          <span className="migration-outcome-count">{item.count.toLocaleString("en-GB")}</span>
          <span className="migration-outcome-label">{item.label}</span>
          <small>{item.hint}</small>
        </button>
      ))}
    </div>
  );
}
