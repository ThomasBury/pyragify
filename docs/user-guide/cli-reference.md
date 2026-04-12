# CLI Reference

Complete reference for all Pyragify command-line commands and options.

## Global Options

All commands support these global options:

```bash
pyragify [GLOBAL_OPTIONS] COMMAND [COMMAND_OPTIONS]
```

| Option | Short | Type | Description |
|--------|-------|------|-------------|
| `--config-file` | `-c` | PATH | Path to configuration YAML file (default: config.yaml) |
| `--help` | `-h` | - | Show help message and exit |
| `--install-completion` | - | - | Install shell completion |
| `--show-completion` | - | - | Show shell completion script |

## Commands

### `process-repo`

Process a repository and generate output files for NotebookLM.

```bash
pyragify process-repo [OPTIONS]
```

#### Repository Options

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--repo-path` | `-r` | PATH | - | Override repository path |
| `--output-dir` | `-o` | PATH | - | Override output directory |
| `--max-words` | `-w` | INTEGER | - | Override max words per chunk |
| `--max-file-size` | `-s` | INTEGER | - | Override max file size (bytes) |
| `--skip-patterns` | - | TEXT | - | Override skip patterns (comma-separated) |
| `--skip-dirs` | - | TEXT | - | Override skip directories (comma-separated) |
| `--verbose` | `-v` | - | - | Enable verbose output |

#### Graph Options

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--enable-graph` | `-g` | - | - | Enable knowledge graph building |
| `--graph-output-dir` | - | PATH | - | Override graph output directory |
| `--graph-format` | - | TEXT | - | Graph format (json, graphml) |
| `--include-relationships` | - | TEXT | - | Relationship types (comma-separated) |

#### Examples

```bash
# Basic usage with config file
pyragify process-repo --config-file my-config.yaml

# Process with overrides
pyragify process-repo \
  --repo-path ./my-project \
  --output-dir ./output \
  --max-words 100000 \
  --verbose

# Enable graph building
pyragify process-repo \
  --enable-graph \
  --graph-output-dir ./graphs \
  --include-relationships imports,calls,inherits

# Skip specific files and directories
pyragify process-repo \
  --skip-patterns "*.log,*.tmp" \
  --skip-dirs "node_modules,__pycache__"
```

### `query-graph`

Query the knowledge graph for context and relationships.

```bash
pyragify query-graph [OPTIONS]
```

#### Query Options

| Option | Short | Type | Description |
|--------|-------|------|-------------|
| `--graph-path` | `-p` | PATH | Path to graph JSON file |
| `--command` | `-c` | TEXT | Query command (required) |
| `--entity` | `-e` | TEXT | Entity ID or name |
| `--depth` | `-d` | INTEGER | Traversal depth (default: 2) |
| `--pattern` | - | TEXT | Search pattern |
| `--output-format` | `-f` | TEXT | Output format (json, text) |

#### Query Commands

##### `stats`

Show graph statistics.

```bash
pyragify query-graph --command stats
```

**Output:**
```json
{
  "total_nodes": 94,
  "total_edges": 93,
  "node_types": {
    "file": 7,
    "function": 72,
    "class": 11,
    "comments": 4
  },
  "edge_types": {
    "contains": 90,
    "cross_file_reference": 3
  },
  "languages": ["python"]
}
```

##### `related`

Find related context for an entity.

```bash
pyragify query-graph --command related --entity "src/main.py::MyClass" --depth 3
```

**Required Parameters:**
- `--entity` *(required)*: Entity ID (e.g., `file.py::function_name`, `file.py::ClassName`)

**Optional Parameters:**
- `--depth`: Traversal depth (default: 2)
- `--output-format`: Output format (`json` or `text`, default: `json`)

**Output:**
```json
{
  "entity": "src/main.py::MyClass",
  "results": [
    {
      "node": {
        "id": "file::src/main.py",
        "type": "file",
        "name": "main.py",
        "file": "src/main.py"
      },
      "relevance_score": 0.5,
      "relationship_path": ["contains"]
    }
  ]
}
```

##### `hierarchy`

Get call hierarchy for a function.

```bash
pyragify query-graph --command hierarchy --entity "calculate_total" --output-format json
```

**Required Parameters:**
- `--entity` *(required)*: Function name

**Optional Parameters:**
- `--output-format`: Output format (`json` or `text`, default: `json`)

**Output:**
```json
{
  "function": "calculate_total",
  "callers": [
    {
      "name": "get_total",
      "file": "src/main.py",
      "line": 25
    }
  ],
  "callees": [
    {
      "name": "sum",
      "line": 12
    }
  ],
  "locations": [
    {
      "file": "src/main.py",
      "line": 5
    }
  ]
}
```

