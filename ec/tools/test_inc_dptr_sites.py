#!/usr/bin/env python3
"""The four figures `ec/annotations/xdata-inc-dptr-only.md` is written on, and
the refusal that keeps the tool behind them harmless (issue #707).

The page states a split -- 107 / 73 / 34 / 27, the 73's own 71 + 2, and the
ten addresses §4.7 names as the head of the 73 -- and every one of those is
arithmetic over two committed corpora that can both move. `--check` holds the
committed table against a fresh generation, which is the reproducibility claim;
it is not the claim that the numbers the page prints are *these* numbers. So
they are pinned here, and a re-derivation that moved one fails this suite
rather than leaving the page quietly wrong.

**The ten, and why not eleven.** §4.7 of `ec/annotations/xdata-register-map.md`
writes "`0x0309 0x0311 0x0313 0x0317 0x031B 0x0333 0x0337 0x0341 0x0346
0x034F` and 63 more, running to `0x0647`" -- ten addresses, and 10 + 63 = 73
closes. Issue #707's prose calls them eleven, counting from that list and
miscounting it; the eleventh address in the 73 is `0x0364`, which §4.7 does not
name. The addresses are what is pinned, so `NAMED_HEAD` is the ten §4.7
actually spells and the eleventh position is asserted separately rather than
folded in to make the prose's count come out.

**The figures are re-derived, not read off the committed CSV.** Every case
below runs the tool's own `build()` against the committed tree and the
committed firmware, so a CSV edited to match a stale claim does not satisfy
this suite. `CommittedTable` then holds the two against each other, which is
the one direction a hand-edited file can fail.

**The refusal is `NoWrites`, and the two readers that hold it are the point of
it.** Asserting "the committed files are unchanged after a run" alone would
also be satisfied by a run that wrote identical bytes, and the property worth
holding is stronger: this tool cannot write a file at all. So it is pinned from
both sides. `NoWrites` replaces `open` for the duration of every mode with a
recorder that raises on any write mode, and a writer that regressed fails the
case cleanly instead of overwriting the two files the whole tree is keyed to.
`NoWriteConstructs` walks the module's own AST for every construct that could
write -- `open` in a write mode, `os.remove`, `Path.write_text`, `shutil.rmtree`
-- so a writer added later, in a new mode or a new helper, is caught even on a
path no case happens to run.

**Why not a mode tripwire.** `test_xdata_register_map.py` mocks its nine mode
entry points because that tool has guarded *flags*, and a guard that moved
below the dispatch would let a mode through with the flag still refused. This
tool has no guarded flags and no refusals to move: the single `open` guard
covers every mode by construction, because every one of them runs inside
`main()`. So the coverage question is not "which modes exist" but "is there any
other write vector", and that is a property of the module rather than of its
dispatch. `NoWriteConstructs` pins it with a synthetic-source case beside the
real one, so the reader is not a function that answers `[]` to anything.

**Not tested, deliberately.** The census cells are not pinned figure for figure
-- 196 references across the 73, and the per-row `census_refs` -- because
`xdata-registers.csv` already holds them and `xdata_register_map.py --check`
holds *that* against a fresh generation; pinning them here would make this suite
red for a change to the decompiled tree that has nothing to do with the
admission rule. What is asserted about the census is the shape the page's rule
rests on: the 73 are `pair-literal`-only and none of them is in the pd census,
so a `pd` token appearing under one of them would be a different byte at the
same address number, and the table's single-address row would be wrong about
which program it described. And `--check` against a path the tool was not given
is not exercised: `trace_xdata_refs.check_table()` owns that behaviour and its
own docstring is its record.
"""
import ast
import builtins
import contextlib
import csv
import functools
import importlib.util
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).parent
EC = HERE.parent
REPO = EC.parent
TOOL = HERE / "inc_dptr_sites.py"
# inc_dptr_sites imports xdata_register_map and trace_xdata_refs by bare module
# name, the way check_site_census.py imports both, so the tool directory has to
# be on the path before it is loaded rather than after.
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location("inc_dptr_sites", TOOL)
ids = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ids)
import trace_xdata_refs as tref  # noqa: E402
import xdata_register_map as xrm  # noqa: E402

