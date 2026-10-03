#!/usr/bin/env python3
"""The `[named]` marker and the index's `annotated` column agree, on every row.

`build_ec_decompile.py --self-test` holds `grade_name_basis.py`'s reserved-prefix
list against `isPlaceholderName()` in both directions, and it reads **one** Java
file — the canonical `ghidra/scripts/TongFang.java`. That guard is what stopped
#602's rule from being forgotten, and it is blind to the failure this test
exists for: while there were two copies of the predicate,
`ExportDecompile.java` carried its own.

**As of #626 there is one Java definition again**, so the table below records
what the four outputs *were* written by rather than what they are — the split is
history, and the disagreement it could produce is what this file still guards.
`bios/tools/test_entry_namespace.py` now holds the definition count that
`--self-test` structurally could not see, because its regex requires `public
static` and so never matched the `private static` twin.

The four outputs were not all written by the same copy:

| output | written by | predicate it called | where it exists |
|---|---|---|---|
| `index.csv`'s `annotated` column | `ExportDecompile` | its own private copy | EC and BIOS |
| the `[named]` marker on a `.c` | `ExportDecompile` | its own private copy | **EC only** |
| `listing-index.csv`'s `annotated` column | `ExportListing` | `TongFang` | EC and BIOS |
| the `[named]` marker on an `.asm` | `ExportListing` | `TongFang` | EC and BIOS |

**The `.c` row is EC-only, and the reason is a mode rather than a fault.**
`ExportDecompile` writes that marker in `writeFunctionFile`, which runs only in
per-function mode. `bios/tools/bios_extract.py` runs the same script in
**per-program** mode, where a `.c` gets a `// ==== <name> @ <addr>` separator
instead and never a marker — so no file under `bios/decompiled/` carries one,
and every row of `bios/ghidra/index.csv` names a whole-program `out_file`
(`DxeOverClock.c`) rather than a per-function one. The relation asserted below is
therefore this file's on the EC and one clause short of it on the BIOS;
asserting the `.c` clause there would read a file that never carries the marker
and report every `annotated=yes` row as a fault.
`docs/findings/entry-namespace-two-copies.md` has the measurement, and against
the BIOS the clause that does hold there is currently red on two rows.

Widen one copy and not the other and the self-test stays green — it compares
`len(java) == len(want_literals)` against the canonical file either way — while
the committed tree holds an address where one of the two markers disagrees with
the column `index.csv` gives it. #602's re-export went through with an
`equals`/`startsWith` divergence already in place, so this is not hypothetical.

So the relation is asserted where it is visible: for every committed row of
`index.csv`, the `[named]` marker on the file its `out_file` names **and** on the
listing beside it must both equal `annotated == "yes"`. That is a relation
between committed files and it holds or fails however the export is later
regenerated — no total of the tree is asserted anywhere here, because a figure
every annotation tranche and every re-export has to edit is a lock nobody holds.

**Ungated by design.** `.github/` is template-copied and the push token has no
`workflow` scope, so this is not wired into `agent-gates.sh` and says so rather
than pretending otherwise; `bash tools/run-tests.sh` discovers it.

**The refusals are what make the check worth anything.** A reader that reports
"no marker" for a file it could not read agrees with every `annotated=no` row in
the tree, so a header it cannot parse is indistinguishable from a header that is
correctly unmarked. Every such case is reported rather than skipped, and each one
is driven on a fixture below — including the tree where the two Java copies
disagree, which is the disagreement this file was written for.
"""

import csv
import os
import re
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
EC = os.path.join(HERE, os.pardir)
DECOMPILED = os.path.join(EC, "decompiled")
INDEX = os.path.join(DECOMPILED, "index.csv")
LISTING_INDEX = os.path.join(DECOMPILED, "listing-index.csv")

# The opening line each file kind is written with: `ExportDecompile` opens a `.c`
# with `//` and `ExportListing` opens an `.asm` with `;`, and the program, the
# address and the name follow in that order. A file carrying the *other* kind's
# sigil is a header this reader cannot read rather than an unmarked one.
SIGIL = {".c": "//", ".asm": ";"}
MARKER = "[named]"
# What `ExportListing` writes into `out_file` for a function with no instructions
# to list, in place of a path. It is the documented way a committed row says it
# has no listing, so a row whose listing is absent and does not say so is a
# fault rather than a state to skip.
NO_LISTING = "(no-instructions)"
# Only the sigil is parsed. Whether the address in the header is the address the
# index row is about is `build_ec_decompile.py`'s presence pass and is asserted
# there; this file answers one question, and answering it in two places would
# only make a red run ambiguous about which tool owns the fault.
HEADER = re.compile(r"^(?P<sigil>//|;) ")


