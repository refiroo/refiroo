import { Icon, type IconName } from "@/ui/Icon";

/**
 * A segmented choice among a few options, as the settings pages and dialogs draw it: as wide as its
 * words, any number of options, each optionally with a glyph (0.9 K6a, D166).
 */
export function Choice<T extends string>({
  name,
  value,
  options,
  onChange,
  describedBy,
  iconSize = 14,
}: {
  name: string;
  value: T;
  options: readonly (readonly [T, string] | readonly [T, string, IconName])[];
  onChange: (value: T) => void;
  /** The id of the help text that describes the whole choice, linked from each radio button. */
  describedBy?: string;
  iconSize?: number;
}) {
  return (
    <div className="theme-choice">
      {options.map(([option, label, icon]) => (
        <label key={option} className={value === option ? "selected" : undefined}>
          <input
            type="radio"
            name={name}
            value={option}
            checked={value === option}
            aria-describedby={describedBy}
            onChange={() => onChange(option)}
          />
          {icon && <Icon name={icon} size={iconSize} />}
          {label}
        </label>
      ))}
    </div>
  );
}
