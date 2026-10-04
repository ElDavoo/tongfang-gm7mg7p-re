#!/usr/bin/env python3
"""What the 176 words at `0x0656` are, and the four `ljmp` tables they name
(issue #1144).

Stands in for the per-word classification in
`docs/findings/0656-directory-words.md`: that page says the `0x0656` span is a
directory of five `ljmp` tables plus 36 ordinary code addresses, and this suite
holds the YAML to saying so. `test_data_regions.py` guards the *contract* every
region shares -- vocabularies, refusals, half-open non-overlapping spans -- and
is deliberately not edited; what is here is specific to this one region and to
the four entries added beside it.

**The low-area class is named for what the sweep establishes, and no more.**
An earlier version of this file and of the write-up called these words "the
8051 vector block" while deriving the class from a linear sweep, which decides
framing and nothing about membership. `discover_vector_table()` decides
membership, and it contradicts four of the nineteen: it stops where code begins,
at `0x002E`, and those four lie past it. They are code addresses in the low
common area, not vectors, and `test_the_words_past_the_vector_block_are_code_addresses`
is the case that keeps the distinction from quietly eroding back.

**Every class below is re-derived from the image, not transcribed.** The
membership of "ljmp entry offset", "ljmp end offset" and "code address" is
computed by walking the tables the same way `data_regions.py`'s `ljmp-table`
decoder does, and the words are then partitioned against that. A hard-coded list
of 176 offsets would pass unchanged if the image changed under it, which is the
failure this file exists to prevent: the whole claim is a claim about bytes.

**No case here asserts a count of the tree.** Not how many regions the YAML
lists, not how many suites exist, not how many words fall in a class. The
counts that *are* asserted are counts over the committed firmware, which no
change to this repository can move, and they are the finding.

**The `0x01EC` regression is the reason this file exists.** Issue #1144 asked for
five new `ljmp` tables, one at `0x01EC`. `0x01EC` is the *fourth entry* of the
`0x01E3` table, so a region declared there overlaps it -- and the overlap is
the interesting half, because `data_regions.py --check` does **not** catch it:
that entry passes standalone, since the `ljmp-table` shape holds at `0x01EC` just
as it does at `0x01E3`. What rejects it is the non-overlap property
`test_data_regions.py` asserts over the whole list. So the case below asserts
the property directly and says which one it is, because a check that cannot
catch the mistake its own provenance is full of is not much of a check.
"""
import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).parent
EC = HERE.parent
REPO = EC.parent
TOOL = HERE / "data_regions.py"
REGIONS_YAML = EC / "annotations" / "data-regions.yaml"
FIRMWARE = EC / "firmware" / "GMxMGxx_11.800"
FINDINGS = REPO / "docs" / "findings" / "0656-directory-words.md"

spec = importlib.util.spec_from_file_location("data_regions", TOOL)
dr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dr)

spec = importlib.util.spec_from_file_location("disasm8051", HERE / "disasm8051.py")
d8051 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d8051)

# `build_ec_decompile.py` is imported for `discover_vector_table()` alone: the
# write-up's claim that these offsets are *vector* entries is settled by the
# repository's own walk, so importing it is what stops this suite from quietly
# re-deriving a private definition of the block that agrees with it by
# construction. The module needs no Ghidra to import.
sys.path.insert(0, str(HERE))
import build_ec_decompile as ec_decompile  # noqa: E402

# The directory region this suite is about, and the four `ljmp` tables it names
# that were not in the map before issue #1144. Named here rather than discovered
# by prefix so that a rename cannot silently empty the suite: a name that no
# longer resolves fails the lookup below, which is the point.
DIRECTORY = "common-0656-address-table"
NEW_TABLES = ("common-0035-ljmp-table", "common-0060-ljmp-table",
              "common-0126-ljmp-table", "common-01e3-ljmp-table")
# The pre-existing table the directory also indexes, so the "five tables"
# reading is checked against all five rather than against the four that moved.
EXISTING_TABLE = "common-032f-ljmp-table"

# The linear sweep the low-area class is derived from, and the wider one
# used to check the words it cannot reach. The narrow window stops at `0x47` by
# construction; the wide one clears the highest word it has to reach, `0x01FF`,
# with room to spare. See `low_area_words` for why the narrow window is the
# right one and why it is not simply made wider.
LOW_AREA_SWEEP_INSTRUCTIONS = 40
WIDE_SWEEP_INSTRUCTIONS = 700