##### `dependencies`

Find dependencies for a file.

```bash
pyragify query-graph --command dependencies --entity "src/main.py" --output-format json
```

**Required Parameters:**
- `--entity` *(required)*: File path

**Optional Parameters:**
- `--output-format`: Output format (`json` or `text`, default: `json`)

**Output:**
```json
{
  "file": "src/main.py",
  "dependencies": [
    "src/utils.py",
    "src/models.py"
  ]
}
```

##### `search`

Search nodes by pattern.

```bash
pyragify query-graph --command search --pattern "function.*error" --output-format json
```

**Required Parameters:**
- `--pattern` *(required)*: Regex pattern to search for

**Optional Parameters:**
- `--output-format`: Output format (`json` or `text`, default: `json`)

**Output:**
```json
{
  "pattern": "function.*error",
  "results": [
    {
      "id": "src/main.py::handle_error",
      "type": "function",
      "name": "handle_error",
      "file": "src/main.py"
    }
  ]
}
```

## Output Formats

### JSON Format

Structured data output for programmatic use:

```bash
pyragify query-graph --command stats --output-format json
```

### Text Format

Human-readable output:

```bash
pyragify query-graph --command stats --output-format text
```

## Configuration File Format

Pyragify uses YAML configuration files:

```yaml
# Repository settings
repo_path: /path/to/repository
output_dir: ./output
max_words: 200000
max_file_size: 10485760

# Processing options
skip_patterns:
  - "*.log"
  - "*.tmp"
skip_dirs:
  - "__pycache__"
  - "node_modules"
verbose: false

# Graph settings
graph:
  enabled: true
  output_dir: "./graphs"
  format: "json"
  relationships:
    - "imports"
    - "calls"
    - "inherits"
    - "references"
  max_depth: 5
  compression: true
  include_cross_file_refs: true
  validate_graph: true
  repair_graph: true
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PYRAGIFY_CONFIG` | Default config file path | `config.yaml` |
| `PYRAGIFY_VERBOSE` | Enable verbose logging | `false` |
| `PYRAGIFY_LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR) | `INFO` |
| `PYRAGIFY_MAX_WORKERS` | Maximum parallel workers for processing | `CPU count` |

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error |
| 2 | Invalid command/arguments |

## Examples

### Complete Workflow

```bash
# 1. Process repository with graph
pyragify process-repo \
  --repo-path ./my-project \
  --output-dir ./output \
  --enable-graph \
  --verbose

# 2. Check graph statistics
pyragify query-graph --command stats

# 3. Find related functions
pyragify query-graph \
  --command related \
  --entity "src/main.py::process_data" \
  --depth 3

# 4. Get call hierarchy
pyragify query-graph \
  --command hierarchy \
  --entity "process_data"

# 5. Search for patterns
pyragify query-graph \
  --command search \
  --pattern "test.*function"
```

### Batch Processing

```bash
# Process multiple repositories
for repo in repo1 repo2 repo3; do
  pyragify process-repo \
    --repo-path "$repo" \
    --output-dir "$repo/output" \
    --enable-graph
done
```

### Integration with Scripts

```bash
#!/bin/bash
# Process and analyze repository

REPO_PATH="./my-project"
OUTPUT_DIR="./analysis"

# Process repository
pyragify process-repo \
  --repo-path "$REPO_PATH" \
  --output-dir "$OUTPUT_DIR" \
  --enable-graph

# Generate summary report
pyragify query-graph --command stats > "$OUTPUT_DIR/graph-stats.json"

# Find main functions
pyragify query-graph \
  --command search \
  --pattern "^main$" \
  --output-format json > "$OUTPUT_DIR/main-functions.json"
```

## Troubleshooting

### Common Issues

**Command not found:**
```bash
# Ensure pyragify is installed and in PATH
which pyragify
pyragify --version
```

**Configuration file not found:**
```bash
# Check file exists and path is correct
ls -la config.yaml
pyragify --config-file /full/path/to/config.yaml
```

**Permission errors:**
```bash
# Check directory permissions
ls -ld /path/to/repo
ls -ld /path/to/output
```

**Graph query fails:**
```bash
# Ensure graph was built during processing
ls -la output/graphs/
pyragify query-graph --graph-path output/graphs/repository_graph.json --command stats
```

### Debug Mode

Enable detailed logging:

```bash
pyragify --verbose process-repo --config-file config.yaml
```

### Getting Help

```bash
# General help
pyragify --help

# Command-specific help
pyragify process-repo --help
pyragify query-graph --help

