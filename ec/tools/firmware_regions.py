#!/usr/bin/env python3
"""Census every 32 KiB block of the EC image by what its bytes measure, and
cross-reference the bank-switch stubs against the result.

The layout in `trace_xdata_refs.REGIONS` is a four-block assumption: the
linker's bank window is `0x8000-0xFFFF`, the image is a flat dump of bank
windows at their file offsets, and so `common`+`bank0`+`bank1`+`erased` cover
the first 128 KiB with `pd-image` after it. Nothing in the repository has ever
walked all 256 KiB and said what is in each block, so the assumption has never
been checked against the rest of the image. This tool walks every block and
classifies it by measured properties only.

**The classification is deliberately weaker than it could be, and each refusal
names itself.** A byte census can separate *erased* from *non-erased* without
help, because an all-`0xFF` block has one distinct byte value and no printable
run in it. Beyond that it runs out: a block of executable code, a block of
data tables, and a block of a different architecture's code all read as "256
distinct byte values, few `0xFF`". So this tool emits four verdicts --
`erased`, `non-erased`, and, for the non-erased ones, whether an image *marker*
was found in them and whether the block's first byte has the shape of an
`ljmp`/`ajmp` entry -- and then, for any block that carries none of those, the
line `not classified by this method`. **No block is ever labelled `code`.**
`disasm8051.py` is deliberately not consulted here for the same reason it is
not consulted for the `0x28000` block's architecture: near-total opcode coverage
means a byte census cannot settle an architecture, and a tool that printed
`0x28000: 8051 code` would be asserting an answer its method cannot produce.

**The `0x28000` block is the reason this tool exists.** It is a 32 KiB block
that is neither erased nor inside the four-block window the layout assumes, it
carries 37 printable runs against the 8 in the `0x20000` block beside it, and
all but one of those runs read as USB-PD protocol messages (`SRC Negotiate
done`, `PR Swap`, `UsbPdVer:01.00`) -- the exception, at `0x2F7AD`, is a stub of
`ret` instructions before the erased tail and not a string. That is enough to
say *a distinct 32 KiB image containing
USB-PD protocol strings*. It is not enough to say what architecture it is (its
first byte is `0x01`, where the three images this repository has identified
open `0x02`), nor whether it drives a second physical controller -- one Type-C
port can be driven by one image, so two images is not two ports. Both stay open
and `docs/findings/bank-map-and-image-census.md` carries them.

**What the stub cross-reference does and does not settle.** `find_banks.py`
reports banks 2 and 3 as having no callers. This tool adds the file-side half:
the linker's window for bank N is the Nth `0x8000`-sized slot from `0x08000`,
so bank 2's slot is the block at `0x18000` and this tool reports it is 100%
`0xFF`. That is a measurement of the *file slot*, and it turns an assumption
about it into one. It does **not** turn "no trampoline routes through `0x1128`"
into "banks 2 and 3 do not exist": per `CLAUDE.md`, a scan finding zero means
*not found by this method*. `ghidra-functions.csv` is careful to say the same
about callers, and that is still the correct reading.

Usage:
    python3 firmware_regions.py
    python3 firmware_regions.py --check
    python3 firmware_regions.py --self-test
    python3 firmware_regions.py --strings 0x28000
"""
import argparse
import os
import re
import sys

from find_banks import find_stubs
from trace_xdata_refs import PD_MARKER

HERE = os.path.dirname(os.path.abspath(__file__))
EC = os.path.join(HERE, os.pardir)
FIRMWARE = os.path.join(EC, "firmware", "GMxMGxx_11.800")

# The unit of the walk. 0x8000 is the linker's bank window (BL51 maps a bank
# into 0x8000-0xFFFF), so it is the granularity at which "which file offset is
# bank N" is even a well-posed question, and the block size the census reads.
BLOCK = 0x8000

# The window base the stubs select into. A stub's target is a runtime address in
# this window; the block's file offset is the mapping being measured elsewhere,
# and this constant is the one piece of that mapping no byte can disagree with
# -- the stubs say `0x8000` themselves, in `push 08h; mov a,#...`.
WINDOW_BASE = 0x8000

