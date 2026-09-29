# Two of the three presence checks key their per-file container and pin that shape; the third has nothing to scan (issue #371)

(2026-09-28, issue #371. Static reading and commands over committed text. No
Ghidra, no EC, no BIOS re-export, no hardware, no Windows.)

`docs/findings.md` §14j records a regression #346 landed on, and names its two
halves: *"§14a is not only 'do not read a file once per row'; it is also 'do not
scan a collection once per row', and the fix is keyed on whatever the join key
is."* The Windows check that regressed built a flat list of `(name, addr)` pairs
and scanned it once per row; `decompile_native.py` now keys its markers on
address, and `--self-test` pins that **structurally** — it reads `_c_markers()`'s
return value back out of the module and asserts it is a dict.

This branch gives the BIOS copy the same guard. `_c_markers()` is lifted out of
`c_presence_problems` to module level (`bios/tools/bios_extract.py:1435`), and
`--self-test` reads it back the same way. Before this change there was nothing
to read: the container was a local inside `c_presence_problems`, so no caller,
and no assertion, could reach it.

## The three copies, and which two have a container worth pinning

Each tool pairs every index row to the function its `.c` declares. That means
each one has to hold "what this one file declares" in memory, and the three
hold it in three different shapes, written per tool:

| | where the per-file value is built | shape | collection? |
|---|---|---|---|
| EC | `ec/tools/build_ec_decompile.py:1433` | `(addr, name)` — two scalars | **no** |
| BIOS | `bios/tools/bios_extract.py:1435` | `({ADDRESS_UPPER, ...}, {name, ...})` | yes |
| Windows | `windows/tools/decompile_native.py:389` | `{address: {names}}` | yes |

**The EC's copy has nothing to scan, and must not be given a guard.** One
`.c` per function: `ec/decompiled/<program>/<addr>.c` is one function per file,
so a single `readline()` of the header (`EC_C_HEADER`,
`build_ec_decompile.py:1387`) and one `re.match` is the whole of it. There is
no collection, so there is no lookup-versus-scan distinction to protect: a
guard there would assert something that is true by construction and would read
as coverage it is not. The issue's asymmetry argument is correct, and this
branch acts on it by leaving the EC alone.

**The other two are the same exposure at different scales, and both are keyed.**
The BIOS's largest module is `Setup.c` at 293 separators; `OemServiceSmm.c` is
118 and `OverClockSmiHandler.c` is 41, over 955 rows naming 38 files. The
Windows `ACPIDriverDll.c` declares 10,141 separators. The BIOS exposure is
roughly a tenth of the Windows one in rows (955 against 10,141) and roughly 3%
in the widest single scan (293 against 10,141) — so **nothing here says a 5.4 s
bug is sitting in the BIOS run today.** The claim is narrower: the BIOS had the
identical unguarded shape, at a scale where the guard costs nothing to carry.

## The two keyed shapes are NOT the same shape, and this branch does not unify them

This is the one thing worth not being vague about, because "the container is
keyed" reads like a shared shape and it is not.

- **Windows is `{address: {names}}` — one dict, names nested under the address
  they were declared at.** A row has to match one of the names declared *at its
  address*, so the address is the join key and the names hang off it. A set of
  names per address rather than one name, because a duplicate separator would
  otherwise be silently discarded.
- **BIOS is a 2-tuple of two independent sets** — addresses in one, names in the
  other. A BIOS row's name is matched **file-wide**: `row_name in names`, against
  every name the file declares, with no record of which separator produced which.
  That is not an accident of the current code, it is what the data supports: the
  address set answers "does this file declare that address", the name set
  answers "does this file declare that name anywhere", and the two questions are
  genuinely independent here.

Converting the BIOS container to `{address: {names}}` would redefine what a name
match *is* and would move the pinned `_nm == 171` and §14j's 171/754/29/1
classification table. That is a behaviour change to a measurement §14j
deliberately does not assert, and issue #371 does not ask for it. So the shapes
stay different, and the docstring of the new `_c_markers()` says so at the point
where a future reader would otherwise assume a shared shape.

## The negative control: the regression is invisible except to this one check

The issue's central claim is that a per-row scan is invisible in the output, and
that is testable rather than arguable. Measured on this tree, 2026-09-28:

```console
$ python3 bios/tools/bios_extract.py --work "$scratch" --check > before.txt
$ python3 bios/tools/bios_extract.py --work "$scratch" --check > after.txt
$ diff before.txt after.txt && echo IDENTICAL
IDENTICAL
```

Then `_c_markers()` was temporarily reverted to the Windows regression's
original form — return the flat list from `findall` and scan it per row, with
`any(a.upper() == addr for _n, a in markers)` in place of the set membership —
and both modes re-run:

- `--check` **byte-identical** to the unmodified baseline, and exit 0. The
  presence line still reads 38 distinct files; the 171-of-955 name figure does
  not move.
- **All 78 pre-existing `--self-test` assertions still pass.**
- **Exactly one check fails**, the new one, with `(type list)` as its detail.

That is the whole case for the guard: on this tree, the regression #346
describes is a silent one, and the only thing that catches it is an assertion
about the container. The mutation was reverted and both modes pass again (80
assertions, `--check` byte-identical to the unmodified baseline).

