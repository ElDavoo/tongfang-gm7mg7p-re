#!/usr/bin/env python3
"""The checker's refusals that `--self-test` does not make, and the process.

`tools/check_deep_schedule_emit.py --self-test` already holds the schedule's
shape on typed fixtures. Two things it deliberately does not do are the two
this file is for, and both are the ones that would let it pass while having
stopped working.

**The fixtures are the tool's own idea of the file.** Every rule in `scan()` was
written beside a `schedule_text()` that produces the shape those rules expect,
so a rule and its fixture agreeing proves very little. What is not circular is a
mutation of the *committed* file, and that is why `--schedule` exists: it lets
each mutation here run as a **subprocess** over a copy, so what the case sees
is the exit code a consumer sees. Patching `SCHEDULE` in-process could not --
the tool's own `main()` reads the module constant, and a case that reached past
it to set the constant would be testing the patch as much as the rule.

**`--self-test` running is not the same as `--self-test` passing.** The self-test
is the tool's own answer sheet, and a self-test that raised before its last
assertion would look the same from outside as one that passed, unless something
turns its return value into a process status. The first case here is that
something.

The negative controls are what make the green mean anything. `scan()`'s comment
strip is the clause that keeps the schedule's own explanations inside the
`run:` block from reading as a `--limit` flag, and a strip that removed nothing
would leave every other case here passing -- so the strip is held from both
sides, by a comment that must not fire and by a flag that must. The header hold
is pinned to a transcription of the column list rather than to
`verify_reassembly.py`'s own, so the writer cannot grade its own homework; and
`NOT_COMPARED` is pinned by value, because a diff that compared `assembler`
would report all 2,705 rows as moved every night and would still be correct
about every row it printed.

**No count is asserted.** Not the schedule's uploads, not the report's rows:
both move with the tree, and an expected count turns every added row into a
failure. What is held is non-emptiness, agreement, and the exit code -- the
properties that are true of the tree rather than of this tool. Nothing here
runs a nightly: `docs/ci/agent-gates-deep-schedule.yml` is prepared, not
landed, so there is no artifact to read and no hardware, no assembler and no
Windows is involved beyond the committed firmware the tool reads by name.
"""
import csv
import hashlib
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import check_deep_schedule_emit as tool  # noqa: E402

HERE = Path(__file__).resolve().parent
REPO = HERE.parent

# What `verify_reassembly.write_report()` writes as its first row, transcribed
# here rather than read from the tool. The tool's header hold compares the
# writer's output to the committed report's, which is the coupling that
# matters; this is the third point, so a column that moved on *both* sides at
# once -- a `--add-digest-column` rerun, say -- is not quietly accepted by two
# agreeing halves. `check_doc_figure_pins.py`'s reason: hold the code, not the
# number.
REPORT_COLUMNS = ["program", "addr", "name", "outcome", "listing_digest",
                  "instructions_checked", "instructions_unchecked", "detail",
                  "assembler"]


def run_tool(*argv):
    """The tool as a subprocess: (returncode, stdout, stderr).

    A subprocess rather than an in-process call throughout, because for a
    checker the exit code is the product and nothing in-process turns a
    return value into a status. Captured rather than inherited, so a refusal's
    own words land in the assertion's message and not in the suite's output,
    where the next real failure would be the one a reader has to find.
    """
    done = subprocess.run(
        [sys.executable, str(HERE / "check_deep_schedule_emit.py"), *argv],
        capture_output=True, text=True, cwd=str(REPO))
    return done.returncode, done.stdout, done.stderr


class ProcessTests(unittest.TestCase):
    """The run, because for a checker `main()` is the product and its exit code
    is the whole of it."""

    def test_self_test_passes_and_the_run_is_green(self):
        rc, out, _err = run_tool("--self-test")
        self.assertEqual(rc, 0, out)
        self.assertIn("all assertions passed", out)

    def test_check_on_the_committed_tree_is_green_with_a_quiet_stderr(self):
        rc, out, err = run_tool("--check")
        self.assertEqual(rc, 0, out + err)
        self.assertEqual(err, "", "a clean --check says nothing on stderr; a "
                                   "reader routing streams cannot tell a "
                                   "verdict from a note")
        self.assertIn("two artifacts", out)

    def test_check_holds_the_two_artifacts_the_schedule_leaves(self):
        # Named rather than counted. A count would be satisfied by a schedule
        # with two copies of the same artifact, which is the claim that would
        # be false -- upload-artifact v4+ merges equal names into one.
        _rc, out, _err = run_tool("--check")
        self.assertIn("2 upload-artifact step(s), 2 named", out)

    def test_a_schedule_that_is_not_there_is_reported_not_a_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc, _out, err = run_tool("--schedule", str(Path(tmp) / "gone.yml"))
        self.assertEqual(rc, 1)
        self.assertIn("cannot read", err)