FIRMWARE = str(EC / "firmware" / "GMxMGxx_11.800")

# The four figures `xdata-inc-dptr-only.md` §1 and §2 are written on.
ONLY_INC = 107          # reached only as the `inc DPTR` half
DECLINED = 73           # of those, no main-EC `MOV DPTR` site
WITH_SITE = 34          # of those, at least one
ENTERED = 7             # of the 34, in registers.yaml
UNENTERED = 27          # of the 34, not in registers.yaml
# The 73's own two-way cut, which is a different question from the 73 and is
# kept apart: "found in no image" and "found in another program" are different
# reasons to decline and the page says so.
NOWHERE = 71
PD_IMAGE_ONLY = 2
PD_ONLY_ADDRESSES = {"0x043B": 2, "0x04A5": 3}
ENTERED_ADDRESSES = ("0x030F", "0x0403", "0x0435", "0x0437", "0x0439",
                     "0x04A7", "0x0523")

# The ten addresses `xdata-register-map.md` §4.7 spells, in order. See the
# docstring for why this is ten and not the issue's eleven.
NAMED_HEAD = ("0x0309", "0x0311", "0x0313", "0x0317", "0x031B", "0x0333",
              "0x0337", "0x0341", "0x0346", "0x034F")
NAMED_ELSEWHERE = 63
LAST_OF_THE_73 = "0x0647"

# The three files a run of this tool must leave byte-identical, plus the
# firmware and the annotations directory. The two census CSVs and
# `registers.yaml` are the ones `agent-gates.sh` and every downstream reader
# are keyed to; a tool that could damage them on a bad run is the wrong place
# to pin a number.
UNTOUCHABLE = (EC / "annotations" / "registers.yaml",
               EC / "annotations" / "xdata-registers.csv",
               EC / "annotations" / "xdata-clusters.csv",
               EC / "annotations" / "xdata-inc-dptr-only.csv")

# The write vectors `NoWriteConstructs` looks for. Dotted names, so that
# `str.replace` -- which `COLUMNS` is built with -- is not caught by an
# attribute-name match on `os.replace`. `open` is handled separately because its
# mode argument is what says whether it writes.
WRITE_CONSTRUCTS = (
    "os.remove", "os.unlink", "os.rename", "os.replace", "os.rmdir",
    "os.mkdir", "os.makedirs", "os.truncate", "os.chmod", "os.chown",
    "shutil.rmtree", "shutil.move", "shutil.copy", "shutil.copyfile",
    "shutil.copymode",
)
# The `Path` methods, matched on the receiver rather than on the method name
# alone for the same reason: `str.replace` is not a path, and a reader that
# could not tell the two apart would be red on the committed tool.
PATH_METHODS = ("write_text", "write_bytes", "unlink", "touch", "mkdir")
PATH_RECEIVERS = ("Path", "pathlib.Path", "PurePath", "pathlib.PurePath")


@functools.lru_cache(maxsize=1)
def build():
    """The tool's own fresh generation, plus the both-halves map behind it.

    Cached, and that is a claim about the tool rather than a shortcut: it is
    deterministic over committed inputs, which is what `--check` and
    `CommittedTable` both rest on. `NoWrites` is unaffected -- it calls
    `main()`, which rebuilds from the tree on every run and is the run being
    measured.
    """
    with open(FIRMWARE, "rb") as f:
        d = f.read()
    off, magic = tref.PD_MARKER
    pd_verified = d[off:off + len(magic)] == magic
    return ids.build(d, pd_verified)


def rows():
    """A fresh generation's rows, through the csv module."""
    return ids.read_rows(build()[1])


def declined(rows_):
    """The rows in the 73, in address order."""
    return [r for r in rows_ if r["mov_dptr_main_ec"] == "0"
            and r["entered"] == "no"]


def run_main(*argv):
    """(exit code, stdout, stderr) for one `main()` under `argv`.

    `ap.error` raises `SystemExit` rather than returning, so the code is taken
    off the exception and handed back: a refusal is the contract, and pinning
    the spelling (`2` today) would be a false alarm about the property that
    matters if it were ever rewritten as `print(...); return 1`.
    """
    out, err = io.StringIO(), io.StringIO()
    argv = [str(TOOL), *argv]
    with mock.patch.object(sys, "argv", argv), \
            contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = ids.main()
        except SystemExit as exc:
            code = exc.code
    return code, out.getvalue(), err.getvalue()


