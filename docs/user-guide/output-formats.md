# Output Formats

Pyragify generates structured output optimized for different use cases. This guide explains the various output formats and how to work with them.

## Directory Structure

After processing, Pyragify creates this output structure:

```
output/
├── graphs/                    # Knowledge graph files
│   └── repository_graph.json
├── hashes.json               # File hash cache
├── metadata.json             # Processing metadata
├── python/                   # Python code chunks
│   ├── chunk_0.txt
│   ├── chunk_1.txt
│   └── ...
├── javascript/               # JavaScript chunks
├── java/                     # Java chunks
├── cpp/                      # C/C++ chunks
├── markdown/                 # Markdown chunks
├── html/                     # HTML chunks
├── css/                      # CSS chunks
└── other/                    # Other file types
```

## Chunk Format

### Python Files

Each Python chunk follows this structure:

```
--- File: src/main.py Type: function Name: calculate_total Lines: 10-25 ---
### Function: `calculate_total`

**Docstring:**
> Calculate the total price of items with tax.

**Code:**
```python
def calculate_total(items, tax_rate=0.1):
    """Calculate the total price of items with tax."""
    subtotal = sum(item.price for item in items)
    return subtotal * (1 + tax_rate)
```
```

**Components:**
- **Header**: File path, chunk type, name, line numbers
- **Title**: Formatted chunk title
- **Docstring**: Extracted documentation
- **Code**: Syntax-highlighted code block

### Class Chunks

```
--- File: src/main.py Type: class Name: ShoppingCart Lines: 30-60 ---
### Class: `ShoppingCart`

**Docstring:**
> A shopping cart that manages items.

**Methods:**
- add_item(item)
- get_total()
- clear()

**Code:**
```python
class ShoppingCart:
    """A shopping cart that manages items."""

    def __init__(self):
        self.items = []

    def add_item(self, item):
        """Add an item to the cart."""
        self.items.append(item)

    def get_total(self):
        """Calculate total price."""
        return calculate_total(self.items)

    def clear(self):
        """Remove all items."""
        self.items.clear()
```
```

### Markdown Files

```
--- File: README.md Type: markdown Header: # Installation Lines: 1-15 ---
### # Installation

This section covers installation instructions.

## Prerequisites

- Python 3.9+
- pip or uv package manager

## Install Command

```bash
pip install pyragify
```
```

## Metadata Files

### metadata.json

Contains comprehensive information about the processing run:

```json
{
  "processed_files": [
    {
      "path": "src/main.py",
      "chunks": 3,
      "size": 2048,
      "lines": 85,
      "words": 450
    }
  ],
  "skipped_files": [
    {
      "path": ".git/config",
      "reason": "Skipped by pattern or size"
    }
  ],
  "summary": {
    "total_files_processed": 8,
    "total_words": 2500
  },
  "graph": {
    "total_nodes": 94,
    "total_edges": 93,
    "languages": ["python"],
    "node_types": {
      "file": 7,
      "function": 72,
      "class": 11
    }
  }
}
```

### hashes.json

Tracks file hashes for incremental processing:

```json
{
  "src/main.py": "a1b2c3d4...",
  "src/utils.py": "e5f6g7h8...",
  "README.md": "i9j0k1l2..."
}
```

## Knowledge Graph Format

### repository_graph.json

The knowledge graph is stored as a JSON file:

```json
{
  "nodes": {
    "file::src/main.py": {
      "id": "file::src/main.py",
      "type": "file",
      "file": "src/main.py",
      "name": "main.py",
      "language": "python",
      "metadata": {
        "size": 2048
      }
    },
    "src/main.py::calculate_total": {
      "id": "src/main.py::calculate_total",
      "type": "function",
      "file": "src/main.py",
      "name": "calculate_total",
      "line_start": 10,
      "line_end": 25,
      "language": "python",
      "metadata": {
        "docstring": "Calculate total price",
        "parameters": ["items", "tax_rate"]
      }
    }
  },
  "edges": [
    {
      "source": "file::src/main.py",
      "target": "src/main.py::calculate_total",
      "type": "contains",
      "metadata": {
        "line_start": 10,
        "line_end": 25
      }
    }
  ],
  "metadata": {
    "version": "1.0",
    "created_at": "2024-01-15T10:30:00Z",
    "total_nodes": 94,
    "total_edges": 93,
    "languages": ["python"]
  }
}
```

## Integration with NotebookLM

### Optimal Chunk Sizes

For best NotebookLM results:

```yaml
# Recommended settings
max_words: 150000  # Smaller chunks for better context
output_dir: ./notebooklm-ready
```

### File Organization

Structure files for easy NotebookLM upload:

```bash
# Create topic-based directories
mkdir -p output/{core-functions,classes,utilities,tests}

# Or use language-based organization (default)
# Python files go to output/python/
# JavaScript files go to output/javascript/
```

### Content Optimization

Pyragify automatically formats content for NotebookLM:

- **Clear headers** with file paths and types
- **Syntax highlighting** in code blocks
- **Docstring preservation** for documentation
- **Line number references** for easy navigation

