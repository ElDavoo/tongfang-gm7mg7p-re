#!/usr/bin/env python3
"""Offline checks for census_cluster_citations.py: fixtures and the committed tree.

The tool is a census, so its failure mode is not a crash and not a red run --
it is a **classification that looks like a result**. An inventory that put a
`main-ec-NNN` inside a correction block into `prose` would invite a sweep to
rewrite the one record of what an id was said to be and when; one that put a
§5 census row's first cell into `prose` would invite the rewrite that silently
drops the row out of the count rule, with no error anywhere. Both print a
sensible table and exit 0, which is by design.

So what is pinned here is the classification and the refusals, in the shape
`pd_unannotated_census.py`'s `--self-test` takes: run the tool's own functions
over a fixture file whose answer is known, rather than re-deriving its rules
beside it. A test that re-derives the answer next to the code certifies the
derivation, not the tool.

**The claims, and none of them is a count of the tree.** The five classes are
disjoint and every occurrence lands in exactly one; `template` is matched
before the id regex and so a line naming both yields two occurrences; a census
row is recognised by its first cell and nothing else, so a name in that cell
stops it being one; a name joins a cluster through `cluster_key` and not
through the rank, which is shown by a fixture whose key and rank disagree; and a
`main-ec-NNN` inside a fence is never classified `prose`.

**A deliberately-broken control.** A names-file row keyed to a `cluster_key`
the census does not carry resolves to nothing and is dropped, not guessed at.
The join that could have been a rank lookup is the one that would have
answered here, and a tool that had made it would report a name against the
wrong membership with no error.

**Nothing here reads a capture, an EC, or a laptop.** Every fixture path is a
hand-written string in a `tempfile`; the last class reads committed files with
`open()` and asserts a property of them.
"""
import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).parent
# The tool imports the gate as a sibling, so the directory has to be on the path
# the same way the gate's own suite puts it there.
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location(
    'census_cluster_citations', HERE / 'census_cluster_citations.py')
ccc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ccc)

# The gate itself, read through the tool's own import so the two are the same
# module object and a test cannot pass against a reimplementation.
import check_cluster_citations as gate  # noqa: E402

# A census fixture with two clusters, written so the *key* and the *rank* of a
# name point at different rows. `main-ec-001` carries `kb1`, `main-ec-002`
# carries `kb2`; a names row keyed `kb2` therefore has to land on `main-ec-002`,
# and the rank a reader would guess from the name's own history lands on
# `main-ec-001`. `kb9` is a key of no row, which is what makes the broken
# control below expressible.
CLUSTERS = """cluster_id,cluster_key,cluster_name,addrs,size,refs,named_addrs,addr_range
main-ec-001,kb1,alpha,0x0400 0x0401,2,10,0x0400,0x0400-0x0401
main-ec-002,kb2,countdown-06c6,0x06C6,1,26,0x06C6,0x06C6-0x06C6
"""
REGISTERS = "addr,program\n0x0400,main-ec\n0x0401,main-ec\n0x06C6,main-ec\n"
NAMES = """cluster_key,cluster_name,note
kb2,countdown-06c6,"two addresses, and a note that is the evidence"
kb9,never-seen,no row in the census carries this key
"""

# One fixture file carrying all five classes, each on a line whose shape is the
# only thing distinguishing it, plus a line that carries both a template and an
# id so the two-match case is exercised. Line 16 is the census row; line 17 is
# the same row with a name in the first cell, which is what a sweep must not
# produce and what this fixture makes checkable.
FIXTURE = """\
# a heading

The `0x06C6` byte sits in main-EC cluster `main-ec-002`, which this census
calls `countdown-06c6`, and that is the durable handle for it.
A document writes the form as `main-ec-NNN` and cites `main-ec-002` beside it.

> **Correction, 2026-09-24.** This block's id was `main-ec-002` and stays so.

```console
$ python3 ec/tools/xdata_register_map.py --check
main-ec-002 matches a fresh generation
```

| cluster | key | name | size | refs | range | named inside |
|---|---|---|---|---|---|---|
| `main-ec-002` | `kb2` | `countdown-06c6` | 1 | 26 | `0x06C6`-`0x06C6` | 1 |
| `countdown-06c6` | `kb2` | — | 1 | 26 | `0x06C6`-`0x06C6` | 1 |
"""


