# The data regions behind the EC's phantoms: six tables, four addresses moved (issue #50)

`ec/annotations/bank-call-audit.md` §2 and §5 read several byte ranges in
`ec/firmware/GMxMGxx_11.800` as data tables rather than instructions. That
reading lived in prose in one file, so every tool in `ec/tools/` rediscovered
the same phantoms and every future write-up re-derived them by hand — which is
how a phantom eventually gets reported as a finding.
`ec/annotations/data-regions.yaml` makes the reading machine-readable and
`ec/tools/data_regions.py` holds it to the image.

**The finding that matters is not the table. It is that four of the six ranges
were wrong**, in a way that is worth understanding rather than merely
correcting: in two of the four the address in the issue is a *scan site*, not
a table boundary, and the two look identical in a hex dump. `0x0035C` is entry
15 of a 120-entry table whose real start is `0x032F`. `0x006940` is not an
entry boundary at all — `d[0x6940] = 0xDE` is the **address byte** of the entry
at `0x693E`. The other two, `0x55D0` and `0x66C`, are simply given late; and
the sixth address, `0x006E78`, is 3.17 repeats into a 6-byte repeating byte
pattern, and there is no word table there to find. This is the strongest
argument the issue has for the file it asked for: the addresses that were
transcribed wrong are wrong in exactly the way the file is meant to make
mechanical.

Every figure below comes from re-deriving the bytes. Nothing here is a
behavioural claim, no `status:` in `registers.yaml` moves, no listing was
re-exported, and nothing was observed on hardware.

## What the re-derivation found

| the issue says | the bytes give | confidence |
|---|---|---|
| `0x0035C`-`0x003B4`, 3-byte `ljmp` step 6 | **`0x032F`-`0x0496`, 120 entries**, targets `0x11F2`-`0x14BC` step 6 | `read-by-hand` |
| `0x0055D0`+, descending BE words | **`0x55A8`-`0x5671`, 101 words**, `0x03E8`..`0x0071` | `read-by-hand` |
| `0x0066C`+, common-area addresses | **`0x0656`-`0x07B5`, 176 words** — stride **not** uniform | `inferred` |
| `0x006940`+, `FF <addr>` triples | **`0x690B`-`0x695B`, 27 entries**, `0x1678`..`0x1714` step 6 | `read-by-hand` |
| `0x0219C`+, `FF <addr>` triples | **`0x219C`-`0x21B3`, 8 entries** — start exactly right | `read-by-hand` |
| `0x006E78`+, BE word table | **not a word table.** `0x6E65`-`0x6E7C` is `10 42 10 41 10 40` × 4 | `read-by-hand` |

Half-open ranges, so the table's `0x0496` is the YAML's `file_hi` of `0x0497`.
A seventh region is not in the issue at all and is listed because a named
phantom needs somewhere to land: `0x6E7D`-`0x6E8E`, 9 descending words, which is
the word table the `0x006E78` claim was probably reaching for — five bytes off.

## The payoff, measured against the audit's own table

`bank-call-audit.md` §1 lists bucket C's ten best-framed sites. Nine of the ten
now resolve to a listed region, and **the one that does not is the one the
audit had placed inside one**:

| site | audit reads | score | region | entry-aligned |
|---|---|---:|---|---|
| `0x00686` | ljmp `0xFD03` | 24/24 | `common-0656-address-table` | yes |
| `0x021C6` | lcall `0xE000` | 24/24 | **none** | — |
| `0x06952` | ljmp `0xFF17` | 24/24 | `common-690b-ff-triples` | **no** |
| `0x06E83` | ljmp `0xAA02` | 24/24 | `common-6e7d-be-words` | yes |
| `0x0067E` | ljmp `0x9B01` | 23/24 | `common-0656-address-table` | yes |
| `0x055DC` | ljmp `0xEC02` | 23/24 | `common-055a8-be-words` | yes |
| `0x055E0` | ljmp `0xD402` | 21/24 | `common-055a8-be-words` | yes |
| `0x055E4` | ljmp `0xBC02` | 19/24 | `common-055a8-be-words` | yes |
| `0x055EA` | ljmp `0x9702` | 17/24 | `common-055a8-be-words` | yes |
| `0x00381` | lcall `0x9402` | 15/24 | `common-032f-ljmp-table` | **no** |

