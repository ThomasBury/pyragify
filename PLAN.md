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

Second PR review follow-up (2026-11-05):

- Graph-enabled runs validate all cached graph records, including empty chunks after an earlier graph-disabled run.
- Tree-sitter code and reference text come from UTF-8 node bytes. JavaScript imports keep source modules and the original statement; default, namespace, and side-effect imports are included. System C/C++ includes survive other edges.
- Unnamed chunk IDs remain unique after repeated collisions. Dependency queries build their file index once per call. Cache version 3 invalidates older parser records.
- The worker return annotation supports Python 3.9. **95 tests passed on Python 3.12.7 and Python 3.9.25**.
- Inactive graph settings are rejected; configuration examples now use supported settings. Documentation corrects CLI syntax, installation groups, partial extraction, license metadata, generated edit paths, and unsupported project-status claims.
- The test workflow token has read-only contents access. The docs build passes; API pages outside navigation remain informational notices, and the broken LICENSE link is fixed.

Third PR review follow-up (2026-11-05): inheritance edges originate at each scoped subclass, and context traversal carries the actual edge type in either direction, including filtered parallel edges. **98 tests pass on Python 3.9 and 3.12**.

Final CodeRabbit follow-up (2026-11-05): text queries include relationship paths; invalid search regular expressions fail instead of returning empty success. Development setup respects the activated environment, cache removal follows the configured output directory, and installation instructions distinguish source checkouts. **100 tests pass on Python 3.9 and 3.12**, and the docs build passes. Codex cleared commit `7492b2a` before this follow-up; the final head is submitted for another review.

### M2 — One useful handoff, with a reuse decision first: implemented (2026-11-05)

First compare Repomix against this repository, one small Python application, and a mixed-language fixture containing Unicode and deliberately oversized files. Check retained source, provenance, file selection, readable navigation, and limits. Record concrete unmet requirements.

If Repomix already supplies the needed handoff, document the supported workflow and propose retiring the duplicate packer. Do not create a forwarding wrapper. If a material gap remains, implement only that gap using the existing processor/metadata where practical, Python's standard library, and installed dependencies.

For any retained custom exporter, address findings 4, 5, and 8; produce the two outputs above; bump the cache version when extraction changes; and correct finding 9 across README, configuration, CLI help, and the affected docs. Keep graph output experimental and outside the trusted handoff until finding 6 is resolved. Do not broaden graph scope in this milestone.

Done when every included source range is present once and traceable, imports/decorators/async code/Unicode survive, oversized input follows the documented limit policy, clean and incremental runs agree, deleted files disappear, and a developer can locate a definition and understand omissions from the bundle alone. The readable output and manifest must agree. No LLM-quality percentage should be claimed without a separate evaluation.

M2 implementation and verification:

