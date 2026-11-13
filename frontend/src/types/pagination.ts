/**
 * Navigation every collection page returns (ADR-030). The cursor fields other than `nextCursor`
 * and the counts, present only with `includeTotal=true` and otherwise omitted, are optional here so
 * that feeds reading forward only need not model them.
 */
export interface PageNavigation {
  nextCursor: string | null;
  prevCursor?: string | null;
  anchor?: string | null;
  totalCount?: number;
  startIndex?: number;
}
