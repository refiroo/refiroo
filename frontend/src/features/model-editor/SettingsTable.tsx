/**
 * The settings of an element the side panel shows as a two-column table (0.13 ED): what the setting
 * is called, and its value. A value is changed in place when one control does it (`CellEdit`), or in
 * the operation's dialog when several fields belong together (a list of attributes, a period). A
 * setting its operation does not offer for this element is shown as it reads, without a pencil.
 */

import type { ReactNode } from "react";
import type { ModelDraftOutline } from "@/types";
import { EditInPlaceValue } from "@/ui/EditInPlace";
import type { CellEdit } from "@/features/model-editor/EditableCell";
import { EditorTable } from "@/features/model-editor/EditorTable";
import type { RunStep } from "@/features/model-editor/OperationDialog";
import type { OnOperation } from "@/features/model-editor/OperationsMenu";
import { operationById, operationsFor, type OperationTarget } from "@/features/model-editor/operations";

export type Setting = {
  key: string;
  label: string;
  /** What the setting means, in a sentence. */
  hint?: string;
  /** The value as it reads. */
  value: ReactNode;
  /** Changed in place by one control. */
  edit?: CellEdit;
  /** Changed in this operation's dialog. */
  operation?: { id: string; target: OperationTarget };
};

export function SettingsTable({
  scope,
  label,
  settings,
  outline,
  run,
  onOperation,
}: {
  scope: string;
  label: string;
  settings: Setting[];
  outline: ModelDraftOutline;
  run: RunStep;
  onOperation: OnOperation;
}) {
  return (
    <EditorTable
      editing={{ outline, run }}
      scope={scope}
      label={label}
      noun={["setting", "settings"]}
      rows={settings}
      rowKey={(setting) => setting.key}
      emptyMessage="Nothing to set here yet."
      columns={[
        {
          key: "setting",
          label: "Setting",
          cell: (setting) => (
            <>
              {setting.label}
              {setting.hint && <span className="muted"> · {setting.hint}</span>}
            </>
          ),
        },
        {
          key: "value",
          label: "Value",
          cell: (setting) => {
            const item = setting.operation && operationById(setting.operation.id);
            if (!setting.operation || !item || !operationsFor(setting.operation.target, outline).includes(item))
              return setting.value;
            const target = setting.operation.target;
            return (
              <EditInPlaceValue layout="row" name={setting.label} onEdit={() => onOperation(item, target)}>
                <span className="attribute-value">{setting.value}</span>
              </EditInPlaceValue>
            );
          },
          edit: (setting) => setting.edit,
        },
      ]}
    />
  );
}