**The mutated copy is not committed.** A deliberately-slow duplicate
implementation kept in the tree to prove an `isinstance` check works is a second
copy of the logic to keep in sync, for no guarantee the type assertion does not
already give — the assertion *is* the negative control, and it fires on any
machine in milliseconds.

## Why 300 markers, and why no timer

The fixture writes a `.c` carrying 300 `// ==== <name> @ <addr>` separators and
builds 300 matching rows, all of which must pair on one file read.

**300 is a round literal, not `len()` of `Setup.c`'s markers.** Pinning 293
would make the assertion a value every re-export has to edit — the shape of
assertion CLAUDE.md's third bullet rules out, and the one
`ec/tools/test_check_pin_table_by_cited_file.py` exists after. What is asserted
is a claim about the container (it is two sets, holding 300 addresses and 300
names), not a census of the tree. A marker-count collision in a per-module
export would make the sets smaller and fail the check, which is the right
direction to fail.

300 is also *honest for a real module* here: `Setup.c`, at 293, is the largest
in the tree, so the fixture is a full-size module rather than a toy. The point
is that the keyed and scanned forms are two genuinely different computations at
that size, not the same one written twice.

**No wall-clock bound, for the reason §14j sets out at length.** A timing
assertion loose enough not to be flaky is loose enough to pass the regression it
was written for — §14j records that the quadratic form takes 0.18 s on the
Windows self-test's 2,000-row fixture, far inside any usable bound, while the
real regression was 5.4 s at 26× the work. So this guard pins the **shape**,
and makes no timing claim about the BIOS `--check` at all. §14j's 0.34 s figure
for that command stands as the record; nothing here re-measures it, and a
refactor plus an assertion is not a reason to add a number to a document nobody
can edit.

The check runs in CI with no pipeline change: `bios_extract.py` is already in
`.github/scripts/agent-gates.sh:129`, and the default arm calls `--check` **and**
`--self-test` (`:283-286`).

## Six cells in the pin census, and why that is not scope creep

The §14j amendment is +9 lines in `docs/findings.md`, and that file is a
**citing** file: `docs/findings/test-line-pin-census.md`'s table records the
citing line of every `test_*.py:NNN` the committed markdown carries, and
`check_pin_table_rows.py` exists to make a moved citing line loud. Six rows
point into `docs/findings.md` below §14j, so all six moved by 9 and were
re-anchored — `:4385`→`:4394`, `:4387`→`:4396`, `:7412`→`:7421`, `:7633`→`:7642`,
`:7694`→`:7703`, `:9478`→`:9487`.

Each was checked rather than assumed: for every one, the line at the new number
was compared against the line at the old number **on `HEAD`**, and all six are
byte-identical, so each verdict is **re-read rather than carried** — which is
the wording the file's own prior re-anchorings use (`#1183`, `#489`, `#904`).
That is what makes this a mechanical re-anchoring and not a re-judgement, and
the verdict cells say so at the point a reader checks it.

**The alternative was considered and rejected: a line-neutral §14j edit.** The
amendment could have been compressed to fit the paragraph's original 8 lines
and shifted nothing. It was not, because the message the issue asks §14j to
carry does not fit in 8 lines — the existing 8 already spend 607 characters,
and the addition is ~190 — so the choice was between a truncated frozen record
and a documented re-anchoring. Shrinking a record in `docs/findings.md` to dodge
a line count is the kind of edit-around-the-check that costs more later than the
re-anchoring does now.

At `HEAD` this suite is **already red**, on two unplaced pairs this change does
not touch: `docs/agent-pipeline.md:409/419` and
`0751-append-unchecked-marks.md:221/246`. The full suite's failure set is
identical with and without this branch — same failing test names, on both trees
— so this is verified not to have made a pre-existing red redder. Those two
pairs are somebody else's in flight and are left alone.

## What this opens

The container shape was written per tool rather than derived once. After this
branch the tree carries three shapes and two guards, and the reason the third
needs no guard — one function per file — is a property of the EC's *export
layout*, not of the separator grammar. Whether the separator grammar and marker
extraction should be one shared helper across `ec/`, `bios/` and `windows/`, or
whether three documented shapes are the right end state, is a real question this
change does not answer. It is worth its own issue: the answer depends on whether
the *name* match is per-address or file-wide in each component, which is a
semantic difference between the components and not a refactor that preserves
behaviour.

Note also that this branch's guard is about **shape**, and a shape guard says
nothing about whether the membership test inside is the right one. The Windows
copy's `{address: {names}}` can express "the name at this address"; the BIOS
copy's file-wide name match cannot, and §14j's 171 figure is the measurement of
what that costs. That is a separate question, and it is not answered here.

## Not a live test, and not a claim about the export

No laptop, no Windows machine and no Ghidra run is reachable from here. Every
figure in this file is arithmetic over committed text or a `--check` /
`--self-test` run of this repository's own tool, reproducible from the repo root
with the commands shown, on 2026-09-28. No register was read back, no capture
taken, no export regenerated; `bios/decompiled/*.c` is byte-for-byte what the
tree already carried, which is why `--check`'s output is identical either way.

The BIOS `name_basis` grades, the 171/754/29/1 name classification, the
38-reads-for-955-rows figure and every `c-digests.csv` row are unchanged by
this branch, and are not re-asserted as new — the pre-existing pins on them
(`bios_extract.py:1931-1944`) are left exactly as they were.
