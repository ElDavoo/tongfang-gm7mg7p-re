# All 170 of §8's trampoline-landing relative sites are the trampoline block's own operands, and no branch reaches the block from outside it

(2026-09-27, issue #57. Static reading of committed bytes through
`ec/tools/audit_call_targets.py`'s own `trampolines()` and `relative_sites()`.
No capture opened, no EC, no hardware, no Windows, no `registers.yaml` row
touched.)

[`bank-call-audit.md`](../../ec/annotations/bank-call-audit.md) §8 counted 170
PC-relative branch sites that resolve onto a BL51 trampoline entry, and
deliberately did not decide them: exactly one is anchored, so "these are
phantoms" was not a claim the section was willing to make on that evidence. This
is the deciding, and the answer is negative for the question #48 was waiting on.

**All 170 have their own address inside the trampoline block**, `0x1150`-`0x1AC2`
— the 403 entries `trampolines()` finds by shape, each `90 hh ll 02 11 00` or
`90 hh ll 02 11 14`, on an exact 6-byte stride with no gap in 403 entries. Not
one site of all 9076 reaches an entry from outside the block. The byte scan is
therefore reading the block's own `mov dptr,#imm16` **immediate** as a branch
opcode, which is a different failure from the one §8 was worried about: a site
that is inside the block cannot be a caller of it.

**The identity is a byte identity, and it is total over the 170.** 168 of them
resolve to `entry+6` — the entry after the one whose immediate they are — and
168 of the 170 carry `disp == 0x02`, which is the `ljmp` opcode at `entry+3`
being read as the displacement byte. The split is `entry+1` (155 sites, 3-byte
form, displacement from `entry+3`) against `entry+2` (13 sites, 2-byte form,
displacement from `entry+3` as well). The two that are not `disp == 0x02` are
the same artefact reading a different byte: both are 2-byte forms at `entry+1`,
so their displacement comes from `entry+2`, the *low* byte of the immediate.

**The one anchored site is that reading too, and it is not a tail-branch.**
`0x01968` is the `0xDB` — the low byte of `mov dptr,#0xe0db` at `0x1966` — read
as `djnz r1`, with `0x1969`'s `ljmp 0x1100` supplying the displacement and
producing the target `0x196C`, which is the next entry. Its 1-of-24 frame score
is the §2 dense-run artefact, not evidence: a 6-byte-stride table converges from
any walk, which is the whole of what `converges_from()` reports.

**So the #48 question resolves negative, and the negative is exhaustive rather
than a sample.** No rel8 tail-branch edge class has to be added to the
bank-attribution set — every one of the 170 candidate sites is inside the
trampoline block's own `mov dptr,#imm16` immediate, and the scan tests
`d[i] in REL_OPCODES` at every offset of the three audited regions bar the two
at each region's top edge (whose six addresses all hold `0xFF`, not a relative
opcode, so nothing is dropped), which makes 0 of 9076 sites reaching the block
from outside it an exhaustive negative for this image, not a sample.

## The 170, and where they actually are

Every figure below is a group-by over the committed
[`bank-relative-branch-targets.csv`](../../ec/annotations/bank-relative-branch-targets.csv),
following §8's own reproduction block, and over the same `trampolines()` run
every table in that file is derived from. The block's bounds are not a column of
the CSV — adding one would churn a generated file for a property `--self-test`
can assert on every run — so they come from the function, and the CSV supplies
the sites.

