# The strict reader described two moments as one (issue #786)

The write-up for [issue
#786](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/786), which asked
for a decision rather than for a change: **is `read_capture`'s two opens
correct, or is one?** #750 added the second one and recorded the count in
prose, and #749 had already removed the same pair of opens from the *notice*
path without the two being connected. This decides **one open**, states the
step in #784's reasoning that no longer follows, and pins the count on the
reader that produces the marks and the changes.

Nothing here is evidence about the machine. No §3 run was performed, no Windows
box was reached, no EC was opened, no mark was typed and no capture was read.
The whole of the evidence is offline behaviour of a tool over hand-written rows
in a `tempfile` directory, and the four-fixture table below is measured on this
tree by the command in "How to re-check this".

The issue's own line numbers are not this tree's — several merges have moved
everything below `grade_0751_isolation.py`'s import block since it was filed —
so every call site below is named by function. The counts are this tree's and
are dated with it.

---

## The two opens, as the code stood

`read_capture` was the only reader in the module that opened a capture twice:

| what | before | after |
|---|---|---|
| the mark | `path_starts_with_bom(path)` — its own binary `open`, three bytes read | `starts_with_bom(raw)` on the one buffer |
| the rows | `capture_rows(path)` — a second `open`, in text mode, for the whole file | `rows_from_bytes(raw)` over the same bytes |

`capture_snapshot`, the notice's reader, was already `open(path, "rb")` + one
`read()` + both questions off the buffer (#749), and its docstring said so.
The strict reader was the half that was left.

**The measured open count was 2, on both the clean path and the decode path.**
See "The four fixtures" and the falsification below.

## The second writer is the premise, and here it bites harder

This part is [#749's](0751-notice-two-moments.md) and is not restated at
length, but the strict reader is where the same argument costs more, and the
difference is worth being exact about:

- §3 runs three `--mark --csv` watchers against one capture, and
  `CsvSink.row` flushes every row, so **a capture is a file with a second
  writer on it by design**. That is not a hazard the design tolerates; it is
  the procedure.
- On the notice path, a row landing between the two reads made one section of
  the printed notice disagree with another. On the strict path it does not
  merely read oddly: **it changes the grading.** `normalised_rows` strips the
  mark off the first field of every row, so a file re-saved between the two
  opens was graded as though it carried no BOM — no refusal, no census, and
  the two moments disagreeing about whether the file was the format's.
- The window is microseconds, and grading happens after the run has finished.
  **This has not been observed and no operator is claimed to have hit it.**
  That is the calibration, and it is also the argument for pinning the count:
  an invariant this repository pins is pinned precisely because the unobserved
  case is the one that arrives.

## The decision: one open, and the step in #784's reasoning that no longer follows

`read_capture` now opens the path in binary, reads it once, asks
`starts_with_bom` of those bytes, raises `bom_refusal` before any row is looked
at, and streams the rows off the same buffer. `path_starts_with_bom` is
deleted: it existed only to open a path for three bytes, and with the fold it
has no caller.

[0751-file-refusal-order.md](0751-file-refusal-order.md) (#784) decided, days
earlier, that `path_starts_with_bom` "remains `read_capture`'s own three-byte
open rather than a third read", and used the laziness of `capture_rows` as one
reason to reject an option. #786 revisits that. The earlier reasoning is not
withdrawn wholesale and the step is named so a reader who found it persuasive
can see exactly which part no longer follows:

> **Correction (2026-10-02, #786), leaving #784's text above as it was
> written.** #784 rejected an option partly because folding would require
> `read_capture` to "decode the whole buffer up front, abandoning the laziness
> `capture_rows` documents". **That conflation is what #786 removes.** Reading
> a file into bytes is not decoding it. The row stream is a generator over a
> *lazily-iterated* `TextIOWrapper`, so an undecodable byte still comes out of
> the loop at the row it stopped on, `read_capture` still names one row rather
> than the whole file, and `refused_capture_rows`' fix-one, re-run,
> meet-the-next contract is intact. The claim that the fold costs laziness was
> true of the option as #784 framed it and is false of the fold, because
> #784's framing had a whole-buffer decode in it and this does not.
>
> #784's *other* reason is untouched and still holds: the mark goes first
> because it is decidable from three bytes without the file decoding at all.
> #786 strengthens it — with one buffer, the mark is asked of the raw bytes
> before any decode is attempted, so the order now holds structurally rather
> than by program order.
>
> The "seventh open" sentences in `docs/findings.md`,
> `0751-capture-row-shape.md` and `windows/tools/ec_watch-marks.md` are
> corrected in place beside themselves, per §4a-4d.

The precedent is in the same file, over the same corpus: `capture_snapshot`
already did exactly this, and the largest capture this repository commits is
`evidence/ec-watch/2026-09-18-profile-switch-0400-07ff.csv` at a little over
200 KB, so buffering is not a cost the grader is newly paying.

## What changed in the tool

`ec/tools/grade_0751_isolation.py`. Its suite and the citation table that pins
into it are under their own headings below, and the write-ups are corrections
beside the sentences they falsify.

- **`rows_from_bytes(raw, errors=None)`, new, at the end of the file.** The
  one place the row shape and the decode policy are stated: a generator over
  `csv.reader` over a lazily-iterated `TextIOWrapper` over a `BytesIO`,
  wrapped in `normalised_rows`. It is at the end rather than beside its callers
  for the reason `MarkBeforeCodecTests` is at the end of its suite — prose
  across `docs/findings/` pins lines of this file by number.
- **`capture_rows`** keeps its signature and stays a generator, and its body
  now delegates: read the file's bytes, hand them to `rows_from_bytes`. Its
  docstring's "a seventh open of the same file, three bytes" sentence is
  corrected in place.
- **`read_capture`** reads once and iterates the shared helper over the same
  bytes. Signature and the `(marks, changes)` two-tuple are unchanged —
  `main()`, `grade_gpu_door.py`, `check_capture_claims.py` and
  `manual_fan_ctrl_probe.py` unpack it, the `windows/tools` suites assert the
  notice's half of the contract, and none of them was touched.
- **`capture_snapshot`**'s strict pass goes through the same helper. This is
  not tidiness. `MarkBeforeCodecTests` holds
  `assertIn(str(bare_exc), refused[0][1])`, and one side of that is
  `read_capture`'s exception while the other is the notice's. Two mechanisms
  producing one message is the situation #784 exists to remove, so one code
  path is what keeps the assertion true *by construction* rather than by two
  decoders continuing to agree. The lenient branch keeps `errors="replace"`.
- **`capture_lines`** stopped being `readlines()` and became a generator over
  the same wrapper. That is the change that keeps the laziness: `readlines()`
  decoded the whole buffer before the caller saw a line, which is exactly the
  thing `read_capture` must not do on a large capture.
- **`path_starts_with_bom`** is deleted, and `starts_with_bom`'s docstring now
  names the callers it has, both of which hand it a buffer they had to read
  anyway.

## The four fixtures, before and after

Measured on this tree by counting `builtins.open` against the target path
around `read_capture`, on the same four hand-written fixtures #784 used. The
message column is kept because the anti-drift contract is about the words as
much as the count.

| fixture | opens before | opens after | the refusal, after |
|---|---|---|---|
| **A.** BOM + cp1252 `é` — both faults | 1 | 1 | `bom_refusal`, exactly equal on both readers |
| **B.** BOM only, decodes | 1 | 1 | `bom_refusal`, exactly equal |
| **C.** cp1252 `é` only, no BOM | 2 | **1** | bare `UnicodeDecodeError`, contained in the notice's sentence |
| **D.** neither — the plain path | 2 | **1** | none; the two-tuple comes back |

**A and B were already one open**, and the table says so rather than implying a
wider win than there is: on the marked paths `read_capture` raised before the
second open was reached, so the probe was the only open. That is also why A and
B are not the falsification below and C and D are — the marked paths cannot
tell the two implementations apart on the count, and they are in the suite for
the *order* (the refusal is named before any row) and for `bom_refusal` staying
the one sentence.

## The cross-chunk decode, measured

`0751-notice-two-moments.md` records a concern it did not test: *"the snapshot
decodes the whole buffer where `read_capture`'s text layer decodes a chunk, so
the `position` inside the exception can in principle differ for a file larger
than that chunk"*, and — *"the case that would expose it has not been
written"*. It is written now, and the measurement is recorded with whatever it
turned out to be rather than as a general claim about `TextIOWrapper`.

Fixture: the same comment-and-header shape as every other case in this suite,
grown past 200 KB, with one undecodable byte inside the **last row's label** so
every row ahead of it is well-formed and the mark row still parses as one. The
bad byte is at file offset 200213 of 200218.

| what | measured |
|---|---|
| what `read_capture` raises | `'utf-8' codec can't decode byte 0xe9 in position 3605: invalid continuation byte` |
| rows produced before the loop raised | 969, of 988 |
| `200213 % 8192` | 3605 — the position is the byte's offset **within the decode chunk**, not within the file |
| does the notice's reason contain that exception verbatim | yes |
| the same fixture on the pre-#786 module | the identical string, `position 3605` |

Three things follow, and only the first is new:

1. **The two readers agree**, and now for the right reason. They call the same
   function with the same bytes. Before the fold they agreed *on this
   fixture*, which is a fact about this measurement and not a guarantee — the
   property the anti-drift suite actually needs is the one that now holds by
   construction.
2. **`position` is chunk-relative.** It is `TextIOWrapper`'s own position in
   the 8 KiB it was decoding, and it is not a file offset. This is a property
   of the tree as measured, not a promise about every interpreter, and the
   reason #749's concern was worth writing down.
3. **The laziness is real, not asserted.** 969 rows came out before the byte
   stopped the loop, which is what a whole-buffer `readlines()` could not have
   done. `read_capture` cannot show this itself — it raises, and the marks it
   had built go out of scope with the exception — so the case walks the row
   stream directly.

## The tests, and what each one can catch

A new class at the end of `ec/tools/test_grade_0751_isolation.py`,
`StrictReaderOpenCountTests`, borrowing `count_opens` by class attribute the
way `MarkBeforeCodecTests` does, and adding one helper beside it:
`count_opens_raising`, which is the same counter keeping the exception instead
of the return value, because two of this reader's three ways out refuse and a
refusal is where the count decides which row the error names. Its own class
rather than a third case folded into `ExistingMarkLabelTests` for the placement
reason that class's docstring already states, and because the existing case is
**named** for the notice's two paths: extending it in place would have given
one case a name covering two readers and pinned a line that every following
merge moves. The issue's "extend it to drive `read_capture`" is satisfied by the
pair, and the existing case is left byte-identical.

1. **`test_the_strict_reader_opens_a_clean_capture_once`** — one open on the
   plain path, with the marks and the change row asserted beside the count, so
   a reader that read nothing and returned something constant is not green.
2. **`test_the_strict_reader_opens_an_undecodable_capture_once`** — one open on
   the refusal path, and the exception still names the declared codec.
3. **`test_a_marked_capture_opens_once_and_is_refused_before_a_row`** —
   one open on the marked path *and* `bom_refusal` verbatim *and* no hex
   complaint, in one case: the count and the order are the same claim here,
   because the second open is what the refusal exists to prevent.
4. **`test_the_no_mark_control_opens_once_and_refuses_over_the_codec`** — #784's
   control, in his shape. The three mark bytes taken off and nothing else
   changed: one open, and the *other* refusal. Without it, a `read_capture`
   that opened the file zero times, or that refused everything with a reason,
   would be green on all three cases above.
5. **`test_a_bad_byte_past_the_first_chunk_still_names_one_row`** — the
   cross-chunk case above, in code.

### The falsification, run rather than claimed

Cases 1–3 were run against the pre-#786 module — `git show
HEAD:ec/tools/grade_0751_isolation.py` loaded whole — counting
`builtins.open` on the same three fixtures. The result:

| fixture | against `HEAD` | against this tree |
|---|---|---|
| clean | **2** | 1 |
| undecodable | **2** | 1 |
| marked | 1 | 1 |

The first two fail there, which is the demonstration. **The third reads 1 on
both**, and it is recorded as measured rather than rounded up: the probe was
the only open, because the refusal is raised before the second open was ever
reached. Cases 1 and 2 are the falsifiers; case 3 is in the suite for the
order, and this table is why it should not be read as one.

## What this does **not** fix, stated plainly

- **The file still moves.** One `open()` is one moment, not a lock. A mark that
  lands after the read is still graded, by the whole-file grading later — which
  is what the notice's closing paragraph already tells the operator. What the
  fold removes is the moment *inside* one read, where the mark and the rows
  could come from different files. It does not make the read atomic and does
  not claim to.
- **[#767](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/767) is a
  different site and is left alone.** `main()` reads the same capture twice
  over, once through `read_capture` and once through `read_early_exits`.
  Fixing it changes nothing about how many times `read_capture` opens the
  file, and `0751-notice-two-moments.md` already deferred it for a reason that
  still holds: taking it over one read is a change to the grader's own grading
  path with its own test surface, and bundling it into a strict-reader fix
  would be a half-fix smuggled in. This change does the strict reader's half
  and writes the residual down instead.
- **Two readers outside this module still spell the `ts`/`#` test out with no
  strip** — `check_capture_encoding`'s `count` and `grade_timer_sweep.load`,
  each a second copy of `skippable_row`, and a BOM'd header is a data row to
  both. That is #784's and #750's residual, unchanged here, and it is named in
  `capture_rows`' docstring rather than fixed by this.
- **`0751-file-refusal-order.md` cites `check_site_census.py` as "a tree that
  counts them".** Reading the tool does not bear that out: it joins the
  `0x086x` opcode sweep against the decompiled-C XDATA census and has nothing
  to do with capture reads. The citation is left standing and flagged rather
  than rewritten, because a corrected sentence in a shared write-up is a merge
  conflict for no gain — but a reader checking whether the open count is gated
  anywhere should know that this is not the gate.
- **Whether the format should ever accept a BOM.** #748 decided the codec and
  #750 made the mark a refusal. Nothing here orders or re-homes that question.

## One thing this change did beyond the issue, and why

The issue's scope was the strict reader. `measure_mark_provenance.py`'s
`CITATIONS` table pins **line numbers** into `grade_0751_isolation.py`, and
`ec/tools/test_measure_mark_provenance_citations.py` is a gate that asserts
every pin resolves at the line it quotes. Deleting `path_starts_with_bom` and
rewriting the docstrings around it moved those lines, so the pins had to move
with them or a green suite would have gone red. The pin whose target line this
change deletes — the `path_starts_with_bom` call — is retargeted to
`read_capture`'s new mark test, with a comment recording the move; the rest were
re-anchored to the line their quoted text now sits on, which the same test
verifies.

That is more than the issue asked for and less than a repair of the whole
table: no pin was re-pointed at a *different statement*, only at the same
statement one line down, and the tool's other findings are untouched.

`check_page` is the other half of that contract and it is the half that
reddened. It requires every `path:line` in `CITATIONS` to be named verbatim in
`0751-mark-provenance-shapes.md` or `0751-mark-provenance-column.md`, and the
`now` column of the first page's table is what those pins are read from. Moving
the pins without moving that column left every moved pin unnamed, so the tool
goes from the exit **0** it has on the tree this merges into to exit **1** on
this diff — this change's own redness, not an inherited one, which is why it is
repaired here rather than filed as separate work. So the column is re-anchored
too, to the line each quoted text now sits on. That is an edit to a shared page,
and it is the point rather than a cost: the tool's pins and the pages that name
them are one measurement, and leaving the two halves disagreeing is what leaves
a figure nobody can re-derive — which is the reason the measurement is a tool
rather than a paragraph.

## How to re-check this

```console
# The new cases, by class name.
python3 ec/tools/test_grade_0751_isolation.py StrictReaderOpenCountTests
# The two existing classes this change sits next to, which must be
# unchanged and green -- especially the containment assertion holding
# read_capture's decode exception against the notice's, and the both-faults
# order.
python3 ec/tools/test_grade_0751_isolation.py \
    ExistingMarkLabelTests MarkBeforeCodecTests
# The notice-side holders of the BOM sentence and of read_capture's
# two-tuple.
python3 windows/tools/test_ec_watch.py
python3 windows/tools/test_system_id_probe.py
# The citation gate, whose pins this change moved with the lines.
python3 -m unittest ec.tools.test_measure_mark_provenance_citations
# Whole tree.
bash tools/run-tests.sh
```

**The evidence is the four-fixture table and the cross-chunk measurement, not
the pass count.** Every fixture is a `tempfile` file this checkout wrote. No
laptop, no Windows box, no capture, no register and no live observation is
involved anywhere in this change.

## What this leaves open

- **The `position` in a decode refusal is chunk-relative, so it is not an
  offset into the file.** A reader who wants to point an operator at the byte
  a refusal stopped on gets the decoder's own position within the 8 KiB it was
  working on. Nothing in the tree compares positions across files and the
  anti-drift contract does not need it to; the notice's sentence quotes the
  exception whole, which is what makes the containment assertion hold.
- **#767**, as above: `main()`'s two reads are still two.
- **The whole-buffer read is now the cost on the strict path.** It was the
  notice's to pay since #749 and the strict reader does not pay it twice
  today; a capture large enough for that to matter would say so here first.
  Nothing measures it, and the largest capture this repository commits is a
  little over 200 KB, so this is a shape to be aware of rather than a problem
  observed.
