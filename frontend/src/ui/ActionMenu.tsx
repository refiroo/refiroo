import {
  Button,
  Header,
  Menu,
  MenuItem,
  MenuSection,
  MenuTrigger,
  Popover,
  Tooltip,
  TooltipTrigger,
  type Selection,
} from "react-aria-components";
import { Icon, type IconName } from "@/ui/Icon";

export type ActionMenuItem = {
  id: string;
  label: string;
  tone?: "default" | "danger";
  disabled?: boolean;
  onAction: () => void;
};

/** A group of radio items: exactly one is selected, and choosing another reports its id. */
export type ActionMenuChoice = {
  id: string;
  label: string;
  selected: string;
  options: readonly { id: string; label: string }[];
  onSelect: (id: string) => void;
};

export function ActionMenu({
  label = "More actions",
  icon = "more",
  tooltip,
  items = [],
  choices = [],
  isOpen,
  onOpenChange,
}: {
  label?: string;
  icon?: IconName;
  /** A visible hint for an icon-only trigger, shown on hover and keyboard focus. */
  tooltip?: string;
  items?: readonly ActionMenuItem[];
  choices?: readonly ActionMenuChoice[];
  isOpen?: boolean;
  onOpenChange?: (open: boolean) => void;
}) {
  const trigger = (
    <Button className="icon-button menu-trigger" aria-label={label}>
      <Icon name={icon} />
    </Button>
  );
  return (
    <MenuTrigger isOpen={isOpen} onOpenChange={onOpenChange}>
      {tooltip ? (
        <TooltipTrigger delay={400}>
          {trigger}
          <Tooltip className="tooltip" placement="top">
            {tooltip}
          </Tooltip>
        </TooltipTrigger>
      ) : (
        trigger
      )}
      <Popover className="action-menu-popover" placement="bottom end">
        <Menu className="action-menu" aria-label={label}>
          {choices.map((choice) => (
            <MenuSection
              key={choice.id}
              id={choice.id}
              className="action-menu-section"
              selectionMode="single"
              disallowEmptySelection
              selectedKeys={[choice.selected]}
              onSelectionChange={(keys: Selection) => {
                const [key] = keys === "all" ? [] : [...keys];
                if (key !== undefined && String(key) !== choice.selected) choice.onSelect(String(key));
              }}
            >
              <Header className="action-menu-header">{choice.label}</Header>
              {choice.options.map((option) => (
                <MenuItem key={option.id} id={option.id} className="action-menu-item" textValue={option.label}>
                  {({ isSelected }) => (
                    <>
                      {option.label}
                      {isSelected && <Icon name="check" size={14} />}
                    </>
                  )}
                </MenuItem>
              ))}
            </MenuSection>
          ))}
          {items.map((item) => (
            <MenuItem
              key={item.id}
              id={item.id}
              className={`action-menu-item${item.tone === "danger" ? " danger-item" : ""}`}
              isDisabled={item.disabled}
              onAction={item.onAction}
            >
              {item.label}
            </MenuItem>
          ))}
        </Menu>
      </Popover>
    </MenuTrigger>
  );
}
