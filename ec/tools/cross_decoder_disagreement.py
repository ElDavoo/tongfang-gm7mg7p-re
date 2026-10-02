#!/usr/bin/env python3
"""What the cross-decoder's `disagree` bucket is made of (issue #510).

`build_ec_decompile.py` records `ec/ghidra/cross-decoder.csv` and ratchets on
it, and its `disagree` bucket is one answer over several situations: a row goes
there when the linear walk's opening finds a `mov dptr,#imm` address the
exported `.c` does not name, and the reason the C does not name it is not one
thing. `CROSS_DECODER_OUTCOMES`'s own comment says the bucket is undivided on
purpose -- splitting it needs the byte-pair-folding case enumerated rather than
described -- and this is the answer to that from the other end. It does not
enumerate the folds. It says, per row, **where the address went**, which is a
fact about the text in both cases, and commits that as a `cause` column in a
sidecar over the same `(program, addr)` keys.

It is a mirror of `cross_decoder_blindness.py`, which did the same for
`vacuous`, and the mirroring is deliberate rather than decorative: the two are
the two halves of one report, so a reader who has learned to read one can read
the other, and a change to how the comparison reads a `.c` has to be argued
about once rather than twice.

**The five causes, and the order they are decided in.** `named-by-register-symbol`
is asked first because it is the closest neighbour of the two spellings the
comparison already accepted: the export names the address, in full, with a name
this repository put there itself, and the name simply does not carry its
address the way `DAT_EXTMEM_07d6` and `XDATA_1664` do. A row in it is a
vocabulary gap and a candidate to be widened; a row in any other is not.

  named-by-register-symbol  Every address the window found and the body does
                            not name is named in the body by an identifier
                            `ec/ghidra/xdata-symbols.csv` maps to that address.
                            A register's real name carries no address, so
                            `_EXTMEM` cannot see it by construction --
                            `bank0 0x8F09`'s body is one statement,
                            `MAIN_FAN_R_DUTY = *param_1;`, and 0x075C is in
                            it.
  named-by-code-symbol      The same, under the export's other address-space
                            spelling: the window's `mov dptr,#imm` named a
                            *code* address -- a table base (`&DAT_CODE_6f39`) or
                            a function entry (`FUN_CODE_08ce`) -- and the export
                            renders it in its own code space. It is not an
                            XDATA address at all, so no XDATA vocabulary could
                            have matched it, and calling that a disagreement is
                            the comparison measuring the wrong address space.
  named-by-decimal-literal  The address is spelled as a decimal literal of that
                            value, which is what a signed helper argument
                            renders as: `bl51_bank_select_0(49000)` is 0xBF68,
                            and `read_xdata_pair_to_r1r2(900)` is 0x0384. This
                            is the shape §14i's bank-switch-trampoline
                            paragraph describes, and it is the class most
                            exposed to a coincidental match, which is why the
                            rule excludes a digit that follows `'`, a
                            backslash, a letter, a dot or another digit.
  names-other-addresses     The body names addresses -- its vocabulary is
                            non-empty -- and none of them is one the window
                            found. The two decoders read different bytes, or
                            one of them folded an address away, and this is
                            the honest remainder.
  names-nothing             The body names no address at all, in the
                            comparison's own vocabulary. `common 0x4BB0` and
                            `common 0x4FED` decompile to `do {} while (true);`
                            and `pd 0x357E` to `return *param_1;`, and there
                            is no address in either body to be in or out of.

**And no sixth cause, which is a decision rather than an omission.** The issue
asked for the rows that stay `disagree` to be kept "and say why", and the five
causes above are the whole of the why that can be written down. Splitting
`names-other-addresses` further -- the body is an empty loop, the pointer
arrives from the caller, the immediate became an argument to an annotated
callee, the C names the neighbouring byte -- means reading each `.c` and
deciding what its render *means*. That is the guess `CROSS_DECODER_OUTCOMES`
refuses when it leaves `disagree` a single bucket, and the one
`cross_decoder_blindness.py` refuses when it leaves `no-literal-named`
undivided: *guessing which of a function's C reads is a fold would manufacture
the very distinction the comparison is meant to measure.* The class states what
is true of every row in it, and the finer split is named in
`../../docs/findings/cross-decoder-disagreement-population.md` as the thing a
future method has to earn.

**No outcome is added, and the same reasoning holds.** `outcome` answers "did
the two decoders agree"; *why this row is what it is* is metadata about the
row. `CROSS_DECODER_OUTCOMES` stays at four, so `denominator_line()` and
`degenerate_sample_problems()` keep meaning exactly what they mean, and the
parent's own column set is untouched.

**`missing` is recomputed here, not read out of the report.** The sidecar
re-runs the comparison's own `compare_function()` for the rows in scope, so a
row cannot be classified against a stale `missing` cell and then blessed by the
parent's `--check` recomputing the same thing differently. `self_test()`
asserts the recomputation against the committed column, both directions, which
is what makes the classes a derivation rather than a transcription.

**And the header comment is stripped before any of it**, by the parent's own
`strip_header_comment`, which is a parameter here exactly as it is in the
parent and in `cross_decoder_blindness.py`. Without it every one of the
causes above would be satisfied by an annotation's prose: `pd/F4CD.c` opens
"/* With DPTR loaded from 0x07D6 ... */", and 118 of the 127 rows this tool
reads name their address nowhere but there — the other 9 disagree either way.
`--self-test` asserts the census is identical when *every* comment is removed
instead, so the rule is a held fact and not a reading.

**Nothing here is measured on hardware.** Every cause is a property of
committed bytes, committed listings and a committed decompile. A register
missing from a decompile says nothing about whether the EC acts on it:
`ec/annotations/registers.yaml` is read here for a name, and is not modified.

Usage:
    python3 cross_decoder_disagreement.py
    python3 cross_decoder_disagreement.py --report
    python3 cross_decoder_disagreement.py --check
    python3 cross_decoder_disagreement.py --self-test
"""
import argparse
import csv
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# The comparison's own matcher, its own offset map's inputs and its own comment
# rules, not copies of them. This tool asks a second question about the same
# bytes that `compare_function()` does, so a second spelling of "names an
# address" or a second comment-stripping rule would be two more things to keep
# in step with the first.
from build_ec_decompile import (CROSS_DECODER, LISTING_INDEX, OUTDIR, REPO,
                                compare_function, names_an_address, read_index,
                                strip_every_comment, strip_header_comment)