- Compared pinned Repomix **1.18.1** locally against this repository, a small Python application, and a mixed-language fixture with Unicode, embedded Markdown fences, and an oversized file. The reproducible assertion harness is [scripts/compare_repomix.py](scripts/compare_repomix.py); observations and the reuse decision are in [the comparison report](docs/user-guide/repomix-comparison.md).
- Repomix preserved ordinary source after outer-whitespace normalization, respected the tested nested ignore and external symlink, and failed explicitly when an indivisible file exceeded its split limit. Its JSON output removed the source's final newline and supplied no source-hash, output-part mapping, or explicit omission manifest. These are concrete unmet requirements; retain the existing narrow exporter for this gap, without a wrapper, tokenizer, or new dependency.
- The trusted handoff now uses whole-file, non-overlapping UTF-8 source blocks in `.md` parts and a linked `index.md` listing files, source ranges, hashes, omissions, and parser limitations. Imports, decorators, async code, comments, whitespace, original line endings, malformed code, and Unicode survive. Dynamic fence lengths protect embedded Markdown. Source hashes and sizes are computed from the retained bytes.
- `metadata.json` format version **1** maps each included file to its source hash, source line range, part, anchor, and exact half-open output byte range. Cache version **5** invalidates earlier extraction records; cache reuse is separate from exclusions, and corrupt cached source is reprocessed. Git-ignored paths are reported with compact directory entries; generated outputs and repository boundaries are also explained.
- `max_words` is positive and bounds every generated Markdown file, including headers and the index. Whole files are indivisible: oversized source or an oversized index fails before publication, preserving the prior handoff. Owned legacy `.txt` parts migrate to `.md`; unowned artifacts remain untouched.
- Graphs remain experimental, opt-in, and outside the trusted handoff. Existing semantic extractors serve only graphs; parser diagnostics are recorded without dropping source. README, CLI help, configuration, package description, and affected user guides describe the implemented contract. The historical PRD is explicitly marked unvalidated and archived.
- `uv run --locked pytest -q`: **113 passed** on Python **3.12.7**. `UV_PROJECT_ENVIRONMENT=/tmp/pyragify-m2-py39 uv run --locked --python 3.9 --group dev pytest -q`: **113 passed** on Python **3.9.25**.
- `uv run --locked --group docs mkdocs build --site-dir /tmp/pyragify-m2-site`: passed, with only the existing API pages outside navigation notices. `git diff --check`: passed.
- Two real graph-enabled CLI exports selected **45 files** into three source parts plus the index. Every mapped source byte range and hash matched the working tree. The second run reused **all 45 cache records**, started no fresh processing, and produced byte-identical Markdown. Artifacts: `/tmp/pyragify-m2-verified`; comparison assertion results: `/tmp/pyragify-m2-repomix-repro/results.json`.

Limits: files and the index are not split internally; users must raise the limit or deliberately reduce selection. Directory omission entries cover descendants without enumerating them. Source-only exports require no parser; experimental graph extraction can reread source independently. Whole-repository snapshot isolation, concurrent exports, crash recovery, large-repository performance, actual NotebookLM ingestion, and LLM answer quality remain unverified or unsupported as documented. No later milestone or graph expansion was started.

M2 PR review follow-up (2026-11-05): universal newline counting now handles CR-only and mixed CR/LF files without changing retained bytes. Regression cases check the source header, index, manifest, and exact byte mapping, including empty files, final line endings, and Unicode line separators inside source strings. Cache version 5 invalidates earlier cached line ranges. **123 tests pass on Python 3.9.25 and 3.12.7**; the documentation build passes with the existing API navigation notices.

### Follow-up resolution plan (2026-11-10)

This is the current task list; M1 and M2 above remain completed historical records. Implement M3–M7 in order, one independently reviewable milestone per session. Record checks and remaining limits before marking a milestone complete.

The review retained the original priorities and regression checks, clarified completion criteria, separated hosted deployment from local completion, and removed performance gates inherited from the unvalidated PRD. Agreed scope: Python import resolution, JavaScript/TypeScript arrow relationships, and measured performance improvements. Graphs remain experimental and opt-in; add no dependencies, graph services, visualization, or general runtime-analysis engine.

Reported performance at **100,000 source lines**: **18.1 s with graphs versus 8.7 s without**, or **9.4 s / approximately 108% overhead (2.08× total)**; related-context queries had a **119 ms median**. These figures have not been reproduced here. The original corpus, machine, cache state, and query settings are unknown. The archived <20% overhead and <100 ms goals remain reference points, not completion gates.

#### M3 — Repair documentation deployment: implemented (2026-11-10)

- [x] Replace the malformed folded `pip install` command in [.github/workflows/docs.yml](.github/workflows/docs.yml) with the existing uv workflow pattern: `astral-sh/setup-uv@v5`, Python **3.12**, and `uv sync --locked --group docs`.
- [x] Deploy with `uv run --locked --group docs mkdocs gh-deploy --force`. Preserve existing deployment triggers, destination, and permissions.
- [x] Execute the YAML-decoded installation command in a clean temporary environment and build the documentation with the deployment command's uv runner.

