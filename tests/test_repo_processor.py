import json
from pathlib import Path

from pyragify.graph import GraphBuilder, KnowledgeGraph
from pyragify.processor import FileProcessor, RepoContentProcessor


def test_chunk_file_can_return_graph(tmp_path):
    sample_file = tmp_path / "sample.py"
    sample_file.write_text("def greet():\n    return 'hi'\n", encoding="utf-8")

    processor = FileProcessor(tmp_path, tmp_path / "output", enable_graph=True)
    chunks, line_count, graph = processor.chunk_file(sample_file, include_graph=True)

    assert line_count == 2
    assert chunks[0]["content"] == sample_file.read_text()
    assert isinstance(graph, KnowledgeGraph)
    assert "file::sample.py" in graph.nodes


def test_process_repo_respects_skip_dirs(tmp_path):
    (tmp_path / "skipme").mkdir()
    (tmp_path / "skipme" / "ignored.py").write_text("def ignored():\n    return 1\n", encoding="utf-8")
    (tmp_path / "kept.py").write_text("def kept():\n    return 2\n", encoding="utf-8")

    output_dir = tmp_path / "output"
    RepoContentProcessor(tmp_path, output_dir, skip_dirs=["skipme"]).process_repo()

    metadata = json.loads((output_dir / "metadata.json").read_text(encoding="utf-8"))
    processed_paths = {entry["path"] for entry in metadata["processed_files"]}
    skipped_paths = {entry["path"] for entry in metadata["skipped_files"]}

    assert "kept.py" in processed_paths
    assert "skipme/ignored.py" not in processed_paths
    assert "skipme" in skipped_paths


def test_process_repo_skips_images_by_default(tmp_path):
    (tmp_path / "diagram.png").write_bytes(b"\x89PNG\r\n\x1a\nbinary")
    (tmp_path / "notes.md").write_text("# Notes\nHello\n", encoding="utf-8")

    output_dir = tmp_path / "output"
    RepoContentProcessor(tmp_path, output_dir).process_repo()

    metadata = json.loads((output_dir / "metadata.json").read_text(encoding="utf-8"))
    processed_paths = {entry["path"] for entry in metadata["processed_files"]}
    skipped = {entry["path"]: entry["reason"] for entry in metadata["skipped_files"]}

    assert "notes.md" in processed_paths
    assert "diagram.png" in skipped


def test_chunk_buffers_stay_in_their_own_subdirs(tmp_path):
    processor = RepoContentProcessor(tmp_path, tmp_path / "output")

    markdown_chunk = {"type": "markdown", "header": "# Heading", "content": "text"}
    python_chunk = {"type": "function", "name": "f", "code": "def f():\n    return 1"}

    markdown_words = len(processor.file_processor.format_chunk(markdown_chunk, "doc.md").split())
    processor.max_words = max(markdown_words, len(processor.file_processor.format_chunk(python_chunk, "code.py").split())) + 1

    processor.save_chunk(markdown_chunk, "markdown", "doc.md")
    processor.save_chunk(python_chunk, "python", "code.py")
    processor.save_content("markdown")
    processor.save_content("python")

    markdown_output = (tmp_path / "output" / "markdown" / "chunk_0.md").read_text(encoding="utf-8")
    python_output = (tmp_path / "output" / "python" / "chunk_0.md").read_text(encoding="utf-8")

    assert "File: doc.md" in markdown_output
    assert "File: code.py" in python_output


