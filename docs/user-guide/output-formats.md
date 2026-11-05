# Output Contract

The trusted handoff consists of `index.md`, language-grouped Markdown parts, and
`metadata.json`, all generated from the same retained source records. Graph JSON
is experimental and outside this contract.

```text
output/
├── index.md
├── metadata.json
├── hashes.json
├── .pyragify-cache.json
├── .pyragify-artifacts.json
├── python/
│   └── chunk_0.md
└── markdown/
    └── chunk_0.md
```

## Readable source

Start at `index.md`: its file links lead to explicit anchors in the parts. Each
entry gives a path, source line range, and MD5 hash. The omissions list names
excluded files or directories and gives reasons. Directory entries cover their
descendants; ignored trees need not be traversed to enumerate every file.
Failures abort publication, so a published handoff's failures list is empty.

Each included file occupies exactly one fenced source block. Whole-file copying
preserves imports, decorators, async definitions, comments, blank lines, original
line endings, final newlines, Unicode, and malformed code. Fence lengths exceed
all backtick runs in the source, so embedded Markdown fences cannot close them.
One additional newline separates source from its closing fence; it is framing,
not part of the original source. Exact byte ranges in the manifest exclude it.
Search within a linked source block to locate a definition. There is no generated
architecture description or symbol-ranking claim.

## Manifest

`metadata.json` uses `format_version: 1`, `source_encoding: "utf-8"`, and
`hash_algorithm: "md5"`. MD5 identifies source snapshots; it is not a security
signature. `processed_files` includes cached files as well as freshly read ones.
Each entry contains:

| Field | Meaning |
| --- | --- |
| `path` | Path relative to the source root |
| `hash` | MD5 of the exact retained UTF-8 bytes |
| `size`, `lines` | Retained byte size and source line count |
| `chunks` | One complete source block |
| `words` | Whitespace-separated words in the formatted source block, including its header |
| `parser_limitations` | Empty for source-only exports; experimental graph limitations when enabled |
| `output.part`, `output.anchor` | Relative Markdown part path and link anchor |
| `output.start_line`, `output.end_line` | One-based inclusive source range; `0–0` for empty files |
| `output.start_byte`, `output.end_byte` | Zero-based, half-open UTF-8 byte offsets in the output part, selecting only source |

`skipped_files` lists exclusions with reasons. `failed_files` is empty on success;
failures are logged and abort publication. `reused_files` names included files
recovered from the cache, rather than misreporting them as omissions. `summary`
counts included files and formatted source-block words, excluding the index.

To verify a source block without parsing Markdown:

```python
import hashlib
import json
from pathlib import Path

output = Path("output")
manifest = json.loads((output / "metadata.json").read_text())
for item in manifest["processed_files"]:
    mapping = item["output"]
    part = (output / mapping["part"]).read_bytes()
    source = part[mapping["start_byte"]:mapping["end_byte"]]
    assert len(source) == item["size"]
    assert hashlib.md5(source).hexdigest() == item["hash"]
```

`hashes.json` repeats source hashes for inspection. `.pyragify-cache.json` version
5 stores source blocks, metadata, and optional graph records for reuse. Removing
it forces reprocessing. `.pyragify-artifacts.json` lists owned parts for safe
cleanup. On upgrade, owned legacy `.txt` parts are removed; unlisted old parts
are left for manual inspection. Consumers of the earlier semantic chunks must
switch to the new manifest and `.md` parts.

## Limits and failures

`max_words` must be positive. It bounds every generated Markdown file, counting
headers, fences, and other formatting with Python's whitespace splitting. It
counts words, not model tokens or bytes. Source files are indivisible: if one
formatted file exceeds the limit, the entire export fails before publication.
The index must also fit, or the export fails. Increase the limit or narrow the
selection; there is no silent truncation or partial-source output.

`max_file_size` excludes oversized input files before processing and records
the omission. JSON artifacts have no word limit. File selection is not secret
detection. Do not change sources during a run: whole-repository snapshot isolation
is unsupported. Experimental graph extraction can reread sources independently.
Ordinary raised write failures restore prior published artifacts; crash recovery
and concurrent writers are unsupported. See [configuration](../getting-started/configuration.md).
