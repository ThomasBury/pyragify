import hashlib
import json
import subprocess

import pytest
from typer.testing import CliRunner

from pyragify.cli import app
from pyragify.processor import FileProcessor, RepoContentProcessor


def check_handoff(repo, output, max_words=200000):
    manifest = json.loads((output / "metadata.json").read_text())
    index = (output / "index.md").read_text()
    intervals = {}
    assert manifest["format_version"] == 1
    assert not manifest["failed_files"]
    for item in manifest["processed_files"]:
        mapping = item["output"]
        part = (output / mapping["part"]).read_bytes()
        source = part[mapping["start_byte"]:mapping["end_byte"]]
        assert source == (repo / item["path"]).read_bytes()
        assert hashlib.md5(source).hexdigest() == item["hash"]
        assert item["size"] == len(source)
        assert mapping["start_line"] == (1 if source else 0)
        assert mapping["end_line"] == item["lines"]
        assert f'#{mapping["anchor"]})' in index
        assert part.count(f'<a id="{mapping["anchor"]}">'.encode()) == 1
        intervals.setdefault(mapping["part"], []).append((mapping["start_byte"], mapping["end_byte"]))
    for spans in intervals.values():
        assert all(left[1] < right[0] for left, right in zip(spans, spans[1:]))
    for part in output.rglob("*.md"):
        assert len(part.read_text().split()) <= max_words
    return manifest


@pytest.mark.parametrize("enable_graph", [False, True])
def test_complete_source_and_manifest(tmp_path, enable_graph):
    repo = tmp_path / "repo"
    repo.mkdir()
    sources = {
        "app.py": 'import os\nVALUE = "café 🐍"\n@decorate\nasync def run():\n    return VALUE\nclass A:\n    def method(self):\n        return 1\n',
        "only_imports.py": "import os\nVALUE = 1\n",
        "broken.py": "async def broken(:\n  # still retained\n",
        "app.js": '// café 🐍\nimport x from "x";\nconst VALUE = 1;\nfunction run() { return VALUE; }\n',
        "typed.ts": 'const run = (x: number): number => x;\r\nrun(1);\r\n',
        "App.java": 'class App {\r\n  int run() { return 1; }\r\n}\r\n',
        "app.c": '#include <stdio.h>\r\nint run() { return puts("café"); }\r\n',
        "app.cpp": 'class Item {};\r\nint run() { return 1; }\r\n',
        "app.go": 'package main\r\nfunc run() {}\r\n',
        "style.css": 'a { color: red; }\r\n',
        "broken.js": '// café 🐍\r\nfunction broken( {\r\n',
        "page.html": '<h1>Keep me</h1><script>run()</script>\n',
        "README.md": '\n# Heading\n````markdown\n```py\n# Not a heading\n```\n````\n\n',
        "empty.txt": "",
        "crlf.txt": "  leading\r\ntrailing  \r\n",
        "no-newline.txt": "你好 🐍",
        "odd [name] #é.md": "# Odd path\n",
    }
    for name, text in sources.items():
        (repo / name).write_bytes(text.encode())
    output = tmp_path / "output"
    RepoContentProcessor(repo, output, enable_graph=enable_graph).process_repo()
    manifest = check_handoff(repo, output)
    assert {item["path"] for item in manifest["processed_files"]} == set(sources)
    assert bool(manifest["processed_files"][0]["parser_limitations"]) == enable_graph
    if enable_graph:
        broken = next(item for item in manifest["processed_files"] if item["path"] == "broken.py")
        assert any("Python graph extraction failed" in note for note in broken["parser_limitations"])
        broken_js = next(item for item in manifest["processed_files"] if item["path"] == "broken.js")
        assert any("syntax errors" in note for note in broken_js["parser_limitations"])
    markdown = (output / "markdown/chunk_0.md").read_text()
    assert "`````markdown" in markdown  # Source fences cannot close the enclosing block.


