# A caller's literals are not index-register loads unless the site indexes on those registers

(2026-09-27, issue #70. Static reading and commands over one committed image.
No capture opened, no EC, no hardware, no Windows.)

`ec/annotations/pd-index-callers.csv` carried this in its last row:

```csv
0xE9F5,0xE9E3,byte-scan,...,R1=#0x00 R2=#0x08 R3=#0x01,literal index loads found
```

`ec/annotations/pd-index-geometry.md` §4.2 decodes that exact caller and concludes
the opposite. The site at `0xE9F5` indexes on `R7` and `R6`; the frame loads
`R1`, `R2` and `R3`; and §4.2's own sentence is **"None of the three literals
is an index for this access."** §4's net is "not one index register bounded by
a literal", and §5 turns that into the reason no record count appears anywhere
in the file.

The prose was right and the CSV was wrong. The status cell was computed from
the *presence* of a literal in the caller's frame and from nothing else:

```python
"status": "literal index loads found" if lits else "unresolved",
```

So a consumer reading the machine-readable artefact without the prose would
draw the single conclusion the prose most insists is not supported. **This
change makes the status a function of the intersection** of the frame's literal
register loads with the index registers the site's own term decode names,
regenerates the CSV, and pins the result in `--self-test` so the two cannot
drift apart again.

No retraction is needed anywhere. §4.2 was already right; only the CSV disagreed
with it, and the sentences in `subsystems.md` §9 and `docs/findings.md` that
restated the CSV's value are corrected in place below.

## What the status is now

> **Corrected after this page was written.** The vocabulary below grew a fifth
> value, `frame too short to say`, on the frame-length axis this page's
> "Readings taken" section named as a known limit and declined to grade. The
> four-value table and the "four values" wording here are left as they stood,
> with the fifth value carried in
> [`pd-caller-frame-quality.md`](pd-caller-frame-quality.md), which states it
> with its measurement and what it does not claim. `unresolved` is now scoped
> to a frame long enough to have held a load, which is a narrowing of this
> page's first row below and not a change to it.

Four values, defined once as module-level constants in
`ec/tools/pd_index_geometry.py` beside the existing `UNRESOLVED_STRIDE` and
exercised from `--self-test`:

| value | when it applies | what it does **not** claim |
|---|---|---|
| `unresolved` | the frame holds no literal load at all | nothing; this is the conservative non-committal value, and it is byte-identical to what the CSV already carried |
| `literals found, none an index register` | literals are present, and none is in a register the decode names as an index | **not** that the index is provably unbounded — only that these loads are not it |
| `literal load into an index register` | at least one literal load is in a register the decode names as an index | **not** that the value survives the call: `--callers` traces no further than the caller frame, the entry pick is a heuristic, and `literals_in()`'s own docstring says it does not follow what a callee leaves in the register bank. It says a load is there, in a register the site indexes on. Nothing more. |
| `literals found; site index registers unresolved` | literals are present, but the decode named **no** index register at all | — |

The fourth value is the one the calibration rule asks for. "Not found by this
method" needs its own wording, distinct from "a match was sought and none was
found" — the same distinction `ec/annotations/registers.yaml` draws between
`absent` and `unknown-not-absent`, and the same one §5 of
`pd-index-geometry.md` draws for its unresolved whole-image sites.

**Branch order is load-bearing, and that is why `caller_status()` tests the
index registers before the intersection.** Testing the empty intersection first
would give a site whose decode names no index register at all the value
`literals found, none an index register` — which asserts that a match was
sought and failed, rather than that nothing was resolved. Those are different
claims and the vocabulary has to keep both. No committed row reaches the fourth
value, so it is covered from hand-built dicts in the self-test; a site whose
terms resolve nothing is a `0x7421`-shaped case the current four sites do not
produce.

The positive value is worded to stop at the *load* for the reason in its row of
the table. Nothing in `--callers` follows a value past the call: `literals_in()`
resets everything it has found when it sees a call in the frame, because what
the callee leaves in the register bank is not traced, and the entry a caller is
attributed to is one of two heuristics whose failure mode the module preamble
names. "A load is there, in a register the site indexes on" is the whole of what
the bytes support.

