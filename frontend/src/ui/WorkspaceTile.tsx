/**
 * A workspace's coloured tile (Home, Settings › Account): the first letters of its name in the ink of
 * the hue slot its key picks, on the slot's soft fill. Decorative; the name beside it says what it
 * is. The letters and the hue come from `features/home/homeText`.
 */

import { tileLetters, workspaceHue } from "@/model/workspaceTile";

export function WorkspaceTile({
  workspaceKey,
  label,
  size = "large",
}: {
  workspaceKey: string;
  label: string;
  size?: "large" | "small";
}) {
  return (
    <span className={`workspace-tile workspace-tile-${size}`} data-hue={workspaceHue(workspaceKey)} aria-hidden="true">
      {tileLetters(label)}
    </span>
  );
}
