/**
 * Items newest first by one of their ISO date fields (`installedAt` of a release, `updatedAt` of a draft or a
 * change set). A new array: the caller's list keeps its order. ISO timestamps from the engine share one
 * format, so they compare as text, without a locale.
 */
export function newestFirst<T>(
  items: readonly T[],
  dateKey: { [K in keyof T]: T[K] extends string ? K : never }[keyof T],
): T[] {
  return [...items].sort((a, b) => {
    const left = a[dateKey] as string;
    const right = b[dateKey] as string;
    return left < right ? 1 : left > right ? -1 : 0;
  });
}