def read_index(path):
    """The index rows of `path`, or [] when the file is not there."""
    if not os.path.isfile(path):
        return []
    with open(path, newline="") as handle:
        return list(csv.DictReader(handle, strict=True))


def header_named(path, kind):
    """Whether `path` carries the `[named]` marker on its opening line.

    None rather than False when the line is not a header this reader can read --
    the file is absent, empty, or opens with something other than `kind`'s sigil.
    None is not "unmarked": a row reported `annotated=no` agrees with False and
    would pass silently, which is the whole reason the distinction is kept.
    """
    want = SIGIL.get(kind)
    if want is None:
        return None
    try:
        with open(path, errors="replace") as handle:
            first = handle.readline()
    except OSError:
        return None
    got = HEADER.match(first)
    if got is None or got.group("sigil") != want:
        return None
    return MARKER in first


def listing_of(row):
    """The `.asm` path an index row's `out_file` implies, or None when it does
    not imply one. The path the listing is *actually* at is the listing index's
    own `out_file`, and `disagreements` holds the two against each other."""
    out = row.get("out_file") or ""
    return out[:-2] + ".asm" if out.endswith(".c") else None


def disagreements(rows, decompiled, listing_rows=()):
    """Every row whose file header disagrees with its `annotated` column.

    (program, addr, kind, annotated, marker) per fault, where the marker is True,
    False or None — the three states a header can be read in, none of which is
    skipped. The `.asm` side is driven by `listing-index.csv`, which is the
    exporter that wrote the listing and the only place that says whether a row
    has one at all: a row it records as `(no-instructions)` is a state to accept,
    while a row it names a path for and that path is not there is a fault.
    """
    listed = {(r["program"], r["addr"]): r.get("out_file") or ""
              for r in listing_rows}
    out = []
    for row in rows:
        key = (row["program"], row["addr"])
        want = row.get("annotated") == "yes"
        marker = header_named(os.path.join(decompiled, row.get("out_file") or ""),
                              ".c")
        if marker != want:
            out.append(key + (".c", row.get("annotated"), marker))
        listing = listed.get(key)
        if listing is None:
            out.append(key + (".asm", row.get("annotated"), "no listing row"))
            continue
        beside = listing_of(row)
        if listing == NO_LISTING:
            # Declared absent, so nothing is read and nothing is asked for -- but
            # the index row still implies a path, and a file there would mean the
            # two exporters disagree about whether there is a listing.
            if beside and os.path.isfile(os.path.join(decompiled, beside)):
                out.append(key + (".asm", row.get("annotated"),
                                  "listed as absent, and the file is there"))
            continue
        if beside and beside != listing:
            out.append(key + (".asm", row.get("annotated"),
                              "listed at %s, index row implies %s"
                              % (listing, beside)))
        marker = header_named(os.path.join(decompiled, listing), ".asm")
        if marker != want:
            out.append(key + (".asm", row.get("annotated"), marker))
    return out


def _fixture(scratch, cases):
    """A scratch decompiled tree holding `cases`, and the rows that read it.

    Fixtures rather than committed rows, because every one of these is a shape
    the committed tree happens not to have — and a refusal tested against the
    committed rows stops being a refusal the day the tree grows one that needs
    it. The headers are written here directly, so the drift being exercised is in
    the output rather than in a Ghidra run a fixture cannot perform.

    A case is (address, annotated, c_marker, asm_marker) and the marker is True
    for a marked header, False for an unmarked one, None for no `.asm` written
    at all (which records the listing as `(no-instructions)`), or `"?"` for one
    written with the `.c`'s sigil, which no reader of an `.asm` can make sense
    of.
    """
    os.makedirs(os.path.join(scratch, "common"), exist_ok=True)
    rows, listing = [], []
    for at, annotated, c_marker, asm_marker in cases:
        addr = "%04X" % at
        name = "fixt_%s" % addr.lower() if annotated == "yes" else "caseD_0"

        def write(kind, sigil, marked):
            if sigil is None:
                return None
            with open(os.path.join(scratch, "common", addr + kind), "w") as f:
                f.write("%s common @ %s   %s%s\nbody\n"
                        % (sigil, addr, name,
                           "   " + MARKER if marked is True else ""))
            return "common/%s%s" % (addr, kind)

        rows.append({"program": "common", "addr": addr, "annotated": annotated,
                     "out_file": write(".c", "//", c_marker)})
        asm_out = write(".asm", "/" if asm_marker == "?" else ";", asm_marker)
        listing.append({"program": "common", "addr": addr,
                        "annotated": annotated,
                        "out_file": asm_out or NO_LISTING})
    return rows, listing


