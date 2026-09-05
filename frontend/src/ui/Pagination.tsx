/**
 * Page-at-a-time controls over a cursor-paged collection.
 *
 * The API is forward-only, so there is no total and no page count; the control shows the current
 * page number and enables Next only while the server reported a further cursor.
 */
export function Pagination({
  page,
  hasNext,
  onPrevious,
  onNext,
}: {
  page: number;
  hasNext: boolean;
  onPrevious: () => void;
  onNext: () => void;
}) {
  return (
    <div className="pagination" aria-label="Pagination">
      <span>Page {page}</span>
      <button className="icon-button" onClick={onPrevious} disabled={page === 1} aria-label="Previous page">
        <Icon name="arrow-left" />
      </button>
      <button className="icon-button" onClick={onNext} disabled={!hasNext} aria-label="Next page">
        <Icon name="arrow-right" />
      </button>
    </div>
  );
}
import { Icon } from "@/ui/Icon";
