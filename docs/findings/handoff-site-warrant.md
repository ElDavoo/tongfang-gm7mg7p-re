# A DPTR handoff that resolves is a warrant, and the one address whose sites do not resolve

(2026-09-28, issue #1105. Static reading of one committed image through
`ec/tools/register_ref_table.py --callee-depth 1` and the new
`ec/tools/check_site_resolution.py` over `ec/firmware/GMxMGxx_11.800`. No
capture opened, no EC, no hardware, no Windows, no Ghidra export, no
`static_refs*` count moved, and no `status:` moved.)

[walk-flow-follow.md](walk-flow-follow.md) closed by handing the grading
question to #32 rather than answering it: *what a site is worth once found*.
#32 answered a different question — whether a *count* can carry a grade — and
said so at [pd-only-status-vocabulary.md](pd-only-status-vocabulary.md) §2 and
in `check_status_vocabulary.py`'s own docstring, which listed "what a site is
worth once found" under what it did not check. Two documents, one deferred
question, no owner. **This is the answer**, and it is a third rule rather than
a widening of the second, for the reason §3 gives.

The answer does not move a single grade. It adds a rule that holds the nine
entries this issue names *to* a standard they already meet, names the one
address in the whole `present-untested` population that does not, and gives
that one an exemption with its own expiry.

## 1. The measurement, and the two shapes the ten sites have

The issue's premise is that these addresses "have no concrete-direction EC
site at all". That is a statement about the **depth-0** census columns, and
the instrument that answers it was already committed.
`register_ref_table.py --callee-depth 1` decodes the called routine's own
entry point, so a `MOV DPTR,#0x0402 ; lcall 0x8892` stops being a shape and
becomes a store. Re-run here, it resolves **nine of the ten**:

| address | entry | EC-side sites | `--callee-depth 1` verdict |
|---|---|---:|---|
| `0x0402` | `BAT_DESIGN_CAPACITY` | 3 | 1 read, 2 write |
| `0x0408` | `BAT_DESIGN_VOLTAGE_1` | 2 | 2 write |
| `0x040A` | `XDATA_040A` | 3 | 2 read, 1 write |
| `0x040C` | `XDATA_040C` | 2 | 1 read, 1 write |
| `0x040E` | `XDATA_040E` | 2 | 1 read, 1 write |
| `0x0410` | `XDATA_0410` | 1 | 1 write |
| `0x043A` | `XDATA_043A` | 3 | 3 read |
| `0x0733` | `MODE_PL_DEFAULTS` | 1 | 1 write |
| `0x0735` | `MODE_PL_DEFAULTS` | 2 | 2 write |
| `0x0420` | `XDATA_0420` | 1 | **unresolved** |

Those sites are **two shapes and no others**, and naming them is most of the
work:

* Nine of the ten addresses hand DPTR to one of four six-byte pair accessors in
  bank1 — `0x8886` `read_xdata_pair_to_r1r2`, `0x888C`
  `write_r1r2_to_xdata_pair`, `0x8892` `read_xdata_pair_to_r3r4`, `0x889E`
  `write_r3r4_to_xdata_pair` — or, for `0x0733`/`0x0735`, to `0xB939`
  `store_a_to_dptr_b939`, which is a single `movx @DPTR,a`. Every one of those
  callees is a plain load or store of one or two bytes. A site that hands DPTR
  to a six-byte routine whose first instruction is `movx @dptr,a` is not an
  unresolved site; it is a store with one `lcall` in the way.
* `0x0420`'s single site is **not a handoff at all**. It is the tail of
  `clamp_r2r1_to_0420_above_3c0b` (`ec/decompiled/bank1/E769.asm`), a range
  check on R2:R1 against `0x3C0B` whose *out-of-range* path loads
  `DPTR,#0x0420`, copies DPTR into R1:R2 and returns. Nothing ever loads or
  stores through it.

The join that produced the function names did not exist and is the one piece
of new machinery here. `register_ref_table.py` classifies a site and
`--callee-depth 1` resolves it, but neither named the *routine* a site sits
in, so a verdict arrived without the thing a reader needs most. This repo has
been placing that join by hand: `ec/annotations/xdata-0400-045f.md` §7 says its
"writer routines" column has no committed reproducer, and the `XDATA_0420`
note named bank1 `0xE779` as an address rather than as a function.
`bucket_c_codemap.py` has the one reusable `containing_function()` and it is
hard-wired to `program == "common"`, so it cannot answer for any bank.
`check_site_resolution.py` does the join against the `size` column of
`ec/decompiled/listing-index.csv` — the column `ghidra-functions.csv` lacks,
and the reason the sibling cannot do this. Its output is committed as
`ec/annotations/site-resolution.csv`, one row per EC-side site of every
`present-untested` address, and `--check` re-derives it byte for byte.

