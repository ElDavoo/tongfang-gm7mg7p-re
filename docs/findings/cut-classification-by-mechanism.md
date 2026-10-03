# Every stop reason `descend()` records is now classified where it is emitted, not recovered from how its message begins

(2026-10-03, issue #1018. Static reading and arithmetic over committed bytes.
No capture opened, no EC, no hardware, no Windows.)

`walk_branch_arms.py` decides whether an arm **finished** or **gave up** by
testing each of its stop reasons against a tuple of message prefixes,
`CUTS`. That works for every reason the walk emits *constant-first*, and fails
for the two it emits **address-first** — `0x… runs past the end of the image`
and `0x… is not reachable from region …`, which begin with the address and so
match no prefix. An arm that stopped because an instruction did not fit, or
because the bytes at the target were never read, was reported `complete`,
left out of `no_claim()`'s blind-spot list, and resolved rather than marked
`unresolved` by `callee_row()`.

This records the classification of all eleven reasons **by mechanism** — by what
actually stopped the walk — and moves it to the call site that knows. The
rendered text of every message is unchanged.

## The eleven reasons, and the verdict for each

`descend()` emits these and no others. `Arm.end()` now takes the verdict as a
required keyword-only argument, and `Arm.cut_ends` reads it back, so this table
is what the tool now does rather than a description of it.

