import copy
import json
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor

import pytest
from typer.testing import CliRunner

from pyragify.cli import app
from pyragify.graph import KnowledgeGraph
from pyragify.processor import RepoContentProcessor, save_json


@pytest.fixture(autouse=True)
def local_workers(monkeypatch):
    # Run the real worker in threads so failure injection is shared with it.
    monkeypatch.setattr("pyragify.processor.ProcessPoolExecutor", ThreadPoolExecutor)


def source(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "app.py").write_text("def run():\n    return 'original'\n")
    return repo, tmp_path / "output"


def snapshot(output):
    return {str(p.relative_to(output)): p.read_bytes()
            for p in output.rglob("*") if p.is_file()}


@pytest.mark.parametrize("ancestor", [False, True])
def test_source_cannot_be_output(tmp_path, ancestor):
    repo, _ = source(tmp_path)
    sentinel = repo / "python" / "chunk_7.txt"
    sentinel.parent.mkdir()
    sentinel.write_text("source content")
    with pytest.raises(ValueError, match="source repository"):
        RepoContentProcessor(repo, repo.parent if ancestor else repo)
    assert sentinel.read_text() == "source content"


@pytest.mark.parametrize("kind", ["output", "graph", "ancestor"])
def test_symlinked_output_rejected_before_creation(tmp_path, kind):
    repo, output = source(tmp_path)
    link = tmp_path / "link"
    link.symlink_to(repo, target_is_directory=True)
    with pytest.raises(ValueError, match="Symlink"):
        RepoContentProcessor(repo, link / "new" if kind == "ancestor" else
                             link if kind == "output" else output,
                             enable_graph=kind == "graph",
                             graph_config={"output_dir": str(link)})
    assert not output.exists()
    assert not (repo / "new").exists()


@pytest.mark.parametrize("git_repo", [False, True])
def test_selection_honors_nested_ignores_and_symlink_boundary(tmp_path, git_repo):
    repo, output = source(tmp_path)
    if git_repo:
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
    private = repo / "private"
    private.mkdir()
    (repo / ".gitignore").write_text("*.txt\nblocked/\n")
    (private / ".gitignore").write_text("secret.py\n!keep.txt\n")
    (private / "secret.py").write_text("private data")
    (private / "keep.txt").write_text("included by nested negation")
    (private / "drop.txt").write_text("excluded by root")
    (repo / "blocked").mkdir()
    (repo / "blocked" / "hidden.py").write_text("hidden")
    external = tmp_path / "external.py"
    external.write_text("external secret")
    (repo / "link.py").symlink_to(external)
    (repo / "linked-dir").symlink_to(tmp_path, target_is_directory=True)
    graph_output = repo / "generated-graphs"
    graph_output.mkdir()
    (graph_output / "old.json").write_text("generated output")
    processor = RepoContentProcessor(repo, output, enable_graph=True,
                                     graph_config={"output_dir": str(graph_output)})
    processor.process_repo()
    paths = {item["path"] for item in processor.metadata["processed_files"]}
    assert "app.py" in paths
    assert "private/keep.txt" in paths
    assert not paths.intersection({"link.py", "private/secret.py", "private/drop.txt",
                                   "blocked/hidden.py", "generated-graphs/old.json"})
    assert not any(path.startswith("linked-dir/") for path in paths)
    assert "external secret" not in "".join(p.read_text() for p in output.rglob("*.txt"))


def test_graph_deserialization_does_not_mutate_input():
    data = KnowledgeGraph().to_dict()
    before = copy.deepcopy(data)
    KnowledgeGraph.from_dict(data)
    assert data == before
    json.dumps(data)


def test_graph_second_run_does_not_process_unchanged_files(tmp_path, monkeypatch):
    repo, output = source(tmp_path)
    (repo / "empty.py").write_text("")
    (repo / "imports.py").write_text("import os\n")
    RepoContentProcessor(repo, output, enable_graph=True).process_repo()
    json.loads((output / ".pyragify-cache.json").read_text())

    def fail(*args):
        pytest.fail("Unchanged file was sent to a worker")

    monkeypatch.setattr("pyragify.processor._process_file_worker", fail)
    RepoContentProcessor(repo, output, enable_graph=True).process_repo()
    assert "file::app.py" in json.loads((output / "graphs/repository_graph.json").read_text())["nodes"]


