# Pyragify review and focused improvement plan

Reviewed on 2026-11-04 against the working tree, including existing uncommitted changes. The review below records the starting state. Milestone completion and current verification are recorded in the implementation sequence.

**What this repo does:** Pyragify turns local repository files into language-grouped text chunks and an optional JSON graph of code relationships. It also exposes graph queries through a CLI. This review assumes one developer exporting a small or medium local repository, including ordinary ignored environments and generated files.

## Recommendation

Focus on one job: **produce a trustworthy repository handoff that a developer can inspect and an LLM can cite**. Preserve the source, show where it came from, and explain what was excluded or failed.

Do not expand the graph platform. The current graph can invent relationships, and the exporter can lose source content. Those problems matter more than additional languages, visualizations, retrieval algorithms, or integrations.

There is not yet evidence that Pyragify needs its own general repository packer. Compare the intended handoff against Repomix before investing further in export features. If Repomix meets the requirements, document that workflow and retire the overlapping implementation instead of wrapping it under a second CLI.

## Current status

- Package version: `0.2.0`; branch: `feat-knowledge-graph-docs`.
- The starting tree had 12 modified tracked files and one new graph test file. Existing work was preserved.
- `uv run --locked pytest -q`: **40 passed**, using Python 3.12.7.
- `uv run --locked --group docs mkdocs build --site-dir /tmp/pyragify-review-site`: passed. MkDocs reported API pages outside navigation and an unresolved relative LICENSE link.
- A complete CLI export of this repository processed 39 files and produced text and graph artifacts. It also failed to serialize its cache while returning success. Generated review artifacts are under `/tmp/pyragify-review-export`.
- Existing tests cover useful fixes: CLI configuration overrides, real parser execution, cached text preservation, deleted files, output exclusion, and simple same-file call hierarchies. They do not establish source completeness, correct cross-file resolution, or successful graph-cache reuse.
- The PRD's coverage, large-repository performance, compression, and completion claims are not supported by the checks performed here. For example, it simultaneously lists compression as unfinished and completed. Treat it as an outdated proposal, not a status report.

## Must fix

### 1. Output cleanup can delete source files

**What this is:** The exporter removes old `chunk_*.txt` files before rebuilding output. See [processor.py](src/pyragify/processor.py), `_clear_managed_chunk_files` at line 916 and `_write_text_output` at line 944.

**Problem:** With the repository itself as `output_dir`, a synthetic source file `python/chunk_7.txt` was deleted. That configuration is accepted today.

**Fix:** Reject output equal to, or an ancestor of, the repository before writing. Reject unsafe symlinked output locations and limit cleanup to artifacts the exporter owns. Keep a valid prior export until its replacement has been written successfully.

**If skipped:** An otherwise normal export can destroy a user's files.

### 2. File selection crosses the intended repository boundary

**What this is:** Discovery uses recursive filesystem enumeration and reads only root ignore files. See [processor.py](src/pyragify/processor.py), `load_ignore_patterns` at line 972 and `should_skip` at line 1002.

**Problem:** A file excluded by `private/.gitignore` was accepted. A repository symlink to a synthetic text file outside the repository was also accepted, and its contents were exported.

**Fix:** Skip file symlinks by default and honor nested ignore rules. Prefer native Git file discovery for Git repositories; define and test the directory-only fallback. Exclude generated outputs consistently, including separately configured graph output. Avoid traversing ignored trees just to discard their contents later.

**If skipped:** A bundle intended for upload can contain private or unrelated files. Ignore support alone is not secret detection; reuse an existing scanner if that workflow is required.

### 3. Graph loading corrupts the data used to save the cache

**What this is:** [graph.py](src/pyragify/graph.py), `KnowledgeGraph.from_dict` at line 193, loads graphs for repository aggregation, graph-file loading, and CLI queries.

**Problem:** It assigns the input metadata dictionary directly, then changes its `languages` value to a set. Repository aggregation therefore mutates the cached JSON records. The complete CLI run left invalid JSON in `.pyragify-cache.json` with `Object of type set is not JSON serializable`.

**Fix:** Copy metadata before normalizing it. Add a regression that loads a graph without changing its input, and a two-run graph test that proves unchanged files bypass processing rather than merely reappear in output.

**If skipped:** Graph-enabled runs cannot persist a usable cache and repeat parsing on subsequent runs.

### 4. Semantic extraction omits essential source content

**What this is:** [processor.py](src/pyragify/processor.py), `chunk_python_file` around line 408, emits selected definitions rather than a complete source partition.

**Problem:** A fixture lost imports, constants, decorators, and an async function. A class method appeared twice because it was emitted both inside its class and separately. A Python file containing only imports and constants produced zero chunks. Other language handlers also select only parts of files.

**Fix:** Make retained source text complete and non-overlapping. The smallest reliable baseline is whole-file content or contiguous source ranges; extracted symbols should be metadata over that text. On parse failure, preserve the file and report the parser limitation.

**If skipped:** LLMs receive incomplete code and waste context on duplicated bodies. Developers cannot use the output as a faithful record.

### 5. Non-ASCII text corrupts tree-sitter excerpts