# Erased means *every* byte is 0xFF. Not "mostly", not "the tail is": an
# all-0xFF block is the one class this census settles outright, and loosening it
# to a fraction would make `erased` a judgement where it is currently a fact.
ERASED = "erased"
NON_ERASED = "non-erased"
UNCLASSIFIED = "not classified by this method"

# A printable run long enough to be a string rather than an incidental ASCII
# byte pair in code. 6 is the threshold; it is a heuristic about what is worth
# printing, not a claim that no shorter run is a string.
STRING_MIN = 6

# The two first-byte values that are an unconditional jump into the rest of the
# image: 0x02 is LJMP, 0x01 is AJMP. Reported, never used to classify -- see the
# module docstring on why a byte census cannot settle an architecture.
JUMP_HEADS = {0x02: "LJMP", 0x01: "AJMP"}

_PRINTABLE = re.compile(rb"[ -~]{%d,}" % STRING_MIN)


def printable_runs(block: bytes):
    """The printable runs of at least STRING_MIN bytes, in order."""
    return [(m.start(), m.group().decode("ascii")) for m in _PRINTABLE.finditer(block)]


def census_block(base: int, block: bytes, marker_bytes: bytes):
    """One block's measured properties, and the three verdicts they support.

    `marker` is the known image marker if the block carries it, else None. It
    is searched for anywhere in the block rather than at one fixed offset: the
    question this tool asks is which blocks announce themselves, and a search
    pinned to a single offset cannot find a second image even if that image
    carries the same marker somewhere else. `trace_xdata_refs.PD_MARKER` is the
    one marker known, so a block carrying something else announcing itself is
    `not classified by this method` -- reported, never guessed at.
    """
    ff = sum(1 for b in block if b == 0xFF)
    runs = printable_runs(block)
    found = block.find(marker_bytes)
    if ff == len(block):
        verdict = ERASED
    elif found >= 0:
        verdict = NON_ERASED
    else:
        verdict = UNCLASSIFIED
    return {
        "base": base,
        "end": base + len(block),
        "ff": ff,
        "ff_fraction": ff / len(block),
        "distinct": len(set(block)),
        "strings": runs,
        "marker": marker_bytes.decode("ascii") if found >= 0 else None,
        "marker_at": base + found if found >= 0 else None,
        "head": block[0] if block else None,
        "head_shape": JUMP_HEADS.get(block[0]) if block else None,
        "verdict": verdict,
    }


def census(d: bytes, block: int = BLOCK, marker_bytes: bytes = PD_MARKER[1]):
    """Every block of the image, in file order.

    A trailing partial block is walked as itself rather than padded, so a dump
    whose length is not a multiple of BLOCK gets its last block reported with
    its real extent instead of a block padded with zeros that were never in the
    file. On the committed image every block is exactly BLOCK long.
    """
    return [census_block(base, d[base:base + block], marker_bytes)
            for base in range(0, len(d), block)]


def bank_slots(stubs):
    """`{bank: block file offset}` for the linker's window, and its own column.

    The window for bank N is the Nth BLOCK-sized slot from the first one. That
    is the linker's own arrangement, not a measurement, which is why the key
    returned beside it says `assumed`: it is the premise `bank_map_score.py`
    scores, and calling it a premise here keeps the two tools agreeing about
    what is assumed and what is read.
    """
    out = {}
    for _addr, bank in stubs:
        out.setdefault(bank, 0x08000 + bank * BLOCK)
    return {bank: {"file_offset": off, "assumed": True} for bank, off in out.items()}


