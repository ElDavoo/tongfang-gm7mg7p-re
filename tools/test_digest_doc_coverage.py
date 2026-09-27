#!/usr/bin/env python3
"""Every tool with a `--write-digests` mode names it on its component's page.

`c-digests.csv` gives every committed `.c` a SHA-256, and `--write-digests` is
the command that refreshes it. The mode is a step in a *workflow*, not a flag
among others: a person who follows a documented re-export and then runs the
documented check gets a digest mismatch, and the one command that resolves it
has to be where they are already looking. When it lives in a different file
the failure looks like a corrupted tree.

That is not hypothetical and it has now recurred. When the digest landed, the
mode was documented in the three build-level pages --
`bios/ghidra/README.md`, `ec/ghidra/README.md`,
`windows/decompiled/native/README.md` -- and missed in two component pages
that a newcomer is likelier to open, one of which carries the canonical
regeneration recipe. The write-up is
`docs/findings/digest-docs-and-timings.md`.

**What this asserts, and what it does not.** A page that *enumerates a tool's
interface* -- a fenced command block, or a catalogued entry in a list -- is
listing the modes that tool has, and a mode missing from that list is a gap
in the enumeration. A page that mentions the tool in a sentence is not
enumerating anything, so there is nothing for it to be incomplete about, and
`windows/README.md` is the live case: it says what `decompile_native.py` wants
to run and nothing about how to run it. That asymmetry is why the rule below
keys on structure rather than on the tool merely being named.

The tools are discovered by reading them, not from a list of paths, so a fourth
one carrying the mode is covered by the fact that it exists rather than by
somebody remembering to add it here. The page is derived from where the tool
lives: a tool at `<component>/tools/<name>.py` is documented on
`<component>/README.md`.

This is a test rather than a gate. It adds no CI surface -- `tools/run-tests.sh`
is deliberately not called from `.github/scripts/agent-gates.sh` -- and it pins
no count, on the same reasoning as `tools/test_readme_suite_table.py`: the set
is the invariant, and comparing numbers would turn every added tool into a
failure.
"""
import os
import re
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
MODE = '--write-digests'

# The same pruning as the runner and as `test_readme_suite_table.py`, for the
# same reason: a `git worktree add` under `.claude/` is a second checkout
# inside this one, and a tool discovered there is one no reader of this tree can
# run. `vendor/` holds binaries.
PRUNED = ('.git', '.claude', 'vendor')

# A page that enumerates a tool's interface, as opposed to one that mentions it
# in a sentence. Two shapes, and both are things a reader reads as a list of
# what the tool accepts:
#
#   - a fenced block (` ``` ` on its own line) carrying the invocation, and
#   - a markdown list item, `| ` table row, or `**` bold lead naming the tool.
#     The bold lead is what `ec/README.md`'s `tools/build_ec_decompile.py`
#     bullet is: a catalogue entry for the tool, which is exactly as much an
#     enumeration as a command block.
#
# Anything outside those is prose, and prose that names a tool is not a
# specification of its flags. `windows/README.md` is what that exclusion buys,
# and it is the reason the rule is structural rather than "every `.md` that
# contains the tool's name".
FENCE = re.compile(r'^```', re.M)
LIST_ITEM = re.compile(r'^(?:[-*+]\s|\|\s|\*\*`?\w)', re.M)


def components():
    """-> {component: [tool paths]} for every tool carrying a digest mode."""
    found = {}
    for path in sorted(REPO.rglob('*.py')):
        rel = path.relative_to(REPO)
        if rel.parts[0] in PRUNED or len(rel.parts) < 2:
            continue
        try:
            source = path.read_text(encoding='utf-8', errors='replace')
        except OSError:
            continue
        if MODE in source:
            found.setdefault(rel.parts[0], []).append(rel.as_posix())
    return found


