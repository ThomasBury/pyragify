# Configuration

Pyragify is highly configurable through YAML configuration files and command-line options. This guide covers all available configuration options.

## Configuration File Structure

Create a `config.yaml` file in your project root:

```yaml
# Repository and output settings
repo_path: /path/to/repository
output_dir: ./output
max_words: 200000
max_file_size: 10485760

# Processing options
skip_patterns: []
skip_dirs: ["__pycache__", "node_modules"]
verbose: false

# Knowledge graph settings
graph:
  enabled: true
  output_dir: "./graphs"
  format: "json"
  relationships: ["imports", "calls", "inherits"]
  max_depth: 5
  compression: true
```

## Core Configuration Options

### Repository Settings

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `repo_path` | string | `.` | Path to the repository to process |
| `output_dir` | string | `./output` | Directory where processed files will be saved |
| `max_words` | integer | `200000` | Maximum words per output chunk |
| `max_file_size` | integer | `10485760` | Maximum file size in bytes (10 MB) |

### Processing Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `skip_patterns` | list | `[]` | File patterns to skip (e.g., `["*.log", "*.tmp"]`) |
| `skip_dirs` | list | `[]` | Directory names to skip (e.g., `["__pycache__", "node_modules"]`) |
| `verbose` | boolean | `false` | Enable detailed logging output |

## Knowledge Graph Configuration

The knowledge graph feature captures relationships between code entities:

```yaml
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
```

### Graph Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | boolean | `false` | Enable knowledge graph building |
| `output_dir` | string | `"./graphs"` | Directory for graph files |
| `format` | string | `"json"` | Graph serialization format |
| `relationships` | list | `["imports", "calls", "inherits"]` | Relationship types to extract |
| `max_depth` | integer | `5` | Maximum traversal depth for queries |
| `compression` | boolean | `true` | Enable graph compression |
| `include_cross_file_refs` | boolean | `true` | Enable cross-file reference resolution |
| `validate_graph` | boolean | `true` | Validate graph integrity after building |
| `repair_graph` | boolean | `true` | Attempt to repair graph issues automatically |

### Relationship Types

Pyragify can extract different types of relationships:

- **`imports`**: Module import relationships
- **`calls`**: Function and method call relationships
- **`inherits`**: Class inheritance relationships
- **`references`**: Variable and symbol references
- **`contains`**: File containment relationships (automatic)

### Advanced Graph Options

For more control over graph processing:

```yaml
graph:
  enabled: true
  # Basic options...
  include_cross_file_refs: true    # Resolve references between files
  validate_graph: true             # Check graph integrity after building
  repair_graph: true               # Auto-fix common graph issues
```

- **`include_cross_file_refs`**: When enabled, Pyragify analyzes relationships between different files and adds cross-file reference edges to the graph
- **`validate_graph`**: Performs integrity checks on the built graph, identifying orphaned edges and duplicate relationships
- **`repair_graph`**: Automatically attempts to fix validation issues by removing invalid edges and deduplicating relationships

## Command-Line Overrides

All configuration options can be overridden via command-line arguments:

```bash
# Override repository path
pyragify --repo-path /different/path

# Override output directory
pyragify --output-dir /custom/output

# Override word limit
pyragify --max-words 100000

# Enable verbose output
pyragify --verbose

# Enable graph building
pyragify --enable-graph

# Custom graph output directory
pyragify --graph-output-dir /custom/graphs
```

### Complete CLI Example

```bash
pyragify \
  --repo-path ./my-project \
  --output-dir ./processed \
  --max-words 150000 \
  --max-file-size 20971520 \
  --skip-patterns "*.log,*.tmp,*.cache" \
  --skip-dirs "__pycache__,node_modules,.git" \
  --verbose \
  --enable-graph \
  --graph-output-dir ./graphs \
  --graph-format json \
  --include-relationships imports,calls,inherits,references
```

## Configuration Examples

### Basic Python Project

```yaml
repo_path: .
output_dir: ./output
max_words: 100000
verbose: true

graph:
  enabled: true
  relationships: ["imports", "calls", "inherits"]
```

### Large JavaScript Project

```yaml
repo_path: ./src
output_dir: ./processed
max_words: 500000
max_file_size: 52428800  # 50 MB

skip_dirs:
  - "node_modules"
  - "dist"
  - "build"
  - ".next"

graph:
  enabled: true
  output_dir: "./graphs"
  relationships: ["imports", "calls", "references"]
```

