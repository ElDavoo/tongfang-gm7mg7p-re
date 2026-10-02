#!/usr/bin/env python3
"""The pure functions of `code_pointer_sites.py`, and what the tool refuses.

`--self-test` holds the tool's own known answers against oracles outside it --
`annotations/static-refs-audit.md` §5.1 and the committed
`annotations/code-pointer-sites.csv`. This file is the other half, and it is
the half that survives the tool changing: §5.1's aggregate and the CSV are
both regenerable, so an agreement between them is an agreement about today's
tree and not a statement about whether the scan is right.

So the classification cases here are built on scratch bytes, not read out of
the firmware. A fixture at a real address keeps testing what it was written to
test only until those bytes change, and the reason this suite is worth having
is precisely that the committed list is going to be re-derived; see
`test_relative_edge_guard.py` for the same argument about the same problem.
Each fixture is a `common`-region buffer, where the file offset is the runtime
address, so an offset in a case can be read as an address.

**The bucket mapping is the load-bearing case.** A hit means *this address has
at least one CODE-pointer site* and nothing more, so the question a reader of
this tool actually has is which of `register_ref_table`'s classes count and
which do not. Five of the seven are ordinary XDATA stories and none of them may
reach the list, and `TheBucketMapping` plants one of each and asks two separate
questions -- which bucket does the window classify to, and does that bucket
reach the list. A scan that quietly widened to "every `MOV DPTR` site" answers
the first correctly for all seven and fails the second for five.

**What this file deliberately does not assert.** No count of
`registers.yaml`, and none of the repository's own text. The pre-flight answer
is a property of the tree -- which of its addresses are on the list, and today
that is none of them -- and that population changes at nearly every landing
edit, so a figure for it here would be a value every other branch has to move.
The figures that *are* asserted are the ones fixed by the image or by the
vocabulary: the class each opcode decodes to, the column order, the shape of
the two headline figures.
"""
import ast
import builtins
import contextlib
import csv
import importlib.util
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
import warnings
from unittest import mock

HERE = Path(__file__).parent
EC = HERE.parent
TOOL = HERE / "code_pointer_sites.py"
# code_pointer_sites imports register_ref_table, data_regions and
# trace_xdata_refs by bare module name, the way inc_dptr_sites.py imports the
# first two, so the tool directory has to be on the path before it is loaded
# rather than after.
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location("code_pointer_sites", TOOL)
cps = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cps)
import register_ref_table as rrt  # noqa: E402
import trace_xdata_refs as tref  # noqa: E402

FIRMWARE = str(EC / "firmware" / "GMxMGxx_11.800")
SITES_CSV = str(EC / "annotations" / "code-pointer-sites.csv")
REGISTERS_YAML = str(EC / "annotations" / "registers.yaml")

# The two files every other claim in the tool is keyed to. `main()` has to come
# back from every mode with both of these byte-identical: the CSV is the
# committed list, and `registers.yaml` is the file the pre-flight mode reads to
# answer the question #29 and #30 will ask. A tool that could write either would
# be able to make its own check green.
UNTOUCHABLE = (SITES_CSV, REGISTERS_YAML)

# `register_ref_table.CLASSES`, transcribed as a mapping from a class label to
# the opcodes that decode to it. Transcribed rather than imported so that a
# *rename* in that file is a red run here and not a silent agreement between
# two files reading the same constant; `TheBucketMapping` also asserts the
# transcription is complete, so a class *added* there is caught too.
VOCABULARY = {
    "read": (0xE0,),                             # movx a,@dptr
    "write": (0xF0,),                            # movx @dptr,a
    "read+write": (0xE0, 0xF0),
    "handed to lcall/ljmp (unresolved)": (0x12, 0x01, 0x20),  # lcall 0x0120
    "no movx in window": (),                    # nothing follows the MOV DPTR
    "movc (CODE pointer)": (0x93,),              # movc a,@a+dptr
    "jmp @a+dptr": (0x73,),                      # jmp @a+dptr
}
# The two of the seven the list is for, spelled out rather than derived from
# `cps.CODE_CLASSES` -- the point of the comparison is what this tool reaches
# for, and a check written against the constant it is checking proves nothing.
CODE_POINTER_LABELS = ("movc (CODE pointer)", "jmp @a+dptr")