# Completion setup
pyragify --install-completion
```

## Advanced Troubleshooting

### Tree-sitter Issues

**Problem**: Tree-sitter parsing fails with version compatibility errors
```
WARNING: Tree-sitter parsing failed for javascript: version compatibility
```

**Solutions**:
```bash
# Check tree-sitter installation
pip list | grep tree-sitter

# Reinstall tree-sitter packages
pip uninstall tree-sitter tree-sitter-languages
pip install tree-sitter tree-sitter-languages

# Force regex fallback (automatic)
pyragify process-repo --verbose  # Will show fallback usage
```

### Graph Building Issues

**Problem**: Graph queries return empty results
```bash
# Check if graph was built
ls -la output/graphs/

# Verify graph file exists
pyragify query-graph --command stats --graph-path output/graphs/repository_graph.json
```

**Problem**: Graph validation errors
```bash
# Enable graph validation in config
echo "graph:
  validate_graph: true
  repair_graph: true" >> config.yaml
```

### Memory Issues

**Problem**: Out of memory errors with large repositories
```yaml
# Reduce memory usage
graph:
  max_depth: 2
  compression: true

# Limit file sizes
max_file_size: 52428800  # 50 MB
```

### Encoding Issues

**Problem**: Files with unusual encodings cause errors
```bash
# Check file encoding
file your-file.py

# Convert encoding if needed
iconv -f latin1 -t utf8 your-file.py > your-file-utf8.py
```

### Performance Issues

**Problem**: Processing takes too long
```yaml
# Optimize for speed
max_words: 100000  # Smaller chunks
graph:
  enabled: false   # Disable graph for faster processing
  relationships: ["imports"]  # Minimal relationships only
```

### Parallel Processing Issues

**Problem**: Worker processes fail
```bash
# Check available memory
free -h

# Reduce worker count
export PYRAGIFY_MAX_WORKERS=2

# Run sequentially (single process)
# Edit processor.py to disable ProcessPoolExecutor
```

### Configuration Override Issues

**Problem**: CLI options not taking effect
```bash
# Check option precedence
pyragify --verbose --config-file config.yaml

# Verify config file syntax
python -c "import yaml; yaml.safe_load(open('config.yaml'))"
```

### File Discovery Issues

**Problem**: Files not being processed
```bash
# Check skip patterns
pyragify --verbose --repo-path . | grep "skip"

# Verify file permissions
find . -name "*.py" -exec ls -la {} \;
```

### Graph Query Issues

**Problem**: Entity not found in graph
```bash
# List available entities
pyragify query-graph --command search --pattern ".*"

# Check entity format
pyragify query-graph --command related --entity "src/main.py::function_name"
```

### Incremental Processing Issues

**Problem**: Files not reprocessing when changed
```bash
# Force reprocessing
rm output/hashes.json

# Check file modification times
find . -name "*.py" -newer output/hashes.json
```

## Advanced Usage

### Custom Output Processing

```bash
# Process output with custom tools
pyragify process-repo --output-dir ./output

# Extract specific information
grep -r "function" output/python/ > functions.txt
grep -r "class" output/python/ > classes.txt

# Generate custom reports
python -c "
import json
with open('output/metadata.json') as f:
    data = json.load(f)
    print(f'Processed {data[\"summary\"][\"total_files_processed\"]} files')
"
```

### Integration with CI/CD

```yaml
# .github/workflows/analyze.yml
name: Analyze Codebase
on: [push, pull_request]

jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - name: Install Pyragify
        run: pip install pyragify
      - name: Analyze repository
        run: |
          pyragify process-repo \
            --repo-path . \
            --output-dir ./analysis \
            --enable-graph \
            --verbose
      - name: Upload analysis
        uses: actions/upload-artifact@v3
        with:
          name: code-analysis
          path: ./analysis/
```

### Custom Scripts

```python
#!/usr/bin/env python3
"""
Custom Pyragify analysis script
"""
import subprocess
import json
from pathlib import Path

def analyze_repository(repo_path, output_dir):
    # Process repository
    cmd = [
        "pyragify", "process-repo",
        "--repo-path", str(repo_path),
        "--output-dir", str(output_dir),
        "--enable-graph",
        "--verbose"
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return False

    # Get statistics
    stats_cmd = ["pyragify", "query-graph", "--command", "stats"]
    stats_result = subprocess.run(stats_cmd, capture_output=True, text=True)

    if stats_result.returncode == 0:
        stats = json.loads(stats_result.stdout)
        print(f"Analysis complete: {stats['total_nodes']} nodes, {stats['total_edges']} edges")

    return True

if __name__ == "__main__":
    analyze_repository(Path("./my-repo"), Path("./output"))