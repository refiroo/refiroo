import {
  Autocomplete,
  Button,
  Input,
  Menu,
  MenuItem,
  MenuTrigger,
  Popover,
  SearchField,
  useFilter,
} from "react-aria-components";
import { Icon, type IconName } from "@/ui/Icon";
import type { PickOption } from "@/ui/MultiSelect";

/**
 * A button that opens a searchable menu and reports the item chosen (U5a), for adding one thing
 * from a long list, such as a filter. Disabled while the list is empty.
 */
export function SearchMenu({
  label,
  icon = "plus",
  items,
  onSelect,
}: {
  label: string;
  icon?: IconName;
  items: readonly PickOption[];
  onSelect: (id: string) => void;
}) {
  const { contains } = useFilter({ sensitivity: "base" });
  return (
    <MenuTrigger>
      <Button className="secondary chip-add" isDisabled={items.length === 0}>
        <Icon name={icon} size={14} /> {label}
      </Button>
      <Popover className="popover picker-popover" placement="bottom end">
        <div className="picker">
          <Autocomplete filter={contains}>
            <SearchField aria-label={`Search: ${label}`} className="picker-search" autoFocus>
              <Icon name="search" size={14} />
              <Input placeholder="Search" />
            </SearchField>
            <Menu
              aria-label={label}
              className="picker-list"
              items={items}
              onAction={(key) => onSelect(String(key))}
              renderEmptyState={() => <p className="picker-empty">Nothing matches.</p>}
            >
              {(item) => (
                <MenuItem id={item.id} textValue={item.label} className="picker-option">
                  <span className="picker-text">
                    <span>{item.label}</span>
                    {item.description && <small>{item.description}</small>}
                  </span>
                </MenuItem>
              )}
            </Menu>
          </Autocomplete>
        </div>
      </Popover>
    </MenuTrigger>
  );
}