DISAGREEMENT = os.path.join(REPO, "ec", "ghidra", "cross-decoder-disagreement.csv")
XDATA = os.path.join(REPO, "ec", "ghidra", "xdata-symbols.csv")

# The sidecar's columns. `program`/`addr` are the key the parent's `--check`
# joins on, `outcome` is carried so a reader can see why a row is blank without
# opening the parent, and `name` so a red `--check` line names a function rather
# than a bare address. `missing` is deliberately *not* carried: it is recomputed
# by `classify_row()`, so a copy of it beside the class would be a second answer
# to the same question -- the same reason `cross_decoder_blindness.py` leaves
# `insns` out.
CAUSE_COLUMNS = ["program", "addr", "name", "outcome", "cause"]

# What a `cause` cell may say, in the order they are decided. A controlled
# vocabulary, for the reason `CROSS_DECODER_OUTCOMES` is one: a second reading
# of `disagree` smuggled in as a synonym would keep the counts right and let
# `--check` go green on a distinction nobody agreed to. Held by name in
# `self_test()` and in the suite, never by length.
NAMED_BY_REGISTER_SYMBOL = "named-by-register-symbol"
NAMED_BY_CODE_SYMBOL = "named-by-code-symbol"
NAMED_BY_DECIMAL_LITERAL = "named-by-decimal-literal"
NAMES_OTHER_ADDRESSES = "names-other-addresses"
NAMES_NOTHING = "names-nothing"
CAUSES = (NAMED_BY_REGISTER_SYMBOL, NAMED_BY_CODE_SYMBOL,
          NAMED_BY_DECIMAL_LITERAL, NAMES_OTHER_ADDRESSES, NAMES_NOTHING)

