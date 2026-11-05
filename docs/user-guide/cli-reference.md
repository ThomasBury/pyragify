# CLI Reference

Use `pyragify --help` for root options. Processing and query options belong after
their subcommand. Short aliases such as `-r` and `-c` are not defined.

## Process a repository

```bash
pyragify process-repo --repo-path ./my-project --output-dir ./output --enable-graph
```

| Option | Behavior |
| --- | --- |
| `--config-file PATH` | Read YAML; defaults to `config.yaml` in the current directory |
| `--repo-path PATH` | Override the required source directory |
| `--output-dir PATH` | Override text output; defaults to `./output` |
| `--max-words INTEGER` | Target words per output file; oversized chunks can exceed it |
| `--max-file-size INTEGER` | Maximum source file size in bytes; default 10485760 |
| `--skip-patterns TEXT` | Add a skip pattern; repeat the option for multiple patterns |
| `--skip-dirs TEXT` | Override skipped directory names; repeat for multiple names |
| `--verbose` / `--no-verbose` | Override verbose logging |
| `--enable-graph` / `--no-enable-graph` | Override graph building |
| `--graph-output-dir PATH` | Graph output directory; relative paths are under text output |
| `--graph-format TEXT` | Only `json` is supported |
| `--include-relationships TEXT` | Unsupported; graph-enabled processing rejects filtering |

```bash
pyragify process-repo --config-file my-config.yaml \
  --skip-patterns '*.log' --skip-patterns '*.tmp' \
  --skip-dirs node_modules --skip-dirs __pycache__
```

Configuration values apply first; supplied CLI options override them. If the
config file is missing, provide `--repo-path`. There are no `PYRAGIFY_*`
environment overrides or alternate configuration filename searches.

See [Configuration](../getting-started/configuration.md) for output boundaries,
ignore behavior, cache recovery, and failed-write handling.

## Query a graph

```bash
pyragify query-graph --graph-path output/graphs/repository_graph.json --command stats
```

| Option | Behavior |
| --- | --- |
| `--graph-path PATH` | JSON input; defaults to `output/graphs/repository_graph.json` |
| `--command TEXT` | Required: `stats`, `related`, `hierarchy`, `dependencies`, or `search` |
| `--entity TEXT` | Node ID for related context; function name or qualified ID for hierarchy; file path for dependencies |
| `--depth INTEGER` | Related-context traversal depth; default 2 |
| `--pattern TEXT` | Regular expression for search |
| `--output-format TEXT` | `json` by default; use `text` for readable output |

```bash
pyragify query-graph --command hierarchy --entity A.run
pyragify query-graph --command dependencies --entity src/app.py
pyragify query-graph --command search --pattern '^main$'
```

Related context contains graph nodes and relationships, not source excerpts.
Graph relationships remain experimental. Missing or malformed graph JSON and
missing required query arguments cause a failing exit status.

## Script example

```bash
OUTPUT_DIR=./analysis
pyragify process-repo --repo-path ./my-project --output-dir "$OUTPUT_DIR" --enable-graph
pyragify query-graph --graph-path "$OUTPUT_DIR/graphs/repository_graph.json" \
  --command stats > "$OUTPUT_DIR/graph-stats.json"
pyragify query-graph --graph-path "$OUTPUT_DIR/graphs/repository_graph.json" \
  --command search --pattern '^main$' > "$OUTPUT_DIR/main-functions.json"
```
