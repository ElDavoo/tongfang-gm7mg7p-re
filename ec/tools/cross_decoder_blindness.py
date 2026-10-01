#!/usr/bin/env python3
"""What the cross-decoder's `vacuous` bucket is made of (issue #350).

`build_ec_decompile.py` records `ec/ghidra/cross-decoder.csv` and ratchets on
it, and its largest bucket is `vacuous` -- a function whose straight-line
opening names no XDATA address, so the comparison had nothing to match. The
denominator line prints how many of those there are and stops, which is
correct and is also the last word on a row whose exported `.c` plainly names
several: `outcome` answers *did the comparison agree*, and for a window that
found no address there was no disagreement to report. So `vacuous` is one
answer covering several different situations, and a reader of the ratchet is
invited to take "no address in the opening" for "nothing there".

This classifies every `vacuous` row into what its absence is *made of*, and
commits the classes as a `blind` column in a sidecar over the same
`(program, addr)` keys. It adds nothing to `CROSS_DECODER_OUTCOMES`, changes
no outcome, and touches no register status: `denominator_line()` and
`degenerate_sample_problems()` are the same functions they were, so the
ratchet keeps meaning what it means today. The reasoning for not extending the
vocabulary is the docstring's last section.

**The four classes, and the order they are decided in.** `entry-is-branch` is
asked first because it is a fact about one byte and holds whatever the `.c`
says: a decompile that names nothing at all still has an entry byte, and for a
function whose entry is a branch the empty window is accounted for twice over
-- once by "the C names nothing" and once, more strongly, by "the window was
never going to hold anything".

  entry-is-branch          The byte at the function's entry is in
                           `disasm8051.FLOW_OPCODES`, so the window is empty by
                           construction and could be nothing else. The
                           comparison stops on instruction one by design and
                           the body is past the branch: a boundary artefact of
                           the comparison's own rule, not a decompile defect.
                           `insns`=0 is exactly this class -- recomputed here
                           from the firmware, and asserted against the report
                           rather than read out of it.
  no-xdata-named           The `.c` names no XDATA address at all. There is no
                           address in question, so this is neither a blind spot
                           nor an absence -- it is the bucket that keeps the
                           other three from being read as one thing.
  named-past-first-branch  The opening is real and holds no `mov dptr,#imm`,
                           but walking the function's *own listing extent* --
                           `stop_at_flow=False`, the listing's `size` and not
                           `CROSS_DECODER_WINDOW`, because the question here is
                           "is the literal in this function at all" rather than
                           "is it in the window" -- finds one whose address the
                           `.c` names. A real match, one branch too late.
  no-literal-named         The `.c` names an address and the function's own
                           listing never loads that address into DPTR. The
                           pointer arrives from the caller or is built by
                           arithmetic from a base.

**Why the walk is over the listing's extent and not the window.** 204 of the
sampled rows decode to more than `CROSS_DECODER_WINDOW`'s 40 instructions over
their own extent, and the longest is 316 (`bank0 0x9D9B`, 627 bytes). A walk
held to the window would therefore answer "is it past the first branch" for the
small functions and "is it anywhere" for the large ones -- two questions
wearing one name, and a split whose answer depends on a function's length. The
question here is the second of those.

**The residue is not split further, and that is the deliberate refusal.** The
issue asked for `no-literal-named` to be divided into "reached through a
caller-supplied pointer" and "DPTR built by arithmetic from a base". Telling
those apart means reading each `.c` and deciding what its pointer algebra
means; a regex proxy does produce buckets -- `*param_N`, `+ 0x..`, neither --
but they are not the issue's two, and they are a guess about intent wearing a
count's clothes. It is `CROSS_DECODER_OUTCOMES`'s own stated reason for
leaving `disagree` as one bucket: *guessing which of a function's C reads is a
fold would manufacture the very distinction the comparison is meant to
measure.* So the class states what is true of every row in it, and the finer
split is named in `../../docs/findings/cross-decoder-blind-population.md` as
the thing a future method has to earn.

**And no outcome is added, which is a decision rather than an omission.**
`outcome` answers "did the comparison agree", and `vacuous` is a correct answer
to that; *why* the row named nothing is orthogonal metadata about the row, not
a different verdict. The issue's alternative -- following the branch's target
inside the comparison -- is the larger change: it redefines what the window is,
so every committed row moves and the baseline has to be re-measured rather
than re-derived. That is its own issue, and the write-up says so.

**The header comment is stripped before the `.c` is read, and the census does
not depend on the rule.** The annotation comment above the signature is prose
written by a person or an agent, and it names addresses the decompiled body
does not -- `ACB4.c`'s comment lists eleven registers its body never mentions.
Counting that would let an annotation's own summary read as a finding about
the decompile. It is identified by the one thing that makes it that comment
rather than any other block comment (a `type:` field line; Ghidra's own
`/* WARNING: ... */` lines carry none) and removed. `--self-test` asserts the
four counts come out identical when *every* block comment is removed instead,
so the rule is a held fact and not a reading of one.

**Nothing here is measured on hardware.** Every class is a property of
committed bytes, committed listings and a committed decompile. A register
being absent from a function's opening says nothing about whether the EC acts
on it: `ec/annotations/registers.yaml` keeps 0x07D0 at
`unknown-not-absent-DO-NOT-WRITE-BLIND`, and no class here reads a `vacuous`
row as an absence.

Usage:
    python3 cross_decoder_blindness.py
    python3 cross_decoder_blindness.py --report
    python3 cross_decoder_blindness.py --check
    python3 cross_decoder_blindness.py --self-test
"""
import argparse
import csv
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import disasm8051
# The comparison's own file-offset map, its own `mov dptr,#imm` opcode and its
# own address-spelling regex, not copies of them. This tool asks the same
# question about the same bytes that `compare_function()` does, so a second
# offset map or a second spelling of "names an XDATA address" would be a second
# thing to keep in step with the first -- and would let the 0x07D0 question
# this measures be answered two ways.
from build_ec_decompile import (CROSS_DECODER, LISTING_INDEX, MOV_DPTR, OUTDIR,
                                REPO, _EXTMEM, file_offset, read_index)

