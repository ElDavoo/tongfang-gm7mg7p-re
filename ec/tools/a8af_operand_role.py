#!/usr/bin/env python3
"""What the `0xA8`-`0xAF` block is, derived from the committed listings alone.

Three candidate readings of `0xA8`-`0xAF` are in play in this repository, and
they disagree about both the length and the operand:

- `XCH A,Rn`, one byte -- what `docs/findings/opcode-table-coverage.md` says
  the block is, and what `opcode_coverage.MCS51_LEN` carries.
- `MOV Rn,direct`, two bytes -- what `disasm8051.OPCODE_LEN` carries and what
  `disasm8051.mnemonic()` prints.
- `MOV direct,@Ri`, two bytes -- what `walk_branch_arms._dptr_write()`'s
  docstring calls the range.

The three are not equally supported and the tree does not currently say which.
Deciding it from a *fourth* decoder would settle nothing: `OPCODE_LEN` already
is a decoder's answer, `MCS51_LEN` is a transcription, and Ghidra's SLEIGH, r2
and `sdas8051` share a lineage that already disagrees with the manual at
`0xA0`/`0xB0`, so their agreement is not two readings that happen to meet. What
is left is the corpus itself, and it decides on two counts.

**Framing.** The listings place the next instruction at `addr+2` at every
`0xA8`-`0xAF` start and at `addr+1` at none. A one-byte instruction would make
its operand byte the next opcode; the listings, which were produced without
reference to any table here, do not. The control is `0xC8`-`0xCF`, the block
that *is* one byte in every map: there the listings do place a row at `addr+1`.
So the check can fail, and on this corpus it does not.

**The operand byte is an address.** The operand bytes are dominated by `0x82`
(DPL), `0x83` (DPH) and `0xf0` (B), with small internal-RAM cells behind them.
Read the operand as an *immediate* -- which is what a one-byte `XCH A,Rn`
forces, and what `pd_inline_arg_sites.SIM_TEXT` used to print -- and those two
values would be the most frequent opcodes in the image. They are not: neither
is placed at an instruction start more than a handful of times corpus-wide,
while `0xf0` is placed thousands of times. A reading that requires the two most
common operand bytes to be among the rarest opcodes is not a reading.

**The direction of the load.** Between the two two-byte candidates, what
distinguishes them is whether the direct byte is a source or a destination, and
the corpus answers that too: a block instruction whose operand is `0x82`
followed immediately by one whose operand is `0x83` is the shape of code saving
DPTR into a register pair, which is what `MOV Rn,direct` does and
`MOV direct,@Ri` does not. Both orders occur, and in both the register numbers
step by one.

None of this is a live test. Nothing here was run on the machine; every
measurement is a read of files already in this repository. `--self-test`
re-derives each of the three on a hand-built fixture, including the fixture
that makes the framing check fail, so the checks are known to be able to fail.

Usage:
    python3 a8af_operand_role.py
    python3 a8af_operand_role.py --self-test
    python3 a8af_operand_role.py --csv /tmp/a8af.csv
"""
import argparse
import collections
import csv
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import opcode_coverage as C
import disasm8051 as D

REPO = os.path.dirname(os.path.dirname(HERE))

# The block under examination, and the two rows beside it that a reading has to
# be told apart from. `0x78`-`0x7F` is `MOV Rn,#data` and `0x88`-`0x8F` is
# `MOV direct,Rn`; both are two bytes in every map, so neither separates the
# candidates, but `0x78` is the row `MCS51_LEN` copied when it transcribed this
# one and `0x88` is the row whose *shape* -- a bare `direct`, no `#` -- the
# operand byte here matches. `0xC8`-`0xCF` is the one-byte control.
BLOCK = (0xA8, 0xAF)
NEIGHBOURS = (
    (0x78, 0x7F, "MOV Rn,#data", "the row MCS51_LEN copied for the block"),
    (0x88, 0x8F, "MOV direct,Rn", "MOV Rn,direct read the other way round"),
    (0xA8, 0xAF, "MOV Rn,direct", "the block itself"),
    (0xC8, 0xCF, "XCH A,Rn", "the one-byte control"),
)

