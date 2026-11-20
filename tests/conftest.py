import pytest


@pytest.fixture(autouse=True)
def isolate_git_discovery(tmp_path_factory, monkeypatch):
    """Keep Git from discovering repositories above pytest's temporary tree."""
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path_factory.getbasetemp().resolve()))
    monkeypatch.delenv("GIT_DIR", raising=False)
    monkeypatch.delenv("GIT_WORK_TREE", raising=False)
