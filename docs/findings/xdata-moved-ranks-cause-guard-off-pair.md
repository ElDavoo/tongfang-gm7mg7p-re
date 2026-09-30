# `cause` opened four registers CSVs and read two, and the two it ignored were the ones the message asked for (issue #905)

**Nothing here is a hardware claim.** No register was read back, no image was
opened, and no laptop, EC or Windows machine is involved. Every transcript below
is the output of a command over committed CSVs or over a fixture the tool's own
`--self-test` writes, with every scratch output under `/tmp` and
`git status --porcelain` printing nothing after the runs. Same framing as
[`xdata-flip-cause-derivation.md`](xdata-flip-cause-derivation.md):3-6 and
[`xdata-moved-ranks-collision-scope.md`](xdata-moved-ranks-collision-scope.md):3-12.

**The calibration comes first, and it is a narrower claim than it looks: no
figure is retracted, because none was wrong.** §7 re-derives §1 of
[`xdata-flip-cause-derivation.md`](xdata-flip-cause-derivation.md) and gets
back the `366/64/439` and `315/124/445` census sizes, the 71/266/23/40 flip
table and the 155 added addresses, and §5 below shows the four-flag transcript
of §2 there is byte-identical after this change. What is corrected here is a
*stated reason*: a docstring and a refusal message that named four input files
where the function under them reads two. Nothing measured moves, and nothing
measured was wrong.

## 1. Four files opened, two read

`added_addresses` took a four-tuple and bound two of its four paths to names
that begin with `_`:

```python
def added_addresses(registers):
    on_a, _off_a, on_b, _off_b = (registers_of(path) for path in registers)
    return set(on_b) - set(on_a)
```

`registers_of` is `{r["addr"]: r for r in csv.DictReader(f)}` — so each of the
four files was opened and fully parsed into a per-address map, and two of the
four maps were then dropped on the floor. The set that survives is a difference
between the two **guard-on** universes and needs nothing else.

The other copy of the same expression is in `registers_report`, which unpacks
all four because it does use them — its perturbed-address sets are
`touches(on_a, off_a)` and `touches(on_b, off_b)` — and prints the *size* of the
added set on a line of its own:

```python
    on_a, off_a, on_b, off_b = (registers_of(p) for p in registers)
    ...
    added = set(on_b) - set(on_a)
    ...
    out.append(f"    {label_b} adds {len(added)} address(es) to the universe and "
               f"{len(added & p_b)} of them are perturbed")
```

`added = set(on_b) - set(on_a)` is the same expression, over the same two
files, in the same file. **That line is where `xdata-flip-cause-derivation.md`
§5's "adds 155 address(es)" comes from**, which matters for what follows: the
count the write-up publishes is already produced by a function that reads all
four files, by a different code path, from a *committed CSV* — so narrowing the
other copy cannot move the number. It is the same set difference over the same
two files, and §7 runs both to confirm it.

## 2. The message and the docstring were wrong about the files and right about the strictness

`main()`'s `cause` branch, verbatim:

> cause needs both generations' guard-on and guard-off registers CSVs; the
> added-address count is one of the two mechanism tests

and `cause_report`'s docstring, verbatim:

> `registers` is required rather than optional here, unlike `across`: the
> added-address count is one of the two mechanism tests, and printing `0` for a
> set the mode was not given would be a wrong answer rather than an absent one.

**The file list was wrong in both, and the strictness was right in both.** The
count is one of the two mechanism tests, and printing `0` for a set the mode was
never handed *would* be a wrong answer rather than an absent one — both
sentences keep that. What was wrong is the set of files: the sentence the
second one reasons about is a set the mode is never handed the guard-off half
of, and the added-address count does not want it. So the docstring now reads:

> It is the two **guard-on** registers CSVs, and nothing else — what this mode
> does with the guard-off pair is nothing, for the reason `added_addresses`
> records.

