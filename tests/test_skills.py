import json
import re
import shlex
from importlib.resources import files

import pytest
import yaml
from typer.testing import CliRunner

from pyragify.cli import app
from test_handoff import check_handoff


SKILLS = files("pyragify").joinpath(".agents", "skills")
NAMES = ("pyragify-export", "pyragify-graph")


@pytest.mark.parametrize("name", NAMES)
def test_skill_frontmatter(name):
    """Each shipped skill declares its directory name and a useful description."""
    path = SKILLS.joinpath(name, "SKILL.md")
    content = path.read_text(encoding="utf-8")
    assert content.startswith("---\n")
    frontmatter, body = content.removeprefix("---\n").split("\n---\n", 1)
    metadata = yaml.safe_load(frontmatter)
    assert metadata["name"] == name == path.parent.name
    assert isinstance(metadata["description"], str) and metadata["description"].strip()
    assert body.strip()


@pytest.mark.parametrize("name", NAMES)
def test_skill_commands_export_and_query(tmp_path, monkeypatch, name):
    """Run the documented commands and check bytes, exclusions, and a known call."""
    monkeypatch.chdir(tmp_path)
    repo = tmp_path / "my-project"
    repo.mkdir()
    (repo / "app.py").write_bytes(
        'from helper import helper\r\n\r\ndef run():\r\n    # café\r\n    return helper()\r\n'.encode()
    )
    (repo / "helper.py").write_text("def helper():\n    return 1\n", encoding="utf-8")
    (repo / ".env").write_text("EXCLUDED=private\n", encoding="utf-8")
    skill = SKILLS.joinpath(name, "SKILL.md").read_text(encoding="utf-8")
    match = re.search(r"```yaml\n(.*?)```", skill, re.DOTALL)
    assert match, f"{name}: SKILL.md has no yaml block"
    config = match.group(1)
    (tmp_path / f"{name}.yaml").write_text(config, encoding="utf-8")
    results = {}
    for block in re.findall(r"```bash\n(.*?)```", skill, re.DOTALL):
        for line in block.splitlines():
            command = shlex.split(line)
            assert command[:3] == ["uv", "run", "pyragify"]
            result = CliRunner().invoke(app, command[3:])
            assert result.exit_code == 0, result.output
            if command[3] == "query-graph":
                results[command[command.index("--command") + 1]] = json.loads(result.output)

    output = tmp_path / yaml.safe_load(config)["output_dir"]
    manifest = check_handoff(repo, output)
    assert {item["path"] for item in manifest["processed_files"]} == {"app.py", "helper.py"}
    assert any(item["path"] == ".env" for item in manifest["skipped_files"])
    graph = output / "graphs/repository_graph.json"
    if name == "pyragify-export":
        assert not graph.exists()
        assert not results
    else:
        assert set(results) == {"stats", "search", "hierarchy", "related", "dependencies"}
        assert any(node["id"] == "app.py::run" for node in results["search"]["results"])
        assert [node["name"] for node in results["hierarchy"]["callees"]] == ["helper"]
        assert results["dependencies"]["dependencies"] == ["helper.py"]
        assert any(item["node"]["id"] == "helper.py::helper"
                   for item in results["related"]["results"])
        data = json.loads(graph.read_text())
        assert any(edge["source"] == "app.py::run" and edge["target"] == "helper.py::helper"
                   and edge["type"] == "calls" for edge in data["edges"])
