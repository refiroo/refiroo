/**
 * Server timestamps are stored in UTC. A database that drops the zone designator (SQLite) returns a
 * naive ISO string, which `Date` would otherwise read as local time and shift by the UTC offset.
 */
export function parseServerTime(value: string): Date {
  return new Date(/(Z|[+-]\d{2}:?\d{2})$/i.test(value) || !value.includes("T") ? value : `${value}Z`);
}

export function formatServerTime(value: string): string {
  const date = parseServerTime(value);
  return Number.isNaN(date.valueOf()) ? value : date.toLocaleString();
}
