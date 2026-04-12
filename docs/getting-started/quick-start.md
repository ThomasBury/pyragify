# Quick Start

Get up and running with Pyragify in minutes. This guide will walk you through processing your first repository.

## Before You Begin

Make sure you have:

- [Pyragify installed](installation.md)
- A code repository to process
- Basic familiarity with command-line tools

## Step 1: Prepare Your Repository

First, navigate to your repository or create a test repository:

```bash
# Navigate to your existing repository
cd /path/to/your/repository

# Or create a test repository
mkdir my-test-repo
cd my-test-repo

# Create some sample files
mkdir src
cat > src/main.py << 'EOF'
def calculate_total(items):
    """Calculate the total price of items."""
    total = 0
    for item in items:
        total += item.price
    return total

class ShoppingCart:
    """A simple shopping cart."""

    def __init__(self):
        self.items = []

    def add_item(self, item):
        """Add an item to the cart."""
        self.items.append(item)

    def get_total(self):
        """Get the total price of all items."""
        return calculate_total(self.items)
EOF

cat > README.md << 'EOF'
# My Test Repository

This is a sample repository for testing Pyragify.

## Features

- Shopping cart functionality
- Price calculation
- Item management
EOF
```

## Step 2: Create Configuration

Create a `config.yaml` file in your repository root:

```yaml
# Basic configuration for quick start
repo_path: .
output_dir: ./output
max_words: 50000
max_file_size: 10485760  # 10 MB

# Enable verbose output for learning
verbose: true

# Enable knowledge graph features
graph:
  enabled: true
  output_dir: "./graphs"
  format: "json"
```

!!! tip "Configuration Tips"
    - `repo_path: .` processes the current directory
    - `max_words: 50000` creates smaller chunks for easier review
    - `verbose: true` shows detailed processing information

## Step 3: Process Your Repository

Run Pyragify to process your repository:

```bash
# Using uv (recommended)
uv run pyragify process-repo --config-file config.yaml

# Or using direct execution
python -m pyragify process-repo --config-file config.yaml
```

You should see output like:

```
2024-01-15 10:30:00,000 - INFO - Loaded configuration from 'config.yaml'
2024-01-15 10:30:00,001 - INFO - Repository graph building enabled
2024-01-15 10:30:00,002 - INFO - Processing repository: /path/to/your/repository
2024-01-15 10:30:00,003 - INFO - Discovering and filtering files...
2024-01-15 10:30:00,004 - INFO - Found 3 new or modified files to process.
2024-01-15 10:30:00,005 - INFO - Graph building enabled for FileProcessor
2024-01-15 10:30:00,006 - INFO - Aggregating results for src/main.py
2024-01-15 10:30:00,007 - INFO - Added 2 cross-file reference edges
2024-01-15 10:30:00,008 - INFO - Graph contains 8 nodes and 7 edges
2024-01-15 10:30:00,009 - INFO - Repository processing complete.
```

## Step 4: Explore the Output

Check what Pyragify created:

```bash
# View the output directory structure
tree output/

# Should show something like:
output/
├── graphs/
│   └── repository_graph.json
├── hashes.json
├── metadata.json
├── python/
│   └── chunk_0.txt
└── remaining/
    └── chunk_0.txt
```

### Examine Processed Content

Look at the processed Python content:

```bash
# View the first chunk of Python code
head -50 output/python/chunk_0.txt
```

You should see structured output like:

```
--- File: src/main.py Type: function Name: calculate_total Lines: 1-8 ---
### Function: `calculate_total`

**Docstring:**
> Calculate the total price of items.

**Code:**
```python
def calculate_total(items):
    """Calculate the total price of items."""
    total = 0
    for item in items:
        total += item.price
    return total
```

--- File: src/main.py Type: class Name: ShoppingCart Lines: 10-25 ---
### Class: `ShoppingCart`

**Docstring:**
> A simple shopping cart.

**Code:**
```python
class ShoppingCart:
    """A simple shopping cart."""

    def __init__(self):
        self.items = []

    def add_item(self, item):
        """Add an item to the cart."""
        self.items.append(item)

    def get_total(self):
        """Get the total price of all items."""
        return calculate_total(self.items)
