import { useEffect, useState } from "react";
import { Icon } from "@/ui/Icon";

/** The search box every list uses: the icon, then an input named by `label`. */
export function SearchField({
  value,
  onChange,
  label = "Search",
  placeholder,
  clearOnEscape = false,
  onSubmit,
  className,
}: {
  value: string;
  onChange: (value: string) => void;
  label?: string;
  placeholder: string;
  /** Escape empties a non-empty box instead of reaching the page. */
  clearOnEscape?: boolean;
  /** Enter sends the words (a question to ask, 0.16 AG4); nothing is sent as the person types. */
  onSubmit?: (value: string) => void;
  /** A treatment the surface adds, such as `candidate-search` inside a dialog. */
  className?: string;
}) {
  return (
    <label className={className ? `search-box ${className}` : "search-box"}>
      <Icon name="search" />
      <input
        aria-label={label}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={
          clearOnEscape || onSubmit
            ? (event) => {
                if (clearOnEscape && event.key === "Escape" && value) {
                  event.preventDefault();
                  onChange("");
                } else if (onSubmit && event.key === "Enter" && !event.nativeEvent.isComposing) {
                  event.preventDefault();
                  onSubmit(value);
                }
              }
            : undefined
        }
        placeholder={placeholder}
      />
    </label>
  );
}

/**
 * A search box over a search held elsewhere (the URL): typing is applied, trimmed, 250ms after
 * the last key, and only when it differs from `appliedValue`. The box stays mounted while its own
 * search comes back, so focus and caret stay put; a search changed elsewhere (back, a clear
 * button, an answer in words) replaces the text.
 */
export function DebouncedSearchField({
  appliedValue,
  onApply,
  label,
  placeholder,
}: {
  appliedValue: string;
  onApply: (value: string) => void;
  label?: string;
  placeholder: string;
}) {
  const [value, setValue] = useState(appliedValue);
  const [seen, setSeen] = useState(appliedValue);
  // The search this box last applied, until it comes back as `appliedValue`.
  const [sent, setSent] = useState<string>();
  if (appliedValue !== seen) {
    setSeen(appliedValue);
    if (appliedValue === sent) setSent(undefined);
    else setValue(appliedValue);
  }
  useEffect(() => {
    const timer = window.setTimeout(() => {
      const search = value.trim();
      if (search === appliedValue) return;
      setSent(search);
      onApply(search);
    }, 250);
    return () => window.clearTimeout(timer);
  }, [appliedValue, onApply, value]);
  return <SearchField value={value} onChange={setValue} label={label} placeholder={placeholder} />;
}
