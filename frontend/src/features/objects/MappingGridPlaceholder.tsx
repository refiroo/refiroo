import type { ViewComponentProps } from "./views/types";

export function MappingGridPlaceholder({ view }: ViewComponentProps) {
  return (
    <div className="empty-state">
      <h2>{view.name}</h2>
      <p>The mapping grid view will be available in a future update.</p>
    </div>
  );
}