# The opcodes, spelled, so a fixture reads as the instruction sequence it is.
# `bytes.ljust`/`rjust` take a one-byte *string* and not an int, so the padding
# is spelled separately from the opcode it is; both are `0x00`, which decodes
# as `nop` and so shifts no offset in a walk that runs past it.
PAD = bytes((0x00,))


def mov_dptr(addr: int) -> bytes:
    """`MOV DPTR,#addr`, the three-byte site the scan is looking for."""
    return bytes((tref.MOV_DPTR, addr >> 8, addr & 0xFF))


def scratch_at(base: int, *chunks) -> bytes:
    """A `common`-region buffer whose first chunk sits at file offset `base`.

    `common` rather than a bank, so the file offset and the runtime address
    are the same number and a case that names an offset means something. The
    regions themselves come from `trace_xdata_refs.REGIONS` where a case needs
    one, rather than from a number written here, so a change to the image map
    moves the fixture with it instead of leaving it testing a region the tool
    no longer has.
    """
    return bytes(base) + b"".join(chunks).ljust(0x40, PAD)


def scan_at(base: int, *chunks) -> list:
    """`code_pointer_sites()` over a scratch buffer."""
    return cps.code_pointer_sites(scratch_at(base, *chunks), pd_verified=True)


def region_row(name: str):
    """`(file_lo, file_hi, runtime_base)` for one row of REGIONS.

    `REGIONS` rows are `(name, file_lo, file_hi, runtime_base, how_to_build_it)`;
    the `how` is documentation for a human and is dropped here.
    """
    (_name, lo, hi, base, _how), = (r for r in tref.REGIONS if r[0] == name)
    return lo, hi, base


class TheBucketMapping(unittest.TestCase):
    """Which of `register_ref_table`'s classes reach the list, and which do not.

    Built on scratch bytes because the claim is about the mapping and not about
    the image. All seven fixtures go into one buffer, so each case below is a
    statement about the whole vocabulary rather than about seven separate scans
    that each happened to be right.
    """

    BASE = 0x1000

    # Where each fixture's site sits. A file offset inside `common`, so the
    # offset and the runtime address are the same number and `walk()` is handed
    # the one number both columns would show.
    SITE = 0x5000

    def buckets(self) -> dict:
        """{class label: the bucket its own fixture's window decodes to}.

        The composition `code_pointer_sites()` performs at every `0x90` --
        `bucket(classify(walk(...)))` -- written out once here so the seven
        opcodes can be asked about one at a time. It is a restatement of one
        expression rather than a second implementation, and the case below
        that runs the real scan over all seven in one buffer is what holds the
        two together.
        """
        out = {}
        for label, ops in VOCABULARY.items():
            image = scratch_at(self.SITE, mov_dptr(self.SITE) + bytes(ops))
            out[label] = cps.bucket(tref.classify(tref.walk(image, self.SITE)))
        return out

    def test_the_transcribed_vocabulary_is_the_whole_of_classes(self):
        # The case that makes the rest of this class mean something. Without
        # it a class added to `register_ref_table` would simply be absent from
        # every fixture below and the suite would stay green.
        self.assertEqual(set(VOCABULARY), {label for label, _ in rrt.CLASSES})

    def test_each_class_is_reached_by_the_opcode_that_implies_it(self):
        self.assertEqual(self.buckets(),
                         {label: label for label in VOCABULARY})

    def test_only_the_two_code_pointer_classes_reach_the_list(self):
        listed = {label for _o, _a, label, _r, _rt, _w
                  in scan_at(self.BASE, *(mov_dptr(self.BASE + n)
                                           + bytes(ops) for n, ops
                                           in enumerate(VOCABULARY.values())))}
        self.assertEqual(listed, set(CODE_POINTER_LABELS))

    def test_the_five_other_classes_are_not_code_pointer_classes(self):
        for label in VOCABULARY:
            with self.subTest(access=label):
                self.assertEqual(label in cps.CODE_CLASSES,
                                 label in CODE_POINTER_LABELS)

    def test_the_two_classes_are_looked_up_in_the_shared_vocabulary(self):
        # A rename in `register_ref_table` moves this tool with it rather than
        # leaving it filtering on a name nothing produces -- which would be a
        # scan that had quietly started finding nothing and looked exactly
        # like a scan that was working.
        self.assertEqual(cps.CODE_CLASSES,
                         tuple(label for label, _ in rrt.CLASSES
                               if _ in cps.CODE_POINTER_COLUMNS))

    def test_a_column_name_the_vocabulary_lacks_is_refused(self):
        with self.assertRaises(SystemExit):
            cps.column_label("table")


