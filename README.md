![Pyragify — Every file. Clearly organized.](docs/images/pyragify-branding/banner/banner-colored.svg)

Pyragify exports complete selected source files from a local repository as
readable Markdown, with a JSON manifest recording source locations and omissions.
Use the CLI directly or install the bundled skills to work through an agent.

[Documentation](https://thomasbury.github.io/pyragify/) ·
[Installation guide](https://thomasbury.github.io/pyragify/getting-started/installation/) ·
[Quick start](https://thomasbury.github.io/pyragify/getting-started/quick-start/)

- **Use it** when handing selected source to a reviewer or agent who needs
  complete files, their original paths, and a list of omissions.
- **Know the limits.** Review the selected source for secrets before sharing.
  The `max_words` limit counts whitespace-separated words. The export fails if
  a whole file or the index exceeds that limit.
  Use a different tool if you need to enforce a model-token budget.
- **Verify graph results** against the source before relying on them. Graphs are
  optional and experimental.

## Use the CLI

Python **3.12** is required (`>=3.12,<3.13`). Install
[uv](https://docs.astral.sh/uv/getting-started/installation/), then install
Pyragify from PyPI in a virtual environment:

```bash
uv venv --python 3.12 pyragify-env
source pyragify-env/bin/activate  # Linux/macOS
# Windows PowerShell: pyragify-env\Scripts\Activate.ps1
uv pip install "pyragify>=0.5.3"
```

With the environment activated, replace `./my-project` with your source directory
and export it to a dedicated output directory:

```bash
pyragify process-repo --repo-path ./my-project --output-dir ./output --no-enable-graph
```

## Use an agent

Install Pyragify in the **consuming project's Python 3.12 environment** so
[Library Skills](https://library-skills.io/reference/) can discover its bundled
skills. From that project's root, install Pyragify and both skills:

```bash
uv add --dev "pyragify>=0.5.3"
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

Here is Pyragify exported from its own repository: 58 files, 54,535 words.
From a checkout with the dev environment installed, reproduce it with:

```bash
uv run pyragify process-repo --config-file config.yaml
```

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
- &quot;uv.lock&quot;: Skipped by pattern or size
…
```

Follow the `config.yaml` link to its complete source block in
`output/other/chunk_0.md`. These selected fields from `output/metadata.json`
identify the same file:

```json
{
    "path": "config.yaml",
    "hash": "fc16223aefba5147271532375495161b",
    "output": {
        "part": "other/chunk_0.md",
        "start_byte": 4136,
        "end_byte": 4692
    }
}
```

Bytes `[4136:4692]` of the Markdown part are exactly the bytes of `config.yaml`.
Hashes and byte ranges are a snapshot of this export; they change when the
sources change. See [Pyragify on itself](https://thomasbury.github.io/pyragify/getting-started/quick-start/#pyragify-on-itself)
for the full source block, or the
[minimal sandboxed example](https://thomasbury.github.io/pyragify/getting-started/quick-start/#reproduce-the-example).

Each selected UTF-8 file is retained once and whole, including imports,
decorators, comments, whitespace, and Unicode. Rerun the same command after
editing your repository: unchanged files reuse the cache, and deleted files
disappear on the next successful export.

The CLI loads `config.yaml` from the current directory when present. Explicit
CLI options override it.

## Go further

- [Configuration and selection rules](https://thomasbury.github.io/pyragify/getting-started/configuration/)
- [Output contract](https://thomasbury.github.io/pyragify/user-guide/output-formats/)
- [CLI reference](https://thomasbury.github.io/pyragify/user-guide/cli-reference/)
- [Graph guide](https://thomasbury.github.io/pyragify/user-guide/knowledge-graph/)
- [Contributing](https://thomasbury.github.io/pyragify/contributing/)
- [License: Unlicense](https://github.com/ThomasBury/pyragify/blob/main/LICENSE)