Complete when installation and documentation building pass locally. Hosted deployment verification is a separate release follow-up and does not block M4.

M3 implementation and verification:

- The workflow uses the existing locked docs dependency group instead of a duplicated pip dependency list. Python is constrained to 3.12, within the package's `<3.13` requirement.
- A temporary assert-based check parsed the actual workflow YAML, checked its Python/action settings and install/deploy argument lists, and executed the decoded install command with a fresh environment and package cache.
- `uv sync --locked --group docs`: passed on **Python 3.12.7**, installing **60 packages**. The lockfile hash was unchanged after installation and building.
- `uv run --locked --group docs mkdocs build --site-dir /tmp/pyragify-m3-cbmhrjfa/site`: passed; only the existing API pages outside navigation notices remain. The generated site contains `index.html`.
- Verification artifacts and the isolated environment are under `/tmp/pyragify-m3-cbmhrjfa`.
- All YAML-decoded shell steps pass `bash -n`; deployment triggers, permissions, and destination arguments match the original workflow. `git diff --check`: passed.

Release follow-up:

- [ ] After an authorized merge, verify the hosted docs job and published site. No deployment was performed during local verification.

#### M4 — Correct Python shadowing and call ownership: implemented (2026-11-10)

- [x] Add regressions before changing resolution: parameter shadowing, local assignment (including assignment later in a function), import shadowing, nested scopes, and `global`/`nonlocal`.
- [x] Build binding information per lexical scope before resolving calls. Parameters, assignments, imports, and other bindings prevent fallback to an unrelated function. Leave uncertain callable values unresolved.
- [x] Record call ownership during AST traversal. Visit defaults, keyword-only defaults, and decorators in the containing execution scope; visit function bodies in their own scope. Apply the same handling to async definitions.
- [x] Preserve that owner through normalization instead of replacing it using line containment. Module-level definition expressions belong to the file; nested expressions belong to the enclosing function or class body.
- [x] Retain source positions sufficient to distinguish definitions and calls sharing a line.

Complete when exact-edge assertions reject false callees and callers, while existing ordinary function, nested-function, and method relationships remain correct. Use the existing graph extraction and normalization paths in [graph.py](src/pyragify/graph.py) and [processor.py](src/pyragify/processor.py).

M4 implementation and verification:

- Added 28 initial regression cases before changing the resolver; all failed against the previous implementation. Expanded coverage to 46 cases, including positional-only/keyword-only/variadic parameters, loop/context-manager/exception/pattern bindings, rebinding, class scopes, lambdas, comprehensions, and declarations inherited by closures.
- Python extraction collects bindings before resolving calls. Shadowed names and uncertain receivers retain unresolved placeholders rather than pointing at unrelated local definitions. Existing ordinary functions, nested functions, and methods keep their scoped IDs and relationships.
- Defaults, keyword-only defaults, decorators, and function bodies record their execution owner during AST traversal, including async definitions. Normalization maps owners and definitions by source line and UTF-8 byte column rather than recomputing Python call ownership from line containment.
- Cache version **6** invalidates earlier extracted records. A regression proves JSON reload and fresh/cached graph equality, bypasses workers on reuse, rebuilds a deliberately stale version-5 cache, and checks retained source bytes, hashes, and manifest mappings with Unicode and CRLF input.
- `uv run --locked pytest -q`: **169 passed on Python 3.12.7**.
- `UV_PROJECT_ENVIRONMENT=/tmp/pyragify-m4-py39 uv run --locked --python 3.9 pytest -q`: **165 passed, 4 skipped on Python 3.9.25**. Only Python 3.10+ pattern-matching syntax cases are skipped.
- Updated the graph guide. `uv run --locked --group docs mkdocs build --site-dir /tmp/pyragify-m4-site`: passed with the existing API pages outside navigation notices. `git diff --check`: passed.
- Preserved the pre-existing documentation workflow and plan changes. No dependencies, CLI options, public signatures, or graph JSON top-level fields changed.

