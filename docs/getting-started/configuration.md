# Configuration

Provide a source directory through YAML or `--repo-path`. The CLI reads
`config.yaml` in the current directory by default. Use `--config-file` to choose
another file; no other filenames or environment variables are searched.

```yaml
repo_path: .
output_dir: ./output
max_words: 200000
max_file_size: 10485760
skip_patterns: ["*.log", "*.tmp"]
skip_dirs: [node_modules, __pycache__]
verbose: false
graph:
  enabled: true
  output_dir: graphs
```

## Supported settings

| Setting | Default | Meaning |
| --- | --- | --- |
| `repo_path` | Required | Source directory |
| `output_dir` | `./output` | Dedicated text and metadata output directory |
| `max_words` | `200000` | Target words per file; oversized semantic chunks may exceed it |
| `max_file_size` | `10485760` | Maximum source size in bytes |
| `skip_patterns` | Built-in image patterns and `.git` | Additional patterns, using gitignore syntax |
| `skip_dirs` | `[node_modules, __pycache__]` | Directory names to exclude; an empty list also uses these defaults |
| `verbose` | `false` | Enable debug logging |
| `graph.enabled` | `false` | Build the experimental repository graph |
| `graph.output_dir` | `graphs` | Graph directory; relative paths are under `output_dir` |
| `graph.format` | `json` | Only JSON is supported |

Relationship filtering, compression, and configuration switches for graph
resolution, validation, repair, or traversal depth are not implemented.
Graph-enabled processing rejects unsupported settings instead of ignoring them.
Use `query-graph --depth` to control related-context traversal.

## Command-line overrides

```bash
pyragify process-repo --config-file config.yaml --repo-path ./my-project \
  --output-dir ./export --max-words 100000 --verbose --enable-graph

pyragify process-repo --repo-path ./my-project \
  --skip-patterns '*.log' --skip-patterns '*.tmp' \
  --skip-dirs node_modules --skip-dirs __pycache__
```

Repeat list options rather than joining values with commas. See the
[CLI reference](../user-guide/cli-reference.md) for all options.

## Incremental processing

Unchanged files reuse versioned cached chunks and graph data. Exports are rebuilt
from all current records, including unchanged files. Deleted sources disappear.
To force reprocessing, remove `.pyragify-cache.json` from your configured
`output_dir` and run the same command again. `hashes.json` is an inspection artifact, not the processing cache.

## Safe paths and export failures

Use dedicated output directories. Text output and graph output must not equal or
contain the source repository. Output paths and artifact destinations containing
symlinks are rejected. Relative graph output paths are resolved under
`output_dir`; an absolute graph output path is used directly. Both locations are
excluded from source discovery.

In a Git working tree, discovery uses Git's tracked and untracked file list with
standard ignore rules. Nested `.gitignore` rules, configured skip patterns,
root `.dockerignore`, size limits, and binary filtering also apply. File and
directory symlinks are excluded. Git submodules and nested untracked repositories
are not recursively exported.

Without Git discovery, Pyragify walks directories without following symlinks,
honors root and nested `.gitignore` files, and prunes ignored directories before
reading their children. Git global ignores and `.git/info/exclude` are not used
in this fallback. Pruned directories are recorded as directory exclusions rather
than a list of every file beneath them. Git-ignored files are omitted by Git
before metadata is assembled, so metadata is not a complete exclusion inventory.
These filters are not a secret scanner; inspect exports before sharing them.

Replacement text, graph, metadata, hashes, and cache files are prepared before
publication. Serialization or write errors fail the command; ordinary publication
errors restore previous artifact contents. Source read/worker failures are
reported separately from exclusions and abort publication. A missing or invalid
optional cache triggers processing again; malformed graph query inputs fail.

`.pyragify-artifacts.json` records owned text chunks. Only previously listed
chunks are removed when obsolete. Old exports without this list may leave stale
chunks; inspect those files and remove them manually. Current chunk names and
standard JSON artifact names are reserved for Pyragify in the output directories.
Keep unrelated files elsewhere. Do not run concurrent exports into the same
output directories. Rollback handles raised errors, not process termination or
power loss during publication.

Graph symbols carry enclosing scopes, so `A.run` and `B.run` have separate
identities. Hierarchy queries accept a bare name, a qualified name, or a node ID.
Python dependency queries resolve exact module paths at the repository root or
under `src/`, including relative imports. Custom import roots and dynamic
receivers remain unresolved. Cross-file edges require explicit imports.

The graph remains experimental: these safety guarantees do not establish correct
relationships or complete source extraction. Those are later plan milestones.
