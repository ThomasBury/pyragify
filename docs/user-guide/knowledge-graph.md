# Knowledge Graph

The optional graph records file nodes, extracted symbols, and relationships.
It is experimental: its structural checks do not prove that all relationships
are correct, and graph data is separate from the readable source chunks.

## Build and query

```bash
pyragify process-repo --repo-path ./my-project --output-dir ./output --enable-graph
pyragify query-graph --graph-path output/graphs/repository_graph.json --command stats
pyragify query-graph --command hierarchy --entity A.run
pyragify query-graph --command dependencies --entity src/app.py
pyragify query-graph --command related --entity 'src/app.py::A' --depth 2
```

Relative graph output directories are resolved under the text output directory.
When using another output location, pass its graph path to every query.
Graphs are stored as JSON with `nodes`, `edges`, and `metadata` fields. See the
[CLI reference](cli-reference.md) for query options.

## Entity identity

Symbols include their enclosing scopes. Methods `A.run` and `B.run` remain
separate even when defined in the same file. Repeated or unnamed chunks receive
unique IDs. Hierarchy queries accept bare names, qualified names, or node IDs;
a bare name can return multiple locations.

## Relationships and limits

The graph can record containment, imports, calls, inheritance, includes, and
cross-file references. Available relationships depend on the language parser.
Files with no semantic chunks still have file nodes and can have import edges.

Cross-file edges require explicit imports. Python dependencies resolve exact
module files and package initializers at the repository root or under `src/`,
including relative imports. Custom import roots, runtime imports, and dynamic
receiver types are unresolved. The exporter does not pick a definition in
another file merely because its name matches.

Related-context queries return names and relationships, not source excerpts.
Relevance scores are traversal heuristics; retrieval quality and performance on
large repositories have not been measured. Relationship filtering, GraphML,
compression, visualization, and configuration controls for repair or resolution
are not implemented. Graph-enabled processing rejects unsupported settings.

See [Configuration](../getting-started/configuration.md) for safe paths, ignore
rules, cache behavior, and export failure handling.
