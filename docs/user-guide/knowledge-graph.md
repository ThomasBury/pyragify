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

Python call resolution checks lexical bindings before choosing a local definition.
Parameters, imports, assignments (including later assignments in a function),
and other bindings block a same-named function. Reassigned or uncertain callable
values stay unresolved. Nested scopes respect `global` and `nonlocal`; methods
do not treat class-body names as enclosing local variables.

Calls in function defaults, keyword-only defaults, and decorators belong to the
containing execution scope, including for async functions. Module-level
definition expressions belong to the file; class-body expressions belong to the
class. Function bodies belong to their function. Source lines and UTF-8 byte
columns in metadata preserve this ownership through serialization and caching.
Lambda and comprehension bindings are isolated, but calls inside them are
grouped under the nearest named execution owner rather than separate graph nodes.
This is static analysis: it does not simulate execution order or runtime rebinding.

Python file dependencies and imported calls share exact module-path matching at
the repository root or under `src/`, including package initializers and relative
imports. Calls resolve explicit function imports and aliases (`from b import run
as execute; execute()`), module imports (`import b as mod; mod.run()`), and direct
submodule imports (`import pkg.b; pkg.b.run()`). The selected import must be visible
in the call's lexical scope; a parameter or assignment that shadows it prevents
resolution. Imported targets must be unambiguous module-level functions;
names with repeated bindings remain unresolved.

Resolution retargets individual call edges. Import edges and file dependencies
remain separate, and unrelated calls sharing an unresolved placeholder keep their
own targets. Serialized graphs preserve import evidence and scope positions;
cached per-file graphs are resolved against the current repository definitions.

Ambiguous module paths or definitions, wildcard imports, re-export chains, custom
import roots, dynamic imports, and dynamic receiver types stay unresolved.
JavaScript module resolution is unsupported. The exporter does not pick a
definition in another file merely because its name matches. Runtime execution
and changes to module attributes are not simulated.

JavaScript and TypeScript arrows directly assigned to a variable keep that name:
`const run = () => work()` creates a `run` symbol and records its call to `work`.
Async arrows and both expression and block bodies use the same rules. Nested
symbols include their enclosing functions or classes. Anonymous callbacks use
`anonymous@line:column`, with a one-based line and zero-based UTF-8 byte column;
their IDs are deterministic for unchanged source and change when they move.

Parser ancestry and byte positions identify each caller and enclosing symbol,
including multiple definitions and calls on one line. Calls inside callbacks
belong to the callback; surrounding calls remain with their enclosing function
or file. Function expressions and methods have their own execution owners so
they cannot lend their calls to a neighboring arrow.

Direct identifier calls resolve only an unambiguous lexical function declaration
or direct variable-bound arrow in the same file. Parameters, destructuring,
imports, local declarations, and writes block unrelated same-named definitions.
Block bindings stay within their blocks; `var` bindings belong to the function.
Repeated declarations and reassigned values remain unresolved. Aliases,
assignment-bound or object-property arrows, member calls, and JavaScript module
calls are not resolved. TypeScript namespaces isolate bindings, but namespace
and receiver lookup are unsupported. This analysis does not simulate execution
order, dynamic scope changes, or runtime callable values.

Related-context queries return names and relationships, not source excerpts.
Relevance scores are traversal heuristics; retrieval quality has not been measured.
Each query builds an adjacency map in edge order and traverses with a deque.
The map exists only for that invocation, so subsequent queries see graph mutations.
Export dependency resolution shares a file/import index within that resolution
pass; it does not maintain an index between exports.

Export relationship filtering, GraphML, compression, visualization, and
configuration controls for repair or resolution are not implemented.
Graph-enabled processing rejects unsupported settings.

See [Configuration](../getting-started/configuration.md) for safe paths, ignore
rules, cache behavior, and export failure handling.

## Synthetic performance benchmark

The M7 benchmark uses **1,000 Python files, 100 lines and 10 functions per file**
(100,000 lines total). Functions call local definitions and explicitly imported
functions in the next module. The corpus is deterministic and is never executed.
It produced 12,000 nodes and 32,000 edges before and after optimization.
This is a synthetic workload; the original reported workload was not recorded
and these measurements do not reproduce it or establish retrieval quality.

Run the development harness from the repository root, using a new directory:

```bash
uv run --locked python scripts/benchmark_graph.py /tmp/pyragify-before --workers 4
# Apply the change being measured, then compare with the same protocol.
uv run --locked python scripts/benchmark_graph.py /tmp/pyragify-after --workers 4 \
  --compare /tmp/pyragify-before/results.json
```

The harness uses only the standard library and the installed project. It requires
a Unix-like system for process resource measurements. It runs five graph-enabled/
disabled pairs for each cache state, alternating graph order between pairs.
Outputs remain outside the corpus, and every export verifies the same selected
source bytes, hashes, and manifest mappings. Empty application caches are labeled
cold; filesystem and OS caches are not flushed. Reused runs must reuse all 1,000
records. Export timings include processor initialization, cache loading, and
publication, excluding interpreter startup, imports, profiling, and verification.

Queries use 20 fixed imported entrypoints (`function_0` in every fiftieth module),
depth 2, and no relationship filter. Each query warms up once, then runs 30 times
in a rotating order. Reported query timings include adjacency construction;
JSON decoding and graph model construction are measured separately, five times
each. Percentiles use the nearest-rank method. Graph fingerprints include both
canonical contents and original edge order; ordered query results must match
before and after. A faster result with different contents fails the harness.

The harness saves raw samples, source/revision/environment fingerprints, counts,
parent export profiles, a profile of ten representative worker extractions, and
a query profile. Parent profiles alone omit worker extraction costs; profiler
timings are used to locate work, not as export latency measurements.

### Measurements on 2026-11-10

Measured on Linux 6.8 x86-64, an Intel Core i5-7300U, Python 3.12.7, and four
configured workers. Baseline is the corrected M6 working tree; candidate adds
only M7's query and export indexes. Both share base revision `196ba90`; source
hashes identify the uncommitted code actually measured. Full environment details,
per-export samples, per-query median/p95 and samples, fingerprints, and selected
profile counters are in the [measurement record](../benchmarks/m7.json).

Export seconds, shown as **median [minimum, maximum]** over five runs:

| Application cache | Graph | Before | After |
| --- | --- | --- | --- |
| Empty | Disabled | 3.631 [2.795, 4.450] | 3.545 [3.288, 4.994] |
| Empty | Enabled | 24.615 [18.858, 25.549] | 20.055 [16.248, 25.488] |
| Reused | Disabled | 1.379 [1.348, 2.356] | 1.599 [1.140, 1.942] |
| Reused | Enabled | 16.025 [14.361, 17.710] | 12.045 [10.784, 15.851] |

Graph-enabled medians fell by **18.5% with empty caches** and **24.8% with reused
caches**. Runs were sequential on a shared development machine; cold ranges
substantially overlap, so the cold median alone does not establish a repeatable
speedup. The reused-cache results and the resolved scan in profiling support
retaining the bounded export change. Graph-disabled variation is a control for
noise, not an improvement attributed to this change.

Query and loading milliseconds, reported separately:

| Measurement | Before | After |
| --- | --- | --- |
| Query median | 76.7 | 23.8 |
| Query p95 | 121.5 | 84.8 |
| JSON read/decode median | 475.3 | 387.8 |
| Graph model construction median | 239.2 | 185.9 |

The query median improved **69.0%**, including map construction. Loading code
was unchanged; its differing measurements illustrate environmental variation
and are not an optimization claim.

The representative query's peak traced allocation increased from **11.4 KiB to
1.68 MiB** because adjacency stores edge references for the whole graph. This
allocation is temporary and grows with graph size. Median parent peak RSS stayed
about **130 MiB for cold graph exports** and **136 MiB for reused graph exports**.
Raw records also report the largest completed child's peak RSS; neither measure
is the sum of concurrent worker memory, and tracing excludes the already loaded
graph. No full process-pool peak-memory claim is made.

Profiling identified 1,000 dependency queries scanning the aggregate graph
(4.005 s cumulatively). Sharing the import/file index reduced the corresponding
resolution helper to 0.021 s; the entire resolution pass fell from 4.619 s to
0.581 s under profiling. These are diagnostic profile times. JSON serialization
remains the larger export cost and was left unchanged. A separate profile of ten representative
per-file worker extractions covers AST analysis and graph serialization that a
parent-only profile misses.

Canonical graph contents, original edge order, and all ordered query results
matched before/after; every fresh and reused export preserved source bytes,
hashes, and manifest mappings. This measures this corpus and these entrypoint
queries on one machine. It establishes no general repository latency, historical
performance target, or LLM answer-quality guarantee.
