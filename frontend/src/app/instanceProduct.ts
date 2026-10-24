import { createContext, useContext, useEffect, useState } from "react";
import { api } from "@/api/client";
import { workspaceModel } from "@/model/workspaceModels";
import type { EngineModel } from "@/types";

/**
 * The instance's name and mark in the top bar (0.11 M6): the default workspace's model's `product`,
 * the same on every page whatever model the shown workspace runs. It stands in for the deployment's
 * own name and logo until it has them.
 */
export const InstanceProductContext = createContext<EngineModel["product"] | undefined>(undefined);

export function useLoadInstanceProduct(defaultWorkspaceKey: string): EngineModel["product"] | undefined {
  const [product, setProduct] = useState<EngineModel["product"]>();
  useEffect(() => {
    let active = true;
    workspaceModel(defaultWorkspaceKey)
      .then((model) => model.product)
      // A person who may not read the default workspace's model still sees the instance's name
      // (0.12 HM1, D338).
      .catch(() => api.system().then((system) => system.product ?? undefined))
      .then((found) => active && found && setProduct({ name: found.name, description: found.description ?? undefined }))
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, [defaultWorkspaceKey]);
  return product;
}

/** The product the top bar names: the instance's, or the shown model's until it has loaded. */
export function useInstanceProduct(fallback: EngineModel["product"]): EngineModel["product"] {
  return useContext(InstanceProductContext) ?? fallback;
}
