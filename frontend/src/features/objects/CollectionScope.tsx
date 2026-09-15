import { useEffect, useState } from "react";
import { errorMessage } from "@/api/errors";
import { useDataApi } from "@/features/workspaces/WorkspaceDataContext";
import { objectTypeFor } from "@/model/lookup";
import type { EngineModel } from "@/types";

export function CollectionScope({
  model,
  workspaceKey,
  parentObjectId,
  parentObjectTypeKey,
}: {
  model: EngineModel;
  workspaceKey: string;
  parentObjectId?: string;
  parentObjectTypeKey?: string;
}) {
  if (!parentObjectId || !parentObjectTypeKey) return null;
  return (
    <LoadedCollectionScope
      key={`${workspaceKey}:${parentObjectTypeKey}:${parentObjectId}`}
      model={model}
      workspaceKey={workspaceKey}
      parentObjectId={parentObjectId}
      parentObjectTypeKey={parentObjectTypeKey}
    />
  );
}

function LoadedCollectionScope({
  model,
  workspaceKey,
  parentObjectId,
  parentObjectTypeKey,
}: {
  model: EngineModel;
  workspaceKey: string;
  parentObjectId: string;
  parentObjectTypeKey: string;
}) {
  const api = useDataApi();
  const [name, setName] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    api
      .object(parentObjectTypeKey, parentObjectId, workspaceKey)
      .then((object) => active && setName(object.name))
      .catch((cause) => active && setError(errorMessage(cause)));
    return () => {
      active = false;
    };
  }, [api, parentObjectId, parentObjectTypeKey, workspaceKey]);

  const type = objectTypeFor(model, parentObjectTypeKey)?.name ?? parentObjectTypeKey;
  return (
    <p className="context-line" title={error || undefined}>
      Within {type}: {name || (error ? parentObjectId : "Loading context…")}
    </p>
  );
}
