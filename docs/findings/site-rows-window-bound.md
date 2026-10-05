# `site_rows()`'s listing is bounded at the region end, and the fifteen erased bytes it used to print as instructions are not a routine

(2026-10-05, issue #1014. Static reading and commands over one committed image,
`ec/firmware/GMxMGxx_11.800`. No capture opened, no EC, no hardware, no
Windows, no `registers.yaml` row touched — nothing here could move one, since
this is Python walking a `bytes` object.)

`--sites 0xFFFF` is a legal call. `0xFFFF` is the top of the 16-bit runtime
space, `check_site_addr()` accepts it, and the PD region is 64 KiB wide, so the
caller named a real address and did nothing wrong. What came back was sixteen
listing lines, and **the last fifteen of them were the erased `0xFF` fill past
the region's end at file `0x30000`, disassembled as `mov r7,a`** — with nothing
in the output saying the routine ended there:

```console
$ python3 ec/tools/pd_index_geometry.py ec/firmware/GMxMGxx_11.800 --sites 0xFFFF
PD runtime 0xFFFF  (file 0x2FFFF)  not a MOV DPTR site; decoded from the anchor itself
  frame 24/24  A=A B=B  -> -
  DPTR += (no term) [chain ends at walk left the pd-image at runtime 0x10000, its end at file 0x30000]
    0xffff  ff       mov  r7,a
    0x10000  ff       mov  r7,a
    ...
    0x1000e  ff       mov  r7,a
```

That is the same defect #843 corrected for `--helpers` on the same legal
argument in the same image, and this is the follow-up its
[`count-bounded-walk-invariant.md`](count-bounded-walk-invariant.md) named.

## The column is the sharpest argument, and it is not about caution

`pd_bounds()` puts the PD region at runtime `0x0000-0xFFFF`. The offending
lines render as runtime `0x10000`–`0x1000e`. **None of those is a PD runtime
address** — they are file offsets from the next `REGIONS` row, printed in a
runtime column whose domain excludes them. That is the same class of defect as
any file offset printed as a runtime address, and it is why
`check_site_addr()`'s refusal goes out of its way to name both ranges.

The window-contract argument that held the loop back does not survive contact
with the two functions it was contrasted against. `walk_helper()` walks to its
`ret` under a `HELPER_MAX_INSNS` cap; `site_rows()` lists a fixed
`SITE_WINDOW` under a fixed budget. Those are the same kind of contract, and the
count bounds the work while the region's end bounds the buffer in both. What
distinguishes them is the caller's expectation, not the loop. The write-up that
made this case for `trace_xdata_refs.walk_why()`'s five tokens,
[`walk-window-terminators.md`](walk-window-terminators.md), puts the other half
plainly: a walk that stops nowhere is a listing with no end. `0xFF` is one byte
and stops nothing, so the listing loop *is* that listing — the argument
concluded the opposite of what it was cited for.

## What changed

**`site_rows()` takes both ends of `pd_bounds()` and clamps `hi` to
`min(hi, len(d))`**, as its two siblings already did, and the listing loop gains
their two region-end stops beside the budget stop: `j` outside `[lo, hi)`, and
an instruction the end cuts — dropped rather than listed short, because a
half-read instruction is not a decodable one.

**One vocabulary, not a fourth.** The three stops are `chain_from()`'s, word for
word: `walk left the {PD_REGION} at runtime … its end at file 0x…`, `the
instruction at runtime … is cut by the {PD_REGION} end at file 0x…`, and
`f"{max_insns}-instruction window ended"`. That is
[`walk-window-terminators.md`](walk-window-terminators.md)'s argument applied
rather than restated. `unmodelled:` is deliberately **not** reused: it is
`walk_helper()`'s completeness flag, consumed by `write_helpers_csv()` and by
`chain_from()`'s chain-stop, and a truncated listing that reused it would read as
an unmodelled routine.

