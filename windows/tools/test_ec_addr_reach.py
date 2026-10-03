#!/usr/bin/env python3
r"""That `ec_addr_reach.py`'s zero is a measurement and not an absence of one.

The subject is `windows/tools/ec_addr_reach.py` and the claim it reports is a
negative: that the vendor service addresses no `0x08xx` byte, which
`docs/hardware-tests/level-block-0860-086e.md` §5 had left open because the
census it would have to come from covers only three high bytes. **A negative
whose search cannot be shown to find a planted address is worthless, so the
positive control comes first** and the tree's own zero is checked against it.
That is the whole reason this suite exists rather than a line in the write-up:
`CLAUDE.md`'s calibration rule turns on whether the method would have found the
thing it did not find, and nothing in the tool itself can say so.

`PositiveControlTests` builds a scratch tree holding an `0x086x` write in each
of the three spellings a real one could take -- a decimal literal through the
parameterised helper, a decimal literal straight through `EcCtrl`, and a hex
literal -- and holds that the sweep finds every one. A control planted and not
found would make every other case here a green run over a broken search.

**No figure of the tree is asserted.** What is held is the claim: which high
bytes the census resolves to, that the level block's addresses resolve to
nothing, and that no `ECSpec` constant in any of the three trees names one.
The counts move when a legitimate re-export lands, and a suite holding one
would go red on exactly the change that is supposed to be reviewable --
`tools/test_readme_suite_table.py` and `census_test_line_pins.py` carry the
same lesson at their own scale.

`AntiTamperAsymmetryTests` holds the distinction the write-up is mostly about:
a zero on the decrypted service and a zero on a partial, anti-tamper-damaged
tree are different claims, and they are checked against `t1wr_callers.py`'s own
body census rather than asserted here. Reusing that tool's measurement is what
makes the asymmetry evidence rather than a claim in prose -- if a future dump
decrypts one of the two, the body census moves and this stops being a
boundary and starts being a hole.

Nothing here opens an EC, calls the vendor driver, or reads hardware: the
subject is a text scan of committed `.cs` files, and every input is either the
committed tree or a fixture written to a temp directory.
"""
import contextlib
import io
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parent))

import ec_callsites  # noqa: E402  (needs the sys.path entry above)
import ec_addr_reach  # noqa: E402

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent

# The tree whose reach the write-up's answer rests on, and the two that are
# partial. Named rather than indexed so a reordering of `TREES` in the tool
# cannot silently re-point a case at a different tree.
SERVICE_ROOT = "windows/decompiled/v3.1.39.0/GCUService"
PARTIAL_ROOTS = ["windows/decompiled/v3.1.6.0", "windows/decompiled/v3.9.18.0"]

# The addresses `docs/hardware-tests/level-block-0860-086e.md` watches, in the
# decimal a C# `const ushort` would carry. Decimal and hex both, because that is
# how the vendor spells one and a sweep that only understood hex would find a
# planted control and still miss the real tree.
LEVEL_DECIMAL = (2143, 2144, 2155, 2156, 2158)

# Addresses the vendor is known to name, used to show the `ECSpec` constant scan
# is reading the table rather than matching nothing.
KNOWN_NAMED = (0x0464, 0x0751, 0x075B, 0x07C5)

# Cached per root. `tree_reach` walks every `.cs` in a tree, and the suite asks
# the same question from several classes; without this the fixture cases and the
# tree cases would pay for the same scan once each.
_REACH = {}


def reach(root=SERVICE_ROOT):
    """The tool's own measurement of one tree, computed once per root."""
    if root not in _REACH:
        _REACH[root] = ec_addr_reach.tree_reach(root)
    return _REACH[root]


