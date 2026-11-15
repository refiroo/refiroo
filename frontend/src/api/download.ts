/**
 * A file the engine serves, saved through `fetch` so the request carries the access token (0.12
 * I2, D247): a plain link cannot send the header, and a token in a URL is excluded (C-D1).
 */

import { errorFromResponse } from "@/api/errors";
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
  // The download's own wording for a body that is not the engine's envelope; it reports neither a
  // forbidden answer nor a changed release.
  if (!response.ok)
    throw errorFromResponse(
      response.status,
      await response.text(),
      `The download failed with status ${response.status}. Retry or contact support if the problem continues.`,
      { detail: false },
    );
  saveBlob(filenameOf(response, fallback), await response.blob());
}