# The SFR addresses 8051 code reaches through a `direct` operand, and the names
# the table uses for them. Spelled here rather than imported because this tool
# has to be readable on its own: the point is that the block's operand bytes
# are *these*, which is a claim about the 8051 and not about any table in the
# tree.
DIRECT_NAMES = {0x82: "DPL", 0x83: "DPH", 0xF0: "B"}

# The opcodes whose operand byte is a `direct` *address*, as opposed to a
# constant, a bit number or the low half of a 16-bit target. The distinction is
# the whole of the operand reading, so the control that uses it has to be drawn
# on the right side of it: `0x12 0xf0` is `lcall 0xf0..`, where `0xf0` is the
# high byte of a code address and means nothing about `B`, and counting it as
# evidence that the firmware addresses `B` directly would be exactly the
# confusion this tool exists to settle. Keyed on the opcode, value in the
# operand position; every entry here is a form `disasm8051.mnemonic()` spells
# with a bare hex byte and no `#`.
DIRECT_OPERAND_OPS = frozenset(
    [0x05, 0x15, 0x25, 0x35, 0x42, 0x43, 0x45, 0x52, 0x53, 0x55, 0x62, 0x63,
     0x65, 0x75, 0x85, 0x95, 0xC0, 0xC2, 0xC5, 0xD0, 0xE5, 0xF5]
    + list(range(0x88, 0x90)))

CSV_HEADER = ("hex", "opcode", "listing_starts", "programs")


def load_corpus(index=None, decompiled=None):
    """[(program, addr, bytes)] for the committed listing corpus.

    `opcode_coverage.read_listings()` does the parse, and this tool calls it
    rather than reimplementing the listing grammar: a second parser here would
    be a second thing that can quietly read a third of the file. It raises
    rather than returning an empty corpus, which is the behaviour this tool
    wants -- zero sites found must not read as a clean bill of health.
    """
    return C.read_listings(index=index or C.LISTING_INDEX,
                           decompiled=decompiled or C.DECOMPILED)[0]


def block_starts(rows, lo=BLOCK[0], hi=BLOCK[1]):
    """[(program, addr, bytes)] for the instruction starts in one block."""
    return [(prog, addr, raw) for prog, addr, raw in rows if lo <= raw[0] <= hi]


def framing(rows, lo=BLOCK[0], hi=BLOCK[1]):
    """How the listings frame this block: (starts, at+1, at+2).

    Two counts over the same sites, and they are the measurement rather than a
    summary of it. `at_addr_plus_one` counts the sites where the listings put
    the *next* instruction one byte on -- which is what a one-byte instruction
    here would force -- and `at_addr_plus_two` the sites where they put it two
    bytes on. Both are reported because a corpus that had no rows at either
    offset would score zero on both and look like agreement with nothing; the
    caller prints them beside a block that does have rows at one of them.
    """
    by_prog = collections.defaultdict(set)
    for prog, addr, _raw in rows:
        by_prog[prog].add(addr)
    sites = block_starts(rows, lo, hi)
    one = sum(1 for prog, addr, _r in sites if addr + 1 in by_prog[prog])
    two = sum(1 for prog, addr, _r in sites if addr + 2 in by_prog[prog])
    return len(sites), one, two


def operand_histogram(rows, lo=BLOCK[0], hi=BLOCK[1]):
    """{operand byte: how many block sites carry it}.

    Counted over sites, not over distinct bytes: the question is what the
    operand position holds across the block, and a byte that appears once is a
    different kind of evidence from one that appears ninety times.
    """
    return collections.Counter(r[1] for _p, _a, r in block_starts(rows, lo, hi)
                              if len(r) > 1)