class SiteColumns(unittest.TestCase):
    """What one row carries, on scratch bytes.

    The columns are the tool's contract with a reader about to paste a site
    into r2: the address is the number to ask about, the file offset and the
    runtime address are two different numbers for the same byte, and the window
    is what the class can be checked against by hand.
    """

    def test_the_window_is_the_decoded_opcodes_after_the_sites_own_mov(self):
        # The site's own `MOV DPTR` is not in the window, because it is what
        # the `addr` column already names; a window that repeated it would make
        # every row's decode start from a byte the reader can see. What follows
        # it is only the `movc` -- `scratch_at()` pads the rest of the buffer
        # with `nop`, which is what keeps the trailing bytes from turning this
        # fixture into something else.
        # `ret` is a flow opcode and is the *last* instruction `walk()` decodes
        # rather than the one it stops before, so the cell carries it. That is
        # the window's own convention and `ec-0x07d0-sites.csv` is full of rows
        # ending `; ret`; what this case pins is that the site's own `MOV DPTR`
        # is not one of them.
        (_o, _a, _c, _r, _rt, window), = scan_at(
            0x2000, mov_dptr(0x2000) + bytes((0x93, 0x22)))
        self.assertEqual(window, "movc a,@a+dptr ; ret")

    def test_a_common_offset_is_its_own_runtime_address(self):
        # The two columns agreeing is the point, not an accident: a reader who
        # has only ever seen them agree has no way to tell a column that was
        # never derived from the map. The bank case below is where they part.
        (_o, _a, _c, region, runtime, _w), = scan_at(
            0x2000, mov_dptr(0x2000) + bytes((0x93,)))
        self.assertEqual(region, "common")
        self.assertEqual(runtime, 0x2000)

    def test_a_bank_offset_is_reported_against_the_bank_runtime_base(self):
        # bank0 is file 0x08000 at runtime base 0x8000, so the same byte is two
        # different numbers. Both come from `trace_xdata_refs.REGIONS` rather
        # than from literals, for the reason `scratch_at()` gives.
        lo, _hi, base = region_row("bank0")
        (_o, _a, _c, region, runtime, _w), = cps.code_pointer_sites(
            scratch_at(lo, mov_dptr(0x9000) + bytes((0x93,))), pd_verified=True)
        self.assertEqual(region, "bank0")
        self.assertEqual(runtime, base + lo - lo)

    def test_a_site_outside_every_mapped_region_is_kept_not_dropped(self):
        # A region the map does not cover leaves the site with no runtime
        # address, and it is still a row: dropping it would make the count a
        # count over the mapped regions only, which reads as a scan of the
        # image. The pair of columns is what says so per row, and a site with
        # no runtime address is also a site a reader cannot cross-read in r2.
        #
        # `REGIONS[-1][2]` is the end of the last mapped region, read off the
        # table rather than written out, so this case follows the image map
        # instead of pinning one number from it. The buffer is the whole file's
        # worth of padding, which is a 256 KiB scan of mostly `0x00` and costs
        # a few tens of milliseconds.
        past = tref.REGIONS[-1][2]
        sites = cps.code_pointer_sites(
            scratch_at(past, mov_dptr(0x1234) + bytes((0x93, 0x22))),
            pd_verified=True)
        self.assertEqual([(r, rt) for _o, _a, _c, r, rt, _w in sites],
                         [(cps.UNMAPPED, None)])