def region_named(regions, name):
    """The one region called `name`, or a failure rather than a None.

    A `next(...)` default would let a rename make a case pass vacuously, which
    is the failure mode a suite written to hold a *narrative* is most prone to.
    """
    found = [r for r in regions if r["name"] == name]
    if len(found) != 1:
        raise AssertionError(
            f"expected exactly one region named {name!r}, found {len(found)}")
    return found[0]


class DirectoryTests(unittest.TestCase):
    """The classification, re-derived from the committed image."""

    @classmethod
    def setUpClass(cls):
        cls.d = FIRMWARE.read_bytes()
        cls.regions = dr.load()
        cls.dir_region = region_named(cls.regions, DIRECTORY)
        cls.lo = cls.dir_region["file_lo"]
        cls.hi = cls.dir_region["file_hi"]
        cls.words = [(cls.d[o] << 8) | cls.d[o + 1]
                     for o in range(cls.lo, cls.hi, cls.dir_region["stride"])]

    def entry_offsets(self, region):
        """Every entry offset of an `ljmp-table`, from the region's own span.

        Arithmetic over the YAML's declared extent, not a walk of the image --
        the walk is `test_each_new_table_walks_the_bytes_it_declares`, which
        asserts the extent agrees with the bytes before this is trusted. Kept
        separate so a disagreement fails the case that names the disagreement
        rather than surfacing as a mysterious change in the classification.
        """
        return set(range(region["file_lo"], region["file_hi"], region["stride"]))

    def test_the_directory_declares_what_its_bytes_hold(self):
        # The span, its stride and its count are `data_regions.py --check`'s
        # job and are asserted there. What is asserted here is that this suite
        # is reading the same span -- a suite pointed at the wrong region would
        # classify a different set of words and still pass every case below.
        self.assertEqual(self.hi - self.lo,
                         self.dir_region["stride"] * self.dir_region["entries"])
        self.assertEqual(len(self.words), self.dir_region["entries"])

    def test_the_five_named_regions_are_all_ljmp_tables(self):
        """The directory indexes five `ljmp` tables, and they are all that shape.

        The premise of block 1: "a directory of five `ljmp` tables" is a claim
        about five specific regions, so it is worth asserting that each of the
        five exists and carries the shape the reading depends on. An entry that
        changed shape would leave the classification below meaningless while
        every other case still passed.
        """
        for name in NEW_TABLES + (EXISTING_TABLE,):
            with self.subTest(table=name):
                self.assertEqual(region_named(self.regions, name)["shape"],
                                 "ljmp-table")

    def test_the_entry_offsets_and_end_offsets_are_what_they_are(self):
        """Block 1: the directory indexes the five tables' entry offsets.

        Each of the five is named by the directory -- otherwise "the directory
        indexes these tables" is a claim about nothing. Asserted as membership,
        which is the claim; the counts behind it are in the write-up.
        """
        for name in NEW_TABLES + (EXISTING_TABLE,):
            with self.subTest(table=name):
                table = region_named(self.regions, name)
                self.assertTrue(self.entry_offsets(table) <= set(self.words),
                                f"{name}'s entry offsets are not all in the "
                                f"directory, so the directory does not index it")
                self.assertIn(table["file_hi"], self.words,
                              f"{name}'s end offset is not a directory word")

    def test_01ec_is_an_entry_of_the_01e3_table_and_not_a_fifth_table(self):
        """The regression issue #1144 would otherwise have shipped.

        `0x01EC` is the fourth *entry* of `common-01e3-ljmp-table`, three bytes
        before that table's own end. A region declared there would overlap it,
        and -- the half worth naming -- `--check` accepts such a region
        standalone, because `ljmp-table` decoding holds at `0x01EC` just as it
        does at `0x01E3`. This case is the property that rejects it.
        """
        table = region_named(self.regions, "common-01e3-ljmp-table")
        self.assertIn(0x01EC, self.entry_offsets(table))
        self.assertLess(0x01EC, table["file_hi"])
        # And no listed region starts there, which is what "not a fifth table"
        # means in the map.
        self.assertFalse([r for r in self.regions if r["file_lo"] == 0x01EC],
                         "0x01EC is an entry offset of common-01e3-ljmp-table, "
                         "not a table boundary")

    def test_no_two_regions_overlap(self):
        """The half-open property, which is what rejects a mis-cut region.

        Held here as well as in `test_data_regions.py` because this is the
        suite that exists because of an overlap `--check` does not catch, and a
        reader should not have to know which sibling file carries the general
        case to learn why `0x01EC` is refused.
        """
        seen = sorted((r["file_lo"], r["file_hi"], r["name"])
                      for r in self.regions)
        for (a_lo, a_hi, a), (b_lo, b_hi, b) in zip(seen, seen[1:]):
            with self.subTest(pair=f"{a} / {b}"):
                self.assertLessEqual(a_hi, b_lo, f"{a} and {b} overlap")

    def test_the_word_at_file_hi_is_outside_the_common_area(self):
        """What stops the run, and why the edge is not a chosen boundary.

        The `addresses` shape claims a word below `0x8000`; the span ends
        because the next one is not that. If this ever stopped holding, the
        region would be declared short and `--check` would say so -- but the
        reason is worth a case of its own, since `file_hi` is also a named
        function's first byte and the two facts are independent.
        """
        self.assertGreaterEqual((self.d[self.hi] << 8) | self.d[self.hi + 1],
                                0x8000)

    def test_the_tail_words_name_a_ret_run_elsewhere(self):
        """Block 2's last class: offsets pointing at padding, not padding.

        The nine words `0x0526`-`0x052E` name a nine-byte `ret` run in the
        image. Neither half is the other: no word *in this region* is `0x2222`,
        and the run those words name is not inside the span. Issue #1144 read
        the target's bytes as the word's value; both directions of that are
        what this pins.
        """
        tail = [w for w in self.words if 0x0526 <= w <= 0x052E]
        self.assertTrue(tail, "the directory no longer names the 0x0526-0x052E run")
        self.assertNotIn(0x2222, self.words,
                         "a word in this region is 0x2222, so the run is "
                         "inside the span rather than named by it")
        for word in tail:
            with self.subTest(word=f"0x{word:04X}"):
                self.assertEqual(self.d[word], 0x22,
                                 f"0x{word:04X} does not name a ret")
                self.assertFalse(self.lo <= word < self.hi,
                                 f"0x{word:04X} is inside the directory span")

    def test_the_low_area_words_are_instruction_aligned(self):
        """Block 2's first class, and the correction that carries it.

        These name addresses in the low common area at `0x0000`. Issue #1144
        read them as "the address byte of `ljmp 0x11xx` instructions rather
        than an offset at all"; they are offsets, and each is the *start* of an
        instruction.

        **They are deliberately not called vector entries.** A linear sweep
        establishes framing, not membership of the vector table, and the two
        disagree: four of the write-up's nineteen lie past the `0x002E` end
        `discover_vector_table()` defines, so they are code addresses in the
        low area rather than vectors. `test_the_words_past_the_vector_block_are_code_addresses`
        holds that half.

        Checked against a linear sweep of the low area rather than against a
        hard-coded list, so the claim is re-derived: `decode()` is walked from
        `0x0000` and the words are required to be among the offsets it reaches.
        A sweep is evidence about framing rather than proof of it --
        `disasm8051.py` says so itself -- but a word landing *mid*-instruction
        under a sweep that starts at the area's first byte is a real signal,
        and the alternative (asserting the byte is `0x02` or `0x22`) would pass
        on a word sitting one byte into an unrelated instruction.

        The class is bounded by the sweep rather than by a threshold, because a
        numeric cutoff would sweep in the routine words at `0x0114` and
        `0x018C`, which are in this region on purpose and are code, not low-area
        vector padding. The window's own reach is why two of the write-up's
        nineteen are checked by `test_the_words_the_sweep_window_does_not_reach`
        instead.
        """
        low = self.low_area_words()
        self.assertTrue(low,
                        "no directory word names the low common area, so the "
                        "reading this suite exists to check has lost its "
                        "subject")
        boundaries = {off for off, _, _ in
                      d8051.decode(self.d, 0x0000, LOW_AREA_SWEEP_INSTRUCTIONS)}
        for word in sorted(low):
            with self.subTest(word=f"0x{word:04X}"):
                self.assertIn(word, boundaries,
                              f"0x{word:04X} is not an instruction boundary "
                              f"under a linear sweep of the low area, so "
                              f"it is not the start of an instruction")
                self.assertIn(self.d[word], (0x02, 0x22),
                              f"0x{word:04X} holds neither an ljmp nor a ret, "
                              f"so the low-area reading does not hold for it")

    def test_the_words_past_the_vector_block_are_code_addresses(self):
        """Not all of them are vector entries, and this is what says so.

        `discover_vector_table()` walks this image's vector table and stops
        where code begins -- `build_ec_decompile.py`'s own self-test pins that
        end at `0x002E`, not the `0x0040` a textbook layout would suggest --
        returning sixteen entries, the last at `0x2B`. Four of the write-up's
        nineteen instruction starts lie past that end and are ordinary code
        addresses. Calling the whole class "the vector block" contradicted a
        committed tool and a committed self-test assertion, which is what this
        case now holds.

        Asserted against the walk rather than transcribed, so the correction
        holds if the image changes. The class partitions three ways, and all
        three parts are required to be non-empty: the walk's own entries, the
        `ret` bytes the walk steps over between them (Keil pads a 3-byte LJMP
        to 4), and the words past the block's end. The last is the point -- it
        is what a "vector entries" label would have denied.
        """
        block = ec_decompile.discover_vector_table(self.d)
        block_end = block[-1][0]
        vector_entries = {off for off, _ in block}
        # The write-up's two classes, taken together: the narrow window's class
        # and the words that window cannot reach. Neither is separately called a
        # vector entry -- both are checked against the walk here.
        members = self.low_area_words() | self.low_area_words_the_window_misses()
        entries = {w for w in members if w in vector_entries}
        padding = {w for w in members if w <= block_end and w not in vector_entries}
        past = {w for w in members if w > block_end}
        self.assertTrue(entries, "no low-area word is a vector entry")
        self.assertTrue(padding,
                        "no low-area word is the walk's inter-entry padding, so "
                        "the class no longer holds the whole block")
        self.assertTrue(past,
                        "no low-area word lies past the vector block's end, so "
                        "the class may be described as vector entries after all")
        self.assertEqual(entries | padding | past, members,
                         "the class does not partition against the walk")

    def low_area_words_the_window_misses(self):
        """The words `low_area_words` cannot see, with the same derivation.

        Factored out of `test_the_words_the_sweep_window_does_not_reach` so the
        vector-block case can hold the *whole* class -- the sweep window is an
        artifact of which class is being checked, not a fact about the words.
        """
        narrow = {off for off, _, _ in
                  d8051.decode(self.d, 0x0000, LOW_AREA_SWEEP_INSTRUCTIONS)}
        entries, _ = self.table_offsets()
        return {w for w in self.words
                if w not in narrow and w not in entries
                and self.d[w] == 0x22 and self.d[w + 1] != 0x22}

    def low_area_words(self):
        """The directory words naming the low common area, re-derived.

        A word belongs here when a linear sweep of `0x0000` reaches it as an
        instruction start. That is the same property the case above asserts,
        used here as the *definition* of the class so the two cannot disagree
        by construction; what the case adds is the check that each such word is
        a genuine `ljmp` or `ret`, and that the class is not empty.

        **The window is `LOW_AREA_SWEEP_INSTRUCTIONS`, and it is not widened.**
        40 instructions reach only `0x47`, so two of the nineteen words the
        write-up lists -- `0x006F` and `0x01FF` -- fall outside it and are
        excluded here as *not reached*. That is why this class has sixteen
        members rather than nineteen. Widening is not the fix: a
        200-instruction sweep reaches `0x15A` and so also swallows `0x0114`,
        which is a `mov dptr` routine address in this region on purpose, and
        that word fails `test_the_low_area_words_are_instruction_aligned`'s own
        `0x02`/`0x22` check while silently becoming a "low-area offset".

        The two words the window misses are therefore checked on their own, by
        `test_the_words_the_sweep_window_does_not_reach`, so every word the
        write-up claims is an instruction start is actually asserted to be one.
        """
        sweep = {off for off, _, _ in
                 d8051.decode(self.d, 0x0000, LOW_AREA_SWEEP_INSTRUCTIONS)}
        entries, ends = self.table_offsets()
        return {w for w in self.words
                if w in sweep and w not in entries and w not in ends}

    def test_the_words_the_sweep_window_does_not_reach(self):
        """The words the class's own sweep window cannot see.

        `low_area_words` reaches only `0x47`, so `0x006F` and `0x01FF` are
        not in the low-area class and no case above checks them -- while the
        write-up claims all nineteen are instruction starts. This is the case
        that holds that half of the claim, against a wider sweep.

        Derived rather than transcribed; see
        `low_area_words_the_window_misses`. The gap is taken as the directory
        words the narrow window does not reach that hold a `ret` **and are not
        part of a `ret` run** -- a run is the `0x0526`-`0x052E` class the other
        case already claims, distinguished here by `d[w + 1] != 0x22` rather than
        by name. `ret` is a one-byte opcode, so every byte of a run is itself an
        instruction start; the run words are excluded because they belong to
        another documented class, not because they fail the sweep.
        """
        wide = {off for off, _, _ in
                d8051.decode(self.d, 0x0000, WIDE_SWEEP_INSTRUCTIONS)}
        missed = self.low_area_words_the_window_misses()
        self.assertTrue(missed,
                        "no word is outside the sweep window any more, so this "
                        "case is no longer covering the words the low-area "
                        "class cannot see")
        for word in sorted(missed):
            with self.subTest(word=f"0x{word:04X}"):
                self.assertIn(word, wide,
                              f"0x{word:04X} is outside even the wider sweep, "
                              f"so it is not the start of an instruction")

    def table_offsets(self):
        """(entry offsets, end offsets) across the five tables, re-derived."""
        entries, ends = set(), set()
        for name in NEW_TABLES + (EXISTING_TABLE,):
            t = region_named(self.regions, name)
            entries |= self.entry_offsets(t)
            ends.add(t["file_hi"])
        return entries, ends

    def test_the_routine_words_are_code_not_table_offsets(self):
        """Block 2's middle class: what is left is not on any table's grid.

        Defined as the remainder after the table offsets, the end offsets and
        the low-area words are removed, so the case states the write-up's
        claim about the *remainder* rather than transcribing which addresses
        are in it.

        The assertion is **not** that these addresses do not begin with `0x02`.
        `0x04B4` does -- it is `ljmp 0x14C2`, a routine whose first instruction
        is a jump, which is the one member of this class a naive "no ljmp
        opcodes here" check rejects. Issue #1144 hit exactly that and read it as
        `mov dptr,#0x1150`. What makes a word a table offset is its position on
        a table's stride grid, not the byte that happens to sit there, so that
        is what is checked: none of the remainder is entry-aligned in any of the
        five tables.
        """
        entries, ends = self.table_offsets()
        low = self.low_area_words()
        routine = sorted(set(self.words) - entries - ends - low)
        self.assertTrue(routine,
                        "the directory's code addresses are gone, so the "
                        "remainder the write-up describes is empty")
        grids = {}
        for name in NEW_TABLES + (EXISTING_TABLE,):
            t = region_named(self.regions, name)
            grids[name] = (t["file_lo"], t["file_hi"], t["stride"])
        for word in routine:
            # Scoped to the table's own span. A stride is a period, so a word
            # far outside a table can still be congruent to its grid -- 0x052E
            # is 0 mod 3 from three of these file_lo values -- and calling that
            # "entry-aligned" would be arithmetic about numbers that have
            # nothing to do with each other.
            aligned = [n for n, (lo, hi, stride) in grids.items()
                       if lo <= word < hi and (word - lo) % stride == 0]
            with self.subTest(word=f"0x{word:04X}"):
                self.assertFalse(aligned,
                                 f"0x{word:04X} is entry-aligned in "
                                 f"{aligned}, so it reads as a table offset")

    def test_the_classes_partition_the_span(self):
        """The partition itself, once each class has been re-derived.

        Four classes: block 1's two, and block 2's two. Kept separate from the
        per-class cases because it is the property that actually matters about a
        classification in prose -- a word claimed twice makes the narrative
        ambiguous about it, and a word claimed by none means the narrative does
        not describe the span. Both are silent in a write-up and loud here.

        Note that `ljmp entry offset` and `ljmp end offset` are checked
        independently rather than as one class, because `0x003E` and `0x006F`
        are both low-area instruction starts and end offsets, and `0x012F` is
        both a routine address and an end offset; the write-up says which side
        counts each of them.
        """
        entries, ends = self.table_offsets()
        low = self.low_area_words()
        routine = set(self.words) - entries - ends - low
        for word in self.words:
            classes = [n for n, s in (("ljmp entry offset", word in entries),
                                      ("ljmp end offset", word in ends),
                                      ("low-area instruction start", word in low),
                                      ("code address", word in routine)) if s]
            with self.subTest(word=f"0x{word:04X}"):
                self.assertEqual(len(classes), 1,
                                 f"0x{word:04X} is {classes}; each word must "
                                 f"fall into exactly one documented class")
        for name, members in (("ljmp entry offsets", entries),
                              ("ljmp end offsets", ends),
                              ("low-area instruction starts", low),
                              ("code addresses", routine)):
            self.assertTrue(members, f"the {name} class is empty")


