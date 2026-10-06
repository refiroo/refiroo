/**
 * Placeholder lines while content loads (Track U U3). Announced once by its label; the lines are
 * decorative.
 */
export function Skeleton({ label, lines = 3 }: { label: string; lines?: number }) {
  return (
    <div className="skeleton" role="status" aria-label={label} aria-busy="true">
      {Array.from({ length: lines }, (_, index) => (
        <span key={index} className="skeleton-line" aria-hidden="true" />
      ))}
    </div>
  );
}
