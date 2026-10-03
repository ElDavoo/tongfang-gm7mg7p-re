# The `lcall 0x5a5a` at 0x0049 sits inside the version-string record, and the edge is a census false positive (issue #703)

**Verdict: the `lcall 0x5A5A` the call-target census booked at 0x0049 is a
false positive, and 0x5A5A is not the start of anything.** Both ends of the
edge are table bytes, and neither end is a hypothesis here — the bytes say what
they are, and what they say is checkable with `python3 -c`.

The lead, first, because the reading below is only worth what its limit is
worth. `disasm8051.converges_from` returns a pair of counts, and its own
docstring says to "read the pair, not either half" and warns that a site nobody
syncs onto is not thereby misframed — it may simply be preceded by data no
linear walk can decode into alignment. `docs/findings/citation-gap-scan.md`
§"What the tool cannot decide" carries the same limit for the same column:
`frame_onto`/`frame_over` are "evidence about framing, not proof of it", and its
§"The boundary-cut pairs, read one by one" gives `bank0,D091` as the case of a
data island decoding exactly as convincingly as code, naming
`citing-listing-evidence.md` as the standing warning. **Here the scores point
the wrong way** — they read *for* a real call at both disputed addresses — and
[§the column does not separate the two cases](#the-column-does-not-separate-the-two-cases)
gives the offsets that make them useless. Nothing below is a proof.

**Nothing else moves.** No register `status:`, no annotation row added or
edited, no function entry seeded or retired, no `--mode rebuild-project`, and
`ec/annotations/call-graph-callees.csv` stays byte-identical under
`call_graph.py --check`. No hardware and no Windows: this is a bounded static
read of committed bytes, so nothing is deferred to a human at the machine.

This adjudicates the one candidate `neighbour-edge-attribution.md`
§"The six that name a different site" called the strongest of its six — the one
where a committed annotation and the call graph flatly disagree rather than
merely naming different sites. That file credited and retracted nothing and set
out "what a recovered edge would need before it is credited"; this is the
adjudication for that one row, and it concludes there is no edge to credit.

## The caller end: 0x0046-0x005F is one record, and it ends in a version string

Twenty-six bytes, and the `lcall` is three bytes into the ten-byte prefix:

```
0046  a4 95 85 12 5a 5a aa 7b 55 55 49 54 45 20 45 43 2d
0056  56 31 34 2e 36 20 20 20 00
```

The last sixteen bytes are `ITE EC-V14.6` padded with spaces and closed by a
NUL. That string is already recorded in `docs/hardware-identity.md`, and
`ec/README.md` and `ec/annotations/lightbar-bat-flow.md` both give its file
offset as `0x50`. What this adds is the other end of it: **the run reaches its
terminator.** The `12 5a 5a` at 0x0049 is bytes 3-5 of the record's ten-byte
prefix, ending four bytes short of the string's first byte at 0x0050 — inside
the 26-byte record, not inside the string — and there is nothing in the ten
bytes before it that saves the alternative reading: no save, no restore, no
instruction that reaches the end of the record.

This is a *positive* reading of the bytes, not an absence claim, and the
distinction is the house one: nothing here says no code exists at 0x0046. It
says these twenty-six bytes are a version-string record, and the census's
transfer-shaped triple is bytes 3-5 of its prefix.

Two things make it more than a string that happens to be nearby.

**The triple is unique.** `12 5a 5a` occurs exactly once in all 256 KiB, at
0x0049. There is one occurrence in the image, and it is inside the record.

**The census disagrees with itself about these bytes, one byte apart.** The
0x0049 row's `earlier_record` cell — the tool's own non-circularity check, the
record starting one or two bytes earlier that spans the site — reads
`0x00048 85 12 5a mov 0x5a,0x12`. Those three bytes are 0x0048-0x004A, so the
competing record **shares 0x0049 and 0x004A with the booked `lcall`**, and the
same tool renders the same two bytes two ways. That is the sharpest statement
available that this site is framing-sensitive rather than merely unproven. It
is corroboration and not the verdict: `audit_call_targets.py`'s own docstring
calls `earlier_record` "a candidate generator, not an adjudicator".

## The bracket: two jump tables and the image's only `a5` run

The record does not sit in open bytes. It is bracketed:

```
0035  02 11 6e 02 11 74 02 11 7a   22 22      ljmp table, targets 0x116E/0x1174/0x117A
0040  a5 a5 a5 a5 a5 a5                        six 0xa5, the only a5{4,} run in the image
0046  a4 95 85 12 5a 5a aa 7b 55 55 49 ...    the record
0050  ... 49 54 45 20 45 43 2d 56 31 34 2e    "ITE EC-V14.6   "
0056  36 20 20 20 00                          ... NUL
0060  02 11 80 02 11 86 02 11 92 ... 22       ljmp table, targets 0x1180..0x119E
0070  75 81 c0 90 10 01 74 3f f0              mov 0x81,#0xc0 / mov dptr,#0x1001 / ...
```

Both `02 hi lo` runs aim into one narrow ascending band, 0x116E to 0x119E, in
steps that are multiples of 6 — not all of them 6, since 0x1186 to 0x1192 is
12. Two runs of `02` bytes aiming at the same block is what makes them one
family of table rather than `02` bytes that happen to align. They are bounded
on both sides: each stops on a `22` that is not `02`, and what follows 0x006F
reads as a routine (`mov 0x81,#0xc0`, `mov dptr,#0x1001`, `mov a,#0x3f`,
`movx @dptr,a` — a write of 0x3F to XDATA 0x1001) rather than more table.

This is the shape `ec/annotations/data-regions.yaml` records for a jump table,
and the six `0xa5` bytes are what makes it readable: **`a5{4,}` occurs exactly
once in the whole image**, at 0x0040. That is the gap between the two tables,
and it is a run, not a guess about where the first one stopped.

## The callee end: 0x5A5A is offset 7 inside a group the image holds ten times

The fifteen bytes

```
3c 3c 46 5a 60 64 6e 8c aa c8 c8 c8 c8 c8 c8
```

are present at 0x5813, 0x58d3, 0x5993, 0x59c3, 0x5A53, 0x5A83, 0x5B13,
0x5B43, 0x5BD3 and 0x5C03. **0x5A5A is at offset 7 inside the copy that starts
at 0x5A53** — the `8c`, which reads as `mov 0xaa, R4` — and it is not the
start of any of the ten. A `8c aa` followed by six `c8` that occurs once is a
little routine; the same fifteen bytes occurring ten times is a table row, and
`common/5A5A.asm` is a listing whose first instruction is the eighth byte of
one.

The run does not stop where the annotation reads a return either. The 0x5A55
row records a `reti` at 0x5A62, and the byte there is `0x32` — but 0x5A63 is
another `0x32`, and the eight after it ascend: `32 32 34 36 38 3a 3c 40 42 44`.
A `reti` the bytes do not mark is the strongest part of the case against code
here, and it is worth being exact that this *corroborates* the annotation
rather than correcting it.

## The column does not separate the two cases

`converges_from` on the committed image gives **23 of 24 onto 0x0049** and
**24 of 24 onto 0x5A5A**. Read alone, that favours a real call: the two sites
are exactly what the docstring's warning says cannot be settled by the count.

It cannot be settled by the count *here*, and the controls are the reason. Every
score below is matched by an offset this file has already shown to be a table
byte:

| offset | score | what it is |
|---|---|---|
| 0x0049 | 23/24 | the booked `lcall` — disputed |
| 0x5A5A | 24/24 | offset 7 in a repeated group — disputed |
| 0x0046, 0x0047, 0x0051, 0x005B, 0x005C | 24/24 | **inside the caller record**, including the ASCII `T`, `6` and space |
| 0x004E, 0x0053, 0x0056, 0x0057, 0x005A | 23/24 | **inside the caller record** |
| 0x5A53, 0x5A55, 0x5A5D-0x5A61, 0x5A62 | 24/24 | **inside the callee group**, including the five `c8` after the `8c aa` and the `32` the annotation reads as `reti` |
| 0x0060 | 23/24 | first entry of the second `ljmp` table |
| 0x631F | 24/24 | interior to the 6-byte record at 0x631E, and not a record start under the stride-3 framing either; the census reads `02 00 46` across a record boundary as `ljmp 0x0046` |

The first three groups are the ones that matter, and the third is the sharpest:
24 of 24 at 0x5A5A, 24 of 24 at each of the five `c8` bytes three further along
in the same run, and 24 of 24 at the `32` the annotation reads as a `reti` —
every one of them a byte this file has already shown to be table data. The
score is not measuring what the reading needs it to measure. **The verdict
rests on the bytes above and on nothing else** — which is what
`bank1-e582-entry-framing.md` §"One column deliberately not banked" insists,
for the same reason.

## What this settles, and what it does not

**This settles the graph's claim, not the annotation's.** The evidence
corroborates `table_bytes_disassembled_as_code_5a55` on both points it makes,
in its own words: the run at 0x5A43-0x5A5A is "a sequence of small immediates",
the bytes 0x5A5A-0x5A61 "disassemble as `xch A, R0`, not as a return", and
"whether any code at all is at 0x5A55 is not established". So under
`CLAUDE.md`'s calibration rule **there is nothing to retract in place**, and the
row's `unresolved` stands in both columns. That is worth stating plainly,
because the issue's phrasing left open whether the row's status would resolve
as a side effect. It does not, and it should not.

One detail in that comment, recorded so a reader checking this file's byte
listing against it is not surprised: the run it calls "0x5A43-0x5A5A" lists
its first byte as `00`, which is at 0x5A42. 0x5A43 is `30`. The byte count and
the rest of the description are right, the consequence for the reading is none,
and nothing here corrects it in place — the comment is embedded verbatim in the
exported `.c`, so editing it changes the export and forces the re-export this
issue declines.

Deliberately not touched, each with its reason:

- **Retiring the `common,0046` and `common,5A5A` seed rows.** Both are
  `call-target`-seed, `annotated=no` placeholder rows in
  `ec/decompiled/index.csv`. Removing either needs `--mode rebuild-project`,
  and `CLAUDE.md` records that two branches which both rebuild the EC database
  cannot merge — `.gitattributes` makes git refuse rather than text-merge it.
  This is the change the reading creates, and it is a scheduling decision, not
  a judgement call. Named here rather than bolted on.
- **The census row `ljmp 0x0046` at 0x631F.** A separate row, a separate
  claim, and the second inbound to 0x0046. `02 00 46` occurs exactly once in
  all 256 KiB, at 0x631F, and **0x631F is not a record start in the run it sits
  in** — so the census read its transfer across a record boundary, the same
  shape `bank1-e582-entry-framing.md` retired at 0x9F03. *Which* record it
  lands inside is the uncertain half, and this file does not settle it. The
  better-evidenced framing is the 6-byte one: the run walks at stride 6 from
  0x62D6 without a break, and three of those records repeat byte for byte 0x24
  later — `0x62D6`/`0x62FA` are both `0f 04 00 46 14 14`, `0x62DC`/`0x6300` are
  both `19 03 00 64 14 14`, `0x62E2`/`0x6306` are both `19 02 00 0f 0a 0a` — so
  0x62D6 is an anchor rather than an arbitrary start, and on that reading the
  record covering 0x631F begins at 0x631E, with the triple at offsets 1-3 of it.
  A stride-3 grid of small-byte triples fits the same bytes and puts 0x631F at
  offset 2 of a record at 0x631D, and the repeats do not exclude it: 0x24
  divides by 3 as well, so what they fix is the anchor, not the stride. That
  reading is therefore available rather than refuted — but it holds only if the
  grid is anchored at 0x62D6, and 0x631D is not. **The conclusion this bullet
  needs is the framing-independent one: under either candidate framing the
  triple is interior, never at a record start.** That is recorded here and not
  adjudicated: it is a different pair of bytes, and adjudicating it here would
  make the unit of adjudication two edges. It also has no listing behind it —
  `call_graph.py` builds the graph from the committed `.asm` listings and there
  is no `common/631F.asm`, which is why `common,0046` never appears in
  `call-graph-callees.csv` at all. One follow-up for both halves.
- **Adding either run to `ec/annotations/data-regions.yaml`.** Its `shape`
  vocabulary is closed at five values — `ljmp-table`, `be-words`,
  `ff-triples`, `addresses`, `repeat-bytes` — and neither run is an instance of
  any of them: the record is a version string with mixed prefix, and the group
  copies are irregularly spaced rather than a contiguous stride. Forcing a fit
  would make `data_regions.py --check` re-derive a claim about the wrong thing.
  This needs a vocabulary extension, which is its own change.
- **`bank-call-targets.csv` and `call-graph-callees.csv`.** Both are tool
  output and regenerate byte for byte. `bank1-e582-entry-framing.md` is the
  precedent: a phantom row is retired **in prose**, because a hand edit would be
  undone on the next run *and* would be a pure merge hazard on files of that
  length. `call_graph.py --check` staying green is the mechanical proof that
  this change moved no number.

## The test that proves it

`ec/tools/test_common_5a5a_edge_framing.py` (new; picked up by
`bash tools/run-tests.sh`, which globs `test_*.py` per directory — no gate edit,
since `agent-gates.sh` is pipeline-copied). It asserts the byte facts **from
the committed image and the committed tables**, and deliberately does not
duplicate `test_bank1_e582_framing.py`, which is the same argument on the
0x9F03 row. It pins:

1. the common area is the firmware file's own first half, so a common-area
   address used as a file offset below is the file offset;
2. `common[0x0046:0x0060]` is the 26-byte record, and `common[0x0050:0x006F]`
   is `ITE EC-V14.6   ` with `common[0x005F] == 0x00`;
3. `12 5a 5a` occurs exactly once in the image, at 0x0049;
4. `a5{4,}` occurs exactly once in the image, at 0x0040, six bytes long, and
   the two `02 hi lo` runs bracket the record and stop on a `22`;
5. the group occurs at the ten offsets listed, and `0x5A5A - 0x5A53 == 7` with
   `0x5A5A` at none of them — the "not a record boundary" claim as arithmetic;
6. `common[0x5A62]` and `common[0x5A63]` are both `0x32` and the eight bytes
   after ascend;
7. **the frame scores and their controls together** — the disputed pair, the
   neighbours inside both runs, and 0x0060 and 0x631F. This is the case that
   makes the section above a test rather than a sentence;
8. the census row still reads `lcall` / `0x5A5A`, its `frame_onto`/`frame_over`
   equal the recomputed pair, and its `earlier_record` names 0x00048 with the
   three bytes the image holds there;
9. `call-graph-callees.csv`'s `common,5A5A` row and both `call-target` seed
   rows in `index.csv` are present and unedited — this change deliberately did
   not move either table.

## Re-deriving

From the repository root.

```sh
python3 -c "
d=open('ec/firmware/GMxMGxx_11.800','rb').read()
print('record 0x0046-0x005F:', d[0x46:0x60].hex(' '))
print('string  0x0050-0x005F:', repr(d[0x50:0x60].decode('latin1')))
print('a5 pad  0x0040-0x0045:', d[0x40:0x46].hex(' '))
print('ljmp before 0x0035-0x003F:', d[0x35:0x40].hex(' '))
print('ljmp after  0x0060-0x006F:', d[0x60:0x70].hex(' '))
print('what follows   0x0070-0x0077:', d[0x70:0x78].hex(' '))
print('12 5a 5a occurrences:', [hex(i) for i in range(len(d)-2) if d[i:i+3]==b'\x12\x5a\x5a'])
print('02 00 46 occurrences:', [hex(i) for i in range(len(d)-2) if d[i:i+3]==b'\x02\x00\x46'])
g=bytes.fromhex('3c 3c 46 5a 60 64 6e 8c aa c8 c8 c8 c8 c8 c8')
print('group copies:', [hex(i) for i in range(len(d)-14) if d[i:i+15]==g])
print('0x5A5A offset in its copy:', hex(0x5A5A-0x5A53))
print('0x5A62 onward:', d[0x5A62:0x5A6C].hex(' '))
r=[(0x62D6+6*i, d[0x62D6+6*i:0x62D6+6*i+6]) for i in range(22)]
print('stride-6 repeats (all-0x32 padding dropped):',
      sorted({(hex(a),hex(b),v.hex(' ')) for i,(a,v) in enumerate(r)
              for b,w in r[i+1:] if v==w and v.strip(b'\x32')}))
print('record at 0x631E:', d[0x631E:0x6324].hex(' '), ' 0x631E-0x62D6 =', 0x631E-0x62D6)
print('0x631F on the stride-6 grid?', (0x631F-0x62D6)%6,
      ' stride-3 at 0x62D6?', (0x631F-0x62D6)%3, ' stride-3 at 0x631D?', (0x631F-0x631D)%3)
"
python3 ec/tools/make_bank_image.py ec/firmware/GMxMGxx_11.800 0 0x10000 /tmp/b0.bin
for a in 0x0046 0x0049 0x0051 0x0060 0x5A5A 0x5A5D 0x631F; do
    python3 ec/tools/disasm8051.py --converge --at $a /tmp/b0.bin
done
python3 ec/tools/disasm8051.py --at 0x0070 /tmp/b0.bin
```

The two table rows, read by predicate rather than by line number:

```sh
python3 -c "
import csv
for r in csv.DictReader(open('ec/annotations/bank-call-targets.csv')):
    if (r['runtime'], r['target']) in (('0x0049','0x5A5A'), ('0x631F','0x0046')):
        print(r['file_offset'], r['runtime'], r['opcode'], r['target'],
              r['frame_onto'] + '/' + r['frame_over'], repr(r['earlier_record']))
"
python3 ec/tools/call_graph.py --check
python3 ec/tools/gen_findings_index.py --check
bash tools/run-tests.sh
```