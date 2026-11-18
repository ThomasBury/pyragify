# Installation

This guide will help you install Pyragify on your system.

## Prerequisites

- **Python**: Version 3.12 only (`>=3.12,<3.13`)
- **Operating System**: Linux, macOS, or Windows

## Installation Methods

### Method 1: Release wheel with uv (Recommended)

These docs describe Pyragify 0.5.3. Install its
[GitHub release wheel](https://github.com/ThomasBury/pyragify/releases/tag/0.5.3)
to get the features documented here. Package-index publication is separate.

[uv](https://docs.astral.sh/uv/pip/environments/) creates virtual environments
and installs packages. Create and activate a Python 3.12 environment first:

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

uv venv --python 3.12 pyragify-env
source pyragify-env/bin/activate  # Linux/macOS
# Windows PowerShell: pyragify-env\Scripts\Activate.ps1
uv pip install https://github.com/ThomasBury/pyragify/releases/download/0.5.3/pyragify-0.5.3-py3-none-any.whl
pyragify --help
```

Once 0.5.3 or later is available on your package index, you can install from
there in the activated environment:

```bash
uv pip install "pyragify>=0.5.3"
```

The version constraint prevents an older release from silently satisfying the
installation.

### Method 2: Release wheel with pip

With Python 3.12 installed:

```bash
python3.12 -m venv pyragify-env  # Linux/macOS
# Windows: py -3.12 -m venv pyragify-env
source pyragify-env/bin/activate  # Linux/macOS
# Windows PowerShell: pyragify-env\Scripts\Activate.ps1
python -m pip install https://github.com/ThomasBury/pyragify/releases/download/0.5.3/pyragify-0.5.3-py3-none-any.whl
pyragify --help
```

Once available on your index, use `python -m pip install "pyragify>=0.5.3"`
in the activated environment instead.

### Method 3: From Source

If you want to install from source (for development or the latest features):

```bash
# Clone the repository
git clone https://github.com/ThomasBury/pyragify.git
cd pyragify

# Install with uv (recommended)
uv sync --locked --group dev --group docs

# Or with pip, in an activated Python 3.12 environment
python -m pip install -e .
```

## Agent skills

Pyragify 0.5.3 bundles two self-contained skills:
`pyragify-export` covers source-only exports and manifest inspection;
`pyragify-graph` covers experimental graph export and queries with source checks.
Versions before 0.5.0 do not contain them. From a consuming project using
Python 3.12, install the [0.5.3 release](https://github.com/ThomasBury/pyragify/releases/tag/0.5.3)
wheel and both skills:

```bash
uv add --dev https://github.com/ThomasBury/pyragify/releases/download/0.5.3/pyragify-0.5.3-py3-none-any.whl
uvx library-skills install --skill pyragify-export --skill pyragify-graph
uvx library-skills scan --json
```

Once 0.5.3 or later is available on your package index, use
`uv add --dev "pyragify>=0.5.3"` instead of the wheel command.

uv records that wheel URL under `[tool.uv.sources]`, so normal upgrades keep
using the same wheel. After 0.5.3 or later is available on your package index,
remove only the `pyragify` entry from `[tool.uv.sources]` in `pyproject.toml`, then
run `uv add --dev "pyragify>=0.5.3"`, `uv lock --upgrade-package pyragify`,
and `uv sync --python 3.12` to resolve and install from the index.

Both commands assume the consuming project's declared `requires-python` is
`>=3.12,<3.13`. uv resolves against that entire range, not just the interpreter
currently running. If your project supports other Python versions, add
`--marker 'python_version == "3.12"'` to either `uv add` command to limit this
development dependency to Python 3.12. The marker does not select an interpreter.
Before adding the dependency, select Python 3.12 for the project environment:

```bash
uv python pin 3.12
uv sync --python 3.12
```

Then run the chosen `uv add` command with the marker. Use `uv run pyragify` for
exports; `uvx library-skills` scans the project's now-synced `.venv`. See
[uv's resolution rules](https://docs.astral.sh/uv/concepts/resolution/).

[Library Skills](https://library-skills.io/create/) discovers skills inside
installed library packages. It scans the project's environment, so a global
installation or an isolated `uvx pyragify` CLI alone does not support this workflow.
Run discovery and installation from the project root with its environment synced.

The default targets are `.agents/skills/pyragify-export` and
`.agents/skills/pyragify-graph`. If prompted for installation targets, accept
Agents (`.agents/skills`). The [official CLI options](https://library-skills.io/reference/)
include `--claude` to install additional targets under `.claude/skills` and `--copy`
to create ordinary directories where symlinks are unavailable:

```bash
uvx library-skills install --skill pyragify-export --skill pyragify-graph --claude
# Alternative for environments without symlinks:
uvx library-skills install --skill pyragify-export --skill pyragify-graph --copy
```

Symlinked skills follow the installed package version. Copied skills require
refreshing after upgrades: remove the old copied skill directories and reinstall
with `--copy`, preserving any local edits separately.

To use a source checkout containing these skills:

```bash
git clone https://github.com/ThomasBury/pyragify.git
cd pyragify
uv sync --locked
uvx library-skills scan --all --json
uvx library-skills install --skill pyragify-export --skill pyragify-graph
```

`--all` includes the checkout package itself, which is not one of its own
declared dependencies. In a consuming project, the default scan includes
Pyragify because it is a declared dependency.

The local packaging check uses Library Skills `0.0.19` against isolated wheel,
editable, and source-distribution installations:

```bash
uv run --locked python scripts/check_skill_packaging.py
```

Installation from PyPI remains unverified until PyPI publication.

## Use the skills

After installing the skills, check the installed targets from the project root:

```bash
uvx library-skills list --installed
```

The list should include `pyragify-export` and `pyragify-graph`. See the
[Library Skills reference](https://library-skills.io/reference/) for this command.
In an agent that loads the project's `.agents/skills`, try these requests:

- **pyragify-export:** "Use pyragify-export to export this repository to
  `./output` without a graph. Review the omissions in `index.md` and
  `metadata.json` before handing over the source."
- **pyragify-graph:** "Use pyragify-graph to find candidate callers of
  `hello_world`. Verify each candidate against the source and report any
  uncertainty."

Replace `hello_world` with a function in your repository. Graph results are
experimental leads; source inspection is required before treating them as facts.

## CLI verification

For a standalone installation, keep its virtual environment activated:

```bash
# View help
pyragify --help
```

For a consuming project or source checkout, run from its root instead:

```bash
uv run pyragify --help
```

You should see output similar to:

```
Usage: pyragify [OPTIONS] COMMAND [ARGS]...

Export complete repository source as Markdown with a provenance manifest.

Options:
  --help  Show this message and exit.

Commands:
  process-repo  Process a repository and output its content to text files...
  query-graph   Query the knowledge graph for context and relationships.
```

## Parser Dependencies

Official Tree-sitter Python bindings and eight individual grammar packages
(JavaScript, TypeScript, Java, C, C++, Go, HTML, and CSS) are required dependencies,
installed with Pyragify at pinned versions. Do not upgrade them independently.
Python analysis continues to use the standard-library `ast` module.

For a source checkout containing `pyproject.toml` and `uv.lock`, install the
locked dependencies from the checkout root:

```bash
uv sync --locked
```

This command is for repository development, not for a standalone pip installation.

### Development Dependencies

From the root of a source checkout:

```bash
uv sync --locked --group dev --group docs
```

## Troubleshooting

### Common Installation Issues

#### Permission Errors

Create the virtual environment in a directory you own, activate it, and rerun
the release-wheel installation above. `uv pip install` needs an environment;
it does not create one automatically.

#### Python Version Issues

Ensure you're using Python 3.12:

```bash
python --version
# Should show Python 3.12.x
```

#### Virtual Environment Issues

For a standalone CLI, activate the environment created above before running
`pyragify`:

```bash
source pyragify-env/bin/activate  # Linux/macOS
# Windows PowerShell: pyragify-env\Scripts\Activate.ps1
python --version  # Should show Python 3.12.x
pyragify --help
```

For a consuming project or source checkout, use `uv run pyragify --help` from
its root. If the environment is missing, follow the corresponding installation
route above.

### Testing the Installation

With the standalone environment activated, create a simple test to verify
everything is working. In a consuming project or source checkout, prefix the
Pyragify command with `uv run`.

```bash
# Create a test directory
mkdir test-repo
cd test-repo

# Create a simple Python file
echo 'def hello_world():
    """A simple function."""
    print("Hello, World!")
    return "success"' > test.py

# Create a basic config
echo 'repo_path: .
output_dir: ./output
max_words: 50000' > config.yaml

# Test Pyragify
pyragify process-repo --config-file config.yaml --verbose
```

If successful, you should see output indicating the repository was processed.

## Next Steps

Now that you have Pyragify installed, you can:

1. [Create your first configuration](configuration.md)
2. [Process your first repository](quick-start.md)
3. [Explore the CLI commands](../user-guide/cli-reference.md)
4. [Learn about the knowledge graph features](../user-guide/knowledge-graph.md)

## Support

If you encounter any issues during installation:

- Check the [GitHub Issues](https://github.com/ThomasBury/pyragify/issues) for similar problems
- Create a new issue with details about your environment and the error message
- Include the output of `python --version` and `pip list` in your issue
