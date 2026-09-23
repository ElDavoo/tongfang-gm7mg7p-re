# Constructed inputs for the tools in `ec/tools/`

**Nothing in this directory is a capture.** These files were written by hand to
exercise a tool's branches; no byte here was read from an EC, and none of them
is evidence of anything. Real captures live in `../../../evidence/` and are
dated with the day they were taken — the files here carry an obviously
placeholder `2026-01-01` timestamp so the two can never be confused.

| File | Feeds | What it constructs |
| --- | --- | --- |
| `0751-isolation-example-quiet.csv` | `../grade_0751_isolation.py` | A capture in which none of the bytes §4 of the isolation procedure names moves after the mark — only two sensor-looking addresses do. |
| `0751-isolation-example-active.csv` | `../grade_0751_isolation.py` | The opposite branch: `0x0784` and `0x07C6` move within a second of the write mark. This is *not* a prediction that they will. |

Both are in `ec_watch.py --mark --csv` format, `MARK` rows included.
