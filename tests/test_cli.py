import json
from pathlib import Path

from typer.testing import CliRunner

from pyragify.cli import app


def _capture_processor(monkeypatch):
    captured = {}

    class DummyProcessor:
        def __init__(self, **kwargs):
            captured["kwargs"] = kwargs

        def process_repo(self):
            captured["processed"] = True

    monkeypatch.setattr("pyragify.cli.RepoContentProcessor", DummyProcessor)
    return captured


def test_process_repo_without_config_uses_processor_defaults(tmp_path, monkeypatch):
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    captured = _capture_processor(monkeypatch)

    result = CliRunner().invoke(
        app,
        [
            "process-repo",
            "--config-file",
            str(tmp_path / "missing.yaml"),
            "--repo-path",
            str(repo_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["processed"] is True
    assert captured["kwargs"] == {
        "repo_path": repo_path,
        "output_dir": Path("./output"),
        "enable_graph": False,
        "graph_config": {},
    }


def test_process_repo_minimal_config_uses_defaults(tmp_path, monkeypatch):
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    config_path = tmp_path / "config.yaml"
    config_path.write_text(f"repo_path: {repo_path.as_posix()}\n", encoding="utf-8")
    captured = _capture_processor(monkeypatch)

    result = CliRunner().invoke(
        app,
        ["process-repo", "--config-file", str(config_path)],
    )

    assert result.exit_code == 0, result.output
    assert captured["processed"] is True
    assert captured["kwargs"] == {
        "repo_path": repo_path,
        "output_dir": Path("./output"),
        "enable_graph": False,
        "graph_config": {},
    }


def test_process_repo_cli_overrides_config_values(tmp_path, monkeypatch):
    config_repo = tmp_path / "config-repo"
    cli_repo = tmp_path / "cli-repo"
    config_repo.mkdir()
    cli_repo.mkdir()
    cli_output = tmp_path / "cli-output"
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        f"""
repo_path: {config_repo.as_posix()}
output_dir: configured-output
max_words: 10
graph:
  enabled: false
  output_dir: configured-graphs
""".lstrip(),
        encoding="utf-8",
    )
    captured = _capture_processor(monkeypatch)

    result = CliRunner().invoke(
        app,
        [
            "process-repo",
            "--config-file",
            str(config_path),
            "--repo-path",
            str(cli_repo),
            "--output-dir",
            str(cli_output),
            "--max-words",
            "123",
            "--enable-graph",
            "--graph-output-dir",
            "cli-graphs",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["processed"] is True
    assert captured["kwargs"] == {
        "repo_path": cli_repo,
        "output_dir": cli_output,
        "enable_graph": True,
        "graph_config": {"enabled": True, "output_dir": "cli-graphs"},
        "max_words": 123,
    }


def test_process_repo_requires_repo_path_without_config(tmp_path, monkeypatch):
    captured = _capture_processor(monkeypatch)

    result = CliRunner().invoke(
        app,
        ["process-repo", "--config-file", str(tmp_path / "missing.yaml")],
    )

    assert result.exit_code == 1
    assert "kwargs" not in captured


def test_query_graph_invalid_command_does_not_echo_exit_code(tmp_path):
    graph_path = tmp_path / "graph.json"
    graph_path.write_text(
        json.dumps({"nodes": {}, "edges": [], "metadata": {"languages": []}}),
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["query-graph", "--graph-path", str(graph_path), "--command", "unknown"],
    )

    assert result.exit_code == 1
    assert "Unknown command 'unknown'" in result.output
    assert "Error: 1" not in result.output
