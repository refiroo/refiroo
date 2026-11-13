/** How a workspace is drawn as a tile: its two letters and its hue. */

import { HUE_SLOTS, type Hue } from "@/model/hues";

/** The two letters of a workspace's tile: the first letters of its first two words, or its first two. */
export function tileLetters(label: string): string {
  const words = label.trim().split(/\s+/).filter(Boolean);
  const letters = words.length > 1 ? `${words[0][0]}${words[1][0]}` : (words[0] ?? "").slice(0, 2);
  return letters.toUpperCase();
}

/** A workspace's hue: one of the palette's slots, picked from its key, so it never changes. */
export function workspaceHue(key: string): Hue {
  let hash = 0;
  for (const character of key) hash = (hash * 31 + character.charCodeAt(0)) >>> 0;
  return ((hash % HUE_SLOTS) + 1) as Hue;
}
