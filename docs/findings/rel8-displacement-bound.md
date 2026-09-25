# What holds the rel8 displacement read in range: a constant in another module, and a marker check three frames away

(2026-09-25, issue #847. Static reading and arithmetic over committed bytes.
No capture opened, no EC, no hardware, no Windows.)

[`opcode-len-bounds-census.md`](opcode-len-bounds-census.md) excluded
`ec/tools/audit_call_targets.py:171,315`'s `d[i + OPCODE_LEN[op] - 1]` from its
20 rows as *a different shape with a different bound*, and in the same
paragraph said that "whether that pair wants a check of its own is a question
for a follow-up, not a finding." This is that follow-up. The subject is a
property of Python walking a `bytes` object; nothing here is a claim about what
the EC does.

## The two sites, and the one bound they share

```python
# ec/tools/audit_call_targets.py:168-172, relative_sites()
for i in range(lo, hi):
    op = d[i]
    if op in REL_OPCODES and i + OPCODE_LEN[op] <= hi:
        yield i, op, relative_target(op, d[i + OPCODE_LEN[op] - 1],
                                     runtime_addr(i, True))
```

```python
# ec/tools/audit_call_targets.py:314-315, relative_survey()
"length": OPCODE_LEN[op],
"disp": d[off + OPCODE_LEN[op] - 1],
```

`OPCODE_LEN[op]` is not the read that can raise — `op` is a byte value in hand
and the table covers all 256 of them (`ec/tools/disasm8051.py:39-56`), which is
the census's first section's argument and is not re-litigated here. The read is
`d[...]`: the *displacement* byte, at an offset the table supplies. The guard
in front of it is `i + OPCODE_LEN[op] <= hi`, and `hi` is not a length.

## Where `hi` comes from, and where the length actually comes from

Two different modules, and neither one is the loop.

`hi` is `region_bounds(name)` (`ec/tools/audit_call_targets.py:206-214`), a
`next()` over `REGIONS` — a hard-coded table at
`ec/tools/trace_xdata_refs.py:72-79`. It is a **constant**. Nothing about it
moves when the buffer does:

```python
("common", 0x00000, 0x08000, 0x0000, ...),
("bank0",   0x08000, 0x10000, 0x8000, ...),
("bank1",   0x10000, 0x18000, 0x8000, ...),
```

`AUDITED` is `("common", "bank0", "bank1")` (`:100`), so the largest `hi` either
site can be handed is bank1's `0x18000`, and the guard caps the read at
`0x17FFF`.

What keeps the read in range is `main()` (`:799-800`), which refuses the image
unless `d[0x20040:0x2004A] == b"ITE8850-PD"`. A Python slice never raises, so a
short buffer yields a short slice, fails the comparison, and the function
returns 1 — the check is a genuine **length floor of `0x2004A` = 131146 bytes**,
verified by running it against buffers of five different lengths rather than
argued (the console block under `## Reproducing it`). The margin between the two
numbers is `0x2004A - 0x17FFF` = **32843 bytes**.

And it is on every path that can reach the read: `relative_sites` and
`relative_survey` are imported by nothing outside this file
(`grep -rn 'relative_sites\|relative_survey' --include=*.py .` returns only
this module's own definitions and uses; `group_functions.py:124`, the one
other module that imports from here, takes only `OTHER_BANK` and `bucket_of`),
and the check sits above the `--self-test` dispatch at `:806` as well as above
the three survey calls.

## The verdict

**It wants a check of its own, and it does not want a `len(d)` guard.**

The two offered fixes split, and the split is on the merits rather than on
convenience:

