/**
 * Barrel over the contract modules, so `import type { … } from "@/types"` keeps working and
 * AGENTS.md's "keep model contracts in src/types" convention still holds.
 *
 * Import from a specific module when only one area is needed.
 */

export type * from "@/types/model";
export type * from "@/types/runtime";
export type * from "@/types/modelAdmin";
export type * from "@/types/integration";
export type * from "@/types/ui";