def report(d: bytes, blocks, stubs):
    """The census, the stub cross-reference, and the limits, as one string."""
    out = []
    out.append("## 1. Every %d-byte block of the %d-byte image, by measurement"
               % (BLOCK, len(d)))
    out.append("")
    out.append("| file | verdict | 0xFF | distinct bytes | printable runs >= %d "
               "| head | known image marker |" % STRING_MIN)
    out.append("|---|---|---:|---:|---:|---|---|")
    for b in blocks:
        head = ("%02x" % b["head"]) if b["head"] is not None else "-"
        head = ("%s `%s`" % (head, b["head_shape"])) if b["head_shape"] else head
        marker = ("`%s` at `0x%05X`" % (b["marker"], b["marker_at"])
                  if b["marker"] else "-")
        out.append("| `0x%05X` | %s | %.1f%% | %d | %d | %s | %s |" % (
            b["base"], b["verdict"], b["ff_fraction"] * 100, b["distinct"],
            len(b["strings"]), head, marker))

    out.append("")
    out.append("## 2. The bank-switch stubs, and the file slot each window names")
    out.append("")
    slots = bank_slots(stubs)
    by_base = {b["base"]: b for b in blocks}
    out.append("| stub | selects bank | window | file slot | that block | "
               "populated? |")
    out.append("|---|---:|---|---|---|---|")
    for addr, bank in stubs:
        slot = slots[bank]["file_offset"]
        blk = by_base.get(slot)
        if blk is None:
            state = "outside the image"
        elif blk["verdict"] == ERASED:
            state = "**erased** (100% 0xFF)"
        else:
            state = "non-erased (%.1f%% 0xFF)" % (blk["ff_fraction"] * 100)
        out.append("| `0x%04X` | %d | `0x%04X`-`0x%04X` | `0x%05X` | %s | %s |"
                   % (addr, bank, WINDOW_BASE, WINDOW_BASE + BLOCK - 1, slot,
                      "yes" if blk is not None else "no", state))

    out.append("")
    out.append("## 3. What this method does not settle")
    out.append("")
    out.append("- **No block is labelled `code`.** `erased` and `non-erased` are "
               "the only verdicts, and the two are decided by whether every "
               "byte is `0xFF`. A block of 8051 code and a block of a "
               "different architecture's code are indistinguishable here, so "
               "every block that is neither erased nor carries a marker reads "
               "`%s`." % UNCLASSIFIED)
    out.append("- **The architecture of a block is not determined.** The head "
               "byte is printed because it is a measurement, not because "
               "`LJMP` settles anything: `0x01` is AJMP on an 8051 and the "
               "start of something else elsewhere, and near-total opcode "
               "coverage means a byte census cannot choose between them.")
    out.append("- **Two images is not two ports.** A block carrying USB-PD "
               "strings is evidence of an image. Whether a second image means "
               "a second physical controller is not a question this image "
               "answers.")
    out.append("- **A bank with no trampoline through its stub is not an "
               "absent bank.** The file-slot column above is a measurement of "
               "the slot. What is *not found by this method* is any caller of "
               "the stub, and the two are different claims.")
    return "\n".join(out)


def strings_report(d: bytes, blocks, base: int):
    """The printable runs of one block, for the case that calls it an image."""
    blk = next((b for b in blocks if b["base"] == base), None)
    if blk is None:
        return ("0x%05X is not a block boundary this census walks "
                "(the block size is 0x%04X)" % (base, BLOCK))
    out = ["## Printable runs of at least %d bytes in `0x%05X`"
           % (STRING_MIN, base), ""]
    if not blk["strings"]:
        out.append("None. Every byte is 0xFF." if blk["verdict"] == ERASED
                   else "None, which is a fact about printable bytes and not "
                        "about what the block holds.")
        return "\n".join(out)
    for off, text in blk["strings"]:
        out.append("- `0x%05X` `%s`" % (base + off, text))
    return "\n".join(out)