**What this is:** The extractor uses byte offsets to slice Python strings. See [processor.py](src/pyragify/processor.py), line 662, and the capture handlers in [graph.py](src/pyragify/graph.py).

**Problem:** With `// café 🐍` before a JavaScript function, the exported function started with `tion foo()` instead of `function foo()`.

**Fix:** Extract from the parser node's UTF-8 bytes, or slice the original bytes and decode. Apply the same correction to dependency captures; test Unicode before a definition and before an import/call.

**If skipped:** Ordinary international comments can produce invalid code and wrong symbol names.

### 6. Graph identity and resolution produce false relationships

**What this is:** Nodes use `file::name` identities, and cross-file resolution chooses a definition by bare name. See [graph.py](src/pyragify/graph.py), lines 404, 984, and 1037.

**Problem:** `A.run` and `B.run` in one file collapsed into one node with both methods' callees. In another fixture, `from b import run` followed by `run()` created a cross-file reference to `a.py`; the dependency query returned no dependency for that import.

**Fix:** Freeze expansion and label the graph experimental. If retained, use qualified scopes and source locations for identities, and resolve only relationships supported by explicit import/scope evidence. Preserve unresolved references as unresolved; do not turn a matching name into a fact.

**If skipped:** Human reviewers and LLMs can confidently follow the wrong code. A graph passing structural validation does not prove its relationships are true.

### 7. Failure is reported as success

**What this is:** [processor.py](src/pyragify/processor.py), `save_json` and `load_json`, log failures without propagating them; callers continue.

**Problem:** Making `metadata.json` an unwritable destination by placing a directory there produced exit code 0 with no metadata file. Querying malformed graph JSON returned exit code 0 and empty graph statistics. The real cache failure in finding 3 also returned success.

**Fix:** Treat required artifact-write failures and malformed query inputs as errors. Distinguish optional missing cache state from an invalid user-supplied graph. Write JSON to a temporary file and replace the destination only after successful serialization. Report per-file failures separately from intentional exclusions.

**If skipped:** Automation cannot distinguish a valid export from incomplete or corrupt results.

### 8. The advertised output limit is not an upper bound

**What this is:** [processor.py](src/pyragify/processor.py), `save_chunk` at line 1057, flushes the previous buffer but does not handle an oversized single chunk.

**Problem:** A 100-word input with `max_words=20` produced a 112-word output file after formatting.

**Fix:** Validate a positive limit and account for headers. Split oversized content with source-range continuity, or fail explicitly when an indivisible piece cannot fit. Keep words clearly distinct from model tokens.

**If skipped:** Files can exceed the limits users selected for their downstream tool.

## Should fix

### 9. Configuration and documentation promise inactive features

**What this is:** [cli.py](src/pyragify/cli.py), lines 43–44, exposes graph format and relationship controls; [config.yaml](config.yaml) and [PRD.md](PRD.md) add further promises.

**Problem:** Requesting GraphML still produced JSON. Requesting only imports still produced calls. Compression is advertised without a corresponding output implementation. The graph's related-context CLI output contains names and relationships, not source excerpts.

**Fix:** Remove unsupported options and claims or reject their use explicitly. Do not implement them simply to catch up with the PRD. Replace performance and quality claims with measured results and documented limits.

**If skipped:** Users cannot tell what the tool actually does or trust configuration choices.

## Target users and the useful output

The primary user is a developer handing repository context to an LLM that cannot read the working tree. The secondary user is a teammate reviewing or learning the same code. Both need the same evidence; they do not require separate products.

The proposed handoff has two parts, generated from the same selected source snapshot:

| Output | Useful content | Consumer |
| --- | --- | --- |
| Readable Markdown bundle, split only when needed | File index, exact source excerpts, paths and line ranges, links within the bundle, explicit omissions | Developers, chat tools, document ingestion |
| Small JSON manifest, evolving existing metadata | Source hashes, output-part mapping, counts, included/excluded/failed files, parser limitations, format version | Scripts and verification |

The human index should help answer “where is this defined?” and “what did this export leave out?”. Do not generate speculative architecture descriptions, arbitrary relevance scores, or an interactive graph viewer. Unsupported languages can remain readable source text; structural guarantees should initially be limited to Python and Markdown if custom extraction remains necessary.

## Reuse before building

