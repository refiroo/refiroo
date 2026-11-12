/**
 * A duration given in milliseconds, said in seconds and minutes (0.17 ST1, PP-D64): "0.4 s", "50 s", "1 min 27 s",
 * "2 h 5 min". Under ten seconds it keeps a tenth.
 */
export function formatDuration(ms: number): string {
  if (!Number.isFinite(ms) || ms < 0) return "—";
  if (ms < 10_000) return `${(Math.round(ms / 100) / 10).toLocaleString("en")} s`;
  const seconds = Math.round(ms / 1000);
  if (seconds < 60) return `${seconds} s`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return seconds % 60 ? `${minutes} min ${seconds % 60} s` : `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  return minutes % 60 ? `${hours} h ${minutes % 60} min` : `${hours} h`;
}
