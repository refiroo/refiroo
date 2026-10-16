/** Server timestamps carry an explicit UTC offset; display them in the viewer's local time. */
export function formatServerTime(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? value : date.toLocaleString();
}

/** A server timestamp's day in the viewer's local time, for lists where the time adds nothing. */
export function formatServerDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.valueOf())
    ? value
    : date.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}