**The `yes` on the two `common-0656-address-table` rows is superseded, not
reversed.** `bank-call-regions.csv` leaves both `0x00686` and `0x0067E` with an
**empty** `entry_aligned`, because that region's stride is not uniform — its
`note` in `data-regions.yaml` records that only 121 of its 176 words are
`0x032F + 3k` — so the modulo this table's `yes` answers is a grid the file
does not claim. The cell declines the question rather than saying `no`; see
[`bank-call-regions-csv.md`](bank-call-regions-csv.md) §"`entry_aligned`: three
values, keyed on `confidence`" for the rule.

Three things in that table are worth more than the count.

**`0x06952` and `0x00381` score 24-of-24 and 15-of-24 and are still not
entry-aligned.** Both sit inside a listed region at an offset that is not a
multiple of the region's stride — `0x06952` is 71 bytes into a stride-3 region,
`0x00381` is 82 bytes into a stride-3 one. So *in a region* and *on an entry
boundary* are two different questions, and the column the tools print answers
the first while the region map answers the second. A site that is inside a
table but off its grid is a table entry read one byte out of frame, which is
the phantom mechanism precisely; a site inside a table *on* the grid is the
table.

**`0x021C6` is the interesting one, and §4 is about it.** It scores 24 of 24
— tying `0x00686`, `0x06952` and `0x06E83`, all four in the table above at
24/24 — and it is **the only one of the four that no region covers**. That is
the claim; "the strongest site in bucket C" was a unique maximum the same
table refutes. See §4.

**`0x00381` is the audit's own worked example, and it is in the table.** The
audit's §5 reads `0x00378`-`0x003B4` as "a `ljmp` dispatch table read one byte
out of frame". That is right about the phenomenon and the real span is
`0x032F`-`0x0496`, 120 entries — `0x00381` is entry 27, one byte past its
start, which is exactly the misframing described.

## §2. The six derivations

Each is one command against the committed image, reproducible as written.

### §2.1 `common-032f-ljmp-table` — 120 entries

```console
$ python3 -c "d=open('ec/firmware/GMxMGxx_11.800','rb').read();o=0x32f
while d[o]==2:o+=3
print(hex(o),(o-0x32f)//3)"
0x497 120
```

`0x035C` is entry 15 of those 120. The issue's `0x003B4` is not entry-aligned
at all: `d[0x378] = 0x12`, and that `0x12` is precisely the opcode byte of the
phantom `lcall 0xXX02` the region is famous for producing. The range mixed the
true start with a misframed end. Targets step by 6 from `0x11F2` to `0x14BC`
and stay in the common area; the byte after the last entry is `0x90`, not
`0x02`, which is what stops the run.

### §2.2 `common-055a8-be-words` — 101 descending words

```console
$ python3 -c "d=open('ec/firmware/GMxMGxx_11.800','rb').read();o=0x55a8
while (d[o]<<8|d[o+1]) < (d[o-2]<<8|d[o-1]):o+=2
print(hex(o-2),(o-0x55a8)//2)"
0x5670 101
```

The issue's `0x0055D0` is 0x34 bytes *into* this table. The phenomenon it names
is real and the audit's own reading of it stands: `0x055DC` **is** entry 26 in
this frame, value `0x02EC`, so the `ljmp 0xEC02` scoring 23 of 24 there is
genuinely a table entry and not a call. The two bytes before the start are
`f0 22` — `movx @dptr,a` / `ret` — so the region begins after a return rather
than at an arbitrary offset. `0x5672` onward is a run of single-byte values,
not more words.

### §2.3 `common-0656-address-table` — 176 words, and the one `inferred` entry

```console
$ python3 -c "d=open('ec/firmware/GMxMGxx_11.800','rb').read();o=0x656
while (d[o]<<8|d[o+1])<0x8000:o+=2
print(hex(o-2),(o-0x656)//2)"
0x7b4 176
```

This is the weakest of the six and the only entry whose confidence is
`inferred`, for a reason worth stating plainly: **the stride is not uniform.**
Every one of the 176 words is a common-area address (`< 0x8000`), and 121 of
them are exactly `0x032F + 3k` for `k = 0..120` — the *entry offsets of the
`0x032F` ljmp table in §2.1*, so this region indexes that table. The remaining
words are not on that progression (`0x0006`, `0x0007`, `0x0114`, `0x018C`,
`0x029B`, `0x04A5`, `0x04B4` and others), so the extent was extended by pattern
to the run's end rather than read edge by edge. `--check` verifies the run and
its bounds; it does not claim every word lies on one stride, and it could not.

