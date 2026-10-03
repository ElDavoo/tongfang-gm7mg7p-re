#!/usr/bin/env python3
"""A prepared patch's description of the tool it wires, held to that tool.

`docs/ci/agent-gates-*.patch` is what `CLAUDE.md` and
`docs/agent-pipeline.md` call for: `.github/scripts/agent-gates.sh` is copied
from the agent-pipeline template and the pipeline's push token has no
`workflow` scope, so a branch editing it fails at the *end* of a PR. Each patch
carries the gate change in a header and a comment at the call site, and a human
lands it by copying the `git apply` line.

`tools/test_agent_gates_patches.py` holds that set's *applicability*: every
patch applies alone, and every ordered pair composes. This holds what each
patch says about the tool it wires. Those are separate properties and the
second was unwatched: a patch whose prose describes a checker that has since
changed still applies perfectly, still composes, and still passes every case in
the sibling suite -- and the sentence it lands into `.github/scripts/agent-gates.sh`
is the permanent description of the rule the gate runs.

The defect is a count in a "what it reads" or "what it counts" sentence.
Descriptions this suite reads were stale when it was written, which is what
makes an exception set mandatory rather than optional: the ones left
uncorrected are enumerated in `KNOWN_STALE` below with the owner of each, and
each key is held in the live direction too (see `ExceptionTests`). The census,
with the command behind every figure, is
`docs/findings/prepared-patch-description-census.md`.

**What this checks, and what it cannot.** For each patch whose tool prints a
figure the patch quotes, run the tool as a subprocess and require the patch to
carry the figure it prints. Separately, for each tool, read the input roots the
tool names in its own module constants and require each to appear in the gate
comment -- an omitted input tree is the sentence a reader deciding what the
cheap tier may read is actually reading.

It cannot check prose. A patch claiming a tool "catches regression X" or is
"cheap because it reads one CSV" is a reading, not a number, and this suite
says nothing about either. Nor can it check a figure the tool derives rather
than prints: `agent-gates-disasm8051-self-test.patch`'s "36 assertions in all"
is a sum over five groups the tool reports separately, so there is no single
printed line to compare it to, and it is recorded in the census as a derived
sum rather than asserted here. Both bounds are the §4a rule applied to this
file: not checked by this method, never absent.

**The exception set is mandatory, not optional.** An asserting suite is red on
the day it lands if the descriptions it reads are already stale, and they are.
`KNOWN_STALE` is keyed on `(patch, claim)` and every key is held both ways, so
a description corrected anywhere makes its key fail and says to drop it. That
is what makes the exemption an enumerated fact rather than a hole. The bound is
the sibling's: *a claim already wrong is exempt by construction; a new one is
not.*

**A patch not in the table is not a patch nobody has read.** `PATCHES` names
what this suite compares and `NOT_HELD` names what it does not and why, and a
case holds the two against the tree in both directions -- the completeness
direction the sibling asserts for applicability. Without it the census read as
a census of the set while covering part of it, which is a scan that covered
part of the tree written up as if it covered all of it: the same defect as a
zero-hit scan called `absent`, and the reason the bound is an enumeration here
rather than a silence.
"""
import collections
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
CI = REPO / 'docs' / 'ci'

# The two halves of a patch's prose: the header a human reads before applying,
# and the comment the patch adds at the call site, which is what lands in
# `agent-gates.sh` and becomes the gate's permanent description. A claim in
# either is a claim the gate carries, and the header is checked beside the
# comment rather than instead of it because they drifted apart in the set: the
# capture-claims header names four input trees and one of its three gate
# comments names two.
HEADER = 'header'
COMMENT = 'comment'


def header_of(text):
    """The comment block above the first `diff --git`, with the `#` stripped.

    The same span `tools/test_agent_gates_patches.py`'s `header()` takes, and
    the same reason: everything before the diff is what a human reads, and
    filtering on `#` would silently drop a line that lost its marker.
    """
    cut = text.find('diff --git ')
    head = text if cut < 0 else text[:cut]
    lines = [line.lstrip('#').strip() for line in head.splitlines()]
    return ' '.join(line for line in lines if line)


