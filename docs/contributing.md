# Contributing to Pyragify

We welcome contributions from the community! This guide explains how to get started with contributing to Pyragify.

## Ways to Contribute

### 🐛 Bug Reports
- Use the [GitHub Issues](https://github.com/ThomasBury/pyragify/issues) page
- Include detailed steps to reproduce
- Provide sample code/files if applicable
- Include your environment details (OS, Python version, etc.)

### 💡 Feature Requests
- Check if the feature is already requested
- Provide detailed use case and benefits
- Consider backward compatibility

### 🛠️ Code Contributions
- Fix bugs
- Add new features
- Improve documentation
- Write tests

### 📚 Documentation
- Improve existing docs
- Add examples and tutorials
- Translate documentation
- Create video tutorials

## Development Setup

### Prerequisites

- Python 3.9 or higher
- Git
- uv package manager (recommended) or pip

### Clone and Setup

```bash
# Clone the repository
git clone https://github.com/ThomasBury/pyragify.git
cd pyragify

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# Install in development mode
pip install -e .[dev]

# Or using uv
uv pip install -e .[dev]
```

### Verify Installation

```bash
# Check installation
pyragify --version

# Run tests
pytest

# Check code quality
# (Add linting commands as needed)
```

## Development Workflow

### 1. Choose an Issue

- Check [GitHub Issues](https://github.com/ThomasBury/pyragify/issues) for open tasks
- Look for issues labeled `good first issue` or `help wanted`
- Comment on the issue to indicate you're working on it

### 2. Create a Branch

```bash
# Create and switch to feature branch
git checkout -b feature/your-feature-name

# Or for bug fixes
git checkout -b fix/issue-number-description
```

### 3. Make Changes

- Write clear, concise commit messages
- Follow the existing code style
- Add tests for new features
- Update documentation as needed

### 4. Test Your Changes

```bash
# Run the full test suite
pytest

# Run specific tests
pytest tests/test_specific_feature.py

# Test CLI commands
pyragify --help
pyragify process-repo --help

# Manual testing
mkdir test-repo
cd test-repo
echo "def test(): pass" > test.py
pyragify --repo-path . --verbose
```

### 5. Update Documentation

```bash
# Build documentation locally
mkdocs serve

# Check documentation builds
mkdocs build
```

### 6. Commit and Push

```bash
# Stage your changes
git add .

# Commit with descriptive message
git commit -m "feat: add new feature description

- What was changed
- Why it was changed
- How it affects users"

# Push to your fork
git push origin feature/your-feature-name
```

### 7. Create Pull Request

- Go to the [Pull Requests](https://github.com/ThomasBury/pyragify/pulls) page
- Click "New Pull Request"
- Select your branch
- Fill out the pull request template
- Link to any related issues

## Code Guidelines

### Python Style

- Follow [PEP 8](https://pep8.org/) style guidelines
- Use type hints for function parameters and return values
- Write docstrings for all public functions and classes
- Use descriptive variable and function names

### Example Code Style

```python
from typing import List, Optional
from pathlib import Path

def process_repository(
    repo_path: Path,
    output_dir: Optional[Path] = None,
    max_words: int = 200000
) -> List[Path]:
    """
    Process a repository and return output file paths.

    Args:
        repo_path: Path to the repository to process
        output_dir: Directory for output files (default: ./output)
        max_words: Maximum words per output chunk

    Returns:
        List of generated output file paths

    Raises:
        ValueError: If repo_path doesn't exist
    """
    if not repo_path.exists():
        raise ValueError(f"Repository path {repo_path} does not exist")

    # Implementation here
    pass
```

### Commit Messages

Follow conventional commit format:

```
type(scope): description

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Test additions/changes
- `chore`: Maintenance tasks

Examples:
```
feat: add support for TypeScript files
fix: resolve memory leak in graph processing
docs: update installation instructions
test: add unit tests for CLI commands
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=pyragify --cov-report=html

# Run specific test file
pytest tests/test_processor.py

# Run tests matching pattern
pytest -k "test_process"
```

### Writing Tests

- Use `pytest` framework
- Place test files in `tests/` directory
- Name test files as `test_*.py`
- Use descriptive test function names

```python
import pytest
from pathlib import Path
from pyragify.processor import FileProcessor

class TestFileProcessor:
    def test_python_chunking(self, tmp_path):
        """Test that Python files are chunked correctly."""
        # Arrange
        processor = FileProcessor(tmp_path, tmp_path / "output")
        test_file = tmp_path / "test.py"
        test_file.write_text("""
def hello_world():
    '''A simple function.'''
    return "Hello, World!"
""")

        # Act
        chunks, line_count = processor.chunk_python_file(test_file)

        # Assert
        assert line_count == 4
        assert len(chunks) == 1
        assert chunks[0]["type"] == "function"
        assert chunks[0]["name"] == "hello_world"
```

### Test Coverage

Aim for high test coverage:

```bash
# Check coverage
pytest --cov=pyragify --cov-report=term-missing

# Generate HTML coverage report
pytest --cov=pyragify --cov-report=html
open htmlcov/index.html  # View report
```

## Documentation

### Building Docs Locally

```bash
# Install documentation dependencies
pip install mkdocs mkdocs-material

# Serve docs locally
mkdocs serve

# Build docs
mkdocs build
```

### Documentation Guidelines

- Use clear, concise language
- Include code examples
- Provide troubleshooting sections
- Keep screenshots up to date
- Test all examples

## Adding Language Support

### Parser Implementation

To add support for a new language:

1. **Choose parser strategy**:
   - AST parsing (like Python)
   - Tree-sitter parsing
   - Regex-based parsing

2. **Implement parser method**:

```python
def _parse_new_language(self, content: str, file_path: Path) -> List[GraphEdge]:
    """Parse new language and extract relationships."""
    edges = []

    # Your parsing logic here
    # Extract imports, calls, inheritance, etc.

    return edges
```

3. **Add to main processing logic**:

```python
elif language == "new_language":
    dependencies = self._parse_new_language(content, file_path)
```

4. **Update FILE_TYPE_MAP**:

```python
FILE_TYPE_MAP.update({
    ".newlang": "new_language",
    ".new": "new_language"
})
```

### Testing New Language Support

```python
def test_new_language_support(tmp_path):
    """Test parsing of new language files."""
    processor = FileProcessor(tmp_path, tmp_path / "output")

    # Create test file
    test_file = tmp_path / "test.new"
    test_file.write_text("""
import something
func call_other()
class MyClass extends BaseClass
""")

    # Test parsing
    dependencies = processor.extract_dependencies(test_file, test_file.read_text(), "new_language")

    # Verify results
    assert len(dependencies) > 0
```

## Performance Optimization

### Profiling Code

```python
import cProfile
import pstats

def profile_processing():
    """Profile repository processing performance."""
    profiler = cProfile.Profile()
    profiler.enable()

    # Your code to profile
    processor.process_repo()

    profiler.disable()
    stats = pstats.Stats(profiler).sort_stats('cumulative')
    stats.print_stats(20)  # Top 20 functions
```

### Memory Optimization

- Use generators for large file processing
- Implement streaming for big repositories
- Cache expensive operations
- Use appropriate data structures

## Release Process

### Version Management

Pyragify uses [semantic versioning](https://semver.org/):

- **MAJOR**: Breaking changes
- **MINOR**: New features
- **PATCH**: Bug fixes

### Creating a Release

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Create git tag
4. Push to GitHub
5. GitHub Actions will create release

## Community

### Communication

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: General questions and ideas
- **Pull Request Comments**: Code review discussions

### Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Help newcomers learn
- Focus on solutions, not blame

### Recognition

Contributors are recognized in:
- GitHub contributor statistics
- CHANGELOG.md entries
- Release notes

## Getting Help

### Resources

- [Documentation](https://thomasbury.github.io/pyragify/)
- [Source Code](https://github.com/ThomasBury/pyragify)
- [GitHub Issues](https://github.com/ThomasBury/pyragify/issues)
- [GitHub Discussions](https://github.com/ThomasBury/pyragify/discussions)

### Asking Questions

When asking for help:

1. **Search existing issues** first
2. **Provide context** about your setup
3. **Include error messages** and stack traces
4. **Share minimal reproducible examples**
5. **Specify versions** of Python and Pyragify

Thank you for contributing to Pyragify! Your efforts help make code analysis more accessible and powerful for everyone.