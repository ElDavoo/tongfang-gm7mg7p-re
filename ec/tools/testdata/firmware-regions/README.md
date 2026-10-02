# firmware-regions fixture

**Nothing here was read from an EC.** `census-example-image.bin` was written by
hand to exercise `../firmware_regions.py`'s branches; not one of its bytes is
evidence of anything about the real dump. It carries the obviously placeholder
`2026-01-01` timestamp so it can never be mistaken for a capture.

It is a binary file with no header comment, which is the only form that works
here: `census()` walks the image in `0x8000`-sized blocks from offset zero, so
anything prepended would shift every block boundary and the fixture would stop
being the shape it claims to be. The claim that it is constructed is this file
and the timestamp, not a header inside it.

| file | what it pins |
|---|---|
| `census-example-image.bin` block `0x00000` | an `LJMP`-headed block with no image marker — the `not classified by this method` verdict, reached on the committed dump too but with no marker anywhere to contrast it against |
| `census-example-image.bin` block `0x08000` | the `ITE8850-PD` marker **at `+0x1234`**. The committed dump carries it at `+0x40`, so a search pinned to one offset finds it there and nothing here; this block is what a search has to be doing for the real case to be found at all |
| `census-example-image.bin` block `0x10000` | every byte `0xFF` — the one verdict a byte census settles outright |
| `census-example-image.bin` block `0x18000` | an `AJMP`-headed block carrying PD-like printable runs and no marker: an AJMP-shaped head and a string table are both reported, and neither makes the block classified |
| `census-example-image.bin` block `0x20000` | a **partial** trailing block, of `0x1234` bytes rather than `0x8000`, filled with `0x00` rather than `0xFF`. The walk has to report it at its real extent, and `0x00` is not `erased`: "every byte is `0xFF`" is what decides the verdict, not "the tail is padding" |

The `0x00` tail is the fixture's quietest and most useful case. A census that
had loosened `erased` from *every* byte to *most* bytes would report the whole
image as erased or near it, and would still be right about every block whose
bytes are real code — which is all of them on the committed dump. Only a block
that is padded rather than blank separates the two rules, and nothing in a real
dump provides one.

**It is *not* a prediction that the committed image has a second firmware
image at `0x28000`, that any block is 8051 code, or that the real marker
appears anywhere but at `+0x40`.** The `0x28000` block is a *finding* about the
committed dump, read with `../firmware_regions.py` and written up in
`../../../../docs/findings/bank-map-and-image-census.md`; this fixture is the
shape that makes the tool able to report it.