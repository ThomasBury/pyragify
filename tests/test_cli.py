import json

from typer.testing import CliRunner

from pyragify.cli import app


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
