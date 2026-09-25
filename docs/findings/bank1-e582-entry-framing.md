# Which entry the `bank1,0xE582` routine is actually reached through (issue #680)

The lead, first, because the reading below is only worth what its limit is
worth. `disasm8051.converges_from` returns a pair of counts, and its own
docstring (`ec/tools/disasm8051.py:314-319`) says to "read the pair, not either
half" and warns that a site nobody syncs onto is not thereby misframed — it may
simply be preceded by data no linear walk can decode into alignment.
[`citation-gap-scan.md`](citation-gap-scan.md) §"What the tool cannot decide"
carries the same limit for the same column: `frame_onto`/`frame_over` are
"evidence about framing, not proof of it", and `bank0,D091` is the standing
warning that a data island decodes exactly as convincingly as code. **Nothing
below is a proof, and this file does not claim to have found one.** What it does
is settle which of two committed census rows is a phantom, on a byte argument
that does not rest on the column alone.

The correction lands on `ec/annotations/ghidra-functions.csv` rows **1190 and
1191** — both of them, because they carry the same clause and correcting one
would leave the pair contradicting itself a line apart. The superseded wording
stays visible in both, per `CLAUDE.md`'s calibration rule, in the idiom already
used in that file at `common,0x158E` / `common,0x1594`.

**Nothing else moves.** No register `status:`, no row added or removed, no
function entry seeded, no `--mode rebuild-project`, no edit to
`bank-call-targets.csv`, and no change to `call-graph-callees.csv`. No hardware
and no Windows: nothing here needs either, so nothing is deferred to a human at
the machine.

## The two rows, and what settles between them

Both census rows are committed, and the issue quotes both:

```
$ sed -n '5766p;4420p' ec/annotations/bank-call-targets.csv
0x16580,bank1,0xE580,lcall,0xE5D6,B,24,0,,,entry,entry
0x11F03,bank1,0x9F03,ljmp,0xE582,B,0,24,,,other,other
```