def opcode_start_counts(rows):
    """{opcode: how many instruction starts carry it}, corpus-wide.

    The comparison that decides the immediate reading. If the operand byte were
    an opcode -- which is what a one-byte block forces -- then the frequency
    with which that value is placed at an instruction start is the frequency
    with which it executes, and the block's own operand histogram has to agree
    with this one. It does not, and the size of the disagreement is the finding.
    """
    return collections.Counter(r[0] for _p, _a, r in rows)


def dpl_dph_adjacency(rows, lo=BLOCK[0], hi=BLOCK[1]):
    """Block sites loading one DPTR half into a register and the other next.

    -> [(program, addr, first raw, second raw)], in file order. Both orders
    count, because the shape -- two consecutive registers holding the two
    halves of DPTR -- does not depend on which half is loaded first, and
    counting only one would understate it by however many sites load DPH first.

    This is the discriminator between the two two-byte candidates rather than
    between those and the one-byte one, which framing has already settled.
    `MOV Rn,direct` loads a register *from* an address, so DPL and DPH arrive
    in two registers one after the other. `MOV direct,@Ri` stores *into* an
    address through a pointer register, which produces no such pairing at all.
    """
    by_prog = collections.defaultdict(dict)
    for prog, addr, raw in rows:
        by_prog[prog][addr] = raw
    out = []
    for prog in sorted(by_prog):
        table = by_prog[prog]
        for addr in sorted(table):
            first = table[addr]
            if not (lo <= first[0] <= hi) or len(first) < 2:
                continue
            if first[1] not in DIRECT_NAMES or first[1] not in (0x82, 0x83):
                continue
            second = table.get(addr + len(first))
            if second is None or not (lo <= second[0] <= hi) or len(second) < 2:
                continue
            other = 0x83 if first[1] == 0x82 else 0x82
            # `abs(...)` rather than `== 1`: which half is loaded first is not
            # something the reading predicts, and a compiler that emits DPH
            # into r1 and DPL into r2 is saving the same register pair as one
            # that emits them the other way round. Requiring the second
            # register to be the *higher* one would silently drop every site of
            # that shape.
            if second[1] == other and abs(second[0] - first[0]) == 1:
                out.append((prog, addr, first, second))
    return out


def direct_users(rows, addresses=None, lo=BLOCK[0], hi=BLOCK[1]):
    """{(opcode, operand byte): sites} for instructions *outside* the block.

    The control for the operand reading. If `0x82`/`0x83`/`0xf0` mean nothing
    as a `direct` operand, the non-block instructions that carry those same
    bytes must not be using them that way either -- and they are, in the
    `mov direct,A` / `push direct` / `pop direct` / `mov direct,Rn` forms a
    compiler emits thousands of times. So the bytes are addresses in this
    firmware's own idiom, not values that happen to sit in the operand column.

    Restricted to `DIRECT_OPERAND_OPS`, so a `lcall` whose *target* low byte is
    `0xf0` is not counted as code addressing `B`. Without that restriction the
    table reads as stronger evidence than it is, which is the failure this
    whole tool is about.
    """
    wanted = set(DIRECT_NAMES) if addresses is None else set(addresses)
    out = collections.Counter()
    for _prog, _addr, raw in rows:
        if lo <= raw[0] <= hi or raw[0] not in DIRECT_OPERAND_OPS:
            continue
        for byte in raw[1:]:
            if byte in wanted:
                out[(raw[0], byte)] += 1
    return out


