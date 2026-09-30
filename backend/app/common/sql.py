"""SQL constructs SQLAlchemy does not provide."""

from typing import Any

from sqlalchemy import true
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.selectable import FromClause, Join


class CrossJoin(Join):
    """``left CROSS JOIN right``: SQLite keeps ``left`` as the outer loop, whatever it estimates.

    A recursive walk joins its queue, one row per step, to the table it descends. SQLite 3.53
    plans that step with the table outside and the queue inside, reading every row of the table's
    owner at each step; written as a cross join, each step probes the table's index with the
    queue's row instead (0.9 Q3: 550 ms against 2 ms for 800 records). Other dialects plan it as
    any inner join. The join condition belongs in the statement's ``WHERE``.
    """

    inherit_cache = True

    def __init__(self, left: FromClause, right: FromClause) -> None:
        super().__init__(left, right, onclause=true())


@compiles(CrossJoin)
def _compile_cross_join(element: CrossJoin, compiler: Any, **kw: Any) -> str:
    kw["asfrom"] = True
    return f"{compiler.process(element.left, **kw)} CROSS JOIN {compiler.process(element.right, **kw)}"
