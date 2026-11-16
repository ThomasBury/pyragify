# Pyragify

Pyragify exports complete selected source files from a local repository as
readable Markdown, with a JSON manifest recording source locations and omissions.
Use the CLI directly or install the bundled skills to work through an agent.

[Documentation](https://thomasbury.github.io/pyragify/) ·
[Installation guide](https://thomasbury.github.io/pyragify/getting-started/installation/) ·
[Quick start](https://thomasbury.github.io/pyragify/getting-started/quick-start/)

## Use the CLI

Python **3.12** is required (`>=3.12,<3.13`). Install
[uv](https://docs.astral.sh/uv/getting-started/installation/), then install the
wheel from the [0.5.1 release](https://github.com/ThomasBury/pyragify/releases/tag/0.5.1)
in a virtual environment:

```bash
uv venv --python 3.12 pyragify-env
source pyragify-env/bin/activate  # Linux/macOS
# Windows PowerShell: pyragify-env\Scripts\Activate.ps1
uv pip install https://github.com/ThomasBury/pyragify/releases/download/0.5.1/pyragify-0.5.1-py3-none-any.whl
```

With the environment activated, replace `./my-project` with your source directory
and export it to a dedicated output directory:

```bash
pyragify process-repo --repo-path ./my-project --output-dir ./output --no-enable-graph
```

## Use an agent

Install Pyragify in the **consuming project's Python 3.12 environment** so
[Library Skills](https://library-skills.io/reference/) can discover its bundled
skills. From that project's root, install the wheel and both skills:

```bash
uv add --dev https://github.com/ThomasBury/pyragify/releases/download/0.5.1/pyragify-0.5.1-py3-none-any.whl
uvx library-skills install --skill pyragify-export --skill pyragify-graph
uvx library-skills list --installed
```

This example assumes the project's declared `requires-python` range is
`>=3.12,<3.13` and its environment uses Python 3.12. If prompted for an
installation target, accept Agents (`.agents/skills`). In an agent that loads
that directory, try one of these requests:

| Skill | Purpose | Example request |
| --- | --- | --- |
| `pyragify-export` | Export complete source and review its manifest. | "Use pyragify-export to export this repository to `./output` without a graph and review the omissions." |
| `pyragify-graph` | Explore experimental relationships and check them against source. | "Use pyragify-graph to find candidate callers of `hello_world` and verify them against the source." |

Replace `hello_world` with a function in your repository. See the
[agent installation guide](https://thomasbury.github.io/pyragify/getting-started/installation/#agent-skills)
for broader Python compatibility, installation targets, and upgrades.

## Understand the output

Start at **`output/index.md`**. It links to complete source blocks in
language-grouped Markdown parts and lists omissions. **`output/metadata.json`**
records source paths, hashes, line ranges, and exact byte ranges within the parts.

Each selected UTF-8 file is retained once and whole, including imports,
decorators, comments, whitespace, and Unicode. Rerun the same command after
editing your repository: unchanged files reuse the cache, and deleted files
disappear on the next successful export.

Inspect exports before sharing them; filters do not detect secrets. The
`max_words` limit counts whitespace-separated words, **not model tokens**, and
includes Markdown formatting and the index. An oversized file or index fails
the export instead of being truncated. Increase the limit or narrow the selection.

The CLI loads `config.yaml` from the current directory when present; explicit
CLI options override it. Graphs are **optional and experimental**, separate from
the source handoff. Their relationships can be incomplete or wrong; check them
against the source before drawing conclusions.

## Go further

- [Configuration and selection rules](https://thomasbury.github.io/pyragify/getting-started/configuration/)
- [Output contract](https://thomasbury.github.io/pyragify/user-guide/output-formats/)
- [CLI reference](https://thomasbury.github.io/pyragify/user-guide/cli-reference/)
- [Graph guide](https://thomasbury.github.io/pyragify/user-guide/knowledge-graph/)
- [Contributing](https://thomasbury.github.io/pyragify/contributing/)
- [License: Unlicense](https://github.com/ThomasBury/pyragify/blob/main/LICENSE)