## What was measured

Run against the committed image with the tool as it stood
(`ec/firmware/GMxMGxx_11.800`, `pd_index_geometry.py`, stdlib only). The
intersection column is `index_registers()` over each site's `effective_terms()`;
the literals are what `literals_in()` found in each caller frame:

| site | `effective_terms()` → index registers | caller frame literals |
|---|---|---|
| `0x7421` | `R3×0x60`, `0x200×R3` → {R3} | none (both rows) |
| `0x9DEC` | `R6×0x60`, `0x200×R6`, `R5×0x1F` → {R6, R5} | none |
| `0xB5D3` | `A×0x60`, `0x200×R7` → {R7} | none |
| `0xE9F5` | `R7×0x60`, `0x200×R7`, `R6×0x1F` → {R7, R6} | {R1=0x00, R2=0x08, R3=0x01} |

The intersection at `0xE9F5` is empty, and at the other three sites the literal
set is empty to begin with. So the four `unresolved` rows keep their status
byte-identically, and the CSV diff is **one line**:

```diff
-0xE9F5,0xE9E3,byte-scan,reaches the site with no intervening `ret`,ret,0,0x266E4,0x66E4,call,lcall 0xe9e3,24,0,R1=#0x00 R2=#0x08 R3=#0x01,literal index loads found
+0xE9F5,0xE9E3,byte-scan,reaches the site with no intervening `ret`,ret,0,0x266E4,0x66E4,call,lcall 0xe9e3,24,0,R1=#0x00 R2=#0x08 R3=#0x01,"literals found, none an index register"
```

The `literals` column is deliberately untouched. The literals stay in their own
column and the status does not become a reason to drop them, because the three
loads are the evidence §4.2 reasons from and a reader needs to see them next to
the conclusion drawn about them. The `--self-test` asserts that column
separately, so the status cannot later be made true for the wrong reason by
emptying the thing it derives from.

**Two exclusions, and why the intersection is well defined at all.** `A` and
`B` are not in the vocabulary `index_registers()` reads, because the site's own
frame reloads both — `A` is reloaded by the frame `ab_of()` decodes and `B` by
`mov b,#0xNN` — so neither is a value a caller's literal could ever bound. That
leaves `R0`–`R7` as the only registers a frame's literal load and a site's index
can share. The `0xB5D3` row is where that exclusion is visible in the data: its
terms are `A×0x60` plus `0x200×R7`, so its index registers are `{R7}` and the
accumulator contributes nothing.

**The `A:R1` destination, which no committed row exercises.** One term template
builds a generic pointer in `A:R1` rather than in DPTR. `0x578E` produces
exactly that form:

```
A:R1 ← 0x089B + A×0x77
```

Read naively, the `R1` there is an index register — and it is not: it is where
the pointer lands. `index_registers()` therefore reads only the right-hand side
of a construction's `←` when the term has one, and a term without one whole.
**None of the four committed sites is one of these**, so the committed CSV
cannot exercise the stripping and the self-test covers it synthetically over
the `0x578E` term instead. Without that case the behaviour would rest on
nothing but the comment.

Matching is on `R[0-7]` as a whole name, so `0x200×R7`, `R6×0x1F` and
`low8(R7×0x5E)` all resolve, and `A`, `B`, `{a}` and `{b}` resolve to nothing.
A hex literal cannot contain `R`, so there is no false positive from a `0x…`
operand.

## A second instance of the same defect: the status was invisible where the claim is read

`print_callers()` printed `lits or r["status"]`, so the one row that carried a
status was the one row whose status never appeared — the fallback only fires
when the literals are empty, and the one interesting row has literals. The text
view is where a reader reads the claim off, so it now prints the status on
**every** row, in brackets beside the literals:

```console
$ python3 ec/tools/pd_index_geometry.py ec/firmware/GMxMGxx_11.800 \
          --callers 0x7421 0x9DEC 0xB5D3 0xE9F5
...
PD runtime 0xE9F5
  byte-scan entry 0xE9E3: reaches the site with no intervening `ret`; preceded by ret; 0 jump target(s) in between
    file 0x266E4  runtime 0x66E4  call      lcall 0xe9e3     frame 24/24 (16 insn)  R1=#0x00, R2=#0x08, R3=#0x01 [literals found, none an index register]
```

`pd-index-geometry.md` §4's console block is re-typed from that run rather than
hand-edited to look right. A `-` stands in for an empty literals column, which
is the same dash the tool already uses for an empty helper chain and for
`0x04A4` in §3.

## A behaviour change for `--callers`: a bad address is now a diagnostic

`--callers` now reaches `check_site_addr()` for the first time, because
`caller_rows()` decodes the site to learn its index registers. Without a guard
that is a `ValueError` traceback from inside the run rather than argparse's
clean error, so the `print_callers()` call is wrapped in the same
`try/except ValueError: ap.error(...)` that `--sites` and `--helpers` already
use:

```console
$ python3 ec/tools/pd_index_geometry.py ec/firmware/GMxMGxx_11.800 --callers 0x23478
pd_index_geometry.py: error: 0x23478 is not a pd-image runtime address: that
region is 0x0000-0xFFFF at run time, 0x20000-0x2FFFF in the file
  0x23478 is inside the file range, which is where a site's file_offset lives;
  the runtime address there is 0x3478
$ echo $?
2
```

`0x23478` is not a contrived argument — it is the first `file_offset` in
`../../ec/annotations/ec-0x07d0-sites.csv`, whose `runtime` column reads
`0x3478` on that same row. `pd-index-geometry.md` §5's bullet on what
`check_site_addr()` does and does not check now names `--callers` beside
`--sites`. The check is a statement about the caller's *argument* and not about
this image's bytes, for the reasons
[`pd-sites-address-range.md`](pd-sites-address-range.md) gives at length; this
change does not reopen that argument.

## The test

`--self-test` is the test, and it lives next to the code that writes the CSV.
It runs two different guards, and this change needed both:

1. **CSV ↔ tool.** The existing loop byte-compares all five generated CSVs
   against the committed files. It is what will fail first if the status logic
   and the committed file ever disagree — **and it is what could not catch this
   bug, because the two were wrong together.** That is the gap the second guard
   closes.
2. **Tool ↔ prose.** A module-level `CALLER_STATUSES` table keyed by
   `(site, caller runtime)`, transcribed from §4/§4.2 rather than read back out
   of the CSV, covers all five rows. Each is asserted against **both** the
   committed CSV row and the freshly computed value, and the key set is checked
   so a new row cannot slip past unpinned. The `0xE9F5` entry is the one the
   issue asks for; the other four are pinned in the same table so a later change
   cannot quietly move a row out of agreement with §4 either.

   Alongside it: a `caller_status()` block exercising all four values from
   hand-built dicts, including the two no committed row reaches, and an
   `index_registers()` case over the synthetic `A:R1 ← …` term. The frame-length
   value added later rides in the same block, which now also carries
   `frame_insns` as a third argument and the `CALLER_STATUSES` tuples carry it
   as a third element.

Both new guards were falsified before being believed — `caller_status()`
replaced by the old presence-of-literals predicate, and `index_registers()`
replaced by one that reads a whole term. Each made `--self-test` exit non-zero
and name the disagreement.

## Readings taken, and what was left out

- **No `index_registers` column in the CSV.** The strongest argument for it is
  that the status is now a function of two things and the CSV carries only one,
  so a consumer still cannot verify the claim from the file alone. Rejected as
  the wider change: it alters the schema of a committed artefact that three
  documents cite by column, for a five-row table, and §4.2 already prints the
  decode the status is derived from. A follow-up candidate, and one that earns
  its place if the row count ever grows.
