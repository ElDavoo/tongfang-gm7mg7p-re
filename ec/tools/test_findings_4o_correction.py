#!/usr/bin/env python3
"""The §4o census bullet's `0x07D1` retraction, and the shape §4a-4d requires.

**Why this suite exists at all.** `check_findings_frozen.py` is the gate that
protects `docs/findings.md`, and its own docstring says it "does not check that
the prose inside an existing section is still true. That is a reading, and this
is a count." So the file's *contents* are unprotected by construction, and the
rule that does protect them — §4a-4d, a wrong claim stays visible with its
correction beside it — is prose in a frozen file. Issue #323 added the first
correction to §4o, and the four ways that one can go wrong later are all
invisible to every existing gate:

1. **The stale clause gets edited out.** It reads as cruft once it is
   corrected, and deleting it loses the record that the bullet was ever wrong —
   the same class of loss the freeze exists to prevent, one level down.
2. **The correction stops quoting it.** A paraphrase is easier to write and
   leaves the reader to work out which words were retracted, which is the part
   the whole pattern exists to make unnecessary.
3. **The correction drifts away from the bullet.** Moved above it, below it, or
   out of its list item by losing its indent, it is no longer *beside* the
   claim, and none of those breaks anything a count can see.
4. **The correction's citations go stale.** The paths are written in backticks
   and `check_doc_links` resolves only markdown link syntax, which is the other
   spelling, so a renamed or deleted walk file leaves the retraction pointing at
   nothing.

The fifth case is `CLAUDE.md`'s own citation rule held over the prose this
change adds: a `file.py:1981` pin is true only until the next merge grows the
file above it, and a bare one is a blocking review finding rather than a style
preference.

None of this is a hardware claim and none of it opens an image: the suite reads
two markdown files and asks about one paragraph in each.
"""

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
FINDINGS = REPO / "docs" / "findings.md"
CORRECTION_FILE = REPO / "docs" / "findings" / "07d6-07d7-pd-image-census.md"
WALK = REPO / "ec" / "annotations" / "ec-07d6-07d7-sites.md"

# The heading the walk document's open-work list sits under, and the tool whose
# work §7's correction closes. Spelled as a heading prefix so a retitled §8
# does not silently turn the case below into a vacuous pass.
STILL_OPEN = "## 8. What is still open"
CLOSED_TOOL = "t1wr_callers.py"

# The clause §4o's census bullet carried before #323 corrected it, and the
# marker of the correction beside it. Both are spelled as fragments of the
# sentences they sit in, so a rewrap of either does not red this: what is
# matched is the prose, not its line breaks.
RETIRED = ("but no per-site decode, and that is a real gap rather than a "
           "formality")
MARKER = "*** CORRECTION 2026-10-01 (issue #323)"

# The repository paths the correction and the write-up lean on. A named list
# rather than a sweep of every backticked path either file happens to contain:
# a general markdown-link checker is `check_doc_links` and it works in the other
# spelling, so this is scoped to the citations this change introduced.
CITED = (
    "ec/annotations/ec-0x07d1-sites.md",
    "ec/annotations/ec-0x07d1-sites.csv",
    "ec/annotations/ec-07d6-07d7-sites.md",
    "ec/annotations/ec-07d6-07d7-sites.csv",
    "docs/findings/07d6-07d7-pd-image-census.md",
    "docs/hardware-tests/gpu-tgp-07c4-07d7-door.md",
    "ec/annotations/registers.yaml",
)

# A `file.py:1981` in prose is true only until the next merge grows the file
# above it, and CLAUDE.md records such a pin as a blocking review finding
# repeatedly. Held over the two pieces of new prose this change adds and nothing
# else: `docs/findings.md` carries historical pins of its own and is not this
# suite's to clean up. The colon is inside the backticks, which is the spelling
# that has to be caught -- `` `grade_0751_isolation.py:1981` `` -- and not
# `` `grade_0751_isolation.py`:1981 ``, which is a path and a number in prose
# rather than a pin. `COMMIT_QUALIFIER` is the exemption CLAUDE.md allows.
LINE_PIN = re.compile(r"`[^`\n]*\.(?:py|md|csv|yaml|sh|json):\d+`")
COMMIT_QUALIFIER = re.compile(r"\s+at [0-9a-f]{7,40}\b")


def flatten(text):
    """`text` as one whitespace-normalised line, so a rewrap is not a change."""
    return " ".join(text.split())


