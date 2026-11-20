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
  enabled: false
  output_dir: graphs
```

## Supported settings

| Setting | Default | Meaning |
| --- | --- | --- |
| `repo_path` | Required | Source directory |
| `output_dir` | `./output` | Dedicated Markdown and manifest output directory |
| `max_words` | `200000` | Positive hard word limit per Markdown file, including formatting; oversized files or index fail |
| `max_file_size` | `10485760` | Maximum source size in bytes |
| `skip_patterns` | Built-in image patterns and `.git` | Additional patterns, using gitignore syntax |
| `skip_dirs` | `[node_modules, __pycache__]` | Directory names to exclude; an empty list also uses these defaults |
| `verbose` | `false` | Enable debug logging |
| `scan_secrets` | `false` | Check selected source with detect-secrets before publication |
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

Unchanged files reuse versioned cached chunks and graph data after the stored
line ranges are checked against the retained source. Exports are rebuilt
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

For a plain directory, or after a warning when Git discovery fails, Pyragify
walks directories without following symlinks,
honors root and nested `.gitignore` files, and prunes ignored directories before
reading their children. Git global ignores and `.git/info/exclude` are not used
in this fallback. Pruned directories are recorded as directory exclusions rather
than a list of every file beneath them. Git-ignored paths are recorded from Git, using compact directory entries that
cover their descendants. The index and manifest also record generated-output
directories and repository metadata as omissions.
Inspect the selected source before sharing it.

Files containing NUL bytes are skipped as binary. After selection filters,
Pyragify validates the entire file as UTF-8. A decode error is reported with
the source path and aborts publication. Convert legacy text to UTF-8, or add
its path to `skip_patterns` (for example, `["legacy/*.txt"]`) or pass
`--skip-patterns 'legacy/*.txt'` to intentionally exclude it.

## Scan for potential secrets

Install the optional scanner, then enable it with `--scan-secrets` or
`scan_secrets: true` in YAML.

```bash
uv pip install "pyragify[scan] @ https://github.com/ThomasBury/pyragify/releases/download/0.6.0/pyragify-0.6.0-py3-none-any.whl"
pyragify process-repo --repo-path ./my-project --scan-secrets
```

[detect-secrets](https://github.com/Yelp/detect-secrets) checks each line of the
source that would be exported, including reused cache entries, using its
built-in detectors without network verification. The first finding reports its
source path and line number and aborts publication. The secret value is omitted.
The scan uses the retained text directly, honors detect-secrets inline
allowlists, and skips file transformers. Detection can miss secrets and flag
harmless text. Review the handoff before sharing it.

## Publication failures

Replacement text, graph, metadata, hashes, and cache files are prepared before
publication. Serialization or write errors fail the command; ordinary publication
errors restore previous artifact contents. Source read/worker failures are
reported separately from exclusions and abort publication. A missing or invalid
optional cache triggers processing again; malformed graph query inputs fail.

`.pyragify-artifacts.json` records owned Markdown parts (and recognizes owned legacy text parts). Only previously listed
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
relationships. Source retention is separate and complete for every selected UTF-8
file; see the [output contract](../user-guide/output-formats.md). Source-only exports
do not use parsers. Do not edit sources during a run or expect repository-wide
snapshot isolation.