# What each cause means, in a reader's terms, printed under the counts on every
# run. A bucket name a reader has to look up is a bucket name nobody reads.
CAUSE_REASONS = {
    NAMED_BY_REGISTER_SYMBOL:
        "the C names the address with a register's real name, which carries no "
        "address in its spelling -- a vocabulary gap, and the same shape issue "
        "#255 fixed one step nearer",
    NAMED_BY_CODE_SYMBOL:
        "the window's DPTR immediate named a code address rather than an XDATA "
        "one -- a table base or a function entry -- and the export spells it in "
        "its own code space, so no XDATA vocabulary could have matched it",
    NAMED_BY_DECIMAL_LITERAL:
        "the C spells the address as a decimal literal of that value, which is "
        "what a signed helper argument renders as",
    NAMES_OTHER_ADDRESSES:
        "the C names addresses and none of them is one the window found: the "
        "two decoders read different bytes, or one of them folded an address "
        "away",
    NAMES_NOTHING:
        "the C names no address at all in the comparison's own vocabulary, so "
        "there is no address in the body to be in or out of",
}

# A decimal literal. The lookbehind refuses a digit that opens a hex literal
# (`0x3f8` -> `3f8`), that follows a letter, an underscore, a dot or another
# digit (`BAT_VOLTAGE_MV_0`, `bVar0`, `1.0`), or that is a character constant
# (`'\0'` is a character and not the address 0x0000, which is why the backslash
# of the escape is in the class too). The lookahead is the same list, so a
# five-digit decimal is not truncated into the 16-bit space.
_DECIMAL = re.compile(r"(?<![0-9A-Za-z_.'\"\\])(\d+)(?![0-9A-Za-z_.])")
# The export's code-space spellings: `DAT_CODE_6f39` for a table base and
# `FUN_CODE_08ce` for a function entry, which is what the same address is
# called when the export has decided it is code rather than data. Anchored on
# the address space it names and not on the C's own vocabulary, because the
# point of the class is that this address is not in that vocabulary. `\b` before
# the prefix, so `FUN_CODE_` is matched as the code-space prefix and not as an
# identifier that happens to end in one.
_CODE_SYMBOL = re.compile(r"\b(?:DAT_|FUN_)?CODE_([0-9a-fA-F]{4})\b")


def repo_path(path):
    return os.path.relpath(path, REPO)


def decimal_literals(text):
    """The values the body spells as decimal literals."""
    return {int(m.group(1)) for m in _DECIMAL.finditer(text)}


def register_symbol_names():
    """{name: {address, ...}} over the export's own XDATA symbol table.

    Read from `ec/ghidra/xdata-symbols.csv` -- the file `gen_xdata_symbols.py`
    generates and the export's symbols come from -- rather than from a list
    written here. A name can be given to more than one address, so the value is
    a set: `register_symbol_named()` asks whether *this* address is among them,
    and a name shared by two bytes answers for neither on its own.
    """
    out = {}
    for row in read_index(XDATA):
        addr, name = row.get("addr", "").strip(), row.get("name", "").strip()
        if addr.startswith("0x") and len(addr) == 6 and name:
            out.setdefault(name, set()).add(int(addr, 16))
    return out


def register_symbol_named(body, addr, name_addr):
    """True when the body names `addr` by one of the table's register names."""
    return any(addr in addrs and re.search(r"\b%s\b" % re.escape(name), body)
               for name, addrs in name_addr.items())


def code_symbol_named(body, addr):
    """True when the body names `addr` by the export's code-space spelling."""
    return any(m.group(1).upper() == "%04X" % addr for m in _CODE_SYMBOL.finditer(body))


def classify_body(body, missing, name_addr):
    """One decompiled body against one row's missing addresses. -> a cause.

    Split from `classify_row()` so the branch order can be exercised against
    hand-made text: reading the `.c` off disk is the only part of the question
    that needs the tree, and everything downstream of it is arithmetic over a
    string.

    The first three are asked in that order and each requires *every* missing
    address to satisfy it, so a row whose addresses split between two routes
    falls through to `names-other-addresses` rather than being given the first
    class that fits one of them. A row is one row, and a class that covers half
    of it describes nothing.
    """
    if body is None:
        return ""
    missing = [int(a, 16) if isinstance(a, str) else a for a in missing]
    if not missing:
        return ""
    if all(register_symbol_named(body, a, name_addr) for a in missing):
        return NAMED_BY_REGISTER_SYMBOL
    if all(code_symbol_named(body, a) for a in missing):
        return NAMED_BY_CODE_SYMBOL
    if all(a in decimal_literals(body) for a in missing):
        return NAMED_BY_DECIMAL_LITERAL
    return NAMES_OTHER_ADDRESSES if names_an_address(body) else NAMES_NOTHING