Limits: binding analysis does not simulate execution order or runtime callable values. Lambda/comprehension bindings are separate, but their calls share the nearest named execution owner. Imported callees remain unresolved until M5; arrow relationships and performance work remain M6 and M7. No hosted deployment or large-repository benchmark was performed.

#### M5 — Resolve imported Python calls: implemented (2026-11-10)

- [x] Resolve explicit function imports and aliases, module-qualified calls, and relative imports against definitions at the repository root or under `src/`.
- [x] Share the existing exact module-path matching between dependency queries and call resolution. Ambiguous paths remain unresolved.
- [x] Carry import bindings and lexical scope through per-file graph serialization. Reuse M4's shadowing rules.
- [x] Retarget each applicable call edge in the aggregate graph. Preserve import/file dependency edges and unrelated unresolved calls; never globally rename a shared `function::name` placeholder.
- [x] Test two modules exporting the same name, aliases, package initializers, scoped imports, and shadowing. Repeat after JSON reload, cache reuse, and changes or deletion of the imported definition.

Complete when `from b import run; run()` reaches `b.py::run`, never an unrelated `a.py::run`, and hierarchy/context queries follow the corrected edge. Wildcard imports, runtime imports, re-export chains, and JavaScript module resolution remain unsupported.

M5 implementation and verification:

- Added 39 initial cases before implementation: **25 failed, 14 passed** against M4. Expanded to **47 cases**, covering root and `src/` layouts, aliases, dotted module imports, package initializers, relative imports, nested/scoped bindings, receiver shadowing, and uncertain exports.
- Per-call metadata records the selected lexical import, its source/scope position, and the original unresolved target. File-node metadata records unambiguous module-level function bindings and names that block submodule inference. Both survive per-file JSON serialization.
- Aggregate resolution copies and retargets individual call edges, preserving per-file graphs, import edges, dependencies, and unrelated unresolved calls. Placeholder deduplication distinguishes import evidence so a shadowed lambda call cannot absorb an imported call from the same named owner. Unused external placeholders are removed only when no edge references them.
- Call resolution and dependency queries share exact module-path matching, including relative imports under `src/`. Duplicate root/src or module/package paths remain unresolved. Known package bindings take precedence over same-named submodule files.
- Cache version **7** invalidates M4 records. Regression checks prove worker-free reuse, version-6 rebuilding, JSON reload, repeated resolution, importer-cache reuse after target changes/renaming/deletion/recreation, and equality with fresh exports. Source bytes, hashes, and manifest mappings remain exact, including Unicode and CRLF input.
- Exact-edge, hierarchy, and related-context assertions prove `from b import run; run()` reaches `b.py::run`, preserving an unrelated `a.py::run` and unresolved shadowed calls.
- `uv run --locked pytest -q`: **216 passed on Python 3.12.7**.
- `UV_PROJECT_ENVIRONMENT=/tmp/pyragify-m4-py39 uv run --locked --python 3.9 pytest -q`: **212 passed, 4 skipped on Python 3.9.25**. The skips remain Python 3.10+ pattern-matching cases.
- Updated the graph guide. `uv run --locked --group docs mkdocs build --site-dir /tmp/pyragify-m5-site`: passed with the existing API pages outside navigation notices. `git diff --check`: passed.
- Preserved all preceding working-tree changes. No dependencies, CLI options, public signatures, or graph JSON top-level fields changed.

Limits: targets must be unambiguous module-level functions. Wildcards, re-export chains, dynamic imports, uncertain or repeated bindings, dynamic receivers/module attributes, custom import roots, and JavaScript module resolution remain unresolved. Execution order is not simulated. No hosted deployment or performance benchmark was performed; M6 and M7 remain untouched.

#### M6 — Correct arrow-function relationships: implemented (2026-11-10)