def added_comment(text):
    """The comment lines the patch adds, `#` stripped, joined by spaces.

    Only `+` lines inside the diff body, and only those that are comments --
    a `+` line that is shell is not a description of the tool. `+++ b/…` names
    the file rather than contributing to it and is excluded, as it is in the
    sibling's `added_lines()`.
    """
    cut = text.find('diff --git ')
    body = text[cut:] if cut >= 0 else text
    out = []
    for line in body.splitlines():
        if not line.startswith('+') or line.startswith('+++'):
            continue
        stripped = line[1:].strip()
        if stripped.startswith('#'):
            out.append(stripped.lstrip('#').strip())
    return ' '.join(out)


def prose(patch):
    """The two prose halves of one patch, keyed by `HEADER` and `COMMENT`."""
    text = (REPO / patch).read_text()
    return {HEADER: header_of(text), COMMENT: added_comment(text)}


# What each patch's tool prints, and what the patch is required to carry. The
# key is the patch; the value names the tool to run and the figures to compare.
#
# `figure` is a regex with one group, matched against the tool's combined
# output, and the patch must contain that captured text. Matching the tool's
# own output rather than hard-coding the expected number is the whole of what
# makes this a check rather than a copy: the figure comes off the run, and the
# patch has to agree with it.
#
# `roots` are the input trees the tool names in its own module constants, each
# required to appear in the gate comment. Read out of the tool rather than
# listed here by hand where possible -- `TOOL_ROOTS` below names the constant
# and this resolves it -- because a hand-kept list of a module's constants is
# the same kind of claim this suite exists to catch.
PATCHES = {
    'docs/ci/agent-gates-0751-self-test.patch': {
        'tool': ['python3', 'ec/tools/grade_0751_isolation.py', '--self-test'],
        'figure': r'test_grade_0751_isolation\.py: (\d+) tests, passed',
        'where': [HEADER],
        'roots': [],
    },
    'docs/ci/agent-gates-0751-writer-census.patch': {
        'tool': ['python3', 'ec/tools/census_xdata_writers.py', '--check'],
        # Only the total, which is what the gate comment quotes. The run splits
        # it three ways -- writers, read-only sites, and the `sites_for()`
        # total -- and the comment says "which of the 29 sites store", so the
        # total is the figure it is required to carry. The header's own half
        # spells its counts as words ("the ten writer sites"), which is prose
        # this suite cannot compare; see the census row.
        'figure': r'of (\d+) found by sites_for\(\)',
        'where': [COMMENT],
        'roots': [],
    },
    'docs/ci/agent-gates-disasm8051-self-test.patch': {
        'tool': ['python3', 'ec/tools/disasm8051.py', '--self-test'],
        'figure': r'all (\d+) relative-branch sites resolve',
        'where': [HEADER],
        'roots': [],
    },
    'docs/ci/agent-gates-gap-text-check.patch': {
        'tool': ['python3', 'ec/tools/verify_gap_text.py', '--check'],
        'figure': r'gap text verdicts: (\d+) agree',
        'where': [HEADER],
        'roots': [],
    },
    'docs/ci/agent-gates-pin-table-rows.patch': {
        'tool': ['python3', 'ec/tools/check_pin_table_rows.py'],
        'figure': r'(\d+) table row\(s\) against \d+ census record',
        'where': [HEADER],
        'roots': [],
    },
    'docs/ci/agent-gates-testdata-row-claims.patch': {
        'tool': ['python3', 'ec/tools/check_testdata_row_claims.py', '--check'],
        # Two groups from one line -- `shape_label()` prints the shapes count
        # and the dated-refusal count together -- and the patch has to carry
        # both, so the figures are a list and every element is required.
        'figure': r'under the (\w+) shapes and the (\w+) dated refusals',
        'where': [HEADER],
        'roots': ['ec/tools/check_testdata_row_claims.py'],
    },
    'docs/ci/agent-gates-capture-claims.patch': {
        # This patch wires four checks and quotes no figure from any of them,
        # so only the root half of the check applies to it -- and the root it
        # is given is `check_capture_claims.py`'s, the one whose gate comment
        # is the thinnest of the four. `figure` is absent rather than a
        # pattern that matches nothing, because "the tool printed a figure and
        # the patch does not carry it" and "this tool prints no figure the
        # patch claims" are different findings and only the second is this one.
        'tool': ['python3', 'ec/tools/check_capture_claims.py', '--check'],
        'where': [],
        'roots': ['ec/tools/check_capture_claims.py'],
    },
}