def enumerates(text, tool):
    """Whether `text` lists the interface of `tool` rather than naming it.

    The tool must appear on the structural line itself, not merely somewhere in
    the file: a fenced block that does not invoke the tool says nothing about
    its flags, and a list item that catalogues something else is not its
    catalogue entry.
    """
    name = os.path.basename(tool)
    for line in text.splitlines():
        if name not in line:
            continue
        if FENCE.match(line.strip()[:3]):
            # The fence itself carries no tool name, so this only fires for a
            # one-liner block; the multi-line case is handled below.
            return True
        if line.startswith('```') or line.startswith('|') or line.startswith('-') \
                or line.startswith('*') or line.startswith('**'):
            return True
    # A fenced block that opens on one line and invokes the tool on a later one,
    # which is how every command block in this repository is actually written.
    for block in re.findall(r'^```.*?^```', text, re.M | re.S):
        if name in block:
            return True
    return False


class DigestDocCoverageTests(unittest.TestCase):
    """The invariant itself, against the committed tree."""

    def test_the_tree_has_something_to_check(self):
        # A discovery that finds nothing compares equal to an empty expectation
        # and passes, which is the §14b shape: a check that has read nothing and
        # reports nothing wrong. If the mode is ever renamed, this is the case
        # that says so instead of the two below quietly going green.
        self.assertTrue(
            components(),
            'no tool under the repository root offers %s. If the mode was '
            'renamed, MODE is wrong; if the digest was removed, this suite has '
            'nothing left to hold.' % MODE)

    def test_every_component_page_enumerating_a_digest_tool_names_the_mode(self):
        gaps = []
        for component, tools in sorted(components().items()):
            readme = REPO / component / 'README.md'
            if not readme.is_file():
                gaps.append('%s: %s has %s but %s/README.md does not exist, so '
                            'the page a reader opens for this component cannot '
                            'name the mode'
                            % (component, ', '.join(tools), MODE, component))
                continue
            text = readme.read_text(encoding='utf-8')
            if MODE in text:
                continue
            for tool in tools:
                if enumerates(text, tool):
                    gaps.append('%s/README.md enumerates %s but never names %s'
                                % (component, tool, MODE))
        self.assertFalse(
            gaps,
            '%d component page(s) list a digest-refresh tool\'s modes without '
            'naming the mode:\n  ' % len(gaps) + '\n  '.join(gaps) +
            '\nA person who follows the re-export on that page, then runs the '
            'check on it, gets a digest mismatch whose fix is in a different '
            'file. Add the mode to the same block or list entry as the tool\'s '
            'other flags.')


class EnumeratesTests(unittest.TestCase):
    """The predicate itself, on inline documents.

    Without these, `enumerates` is a regex away from returning False for
    everything -- and False for everything is the shape that makes the case
    above pass having compared nothing.
    """

    def test_a_command_block_that_invokes_the_tool_enumerates_it(self):
        text = '\n'.join([
            'prose naming `bios_extract.py` in a sentence',
            '',
            '```',
            'python3 bios/tools/bios_extract.py --work /tmp/bios --check',
            '```',
        ])
        self.assertTrue(enumerates(text, 'bios/tools/bios_extract.py'))

    def test_a_catalogue_entry_naming_the_tool_enumerates_it(self):
        text = ('- **`tools/build_ec_decompile.py`** — builds the project, and '
                '`--mode rebuild-project` rewrites it.\n')
        self.assertTrue(enumerates(text, 'ec/tools/build_ec_decompile.py'))

    def test_a_sentence_mentioning_the_tool_does_not(self):
        # The live case: windows/README.md says what decompile_native.py wants
        # to run and lists none of its flags, so there is nothing there to be
        # an incomplete enumeration of.
        text = ('The .NET-side ones want `pefile` or `dnfile` from pip, and '
                '`decompile_native.py` is the Ghidra export scaffold, refused '
                'without `analyzeHeadless`.\n')
        self.assertFalse(enumerates(text, 'windows/tools/decompile_native.py'))

    def test_another_tool_s_block_is_not_this_tool_s_catalogue(self):
        # A fence that does not name the tool says nothing about its flags, and
        # a list item for a different file is not its row.
        text = '\n'.join([
            '- **`ecrw.py`** — the register writer',
            '```',
            'python3 ec/tools/grade_0751_isolation.py --csv out.csv',
            '```',
        ])
        self.assertFalse(enumerates(text, 'ec/tools/build_ec_decompile.py'))


if __name__ == '__main__':
    unittest.main()
