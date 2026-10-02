#!/usr/bin/env python3
"""The BL51 bank-select trampolines, recognised by listing shape.

`ec/annotations/subsystems.md` §4 measures the population by shape: a function
whose whole body is `mov DPTR,#imm16` followed by `ljmp <a BL51 stub>`. Those
are the firmware's bank-select trampolines -- the address is loaded into DPTR
and handed to a stub that switches bank and jumps to it -- and the shape is the
whole of the rule, because the annotations that name them read the same two
instructions.

**Why the shape is pinned to the stub set, and what that costs.** `mov
DPTR,#imm16` followed by `ljmp <anything>` matches more annotated rows than
`ljmp <a BL51 stub>` does, and the gap is not noise: a function that loads
DPTR and jumps somewhere that is not a bank-select stub is doing something
else with the address, and treating its jump as a bank boundary would cut an
edge for a reason the rule does not name. So `is_trampoline()` takes the stub
set as an argument rather than hard-coding four addresses, and the set is
derived from `ghidra-functions.csv` so it cannot drift away from the file that
names them. `run()` prints both populations side by side, which is the number
that makes the gap visible if the pin is ever loosened.

**The stub names need the whole-name match, and the wrapper row is why.** The
stub rows are `bl51_bank_select_0` .. `bl51_bank_select_3`, but
`ghidra-functions.csv` also carries `bl51_bank_select_0_tail_110a_wrapper` at
`common` `0x1048`, which shares the prefix and is a wrapper *around* a stub
rather than a stub. A substring or prefix match sweeps it in and silently makes
the stub set five. `STUB_COUNT` is the assertion that catches that class of
mistake at the point it happens rather than in the next census figure.

**What a zero here means.** Everything above is read out of committed `.asm`
listings and one committed CSV. Nothing was executed, no bank was switched, and
no register was read: the stub's own behaviour is the open question, and
`subsystems.md` §12 note 4 carries the same-bank caveat forward untouched --
naming which bank a trampoline reaches is *not* established by any of this, and
this tool does not attempt it.

Usage:
    python3 ec/tools/bl51_trampolines.py
"""
import argparse
import collections
import csv
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)

ANNOTATIONS = os.path.join(REPO, "ec", "annotations", "ghidra-functions.csv")
GROUPS = os.path.join(REPO, "ec", "annotations", "function-groups.csv")
INDEX = os.path.join(REPO, "ec", "decompiled", "index.csv")

# `<addr> <bytes> <mnemonic> <operands>`, the shape the export writes. Read out
# of the committed listings rather than reconstructed: `build_ec_decompile.py`
# is what decides this format, and a second spelling of it here would be a
# second thing to keep in step with it.
LISTING = re.compile(r"^\s*([0-9A-Fa-f]{4,8})\s+"
                     r"((?:[0-9a-f]{2}|-)(?:\s+(?:[0-9a-f]{2}|-)){1,5})\s+"
                     r"(\S+)\s*(.*?)\s*$")

# The stub names, whole. See the module docstring for the wrapper row that
# makes a prefix match wrong: `bl51_bank_select_0_tail_110a_wrapper` is not a
# stub, and `STUB_COUNT` is what notices if this ever matches it.
STUB_NAME = re.compile(r"^bl51_bank_select_[0-9]+$")

# `subsystems.md` §4 names four BL51 stubs, all `type: gate`, at 0x1100,
# 0x1114, 0x1128 and 0x113C. This asserts the rule still resolves to that
# many rather than sweeping the set wider, and it is deliberately a count: the
# question it answers is "did the name pattern stop meaning the stubs", which
# is not answerable from any one row.
STUB_COUNT = 4


def read_csv(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f, strict=True))


def norm_addr(addr):
    return (addr or "").upper().replace("0X", "")


def read_listing(path):
    """The instructions in a committed `.asm`, as `(addr, mnemonic, operands)`.

    Comments and blank lines are dropped and the mnemonic is lower-cased, so
    the callers compare against forms rather than against the export's
    capitalisation. A path that is not a listing on disk reads as no
    instructions rather than raising: an annotation row whose evidence does not
    resolve is a gap in the annotations, not a malformed export, and the shape
    rule has nothing to say about it either way.
    """
    out = []
    if not path or not os.path.isfile(path):
        return out
    with open(path, errors="replace") as text:
        for line in text:
            if line.lstrip().startswith(";") or not line.strip():
                continue
            m = LISTING.match(line)
            if m:
                out.append((int(m.group(1), 16), m.group(3).lower(), m.group(4)))
    return out