FIRMWARE = os.path.join(REPO, "ec", "firmware", "GMxMGxx_11.800")
BLINDNESS = os.path.join(REPO, "ec", "ghidra", "cross-decoder-blindness.csv")

# The sidecar's columns. `program`/`addr` are the key the parent's `--check`
# joins on, `outcome` is carried so a reader can see why a row is blank without
# opening the parent, and `name` so a red `--check` line names a function rather
# than a bare address. `insns` is deliberately *not* carried: `entry-is-branch`
# is recomputed from the firmware precisely so that it is not the column, and a
# copy of it beside the class would be a second answer to the same question.
BLIND_COLUMNS = ["program", "addr", "name", "outcome", "blind"]

# What a `blind` cell may say. A controlled vocabulary, for the reason
# `CROSS_DECODER_OUTCOMES` is one: a fourth reading of `vacuous` smuggled in as
# a synonym would keep the counts right and let `--check` go green on a
# distinction nobody agreed to. Held by name in `self_test()`, never by length.
NO_XDATA_NAMED = "no-xdata-named"
ENTRY_IS_BRANCH = "entry-is-branch"
NAMED_PAST_FIRST_BRANCH = "named-past-first-branch"
NO_LITERAL_NAMED = "no-literal-named"
BLIND_CLASSES = (ENTRY_IS_BRANCH, NO_XDATA_NAMED, NAMED_PAST_FIRST_BRANCH,
                 NO_LITERAL_NAMED)

# What each class means, in a reader's terms, printed under the counts on every
# run. A bucket name a reader has to look up is a bucket name nobody reads.
CLASS_REASONS = {
    NO_XDATA_NAMED:
        "the C names no XDATA address at all, so there is no address in "
        "question -- not a blind spot, and not an absence either",
    ENTRY_IS_BRANCH:
        "the export's entry is a branch, so the window stops on instruction "
        "one by design and the body is past it",
    NAMED_PAST_FIRST_BRANCH:
        "the opening is real and names no address, and the function's own "
        "listing extent holds one the C does name: a match one branch too late",
    NO_LITERAL_NAMED:
        "the C names an address the function's own listing never loads into "
        "DPTR, so the pointer arrives from the caller or is built by "
        "arithmetic from a base -- which of the two is not decided here",
}

