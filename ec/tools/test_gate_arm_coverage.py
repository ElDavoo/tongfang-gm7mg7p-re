#!/usr/bin/env python3
"""Cases for `check_gate_arm_coverage.py`.

The checker's subject is the *relationship* between two halves of one shell
function, so every case here is a scratch gate script and a verdict. The
substantive cases are the ones that go red, and each asserts that the run
**names the tool or the pattern** rather than merely failing: a red run that
says "coverage problem" sends a reader looking, and one that says
"`ec/tools/xdata_register_map.py` is in the list and no arm dispatches it"
does not.

Three of these are the reason the tool exists:

  - `test_the_318_shape_goes_red_and_names_the_tool` is issue #318 as a
    fixture. The tool was in the gate's list with no `case` arm for it, and
    the issue was filed because nothing said so. Run as a case, that is a red
    run rather than an issue.
  - `test_a_dead_glob_goes_red` is the direction a one-way check fails. A
    renamed tool leaves its arm behind; the glob matches nothing, the tool
    takes `*)`, and the run is *green* if the fallback's flags happen to
    parse. This is the case that decides whether the check is worth having.
  - `test_adding_a_tool_with_a_correct_arm_is_green` is the "not a census"
    case. If this went red, the tool had grown a count of the list and would
    have to be edited by every landing tool.

Scratch trees, never `.github/`. Every mutation is a `tempfile` copy, and
`TheCommittedTreeIsUnchanged` holds the working tree byte-identical across a
run, because the one file this reads is the one several open agent PRs collide
on.
"""

import ast
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.abspath(os.path.join(HERE, os.pardir))
REPO = os.path.abspath(os.path.join(HERE, os.pardir, os.pardir))
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

import check_gate_arm_coverage as gac  # noqa: E402

GATE_REL = os.path.join(".github", "scripts", "agent-gates.sh")
COMMITTED_GATE = os.path.join(REPO, GATE_REL)


def committed_gate():
    with open(COMMITTED_GATE, encoding="utf-8") as handle:
        return handle.read()


def committed_docstring(rel):
    """A committed tool's module docstring, for a scratch tree that needs it.

    The claim direction reads docstrings out of the repo it is pointed at, so a
    scratch tree carrying only a gate script has no claims to check at all. The
    case that wants the committed tree's one real claim therefore copies the
    real docstring rather than a paraphrase of it -- a paraphrase that happened
    to contain the phrase the predicate looks for would be a fixture passing for
    the wrong reason.
    """
    path = os.path.join(REPO, rel.replace("/", os.sep))
    with open(path, encoding="utf-8") as handle:
        return ast.get_docstring(ast.parse(handle.read())) or ""


def add_to_tool_list(text, tool):
    """The gate script with `tool` appended to the `for` list.

    Anchored on the list's own terminator rather than on the `case`: the `for`
    ends at `; do`, so an insertion before `case "$tool" in` would land after
    the loop and add nothing at all -- a fixture that reads as green because it
    changed nothing, which is the one shape this suite must not contain.
    """
    marker = "              windows/tools/decompile_native.py; do\n"
    if marker not in text:
        raise AssertionError("the tool list's terminator moved")
    return text.replace(marker,
                        "              windows/tools/decompile_native.py \\\n"
                        "              %s; do\n" % tool)


def drop_arm(text, pattern):
    """The committed gate with one `case` arm removed, label through `;;`."""
    regex = re.compile(r"[ ]*\*" + re.escape(pattern) + r"\)\n(?:.*\n)*?[ ]*;;\n")
    out, n = regex.subn("", text)
    if n != 1:
        raise AssertionError("expected exactly one %s arm, removed %d"
                             % (pattern, n))
    return out