# Patches on disk that `PATCHES` above does not hold, keyed on why. The bound
# has to be an enumeration rather than a silence: the sibling
# (`tools/test_agent_gates_patches.py`) holds the completeness direction for
# applicability and says why -- "a new one is picked up silently by the glob" --
# and a table that only checks its own entries cannot see a patch arriving
# outside it. The census that read part of the set was read as a census of all
# of it, which is the same defect as a zero-hit scan called `absent`: part of
# the set was never examined and nothing said so.
#
# Each reason is a shape of claim, not an excuse. None of these patches quotes a
# figure its tool prints, which is the one thing the figure comparison can see;
# each row of `docs/findings/prepared-patch-description-census.md` records what
# the patch says, what the tool says and the reading, beside the command.
NOT_HELD = {
    'docs/ci/agent-gates-bank-map-score.patch':
        'quotes no figure either tool prints: "outside the three its '
        'classifier can produce" is a count of `firmware_regions.py`\'s '
        '`ERASED`/`NON_ERASED`/`UNCLASSIFIED`, spelled as a word, and a '
        'derived sum over constants is what this suite is documented as not '
        'checking',
    'docs/ci/agent-gates-cross-decoder-disagreement.patch':
        'quotes no printed figure: "each of the five causes" is a count of the '
        'closed vocabulary the `--check` run enumerates one label at a time, '
        'spelled as a word -- the same derived-sum shape as the disasm row the '
        'census records',
    'docs/ci/agent-gates-findings-frozen.patch':
        'quotes no figure its tools print: what it carries is what '
        '`tools/README.md` and `docs/findings/test-line-pin-census.md` *were* '
        '-- a hand-kept total with supersession notes under it, dated '
        'per-merge headings -- and the checks this same patch wires are what '
        'removed both, so the figures are a record of a past tree rather than '
        'a claim about this one',
    'docs/ci/agent-gates-reassembly-bound-check.patch':
        'quotes no figure its tool prints: "0.15 s here over three runs" is a '
        'timing on one runner, which the header itself calls one runner\'s '
        'figure, and the 5.9 s beside it is `docs/agent-pipeline.md`\'s cheap '
        'tier rather than an output of `reassembly_checked_bound.py`',
}

# Which module constant of each tool names its input trees. Read rather than
# transcribed: a tree added to a tool without a line here is invisible to this
# suite, which is the same blind spot the set already had once, so a case below
# asserts each named constant still exists and still resolves.
#
# `CAPTURES` is not a literal -- it is `os.path.normpath(os.path.join(EC,
# os.pardir, WATCH))` -- so `root_of()` follows it to the constant it is built
# from, which is the honest form of the check: this holds that the capture root
# is still derived from `WATCH`, not what `normpath` returns for it.
TOOL_ROOTS = {
    'ec/tools/check_testdata_row_claims.py': 'CAPTURES',
    'ec/tools/check_capture_claims.py': 'WATCH',
}

# The value each literal input-root constant must read. A constant built from
# another name is resolved to *that* constant's key, which is why this is
# keyed by constant name and not by tool.
ROOT_VALUES = {
    'WATCH': 'evidence/ec-watch',
}

# A description that is wrong today, keyed on `(patch, the text it claims)`.
#
# The key is the sentence the patch actually carries, so it is falsifiable by
# reading the patch: correct that sentence and the key stops matching anything
# and the case below says so. The value is the *owner* of the correction,
# because the issue that produced this suite scoped the other descriptions to
# be reported rather than edited, and a bare "stale" would leave the next
# reader with nowhere to go.
#
# **A key records no figure, and that is the point.** The obvious thing to
# write beside a stale claim is what the tool prints in its place, and for two
# of these it is a count of this repository's own tests: a value every merge
# that adds a test case has to edit, in a table nothing else makes anyone
# edit. The direction that needs it is already the second assertion in
# `test_every_stale_key_is_still_wrong` -- `assertNotIn(_quoted_figure(claim),
# printed)` -- and it asks its question off the run, so it keeps holding when
# the figure moves.
#
# **An owner is a file in this repository, not an issue number.** An issue
# closes and its number goes on naming work nobody is doing, and a reader
# cannot tell a closed one from a live one by looking at it: two of these
# descriptions were first attributed to issues that have since closed, which
# left the suite reporting them as owned and the corrections unowned.
# `test_every_stale_key_names_an_owner` holds the replacement by requiring the
# owner to name a file that is there.
#
# `KNOWN_STALE` is not a backlog to drain here. The census records what each
# claim is and where the correction is recorded.
KNOWN_STALE = {
    ('docs/ci/agent-gates-0751-self-test.patch', '103 committed tests'):
        "`docs/ci/agent-gates-0751-self-test.patch`'s own header, which "
        "assigns the other occurrences of that figure to issue #685",
    ('docs/ci/agent-gates-pin-table-rows.patch', '105 rows of the per-pin'):
        "`docs/findings/prepared-patch-description-census.md`, *Read and not "
        "corrected*, where the row-count claim and the red tool it describes "
        "are recorded as follow-up work",
}