class TheTwoHeadlineFigures(unittest.TestCase):
    """"54 sites" and "48 addresses" are different numbers, and stay different.

    `repeated()` is what stops the report reading them as a contradiction, so
    the relation between them is the property worth holding: the two figures
    differ by exactly the extra sites on the addresses that carry more than
    one, and neither is obtained from the other by a subtraction that could go
    quietly wrong.
    """

    def setUp(self):
        self.sites = scan_at(
            0x3000,
            mov_dptr(0x3000) + bytes((0x93,)),
            mov_dptr(0x3000) + bytes((0x73,)),
            mov_dptr(0x3000) + bytes((0x93,)),
            mov_dptr(0x3001) + bytes((0x93,)),
            mov_dptr(0x3001) + bytes((0x93,)),
            mov_dptr(0x3002) + bytes((0x93,)),
        )
        self.addrs = {addr for _, addr, _, _, _, _ in self.sites}

    def test_repeated_names_only_the_addresses_with_more_than_one_site(self):
        self.assertEqual(cps.repeated(self.sites), {0x3000: 3, 0x3001: 2})

    def test_a_single_site_address_is_not_reported_as_repeated(self):
        self.assertNotIn(0x3002, cps.repeated(self.sites))

    def test_the_two_figures_differ_only_by_the_repeated_addresses(self):
        extra = sum(n - 1 for n in cps.repeated(self.sites).values())
        self.assertEqual(len(self.sites) - len(self.addrs), extra)
        self.assertNotEqual(len(self.sites), len(self.addrs))


class TheCsvTable(unittest.TestCase):
    """Column order, one row per site, and the `--check` diff path.

    The column order is a promise to whatever reads the committed file with a
    `cut`, so it is asserted as a list and not as a substring: a column added
    in the middle changes both the order and the row width, and a substring
    check would only notice the first.
    """

    def setUp(self):
        self.sites = scan_at(
            0x4000,
            mov_dptr(0x4000) + bytes((0x93,)),
            mov_dptr(0x4000) + bytes((0x73,)),
            mov_dptr(0x4001) + bytes((0xE0,)),
        )
        self.table = cps.csv_table(self.sites)

    def rows(self) -> list:
        return list(csv.DictReader(io.StringIO(self.table)))

    def test_the_header_is_the_committed_column_order(self):
        self.assertEqual(next(csv.reader(io.StringIO(self.table))),
                         cps.CSV_COLUMNS)
        self.assertEqual(cps.CSV_COLUMNS,
                         ["addr", "file_offset", "region", "runtime",
                          "class", "window"])

    def test_the_committed_table_has_those_columns(self):
        with open(SITES_CSV, newline="") as f:
            self.assertEqual(next(csv.reader(f)), cps.CSV_COLUMNS)

    def test_one_row_per_site_and_not_per_address(self):
        rows = self.rows()
        self.assertEqual([r["addr"] for r in rows], ["0x4000", "0x4000"])
        self.assertEqual([r["class"] for r in rows], list(CODE_POINTER_LABELS))

    def test_a_non_code_pointer_site_is_not_a_row(self):
        self.assertNotIn("0x4001", self.table)

    def test_the_rows_are_in_file_offset_order(self):
        offsets = [r["file_offset"] for r in self.rows()]
        self.assertEqual(offsets, sorted(offsets))

    def test_the_table_carries_crlf_terminators(self):
        # `trace_xdata_refs.check_table()`'s own note: the committed tables
        # carry the csv module's terminator, and `--check` reads with
        # `newline=""` so the two compare as bytes. A writer that normalised to
        # LF would make every committed table red on every run, which is worse
        # than having no check.
        self.assertIn("\r\n", self.table)

    def test_check_accepts_the_table_this_run_produces(self):
        with scratch_file(self.table) as path:
            self.assertEqual(self.verdict(self.table, path), 0)

    def test_check_rejects_a_table_this_run_cannot_reproduce(self):
        with scratch_file(self.table) as path:
            self.assertNotEqual(
                self.verdict(self.table.replace("0x4000", "0x4009", 1), path), 0)

    def test_check_reports_a_path_that_does_not_exist(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertNotEqual(
                self.verdict(self.table, os.path.join(tmp, "absent.csv")), 0)

    @staticmethod
    def verdict(generated: str, path: str) -> int:
        """`check_table()`'s exit code, with its own output off the test log.

        Both streams, and both deliberately: the pass line goes to stdout and
        the diff to stderr, and either one printed from a suite is the tool
        talking to a reader who is looking for a test failure. The messages
        belong to whoever runs `--check`.
        """
        with contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()):
            return cps.check_table(generated, path)