**The row carries both stops.** `site_rows()` already returned `stopped` — the
chain's, rendered as `[chain ends at …]` — and the listing's stop is a second
key beside it, `listing_stop`. It does not shadow `stopped`:
`caller_rows()` reads the row and `print_sites()` renders `stopped` in the chain
bracket.

**`print_sites()` renders the listing's stop always**, including the ordinary
budget stop, which is the one design call here. Every other walk in this module
announces its stop in ordinary operation — `walk_helper()`'s `note` is never
empty and `chain_from()`'s `stopped` is never empty — and a sixteen-line listing
is not distinguishable from a window that ended early without the sentence. The
cost is one line per address on every `--sites` run, reported below as a
behaviour change rather than folded in.

The same run now reads:

```console
  [listing ends at listing left the pd-image at runtime 0x10000, its end at file 0x30000]
    0xffff  ff       mov  r7,a
```

## The pin moved, and the premise it rested on went with it

The `--self-test` asserted `len(top["listing"]) == SITE_WINDOW and 0x3000E <=
peak <= 0x3002C` for `--sites 0xFFFF`, which was a pin that the listing reads
the **full** sixteen instructions. That cannot survive the bound, so it is
replaced by one that pins the new contract — the listing ends at `hi - 1`, its
stop names `0x30000`, and it does not end in `ended` — with a **positive
control beside it**: a mid-region anchor (`0xC2FA`, already named in this file
and in the committed CSVs, so no new magic address) still lists exactly
`SITE_WINDOW` lines with the budget stop. Without that second case a bound
tight enough to stop at the first instruction would pass the first.

Two further cases are synthetic, because the committed image cannot reach them:
an instruction cut needs a multi-byte opcode straddling the end, and this
image's last in-region bytes are all one-byte `0xFF`; the buffer clamp needs a
buffer shorter than the region, and the committed image carries 64 KiB past it.
Both run on `fixture()`.

**`erased_band_holds()` is deleted, and that is a relocation rather than a
loss.** By its own docstring it existed to hold `0x3000E` as a floor. After the
bound nothing in this tool rests on the bytes past the region: the listing's new
end comes from `pd_bounds()`, and the `0x1FFF1` refusal is `check_site_addr()`'s.
Measured, so this is not an assertion about the code: splicing `0x00`, `0x74` or
`0x90` into `0x30000` of a copy of the committed image leaves the `--sites
0xFFFF` listing at one line reading `0x2FFFF` in every case, where it moved the
old peak by one or two bytes.

The premise it asserted — that the `("erased", 0x30000, 0x40000, None, "all
0xFF")` row of `trace_xdata_refs.REGIONS` is what the map says it is — is a
claim about the image map, and it is asserted where the map is:
`python3 ec/tools/check_image_map.py ec/firmware/GMxMGxx_11.800` puts
`d[0x30000:0x40000]` to that test, prints the band's size, distinct byte values
and `0x90` count, and exits non-zero on a band whose bytes do not satisfy it.
Verified by splicing `0x90` into a copy: `check_image_map.py` refuses it naming
`0x30000`, while `pd_index_geometry.py --self-test` stays green, because the
listing stops at the region end either way. `check_image_map.py --self-test`
holds the predicate and the `CHECKED` vocabulary it selects through, so the
measurement keeps the negative control it had in the other tool.
[`erased-band-fill-claim.md`](erased-band-fill-claim.md) records the move.

## What this does not establish

- **"15 of the 16" is a property of these bytes**, not a general figure. `0xFF`
  is a one-byte opcode (`disasm8051.OPCODE_LEN[0xFF] == 1`), so a window over
  this fill advances one byte per instruction and the sixteenth read lands at
  `0x2FFFF + 15`. Three-byte instructions would put it at `0x2FFFF + 45`. It is
  not a claim about any other dump.
- **An arithmetic correction, beside the figure it corrects.**
  `count-bounded-walk-invariant.md` said `--sites 0xFFFF` read "14 bytes past
  the region's last byte". That is measured from the region's *end address*
  `0x30000`; from the last in-region *byte* `0x2FFFF` it is 15, which is why 15
  of 16 lines were the fill. Both numbers were in the corpus and only one was
  right.