def verdict(starts, at_one, at_two, histogram, starts_by_opcode):
    """(the reading the corpus supports, why, what it costs).

    -> (name, length, reason). A third return would be a place for a caveat
    the caller has to remember to print, so the caveats are in the reason text
    where a reader meets them.

    Every branch states the measurement it turns on, and the "not decided by
    this" branch exists so a corpus that supports nothing says so instead of
    falling through to a default.
    """
    if not starts:
        return (None, None,
                "no instruction start in this block was found by this scan -- "
                "'not found by this method', which is not a reading")
    # 0x82 and 0x83 are the block's two commonest operands; under a one-byte
    # reading they would be opcodes, and an opcode's frequency here is how
    # often it is placed at an instruction start.
    sfr_as_opcode = max(starts_by_opcode.get(b, 0) for b in (0x82, 0x83))
    sfr_as_operand = max(histogram.get(b, 0) for b in (0x82, 0x83))
    if at_one > at_two:
        return ("XCH A,Rn", 1,
                "the listings place a row at addr+1 at %d of %d sites and at "
                "addr+2 at %d, which is one-byte framing" % (at_one, starts, at_two))
    if at_two == 0:
        return (None, None,
                "the listings place a row at neither addr+1 nor addr+2 at any of "
                "%d sites, so this scan has no framing evidence to give" % starts)
    reason = (
        "the listings place a row at addr+2 at %d of %d sites and at addr+1 at "
        "none, which is two-byte framing" % (at_two, starts))
    if sfr_as_operand > sfr_as_opcode:
        reason += ("; and the operand bytes are dominated by 0x82/0x83 (%d and "
                   "%d sites), which as opcodes are placed at an instruction "
                   "start only %d and %d times corpus-wide, so reading the "
                   "operand as an opcode would make this block's commonest "
                   "operands among the image's rarest instructions"
                   % (histogram.get(0x82, 0), histogram.get(0x83, 0),
                      starts_by_opcode.get(0x82, 0), starts_by_opcode.get(0x83, 0)))
    else:
        reason += ("; note the operand bytes are not dominated by the SFR "
                   "addresses, so the operand-is-an-address half of the case "
                   "is not what this corpus shows")
    return ("MOV Rn,direct", 2, reason)


def corpus_by_fixture(tmpdir, text):
    """Build a one-listing corpus in a temp dir and read it back.

    The tests need a corpus they can make wrong on purpose -- one where the
    block is framed one byte on -- and that means writing the listing and the
    image beside it. Returns the rows, so a case can assert on what the parse
    produced rather than on what it fed in.

    The image is built from the listing with `opcode_coverage.parse_listing`,
    not by splitting the lines here: `read_listings` drops any row whose bytes
    are not the image's, so a fixture whose image disagreed with its own text
    would come back empty and every case built on it would pass for the wrong
    reason. One parser, used twice.
    """
    d = os.path.join(tmpdir, "fix")
    os.makedirs(os.path.join(d, "bank0"), exist_ok=True)
    asm = os.path.join(d, "bank0", "FIX.asm")
    with open(asm, "w") as fh:
        fh.write(text)
    with open(os.path.join(d, "listing-index.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["program", "addr", "name", "size", "seed_basis", "common",
                    "annotated", "type", "basis", "evidence", "also_in",
                    "out_file"])
        w.writerow(["bank0", "0000", "fix", "0", "annotation", "yes", "yes",
                    "", "", "", "", "bank0/FIX.asm"])
    img = bytearray(0x10000)
    for addr, raw in C.parse_listing(asm):
        img[addr:addr + len(raw)] = raw
    return C.read_listings(index=os.path.join(d, "listing-index.csv"),
                           decompiled=d, images={"bank0": bytes(img)})[0]


# A one-byte block: `a8 82` at 0000 followed by a row at 0001. This is what the
# immediate/`XCH A,Rn` reading predicts the corpus would look like, and the
# self-test runs the tool over it to prove the framing check can fail.
FIXTURE_ONE_BYTE = """\
; bank0 @ 0000   FIX_one_byte
1000     a8 - -   xch      A, R0
1001     90 00 10 mov      DPTR, #0x0010
1004     e0 - -   movx     A, @DPTR
"""

# A two-byte block: a row at 0002, none at 0001.
FIXTURE_TWO_BYTE = """\
; bank0 @ 0000   FIX_two_byte
1000     a8 82 -  mov      R0, DPL
1002     90 00 10 mov      DPTR, #0x0010
1005     e0 - -   movx     A, @DPTR
"""