## 2. The ten, site by site, with the function that holds each

Transcribed from `--summary`'s sibling, `check_site_resolution.py`'s default
run. `0x0733`/`0x0735` are cited at
`ec/decompiled/bank0/94D0.asm:74,106,117` and `0x0420` at
`ec/decompiled/bank1/E769.asm:18`.

```console
$ python3 ec/tools/check_site_resolution.py | grep -A1 -E '^  0x(0402|0408|040A|040C|040E|0410|0420|043A|0733|0735)  '
  0x0402  file 0x134BD  bank1    0xB4BD  read                   handed to lcall/ljmp -> callee reads
        in 0xB43B FUN_CODE_b43b, handing to 0x8892 = 0x8892 read_xdata_pair_to_r3r4
  0x0402  file 0x15C14  bank1    0xDC14  write                  handed to lcall/ljmp -> callee writes
        in 0xDB0B FUN_CODE_db0b, handing to 0x889E = 0x889E write_r3r4_to_xdata_pair
  0x0402  file 0x15F7C  bank1    0xDF7C  write                  handed to lcall/ljmp -> callee writes
        in 0xDEF1 FUN_CODE_def1, handing to 0x888C = 0x888C write_r1r2_to_xdata_pair
  0x0408  file 0x15C2B  bank1    0xDC2B  write                  handed to lcall/ljmp -> callee writes
        in 0xDB0B FUN_CODE_db0b, handing to 0x889E = 0x889E write_r3r4_to_xdata_pair
  0x0408  file 0x15FA0  bank1    0xDFA0  write                  handed to lcall/ljmp -> callee writes
        in 0xDEF1 FUN_CODE_def1, handing to 0x888C = 0x888C write_r1r2_to_xdata_pair
  0x040A  file 0x12E31  bank1    0xAE31  read                   handed to lcall/ljmp -> callee reads
        in 0xAE2B cmp_0436_0437_against_040a_040b, handing to 0x8886 = 0x8886 read_xdata_pair_to_r1r2
  0x040A  file 0x1351D  bank1    0xB51D  write                  handed to lcall/ljmp -> callee writes
        in 0xB50E derive_scaled_values_from_0404, handing to 0x888C = 0x888C write_r1r2_to_xdata_pair
  0x040A  file 0x13549  bank1    0xB549  read                   handed to lcall/ljmp -> callee reads
        in 0xB50E derive_scaled_values_from_0404, handing to 0x8886 = 0x8886 read_xdata_pair_to_r1r2
  0x040C  file 0x12E98  bank1    0xAE98  read                   handed to lcall/ljmp -> callee reads
        in 0xAE92 cmp_0436_0437_against_040c_040d, handing to 0x8886 = 0x8886 read_xdata_pair_to_r1r2
  0x040C  file 0x1352C  bank1    0xB52C  write                  handed to lcall/ljmp -> callee writes
        in 0xB50E derive_scaled_values_from_0404, handing to 0x888C = 0x888C write_r1r2_to_xdata_pair
  0x040E  file 0x13532  bank1    0xB532  write                  handed to lcall/ljmp -> callee writes
        in 0xB50E derive_scaled_values_from_0404, handing to 0x888C = 0x888C write_r1r2_to_xdata_pair
  0x040E  file 0x1355C  bank1    0xB55C  read                   handed to lcall/ljmp -> callee reads
        in 0xB50E derive_scaled_values_from_0404, handing to 0x8886 = 0x8886 read_xdata_pair_to_r1r2
  0x0410  file 0x13565  bank1    0xB565  write                  handed to lcall/ljmp -> callee writes
        in 0xB50E derive_scaled_values_from_0404, handing to 0x889E = 0x889E write_r3r4_to_xdata_pair
  0x0420  file 0x16779  bank1    0xE779  unresolved-none        no movx in window
        in 0xE769 clamp_r2r1_to_0420_above_3c0b
  0x043A  file 0x13572  bank1    0xB572  read                   handed to lcall/ljmp -> callee reads
        in 0xB56C cmp_043a_0436_store_0548, handing to 0x8892 = 0x8892 read_xdata_pair_to_r3r4
  0x043A  file 0x13590  bank1    0xB590  read                   handed to lcall/ljmp -> callee reads
        in 0xB56C cmp_043a_0436_store_0548, handing to 0x8886 = 0x8886 read_xdata_pair_to_r1r2
  0x043A  file 0x135A2  bank1    0xB5A2  read                   handed to lcall/ljmp -> callee reads
        in 0xB56C cmp_043a_0436_store_0548, handing to 0x8886 = 0x8886 read_xdata_pair_to_r1r2
  0x0733  file 0x09548  bank0    0x9548  write                  handed to lcall/ljmp -> callee writes
        in 0x94D0 copy_code_table_into_0730_07a7, handing to 0xB939 = 0xB939 store_a_to_dptr_b939
  0x0735  file 0x0958A  bank0    0x958A  write                  handed to lcall/ljmp -> callee writes
        in 0x94D0 copy_code_table_into_0730_07a7, handing to 0xB939 = 0xB939 store_a_to_dptr_b939
  0x0735  file 0x095A4  bank0    0x95A4  write                  handed to lcall/ljmp -> callee writes
        in 0x94D0 copy_code_table_into_0730_07a7, handing to 0xB939 = 0xB939 store_a_to_dptr_b939
```