def stub_addresses(rows):
    """The BL51 stub addresses, from the annotation rows that name them.

    `rows` is an annotation CSV, taken as an argument so that the caller already
    has it -- this reads no file, and the `--report` census and
    `trampoline_listings()` pass the same rows so the set cannot be two
    different answers to one question.

    **The assertion is "all four or none", and none is a real case rather than
    an escape.** `group_functions.cluster()` runs this over the BIOS rows as
    well as the EC's, and the BIOS has no BL51 stubs because it is not this
    firmware; the split mode is inert there and measured so, rather than
    assumed. What must never happen is a PARTIAL set -- one, two or three stubs,
    or five with the wrapper row swept in -- because that is the pattern having
    stopped meaning the stubs, and every shape answer downstream of it would
    still be produced quietly.
    """
    stubs = {norm_addr(row["addr"]) for row in rows
             if STUB_NAME.match(row.get("name") or "")}
    if stubs and len(stubs) != STUB_COUNT:
        raise AssertionError(
            "the BL51 stub name pattern resolved to %d address(es) (%s), and %s "
            "names %d; `subsystems.md` §4 is where those are enumerated, and "
            "the shape rule below is pinned to this set. A set of zero is the "
            "other component's rows and is left alone."
            % (len(stubs), ", ".join(sorted(stubs)),
               os.path.relpath(ANNOTATIONS, REPO), STUB_COUNT))
    return stubs


def is_trampoline(listing_path, stubs):
    """The stub address this listing tail-jumps to, or None.

    The rule is the body, not the name and not the `type` column: exactly two
    instructions, `mov DPTR,#imm16` first and an `ljmp` second, and the jump
    lands on a BL51 stub. `subsystems.md` §4 states it that way ("a function
    whose whole body is `mov DPTR,#imm16` followed by `ljmp <stub>`"), and the
    whole-body half is what makes the rule a shape rather than a prefix search.

    `stubs` is a parameter rather than a module constant so that the gap this
    function creates is measurable: `stubs=None` asks the unpinned question --
    the shape with any `ljmp` target, which is §4's "290 across the export" --
    and the difference between the two answers is what the pin is worth.
    `run()` prints both, and `test_trampoline_split.py` pins the difference on
    fixtures rather than on the tree.
    """
    ins = read_listing(listing_path)
    if len(ins) != 2:
        return None
    (_a, first, first_operands), (_b, second, second_operands) = ins
    if first != "mov" or not first_operands.upper().replace(" ", "").startswith(
            "DPTR,#"):
        return None
    if second != "ljmp":
        return None
    m = re.search(r"0x([0-9a-fA-F]{4})", second_operands)
    if not m:
        return None
    target = m.group(1).upper()
    return target if stubs is None or target in stubs else None


def asm_path(row, repo=REPO):
    """The row's committed `.asm`, the `.asm` first per the evidence
    convention (the machine code is ground truth, the `.c` is a reading)."""
    for path in (row.get("evidence") or "").split(";"):
        path = path.strip()
        if path.endswith(".asm"):
            full = os.path.join(repo, path)
            if os.path.isfile(full):
                return full
    return None


def trampoline_listings(rows, repo=REPO):
    """`{(scope, addr): the row's .asm}` for every shape-matched trampoline.

    The keying is by `(scope, addr)` rather than by path because that is what
    `group_functions.cluster()` walks -- it is holding one row at a time and
    has already resolved that row's listing. Nothing is returned for a row
    whose evidence resolves to no `.asm`: an unlisted row is *not found by this
    method*, which is the same wording `group_functions.py` uses and the same
    reason.

    This is a second read of the same committed files the caller's own edge
    walk does, and it is worth naming: the shape rule needs the whole body,
    which the edge walk discards, so there is no single parse that serves both.
    Both reads are of the same file on disk and neither transforms it, so they
    cannot disagree about the bytes -- what they can disagree about is *which
    question* they answer, and that is what the return value separates.
    """
    stubs = stub_addresses(rows)
    out = {}
    for row in rows:
        path = asm_path(row, repo)
        if path and is_trampoline(path, stubs):
            out[(row["scope"], norm_addr(row["addr"]))] = path
    return out