The issue's `0x0066C` is 0x16 bytes in. The word at `file_hi` is `0xE490`,
outside the common area, which is what stops the run.

### §2.4 `common-219c-ff-triples` — 8 entries, and the start that was right

```console
$ python3 -c "d=open('ec/firmware/GMxMGxx_11.800','rb').read();o=0x219c
while d[o]==0xff:o+=3
print(hex(o),(o-0x219c)//3)"
0x21b4 8
```

The issue's `0x0219C` is the one range of the six that needed no correction,
and the disagreement in the rest of that sentence is worth explaining: the
start was read off the table, the `0x021C6` was read off a scan site. See §4.

### §2.5 `common-690b-ff-triples` — 27 entries

```console
$ python3 -c "d=open('ec/firmware/GMxMGxx_11.800','rb').read();o=0x690b
while d[o]==0xff:o+=3
print(hex(o),(o-0x690b)//3)"
0x695c 27
```

`d[0x6940] = 0xDE` is the address byte of the entry at `0x693E`, so the issue's
offset is one byte off the 3-byte grid and mid-entry. The address field steps
by 6 throughout; the byte after the last entry is `0x3D`, not `0xFF`.

### §2.6 `common-6e65-repeat-bytes` and `common-6e7d-be-words`

```console
$ python3 -c "d=open('ec/firmware/GMxMGxx_11.800','rb').read();p=bytes.fromhex('104210411040');o=0x6e65
while d[o:o+6]==p:o+=6
print(hex(o),(o-0x6e65)//6)"
0x6e7d 4
$ python3 -c "d=open('ec/firmware/GMxMGxx_11.800','rb').read();o=0x6e7d
while (d[o]<<8|d[o+1]) < (d[o-2]<<8|d[o-1]):o+=2
print(hex(o-2),(o-0x6e7d)//2)"
0x6e8d 9
```

**`0x006E78` is not a big-endian word table.** `d[0x6E78] = 0x42` is the third
byte of a `10 42 10 41 10 40` pattern that repeats four times over
`0x6E65`-`0x6E7C`. The word table the issue was reaching for is the nine
descending words immediately after it, at `0x6E7D`. Both are listed, as two
entries rather than one, because they have different strides and different
checks; they are adjacent, not overlapping, and the suite holds them to that.
`0x06E83` is entry 3 of the second one and is entry-aligned, so the `ljmp
0xAA02` there is a table entry on the same grounds as `0x055DC`'s.

## §3. The corrections, in place

`CLAUDE.md` asks that a retraction leave the wrong version visible with a
correction beside it rather than silently edit history. Three claims are
corrected this way; the two that live in another file are corrected *in that
file*, per the same rule.

- **`bank-call-audit.md` §5**, "`0x021C6` scoring 24 of 24 sits inside them" —
  corrected in place. `0x021C6` is 0x12 bytes *past* the end of the `0x219C`
  triples, not inside them. See §4.
- **`bank-call-audit.md` §5**, "`0x006E78`+ is a big-endian word table" —
  corrected in place. See §2.6.
- **This issue's own six ranges** — the four that moved are corrected in each
  YAML entry's `supersedes` field, with the wrong value kept in the text, and
  in the table at the top of this file.

The audit's §2 reading of `0x055DC` and §5 reading of `0x00378`-`0x003B4` are
**not** retracted: both are right about the phenomenon, and only the extent is
narrower than the issue transcribed. The audit's headline, its 140/83 bucket-C
count, and its verdict are untouched.

## §4. `0x021C6`: a 24-of-24 site no region explains

This is the most interesting result in the diff, and the one that should shape
the follow-up.

`0x021C6` scores 24 of 24 anchors decoding onto it, which **ties** `0x00686`,
`0x06952` and `0x06E83` rather than leading them, and it is the only one of the
four that no listed region covers. The audit placed it inside the `0x219C` triple table. It is not inside it —
the table's last entry byte is `0x21B3` and the site is at `0x21C6`, **0x13
bytes past the end** — `0x12` past the region's `file_hi` of `0x21B4`, the byte
after that last entry, which is the reference the `--self-test` in
`test_data_regions.py` pins — with `d[0x21C5] = 0xE0` between them. So the site
is a 24-of-24 scan hit that no listed region explains: it is one of the **50
anchored bucket-C sites outside every listed region** (§Limits), and the
best-framed of them.