def in_fixture(files, fn):
    """Run `fn(root)` against a scratch .cs tree, removed afterwards.

    The work has to happen *inside* the fixture's lifetime: `scan` and
    `helper_callers` both take a directory rather than a repository, which is
    what lets the positive control be a fixture at all, and both need the files
    to still be there when they are called. Passing the work in rather than
    returning the directory is what keeps that honest -- a caller that stashed
    the path and swept it after the `with` would silently scan nothing.

    Nothing is written under the repository: a control that had to be committed
    to be tested would be a control nobody could trust as one.
    """
    tmp = tempfile.mkdtemp(prefix="ec-addr-reach-")
    try:
        for rel, text in files.items():
            path = os.path.join(tmp, rel)
            parent = os.path.dirname(path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text)
        return fn(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def sweep(root):
    """(census rows, parameterised callers) for a tree, the tool's own path."""
    rows = list(ec_callsites.scan(root))
    callers = ec_addr_reach.helper_callers(
        root, ec_addr_reach.parameterised_helpers(rows))
    return rows, callers


# The three spellings, as three sources. The first is the shape that matters
# most: an `0x08xx` write through the parameterised helper is the one form the
# committed census structurally cannot hold, so a control that skipped it would
# leave the whole issue's reasoning untested.
CONTROL_HELPER = """\
namespace MyControlCenter;

internal class Control
{
	private void WriteECRAM(ushort Addr, ulong Value)
	{
		EcCtrl.Write(className, Addr, Convert.ToByte(Value));
	}

	public void SetLevel(byte level)
	{
		WriteECRAM(2155, level);
	}
}
"""

CONTROL_DIRECT_DECIMAL = """\
namespace MyControlCenter;

internal class Control
{
	public void SetLevel(byte level)
	{
		EcCtrl.Write(className, 2156, level);
	}
}
"""

CONTROL_DIRECT_HEX = """\
namespace MyControlCenter;

internal class Control
{
	public void SetLevel(byte level)
	{
		EcCtrl.Write(className, 0x086B, level);
	}
}
"""

# The look-alike this repository's tree actually contains:
# `MyRgbLightBarDefault.WriteECRAM` takes six lightbar levels, not an address,
# and its first argument would parse as an EC address if the sweep were
# name-based. `AddressHelperTests` holds the scoping that excludes it, and this
# is the shape: the same method name, a first argument that is a *variable*, and
# a body whose real `EcCtrl.Write` calls carry their own literal addresses.
LOOKALIKE_LIGHTBAR = """\
namespace MyControlCenter;

internal class MyRgbLightBarDefault
{
	private static void WriteECRAM(int _LightBarOnOff, uint _WelcomeMode,
		uint _BreathingLightEffect, uint _red_level, uint _green_level,
		uint _blue_level)
	{
		EcCtrl.Write(m_ClassName, 1864, 128);
		EcCtrl.Write(m_ClassName, 1865, 0);
	}

	public void Apply(int m_nLightBarOnOff, uint m_nColorful)
	{
		WriteECRAM(m_nLightBarOnOff, m_nColorful, 0u, 0u, 0u, 0u);
	}
}
"""


class PositiveControlTests(unittest.TestCase):
    """A sweep that cannot find a planted address proves nothing by its silence.

    These run before anything asserts a zero, and each holds one of the three
    spellings separately so a regression names the path it broke rather than
    only that the fixture went unfound.
    """

    def test_decimal_through_the_parameterised_helper_is_found(self):
        def run(root):
            rows, callers = sweep(root)
            return [r for r in rows if r["addr_kind"] == "unresolved"], callers

        unresolved, callers = in_fixture({"Control.cs": CONTROL_HELPER}, run)
        self.assertEqual([r["method"] for r in unresolved], ["WriteECRAM"],
                         "the fixture's helper body did not land as unresolved")
        self.assertEqual([c["addr"] for c in callers], ["0x086B"],
                         "a 2155 decimal caller was not resolved to 0x086B")
        self.assertEqual([c["addr_kind"] for c in callers], ["literal"])

    def test_decimal_direct_write_is_found(self):
        rows, _ = in_fixture({"Control.cs": CONTROL_DIRECT_DECIMAL}, sweep)
        self.assertEqual([r["addr"] for r in rows], ["0x086C"])

    def test_hex_direct_write_is_found(self):
        rows, _ = in_fixture({"Control.cs": CONTROL_DIRECT_HEX}, sweep)
        self.assertEqual([r["addr"] for r in rows], ["0x086B"])

    def test_each_spelling_lands_in_the_band_the_negative_covers(self):
        """The end-to-end path, not just its parts.

        Each spelling on its own is a component test; this says the property
        `self_check` tests -- an `0x08xx` write is a band hit -- is reachable
        by all three of them. Without it, a change that broke one route into
        the band while leaving the case above green would still let the
        committed negative read clean.
        """
        for name, text, planted in (("helper", CONTROL_HELPER, 0x086B),
                                    ("decimal", CONTROL_DIRECT_DECIMAL, 0x086C),
                                    ("hex", CONTROL_DIRECT_HEX, 0x086B)):
            with self.subTest(spelling=name):
                def run(root, text=text):
                    rows, callers = sweep(root)
                    return [int(r["addr"], 16) for r in rows if r["addr"]] + \
                           [int(c["addr"], 16) for c in callers if c["addr"]]

                found = in_fixture({"Control.cs": text}, run)
                self.assertIn(planted, found,
                              "the planted address was not found at all, so "
                              "the committed negative is untested")
                self.assertTrue(ec_addr_reach.in_band(
                    planted, ec_addr_reach.LEVEL_BLOCK))

    def test_a_helper_definition_is_not_counted_as_its_own_caller(self):
        """The `unresolved` row and the definition are the same site.

        Counting a definition as a caller would add one unresolvable row per
        helper to the very population the derivation reads, and the caller set
        would not match what a reader counts in the file.
        """
        _rows, callers = in_fixture({"Control.cs": CONTROL_HELPER}, sweep)
        self.assertEqual(len(callers), 1,
                         f"expected the one real caller, got {callers}")

    def test_a_call_spanning_two_lines_is_found(self):
        """The shape ILSpy actually emits for a wrapped argument list.

        `ec_callsites.split_args` returns None for a call whose closing paren is
        on the next line, and the sweep has to keep reading. A planted control
        on one line would pass against a tool that dropped the wrapped ones --
        and the committed tree has wrapped calls.
        """
        src = """\
namespace MyControlCenter;

internal class Control
{
	private void WriteECRAM(ushort Addr, ulong Value)
	{
		EcCtrl.Write(className, Addr, Convert.ToByte(Value));
	}

	public void SetLevel(byte level)
	{
		WriteECRAM(2155,
			level);
	}
}
"""
        _rows, callers = in_fixture({"Control.cs": src}, sweep)
        self.assertEqual([c["addr"] for c in callers], ["0x086B"])


class AddressHelperTests(unittest.TestCase):
    """The scoping of the parameterised sweep, which a name cannot do.

    The committed tree holds two `WriteECRAM` methods in two classes with two
    signatures, and only one of them takes an EC address. A sweep that matched
    the name would resolve `MyRgbLightBarDefault`'s four call sites as though
    they were addresses -- which they are not, and which would make this tool
    report a caller population four larger than the one that exists.
    """

    LOOKALIKE_FILES = {"MyRgbLightBarDefault.cs": LOOKALIKE_LIGHTBAR}

    def test_a_same_named_helper_in_another_class_is_excluded(self):
        def run(root):
            rows, callers = sweep(root)
            helpers = ec_addr_reach.parameterised_helpers(rows)
            return rows, callers, [h for h in helpers if h["file"] is not None]

        rows, callers, scoped = in_fixture(self.LOOKALIKE_FILES, run)
        self.assertTrue(rows, "the look-alike body's own writes should land")
        self.assertEqual(scoped, [],
                         "a class with no unresolved row is not a helper set")
        self.assertEqual(callers, [])

    def test_the_scoped_helper_and_the_look_alike_coexist_without_colliding(self):
        files = dict(self.LOOKALIKE_FILES)
        files["SingleZone.cs"] = CONTROL_HELPER
        _rows, callers = in_fixture(files, sweep)
        self.assertEqual([c["addr"] for c in callers], ["0x086B"])
        self.assertTrue(all("SingleZone.cs" in c["file"] for c in callers),
                        f"a call leaked across files: {callers}")

    def test_an_unresolved_first_argument_is_reported_not_dropped(self):
        """A caller whose address is a variable is the shape a computed
        `0x08xx` write would take, so it has to be visible in the output.

        Silently skipping it would make the caller count agree with the number
        of resolvable addresses while covering fewer sites than it appears to,
        which is the failure mode a negative is most vulnerable to.
        """
        src = """\
namespace MyControlCenter;

internal class Control
{
	private void WriteECRAM(ushort Addr, ulong Value)
	{
		EcCtrl.Write(className, Addr, Convert.ToByte(Value));
	}

	public void SetLevel(ushort computed)
	{
		WriteECRAM(computed, 1uL);
	}
}
"""
        _rows, callers = in_fixture({"Control.cs": src}, sweep)
        self.assertEqual(len(callers), 1)
        self.assertEqual(callers[0]["addr"], "")
        self.assertEqual(callers[0]["addr_kind"], "unresolved")


class ReachTests(unittest.TestCase):
    """The claim the write-up makes, against the committed tree."""

    @classmethod
    def setUpClass(cls):
        cls.reach = reach()

    def test_the_level_block_addresses_resolve_nowhere(self):
        resolved = {int(r["addr"], 16) for r in self.reach["sites"] if r["addr"]}
        resolved |= {int(c["addr"], 16)
                     for c in self.reach["callers_resolved"]}
        for addr in LEVEL_DECIMAL:
            with self.subTest(addr=f"0x{addr:04X}"):
                self.assertNotIn(addr, resolved,
                                 "a level-block address resolves; the negative "
                                 "no longer holds")

    def test_the_resolved_bands_are_the_ones_the_write_up_names(self):
        """A property of the census's shape, not a count of the tree.

        Which high bytes resolve is what the reach statement is, and it is what
        `0x08xx` is absent from. The per-band site counts are deliberately not
        asserted: they move on any legitimate re-export.
        """
        self.assertEqual(set(self.reach["bands"]), {0x04, 0x07, 0x0F})
        self.assertNotIn(0x08 >> 8, self.reach["bands"])

    def test_the_suite_and_the_tool_cover_the_same_addresses(self):
        """The negative is only as good as the addresses it covers.

        The tool and this file each hold a spelling of them -- one as hex, one
        as the decimal a `const ushort` carries. If the two ever disagreed the
        case above would be asserting coverage of addresses the tool never
        looked for, and would pass while proving nothing.
        """
        self.assertEqual({f"0x{a:04X}" for a in ec_addr_reach.LEVEL_ADDRESSES},
                         {f"0x{a:04X}" for a in LEVEL_DECIMAL})

    def test_the_parameterised_path_is_genuinely_swept(self):
        """Not read off the two `unresolved` rows the census already had.

        The census's own contribution is the two helper bodies with no address.
        If that were the whole of the parameterised search the caller set would
        be empty, and an empty set and a swept-and-clean set are
        indistinguishable from outside -- which is why this asserts the callers
        exist, come from the file the derivation scoped them to, and land
        outside the band.
        """
        callers = self.reach["callers_resolved"]
        self.assertTrue(callers, "no parameterised caller resolved")
        self.assertTrue(all(c["file"].endswith("SingleZone.cs")
                            for c in callers),
                        f"a caller came from an unexpected file: {callers}")
        for c in callers:
            with self.subTest(where=f"{c['file']}:{c['line']}"):
                self.assertFalse(
                    ec_addr_reach.in_band(int(c["addr"], 16),
                                          ec_addr_reach.LEVEL_BLOCK))

    def test_the_wmi_helpers_are_a_dead_door_and_not_a_live_blind_spot(self):
        """A helper nobody calls cannot hide an address.

        `WMIEC.WMIReadECRAM`/`WMIWriteECRAM` reach the EC over WMI rather than
        through `EcCtrl`, so no call site of theirs is a row in the census and
        they are listed rather than derived. The distinction the write-up turns
        on is that a dead door is not a blind spot: the method searched for the
        callers and found none, rather than having nowhere to look.
        """
        live = [c for c in self.reach["callers"]
                if c["helper"].startswith("WMI")]
        self.assertEqual(live, [], "a WMIEC helper now has a caller")
        wmi = [h for h in self.reach["helpers"] if h["helper"].startswith("WMI")]
        self.assertTrue(wmi, "the WMI helpers were not searched for at all")

    def test_the_computed_index_is_reported_unproven(self):
        """A base is a start, not a range, and the tool must not claim more.

        `(ushort)(3840 + i)` is a table walk whose index the census cannot
        bound. Reporting the base as though it were the address would let a
        reader take the empty `0x08xx` band as covering the walk.
        """
        bases = self.reach["computed"]
        self.assertTrue(bases, "no computed site, so the walk shape is untested")
        for base in bases:
            with self.subTest(base=base):
                self.assertGreaterEqual(int(base, 16) >> 8, 0x0F,
                                        "a computed base outside the fan-table "
                                        "page changes what the bound means")

    def test_every_computed_site_is_a_fan_table_walk(self):
        """What narrows the walk population, and what does not narrow it.

        All of them belong to a fan-table manager, and the bases above the
        extent `windows/vendor-ec-map.md` documents for `FanTable_Manager1p5`
        belong to `FanTable_Manager2`, which `MyFanTableCtrl` does not
        instantiate on this board. Both are held here because the write-up
        leans on neither for the index bound -- but if a computed site appeared
        in some other class, the shape of that boundary would change and this
        is what would say so.
        """
        computed = [r for r in self.reach["sites"]
                    if r["addr_kind"] == "computed"]
        self.assertTrue(computed)
        strays = sorted({f"{r['type']}.{r['method']}" for r in computed
                         if "FanTable" not in r["type"]})
        self.assertEqual(strays, [],
                         "a computed site outside a fan-table class; the "
                         "walk population is no longer the fan table's")
        high = {r["type"] for r in computed if int(r["addr"], 16) > 0x0F5F}
        for t in high:
            with self.subTest(cls=t):
                self.assertIn("FanTable_Manager2", t,
                              "a base past the documented Manager1p5 extent is "
                              "in a class the write-up does not describe")


class EcspecTests(unittest.TestCase):
    """The independent line of evidence, over all three trees.

    `ECSpec` constants are C# `const`, so one naming an `0x08xx` byte would be
    inlined into its call site and would already be in the census. Reading the
    table separately is what makes that a measurement rather than an inference:
    it needs no call-site parser to be right, so a parser bug cannot produce it.
    """

    def _trees(self):
        return [(path, reach(path))
                for path in [SERVICE_ROOT] + PARTIAL_ROOTS]

    def test_no_tree_names_an_address_in_the_band(self):
        for path, t in self._trees():
            with self.subTest(tree=path):
                self.assertIsNotNone(t["ecspec"],
                                     "ECSpec.cs not found; the constant census "
                                     "did not run, which is not a pass")
                named = sorted(n for n, v in t["ecspec"].items()
                               if ec_addr_reach.in_band(
                                   v, ec_addr_reach.LEVEL_BLOCK))
                self.assertEqual(named, [])

    def test_the_constant_census_is_not_vacuous(self):
        """Every tree has to actually hold named addresses, or the case above
        is empty.

        This is what makes the negative mean something: a `const ushort` scanner
        that matched nothing would report "0 in the band" for a file full of
        named addresses, and the case above would pass on it.
        """
        for path, t in self._trees():
            with self.subTest(tree=path):
                values = set(t["ecspec"].values())
                self.assertTrue(
                    values & set(KNOWN_NAMED),
                    f"none of {KNOWN_NAMED} parsed, so the constant scan is "
                    f"not reading the table")

    def test_the_type_filter_is_what_keeps_fan_modes_out(self):
        """`ECSpec` carries `const uint` fan-mode codes and `[Flags]` masks.

        A bare number scan over the file would read `FAN_MODE_TURBO = 0x10` and
        a fan-level enum as addresses. The `const ushort` requirement is the
        filter, and `User_Fan_Level1 = 0x81` is the case that matters: it is an
        enum member whose value is a plausible address, so a scanner without
        the filter would report a named address that is not one.
        """
        path = (REPO / "windows" / "decompiled" / "v3.1.39.0" / "GCUService" /
                "Define" / "ECSpec.cs")
        text = path.read_text(encoding="utf-8-sig")
        self.assertIn("User_Fan_Level1 = 0x81", text,
                      "the fixture this filter is tested against is gone")
        names = {m.group("name") for line in text.splitlines()
                 for m in [ec_addr_reach.ECSPEC_CONST.match(line)] if m}
        for absent in ("User_Fan_Level1", "Bit0", "FAN_MODE_TURBO"):
            with self.subTest(name=absent):
                self.assertNotIn(absent, names,
                                 "a non-address constant was read as one")
        self.assertIn("ADDR_EC_MAIN_FAN_RPM_BYTE1", names,
                      "a real address constant was missed")

    def test_the_filter_is_not_tighter_than_it_looks(self):
        """What `const ushort` still admits, and why the claim survives it.

        The `0x00xx` band of the table is WMI event codes rather than
        addresses, so the filter does not isolate addresses and the write-up
        does not claim it does. The claim is over *every* named constant the
        file carries, which is the stronger statement -- and it is only correct
        while the filter keeps that band in, so this pins the shape.
        """
        consts = reach(SERVICE_ROOT)["ecspec"]
        low = {n: v for n, v in consts.items() if v < 0x0400}
        self.assertTrue(low, "the low band went away; re-derive what it held")
        self.assertFalse([n for n in low if n.startswith("ADDR")],
                         "a new low-band entry is an EC address and the "
                         "write-up's description of that band is stale")
        self.assertIn("OSD_FanModeSwitch", low,
                      "the low band's WMI event codes are gone, so the "
                      "description of what the filter admits is stale")


class AntiTamperAsymmetryTests(unittest.TestCase):
    """A zero on a partial tree is a weaker claim, and this is why.

    `docs/findings/ec-addr-reach-086x.md` reports the two partial trees
    separately from the decrypted service rather than pooling the three. The
    pooling would read as a stronger result than any of them is: the decrypted
    service's zero is a statement about a readable program, while the two others
    are statements about a program half of whose method bodies are not in the
    tree at all.

    The asymmetry is measured with `t1wr_callers.py`'s own marker census rather
    than asserted here, so it is evidence rather than a claim in prose: a future
    dump that decrypts one of those trees changes the number, and this stops
    being a boundary.

    The census is ILSpy's own `Invalid MethodBodyBlock` markers in the `.cs`
    trees -- the decompiler saying which bodies it could not turn back into C#,
    counted from committed text with no pip package involved. That is the right
    input here, and deliberately not `t1wr_callers.body_census()`: that one
    classifies the `.exe` method-body headers behind `dnfile`, which says when
    the *binary* was encrypted rather than what is missing from the tree this
    tool searches, and it makes the suite unrunnable on a checkout without it.
    """

    @classmethod
    def setUpClass(cls):
        import t1wr_callers
        cls.marks = {}
        for _label, paths in t1wr_callers.TEXT_INPUTS[:3]:
            for rel in paths:
                cls.marks[rel] = t1wr_callers.decompiler_census(REPO / rel)

    def _markers(self, root):
        return self.marks[root]

    def test_the_service_tree_is_free_of_decompiler_damage(self):
        """The premise of the asymmetry, from the tool that measures it.

        Zero markers in the decrypted service is what "every method body
        decrypted" means from the decompiler's side, and it is what makes the
        service's zero a different kind of statement from a zero on a tree that
        was never readable at all.
        """
        service = [rel for rel in self.marks if "v3.1.39.0" in rel]
        self.assertTrue(service, "the service tree is not among the census inputs")
        for rel in service:
            with self.subTest(tree=rel):
                self.assertEqual(sum(self._markers(rel).values()), 0,
                                 "the decrypted service still carries ILSpy "
                                 "error markers, so its zero is not a "
                                 "zero over a readable program")

    def test_the_partial_trees_carry_the_damage_the_service_does_not(self):
        """The other half, and it is the half the write-up's caveat rests on."""
        for root in PARTIAL_ROOTS:
            with self.subTest(tree=root):
                marks = self._markers(root)
                self.assertGreater(sum(marks.values()), 0,
                                   f"{root} carries no ILSpy error markers, so "
                                   f"it is no longer a tree this method could "
                                   f"only partly read")

    def test_the_partial_trees_yield_no_call_site_at_all(self):
        """The asymmetry in its primary form: zero, not zero in the band.

        Not zero in `0x08xx` -- zero. That is a different fact from a tree that
        was searched and came back empty, and it is the one the write-up's
        first boundary turns on.
        """
        for root in PARTIAL_ROOTS:
            with self.subTest(tree=root):
                self.assertEqual(reach(root)["sites"], [],
                                 f"{root} now yields EC call sites; it is no "
                                 f"longer a tree this method cannot read, and "
                                 f"the write-up's asymmetry needs re-deriving")

    def test_the_write_up_names_both_partial_trees(self):
        """The prose has to carry the asymmetry, not just the tool.

        A report that pooled the three trees would leave the runbook's
        service-stopped second pass looking optional on the strength of a zero
        from two trees that were never readable. The sentence is in the
        write-up, and this is what keeps it there.
        """
        text = ((REPO / "docs" / "findings" /
                 "ec-addr-reach-086x.md").read_text(encoding="utf-8"))
        for name in ("v3.1.6.0", "v3.9.18.0"):
            with self.subTest(tree=name):
                self.assertIn(name, text,
                              f"the write-up does not name {name}, so a reader "
                              f"cannot tell the zero's reach")
        self.assertIn("not found by this method", text,
                      "the write-up states the zero without the method's reach")


class RenderingTests(unittest.TestCase):
    """The report is the deliverable, and it has to say what it is.

    `boundaries()` is the half that cannot be dropped: a zero printed on its
    own reads as an absence, and the negative is only honest with the boundary
    attached to it.
    """

    @classmethod
    def _render(cls, root=SERVICE_ROOT, band=ec_addr_reach.LEVEL_BLOCK):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            ec_addr_reach.report(reach(root), band)
            ec_addr_reach.boundaries()
        return buf.getvalue()

    def test_the_boundaries_name_each_way_the_search_can_fail(self):
        out = self._render()
        for phrase in ("not found by this method", "anti-tamper", "immediate",
                       "firmware", "unbounded"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, out)

    def test_a_tree_with_no_sites_is_not_reported_as_a_clean_tree(self):
        """Zero sites is a statement about the search, not about the service.

        `v3.1.6.0` yields nothing at all, which is a different fact from
        yielding nothing in one band. Printing the same "0 site(s) in the
        census" line for both is what would let a reader take the first as the
        second.
        """
        out = self._render(PARTIAL_ROOTS[0])
        self.assertIn("could not search", out)
        self.assertIn("no answer for", out)
        self.assertNotIn("answer for 0x0800-0x08FF: 0 site", out)

    def test_the_band_query_reports_the_band_it_was_asked_about(self):
        out = self._render(band=(0x0400, 0x04FF))
        self.assertIn("answer for 0x0400-0x04FF", out)

    def test_a_band_with_sites_is_listed_rather_than_only_counted(self):
        """A band that does resolve says which sites, so `--band` is usable.

        The count alone would answer "is there anything here" without saying
        what, which is the question `ec_callsites.py --addr` is asked elsewhere.
        """
        out = self._render(band=(0x0400, 0x04FF))
        self.assertNotIn("answer for 0x0400-0x04FF: 0 site", out)
        self.assertIn("census  ", out)


class SelfCheckTests(unittest.TestCase):
    """`--self-check` against the committed tree, and against broken copies.

    A self-check that only ever sees the committed tree has never shown it can
    go red, which is the same "a check that has quietly stopped refusing looks
    exactly like a check that is working" note `agent-gates.sh` carries. So the
    refusals are exercised: each is a claim the write-up makes, broken on a copy
    of the tool's own measurement.
    """

    def _mutated(self, **changes):
        t = dict(reach())
        t.update(changes)
        return [t]

    def _drifts(self, t):
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            rc = ec_addr_reach.self_check(t)
        return rc, buf.getvalue()

    def test_it_passes_on_the_committed_tree(self):
        rc, err = self._drifts([reach()])
        self.assertEqual(rc, 0, err)

    def test_a_band_that_reaches_the_level_block_is_drift(self):
        bands = dict(reach()["bands"])
        bands[0x08] = 1
        rc, err = self._drifts(self._mutated(bands=bands))
        self.assertEqual(rc, 1)
        self.assertIn("0x8", err)

    def test_a_level_block_address_in_the_census_is_drift(self):
        planted = {"file": "C.cs", "line": 1, "type": "N.C", "method": "M",
                   "op": "write", "addr": "0x086B", "addr_kind": "literal",
                   "addr_expr": "2155", "value_expr": "b"}
        t = reach()
        rc, err = self._drifts(self._mutated(
            sites=list(t["sites"]) + [planted]))
        self.assertEqual(rc, 1)
        self.assertIn("0x086B", err)

    def test_a_level_block_address_in_a_parameterised_caller_is_drift(self):
        planted = {"helper": "WriteECRAM", "type": "N.C", "file": "C.cs",
                   "line": 1, "addr": "0x086B", "addr_kind": "literal",
                   "addr_expr": "2155"}
        t = reach()
        rc, err = self._drifts(self._mutated(
            callers=list(t["callers"]) + [planted],
            callers_resolved=list(t["callers_resolved"]) + [planted]))
        self.assertEqual(rc, 1)
        self.assertIn("parameterised caller", err)

    def test_an_empty_caller_set_is_drift(self):
        """The silent-pass case: a sweep that stopped finding callers at all.

        The negative would still read clean, because a set with nothing in it
        contains no address in the band. That is the vacuity this guard exists
        to catch, and it is why the caller set has to be non-empty rather than
        merely in-band.
        """
        rc, err = self._drifts(self._mutated(callers=[], callers_resolved=[]))
        self.assertEqual(rc, 1)
        self.assertIn("untested", err)

    def test_a_wmi_helper_with_a_caller_is_drift(self):
        planted = {"helper": "WMIWriteECRAM", "type": "MyControlCenter.WMIEC",
                   "file": "WMIEC.cs", "line": 9, "addr": "0x086C",
                   "addr_kind": "literal", "addr_expr": "2156"}
        rc, err = self._drifts(
            self._mutated(callers=list(reach()["callers"]) + [planted]))
        self.assertEqual(rc, 1)
        self.assertIn("WMIEC", err)

    def test_a_missing_ecspec_is_drift_rather_than_a_pass(self):
        rc, err = self._drifts(self._mutated(ecspec=None))
        self.assertEqual(rc, 1)
        self.assertIn("ECSpec", err)

    def test_the_lightbar_lookalike_reaching_the_sweep_is_drift(self):
        """The scoping has to hold for the negative to mean what it says.

        `MyRgbLightBarDefault.WriteECRAM`'s first argument is a lightbar level.
        If it ever reached the sweep, the caller population would be larger
        than the one that exists and the write-up's account of what was swept
        would be wrong in a way no other case here would notice.
        """
        planted = {"helper": "WriteECRAM",
                   "type": "MyControlCenter.MyRgbLightBarDefault",
                   "file": "MyControlCenter/MyRgbLightBarDefault.cs",
                   "line": 76, "addr": "", "addr_kind": "unresolved",
                   "addr_expr": "m_nLightBarOnOff"}
        rc, err = self._drifts(
            self._mutated(callers=list(reach()["callers"]) + [planted]))
        self.assertEqual(rc, 1)
        self.assertIn("LightBar", err)


class TreeListTests(unittest.TestCase):
    """The three committed trees, and what each one is called.

    The tool reports a partial tree differently from the decrypted service, and
    that difference is carried in the label rather than inferred from the path.
    A pool of three identical rows would read as one claim instead of three.
    """

    def test_every_tree_the_names_promise_is_on_disk(self):
        for _label, rel in ec_addr_reach.TREES:
            with self.subTest(tree=rel):
                self.assertTrue((REPO / rel).is_dir(), f"{rel} is not in the tree")

    def test_every_tree_with_an_ecspec_entry_names_one_that_exists(self):
        """The `ECSPEC` table is keyed by tree root, so a stale key is a
        silently skipped census rather than a failure.

        A root that falls off the mapping returns None, the report prints "not
        found in this tree", and that tree quietly loses its independent line
        of evidence -- a green run with one fewer check in it.
        """
        for _label, rel in ec_addr_reach.TREES:
            with self.subTest(tree=rel):
                self.assertIn(rel, ec_addr_reach.ECSPEC)
                self.assertIsNotNone(ec_addr_reach.ecspec_constants(rel))

    def test_a_tree_that_is_not_the_service_is_labelled_as_partial(self):
        labels = dict((path, label) for label, path in ec_addr_reach.TREES)
        self.assertEqual([labels[p] for p in PARTIAL_ROOTS],
                         ["v3.1.6.0 (partial, anti-tamper)",
                          "v3.9.18.0 (partial, anti-tamper)"])


if __name__ == "__main__":
    unittest.main()