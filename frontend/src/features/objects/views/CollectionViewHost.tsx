/**
 * Dispatches a configured view to its renderer.
 */

import { viewComponentRegistry } from "./registry";
import type { ViewComponentProps } from "./types";

export function CollectionView(props: ViewComponentProps) {
  const Component = viewComponentRegistry[props.view.type];
  return <Component {...props} />;
}