The bytes around it decode as ordinary code from an anchored frame, and
`disasm8051.py` agrees with `r2 -a 8051` byte for byte — both transcripts, so
the agreement is checkable rather than asserted:

```console
$ python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x21B4 -n 6
0x021b4  e0       movx a,@dptr
0x021b5  f0       movx @dptr,a
0x021b6  00       nop
0x021b7  e0       movx a,@dptr
0x021b8  f0       movx @dptr,a
0x021b9  1200e0   lcall 0x00e0
$ python3 ec/tools/make_bank_image.py ec/firmware/GMxMGxx_11.800 0 0x08000 /tmp/bank0.bin
wrote /tmp/bank0.bin: common 0x0000-0x7FFF + bank 0 (file 0x08000) at 0x8000-0xFFFF
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x21b4; pd 6' /tmp/bank0.bin
            0x000021b4      e0             movx a, @dptr
            0x000021b5      f0             movx @dptr, a
            0x000021b6      00             nop
            0x000021b7      e0             movx a, @dptr
            0x000021b8      f0             movx @dptr, a
            0x000021b9      1200e0         lcall 0x00e0
$ python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x21C6 --converge
0x021C6: 24 of 24 preceding anchors decode onto it, 0 step over it
```

**And this is where the calibration rule binds hardest, so nothing more is
claimed than that.** A `movx`/`lcall` run with 24-of-24 anchor agreement is
*not* evidence that `0x021C6` is a real `lcall 0xE000`. `converges_from()`
measures framing, not meaning, and the audit's §2 is explicit that a dense
uniform run resyncs *any* walk — which is the same reason `0x055DC` was a
phantom. Two readings are open and this file settles neither:

1. it is a real call into bank space, in which case bucket C is non-empty in the
   way `offset_for_runtime()` cannot resolve; or
2. it is another misframed table or a legitimate-but-unnamed routine, in which
   case the region map is incomplete.

Deciding it needs a recovered common-area function boundary set, which is a
disassembler's job and issue #20's, and **not** something more static reading
of these bytes can do. What is established is narrower and still useful: *a
24-of-24 bucket-C site now has a name for what would have to be found next.* The
honest follow-up is a census of anchored high-scoring sites that fall **outside**
every listed region — the mirror of what this issue asked for, and the
population where a real call and a phantom look identical.

## Limits

- **Nothing here is a behavioural claim.** No register was read back, no EC was
  opened, no capture was read. Every input is a committed file.
- **No `status:` in `registers.yaml` moves.** These are addresses in a code
  image, not XDATA registers.
- **The regions are not exhaustive, and their absence is not a claim.** The set
  is what one reading of `bank-call-audit.md` §2 and §5 turned up. A span not
  listed is a span this reading did not find — never "not a table". This file's
  entire subject is one method's blind spots, so `docs/findings.md` §4c applies
  to it more than to anything else in the tree: **a zero is "not found by this
  method", never "absent".**
- **It is not a code/data separation of the image.** That is issue #20's goal
  and the first thing this map would feed. Untouched here.
- **It settles none of bucket C.** The 140 sites, 83 anchored, stay `None` from
  `offset_for_runtime()`, and "no direct common-to-bank `lcall`/`ljmp` was found
  by this method" remains the whole claim. A region map makes the *known*
  phantoms mechanically identifiable; it does not clear the other 105 — 50 of
  them anchored, 140 less the 35 the map labels — and §4's `0x021C6` is a
  24-of-24 site it cannot place at all.
- **`inferred` means the extent was extended by pattern**, not that the bytes
  disagree. `--check` verifies stride and shape for both tiers identically; the
  third tier, `inferred-unchecked`, exists so a span `--check` cannot reach can
  say so and be reported as unchecked rather than as a pass. No entry carries
  it today.
- **Entry-aligned is a stronger statement than in-a-region**, and the tools
  print the first while the map holds the second. See the table in §"The
  payoff".

## Re-deriving

```console
$ python3 ec/tools/data_regions.py --check        # every span, from the image
$ python3 ec/tools/data_regions.py --self-test    # the refusals and the oracle
$ python3 ec/tools/data_regions.py --csv
$ python3 ec/tools/data_regions.py --for-offset 0x055DC
$ python3 ec/tools/scan_refs.py ec/firmware/GMxMGxx_11.800 0x07D0
$ python3 ec/tools/audit_call_targets.py ec/firmware/GMxMGxx_11.800
$ bash tools/run-tests.sh ec/tools                # collects test_data_regions.py
```