def lines():
    return FINDINGS.read_text(encoding="utf-8").splitlines()


def marker_line():
    """The line #323's correction marker is on, or `None` if it is gone."""
    rows = lines()
    return next((i for i, line in enumerate(rows) if MARKER in line), None)


def line_holding(needle, limit=None):
    """The index of the line a `needle` ends on, in `docs/findings.md`.

    Read against the flattened text rather than one line at a time, because the
    clause this suite is about is wrapped across two of them and a rewrap is
    not a change to the prose. The line returned is the one the clause *ends*
    on, which is where its correction has to follow from.

    `limit` bounds the search, and it is load-bearing rather than tidy: the
    correction quotes the clause it corrects, so a search over the whole file
    would find the quotation and report the bullet as still carrying the claim
    after it had been edited out of it.
    """
    rows = lines()[:limit] if limit is not None else lines()
    offsets, at = [], 0
    for line in rows:
        offsets.append(at)
        at += len(" ".join(line.split())) + 1
    found = flatten("\n".join(rows)).find(needle)
    if found < 0:
        return None
    line = 0
    for index, offset in enumerate(offsets):
        if offset <= found:
            line = index
        else:
            break
    return line


def bullet_end(rows, start):
    """The next line after `start` that opens a bullet at column 0, or the end.

    One rule, used by every case that asks where the correction stops: a
    paragraph break inside a list item is indented, so a column-0 `- ` is the
    only thing that can end the item.
    """
    for index in range(start + 1, len(rows)):
        if rows[index].startswith("- "):
            return index
    return len(rows)


def correction_block():
    """The correction paragraph, from its marker to the end of its bullet."""
    rows = lines()
    start = marker_line()
    if start is None:
        return ""
    return "\n".join(rows[start:bullet_end(rows, start)])


def walk_rows():
    return WALK.read_text(encoding="utf-8").splitlines()


def prose(block):
    """`block` as one line, with markdown blockquote markers stripped.

    A correction nested inside a bullet is written as a `> ` quote, so a phrase
    that spans a wrap picks the marker up in the middle of itself and `flatten`
    alone will not match it. Stripping the marker first is what keeps a rewrap
    from reading as a change to the prose, which is the reason the text is
    flattened at all.
    """
    stripped = [re.sub(r"^\s*(?:>\s*)?", "", line)
                for line in block.splitlines()]
    return flatten("\n".join(stripped))


def still_open_bullets():
    """Each bullet under the walk document's open-work heading, with its body.

    A bullet runs from its `- ` line to the next `- ` at column 0, which is
    what makes the correction nested inside it part of the bullet: a correction
    written beside the claim but outside the list item renders as a sibling
    paragraph, and the reader sees a to-do that nothing corrects. Returned
    whole rather than line by line for that reason.
    """
    rows = walk_rows()
    start = next((i for i, line in enumerate(rows)
                  if line.startswith(STILL_OPEN)), None)
    if start is None:
        return []
    blocks, current = [], None
    for line in rows[start + 1:]:
        if line.startswith("- "):
            if current is not None:
                blocks.append("\n".join(current))
            current = [line]
        elif current is not None:
            current.append(line)
    if current is not None:
        blocks.append("\n".join(current))
    return blocks


def walk_corrections():
    """Every correction paragraph in the walk document, in file order.

    Scanned over the whole file rather than over §8's bullets: §1 and §7 each
    carry one too, and a pin check that quietly read only the last section
    would be a weaker check wearing the stronger check's name.
    """
    rows, blocks, current = walk_rows(), [], None
    for line in rows:
        if "CORRECTION" in line:
            current = [line]
        elif current is not None:
            # A correction runs until the next blank line, which is what ends
            # the paragraph; a bullet is a list, not a paragraph.
            if not line.strip():
                blocks.append("\n".join(current))
                current = None
            else:
                current.append(line)
    if current is not None:
        blocks.append("\n".join(current))
    return blocks


