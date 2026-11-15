/**
 * Numbers, counts and plurals (SR4, SR-D1): every number a person reads goes through `count`, in the
 * browser's locale as dates do, decimals included; one cached formatter serves the render loops.
 * Home's spelled numbers ("No", "One"…"Ten") are its own and stay in `features/home/homeText.ts`.
 */

let numbers: Intl.NumberFormat | undefined;

/** A number in the browser's locale; a string (a figure already shown, a "more than" text) passes through. */
export function count(value: number | string): string {
  if (typeof value === "string") return value;
  return (numbers ??= new Intl.NumberFormat()).format(value);
}

/** The word for a count: `one` for exactly one, otherwise `many` (`one` + "s" when not given); a string count ("1,000+") is many. */
export function plural(n: number | string, one: string, many = `${one}s`): string {
  return n === 1 ? one : many;
}

/** The count and its word: "1 record", "1,200 records". */
export function counted(n: number | string, one: string, many = `${one}s`): string {
  return `${count(n)} ${plural(n, one, many)}`;
}