```
```

### Explore the Knowledge Graph

Check the generated knowledge graph:

```bash
# View graph statistics
python -m pyragify.cli query-graph --command stats

# Should show:
{
  "total_nodes": 8,
  "total_edges": 7,
  "node_types": {
    "file": 2,
    "function": 3,
    "class": 1,
    "comments": 2
  },
  "edge_types": {
    "contains": 6,
    "cross_file_reference": 1
  },
  "languages": ["python"]
}
```

## Step 5: Query Your Codebase

Try some queries on your processed repository:

```bash
# Find related context for the calculate_total function
python -m pyragify.cli query-graph --command related --entity "src/main.py::calculate_total"

# Get call hierarchy for calculate_total
python -m pyragify.cli query-graph --command hierarchy --entity "calculate_total"

# Search for all functions
python -m pyragify.cli query-graph --command search --pattern "function"
```

## Step 6: Use with NotebookLM

Your processed content is now ready for NotebookLM:

1. Go to [NotebookLM](https://notebooklm.google.com/)
2. Create a new notebook
3. Upload the `output/python/chunk_0.txt` file
4. Start asking questions like:
   - "What does the calculate_total function do?"
   - "How does the ShoppingCart class work?"
   - "What are the relationships between the functions?"

## Advanced Quick Start

### Process a Real Repository

Try processing a real Python project:

```bash
# Example: Process a Flask application
cd /path/to/flask-app

# Create config for larger project
cat > config.yaml << 'EOF'
repo_path: .
output_dir: ./pyragify-output
max_words: 200000
max_file_size: 52428800  # 50 MB

# Skip common directories
skip_dirs:
  - "__pycache__"
  - ".git"
  - "venv"
  - "node_modules"

verbose: true

graph:
  enabled: true
  output_dir: "./graphs"
EOF

# Process the repository
pyragify --config-file config.yaml
```

### Customize Processing

Experiment with different configurations:

```yaml
# Focus on specific file types
skip_patterns:
  - "*.md"      # Skip markdown files
  - "*.txt"     # Skip text files
  - "*.json"    # Skip JSON files

# Process only Python files
# (default behavior includes all supported types)

# Larger chunks for better context
max_words: 500000

# Include more relationship types
graph:
  enabled: true
  relationships:
    - "imports"
    - "calls"
    - "inherits"
    - "references"
    - "contains"
```

## Troubleshooting

### Common Issues

**"No files found to process"**
- Check that your `repo_path` is correct
- Ensure there are actual source files in the directory
- Check `skip_patterns` aren't excluding everything

**"Permission denied"**
- Make sure you have read access to the repository
- Check that the output directory is writable

**"Tree-sitter parsing failed"**
- This is normal for some languages
- Pyragify falls back to regex-based parsing
- The output will still be usable

### Getting Help

```bash
# View all available options
pyragify --help

# Get help for specific commands
pyragify process-repo --help
pyragify query-graph --help
```

## Next Steps

Now that you've processed your first repository:

1. [Learn about configuration options](configuration.md)
2. [Explore CLI commands](../user-guide/cli-reference.md)
3. [Understand the knowledge graph](../user-guide/knowledge-graph.md)
4. [See supported languages](../user-guide/supported-languages.md)

## Examples

### Real-World Examples

- **Web Application**: Process a Django or Flask app to understand the URL routing, models, and views
- **Data Science**: Analyze a Jupyter notebook collection with custom preprocessing
- **API Service**: Map out microservice architectures and API endpoints
- **Library**: Document internal code relationships and dependencies

### Integration Examples

- **CI/CD**: Add Pyragify to your build pipeline for automatic documentation
- **Code Review**: Generate context files for pull request reviews
- **Onboarding**: Create knowledge bases for new team members
- **Research**: Analyze code patterns across multiple repositories