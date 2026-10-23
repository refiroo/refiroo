/**
 * A file the engine serves, saved through `fetch` so the request carries the access token (0.12
 * I2, D247): a plain link cannot send the header, and a token in a URL is excluded (C-D1).
 */

import { ApiError } from "@/api/errors";
import { authorizedFetch } from "@/api/session";
import { saveBlob } from "@/lib/download";

function filenameOf(response: Response, fallback: string): string {
  const disposition = response.headers.get("content-disposition") ?? "";
  const encoded = /filename\*=UTF-8''([^;]+)/i.exec(disposition);
  if (encoded) return decodeURIComponent(encoded[1]);
  const plain = /filename="?([^";]+)"?/i.exec(disposition);
  return plain ? plain[1] : fallback;
}

/** Download `url` and save it, named as the engine names it or `fallback`. */
export async function downloadFrom(url: string, fallback: string): Promise<void> {
  const response = await authorizedFetch(url);
  if (!response.ok) {
    let message = `The download failed with status ${response.status}. Retry or contact support if the problem continues.`;
    let code = "HTTP_ERROR";
    try {
      const parsed = await response.json();
      message = parsed.error?.message ?? message;
      code = parsed.error?.code ?? code;
    } catch {
      // A body that is not the engine's envelope keeps the general message.
    }
    throw new ApiError(response.status, code, message);
  }
  saveBlob(filenameOf(response, fallback), await response.blob());
}
