# Installation

This guide will help you install Pyragify on your system.

## Prerequisites

- **Python**: Version 3.9 or higher (up to 3.12)
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
uv pip install -e .

# Or with pip
pip install -e .
```

## Verification

After installation, verify that Pyragify is working:

```bash
# Check version
pyragify --version

# View help
pyragify --help
```

You should see output similar to:

```
Usage: pyragify [OPTIONS] COMMAND [ARGS]...

A tool to process repositories and output text files for NotebookLM.

Options:
  --help  Show this message and exit.

Commands:
  process-repo  Process a repository and output its content to text files...
  query-graph   Query the knowledge graph for context and relationships.
```

## Optional Dependencies

Pyragify works out of the box, but you can enhance its capabilities with optional dependencies:

### Tree-sitter Support

For advanced parsing of JavaScript, TypeScript, Java, and C/C++ files:

```bash
# These are included by default, but you can ensure they're installed
uv pip install tree-sitter tree-sitter-languages
```

!!! note "Tree-sitter Compatibility"
    Currently, there are version compatibility issues between `tree-sitter` and `tree-sitter-languages` packages. Pyragify gracefully falls back to regex-based parsing when tree-sitter parsing fails.

### Development Dependencies

If you plan to contribute to Pyragify:

```bash
# Install development dependencies
uv pip install -e ".[dev]"

# Or with pip
pip install -e ".[dev]"
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

Ensure you're using Python 3.9+:

```bash
python --version
# Should show Python 3.9.x or higher
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