# A block comment, and the one line that tells the exporter's annotation comment
# apart from any other. Both anchored on the comment rather than on a position:
# a `.c` whose annotation is absent carries no such block, and one whose
# decompile opens with a Ghidra warning carries that block first.
_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.S)
_ANNOTATION_FIELD = re.compile(r"^[ \t]*type:[ \t]", re.M)
# A committed listing line: address, three fixed byte slots, then the mnemonic
# and its operands. Anchored on the whole shape rather than searched for, so a
# line that is a comment or a wrapped operand is skipped rather than parsed as
# though it were an instruction -- `asm_opening_bytes()`'s rule and its reason.
_ASM_LINE = re.compile(r"^[0-9A-Fa-f]{4}\s+([0-9A-Fa-f]{2}|-)\s+"
                       r"([0-9A-Fa-f]{2}|-)\s+([0-9A-Fa-f]{2}|-)\s+(\S+)\s*(.*)$")


def repo_path(path):
    return os.path.relpath(path, REPO)


def strip_header_comment(text):
    """The `.c` with the exporter's annotation comment removed.

    The comment is found by the `type:` field it carries rather than by being
    first, because Ghidra's warnings are block comments too and some of them
    come first. A `.c` with no annotation is returned whole -- there is nothing
    to remove, and that is not a failure.
    """
    out, at = [], 0
    for m in _BLOCK_COMMENT.finditer(text):
        if _ANNOTATION_FIELD.search(m.group()):
            out.append(text[at:m.start()])
            at = m.end()
    out.append(text[at:])
    return "".join(out)


def strip_every_comment(text):
    """Every block comment removed. `--self-test`'s control for the rule above."""
    return _BLOCK_COMMENT.sub("", text)


def names_an_address(text):
    """The XDATA addresses the text carries, as the comparison spells them."""
    return {m.upper() for m in _EXTMEM.findall(text)}


def extent_literals(fw, program, addr, size):
    """Every address the function's own listing extent loads into DPTR.

    `stop_at_flow=False`, deliberately and against the comparison's own rule:
    the branch is what this has to walk past, and the whole of
    `named-past-first-branch` is that it exists.
    """
    if not size:
        return set()
    file_off = file_offset(program, addr)
    limit = file_off + size
    out = set()
    for i, raw, _text in disasm8051.decode(fw, file_off, size, addr=addr,
                                          stop_at_flow=False):
        if i >= limit:
            break
        if raw[0] == MOV_DPTR:
            out.add("%04X" % ((raw[1] << 8) | raw[2]))
    return out


def entry_is_branch(fw, program, addr):
    """True when the byte at the function's entry is one a window ending at the
    first flow instruction would stop on.

    Computed from the image rather than read out of the report's `insns`
    column, and that is the point: `insns`=0 is *this class with no second
    reading* -- a listing of size zero would also decode nothing, and a tool
    that read the column would call that the same thing. `self_test()` asserts
    the identity over the committed report, both directions, and names the
    zero-size case rather than assuming it away.
    """
    return fw[file_offset(program, addr)] in disasm8051.FLOW_OPCODES


def asm_instructions(program, addr):
    """[(mnemonic, operands), ...] as the committed listing renders them.

    `--self-test`'s oracle, read from the committed `.asm` rather than from the
    image. `extent_literals()` and `entry_is_branch()` both walk the firmware
    with `disasm8051`'s own tables, so the only thing that can contradict them
    is the record the exporter wrote of the same bytes; without this they would
    be two functions agreeing with themselves. A line whose shape is not the
    exporter's is skipped rather than parsed as though it were, which is
    `asm_opening_bytes()`'s rule -- an oracle that parses whatever it finds is
    an oracle that agrees.
    """
    path = os.path.join(OUTDIR, program, "%04X.asm" % addr)
    if not os.path.isfile(path):
        return []
    out = []
    with open(path, errors="replace") as f:
        for line in f:
            if line.startswith(";") or not line.strip():
                continue
            m = _ASM_LINE.match(line.rstrip("\n"))
            if m:
                out.append((m.group(4), m.group(5).strip()))
    return out