- **No fifth status value for "the frame is too short to say anything".** The
  `0x7421` byte-scan row has a one-instruction frame (`frame_onto 1 / over 23`)
  and is weaker evidence than the three `24/24` rows, so the four `unresolved`
  rows are not interchangeable in strength. Grading them would need a claim
  about frame quality that this change has no basis for; §4.1 already attributes
  that row, and `frame_onto`/`frame_over` carry the evidence per row. Named here
  as a known limit rather than papered over with a value.

  > **Overtaken.** The basis was the missing measurement, not a reason not to
  > grade. `ec/tools/pd_caller_frame_quality.py` now measures the frame-length
  > distribution over every whole-image caller row, `MIN_FRAME_INSNS` draws the
  > line from it, and the `0xC9DD` row is filed `frame too short to say`. A
  > `frame_insns` column carries the evidence per row the way `frame_onto` and
  > `frame_over` could not. See
  > [`pd-caller-frame-quality.md`](pd-caller-frame-quality.md).
- **Not done: tracing a literal through the entry.** What the callee leaves in
  the register bank is not followed, and that is the limit the positive status
  value is worded around rather than a gap this change closes.
- **Not a `registers.yaml` change, and none could have been.** A decode of a
  second 8051 image's address arithmetic is not evidence about an EC register
  in either direction — the same reasoning `pd-index-geometry.md`'s preamble
  and `subsystems.md` §10 already record.

## What this does not establish

- **No live test ran.** No EC was opened, no register was read or read back, no
  capture taken, no hardware and no Windows involved. Every number above is a
  static read of a committed file or the output of a command over one. What
  `R7` and `R6` actually hold at `0xE9F5` is `pd-index-geometry.md` §6's
  runtime step, needs the physical machine, and is unchanged.
- **No index range and no record count is bounded.** The status says what was
  found in one frame of one heuristic caller, not what range the index takes.
  §5's "no record count" stands.
- **"None an index register" is not "unbounded".** It is a statement about three
  loads in `R1`, `R2` and `R3` against a decode naming `R7` and `R6`. The index
  could still be bounded by something this method does not see — a second
  caller, a table-mediated call, a value built in the entry.
- **The entry pick is still a heuristic**, and this change does not move §4.1's
  phantom or §5's named failure direction for it.
- **The self-test pins values, not wording.** It asserts that the committed
  cells and the computed values agree with the transcribed table; it does not
  assert that these four strings are the best four strings.

## Reproducing it

From the repository root. The `cmp` follows §8.2's generate-then-compare
convention rather than overwriting the baseline in place.

```sh
python3 ec/tools/pd_index_geometry.py ec/firmware/GMxMGxx_11.800 --self-test
python3 ec/tools/pd_index_geometry.py ec/firmware/GMxMGxx_11.800 --callers \
        0x7421 0x9DEC 0xB5D3 0xE9F5          # §4's block, re-typed from this
python3 ec/tools/pd_index_geometry.py ec/firmware/GMxMGxx_11.800 --callers-csv \
        > /tmp/pd-callers.csv
cmp /tmp/pd-callers.csv ec/annotations/pd-index-callers.csv
```

The intersection table above is a two-line import, and is the quickest way to
check the claim rather than the string:

```sh
python3 - <<'PY'
import sys; sys.path.insert(0, "ec/tools")
import pd_index_geometry as P
d = open("ec/firmware/GMxMGxx_11.800", "rb").read()
for r in P.site_rows(d, P.DEFAULT_CALLER_SITES):
    print(f"0x{r['addr']:04X}", P.effective_terms(r["terms"]),
          "->", sorted(P.index_registers(P.effective_terms(r["terms"]))))
PY
```

`.github/scripts/agent-gates.sh` does **not** run this self-test — it is not in
that script's tool list — so a PR touching this status column has to carry the
`--self-test` output in its body. Adding it to the gate is a human's change; the
pipeline's token has no `workflow` scope, and the script is itself copied from
the `agent-pipeline` template.