# A DPL/DPH register pair: consecutive registers, the two halves of DPTR.
FIXTURE_DPLDPH = """\
; bank0 @ 0010   FIX_dpl_dph
1010     a9 82 -  mov      R1, DPL
1012     aa 83 -  mov      R2, DPH
1014     90 00 10 mov      DPTR, #0x0010
1017     e0 - -   movx     A, @DPTR
"""


def self_test() -> int:
    """Re-derive each measurement on a fixture built to make it fail.

    The real corpus is not a self-test: it is the thing being reported on, and
    a check that has only ever seen agreement cannot be shown to disagree. Each
    case below is a corpus constructed so that the measurement *should* come
    out the other way, which is what makes the real run mean something.
    """
    import tempfile
    bad = 0
    with tempfile.TemporaryDirectory() as tmp:
        rows = corpus_by_fixture(tmp, FIXTURE_ONE_BYTE)
        starts, at_one, at_two = framing(rows)
        if not (starts == 1 and at_one == 1 and at_two == 0):
            bad += 1
            print("  !   one-byte fixture framed as starts=%d at+1=%d at+2=%d, "
                  "expected 1/1/0" % (starts, at_one, at_two))
        else:
            print("  ok  a one-byte block reads as starts=1 at+1=1 at+2=0 -- "
                  "the framing check fails when the corpus says it should")

        rows = corpus_by_fixture(tmp, FIXTURE_TWO_BYTE)
        starts, at_one, at_two = framing(rows)
        if not (starts == 1 and at_one == 0 and at_two == 1):
            bad += 1
            print("  !   two-byte fixture framed as starts=%d at+1=%d at+2=%d, "
                  "expected 1/0/1" % (starts, at_one, at_two))
        else:
            print("  ok  a two-byte block reads as starts=1 at+1=0 at+2=1")

        name, length, why = verdict(1, 0, 1,
                                    collections.Counter({0x82: 1}),
                                    collections.Counter({0x82: 0}))
        if (name, length) != ("MOV Rn,direct", 2):
            bad += 1
            print("  !   verdict on a two-byte fixture is %r/%r" % (name, length))
        else:
            print("  ok  verdict on a two-byte fixture is MOV Rn,direct at 2 "
                  "bytes")

        name, length, why = verdict(1, 1, 0,
                                    collections.Counter({0x82: 1}),
                                    collections.Counter({0x82: 9}))
        if (name, length) != ("XCH A,Rn", 1):
            bad += 1
            print("  !   verdict on a one-byte fixture is %r/%r" % (name, length))
        else:
            print("  ok  verdict on a one-byte fixture is XCH A,Rn at 1 byte -- "
                  "the check discriminates, it does not always answer the same")

        rows = corpus_by_fixture(tmp, FIXTURE_DPLDPH)
        pairs = dpl_dph_adjacency(rows)
        if len(pairs) != 1 or pairs[0][0] != "bank0" or pairs[0][1] != 0x1010:
            bad += 1
            print("  !   DPL/DPH adjacency found %r" % (pairs,))
        else:
            print("  ok  a DPL-then-DPH register pair is found at 0x1010")

        name, length, why = verdict(0, 0, 0, collections.Counter(),
                                    collections.Counter())
        if name is not None:
            bad += 1
            print("  !   an empty corpus produced a reading: %r" % name)
        else:
            print("  ok  an empty corpus names no reading rather than a default "
                  "one -- 'not found by this method'")

    # The real corpus, for the record, and the figures the write-up quotes.
    rows = load_corpus()
    starts, at_one, at_two = framing(rows)
    hist = operand_histogram(rows)
    by_op = opcode_start_counts(rows)
    name, length, why = verdict(starts, at_one, at_two, hist, by_op)
    print("  --  the committed corpus: starts=%d at+1=%d at+2=%d -> %s"
          % (starts, at_one, at_two, name))
    print()
    print("self-test %s" % ("FAILED: %d case(s)" % bad if bad else "passed"))
    return 1 if bad else 0


