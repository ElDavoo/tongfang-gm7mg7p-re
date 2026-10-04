#!/usr/bin/env python3
"""Unit checks for the fan-tachometer address resolution (issue #29).

`docs/findings/fan-tachometer-addresses.md` resolves the four `docs/findings.md`
§2 features `ec/annotations/static-refs-audit.md` §3 called unresolvable, and
turns up one vendor defect worth keeping: `ECSpec.cs` names `0x046B` as the
second fan's low byte while upstream at the pinned rev, the EC's own
`store_r6_r7_to_046c_046d`, `be16_046c_046d_minus_100` and the committed
capture all put it at `0x046D`. This file pins the byte facts that reading
stands on, so a firmware or a table that stops matching fails rather than
quietly agreeing with a stale transcription.

Three things it holds, one per class:

  * the resolved addresses. Each entry's three `static_refs*` keys are
    re-derived from the committed image here rather than read out of
    `registers.yaml` and compared, so a stale count fails instead of
    agreeing with itself. It does not re-run the scan that wrote
    `xdata-registers.csv`: that would assert the tool against itself, and
    `check_register_counts.py` is already in the gate for the same numbers.
  * `0x046B`'s four sites. The claim is that all four sit inside one routine,
    and that two of them are in the routine's four-byte sync, which is what
    the entry's `present-untested` grade is named for. It is not all four, and
    not three of four: the read at `0x9D69` is downstream of the sync, in the
    tail that stages the quartet's members into R7 for a call, and the write
    at `0x9CEB` is on an earlier three-byte store that never touches `0x046E`.
    Which site is which is read out of the committed `.asm`, which is the
    machine code; where it and the `.c` disagree, the `.asm` is right.
  * the correction. The load-bearing claim of this diff is a negative about
    the *repository* rather than about the firmware: that no committed file
    again asserts the driver defines are absent, since that sentence was
    false and survived three review rounds in its corrected form. A `grep`
    that finds nothing is "not found by this method", so this class asserts
    the absence of a known false sentence in the files this change touches
    and names them -- it is a check on prose, which is the only kind that can
    hold a prose claim.

What it deliberately does not do: claim anything about the driver's *use* of
the defines. `linux/patches/gm7mg7p-dmi-entry/upstream-excerpt.txt` quotes
`#define` lines, the `struct uniwill_device_descriptor` definition and the
`.features =` initializers -- so it is not a defines-only file -- but it
quotes no function body and therefore no EC access at all, which is why how
`uniwill-laptop` *reads* a define is not re-derivable from this tree.
`docs/findings/dmi-descriptor-evidence.md` §1 is the write-up that drew the
line between "not vendored" and "not readable". What *is* re-derivable is the
address each define carries, and that is checked below against the excerpt's
own text.

Nothing here was measured on hardware.
"""
import csv
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))

import verify_gap_text as G
import yaml

REGISTERS = ROOT / 'ec' / 'annotations' / 'registers.yaml'
EXCERPT = (ROOT / 'linux' / 'patches' / 'gm7mg7p-dmi-entry'
           / 'upstream-excerpt.txt')
FEATURE_MAP = (ROOT / 'linux' / 'patches' / 'gm7mg7p-dmi-entry'
               / 'feature-map.csv')
SYMBOLS = ROOT / 'ec' / 'ghidra' / 'xdata-symbols.csv'

# Address == image offset for every program, which is what make_bank_image.py
# arranges and why nothing here does address arithmetic of its own. Loaded once
# rather than per test, for the reason test_xdata_07fd_07ff_triple.py gives: the
# reader leaves an unclosed file and unittest's warning filters would put the
# ResourceWarning on a shared tool this suite is not here to fix.
IMAGES = G.load_images()

# The resolved addresses, as the entries name them. Written as a mapping from
# entry name to its address list rather than as five flat constants, so a test
# reads as "the MAIN_FAN_RPM entry covers 0x0464 and 0x0465" -- which is the
# claim -- instead of as a list of numbers that has to be checked against
# registers.yaml by eye.
RESOLVED = {
    'MAIN_FAN_RPM': [0x0464, 0x0465],
    'SECOND_FAN_RPM': [0x046C, 0x046D],
    'XDATA_046B': [0x046B],
}

