"""The rows written by ``COPY … FROM STDIN`` and the first application that lists a type."""

from contextlib import contextmanager
from types import SimpleNamespace

from app.common.copy_rows import CopyRows
from app.models.schema import EngineModel


class _Copy:
    def __init__(self, written: list) -> None:
        self.written = written

    def write_row(self, row: tuple) -> None:
        self.written.append(row)


class _Cursor:
    def __init__(self, written: list, statements: list) -> None:
        self.written, self.statements = written, statements

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    @contextmanager
    def copy(self, statement: str):
        self.statements.append(statement)
        yield _Copy(self.written)


class _Session:
    def __init__(self) -> None:
        self.written: list = []
        self.statements: list = []
        driver = SimpleNamespace(cursor=lambda: _Cursor(self.written, self.statements))
        self._connection = SimpleNamespace(connection=SimpleNamespace(driver_connection=driver))

    def connection(self):
        return self._connection


def test_rows_are_written_in_one_copy_with_json_text_and_the_check_runs_after():
    session, checks = _Session(), []
    copy = CopyRows(session, "t", ("a", "b"), after_flush=lambda: checks.append(1))
    copy.add(1, {"é": [1]})
    copy.add(2, None)
    assert len(copy) == 2
    copy.flush()
    assert session.statements == ["COPY t (a, b) FROM STDIN"]
    assert session.written == [(1, '{"é":[1]}'), (2, None)]
    assert checks == [1] and len(copy) == 0
    copy.flush()  # nothing to write: no statement, no check
    assert len(session.statements) == 1 and checks == [1]


def test_the_first_application_listing_a_type_answers_and_a_missing_one_gives_the_default():
    applications = (
        SimpleNamespace(key="first", objectTypeKeys=("a", "b")),
        SimpleNamespace(key="second", objectTypeKeys=("b", "c")),
    )
    model = SimpleNamespace(applications=applications)
    assert EngineModel.application_of_type(model, "b") == "first"
    assert EngineModel.application_of_type(model, "c") == "second"
    assert EngineModel.application_of_type(model, "z") == ""
    assert EngineModel.application_of_type(model, "z", "none") == "none"
