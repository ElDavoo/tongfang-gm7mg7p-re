#!/usr/bin/env python3
"""What `ec/ghidra/reassembly.csv` says about itself, read from its own columns.

**The question.** `verify_reassembly.check_one()` returns two different counts
under one name. `instructions_checked` is the number of instructions `to_sdas()`
translated -- how many were *handed* to the assembler -- and the number of bytes
that actually reached the comparison against the firmware image was not counted
at all. For most rows the two coincide; for the rows this tool is about, they
do not, and the difference is the whole of issue #229.

The row that matters reads `assembler-gap`, `instructions_checked` 12,
`instructions_unchecked` 0, and `detail` `no bytes emitted at 0042`. Every
instruction in it translated, the assembler ran and exited 0, and `read_lst()`'s
parse of the listing it printed carried no entry at the first address the
comparison reached -- so zero of those twelve instructions reached a comparison.
Nothing in the row says the form is inexpressible; that is what `assembler-gap`
means everywhere else.

**The bound, and why it is an upper bound.** Every instruction in the committed
listings is in one of three states: translated and compared, translated and not
compared, or declined by `to_sdas()` before the assembler was asked. This tool
counts the second state per row, from the `detail` cell alone, and subtracts it
from the report's own `instructions_checked` total. What is left is how many
instructions *could* have been compared, which is a ceiling: a row that stopped
part-way through contributes its full `instructions_checked` even though only
some of it was reached, so the true figure is lower and cannot be recovered
from the committed file. The one figure that could have been compared and
provably was not is the one this tool subtracts.

**The anchor, and why it is read rather than assumed.** `check_one()` emits its
`.org` at `insns[0][0]`, the listing's first parsed address, while the report is
keyed on Ghidra's function entry. For most rows those are the same number and
the difference is invisible; for 14 of them they are not, and classifying a
detail on the *row's* address instead of the *anchor's* silently misses the rows
where the two disagree -- `common/6D46` anchors at 0x67EC and stops there, so
`no bytes emitted at 67EC` reads as a row that got nowhere but its own address
says 0x6D46. Both counts are printed. The anchor census is derived from
`ec/decompiled/listing-index.csv` joined against `parse_listing()`, the reader
`check_one()` itself uses, so the two agree about what a listing's first address
is by construction rather than by two readers happening to match.

**What this concludes, and what it does not.** It reads what a row's own cells
say. A `no bytes emitted` detail means `read_lst()`'s parse of the assembler's
listing carried no entry at that address -- it does not mean the assembler
emitted nothing, that it refused the form, or that anything is wrong with the
disassembly. Those are three different questions and none of them is answered
here; `docs/findings/reassembly-checked-counts-comparisons.md` names what would
answer each. Equally, a listing-index address this tool cannot open is *not
found by this method*, and is counted as such rather than as an agreement.

**Why `--check` is not the assertion a reader expects.** The strict form -- fail
when a row claims a checked instruction and compared none -- is a property of
the committed report, and #157's re-report is what replaces it. A gate that is
red on the tree it is landed onto, for a reason no commit to it can fix, is a
gate that gets switched off, which `docs/ci/agent-gates-gap-text-check.patch`
records happening once already. So `--check` fails on what a commit *can* fix:
a cell that does not hold an integer, a detail this tool cannot classify, an
anchor that cannot be read. The overclaim itself is printed, with its rows
named, on every run; `--fail-on-overclaim` makes it fatal for a caller that
wants the strict form and is wired nowhere.

**Every figure here is computed at run time from the committed file.** None of
them is transcribed, and the file has already moved once under a hand-kept
number in this repository (`verify_gap_text.EXPECT_CHECKED`, red for that
reason at #229's base). Quote this tool's output, not a figure copied out of it.

Usage:
    python3 ec/tools/reassembly_checked_bound.py              # the census
    python3 ec/tools/reassembly_checked_bound.py --check      # for the gate
    python3 ec/tools/reassembly_checked_bound.py --self-test  # known answers
"""
import argparse
import csv
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import verify_reassembly as V                                 # noqa: E402

REPO = V.REPO
REPORT = V.REPORT
LISTING_INDEX = V.LISTING_INDEX
DECOMPILED = V.DECOMPILED

