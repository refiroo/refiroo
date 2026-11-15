/**
 * Puts `text` on the clipboard. Answers whether it did: no clipboard (an insecure page, an old
 * browser) and a refusal (no permission, no focus) are both "no", and each caller says its own words
 * for either outcome.
 */
export async function copyText(text: string): Promise<boolean> {
  try {
    if (!navigator.clipboard) return false;
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}
