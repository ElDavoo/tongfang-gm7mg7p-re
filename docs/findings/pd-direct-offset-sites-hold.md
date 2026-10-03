# The PD direct-offset site table is derived, and the derivation was called by nothing

`ec/annotations/pd-direct-offset-sites.csv` is the committed table of every
candidate site in the PD image that may write the direct `0x0D`/`0x0E` pair, or
that may reach the `0x1253` pointer add through an `lcall`/`ljmp` — a row per
candidate, which is what the tool's own docstring says a byte scan can honestly
produce, and no more than that. It is the measurement
`docs/findings/pd-direct-offset-pointer-add.md` rests on, and like that
write-up it is entirely static analysis of the committed
`ec/firmware/GMxMGxx_11.800`.

`ec/tools/pd_direct_offset_sites.py` re-derives the table from that image and
its `--check` mode diffs the two byte for byte. **That mode was called by
nothing.** It was not an arm in `.github/scripts/agent-gates.sh`, no
`.github/workflows/` file invoked it, no `test_*.py` ran it, and no other tool
reads the table. So the one thing that would catch a drifted row was
itself unwired: a hand edit of a cell, a re-cut of the scan after a rename, a
regenerated image — each would have merged green with the table describing the
PD image no longer.

`ec/tools/test_pd_direct_offset_sites.py` is that wiring. It runs both of the
tool's modes over the committed tree.

## The table, and what a green run says about it

```
$ python3 ec/tools/pd_direct_offset_sites.py ec/firmware/GMxMGxx_11.800 --csv --check
ec/annotations/pd-direct-offset-sites.csv: this run reproduces it byte for byte (2617 lines)
$ python3 ec/tools/pd_direct_offset_sites.py --self-test
self-test passed: the decodes match the `r2 -a 8051` transcriptions, the three
populations hold, the aliasing bank is selected by exactly the two PSW writes
named above, and the store entry's returned DPTR is read on the next instruction
```

The rows carry a `form` that keeps two things apart. In the 8051 direct space
`0x00`-`0x1F` is the four register banks, so `0x0D`/`0x0E` are R5 and R6 *of
bank 1*: a **direct**-form row (`75 0d 27`, `f5 0d`, `85 82 0e`) means
`0x0D`/`0x0E` whatever PSW says, while a **register**-form row means it only
under PSW.RS = 1, which the tool computes from the nearest `mov psw,#imm` rather
than assuming. The other two forms are the `0x1253` callers. The counts are in
the table rather than here, because a count of rows is a figure every PD change
moves and this file would then be a sentence every commit has to edit.

**A green run is not a claim that the scan is complete.** The tool's docstring
is explicit that a byte scan over the region both over-counts — a `75 0D` inside
a data table reads exactly like `mov 0x0d,#imm` — and under-counts, because a
call reached through a dispatch table carries no target bytes at all. That is
why a phantom is labelled rather than filtered: a row scoring no converging
anchor is printed with that beside it and marked unsyncable. The `note` column
carries that label, and it is the reason this suite asserts nothing about how
many rows there are.

**Nothing here observed hardware.** No EC was opened, no register was read back,
no write was attempted. The suite reads two committed files — the image and the
table — and every figure in the table is a static count over the image.

## Why this instance and not another

The shape is not rare in this tree; several tools have a `--check` nothing
calls. What makes this one the instance is that its siblings are all wired, so
the gap is a fact about this table rather than a general condition nobody had
noticed:

| hold | how it is wired |
|---|---|
| `call-graph-callees.csv` | `call_graph.py --check` is a cheap-tier arm in `.github/scripts/agent-gates.sh` |
| `gap-text-check.csv` | `ec/tools/test_verify_gap_text.py` runs `verify_gap_text.py --check` as a subprocess |
| `dsdt-ecmg-fields.csv` | `ec/tools/test_dsdt_ec_fields.py` runs `dsdt_ec_fields.py --csv --check` as a subprocess |
| `pd-direct-offset-sites.csv` | **nothing ran it** |

## The negative controls, which are the substance

Every positive case above is also satisfied by a comparison that reads nothing,
so the mutations run over `tempfile` copies and are checked as a subprocess —
what the case sees is the exit code a reader gets, not a value this file
produced. `--check` takes a path, so the tool reads a file the suite made and
the committed table is never written; a separate case asserts that by comparing
the committed bytes before and after both modes have run.

- a doctored cell in one row is red, and the diff names the row. The mutation
  parses and re-renders with the csv module rather than splitting on `,`,
  because a row's `text` cell is quoted and carries a comma of its own
  (`"mov  0x0d,#0x27"`); a naive split would count that comma as a column and
  alter the wrong field while still producing a difference;
- an unaltered copy beside it is green, because a check that reports a
  difference for everything passes all the reds;
- a missing table is red **and is not created** — the failure that turns a
  missing artifact into a green run and leaves a file behind for the next commit
  to trust;
- a dropped row is red, which is the shape a partial regeneration leaves behind.

The control that is not a mutation of the table is the derivation itself:
changing the tool's framing constant changes what it produces, and the suite goes
red on the `--check` case. A suite that only caught a hand edit of the CSV would
not notice its own tool changing its mind about what the table says.

And the converse, which is what stops the reds being an accident of the check
being strict: neutering `check_table` to return 0 turns exactly the three
"is red" cases red and leaves the two green ones green. Both directions were run
by hand, and the tool was restored afterwards.

The committed-shape cases hold the table's vocabulary rather than its size: the
header is the tool's own `COLUMNS`, every row names the region it was scanned in
so no row reads as an EC claim, the `form` values stay inside the four the tool
distinguishes, and a direct-form row's opcode really does write `0x0D`/`0x0E` —
read from the tool's `DIRECT_DST` rather than guessed, because `75 0d 27` carries
its destination in the middle byte and `f5 0d` in the last.

## Where this runs, and what it does not claim

The suite is discovered by `tools/run-tests.sh`, which CI runs as the `tests` job
in `ci.yml`. **It is not the cheap tier.** `.github/scripts/agent-gates.sh` is
copied from the `agent-pipeline` template and the pipeline's push token has no
`workflow` scope, so a gate arm there is an upstream change and a re-copy. This
needs no `git apply` and no human, which is the route available; the cheap tier
would be a separate, template-owned change.

## What this opens

`pd_direct_offset_sites.py` has modes beyond the two run here — `--writers`,
`--register-writers`, `--callers`, `--base` — which report on the same scan and
are held by nothing in the same way. What is *not* open is whether the scan is
right: that is the `unsyncable` label's own question, and answering it needs a
method this tool does not have, which is the blind spot
`docs/findings/pd-direct-offset-pointer-add.md` records rather than hides.