One is a transfer that 24 of 24 backwards anchors decode onto. The other is a
transfer that 0 of 24 do, with all 24 stepping over it. Read alone, that is a
tie — the docstring's warning cuts both ways, and `other,other` is not
evidence of anything being *wrong* with the second row any more than `entry,entry`
is evidence of anything being *right* with the first. (See
[§One column deliberately not banked](#one-column-deliberately-not-banked)
for why the `own_bank`/`other_bank` half of the same rows is not a second vote.)

The argument below does not rest on the column. It rests on a byte pattern that
a misframed read does not produce by accident.

## 0xE580 is a transfer, and 0xE582 is its third byte

`ec/decompiled/bank1/E57E.asm` is a single `c0 07` — `PUSH direct 0x07`, which
saves bank-0 R7 — so the listing ends at 0xE580 and the next two bytes are in
no listing. The bytes across the cut are:

```
E57E  c0 07        push    0x07
E580  12 e5 d6     lcall   0xE5D6
E583  d0 07        pop     0x07
E585  ef 64 07     mov     a,r7 / xrl a,#0x07      (and so on into the E582 listing)
```

**The `POP direct 0x07` at 0xE583 is the load-bearing byte, and it is what
separates this from a coincidence of framing.** A three-byte transfer does not
have to be followed by its matching restore; the probability that the four bytes
after an `lcall` happen to contain the `PUSH`'s own operand is not zero, but a
save/restore pair bracketing a transfer is a shape a misframed read does not
manufacture. It says the byte stream was framed correctly at 0xE57E, which is
the anchor 0xE580 is read from. `ec/tools/test_citation_gap_scan.py:109` already
pins the five window bytes `12 e5 d6 d0 07` and asserts that a two-byte window
decodes to *nothing* — so this is corroborated by a committed test, not only by
a reading made here.

`disasm8051.converges_from` on the same image agrees, and the disagreement it
reports is the shape of the argument:

```console
$ python3 ec/tools/make_bank_image.py ec/firmware/GMxMGxx_11.800 1 0x10000 /tmp/bank1.bin
$ python3 ec/tools/disasm8051.py --converge --at 0xE580 /tmp/bank1.bin
0x0E580: 24 of 24 preceding anchors decode onto it, 0 step over it
$ python3 ec/tools/disasm8051.py --converge --at 0xE582 /tmp/bank1.bin
0x0E582: 0 of 24 preceding anchors decode onto it, 24 step over it
```

So `0xE582` is **not an instruction boundary**. The routine begins at 0xE57E,
and the `lcall 0xE5D6` at 0xE580 reads *through* 0xE582 to complete itself. The
`XCHD A,@R0` the `bank1,0xE582` listing opens with is the `d6`, the third byte
of that `lcall` — a real opcode, decoded at an address that is not its own.

## The false positive is 0x9F03, and the `e5 82` is `MOV A, DPL`

`bank-call-targets.csv:4420` records `0x11F03,bank1,0x9F03,ljmp,0xE582`. Bank 1
at 0x9F00 is:

```
9F00  22           ret
9F01  ef           mov     a,r7
9F02  80 02        sjmp    0x9F06
9F04  e5 82        mov     a,0x82            <- MOV A, DPL
9F06  b4 5b 02     cjne    a,#0x5b,0x9F0b
```

`ec/decompiled/bank1/9F00.asm` is a single `22` — all of it — so the listing ends
at 0x9F01. The census, scanning linearly from there, walks `ef / 80 02 / e5 82`
and lands a `0x02` at 0x9F03, which it reads as an `ljmp` with address `e5 82`
= **0xE582**.

**Those two bytes are the machine code of `MOV A, DPL`, not a destination.**
`ec/decompiled/bank1/9F04.asm` opens at its own first instruction with exactly
`e5 82`, mnemonic `mov A, DPL`. So the "target" the census recorded is the
opcode of a committed, separately-exported function — re-read at the wrong
alignment, it happens to spell a valid address.

The linear decode from 0x9F01 **rejoins the committed listing at its own first
instruction** rather than merely failing to be contradicted:

```console
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0x9f01; pd 4' /tmp/bank1.bin
            0x00009f01      ef             mov a, r7
        ┌─< 0x00009f02      8002           sjmp 0x9f06
        │   0x00009f04      e582           mov a, dpl
       ┌└─> 0x00009f06      b45b02         cjne a, #0x5b, 0x9f0b
```

This is the part that makes the reading a displacement-byte argument rather than
merely an unsupported site. 0/24 on its own is absence of evidence, and the
docstring says so. What makes it more than that here is that the misframed read
is **displaced by a positive alternative that explains the same bytes two
ways**: a `sjmp` at 0x9F02 that every one of the 24 anchors lands on, and a
decode that continues into a listing committed independently of this census.
`0x9F03` is the `sjmp`'s displacement byte.

```console
$ python3 ec/tools/disasm8051.py --converge --at 0x9F02 /tmp/bank1.bin
0x09F02: 24 of 24 preceding anchors decode onto it, 0 step over it
$ python3 ec/tools/disasm8051.py --converge --at 0x9F03 /tmp/bank1.bin
0x09F03: 0 of 24 preceding anchors decode onto it, 24 step over it
```

## The precedent is the same argument, on the same shape

[`ec/annotations/bank-call-audit.md`](../../ec/annotations/bank-call-audit.md)
§9 read three census rows to the same standard in the other direction, and one
of them is a displacement byte like this one. Of `bank0,0xAA19` it says: the
`0x02` there *"is the displacement of the `jnb` at `0xAA17`"*, and then — the
phrase worth quoting back, because it is the exact reasoning being applied here —
*"the CSV records `frame_onto` 0 and `frame_over` 24 for it, which is the scan's
own evidence pointing the same way."*

That section retires all three offered sites: two `0x02` displacement bytes and
one row assembled out of two table entries. The adjudication is **in prose**,
not in the CSV, and the reason is mechanical: `bank-call-targets.csv` is
`audit_call_targets.py --csv` run against the image, and it regenerates byte for
byte. A hand edit would be undone on the next run *and* would be a pure merge
hazard on a file several hundred rows long. **So this file does not edit row
4420** — reconciling is not editing. The retirement is this paragraph and the
two corrected comments, and `bank-call-audit.md` carries a pointer to it.

## One column deliberately not banked

The 0xE580 row reads `own_bank,other_bank = entry,entry` and the 0x9F03 row
reads `other,other`, which looks like a second vote on the same question. It is
not one, and the write-up that quietly counted it would be overclaiming.
`audit_call_targets.py:131` documents `byte_class` — and `entry` is
`find_banks.py`'s `START_OPCODES` heuristic, *"a scoring aid, not a decode"*,
"exactly as strong as that". For a site whose byte **is** `0x12` the `entry`
classification is true by construction, not discovered. It is recorded here so a
reader knows it was considered and rejected as corroboration, rather than
silently omitted.

## The limit, stated so it travels with the claim

Everything above is a reading of the committed bytes. It is not a proof, and
specifically:

- **The frame scores are evidence about framing, not proof of it.** The 24/0
  and 0/24 pairs are what makes a site a candidate for a displacement-byte
  reading; the byte-level alternative is what makes it a reading rather than a
  guess. Neither is a decode of a program's control flow.
- **The `bank0,D091` warning is not answered here.** That is the standing case
  where a 40-byte CODE table decodes exactly as convincingly as code. A
  displaced positive alternative is a stronger argument than a bare score, and
  it is still not a proof — the general failure mode is untouched by this
  reading.
- **A linear decode is not a parser.** It does not follow branches, recover
  function boundaries, or tell code from data. Both decodes above
  (`disasm8051.py` and `r2 -a 8051`) are linear walks over the same committed
  tables; `r2` agreeing is a second implementation of the same method, not an
  independent method.
- **This says nothing about the census's other rows.** One phantom retired is
  not a validation of `audit_call_targets.py`'s framing heuristic elsewhere,
  and no such claim is made.
- **No behavioural claim.** Nothing here is about what the EC or the firmware
  does at run time. No register `status:` changed; `ec/annotations/registers.yaml`
  and the generated `ec/ghidra/xdata-symbols.csv` are untouched.

## Does a function entry belong at 0xE580? No.

**The seed row is not added, and the reason is the instruction stream, not
scheduling.** 0xE580 is not the start of anything: the routine begins at 0xE57E
with `push 0x07`, and 0xE580 is the `lcall` *inside* it. Seeding an entry there
would split a register-preserving forwarder in half — taking the save and the
call away from their matching restore. So the issue's "if it does" branch does
not fire, and **no `--mode rebuild-project` is required by this issue**.

The corollary is the part that *would* need one. The `bank1,0xE582` entry is
unjustified: 0xE582 is a byte inside the `lcall` at 0xE580, not a boundary
anyone branches to. **Retiring that row is filed as the named follow-up below**,
not done here, because removing it changes the export and the committed project
still holds the function — so it only takes effect on a rebuild, which `CLAUDE.md`
records as a deliberate scheduling decision: two branches that both rebuild the
7 MB EC database cannot merge, and the `.gitattributes` entry makes git refuse
rather than text-merge it. The issue frames the rebuild as a separate call for
the same reason. Not bolted onto this change.

## What this opens

- **Retire the `bank1,0xE582` function entry, and re-export.**
  `ec/annotations/ghidra-functions.csv:1191` goes away,
  `ec/decompiled/bank1/E582.{asm,c}` with it, and `common` and `bank1` listings
  meet at 0xE580's `lcall`. Needs `--mode rebuild-project`, and the 0xE57E
  row's name already describes the merged routine correctly
  (`push_r7_call_e5d6_pop_r7`), so no rename is implied. This is the change
  this reading creates.
- **Credit the 0xE580 `lcall` to the call graph.**
  `ec/annotations/call-graph-callees.csv:4` reads
  `bank1,E5D6,FUN_CODE_e5d6,no,,1,1,0,0,0,1,1,3,bank1:E57E bank1:E582 bank1:E5A7`
  — rank 3, `cited_by=3`, `inbound=1`, and that one inbound is `bank1,E5A7`'s
  `lcall`, not this one. So **`bank1,E5D6`'s `inbound=1` is a known undercount**,
  and one of its three `cited_by` comments (`bank1,E582`, whose listing carries
  no transfer to 0xE5D6 at all) is really about the 0xE580 call. Crediting a
  boundary-cut edge is a separate change with its own re-measurement —
  `citation-gap-scan.md` names it, and names `bank0,D091` as the wrong-credit
  precedent — so the table stays **byte-identical** here. This is the concrete
  consequence of the reading.
- **The `disasm8051.decode()` `IndexError`** one-line fix stays recorded as its
  own follow-up in `citation-gap-scan.md`, kept there so this change stays off a
  file another agent may hold.

Explicitly **not** touched here, so a reader does not think it was overlooked:
`bank0,3AD6`'s not-code window and 0x3AF0–0x445D (left to **#543**, which is
open, and the issue says not to re-adjudicate 0x3AF0); the bank0 `0x9F6C`
`cjne` → `0x9F03` row in `bank-relative-branch-targets.csv:3886` (a shared hex
address and nothing else — different scope, different image, a real
`frame_onto=24` relative branch); and `bank-call-targets.csv:4420` itself, per
[the precedent](#the-precedent-is-the-same-argument-on-the-same-shape) above.

## The test that proves it

`ec/tools/test_bank1_e582_framing.py` (new; picked up by
`bash tools/run-tests.sh`, which globs `test_*.py` per directory — no gate edit,
since `agent-gates.sh` is pipeline-copied and must not be edited). It asserts the
byte facts **from the committed image and the committed tables**, not by
re-running the scan that produced them, and deliberately does not duplicate
`test_citation_gap_scan.py`, which already pins the 0xE580 window and its five
bytes:

1. `bank1[0xE57E:0xE586] == c0 07 12 e5 d6 d0 07 ef` — the push / lcall / pop
   save-restore pair.
2. `bank1[0x9F00:0x9F06] == 22 ef 80 02 e5 82` — ret / mov / `80 02` / `e5 82`.
3. `converges_from` gives `(24, 0)` at 0xE580 and 0x9F02, `(0, 24)` at 0xE582
   and 0x9F03.
4. A linear decode from 0x9F01 lands on **0x9F04**, and the two bytes the census
   consumed as a target (`e5 82`) are the first two bytes of the committed
   `ec/decompiled/bank1/9F04.asm` first instruction — the row is
   reconstructible as a misframed read, not merely unsupported.
5. The two committed census rows still carry exactly those frame numbers, read
   by predicate on `runtime`/`target`, so the test fails loudly if the census is
   ever regenerated differently rather than passing on a stale CSV.
6. Both annotation comments contain the correction **and** still contain the
   superseded clause — a presence check, not an exact-prose check, so a later
   edit cannot silently drop the visible retraction `CLAUDE.md` requires.

The mechanical proof that the build agrees:

```sh
python3 ec/tools/build_ec_decompile.py --work /tmp/ec --write-digests
python3 ec/tools/build_ec_decompile.py --work /tmp/ec --check
```

`--mode export-only` re-applies the annotations to a scratch copy, so the
committed 7 MB project is never written and cannot collide with a branch that is
rebuilding it. The two `.c` files change because the annotation comment is
embedded verbatim in the export as the plate comment — `E582.c` carries
"contested rather than established" today — and their committed SHA-256 digests
in `ec/ghidra/c-digests.csv` are rewritten by `--write-digests`. Neither `.c` is
ever hand-edited.

## Re-deriving

From the repository root.

```sh
python3 ec/tools/make_bank_image.py ec/firmware/GMxMGxx_11.800 1 0x10000 /tmp/bank1.bin
python3 ec/tools/disasm8051.py --converge --at 0xE580 /tmp/bank1.bin
python3 ec/tools/disasm8051.py --converge --at 0xE582 /tmp/bank1.bin
python3 ec/tools/disasm8051.py --converge --at 0x9F02 /tmp/bank1.bin
python3 ec/tools/disasm8051.py --converge --at 0x9F03 /tmp/bank1.bin
r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0x9f01; pd 4' /tmp/bank1.bin
r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0xe57e; pd 4' /tmp/bank1.bin
```

The two census rows, and the two listings that rejoin them:

```sh
sed -n '5766p;4420p' ec/annotations/bank-call-targets.csv
head -8 ec/decompiled/bank1/9F04.asm
head -8 ec/decompiled/bank1/9F00.asm
```