# The two bit features, as the aliases the two pre-existing entries carry. They
# get no status of their own, so what is asserted is that the entry names the
# bit at all -- a future edit that drops the alias loses the driver interface
# and the Windows stack's own name for it at the same time. Spelled as the
# §2 feature names, not as `USB`/`TOUCHPAD`: the short forms are substrings of
# unrelated entry names (`USB_C_POWER_PRIORITY`), which would make the
# "no entry of its own" assertion below match a byte that has nothing to do
# with either feature.
BIT_ALIASES = {
    'TRIGGER': ('USB_POWERSHARE', '0x0767'),
    'OEM_4 (CHARGING_PROFILE_MASK)': ('TOUCHPAD_TOGGLE', '0x07A6'),
}

# The upstream defines, as (symbol, value) at the rev BASE_COMMIT pins. The
# value is the integer the excerpt's `0x....` literal denotes, so the assertion
# compares numbers rather than re-implementing hex parsing.
UPSTREAM = (
    ('EC_ADDR_MAIN_FAN_RPM_1', 0x0464),
    ('EC_ADDR_MAIN_FAN_RPM_2', 0x0465),
    ('EC_ADDR_SECOND_FAN_RPM_1', 0x046C),
    ('EC_ADDR_SECOND_FAN_RPM_2', 0x046D),
    ('EC_ADDR_TRIGGER', 0x0767),
    ('EC_ADDR_OEM_4', 0x07A6),
)

# `gate_06e6_442_then_sync_046a_from_086b`, the routine every 0x046B site sits
# in, as the half-open runtime span its committed listing covers. Read from
# `ec/decompiled/bank0/9CA6.asm`, which runs from the routine's own entry to
# its last instruction, the `lcall 0x163c` at 0x9D97 -- so the span is inclusive
# of the last byte of that instruction.
QUARTET_ROUTINE = ('9CA6', '9D97')

# The quartet the sync moves: 0x046A/0x046B/0x046E/0x046F from 0x086B-0x086E.
# Asserted because it is what the entry's note says the byte is for, and
# because "0x046B is the second fan's low byte" and "0x046B is a member of an
# unrelated four-byte sync" are indistinguishable from the count alone.
QUARTET = (0x046A, 0x046B, 0x046E, 0x046F)
QUARTET_SOURCE = (0x086B, 0x086C, 0x086D, 0x086E)

# The two spans of the routine the note cites for the quartet sync: the
# `xrl a,r7` compare chain and the store run that copies all four members.
# Half-open at the upper end in the sense the listing uses -- both inclusive
# of the instruction they end on, since that instruction is part of each span.
# Held as data so the check below can hold a site against them, which is the
# distinction the note's prose turns on and the one a count of 4 cannot make.
SYNC_COMPARE = (0x9D1A, 0x9D3E)
SYNC_STORE = (0x9D41, 0x9D60)


def registers():
    with open(REGISTERS) as f:
        return yaml.safe_load(f)['registers']


def row_for(name):
    for r in registers():
        if r['name'] == name:
            return r
    return None


def entry_addrs(entry):
    """One entry's `addr` as a list, whichever of the two shapes it uses."""
    a = entry['addr']
    return a if isinstance(a, list) else [a]


def as_list(value):
    """A `static_refs*` key as a list, for an entry of either shape."""
    return value if isinstance(value, list) else [value]


def direct_sites(addr):
    """{runtime: (mnemonic, ...)} for every `mov dptr,#addr` in bank0.

    Anchored on the three raw bytes `90 <hi> <lo>`, which is the whole opcode,
    so a site is found without decoding anything around it. Only bank0: every
    one of the five resolved addresses is bank0-only, and the point of the
    re-derivation below is that this stays true rather than being assumed.
    """
    needle = bytes((0x90, (addr >> 8) & 0xFF, addr & 0xFF))
    image = IMAGES['bank0']
    return {i for i in range(len(image) - 2) if image[i:i + 3] == needle}


def listing_runtimes(path):
    """The runtime addresses a committed `.asm` export lists instructions at."""
    text = path.read_text()
    return {int(m.group(1), 16)
            for m in re.finditer(r'^([0-9A-F]{4})\s+[0-9a-f]{2} ', text,
                                 re.MULTILINE)}