# Which prose half each root must appear in. The capture root is what the cheap
# tier is allowed to read, and that is a statement about the gate comment -- the
# text that lands at the call site -- rather than about the header, which is
# read once by whoever applies the patch.
ROOT_WHERE = COMMENT


def run(tool):
    """`(returncode, stdout+stderr)` for one tool, run against this tree.

    A subprocess rather than an import, and that is deliberate twice over.
    `ec/tools/`'s sibling imports only resolve with that directory on
    `sys.path`, so importing would put this suite in the arrangement
    `check_testdata_row_claims.py`'s own header argues against reproducing.
    And a tool run as the gate runs it is the tool the gate would run: the
    figure this suite compares is the one a reader would see, not the one an
    in-process call happens to return.

    `cwd` is the repository because that is where the gate's cwd is, and two
    of these tools resolve a path from `__file__` and would be indifferent.

    **The return code is carried but not asserted, deliberately.** What this
    suite holds is a *description* against a *figure*, and a tool that exits
    non-zero can still print the figure its patch quotes. Asserting the code
    would make this a second copy of every tool's own gate, and one of them is
    red on this tree for a reason recorded in the census, so the assertion
    would go red here over a fact about the tool rather than about any
    description. `stdout` and `stderr` are merged, so the code and the figure
    arrive together and every failure message quotes both. The bound is the
    suite's: a patch whose tool is red is a census row, and the census is where
    that reading lives.
    """
    done = subprocess.run(tool, cwd=REPO, capture_output=True, text=True)
    return done.returncode, done.stdout + done.stderr


def figures(tool_out, pattern):
    """The capture groups of `pattern` in `tool_out`, or None if it did not match.

    None rather than an empty list so a pattern that stops matching the tool is
    distinguishable from one that matches nothing: the first is a broken check
    and the second is a tool that printed no figure.
    """
    found = re.search(pattern, tool_out)
    return None if found is None else [g for g in found.groups() if g]


def tool_constant(path, name):
    """A module-level constant read out of `path` by parsing it, not running it.

    `ast` over the assignment, so nothing in the tool is executed to read its
    own configuration. That matters for the same reason `run()` uses a
    subprocess: a suite that imports the tools to inspect them inherits their
    import-time behaviour, and a tool that reads the firmware at import would
    make this suite depend on that read.

    A literal is returned as its value. Anything else -- `CAPTURES` is
    `os.path.normpath(os.path.join(...))` -- is returned as the set of names its
    expression mentions, so a caller can see *what it is built from* without
    this suite re-deriving the tool's own path arithmetic. None means the
    constant is not assigned at module level at all, which is a different
    answer from either and the case below says so.
    """
    import ast
    tree = ast.parse((REPO / path).read_text())
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(t, ast.Name) and t.id == name
                   for t in node.targets):
            continue
        try:
            return ast.literal_eval(node.value)
        except ValueError:
            return {n.id for n in ast.walk(node.value)
                    if isinstance(n, ast.Name)}
    return None