class NamedMarkerAgreement(unittest.TestCase):
    """The committed relation, over both indexes and both file kinds."""

    def test_every_committed_row_agrees_with_its_own_headers(self):
        found = disagreements(read_index(INDEX), DECOMPILED,
                              read_index(LISTING_INDEX))
        self.assertEqual(found, [], "%d row(s) disagree" % len(found))


class HeaderReading(unittest.TestCase):
    """What the reader does with each shape of opening line."""

    def faults(self, cases):
        scratch = tempfile.mkdtemp(prefix="named_marker_agreement")
        self.addCleanup(shutil.rmtree, scratch, True)
        rows, listing = _fixture(scratch, cases)
        return list(disagreements(rows, scratch, listing))

    def header(self, addr, kind):
        handle = tempfile.NamedTemporaryFile("w", suffix=kind, delete=False)
        self.addCleanup(os.remove, handle.name)
        return handle.name

    def test_a_pair_that_agrees_with_its_column_reads_through(self):
        self.assertEqual(self.faults([(0x0100, "yes", True, True),
                                      (0x0110, "no", False, False)]), [])

    def test_each_java_copy_widening_alone_is_a_fault(self):
        # Both halves of the drift this file exists for, and they are different
        # faults: the `.c` marked under a column saying `no` is `ExportDecompile`
        # widening alone, and the `.asm` marked the same way is `TongFang`
        # widening alone. Reading one Java file sees neither, and a reader that
        # only looked at `.c` files would see one of them.
        self.assertEqual(self.faults([(0x0120, "no", True, False),
                                      (0x0130, "no", False, True)]),
                         [("common", "0120", ".c", "no", True),
                          ("common", "0130", ".asm", "no", True)])

    def test_a_header_this_reader_cannot_read_is_reported_not_skipped(self):
        # An `.asm` opening with the `.c`'s sigil, against an `annotated=no`
        # row -- the row a reader that reported "no marker" would have passed.
        scratch = tempfile.mkdtemp(prefix="named_marker_agreement")
        self.addCleanup(shutil.rmtree, scratch, True)
        rows, listing = _fixture(scratch, [(0x0140, "no", False, "?")])
        self.assertIsNone(header_named(os.path.join(scratch, "common",
                                                    "0140.asm"), ".asm"))
        self.assertEqual(disagreements(rows, scratch, listing),
                         [("common", "0140", ".asm", "no", None)])

    def test_a_row_with_no_listing_may_say_so(self):
        # `ExportListing` writes `(no-instructions)` in place of a path for a
        # function it has nothing to list, and that is a state to accept rather
        # than a fault -- the committed tree's three such rows are `FUN_CODE_*`
        # stubs of one byte each. Declaring it is what tells an absent listing
        # from a deleted one, so the same row is clean declared and a fault not.
        self.assertEqual(self.faults([(0x0150, "no", False, None)]), [])
        self.assertEqual(self.faults([(0x0160, "no", False, "?")]),
                         [("common", "0160", ".asm", "no", None)])

    def test_a_kind_with_no_sigil_is_itself_unreadable(self):
        path = self.header(0x0100, ".c")
        with open(path, "w") as f:
            f.write("// common @ 0100   fixt_0100   %s\n" % MARKER)
        self.assertIs(header_named(path, ".c"), True)
        self.assertIsNone(header_named(path, ".asm"))
        self.assertIsNone(header_named(path, ".txt"))


if __name__ == "__main__":
    sys.exit(unittest.main())
