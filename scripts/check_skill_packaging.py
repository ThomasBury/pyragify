"""Build and exercise bundled skills in temporary Python 3.12 consumer projects.

Run with: uv run --locked python scripts/check_skill_packaging.py
Requires network/cache access for builds, dependencies, and Library Skills 0.0.19.
"""

import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import tarfile
import tempfile
import tomllib
import zipfile


ROOT = Path(__file__).resolve().parents[1]
NAMES = ("pyragify-export", "pyragify-graph")
LIBRARY_SKILLS = ["uvx", "--python", "3.12", "--from", "library-skills==0.0.19", "library-skills"]
SELECT = [arg for name in NAMES for arg in ("--skill", name)]


def run(*args, cwd):
    # Consumer discovery must not inherit the checkout's activated environment.
    env = {key: value for key, value in os.environ.items()
           if key not in {"VIRTUAL_ENV", "PYTHONPATH", "UV_PROJECT", "UV_WORKING_DIRECTORY",
                          "UV_PROJECT_ENVIRONMENT"}}
    result = subprocess.run(args, cwd=cwd, env=env, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(f"{shlex.join(map(str, args))}\n{result.stdout}\n{result.stderr}")
    return result.stdout


def check_archive(path, expected):
    if path.suffix == ".whl":
        with zipfile.ZipFile(path) as archive:
            actual = {name: archive.read(name) for name in archive.namelist()
                      if "/.agents/skills/" in name and not name.endswith("/")}
        prefix = "pyragify/"
    else:
        with tarfile.open(path) as archive:
            actual = {member.name: archive.extractfile(member).read()
                      for member in archive.getmembers()
                      if member.isfile() and "/.agents/skills/" in member.name}
        prefix = f"{path.name.removesuffix('.tar.gz')}/src/pyragify/"
    assert actual == {prefix + name: content for name, content in expected.items()}, path


def exercise_skills(consumer):
    repo = consumer / "my-project"
    repo.mkdir()
    (repo / "app.py").write_bytes(
        'from helper import helper\r\n\r\ndef run():\r\n    # café\r\n    return helper()\r\n'.encode()
    )
    (repo / "helper.py").write_text("def helper():\n    return 1\n", encoding="utf-8")
    results = {}
    for name in NAMES:
        skill = (consumer / ".agents/skills" / name / "SKILL.md").read_text(encoding="utf-8")
        config = re.search(r"```yaml\n(.*?)```", skill, re.DOTALL).group(1)
        (consumer / f"{name}.yaml").write_text(config, encoding="utf-8")
        for block in re.findall(r"```bash\n(.*?)```", skill, re.DOTALL):
            for line in block.splitlines():
                command = shlex.split(line)
                assert command[:3] == ["uv", "run", "pyragify"]
                output = run(*command, cwd=consumer)
                if "query-graph" in command:
                    results[command[command.index("--command") + 1]] = json.loads(output)
        destination = consumer / ("pyragify-output" if name == "pyragify-export"
                                  else "pyragify-graph-output")
        manifest = json.loads((destination / "metadata.json").read_text())
        assert not manifest["failed_files"]
        assert {item["path"] for item in manifest["processed_files"]} == {"app.py", "helper.py"}
        index = (destination / "index.md").read_text()
        for item in manifest["processed_files"]:
            mapping = item["output"]
            part = (destination / mapping["part"]).read_bytes()
            source = part[mapping["start_byte"]:mapping["end_byte"]]
            assert source == (repo / item["path"]).read_bytes()
            assert hashlib.md5(source).hexdigest() == item["hash"]
            assert f'#{mapping["anchor"]})' in index
        if name == "pyragify-export":
            assert not (destination / "graphs").exists()
    assert set(results) == {"stats", "search", "hierarchy", "related", "dependencies"}
    assert any(node["id"] == "app.py::run" for node in results["search"]["results"])
    assert [node["name"] for node in results["hierarchy"]["callees"]] == ["helper"]
    assert results["dependencies"]["dependencies"] == ["helper.py"]
    assert any(item["node"]["id"] == "helper.py::helper" for item in results["related"]["results"])


def check_consumer(consumer, package, version, expected, *, editable=False):
    consumer.mkdir()
    # A workspace boundary keeps unrelated parent projects out of discovery.
    (consumer / "pyproject.toml").write_text(
        '[project]\nname = "skill-consumer"\nversion = "0.0.0"\nrequires-python = ">=3.12,<3.13"\n'
        '\n[tool.uv.workspace]\nmembers = []\n',
        encoding="utf-8",
    )
    run("uv", "add", "--dev", *(["--editable"] if editable else []), str(package), cwd=consumer)
    scan = json.loads(run(*LIBRARY_SKILLS, "scan", "--json", cwd=consumer))
    assert Path(scan["target_environment"]).resolve() == (consumer / ".venv").resolve(), scan
    skills = {item["name"]: item for item in scan["skills"] if item["package"] == "pyragify"}
    assert set(skills) == set(NAMES), scan
    assert all(item["version"] == version for item in skills.values()), scan
    if not editable:
        for item in skills.values():
            assert Path(item["path"]).is_relative_to(consumer / ".venv"), item

    for options in ([], [], ["--claude"]):
        run(*LIBRARY_SKILLS, "install", *SELECT, *options, "--yes", cwd=consumer)
        for target in (".agents", ".claude") if options else (".agents",):
            for name in NAMES:
                link = consumer / target / "skills" / name
                assert link.is_symlink() and not Path(os.readlink(link)).is_absolute(), link
                assert link.resolve() == Path(skills[name]["path"]).resolve(), link
                assert (link / "SKILL.md").read_bytes() == expected[f".agents/skills/{name}/SKILL.md"]

    # Exercise the installed instructions while they still use the package symlinks.
    exercise_skills(consumer)
    run(*LIBRARY_SKILLS, "remove", *NAMES, "--claude", "--yes", cwd=consumer)
    run(*LIBRARY_SKILLS, "install", *SELECT, "--copy", "--claude", "--yes", cwd=consumer)
    for target in (".agents", ".claude"):
        for name in NAMES:
            directory = consumer / target / "skills" / name
            assert directory.is_dir() and not directory.is_symlink(), directory
            assert (directory / "SKILL.md").read_bytes() == expected[f".agents/skills/{name}/SKILL.md"]
    print(f"Verified {consumer.name}: discovery, installs, and runnable skills", flush=True)


def main():
    version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    expected = {f".agents/skills/{name}/SKILL.md":
                (ROOT / "src/pyragify/.agents/skills" / name / "SKILL.md").read_bytes()
                for name in NAMES}
    with tempfile.TemporaryDirectory(prefix="pyragify-skills-") as directory:
        temporary = Path(directory).resolve()
        artifacts = temporary / "dist"
        run("uv", "build", "--out-dir", str(artifacts), cwd=ROOT)
        wheel, = artifacts.glob("*.whl")
        sdist, = artifacts.glob("*.tar.gz")
        check_archive(wheel, expected)
        check_archive(sdist, expected)
        print("Verified wheel and source archive contents", flush=True)
        check_consumer(temporary / "wheel-consumer", wheel, version, expected)
        check_consumer(temporary / "editable-consumer", ROOT, version, expected, editable=True)

        source = temporary / "source"
        with tarfile.open(sdist) as archive:
            archive.extractall(source, filter="data")
        project, = source.iterdir()
        rebuilt = temporary / "rebuilt"
        run("uv", "build", "--wheel", "--out-dir", str(rebuilt), cwd=project)
        rebuilt_wheel, = rebuilt.glob("*.whl")
        check_archive(rebuilt_wheel, expected)
        check_consumer(temporary / "sdist-consumer", rebuilt_wheel, version, expected)
    print(f"All bundled skill packaging checks passed for pyragify {version}.")


if __name__ == "__main__":
    main()
