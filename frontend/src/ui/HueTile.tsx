/**
 * The coloured tile of a kind of record or an application (ADR-040): the model's icon in the
 * hue's ink on its soft fill. Decorative; the name beside it says what it is. The hue comes from
 * `model/hues`; without one the tile is neutral.
 */

import type { Hue } from "@/model/hues";
import { ModelIcon } from "@/ui/Icon";

export function HueTile({ hue, icon, size = 22 }: { hue?: Hue; icon?: string; size?: 18 | 20 | 22 }) {
  return (
    <span className={`hue-tile hue-tile-${size}`} data-hue={hue}>
      <ModelIcon name={icon} size={size <= 18 ? 11 : 12} />
    </span>
  );
}