## Custom Processing

### Filtering Output

Control what gets included in output:

```python
# Custom filter script
import json
from pathlib import Path

def filter_chunks(input_dir, output_dir, criteria):
    """Filter and reorganize chunks based on criteria."""

    for chunk_file in Path(input_dir).glob("*.txt"):
        with open(chunk_file) as f:
            content = f.read()

        # Apply filtering logic
        if criteria in content:
            # Copy or modify chunk
            pass
```

### Merging Chunks

Combine related chunks:

```python
def merge_related_chunks(chunk_files):
    """Merge chunks that belong together."""

    merged = {}
    for chunk_file in chunk_files:
        # Extract topic from chunk
        topic = extract_topic(chunk_file)

        if topic not in merged:
            merged[topic] = []

        merged[topic].append(chunk_file)

    # Combine chunks by topic
    for topic, files in merged.items():
        combine_chunks(files, f"{topic}.txt")
```

## Advanced Output Options

### JSON Export

Export structured data for programmatic use:

```bash
# Export graph as JSON
pyragify query-graph --command stats --output-format json > stats.json

# Export search results
pyragify query-graph --command search --pattern "function" --output-format json > functions.json
```

### Custom Formatting

Modify chunk formatting:

```python
# Custom chunk formatter
def custom_format_chunk(chunk):
    """Custom formatting for specific use cases."""

    if chunk["type"] == "function":
        return f"""
# {chunk["name"]}
# File: {chunk["file"]}
# Lines: {chunk["start_line"]}-{chunk["end_line"]}

{chunk["code"]}
""".strip()

    return str(chunk)
```

## Performance Considerations

### Chunk Size Optimization

```yaml
# For large repositories
max_words: 200000  # Balance between context and file size

# For detailed analysis
max_words: 50000   # Smaller chunks for precision
```

### Incremental Updates

Pyragify uses file hashing to avoid reprocessing:

```bash
# Force reprocessing
rm output/hashes.json
pyragify --config-file config.yaml

# Check what changed
pyragify --verbose --config-file config.yaml
```

## Troubleshooting Output Issues

### Missing Chunks

**Problem:** Some files not appearing in output

**Solutions:**
```bash
# Check if files were processed
grep "filename" output/metadata.json

# Enable verbose logging
pyragify --verbose --config-file config.yaml

# Check skip patterns
cat config.yaml | grep skip
```

### Incorrect Chunking

**Problem:** Code split incorrectly

**Solutions:**
```yaml
# Adjust chunk size
max_words: 100000  # Smaller chunks

# Or disable chunking for specific files
skip_patterns:
  - "large_file.py"  # Process as single chunk
```

### Encoding Issues

**Problem:** Special characters not displaying correctly

**Solutions:**
```bash
# Ensure UTF-8 encoding
export PYTHONIOENCODING=utf-8
pyragify --config-file config.yaml

# Check file encoding
file output/python/chunk_0.txt
```

## Integration Examples

### CI/CD Pipeline

```yaml
# .github/workflows/docs.yml
name: Generate Documentation
on: [push, pull_request]

jobs:
  docs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Process with Pyragify
        run: |
          pip install pyragify
          pyragify --repo-path . --enable-graph
      - name: Upload chunks
        uses: actions/upload-artifact@v3
        with:
          name: code-chunks
          path: output/
```

### Documentation Generation

```python
#!/usr/bin/env python3
"""
Generate API documentation from Pyragify output
"""
import json
from pathlib import Path

def generate_api_docs(output_dir):
    """Generate API docs from processed chunks."""

    # Load metadata
    with open(f"{output_dir}/metadata.json") as f:
        metadata = json.load(f)

    # Process each chunk file
    api_docs = {}

    for file_info in metadata["processed_files"]:
        file_path = file_info["path"]
        language = Path(file_path).suffix[1:]

        if language not in api_docs:
            api_docs[language] = []

        # Extract functions and classes from chunks
        # (Implementation depends on chunk format)

    return api_docs
```

### Custom Analysis

```python
#!/usr/bin/env python3
"""
Custom analysis of Pyragify output
"""
import re
from pathlib import Path

def analyze_complexity(output_dir):
    """Analyze code complexity from chunks."""

    complexity = {
        "functions": [],
        "classes": [],
        "files": []
    }

    chunk_dir = Path(output_dir) / "python"

    for chunk_file in chunk_dir.glob("*.txt"):
        with open(chunk_file) as f:
            content = f.read()

        # Extract complexity metrics
        functions = len(re.findall(r'---.*Type: function', content))
        classes = len(re.findall(r'---.*Type: class', content))
        lines = len(content.split('\n'))

        complexity["functions"].append(functions)
        complexity["classes"].append(classes)
        complexity["files"].append({
            "name": chunk_file.name,
            "functions": functions,
            "classes": classes,
            "lines": lines
        })

    return complexity
```

The output formats are designed to be both human-readable and machine-processable, making Pyragify suitable for a wide range of use cases from documentation generation to automated analysis.