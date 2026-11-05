# Repomix Comparison

M2 requires evidence before extending Pyragify's exporter. On 2026-11-05,
Repomix **1.18.1** was run locally with Node **26.9.0** against this repository,
a small Python application, and a mixed-language Unicode fixture with a
deliberately oversized file. No repository was uploaded. Repomix's security check
was left enabled; that is not a claim that the selected files contain no secrets.

## Reproduce

From this checkout, with Node/npm available:

```bash
python scripts/compare_repomix.py /tmp/pyragify-repomix-comparison
```

The destination must not exist. The harness downloads the pinned CLI into a
temporary npm cache under that destination, creates synthetic Git repositories,
and leaves Markdown, JSON, logs, and assertion results there. It is a verification
script, not an export wrapper. Run only against a trusted local checkout:
Repomix can load repository configuration.

The measured Markdown command was equivalent to:

```bash
npx --yes repomix@1.18.1 ./my-project --style markdown --parsable-style \
  --output-show-line-numbers --no-git-sort-by-changes -o /tmp/handoff.md
```

Compression, comment removal, and blank-line removal were not enabled. The small
application was also exported with `--style json`. The oversized fixture was
rerun with `--split-output 5kb`.

## Observations

| Requirement | Measured result |
| --- | --- |
| Retained source | All emitted file bodies matched source after stripping outer whitespace. Imports, constants, decorators, async definitions, class methods, and Unicode survived without duplicated bodies. JSON output discarded the final newline of `app.py`, so it was not an exact-byte copy. |
| Provenance | Markdown supplied file paths and numbered lines. JSON contained `fileSummary`, `directoryStructure`, and `files`; no source hashes or source-to-Markdown-part byte mapping were present. |
| File selection | The small app's nested `.gitignore` excluded `private/hidden.txt`; an external-file symlink was excluded. The omitted path names/reasons were absent from JSON. This does not establish all Git edge cases. |
| Navigation | Markdown supplied a directory tree and per-file headings with line numbers, sufficient for text search. It did not supply the required linked omission and manifest inventory. |
| Limits | `--split-output 5kb` failed nonzero for `oversized.txt`, reporting 81,747 bytes against 5,120. It explicitly refused to split one source file. Without the small limit, all four mixed-fixture files were retained. |
| Repository run | The initial pre-M2 checkout produced 43 readable files, with security checks enabled. This is a small-repository observation, not a performance benchmark. |

The reproducible harness checks every emitted source body, uniqueness of file
entries, ignored/symlink sentinel absence, JSON schema and final-newline loss,
and the nonzero oversized-file result. File counts and sizes for this repository
will change with the checkout; inspect `results.json` rather than treating 43 as
a fixed expectation.

## Decision

Repomix supplies ordinary readable repository packaging and honest oversized-file
failure already. Use it directly if that is the whole requirement. No forwarding
wrapper or Repomix runtime dependency is justified.

The material gaps for this project's handoff are exact retained source bytes and
a manifest combining hashes, output mapping, and explicit omissions. Retain only
the existing processor's narrow whole-file exporter to meet that contract. Do not
build another tokenizer, graph-ranking engine, extra output format, or secret
scanner. Reconsider retiring the packer if Repomix supplies this contract later.

Pyragify adopts the same simple indivisible-file limit policy: fail explicitly
if one source file cannot fit. Its Markdown index and manifest are generated
from the same records as its verbatim source blocks. Graphs remain experimental
and outside the trusted handoff. Neither tool's result here establishes actual
NotebookLM ingestion or improved LLM answers.

The official [CLI options](https://repomix.com/guide/command-line-options),
[output formats](https://repomix.com/guide/output), and
[configuration](https://repomix.com/guide/configuration) were consulted through
Context7; the conclusions above come from executing the pinned version.