def c_body(out_file, strip):
    """The exported C's code, or None when the row carries no export.

    `strip` defaults to nothing at all, and `disagreement_rows()` passes
    `strip_every_comment`: a cause is a fact about the code the decompiler
    emitted, and Ghidra's `/* WARNING: Removing unreachable block (CODE,0x4be1) */`
    is not code. `common 0x4BB0`'s body is `do {} while (true);` and reads
    `names-nothing` here rather than `names-other-addresses` because of that
    line and no other.
    """
    if not out_file or out_file.startswith("("):
        return None
    path = os.path.join(OUTDIR, out_file.replace(".asm", ".c"))
    if not os.path.isfile(path):
        return None
    with open(path, errors="replace") as f:
        return strip(f.read())


def classify_row(program, addr, out_file, missing, name_addr, strip):
    """One row's cause, or "" for a row that is not in scope."""
    return classify_body(c_body(out_file, strip), missing, name_addr)


def missing_addresses(fw, program, addr, size, out_file, strip):
    """The addresses the comparison still does not see, recomputed here.

    `compare_function()` rather than the report's own `missing` column, and the
    reason is the same one `cross_decoder_blindness.entry_is_branch()` gives for
    recomputing `insns`: a sidecar that read the parent's column would classify
    against whatever that column said, and would go on saying so after the
    parent's `--check` had recomputed it differently. `--self-test` asserts the
    two agree over the committed report.
    """
    return compare_function(program, addr, size, out_file, fw, strip)[4]


def disagreement_rows(fw, strip=strip_header_comment, code=strip_every_comment):
    """The whole sidecar, in the parent's row order. -> [row, ...].

    Every parent key appears, and only a `disagree` row carries a cause. A row
    the parent has stopped sampling is therefore a row this file has to drop,
    which `--check` can say -- and a sidecar holding only the classified rows
    could not tell that from a row the classifier had stopped reaching.

    The two strippers are different on purpose and neither is a copy of the
    other's: `strip` decides which addresses the comparison misses, and it is
    the parent's own rule so that this sidecar classifies the parent's rows;
    `code` decides what the classifier reads, and it removes every comment
    because a cause is about the emitted code. `--self-test` re-runs the whole
    sidecar with `strip` widened to `code`'s rule and asserts the census does
    not move, which is the control `cross_decoder_blindness.py` runs on its own
    stripper for the same reason.
    """
    listing = {(r["program"], r["addr"]): r for r in read_index(LISTING_INDEX)}
    name_addr = register_symbol_names()
    rows = []
    for parent in read_index(CROSS_DECODER):
        program, addr_hex = parent["program"], parent["addr"]
        listed = listing.get((program, addr_hex))
        cause = ""
        if parent["outcome"] == "disagree" and listed is not None:
            addr = int(addr_hex, 16)
            size = int(listed["size"])
            missing = missing_addresses(fw, program, addr, size,
                                        listed["out_file"], strip)
            cause = classify_row(program, addr, listed["out_file"], missing,
                                 name_addr, code)
        rows.append({"program": program, "addr": addr_hex,
                     "name": parent["name"], "outcome": parent["outcome"],
                     "cause": cause})
    return rows


def census(rows):
    """{cause: n} over CAUSES, every key present."""
    counts = dict.fromkeys(CAUSES, 0)
    for row in rows:
        if row["cause"]:
            counts[row["cause"]] += 1
    return counts


