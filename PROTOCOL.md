# RunbookLatch protocol

## State and identity

`OPEN → ACTIVE → COMPLETE`, or `OPEN → REVIEW / CYCLE`.

Owner is the caller of `open_run`. Storage key is lowercase owner address + `/` + run ID. Run IDs and step IDs use 1–40 ASCII letters, digits, hyphen or underscore. No existing run can be overwritten. An executor may compile an OPEN run but cannot alter the plan. Only the executor declared for a step can acknowledge it, even when the caller is the run owner.

`plan_json` has exactly `procedure` and `steps`. The procedure is 40–3000 stripped characters, containing 1–8 nonempty newline-delimited rule lines of 8–500 stripped characters each. The normalized plan adds a deterministic `rules` array; do not supply `rules` in input JSON. There are 2–6 steps, each with exactly `id`, `action`, `executor`. Actions are 12–400 stripped characters. IDs and exact action strings must be distinct. Executors are nonzero 20-byte hexadecimal wallet strings. The total JSON input is 80–6500 characters. Notes are 12–500 stripped characters. Text is validated and never silently truncated.

## Equivalence check

All ordered pairs excluding self-pairs appear in step-major order. Self-dependencies are unsupported inputs at the semantic level and are not represented or reliably detected; graph cycle detection covers distinct-step cycles only. REQUIRED means an explicit direct requirement that one action's completion precede acknowledgement of the other. NO_DIRECT means no direct requirement is stated. UNCLEAR captures unresolved ordering, applicability, missing actions, unsupported conditions or alternatives. An unrepresented prerequisite affecting a target must mark at least one incoming pair UNCLEAR, blocking the entire run.

Each model finding includes before/after IDs, category, a nonempty list of distinct zero-based `rule_indices`, and a 12–350-character explanation. Indices must be literal integers in bounds. Code sorts the indices and constructs `quote` by joining their exact source rule lines with a newline. If a candidate includes a quote, it must equal that derived string. Models cannot substitute a paraphrase. A stored finding retains both references and original text. The leader's complete matrix is structurally checked, then validators independently produce the same ordered categories from the original plan. The proposed quotes are separately audited for their substantive relation to the exact action pair; only literal boolean true passes. Failure, malformed output or a non-return leader result is rejected. Explanation wording is not required to be identical.

No external web data is fetched. The runbook is an immutable owner assertion. Semantic equivalence does not establish real-world truth. A malicious or incomplete procedure can still produce an apparently executable graph.

## Graph and gating

REQUIRED findings become directed edges. Kahn's algorithm repeatedly removes all remaining nodes without incoming edges from remaining nodes, preserving step order within each layer. If nodes remain with no removable layer, status is CYCLE. `cycle_blocked` includes remaining cycle nodes and any downstream nodes still blocked by them; it is not a minimal cycle witness. CYCLE takes precedence over REVIEW. Otherwise any UNCLEAR produces REVIEW; only a fully classified acyclic graph becomes ACTIVE.

`available` includes exactly unacknowledged steps whose every incoming predecessor is acknowledged, and is empty for non-ACTIVE runs. It is derived during reads, not stored as authoritative state. Acknowledgement validates ACTIVE status, exact digest, step existence, executor identity, non-repetition and all prerequisites before changing storage. Every successful acknowledgement appends actor/note/step/ordinal to the journal. The last acknowledgement changes status to COMPLETE. An early acknowledgement never queues an operation or reserves a step.

## Digests

Canonical JSON is Python `json.dumps(value, sort_keys=True, separators=(",", ":"))`, with default ASCII escaping. Hash the UTF-8 bytes with SHA-256.

`plan_digest = hash({owner, id, plan})`.

`graph_digest = hash({plan_digest, findings, graph})` after compile. The immutable graph retains its original ACTIVE/REVIEW/CYCLE status even when the enclosing run later becomes COMPLETE. Acknowledgements and journal are outside the graph digest; the digest by itself does not prove actor signatures or completed work. Always read authenticated finalized state.

## Integrating safely

Pin a trusted contract source digest and expected owner/run. Verify protocol, deployed code, full-consensus finalized receipt, exact caller/method/arguments, graph digest and latest state. Check executor acknowledgements rather than accepting an exported JSON alone. Model errors and false completion assertions must be handled by the consuming system. A passing graph is not a safety assessment. Signing keys, operational credentials and private procedure information must stay outside this public record.