def root_of(tool):
    """The input tree `tool` reads, from the constant that names it.

    Two steps, because the two tools declare it differently.
    `check_capture_claims.py` assigns `WATCH` to the literal, so the constant
    *is* the tree. `check_testdata_row_claims.py` imports that same `WATCH`
    and builds `CAPTURES` from it with `os.path.join(EC, os.pardir, WATCH)` --
    so its own expression mentions `EC` and `os` as well, and the tree is one
    hop further on.

    The hop is taken to the name the constant **imports**, not to the only name
    its expression mentions: `EC` and `os` are the tool's own locals, and
    following them would mean re-deriving the path arithmetic this suite
    exists to avoid carrying a second copy of. `_imported_names` asks which of
    them came in from another module, and exactly one of those is the tree's
    own. `test_each_named_root_constant_still_reads_as_it_did` is what says so
    when that stops being true.
    """
    source = TOOL_ROOTS[tool]
    value = tool_constant(tool, source)
    if isinstance(value, str):
        return value
    imported = (value or set()) & _imported_names(tool)
    name = _sole_name(imported)
    if name is None:
        return None
    # One hop only: the constant this one is built from is defined in some
    # tool, and that tool's own value is the literal.
    owner = _constant_owner(name)
    return tool_constant(owner, name) if owner else None


def _imported_names(tool):
    """The names `tool` brought in with `from … import`, at module level."""
    import ast
    tree = ast.parse((REPO / tool).read_text())
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            out.update(alias.asname or alias.name for alias in node.names)
    return out


def _constant_owner(name):
    """Which declared tool assigns `name` at module level, or None."""
    for tool, source in TOOL_ROOTS.items():
        value = tool_constant(tool, source)
        names = {source} if isinstance(value, str) else (value or set())
        if name in names and tool_constant(tool, name) is not None:
            return tool
    return None


def _sole_name(names):
    """The one name in a set, or None when there is not exactly one."""
    return next(iter(names)) if names and len(names) == 1 else None


