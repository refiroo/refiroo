import { useState } from "react";
import { Button, Tag, TagGroup, TagList } from "react-aria-components";
import type { FieldControlProps } from "@/ui/FormField";
import { Icon } from "@/ui/Icon";

/** The values in typed text: separated by commas, trimmed, empties dropped. */
const split = (text: string) =>
  text
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean);

/**
 * Several short values as chips in one field (U5a), such as a filter's codes: typed, then Enter, a
 * comma or leaving the field makes a chip; Backspace in the empty field removes the last one;
 * pasted text is split at commas. The text input takes the field's label and description.
 */
export function TokenField({
  control,
  label,
  values,
  onChange,
  placeholder,
}: {
  control: FieldControlProps;
  label: string;
  values: readonly string[];
  onChange: (values: string[]) => void;
  placeholder?: string;
}) {
  const [text, setText] = useState("");
  const commit = (typed: string) => {
    const added = split(typed).filter((value) => !values.includes(value));
    if (added.length) onChange([...values, ...added]);
    setText("");
  };
  return (
    <div className="token-field">
      {values.length > 0 && (
        <TagGroup aria-label={`${label}: values`} onRemove={(keys) => onChange(values.filter((v) => !keys.has(v)))}>
          <TagList className="chip-list" items={values.map((value) => ({ id: value }))}>
            {(item) => (
              <Tag id={item.id} textValue={item.id} className="chip">
                <span className="chip-label">{item.id}</span>
                <Button slot="remove" className="chip-remove" aria-label={`Remove ${item.id}`}>
                  <Icon name="close" size={12} />
                </Button>
              </Tag>
            )}
          </TagList>
        </TagGroup>
      )}
      <input
        {...control}
        value={text}
        placeholder={values.length ? undefined : placeholder}
        onChange={(event) => {
          const typed = event.target.value;
          if (typed.includes(",")) commit(typed);
          else setText(typed);
        }}
        onKeyDown={(event) => {
          if (event.key === "Enter") {
            event.preventDefault();
            commit(text);
          } else if (event.key === "Backspace" && !text && values.length) {
            onChange(values.slice(0, -1));
          }
        }}
        onBlur={() => commit(text)}
      />
    </div>
  );
}