`test_check_site_resolution.py` asserts every line of that table **out of the
committed image**, with the expected verdicts transcribed by hand from the
exported `.asm` files the table cites — `bank1/8886.asm` is two `movx a,@dptr`,
`bank0/B939.asm` is one `movx @dptr,a`, `bank1/E769.asm` has no `movx` at
all — so the oracle does not come from the code under test.

## 3. Which branch of the issue, and why the other is declined

The issue offers a binary: a handoff *is*, or *is not*, a legitimate warrant.
Both branches are implemented, and I take the first, on the measurement
above.

**A handoff that resolves to a direction at the callee's entry is a
legitimate warrant.** The reason is not that it feels like one: the callee
here is six bytes of `movx`, and the store is unambiguous. The reason is what
makes it general — the handoff is *positive* evidence that the address is
passed somewhere a direct `MOV DPTR` scan cannot see, and the direction is a
plain load or store one call away. That is a weaker claim than a read at the
site, and this write-up says so at each site, but it is not a *different kind*
of claim from a store, and it does not need a live test to be true of the
firmware.

**A `none` cell is not.** It says only that the linear walk stopped. It is
evidence of nothing in either direction, and a grade that rested on one would
be resting on the walk's budget.

**The second branch is therefore declined, with evidence rather than by
omission.** Re-grading the entries that fail rule 3 would mean re-grading
`XDATA_0420`, and the entry's own note already says the thing that would have
to change: the site "is neither a read nor a store, and whether the byte is
touched at all is not established". Nothing in this change establishes it
either. The available vocabulary has no value for "present, direction
unresolved" — `unknown-not-absent` means the *EC image has no site*, which is
false here, and `absent` is the `0x07B9` blind spot that
`docs/findings.md` §4c retracts. Inventing a value for one entry would be a
new name and a new precedent, where
[pd-only-status-vocabulary.md](pd-only-status-vocabulary.md) §1 sets the
precedent of recording the decision and leaving it open.

The rule is **not** an edit to rule 2. `check_status_vocabulary.py`'s
docstring states rule 2's own contract — that both rules are "about the shape
of a claim, never its strength" — and the issue makes the same point: widening
rule 2 to site *meaning* "would make it a rule about something other than the
reference count". So it is a **third, separately named rule**, and the header
in `ec/annotations/registers.yaml` now says "Three rules" where it said "Two".

## 4. Rule 3, and the one exemption with its own expiry

`present-untested` requires, per address, at least one EC-side site that
resolves to `read`, `write` or `read+write`. The verdicts are read out of
`ec/annotations/site-resolution.csv`, so the checker **still opens no image** —
which is what lets rule 3 land in
`.github/scripts/agent-gates.sh`'s existing `check_status_vocabulary.py`
invocation without a workflow change.

Measured over the whole `present-untested` population rather than only the
ten, the rule refuses **exactly one address**:

```console
$ python3 ec/tools/check_site_resolution.py --summary | grep 'NO RESOLUTION'
0x0420  NO RESOLUTION unresolved-none 1
```

`XDATA_0420` is exempted **by name**, and the exemption is a *tool* limit
rather than an evidence one, which is why it is stated rather than reasoned
around: `resolve_handoff()` models a DPTR passed to a `lcall`/`ljmp`, and this
site passes the address in R1:R2 across a `ret`. The verdict is what the
instrument cannot follow, not what the byte is. **#1103 owns the R1:R2
propagation, and when `0x0420`'s direction is established this exemption is
deleted** and the refusal returns with it. `check_status_vocabulary.py` also
reports an exemption whose entry has gone or stopped being
`present-untested`, because a named carve-out that stops being needed breaks
nothing and would otherwise be inherited silently by the next reader.

This mirrors how rule 2's exemption is held by `LIGHTBAR_AC_*`, and it gives
the count rule's exemption rationale the second committed user the issue asked
it to have.

The three refusal shapes are pinned under `--self-test` against a
**constructed** census rather than the committed one, for the reason the
tool's own docstring gives: a rule tested only against the data it was derived
from is not tested.

## 5. Two corrections, left in place

Per `docs/findings.md` §4a-4d, the wrong text stays visible beside its
correction.

**The issue's own count is off by one.** It writes that
[pd-only-status-vocabulary.md](pd-only-status-vocabulary.md)'s "Several
`present-untested` entries pass rule 2 on one EC-side site" describes two
addresses, `0x0410` and `0x0420`. Measured, `0x0733` also carries
`static_refs_main_ec: 1` — the issue's own table says so; only its prose says
two — so the count is **three**. And of those three, `0x0410` and `0x0733`
resolve to a write at depth 1, leaving **one** address, not "several", resting
on a site that resolves no further. That is the sentence corrected in place in
that file, with the measured figures beside it.

**`MODE_PL_DEFAULTS`' note was wrong on both halves.** It read "The D-state
byte is read but never written anywhere". The D-state byte is the fourth of
each four-byte block — `0x0733`, `0x0737`, `0x07AA` — and **all three are
written and none is read**: every one of the 18 EC-side sites of the
twelve-byte block is a store. `0x0733`'s site resolves through `0xB939` to a
`movx @DPTR,a`; `0x0737`'s two and `0x07AA`'s one are direct `movx @DPTR,A` in
`copy_code_table_into_0730_07a7`, which copies a CODE table into the block.
The wrong sentence stays in the note with a dated correction beside it.

## 6. What this does not establish

* **Nothing is measured on hardware.** Every verdict above is a static
  instruction. A `write` is a store to the address, not evidence that the EC
  reads the value back or acts on it. `present-untested` means exactly what
  its own gloss in `registers.yaml` says — "static-scan finds real references,
  not yet exercised live" — and no status moved.
* **An unresolved cell is "not found by this method", never "absent".**
  `0x0420`'s site is a *range check* that hands the address onward; whether
  the byte is touched at all remains unestablished, and no static direction
  would have settled it. `0x07B9` is the standing counter-example in the other
  direction — writable, working, zero direct sites anywhere.
* **`--follow-flow` is deliberately not used.** It resolves a `none` cell by
  continuing one path past the branch the walk stopped at, and
  `register_ref_table.py`'s docstring calls that "a **weaker** claim than one
  resolved where it sits". Correct, and exactly why a site resolved that way
  may not warrant a grade.
* **The callee's body is not read past its entry point.**
  `resolve_handoff()` stops at the callee's first control-flow instruction and
  inherits that limit twice over. A `handoff->write` is a store at the entry,
  not a statement about the rest of the routine.
* **`not exported` is not "no function contains this".** The join is against
  the census of *named, exported* functions, so a site in a gap between
  exports reads that way — which is a fact about the exports.

## 7. Declined, and named as follow-ups

* **Adding the census tool to the agent gate is declined, not forgotten.**
  `.github/` is out of scope for this pipeline, and it costs nothing: the
  committed CSV is held by `test_check_site_resolution.py` under
  `tools/run-tests.sh`, and rule 3's own check runs in the gate already. A
  prepared patch under `docs/ci/` adding the tool to
  `agent-gates.sh` would be an unapplied `.github/` change needing a human;
  the convention is in
  [prepared-gate-patches.md](prepared-gate-patches.md).