def asm_dptr_operands(program, addr):
    """The addresses the committed listing renders as `mov DPTR, #0x…`."""
    return {ops.split("#", 1)[1] for mnem, ops in asm_instructions(program, addr)
            if mnem == "mov" and ops.startswith("DPTR, #")}


def c_body(out_file, strip):
    """The exported C's body, or None when the row carries no export."""
    if not out_file or out_file.startswith("("):
        return None
    path = os.path.join(OUTDIR, out_file.replace(".asm", ".c"))
    if not os.path.isfile(path):
        return None
    with open(path, errors="replace") as f:
        return strip(f.read())


def classify_body(body, fw, program, addr, size):
    """One decompiled body over one function's bytes. -> a class, or "".

    Split from `classify()` so the branch order can be exercised against
    hand-made bytes: the file read is the only part of the question that needs
    the tree, and everything downstream of it is arithmetic over `fw`.

    `entry-is-branch` is asked first, and the order is the measurement rather
    than a preference: a decompile that names no address still has an entry
    byte, and for a function whose entry is a branch the empty window is
    accounted for twice over -- once by "the C names nothing" and once, more
    strongly, by "the window was never going to hold anything". Reading them
    the other way round leaves 223 rows of the 356 in `no-xdata-named` and
    makes `insns`=0 stop meaning `entry-is-branch`, which is the one identity
    the whole class rests on.
    """
    if body is None:
        return ""
    if entry_is_branch(fw, program, addr):
        return ENTRY_IS_BRANCH
    named = names_an_address(body)
    if not named:
        return NO_XDATA_NAMED
    if named & extent_literals(fw, program, addr, size):
        return NAMED_PAST_FIRST_BRANCH
    return NO_LITERAL_NAMED


def classify(fw, program, addr, size, out_file, strip=strip_header_comment):
    """One sampled row's `blind` class, or "" for a row that is not in scope."""
    return classify_body(c_body(out_file, strip), fw, program, addr, size)


def blind_rows(fw, strip=strip_header_comment):
    """The whole sidecar, in the parent's row order. -> [row, ...].

    Every parent key appears, and only a `vacuous` row carries a class. A row
    the parent has stopped sampling is therefore a row this file has to drop,
    which `--check` can say -- and a sidecar holding only the classified rows
    could not tell that from a row the classifier had stopped reaching.
    """
    listing = {(r["program"], r["addr"]): r for r in read_index(LISTING_INDEX)}
    rows = []
    for parent in read_index(CROSS_DECODER):
        program, addr_hex = parent["program"], parent["addr"]
        listed = listing.get((program, addr_hex))
        blind = ""
        if parent["outcome"] == "vacuous" and listed is not None:
            blind = classify(fw, program, int(addr_hex, 16),
                             int(listed["size"]), listed["out_file"], strip)
        rows.append({"program": program, "addr": addr_hex,
                     "name": parent["name"], "outcome": parent["outcome"],
                     "blind": blind})
    return rows


def census(rows):
    """{class: n} over BLIND_CLASSES, every key present."""
    counts = dict.fromkeys(BLIND_CLASSES, 0)
    for row in rows:
        if row["blind"]:
            counts[row["blind"]] += 1
    return counts


def census_line(rows):
    """The line a reader takes away: how much of the vacuous bucket is which,
    beside how much of the sample was ever compared."""
    counts = census(rows)
    compared = sum(1 for r in rows if r["outcome"] in ("agree", "disagree"))
    return ("  the %d vacuous row(s) are %s, out of %d sampled function(s) of "
            "which %d were compared" % (
                sum(counts.values()),
                ", ".join("%d %s" % (counts[c], c) for c in BLIND_CLASSES),
                len(rows), compared))


