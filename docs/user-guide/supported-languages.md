# Supported Languages

Language-aware extraction selects symbols or sections. It does not yet provide
a complete, non-overlapping copy of every supported source file. Inspect output
before using it as a repository handoff.

| Language | Parser | Readable output and limits |
| --- | --- | --- |
| Python | Standard library AST | Partial: functions, async functions, classes, and comments. Imports, module-level assignments, decorators, and other statements can be omitted; nested bodies can appear more than once. |
| JavaScript / TypeScript | Tree-sitter | Partial: selected functions, classes, and arrow functions. Whole-file fallback when extraction yields no chunks. |
| Java | Tree-sitter | Partial: selected methods and classes; whole-file fallback when no chunks are found. |
| C / C++ | Tree-sitter | Partial: selected functions, structs, and classes; whole-file fallback when no chunks are found. |
| Go | Tree-sitter | Partial: selected functions and types; whole-file fallback when no chunks are found. |
| Markdown | Heading/fence matching | Heading sections and their content. |
| HTML | Regular expressions | Partial: scripts and styles when present; otherwise whole-file content. |
| CSS | Regular expressions | Partial: selected rules. |
| Other text | Direct read | Whole-file content in a generic chunk. |

Binary files, symlinks, ignored paths, and oversized source files are excluded
before extraction. The word target does not yet split an oversized single chunk.

Graph extraction is separate from readable output: an import-only Python file
can have import edges while contributing no readable chunks. Python, JavaScript,
TypeScript, Java, C, and C++ have dependency extractors; other languages primarily
have file and containment nodes. Resolution remains experimental.

Tree-sitter and its bundled grammars must use compatible versions. Repository
development uses `uv sync --locked`; do not upgrade the parser independently of
the declared dependency constraints. Fallbacks are limited and do not guarantee
complete extraction after a parser error.