- [x] Recover names from direct variable-bound arrow functions using the existing JavaScript/TypeScript parser.
- [x] Use parser ancestry and source positions to identify callers and scopes. Preserve stable IDs for existing named symbols; give anonymous callbacks deterministic identities based on source position.
- [x] Resolve calls to named arrows and calls within expression/block bodies. Leave unsupported bindings and uncertain rebinding unresolved.
- [x] Test JavaScript and TypeScript with async arrows, nested arrows, anonymous callbacks, Unicode, and multiple definitions/calls on one line.

Complete when arrows act as the correct callers and callees without absorbing neighboring calls or breaking existing function relationships.

M6 implementation and verification:

- Added 50 initial regression cases before implementation; all failed against M5. Expanded to **74 cases** covering JavaScript and TypeScript, async arrows, expression/block bodies, nested arrows, anonymous callbacks, Unicode byte columns, CRLF, same-line definitions/calls, and uncertain bindings.
- Shared tree-sitter analysis recovers direct variable-bound arrow names, lexical bindings, enclosing symbols, and execution owners. Existing named function IDs remain stable; anonymous callbacks use deterministic `anonymous@line:column` names. Function expressions and methods own their calls rather than lending them to neighboring arrows.
- Calls resolve only unambiguous local function declarations or direct variable-bound arrows. Parameters, destructuring, imports, local declarations, repeated bindings, and writes prevent unrelated matches. Block/function boundaries distinguish lexical declarations from `var`; TypeScript namespaces isolate their bindings and unsupported value declarations block false targets.
- Normalization uses parser byte positions instead of line containment for JavaScript/TypeScript callers and callees. Symbol and dependency parsing both retain CRLF bytes so their offsets agree. Same-line and nested calls keep their actual owners.
- Cache version **8** invalidates M5 records. Regressions prove JSON reload, worker-free reuse, version-7 rebuilding, fresh/cached graph equality, and exact retained source bytes, hashes, and manifest mappings with Unicode and CRLF input. Hierarchy and related-context queries follow the corrected edges.
- `uv run --locked pytest -q`: **290 passed on Python 3.12.7**.
- `UV_PROJECT_ENVIRONMENT=/tmp/pyragify-m4-py39 uv run --locked --python 3.9 pytest -q`: **286 passed, 4 skipped on Python 3.9.25**. The skips remain Python 3.10+ pattern-matching cases.
- Updated the graph guide. `uv run --locked --group docs mkdocs build --site-dir /tmp/pyragify-m6-site`: passed with the existing API pages outside navigation notices. `git diff --check`: passed.
- Preserved preceding working-tree changes. No dependencies, CLI options, public signatures, or graph JSON top-level fields changed.

Limits: aliases, assignment-bound or object-property arrows, member calls, JavaScript module resolution, and namespace/receiver lookup remain unsupported. Repeated or reassigned bindings remain unresolved; execution order, dynamic scope changes, and runtime callable values are not simulated. Anonymous identities change when source positions change. No hosted deployment or performance benchmark was performed; M7 remains untouched.

#### M7 — Benchmark and deliver bounded performance improvements: implemented (2026-11-10)

- [x] Add one standard-library benchmark harness under `scripts/`. Use a deterministic **100,000-line Python corpus: 1,000 files, 100 lines and 10 functions per file**, with local calls and explicit imports. Label it synthetic; do not claim it reproduces the original workload.
- [x] Record revision, environment, worker count, corpus hash, and node/edge counts. Keep outputs outside the input tree and file selection constant. Run five graph-enabled/disabled export pairs, separating empty application caches from reusable caches. Report medians and ranges.
- [x] Measure 20 fixed function queries at depth 2, without relationship filters, after warm-up. Record median/p95 across 30 repetitions per query. Report JSON loading separately.
- [x] Profile the corrected implementation before optimizing. Include representative per-file extraction because process-worker costs are absent from a parent-only profile.
- [x] Replace repeated full-edge scans in related-context traversal with an adjacency map built inside each query invocation, preserving edge order. Include construction time in query latency; use `deque` for traversal.
- [x] Address one highest-cost repeated export scan identified by profiling. Retain the change only if repeated measurements demonstrate improvement.
- [x] Compare canonical graph contents and query results before/after optimization. Record latency and memory tradeoffs.