class ScratchTreeCase(unittest.TestCase):
    """A temp directory per case, torn down after it."""

    def setUp(self):
        self.roots = []

    def tearDown(self):
        for root in self.roots:
            shutil.rmtree(root, ignore_errors=True)

    def scratch_repo(self, files):
        root = tempfile.mkdtemp()
        self.roots.append(root)
        for rel, text in files.items():
            path = os.path.join(root, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(text)
        return root

    def scratch_gate(self, mutate=None, docstrings=None):
        """A scratch repo holding a copy of the gate script, and run over it.

        `docstrings` writes scratch tool files, so the claim direction can be
        driven from a fixture rather than from the committed tree's one real
        claim -- which is the only way to show the same docstring is red with
        no arm and green with one.
        """
        text = committed_gate() if mutate is None else mutate(committed_gate())
        files = {GATE_REL: text}
        for rel, doc in (docstrings or {}).items():
            files[rel] = ('"""%s"""\n' % doc)
        root = self.scratch_repo(files)
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = gac.check(root, quiet=True)
        return rc, buf.getvalue()


class TheCommittedScript(ScratchTreeCase):
    """The tree as committed: the two halves agree today."""

    def test_the_committed_script_is_clean(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = gac.check(REPO, quiet=True)
        self.assertEqual(rc, 0, buf.getvalue())

    def test_the_parse_reads_a_list_and_arms_and_is_not_vacuous(self):
        # An empty parse matches an empty list, which is the §14b defect the
        # runner's empty-discovery guard exists for. Both directions of the
        # comparison above need a non-empty subject to be a comparison.
        body = gac.function_body(committed_gate())
        tools = gac.tool_list(body)
        parsed = gac.arms(body)
        self.assertTrue(tools, "no tools read out of the committed list")
        self.assertTrue(parsed, "no arms read out of the committed case")
        self.assertTrue(any(gac.is_fallback(p) for p, _ in parsed),
                        "no `*)` arm read, so the fallback exemption is untested")

    def test_the_fallback_arm_names_the_tools_it_is_the_fallback_for(self):
        # The direction-1 exemption is read out of this comment rather than
        # from a table here, so the table and the arm cannot disagree. If the
        # arm's comment were dropped the exemption would silently empty and
        # red the committed tree; this is the assertion that it did not.
        parsed = gac.arms(gac.function_body(committed_gate()))
        own = gac.fallback_own_tools(
            [b for p, b in parsed if gac.is_fallback(p)][0])
        self.assertTrue(own, "the `*)` arm names no tool of its own")

    def test_a_gate_script_that_cannot_be_read_refuses_rather_than_passing(self):
        # A checker that cannot find its target must not read as a clean pass.
        # Missing and unparseable are the two ways, and they are separate
        # failures: one is an absent file, the other is a file this cannot
        # find the function or the tool list in.
        root = self.scratch_repo({})
        buf = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(buf):
            rc = gac.check(root, quiet=True)
        self.assertEqual(rc, 2, buf.getvalue())
        self.assertIn("cannot be read", buf.getvalue())

        for broken in ("#!/bin/sh\necho nothing here\n",
                       "check_ghidra_tooling() {\n  echo hi\n",
                       "check_ghidra_tooling() {\n"
                       "  for tool in ; do\n  done\n}\n"):
            root = self.scratch_repo({GATE_REL: broken})
            buf = io.StringIO()
            with redirect_stdout(buf), redirect_stderr(buf):
                rc = gac.check(root, quiet=True)
            self.assertEqual(rc, 2,
                             "an unparseable script passed as clean: %r"
                             % broken)

    def test_a_case_with_no_fallback_arm_refuses(self):
        # The shape that would otherwise decide the exemption by accident. A
        # `case` with no `*)` has no fallback and so nothing to exempt, and
        # whether each undispatched tool is a finding or an error turns on
        # which tools the missing fallback would have covered -- so it is a
        # refusal rather than a guess.
        root = self.scratch_repo({GATE_REL: committed_gate().replace(
            "      *)\n", "      # no fallback here\n")})
        buf = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(buf):
            rc = gac.check(root, quiet=True)
        self.assertEqual(rc, 2, buf.getvalue())
        self.assertIn("no `*)` arm", buf.getvalue())


class DirectionOneListedSoDispatched(ScratchTreeCase):
    """Every listed tool is dispatched, or the fallback claims it by name."""

    def test_the_318_shape_goes_red_and_names_the_tool(self):
        # The case this tool exists for. `xdata_register_map.py` in the list
        # with no arm for it is what issue #318 reported; here it is a fixture,
        # so the next one is a red run instead of an issue.
        rc, out = self.scratch_gate(
            mutate=lambda t: drop_arm(t, "xdata_register_map.py"))
        self.assertEqual(rc, 1, out)
        self.assertIn("ec/tools/xdata_register_map.py", out)
        self.assertIn("no `case` arm", out)

    def test_the_same_state_also_fails_the_claim_direction(self):
        # The other end of the same state, and the one that would have read
        # the docstring: the tool's own claim stops being true. The scratch
        # tree carries the committed docstring, because direction 3 reads the
        # repo it is pointed at and a scratch tree has no claims otherwise.
        rc, out = self.scratch_gate(
            mutate=lambda t: drop_arm(t, "xdata_register_map.py"),
            docstrings={"ec/tools/xdata_register_map.py":
                        committed_docstring("ec/tools/xdata_register_map.py")})
        self.assertEqual(rc, 1, out)
        self.assertIn("says it lives in the gate", out)
        self.assertIn("ec/tools/xdata_register_map.py", out)

    def test_adding_a_tool_to_the_list_with_no_arm_goes_red_and_names_it(self):
        # The other way to reach #318's state: the tool was never listed at
        # all. Named in the failure, so the reader knows which line to add.
        rc, out = self.scratch_gate(
            mutate=lambda t: add_to_tool_list(t, "ec/tools/some_new_tool.py"))
        self.assertEqual(rc, 1, out)
        self.assertIn("ec/tools/some_new_tool.py", out)

    def test_adding_a_tool_with_a_correct_arm_is_green(self):
        # **Not a census.** If this were red, the tool had grown a count of
        # the list, and every landing tool would have to edit it -- which is
        # the failure `CLAUDE.md` records four times over. This is the case
        # that keeps it membership.
        def add(t):
            return add_to_tool_list(t, "ec/tools/some_new_tool.py").replace(
                "      *gen_xdata_symbols.py)\n",
                "      *some_new_tool.py)\n"
                "        python3 \"$tool\" --check || rc=1\n"
                "        ;;\n"
                "      *gen_xdata_symbols.py)\n")

        rc, out = self.scratch_gate(mutate=add)
        self.assertEqual(rc, 0, out)

    def test_a_tool_the_fallback_comment_names_is_exempt(self):
        # The committed arm's own comment is what exempts the two `--work`
        # tools, so the exemption is read from the script rather than from a
        # copy of it in this file. Adding a third `--work` tool and naming it
        # there must not need an edit here.
        def add(t):
            return t.replace(
                "              ec/tools/check_status_vocabulary.py \\\n",
                "              ec/tools/check_status_vocabulary.py \\\n"
                "              ec/tools/third_work_tool.py \\\n").replace(
                "# build_ec_decompile.py and bios_extract.py both take --work.",
                "# build_ec_decompile.py, bios_extract.py and third_work_tool.py"
                "\n        # all take --work.")

        rc, out = self.scratch_gate(mutate=add)
        self.assertEqual(rc, 0, out)


class DirectionTwoDispatchedSoListed(ScratchTreeCase):
    """Every `case` pattern matches a listed tool. The other direction."""

    def test_a_dead_glob_goes_red_and_names_the_pattern(self):
        # The case a one-way check fails. The arm survives a tool rename; the
        # glob matches nothing; the tool takes `*)` and the run is green if
        # the fallback's flags happen to parse.
        rc, out = self.scratch_gate(
            mutate=lambda t: t.replace(
                "      *call_graph.py)\n",
                "      *call_graph_renamed.py)\n"))
        self.assertEqual(rc, 1, out)
        self.assertIn("*call_graph_renamed.py", out)
        self.assertIn("matches no tool", out)

    def test_a_dead_glob_for_a_fallback_tool_is_red_with_no_orphaned_tool(self):
        # Direction 2 alone, and the case that shows it is not redundant with
        # direction 1. The glob is pointed at nothing *and* names a tool the
        # `*)` arm already claims, so no listed tool loses its dispatch and
        # direction 1 has nothing to say -- a check with only direction 1 is
        # green here.
        #
        # `build_ec_decompile.py` is the subject because the `*)` arm's comment
        # names it, so an arm pointed at it is a dispatch of something the
        # fallback already handles: harmless to the run, and still a glob that
        # reaches nothing. This is the stale-arm shape that survives a rename
        # and is not visible from the tool list.
        rc, out = self.scratch_gate(
            mutate=lambda t: t.replace(
                "      *call_graph.py)\n",
                "      *call_graph_renamed.py)\n        :\n        ;;\n"
                "      *build_ec_decompile_renamed.py)\n"
                "        python3 \"$tool\" --check || rc=1\n"
                "        ;;\n"
                "      *call_graph.py)\n"))
        self.assertEqual(rc, 1, out)
        self.assertIn("matches no tool", out)
        # Both stale globs are named, and nothing is reported as an undispatched
        # listed tool -- the list and the arms agree, which is the whole point.
        self.assertIn("*call_graph_renamed.py", out)
        self.assertIn("*build_ec_decompile_renamed.py", out)
        self.assertNotIn("and no `case` arm dispatches it", out)

    def test_an_arm_matching_several_tools_dispatches_all_of_them(self):
        # `*grade_name_basis.py|*group_functions.py` is a real arm covering
        # two tools. A check that read only the first pattern of an arm would
        # call the second a dead glob, so this is what holds the split.
        rc, out = self.scratch_gate()
        self.assertEqual(rc, 0, out)


class DirectionThreeClaimsAgainstReality(ScratchTreeCase):
    """A docstring claiming a place in the gate has an arm that runs it."""

    CLAIM = ("No image, no network, which is what lets this live in "
             "`.github/scripts/agent-gates.sh` beside the other self-tests.")

    def test_a_claim_with_no_arm_is_red_and_names_the_tool(self):
        rc, out = self.scratch_gate(
            mutate=lambda t: drop_arm(t, "xdata_register_map.py"),
            docstrings={"ec/tools/claiming_tool.py": self.CLAIM})
        self.assertEqual(rc, 1, out)
        self.assertIn("ec/tools/claiming_tool.py", out)
        self.assertIn("says it lives in the gate", out)

    def test_the_same_claim_with_an_arm_is_green(self):
        # The pair that makes direction 3 a claim-checked-against-reality and
        # not a substring test: identical docstring, opposite verdicts, and the
        # only difference is the arm.
        def add(t):
            return add_to_tool_list(t, "ec/tools/claiming_tool.py").replace(
                "      *gen_xdata_symbols.py)\n",
                "      *claiming_tool.py)\n"
                "        python3 \"$tool\" --check || rc=1\n"
                "        ;;\n"
                "      *gen_xdata_symbols.py)\n")

        rc, out = self.scratch_gate(mutate=add,
                                    docstrings={"ec/tools/claiming_tool.py":
                                                self.CLAIM})
        self.assertEqual(rc, 0, out)

    def test_a_docstring_declining_the_gate_is_not_a_claim(self):
        # The boundary that makes this usable. Most of this tree's docstrings
        # name the gate to decline it, and a predicate that fired on the path
        # alone would be red on every one of them -- which is how a gate
        # teaches everyone to ignore it.
        declining = [
            "It is not in `.github/scripts/agent-gates.sh`, and cannot be "
            "from an agent branch.",
            "This is **not registered in any gate**: "
            "`.github/scripts/agent-gates.sh` is a pipeline file.",
            "Neither is in the committed `.github/scripts/agent-gates.sh`, "
            "and the reason is that a branch cannot edit it.",
            "No job calls it: `.github/scripts/agent-gates.sh` runs "
            "`run-tests.sh` nowhere.",
        ]
        for docstring in declining:
            rc, out = self.scratch_gate(
                docstrings={"ec/tools/declining_tool.py": docstring})
            self.assertEqual(rc, 0, "%r read as a claim:\n%s"
                             % (docstring, out))

    def test_a_claim_about_the_syntax_check_is_not_a_tool_list_claim(self):
        # `pd_image_census.py`'s true claim that it runs under the gate's
        # `python3 syntax` check. "run under" is deliberately not a membership
        # phrasing, so the real tree and this fixture agree.
        rc, out = self.scratch_gate(docstrings={
            "ec/tools/syntax_checked.py":
                "It does run under `.github/scripts/agent-gates.sh`'s "
                "`python3 syntax` check, which globs every tool directory."})
        self.assertEqual(rc, 0, out)

    def test_a_claim_split_across_two_lines_is_still_a_claim(self):
        # Several docstrings wrap the path, and a docstring that names the gate
        # across a line break is still naming it.
        rc, out = self.scratch_gate(docstrings={
            "ec/tools/wrapped_claim.py":
                "No image, which is what lets this live in "
                "`.github/scripts/agent-gates.sh`\nnext to the others."})
        self.assertEqual(rc, 1, out)
        self.assertIn("ec/tools/wrapped_claim.py", out)


class TheCommittedTreeIsUnchanged(unittest.TestCase):
    """The checker reads `.github/` and writes nothing, least of all there."""

    @staticmethod
    def _status():
        proc = subprocess.run(["git", "status", "--porcelain"], cwd=REPO,
                              capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            raise unittest.SkipTest("git is not available here")
        return proc.stdout

    def test_every_mode_leaves_the_tree_byte_identical(self):
        # Same shape `test_xdata_program_keyed_table.py` uses for the same
        # reason. The file this reads is the one several open agent PRs
        # collide on, so a checker that rewrote it would be a merge conflict
        # wearing a gate's clothes.
        before = self._status()
        for argv in ([], ["--check"], ["--quiet"]):
            proc = subprocess.run(
                [sys.executable, os.path.join("ec", "tools",
                                              "check_gate_arm_coverage.py")]
                + argv, cwd=REPO, capture_output=True, text=True, check=False)
            self.assertEqual(proc.returncode, 0, argv + [proc.stdout, proc.stderr])
        self.assertEqual(self._status(), before)


if __name__ == "__main__":
    unittest.main()