"""``engine/imports/reread.py``: the new preview of a re-read import is the first one's request again.

The journeys walk the reading choices through the API. Here is what a re-read carries over without
the person choosing it: the stored source file the first preview read, which a profile's check
compares the next version with."""

from types import SimpleNamespace

from app.engine.imports import reread
from app.engine.jobs.store import AWAITING


class _Session:
    def refresh(self, *_args, **_kwargs) -> None:
        pass


class _Files:
    def __init__(self, path) -> None:
        self.path = path
        self.removed: list[str] = []

    def source(self, _job_id):
        return self.path

    def remove(self, job_id) -> None:
        self.removed.append(job_id)


def test_a_re_read_carries_the_source_file_of_the_first_preview(tmp_path, monkeypatch):
    path = tmp_path / "file.source"
    path.write_bytes(b"Name\nOne\n")
    job = SimpleNamespace(
        id="job-1",
        kind="import",
        state=AWAITING,
        workspace_key="w",
        change_set_id=None,
        change_set_version=None,
        parameters={
            "file": {"name": "file.csv", "format": "csv"},
            "policy": "independent",
            "onExisting": "reject",
            "otherWorkspaceIds": "refuse",
            "sourceFileId": "source-7",
            "profile": {
                "definition": {
                    "sources": [
                        {
                            "applicationKey": "a",
                            "objectTypeKey": "t",
                            "columns": [{"column": "Name", "field": "name"}],
                        }
                    ]
                }
            },
        },
    )
    sent = []
    monkeypatch.setattr(reread, "load_job", lambda _session, _id: job)
    monkeypatch.setattr(reread, "open_job_context", lambda _s, _j: SimpleNamespace(model=None))
    monkeypatch.setattr(reread, "source_order", lambda _model, _definition: None)
    monkeypatch.setattr(
        reread,
        "submit_import",
        lambda _session, request, upload, **_kw: (sent.append(request) or "new", None),
    )
    files = _Files(path)
    found = reread.reread_import(
        _Session(), "job-1", [], files=files, max_bytes=10_000, retention_days=7
    )
    assert found == "new"
    assert sent[0].sourceFileId == "source-7" and sent[0].stage == "preview"
    assert files.removed == ["job-1"]
