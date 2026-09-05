import type { LucideIcon } from "lucide-react";
import { ArrowLeft, ArrowRight, Check, ChevronDown, ChevronRight, Ellipsis, Menu, Plus, Search, X } from "lucide-react";

const icons = {
  "arrow-left": ArrowLeft,
  "arrow-right": ArrowRight,
  check: Check,
  "chevron-down": ChevronDown,
  "chevron-right": ChevronRight,
  close: X,
  menu: Menu,
  more: Ellipsis,
  plus: Plus,
  search: Search,
} satisfies Record<string, LucideIcon>;

export type IconName = keyof typeof icons;

/** The only Lucide boundary exposed to RDM components and feature code. */
export function Icon({ name, label, size = 16 }: { name: IconName; label?: string; size?: number }) {
  const Glyph = icons[name];
  return label ? (
    <Glyph className="icon" size={size} role="img" aria-label={label} />
  ) : (
    <Glyph className="icon" size={size} aria-hidden="true" />
  );
}