def census_line(rows):
    """The line a reader takes away: how much of the disagree bucket is which,
    beside how much of the sample was ever compared."""
    counts = census(rows)
    compared = sum(1 for r in rows if r["outcome"] in ("agree", "disagree"))
    return ("  the %d disagree row(s) are %s, out of %d sampled function(s) "
            "of which %d were compared" % (
                sum(counts.values()),
                ", ".join("%d %s" % (counts[c], c) for c in CAUSES),
                len(rows), compared))


def disagreement_problems(committed, current):
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
        for column in CAUSE_COLUMNS:
            if theirs[key].get(column) != mine[key].get(column):
                problems.append(
                    "%s %s: %s is %r in the sidecar and %r now -- the export, "
                    "the comparison or the classifier moved, so regenerate it"
                    % (key[0], key[1], column, theirs[key].get(column, ""),
                       mine[key].get(column, "")))
    return compared, problems


def partition_problems(rows, parent):
    """The classification is a partition of the disagree rows, and nothing else.

    Three things a reader of the sidecar would otherwise take on trust, and all
    three fail rather than being left out: a `disagree` row carrying no cause, a
    cause on a row that is not `disagree`, and a cause outside the closed
    vocabulary. The first is the one that matters -- it is the row this tool
    exists to stop being silently dropped from a census -- so it is named.
    """
    disagree = {(r["program"], r["addr"]) for r in parent
                if r["outcome"] == "disagree"}
    mine = {(r["program"], r["addr"]): r for r in rows}
    problems = []
    for key in sorted(disagree - set(mine)):
        problems.append("%s %s is disagree in %s and has no row in the sidecar"
                        % (key[0], key[1], repo_path(CROSS_DECODER)))
    for key in sorted(set(mine)):
        row = mine[key]
        if key not in disagree:
            if row["cause"]:
                problems.append("%s %s is %s and carries a `cause`, but only a "
                                "disagree row is in scope"
                                % (key[0], key[1], row["outcome"]))
        elif not row["cause"]:
            problems.append("%s %s is disagree and carries no `cause`: it fell "
                            "in none of them" % key)
        elif row["cause"] not in CAUSES:
            problems.append("%s %s carries %r, which is not in the closed "
                            "vocabulary" % (key[0], key[1], row["cause"]))
    return problems


# The functions this tool is pinned on, one per cause and two per cause that
# could be read as a synonym of another. These are claims about named
# functions, not a count of the tree: every other suite here would rather hold
# a relation over the whole population, and this is the one figure that cannot
# be derived from the sidecar and the parent together.
#
# `bank0 0xB158` is the row §14i's byte-pair fold and the one issue #510 named:
# its body's `store_be16_a(BAT_VOLTAGE_MV_0,0xa48,BAT_VOLTAGE_MV_1)` hands the
# 0x0438/0x0439 pair to a helper as two register names, so the addresses are in
# the C and `_EXTMEM` cannot see them. It is asked first in the class order for
# the same reason, and pinning it at `named-by-register-symbol` rather than at
# a fold of its own is this tool's refusal, made checkable.
#
# `bank0 0xB93A` and `pd 0x357E` are a pair on purpose: one body names an
# address (`DAT_EXTMEM_0a52`) that is not the one the window found, the other
# names none at all (`return *param_1;`). Those are the two readings of
# "not named in the C", and reading them as one bucket is the mistake the last
# two causes exist to prevent.
KNOWN_ANSWERS = [
    ("bank0", "B158", "charge_target_update", NAMED_BY_REGISTER_SYMBOL),
    ("bank0", "8F09", "copy_dptr_byte_to_075c", NAMED_BY_REGISTER_SYMBOL),
    ("common", "00CF", "walk_code_table_6f39", NAMED_BY_CODE_SYMBOL),
    ("bank1", "87DD", "copy_code_a691_a693_to_xdata", NAMED_BY_CODE_SYMBOL),
    ("common", "1228", "FUN_CODE_1228", NAMED_BY_DECIMAL_LITERAL),
    ("bank1", "CFB1", "step_03c3_and_reload_03bf", NAMED_BY_DECIMAL_LITERAL),
    ("bank0", "B93A", "set_dptr_0a51_b93a", NAMES_OTHER_ADDRESSES),
    ("pd", "357E", "read_byte_to_r3_stride_60", NAMES_NOTHING),
    ("common", "4BB0", "FUN_CODE_4bb0", NAMES_NOTHING),
]


