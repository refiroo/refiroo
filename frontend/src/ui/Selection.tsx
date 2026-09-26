import { useState } from "react";
import type { Key } from "react-aria-components";
import {
  Button,
  ComboBox,
  Input,
  Label,
  ListBox,
  ListBoxItem,
  Popover,
  Select,
  SelectValue,
} from "react-aria-components";
import { Icon } from "@/ui/Icon";

export type SelectionOption = {
  id: string;
  label: string;
  description?: string;
  disabled?: boolean;
};

export function SelectField({
  label,
  value,
  options,
  onChange,
  className,
}: {
  label: string;
  value: string;
  options: readonly SelectionOption[];
  onChange: (value: string) => void;
  className?: string;
}) {
  return (
    <Select
      className={`selection-field${className ? ` ${className}` : ""}`}
      selectedKey={value}
      onSelectionChange={(key) => onChange(String(key))}
    >
      <Label>{label}</Label>
      <Button className="selection-trigger">
        <SelectValue />
        <Icon name="chevron-down" />
      </Button>
      <Popover className="selection-popover">
        <ListBox className="selection-list" items={options}>
          {(option) => (
            <ListBoxItem
              className="selection-option"
              id={option.id}
              isDisabled={option.disabled}
              textValue={option.label}
            >
              {({ isSelected }) => (
                <>
                  <span>
                    <strong>{option.label}</strong>
                    {option.description && <small>{option.description}</small>}
                  </span>
                  {isSelected && <Icon name="check" />}
                </>
              )}
            </ListBoxItem>
          )}
        </ListBox>
      </Popover>
    </Select>
  );
}

/** A key no option can use: model and catalogue keys never contain a NUL character. */
const ACTION_KEY = "\u0000action";

export function ComboBoxField({
  label,
  value,
  options,
  onChange,
  description,
  allowsCustomValue = true,
  onSelect,
  action,
}: {
  label: string;
  value: string;
  options: readonly SelectionOption[];
  onChange: (value: string) => void;
  description?: string;
  allowsCustomValue?: boolean;
  onSelect?: (value: string) => void;
  /** A command listed after the options, such as opening the screen that manages them. */
  action?: { label: string; onAction: () => void };
}) {
  const items: readonly (SelectionOption & { action?: true })[] = action
    ? [...options, { id: ACTION_KEY, label: action.label, action: true }]
    : options;
  // Held here so that choosing the action, a command rather than a value, never becomes the
  // selection: the combobox would otherwise show the action's label as the field's value.
  const [selectedKey, setSelectedKey] = useState<Key | null>(null);

  function select(key: Key | null) {
    if (key === ACTION_KEY) {
      action?.onAction();
    } else if (key !== null) {
      setSelectedKey(key);
      onChange(String(key));
      onSelect?.(String(key));
    }
  }

  return (
    <ComboBox
      className="selection-field combo-field"
      inputValue={value}
      onInputChange={onChange}
      selectedKey={selectedKey}
      onSelectionChange={select}
      allowsCustomValue={allowsCustomValue}
      allowsEmptyCollection
      menuTrigger="focus"
    >
      <Label>{label}</Label>
      <div className="combo-control">
        <Input />
        <Button aria-label={`Show ${label.toLowerCase()} options`}>
          <Icon name="chevron-down" />
        </Button>
      </div>
      {description && <small className="field-description">{description}</small>}
      <Popover className="selection-popover">
        <ListBox className="selection-list" items={items}>
          {(option) => (
            <ListBoxItem
              className={`selection-option${option.action ? " selection-action" : ""}`}
              id={option.id}
              textValue={option.label}
            >
              <span>
                <strong>{option.label}</strong>
                {option.description && <small>{option.description}</small>}
              </span>
            </ListBoxItem>
          )}
        </ListBox>
      </Popover>
    </ComboBox>
  );
}
