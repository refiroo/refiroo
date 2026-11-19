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
import { HueTile } from "@/ui/HueTile";
import { Icon, type IconName } from "@/ui/Icon";
import type { PickOption } from "@/ui/MultiSelect";

const tiled = (item: PickOption) => item.hue !== undefined || item.icon !== undefined;

/**
 * A button that opens a searchable menu and reports the item chosen (U5a), for adding one thing
 * from a long list, such as a filter. Disabled while the list is empty.
 *
 * With `selected` (an item's id) it is a single choice instead (OT1, OT-D5): the button shows the
 * chosen item, the list ticks it, and choosing another reports it the same way. An item with a `hue`
 * or an `icon` is drawn with its tile, in the list and on the button.
 */
export function SearchMenu({
  label,
  icon = "plus",
  items,
  onSelect,
  selected,
}: {
  label: string;
  icon?: IconName;
  items: readonly PickOption[];
  onSelect: (id: string) => void;
  selected?: string;
}) {
  const { contains } = useFilter({ sensitivity: "base" });
  const choosing = selected !== undefined;
  const chosen = choosing ? items.find((item) => item.id === selected) : undefined;
  return (
    <MenuTrigger>
      {choosing ? (
        <Button
          className="secondary search-menu-choice"
          isDisabled={items.length === 0}
          aria-label={chosen ? `${label}: ${chosen.label}` : label}
        >
          {chosen && tiled(chosen) && <HueTile hue={chosen.hue} icon={chosen.icon} size={20} />}
          <span>{chosen?.label ?? label}</span>
          <Icon name="chevron-down" size={14} />
        </Button>
      ) : (
        <Button className="secondary chip-add" isDisabled={items.length === 0}>
          <Icon name={icon} size={14} /> {label}
        </Button>
      )}
      <Popover className="popover picker-popover" placement={choosing ? "bottom start" : "bottom end"}>
        <div className={choosing ? "picker picker-choice" : "picker"}>
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
              {...(choosing
                ? // Without disallowEmptySelection the first Escape only tries to clear the choice.
                  { selectionMode: "single" as const, selectedKeys: [selected], disallowEmptySelection: true }
                : {})}
              renderEmptyState={() => <p className="picker-empty">Nothing matches.</p>}
            >
              {(item) => (
                <MenuItem id={item.id} textValue={item.label} className="picker-option">
                  {({ isSelected }) => (
                    <>
                      {tiled(item) && <HueTile hue={item.hue} icon={item.icon} size={20} />}
                      <span className="picker-text">
                        <span>{item.label}</span>
                        {item.description && <small>{item.description}</small>}
                      </span>
                      {choosing && isSelected && (
                        <span className="picker-tick">
                          <Icon name="check" size={14} />
                        </span>
                      )}
                    </>
                  )}
                </MenuItem>
              )}
            </Menu>
          </Autocomplete>
        </div>
      </Popover>
    </MenuTrigger>
  );
}
