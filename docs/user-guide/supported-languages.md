# Supported Languages

The handoff retains complete UTF-8 source without parsing, for every selected
text file. Python, Markdown, JavaScript, TypeScript, Java, C/C++, Go, HTML, CSS,
and other text have the same source-completeness contract. Language names only
choose output subdirectories and code-fence labels.

Imports, decorators, async definitions, constants, comments, whitespace, and
Unicode are copied verbatim. Malformed code is retained too. Empty files have
source range `0–0`; nonempty files use one-based inclusive line ranges.

Binary or non-UTF-8 files, symlinks, ignored paths, and sources above
`max_file_size` are excluded and reported. Source decoding failures after the
binary sample abort publication. A whole source file that cannot fit
`max_words`, including formatting, fails rather than being truncated or omitted.
See [selection rules](../getting-started/configuration.md) and
[output details](output-formats.md).

## Experimental graph extraction

Graphs still use the existing language-specific extractors: Python AST,
Tree-sitter for supported code languages, Markdown heading matching, and limited
HTML/CSS extraction. These can omit symbols and relationships. The manifest
reports that limitation when graphs are enabled. A failed parser cannot remove
source from the readable handoff.

Official Tree-sitter bindings and the eight individual grammar packages are
installed at pinned compatible versions on Python 3.12. Repository
development uses `uv sync --locked`; do not upgrade the parser independently of
the declared dependency constraints. See the [graph guide](knowledge-graph.md).