class MutationTests(unittest.TestCase):
    """One case per way the committed schedule can stop being what it claims.

    Each mutates a **copy of the real file** and runs `--check` over it, so the
    rule and the expectation are both about the file a human will copy into
    `.github/workflows/` rather than about a fixture this tool wrote.
    """

    def setUp(self):
        self.real = tool.SCHEDULE.read_text(encoding="utf-8")
        # A guard rather than an assumption: every mutation below is a
        # substitution into this text, and a string that is not present would
        # make the case assert against an unmutated file and pass for the
        # wrong reason.
        self.assertIn("--emit-csv", self.real)

    def _mutated(self, mutate):
        """`--check` as a subprocess over a mutated copy, as (rc, out, err).

        The `assertNotEqual` is the load-bearing half and it is why this is a
        helper rather than a `subprocess` call per case: a substitution whose
        text is not present leaves the file unmutated, and a case written
        against a string that moved would then assert against the real
        schedule and pass for a reason that has nothing to do with the rule.
        """
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "mutated.yml"
            before, after = self.real, mutate(self.real)
            self.assertNotEqual(before, after,
                                "the mutation changed nothing, so this case "
                                "would pass without testing the rule")
            path.write_text(after, encoding="utf-8")
            return run_tool("--schedule", str(path))

    def refuses(self, mutate, needle):
        rc, out, err = self._mutated(mutate)
        self.assertEqual(rc, 1, "a mutated schedule was accepted:\n" + out)
        self.assertIn(needle, out + err)
        return out

    def accepts(self, mutate, needle):
        """The other half: an edit that must *not* turn the check red.

        Every helper that only refuses is satisfied by a `scan()` that refuses
        everything, so the mutations here are the ones that look like defects
        and are not -- a comment naming a flag, a `#` inside a path.
        """
        rc, out, err = self._mutated(mutate)
        self.assertEqual(rc, 0, "an edit that changes nothing went red:\n"
                                 + out + err)
        self.assertIn(needle, out)
        return out

    def test_the_unmutated_copy_is_green(self):
        # The control for every case below. Without it, a `scan()` that refused
        # everything would pass all of them.
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "copy.yml"
            path.write_text(self.real, encoding="utf-8")
            rc, out, err = run_tool("--schedule", str(path))
        self.assertEqual(rc, 0, out + err)

    def test_two_uploads_sharing_a_name(self):
        self.refuses(lambda t: t.replace("name: deep-gates-csv-${{ github.run_id }}",
                                         "name: deep-gates-${{ github.run_id }}"),
                     "share a name")

    def test_an_artifact_name_without_the_run_id(self):
        self.refuses(lambda t: t.replace("name: deep-gates-csv-${{ github.run_id }}",
                                         "name: deep-gates-csv"),
                     "does not carry ${{ github.run_id }}")

    def test_the_csv_upload_collecting_the_committed_report(self):
        # The `refuses_committed_report` invariant as a held claim rather than
        # a comment about `runner.temp`.
        self.refuses(lambda t: t.replace(
            "path: ${{ runner.temp }}/deep-gates-csv.csv",
            "path: ${{ github.workspace }}/ec/ghidra/reassembly.csv"),
            "names the committed report")

    def test_the_csv_upload_outside_runner_temp(self):
        self.refuses(lambda t: t.replace(
            "path: ${{ runner.temp }}/deep-gates-csv.csv",
            "path: ${{ github.workspace }}/tmp/deep-gates-csv.csv"),
            "not rooted at ${{ runner.temp }}")

    def test_the_emit_step_sampling_the_firmware(self):
        self.refuses(lambda t: t.replace("--jobs 4 \\", "--jobs 4 --limit 100 \\"),
                     "passes --limit")

    def test_the_emit_step_pinning_a_nix_assembler(self):
        self.refuses(lambda t: t.replace("SDAS8051='' python3",
                                         "SDAS8051=/nix/store/x/bin/sdas8051 python3"),
                     "sets SDAS8051 to `/nix/store/x/bin/sdas8051`")

    def test_the_emit_step_never_pinning_the_assembler(self):
        self.refuses(lambda t: t.replace("SDAS8051='' python3", "python3"),
                     "never pins SDAS8051")

    def test_the_second_upload_step_removed(self):
        # Not a refutation of a rule: the *count* hold. "Two artifacts" is
        # half a sentence, and the other half is the one this is.
        self.refuses(lambda t: t.split("      - name: Upload the deep gates CSV")[0],
                     "1 upload-artifact step(s)")

    def test_an_upload_that_is_not_always(self):
        self.refuses(lambda t: t.replace(
            "        if: always()\n        uses: actions/upload-artifact@",
            "        if: success()\n        uses: actions/upload-artifact@"),
            "not `if: always()`")

    def test_a_comment_in_the_run_block_is_not_a_flag(self):
        # The negative control for the comment strip, and the case that decides
        # whether the tool survives a week. The committed schedule's own emit
        # step has to explain *why* it passes no `--limit` and why it pins
        # `SDAS8051`, and both sentences are inside the `run:`. A rule that
        # fired on the sentence stating it would go red on the correct file --
        # which is how a gate gets switched off rather than fixed.
        out = self.accepts(
            lambda t: t.replace("          rc=0",
                                "          # no --limit, and SDAS8051 is not set\n"
                                "          rc=0"),
            "the shape is as documented")
        self.assertIn("--emit-csv writes $RUNNER_TEMP/deep-gates-csv.csv", out,
                      "and the destination is still read out of the command, "
                      "not out of the comment")

    def test_a_hash_in_a_path_is_not_a_comment(self):
        # The other side of the strip. `#` is only a comment at the start of a
        # line or after whitespace, so a `#` inside a path cannot swallow the
        # argument that follows it.
        self.refuses(lambda t: t.replace('--emit-csv "$RUNNER_TEMP/deep-gates-csv.csv"',
                                         '--emit-csv "$RUNNER_TEMP/nope#1.csv"'),
                     "no upload-artifact collects")

    def test_a_destination_held_in_a_shell_variable(self):
        # Deliberate: the file that is written and the file that is uploaded
        # are only holdable to be the same one if the destination is readable
        # without resolving a shell assignment first.
        # Refused on the clause that fires rather than the one that was
        # intended: `"$out"` *is* readable as an argument, so the destination
        # is found and then found not to be under $RUNNER_TEMP. Both are
        # refusals; only the second is this edit's.
        self.refuses(lambda t: t.replace('--emit-csv "$RUNNER_TEMP/deep-gates-csv.csv"',
                                         '--emit-csv "$out"'),
                     "which is not under $RUNNER_TEMP")