class PatchDescriptionTests(unittest.TestCase):
    """Every patch's prose against what its tool prints.

    Each case runs the tool rather than comparing two strings, so a figure that
    moves on the next merge to the tool fails here rather than being restated
    in a second place.
    """

    def test_the_table_names_a_patch_that_exists(self):
        gone = sorted(set(PATCHES) - {p.relative_to(REPO).as_posix()
                                      for p in CI.glob('agent-gates-*.patch')})
        self.assertFalse(
            gone,
            f'{len(gone)} patch(es) in this suite\'s table are not in '
            f'docs/ci/: ' + ', '.join(gone) +
            '. A renamed or folded patch would leave the cases below checking '
            'a file that is not there.')

    def test_every_patch_on_disk_is_accounted_for(self):
        # The direction the table above does not check, and the one the census
        # needed. `test_the_table_names_a_patch_that_exists` holds PATCHES
        # against the tree; nothing held the tree against PATCHES, so a patch
        # landing in `docs/ci/` joined the unwatched half silently and the
        # census read as a census of the set while covering part of it. The
        # sibling suite asserts this same direction for applicability and
        # gives the reason in one line: a new one is picked up silently by the
        # glob.
        on_disk = {p.relative_to(REPO).as_posix()
                   for p in CI.glob('agent-gates-*.patch')}
        for name in (PATCHES, NOT_HELD):
            orphans = sorted(set(name) - on_disk)
            self.assertFalse(
                orphans,
                f'{len(orphans)} name(s) in a table here are not in '
                f'docs/ci/: ' + ', '.join(orphans) +
                '. A renamed or folded patch leaves the table naming a file '
                'that is not there, and the reason recorded for a patch that '
                'no longer exists describes nothing.')
        unaccounted = sorted(on_disk - set(PATCHES) - set(NOT_HELD))
        self.assertFalse(
            unaccounted,
            'these patches in docs/ci/ are in neither this suite\'s table nor '
            'its exclusion set: ' + ', '.join(unaccounted) + '. One in neither '
            'is a patch nobody has read, which is the gap this suite exists to '
            'close: give it an entry in PATCHES if it quotes a figure its tool '
            'prints, or in NOT_HELD with the reason there is nothing to '
            'compare -- and record the reading in the census either way.')

    def test_each_patch_carries_the_figure_its_tool_prints(self):
        for patch, spec in sorted(PATCHES.items()):
            if not spec.get('figure'):
                # A patch quoting no figure has nothing here to be wrong about;
                # `test_each_gate_comment_names_every_input_tree_its_tool_reads`
                # is what holds it.
                continue
            with self.subTest(patch=patch):
                code, out = run(spec['tool'])
                printed = figures(out, spec['figure'])
                self.assertIsNotNone(
                    printed,
                    f'{patch} quotes a figure from `{" ".join(spec["tool"])}` '
                    f'and this suite cannot find it in the output (exit {code}). '
                    'Either the tool stopped printing it or stopped printing it '
                    'in that shape; both mean the patch is describing something '
                    'this suite can no longer check, which is worth knowing.')
                said = prose(patch)
                for where in spec['where']:
                    if exempt(patch, where, said):
                        # An enumerated stale sentence lives in this half, so
                        # what the tool prints is not what this half is
                        # required to carry. `ExceptionTests` is what holds
                        # the key rather than this skip.
                        continue
                    for figure in printed:
                        self.assertIn(
                            figure, said[where],
                            f'{patch} does not carry {figure!r}, which '
                            f'`{" ".join(spec["tool"])}` prints (exit {code}). '
                            f'The {where} describes the tool as it is not.'
                            + _not_enumerated())

    def test_each_gate_comment_names_every_input_tree_its_tool_reads(self):
        for patch, spec in sorted(PATCHES.items()):
            for tool in spec['roots']:
                with self.subTest(patch=patch, tool=tool):
                    root = root_of(tool)
                    self.assertIsNotNone(
                        root, f'{tool} names no input tree this suite can '
                              'read; see '
                              'test_each_named_root_constant_still_reads_as_it_did')
                    said = prose(patch)
                    if exempt(patch, ROOT_WHERE, said):
                        continue
                    comment = said[ROOT_WHERE]
                    self.assertIn(
                        root, comment,
                        f'{patch} does not name {root!r} in its gate comment, '
                        f'and {tool} reads it. That comment is what lands in '
                        '`.github/scripts/agent-gates.sh` as the gate\'s '
                        'permanent description of what the cheap tier may '
                        'read, so a reader deciding whether the check is cheap '
                        'is reading a list with a tree missing from it.'
                        + _not_enumerated())

    def test_each_named_root_constant_still_reads_as_it_did(self):
        # The direction that keeps the root honest. A root asserted against the
        # tool's own constant is only as good as that constant, and one that is
        # renamed, rebuilt or dropped leaves the case above comparing a comment
        # against a path nothing reads.
        for tool, source in sorted(TOOL_ROOTS.items()):
            with self.subTest(tool=tool):
                self.assertIsNotNone(
                    tool_constant(tool, source),
                    f'{tool} no longer assigns {source} at module level. The '
                    'root this suite requires a gate comment to name is read '
                    'out of that constant, so the cases above would be '
                    'comparing a comment against nothing. Point TOOL_ROOTS at '
                    'whatever names the tree now.')
                root = root_of(tool)
                self.assertIsNotNone(
                    root,
                    f'{tool}\'s {source} does not resolve to a tree this suite '
                    'can read. It is either built from a name no declared tool '
                    'assigns, or from more than one; either way the cases above '
                    'are now vacuous, because `assertIn(None, ...)` is a '
                    'TypeError rather than a pass and the root check below is '
                    'the one that should say so.')
                # A root that resolved but names a tree nobody records is a
                # path this suite made up, which is the vacuous-pass shape
                # `tools/run-tests.sh`'s empty-discovery guard exists for.
                self.assertIn(
                    root, ROOT_VALUES.values(),
                    f'{tool}\'s {source} resolves to {root!r}, which is not a '
                    'root in ROOT_VALUES, so this suite is holding a gate '
                    'comment against a path it invented. Add the tree to '
                    'ROOT_VALUES under the constant that names it.')