def listing_ops(path):
    """{runtime: (mnemonic, operands)} for a committed `.asm` export.

    The operand column is what distinguishes the three things a `0x046B` site
    can be, and none of them is distinguishable from the address alone: a
    `movx @dptr,a` is a store, a `movx a,@dptr` followed by `xrl a,r7` is the
    sync's compare, and a `movx a,@dptr` followed by `mov r7,a` and a call is
    a read staged for that call. Parsing the operands rather than taking a role
    from a table here is what keeps this check from restating the note -- the
    defect it exists to catch was a role asserted in prose that the listing
    did not support.

    The byte columns are padded with `-` for one- and two-byte opcodes, so the
    mnemonic is found after a run of two-or-more spaces past the address rather
    than at a fixed column, which differs between the two widths.
    """
    out = {}
    pat = re.compile(r'^([0-9A-F]{4})\s+(?:[0-9a-f]{2}|- -)'
                     r'(?:\s+(?:[0-9a-f]{2}|- -)?){0,2}\s{2,}(\S+)\s*(.*)$',
                     re.MULTILINE)
    for m in pat.finditer(path.read_text()):
        out[int(m.group(1), 16)] = (m.group(2).lower(), m.group(3).strip().lower())
    return out


class TestResolvedEntries(unittest.TestCase):
    """The entries exist, carry every split key, and their counts are the
    image's rather than the file's."""

    def test_each_resolved_address_has_its_entry(self):
        """Every resolved address appears under the entry that claims it."""
        for name, addrs in RESOLVED.items():
            entry = row_for(name)
            self.assertIsNotNone(entry, f'no registers.yaml entry named {name}')
            self.assertEqual(addrs, entry_addrs(entry),
                             f'{name} does not carry the addresses the '
                             f'write-up resolves it to')

    def test_no_other_entry_claims_these_addresses(self):
        """The addresses are not also claimed by some other entry, which would
        make a reader of registers.yaml unable to tell which note governs."""
        claimed = {a: n for n, addrs in RESOLVED.items() for a in addrs}
        for entry in registers():
            for addr in entry_addrs(entry):
                if addr in claimed:
                    self.assertEqual(entry['name'], claimed[addr],
                                     f'0x{addr:04X} is claimed by both '
                                     f'{claimed[addr]} and {entry["name"]}')

    def test_every_entry_carries_all_three_split_keys(self):
        """A missing split key is an error in check_register_counts.py, not a
        zero, so an entry that drops one is not a smaller entry."""
        for name in RESOLVED:
            entry = row_for(name)
            for key in ('static_refs', 'static_refs_main_ec',
                        'static_refs_pd_image'):
                self.assertIn(key, entry, f'{name} has no {key}')
                self.assertEqual(len(as_list(entry[key])), len(entry_addrs(entry)),
                                 f'{name}.{key} does not have one value per '
                                 f'address')

    def test_counts_are_re_derived_from_the_image(self):
        """The committed counts are the image's, re-derived here rather than
        read back out of the file being checked."""
        for name, addrs in RESOLVED.items():
            entry = row_for(name)
            for addr, total, main, pd in zip(
                    entry_addrs(entry),
                    as_list(entry['static_refs']),
                    as_list(entry['static_refs_main_ec']),
                    as_list(entry['static_refs_pd_image'])):
                found = len(direct_sites(addr))
                self.assertEqual(
                    found, total,
                    f'{name} 0x{addr:04X}: registers.yaml says {total} direct '
                    f'sites, the image has {found}')
                self.assertEqual(main, found,
                                 f'{name} 0x{addr:04X}: main-EC split '
                                 f'{main} against {found} found in bank0')
                self.assertEqual(pd, 0,
                                 f'{name} 0x{addr:04X}: a PD-image site is not '
                                 f'expected for this address, and the split '
                                 f'key says {pd}')

    def test_both_pairs_are_wholly_main_ec(self):
        """The four tachometer bytes have a direct site in bank0 and none in
        the PD image, which is why their splits are `found / 0` rather than a
        graded split. The PD half is checked in
        `test_counts_are_re_derived_from_the_image`; what this adds is that
        the bank0 half is not vacuous, since a `0 / 0` pair would satisfy the
        split assertion above without any site existing at all."""
        for addr in (0x0464, 0x0465, 0x046C, 0x046D):
            self.assertTrue(direct_sites(addr),
                            f'0x{addr:04X} has no direct site in bank0, which '
                            f'the write-up says it has')

    def test_the_symbols_are_named_by_address_order(self):
        """`gen_xdata_symbols.py` spells a two-address entry `_0`/`_1` by
        address order and never `_HI`/`_LO`, because an endianness claim baked
        into a symbol outlives the note that corrects it. That rule is
        asserted here rather than left to the generator's own convention."""
        names = {}
        with open(SYMBOLS) as f:
            for row in csv.DictReader(f):
                names[int(row['addr'], 16)] = row['name']
        for base, addrs in (('MAIN_FAN_RPM', [0x0464, 0x0465]),
                            ('SECOND_FAN_RPM', [0x046C, 0x046D])):
            for i, addr in enumerate(addrs):
                self.assertEqual(f'{base}_{i}', names[addr])
        self.assertEqual('XDATA_046B', names[0x046B])

    def test_status_values_are_from_the_existing_vocabulary(self):
        """`confirmed-working` and `present-untested` are both existing
        values. Asserted against the file rather than against a list written
        here, so a re-grade that moves one of these to a value the vocabulary
        has not got fails instead of passing against this suite's own idea of
        what is allowed."""
        vocabulary = set(re.findall(r'^#\s+([a-z][a-z-]+)\s*:',
                                    REGISTERS.read_text(), re.MULTILINE))
        for name in ('MAIN_FAN_RPM', 'SECOND_FAN_RPM', 'XDATA_046B'):
            self.assertIn(row_for(name)['status'], vocabulary,
                          f'{name} carries a status the vocabulary does not '
                          f'define')

    def test_the_bit_features_got_no_entry_of_their_own(self):
        """`USB_POWERSHARE` and `TOUCHPAD_TOGGLE` are bits of bytes that
        already carry a grade, and neither has a live verdict at the register.
        Giving either its own entry is the overclaim this diff exists to
        correct, so its absence is the assertion -- an empty name list here
        would be a new row with a live status nothing supports."""
        for feature, _ in BIT_ALIASES.values():
            names = [r['name'] for r in registers()]
            self.assertFalse([n for n in names if feature in n],
                             f'a registers.yaml entry is named after the '
                             f'{feature} feature, which is a bit of a byte '
                             f'that already has an entry')