Complete separately: benchmark reproducibility, query improvement, and export improvement. An improvement checkbox stays open if gains are indistinguishable from measurement noise. Historical targets do not create an unlimited optimization project.

M7 implementation and verification:

- **Benchmark reproducibility: complete.** Added [scripts/benchmark_graph.py](scripts/benchmark_graph.py), using only the standard library and the installed project. The deterministic synthetic corpus contains exactly **1,000 files, 100 lines and 10 functions per file**, with local calls and explicit imports. Corpus SHA-256: `c996dd67e4938253599f6a41e081ff420dd5eac3e35a278c088185783d5818ec`.
- Recorded revision, source/harness hashes, Python/dependency/platform details, configured workers, corpus hash, graph counts, raw samples, and selected profile counters in [docs/benchmarks/m7.json](docs/benchmarks/m7.json). Measurements used Python **3.12.7**, Linux 6.8 x86-64, an Intel Core i5-7300U, and **four workers**. Both working trees share base revision `196ba90`; file hashes identify the uncommitted implementations.
- Ran **five graph-enabled/disabled pairs for each cache state, before and after** (40 unprofiled exports, plus two separate profiled exports). Outputs remained outside the corpus. Every export verified identical selection, retained source bytes, hashes, and manifest mappings; cold runs reused zero records, reused runs reused all **1,000**.
- Profiled the corrected implementation before editing production code. The repeated export scan was **1,000 whole-graph dependency queries**, costing **4.005 s cumulatively under profiling**. A separate profile covered ten representative worker extractions, including AST analysis and per-file graph serialization. JSON serialization was the larger overall export cost and remains unchanged.
- **Query improvement: complete.** Related-context traversal builds an adjacency map inside each invocation, preserves original edge order and bidirectional relationship paths, and uses `deque`. Twenty fixed imported-entrypoint queries (`function_0` in every fiftieth module), depth 2 and no filters, ran 30 times each after warm-up. Aggregate median fell **76.7 ms → 23.8 ms (69.0%)**; p95 fell **121.5 ms → 84.8 ms**. Timings include map construction. JSON read/decode and graph model construction were measured separately; their code was unchanged and differing load times are not an optimization claim.
- **Export improvement: complete.** One resolution pass now shares a file/import index rather than scanning the aggregate graph per file; public dependency queries reuse the same resolution logic. Under profiling, the shared helper took **0.021 s**, and the entire resolution pass fell **4.619 s → 0.581 s**. Unprofiled graph-enabled medians fell **24.615 s → 20.055 s** with empty application caches and **16.025 s → 12.045 s** with reused caches. Retained the change based on repeated reused-cache improvement and the removed profiled scan; cold ranges overlap substantially, so its median alone does not establish a repeatable cold-export gain.
- Canonical graph contents **and edge order** matched before/after: **12,000 nodes, 32,000 edges**, canonical SHA-256 `d7c67d32f3e53ecfb77bd3175b8dac5dce2ebe5c0d3b1fbb3ea6eae3c7b6c275`. All ordered query results and all fresh/reused graph fingerprints matched. The delivered source and harness hashes match the measured candidate.
- Recorded memory tradeoffs: representative query peak traced allocation rose **11.4 KiB → 1.68 MiB**, excluding the loaded graph. Median parent peak RSS stayed about **130 MiB cold / 136 MiB reused** for graph-enabled exports. Parent and largest completed-child RSS are recorded separately; no total process-pool peak is claimed. Indexes are operation-local, with no stale persistent cache.
- Added **14 regressions** covering forward/reverse traversal, cycles, self-edges, depth, filters, parallel relationships, edge-order changes, mutation on an existing query instance, exact/ambiguous module paths, package bindings, includes, and repeated resolution. Harness assertions also check corpus dimensions, provenance, cache state, graph/query equivalence, invalid worker counts, and protection of existing output directories. No timing assertions enter unit tests.
- `uv run --locked pytest -q`: **304 passed on Python 3.12.7**. `UV_PROJECT_ENVIRONMENT=/tmp/pyragify-m4-py39 uv run --locked --python 3.9 pytest -q`: **300 passed, 4 skipped on Python 3.9.25**; skips remain Python 3.10+ pattern-matching cases.
- Updated [the graph guide](docs/user-guide/knowledge-graph.md) with reproduction commands, full timing ranges, loading costs, memory costs, and limits. `uv run --locked --group docs mkdocs build --site-dir /tmp/pyragify-m7-site`: passed with existing API pages outside navigation notices. `git diff --check`: passed.
- Preserved preceding working-tree changes, including `processor.py` byte-for-byte. No dependencies, public signatures, CLI options, or graph JSON top-level fields changed. Cache version remains **8** because extracted records are unchanged.