def blindness_problems(committed, current):
    """The committed sidecar against this run's rows. -> (compared, problems).

    Three ways the file can stop describing the tree, and the same three
    `build_ec_decompile.cross_decoder_problems()` fails on for the same reason:
    a row it carries that the sample no longer has, a sampled row it does not
    carry, and a row whose recomputed cells differ. Every column is compared, so
    a renamed function or an outcome that moved is caught as well as a
    reclassified row -- the same ratchet the parent keeps, one column wider.
    """
    mine = {(r["program"], r["addr"]): r for r in current}
    theirs = {(r["program"], r["addr"]): r for r in committed}
    problems = []
    for key in sorted(set(theirs) - set(mine)):
        problems.append("%s %s is in the sidecar and not in the sample: the "
                        "sidecar is stale -- re-run --report" % key)
    for key in sorted(set(mine) - set(theirs)):
        problems.append("%s %s is in the sample and not in the sidecar: the "
                        "sidecar predates this export" % key)
    compared = 0
    for key in sorted(set(mine) & set(theirs)):
        compared += 1
        for column in BLIND_COLUMNS:
            if theirs[key].get(column) != mine[key].get(column):
                problems.append(
                    "%s %s: %s is %r in the sidecar and %r now -- the export, "
                    "the comparison or the classifier moved, so regenerate it"
                    % (key[0], key[1], column, theirs[key].get(column, ""),
                       mine[key].get(column, "")))
    return compared, problems


def partition_problems(rows, parent):
    """The classification is a partition of the vacuous rows, and nothing else.

    Three things a reader of the sidecar would otherwise take on trust, and all
    three fail rather than being left out: a `vacuous` row carrying no class, a
    class on a row that is not `vacuous`, and a class outside the closed
    vocabulary. The first is the one that matters -- it is the row this tool
    exists to stop being silently dropped from a census -- so it is named.
    """
    vacuous = {(r["program"], r["addr"]) for r in parent
               if r["outcome"] == "vacuous"}
    mine = {(r["program"], r["addr"]): r for r in rows}
    problems = []
    for key in sorted(vacuous - set(mine)):
        problems.append("%s %s is vacuous in %s and has no row in the sidecar"
                        % (key[0], key[1], repo_path(CROSS_DECODER)))
    for key in sorted(set(mine)):
        row = mine[key]
        if key not in vacuous:
            if row["blind"]:
                problems.append("%s %s is %s and carries a `blind` class, but "
                                "only a vacuous row is in scope"
                                % (key[0], key[1], row["outcome"]))
        elif not row["blind"]:
            problems.append("%s %s is vacuous and carries no `blind` class: it "
                            "fell in none of them" % key)
        elif row["blind"] not in BLIND_CLASSES:
            problems.append("%s %s carries %r, which is not in the closed "
                            "vocabulary" % (key[0], key[1], row["blind"]))
    return problems


# The five functions issue #350 named, and what each reads on this tree. Three
# of the issue's five classifications are reproduced and two are not;
# `--self-test` pins all five, and the write-up carries the difference with its
# reason rather than dropping the row the measurement disagreed with.
#
# `bank0 0x9007` and `bank0 0x9006` are adjacent on purpose: the same listing
# boundary, read one address apart, is the whole `entry-is-branch` /
# `no-literal-named` distinction in two lines.
#
# `bank0 0xACB4` is the case worth reading. The issue filed it as the residue,
# on the ground that its C "names neither 0x07C5 nor 0x075E". That is a claim
# about two named addresses; this classifier asks whether the *function* loads
# an address its C names, and `ACB4`'s own 238-byte listing extent loads
# twenty-one and its C names ten of them -- so it reads
# `named-past-first-branch` here.
# Pinned at what it reads. `docs/findings/cross-decoder-blind-population.md`
# says why it moved and what answering the issue's question would take.
KNOWN_ANSWERS = [
    ("bank0", "8FDB", "state_0817_fallthrough", ENTRY_IS_BRANCH),
    ("bank0", "9007", "word_nonzero_check_tail", ENTRY_IS_BRANCH),
    ("bank0", "9C24", "reset_08ad_08bf_and_clear_08e2_bit7",
     NAMED_PAST_FIRST_BRANCH),
    ("bank0", "9006", "read_dptr_byte", NO_LITERAL_NAMED),
    ("bank0", "ACB4", "reset_xdata_flags_and_07d5_to_ff",
     NAMED_PAST_FIRST_BRANCH),
]


