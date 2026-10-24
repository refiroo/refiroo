/**
 * The model a person who may browse no workspace sees Settings under (0.12 Z5, D326): no
 * applications and no types, so the top bar offers none and every page that reads the model
 * finds nothing in it. Its product is the instance's, which `GET /system` names for anyone signed in.
 */

import { api } from "@/api/client";
import type { EngineModel } from "@/types";

export function emptyModel(productName = ""): EngineModel {
  return {
    schemaVersion: "",
    release: { key: "", name: "", version: "" },
    product: { name: productName },
    attributeTypes: [],
    objectTypes: [],
    relationTypes: [],
    objectTypeRelations: [],
    applications: [],
    placements: { applications: [] },
  };
}

/** The empty model, named after the instance's product (0.12 HM1, D338), the same as everyone sees. */
export async function loadEmptyModel(): Promise<EngineModel> {
  const system = await api.system().catch(() => undefined);
  return emptyModel(system?.product?.name ?? system?.activeModelRelease.name ?? "");
}
