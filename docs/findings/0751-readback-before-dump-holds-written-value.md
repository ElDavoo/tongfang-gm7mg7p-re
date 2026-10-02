# §4.6 said "still" without reading the dump that would support it (issue #1401)

The write-up for [issue
#1401](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/1401), which
follows #202 and #387 on the same section. #202 made §4.6 *a coverage
statement before it is a comparison*; #387 gave the comparison the second half
it needs, a value to compare the byte against. This is the third member of that
family and the first that is not about an input that was left out: the
comparison was taken, and what it was printed as overclaimed.

**Offline throughout, and nothing here is a claim about the machine.** No EC was
read, no §3 run was performed, no laptop or Windows box was reached, and no
register was observed. Every transcript below is this tree's Python over the
committed fixtures in `ec/tools/testdata/`, whose own headers read
`CONSTRUCTED INPUT, NOT A CAPTURE`. The one dump that does something the
committed set cannot is built per run by rewriting a single byte of a copy of
§6's own into a `tempfile` directory. What is under discussion is which files
were handed in and what can be read out of them.

---

## The word, and the file that would back it

`report_readback` prints one of two sentences, and both are a comparison of one
number against another:

```
  the last dump still holds the written 0xA0. Per CLAUDE.md that is a readback,
  not evidence the EC acted on it.

  the last dump holds 0x10, not the written 0xA0 -- something put it back; §3a's
  service-stopped run is what separates the vendor service from the EC.
```

`here` is the block's group of `--dump`s in command-line order, so `here[-1]` is
the last file handed in and is what §6's own command block means when it says
the readback is taken from the final `--dump`. **"Still" is the only word in
either sentence that is not a statement about that one file**, because it says
the value survived the write, and surviving is a claim about what the byte held
before it. Nothing read `here[0]`.

`report_dumps` had already read it and thrown it away. Two lines above the
verdict it prints every file's byte:

```
  ...-a0-before-0700.txt: 0x0751 = 0x10
  ...-a0-after-0700.txt: 0x0751 = 0xA0
```

So on a §6 run — which hands the pair in before-then-after — the file that
would support "still" is on the page, in the group, in the order the procedure
specifies, and unused.

## What a write that did not land looked like

§3's step 0 takes the `-before-` dump before any write. Set the `0x0751` byte of
§6's own before-dump to what the block is about to write, and grade the block
the way §6 grades it:

```
$ python3 ec/tools/grade_0751_isolation.py \
    ec/tools/testdata/0751-isolation-run/2026-01-01-0751-isolation-0700-07ff.csv \
    --dump <copy with 0x0751 = 0xA0> \
    --dump ec/tools/testdata/0751-isolation-run/2026-01-01-0751-isolation-a0-after-0700.txt \
    --block 0xA0 --wrote 0xA0
```

Before this change that printed, byte for byte, the section a successful write
produces — calibration clause included:

```
  the last dump still holds the written 0xA0. Per CLAUDE.md that is a readback,
  not evidence the EC acted on it.
```

Those files admit two readings, and neither is available from the last dump:
**the write never reached the byte**, or **the file named `-before-` is not
before it**. Both are facts about the run, and both are readings the operator
has to be told are still open rather than have the section's wording settle
between them.

Handing in a single `--dump` was the same shape: `here[0] is here[-1]`, and the
same sentence printed. That one is not a defect at all — it is a real branch,
because a run is not required to hand in a pair.

## The three branches, and why each is worded the way it is

Driven by the block's first dump's `0x0751` byte against the written value, and
each case is about what these files can be read as saying:

1. **The before-side demonstrably held something else.** Both existing verdict
   lines print unchanged, byte for byte. This is the case they were written for,
   and every existing assertion over the committed fixtures sits here, so the
   branch is untouched rather than reworded: everything the section said about
   those files remains true of them.
2. **The before-side already holds the written value.** A line of its own,
   naming what it leaves open — the write did not take, or the dump named
   `before` was taken after it — and saying the files do not separate them.
   **"Still" is not printed**, because that comparison is exactly the one the
   before-side fails to support. The clause "nothing here separates the two" is
   load-bearing rather than a courtesy: the line has to say what the files
   admit, not pick between two things only the machine can distinguish.
3. **One `--dump` for the block.** The value comparison and its calibration
   clause still print; the word goes, and a line of its own says why.

Branch 3 settles the question the issue posed — *is a before-side required for
the positive verdict, or does it only disqualify the positive verdict?* **Only
disqualifies.** Refusing the comparison outright would discard a fact the
operator can use (what the byte holds now) over a missing one (what it held
before), and §6 does not require a pair.

A first dump that does not reach `0x0751` — a `0f00` dump passed first, say — has
no before-side value to compare against. That is not any of these three, and the
section reads exactly as it always has. Pinned, because a line announcing a
before-side that is not there would be a claim about nothing.

## Where the new read sits, and why not beside the other notices

The three precondition notices are grouped ahead of any verdict: coverage, then
the unnamed value, then the `--wrote`-against-the-`§6`-name disagreement. The
new read does **not** join that group, and that is a deliberate departure from
where it would sit most naturally.

Those notices are statements about an input that was left out. The new lines are
not: they are about what the comparison that *was* taken can support, and the
verdict sentence they qualify is the only thing they qualify. Reading them
beside the guards would let them print over a run whose readback was never
taken — `--dump <after-0700> --dump <0f00>` is a group whose first dump holds
the written value and whose last dump holds no `0x0751` at all, and "these files
do not show the write landing" over that is a conclusion about a comparison the
page never made. So the read sits below both guards: a before-side is only ever
read against a readback that was taken.

It also fires on the `last != written` arm, which is worth stating because it
reads as a surprise the first time. §6's command block warns about handing the
pair in the wrong order, and that mistake is not something the bytes can be
caught doing — nothing distinguishes a swapped pair from a run whose before-side
happens to hold the written value. What the section can say is the one thing
both have in common, and on a swapped pair it is the useful one: no file in the
group shows the byte anywhere but the written value before the last dump. The
`something put it back` verdict beneath it is unchanged.

## What this does and does not settle

- **The section's positive verdict still means what it meant.** On a run with a
  before-side that held something else — which is every committed fixture, and
  every §6 run that took step 0 before it wrote anything — the sentence is
  identical to what it was.
- **`0x0751` is unchanged.** `ec/annotations/registers.yaml` is not touched: its
  `MANUAL_FAN_CTRL` row stays `present-untested`, because nothing here ran a
  write or observed the EC. The point of the fix is that the section stops
  sounding as though it had.
- **No live readback happened, and none is implied.** The transcript above is a
  Python process reading files. §3's step 0 / step 6 bracket on real hardware
  remains a human's to take, and whether `0x0751` does anything on this machine
  is still exactly as open as it was.
- **`docs/findings.md` is not edited.** This is a file of its own, per
  `CLAUDE.md`; the section counter there is closed and nothing was added to it.

## Two things this opened, left for a follow-up

- **`something put it back` on a one-dump run.** That sentence is the same
  shape of claim `still` was, one level down and not yet gated: a single dump
  that does not hold the written value is equally consistent with the write
  never having landed and with a writer having taken it back, and the section
  picks the second. Branch 3's line is printed above it and says what the
  files cannot separate, which helps but does not fix it. Aligning that arm is
  the same change one branch further, and it is not taken here.
- **`--dump-pair` reads the same two files at a different strength.** A pair
  whose before file already holds the written value is reported as `unchanged`
  for `0x0751`, and §6 already says a dump diffed against itself "proves
  nothing". §4.6 is now the stronger of the two readers on this shape, which is
  the right way round, but the `--dump-pair` section has not been brought up to
  it. The issue raised this and left it out of scope; it is recorded here so the
  next pass starts from it.

## Where the rest of it lives

- `ec/tools/grade_0751_isolation.py` — `report_readback`, and the precondition
  paragraphs in that function's docstring and in the module docstring. Growing
  those moves the file under `measure_mark_provenance.py`'s `CITATIONS`, which
  pins sites by line and re-reads the quoted text on every run; those rows are
  re-anchored to the lines that now carry their text, by the procedure
  [`0762-provenance-citation-reanchor.md`](0762-provenance-citation-reanchor.md)
  records. Only the line numbers moved — the quoted text and the `what` beside
  each one are unchanged, because each still describes the line it lands on.
- `ec/tools/test_grade_0751_isolation.py` — `BeforeSideReadbackTests`, the
  last class in the file. Appended rather than inserted, for the reason the
  class above it records: line pins across this suite's write-ups and the
  per-pin table in [`test-line-pin-census.md`](test-line-pin-census.md) cite
  into the file below `GradeTests`, and a class added anywhere else moves all of
  them onto a line that no longer says what its sentence says it does.
- `docs/hardware-tests/manual-fan-ctrl-0751-isolation.md` — §4.6 item 6, whose
  list of the preconditions a section can end on named two and now names the
  before-side's as well.
- [`0751-readback-written-value-notice.md`](0751-readback-written-value-notice.md)
  and [`0751-notice-two-moments.md`](0751-notice-two-moments.md) — the
  neighbouring work on what §4.6 is allowed to conclude, which is what this
  continues.