Limits: these are sequential runs on a shared development machine with OS/filesystem caches left intact; only application-cache state is controlled. Cold-export ranges overlap; graph-disabled variation is a noise control. The synthetic corpus and imported-entrypoint queries do not reproduce the unknown historical workload or establish general repository performance. Adjacency adds temporary memory proportional to graph size. The harness requires a Unix-like system for resource measurements. Original performance targets, whole-pool peak memory, hosted deployment, actual NotebookLM ingestion, and LLM answer quality remain unverified. No additional optimization was started.

#### Shared interfaces and verification

- Keep CLI options, public signatures, and graph JSON top-level fields unchanged. Add source/scope metadata within existing metadata dictionaries.
- Advance the cache version for each milestone changing extracted records. Prove old records rebuild and fresh/cached graph semantics agree.
- For M4–M6, run focused regressions and `uv run --locked pytest -q` on Python **3.9 and 3.12**.
- For M7, test traversal direction, cycles, depth, filters, parallel relationships, and query-after-mutation behavior; rerun the full correctness suite.
- Verify retained source bytes, hashes, and manifest mappings. Whole-manifest byte equality is unnecessary because cache/diagnostic metadata can change.
- Update [the graph guide](docs/user-guide/knowledge-graph.md) and build documentation after behavior changes. Keep timing assertions outside unit tests.

Review evidence: temporary fixtures reproduced shadowed Python calls reaching unrelated functions, default-expression calls assigned to the new function, imported calls staying unresolved, and named arrows appearing as `anonymous`. The full suite and large benchmark were not rerun during the planning review or the workflow-only M3 implementation. M4–M7 subsequently reran the full suite as recorded above. M7 also ran the standardized synthetic benchmark; the original workload remains unreproduced. The listed implementation milestones are complete.

## Scope cuts and verification limits

Defer graph visualization, GraphML, more language-specific analysis, embeddings, vector stores, chat servers, IDE plugins, ML pattern recognition, automatic architecture narratives, and extra export formats. There is no demonstrated need for these in the handoff workflow.

Small cleanup can wait: `load_yaml_config`, `is_documentation_file`, and `read_file_in_chunks` have no runtime callers in this repository. Removing their definitions would remove **84 source lines, 0 runtime dependencies**; related tests/docs and possible external API users would need review. This is not the next milestone.

**Verdict:** The existing fixes are useful, but passing tests currently hide source-loss, data-boundary, cache, and graph-accuracy bugs. Fix safe operation first, then earn any further custom export work through the reuse comparison.

**Not checked:** Published package behavior, live CI history, supported-Python-version matrix, clean wheel installation, large-repository load, external-tool execution, actual NotebookLM ingestion, or LLM answer quality. Documentation was inspected selectively and built, not exhaustively verified. No implementation, dependency, commit, or publishing changes were made during this review.
