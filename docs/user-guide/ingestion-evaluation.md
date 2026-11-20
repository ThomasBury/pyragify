# Chat ingestion evaluation

On November 19, 2026, a single paired comparison in Codex chat scored
**5/5 for answer correctness and 4/4 for source citations in both conditions**.
The handoff supplied an index, source ranges, and byte mappings. On this
fixture, the chat answered and cited the raw files just as accurately.

| Chat input | UTF-8 prompt bytes | Correct answers | Correct source citations |
| --- | ---: | ---: | ---: |
| Five raw repository files | 1,881 | 5/5 | 4/4 |
| Pyragify index, Markdown parts, and manifest | 6,703 | 5/5 | 4/4 |

## Setup

The synthetic repository models a small queue relay. Its README lists stale
retry rules, the implementation reads defaults from JSON, and production
configuration is absent. Both conditions used the same five source files and
the same questions. I exported the fixture through the CLI with
`--no-enable-graph` and verified each source byte slice against the original.
The handoff condition received the actual export files as inline text. The
baseline received the original file contents with filename labels.

Each condition ran in a fresh, temporary Codex CLI 0.170.0 chat with the default
hosted model and no tools used in either response. The event output did not
identify the model. The exact prompts, responses, and fixture are available in
the [evaluation record](../benchmarks/ingestion.json).

## Scoring

| Question | Expected answer |
| --- | --- |
| Only 503 responses | Three send attempts, then dead-letter |
| Initial 429 | One attempt, then dead-letter |
| Acknowledgement status | HTTP 204 |
| Stale README claims | Active defaults retry 502 and 503, and allow two retries. The README lists 429 and 503 and claims five retries. |
| Production setting for `QUEUE_RETRIES` | Unknown from the supplied material |

Each question earned a point for a correct answer. Each of the first four
earned a separate point for citations to source lines supporting the answer.
The fifth tested whether the chat would acknowledge missing evidence.

The export gave both a human and a program a way to verify source bytes and
locate files in the bundle. For this small fixture, that structure came with
3.6 times the prompt bytes and did not improve the scores. The comparison
covers one fixture and one response per condition. It leaves file-upload
behavior, NotebookLM retrieval, and larger repositories unmeasured.