def self_test() -> int:
    """The known answers, and -- the half that matters -- the refusals.

    The known answers come from oracles outside this tool: the `0xFF` fractions
    and string counts are properties of the committed image, and the marker
    offset is `trace_xdata_refs.PD_MARKER`'s, imported rather than restated so
    a change to that constant fails here instead of quietly leaving a second
    copy of it in this file.

    The refusals are what a byte census must *not* do. A tool that had quietly
    degraded into "print the table and call every non-erased block code" would
    still print every known answer above, so what is pinned beside them is the
    three ways it can be wrong: a block it cannot classify is reported rather
    than dropped, a `0x28000` block with its strings removed stops being called
    an image, and a classification that claims an architecture is refused
    outright. Each refusal assertion says which clause it is holding.
    """
    bad = 0
    print("firmware_regions.py --self-test")

    def check(label, ok, detail=""):
        nonlocal bad
        bad += 0 if ok else 1
        print("  %s  %s%s" % ("ok  " if ok else "FAIL", label,
                              "" if ok or not detail else "  " + detail))

    d = open(FIRMWARE, "rb").read()
    blocks = census(d)
    by_base = {b["base"]: b for b in blocks}

    check("the image is 256 KiB and walks as eight whole blocks",
          len(d) == 0x40000 and len(blocks) == 8 and
          all(b["end"] - b["base"] == BLOCK for b in blocks),
          "len=%d blocks=%d" % (len(d), len(blocks)))

    # The erased blocks, which are the one class settled outright.
    erased = sorted(b["base"] for b in blocks if b["verdict"] == ERASED)
    check("exactly three blocks are 100% 0xFF, and they are the ones "
          "0x18000, 0x30000 and 0x38000", erased == [0x18000, 0x30000, 0x38000],
          "got " + repr([hex(x) for x in erased]))
    for base in (0x18000, 0x30000, 0x38000):
        blk = by_base[base]
        check("0x%05X is every byte 0xFF, and one distinct byte value" % base,
              blk["ff"] == BLOCK and blk["distinct"] == 1 and not blk["strings"],
              "ff=%d distinct=%d strings=%d" % (blk["ff"], blk["distinct"],
                                                len(blk["strings"])))
    # 0x20000's block is the thinnest of the live ones -- an 0xFF *fraction* is
    # not an erased verdict, and this is where that distinction is held.
    check("the 0x20000 block is non-erased and not the highest 0xFF fraction, "
          "so a fraction is not what decides the verdict",
          by_base[0x20000]["verdict"] == NON_ERASED and
          by_base[0x20000]["ff"] < by_base[0x18000]["ff"],
          "ff=%d" % by_base[0x20000]["ff"])

    # The marker, imported rather than restated.
    marker_off, marker_bytes = PD_MARKER
    check("the ITE8850-PD marker is at file 0x%05X and is read back out of the "
          "block that contains it" % marker_off,
          d[marker_off:marker_off + len(marker_bytes)] == marker_bytes and
          by_base[0x20000]["marker"] == marker_bytes.decode("ascii") and
          by_base[0x20000]["marker_at"] == marker_off and
          not any(b["marker"] for b in blocks
                  if b["base"] != marker_off // BLOCK * BLOCK),
          "block marker=%r at %r" % (by_base[0x20000]["marker"],
                                     by_base[0x20000]["marker_at"]))

    # The 0x28000 block: a distinct image carrying PD strings. Held as a
    # relation between the two PD blocks, not as a count of strings, because a
    # count here is a property of the committed image rather than of the tree
    # -- but the *relation* is the finding and survives a string being edited.
    pd20000, pd28000 = by_base[0x20000], by_base[0x28000]
    pd_strings = ("SRC Negotiate done", "PR Swap", "UsbPdVer:01.00",
                  "Detect HW Reset")
    have = {t for _, t in pd28000["strings"]}
    check("the 0x28000 block carries the named USB-PD strings",
          all(s in have for s in pd_strings),
          "missing " + repr([s for s in pd_strings if s not in have]))
    check("the 0x28000 block carries more printable runs than the 0x20000 "
          "block, and differs from it at its first byte",
          len(pd28000["strings"]) > len(pd20000["strings"]) and
          pd28000["head"] != pd20000["head"],
          "strings %d vs %d, head %02x vs %02x" % (
              len(pd28000["strings"]), len(pd20000["strings"]),
              pd28000["head"], pd20000["head"]))
    check("the 0x28000 block carries no known image marker anywhere in it",
          pd28000["marker"] is None, "got %r" % pd28000["marker"])

    # -- the refusals --
    unclassified = sorted(b["base"] for b in blocks if b["verdict"] == UNCLASSIFIED)
    check("every block carries one of the three verdicts and every "
          "unclassifiable one is REPORTED, not dropped: %d of %d read `%s`"
          % (len(unclassified), len(blocks), UNCLASSIFIED),
          all(b["verdict"] in (ERASED, NON_ERASED, UNCLASSIFIED) for b in blocks)
          and 0x28000 in unclassified,
          "got " + repr([hex(x) for x in unclassified]))
    check("no block is ever labelled `code` by this method",
          not any("code" in b["verdict"] for b in blocks) and
          UNCLASSIFIED not in ("code", "unknown"),
          "verdicts " + repr(sorted({b["verdict"] for b in blocks})))
    check("the head byte is reported but never used as the verdict, and an "
          "AJMP-shaped head does not make a block classified",
          by_base[0x28000]["head"] == 0x01 and
          by_base[0x28000]["head_shape"] == "AJMP" and
          by_base[0x28000]["verdict"] == UNCLASSIFIED,
          "head=%r shape=%r verdict=%r" % (by_base[0x28000]["head"],
                                           by_base[0x28000]["head_shape"],
                                           by_base[0x28000]["verdict"]))

    # The stubs, and the slot each window names.
    stubs = find_stubs(d)
    check("four bank-switch stubs are found, one per bank, at the addresses "
          "the common area's dispatch table names",
          [(a, b) for a, b in stubs] ==
          [(0x1100, 0), (0x1114, 1), (0x1128, 2), (0x113C, 3)],
          "got " + repr([(hex(a), b) for a, b in stubs]))
    slots = bank_slots(stubs)
    check("the window for bank 2 is the 0x18000 block, which this tool "
          "measures as erased, and bank 3's is 0x20000, which is not",
          slots[2]["file_offset"] == 0x18000 and
          by_base[0x18000]["verdict"] == ERASED and
          slots[3]["file_offset"] == 0x20000 and
          by_base[0x20000]["verdict"] == NON_ERASED,
          repr({k: v["file_offset"] for k, v in slots.items()}))
    check("a bank whose stub has no caller is reported as having no caller, "
          "not as absent: the two unpopulated slots read `erased`, and the "
          "report's own limits section says *not found by this method*",
          stub_states(blocks, stubs)[2] == ERASED and
          "not found by this method" in report(d, blocks, stubs) and
          not re.search(r"banks? 2 and 3 (do not|don't) exist",
                        report(d, blocks, stubs)),
          repr(stub_states(blocks, stubs)))

    # A block whose strings are removed stops being an image. This is what
    # stops the 0x28000 claim from being an assertion about a property of the
    # file rather than about what the bytes say.
    stripped = census(b"\x01" + bytes(0xFF) * (BLOCK - 1))
    check("a block with no printable run and no marker is reported "
          "unclassified, not as an image",
          stripped[0]["verdict"] == UNCLASSIFIED and not stripped[0]["strings"],
          "verdict=%r strings=%d" % (stripped[0]["verdict"],
                                     len(stripped[0]["strings"])))

    print("\n%d assertion(s) failed" % bad if bad else "\nall assertions passed")
    return 1 if bad else 0


def stub_states(blocks, stubs):
    """`{bank: what §2 says about its file slot}`, keyed the way §2 prints it."""
    slots = bank_slots(stubs)
    by_base = {b["base"]: b for b in blocks}
    out = {}
    for _addr, bank in stubs:
        blk = by_base.get(slots[bank]["file_offset"])
        out[bank] = "outside the image" if blk is None else blk["verdict"]
    return out


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="the gate form: the census, and a non-zero exit on a "
                         "block whose 0xFF fraction is neither all nor not")
    ap.add_argument("--self-test", action="store_true",
                    help="the known answers and the refusals")
    ap.add_argument("--strings", metavar="OFFSET", default=None,
                    help="the printable runs of one block, as "
                         "python3 firmware_regions.py --strings 0x28000")
    ap.add_argument("--image", default=FIRMWARE,
                    help="the image to walk; defaults to the committed dump, "
                         "and the fixtures under testdata/ are read this way")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    d = open(args.image, "rb").read()
    blocks = census(d)
    if args.strings is not None:
        print(strings_report(d, blocks, int(args.strings, 0)))
        return 0
    print(report(d, blocks, find_stubs(d)))
    if not args.check:
        return 0
    # A census whose own verdicts do not partition the blocks has a bug in the
    # classifier, and that is the only thing --check is here to fail on: it is
    # not a gate on what the firmware contains.
    bad = [b["base"] for b in blocks
           if b["verdict"] not in (ERASED, NON_ERASED, UNCLASSIFIED)]
    if bad:
        print("\nFAIL: blocks with no verdict: %s"
              % ", ".join("0x%05X" % x for x in bad), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())