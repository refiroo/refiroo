/**
 * The props every detail panel receives.
 *
 * `P` narrows the panel definition to the member of the union that matches the registry key, so a
 * panel component reads its own configuration without a cast.
 */

import type { ApplicationDefinition, EngineModel, ObjectItem, PanelDefinition } from "@/types";

export interface PanelProps<P extends PanelDefinition = PanelDefinition> {
  model: EngineModel;
  application: ApplicationDefinition;
  object: ObjectItem;
  panel: P;
  onOpen: (objectTypeKey: string, objectId: string, applicationKey?: string) => void;
  onChanged: () => void;
  onObjectChanged: (object: ObjectItem) => void;
  onReload: () => Promise<void>;
  readOnly: boolean;
}