# The detail `check_one()` writes from inside its comparison loop, with the
# address it reached. Anchored, so the current report's bare spelling and the
# `(anchored at %04X)` suffix #229's check_one() adds both match, and a future
# report written by this file's own writer does not read as an unclassified
# detail and silently drop out of the census.
NO_ENTRY = re.compile(r"^no bytes emitted at ([0-9A-Fa-f]+)")

# The outcomes whose detail can be a `no bytes emitted` one. Both spellings are
# listed because the committed report predates `listing-gap` (verify_reassembly
# OUTCOMES) and the two files disagree about this row's meaning until #157
# re-reports it; reading only one of them would count half the census.
NO_ENTRY_OUTCOMES = ("assembler-gap", "listing-gap")

# The three classes a row with no entry falls into. `own-anchor` is the only one
# that proves nothing was compared: the detail named the address the `.org` was
# emitted at, so the very first translated instruction is the one with no entry
# and the loop returned before comparing a byte. `stopped-later` says the
# listing had an entry at the anchor and none further on, so something was
# compared and how much is not recoverable. `no-entry` is a detail that is not a
# `no bytes emitted` one at all -- the shape an inexpressible form takes, where
# nothing was translated and so nothing could be compared.
OWN_ANCHOR = "own-anchor"
STOPPED_LATER = "stopped-later"
NO_ENTRY_DETAIL = "no-entry-detail"
UNCLASSIFIED = "unclassified"
CLASSES = (OWN_ANCHOR, STOPPED_LATER, NO_ENTRY_DETAIL, UNCLASSIFIED)


def cell(row, column):
    """A report cell as an int, or None if it does not hold one.

    The same `verify_reassembly.int_cell()` the run comparison uses, wrapped so
    this file's rows can be hand-built in `--self-test` without a second reader
    with a second idea of what a blank cell means.
    """
    return V.int_cell(row, column)


def listing_anchor(out_file):
    """The listing's first parsed address as a 4-digit string, or None.

    None covers all three ways this cannot be answered: no `out_file`, a file
    that is not on disk, and a file `parse_listing()` returns nothing for. The
    first two are *not found by this method* rather than a disagreement, and the
    census below counts them as such.
    """
    if not out_file or out_file.startswith("("):
        return None
    path = os.path.join(DECOMPILED, out_file)
    if not os.path.isfile(path):
        return None
    insns = V.parse_listing(path)
    return "%04X" % insns[0][0] if insns else None


def classify(row, anchor):
    """`row`'s class, and the address its detail named (None when it named none).

    The anchor is passed in rather than read here so `--self-test` can drive the
    same function on rows whose listings do not exist, which is the only way to
    exercise the disagreement case without building 2,717 `.asm` files.
    """
    outcome = (row.get("outcome") or "").strip()
    detail = (row.get("detail") or "").strip()
    match = NO_ENTRY.match(detail)
    if outcome not in NO_ENTRY_OUTCOMES:
        return ("n/a", None)
    if match is None:
        # A `no bytes emitted` prefix this regex did not match is the shape a
        # future writer would produce by re-wording the detail. Guessing at it
        # is how a census quietly loses rows, so it is named instead.
        if detail.startswith("no bytes emitted"):
            return (UNCLASSIFIED, None)
        return (NO_ENTRY_DETAIL, None)
    at = match.group(1).upper()
    if anchor is not None and at == anchor:
        return (OWN_ANCHOR, at)
    return (STOPPED_LATER, at)