class HeaderCouplingTests(unittest.TestCase):
    """Holds 4 and 5, from outside the tool that reads them."""

    def test_the_committed_report_carries_the_columns_the_writer_writes(self):
        fields, rows, dupes = tool.read_rows(tool.REPORT)
        self.assertEqual(fields, REPORT_COLUMNS,
                         "the committed report's header is not the column list "
                         "`write_report()` writes; a `--diff` joining the two "
                         "would be reading two different tables")
        self.assertTrue(rows, "the committed report has no row: the join would "
                              "be comparing nothing")
        self.assertEqual(dupes, [], "the committed report has a duplicate "
                                    "(program, addr) key")

    def test_the_header_the_writer_produces_is_the_committed_one(self):
        problems, held = tool.header_coupling()
        self.assertEqual(problems, [], "\n".join(problems))
        self.assertEqual(held, 2, "both the header hold and the refusal hold "
                                  "were evaluated")

    def test_this_tool_and_verify_reassembly_agree_on_which_file_is_the_report(self):
        # The coupling the header hold rides on: it compares against a path
        # built from the report's *name*, so if `verify_reassembly.REPORT` moved
        # the two could be reading different files and still agreeing.
        verify = tool.load_verify()
        self.assertEqual(os.path.realpath(verify.REPORT),
                         os.path.realpath(tool.REPORT))

    def test_not_compared_is_the_assembler_column_and_nothing_else(self):
        # Pinned by value because the consequence is quiet: `assembler` is the
        # one column whose whole job is to differ between a nightly and the
        # committed report, and comparing it would report every row as moved.
        self.assertEqual(tool.NOT_COMPARED, ("assembler",))
        for column in tool.NOT_COMPARED:
            self.assertIn(column, REPORT_COLUMNS,
                          "a column this diff declines to compare is not in "
                          "the report, so the exclusion is naming nothing")