class TestBitAliases(unittest.TestCase):
    """The two bit features are recorded as aliases on the entries that own
    the bytes, with the reason each gets no status of its own."""

    def test_each_alias_names_its_feature_and_address(self):
        for name, (feature, addr) in BIT_ALIASES.items():
            note = str(row_for(name).get('note') or '')
            self.assertIn(feature, note,
                          f'{name}.note does not name the {feature} feature')
            self.assertIn(addr, note,
                          f'{name}.note does not carry the {feature} address')

    def test_the_alias_notes_say_why_there_is_no_own_status(self):
        """A readback is not a behaviour, and a hotkey that never raised its
        event never reached the byte. Without these two sentences an alias
        reads as a second grade, which is the overclaim this diff exists to
        correct."""
        for name in BIT_ALIASES:
            note = str(row_for(name).get('note') or '')
            self.assertIn('no status of its own', note,
                          f'{name}.note records the alias without saying why '
                          f'it carries no status of its own')


class TestVendorConstants(unittest.TestCase):
    """The committed defines and vendor constants, read rather than taken on
    trust."""

    def test_every_define_is_quoted_in_the_excerpt(self):
        """Each resolved address is named by an `#define` quoted verbatim at
        the rev `BASE_COMMIT` pins. This is the claim that falsified the
        "the driver source is not vendored here" sentence the correction in
        `static-refs-audit.md` and `docs/findings.md` retracts, so it is
        asserted against the excerpt's own text rather than trusted."""
        text = EXCERPT.read_text()
        for symbol, value in UPSTREAM:
            pattern = (r'^\s*\d+:\s*#define\s+' + re.escape(symbol) +
                       r'\s+0x([0-9A-Fa-f]{4})\s*$')
            m = re.search(pattern, text, re.MULTILINE)
            self.assertIsNotNone(
                m, f'{symbol} is not quoted as a #define in '
                   f'linux/patches/gm7mg7p-dmi-entry/upstream-excerpt.txt')
            self.assertEqual(int(m.group(1), 16), value,
                             f'{symbol} is quoted at a different address than '
                             f'the write-up resolves it to')

    def test_the_excerpt_names_the_pinned_rev(self):
        """The excerpt's own header must name the full SHA `BASE_COMMIT`
        pins, or "at the pinned rev" is an assertion with nothing behind it.
        `BASE_COMMIT` holds the short form, so the comparison is a prefix."""
        short = (ROOT / 'linux' / 'patches' / 'BASE_COMMIT').read_text().split()
        self.assertTrue(short, 'BASE_COMMIT is empty')
        header = EXCERPT.read_text()
        full = re.search(r'Base rev\s*:\s*([0-9a-f]{40})', header)
        self.assertIsNotNone(full, 'the excerpt names no base rev')
        self.assertTrue(
            full.group(1).startswith(short[0]),
            f'the excerpt quotes rev {full.group(1)}, which is not the rev '
            f'linux/patches/BASE_COMMIT pins ({short[0]})')

    def test_feature_map_points_the_four_features_at_their_addresses(self):
        """`feature-map.csv` is what makes the defines reachable without
        reading the excerpt, and rule 7 of `check_dmi_descriptor.py` is what
        holds it to the excerpt byte for byte. Asserted here so the pair is
        checked even where that checker is not run."""
        rows = {r['repo_feature']: r
                for r in csv.DictReader(FEATURE_MAP.open())}
        for feature, addr in (('PRIMARY_FAN', '0x0464'),
                              ('SECONDARY_FAN', '0x046C'),
                              ('TOUCHPAD_TOGGLE', '0x07A6'),
                              ('USB_POWERSHARE', '0x0767')):
            self.assertIn(feature, rows,
                          f'feature-map.csv has no {feature} row')
            self.assertEqual(addr, rows[feature]['upstream_ec_addr'])
            self.assertTrue(rows[feature]['reason'].strip(),
                            f'{feature} carries no reason, which is what the '
                            f'address claim rests on')


