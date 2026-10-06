/**
 * The hue of a kind of record and of an application (ADR-040, U-D13): its position in the model's
 * `objectTypes` or `applications`, over the eight slots of the type palette (`--hue-1` … `--hue-8`
 * in `tokens.css`). Any model is coloured, no renderer knows a key, and a hue stays while the
 * model's order does.
 */

import type { EngineModel } from "@/types";

export const HUE_SLOTS = 8;

/** A palette slot, 1–8; rendered as `data-hue`. */
export type Hue = 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8;

function slot(index: number): Hue | undefined {
  return index < 0 ? undefined : (((index % HUE_SLOTS) + 1) as Hue);
}

export function objectTypeHue(model: EngineModel, objectTypeKey: string): Hue | undefined {
  return slot(model.objectTypes.findIndex((item) => item.key === objectTypeKey));
}

export function applicationHue(model: EngineModel, applicationKey: string): Hue | undefined {
  return slot(model.applications.findIndex((item) => item.key === applicationKey));
}
