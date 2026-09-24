import type { LucideIcon } from "lucide-react";
import {
  ArrowLeft,
  ArrowRight,
  ArrowUpDown,
  Box,
  Check,
  ChevronDown,
  ChevronRight,
  CircleDot,
  Database,
  Ellipsis,
  FileText,
  Folder,
  GitCompareArrows,
  Info,
  Languages,
  Layers,
  List,
  ListFilter,
  Menu,
  Network,
  Plug,
  Plus,
  Search,
  Server,
  Settings2,
  SlidersHorizontal,
  Table2,
  Text,
  X,
} from "lucide-react";

const icons = {
  "arrow-left": ArrowLeft,
  "arrow-right": ArrowRight,
  check: Check,
  "chevron-down": ChevronDown,
  "chevron-right": ChevronRight,
  close: X,
  filter: ListFilter,
  info: Info,
  list: List,
  mapping: GitCompareArrows,
  menu: Menu,
  more: Ellipsis,
  plus: Plus,
  search: Search,
  settings: Settings2,
  sort: ArrowUpDown,
  sliders: SlidersHorizontal,
  table: Table2,
} satisfies Record<string, LucideIcon>;

/**
 * Glyphs a model may name in `objectType.icon` or `application.icon`. The model owns the choice;
 * this is only the bounded set the bundle ships. Unknown names fall back to a neutral glyph, so a
 * new model icon degrades to a generic mark rather than failing.
 */
const modelIcons: Record<string, LucideIcon> = {
  "circle-dot": CircleDot,
  database: Database,
  file: FileText,
  folder: Folder,
  languages: Languages,
  layers: Layers,
  list: List,
  network: Network,
  plug: Plug,
  server: Server,
  text: Text,
};

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

/** A decorative glyph for a model-declared icon name. */
export function ModelIcon({ name, size = 16 }: { name?: string; size?: number }) {
  const Glyph = (name && modelIcons[name]) || Box;
  return <Glyph className="icon" size={size} aria-hidden="true" />;
}
