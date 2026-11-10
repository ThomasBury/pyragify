# Changelog

All notable changes to Pyragify will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] — 2026-11-10

### Added

- Complete source exports with a provenance manifest, source hashes, and line mappings.
- Resolution of explicit Python function imports and aliases in root and `src/` layouts.
- JavaScript and TypeScript arrow-function callers and callees, including nested callbacks.
- A reproducible synthetic graph benchmark with recorded results and limitations.

### Changed

- Graph queries build a temporary adjacency map; cross-file resolution shares import indexes.
- Cache version 8 rebuilds records created by earlier graph extractors.
- Graphs remain experimental and opt-in. Dynamic calls, re-export chains, and JavaScript module resolution remain unsupported.

### Fixed

- Python shadowed names no longer resolve to unrelated local functions.
- Definition defaults and decorators retain their containing execution owner.
- JavaScript and TypeScript calls use parser positions, including same-line definitions and CRLF input.
- Documentation deployment uses the locked docs dependency group on Python 3.12.
- Export safety, CLI query validation, and relationship traversal fixes accumulated since 0.2.0.

## [0.2.0] — 2026-04-12

### Added

- Knowledge graph integration with comprehensive relationship analysis
- Graph query interface for exploring code relationships
- Support for cross-file reference resolution
- Tree-sitter integration for advanced language parsing (with regex fallback)
- Mkdocs documentation with comprehensive user guides
- CLI query commands for graph analysis
- Performance optimizations for large repositories
- Incremental processing with file hashing
- Graph validation and repair functionality
- Cross-file reference resolution
- Advanced query patterns and pattern matching

- Knowledge Graph Integration (Phase 1-3)
  - Graph data structures (GraphNode, GraphEdge, KnowledgeGraph)
  - Python dependency extraction using AST
  - Graph serialization to JSON format
  - Basic graph query capabilities
- Multi-language support infrastructure
  - Tree-sitter integration for JavaScript, TypeScript, Java, C/C++
  - Regex-based fallback parsing
  - Language detection and routing
- CLI enhancements
  - Graph-related command-line options
  - Verbose logging improvements
  - Better error messages and validation

### Changed

- Improved Python AST parsing with better error handling
- Enhanced output formatting for better NotebookLM compatibility
- Updated configuration system with graph-specific options
- Restructured documentation for better user experience
- Enhanced CLI with additional query commands and options

- Refactored FileProcessor for better modularity
- Improved chunking algorithms for semantic preservation
- Enhanced configuration validation
- Updated dependency management

### Fixed

- Format chunk method to handle list-type content properly
- Tree-sitter version compatibility issues with automatic fallback to regex parsing
- Memory usage optimization for large codebases
- Encoding issues with non-UTF8 files
- Graph serialization and deserialization edge cases

- Various parsing edge cases
- Memory leaks in large file processing
- File encoding detection issues
- Skip pattern matching inconsistencies

## [0.1.0] — date not recorded

### Added

- Initial release of Pyragify
- Python file processing with AST-based parsing
- Basic multi-language support (JavaScript, TypeScript, Java, C/C++, Markdown, HTML, CSS)
- Semantic chunking for code files
- NotebookLM-compatible output formatting
- YAML configuration system
- CLI interface with comprehensive options
- File hashing for incremental processing
- Basic documentation and examples

### Features

- Process Python functions, classes, and imports
- Extract docstrings and code structure
- Generate syntax-highlighted output
- Support for custom skip patterns and file size limits
- Parallel processing for improved performance
- Comprehensive metadata generation

---

## Development Versions

### [0.0.1-alpha] — date not recorded

- Initial prototype
- Basic Python file processing
- Simple CLI interface
- Proof of concept for NotebookLM integration

---

## Version History Notes

### Semantic Versioning

Pyragify follows semantic versioning:

- **MAJOR** version for incompatible API changes
- **MINOR** version for backwards-compatible functionality additions
- **PATCH** version for backwards-compatible bug fixes

### Release Frequency

- Major releases: When significant new features are added
- Minor releases: Monthly for feature additions and improvements
- Patch releases: As needed for bug fixes

### Support Policy

- Latest major version receives active support
- Previous major version receives security updates for 6 months
- Older versions are community-supported

---

## Contributing to Changelog

When contributing to Pyragify:

1. **Keep entries concise** but descriptive
2. **Group related changes** together
3. **Use consistent formatting** for similar entries
4. **Include issue/PR references** when applicable
5. **Test changes** before documenting

### Entry Format

```markdown
### Added
- New feature description ([#123](https://github.com/ThomasBury/pyragify/pull/123))

### Changed
- Modified existing functionality for better performance

### Fixed
- Resolved issue with file encoding detection
```

---

For the most up-to-date information, check the [GitHub Releases](https://github.com/ThomasBury/pyragify/releases) page.
