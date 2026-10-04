# Правила источника и границы интерпретации

| Фактический случай | Legacy state | Format facts / текст | Raw / gap |
| --- | --- | --- | --- |
| Valid UTF8, no binary controls | INDEXED | UTF8_TEXT_CANDIDATE / ELIGIBLE | Git bytes recorded; proof separate |
| Empty `[0,0)` chunk | INDEXED | EMPTY / ELIGIBLE | Empty hash and one empty chunk preserved |
| UTF8 BOM, CRLF, long line | INDEXED | UTF8_TEXT_CANDIDATE / ELIGIBLE | No normalization/transcoding |
| Python syntax error | INDEXED | Text eligible, parser PYTHON_PARSE_FAILED | No AST completeness claim |
| NUL/C0 controls | INDEXED | BINARY_CONTROL_HEURISTIC / INELIGIBLE | Raw retained; all fragments gated |
| Invalid UTF8 / UTF16 | INDEXED | NON_UTF8 / INELIGIBLE | Raw retained; no text loss disguised as decode |
| Canonical LFS v1 pointer | INDEXED | LFS_POINTER_V1 / METADATA_ONLY | Pointer bytes recorded, external payload NOT_CHECKED |
| Recognized malformed pointer | INDEXED | LFS_POINTER_MALFORMED / METADATA_ONLY | Raw retained; no trusted payload descriptor |
| Extended/legacy pointer | INDEXED | LFS_POINTER_UNSUPPORTED / METADATA_ONLY | Explicit supported-form gap |
| Protected name / operator exclude | EXCLUDED | NOT_CLASSIFIED / INELIGIBLE | Separate policy reason; no fake byte hash |
| Protected text heuristic | EXCLUDED | NOT_CLASSIFIED / INELIGIBLE | Recorded hash may exist; no protected text projection |
| Symlink 120000 | EXCLUDED | SYMLINK_METADATA / INELIGIBLE | Link target contents not captured |
| Submodule 160000/commit | EXCLUDED | SUBMODULE_METADATA / INELIGIBLE | Pinned commit metadata, no recursive submodule capture |
| Reversible unsupported path | EXCLUDED | UNSUPPORTED_PATH_METADATA / INELIGIBLE | Raw path token preserved as data |
| Blob exceeds existing budget | ERROR | NOT_CLASSIFIED / INELIGIBLE | FILE_TOO_LARGE + observed budget; followup streaming |
| Missing/inaccessible blob | ERROR | NOT_CLASSIFIED / INELIGIBLE | Existing failure reason, no hidden fetch |
| Existing row without v1 facts | unchanged | LEGACY_UNKNOWN / UNKNOWN | Requires explicit bounded stored-chunk backfill |
| Damaged ranges/raw/hash in backfill | unchanged | CORRUPT_CAPTURE / INELIGIBLE | Block facts readiness; preserve evidence of failure |

No universal binary detector is claimed. UTF8_TEXT_CANDIDATE means only the
documented encoding/control-byte policy passes. Extension-based guesses are
diagnostic candidates, never byte evidence. Binary capture does not imply a
text decoder. Parser failure is independent of encoding eligibility.

`raw_capture=RECORDED` is a store observation. `raw_integrity=NOT_RUN` cannot
become PASS from a summary count. Pointer-declared SHA/size is not payload
evidence. Text display eligibility is not AI sent/read/used; those statuses
remain their own owner projections. Format facts apply equally to user-selected
files and automatically related files in a text packet.

`GAPS.jsonl` includes every row with text_eligibility!=ELIGIBLE or uncaptured
content or unknown external payload. One row may have several reasons; no
duplicate inventory entry. Count categories overlap; do not sum them as total.
All 64 golden rows have facts. Source labels in fixtures are synthetic.