def self_test(fw):
    """The known answers, the recomputation, the partition, and the comment
    rule's control. 0 failures exits 0."""
    problems = checks = 0

    def check(label, cond, detail=""):
        nonlocal problems, checks
        checks += 1
        if not cond:
            problems += 1
            print("cross_decoder_disagreement.py: FAIL  %s%s"
                  % (label, "  (%s)" % detail if detail else ""), file=sys.stderr)

    parent = read_index(CROSS_DECODER)
    rows = disagreement_rows(fw)
    by_key = {(r["program"], r["addr"]): r for r in rows}
    listing = {(r["program"], r["addr"]): r for r in read_index(LISTING_INDEX)}
    name_addr = register_symbol_names()

    check("the closed vocabulary is still these five causes, held by name",
          set(CAUSES) == {NAMED_BY_REGISTER_SYMBOL, NAMED_BY_CODE_SYMBOL,
                          NAMED_BY_DECIMAL_LITERAL, NAMES_OTHER_ADDRESSES,
                          NAMES_NOTHING} and len(CAUSES) == 5)

    for program, addr, name, want in KNOWN_ANSWERS:
        row = by_key.get((program, addr))
        check("%s 0x%s %s is %s" % (program, addr, name, want),
              row is not None and row["cause"] == want,
              "no row in the sidecar" if row is None
              else "reads %r, outcome %s" % (row["cause"] or "unclassified",
                                             row["outcome"]))

    # The sidecar's own recomputation against the parent's committed cells, both
    # directions. This is what makes the classes a derivation: a stale `missing`
    # in the report would otherwise classify rows against a number the parent's
    # `--check` has already stopped believing.
    drift = []
    for row in parent:
        if row["outcome"] != "disagree":
            continue
        listed = listing.get((row["program"], row["addr"]))
        if listed is None:
            continue
        again = missing_addresses(fw, row["program"], int(row["addr"], 16),
                                  int(listed["size"]), listed["out_file"],
                                  strip_header_comment)
        if " ".join(sorted(again)) != row["missing"]:
            drift.append((row["program"], row["addr"]))
    check("the recomputed `missing` is the one the committed report records, "
          "for every disagree row", not drift,
          "%d row(s), e.g. %s" % (len(drift), drift[:3]))

    partition = partition_problems(rows, parent)
    check("the classification is a partition of the disagree rows and nothing "
          "else", not partition, "; ".join(partition[:3]))
    check("the partition is over a non-empty population",
          [r for r in parent if r["outcome"] == "disagree"])

    # The comment rule's control: the census cannot depend on which of the two
    # strippers decides the missing set, so the one in the docstring is a choice
    # rather than a reading. A matcher applied to the whole file would find 118
    # fewer rows disagreeing, every one of them only because an annotation
    # mentioned the address its body does not.
    check("widening the rule that finds the missing addresses gives the same "
          "five counts",
          census(disagreement_rows(fw, strip_every_comment)) == census(rows),
          "%s vs %s" % (sorted(census(rows).items()),
                        sorted(census(disagreement_rows(
                            fw, strip_every_comment)).items())))

    # Every cause, constructed. A class nothing can build is a class nothing can
    # check, and a class checked only against the committed tree is a class that
    # stops being reachable without anyone noticing. Each negative case is the
    # positive one with exactly one thing wrong, so a failure names the rule
    # that stopped rejecting rather than the class that stopped matching.
    _names = {"MAIN_FAN_R_DUTY": {0x075C}, "GPU_DYNAMIC_BOOST_STATUS": {0x07C4}}
    # A body that names an address in the comparison's own vocabulary, so the
    # two last causes can be told apart from "names nothing at all".
    _names_an_address = "  DAT_EXTMEM_0a52 = 1;\n  %s\n"
    check("a name from the symbol table names the address, and nothing else "
          "does",
          classify_body("  MAIN_FAN_R_DUTY = *param_1;\n", ["075C"], _names)
          == NAMED_BY_REGISTER_SYMBOL)
    check("a register name for a different address does not count",
          classify_body(_names_an_address % "MAIN_FAN_R_DUTY = 2;",
                        ["07C4"], _names) == NAMES_OTHER_ADDRESSES,
          classify_body(_names_an_address % "MAIN_FAN_R_DUTY = 2;",
                        ["07C4"], _names))
    check("a code-space symbol names a code address",
          classify_body("  pbVar6 = &DAT_CODE_6f39;\n", ["6F39"], _names)
          == NAMED_BY_CODE_SYMBOL)
    check("and does not name an address an EXTMEM_ symbol would",
          classify_body(_names_an_address % "pbVar6 = &DAT_CODE_6f39;",
                        ["075C"], _names) == NAMES_OTHER_ADDRESSES,
          classify_body(_names_an_address % "pbVar6 = &DAT_CODE_6f39;",
                        ["075C"], _names))
    check("a decimal literal of that value names the address",
          classify_body("  read_xdata_pair_to_r1r2(900);\n", ["0384"], _names)
          == NAMED_BY_DECIMAL_LITERAL)
    check("and one of a different value does not",
          classify_body(_names_an_address % "read_xdata_pair_to_r1r2(901);",
                        ["0384"], _names) == NAMES_OTHER_ADDRESSES,
          classify_body(_names_an_address % "read_xdata_pair_to_r1r2(901);",
                        ["0384"], _names))
    check("a hex literal is a route the matcher already had, not a decimal one",
          classify_body("  read_xdata_pair_to_r1r2(0x384);\n", ["0384"], _names)
          == NAMES_OTHER_ADDRESSES,
          classify_body("  read_xdata_pair_to_r1r2(0x384);\n", ["0384"], _names))
    check("a character constant is not the address zero",
          classify_body("  cVar = '\\0';\n", ["0000"], _names)
          == NAMES_NOTHING,
          classify_body("  cVar = '\\0';\n", ["0000"], _names))
    check("a body naming some other address is names-other-addresses",
          classify_body("  return DAT_EXTMEM_0a52;\n", ["0A51"], _names)
          == NAMES_OTHER_ADDRESSES)
    check("a body naming nothing at all is names-nothing",
          classify_body("  return *param_1;\n", ["0408"], _names)
          == NAMES_NOTHING)
    check("a body split between two of the first three causes falls through "
          "rather than taking the first that fits",
          classify_body("  store_be16_a(MAIN_FAN_R_DUTY,0xa48,"
                        "read_xdata_pair_to_r1r2);\n",
                        ["075C", "0384"], _names) == NAMES_OTHER_ADDRESSES,
          classify_body("  store_be16_a(MAIN_FAN_R_DUTY,0xa48,"
                        "read_xdata_pair_to_r1r2);\n",
                        ["075C", "0384"], _names))
    check("a row with no exported C is unclassified rather than guessed",
          classify_body(None, ["075C"], _names) == "")
    check("a row with nothing missing is unclassified rather than guessed",
          classify_body("  MAIN_FAN_R_DUTY = *param_1;\n", [], _names) == "")

    # The classes against the committed decompiles, read as the exporter wrote
    # them, so a class is a statement about the tree and not only about the
    # sidecar that describes it.
    _f4cd = os.path.join(OUTDIR, "pd", "F4CD.c")
    check("pd 0xF4CD's annotation says 'With DPTR loaded from 0x07D6', which is "
          "the whole reason the body has to be read separately",
          os.path.isfile(_f4cd)
          and "With DPTR loaded from 0x07D6" in open(_f4cd, errors="replace").read()
          and "07D6" in names_an_address(open(_f4cd, errors="replace").read()),
          "the fixture the header-comment rule exists for")
    check("common 0x1228's body spells 0xBF68 as the decimal 49000",
          49000 in decimal_literals(c_body("common/1228.c", strip_every_comment)),
          str(sorted(decimal_literals(c_body("common/1228.c",
                                             strip_every_comment)))))
    check("pd 0x357E's body names no address at all",
          not names_an_address(c_body("pd/357E.c", strip_every_comment)))
    check("common 0x4BB0's body is the empty loop it is",
          "while( true )" in (c_body("common/4BB0.c", strip_every_comment) or ""),
          (c_body("common/4BB0.c", strip_every_comment) or "")[:60])
    # The one that decides between the last two causes: Ghidra's own
    # `/* WARNING: Removing unreachable block (CODE,0x4be1) */` lines name six
    # code addresses in a body that is an empty loop, and a class asked of the
    # file rather than of the code would call that a body that names something.
    check("and its WARNING blocks, which name six code addresses, are prose "
          "rather than code",
          names_an_address(c_body("common/4BB0.c", strip_header_comment))
          - names_an_address(c_body("common/4BB0.c", strip_every_comment)),
          str(sorted(names_an_address(c_body("common/4BB0.c",
                                             strip_every_comment)))))

    if problems:
        print("cross_decoder_disagreement.py: %d failure(s) of %d check(s)"
              % (problems, checks), file=sys.stderr)
        return 1
    print("cross_decoder_disagreement.py --self-test: %d check(s) passed over "
          "%d sampled row(s)\n%s" % (checks, len(rows), census_line(rows)))
    return 0