| Need | Existing solution | Decision |
| --- | --- | --- |
| Repository packaging, readable formats, line numbers, output splitting and token counts | [Repomix CLI](https://repomix.com/guide/command-line-options), [output formats](https://repomix.com/guide/output) | Evaluate against the handoff contract before adding an exporter or tokenizer. |
| Common credential-pattern scanning | Repomix already integrates [Secretlint](https://repomix.com/guide/security) | Do not write a custom secret detector. |
| Ranked symbol context for an interactive coding assistant | [Aider repository maps](https://aider.chat/docs/repomap.html) | Do not recreate a graph-ranking engine. |
| API documentation and interactive code navigation | Existing MkDocs/mkdocstrings setup; developers' editors | Keep those responsibilities outside the export tool. |

These are documentation-backed comparisons, not a measured claim that another tool satisfies every requirement. No alternative package was installed or benchmarked during this review.

## Implementation sequence

Each milestone must be independently reviewable. Complete one, verify it, and stop before beginning the next.

### M1 — Safe boundaries and honest failures: implemented (2026-11-04)

Scope: findings 1, 2, 3, and 7. Touch discovery/output handling in `processor.py`, graph deserialization in `graph.py`, CLI error propagation, and the corresponding tests and safety documentation. Preserve existing working-tree changes.

- Validate source/output separation before creating or deleting files.
- Make file selection respect repository boundaries and nested ignores.
- Stop deserialization from mutating cache records.
- Preserve prior valid artifacts on failed writes and return a failing exit status for required failures.

Done when synthetic boundary cases cannot read external files or delete source, nested ignored content stays out, malformed graph queries fail, failed writes preserve previous valid artifacts, and a second graph-enabled run demonstrably reuses a valid cache. Run the full existing suite and an end-to-end CLI export. This milestone does not make graph relationships or source extraction accurate yet.

M1 implementation and verification:

- Source/output overlap and symlinked output destinations are rejected before writes.
- Git discovery and the directory fallback exclude symlinks, nested ignored content, and both output locations. The fallback prunes excluded trees; its metadata records directory exclusions.
- Graph deserialization preserves cache input. Invalid optional cache records are reprocessed; unchanged files with no extracted symbols also reuse their cache records.
- Required JSON writes propagate errors and replace files only after serialization. Exports stage all artifacts and restore previous contents on ordinary publication failures. Cleanup removes only chunks listed in `.pyragify-artifacts.json`.
- Source processing failures abort publication and are distinguished from exclusions. Malformed graph queries fail.
- `uv run --locked pytest -q`: **64 passed**, including boundary, failure injection, cache reuse, and empty-file regressions.
- `uv run --locked --group docs mkdocs build --site-dir /tmp/pyragify-m1-site`: passed, with the existing navigation and LICENSE-link notices.
- Two real graph-enabled CLI exports processed **41 files**; the second reused **all 41 cache records**, launched no fresh workers, and preserved the **953-node** graph. Verified output: `/tmp/pyragify-m1-verified-5fnuddz9`.
- `git diff --check`: passed. Existing working-tree changes were preserved.

Limits: publication rollback covers raised errors, not process termination or power loss; concurrent exports into the same directories are unsupported. Legacy unlisted chunks are left for manual inspection. File selection is not secret detection. Source completeness and graph relationship accuracy remain unresolved for M2 and finding 6.

PR review follow-up (2026-11-04):

- UTF-8 sampling preserves complete characters across the binary-detection boundary.
- Graphs include empty and import-only files. Scoped entity IDs keep same-named methods and nested functions separate; unresolved receivers are left unresolved.
- Python package dependencies use exact root or `src/` module paths, including relative imports. Cross-file edges now require explicit imports instead of matching bare symbol names.
- Cache format version 2 invalidates older extraction records. `uv run --locked pytest -q`: **82 passed**; the documentation build also passed with the existing notices.

### M2 — One useful handoff, with a reuse decision first: next milestone

First compare Repomix against this repository, one small Python application, and a mixed-language fixture containing Unicode and deliberately oversized files. Check retained source, provenance, file selection, readable navigation, and limits. Record concrete unmet requirements.

If Repomix already supplies the needed handoff, document the supported workflow and propose retiring the duplicate packer. Do not create a forwarding wrapper. If a material gap remains, implement only that gap using the existing processor/metadata where practical, Python's standard library, and installed dependencies.

For any retained custom exporter, address findings 4, 5, and 8; produce the two outputs above; bump the cache version when extraction changes; and correct finding 9 across README, configuration, CLI help, and the affected docs. Keep graph output experimental and outside the trusted handoff until finding 6 is resolved. Do not broaden graph scope in this milestone.

Done when every included source range is present once and traceable, imports/decorators/async code/Unicode survive, oversized input follows the documented limit policy, clean and incremental runs agree, deleted files disappear, and a developer can locate a definition and understand omissions from the bundle alone. The readable output and manifest must agree. No LLM-quality percentage should be claimed without a separate evaluation.

## Scope cuts and verification limits

Defer graph visualization, GraphML, more language-specific analysis, embeddings, vector stores, chat servers, IDE plugins, ML pattern recognition, automatic architecture narratives, and extra export formats. There is no demonstrated need for these in the handoff workflow.

Small cleanup can wait: `load_yaml_config`, `is_documentation_file`, and `read_file_in_chunks` have no runtime callers in this repository. Removing their definitions would remove **84 source lines, 0 runtime dependencies**; related tests/docs and possible external API users would need review. This is not the next milestone.

**Verdict:** The existing fixes are useful, but passing tests currently hide source-loss, data-boundary, cache, and graph-accuracy bugs. Fix safe operation first, then earn any further custom export work through the reuse comparison.

**Not checked:** Published package behavior, live CI history, supported-Python-version matrix, clean wheel installation, large-repository load, external-tool execution, actual NotebookLM ingestion, or LLM answer quality. Documentation was inspected selectively and built, not exhaustively verified. No implementation, dependency, commit, or publishing changes were made during this review.
