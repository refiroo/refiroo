/** Words the product says in several places, each written once. */

/** Where a role or a grant applies to the whole instance. */
export const EVERY_WORKSPACE = "Every workspace";

/** The one action that ends every session of a person (their own page and an administrator's). */
export const SIGN_OUT_EVERYWHERE = "Sign out everywhere";

/** An option the model does not offer but its author typed in. */
export const WRITTEN_BY_HAND = "Written by hand";

/** What a change set without a title is called. */
export function changeSetTitle(name: string | null | undefined): string {
  return name || "Untitled change set";
}

/** A name quoted in running text: “name”, or what stands for it when it has none. */
export function quoted(name: string | null | undefined, fallback: string): string {
  return name ? `“${name}”` : fallback;
}