- **Nothing is claimed about the firmware's behaviour.** The bytes past
  `0x30000` are `0xFF` on this image and the region ends at `0x2FFFF`; that is
  a statement about a committed file, and `REGIONS` is a heuristic table whose
  bank→offset rows `find_banks.py` scores. Re-derive the map with
  `find_banks.py` before reading the bound against a different dump.
- **The instruction-boundary precondition stays a precondition.** A caller
  naming a mid-instruction address still gets a visibly wrong listing rather
  than a refusal: no byte says where a routine's instructions begin. That is
  #848's `pd-sites-address-range.md` argument and this change does not touch it.
- **`--sites`'s argument check is not re-derived.** `check_site_addr()` is
  #848's, it is not what moved here, and the issue says so.
- **The other `lo, _ = pd_bounds()` sites are still there** — census rows 11,
  12, 17, 18, 20 and `--callers`' unstated argument contract. They are named as
  #843's follow-ups and they are the next sweep, not this change.
- **`pd_stride_families.py`'s own ten-instruction listing loop** in
  `print_site_detail()` is the same shape in a different tool, found while
  checking the consumers of `site_rows()`. Named here, not fixed here.

## Behaviour changes, and the diff pair

Every mode run against the pre-change file and the committed image, stdout and
stderr compared. **Three move, and are reported rather than folded in:**

| mode | what moved |
|---|---|
| `--sites 0xFFFF` | 16 listing lines become 1 — the 15 post-region lines were erased bytes presented as instructions — plus the new stop bracket. A **correction** in #843's sense of the word |
| `--sites 0xFFF0` | listing content unchanged; gains the bracket naming its budget stop |
| `--sites 0xC2FA 0xDA9B` | as above, one bracket per address |

`--helpers 0xFFFF`, `--callers 0x7421`, `--bases`, `--strides` and `--reached`
are byte-identical — asserted by the diff, not claimed here. The two
`ec/annotations/pd-index-geometry.md` §7 captures gain their one bracket line
each, so they stay truthful. No committed CSV is written from this listing
(there is no `--sites-csv`, and `write_callers_csv()` does not carry it); the
`--self-test`'s existing byte-for-byte CSV regeneration is what holds that, and
it passes.

To reproduce the pair, extract the pre-change file from `HEAD` **before this
branch's change lands** — `HEAD` is the pre-change file while the change is in
the working tree, and is the post-change file after the merge, where both
columns would be the after one. The ref `99c01938` that
`count-bounded-walk-invariant.md` names is an older ancestor that predates
several unrelated changes to this tool, so every mode diffs against it; it is
the right ref for that document's own change and not for this one.

```sh
git show HEAD:ec/tools/pd_index_geometry.py > /tmp/old-pd.py
for m in '--sites 0xFFFF' '--sites 0xFFF0' '--sites 0xC2FA 0xDA9B' \
         '--helpers 0xFFFF' '--callers 0x7421' '--bases' '--strides' '--reached'; do
  PYTHONPATH=ec/tools python3 /tmp/old-pd.py ec/firmware/GMxMGxx_11.800 $m > /tmp/before.txt
  python3 ec/tools/pd_index_geometry.py ec/firmware/GMxMGxx_11.800 $m > /tmp/after.txt
  diff /tmp/before.txt /tmp/after.txt > /dev/null && echo "unchanged  $m" || echo "MOVED  $m"
done
```

## Commands

```sh
python3 ec/tools/pd_index_geometry.py ec/firmware/GMxMGxx_11.800 --self-test
python3 ec/tools/pd_index_geometry.py ec/firmware/GMxMGxx_11.800 --sites 0xFFFF
python3 ec/tools/check_image_map.py --self-test
python3 ec/tools/check_image_map.py ec/firmware/GMxMGxx_11.800
bash tools/run-tests.sh ec/tools
```
