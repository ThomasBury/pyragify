# Pyragify

<div align="center">

**Transform your code repositories into LLM-ready context for NotebookLM and other AI assistants.**

[![PyPI version](https://badge.fury.io/py/pyragify.svg)](https://pypi.org/project/pyragify/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

[📖 Full Documentation](https://thomasbury.github.io/pyragify/) • [🐛 Issues](https://github.com/ThomasBury/pyragify/issues) • [💡 Discussions](https://github.com/ThomasBury/pyragify/discussions)

</div>

## ✨ What is Pyragify?

Pyragify transforms code repositories into structured, LLM-ready context. It processes multiple programming languages, extracts semantic relationships, and creates manageable chunks optimized for AI analysis with tools like NotebookLM.

## 🚀 Key Features

- **🔍 Knowledge Graph**: Build comprehensive graphs of code relationships
- **🌍 Multi-Language Support**: Python, JavaScript, TypeScript, Java, C/C++, and more
- **🎯 Semantic Chunking**: Preserve context and relationships for better AI analysis
- **📊 Query Interface**: Explore your codebase with powerful graph queries
- **⚡ High Performance**: Parallel processing with incremental updates
- **📱 NotebookLM Ready**: Optimized output format for seamless AI integration

## 🚀 Quick Start

### Install

```bash
# Using uv (recommended)
uv pip install pyragify

# Using pip
pip install pyragify
```

### Basic Usage

```bash
# Process your repository
pyragify process-repo --repo-path ./my-project --enable-graph

# Query the knowledge graph
pyragify query-graph --command stats
pyragify query-graph --command related --entity "src/main.py::MyClass"
```

## 📖 Documentation

📚 **[Full Documentation](https://thomasbury.github.io/pyragify/)** - Complete guides, tutorials, and API reference

**Popular Sections:**

- [Installation Guide](https://thomasbury.github.io/pyragify/getting-started/installation/)
- [Configuration Reference](https://thomasbury.github.io/pyragify/getting-started/configuration/)
- [CLI Reference](https://thomasbury.github.io/pyragify/user-guide/cli-reference/)
- [Knowledge Graph Guide](https://thomasbury.github.io/pyragify/user-guide/knowledge-graph/)

## 🎯 Perfect For

- **Code Analysis** - Understand complex codebases quickly
- **AI Integration** - Prepare code for LLM analysis with NotebookLM
- **Code Review** - Analyze relationships and dependencies
- **Documentation** - Generate comprehensive API docs
- **Onboarding** - Help new team members understand the codebase

## 🤝 Contributing

We welcome contributions! See our [Contributing Guide](https://thomasbury.github.io/pyragify/contributing/) for development setup, code style guidelines, and how to submit pull requests.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<div align="center">

**Ready to transform your codebase?** [Get started!](https://thomasbury.github.io/pyragify/getting-started/quick-start/)

</div>