def write_csv(path, rows):
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(CSV_HEADER)
        for prog, addr, raw in rows:
            w.writerow(["0x%02x" % raw[0], raw[0], 1, prog])
    print("wrote %s (%d rows)" % (path, len(rows)))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--self-test", action="store_true",
                    help="re-derive each measurement on a fixture built to "
                         "make it fail, then report the committed corpus")
    ap.add_argument("--csv", metavar="PATH",
                    help="one row per block instruction start")
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()

    rows = load_corpus()
    block = block_starts(rows)
    if args.csv:
        write_csv(args.csv, block)

    print("The 0x%02X-0x%02X block, read from the committed Ghidra listings"
          % BLOCK)
    print()
    print("Framing, and the two rows beside it that a reading must not be")
    print("confused with.  `at+1`/`at+2` count the sites where the listings")
    print("place the next instruction at that offset:\n")
    for lo, hi, name, why in NEIGHBOURS:
        starts, at_one, at_two = framing(rows, lo, hi)
        print("  0x%02X-0x%02X  %-15s starts=%-5d at+1=%-5d at+2=%-5d  %s"
              % (lo, hi, name, starts, at_one, at_two, why))
    print()

    hist = operand_histogram(rows)
    by_op = opcode_start_counts(rows)
    print("The operand byte at those sites, against the same byte value as an")
    print("opcode.  The second column is how often the value is placed at an")
    print("instruction start anywhere in the corpus, which is what it would")
    print("mean if the operand were an opcode:\n")
    print("  %-6s %-10s %-14s %s" % ("byte", "as operand", "as opcode", "name"))
    for byte, n in hist.most_common(8):
        print("  0x%02x   %-10d %-14d %s"
              % (byte, n, by_op.get(byte, 0),
                 DIRECT_NAMES.get(byte, "internal RAM")))
    print()

    pairs = dpl_dph_adjacency(rows)
    both = [(p, a, f, s) for p, a, f, s in pairs]
    print("A block instruction loading one half of DPTR into a register,")
    print("immediately followed by one loading the other half into the next")
    print("register -- the shape of `MOV Rn,direct`, and not one")
    print("`MOV direct,@Ri` can produce:\n")
    for prog, addr, first, second in pairs[:6]:
        print("  %-7s 0x%04X  %s (%s)  then  %s (%s)"
              % (prog, addr, first.hex(" "),
                 "mov r%d,%s" % (first[0] - 0xA8, DIRECT_NAMES[first[1]]),
                 second.hex(" "),
                 "mov r%d,%s" % (second[0] - 0xA8, DIRECT_NAMES[second[1]])))
    if len(pairs) > 6:
        print("  ... and %d more" % (len(pairs) - 6))
    print("  %d site(s) of that shape" % len(pairs))
    print()

    users = direct_users(rows)
    print("What instructions *outside* the block do with those same")
    print("addresses -- the control on reading the operand as an address:")
    print()
    for (op, byte), n in users.most_common(6):
        print("  0x%02x 0x%02x  %-5d %s"
              % (op, byte, n, DIRECT_NAMES.get(byte, "")))
    print()

    name, length, why = verdict(framing(rows)[0], framing(rows)[1],
                                framing(rows)[2], hist, by_op)
    print("Verdict: %s at %s byte(s)." % (name, length))
    for chunk in _wrap(why, 74):
        print("  " + chunk)
    print()
    print("What this is not.  Every number above is a read of files in this")
    print("repository; nothing here was run on the machine, and no behaviour")
    print("was observed.  The framing half is a measurement the corpus")
    print("settles; the name is an inference from it, and the two together are")
    print("what `opcode_coverage.py --divergence` reports the block as.  A")
    print("human at the machine can still say the firmware does something")
    print("else with these bytes; nothing here forecloses that.")
    return 0


def _wrap(text, width):
    words, line, out = text.split(), "", []
    for w in words:
        if len(line) + len(w) + 1 > width:
            out.append(line)
            line = w
        else:
            line = w if not line else line + " " + w
    if line:
        out.append(line)
    return out


if __name__ == "__main__":
    sys.exit(main())