def self_test(fw):
    """The known answers, the identities the classes rest on, and the comment
    rule's control. 0 failures exits 0."""
    problems = checks = 0

    def check(label, cond, detail=""):
        nonlocal problems, checks
        checks += 1
        if not cond:
            problems += 1
            print("cross_decoder_blindness.py: FAIL  %s%s"
                  % (label, "  (%s)" % detail if detail else ""), file=sys.stderr)

    parent = read_index(CROSS_DECODER)
    rows = blind_rows(fw)
    by_key = {(r["program"], r["addr"]): r for r in rows}
    listing = {(r["program"], r["addr"]): r for r in read_index(LISTING_INDEX)}

    check("the closed vocabulary is still these four classes, held by name",
          set(BLIND_CLASSES) == {NO_XDATA_NAMED, ENTRY_IS_BRANCH,
                                 NAMED_PAST_FIRST_BRANCH, NO_LITERAL_NAMED}
          and len(BLIND_CLASSES) == 4)

    for program, addr, name, want in KNOWN_ANSWERS:
        row = by_key.get((program, addr))
        check("%s 0x%s %s is %s" % (program, addr, name, want),
              row is not None and row["blind"] == want,
              "no row in the sidecar" if row is None
              else "reads %r, outcome %s" % (row["blind"] or "unclassified",
                                             row["outcome"]))

    # The identity `entry-is-branch` rests on, asserted from the firmware in
    # both directions and with the one alternative reading named.
    vacuous = [r for r in parent if r["outcome"] == "vacuous"]
    zero = [r for r in vacuous if r["insns"] == "0"]
    nonzero = [r for r in vacuous if r["insns"] != "0"]
    check("there are vacuous rows in both window states to compare",
          zero and nonzero, "%d zero, %d non-zero" % (len(zero), len(nonzero)))
    check("every vacuous insns=0 row's entry byte is a flow opcode",
          all(entry_is_branch(fw, r["program"], int(r["addr"], 16)) for r in zero))
    check("no vacuous insns>0 row's entry byte is a flow opcode",
          all(not entry_is_branch(fw, r["program"], int(r["addr"], 16))
              for r in nonzero))
    zero_sized = [r for r in zero
                  if int(listing[(r["program"], r["addr"])]["size"]) == 0]
    check("no vacuous insns=0 row is a zero-size listing, so insns=0 has no "
          "second reading", not zero_sized,
          "%d such row(s): %s" % (len(zero_sized),
                                  [r["addr"] for r in zero_sized][:5]))
    check("every vacuous insns=0 row classifies as entry-is-branch",
          all(by_key[(r["program"], r["addr"])]["blind"] == ENTRY_IS_BRANCH
              for r in zero))

    partition = partition_problems(rows, parent)
    check("the classification is a partition of the vacuous rows and nothing "
          "else", not partition, "; ".join(partition[:3]))
    check("the partition is over a non-empty population", vacuous)

    # The comment rule's control: the census cannot depend on which of the two
    # strippers is used, so the one in the docstring is a choice rather than a
    # reading.
    check("stripping every block comment gives the same four counts",
          census(blind_rows(fw, strip_every_comment)) == census(rows),
          "%s vs %s" % (sorted(census(rows).items()),
                        sorted(census(blind_rows(fw,
                                                 strip_every_comment)).items())))

    # The header comment rule on hand-built text, because a `.c` that gains or
    # loses its annotation later must not move this quietly.
    plain = "void f(void)\n{\n  DAT_EXTMEM_0988 = 1;\n}\n"
    check("a .c with no annotation comment keeps its body",
          names_an_address(strip_header_comment(plain)) == {"0988"})
    warned = ("/* WARNING: Do nothing block with infinite loop */\n"
              "/* a type: line that is not the exporter's field */\n"
              + plain)
    check("a Ghidra WARNING block is not mistaken for the annotation comment",
          names_an_address(strip_header_comment(warned)) == {"0988"})
    annotated = ("/* Names 0x07D0 in prose.\n   type: state\n"
                 "   evidence: ec/decompiled/bank0/9006.c */\n" + plain)
    check("the annotation comment's own addresses do not count as the body's",
          names_an_address(strip_header_comment(annotated)) == {"0988"},
          str(sorted(names_an_address(strip_header_comment(annotated)))))

    # The walk against the committed listing, which is the record the exporter
    # wrote of the same bytes. `bank0 0x9C24` is the one function in the
    # known answers whose class is a window that stopped short rather than an
    # entry that was a branch, so its listing is where the walk has to be seen
    # to reach past the `lcall` on its second instruction.
    listing_9c24 = asm_dptr_operands("bank0", 0x9C24)
    check("bank0 0x9C24's committed listing renders three `mov DPTR, #imm`",
          listing_9c24 == {"0x490", "0x8ad", "0x8bf"}, str(sorted(listing_9c24)))
    check("extent_literals() reads the same three out of the firmware",
          extent_literals(fw, "bank0", 0x9C24,
                          int(listing[("bank0", "9C24")]["size"]))
          == {"0490", "08AD", "08BF"})
    check("the first of them is past the transfer on the second instruction, "
          "which is why the window found nothing",
          [m for m, _ in asm_instructions("bank0", 0x9C24)][:2]
          == ["clr", "lcall"])
    check("bank0 0x8FDB's committed listing opens on a transfer, which is the "
          "entry-is-branch reading of its insns=0",
          asm_instructions("bank0", 0x8FDB)[0][0] == "lcall",
          str(asm_instructions("bank0", 0x8FDB)[:1]))
    check("and 0x06C5 is in that listing, past the branch its entry is",
          "0x6c5" in asm_dptr_operands("bank0", 0x8FDB))
    check("bank0 0x9006's committed listing is one `movx a,@dptr` and loads "
          "no DPTR literal at all, which is the whole of no-literal-named",
          asm_dptr_operands("bank0", 0x9006) == set(),
          str(sorted(asm_dptr_operands("bank0", 0x9006))))

    # The classifier's branch order, on hand-made bytes: `bank0` addresses below
    # COMMON_END map to themselves, so a fixture image this small is readable.
    fixture = bytearray(0x1008)
    fixture[0x1000:0x1004] = bytes([0x90, 0x09, 0x88, 0x22])   # mov dptr,#0988; ret
    fixture[0x1004:0x1006] = bytes([0x22, 0x00])               # ret
    fixture = bytes(fixture)
    names_0988 = "void f(void)\n{\n  DAT_EXTMEM_0988 = 1;\n}\n"
    names_07d0 = "void f(void)\n{\n  DAT_EXTMEM_07d0 = 1;\n}\n"
    silent = "void f(void)\n{\n  bVar1 = 1;\n}\n"
    check("a body that names nothing is no-xdata-named, even though the "
          "extent holds a literal it does not name",
          classify_body(silent, fixture, "bank0", 0x1000, 4) == NO_XDATA_NAMED)
    check("a flow opcode at the entry outranks a body that names nothing",
          classify_body(silent, fixture, "bank0", 0x1004, 2) == ENTRY_IS_BRANCH)
    check("a body naming an address the extent holds is "
          "named-past-first-branch",
          classify_body(names_0988, fixture, "bank0", 0x1000, 4)
          == NAMED_PAST_FIRST_BRANCH)
    check("a body naming an address the extent does not hold is "
          "no-literal-named",
          classify_body(names_07d0, fixture, "bank0", 0x1000, 4) == NO_LITERAL_NAMED)
    check("a flow opcode at the entry is entry-is-branch, ahead of the extent",
          classify_body(names_07d0, fixture, "bank0", 0x1004, 2) == ENTRY_IS_BRANCH)
    check("a row with no exported C is unclassified rather than guessed",
          classify_body(None, fixture, "bank0", 0x1000, 4) == "")
    check("a zero-size listing loads nothing, so it cannot be "
          "named-past-first-branch",
          classify_body(names_0988, fixture, "bank0", 0x1000, 0) == NO_LITERAL_NAMED)

    if problems:
        print("cross_decoder_blindness.py: %d failure(s) of %d check(s)"
              % (problems, checks), file=sys.stderr)
        return 1
    print("cross_decoder_blindness.py --self-test: %d check(s) passed over %d "
          "sampled row(s)\n%s" % (checks, len(rows), census_line(rows)))
    return 0