def test_incremental_processing_keeps_unchanged_files_in_output(tmp_path):
    (tmp_path / "a.py").write_text("def keep():\n    return 'a'\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("def change():\n    return 'old'\n", encoding="utf-8")

    output_dir = tmp_path / "output"
    RepoContentProcessor(tmp_path, output_dir).process_repo()

    (tmp_path / "b.py").write_text("def change():\n    return 'new'\n", encoding="utf-8")
    RepoContentProcessor(tmp_path, output_dir).process_repo()

    output = (output_dir / "python" / "chunk_0.md").read_text(encoding="utf-8")
    metadata = json.loads((output_dir / "metadata.json").read_text(encoding="utf-8"))
    skipped = {entry["path"]: entry["reason"] for entry in metadata["skipped_files"]}

    assert "File: a.py" in output
    assert "return 'a'" in output
    assert "File: b.py" in output
    assert "return 'new'" in output
    assert "return 'old'" not in output
    assert {entry["path"] for entry in metadata["processed_files"]} == {"a.py", "b.py"}
    assert "a.py" in metadata["reused_files"]
    assert "a.py" not in skipped


def test_deleting_file_cache_forces_reprocessing(tmp_path):
    (tmp_path / "a.py").write_text("def keep():\n    return 'a'\n", encoding="utf-8")

    output_dir = tmp_path / "output"
    RepoContentProcessor(tmp_path, output_dir).process_repo()
    (output_dir / ".pyragify-cache.json").unlink()

    RepoContentProcessor(tmp_path, output_dir).process_repo()

    metadata = json.loads((output_dir / "metadata.json").read_text(encoding="utf-8"))

    assert {entry["path"] for entry in metadata["processed_files"]} == {"a.py"}
    assert "a.py" not in {entry["path"] for entry in metadata["skipped_files"]}


def test_incremental_processing_drops_deleted_files(tmp_path):
    (tmp_path / "a.py").write_text("def removed():\n    return 'a'\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("def kept():\n    return 'b'\n", encoding="utf-8")

    output_dir = tmp_path / "output"
    RepoContentProcessor(tmp_path, output_dir).process_repo()

    (tmp_path / "a.py").unlink()
    RepoContentProcessor(tmp_path, output_dir).process_repo()

    output = (output_dir / "python" / "chunk_0.md").read_text(encoding="utf-8")
    metadata = json.loads((output_dir / "metadata.json").read_text(encoding="utf-8"))
    hashes = json.loads((output_dir / "hashes.json").read_text(encoding="utf-8"))
    cache = json.loads((output_dir / ".pyragify-cache.json").read_text(encoding="utf-8"))

    assert "File: a.py" not in output
    assert "File: b.py" in output
    assert {entry["path"] for entry in metadata["processed_files"]} == {"b.py"}
    assert "a.py" not in hashes
    assert "a.py" not in cache["files"]


def test_process_repo_ignores_output_dir_artifacts(tmp_path):
    output_dir = tmp_path / "output"
    (output_dir / "python").mkdir(parents=True)
    (output_dir / "python" / "chunk_0.md").write_text(
        "---\nFile: output/python/chunk_0.md\n---\n",
        encoding="utf-8",
    )
    (tmp_path / "app.py").write_text("def app():\n    return 1\n", encoding="utf-8")

    RepoContentProcessor(tmp_path, output_dir).process_repo()

    metadata = json.loads((output_dir / "metadata.json").read_text(encoding="utf-8"))
    output = (output_dir / "python" / "chunk_0.md").read_text(encoding="utf-8")

    assert {entry["path"] for entry in metadata["processed_files"]} == {"app.py"}
    assert all(not entry["path"].startswith("output/") for entry in metadata["processed_files"])
    assert "File: app.py" in output
    assert "output/python/chunk_0.md" not in output


def test_incremental_graph_rebuild_keeps_cached_unchanged_file_nodes(tmp_path):
    (tmp_path / "a.py").write_text("def stable():\n    return 'a'\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("def changed():\n    return 'old'\n", encoding="utf-8")

    output_dir = tmp_path / "output"
    RepoContentProcessor(tmp_path, output_dir, enable_graph=True).process_repo()

    (tmp_path / "b.py").write_text("def changed():\n    return 'new'\n", encoding="utf-8")
    RepoContentProcessor(tmp_path, output_dir, enable_graph=True).process_repo()

    graph = json.loads((output_dir / "graphs" / "repository_graph.json").read_text(encoding="utf-8"))

    assert "file::a.py" in graph["nodes"]
    assert "file::b.py" in graph["nodes"]
    assert any(node["file"] == "a.py" and node["name"] == "stable" for node in graph["nodes"].values())
    assert any(node["file"] == "b.py" and node["name"] == "changed" for node in graph["nodes"].values())


def test_graph_output_keeps_dependency_edges_and_metadata(tmp_path):
    package_dir = tmp_path / "pkg"
    package_dir.mkdir()
    (package_dir / "a.py").write_text(
        "import os\n\n\ndef greet():\n    print('hi')\n",
        encoding="utf-8",
    )

    output_dir = tmp_path / "output"
    RepoContentProcessor(tmp_path, output_dir, enable_graph=True).process_repo()

    graph = json.loads((output_dir / "graphs" / "repository_graph.json").read_text(encoding="utf-8"))
    metadata = json.loads((output_dir / "metadata.json").read_text(encoding="utf-8"))

    assert any(edge["type"] == "imports" for edge in graph["edges"])
    assert any(edge["type"] == "calls" for edge in graph["edges"])
    assert graph["metadata"]["total_edges"] == len(graph["edges"])
    assert "graph" in metadata
    assert metadata["graph"]["output_path"].endswith("repository_graph.json")
    assert all(edge["source"] in graph["nodes"] for edge in graph["edges"])
    assert all(edge["target"] in graph["nodes"] for edge in graph["edges"])


def test_markdown_graph_nodes_have_names(tmp_path):
    (tmp_path / "README.md").write_text(
        "# Guide\n"
        "Intro text.\n"
        "```bash\n"
        "# not a header\n"
        "echo hi\n"
        "```\n"
        "## Usage\n"
        "Run it.\n",
        encoding="utf-8",
    )

    output_dir = tmp_path / "output"
    RepoContentProcessor(tmp_path, output_dir, enable_graph=True).process_repo()

    builder = GraphBuilder(tmp_path)
    builder.load_graph(output_dir / "graphs" / "repository_graph.json")
    validation = builder.validate_graph()

    assert not any("has empty name" in warning for warning in validation["warnings"])


def test_generic_file_nodes_are_not_isolated(tmp_path):
    (tmp_path / "config.yaml").write_text("repo_path: .\n", encoding="utf-8")

    output_dir = tmp_path / "output"
    RepoContentProcessor(tmp_path, output_dir, enable_graph=True).process_repo()

    builder = GraphBuilder(tmp_path)
    builder.load_graph(output_dir / "graphs" / "repository_graph.json")
    validation = builder.validate_graph()

    assert not any("isolated nodes" in warning for warning in validation["warnings"])


def test_cross_file_resolution_ignores_external_placeholders(tmp_path):
    sample_file = tmp_path / "app.py"
    sample_file.write_text("import os\n\n\ndef run():\n    return os.getcwd()\n", encoding="utf-8")

    processor = FileProcessor(tmp_path, tmp_path / "output", enable_graph=True)
    chunks, _, file_graph = processor.chunk_file(sample_file, include_graph=True)

    assert chunks

    builder = GraphBuilder(tmp_path)
    builder.graph.merge(file_graph)
    builder.resolve_cross_file_references([file_graph])
    validation = builder.validate_graph()

    assert validation["errors"] == []
    assert not any(edge.target == "file::<external>" for edge in builder.graph.edges)