class DiffRunTests(unittest.TestCase):
    """`--diff` as a process, on the committed report and on copies of it."""

    def test_the_report_joined_against_itself_moves_nothing(self):
        # The property the join has to have before it can be trusted on two
        # *different* files, asserted on the real 2,705 rows rather than a
        # fixture. The count is never held by value: this asserts the words and
        # the exit code, both of which survive the report being re-cut.
        rc, out, _err = run_tool("--diff", str(tool.REPORT), str(tool.REPORT))
        self.assertEqual(rc, 0, out)
        self.assertIn("no row moved", out)

    def test_one_changed_outcome_is_one_moved_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            edited = Path(tmp) / "edited.csv"
            with open(tool.REPORT, newline="", encoding="utf-8") as f:
                reader = csv.reader(f)
                header, rows = next(reader), list(reader)
            rows[0][3] = ("mismatch" if rows[0][3] != "mismatch" else "match")
            with open(edited, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f, lineterminator="\n")
                writer.writerow(header)
                writer.writerows(rows)
            rc, out, _err = run_tool("--diff", str(edited), str(tool.REPORT))
        self.assertEqual(
            rc, 0,
            "a row that moved is a reading, not a failure: §14h measured 52 of "
            "them between this report and the apt build a runner installs\n"
            + out)
        self.assertIn("1 row(s) moved", out)
        self.assertIn("outcome", out)
        self.assertIn("  moved  %s %s " % (rows[0][0], rows[0][1]), out,
                      "and the moved row is named by its (program, addr) key, "
                      "which is what makes the diff joinable against a report "
                      "whose rows are in a different order")

    def test_a_missing_file_is_2_and_not_1(self):
        # Distinct from both the empty and the disagreeing answers, so a reader
        # can tell "I could not look" from "I looked and they differ".
        with tempfile.TemporaryDirectory() as tmp:
            _rc, _out, err = run_tool("--diff", str(Path(tmp) / "nope.csv"),
                                      str(tool.REPORT))
        self.assertEqual(_rc, 2)
        self.assertIn("no such file", err)

    def test_help_reaches_every_mode(self):
        # Otherwise reached by nothing at all, since every other invocation here
        # names a mode.
        rc, out, _err = run_tool("--help")
        self.assertEqual(rc, 0)
        for flag in ("--check", "--diff", "--self-test", "--schedule"):
            self.assertIn(flag, out)


class NoWriteTests(unittest.TestCase):
    """Nothing in the tool writes to the tree it reads."""

    def test_a_full_run_leaves_the_working_tree_untouched(self):
        # The `refuses_committed_report` invariant seen from the other side: the
        # invariant is that a run has no second writer for the committed report,
        # and the only way to hold that for a *new* mode is to run every mode
        # and see the tree come back byte-identical.
        before = _tree_digest()
        for argv in (("--check",), ("--self-test",),
                     ("--diff", str(tool.REPORT), str(tool.REPORT))):
            run_tool(*argv)
        self.assertEqual(_tree_digest(), before,
                         "a run wrote to the tree it reads")


def _tree_digest():
    """A digest of every file this tool's modes could plausibly write to.

    The two reports, the schedule and the verify tool: the paths named in this
    file and in the tool. Not the whole tree -- `run-tests.sh` writes nothing,
    and a digest of 4,000 files to assert "this module opens no files for
    writing" is a slow way to say the same thing.
    """
    digest = hashlib.sha256()
    for path in (tool.SCHEDULE, tool.REPORT, tool.VERIFY):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


if __name__ == "__main__":
    unittest.main()
