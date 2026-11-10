---
name: pyragify-graph
description: Build and query Pyragify's experimental code graph to find candidate callers, dependencies, and related source, then check the relationships against source.
---

# Explore an experimental code graph

Use a project environment with Python 3.12 and `pyragify` installed. Select the
source root explicitly and use dedicated output paths without symlinks. Output
must not equal or contain the source root; keep unrelated files elsewhere and
avoid concurrent exports. Graph relationships can be incomplete or wrong. Query
results guide source inspection; they do not establish runtime behavior.

The CLI reads `config.yaml` in the working directory unless `--config-file` is
supplied. CLI options override YAML; missing settings use built-in defaults.
Paths are relative to the working directory, except relative graph output paths,
which are under the text output directory. Save this example as
`pyragify-graph.yaml`, adapting source selection and exclusions:

```yaml
repo_path: ./my-project
output_dir: ./pyragify-graph-output
max_words: 200000
max_file_size: 10485760
skip_patterns: ["*.log", ".env", ".env.*"]
skip_dirs: [node_modules, __pycache__, .venv]
graph:
  enabled: true
  output_dir: graphs
  format: json
```

```bash
uv run pyragify process-repo --config-file pyragify-graph.yaml --repo-path ./my-project --output-dir ./pyragify-graph-output --enable-graph --graph-output-dir graphs
uv run pyragify query-graph --graph-path ./pyragify-graph-output/graphs/repository_graph.json --command stats
uv run pyragify query-graph --graph-path ./pyragify-graph-output/graphs/repository_graph.json --command search --pattern 'run|app[.]py'
```

`search` uses a case-insensitive regular expression and returns IDs, types,
names, and file paths. Discover an entity first; do not invent IDs from names.
If the search reports the function ID `app.py::run`, use that exact ID for
hierarchy and related context. Replace it below with your discovered function:

```bash
uv run pyragify query-graph --graph-path ./pyragify-graph-output/graphs/repository_graph.json --command hierarchy --entity 'app.py::run'
uv run pyragify query-graph --graph-path ./pyragify-graph-output/graphs/repository_graph.json --command related --entity 'app.py::run' --depth 2
```

`hierarchy` reports candidate callers, callees, and source locations. Bare names
can combine several definitions; an exact ID avoids that ambiguity. `related`
traverses relationships in both directions up to the specified depth; its score
reflects traversal distance, not confidence or semantic importance.

For `dependencies`, use the repository-relative **file path** from search's
`file` field, without the `file::` ID prefix. For example:

```bash
uv run pyragify query-graph --graph-path ./pyragify-graph-output/graphs/repository_graph.json --command dependencies --entity app.py
```

Only JSON graph serialization is supported; relationship filtering and
compression are unsupported. Dynamic calls, re-export chains, custom Python
import roots, and JavaScript module resolution can remain unresolved. Check
candidate relationships against the actual source, imports, enclosing scopes,
and relevant tests before drawing conclusions. Empty results do not prove an
entity has no callers or dependencies.

Graph JSON is separate from the source handoff. Inspect `index.md` and
`metadata.json` in the text output directory for retained sources, omissions, and
per-file `parser_limitations`. Whole UTF-8 files are preserved even when graph
extraction is limited. Manifest `output.part`/`anchor` locate each block;
`start_byte`/`end_byte` select its exact source bytes as a zero-based, half-open
slice of the Markdown part. File `hash` values are MD5 snapshot identifiers,
not security signatures.

Git/ignore rules, configured exclusions, size limits, binary filtering, and
symlink exclusions affect selection; these filters do not detect secrets.
Review output before sharing it. `max_words` counts whitespace-separated words,
not tokens, including Markdown framing. Files stay whole; an oversized formatted
file or index fails the export. `max_file_size` records oversized inputs as
omissions. Do not edit source during processing; graph extraction may reread it.