**This is a correction to a stated reason, not to a figure.** Nothing measured
is retracted: the 155, the 71/266/23/40 table, and the 151-of-155 correction in
`xdata-flip-cause-derivation.md` §5 all come from the same two guard-on CSVs and
are unchanged. What was wrong was the *account* of why the mode wants what it
wants, and the same file records the correction in these words.

## 3. The guard-off pair, and the candidate the mode does not use

**This is a fact about the tree, not a choice of method, and it is the reason
`cause` is membership-level.**

The writer axis is the natural next thing an added-address count could be
computed over. `xdata_register_map.py` builds it inside `components()`:

```python
writers = ({a: touches(group[a], "write") | touches(group[a], "read+write")
            for a in addrs} if writers_on else {})
```

and `touches()` reads one thing:

```python
def touches(entry, bucket: str):
    """The functions of `entry` that used `bucket` themselves."""
    return {f for f, buckets in entry["dirs"].items() if bucket in buckets}
```

`entry["dirs"]` is a per-address `{function: {bucket, ...}}` map, declared as a
`collections.defaultdict(set)` in `blank_entry()` and accumulated per reference
as `entry["dirs"][key].add(bucket)` in the main pass and
`entry["dirs"][key].add(direction)` in the pair-accessor pass, then merged
file-by-file by `absorb()`. **No column of `annotations/xdata-registers.csv`
carries it.** The two columns that look like it are the two the writer axis is
built *from*, and neither is it:

- **`functions`** is a flat sorted touch list —
  `"; ".join(func_label(f, names) for f in sorted(funcs_touched))`. Every
  function that touched the address, with no bucket, so it cannot say which of
  them wrote it.
- **`writers`** is `len(writers)` — an integer. The size of the writer set, not
  its membership.

So a committed registers CSV **cannot** reconstruct the incidence matrix that
`xdata-flip-cause-derivation.md` §6's "necessary-condition proxy" would have to
be promoted past a proxy, and the added set this mode computes is membership
over the address universe because that is what a column can carry.

**The limit is about this input, not about the promotion in principle.** A new
column in `xdata_register_map.py` would carry the per-function bucket map, and
regenerating the committed 1,326-row CSV would write it. That is a different
change with a different blast radius — a column in a shared generated file, and
a schema every consumer of the registers CSVs sees — and it is out of scope
here. What §6's proxy needs is a *measurement* the tree cannot currently
produce on demand; this records why, so the next reader does not re-derive it.

## 4. What changed and what did not

| | before | after |
|---|---|---|
| `cause`'s registers flags | four, all required | two, `--old-a-registers` and `--old-b-registers` |
| `--new-a-registers` / `--new-b-registers` to `cause` | required, parsed, discarded | accepted, not read, named back on **stderr** |
| `across`'s four flags | required together, gate above both modes | unchanged, gate now inside the `across` path |
| `pair`'s `--old-registers`/`--new-registers` | its own pair, outside that gate | unchanged, still outside it |
| `pair`'s and `across`'s printed output | — | byte-identical, diffed over the real pair |

**The gate moved; it did not change.** The `if any(quad) and not all(quad)`
check sat *above* the `cause` branch, so it fired for `cause` too — and a
`cause` run handed exactly the two guard-on CSVs tripped it and died. It is now
inside the `across` path, with the same condition and the same message string.
That is also what makes the message honest: it says *"across needs both
generations' guard-on and guard-off registers CSVs"* and names only `across`,
and after this change that is the only mode it can be reached from.

**The four registered pins into this file did not move.** Every edit above lands
at line 827 or below, and the usage block above every pin kept its line count:

```console
$ grep -rno 'xdata_moved_ranks\.py:[0-9-]*' --include=*.md . | grep -v '^\./vendor' | sort > /tmp/pins_after.txt
$ diff /tmp/pins_before.txt /tmp/pins_after.txt && echo "all 20 pins unmoved"
all 20 pins unmoved
```

