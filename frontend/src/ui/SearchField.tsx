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
}: {
  value: string;
  onChange: (value: string) => void;
  label?: string;
  placeholder: string;
  /** Escape empties a non-empty box instead of reaching the page. */
  clearOnEscape?: boolean;
  /** Enter sends the words (a question to ask, 0.16 AG4); nothing is sent as the person types. */
  onSubmit?: (value: string) => void;
}) {
  return (
    <label className="search-box">
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
 * the last key, and only when it differs from `appliedValue`.
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
  useEffect(() => {
    const timer = window.setTimeout(() => {
      const search = value.trim();
      if (search !== appliedValue) onApply(search);
    }, 250);
    return () => window.clearTimeout(timer);
  }, [appliedValue, onApply, value]);
  return <SearchField value={value} onChange={setValue} label={label} placeholder={placeholder} />;
}
