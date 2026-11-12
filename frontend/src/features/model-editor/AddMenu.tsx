/**
 * The "+" Add menu of the model editor and of the draft canvas: the draft's own add operations
 * (application, object type, attribute type, relation type, group) or, on the editor's consumer APIs
 * tab, a consumer API. One component, so the two views offer it with one trigger, label and form.
 */

import type { ModelDraftOutline } from "@/types";
import type { OperationTarget } from "@/features/model-editor/operations";
import { OperationsMenu, type OnOperation } from "@/features/model-editor/OperationsMenu";

export function AddMenu({
  outline,
  onOperation,
  consumerApis = false,
}: {
  outline: ModelDraftOutline;
  onOperation: OnOperation;
  /** The editor's consumer APIs tab adds a consumer API instead. */
  consumerApis?: boolean;
}) {
  const target: OperationTarget = consumerApis ? { on: "consumerApis" } : { on: "draft" };
  return (
    <OperationsMenu
      label={consumerApis ? "Add a consumer API" : "Add to the model"}
      icon="plus"
      tooltip="Add"
      target={target}
      outline={outline}
      onOperation={onOperation}
    />
  );
}