### Multi-Language Repository

```yaml
repo_path: .
output_dir: ./output
max_words: 200000

# Skip common build artifacts
skip_patterns:
  - "*.min.js"
  - "*.min.css"
  - "*.map"

skip_dirs:
  - "__pycache__"
  - "node_modules"
  - "target"      # Java/Maven
  - "build"       # Various build outputs
  - "dist"
  - ".git"

graph:
  enabled: true
  relationships: ["imports", "calls", "inherits", "references"]
```

### Documentation-Focused Processing

```yaml
repo_path: .
output_dir: ./docs-output
max_words: 75000  # Smaller chunks for documentation

# Focus on source code, skip tests and build files
skip_patterns:
  - "*test*.py"
  - "*spec*.js"
  - "*.min.*"

skip_dirs:
  - "tests"
  - "__pycache__"
  - "node_modules"
  - "coverage"

graph:
  enabled: true
  # Include all relationship types for comprehensive analysis
  relationships: ["imports", "calls", "inherits", "references", "contains"]
```

## Advanced Configuration

### Custom Skip Patterns

Use glob patterns to skip specific files:

```yaml
skip_patterns:
  - "*.log"           # Log files
  - "*.tmp"           # Temporary files
  - "*.min.js"        # Minified JavaScript
  - "*.min.css"       # Minified CSS
  - "*.map"           # Source maps
  - "*test*"          # Test files
  - "*spec*"          # Spec files
  - "*.DS_Store"      # macOS system files
  - "Thumbs.db"       # Windows system files
```

### Performance Tuning

For large repositories, optimize performance:

```yaml
# Increase chunk size for fewer files
max_words: 500000

# Increase file size limit
max_file_size: 104857600  # 100 MB

# Limit graph depth for faster processing
graph:
  enabled: true
  max_depth: 3
  compression: true
```

### Incremental Processing

Pyragify automatically handles incremental processing using file hashes. To force reprocessing:

```bash
# Delete hashes to force full reprocessing
rm output/hashes.json

# Then run pyragify
pyragify --config-file config.yaml
```

## Environment Variables

Pyragify supports some configuration via environment variables:

```bash
# Set default config file location
export PYRAGIFY_CONFIG=config.yaml

# Enable verbose logging globally
export PYRAGIFY_VERBOSE=1
```

## Validation

Pyragify validates your configuration on startup. Common validation errors:

- **Invalid repo_path**: Directory doesn't exist or isn't readable
- **Invalid output_dir**: Cannot create output directory
- **Invalid max_words**: Must be positive integer
- **Invalid relationships**: Unknown relationship types

## Configuration File Discovery

Pyragify looks for configuration files in this order:

1. File specified with `--config-file`
2. `config.yaml` in current directory
3. `pyragify.yaml` in current directory
4. `.pyragify.yaml` in current directory

## Best Practices

### Organization

- Keep configuration files in your repository root
- Use descriptive names for output directories
- Document your configuration choices in comments

### Performance

- Use appropriate `max_words` for your use case
- Enable compression for large graphs
- Use `skip_patterns` to exclude irrelevant files

### Maintenance

- Version control your configuration files
- Document custom skip patterns
- Regularly review and update skip patterns as your project evolves

### Security

- Be careful with `skip_patterns` - don't accidentally exclude important files
- Validate output directories are writable
- Check file permissions on repository access

## Troubleshooting Configuration

### Common Issues

**Configuration file not found:**
```bash
# Specify full path
pyragify --config-file /full/path/to/config.yaml

# Or check current directory
ls -la config.yaml
```

**Invalid YAML syntax:**
```yaml
# Check for common YAML errors:
# - Incorrect indentation
# - Missing quotes around strings
# - Invalid boolean values (use true/false, not True/False)
```

**Permission errors:**
```bash
# Check directory permissions
ls -ld /path/to/repo
ls -ld /path/to/output

# Make directories writable
chmod 755 /path/to/output
```

### Debugging Configuration

Enable verbose logging to see configuration details:

```bash
pyragify --verbose --config-file config.yaml
```

This will show:
- Configuration file loaded
- All resolved configuration values
- File discovery and filtering details
- Processing progress

### Getting Help

```bash
# View all configuration options
pyragify --help

# Get help for specific commands
pyragify process-repo --help