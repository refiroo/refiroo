import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { useCursorFeed, type CursorPage } from "@/lib/hooks/useCursorFeed";

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => {
    resolve = done;
  });
  return { promise, resolve };
}

function Feed({
  query,
  fetchPage,
}: {
  query: string;
  fetchPage: (query: string, cursor?: string) => Promise<CursorPage<string>>;
}) {
  const feed = useCursorFeed((cursor) => fetchPage(query, cursor), [query]);
  return (
    <div>
      <span>{feed.items.join(",")}</span>
      {feed.hasMore && <button onClick={feed.loadMore}>More</button>}
    </div>
  );
}

describe("useCursorFeed", () => {
  it("ignores a load-more response from the previous dependency set", async () => {
    const oldMore = deferred<CursorPage<string>>();
    const newFirst = deferred<CursorPage<string>>();
    const fetchPage = vi
      .fn<(query: string, cursor?: string) => Promise<CursorPage<string>>>()
      .mockResolvedValueOnce({ items: ["old-first"], nextCursor: "old-next" })
      .mockReturnValueOnce(oldMore.promise)
      .mockReturnValueOnce(newFirst.promise);

    const { rerender } = render(<Feed query="old" fetchPage={fetchPage} />);
    fireEvent.click(await screen.findByRole("button", { name: "More" }));
    rerender(<Feed query="new" fetchPage={fetchPage} />);
    await waitFor(() => expect(fetchPage).toHaveBeenCalledTimes(3));

    await act(async () => newFirst.resolve({ items: ["new-first"], nextCursor: null }));
    expect(await screen.findByText("new-first")).toBeInTheDocument();
    await act(async () => oldMore.resolve({ items: ["stale-more"], nextCursor: null }));
    expect(screen.queryByText(/stale-more/)).not.toBeInTheDocument();
  });
});