class AgainstRegisters(unittest.TestCase):
    """The pre-flight answer, and the two ways it can be wrong.

    The whole-file question -- which addresses `registers.yaml` carries are on
    this list -- is asserted as a property (today, none of them) and never as a
    count of the file, because that population changes at almost every landing
    edit and a figure here would be one every other branch has to move.
    """

    SITES = None

    @classmethod
    def setUpClass(cls):
        with open(FIRMWARE, "rb") as f:
            cls.SITES = cps.code_pointer_sites(f.read(), True)

    def on_list(self) -> set:
        return {addr for _, addr, _, _, _, _ in self.SITES}

    def test_no_address_in_registers_yaml_is_on_the_list(self):
        overlap = self.on_list() & cps.registers_addrs()
        self.assertEqual([f"0x{a:04X}" for a in sorted(overlap)], [])

    def test_a_known_table_address_is_found_and_an_xdata_control_is_not(self):
        # 0x63BE is §5.1's worked example and is on the list; 0x0741 is one of
        # its two `movx` controls and is not. The pair is the calibration in
        # one assertion -- the list is a flag on an address, not a verdict on
        # one, and a real register access and a table read are told apart.
        self.assertIn(0x63BE, self.on_list())
        self.assertNotIn(0x0741, self.on_list())

    def test_a_pair_entry_contributes_both_its_addresses(self):
        # `addr` is a list for a pair and a scalar otherwise, and the question
        # is per number: a loader that took only the low half would leave the
        # high half unchecked and would report it as "no CODE-pointer site",
        # which reads as a clearance. The `status:` here is deliberately
        # `absent`, which is the point -- the loader reads addresses and
        # nothing else, and does not return a verdict about them.
        with scratch_file(b"registers:\n"
                          b"- {name: PAIR, addr: [0x63be, 0x63bf], status: absent}\n"
                          b"- {name: ONE, addr: 0x63c0, status: absent}\n") as path:
            addrs = cps.registers_addrs(path)
        self.assertEqual(addrs, {0x63BE, 0x63BF, 0x63C0})

    def test_the_report_names_an_address_that_is_on_the_list(self):
        out = capture_main(FIRMWARE, "--against-registers", "0x63BE")
        self.assertIn("0x63BE", out)
        self.assertIn("ON THE LIST", out)
        # Once in the per-address answer and once per site in the detail below
        # it, which is the "a site is not an address" point made on the row.
        self.assertEqual(out.count("0x63BE"),
                         1 + cps.repeated(self.SITES)[0x63BE])

    def test_the_whole_file_run_says_nothing_is_on_the_list(self):
        out = capture_main(FIRMWARE, "--against-registers")
        self.assertIn("on the CODE-pointer list", out)
        self.assertIn("none.", out)
        # The caveat is the answer's load-bearing half. An empty intersection
        # is a statement about this method over this image, and a report that
        # dropped the sentence would let a reader take it for more.
        self.assertIn("is not on the list and", out)

    def test_a_clean_run_exits_zero(self):
        # Deliberately not the other way round. A non-empty intersection is a
        # fact about an address and not a failure of the tool, and the whole
        # point of the mode is to print the sites behind one, so making it
        # non-zero would make it usable in a gate in a way nothing authorises.
        code, _out, _err = run_main(FIRMWARE, "--against-registers", "0x63BE")
        self.assertEqual(code, 0)


