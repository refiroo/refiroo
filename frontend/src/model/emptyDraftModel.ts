import { keyFromLabel } from "@/model/outline";

/** A model with nothing in it yet, in the newest schema language the deployment reads. */
export function emptyDraftModel(name: string, schemaLanguages: string[]): Record<string, unknown> {
  return {
    schemaVersion: schemaLanguages[schemaLanguages.length - 1],
    release: { key: keyFromLabel(name, new Set()), name, version: "1.0.0" },
    product: { name },
    attributeTypes: [],
    objectTypes: [],
    relationTypes: [],
    objectTypeRelations: [],
    applications: [],
  };
}