class EstablishedByTests(unittest.TestCase):
    """Each new entry's `established_by` pastes and prints its own numbers.

    `test_data_regions.py` already runs every region's command. This repeats it
    for the four new entries and additionally checks the thing that suite's
    general case cannot: that the walk it names is *this* table's, seeded at its
    own `file_lo`. Seeding a `0x032F`-style walk at a later offset still stops
    in the right place, so the seed is the load-bearing half.
    """

    def setUp(self):
        self.regions = dr.load()

    def command_payload(self, established_by: str) -> str:
        """The `python3 -c` body, lifted out of the field's prose."""
        marker = 'python3 -c "'
        start = established_by.index(marker) + len(marker)
        end = established_by.index('"', start)
        return established_by[start:end]

    def test_each_new_table_re_derives_its_own_extent(self):
        d = FIRMWARE.read_bytes()
        for name in NEW_TABLES:
            with self.subTest(table=name):
                r = region_named(self.regions, name)
                payload = self.command_payload(r["established_by"])
                # The seed is pinned to this entry's own file_lo, not merely to
                # a file_lo: an in-run seed walks a shorter span and still
                # prints an end this entry would accept.
                self.assertIn(f"o=0x{r['file_lo']:x}", payload,
                              "the walk is not seeded at this entry's own "
                              "file_lo, so it re-derives a different span")
                run = subprocess.run([sys.executable, "-c", payload],
                                     cwd=REPO, capture_output=True, text=True)
                self.assertEqual(run.returncode, 0,
                                 f"established_by does not run: "
                                 f"{run.stderr.strip()}\n  command: {payload}")
                end, count = run.stdout.split()
                self.assertEqual(int(end, 16), r["file_hi"])
                self.assertEqual(int(count), r["entries"])

    def test_each_new_table_walks_the_bytes_it_declares(self):
        """The extent is re-derived from the image, not read off the YAML."""
        d = FIRMWARE.read_bytes()
        for name in NEW_TABLES:
            with self.subTest(table=name):
                r = region_named(self.regions, name)
                o = r["file_lo"]
                while d[o] == 0x02:
                    o += r["stride"]
                self.assertEqual(o, r["file_hi"],
                                 f"{name}: the ljmp run does not stop where "
                                 f"the entry says it does")
                self.assertEqual((o - r["file_lo"]) // r["stride"],
                                 r["entries"])

    def test_the_established_by_blocks_stay_literal(self):
        """A folded block is a `SyntaxError` on paste that still looks right.

        The YAML header warns about this and `test_data_regions.py` catches it
        by running the payload; this asserts the shape directly so the failure
        names the cause rather than arriving as a `SyntaxError` from a
        subprocess. `|-` keeps newlines; `>` would join them with spaces and put
        the `while` clause on the `print`'s line.
        """
        for name in NEW_TABLES:
            with self.subTest(table=name):
                r = region_named(self.regions, name)
                self.assertIn("\n", r["established_by"].rstrip("\n"),
                              "established_by is a single line, so it is a "
                              "folded block")


class WriteUpTests(unittest.TestCase):
    """The page exists and the claims it anchors resolve.

    A write-up citing a path that is not there is a claim with nothing behind
    it, which is the rule `data_regions.py`'s loader enforces on `evidence:`
    from the other side. The path is the only thing checked -- what the page
    says is measured by re-running its commands, not by reading it.
    """

    def test_the_findings_page_is_the_evidence_for_the_new_entries(self):
        self.assertTrue(FINDINGS.exists(),
                        f"the write-up the new entries cite is missing: "
                        f"{FINDINGS}")
        for name in NEW_TABLES:
            with self.subTest(table=name):
                r = region_named(dr.load(), name)
                for path in (p.strip() for p in r["evidence"].split(";")):
                    self.assertTrue((REPO / path).exists(),
                                    f"evidence path does not resolve: {path}")

    def test_the_directory_entry_cites_the_write_up(self):
        r = region_named(dr.load(), DIRECTORY)
        paths = [p.strip() for p in r["evidence"].split(";")]
        self.assertIn("docs/findings/0656-directory-words.md", paths,
                      "the directory entry no longer cites the page that "
                      "classifies its words")


if __name__ == "__main__":
    unittest.main()