def main_of(source):
    """The `main()` of `source`, which the reader below starts from."""
    return next(n for n in ast.walk(ast.parse(source))
                if isinstance(n, ast.FunctionDef) and n.name == "main")


def dotted(node):
    """`os.path.join` as a string, or None for anything not a dotted chain.

    A chain rooted in a call -- `Path(p).write_text` -- is not one, and returns
    None rather than the tail: a reader that answered with the tail would
    match `s.replace` on `str.replace` for the same reason it would match
    `Path(p).write_text`, and the two are not the same claim.
    """
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if not isinstance(node, ast.Name):
        return None
    return ".".join(reversed(parts + [node.id]))


def open_mode(node):
    """The mode argument of an `open` call, or None when it is not a constant.

    None is the finding, not a pass: a read-only tool has no reason to compute
    a mode, and a reader that only looked at constants would answer "no write"
    to exactly the edit that introduced one.
    """
    if len(node.args) > 1:
        arg = node.args[1]
    else:
        kw = next((kw for kw in node.keywords if kw.arg == "mode"), None)
        if kw is None:
            return "r"
        arg = kw.value
    return arg.value if isinstance(arg, ast.Constant) else None


def write_constructs(source) -> list:
    """Every `open` that can write and every dotted write call in `source`.

    Three shapes, because they say different things. An `open` whose mode is a
    constant is decided by the constant; one whose mode is computed is returned
    too. The dotted set catches a writer that does not go through `open` at all,
    and the `Path` methods catch the one that reaches a receiver this reader
    cannot reduce to a name.
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
            continue
        if (isinstance(node.func, ast.Attribute)
                and node.func.attr in PATH_METHODS
                and isinstance(node.func.value, ast.Call)
                and dotted(node.func.value.func) in PATH_RECEIVERS):
            found.append(f"Path(...).{node.func.attr} at line {node.lineno}")
    return found


class TheSplit(unittest.TestCase):
    """The 107, and the four populations they fall into.

    One fresh generation for the whole class: `build()` reads the whole
    decompiled tree and both corpora behind it, and re-running it per case would
    buy nothing -- the tool is deterministic over committed inputs, which is the
    property `--check` and `CommittedTable` both rest on.
    """

    @classmethod
    def setUpClass(cls):
        cls.resolved, cls.generated = build()
        cls.rows = ids.read_rows(cls.generated)

    def test_the_two_halves_are_disjoint_and_close_on_pair_rows(self):
        # The arithmetic the 107 rests on, measured rather than assumed. `S` is
        # every address a call passes and `S1` every `addr + 1`; the
        # population is `S1 - S`, so an address that is both is in neither
        # count. `PAIR_ROWS` is the tool's own pin for the 214, and reading it
        # back out of the same module that produced these rows is what makes
        # the two the same measurement rather than two that happen to agree.
        both = len(self.resolved)
        only = len(self.rows)
        shared = sorted(a for a, e in self.resolved.items()
                        if e["reached_as_seed"] and e["directions"])
        pure_seeds = sorted(a for a, e in self.resolved.items()
                            if e["reached_as_seed"] and not e["directions"])
        inc_halves = sorted(a for a, e in self.resolved.items() if e["directions"])
        self.assertEqual(shared, [],
                         f"{[f'0x{a:04X}' for a in shared]} are a seed in one "
                         "call and an `inc DPTR` half in another, so the two "
                         "halves are not disjoint and neither figure is what "
                         "it claims to be")
        self.assertEqual(both, xrm.PAIR_ROWS,
                         f"the both-halves map holds {both} addresses and "
                         f"PAIR_ROWS is {xrm.PAIR_ROWS}")
        self.assertEqual(only, ONLY_INC)
        # The whole of the 214 accounted for: the 107 pure seeds and the 107
        # `inc DPTR` halves, disjoint, with nothing in `resolved` outside the
        # two. Asserted as the union rather than as `both == 2 * only`, so a
        # 214 that closed by sharing an address fails on the two lists above
        # rather than on a coincidence.
        self.assertEqual(len(inc_halves), only)
        self.assertEqual(len(pure_seeds) + len(inc_halves), both)
        self.assertEqual(sorted(set(pure_seeds) | set(inc_halves)),
                         sorted(self.resolved))

    def test_the_73_split_from_the_34(self):
        counts = {name: sum(1 for r in self.rows if ids.population_of(r) == name)
                  for name in ids.POPULATIONS}
        self.assertEqual(counts[ids.NO_SITE_ANY_IMAGE]
                         + counts[ids.PD_IMAGE_ONLY], DECLINED)
        self.assertEqual(counts[ids.MOV_DPTR_ENTERED], ENTERED)
        self.assertEqual(counts[ids.MOV_DPTR_NOT_ENTERED], UNENTERED)
        self.assertEqual(counts[ids.MOV_DPTR_ENTERED]
                         + counts[ids.MOV_DPTR_NOT_ENTERED], WITH_SITE)

    def test_the_73_split_71_and_2_and_the_two_are_the_named_pair(self):
        # The cut is by *main-EC* site, so the two bytes with pd-image sites
        # and no main-EC one are in the 73 and not in the 71. Merging them
        # would be the 0x07E2-0x07E5 mistake `trace_xdata_refs.py`'s docstring
        # opens with: a `MOV DPTR` in the pd image is another program's byte at
        # the same address number. The two site counts are named because the
        # page quotes them, and `0x043B`'s 2 is the figure
        # `xdata-0400-045f.md` §6 already records for it.
        nowhere = [r for r in self.rows
                   if ids.population_of(r) == ids.NO_SITE_ANY_IMAGE]
        pd_only = [r for r in self.rows
                   if ids.population_of(r) == ids.PD_IMAGE_ONLY]
        self.assertEqual(len(nowhere), NOWHERE)
        self.assertEqual(len(pd_only), PD_IMAGE_ONLY)
        self.assertEqual({r["addr"]: int(r["mov_dptr_pd_image"]) for r in pd_only},
                         PD_ONLY_ADDRESSES)
        self.assertEqual([r["addr"] for r in pd_only
                          if int(r["mov_dptr_main_ec"])], [])

    def test_the_named_head_is_the_head_of_the_73(self):
        # §4.7's ten addresses, in order, at the head of the 73, and the 73
        # running to `0x0647`. Both ends matter: the head pins that the list
        # was built by the same derivation §4.7's recipe describes rather than
        # sorted independently, and the tail pins that the list stops where the
        # page says it stops -- a 107 that ran on into the 0x08xx pair-reached
        # addresses would still satisfy every other case here.
        the73 = [r["addr"] for r in declined(self.rows)]
        self.assertEqual(the73[:len(NAMED_HEAD)], list(NAMED_HEAD))
        self.assertEqual(the73[-1], LAST_OF_THE_73)
        self.assertEqual(len(NAMED_HEAD) + NAMED_ELSEWHERE, len(the73),
                         f"§4.7 says {NAMED_HEAD.__len__()} named addresses "
                         f"plus {NAMED_ELSEWHERE} more")

    def test_the_eleventh_address_is_not_one_section_4_7_names(self):
        # The issue's prose says eleven; §4.7's list has ten and then "63
        # more", which closes on 73. Pinned so that a reader who goes looking
        # for an eleventh named byte finds `0x0364` and learns where the
        # mismatch is, rather than concluding the list is wrong.
        the73 = [r["addr"] for r in declined(self.rows)]
        self.assertEqual(the73[len(NAMED_HEAD)], "0x0364")
        self.assertNotIn(the73[len(NAMED_HEAD)], NAMED_HEAD)

    def test_the_seven_entered_are_the_seven_named(self):
        entered = [r["addr"] for r in self.rows if r["entered"] == "yes"]
        self.assertEqual(entered, list(ENTERED_ADDRESSES))
        for r in self.rows:
            if r["entered"] == "yes":
                self.assertNotEqual(r["mov_dptr_main_ec"], "0",
                                    f"{r['addr']} is entered with no main-EC "
                                    "`MOV DPTR` site, so §6's rule and this "
                                    "table disagree about what entering means")

    def test_no_address_is_both_a_seed_and_only_an_inc_half(self):
        # The same relation from the other side, on the seed column rather than
        # on the population: a row's `seed` must be the byte below it. A seed
        # column that did not hold that would make the table's whole reading --
        # "this is the `+1` of that" -- unfalsifiable.
        for r in self.rows:
            self.assertEqual(int(r["seed"], 16) + 1, int(r["addr"], 16),
                             f"{r['addr']} is not the `inc DPTR` half of "
                             f"{r['seed']}")

    def test_the_page_50_splits_the_same_way(self):
        # `xdata-0400-045f.md` §6's 50 and this population overlap in seven
        # addresses -- `0x0405` `0x0409` `0x040B` `0x040D` `0x040F` `0x0411`
        # `0x043B` -- which §4 of that page already names as "reached only as
        # `param_1 + 1` inside an accessor". Those seven are the reason §6's
        # membership rule and this page's rule are the same rule and not two,
        # so the overlap is pinned here rather than left to the prose to keep
        # true.
        page = {r["addr"] for r in declined(self.rows)} & {
            f"0x{a:04X}" for a in range(0x400, 0x460)}
        self.assertEqual(page, {"0x0405", "0x0409", "0x040B", "0x040D",
                                "0x040F", "0x0411", "0x043B"})


class TheCensusShape(unittest.TestCase):
    """What the census columns are allowed to say about the 73.

    Not the figures -- `xdata-registers.csv` owns those and
    `xdata_register_map.py --check` holds them. The shape, because the rule
    this page states is about what a census row is, and a `pd` token or a
    second spelling under one of the 73 would change what the row is about.
    """

    @classmethod
    def setUpClass(cls):
        _resolved, cls.generated = build()
        cls.rows = [r for r in ids.read_rows(cls.generated)
                    if r["mov_dptr_main_ec"] == "0" and r["entered"] == "no"]

    def test_census_refs_is_the_sum_of_the_bucket_columns(self):
        # On all 107. The bucket columns are generated from `xrm.BUCKETS` and
        # the accession is `census_refs`, so this is the check that a bucket
        # added to that tuple cannot be dropped from the table: the schema would
        # gain a column and `census_refs` would stop closing without it.
        for r in ids.read_rows(self.generated):
            self.assertEqual(int(r["census_refs"]),
                             sum(int(r[c]) for c in r
                                 if c.startswith("census_") and c != "census_refs"),
                             f"{r['addr']}: census_refs does not close on the "
                             "bucket columns")

    def test_only_read_write_and_read_write_occur_in_this_population(self):
        # The other two buckets in `xrm.BUCKETS` are zero everywhere on this
        # population, and that is a measurement rather than a schema decision:
        # a pair-accessor call is the caller's only reference to the address, so
        # it cannot also be a handoff or an address-taken. Pinned because the
        # page's rule leans on it -- a `passed-to-call` on one of the 73 would
        # mean the byte is named somewhere the census has not resolved, which
        # is a different question from the one this page answers.
        non_zero = {(r["addr"], c) for r in self.rows
                    for c in ("census_passed_to_call", "census_address_taken")
                    if int(r[c])}
        self.assertEqual(non_zero, set())

    def test_the_73_are_pair_literal_only_and_main_ec_only(self):
        # Re-derived through the census rather than read from the table, so an
        # edited CSV cannot satisfy it. `pair-literal` alone means no
        # `DAT_EXTMEM_` token and no generated symbol name names any of the 73
        # anywhere in the main EC: they are reached as an argument and by
        # nothing else. And the pd census is a separate dict the tool never
        # merges, so an address appearing there would be another program's byte
        # and the row's single `addr` would be about the wrong one.
        _funcs, by_file = xrm.load_index()
        symbols = xrm.load_symbols()
        accessors = xrm.load_pair_accessors()
        census, _calls, _raw = xrm.scan(by_file, xrm.load_names(_funcs),
                                        set(xrm.load_names(_funcs)), symbols,
                                        accessors=accessors)
        for r in self.rows:
            addr = int(r["addr"], 16)
            merged = xrm.blank_entry()
            for program in xrm.MAIN_PROGRAMS:
                if addr in census[program]:
                    xrm.absorb(merged, census[program][addr])
            self.assertEqual(merged["spellings"], {xrm.PAIR_SPELLING},
                             f"{r['addr']} is spelled {sorted(merged['spellings'])}, "
                             "not pair-literal alone")
            self.assertNotIn(addr, census[xrm.PD_PROGRAM],
                             f"{r['addr']} also has a pd census row, so it is "
                             "not a main-EC-only byte")


class CrossCheck(unittest.TestCase):
    """The list confirmed by a second entry point, not only by the tool that
    made it."""

    def test_the_named_ten_have_no_mov_dptr_site_by_byte_scan(self):
        # `trace_xdata_refs.sites_for` over the image is the method the page's
        # rule is written against, run here directly rather than through this
        # tool's table. The write-up prints this command, so the figure it
        # prints is the one this case holds.
        with open(FIRMWARE, "rb") as f:
            d = f.read()
        for text in list(NAMED_HEAD) + [LAST_OF_THE_73]:
            self.assertEqual(tref.sites_for(d, int(text, 16)), [],
                             f"{text} has a direct MOV DPTR site in the file, "
                             "so the page's zero for it has moved")

    def test_the_named_ten_are_counted_zero_by_the_committed_tool(self):
        # The same fact through the tool a reader would run, because the
        # command on the page is the tool's and the page's zero is its output.
        # Two entry points, one answer -- and the run is a real `main()`, not
        # the cached generation, so the command on the page is what is measured.
        code, out, err = run_main(FIRMWARE, "--csv")
        self.assertEqual(code, 0, err)
        table = {r["addr"]: r for r in ids.read_rows(out)}
        for text in list(NAMED_HEAD) + [LAST_OF_THE_73]:
            row = table.get(text)
            self.assertIsNotNone(row, f"{text} is not in the table")
            self.assertEqual((row["mov_dptr_main_ec"], row["mov_dptr_pd_image"]),
                             ("0", "0"),
                             f"{text}: the page says no site in any image")


class CounterExample(unittest.TestCase):
    """`0x0420` is what keeps the rule from being "any literal first argument".

    The address is passed to `add_full_product_to_dptr` as a bare hex literal
    at `pd/34A5.c:19`, and that is the same *spelling* that gets the 73
    resolved. What differs is the callee: the committed `.asm` is
    `mul AB / add A,DPL / addc A,DPH / ret` with no `movx` at all, so it
    dereferences nothing and `pair_accessor()` does not select it. The address
    space is a property of the callee's body, not of the token -- which is the
    whole discriminator, and it is worth holding in a test because the
    alternative rule is the one a reader would write from the spelling alone.
    """

    def test_the_callee_is_not_selected_as_an_accessor(self):
        self.assertNotIn("add_full_product_to_dptr", xrm.load_pair_accessors())

    def test_the_callees_committed_asm_has_no_movx(self):
        asm = xrm.read_asm("pd")["10BC"]
        self.assertEqual([mnem for _at, mnem, _oper in asm if mnem == "movx"], [],
                         "pd/10BC.asm has a movx, so the counter-example is no "
                         "longer one")
        self.assertEqual(xrm.pair_accessor(asm), None)

    def test_the_address_is_not_in_the_population(self):
        _resolved, generated = build()
        self.assertNotIn("0x0420", {r["addr"] for r in ids.read_rows(generated)})

    def test_every_accessor_the_table_names_still_dereferences_xdata(self):
        # The positive half of the same claim, and the one that would fail if a
        # routine's body changed under a name the table still printed. Read back
        # out of the committed `.asm` rather than taken from the accessor table,
        # the way `xdata_register_map.py --self-test` does it, and the name ->
        # address step through the committed annotation CSV rather than through
        # a table of this suite's own.
        asm = xrm.read_asm("bank1")
        _resolved, generated = build()
        named = {name for r in ids.read_rows(generated)
                 for name in r["accessor"].split(";") if name}
        accessors = xrm.load_pair_accessors()
        with open(xrm.ANNOT_CSV, newline="") as f:
            annotated = {row["name"]: (row["scope"], row["addr"])
                         for row in csv.DictReader(f)
                         if row["type"] in xrm.PAIR_TYPE_DIR}
        self.assertTrue(named, "the table names no accessor, so this case "
                               "measured nothing")
        for name in sorted(named):
            self.assertIn(name, accessors,
                          f"{name} reaches an address in the table but is not a "
                          "selected accessor")
            scope, addr = annotated[name]
            self.assertEqual(scope, "bank1",
                             f"{name} is annotated in {scope}, so the bank1 "
                             "listing read for it is the wrong one")
            self.assertEqual(xrm.pair_accessor(asm[addr]), accessors[name],
                             f"{name}'s committed .asm is no longer the "
                             f"{accessors[name]} the table recorded")


class CommittedTable(unittest.TestCase):
    """The committed CSV is what a fresh generation produces, byte for byte.

    `--check` does this as a command; doing it here as well is what makes the
    figures in `TheSplit` about the *tree* rather than about whatever is in the
    file. A hand-edited CSV that agreed with a stale claim would leave `TheSplit`
    green, because those cases run `build()` themselves -- so the one case that
    reads the file is the one that would notice.
    """

    def test_the_committed_table_is_a_fresh_generation(self):
        _resolved, generated = build()
        code, _out, err = run_main(FIRMWARE, "--check")
        self.assertEqual(code, 0, err)

    def test_the_committed_table_has_the_generated_columns(self):
        with open(ids.SITES_CSV, newline="") as f:
            header = next(csv.reader(f))
        self.assertEqual(header, ids.COLUMNS)


class NoWrites(unittest.TestCase):
    """No mode opens a file in the repository for writing, and the three
    files everything else is keyed to come back byte-identical.

    The tripwire is the point rather than belt-and-braces: asserting "the
    committed files are unchanged" alone would also be satisfied by a run that
    wrote identical bytes, and the property worth holding is that this tool
    cannot write at all. So `open` is replaced with a recorder that raises on
    any write mode, and the refusal is a clean failure instead of a damaged
    tree. Every mode runs under it -- `--csv`, `--check` and the default
    summary -- because a tool that could damage the repository on a bad run is
    the wrong place to pin a number.
    """

    def refuse(self, *argv):
        """Run `main()` with `open` unable to write, and assert the three
        things a write-free run owes: no write-mode open, a zero exit, and the
        committed files byte-identical to just before."""
        attempted = []
        real_open = builtins.open

        def tripwire(file, mode="r", *a, **kw):
            if any(m in str(mode) for m in "wxa+"):
                attempted.append((str(file), str(mode)))
                raise AssertionError(
                    f"inc_dptr_sites.py opened {file!r} for writing (mode "
                    f"{mode!r}); the tool writes stdout and nothing else")
            return real_open(file, mode, *a, **kw)

        before = {p: Path(p).read_bytes() for p in UNTOUCHABLE}
        with mock.patch.object(builtins, "open", tripwire):
            code, _out, err = run_main(*argv)
        self.assertEqual(attempted, [],
                         f"`{' '.join(argv)}` opened a file for writing")
        self.assertEqual(code, 0, err)
        self.assertEqual({p: Path(p).read_bytes() for p in UNTOUCHABLE}, before,
                         f"`{' '.join(argv)}` changed a committed file")
        return code, _out, err

    def test_the_csv_mode_writes_only_to_stdout(self):
        _code, out, err = self.refuse(FIRMWARE, "--csv")
        self.assertTrue(out.startswith("addr,seed,direction,accessor,"), err)
        self.assertEqual(len(ids.read_rows(out)), ONLY_INC)

    def test_the_check_mode_writes_nothing(self):
        # `--check` diffs the committed table and returns its verdict. A tool
        # that rewrote the file it is checking would make the check a
        # regeneration, and the tripwire is what says it does not.
        self.refuse(FIRMWARE, "--check")

    def test_the_summary_mode_writes_nothing(self):
        _code, out, err = self.refuse(FIRMWARE)
        self.assertIn(f"{xrm.PAIR_ROWS} addresses are reached by a pair "
                      f"accessor, {ONLY_INC} of them only as", out)
        self.assertIn("is §4.7's 73", out)

    def test_an_unidentified_pd_image_refuses_rather_than_reporting_zeroes(self):
        # A dump whose 0x20040 marker is not there has an unidentified pd
        # region, so `mov_dptr_pd_image` would read 0 for every row and the
        # 71 / 2 cut would become 73 / 0 -- a measurement that looks like a
        # finding. The refusal is the same one `trace_xdata_refs.py` makes and
        # it is the same claim, so it is the same rule.
        with tempfile_scratch() as image:
            with open(FIRMWARE, "rb") as f:
                data = bytearray(f.read())
            off, _magic = tref.PD_MARKER
            data[off:off + len(b"ITE8850-PD")] = b"ITE8850-XX"
            with open(image, "wb") as f:
                f.write(data)
            before = {p: Path(p).read_bytes() for p in UNTOUCHABLE}
            code, out, err = run_main(image, "--csv")
        self.assertNotEqual(code, 0)
        self.assertIn("pd region is unidentified", err)
        self.assertEqual(out, "", "a refused run printed a table anyway")
        self.assertEqual({p: Path(p).read_bytes() for p in UNTOUCHABLE}, before)


class NoWriteConstructs(unittest.TestCase):
    """The module contains nothing that could write a file, at all.

    `NoWrites` runs the three modes with `open` unable to write, which covers
    every path those three take. This is the other half: a *fourth* mode, or a
    helper it calls, that writes through something `NoWrites` never exercises
    would not be caught there, so the property is also read out of the module's
    own AST. Both shapes matter and the synthetic case below keeps the reader
    honest about each of them, because a reader that answered `[]` to
    everything would pass the real tree for the wrong reason.
    """

    def test_the_module_has_no_write_construct(self):
        self.assertEqual(write_constructs(TOOL.read_text()), [])

    def test_a_write_mode_open_is_caught(self):
        self.assertEqual(len(write_constructs('open(p, "w")\n')), 1)
        self.assertEqual(len(write_constructs('open(p, "wb")\n')), 1)
        self.assertEqual(len(write_constructs('open(p, mode="a")\n')), 1)

    def test_a_read_mode_open_is_not_caught(self):
        # The negative, or the case above would pass on a reader that flagged
        # every `open` it saw -- including the read-only ones the tool needs.
        self.assertEqual(write_constructs('open(p, "rb")\n'), [])
        self.assertEqual(write_constructs("open(p)\n"), [])

    def test_a_computed_mode_is_caught(self):
        # The one shape a reader that only looked at constant modes would miss,
        # and the one an edit actually takes: `open(p, "w" if flag else "r")`
        # writes on some runs. A read-only tool has no reason to compute a mode,
        # so the computed form is the finding rather than an exception to it.
        self.assertEqual(len(write_constructs("open(p, mode)\n")), 1)
        self.assertEqual(len(write_constructs("open(p, 'w' if x else 'r')\n")), 1)

    def test_a_dotted_writer_is_caught_and_a_str_method_is_not(self):
        # `COLUMNS` is built with `str.replace` and `os.replace` is a writer, so
        # a reader matching on the attribute name alone would be red on the
        # committed tool. The dotted form is what tells them apart.
        self.assertEqual(len(write_constructs("os.remove(p)\n")), 1)
        self.assertEqual(len(write_constructs("shutil.rmtree(p)\n")), 1)
        self.assertEqual(len(write_constructs("Path(p).write_text(s)\n")), 1)
        self.assertEqual(write_constructs("s.replace('-', '_')\n"), [])


@contextlib.contextmanager
def tempfile_scratch():
    """A directory the refusal cases can write a derived image into.

    The one thing this suite writes at all, and it is a copy of the committed
    firmware with ten bytes of its pd marker changed -- a fixture, not an
    input. The tripwire in `NoWrites` patches `open` only around `main()`, so
    the fixture is built outside it; were it built inside, the tripwire would
    be refusing the test rather than the tool, which is the failure mode a
    guard that is too broad always has.
    """
    with tempfile.TemporaryDirectory(prefix="inc-dptr-") as tmp:
        yield os.path.join(tmp, "no-pd-marker.800")


if __name__ == "__main__":
    unittest.main()