class ExceptionTests(unittest.TestCase):
    """`KNOWN_STALE` is an enumerated fact, held in both directions.

    An exemption that nothing checks is a hole with a comment on it. Each key
    is asserted twice: the quoted text is still in the patch, so the key still
    names something real; and the tool does not print the figure the key's
    sentence quotes, so the key is still needed. Correct a description anywhere
    and the first assertion fails and says to drop the key -- which is the only
    thing that makes it safe to leave the wrong descriptions uncorrected. Both
    are read off a run, so neither is a figure this table has to be edited
    into when one of them moves.

    The reverse direction matters for the same reason and is what stops the set
    growing: a key that never matched any patch is a claim about a sentence
    that does not exist, and it is as wrong as a stale one.
    """

    def test_every_stale_key_still_quotes_its_patch(self):
        for (patch, claim) in sorted(KNOWN_STALE):
            with self.subTest(patch=patch, claim=claim):
                text = (REPO / patch).read_text()
                self.assertIn(
                    claim, header_of(text) + ' ' + added_comment(text),
                    f'{patch} no longer carries {claim!r}, so the KNOWN_STALE '
                    'key for it is dead. The description was corrected -- drop '
                    'the key, so the exemption stops covering a claim that is '
                    'now right.')

    def test_every_stale_key_is_still_wrong(self):
        for (patch, claim), owner in sorted(KNOWN_STALE.items()):
            with self.subTest(patch=patch, claim=claim):
                self.assertIn(
                    patch, PATCHES,
                    f'KNOWN_STALE names {patch}, which is not in PATCHES, so '
                    'nothing checks whether the claim it quotes is still '
                    'wrong. Add the patch to PATCHES, or drop the key.')
                spec = PATCHES[patch]
                code, out = run(spec['tool'])
                printed = figures(out, spec['figure'])
                self.assertIsNotNone(
                    printed,
                    f'{patch} carries no figure pattern in this suite\'s table, '
                    'so nothing can tell whether the claim its key quotes is '
                    'still wrong. Give the entry a `figure`, or drop the key.')
                # Read off the run, not off the table: the figure the tool
                # prints is a count of this repository's own tests, and holding
                # one here is a value every merge that adds a case has to edit.
                quoted = _quoted_figure(claim)
                # Before comparing it, because `assertNotIn` cannot make that
                # distinction: a key quoting no figure yields None, and
                # `assertNotIn(None, printed)` is True for any list of strings,
                # so without this the "is it still wrong" direction passes
                # unconditionally for such a key -- and the exemption silences
                # the asserting case for that patch's whole `where` half with
                # nothing checked. The docstring on `_quoted_figure` says a key
                # quoting prose "must say so rather than read as a checked
                # one", and this is what says it.
                self.assertIsNotNone(
                    quoted,
                    f'the KNOWN_STALE key for {patch} quotes {claim!r}, which '
                    'carries no standalone figure for this suite to compare '
                    'against the run. A key that quotes prose exempts that '
                    'patch\'s half from the asserting cases and cannot be held '
                    'to still being wrong, which is a hole with a comment on '
                    'it. Give the key a figure the tool prints, or drop it and '
                    'record the reading in the census instead -- the census '
                    'is where a claim this suite cannot judge belongs.')
                self.assertNotIn(
                    quoted, printed,
                    f'{patch} quotes {claim!r} and its tool now prints that '
                    f'figure too, so the claim is no longer stale. The '
                    f'exception ({owner}) can be dropped, and the patch should '
                    'be corrected if the two still disagree.')

    def test_every_stale_key_names_an_owner(self):
        for (patch, claim), owner in sorted(KNOWN_STALE.items()):
            with self.subTest(patch=patch, claim=claim):
                # An exemption with no owner is a deferral with no name on it,
                # which is how a stale description outlives the branch that
                # found it.
                self.assertTrue(
                    owner.strip() and not owner.lower().startswith('tbd'),
                    f'the KNOWN_STALE key for {patch} ({claim!r}) names no '
                    'owner for its correction. Name where it is recorded, or '
                    'correct the description and drop the key.')
                # And an owner that is a bare issue number is the same hole
                # with a number on it. The issue closes; the number goes on
                # naming work nobody is doing, and nothing in this repository
                # distinguishes a closed one from a live one -- two of these
                # descriptions were first attributed to issues that have since
                # closed, and the suite reported them as owned. This cannot
                # reach GitHub to ask, so it holds the shape that cannot rot
                # instead: an owner names a file here, and the file is there.
                named = _owner_paths(owner)
                self.assertTrue(
                    named,
                    f'the KNOWN_STALE key for {patch} ({claim!r}) gives its '
                    f'owner as {owner!r}, which names no file in this '
                    'repository. An issue number is not an owner -- it closes, '
                    'and a closed one reads exactly like a live one. Name the '
                    'file recording where the correction is tracked.')
                for path in named:
                    self.assertTrue(
                        (REPO / path).exists(),
                        f'the KNOWN_STALE key for {patch} ({claim!r}) names '
                        f'{path!r} as where its correction is tracked, and '
                        'there is no such file here.')