class NoWrites(unittest.TestCase):
    """No mode opens a repository file for writing.

    The tripwire rather than a before/after comparison, for the reason
    `test_inc_dptr_sites.py` gives: "the committed files are unchanged" is also
    satisfied by a run that wrote identical bytes, and the property worth
    holding is that this tool cannot write at all. Every mode runs under it --
    `--csv`, `--check`, the default report and `--against-registers` -- because
    a tool that could rewrite the table it checks would be able to make its own
    check green.
    """

    def refuse(self, image, *argv):
        attempted = []
        real_open = builtins.open

        def tripwire(file, mode="r", *a, **kw):
            if any(m in str(mode) for m in "wxa+"):
                attempted.append((str(file), str(mode)))
                raise AssertionError(
                    f"code_pointer_sites.py opened {file!r} for writing (mode "
                    f"{mode!r}); the tool writes stdout and nothing else")
            return real_open(file, mode, *a, **kw)

        before = {p: Path(p).read_bytes() for p in UNTOUCHABLE}
        with mock.patch.object(builtins, "open", tripwire):
            code, out, err = run_main(image, *argv)
        self.assertEqual(code, 0, err)
        self.assertEqual(attempted, [],
                         f"`{' '.join(argv)}` opened a file for writing")
        self.assertEqual({p: Path(p).read_bytes() for p in UNTOUCHABLE}, before,
                         f"`{' '.join(argv)}` changed a committed file")
        return out, err

    def test_the_csv_mode_writes_only_to_stdout(self):
        out, _err = self.refuse(FIRMWARE, "--csv")
        self.assertTrue(out.startswith("addr,file_offset,region,runtime,class,"))

    def test_the_check_mode_writes_nothing(self):
        self.refuse(FIRMWARE, "--check")

    def test_the_report_mode_writes_nothing(self):
        out, _err = self.refuse(FIRMWARE)
        self.assertIn("CODE-pointer site(s) across", out)

    def test_the_pre_flight_mode_writes_nothing(self):
        out, _err = self.refuse(FIRMWARE, "--against-registers", "0x63BE")
        self.assertIn("ON THE LIST", out)

    def test_an_unidentified_pd_image_refuses_rather_than_reporting_zeroes(self):
        # Without the marker `region_of()` calls the 0x20000 region `unknown`,
        # so the per-region split would lose its `pd-image` row and report a
        # smaller scan that looks like a measurement. The refusal is the same
        # one `inc_dptr_sites.py` makes and it is the same claim, so it is the
        # same rule -- with the difference that here it is a headline number.
        with open(FIRMWARE, "rb") as f:
            blank = bytes(len(f.read()))
        with scratch_file(blank) as path:
            before = {p: Path(p).read_bytes() for p in UNTOUCHABLE}
            with warnings.catch_warnings():
                # The tool opens the image without a `with`, the way every
                # other tool in this directory does; on the refusal path the
                # handle is still uncollected when the interpreter gets here,
                # and the ResourceWarning would land in the captured stderr the
                # assertion below reads.
                warnings.simplefilter("ignore", ResourceWarning)
                code, out, err = run_main(path, "--csv")
        self.assertNotEqual(code, 0)
        self.assertIn("ITE8850-PD", err)
        self.assertEqual(out, "", "a refused run printed a table anyway")
        self.assertEqual({p: Path(p).read_bytes() for p in UNTOUCHABLE}, before)

    def test_a_missing_image_is_an_error_and_not_an_empty_list(self):
        # The other half of the same property. A tool that turned an
        # unreadable image into zero sites would be reporting a measurement of
        # a file it never read, and the "not found by this method" caveat would
        # be the only thing standing between that and a finding.
        code, out, _err = run_main("no-such-image.800", "--csv")
        self.assertNotEqual(code, 0)
        self.assertEqual(out, "")


