# Pyragify

Export a local repository as readable Markdown with a JSON manifest that records
where the source came from and what was excluded. Each selected UTF-8 file is
retained once, including imports, decorators, comments, whitespace, and Unicode.

## Agent skills in a consuming project

Pyragify 0.5.0 bundles `pyragify-export` for source handoffs and
`pyragify-graph` for experimental graph exploration. Versions before 0.5.0
do not include these skills. Once 0.5.0 or later is available on your package
index, run this in a consuming project using Python 3.12:

```bash
uv add --dev pyragify
uvx library-skills install --skill pyragify-export --skill pyragify-graph
```

Until then, install the wheel attached to the
[0.5.0 GitHub release](https://github.com/ThomasBury/pyragify/releases/tag/0.5.0)
with `uv add --dev /path/to/pyragify-0.5.0-py3-none-any.whl`, then run the same
Library Skills command.

[Library Skills](https://library-skills.io/reference/) scans the project's
environment; a global or isolated Pyragify CLI installation alone is insufficient.
Skills install into `.agents/skills` by default. Add `--claude` to also install
into `.claude/skills`, or `--copy` where symlinks are unavailable. Symlinked skills
follow the installed package version; refresh copied skills after upgrades.
Use `uvx library-skills scan --json` to inspect discovery. See the
[installation guide](docs/getting-started/installation.md#agent-skills) for the
source-checkout route available before publication.

## Use from a source checkout

```bash
uv sync --locked --group dev --group docs
uv run pyragify process-repo --repo-path ./my-project --output-dir ./output --no-enable-graph
```

The CLI reads `config.yaml` in the current directory when present; supplied
options override it. Open `output/index.md` to follow links to complete source
files and inspect omissions. `output/metadata.json` contains source hashes,
line ranges, and exact byte ranges within the Markdown parts. Unchanged files
reuse the versioned cache; deleted files disappear on the next successful run.

`max_words` is a positive, hard limit on every generated Markdown file, including
formatting and the index. Words are whitespace-separated units, not model tokens.
Files stay whole: an oversized file or index fails the export before publication.
Raise the limit or deliberately exclude that source file. Read the
[output contract](docs/user-guide/output-formats.md) and
[safety and selection rules](docs/getting-started/configuration.md) before sharing.

## Why retain a custom exporter?

[The measured Repomix comparison](docs/user-guide/repomix-comparison.md) found that
Repomix handles ordinary readable packaging well, including Unicode and size
failures. Pyragify retains a narrow exporter for exact source bytes and the
hash, part mapping, and omission manifest required by this project. There is no
Repomix wrapper or runtime dependency.

## Experimental graphs

Graph output is opt-in and outside the trusted source handoff. Its relationships
can be incomplete or wrong; structural validation does not establish accuracy.

```bash
uv run pyragify process-repo --repo-path ./my-project --output-dir ./output --enable-graph
uv run pyragify query-graph --graph-path output/graphs/repository_graph.json --command stats
```

Source retention does not depend on a parser. No NotebookLM ingestion result,
LLM answer-quality improvement, or large-repository performance is claimed.

## Development and documentation

```bash
uv run --locked pytest
uv run --locked python scripts/check_skill_packaging.py
uv run --locked --group docs mkdocs build
```

See the [quick start](docs/getting-started/quick-start.md),
[CLI reference](docs/user-guide/cli-reference.md),
[contribution guide](docs/contributing.md), and [implementation plan](PLAN.md).
Python 3.12 is required (>=3.12,<3.13). Licensed under the [Unlicense](LICENSE).
