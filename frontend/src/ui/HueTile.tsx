/**
 * The coloured tile of a kind of record or an application (ADR-040): the model's icon in the
 * hue's ink on its soft fill. Decorative; the name beside it says what it is. The hue comes from
 * `model/hues`; without one the tile is neutral.
 */

import type { Hue } from "@/model/hues";
import { Icon, ModelIcon, type IconName } from "@/ui/Icon";

export function HueTile({
  hue,
  icon,
  glyph,
  size = 22,
}: {
  hue?: Hue;
  icon?: string;
  /** The interface's own glyph in place of a model icon (a relation matrix's entry). */
  glyph?: IconName;
  size?: 18 | 20 | 22 | 40;
}) {
  const glyphSize = size === 40 ? 20 : size <= 18 ? 11 : 12;
  return (
    <span className={`hue-tile hue-tile-${size}`} data-hue={hue}>
      {glyph ? <Icon name={glyph} size={glyphSize} /> : <ModelIcon name={icon} size={glyphSize} />}
    </span>
  );
}
