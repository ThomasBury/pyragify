---
name: pyragify-export
description: Export a local repository as complete Markdown source with Pyragify and inspect its provenance manifest before handing it to an agent or reader.
---

# Export source with Pyragify

Use the project's Python 3.12 environment with `pyragify` installed. Choose the
source repository explicitly; it need not be the current project. Use dedicated
output directories: they must not equal or contain the source root, and output
paths must not contain symlinks. Keep unrelated files out of them and do not run
concurrent exports to the same paths.

The CLI loads `config.yaml` from the current working directory by default.
`--config-file` chooses another file; supplied CLI options override YAML values,
then built-in defaults fill missing settings. Paths are relative to the working
directory, except relative `graph.output_dir` paths, which are under `output_dir`.
Inspect the chosen config instead of inheriting unknown selection settings.

For example, save this as `pyragify-export.yaml`, adapting paths and exclusions:

```yaml
repo_path: ./my-project
output_dir: ./pyragify-output
max_words: 200000
max_file_size: 10485760
skip_patterns: ["*.log", ".env", ".env.*"]
skip_dirs: [node_modules, __pycache__, .venv]
graph:
  enabled: false
```

```bash
uv run pyragify process-repo --config-file pyragify-export.yaml --repo-path ./my-project --output-dir ./pyragify-output --no-enable-graph
```

Keep graphs explicitly disabled for a source-only handoff. Each selected UTF-8
file is retained once and whole, preserving source bytes independently of parsers.
`max_words` counts whitespace-separated words, not model tokens, including
Markdown framing. An oversized source block or index fails the export; increase
the limit or deliberately narrow selection. `max_file_size` instead excludes
oversized inputs and records the omission.

Selection applies Git discovery/ignore rules when available, root and nested
`.gitignore`, root `.dockerignore`, built-in and configured skip patterns,
directory exclusions, size limits, and binary filtering. Symlinks, generated
output, and repository metadata are excluded. Submodules and nested untracked
repositories are not recursively exported. The fallback directory walk does not
use global Git ignores or `.git/info/exclude`. Filters do not detect secrets:
inspect the result before sharing it.

Open `pyragify-output/index.md`, follow its source links, and review omissions.
Inspect `metadata.json`: `processed_files` includes fresh and cached files;
`skipped_files` records excluded files or directories and reasons (a directory
entry covers descendants); `failed_files` is empty on successful publication.
For each processed file, `output.part` and `output.anchor` locate the Markdown
block. Slice the part's raw bytes with `[output.start_byte:output.end_byte]`:
these zero-based, half-open UTF-8 offsets select only the original source, without
fences or the extra framing newline. Compare those bytes to the source and its
`hash` (MD5); MD5 identifies a snapshot and is not a security signature.
`output.start_line`/`end_line` are inclusive source lines, or 0–0 for an empty file.

Unchanged files reuse the versioned cache; deleted sources disappear on the next
successful export. Do not change sources during a run: repository-wide snapshot
isolation is unsupported. Ordinary raised publication errors restore previous
artifacts; process termination and power loss are outside that guarantee.