Each region's `established_by` carries its own derivation command, so an entry
can be re-walked without this file. It is a multi-line `python3 -c` command
held as a YAML **literal** block (`|-`, not `>-`): a folded block joins those
lines with spaces, which leaves a field that still reads as a command, still
names the firmware, and is a `SyntaxError` on paste.
`test_data_regions.py` therefore does not read those fields, it runs them —
extracting the `python3 -c "..."` payload, executing it against the committed
image, and holding what it prints to that entry's own `file_hi` and entry count
with its walk seeded at `file_lo`. All three matter: the printed end alone is
satisfied by a seed that has slid to another entry in the same run, since that
walk still stops in the same place.

**Not in the committed `.github/scripts/agent-gates.sh`, because a branch cannot
edit that file — and a prepared patch already carries the `case` arm.** The file
is a template copy under `.github/`, and the pipeline's push token has no
`workflow` scope, so a branch editing it fails at the very end of the PR rather
than at the start of it. That is why the change is cut and held here instead of
landed, and [`prepared-gate-patches.md`](prepared-gate-patches.md) is where that
account lives. `--check` and `--self-test` **fold into**
[`../ci/agent-gates-disasm8051-self-test.patch`](../ci/agent-gates-disasm8051-self-test.patch)
rather than shipping a seventh file, for the collision reason
`prepared-gate-patches.md`'s table gives: the free hunks in the script are
already spent, so a seventh patch would have to cut the same
`windows/tools/decompile_native.py; do` line to be independently applicable,
and could then not compose with that one in
every ordered pair — a failure that is silent in the way that matters, since each
would still apply cleanly alone. Its `*data_regions.py)` arm runs `--check` as
well as `--self-test`, because `--check` is the mode that holds
`data-regions.yaml` to the committed image, and all four of the patch's strings
sit in `ArmRetentionTests.REQUIRED` in
[`tools/test_agent_gates_patches.py`](../../tools/test_agent_gates_patches.py),
so a re-cut that landed one tool's halves and dropped this one's goes red rather
than passing quietly.

A human can land the prepared patch; what that buys is that the map cannot
drift from the image in an otherwise-green PR, and what it would not buy is
anything about the map being *right* — that is the `read-by-hand` tier and a
human's, not a gate's.

### Reading the column in the tools

`scan_refs.py` and `audit_call_targets.py` **label** a site that lands in a
listed region; neither filters it out. That is the rule the issue states and it
is load-bearing: a scan that dropped the phantoms would report a smaller
number, and a smaller number nobody can audit is indistinguishable from
absence — the `docs/findings.md` §4c failure this repository has two recorded
instances of. So `data_regions.py` has no filtering mode at all, and the refusal
is a function (`refuse_filtering()`) rather than a convention in a comment, for
the same reason `build_ec_decompile.py` refuses its `--out-` paths.

`bank-call-targets.csv` does **not** gain the column. That is a deliberate
deviation from the issue's letter and the reason is in the tree:
`ec/tools/build_ec_decompile.py:206` holds a hard-coded 12-name
`CALL_TARGET_COLUMNS` list marked *asserted rather than assumed*, and its
`--self-test` asserts the committed file against it — and that self-test runs in
the cheap gate. A 13th column turns a gate assertion red for an unrelated
cause, which is the cheapest way to get a gate switched off. The tool's own
`write_paged_csv()` docstring already sets the precedent: *a sibling of
`write_csv()` rather than more columns on it*. So the column ships as a console
column and, for a future consumer, a new sibling CSV. Adding it to the
committed CSV needs `build_ec_decompile.py` edited and is follow-up work, not
this issue's worth of blast radius.

**The committed sibling now exists**, one step further than that sentence
leaves it: `annotations/bank-call-regions.csv`, written and re-derived by
`tools/bank_call_regions.py`. It carries every bucket-C site and every paged
`ajmp`/`acall` site rather than a sample, and it is keyed on `file_offset` alone
so the two populations share one file without a tie to break. It is beside the
console columns above, not instead of them: `scan_refs.py` and
`audit_call_targets.py` are untouched, as are the committed per-site tables.
What it adds is the *second* question — `entry_aligned`, which says whether a
site is on its region's entry grid rather than merely inside the span, and
which `--for-offset` above answers for one address. The cell is three-valued,
`region_confidence` says which of the three a row gets, and
[`bank-call-regions-csv.md`](bank-call-regions-csv.md) is where that rule and its
boundary are argued.