def run(repo=REPO, annotations=ANNOTATIONS, groups=GROUPS, index=INDEX):
    """The census, printed. The command that reproduces `subsystems.md` §4's
    shape figures and the annotated-by-stub count."""
    rows = read_csv(annotations)
    stubs = stub_addresses(rows)
    print("BL51 stubs named by %s: %d (%s)"
          % (os.path.relpath(annotations, repo), len(stubs),
             ", ".join("0x%s" % s for s in sorted(stubs))))

    # The export-wide population, over `index.csv` rather than over the
    # annotation CSV: §4's figure is a count of the whole export, and reading it
    # off the annotations would quietly redefine it as a count of what has been
    # named so far. `is_trampoline(path, None)` rather than a second copy of
    # the shape test -- the census and the cut must be the same rule, or the
    # number the census prints is not the number the cut removes -- and one call
    # rather than two, since the unpinned answer already carries the target the
    # pinned test would look up.
    shape_total = naming_total = 0
    by_stub = collections.Counter()
    export_rows = read_csv(index)
    for row in export_rows:
        path = os.path.join(repo, "ec", "decompiled", row["program"],
                            row["addr"] + ".asm")
        target = is_trampoline(path, None)
        if target is None:
            continue
        shape_total += 1
        if target in stubs:
            naming_total += 1
            by_stub[target] += 1
    print("across the export: %d listing(s) of that shape, %d of them naming a "
          "stub (%s), and %d naming something else"
          % (shape_total, naming_total,
             ", ".join("0x%s=%d" % (s, by_stub[s]) for s in sorted(by_stub)),
             shape_total - naming_total))

    # The annotated half, and the gap the pin creates. `elsewhere` is the count
    # of listings the SHAPE rule accepts and the stub set rejects -- what the
    # pin is worth here -- and it is the number to watch: it growing with the
    # pinned count means the two are diverging and the pin is doing more work
    # than the docstring above says it does.
    pinned = elsewhere = 0
    ann_by_stub = collections.Counter()
    for row in rows:
        path = asm_path(row, repo)
        if not path:
            continue
        target = is_trampoline(path, None)
        if target is None:
            continue
        if target in stubs:
            pinned += 1
            ann_by_stub[target] += 1
        else:
            elsewhere += 1
    print("annotated: %d of that shape, %d naming a stub (%s), and %d naming "
          "something else -- the pin is worth %d row(s)"
          % (pinned + elsewhere, pinned,
             ", ".join("0x%s=%d" % (s, ann_by_stub[s])
                       for s in sorted(ann_by_stub)),
             elsewhere, elsewhere))

    # Where the annotated trampolines already sit, because that is what a cut
    # at this boundary would move: a seeded row is labelled by something else
    # already, and a seed does not remove its edges, so only the rows carrying
    # `callgraph` are in the graph a split would reshape.
    landed = collections.Counter()
    if os.path.isfile(groups):
        by_key = {(row["scope"].strip(), norm_addr(row["addr"])):
                  (row.get("group") or "").strip()
                  for row in read_csv(groups)}
        for scope, addr in trampoline_listings(rows, repo):
            landed[by_key.get((scope, addr), "(no group row)")] += 1
        print("where the %d annotated trampoline(s) are grouped today: %s"
              % (sum(landed.values()),
                 ", ".join("%s=%d" % (g, n) for g, n in landed.most_common())))

    # What each trampoline's DPTR immediate names, which is the argument the
    # drop is chosen over a contraction. A contraction would rewrite the tail
    # jump to point at that immediate instead of at the stub, so the address
    # becomes an edge target -- and where the immediate carries a row in the
    # OTHER bank, that edge is the bucket-B ambiguity `group_functions.py`
    # exists to refuse, on a function whose whole purpose is to reach the other
    # image. Printed because it is the population the choice rests on, and a
    # choice whose justification is a figure nothing prints is a figure
    # nobody re-checks.
    scopes_at = collections.defaultdict(set)
    for row in rows:
        scopes_at[norm_addr(row["addr"])].add(row["scope"])
    other_bank = {"bank0": "bank1", "bank1": "bank0"}
    cross_bank = 0
    landing = collections.Counter()
    for row in rows:
        path = asm_path(row, repo)
        if not path or not is_trampoline(path, stubs):
            continue
        ins = read_listing(path)
        m = re.search(r"#0x([0-9a-fA-F]{4})", ins[0][2]) if ins else None
        if not m:
            continue
        imm = m.group(1).upper()
        landing["in another bank" if other_bank.get(row["scope"])
                in scopes_at.get(imm, ())
                else "in this bank" if row["scope"] in scopes_at.get(imm, ())
                else "on no annotated row"] += 1
        if other_bank.get(row["scope"]) in scopes_at.get(imm, ()):
            cross_bank += 1
    print("the DPTR immediate of each annotated trampoline carries a row %s; "
          "%d of them name an address the OTHER bank also has, which is the "
          "population a contraction would walk into"
          % (", ".join("%s %d" % (k, landing[k]) for k in sorted(landing)),
             cross_bank))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__.split("\n")[1],
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--report", action="store_true",
                    help="accepted for symmetry with the other census tools; "
                         "the census is what this tool runs")
    ap.parse_args(argv)
    return run()


if __name__ == "__main__":
    sys.exit(main())