def render(rows):
    """The sidecar as text: what `--report` writes and what `--check` diffs."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=BLIND_COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


def report(rows, path=BLINDNESS):
    """The sidecar to disk. Its only writer.

    Safe to regenerate from committed inputs alone -- firmware, listings, the
    committed report and the `.c` files -- so refreshing it needs python3 and no
    Ghidra run, and a row cannot be refreshed by copying a value across by hand
    because `--check` recomputes it.
    """
    with open(path, "w", newline="") as f:
        f.write(render(rows))
    return path


def print_census(rows):
    print(census_line(rows))
    for cls in BLIND_CLASSES:
        print("  %-22s %s" % (cls, CLASS_REASONS[cls]))


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--report", action="store_true",
                    help="(re)write the sidecar from the current tree "
                         "(default: %s)" % repo_path(BLINDNESS))
    ap.add_argument("--check", action="store_true",
                    help="re-derive the sidecar and diff it against the "
                         "committed one, exiting non-zero on any difference. A "
                         "missing file fails; it is never created")
    ap.add_argument("--sidecar", metavar="PATH",
                    help="the sidecar --report writes and --check reads, for a "
                         "scratch copy rather than the committed one")
    ap.add_argument("--self-test", action="store_true",
                    help="the five known answers, the insns=0 identity, the "
                         "partition, and the comment rule's control")
    args = ap.parse_args(argv)
    if args.report and args.check:
        ap.error("--check reads the file --report writes; giving both is a "
                 "check that writes the file it is checking")
    sidecar = args.sidecar or BLINDNESS

    fw = open(FIRMWARE, "rb").read()
    if args.self_test:
        return self_test(fw)

    rows = blind_rows(fw)
    # Before anything is written or compared: a row that fell in no class is
    # this tool's own failure, and committing a sidecar that quietly omits one
    # is the shape of error the sidecar exists to remove.
    problems = partition_problems(rows, read_index(CROSS_DECODER))
    if problems:
        for problem in problems:
            print("cross_decoder_blindness.py: %s" % problem, file=sys.stderr)
        print("cross_decoder_blindness.py: %d partition problem(s); nothing "
              "written and nothing compared" % len(problems), file=sys.stderr)
        return 1

    if args.check:
        if not os.path.isfile(sidecar):
            print("cross_decoder_blindness.py: no %s -- run --report first. A "
                  "--check that creates the file it is checking has stopped "
                  "checking it" % repo_path(sidecar), file=sys.stderr)
            return 1
        header = next(csv.reader(open(sidecar, newline="")), None)
        if header != BLIND_COLUMNS:
            problems.append("%s carries the header %r, not this tool's %d "
                            "columns" % (repo_path(sidecar), header,
                                         len(BLIND_COLUMNS)))
        else:
            compared, drifted = blindness_problems(read_index(sidecar), rows)
            problems += drifted
        for problem in problems:
            print("cross_decoder_blindness.py: %s" % problem, file=sys.stderr)
        if problems:
            print("cross_decoder_blindness.py: %d problem(s)" % len(problems),
                  file=sys.stderr)
            return 1
        print("  %d row(s) recomputed, every cell agreeing with %s"
              % (compared, repo_path(sidecar)))
        print_census(rows)
        return 0

    if args.report:
        print("cross_decoder_blindness.py: wrote %s" % repo_path(report(rows, sidecar)))
    print_census(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
