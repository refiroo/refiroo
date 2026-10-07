import {
  Autocomplete,
  Button,
  Dialog,
  DialogTrigger,
  Input,
  ListBox,
  ListBoxItem,
  Popover,
  SearchField,
  Tag,
  TagGroup,
  TagList,
  useFilter,
  type Selection,
} from "react-aria-components";
import { Icon } from "@/ui/Icon";

export interface PickOption {
  id: string;
  label: string;
  /** A second line under the label, such as what an event covers. */
  description?: string;
}

/** Ids in the options' order, from a React Aria selection. */
const ordered = (options: readonly PickOption[], keys: Selection) =>
  keys === "all" ? options.map((option) => option.id) : options.filter((o) => keys.has(o.id)).map((o) => o.id);

/**
 * A choice of several from a long list (U5a): the chosen ones as removable chips, and a button
 * that opens a searchable list to tick them, with Select all and Clear. Keyboard: the chips are a
 * grid (arrows, Delete removes one); the list is filtered as the search is typed.
 */
export function MultiSelect({
  label,
  options,
  selected,
  onChange,
  addLabel,
  emptyLabel,
  describedBy,
}: {
  label: string;
  options: readonly PickOption[];
  selected: readonly string[];
  onChange: (ids: string[]) => void;
  addLabel: string;
  /** Shown in place of chips while nothing is chosen. */
  emptyLabel: string;
  describedBy?: string;
}) {
  const { contains } = useFilter({ sensitivity: "base" });
  const chosen = options.filter((option) => selected.includes(option.id));
  return (
    <div className="multi-select">
      <TagGroup
        aria-label={label}
        aria-describedby={describedBy}
        onRemove={(keys) => onChange(selected.filter((id) => !keys.has(id)))}
      >
        <TagList
          className="chip-list"
          items={chosen}
          renderEmptyState={() => <span className="chip-empty">{emptyLabel}</span>}
        >
          {(option) => (
            <Tag id={option.id} textValue={option.label} className="chip">
              <span className="chip-label">{option.label}</span>
              <Button slot="remove" className="chip-remove" aria-label={`Remove ${option.label}`}>
                <Icon name="close" size={12} />
              </Button>
            </Tag>
          )}
        </TagList>
      </TagGroup>
      <DialogTrigger>
        <Button className="secondary chip-add">
          <Icon name="plus" size={14} /> {addLabel}
        </Button>
        <Popover className="picker-popover" placement="bottom start">
          <Dialog aria-label={label} className="picker">
            {({ close }) => (
              <>
                <Autocomplete filter={contains}>
                  <SearchField aria-label={`Search ${label.toLowerCase()}`} className="picker-search" autoFocus>
                    <Icon name="search" size={14} />
                    <Input placeholder="Search" />
                  </SearchField>
                  <ListBox
                    aria-label={label}
                    className="picker-list"
                    items={options}
                    selectionMode="multiple"
                    selectedKeys={new Set(selected)}
                    onSelectionChange={(keys) => onChange(ordered(options, keys))}
                    renderEmptyState={() => <p className="picker-empty">Nothing matches.</p>}
                  >
                    {(option) => (
                      <ListBoxItem id={option.id} textValue={option.label} className="picker-option">
                        {({ isSelected }) => (
                          <>
                            <span className="picker-check" aria-hidden="true">
                              {isSelected && <Icon name="check" size={13} />}
                            </span>
                            <span className="picker-text">
                              <span>{option.label}</span>
                              {option.description && <small>{option.description}</small>}
                            </span>
                          </>
                        )}
                      </ListBoxItem>
                    )}
                  </ListBox>
                </Autocomplete>
                <footer className="picker-footer">
                  <span>
                    {selected.length} of {options.length} chosen
                  </span>
                  <Button className="ghost" onPress={() => onChange(options.map((option) => option.id))}>
                    Select all
                  </Button>
                  <Button className="ghost" onPress={() => onChange([])}>
                    Clear
                  </Button>
                  <Button className="primary" onPress={close}>
                    Done
                  </Button>
                </footer>
              </>
            )}
          </Dialog>
        </Popover>
      </DialogTrigger>
    </div>
  );
}
