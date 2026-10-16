import { createContext, useContext, useEffect, useState } from "react";
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
      .then((model) => active && setProduct(model.product))
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
