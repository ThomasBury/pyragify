"""Run M2's local comparison; npm downloads the pinned CLI into a temporary cache.

Usage: python scripts/compare_repomix.py /tmp/pyragify-repomix-check
This is a verification harness, not a supported export command.
"""

import json
import re
import subprocess
import sys
from pathlib import Path


def main():
    output = Path(sys.argv[1]).resolve()
    output.mkdir(parents=True, exist_ok=False)
    repo = Path(__file__).resolve().parents[1]
    small, mixed = output / "small", output / "mixed"
    for root in (small, mixed):
        root.mkdir()
        subprocess.run(["git", "init", "-q", str(root)], check=True)
    (small / "private").mkdir()
    (small / "private/.gitignore").write_text("hidden.txt\n")
    (small / "private/hidden.txt").write_text("IGNORED_SENTINEL\n")
    (output / "outside.txt").write_text("EXTERNAL_SENTINEL\n")
    (small / "external.txt").symlink_to(output / "outside.txt")
    (small / "app.py").write_text(
        'import asyncio\n\nLIMIT = 3\n\ndef decorate(fn):\n    return fn\n\n'
        '@decorate\nasync def main():\n    """café 🐍"""\n    return await asyncio.sleep(0)\n\n'
        'class A:\n    def run(self):\n        return LIMIT\n', encoding="utf-8")
    (small / "README.md").write_text('# Small app\n\nSee `app.py::main`.\n')
    (mixed / "app.js").write_text(
        '// café 🐍\nimport {x} from "./x.js";\nexport async function foo() { return x; }\n', encoding="utf-8")
    (mixed / "x.js").write_text('export const x = "你好";\n', encoding="utf-8")
    (mixed / "README.md").write_text('# Guide\n\n````markdown\n```py\nprint("fenced")\n```\n````\n')
    (mixed / "oversized.txt").write_text('oversized source words café 🐍\n' * 2000, encoding="utf-8")

    cli = ["npm", "--cache", str(output / "npm-cache"), "exec", "--yes",
           "--package=repomix@1.18.1", "--", "repomix"]

    def run(name, root, *options):
        result = subprocess.run(cli + [str(root), "--no-git-sort-by-changes", *options],
                                capture_output=True, text=True)
        (output / f"{name}.log").write_text(result.stdout + result.stderr, encoding="utf-8")
        return result

    results = {}
    for name, root in (("pyragify", repo), ("small", small), ("mixed", mixed)):
        path = output / f"{name}.md"
        result = run(name, root, "--style", "markdown", "--parsable-style",
                     "--output-show-line-numbers", "-o", str(path))
        assert result.returncode == 0, result.stderr
        text = path.read_text(encoding="utf-8")
        entries = list(re.finditer(
            r"^## File: ([^\n]+)\n(?P<fence>`{3,})[^\n]*\n(?P<body>.*?)\n(?P=fence)$",
            text, re.MULTILINE | re.DOTALL))
        assert entries, f"No navigable source entries in {name}"
        for entry in entries:
            retained = "\n".join(re.sub(r"^\s*\d+: ?", "", line)
                                 for line in entry["body"].splitlines())
            expected = (root / entry[1]).read_text(encoding="utf-8").strip()
            assert retained == expected, f"Source difference beyond outer whitespace: {entry[1]}"
        assert len({entry[1] for entry in entries}) == len(entries)
        results[name] = {"files": len(entries), "markdown_bytes": path.stat().st_size,
                         "retained_source_matches_after_strip": True}
    assert "IGNORED_SENTINEL" not in (output / "small.md").read_text()
    assert "EXTERNAL_SENTINEL" not in (output / "small.md").read_text()

    path = output / "small.json"
    result = run("json", small, "--style", "json", "-o", str(path))
    assert result.returncode == 0, result.stderr
    data = json.loads(path.read_text())
    assert set(data) == {"fileSummary", "directoryStructure", "files"}
    original = (small / "app.py").read_text(encoding="utf-8")
    assert data["files"]["app.py"] == original.strip()
    assert data["files"]["app.py"] != original  # Final newline is discarded.
    assert "private/hidden.txt" not in path.read_text()
    result = run("oversized", mixed, "--style", "markdown", "--parsable-style",
                 "--output-show-line-numbers", "--split-output", "5kb",
                 "-o", str(output / "limited.md"))
    assert result.returncode != 0
    assert "A single file cannot be split" in result.stderr + result.stdout
    results.update({"version": "1.18.1", "nested_ignore_and_symlink_excluded": True,
                    "oversized_file_rejected": True, "json_keys": sorted(data),
                    "exact_source_bytes": False, "hash_and_omission_manifest": False})
    (output / "results.json").write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