```console
$ python3 -c '
import csv, sys
sys.path.insert(0, "ec/tools")
from audit_call_targets import bank_switch_stubs, trampolines

d = open("ec/firmware/GMxMGxx_11.800", "rb").read()
entries = sorted(trampolines(d, bank_switch_stubs(d)))
lo, hi = entries[0], entries[-1] + 6
rows = list(csv.DictReader(open("ec/annotations/bank-relative-branch-targets.csv")))
onto = [r for r in rows if r["calls_trampoline"] != ""]
print("%d entries, block 0x%04X-0x%04X, one %d-byte stride"
      % (len(entries), lo, hi, entries[1] - entries[0]))
print("%d of %d sites onto an entry: %s bank-0, %s bank-1, %s anchored"
      % (len(onto), len(rows),
         sum(1 for r in onto if r["calls_trampoline"] == "0"),
         sum(1 for r in onto if r["calls_trampoline"] == "1"),
         sum(1 for r in onto if int(r["frame_onto"]) > 0)))
for r in onto:
    if int(r["frame_onto"]) > 0:
        print("  anchored: %s %s, %s-byte, disp %s -> %s, frame %s/%d"
              % (r["file_offset"], r["opcode"], r["length"], r["disp"],
                 r["target"], r["frame_onto"],
                 int(r["frame_onto"]) + int(r["frame_over"])))
inb = sum(1 for r in onto if lo <= int(r["file_offset"], 16) < hi)
print("  own address inside the block: %d, from outside it: %d" % (inb, len(onto) - inb))
shape = {}
for r in onto:
    e = entries[0] + (int(r["file_offset"], 16) - entries[0]) // 6 * 6
    k = (int(r["file_offset"], 16) - e, r["length"], r["disp"] == "0x02")
    shape[k] = shape.get(k, 0) + 1
for k, n in sorted(shape.items()):
    print("  entry+%d, %s-byte form, disp %-5s: %d" % (k[0], k[1], "0x02" if k[2] else "other", n))
inblock = [r for r in rows if lo <= int(r["file_offset"], 16) < hi]
print("%d sites have their own address in the block: %d onto an entry, %d elsewhere"
      % (len(inblock), len(onto), len(inblock) - len(onto)))
'
403 entries, block 0x1150-0x1AC2, one 6-byte stride
170 of 9076 sites onto an entry: 168 bank-0, 2 bank-1, 1 anchored
  anchored: 0x01968 djnz, 2-byte, disp 0x02 -> 0x196C, frame 1/24
  own address inside the block: 170, from outside it: 0
  entry+1, 2-byte form, disp other: 2
  entry+1, 3-byte form, disp 0x02 : 155
  entry+2, 2-byte form, disp 0x02 : 13
215 sites have their own address in the block: 170 onto an entry, 45 elsewhere
```

The lowest and highest of the 170 are `0x01151` and `0x01A82`. Both are inside
the span, and so is every one between them: 170 of 170, and 0 of the other 8906.

## The anchored site, read by hand

```console
$ python3 ec/tools/make_bank_image.py ec/firmware/GMxMGxx_11.800 0 0x08000 /tmp/bank0.bin
wrote /tmp/bank0.bin: common 0x0000-0x7FFF + bank 0 (file 0x08000) at 0x8000-0xFFFF
       ╎╎   0x00001966      90e0db         mov dptr, #0xe0db
       └──< 0x00001969      021100         ljmp 0x1100
        ╎   0x0000196c      90e0a2         mov dptr, #0xe0a2
        └─< 0x0000196f      021100         ljmp 0x1100
$ python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x1966 --runtime 0x1966 -n 4
0x1966  90e0db   mov  dptr,#0xe0db
0x1969  021100   ljmp 0x1100
0x196c  90e0a2   mov  dptr,#0xe0a2
0x196f  021100   ljmp 0x1100
```

`0x1966` is an ordinary entry: `mov dptr,#0xe0db` sets DPTR to a bank address
and `ljmp 0x1100` hands over to the bank-0 stub, which is what every one of the
403 entries does. The two bytes between them are the immediate — `0xE0` at
`0x1967`, `0xDB` at `0x1968` — and `0xDB` is `djnz r1`, a 2-byte relative
opcode. That is the site the CSV records as `0x01968,djnz,2,0x02,0x196C`:
`relative_sites()` reads its displacement from `d[0x1968 + 2 - 1] = d[0x1969]`,
which is the `0x02` of the `ljmp`, and lands on `0x196C` — the next entry,
three bytes into the following `mov dptr`. `0x1967`'s `0xE0` is not in
`REL_OPCODES`, which is why only one of the two immediate bytes shows up as a
site and why there is one anchored site here rather than two.

r2's own 24-line score for the site is not evidence either way, and the reason
is §2's, not new: a 6-byte-stride run of identical instruction lengths resyncs
from any starting frame, which is exactly the property that makes a dispatch
table read as a ladder of branches. What the two decoders agree on above is
narrower and is the whole of the claim — the bytes at `0x1966` are a
`mov dptr`/`ljmp` pair — and it is a reading, not a trace.

## The method, and its blind spot

The method is one byte identity, applied in bulk rather than one site at a
time, and it is worth stating in its smallest form because the identity is what
carries all 170 and not the anchor score. For an entry at address `e`, the six
bytes are:

```
e+0  90        mov dptr, #imm16
e+1  hh        \
e+2  ll        /  the immediate
e+3  02        ljmp
e+4  11        \
e+5  00 / 14   /  the target: 0x1100 or 0x1114
```

A relative site at `e+1` reads its displacement from `d[e+3]` (3-byte form) or
`d[e+2]` (2-byte form); one at `e+2` reads from `d[e+3]` (2-byte form) or
`d[e+4]` (3-byte form). Two of those four readings take the `0x02` and produce
`e+6`, the next entry — which is why 168 of the 170 share a target and a
displacement, and why the population looked like a family rather than noise.
The other two read a byte of the immediate or of the `ljmp`'s own address
instead, and that is the two exceptions, read individually because they are the
only two that are not the common case:

| site | form | displacement read | target | the bytes it is reading |
|---|---|---|---|---|
| `0x01637` | `djnz` 2-byte at `e+1` of the entry at `0x1636` | `d[e+2] = 0x91` = `-0x6F` | `0x15CA` | `90 d9 91 02 11 00` — `0x91` is the low byte of `mov dptr,#0xd991` |
| `0x0195B` | `djnz` 2-byte at `e+1` of the entry at `0x195A` | `d[e+2] = 0xFD` = `-3` | `0x195A` | `90 df fd 02 11 00` — `0xFD` is the low byte of `mov dptr,#0xdffd`, and the target is the site's own entry |

Both are the same artefact with a different displacement source, both land on a
real address inside the block, and neither is a branch. `0x15CA` is a trampoline
in its own right (`90 c9 25 02 11 00`), and `0x195A` is the entry the site
belongs to, so the displacement the scan computed happens to name the same
block twice over; that is a coincidence of a 6-byte stride, not a decode.
Neither is evidence that anything executes at either address.

**The blind spot is stated rather than argued away: this decides only sites
whose own address is inside a block already known to be code, and it takes that
block's framing as given.** So it cannot discover a trampoline `trampolines()`
missed — an entry spelled in a shape the function's `d[i - 3] != 0x90` test
does not admit would be invisible here exactly as it is to every other count in
`bank-call-audit.md`. That is a real ceiling and it is the same one §2's
enumeration had; what makes it tolerable here is that the block is corroborated
three ways that do not depend on this finding:

- 403 entries on an **exact 6-byte stride with no gap**, first at `0x1150`,
  last at `0x1ABC` — a run of 403 well-formed instructions is not what a data
  table looks like, and `--self-test` now asserts the stride rather than
  assuming it;
- every one of the 403 ends `02 11 00` (350 of them) or `02 11 14` (53) — two
  targets, matching §2's 350 through the bank-0 stub and 53 through the
  bank-1 one, and all 403 immediates name an address at or above `0x8000`;
- the four stub sites' `C0 08 74` prologue is pinned by an existing
  `--self-test` line, so the two `ljmp` targets above are the stubs that
  prologue lives in.

That is also exactly the ceiling: what licenses the reading is the block's
independent framing, and nothing here would detect a block entry outside it.

## The other 45 in-block sites

215 relative sites in all have their own address inside the block. 170 land on
an entry and the other 45 do not: 44 land elsewhere inside the block and one,
`0x01A99`, lands at `0x1ACC` — ten bytes past the block's end. They are
the same class, at `entry+2` (29 of them) and `entry+1` (16), reading
`d[entry+4]` and `d[entry+2]` respectively, and the 29 at `entry+2` all read
the same `0x11` — the middle byte of `ljmp 0x11xx`. **They are reported here
and not expanded**, because nothing turns on them: whether a site inside a
6-byte-stride block resolves to a byte of the block or past its end, the site
is not a branch into anything, and the #48 question is already answered by the
population that resolves *onto* an entry.

## What this means for #48

**The sentence, stated once and meant to be quoted:** no rel8 tail-branch edge
class has to be added to the bank-attribution set — every one of the 170
candidate sites is inside the trampoline block's own `mov dptr,#imm16`
immediate, and the scan tests `d[i] in REL_OPCODES` at every offset of the three
audited regions bar the two at each region's top edge (whose six addresses all
hold `0xFF`, not a relative opcode, so nothing is dropped), which makes 0 of
9076 sites reaching the block from outside it an exhaustive negative for this
image, not a sample.

It lands in [`bank-attribution.md`](../../ec/annotations/bank-attribution.md)'s
`## 5. Named blind spots` (line 412), where the `jmp @a+dptr` computed-target
blind spot next to it is the other edge class a byte scan cannot resolve, and in
its `## 9. Follow-ups this hands on` (line 588). **Neither is edited here.**
That file belongs to #48, and pre-empting an open issue's own write-up is the
merge conflict [`CLAUDE.md`](../../CLAUDE.md) warns about; citing the two
locations is what makes the placement obvious to whoever picks it up.