class TestVendorDivergence(unittest.TestCase):
    """`0x046B` is not the second fan's low byte. That is a fact about the
    vendor's code, and the entry's grade is named for what the EC does with
    the byte rather than for what the vendor reads."""

    def setUp(self):
        self.asm = ROOT / 'ec' / 'decompiled' / 'bank0' / '9CA6.asm'
        self.text = self.asm.read_text().lower()
        self.note = str(row_for('XDATA_046B').get('note') or '')

    def test_all_four_sites_are_inside_the_one_routine(self):
        """Every `0x046B` site is in `0x9CA6`'s listing. The claim is about
        containment, so it is checked against the committed listing's own
        runtime addresses rather than against a start/end pair written here --
        a span written here could drift from the listing and still agree with
        itself."""
        lo, hi = (int(v, 16) for v in QUARTET_ROUTINE)
        listed = listing_runtimes(self.asm)
        self.assertIn(lo, listed, 'the listing does not start at its entry')
        self.assertIn(hi, listed, 'the listing does not reach its last insn')
        sites = direct_sites(0x046B)
        self.assertTrue(sites, '0x046B has no direct site to contain')
        for site in sorted(sites):
            self.assertGreaterEqual(site, lo,
                                    f'0x{site:04X} is before the routine entry')
            self.assertLessEqual(site, hi,
                                 f'0x{site:04X} is past the routine\'s last '
                                 f'instruction, so the entry note that all '
                                 f'four sites sit inside it is false')

    def test_each_site_lands_where_the_note_says_it_does(self):
        """The four sites are not four of a kind, and the entry note's split is
        the claim this holds.

        The role is read out of each site's operands in the committed listing
        rather than taken from a table here, so a site cannot be filed as a
        sync member because prose filed it that way -- which is exactly the
        error the note previously carried, naming `0x9D69` as part of a store
        run that ends ten bytes earlier. A read staged into R7 for a call is
        downstream of the sync, not in it, and the check says so from the
        listing.
        """
        ops = listing_ops(self.asm)
        roles = {}
        for site in sorted(direct_sites(0x046B)):
            # The `mov dptr,#0x046b` is followed by the instruction that acts
            # on it; read a couple past it so the follow-on is available.
            after = sorted(a for a in ops if site < a <= site + 8)
            self.assertTrue(after, f'0x{site:04X} has no instruction after it '
                                   f'in the listing, so its role is unreadable')
            mnemonic, operands = ops[after[0]]
            if operands.startswith('@dptr'):
                roles[site] = 'store'
            elif operands.startswith('a, @dptr'):
                follow = ops[after[1]] if len(after) > 1 else ('', '')
                roles[site] = ('compare' if follow[0] == 'xrl'
                               else 'staged-read')
            else:
                roles[site] = f'unclassified ({mnemonic} {operands})'

        # The two sync sites are the compare and the store inside the spans
        # the note cites; the staged read at 0x9D69 is past the end of the
        # store run, and the earlier store at 0x9CEB is before both.
        compare_lo, compare_hi = SYNC_COMPARE
        store_lo, store_hi = SYNC_STORE
        self.assertEqual(roles.get(0x9D22), 'compare',
                         'the read at 0x9D22 is the sync\'s compare')
        self.assertTrue(compare_lo <= 0x9D22 <= compare_hi,
                        'the compare site is outside the cited chain')
        self.assertEqual(roles.get(0x9D4D), 'store',
                         'the write at 0x9D4D is the sync\'s store')
        self.assertTrue(store_lo <= 0x9D4D <= store_hi,
                        'the store site is outside the cited run')
        self.assertEqual(roles.get(0x9D69), 'staged-read',
                         'the read at 0x9D69 is a value staged into R7 for a '
                         'call, not a copy -- see the note, which calls it part '
                         'of the sync')
        self.assertFalse(store_lo <= 0x9D69 <= store_hi,
                         '0x9D69 has moved into the cited store run, so the '
                         'note\'s split needs re-deriving')
        self.assertEqual(roles.get(0x9CEB), 'store',
                         'the write at 0x9CEB is the earlier store')
        self.assertFalse(store_lo <= 0x9CEB <= store_hi
                         or compare_lo <= 0x9CEB <= compare_hi,
                         '0x9CEB has moved into a sync span, so the note\'s '
                         'split needs re-deriving')

    def test_the_routine_syncs_the_four_byte_quartet(self):
        """The listing names all four destination bytes and all four source
        bytes, each as a `mov DPTR,#...` literal. This is what makes 0x046B a
        member of a sync rather than a fan reading: without the quartet the
        count of 4 proves nothing about what the byte is for."""
        for addr in QUARTET + QUARTET_SOURCE:
            # Ghidra prints an immediate without zero padding (`#0x46a`), so
            # the needle is built unpadded; a padded one would miss every
            # address below 0x1000 and the check would pass vacuously.
            self.assertIn(f'mov      dptr, #0x{addr:x}',
                          self.text,
                          f'0x{addr:04X} does not appear as a DPTR literal in '
                          f'the 0x9CA6 listing')

    def test_the_note_records_the_divergence_and_its_grade(self):
        """The entry has to say which byte the vendor names and that the grade
        is not taken from it, or a reader meets a `present-untested` fan byte
        with no explanation."""
        self.assertIn('0x046B', self.note)
        self.assertIn('0x046D', self.note)
        self.assertIn('NOT the second fan', self.note)
        self.assertIn('present-untested', self.note)


