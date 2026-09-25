/** Server timestamps carry an explicit UTC offset; display them in the viewer's local time. */
export function formatServerTime(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? value : date.toLocaleString();
}
