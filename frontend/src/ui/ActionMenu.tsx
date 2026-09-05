import { Button, Menu, MenuItem, MenuTrigger, Popover } from "react-aria-components";
import { Icon } from "@/ui/Icon";

export type ActionMenuItem = {
  id: string;
  label: string;
  tone?: "default" | "danger";
  onAction: () => void;
};

export function ActionMenu({ label = "More actions", items }: { label?: string; items: readonly ActionMenuItem[] }) {
  return (
    <MenuTrigger>
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