- **A `len(d)` test in `relative_sites()` — no.** `hi` is a *region* bound, and
  every loop in this tool is region-relative: `call_sites()` stops two short of
  `hi` (`:142`), `paged_sites()` one short (`:154`), `erased_runs()` reads to
  `hi - 1` (`:121`). A clamp inside `relative_sites()` would test something
  other than the loop's own invariant, which is the same reason the census gave
  rows 11-20 a measured verdict rather than a guard. The invariant that is
  actually true is `hi <= len(d)` — and that is a property of the *call sites*,
  not of any one loop, which is why it does not belong in the loop.
- **A note on the bound — yes, on the consumer rather than the table.** "That
  `hi` is a constant and not a bound on `len(d)`" is a claim about how *this*
  tool reads the table, and a consumer's property belongs on the consumer. Four
  modules import `REGIONS` by name (`xdata_span_survey.py:40`,
  `decode_index_table.py:61`, `pd_index_geometry.py:110`, and this one at `:83`)
  out of thirteen that import something from `trace_xdata_refs`; editing the
  table for a sentence only this one of them acts on would be a shared-file
  edit for a claim the other twelve have no occasion to make.

So the change is the note, on `region_bounds()` (`:206-214`), where a reader
asking "where does `hi` come from" lands — plus **one `check()` in the existing
`--self-test` harness** (`:728-735`) asserting `max(region_bounds(n)[1] for n in
AUDITED) <= len(d)`. That check is beyond the issue's literal ask and is
labelled as such; the verdict above does not rest on it. It *reports* the
invariant rather than guarding the loop, which is the difference the census's
rows 11-20 are about: a future dump that breaks it becomes a visible failed
line rather than an `IndexError` three functions deep, and no loop in the tool
has to grow a bound that is not its own.

**Nothing about the tool's behaviour changed.** The two code edits are a
docstring and a `check()`. `audit_call_targets.py` over the committed image
exits 0 and produces byte-identical output before and after, and `--relative-csv`
— the artifact that exercises `:315` specifically, since `disp` is a column of
it — is 9077 lines and identical on both runs. That is the evidence for the
sentence, not a formality.

## The vector: the guard passes on a buffer the read cannot survive

The trace above is the argument; this is the picture. `hi` is a constant, so on
a truncated buffer the guard still admits a site the read cannot serve, and the
`IndexError` is real rather than hypothetical:

```
vector: truncate the image one byte past 0x0802C (`bc b6 a3`, a 3-byte form)
  guard at :170 sees i+3 = 0x0802F <= hi = 0x10000 -> True, on a 0x0802D-byte buffer
  committed -> 3281 site(s) in bank0
  truncated -> IndexError: index out of range
```

The guard is satisfied by arithmetic on a constant; the read fails on the
buffer. That gap — 32843 bytes wide on the committed image, and closed by one
comparison in a different function — is the whole finding. The same
truncation fed to `relative_survey()` rather than to the generator raises
`IndexError` too, at `:121` in `erased_runs()` instead, which is a fact about
call order and is **not** evidence about the two named sites; it is why the
vector above is aimed at `relative_sites()` directly.

**Two corrections to the issue's arithmetic, both left visible here rather than
silently replaced.** The issue gives the marker slice as
`d[0x20040:0x20045]`, but `PD_MARKER`'s magic is `b"ITE8850-PD"` — **ten**
bytes, not five — so the slice is `d[0x20040:0x2004A]` and the length floor is
`0x2004A`, five bytes higher than the issue's. And the issue's headline figure
of *33061 bytes* past the highest index `hi` admits corresponds to index
`0x17F25`, which is not a region edge and is not where any bound in this
repository sits. The margin is **32843**. The issue's reasoning is right in
every step and wrong in its last two numbers; the reasoning is what carries the
verdict, and the corrected figures are what the `--self-test` line and the
snippet below both print.

## The other two tools directories, measured

The census's disclaimer said it "says nothing at all about `bios/tools` or
`windows/tools`." It does now — one grep per directory, the census's own
membership test:

```console
$ grep -rn 'OPCODE_LEN\[' --include=*.py bios/tools windows/tools
$ echo $?
1
```