class NoWriteConstructs(unittest.TestCase):
    """The module contains nothing that *could* write a file, at all.

    `NoWrites` runs the modes with `open` unable to write, which covers every
    path they take. This is the other half: a helper they never reach that
    writes through something `NoWrites` does not see would not be caught there,
    so the property is also read out of the module's own AST. The synthetic
    cases below keep the reader honest -- one that answered `[]` to everything
    would pass the real tree for the wrong reason.
    """

    def test_the_module_has_no_write_construct(self):
        self.assertEqual(write_constructs(TOOL.read_text()), [])

    def test_a_write_mode_open_is_caught(self):
        self.assertEqual(len(write_constructs('open(p, "w")\n')), 1)
        self.assertEqual(len(write_constructs('open(p, "wb")\n')), 1)
        self.assertEqual(len(write_constructs('open(p, mode="a")\n')), 1)

    def test_a_read_mode_open_is_not_caught(self):
        self.assertEqual(write_constructs('open(p, "rb")\n'), [])
        self.assertEqual(write_constructs("open(p)\n"), [])

    def test_a_computed_mode_is_caught(self):
        # A reader that only looked at constant modes would miss this one, and
        # it is the shape an edit actually takes. A read-only tool has no
        # reason to compute a mode, so the computed form is the finding rather
        # than an exception to it.
        self.assertEqual(len(write_constructs("open(p, mode)\n")), 1)
        self.assertEqual(len(write_constructs("open(p, 'w' if x else 'r')\n")), 1)

    def test_a_dotted_writer_is_caught_and_a_str_method_is_not(self):
        # `runtime_addr()` returns a number and `repo_path()` builds a path with
        # `os.path.relpath`, so a reader matching on the attribute name alone
        # would be red on the committed tool. The dotted form is what tells
        # them apart.
        self.assertEqual(len(write_constructs("os.remove(p)\n")), 1)
        self.assertEqual(len(write_constructs("shutil.rmtree(p)\n")), 1)
        self.assertEqual(len(write_constructs("Path(p).write_text(s)\n")), 1)
        self.assertEqual(write_constructs("s.replace('-', '_')\n"), [])


def run_main(image, *argv):
    """`main()` with `sys.argv` set to `image` and `argv`, plus what it owes.

    A subprocess would give isolation this suite does not need and a slower run
    than a byte scan of a 256 KiB image takes. `sys.argv` is restored in a
    `finally` so a case that fails does not leave the next one parsing the
    wrong arguments, and the image is an explicit parameter rather than a
    default so a case with a derived one cannot silently read the committed
    firmware instead.

    `SystemExit` and `OSError` are both turned into a non-zero code because
    both are how this tool refuses -- one for a missing marker, one for an
    image it cannot open -- and a case that wanted to see a traceback would be
    testing the interpreter rather than the tool.
    """
    saved, sys.argv = sys.argv, ["code_pointer_sites.py", image, *argv]
    out, err = io.StringIO(), io.StringIO()
    saved_out, saved_err = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = out, err
    try:
        code = cps.main()
    except SystemExit as exc:
        # A refusal is `SystemExit` carrying its own message, and an
        # uncaught one would put that message on the real stderr rather than
        # the captured one -- so the suite would see a refusal as a bare
        # non-zero exit and could not say *which* refusal it was.
        if not isinstance(exc.code, int):
            print(exc.code, file=err)
            code = 1
        else:
            code = exc.code
    except OSError as exc:
        print(exc, file=err)
        code = 1
    finally:
        sys.stdout, sys.stderr = saved_out, saved_err
        sys.argv = saved
    return code, out.getvalue(), err.getvalue()