def render(rows):
    """The sidecar as text: what `--report` writes and what `--check` diffs."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=CAUSE_COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


def report(rows, path=DISAGREEMENT):
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
    for cause in CAUSES:
        print("  %-24s %s" % (cause, CAUSE_REASONS[cause]))


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--report", action="store_true",
                    help="(re)write the sidecar from the current tree "
                         "(default: %s)" % repo_path(DISAGREEMENT))
    ap.add_argument("--check", action="store_true",
                    help="re-derive the sidecar and diff it against the "
                         "committed one, exiting non-zero on any difference. A "
                         "missing file fails; it is never created")
    ap.add_argument("--sidecar", metavar="PATH",
                    help="the sidecar --report writes and --check reads, for a "
                         "scratch copy rather than the committed one")
    ap.add_argument("--self-test", action="store_true",
                    help="the known answers, the recomputed `missing`, the "
                         "partition, and the comment rule's control")
    args = ap.parse_args(argv)
    if args.report and args.check:
        ap.error("--check reads the file --report writes; giving both is a "
                 "check that writes the file it is checking")
    sidecar = args.sidecar or DISAGREEMENT

    fw = open(os.path.join(REPO, "ec", "firmware", "GMxMGxx_11.800"), "rb").read()
    if args.self_test:
        return self_test(fw)

    rows = disagreement_rows(fw)
    # Before anything is written or compared: a row that fell in no class is
    # this tool's own failure, and committing a sidecar that quietly omits one
    # is the shape of error the sidecar exists to remove.
    problems = partition_problems(rows, read_index(CROSS_DECODER))
    if problems:
        for problem in problems:
            print("cross_decoder_disagreement.py: %s" % problem, file=sys.stderr)
        print("cross_decoder_disagreement.py: %d partition problem(s); nothing "
              "written and nothing compared" % len(problems), file=sys.stderr)
        return 1

    if args.check:
        if not os.path.isfile(sidecar):
            print("cross_decoder_disagreement.py: no %s -- run --report first. A "
                  "--check that creates the file it is checking has stopped "
                  "checking it" % repo_path(sidecar), file=sys.stderr)
            return 1
        header = next(csv.reader(open(sidecar, newline="")), None)
        if header != CAUSE_COLUMNS:
            problems.append("%s carries the header %r, not this tool's %d "
                            "columns" % (repo_path(sidecar), header,
                                         len(CAUSE_COLUMNS)))
        else:
            compared, drifted = disagreement_problems(read_index(sidecar), rows)
            problems += drifted
        for problem in problems:
            print("cross_decoder_disagreement.py: %s" % problem, file=sys.stderr)
        if problems:
            print("cross_decoder_disagreement.py: %d problem(s)" % len(problems),
                  file=sys.stderr)
            return 1
        print("  %d row(s) recomputed, every cell agreeing with %s"
              % (compared, repo_path(sidecar)))
        print_census(rows)
        return 0

    if args.report:
        print("cross_decoder_disagreement.py: wrote %s"
              % repo_path(report(rows, sidecar)))
    print_census(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