Nothing found, by that method. The stronger reason is structural and is the one
worth keeping, because it does not depend on the pattern being the right one:
`OPCODE_LEN` is defined in exactly one file, `ec/tools/disasm8051.py:39`, and
`grep -rn 'disasm8051' --include=*.py bios windows` returns nothing — so those
directories do not merely fail this grep, they **cannot have the shape**,
because they do not have the table.

The issue's own pattern, which does not assume the table's name, is empty over
both directories too — `grep -rcE '\w+\[[a-z_]*\[[a-z_]+\]' --include=*.py`
reports `0` for every file in both:

| directory | `.py` files | files with a match |
|---|---:|---:|
| `bios/tools` | 1 (`bios_extract.py`, 114295 bytes) | 0 |
| `windows/tools` | 30 | 0 |

**This is a negative result and is stated as one.** Per the caveat in
`ec/annotations/registers.yaml`, a sweep that finds nothing means *not found by
this method* — naming the directories and the commands, not "no other tool has
the shape". The structural sentence is stronger and is separately checkable
(the one definition, the empty import grep), and even it is scoped to the
committed tree today, not to any future one.

## What this does not say

- **Nothing here is a report of a live fault.** `audit_call_targets.py` over
  the committed image exits 0 (`opcode-len-bounds-census.md`'s
  `## Reproducing it`, command 8), and it exits 0 after this change too. The
  `IndexError` above is produced by a buffer truncated *in this snippet*, not
  by any image in the repository.
- **No site "cannot raise."** The `32843` is a margin on this input, and the
  `--self-test` check is a statement about the committed image, not a proof
  about the code. What it does is make the assumption a printed line rather
  than an unstated one.
- **No live test ran.** No EC was opened, no register read back, no hardware
  and no Windows involved. Every number here is a static read of a committed
  file or the output of a command over a committed file.
- **No EC claim.** The subject is a property of Python walking a `bytes`
  object. `REGIONS` is an image map this repository derived; the marker check
  is a Python slice comparison. Neither says anything about the hardware.
- **The line shift is recorded, not hidden.** `region_bounds()`'s docstring
  sits above `relative_survey()`, so `:307,308` became `:314,315` and the
  census's own citations were re-run rather than left stale. The census's sweep
  count is unchanged at 39.

## Reproducing it

Commands 1-3 first, then the snippet. All from the repository root.

```sh
# 1. the pair's own command, and the one that has to be unaffected by the edit
python3 ec/tools/audit_call_targets.py ec/firmware/GMxMGxx_11.800

# 2. the artifact that exercises :315 specifically -- `disp` is a column of it
python3 ec/tools/audit_call_targets.py ec/firmware/GMxMGxx_11.800 \
  --relative-csv | wc -l

# 3. the new line, among the existing ones
python3 ec/tools/audit_call_targets.py ec/firmware/GMxMGxx_11.800 --self-test

# 4-6. the other two tools directories
grep -rn 'OPCODE_LEN\[' --include=*.py bios/tools windows/tools
grep -rn 'disasm8051' --include=*.py bios windows
grep -rcE '\w+\[[a-z_]*\[[a-z_]+\]' --include=*.py bios/tools windows/tools
```

`bash tools/run-tests.sh ec/tools` and the two self-tests are green and pick up
nothing new, which is the point: **this work adds no suite**. The one red suite
in the merged tree, `test_check_cluster_citations.py`, is the merged-tree red
`opcode-len-bounds-census.md` already names; it reproduces on a clean
`origin/main` and is named here rather than fixed.

The snippet needs no committed file of its own. It re-reads the tool, so it is
correct both before and after the docstring.