**Why the negative is exhaustive, which is the one place the usual calibration
runs the other way.** Everything else in this repository's byte scans gets
stated as *not found by this method*, because over-counting is what they do
wrong. A byte scan can invent a branch that is not there — a `0x02` that is
somebody's operand — but it cannot miss a real one: a rel8 branch is a rel8
opcode at its own PC, and `relative_sites()` reports every such byte it finds.
So §8's over-counting, the thing that makes the 170 look like phantoms, is
one-directional and does not threaten the count of *external* sites, which is
the number #48 needs. The one place a byte scan can under-report is
`relative_sites()`'s guard `i + OPCODE_LEN[op] <= hi`
(`ec/tools/audit_call_targets.py:176`), which declines a 3-byte form in a
region's last two bytes rather than read its displacement out of the next
region. That is six addresses — `0x7FFE`, `0x7FFF`, `0xFFFE`, `0xFFFF`,
`0x17FFE`, `0x17FFF` — and **all six hold `0xFF`**, which is `mov r7,a` and not
a relative opcode, so on this image the guard drops nothing at all. Even
hypothetically the gap would not reach: the six are all above the block's
highest byte `0x1AC1`, and a rel8 target cannot fall more than 128 below the
next PC, so the lowest any of them could reach is `0x7F81`. Which is why this
is a ruling and not a sample.

## What this does not say

- **No live test ran.** No EC was opened, no register read back, no capture
  opened, no hardware and no Windows involved. Every number here is a static
  read of `ec/firmware/GMxMGxx_11.800` or of a group-by over a committed CSV.
- **No EC claim.** This is a statement about bytes in three audited regions of
  one image. It is not a claim about the EC's behaviour, and not a claim about
  any other dump — a different image gets the two new `--self-test` lines
  re-checked, not this verdict inherited.
- **No `registers.yaml` `status:` moved**, and none should: an edge is not
  evidence the EC acts on anything, which is what §8 said and this does not
  change.
- **The 45 in-block sites are not decided**, only counted and located. See
  `## The other 45 in-block sites`.
- **The block's framing is taken as given**, and this finding cannot check it.
  See `## The method, and its blind spot`.
- **§7's paged family is a different population and is not decided here.** §7
  read two of its own hits by hand and found the same shape — `0x15BA` is the
  `0x81` low byte of the `mov dptr,#0xc881` at `0x15B8` — and the 16 §7 did not
  read are #54's population and its own anchor rate. One sentence of
  resemblance, and no more.

## Reproducing it

All from the repository root, all over committed inputs.

```sh
# 1. the new guard, and the existing lines it sits after
python3 ec/tools/audit_call_targets.py ec/firmware/GMxMGxx_11.800 --self-test

# 2. the generated CSV is untouched by any of this
python3 ec/tools/audit_call_targets.py ec/firmware/GMxMGxx_11.800 \
  --relative-csv | diff - ec/annotations/bank-relative-branch-targets.csv

# 3. the hand decode of the one anchored site
python3 ec/tools/make_bank_image.py ec/firmware/GMxMGxx_11.800 0 0x08000 /tmp/bank0.bin
r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0x1966; pd 4' /tmp/bank0.bin
python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x1966 --runtime 0x1966 -n 4

# 4. the group-by every figure above comes from is the console block under
#    "## The 170, and where they actually are"
```

Command 2 must print nothing. `audit_call_targets.py` over the committed image
is **not** in `.github/scripts/agent-gates.sh` — the cheap tier runs
`registers.yaml`, `scan_refs.py`, the register counts, the Ghidra-tooling loop,
`py_compile`, shellcheck and the doc-link check — so the guard rides in the
tool's own `--self-test`, and nothing under `.github/` has to move for it.

The guard is written to name the case it exists for, and the case is
demonstrable rather than hypothetical. Planting an `sjmp` at `0x1144`, twelve
bytes below the first entry, with the displacement that reaches `0x1150`, turns
the line red and the count from 170 to 171:

```
committed -> ok   all 170 relative site(s) resolving onto a trampoline entry have their own address inside the block's 0x1150-0x1AC2, so none of them is a branch reaching the block from outside it
planted   -> FAIL all 171 relative site(s) ... -- reached it from outside at 0x01144
```

That is two bytes written into a copy of the image in a scratch script, not a
different dump, and the point is that the line is a check and not a comment.

## Follow-ups this opens

- **#54**, the paged half of the same question, is untouched and stays open. The
  resemblance between §7's two hand reads and this population is noted above and
  nothing more; its 16 unread sites have their own anchor rate and #54 is where
  they belong.
- **#48** consumes the sentence above, in its own file and by its own
  implementer. This finding is the input, not the edit.
- **#53 stays open on its own terms.** It was the stated fallback blocker and it
  is not one: deciding these 170 needed the framing of a block already known to
  be code, not a code/data map of the common area. Nothing here re-scopes it,
  closes it, or answers it.
- Nothing else is queued. The `--self-test` lines are what keep this closed: an
  image that ever produces a branch reaching the block from outside it names
  itself, and an image whose block is not a 6-byte-stride run says so too.