def _quoted_figure(claim):
    """The figure a stale claim quotes, or None when it quotes none.

    The first standalone run of digits in the quoted text, which is what every
    current key quotes. A key quoting prose instead is a claim this suite
    cannot judge and must say so rather than read as a checked one.
    """
    found = re.search(r'(?<![\w.])\d+(?![\w.])', claim)
    return found.group(0) if found else None


def exempt(patch, where, said):
    """The owner of an enumerated stale claim in `patch`'s `where` half, or None.

    The single place the asserting cases consult `KNOWN_STALE` through, so a
    key and the case it silences cannot disagree about what a key is: both go
    through this, and the second direction -- that a key is still *needed* --
    is `ExceptionTests`.

    Matched on the sentence the patch carries, and on the half of the prose
    being checked. What the tool prints today is a count this repository's own
    next merge moves, and matching on it would put that count in the exemption
    table -- see the note above `KNOWN_STALE`. A key whose sentence has been
    corrected matches nothing here, which is
    `test_every_stale_key_still_quotes_its_patch` saying so by name.
    """
    for (stale_patch, claim), owner in sorted(KNOWN_STALE.items()):
        if stale_patch == patch and claim in said.get(where, ''):
            return owner
    return None


def _not_enumerated():
    """The trailing note for a claim the suite is about to fail on.

    One branch rather than two: an enumerated claim is skipped above the
    assertion, so a failure here is by construction a claim nothing has
    claimed, and the message says what to do about that.
    """
    return ('\n\nIf this is a claim already known to be wrong, add it to '
            'KNOWN_STALE with the file recording where its correction is '
            'tracked; a claim already wrong is exempt by construction, a new '
            'one is not.')


def _owner_paths(owner):
    """The repository paths an owner names, read out of its backticks.

    What `test_every_stale_key_names_an_owner` requires at least one of, so
    that an owner is somewhere a reader can go rather than a number that may
    or may not still be open.
    """
    return re.findall(r'`([^`]+)`', owner)


class ParseTests(unittest.TestCase):
    """The prose parse, on inline patch text.

    Without these the cases above are one bad regex away from passing
    vacuously -- a parse that found no header matches a patch whose header
    carries no claim, which is the same defect as a run that found nothing.
    """

    TEXT = '\n'.join([
        '# A header naming a figure.',
        '',
        'diff --git a/f b/f',
        '--- a/f',
        '+++ b/f',
        '@@ -1 +1 @@',
        '+# A comment naming an input tree.',
        '+check_x() {',
        '+  true',
        '+}',
        ' context',
    ])

    # A patch whose prose halves are both empty: no header comment above the
    # diff, and no `+#` line inside it. This is what a patch looks like after a
    # rewrite drops the sentence rather than correcting it.
    BARE = '\n'.join([
        'diff --git a/f b/f',
        '--- a/f',
        '+++ b/f',
        '@@ -1 +1 @@',
        '+check_x() {',
        '+  true',
        '+}',
    ])

    def test_the_header_stops_at_the_diff(self):
        self.assertEqual(header_of(self.TEXT), 'A header naming a figure.')

    def test_the_comment_keeps_only_added_comment_lines(self):
        # `check_x() {` is a `+` line and not a comment; taking it would make
        # the comment half describe shell rather than the tool.
        self.assertEqual(added_comment(self.TEXT),
                         'A comment naming an input tree.')

    def test_a_patch_with_no_diff_yields_its_whole_text(self):
        self.assertEqual(header_of('# just prose\n'), 'just prose')
        self.assertEqual(added_comment('# just prose\n'), '')

    def test_a_prose_half_with_no_claim_reads_as_empty(self):
        # The other direction: a rewritten patch that dropped the sentence
        # entirely must read as empty rather than as clean, because empty is
        # what the asserting cases need -- `assertNotIn(claim, '')` is the
        # failure that says the claim is gone. Asserting the emptiness is the
        # whole point, so this compares the halves against `''` directly
        # rather than slicing them: `[:0]` is `''` for every possible input,
        # which is the vacuous-pass shape these cases exist to catch.
        self.assertEqual(header_of(self.BARE), '')
        self.assertEqual(added_comment(self.BARE), '')


if __name__ == '__main__':
    unittest.main()