@pytest.mark.parametrize("payload", ["{", "[]", "{}", '{"nodes": [], "edges": {}}'])
def test_malformed_graph_query_fails(tmp_path, payload):
    graph = tmp_path / "graph.json"
    graph.write_text(payload)
    result = CliRunner().invoke(app, ["query-graph", "--graph-path", str(graph), "--command", "stats"])
    assert result.exit_code == 1
    assert "Error:" in result.output


def test_json_serialization_failure_preserves_old_file(tmp_path):
    path = tmp_path / "data.json"
    path.write_text('{"valid": true}')
    with pytest.raises(TypeError):
        save_json({"bad": set()}, path, "test")
    assert path.read_text() == '{"valid": true}'
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize("failure", ["serialize", "publish", "source", "chunk"])
def test_failed_export_preserves_previous_artifacts(tmp_path, monkeypatch, failure):
    repo, output = source(tmp_path)
    RepoContentProcessor(repo, output, enable_graph=True).process_repo()
    before = snapshot(output)
    (repo / "app.py").write_text("def changed():\n    return 'replacement'\n")
    if failure == "serialize":
        original = json.dump

        def dump(data, stream, **kwargs):
            if isinstance(data, dict) and "processed_files" in data:
                raise TypeError("injected serialization error")
            return original(data, stream, **kwargs)

        monkeypatch.setattr("pyragify.processor.json.dump", dump)
    elif failure == "publish":
        original = os.replace

        def replace(src, dst):
            if str(dst) == str(output / "python/chunk_0.txt") and "stage" not in str(src):
                raise OSError("injected publication error")
            return original(src, dst)

        monkeypatch.setattr("pyragify.processor.os.replace", replace)
    elif failure == "source":
        monkeypatch.setattr("pyragify.processor._process_file_worker", lambda task: None)
    else:
        monkeypatch.setattr(RepoContentProcessor, "save_content",
                            lambda *args: (_ for _ in ()).throw(OSError("chunk error")))
    with pytest.raises((OSError, TypeError, RuntimeError)):
        RepoContentProcessor(repo, output, enable_graph=True).process_repo()
    assert snapshot(output) == before


def test_cleanup_deletes_only_owned_chunks(tmp_path):
    repo, output = source(tmp_path)
    (output / "python").mkdir(parents=True)
    unknown = output / "python/chunk_7.txt"
    unknown.write_text("unowned file")
    RepoContentProcessor(repo, output).process_repo()
    (repo / "app.py").unlink()
    RepoContentProcessor(repo, output).process_repo()
    assert not (output / "python/chunk_0.txt").exists()
    assert unknown.read_text() == "unowned file"


def test_required_artifact_directory_causes_cli_failure(tmp_path):
    repo, output = source(tmp_path)
    (output / "metadata.json").mkdir(parents=True)
    result = CliRunner().invoke(app, ["process-repo", "--config-file", str(tmp_path / "missing"),
                                     "--repo-path", str(repo), "--output-dir", str(output)])
    assert result.exit_code == 1
    assert not (output / "python/chunk_0.txt").exists()


def test_symlinked_chunk_cannot_overwrite_external_file(tmp_path):
    repo, output = source(tmp_path)
    (output / "python").mkdir(parents=True)
    external = tmp_path / "external.txt"
    external.write_text("precious")
    (output / "python/chunk_0.txt").symlink_to(external)
    with pytest.raises(ValueError, match="Symlink"):
        RepoContentProcessor(repo, output).process_repo()
    assert external.read_text() == "precious"


@pytest.mark.parametrize("cache_kind", ["json", "graph"])
def test_invalid_optional_cache_reprocesses_source(tmp_path, cache_kind):
    repo, output = source(tmp_path)
    RepoContentProcessor(repo, output, enable_graph=True).process_repo()
    cache = output / ".pyragify-cache.json"
    if cache_kind == "json":
        cache.write_text("{")
    else:
        data = json.loads(cache.read_text())
        data["files"]["app.py"]["graph"] = {}
        cache.write_text(json.dumps(data))
    processor = RepoContentProcessor(repo, output, enable_graph=True)
    processor.process_repo()
    assert not any(item["reason"] == "Unchanged file (hash match)"
                   for item in processor.metadata["skipped_files"])
    assert "file::app.py" in json.loads((output / "graphs/repository_graph.json").read_text())["nodes"]


def test_graph_can_share_text_output_directory(tmp_path):
    repo, output = source(tmp_path)
    RepoContentProcessor(repo, output, enable_graph=True,
                         graph_config={"output_dir": "."}).process_repo()
    assert "file::app.py" in json.loads((output / "repository_graph.json").read_text())["nodes"]