@pytest.mark.parametrize('failure', ['loader', 'query', 'graph'])
def test_parser_failure_retains_complete_source(tmp_path, monkeypatch, caplog, failure):
    source = '// café 🐍\r\nclass Item {\r\n  void run() {}\r\n}\r\n'.encode()
    path = tmp_path / 'App.java'
    path.write_bytes(source)

    def fail(*args):
        raise ValueError('injected graph extraction failure')

    target = {'loader': 'pyragify.processor.get_tree_sitter_language_and_parser',
              'query': 'pyragify.processor.Query',
              'graph': 'pyragify.graph.GraphBuilder.build_from_chunks'}[failure]
    monkeypatch.setattr(target, fail)
    processor = FileProcessor(tmp_path, tmp_path / 'output', enable_graph=True)
    chunks, line_count, _ = processor.chunk_file(path, True)
    assert chunks[0]['content'].encode() == source
    assert line_count == 4
    assert any('injected graph extraction failure' in note for note in chunks[0]['parser_limitations'])
    assert 'injected graph extraction failure' in caplog.text


@pytest.mark.parametrize("source, expected_lines", [
    (b"", 0),
    (b"a = 1", 1),
    (b"a = 1\n", 1),
    (b"a = 1\r", 1),
    (b"a = 1\r\n", 1),
    (b"a = 1\rb = 2", 2),
    (b"a = 1\rb = 2\r", 2),
    (b"a = 1\r\nb = 2\rc = 3\nd = 4\r\n", 4),
    ('value = "a\u2028b"'.encode("utf-8"), 1),
])
def test_universal_newline_ranges_preserve_bytes(tmp_path, source, expected_lines):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "app.py").write_bytes(source)
    output = tmp_path / "output"
    RepoContentProcessor(repo, output).process_repo()
    item = check_handoff(repo, output)["processed_files"][0]
    assert item["lines"] == expected_lines
    assert item["output"]["end_line"] == expected_lines
    start = 1 if source else 0
    part = (output / item["output"]["part"]).read_text()
    assert f"Lines: {start}-{expected_lines}\n" in part
    assert f"lines {start}-{expected_lines};" in (output / "index.md").read_text()


def test_previous_cache_with_incorrect_line_range_is_reprocessed(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "app.py").write_bytes(b"a = 1\rb = 2")
    output = tmp_path / "output"
    RepoContentProcessor(repo, output).process_repo()
    path = output / ".pyragify-cache.json"
    cache = json.loads(path.read_text())
    cache["version"] = 4
    cache["files"]["app.py"]["metadata"]["lines"] = 1
    cache["files"]["app.py"]["chunks"][0]["end_line"] = 1
    path.write_text(json.dumps(cache))
    RepoContentProcessor(repo, output).process_repo()
    manifest = check_handoff(repo, output)
    assert manifest["reused_files"] == []
    assert manifest["processed_files"][0]["lines"] == 2