def census(rows, anchors):
    """Every figure the tool prints, from `rows` and `anchors`.

    `anchors` is `{(program, addr): anchor_or_None}`, read by `read_anchors()`.
    Returned as one dict so `--check`, the default print and `--self-test` are
    all reading the same arithmetic rather than three readings of it.
    """
    out = {
        "rows": len(rows),
        "checked": 0,
        "unchecked": 0,
        "cells_bad": [],
        "anchors_missing": [],
        "classes": dict.fromkeys(CLASSES, 0),
        "unclassified_rows": [],
        "own_anchor_rows": [],
        "stopped_later_rows": [],
        "anchors_divergent": [],
        "anchor_outcomes": {},
    }
    for row in rows:
        checked = cell(row, "instructions_checked")
        unchecked = cell(row, "instructions_unchecked")
        key = (row.get("program"), row.get("addr"))
        anchor = anchors.get(key)
        if checked is None or unchecked is None:
            out["cells_bad"].append(key)
        else:
            out["checked"] += checked
            out["unchecked"] += unchecked
        if anchor is None:
            out["anchors_missing"].append(key)
        if anchor is not None and anchor.upper() != (row.get("addr") or "").upper():
            out["anchors_divergent"].append(key)
            out["anchor_outcomes"][row.get("outcome")] = \
                out["anchor_outcomes"].get(row.get("outcome"), 0) + 1
        klass, at = classify(row, anchor)
        if klass == "n/a":
            continue
        out["classes"][klass] += 1
        if klass == OWN_ANCHOR:
            out["own_anchor_rows"].append(key)
        elif klass == STOPPED_LATER:
            out["stopped_later_rows"].append((key, at))
        elif klass == UNCLASSIFIED:
            out["unclassified_rows"].append((key, row.get("detail")))
    # The bound: everything the report calls checked, less the instructions in
    # the rows that provably compared nothing. `checked` here is the report's
    # own total, so a cell that did not parse contributes nothing and the
    # `cells_bad` list above is what says so rather than the number quietly
    # being lower than it looks. The key set is built once rather than per row.
    own = set(out["own_anchor_rows"])
    out["own_anchor_instructions"] = sum(
        cell(row, "instructions_checked") or 0
        for row in rows if (row.get("program"), row.get("addr")) in own)
    out["bound"] = out["checked"] - out["own_anchor_instructions"]
    out["total"] = out["checked"] + out["unchecked"]
    return out


def read_report(path=REPORT):
    """The committed report's rows, read with its own DictReader."""
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def read_anchors(index=LISTING_INDEX):
    """`{(program, addr): first-address-or-None}` over the listing index.

    Every row, not only the ones the report carries, because a report row whose
    index row is missing is itself something a reader needs named and a census
    that silently skipped it would report the wrong denominator.
    """
    anchors = {}
    with open(index, newline="") as f:
        for row in csv.DictReader(f):
            rel = row.get("out_file")
            if not rel or rel.startswith("("):
                continue
            anchors[(row.get("program"), row.get("addr"))] = listing_anchor(rel)
    return anchors


def report_lines(out):
    """The census as lines, so the default print and `--check` say one thing."""
    return [
        "  reassembly report: %d row(s), %d instruction(s) checked, "
        "%d unchecked, %d in all"
        % (out["rows"], out["checked"], out["unchecked"], out["total"]),
        "  rows whose detail says the listing parse had no entry:",
        "    at the row's own anchor, so nothing compared : %d row(s), "
        "%d instruction(s)"
        % (out["classes"][OWN_ANCHOR], out["own_anchor_instructions"]),
        "    further on, so an unknown part compared       : %d row(s)"
        % out["classes"][STOPPED_LATER],
        "    a detail that is not a `no bytes emitted` one: %d row(s)"
        % out["classes"][NO_ENTRY_DETAIL],
        "  ceiling: at most %d of the %d instructions reached a comparison."
        % (out["bound"], out["total"]),
        "  That is a ceiling and not a figure. The %d instruction(s) in the "
        "first group above\n  are the only ones this file proves did not; the "
        "second group's rows stopped part-way\n  through, so the real count is "
        "lower and the committed file does not say by how much."
        % out["own_anchor_instructions"],
        "  anchors (the `.org` address) that are not the row's own address: "
        "%d row(s) -- %s"
        % (len(out["anchors_divergent"]),
           ", ".join("%d %s" % (n, o) for o, n in sorted(out["anchor_outcomes"].items()))
           or "none"),
    ]


def check(args):
    """Fail on what a commit can fix. Say the rest.

    Returns an exit status, and prints the census either way: a reader who lands
    this in the gate needs to see the overclaim on the run that says the wiring
    is sound, not only on the one that says it is not.
    """
    out = census(read_report(), read_anchors())
    for line in report_lines(out):
        print(line)
    ok = True
    for key in out["cells_bad"]:
        print("  FAIL %s %s: instructions_checked or instructions_unchecked "
              "does not hold an integer, so this row is in no total above"
              % key)
        ok = False
    for key, detail in out["unclassified_rows"]:
        print("  FAIL %s %s: %r starts like a `no bytes emitted` detail and "
              "nothing here classifies it. Teach classify() the new spelling "
              "rather than letting the row leave the census."
              % (key[0], key[1], detail))
        ok = False
    for key, at in out["stopped_later_rows"]:
        print("  --   %s %s: no entry at %s, above its anchor, so an unknown "
              "part of its instruction count was compared and the ceiling "
              "counts all of it." % (key[0], key[1], at))
    for key in out["anchors_missing"]:
        print("  --   %s %s: no listing to read an anchor from. Not found by "
              "this method -- not an agreement, and not a disagreement."
              % key)
    if args.fail_on_overclaim and out["own_anchor_rows"]:
        for key in out["own_anchor_rows"]:
            print("  FAIL %s %s reports a checked instruction and compared "
                  "none." % key)
        ok = False
    print("  all checks passed" if ok else "  FAILURES ABOVE")
    return 0 if ok else 1


