import { useEffect, useState, type ReactNode } from "react";
import { errorMessage } from "@/api/errors";
import { useDataApi } from "@/state/WorkspaceDataContext";
import { objectTypeFor } from "@/model/lookup";
import type { CollectionQueryState, EngineModel } from "@/types";

/** The parent a collection is narrowed to, with the way back to all of `pluralName`. */
export function ScopeBanner<Q extends CollectionQueryState>({
  model,
  workspaceKey,
  query,
  onQueryChange,
  pluralName,
}: {
  model: EngineModel;
  workspaceKey: string;
  query: Q;
  onQueryChange: (query: Q) => void;
  pluralName: string;
}) {
  if (!query.parentObjectId) return null;
  return (
    <NarrowedBanner
      clearLabel={`Show all ${pluralName.toLowerCase()}`}
      onClear={() =>
        onQueryChange({ ...query, parentObjectId: undefined, parentObjectTypeKey: undefined, anchor: undefined })
      }
    >
      <CollectionScope
        model={model}
        workspaceKey={workspaceKey}
        parentObjectId={query.parentObjectId}
        parentObjectTypeKey={query.parentObjectTypeKey}
      />
    </NarrowedBanner>
  );
}

/**
 * What a narrowed list is narrowed to, with the way back to all of it: the banner of a collection under a parent
 * (`ScopeBanner`) and of the activity a fact of an account of history counted (0.16 AO2).
 */
export function NarrowedBanner({
  children,
  clearLabel,
  onClear,
}: {
  children: ReactNode;
  clearLabel: string;
  onClear: () => void;
}) {
  return (
    <div className="scope-banner">
      {children}
      <button className="ghost" onClick={onClear}>
        {clearLabel}
      </button>
    </div>
  );
}

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
