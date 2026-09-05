/**
 * Hands the browser a file to save.
 *
 * Model documents leave the engine through the browser rather than a server-side export, which is
 * the model document boundary Base 0.6 principle 5 fixes in place.
 */
export function downloadJson(filename: string, content: string) {
  const blob = new Blob([content], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename.replace(/[^a-z0-9._-]+/gi, "-");
  anchor.click();
  URL.revokeObjectURL(url);
}