def self_test():
    """The arithmetic, on rows whose listings do not exist.

    Hand-built throughout: an oracle derived from the committed CSV would assert
    that the committed CSV agrees with itself, which is the thing
    `verify_gap_text.self_test()` and `verify_reassembly.self_test()` both say
    they refuse to do.
    """
    ok = True

    def assert_that(cond, what):
        nonlocal ok
        print("  %s %s" % ("ok  " if cond else "FAIL", what))
        ok = ok and bool(cond)

    def row(prog, addr, outcome, checked, unchecked, detail):
        return {"program": prog, "addr": addr, "outcome": outcome,
                "instructions_checked": str(checked),
                "instructions_unchecked": str(unchecked), "detail": detail}

    assert_that(NO_ENTRY.match("no bytes emitted at 0042").group(1) == "0042",
                "the detail's address is read off the committed spelling")
    assert_that(NO_ENTRY.match("no bytes emitted at 0042 (anchored at 0040)")
                .group(1) == "0042",
                "and off the spelling check_one() writes now, so a re-reported "
                "file does not leave the census")
    assert_that(NO_ENTRY.match("1 of 13 instruction(s) unchecked, first: mov "
                               "0x57, CY") is None,
                "a `partial` detail is not read as a no-entry one")
    assert_that(NO_ENTRY.match("ajmp 0x845d") is None,
                "nor is an inexpressible form's")

    # The two calls of `assembler-gap`, one per meaning. This is the split the
    # whole tool exists to make visible, so it is made visible by value rather
    # than by a comment saying it happens.
    assert_that(classify(row("bank0", "8044", "assembler-gap", 0, 1,
                              "ajmp 0x845d"), "8044") == (NO_ENTRY_DETAIL, None),
                "a declined form is `no-entry-detail`: nothing was translated, "
                "so nothing could be compared")
    assert_that(classify(row("bank0", "0040", "assembler-gap", 12, 0,
                              "no bytes emitted at 0040"), "0040")
                == (OWN_ANCHOR, "0040"),
                "a detail naming the anchor is `own-anchor`: the first "
                "translated instruction is the one with no entry")
    assert_that(classify(row("bank1", "D946", "assembler-gap", 176, 0,
                              "no bytes emitted at DA6E"), "D946")
                == (STOPPED_LATER, "DA6E"),
                "a detail naming a later address is `stopped-later`: something "
                "was compared and the ceiling cannot say how much")
    # The anchor case that makes the difference. Classified on the row's own
    # address this reads as `stopped-later`, which is right about the address
    # and wrong about the zero.
    assert_that(classify(row("common", "6D46", "assembler-gap", 77, 6,
                              "no bytes emitted at 67EC"), "67EC")
                == (OWN_ANCHOR, "67EC"),
                "a detail naming the *anchor* rather than the row's address is "
                "still `own-anchor` -- common/6D46 is the row that makes this "
                "one, and it anchors 0x55A below itself")
    assert_that(classify(row("common", "6D46", "assembler-gap", 77, 6,
                              "no bytes emitted at 67EC"), None)
                == (STOPPED_LATER, "67EC"),
                "and with no anchor readable it is `stopped-later`, which is "
                "the honest answer when the anchor is *not found by this "
                "method*")
    assert_that(classify(row("bank0", "0040", "listing-gap", 12, 0,
                              "no bytes emitted at 0040 (anchored at 0040)"),
                         "0040") == (OWN_ANCHOR, "0040"),
                "the current vocabulary's spelling classifies the same way, so "
                "the census does not depend on which report is committed")
    assert_that(classify(row("bank0", "0040", "match", 9, 0, ""), "0040")
                == ("n/a", None),
                "a row that is not a no-entry outcome is not classified")

    # A detail that starts like one and is not parseable is named, not dropped.
    assert_that(classify(row("bank0", "0040", "assembler-gap", 1, 0,
                              "no bytes emitted at wherever"), "0040")
                == (UNCLASSIFIED, None),
                "a `no bytes emitted` detail with no address is `unclassified`, "
                "so --check fails rather than losing the row")
    assert_that(classify(row("bank0", "0040", "assembler-gap", 1, 0,
                              "no bytes at 0040"), "0040") == (NO_ENTRY_DETAIL, None),
                "but a re-worded detail that is not this one is not guessed at")

    # The bound, on rows with a known answer.
    rows = [row("bank0", "0040", "match", 10, 0, ""),
            row("bank0", "0042", "match", 5, 0, ""),
            row("bank0", "0044", "partial", 3, 2, "2 of 5 unchecked"),
            row("bank0", "0046", "assembler-gap", 0, 1, "ajmp 0x9000"),
            row("bank0", "0048", "assembler-gap", 12, 0,
                "no bytes emitted at 0048"),
            row("bank0", "004A", "assembler-gap", 4, 1,
                "no bytes emitted at 004B")]
    anchors = {("bank0", a): a for a in ("0040", "0042", "0044", "0046",
                                         "0048", "004A")}
    out = census(rows, anchors)
    assert_that(out["classes"][OWN_ANCHOR] == 1
                and out["classes"][STOPPED_LATER] == 1
                and out["classes"][NO_ENTRY_DETAIL] == 1,
                "one row in each class, and the three add up to the four "
                "no-entry rows")
    assert_that(out["own_anchor_instructions"] == 12 and out["checked"] == 34
                and out["total"] == 38,
                "12 instructions in the own-anchor row, 34 checked in all "
                "(%d), 38 instructions in all (%d)"
                % (out["checked"], out["total"]))
    assert_that(out["bound"] == 22,
                "the bound is 34 less the 12 that provably compared nothing "
                "(%d)" % out["bound"])
    assert_that(out["bound"] > 0 and out["bound"] < out["total"],
                "and it is below the total, which is what makes it a bound "
                "rather than the figure")

    # A cell that does not parse is named and left out, not read as zero.
    broken = [row("bank0", "0040", "match", 10, 0, ""),
              dict(row("bank0", "0042", "match", 5, 0, ""),
                   instructions_checked="five")]
    out = census(broken, {("bank0", "0040"): "0040", ("bank0", "0042"): "0042"})
    assert_that(out["cells_bad"] == [("bank0", "0042")]
                and out["checked"] == 10,
                "a cell that does not hold an integer is reported by key and "
                "counted for nothing, rather than read as 0")

    # The anchor census, including a row whose listing cannot be read.
    anchored = [row("bank0", "0040", "match", 9, 0, ""),
                row("common", "6D46", "assembler-gap", 77, 6,
                    "no bytes emitted at 67EC")]
    out = census(anchored, {("bank0", "0040"): "0040", ("common", "6D46"): "67EC"})
    assert_that(len(out["anchors_divergent"]) == 1
                and out["anchors_divergent"][0] == ("common", "6D46")
                and out["anchor_outcomes"] == {"assembler-gap": 1},
                "a row anchored below itself is counted, with its outcome "
                "(%d)" % len(out["anchors_divergent"]))
    out = census(anchored, {("bank0", "0040"): "0040"})
    assert_that(out["anchors_missing"] == [("common", "6D46")]
                and out["classes"][STOPPED_LATER] == 1,
                "a row with no readable anchor is named as not found by this "
                "method, and falls back to the weaker class")

    # The committed file, through the reader the run comparison uses.
    committed = read_report()
    assert_that(committed and committed[0].get("listing_digest") is not None,
                "the committed report reads with its own column names, so the "
                "tool sees the file rather than a transcription of it")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="fail on a cell or a detail this tool cannot read")
    ap.add_argument("--fail-on-overclaim", action="store_true",
                    help="also fail when a row reports a checked instruction "
                         "and compared none; the strict form, wired nowhere")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    if args.check:
        return check(args)
    for line in report_lines(census(read_report(), read_anchors())):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)