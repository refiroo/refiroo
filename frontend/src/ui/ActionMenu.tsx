import { Button, Menu, MenuItem, MenuTrigger, Popover } from "react-aria-components";
import { Icon } from "@/ui/Icon";

export type ActionMenuItem = {
  id: string;
  label: string;
  tone?: "default" | "danger";
  onAction: () => void;
};

export function ActionMenu({
  label = "More actions",
  items,
  isOpen,
  onOpenChange,
}: {
  label?: string;
  items: readonly ActionMenuItem[];
  isOpen?: boolean;
  onOpenChange?: (open: boolean) => void;
}) {
  return (
    <MenuTrigger isOpen={isOpen} onOpenChange={onOpenChange}>
      <Button className="icon-button menu-trigger" aria-label={label}>
        <Icon name="more" />
      </Button>
      <Popover className="action-menu-popover" placement="bottom end">
        <Menu className="action-menu" aria-label={label}>
          {items.map((item) => (
            <MenuItem
              key={item.id}
              id={item.id}
              className={`action-menu-item${item.tone === "danger" ? " danger-item" : ""}`}
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
