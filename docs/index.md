# Pyragify

Pyragify exports local repository source as Markdown with a provenance manifest.
Each selected UTF-8 file appears once, without semantic extraction or whitespace
normalization. The index links to source blocks and lists intentional omissions.

```bash
pyragify process-repo --repo-path ./my-project --output-dir ./output --no-enable-graph
```

Open `output/index.md`, then inspect the source parts and `metadata.json` before
sharing them. Ignore rules are not secret detection. Source read failures and
word-limit violations fail the export before publication.

Start with the [quick start](getting-started/quick-start.md),
[configuration](getting-started/configuration.md), and
[output contract](user-guide/output-formats.md). The
[Repomix comparison](user-guide/repomix-comparison.md) explains the remaining
reason for a custom exporter.

[Knowledge graphs](user-guide/knowledge-graph.md) are a separate, experimental
output. They may omit or misidentify relationships. Source retention does not
require their parsers. NotebookLM ingestion, LLM answer quality, and
large-repository performance have not been evaluated.

For development, see [contributing](contributing.md) and the
[API reference](reference/pyragify/index.md).
