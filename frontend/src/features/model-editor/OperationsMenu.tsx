/**
 * The menu of an element's operations in the model editor (0.10 A4a, D38): one item per descriptor
 * the element offers, with its glyph, its section and the migration a released element would need.
 */

import type { ModelDraftOutline } from "@/types";
import { ActionMenu } from "@/ui/ActionMenu";
import {
  menuItems,
  type FieldValues,
  type OperationSpec,
  type OperationTarget,
} from "@/features/model-editor/operations";

export type OnOperation = (operation: OperationSpec, target: OperationTarget, preset?: FieldValues) => void;

export function OperationsMenu({
  label,
  target,
  outline,
  onOperation,
  icon,
  tooltip = "Operations",
  isOpen,
  onOpenChange,
}: {
  label: string;
  target: OperationTarget;
  outline: ModelDraftOutline;
  onOperation: OnOperation;
  icon?: "plus" | "more";
  tooltip?: string;
  isOpen?: boolean;
  onOpenChange?: (open: boolean) => void;
}) {
  return (
    <ActionMenu
      label={label}
      icon={icon}
      tooltip={tooltip}
      isOpen={isOpen}
      onOpenChange={onOpenChange}
      // The Add menu holds one kind of action; its sections would repeat one heading.
      items={menuItems(target, outline, (item) => onOperation(item, target), {
        sections: target.on !== "draft" && target.on !== "consumerApis",
      })}
    />
  );
}