class TheRetractedSentenceIsStillThere(unittest.TestCase):
    """Case 1: the wrong claim stays visible rather than being edited out."""

    def test_the_bullet_still_carries_the_claim_it_made(self):
        # Searched ahead of the marker only. The correction quotes the clause
        # on purpose, so a search over the whole file is satisfied by the
        # quotation and would pass on a bullet the clause had been deleted from
        # -- which is the deletion this case exists to catch.
        marker = marker_line()
        self.assertIsNotNone(marker, "the #323 correction marker is not in "
                                   "docs/findings.md")
        bullet = flatten("\n".join(lines()[:marker]))
        self.assertIn(RETIRED, bullet,
                      "§4o's census bullet no longer carries the clause it "
                      "made; §4a-4d keeps a wrong claim visible beside its "
                      "correction, and deleting it loses the record that the "
                      "bullet was ever wrong")

    def test_the_correction_quotes_it_rather_than_paraphrasing_it(self):
        # §4a-4d's rule is that the correction quotes the sentence it corrects.
        # A paraphrase leaves a reader to work out which words were retracted,
        # which is the part the whole pattern exists to make unnecessary.
        block = correction_block()
        self.assertIn(RETIRED, flatten(block),
                      "the correction does not quote the clause it retracts")


class TheCorrectionSitsBesideTheBullet(unittest.TestCase):
    """Case 2: same list item, after the clause, before the next bullet."""

    def setUp(self):
        self.rows = lines()
        marker = marker_line()
        self.assertIsNotNone(marker, "the #323 correction marker is not in "
                                     "docs/findings.md")
        self.start = line_holding(RETIRED, limit=marker)
        self.assertIsNotNone(
            self.start,
            "the retracted clause is not in the bullet above the correction; "
            "§4a-4d keeps the wrong claim visible beside its correction")

    def _bullet_end(self):
        return bullet_end(self.rows, self.start)

    def test_the_correction_follows_the_clause_it_corrects(self):
        end = self._bullet_end()
        markers = [i for i in range(self.start, end)
                   if MARKER in self.rows[i]]
        self.assertEqual(
            len(markers), 1,
            "the correction is not inside the bullet that carries the "
            "retracted clause, or is written more than once")

    def test_the_correction_is_indented_so_it_renders_inside_the_item(self):
        # Markdown drops a blockquote to the next block when it is not indented,
        # so an unindented correction silently becomes a sibling paragraph and
        # the bullet reads as though nothing corrected it.
        end = self._bullet_end()
        markers = [i for i in range(self.start, end)
                   if MARKER in self.rows[i]]
        self.assertTrue(markers, "no correction inside the bullet")
        self.assertTrue(self.rows[markers[0]].startswith("  "),
                        "the correction is not indented under its bullet")

    def test_the_correction_does_not_run_past_the_bullet(self):
        self.assertTrue(correction_block(),
                        "the correction paragraph is empty or was merged into "
                        "the following bullet")


class TheCitationsResolve(unittest.TestCase):
    """Case 3: the files the correction leans on are still in the tree."""

    def test_every_path_the_correction_and_write_up_name_exists(self):
        for path in CITED:
            with self.subTest(path=path):
                self.assertTrue((REPO / path).is_file(),
                                "%s is cited and is not in the tree" % path)

    def test_the_write_up_names_the_two_walks_the_correction_points_at(self):
        # The write-up is the pointer the frozen file cannot carry, so it has to
        # carry the pointer itself rather than restate the record.
        text = CORRECTION_FILE.read_text(encoding="utf-8")
        for path in ("ec-0x07d1-sites.md", "ec-07d6-07d7-sites.md"):
            with self.subTest(path=path):
                self.assertIn(path, text)

    def test_the_write_up_has_the_one_heading_the_index_reads(self):
        # `gen_findings_index.py` takes the first `# ` line as the row's title
        # and falls back to the file name if there is none, so a heading that
        # moved below the lead would leave the index row a filename.
        headings = [line for line in CORRECTION_FILE.read_text(
            encoding="utf-8").splitlines() if line.startswith("# ")]
        self.assertEqual(len(headings), 1,
                         "docs/findings/07d6-07d7-pd-image-census.md must carry "
                         "exactly one `# ` heading for the index row")


def bare_pins(text):
    """Every line-pin in `text` that does not also carry a commit.

    CLAUDE.md's exemption is the pin that comes with a commit -- a reader can
    follow it to the tree the line was measured on -- and a rule that reddened
    on that spelling would redden on the correct answer, which is how a check
    gets switched off rather than fixed.
    """
    return [m.group(0) for m in LINE_PIN.finditer(text)
            if not COMMIT_QUALIFIER.match(text[m.end():m.end() + 48])]


