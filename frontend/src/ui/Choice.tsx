/** A segmented choice among a few options, as the settings pages and dialogs draw it. */
export function Choice<T extends string>({
  name,
  value,
  options,
  onChange,
}: {
  name: string;
  value: T;
  options: readonly (readonly [T, string])[];
  onChange: (value: T) => void;
}) {
  return (
    <div className="theme-choice">
      {options.map(([option, label]) => (
        <label key={option} className={value === option ? "selected" : undefined}>
          <input type="radio" name={name} checked={value === option} onChange={() => onChange(option)} />
          {label}
        </label>
      ))}
    </div>
  );
}