* **#1100** (32 unmeasured `none` cells) and **#1103** (the `--callee-depth`
  tool gap) are inputs, not part of this. #1103 has since landed the two hops
  it named — a handoff reached past a branch, and a callee that forwards DPTR
  on again — in columns of their own, and `0x0420`'s R1:R2 handoff is
  deliberately not among them: `clamp_r2r1_to_0420_above_3c0b` loads `0x0420`
  through DPTR, copies it into R1:R2 and returns, with no branch in its
  window, so it is not the accessor-stub shape `walk_branch_arms.py` walks.
  What remains open for `0x0420` is what its one caller, bank1 `0x6727`, then
  does with that pair, and nothing above depends on it.
* **`absent` on a zero-in-both-images count** (`0x0726`/`0x0765`) is a second
  decision about a second value, left open per the precedent in
  [pd-only-status-vocabulary.md](pd-only-status-vocabulary.md) §1.
* **No `status:` value is added.** See §3.
* **Nothing upstream.** No file here is proposed for submission; the mission's
  upstream PRs (#10) are out of scope and none is opened.

## 8. Reproducing it

Every command reads committed inputs only — no image beyond the committed
firmware, no Ghidra, no network, no hardware — and leaves the tree unchanged.
Measured on this runner from the repo root.

```console
$ python3 ec/tools/check_site_resolution.py --check ; echo "exit=$?"
ec/annotations/site-resolution.csv: 866 site row(s) match a fresh census from the committed image
exit=0

$ python3 ec/tools/check_site_resolution.py --self-test ; echo "exit=$?"
  self-test passed
exit=0

$ python3 ec/tools/test_check_site_resolution.py 2>&1 | tail -3
----------------------------------------------------------------------
Ran 31 tests in <elapsed, which varies run to run and is not a claim>

OK
exit=0

$ python3 ec/tools/check_status_vocabulary.py --check 2>&1 | tail -3 ; echo "exit=$?"
resolution rule: present-untested needs one EC-side site per address that resolves to read, write, read+write; 1 address(es) in the census resolve to nothing (0x0420), held by the named exemption: XDATA_0420
exit=0

$ python3 ec/tools/check_status_vocabulary.py --self-test ; echo "exit=$?"
  self-test passed
exit=0
```

**The positive control**, because a check that has never been seen to refuse is
not evidence of anything. Exactly one variable changed: `0x0410`'s single
resolution cell, from the write it resolves to into the unresolved verdict.
`0x0410` is chosen because it has exactly one EC-side site, so one cell is
enough to flip the rule — on a three-site address such as `0x0402` the same
edit correctly does *not* fire, because two resolved sites remain. The file is
constructed in `/tmp` and handed over with `--site-csv`, never committed, for
the reason `pd-only-status-vocabulary.md` gives: a committed copy of a file
this change edited is a second source of truth that goes stale the moment
either moves.

```console
$ python3 ec/tools/check_status_vocabulary.py --check --site-csv /tmp/pre-1105/site-resolution.csv 2>&1 >/dev/null ; echo "exit=${PIPESTATUS[0]}"
  REFUSED  XDATA_0410 0x0410: present-untested needs an EC-side site that resolves to a direction and this address's sites resolve to none (unresolved-handoff 1). A DPTR handoff the callee's entry point settles is a warrant; unresolved-handoff and unresolved-none are not -- a handoff is positive evidence the address is passed somewhere, a `none` cell is not evidence of anything. Neither is a statement that the EC does not touch the byte: 0x07B9 is the standing counter-example. See docs/findings/handoff-site-warrant.md
1 refusal(s). A refusal is a shape a status is not allowed to take, not an argument that the grade is wrong.
exit=1
```

**And that no count moved**, which is the claim §1's table depends on:

```console
$ python3 ec/tools/check_register_counts.py ec/firmware/GMxMGxx_11.800 ; echo "exit=$?"
176 entries / 208 addresses: every static_refs, static_refs_main_ec and static_refs_pd_image reproduced from ec/firmware/GMxMGxx_11.800
exit=0

$ python3 ec/tools/gen_xdata_symbols.py --check ; echo "exit=$?"
ec/ghidra/xdata-symbols.csv: 208 symbols match a fresh generation from ec/annotations/registers.yaml
exit=0
```

(The generator prints absolute paths, since it builds them from its own
location; the line above is the same one with the repo root elided.)