class NoBareLinePinInTheNewProse(unittest.TestCase):
    """The new prose cites by name, the way CLAUDE.md requires."""

    def test_the_write_up_cites_by_name(self):
        hits = bare_pins(CORRECTION_FILE.read_text(encoding="utf-8"))
        self.assertEqual(hits, [], "the write-up carries a bare line pin: %r"
                         % (hits,))

    def test_the_correction_cites_by_name(self):
        hits = bare_pins(correction_block())
        self.assertEqual(hits, [], "the correction carries a bare line pin: %r"
                         % (hits,))

    def test_the_walk_document_corrections_cite_by_name(self):
        for block in walk_corrections():
            hits = bare_pins(block)
            self.assertEqual(hits, [], "a walk-document correction carries a "
                                       "bare line pin: %r" % (hits,))

    def test_a_pin_with_a_commit_is_the_exemption_and_passes(self):
        # The negative control for the case above: a rule that fires on the
        # spelling CLAUDE.md permits is worse than no rule, because it trains
        # everyone to ignore it.
        self.assertEqual(bare_pins("as `grade_0751_isolation.py:1981 at "
                                   "0a088444` says"), [])
        self.assertEqual(bare_pins("as `grade_0751_isolation.py:1981` says"),
                         ["`grade_0751_isolation.py:1981`"])


class TheOpenListDoesNotResurrectClosedWork(unittest.TestCase):
    """§4a-4d's shape, one level down: a corrected claim is not still open.

    A correction in one section does not reach a to-do list in another. §7's
    correction closes the `t1wr_callers.py` widening; §8's list kept naming it
    as open work, twenty lines below the paragraph saying it was done, and a
    reader arriving at "what is still open" is sent to re-bake a tool that
    self-checks clean. The stale bullet stays visible with its correction
    beside it, exactly as §7's does, so the fix is the shape and not a deletion
    -- what these cases hold is that the two sections cannot disagree again.
    """

    def setUp(self):
        self.blocks = still_open_bullets()
        self.assertTrue(self.blocks,
                        "the walk document has no bullets under %r; the cases "
                        "below would pass vacuously" % STILL_OPEN)

    def test_the_heading_the_cases_read_is_the_one_that_is_there(self):
        # Guards the vacuous pass above: a retitled or renumbered §8 must fail
        # loudly here rather than leave the sweep below matching nothing.
        headings = [line for line in WALK.read_text(
            encoding="utf-8").splitlines() if line.startswith("## ")]
        self.assertTrue(any(flatten(h).startswith(STILL_OPEN) for h in headings),
                        "the walk document's open-work heading is not %r"
                        % STILL_OPEN)

    def test_the_bullet_naming_the_closed_work_carries_a_correction(self):
        naming = [b for b in self.blocks if CLOSED_TOOL in b]
        self.assertTrue(naming,
                        "no bullet under %r names %s any more; if the to-do "
                        "was deleted rather than corrected, the record that it "
                        "was ever open is gone"
                        % (STILL_OPEN, CLOSED_TOOL))
        for block in naming:
            self.assertIn("CORRECTION", block,
                          "a bullet under %r still lists the %s widening as "
                          "open work with no correction beside it; §7's "
                          "correction closes it"
                          % (STILL_OPEN, CLOSED_TOOL))

    def test_no_bullet_under_the_open_list_names_the_closed_work_uncorrected(self):
        # The same claim as a sweep rather than as a lookup, so a second bullet
        # naming the same closed work is caught rather than passing because the
        # first one is corrected.
        offenders = [b for b in self.blocks
                     if CLOSED_TOOL in b and "CORRECTION" not in b]
        self.assertEqual(offenders, [],
                         "these bullets under %r name %s with no correction: "
                         "%r" % (STILL_OPEN, CLOSED_TOOL, offenders))

    def test_the_correction_says_the_re_bake_names_the_right_section(self):
        # The stale bullet attributes the re-bake to `docs/findings.md` §4f.
        # The tool's census is quoted in §4o and §4f does not mention the tool,
        # so a correction that fixes only the "still open" half leaves the
        # reader with a to-do pointed at a section that never carried it.
        for block in self.blocks:
            if CLOSED_TOOL not in block or "CORRECTION" not in block:
                continue
            self.assertIn("§4o", prose(block),
                          "the correction does not name §4o as the section "
                          "carrying the census")
            self.assertIn("does not mention the tool", prose(block),
                          "the correction does not say that §4f does not "
                          "mention the tool, so the wrong attribution stands "
                          "uncorrected beside it")


if __name__ == "__main__":
    unittest.main()