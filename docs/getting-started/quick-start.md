# Quick Start

After [installation](installation.md), choose a source directory and a dedicated
output directory. From a consuming project or source checkout:

```bash
uv run pyragify process-repo --repo-path ./my-project --output-dir ./output --no-enable-graph
```

For a standalone CLI installation, activate its environment and use `pyragify`
in place of `uv run pyragify` in these examples. To work through an agent, see
[example skill requests](installation.md#use-the-skills).

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

## Reproduce the example

With the standalone CLI environment activated, run these commands in Bash. The
temporary directory keeps the example Git repository outside your checkout.

```bash
example_dir=$(mktemp -d)
cd "$example_dir"
git init -q example
printf 'def hello_world():\n    return "Hello, world!"\n' > example/hello.py
printf 'debug message\n' > example/debug.log
git -C example add -f hello.py debug.log
pyragify process-repo --repo-path ./example --output-dir ./output --no-enable-graph --skip-patterns '*.log'
```

In `output/index.md`, follow the `hello.py` link to this block in
`output/python/chunk_0.md`. The index also lists `debug.log` under **Omissions**.

````markdown
<a id="source-68656c6c6f2e7079"></a>

### File: hello.py

Lines: 1-2

```python
def hello_world():
    return "Hello, world!"

```

````

These selected fields from `output/metadata.json` identify the source and record
the omission:

```json
{
    "processed_files": [
        {
            "path": "hello.py",
            "hash": "44641958f3c8eb28b3323cf7400cd0f6",
            "output": {
                "part": "python/chunk_0.md",
                "start_byte": 80,
                "end_byte": 126
            }
        }
    ],
    "skipped_files": [
        {
            "path": "debug.log",
            "reason": "Skipped by pattern or size"
        }
    ]
}
```

Bytes `[80:126]` of the Markdown part are exactly the bytes in `example/hello.py`.
See the [output contract](../user-guide/output-formats.md#manifest) for field
definitions and a verification example.

## Pyragify on itself

For a realistic handoff, export Pyragify's own repository. From a checkout of
the [Pyragify repository](https://github.com/ThomasBury/pyragify):

```bash
uv sync --locked --group dev
uv run pyragify process-repo --config-file config.yaml
```

The export selects 58 files (54,609 words) into `./output/`. Git ignore rules
omit `.venv/`, `dist/`, `site/`, and caches; `config.yaml` skips `uv.lock`,
`.gitignore`, and images; the generated `output/` directory excludes itself.

Excerpt from `output/index.md` (file list trimmed):

```markdown
## Files

- [&quot;config.yaml&quot;](other/chunk_0.md#source-636f6e6669672e79616d6c) — lines 1-23; MD5 fc16223aefba5147271532375495161b
- [&quot;src/pyragify/cli.py&quot;](python/chunk_0.md#source-7372632f70797261676966792f636c692e7079) — lines 1-336; MD5 bf2855526380de07004c865f724646af
- [&quot;src/pyragify/processor.py&quot;](python/chunk_0.md#source-7372632f70797261676966792f70726f636573736f722e7079) — lines 1-1490; MD5 4649437bc1a141f559a3c3b03d126151
- [&quot;tests/test_processor.py&quot;](python/chunk_0.md#source-74657374732f746573745f70726f636573736f722e7079) — lines 1-310; MD5 df1596575d7df4647a225514daf1621b
…

## Omissions

- &quot;output/&quot;: Generated output directory
- &quot;.git&quot;: Git repository metadata
- &quot;.venv/&quot;: Git ignore rule (directory entries cover descendants)
- &quot;dist/&quot;: Git ignore rule (directory entries cover descendants)
- &quot;chat_code_base.png&quot;: Skipped by pattern or size
- &quot;docs/images/pyragify-branding/icon/icon-colored.svg&quot;: Skipped by pattern or size
- &quot;uv.lock&quot;: Skipped by pattern or size
…
```

Follow the `config.yaml` link to this block in `output/other/chunk_0.md`:

````markdown
<a id="source-636f6e6669672e79616d6c"></a>

### File: config.yaml

Lines: 1-23

```text
repo_path: .
output_dir: ./output
max_words: 200000  # Hard words-per-Markdown-file limit, including headers; oversized files fail
max_file_size: 10485760  # 10 MB
skip_patterns:
  - ".git"
  - "uv.lock"
  - ".gitignore"
  - "*.png"
  - "*.jpg"
  - "*.jpeg"
  - "*.gif"
  - "*.bmp"
  - "*.webp"
  - "*.ico"
  - "*.svg"
skip_dirs: []
verbose: false

# Experimental graph output is separate from the trusted source handoff.
graph:
  enabled: false  # Opt in separately to experimental graph building
  output_dir: "./graphs"  # Directory to save graph files

```

````

These selected fields from `output/metadata.json` identify the source:

```json
{
    "path": "config.yaml",
    "size": 556,
    "lines": 23,
    "words": 86,
    "hash": "fc16223aefba5147271532375495161b",
    "output": {
        "part": "other/chunk_0.md",
        "anchor": "source-636f6e6669672e79616d6c",
        "start_line": 1,
        "end_line": 23,
        "start_byte": 4136,
        "end_byte": 4692
    }
}
```

Bytes `[4136:4692]` of `output/other/chunk_0.md` are exactly the bytes of
`config.yaml`. Hashes and byte ranges are a snapshot of this export; they
change when the sources change.