class TestRetractionStaysPaired(unittest.TestCase):
    """The load-bearing claim of this change is a claim about the repository
    rather than about the firmware, and it is the kind a green suite does not
    otherwise catch.

    A `grep` that finds nothing is "not found by this method" -- which is
    exactly the error the sentence being retracted made: a statement about
    what one search failed to return, phrased as a statement about the tree.
    It then survived three review rounds, because it had been installed as
    the *corrected* form inside two otherwise append-only files, where an
    unreviewed reader inherits it as settled.

    So this class does **not** assert the wording is absent. CLAUDE.md's
    retraction pattern requires the wrong version to stay visible with the
    correction beside it, and a check that failed on its visibility would
    contradict the convention it is meant to protect. What it asserts instead
    is the pairing: a file that says the driver defines are unavailable must
    also say where they actually are. That is the property whose absence let
    the sentence stand three rounds -- a reader who landed on it had nothing
    further to read -- and it is checkable, so it is checked.
    """

    # The claim, in the wordings this repository has actually used for it. Each
    # is matched as a phrase rather than as a sentence, so a rewrite that
    # keeps the assertion trips it even when the sentence around it changes.
    PHRASES = (
        'not vendored here',
        'nowhere in this repo',
        'no EC address anywhere in this repo',
        'not recorded anywhere in this repository',
    )

    def files(self):
        """The files this change touches that could carry the sentence, plus
        the write-up beside them. `docs/findings.md` is included because two of
        its correction blocks quote the wording being retracted, which is the
        established pattern here rather than a lapse."""
        yield ROOT / 'docs' / 'findings.md'
        yield ROOT / 'ec' / 'annotations' / 'static-refs-audit.md'
        yield ROOT / 'ec' / 'annotations' / 'registers.yaml'
        yield ROOT / 'docs' / 'findings' / 'fan-tachometer-addresses.md'

    def test_a_retraction_always_names_the_committed_source(self):
        """Where the retracted wording appears, the committed excerpt has to
        appear in the same file. This is what fails if the claim is ever
        reinstated as a live assertion with nothing beside it."""
        for path in self.files():
            text = path.read_text()
            if not any(phrase in text for phrase in self.PHRASES):
                continue
            self.assertIn(
                'upstream-excerpt.txt', text,
                f'{path.relative_to(ROOT)} says the driver defines are '
                f'unavailable without naming where they are committed, which '
                f'is how that sentence survived three review rounds')

    def test_the_correction_is_actually_present(self):
        """The negative above is satisfied by a file that never made the
        claim, so the other half is asserted directly: each corrected file
        carries a dated correction block for this change."""
        for path in (ROOT / 'docs' / 'findings.md',
                     ROOT / 'ec' / 'annotations' / 'static-refs-audit.md'):
            text = path.read_text()
            self.assertIn('upstream-excerpt.txt', text,
                          f'{path.relative_to(ROOT)} drops the retracted '
                          f'wording without replacing it with the committed '
                          f'excerpt it should name instead')
            self.assertIn('issue #29', text,
                          f'{path.relative_to(ROOT)} carries no dated '
                          f'correction block for this change')

    def test_the_excerpt_quotes_no_function_body(self):
        """The boundary the correction turns on: the excerpt carries no EC
        access, so how the driver reads or writes a byte is not re-derivable
        from this tree.

        Asserted as a search for the access idioms rather than as a check on
        the shape of the quoted lines, because the excerpt is not defines-only
        and a shape test would have been both wrong and easy to pass
        vacuously: an empty-string entry in a `startswith` tuple matches every
        string, which is what an earlier draft of this test did and what let a
        false "quotes #define lines only" claim stand while the suite was
        green. If a future refresh of the excerpt starts quoting a body, this
        fails and the correction's wording is re-read rather than left
        standing on a stale reading of the file."""
        text = EXCERPT.read_text()
        for idiom in ('regmap_bulk_read', 'regmap_read', 'be16_to_cpu',
                      'ec_read', 'ec_write', '~('):
            self.assertNotIn(
                idiom, text,
                f'the excerpt now contains {idiom!r}, so it quotes a function '
                f'body; the correction in static-refs-audit.md and '
                f'docs/findings.md rests on it not doing so')

    def test_the_excerpt_quotes_each_feature_bit(self):
        """The `UNIWILL_FEATURE_*` assigns are the other half of what the
        excerpt carries beyond the defines, and they are what tie a §2
        feature name to an upstream symbol offline."""
        text = EXCERPT.read_text()
        for symbol, bit in (('UNIWILL_FEATURE_PRIMARY_FAN', 8),
                            ('UNIWILL_FEATURE_SECONDARY_FAN', 9),
                            ('UNIWILL_FEATURE_TOUCHPAD_TOGGLE', 2),
                            ('UNIWILL_FEATURE_USB_POWERSHARE', 14)):
            pattern = (r'^\s*\d+:\s*#define\s+' + re.escape(symbol) +
                       r'\s+BIT\(' + str(bit) + r'\)\s*$')
            self.assertIsNotNone(
                re.search(pattern, text, re.MULTILINE),
                f'{symbol} BIT({bit}) is not quoted in '
                f'linux/patches/gm7mg7p-dmi-entry/upstream-excerpt.txt')


if __name__ == '__main__':
    unittest.main()