def test_clean_incremental_deleted_and_changed_sources_agree(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    for name in ("a.py", "b.py", "c.py"):
        (repo / name).write_text(f'NAME = "{name}"\n')
    output = tmp_path / "output"
    RepoContentProcessor(repo, output).process_repo()
    before = {p.relative_to(output): p.read_bytes() for p in output.rglob("*.md")}
    with monkeypatch.context() as patch:
        patch.setattr("pyragify.processor._process_file_worker", lambda task: pytest.fail("Cache was not reused"))
        RepoContentProcessor(repo, output).process_repo()
    assert before == {p.relative_to(output): p.read_bytes() for p in output.rglob("*.md")}
    (repo / "a.py").unlink()
    (repo / "b.py").write_text("NEW = 2\n")
    RepoContentProcessor(repo, output).process_repo()
    incremental = check_handoff(repo, output)
    clean = tmp_path / "clean"
    RepoContentProcessor(repo, clean).process_repo()
    fresh = check_handoff(repo, clean)
    assert incremental["processed_files"] == fresh["processed_files"]
    assert {p.relative_to(output): p.read_bytes() for p in output.rglob("*.md")} == {
        p.relative_to(clean): p.read_bytes() for p in clean.rglob("*.md")}


@pytest.mark.parametrize("git", [False, True])
def test_omissions_are_visible_from_bundle(tmp_path, git):
    repo = tmp_path / "repo"
    repo.mkdir()
    if git:
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
    (repo / "private").mkdir()
    (repo / "private/.gitignore").write_text("hidden.txt\n")
    (repo / "private/hidden.txt").write_text("PRIVATE_CONTENT")
    (repo / "kept.py").write_text("VALUE = 1\n")
    (repo / "binary.dat").write_bytes(b"\x00binary")
    (repo / "large.dat").write_text("x" * 101)
    (repo / "external.txt").symlink_to(tmp_path / "outside")
    (tmp_path / "outside").write_text("EXTERNAL_CONTENT")
    output = repo / "export"
    RepoContentProcessor(repo, output, max_file_size=100).process_repo()
    manifest = check_handoff(repo, output)
    omissions = {item["path"] for item in manifest["skipped_files"]}
    assert {"private/hidden.txt", "binary.dat", "large.dat", "external.txt"} <= omissions
    index = (output / "index.md").read_text()
    assert all(path in index for path in omissions)
    assert all("PRIVATE_CONTENT" not in p.read_text() and "EXTERNAL_CONTENT" not in p.read_text()
               for p in output.rglob("*.md"))
    index_before = (output / "index.md").read_bytes()
    RepoContentProcessor(repo, output, max_file_size=100).process_repo()
    assert (output / "index.md").read_bytes() == index_before


def test_corrupt_cached_source_is_reprocessed(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "app.py").write_text("VALUE = 1\n")
    output = tmp_path / "output"
    RepoContentProcessor(repo, output).process_repo()
    path = output / ".pyragify-cache.json"
    cache = json.loads(path.read_text())
    cache["files"]["app.py"]["chunks"][0]["content"] = "CORRUPTED\n"
    path.write_text(json.dumps(cache))
    RepoContentProcessor(repo, output).process_repo()
    manifest = check_handoff(repo, output)
    assert manifest["reused_files"] == []


def test_disabling_graph_removes_cached_parser_limitations(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "app.py").write_text("VALUE = 1\n")
    output = tmp_path / "output"
    RepoContentProcessor(repo, output, enable_graph=True).process_repo()
    RepoContentProcessor(repo, output).process_repo()
    manifest = check_handoff(repo, output)
    assert manifest["reused_files"] == ["app.py"]
    assert manifest["processed_files"][0]["parser_limitations"] == []
    clean = tmp_path / "clean"
    RepoContentProcessor(repo, clean).process_repo()
    assert (output / "index.md").read_bytes() == (clean / "index.md").read_bytes()


@pytest.mark.parametrize("limit", [0, -1])
def test_invalid_word_limit_does_not_create_output(tmp_path, limit):
    with pytest.raises(ValueError, match="positive"):
        RepoContentProcessor(tmp_path, tmp_path / "output", max_words=limit)
    assert not (tmp_path / "output").exists()


def test_oversized_source_fails_cli_and_preserves_prior_export(tmp_path, caplog):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "text.txt").write_text("original\n")
    output = tmp_path / "output"
    RepoContentProcessor(repo, output).process_repo()
    before = {p.relative_to(output): p.read_bytes() for p in output.rglob("*") if p.is_file()}
    (repo / "text.txt").write_text("word " * 100)
    result = CliRunner().invoke(app, ["process-repo", "--config-file", str(tmp_path / "missing"),
                                    "--repo-path", str(repo), "--output-dir", str(output), "--max-words", "20"])
    assert result.exit_code == 1
    assert "including headers" in caplog.text
    assert before == {p.relative_to(output): p.read_bytes() for p in output.rglob("*") if p.is_file()}


def test_part_splitting_counts_headers_and_removes_old_owned_parts(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    for n in range(3):
        (repo / f"{n}.txt").write_text("word " * 200)
    output = tmp_path / "output"
    RepoContentProcessor(repo, output, max_words=300).process_repo()
    check_handoff(repo, output, max_words=300)
    assert len(list(output.glob("other/chunk_*.md"))) == 3
    (repo / "1.txt").unlink()
    (repo / "2.txt").unlink()
    RepoContentProcessor(repo, output, max_words=300).process_repo()
    assert len(list(output.glob("other/chunk_*.md"))) == 1


def test_index_word_limit_is_enforced(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "a").write_text("small")
    with pytest.raises(ValueError, match="index.md exceeds"):
        RepoContentProcessor(repo, tmp_path / "output", max_words=25).process_repo()
    assert not (tmp_path / "output/metadata.json").exists()


def test_owned_legacy_text_parts_are_removed(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "a.py").write_text("VALUE = 1\n")
    output = tmp_path / "output"
    (output / "python").mkdir(parents=True)
    (output / "python/chunk_0.txt").write_text("old owned output")
    (output / ".pyragify-artifacts.json").write_text('{"chunks": ["python/chunk_0.txt"]}')
    RepoContentProcessor(repo, output).process_repo()
    assert not (output / "python/chunk_0.txt").exists()
    check_handoff(repo, output)