20 occurrences before, 20 after, none of them renamed. The enumerator and the
population it reads over are
[`xdata-moved-ranks-pin-decisions.md`](xdata-moved-ranks-pin-decisions.md) §2's;
the eight spellings it lists plus the elided ones it names are all still
pointing at the lines they were pointing at.

## 5. The self-test case, and what it would have caught

The new case drives `main()` rather than the report function, because the
decision of *which files to hand the mode* is `main()`'s. The guard-off
registers CSVs it passes are built to be wrong: an address neither guard-on
universe holds (`0xDEAD`, `0xBEEF`) and a `write` column that would move a
perturbation count had the mode read it. Over the existing D/E census fixtures,
once with the two guard-on flags and once with all four:

1. **stdout is byte-identical** between the two runs, and carries
   `the added set is 2 address(es)` — the same figure either way, because the
   mode does not read the guard-off pair.
2. **the stderr note names both flags** in the four-flag run and is absent from
   the two-flag run, so the note is not unconditional noise.
3. **one guard-on flag exits 2** and the `error:` line names both flags it
   wants, so the missing one is named rather than answered with an added set
   computed from half an input.

A fourth assertion, cheap while the fixtures are in hand: the size
`registers_report` prints is the size `added_addresses` returns over the same
pair. The same expression lives in two places in this file, and this is what
stops them drifting.

**What it would have caught.** Before this change, a `cause` handed a stale,
wrong-generation or unrelated guard-off pair printed the same figures it
prints now — the files were parsed and thrown away — so a wrong file was
indistinguishable from a right one. That is the specific failure
`xdata-flip-cause-derivation.md` §5's own correction is about: a count read out
of prose rather than derived from the CSVs, where editing the prose could move
it. The figure was never at risk, because the figure never came from the
guard-off pair. The **caller** was, and is now told.

The checks were verified by mutation rather than by reading them back: dropping
the stderr note, tolerating one guard-on flag, a consistent future state in
which the mode does read the guard-off pair, a message that names neither flag,
and a one-address drift between the two copies of `set(on_b) - set(on_a)` each
turn one of the four red. The first of those is worth naming: a state in which
`main()` passes the guard-off files and `added_addresses` reads them would
still print the same report, and only the byte-identical assertion distinguishes
it from this one.

## 6. What this does not do

- **No CSV, YAML, threshold or assertion moves.**
  `annotations/xdata-registers.csv`, `annotations/xdata-clusters.csv`,
  `annotations/xdata-cluster-names.csv`, `annotations/registers.yaml` and
  `ec/firmware/` are read-only here, and every scratch output went to `/tmp`.
- **No live run of any kind.** No hardware, no EC readback, no Windows, no
  image opened. Nothing in this change needs one.
- **The writer axis is not built**, and §6's proxy is not promoted past a proxy.
  §3 records why a committed registers CSV cannot carry it, which is all the
  issue asked for.
- **Nothing opened in another repository.** There is no upstream patch here;
  `upstream/` is untouched.
- **No shared document was edited for a number that is correct about the
  past.** `xdata-flip-cause-derivation.md` §9's merged-tree note says the tree
  printed 39 self-test cases, and this change adds one. That note is a record
  of the trees those runs happened on and is left exactly as it is, the way
  §4a-4d asks; the census this file belongs to is
  [`test-line-pin-census.md`](test-line-pin-census.md) and its own run's tail is
  in §7 below.

## 7. The test that proves it

The `--self-test` is this tool's suite and lives inside the tool — this file is
not a `test_*.py`, so `tools/run-tests.sh` does not collect it and nothing
needs registering.