def capture_main(image, *argv) -> str:
    _code, out, _err = run_main(image, *argv)
    return out


@contextlib.contextmanager
def scratch_file(data):
    """A throwaway file holding `data`, removed when the case is done.

    `data` is bytes or text, because the two fixtures this suite needs are
    different things: a derived firmware image and a `registers.yaml` whose
    shape is under test. Written in binary so the bytes are the bytes -- a CSV
    written as text would have its CRLF terminators translated, and a
    `--check` case would then be testing a table the tool never produces.

    The one thing this suite writes at all, and it is a fixture rather than an
    input. Built outside any tripwire on purpose: a guard that refuses the
    fixture is refusing the test rather than the tool, which is the failure a
    guard that is too broad always has.
    """
    with tempfile.TemporaryDirectory(prefix="code-pointer-") as tmp:
        path = os.path.join(tmp, "fixture.bin")
        with open(path, "wb") as f:
            f.write(data if isinstance(data, bytes) else data.encode())
        yield path


# The `open` shapes and the dotted writers a read-only module must not contain.
# Both sets are named rather than inlined so the synthetic cases above can say
# what each one is for.
WRITE_CONSTRUCTS = frozenset((
    "os.remove", "os.unlink", "os.rename", "os.replace", "os.mkdir",
    "os.makedirs", "os.rmdir", "os.removedirs", "shutil.rmtree",
    "shutil.copy", "shutil.copy2", "shutil.copyfile", "shutil.move",
))
PATH_METHODS = frozenset((
    "write_text", "write_bytes", "unlink", "rename", "touch", "mkdir",
))


def write_constructs(source) -> list:
    """Every `open` that can write and every dotted write call in `source`.

    Three shapes, because they say different things. An `open` whose mode is a
    constant is decided by the constant; one whose mode is computed is returned
    too, since it writes on some runs. The dotted set catches a writer that
    does not go through `open` at all, and the `Path` methods catch the one
    that reaches a receiver this reader cannot reduce to a name.
    """
    found = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name) and node.func.id == "open":
            mode = open_mode(node)
            if mode is None:
                found.append(f"open(..., <computed mode>) at line {node.lineno}")
            elif any(m in mode for m in "wxa+"):
                found.append(f"open(..., {mode!r}) at line {node.lineno}")
            continue
        name = dotted(node.func)
        if name in WRITE_CONSTRUCTS:
            found.append(f"{name} at line {node.lineno}")
        elif (isinstance(node.func, ast.Attribute)
                and node.func.attr in PATH_METHODS
                and isinstance(node.func.value, ast.Call)
                and dotted(node.func.value.func).rsplit(".", 1)[-1] == "Path"):
            found.append(f"Path(...).{node.func.attr} at line {node.lineno}")
    return found


def open_mode(node):
    """The mode string an `open(...)` call was given, or None if computed."""
    for keyword in node.keywords:
        if keyword.arg == "mode":
            return constant(keyword.value)
    if len(node.args) >= 2:
        return constant(node.args[1])
    return "r"


def constant(node):
    """A string literal's value, or None for anything computed."""
    return node.value if isinstance(node, ast.Constant) and isinstance(
        node.value, str) else None


def dotted(node) -> str:
    """`a.b.c` for a nested attribute/name chain, or '' if it is neither."""
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if not isinstance(node, ast.Name):
        return ""
    parts.append(node.id)
    return ".".join(reversed(parts))


if __name__ == "__main__":
    unittest.main()
