# Installation

This guide will help you install Pyragify on your system.

## Prerequisites

- **Python**: Version 3.12 only (`>=3.12,<3.13`)
- **Operating System**: Linux, macOS, or Windows

## Installation Methods

### Method 1: Using uv (Recommended)

[uv](https://github.com/astral-sh/uv) is a fast Python package manager that handles virtual environments automatically.

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Pyragify
uv pip install pyragify
```

### Method 2: Using pip

If you prefer using pip, you can install Pyragify from PyPI:

```bash
# Install Pyragify
pip install pyragify

# Optional: Create a virtual environment first
python -m venv pyragify-env
source pyragify-env/bin/activate  # On Windows: pyragify-env\Scripts\activate
pip install pyragify
```

### Method 3: From Source

If you want to install from source (for development or the latest features):

```bash
# Clone the repository
git clone https://github.com/ThomasBury/pyragify.git
cd pyragify

# Install with uv (recommended)
uv sync --locked --group dev --group docs

# Or with pip
pip install -e .
```

## Agent skills

Pyragify 0.5.0 bundles two self-contained skills:
`pyragify-export` covers source-only exports and manifest inspection;
`pyragify-graph` covers experimental graph export and queries with source checks.
Versions before 0.5.0 do not contain them. Once 0.5.0 or later is available on
your package index, install from a consuming project using Python 3.12:

```bash
uv add --dev pyragify
uvx library-skills install --skill pyragify-export --skill pyragify-graph
uvx library-skills scan --json
```

PyPI publication is separate from the GitHub release. Until the package is on
your index, download the wheel from the
[0.5.0 release](https://github.com/ThomasBury/pyragify/releases/tag/0.5.0)
and use `uv add --dev /path/to/pyragify-0.5.0-py3-none-any.whl` instead.

[Library Skills](https://library-skills.io/create/) discovers skills inside
installed library packages. It scans the project's environment, so a global
installation or an isolated `uvx pyragify` CLI alone does not support this workflow.
Run discovery and installation from the project root with its environment synced.

The default targets are `.agents/skills/pyragify-export` and
`.agents/skills/pyragify-graph`. The [official CLI options](https://library-skills.io/reference/)
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
uvx library-skills scan --json
uvx library-skills install --skill pyragify-export --skill pyragify-graph
```

The local packaging check uses Library Skills `0.0.19` against isolated wheel,
editable, and source-distribution installations:

```bash
uv run --locked python scripts/check_skill_packaging.py
```

Installation from PyPI remains unverified until PyPI publication.

## CLI verification

After installation, verify that Pyragify is working:

```bash
# View help
pyragify --help
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

If you get permission errors during installation:

```bash
# Use --user flag with pip
pip install --user pyragify

# Or use uv which handles this automatically
uv pip install pyragify
```

#### Python Version Issues

Ensure you're using Python 3.12:

```bash
python --version
# Should show Python 3.12.x
```

#### Virtual Environment Issues

If you're having trouble with virtual environments:

```bash
# Create and activate a new environment
python -m venv pyragify-env
source pyragify-env/bin/activate  # Linux/macOS
# pyragify-env\Scripts\activate   # Windows

# Install in the activated environment
pip install pyragify
```

### Testing the Installation

Create a simple test to verify everything is working:

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