```sh
python3 - <<'EOF'
import sys
sys.path.insert(0, "ec/tools")
import audit_call_targets as A
import trace_xdata_refs as T
from disasm8051 import OPCODE_LEN, REL_OPCODES

d = open("ec/firmware/GMxMGxx_11.800", "rb").read()
off, magic = T.PD_MARKER
floor = off + len(magic)
print("PD_MARKER %r at 0x%05X is %d bytes -> the slice is d[0x%05X:0x%05X]"
      % (magic, off, len(magic), off, floor))
for cut in (0x18000, 0x20000, 0x20045, floor - 1, floor):
    print("  main()'s marker test on a 0x%05X-byte buffer: %s"
          % (cut, d[:cut][off:off + len(magic)] == magic))
print("  -> a Python slice never raises, so a short buffer fails the comparison")
print("     rather than erroring: the check is a length floor of 0x%05X bytes.\n" % floor)

ceil = max(A.region_bounds(n)[1] for n in A.AUDITED) - 1
print("largest `hi` a caller passes is bank1's 0x%05X; the guard"
      " `i + OPCODE_LEN[op] <= hi` caps the read at 0x%05X." % (ceil + 1, ceil))
print("  floor 0x%05X - ceiling 0x%05X = %d bytes of margin\n"
      % (floor, ceil, floor - ceil))

top = max(off + OPCODE_LEN[op] - 1
          for n in A.AUDITED
          for off, op, _ in A.relative_sites(d, *A.region_bounds(n)))
print("highest index relative_sites() actually reads over this image: 0x%05X" % top)
print("  len(d) 0x%X - 1 - that = %d bytes\n" % (len(d), len(d) - 1 - top))

lo, hi = A.region_bounds("bank0")
i = next(i for i in range(lo, hi - 3) if d[i] in REL_OPCODES and OPCODE_LEN[d[i]] == 3)
trunc = d[:i + 1]
print("vector: truncate the image one byte past 0x%05X (`%s`, a 3-byte form)"
      % (i, d[i:i + 3].hex(" ")))
print("  guard at :170 sees i+3 = 0x%05X <= hi = 0x%05X -> %s, on a 0x%05X-byte buffer"
      % (i + 3, hi, i + 3 <= hi, len(trunc)))
for label, buf in (("committed", d), ("truncated", trunc)):
    try:
        print("  %-9s -> %d site(s) in bank0"
              % (label, sum(1 for _ in A.relative_sites(buf, lo, hi))))
    except IndexError as e:
        print("  %-9s -> IndexError: %s" % (label, e))
EOF
```

```
PD_MARKER b'ITE8850-PD' at 0x20040 is 10 bytes -> the slice is d[0x20040:0x2004A]
  main()'s marker test on a 0x18000-byte buffer: False
  main()'s marker test on a 0x20000-byte buffer: False
  main()'s marker test on a 0x20045-byte buffer: False
  main()'s marker test on a 0x20049-byte buffer: False
  main()'s marker test on a 0x2004A-byte buffer: True
  -> a Python slice never raises, so a short buffer fails the comparison
     rather than erroring: the check is a length floor of 0x2004A bytes.

largest `hi` a caller passes is bank1's 0x18000; the guard `i + OPCODE_LEN[op] <= hi` caps the read at 0x17FFF.
  floor 0x2004A - ceiling 0x17FFF = 32843 bytes of margin

highest index relative_sites() actually reads over this image: 0x1744D
  len(d) 0x40000 - 1 - that = 166834 bytes

vector: truncate the image one byte past 0x0802C (`bc b6 a3`, a 3-byte form)
  guard at :170 sees i+3 = 0x0802F <= hi = 0x10000 -> True, on a 0x0802D-byte buffer
  committed -> 3281 site(s) in bank0
  truncated -> IndexError: index out of range
```

## Follow-ups this opens

None recorded. The hand-off this answers is closed by this file, and the
`--self-test` line it adds is what keeps it closed: if a future image breaks
`hi <= len(d)`, the suite says so. A guard in `relative_sites()` would be
answering a question this write-up argues is the wrong one, so it is not
queued.
