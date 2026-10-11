import {
  Button,
  Header,
  Menu,
  MenuItem,
  MenuSection,
  MenuTrigger,
  Popover,
  Text,
  Tooltip,
  TooltipTrigger,
  type Selection,
} from "react-aria-components";
import { Icon, type IconName } from "@/ui/Icon";

export type ActionMenuItem = {
  id: string;
  label: string;
  /** A glyph before the label, naming the kind of action. */
  icon?: IconName;
  /** A second line under the label: a consequence or condition ("Needs a migration"). */
  description?: string;
  /** The heading of the group the item belongs to; consecutive items with one heading form a section. */
  section?: string;
  tone?: "default" | "danger";
  disabled?: boolean;
  onAction: () => void;
};

/** Consecutive items grouped by their section heading, in order. */
function sectionsOf(items: readonly ActionMenuItem[]) {
  const sections: { heading?: string; items: ActionMenuItem[] }[] = [];
  for (const item of items) {
    const last = sections[sections.length - 1];
    if (last && last.heading === item.section) last.items.push(item);
    else sections.push({ heading: item.section, items: [item] });
  }
  return sections;
}

/** A group of radio items: exactly one is selected, and choosing another reports its id. */
export type ActionMenuChoice = {
  id: string;
  label: string;
  selected: string;
  options: readonly { id: string; label: string }[];
  onSelect: (id: string) => void;
};

function renderItem(item: ActionMenuItem) {
  return (
    <MenuItem
      key={item.id}
      id={item.id}
      className={`action-menu-item${item.tone === "danger" ? " danger-item" : ""}${item.icon || item.description ? " rich-item" : ""}`}
      isDisabled={item.disabled}
      onAction={item.onAction}
      textValue={item.label}
    >
      {item.icon && <Icon name={item.icon} size={15} />}
      <span className="action-menu-text">
        <Text slot="label">{item.label}</Text>
        {item.description && (
          <Text slot="description" className="action-menu-description">
            {item.description}
          </Text>
        )}
      </span>
    </MenuItem>
  );
}

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
          {sectionsOf(items).map((section, index) =>
            section.heading ? (
              <MenuSection key={`${section.heading}-${index}`} className="action-menu-section">
                <Header className="action-menu-header">{section.heading}</Header>
                {section.items.map(renderItem)}
              </MenuSection>
            ) : (
              section.items.map(renderItem)
            ),
          )}
        </Menu>
      </Popover>
    </MenuTrigger>
  );
}