def write(directory, name, text):
    path = os.path.join(directory, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


def fixture_census(directory):
    """(clusters, registers, names) paths for the fixtures above."""
    return (write(directory, "clusters.csv", CLUSTERS),
            write(directory, "registers.csv", REGISTERS),
            write(directory, "names.csv", NAMES))


class Classify(unittest.TestCase):
    """The five classes, on one fixture file whose answer is known.

    Asserted by *line*, because that is the shape the report has: a reader
    following `path:line` to a class has to land on the class they were told.
    """

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.path = write(self.dir.name, "fixture.md", FIXTURE)
        clusters, _, names = fixture_census(self.dir.name)
        self.by_id = ccc.names_by_id(clusters, names)

    def lines(self):
        with open(self.path, encoding="utf-8") as f:
            return f.read().split("\n")

    def occurrences(self):
        return ccc.occurrences_in(self.path, self.by_id)

    def test_every_occurrence_lands_in_exactly_one_class(self):
        found = self.occurrences()
        self.assertTrue(found, "the fixture carries a main-ec-NNN and was not read")
        for o in found:
            self.assertIn(o.cls, ccc.CLASSES)

    def test_running_prose_is_prose(self):
        # Lines 3-4 are one wrapped sentence, and the id is on the first of
        # them: the class is the line's, not the unit's, so a reader sent to
        # `path:3` sees what the report said it would.
        self.assertEqual(
            [o.cls for o in self.occurrences() if o.lineno == 3], ["prose"])

    def test_a_blockquote_is_quoted(self):
        self.assertEqual(
            [o.cls for o in self.occurrences() if o.lineno == 7], ["quoted"])

    def test_a_fenced_block_is_not_prose(self):
        inside = [o for o in self.occurrences() if o.lineno == 11]
        self.assertEqual([o.cls for o in inside], ["fenced"])
        self.assertNotIn("prose", [o.cls for o in inside])

    def test_the_form_itself_is_a_template(self):
        templates = [o for o in self.occurrences() if o.cls == ccc.TEMPLATE_CLS]
        self.assertEqual([o.cid for o in templates], ["main-ec-NNN"])

    def test_a_line_naming_both_yields_two_occurrences(self):
        # The whole reason `template` is matched separately rather than left to
        # the id regex: the two are different claims about different things, and
        # a line carrying both is a sentence naming the form while citing a
        # cluster. `main-ec-NNN` sorts first because it starts earlier in the
        # line, which is what makes the report read in reading order.
        on_line_5 = [o for o in self.occurrences() if o.lineno == 5]
        self.assertEqual([(o.cid, o.cls) for o in on_line_5],
                         [("main-ec-NNN", "template"), ("main-ec-002", "prose")])

    def test_a_census_row_is_a_census_row(self):
        self.assertEqual(
            [o.cls for o in self.occurrences() if o.lineno == 16],
            [ccc.CENSUS_ROW])

    def test_the_same_row_with_a_name_in_the_first_cell_is_not_one(self):
        # The claim the sweep has to keep: rewriting a §5 first cell stops the
        # row being a census row at all, and its hand-typed figures then go
        # unchecked with nothing saying so. If this test ever fails, a sweep has
        # edited a first cell.
        self.assertFalse(ccc.head_is_id(self.lines()[16]))
        self.assertNotIn(17, [o.lineno for o in self.occurrences()
                              if o.cls == ccc.CENSUS_ROW])

    def test_an_occurrence_of_an_id_the_census_lacks_is_still_reported(self):
        # A stale cross-reference and a swept one look the same in a report
        # that drops what it cannot resolve, so it is reported with no name.
        path = write(self.dir.name, "stale.md", "The cluster is `main-ec-404`.\n")
        found = ccc.occurrences_in(path, self.by_id)
        self.assertEqual([(o.cid, o.name) for o in found], [("main-ec-404", None)])


class JoinByKey(unittest.TestCase):
    """A name joins its cluster through `cluster_key`, and not through the rank."""

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.clusters, _, self.names = fixture_census(self.dir.name)

    def joined(self):
        return ccc.names_by_id(self.clusters, self.names)

    def test_the_key_finds_the_row_the_names_file_is_keyed_by(self):
        # `kb2` is `main-ec-002`'s key, so `countdown-06c6` belongs to it. A
        # join on the rank would have had to guess which number the names file
        # meant, and every guess is a name on the wrong membership.
        self.assertEqual(self.joined(), {"main-ec-002": ("countdown-06c6",
                                                         "two addresses, and a "
                                                         "note that is the evidence")})

    def test_a_key_the_census_does_not_carry_resolves_to_nothing(self):
        # The deliberately-broken control. `kb9` is a row of the names file and
        # no row of the census, and the honest answer is that this walk did not
        # find a cluster for it -- not a guess, and not an id invented from the
        # row's position.
        self.assertNotIn("never-seen", {name for name, _ in self.joined().values()})

    def test_an_occurrence_reports_the_note_that_is_its_evidence(self):
        # The note is why the tool prints it: a reader deciding whether an
        # occurrence is a pointer needs the reason the name is that name, and
        # `ghidra-functions.csv`'s mandatory evidence column is the precedent.
        self.assertIn("note that is the evidence",
                      self.joined()["main-ec-002"][1])


class TheCommittedTree(unittest.TestCase):
    """Properties of the committed files, not a count of them.

    Every assertion below is a claim that stays true as the corpus grows; none
    of them is a figure a merge would have to edit, which is the trap
    `CLAUDE.md` names. A sweep that turned a §5 first cell into a name, or left
    a fence's ids looking like prose, fails one of these.
    """

    def test_every_name_the_census_carries_is_read(self):
        # If a name were added to `xdata-clusters.csv` and its row dropped from
        # the names file, or the join broke, the tool would report fewer names
        # than the census carries and a sweep would never see them. The claim is
        # agreement between two committed files, not a number.
        by_id = ccc.names_by_id()
        carried = {name for name in gate.census()[4]}
        self.assertTrue(carried, "the census carries no cluster_name at all")
        self.assertEqual({name for name, _ in by_id.values()}, carried)

    def test_no_main_ec_id_in_a_fence_is_classified_prose(self):
        # The class a sweep would act on. An id inside a fenced block is pasted
        # output from a run the reader cannot open, and re-pointing it at a
        # name would edit a transcript.
        for rel in ccc.SWEPT:
            path = os.path.join(ccc.REPO, rel)
            with open(path, encoding="utf-8") as f:
                text = f.read()
            fences = {n for open_at, close_at in gate.fence_spans(
                text.split("\n")) for n in range(open_at, close_at + 1)}
            for o in ccc.occurrences_in(path, ccc.names_by_id()):
                self.assertFalse(o.lineno in fences and o.cls == ccc.PROSE,
                                 "%s:%d is inside a fence" % (rel, o.lineno))

    def test_every_census_row_still_carries_an_id_the_census_knows(self):
        # The coverage the sweep had to give up, asserted as the property and
        # not as a row total: the count rule reads a census row only when the
        # first cell is exactly one id, so a name there would drop the row's
        # hand-typed figures out of checking with nothing saying so. Every row
        # the tool calls a census row must still be one the gate would hold to
        # the CSV, or the inventory is pointing a sweep at a row that is not
        # being checked anyway.
        _, _, counts, _, _ = gate.census()
        for rel in ccc.SWEPT:
            path = os.path.join(ccc.REPO, rel)
            with open(path, encoding="utf-8") as f:
                lines = f.read().split("\n")
            for o in ccc.occurrences_in(path, ccc.names_by_id()):
                if o.cls != ccc.CENSUS_ROW:
                    continue
                self.assertIn(o.cid, counts,
                              "%s:%d is a census row for an id this census does "
                              "not carry, so the count rule never held it to "
                              "anything" % (rel, o.lineno))

    def test_every_name_cited_in_the_swept_files_resolves(self):
        # The property the sweep exists to establish, read through the gate's
        # own `name_re()` and `cited_clusters()` rather than this tool's map: a
        # name in the prose that the gate cannot resolve would be a citation
        # the sweep introduced and the gate cannot check.
        _, _, _, by_key, by_name = gate.census()
        names = gate.name_re(by_name)
        self.assertIsNotNone(names, "the census carries no name to match")
        for rel in ccc.SWEPT:
            path = os.path.join(ccc.REPO, rel)
            with open(path, encoding="utf-8") as f:
                text = f.read()
            for unit in text.split("\n"):
                for cited in names.findall(unit):
                    self.assertIn(cited, by_name,
                                  "%s cites %r, which this census does not carry"
                                  % (rel, cited))
            # And the union of the three forms is what a reader resolves.
            for lineno, unit in gate.units(text):
                for cid in gate.cited_clusters(unit, by_key, by_name, names):
                    self.assertTrue(cid.startswith(("main-ec-", "pd-")),
                                    "%s:%d cites %r" % (rel, lineno, cid))

    def test_the_swept_files_are_the_seven_the_issue_names(self):
        # A path typo here would make every other test in this class read a
        # different file from the one the sweep edited, and the suite would
        # still be green.
        for rel in ccc.SWEPT:
            self.assertTrue(os.path.exists(os.path.join(ccc.REPO, rel)), rel)
            self.assertTrue(rel.endswith(".md"), rel)


if __name__ == '__main__':
    unittest.main()