| message | cut? | why |
|---|---|---|
| `ret` | no | the routine returned |
| `reti` | no | interrupt return |
| `tail jump to a callee` | no | the target is in `callees`, and that table is what covers it |
| `loop back to 0x…` | no | an arm that cycles has been fully explored; it comes back round rather than ending |
| `DPTR built at run time (a store to DPL/DPH)` | no | **a note, not a terminator** — the walk records it and continues past it. Neither a cut nor a control-flow end, which is what makes it the one most likely to be mis-set |
| `instruction budget at 0x…` | yes | the budget was exhausted |
| `depth limit at 0x…` | yes | a transfer was not followed |
| `indirect jump -- target not resolvable from the bytes` | yes | `jmp @a+dptr` cannot be resolved from the bytes |
| `index past the end of the image at 0x…` | yes | the first address that cannot be read ([`descend-index-guard.md`](descend-index-guard.md), #844) |
| `0x… runs past the end of the image` | **yes** (changed) | the instruction does not fit, so it was never decoded — the same condition `index past the end` records one step earlier, for the index rather than the instruction |
| `0x… is not reachable from region …` | **yes** (changed) | the bytes at the address were never read. `callee_row()` already reports this same condition as `unresolved: not reachable from region …` for a callee entry point; the two rows were describing one condition and disagreeing about what it is |

Nine of the eleven keep the answer they had. The change is that the answer is
now *recorded* at the call site rather than *recovered* from a string, and that
two of them change — both of them address-first, and both of them cuts.

## Why the verdict is an argument and not a reworded constant

The obvious alternative is to re-emit every reason constant-first and keep
matching prefixes. It was declined because two other tools match the rendered
text by **suffix**, so a reword would degrade a classification each of them
makes today — and, as the first bullet records, nothing on the committed image
catches that happening:

- `bucket_c_codemap.py`'s `token_for_ends()` matches
  `endswith("runs past the end of the image")` and
  `endswith("is not reachable from region common")` exactly. Re-emit either
  address-first message with a trailing `at 0x…` and both stop matching, the
  token falls through to `UNCLASSIFIED`, and the site would read `unknown`
  rather than the settled `undecodable-byte` or `bank-edge-jump` it gives
  today. **That cost is latent on the committed image, not observed there.**
  Both messages fire 0 times over the run measured below, so the
  `unclassified-end` cell is 0 with or without the reword: re-emitting them
  constant-first and running that suite leaves it green. No test catches the
  degradation today, and the argument for declining the reword is not that one
  does — it is that the classification would be wrong *whenever those paths are
  reached*, and the evidence for it is what `token_for_ends()` does to the
  string, which is visible directly.
- `bank_attribution.py`'s cut tally keys on `why.split(" at ")[0]`, so a reword
  would key a second tool's output on a new string for no reason this issue
  asks for.

So the **text of every message stays byte for byte what it is**, and the
classification moves off the string. `CUTS` keeps its name, its four members and
its meaning, because every module that imports it — `run_entry_map.py`,
`stride_index_table.py`, `bank_attribution.py` and `bucket_c_codemap.py`, all
four named in *The readers outside this tool* below — matches `Arm.ends` against
it, and their behaviour is not this change's to move. It is no longer the
mechanism *here*, and its comment says so.

## What did not change, and the evidence for it

**Both committed CSVs come out byte-identical.** The arms and sites tables were
generated on the clean checkout before the edit and again after it, and both
`diff`s are silent (commands below). That is the load-bearing result: a
byte-identical arms table means no row's `status` or `ends` column moved, which
is what "the reclassification changed no row" means here.

**This is a latent misclassification, not a corrected wrong claim.** Both
reclassified messages fire **0 times** over the committed `0x0751` run at the
default bounds — measured over `arms_for()` at depth 16 and 500 instructions —
so no committed row was wrong and none is corrected. That zero is a measurement
of *this run at these bounds*, in the sense
[`descend-index-guard.md`](descend-index-guard.md) applies to its own: not
"cannot fire". The fixtures in `BoundTests` reach both messages deliberately,
which is the other half of the same statement — the paths exist and are covered,
this image at these bounds does not take them.

**No live test ran.** No EC was opened, no register read back, no capture
taken, no hardware and no Windows involved. The subject is a Python function
classifying its own messages over a committed file. Nothing here is a claim
about what the firmware does with any of this, and nothing here changes an
`ec/annotations/registers.yaml` status.

## The readers outside this tool

`Arm.ends` has readers beyond this file, and **four** of them classify it rather
than print it. All four keep working unchanged, because every `CUTS` member is
unchanged and still constant-first — but they arrive at the answer by four
different routes, and one does not agree:

- **`bucket_c_codemap.py`** — `GAVE_UP = frozenset(CUTS)`, plus the two
  `endswith` matches in `token_for_ends()`, which map the two address-first
  messages to `undecodable-byte` and `BANK_EDGE`; both are in its
  `UNKNOWN_REASONS`, so the site becomes `unknown`. **It already treats both as
  "the walk could not say", which agrees with this change** — by string matching
  that this change shows to be the wrong mechanism. Recording that is worth
  more than leaving it to be rediscovered.
- **`bank_attribution.py`** — `why.startswith(CUTS)`, keyed on
  `why.split(" at ")[0]`. **No fallback**: an address-first end would not be
  recognised at all. This one does *not* agree, and its tally would understate a
  cut the same way `arm_status()` did.
- **`run_entry_map.py`** — three `startswith(CUTS)` readers over the same ends
  (`callee_row`-equivalent status, `slot_status()`, `no_claim()`). Same shape as
  `bank_attribution.py`, same blindness to the two address-first reasons.
- **`stride_index_table.py`** — `GAVE_UP = CUTS` tested by **exact membership**
  (`why in GAVE_UP`), not by prefix. This is a defect of its own and predates
  this change by a wide margin: three of the four `CUTS` reasons are emitted with
  an ` at 0x…` suffix, so they never match exactly and only `END_INDIRECT` can.
  A walk that stops on the budget is reported `not-reached` where this tool now
  says `cut:`. **Not fixed here** — it changes another tool's output, and this
  change makes no such change — but it is the sharpest instance of the general
  point, and it is worth an issue of its own.

**"Make these four read `Arm.cut_ends`" is the natural follow-up**, and is what
the follow-up pass should turn into the next issue. It is one line each in three
files and one predicate in the fourth, and it would let `stride_index_table.py`
drop the exact-membership shape that is wrong today.

One further latent defect was noticed while reading `bucket_c_codemap.py` and is
**not** fixed here: its `BANK_EDGE` suffix match is hardcoded to
`"is not reachable from region common"`, so the same end reached in a `bank0`
or `bank1` region would classify as `UNCLASSIFIED` rather than `BANK_EDGE`.

## The pins

`BoundTests` is the class whose stated job is "every bound has to stop the walk
and say so"; it already drives `descend()` through `walk()`, and the
classification cases sit in it. Each stop reason's verdict is asserted, and the
three that changed answer are asserted **against the pre-change tool's
behaviour**: an instruction that does not fit, an address outside the region at
the entry point, and the same address reached *after* decoding — the third so
the second cannot be read as an artefact of an entry point that is never in
range. All three report `complete` on `HEAD`'s tool and are cuts on this one.

The case that makes the issue's done-condition executable is the one that walks
all eleven reasons and checks that the ones meaning the walk gave up are exactly
the ones reported. What makes the set exhaustive rather than representative is
the required argument: a new reason cannot be added at a call site without a
verdict being stated there, so the failure this change exists to prevent is a
`TypeError` at the call site rather than a silent bucket.

## Reproducing it

From the repository root.

```sh
# the load-bearing evidence: both committed artifacts byte-identical.
# Run on the clean checkout first, so "before" is measured rather than asserted.
python3 ec/tools/walk_branch_arms.py ec/firmware/GMxMGxx_11.800 \
    0x0751 --callee-depth 1 --csv \
  | diff - ec/annotations/manual-fan-ctrl-0751-arms.csv
python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 \
    0x0751 --csv --terminator-column \
  | diff - ec/annotations/manual-fan-ctrl-0751-sites.csv
# ...then the identical pair against the changed tool. Both diffs silent.

python3 ec/tools/walk_branch_arms.py --self-test ec/firmware/GMxMGxx_11.800
python3 ec/tools/test_walk_branch_arms.py            # the whole suite
python3 ec/tools/test_walk_branch_arms.py BoundTests # the classification pins

# that the two newly-classified reasons are pins: on HEAD's tool each reports
# `complete`, which is what the fixture cases fail on.
git show HEAD:ec/tools/walk_branch_arms.py > /tmp/wba_head.py
PYTHONPATH=ec/tools python3 /tmp/wba_head.py --self-test ec/firmware/GMxMGxx_11.800

# the fire counts quoted above, over the committed run
python3 -c "
import sys; sys.path.insert(0,'ec/tools')
from pathlib import Path
import walk_branch_arms as wba
d = Path('ec/firmware/GMxMGxx_11.800').read_bytes()
off, magic = wba.PD_MARKER
pd = d[off:off+len(magic)] == magic
seen = [e for _,_,_,_,arms in wba.arms_for(d, 0x0751, pd, 16, 500)
        for a in arms for e in a.ends]
print(sum('runs past the end' in e for e in seen),
      sum('not reachable from region' in e for e in seen))"

# the opcode-length census's membership test, re-run rather than hand-edited
grep -rn 'OPCODE_LEN\[' --include=*.py ec/tools | grep walk_branch_arms

# what the declined reword would do, which is the claim it rests on.
# First the mechanism, visible directly on the strings:
python3 -c "
import sys; sys.path.insert(0,'ec/tools')
import bucket_c_codemap as bcc
print(bcc.token_for_ends(['0x0009 runs past the end of the image']))
print(bcc.token_for_ends(['runs past the end of the image at 0x0009']))"
# Then the counterfactual: apply the reword to a copy and run that tool's suite
# against it. Unmodified it reports OK; so does the reworded copy, because both
# messages fire 0 times here and the `unclassified-end` cell is 0 either way.
cp ec/tools/walk_branch_arms.py /tmp/wba_reword.py
sed -i 's/^END_RUNS_PAST = .*/END_RUNS_PAST = "runs past the end of the image at 0x{pc:04X}"/; s/^END_UNREACHABLE = .*/END_UNREACHABLE = "is not reachable from region {region} at 0x{pc:04X}"/' \
    /tmp/wba_reword.py
python3 -m unittest ec.tools.test_bucket_c_codemap     # OK, as it is unmodified
```

**`--terminator-column` is load-bearing** on the sites half of the pair. It is
listed in `trace_xdata_refs.py`'s own `Usage:` block as of
[`csv-column-usage-advice.md`](csv-column-usage-advice.md) (#1020), so it is
discoverable now; omitting it makes the diff fail for a reason unrelated to this
change.

## What this does not establish

- **Nothing about the firmware.** This is a tool's bookkeeping of its own
  messages. No register, no bank, no BIOS menu and no Windows class is touched,
  and no claim about EC behaviour is made or implied.
- **The two fire counts are not "cannot fire".** They are what the committed
  `0x0751` run at depth 16 and a 500-instruction budget produced. The fixtures
  in `BoundTests` are the other half of the statement.
- **The external readers still classify for themselves.** Making the four read
  `cut_ends` is the follow-up above, and until it lands
  `stride_index_table.py` and `bank_attribution.py` still under-report a cut of
  this shape — and `stride_index_table.py`'s exact-membership defect is still
  there, unfixed, as it was before this change.
- **`ec/annotations/manual-fan-ctrl-0751.md` is unaffected.** Its arms all report
  `status: complete` at the default bounds and still do; it is not about the
  stop-reason vocabulary, and the byte-identical CSV is the evidence.
- **`docs/findings.md` is untouched.** No section, no pointer, no reused number.
  §83's statement that `END_IMAGE` is in `CUTS` deliberately and fires 0 times
  remains exactly true, and it says nothing about the two address-first messages,
  so no correction is owed to it.