```console
$ python3 ec/tools/xdata_moved_ranks.py --self-test
  …
  ok    a guard-off registers pair built to be wrong leaves `cause`'s report byte-identical: the mode does not read it, and the added set is the difference between the two guard-on universes either way
  ok    the flags the mode was handed are named back on stderr, and the two-flag run -- which passes neither -- says nothing there
  ok    `cause` handed one guard-on flag stops and names both it wants, so the missing one is named rather than reported as an added set from half an input
  ok    the added set `cause` counts against is the same set the size `registers_report` prints, over the same two guard-on CSVs
  all checks passed
```

**The regression that matters most is a transcript.** The four-flag `cause`
invocation published at
[`xdata-flip-cause-derivation.md`](xdata-flip-cause-derivation.md):88-90, run
over the same pair, is byte-identical to the one that block records, and the
same command with the two guard-off flags removed is byte-identical to it:

```console
$ python3 ec/tools/xdata_moved_ranks.py cause \
    --label-a 'the 430-row pair' --label-b 'the 439-row pair' \
    --old-a /tmp/xdata-old/ec/annotations/xdata-clusters.csv --new-a /tmp/old-off-clusters.csv \
    --old-b ec/annotations/xdata-clusters.csv --new-b /tmp/new-off-clusters.csv \
    --old-a-registers /tmp/xdata-old/ec/annotations/xdata-registers.csv --new-a-registers /tmp/old-off-registers.csv \
    --old-b-registers ec/annotations/xdata-registers.csv --new-b-registers /tmp/new-off-registers.csv
cause the 430-row pair -> the 439-row pair
  page 0x0300-0x05FF; the added set is 155 address(es)
…
note: cause reads neither guard-off registers CSV; --new-a-registers and --new-b-registers were parsed and not read
```

with the two guard-off flags removed, stdout byte-for-byte the same and stderr
empty. `the added set is 155 address(es)`, the population block, `408/31/37`,
`mean +6.80` and `1219 membership(s) over 1171 distinct address(es)` are all
where that block has them. The note goes to **stderr** deliberately: putting it
in the report would have edited a published transcript to record a change to
the tool that changed no figure in it.

**§1 of the merged write-up still reproducing on the merged tree**, as
[`xdata-flip-cause-derivation.md`](xdata-flip-cause-derivation.md) §1 spells
it — `xdata_register_map.py --check`, a
`git worktree add --detach /tmp/xdata-old e169a0e4` of the historical tree, and
both `--no-eq-guard` regenerations to `/tmp`:

```console
$ python3 ec/tools/xdata_register_map.py --check
  names: seeded 9, exact 0, carried by overlap 0, tied, not carried 0, with no name 430
ec/annotations/xdata-registers.csv: 1326 rows match a fresh generation from the committed tree at threshold 0.5
ec/annotations/xdata-clusters.csv: 439 rows match a fresh generation from the committed tree at threshold 0.5

$ git worktree add --detach /tmp/xdata-old e169a0e4
$ cd /tmp/xdata-old && python3 ec/tools/xdata_register_map.py --no-eq-guard \
    --out-clusters /tmp/old-off-clusters.csv --out-registers /tmp/old-off-registers.csv
wrote /tmp/old-off-registers.csv: 1171 rows
wrote /tmp/old-off-clusters.csv: 439 rows
$ cd - && python3 ec/tools/xdata_register_map.py --no-eq-guard \
    --out-clusters /tmp/new-off-clusters.csv --out-registers /tmp/new-off-registers.csv
wrote /tmp/new-off-registers.csv: 1326 rows
wrote /tmp/new-off-clusters.csv: 445 rows
```

**The `366/64/439` and `315/124/445` census sizes reproduce, and so does the
71/266/23/40 flip table and the 155**, so every figure in
[`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md) §2–§4 still describes
this tree. The mechanical half:

```console
$ bash tools/run-tests.sh ec/tools
$ python3 ec/tools/gen_findings_index.py --check
$ python3 ec/tools/check_findings_frozen.py
$ python3 ec/tools/check_no_append_logs.py
$ python3 ec/tools/check_no_conflict_markers.py
$ .github/scripts/agent-gates.sh
```
