# Changelog

All notable changes to Pyragify will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2024-01-XX

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

### Changed

- Improved Python AST parsing with better error handling
- Enhanced output formatting for better NotebookLM compatibility
- Updated configuration system with graph-specific options
- Restructured documentation for better user experience
- Enhanced CLI with additional query commands and options

### Fixed

- Format chunk method to handle list-type content properly
- Tree-sitter version compatibility issues with automatic fallback to regex parsing
- Memory usage optimization for large codebases
- Encoding issues with non-UTF8 files
- Graph serialization and deserialization edge cases

## [Unreleased] - Development

### Planned for v0.3.0

- Graph visualization interface
- Advanced query language for complex analysis
- Plugin system for custom parsers
- Integration with popular IDEs
- Machine learning-based code pattern recognition

## [0.2.0] - 2024-01-XX

### Added

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

- Refactored FileProcessor for better modularity
- Improved chunking algorithms for semantic preservation
- Enhanced configuration validation
- Updated dependency management

### Fixed

- Various parsing edge cases
- Memory leaks in large file processing
- File encoding detection issues
- Skip pattern matching inconsistencies

## [0.1.0] - 2024-01-XX

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

### [0.0.1-alpha] - 2024-01-XX

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

## Future Roadmap

### Planned for v0.3.0

- Enhanced tree-sitter support with version compatibility fixes
- Graph visualization interface
- Advanced query language for complex analysis
- Plugin system for custom parsers
- Integration with popular IDEs

### Planned for v0.4.0

- Machine learning-based code pattern recognition
- Automated documentation generation
- Code quality analysis integration
- Support for additional languages (Go, Rust, Ruby)

### Long-term Vision

- Real-time code analysis during development
- Integration with CI/CD pipelines
- Advanced refactoring suggestions
- Cross-repository analysis capabilities

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
