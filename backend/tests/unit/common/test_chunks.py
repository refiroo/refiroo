"""Lists of at most ``CHUNK_SIZE`` items."""

from app.common.chunks import CHUNK_SIZE, chunks


def test_chunks_keep_the_order_and_cut_at_the_size():
    assert list(chunks([])) == []
    assert list(chunks(range(CHUNK_SIZE * 2 + 1))) == [
        list(range(CHUNK_SIZE)),
        list(range(CHUNK_SIZE, CHUNK_SIZE * 2)),
        [CHUNK_SIZE * 2],
    ]
    assert list(chunks(iter("abcde"), 2)) == [["a", "b"], ["c", "d"], ["e"]]
