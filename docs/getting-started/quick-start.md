# Quick Start

After [installation](installation.md), choose a source directory and a dedicated
output directory. From a source checkout:

```bash
uv run pyragify process-repo --repo-path ./my-project --output-dir ./output --no-enable-graph
```

The CLI reads `config.yaml` in the current directory by default. Options override
its values. To save a repeatable configuration:

```yaml
repo_path: ./my-project
output_dir: ./output
max_words: 200000
max_file_size: 10485760
skip_patterns: ["*.log"]
skip_dirs: [node_modules, __pycache__]
graph:
  enabled: false
```

```bash
uv run pyragify process-repo --config-file config.yaml
```

Open `output/index.md`. Follow the file links to complete source blocks, use their
paths and source line ranges to locate definitions, and read the omissions list.
`metadata.json` maps the same files to parts, source hashes, and exact output byte
ranges. Included source appears once; imports, decorators, async code, comments,
and Markdown headings are retained.

Every generated Markdown file must fit `max_words`, including its headers and
the index. Files are indivisible. If a source file or the index cannot fit,
processing fails with a message to increase the limit or reduce the selection.
The limit counts whitespace-separated words, not model tokens.

Run the same command after editing your repository. Unchanged files reuse the
cache, and deleted files disappear from the new handoff. A failed export leaves
the previous published handoff intact for ordinary raised errors. Do not edit
sources or run concurrent exports during processing.

Graph building is optional and experimental:

```bash
uv run pyragify process-repo --config-file config.yaml --enable-graph
uv run pyragify query-graph --graph-path output/graphs/repository_graph.json --command stats
```

Graphs are outside the trusted source handoff. Inspect selected files before
sharing; filtering is not secret detection. No particular chat service's
acceptance or answer quality is guaranteed.

See [configuration](configuration.md), the [CLI reference](../user-guide/cli-reference.md),
and the [output contract](../user-guide/output-formats.md) for details.
