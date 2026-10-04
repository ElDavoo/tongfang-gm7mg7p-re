#!/usr/bin/env python3
"""Offline checks; no EC is opened and the vendor driver is never called.

`test_ctgp_dben_probe.py` holds the *bytes*: which arms the tool writes, which
bits those arms drive, and that the bits are the ones the committed annotation
rows name. What was missing is the other half of the handoff -- the **names**.
`docs/hardware-tests/ctgp-dben-07c4-bit3.md` §3 runs two captures and §6 lists
two files, and nothing held the two sets together, nor held the usage example
in `ctgp_dben_probe.py`'s docstring -- which is what `--help` prints, and so the
first spelling of a capture an operator meets -- against either. Three places
spell that document's capture names and all three have to agree, and an
operator following §3 verbatim has to land each §6 entry without a rename.

**Nothing here is behavioural.** The suite reads markdown, a module docstring
and `arm_bytes()`; it opens no capture, runs no probe and reaches no machine.
A green run says three sets of names agree, not that any run happened -- the
procedure's status header still reads *not run* (issue #284), and no file under
`evidence/` comes from it. The one phrase hold it started with was not enough:
a §6 could be right about the gate and still claim the capture records the byte
the run started from, which no CSV row holds, so the wording of *where* the
starting state is kept is held as well.

**Why this is a suite of its own rather than three more cases in
`test_ctgp_dben_probe.py`.** The whole of what it holds is *names*; the probe's
own `arm_bytes()` is the one property it reads out of the tool, and that is
already held there against the byte rather than against a file name. It is also
a stated non-merge the other way: `tools/test_hardware_test_artifacts.py`
holds §3 against §6 on the **basename**, on stated grounds --
`docs/findings/hardware-test-artifact-handoff.md` §"The decision: normalise the
prefix, not the command" -- and that decision is not reopened here. What is
checked is the half it gives up, for the one document whose §3 now spells the
directory out, plus the docstring nothing in the tree held against anything.

Like every suite in this directory that imports a tool importing `ecrw`, it
installs `ecrw_fake` the one way that works, by assignment.

Runs from inside the repository, which `tools/run-tests.sh` guarantees.
"""
import posixpath
import re
from pathlib import Path
import sys
import unittest

TOOLS = Path(__file__).parent
REPO = TOOLS.parent.parent
PROCEDURE = REPO / "docs" / "hardware-tests" / "ctgp-dben-07c4-bit3.md"

sys.path.insert(0, str(TOOLS))

import ecrw_fake  # noqa: E402  (needs the sys.path entry above)
ecrw_fake.install()

import ctgp_dben_probe as probe  # noqa: E402  (needs the fake ecrw above)

# The two-run split's premise, in the words §6 uses for it. Held as a phrase
# rather than as a behaviour, and the distinction is the point: what the tool
# does with `0x0743` is held in the probe's own suite against the byte, and
# this holds the sentence that tells an operator which starting state the file
# named `-gate-closed` was taken from. The filename reads as a window with the
# gate held off, and it is not one -- `arm_bytes()` sets bit 0 in both arms.
STARTING_CLAIM = ("is the byte the second run begins from, not a window "
                  "with the gate held off")

# What §6 has to say about where that starting byte is *recorded*, held for the
# same reason and because the phrase above is not sufficient on its own: a §6
# can be right about the gate and still claim the capture records the byte the
# run started from, which no CSV row carries. `arm_bytes(0x00)` and
# `arm_bytes(0x03)` are the same pair, and `sample()` re-reads `0x0743` on every
# sweep *after* the arm byte is written, so the only places the start state
# reaches are the filename and the console banner -- and a capture whose
# `ctrl_read` never shows it is the expected shape rather than a fault. Phrases
# again, in this suite's idiom: the byte half is `arm_bytes()` above, and this
# is the document saying where the difference is kept.
STARTING_BYTE_CLAIMS = ("not in either capture",
                        "What tells the two apart is the")

# The name the tool's usage example carried before, and the reason it was a
# defect rather than a variant: in neither §6 list, so an operator who copied it
# wrote a capture the index could not pair with the procedure that produced it.
# Asserted *absent* below, which gives the check a named wrong answer to fail
# on rather than leaving it satisfied by any reworded sentence.
RETIRED_NAME = "<date>-ctgp-dben-07c4-bit3.csv"


def fenced_blocks(text):
    """[(language tag, body)] for every fenced block in `text`, in order.

    Line-by-line rather than by regex, and the reason is worth stating because
    the regex is the obvious one and is wrong: an opening fence matches
    ``` followed by a newline, and so does a ```console block's *closing*
    fence. A document with a console block followed by its output section then
    reads the heading between them as a file list, which is a plausible answer
    rather than a wrong one. An opening fence may carry a language tag and a
    closing one never does, so the two are told apart by position.
    """
    blocks, tag, body, inside = [], None, [], False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            if inside:
                blocks.append((tag, "\n".join(body)))
                inside = False
            else:
                inside, tag, body = True, stripped[3:].strip(), []
            continue
        if inside:
            body.append(line)
    return blocks


def fenced(text, language):
    """The body of the first fence whose opening line carries `language`.

    Raises rather than yielding an empty string, for the reason the door's own
    reader gives: an empty span makes every check that reads it pass
    vacuously, which is the outcome worse than a document that has stopped
    carrying the thing at all. An empty tag is the plain ``` fence §6's list
    is written in.
    """
    for tag, body in fenced_blocks(text):
        if tag == language:
            return body
    raise AssertionError(f"no {language or 'plain'!r} fence in the document")


def section(text, heading):
    """The body of the named `## ` section, up to the next `## `.

    A missing heading raises for the same reason `fenced` does.
    """
    lines = text.splitlines()
    try:
        start = next(i for i, l in enumerate(lines)
                     if l.startswith(heading))
    except StopIteration:
        raise AssertionError(f"no {heading!r} in the document") from None
    body = lines[start + 1:]
    for i, line in enumerate(body):
        if line.startswith("## "):
            return "\n".join(body[:i])
    return "\n".join(body)


def console_commands(text):
    """§3's command lines, with the `rem` comments dropped.

    `rem` is how a cmd batch spells a comment and §3's own prose explains
    `--csv` by name, so reading either as a command is a check on the
    documentation rather than on the command it is about.
    """
    return "\n".join(line for line in fenced(text, "console").splitlines()
                     if not line.strip().startswith("rem"))


def listed_captures(text):
    """§6's file list, as paths with separators normalised.

    The list is written in a plain ``` fence rather than a ```console one, so
    it is found by that difference rather than by its position -- §3's console
    block closes with a bare ``` of its own, and a reader that took the first
    bare fence in the document would get that.
    """
    out = []
    for line in fenced(text, "").splitlines():
        line = line.strip()
        if line:
            out.append(line.replace("\\", "/"))
    return out


def written_captures(text):
    """The paths §3's commands pass to `--csv`, separators normalised."""
    return [p.replace("\\", "/")
            for p in re.findall(r"--csv\s+(\S+)", console_commands(text))]


def capture_problems(listed, written):
    """Every way §3's commands and §6's file list disagree, as a sorted list.

    Both directions, because they are the same defect seen from either side: a
    §6 entry no command writes is a name the operator cannot produce, and a
    `--csv` §6 does not name is a capture that lands where the index will not
    find it. Compared **whole**, with separators normalised, rather than on the
    basename -- which is the direction `tools/test_hardware_test_artifacts.py`
    takes, on the grounds its findings write-up records: the sibling procedures
    pass bare filenames, so requiring the directory would mean rewriting their
    §3 prose or a committed tool's documented invocation. That decision is not
    reopened here; this is the directory half it gives up, checked for the one
    document whose §3 spells the directory out.
    """
    problems = []
    for entry in listed:
        if entry not in written:
            problems.append(f"§6 names {entry}, which no command writes")
    for path in written:
        if path not in listed:
            problems.append(f"§3 writes {path}, which §6 does not name")
    return sorted(problems)


def names_the_starting_byte(text):
    """Whether the text ties `-gate-closed` to a starting byte, not a window.

    Matched against whitespace collapsed, because markdown wraps wherever the
    line runs out and a phrase spanning a wrap would otherwise fail on the
    wrapping rather than on the claim -- which is the failure mode a phrase
    hold is supposed to avoid. A helper rather than an inline `assertIn` so the
    negative below drives this same comparison on text with the sentence taken
    out, instead of a copy of it.
    """
    return STARTING_CLAIM in " ".join(text.split())


def keeps_the_starting_byte_in_the_banner(text):
    """Whether the text says where the two runs' difference is recorded.

    Same whitespace collapsing and the same reason for a helper. Every phrase
    is required, so a §6 that says one and not the other reads as a document
    that half-corrected itself: it would stop claiming the capture holds the
    byte without saying where the byte is instead.
    """
    flat = " ".join(text.split())
    return all(claim in flat for claim in STARTING_BYTE_CLAIMS)


def usage_capture(doc):
    """The path the docstring's `Usage:` block passes to `--csv`.

    Scoped to the usage block because the prose above it names `--csv` without
    a path -- "`--csv` is required for a run that acts" -- and reading that as
    the example would check the sentence rather than the command. Exactly one
    `--csv` value is expected, so a docstring that grows a second example has to
    say which one is the run's.
    """
    if "Usage:" not in doc:
        raise AssertionError("the docstring has no Usage: block")
    found = re.findall(r"--csv\s+(\S+)", doc.split("Usage:", 1)[1])
    if len(found) != 1:
        raise AssertionError(f"the usage block passes {len(found)} --csv "
                             f"values, not one: {found}")
    return found[0].replace("\\", "/")


# A procedure small enough to reason about, written once and used for the
# negatives. Not a paraphrase of the real one on purpose: the case that matters
# is the one a real document cannot be made to produce without breaking some
# other hold, and a fixture keeps it honest.
SAMPLE = """\
# A procedure with one capture

## 3. The run

```console
rem  the capture, with the directory spelled out
python windows\\tools\\probe.py --csv evidence\\ec-watch\\<date>-thing.csv ^
       --i-mean-it
```

## 6. Where the output goes

```
evidence/ec-watch/<date>-thing.csv
```

"Starting closed" is the byte the second run begins from, not a window with
the gate held off. The starting byte is not in either capture. What tells the
two apart is the filename and the console banner.
"""


class CaptureHandoffTests(unittest.TestCase):
    """§3, §6 and the tool's usage example, all naming the same captures.

    Three spellings of one document's output names, held to each other rather
    than to a list of known-good strings, so a rename in any one of the three is
    caught whichever way it goes.
    """

    @classmethod
    def setUpClass(cls):
        cls.text = PROCEDURE.read_text(encoding="utf-8")
        # `capture`, not `run`: an attribute of that name on a TestCase shadows
        # the method unittest calls every test through.
        cls.capture = section(cls.text, "## 3. The run")
        cls.where = section(cls.text, "## 6. Where the output goes")
        cls.listed = listed_captures(cls.where)
        cls.written = written_captures(cls.capture)

    def test_the_two_sides_were_parsed(self):
        # The non-vacuity guard. `fenced` raises on a missing fence, but an
        # empty *list* would still satisfy every comparison below, so the counts
        # here are what stops "§6 names nothing" passing as agreement.
        self.assertEqual(len(self.listed), 2, self.listed)
        self.assertEqual(len(self.written), 2, self.written)

    def test_every_capture_the_output_section_names_is_written_at_that_path(self):
        # The operator-facing half: following §3 verbatim lands each §6 entry
        # where §6 says it goes. The `startswith` is the rename step the bare
        # filename left behind -- the tool resolves `--csv` against whatever
        # directory it runs in and creates nothing above it, so a bare name
        # lands beside the operator rather than under `evidence/ec-watch/`.
        self.assertEqual(capture_problems(self.listed, self.written), [])
        for path in self.written:
            self.assertTrue(path.startswith("evidence/ec-watch/"), path)
        # And the directory is one the tree actually has, so the name points
        # somewhere rather than nowhere.
        self.assertTrue((REPO / "evidence" / "ec-watch").is_dir())

    def test_the_tool_usage_example_names_a_capture_the_procedure_lists(self):
        # `--help` prints the docstring, so this example is what an operator
        # copies before they find §3. It named a third capture, in neither §6
        # list. Only the **name** is checked here: the directory it carries is
        # relative to the run directory the docstring names ("next to
        # ecrw.py"), so it is not comparable to §3's, and the two spellings
        # resolve to the same `evidence/ec-watch/`.
        used = usage_capture(probe.__doc__)
        self.assertIn(posixpath.basename(used),
                      [posixpath.basename(p) for p in self.listed], used)
        # Named so the check above fails on the old spelling rather than
        # passing on any reworded sentence: a third name is the defect.
        self.assertNotIn(RETIRED_NAME, [posixpath.basename(p)
                                        for p in self.listed])

    def test_both_arms_force_the_gate_open_from_a_clear_starting_byte(self):
        # The property the `-gate-closed` filename does not say. `arm_bytes()`
        # returns two bytes, and both have bit 0 set whatever the run started
        # from -- derived from the tool's own GATE_BIT rather than restated as
        # 0x01/0x03, so a probe that stopped opening the gate fails here rather
        # than passing as a different starting value.
        for orig in (0x00, 0x03):
            for arm in probe.arm_bytes(orig):
                self.assertTrue(arm & probe.GATE_BIT,
                                f"0x{orig:02X}: 0x{arm:02X} does not open the "
                                f"gate, so a `-gate-closed` capture holds no "
                                f"closed window")
        # ...and §6 says so, in the words an operator reads. A phrase hold, not
        # a behavioural one: the byte half is above, and this is the document
        # saying which starting state the file was taken from.
        self.assertTrue(names_the_starting_byte(self.where),
                        f"§6 does not say the second run starts from a byte "
                        f"whose bit 0 was clear: {STARTING_CLAIM!r} is not "
                        f"there, so `-gate-closed.csv` reads as a window with "
                        f"the gate held off")

    def test_the_starting_byte_is_kept_in_the_banner_not_the_capture(self):
        # The overclaim this half exists for. A §6 saying the second capture
        # records the starting byte the first does not is false, and an
        # operator sent to the CSV for that evidence would find the arm bytes
        # throughout and could read the run as something it was not. Nothing in
        # the file records which state the run started from -- only the filename
        # and the banner do -- so §6 has to say which, or the name carries a
        # claim the capture cannot back. Held as a phrase and not as a
        # behavioural check, like the hold above it: this is the document's
        # wording, and `arm_bytes()` is what makes it true.
        self.assertTrue(keeps_the_starting_byte_in_the_banner(self.where),
                        f"§6 does not say where the starting byte is "
                        f"recorded: none of {STARTING_BYTE_CLAIMS!r} is there, "
                        f"so a reader looks for the run's start state in a CSV "
                        f"that never holds it")


class LoosenedDiscriminatorTests(unittest.TestCase):
    """The negatives: each check has a named way to fail, on text built here.

    Without these the class above is a green run and nothing -- a check that
    cannot be seen to fail has not been shown to hold anything.
    """

    def test_a_bare_filename_fails_the_handoff_the_way_the_issue_found_it(self):
        # The defect itself: §3's command without its directory, which is what
        # the two documents said before the correction.
        text = SAMPLE.replace("evidence\\ec-watch\\<date>-thing.csv",
                              "<date>-thing.csv")
        problems = capture_problems(listed_captures(text),
                                    written_captures(text))
        self.assertEqual(problems, [
            "§3 writes <date>-thing.csv, which §6 does not name",
            "§6 names evidence/ec-watch/<date>-thing.csv, which no command "
            "writes",
        ], problems)

    def test_a_listed_capture_no_command_writes_is_reported(self):
        # The other direction, which a bare-filename fixture reaches too only
        # by accident: here §6 gains an entry and the commands do not.
        text = SAMPLE.replace(
            "evidence/ec-watch/<date>-thing.csv\n```",
            "evidence/ec-watch/<date>-thing.csv\n"
            "evidence/ec-watch/<date>-thing-second.csv\n```")
        self.assertEqual(
            capture_problems(listed_captures(text), written_captures(text)),
            ["§6 names evidence/ec-watch/<date>-thing-second.csv, which no "
             "command writes"])

    def test_a_retired_name_in_the_usage_block_is_reported(self):
        # The third name, put back where it was, and read through the same
        # reader the positive uses rather than by restating the comparison: a
        # docstring carrying it has to be one `usage_capture` rejects against
        # §6's list, which is the failure an operator would have hit.
        doc = ("Usage:\n  probe.py --csv ../../evidence/ec-watch/"
               f"{RETIRED_NAME} ^\n      --i-mean-it\n")
        used = usage_capture(doc)
        self.assertNotIn(posixpath.basename(used),
                         [posixpath.basename(p) for p in listed_captures(SAMPLE)],
                         used)
        # The retired spelling is the whole assertion: a name in neither §6
        # list is the defect, whatever the surrounding sentence says.
        self.assertEqual(posixpath.basename(used), RETIRED_NAME)

    def test_a_section_six_that_drops_the_starting_byte_sentence_is_reported(self):
        # The negative for the phrase hold, on text with the sentence taken
        # out rather than on a reworded one: the check has to notice the claim
        # is gone, not merely that the wording changed.
        without = " ".join(SAMPLE.split()).replace(
            " ".join(STARTING_CLAIM.split()), "a window with the gate shut")
        self.assertFalse(names_the_starting_byte(without),
                         "the check passed a §6 that no longer says which "
                         "byte the second run starts from")
        self.assertTrue(names_the_starting_byte(SAMPLE))

    def test_a_section_six_that_puts_the_starting_byte_in_the_capture_is_reported(self):
        # The overclaim over the fixture: a §6 saying the second capture
        # "records" the starting byte. This is the claim the check exists to
        # fail on, so it is driven as a whole §6 rather than as a deletion -- a
        # rewording that stopped being wrong would pass a take-it-out negative,
        # and passing it is the defect.
        overclaim = " ".join(SAMPLE.split()).replace(
            " ".join(
                ("The starting byte is not in either capture. What tells the "
                 "two apart is the filename and the console banner.").split()),
            "what the second capture records that the first does not is the "
            "starting byte")
        self.assertFalse(keeps_the_starting_byte_in_the_banner(overclaim),
                         "the check passed a §6 that puts the starting byte "
                         "in the capture, which no CSV row holds")
        # ...and the reason this check is not the one above: the overclaim
        # still carries STARTING_CLAIM, so the phrase that used to be the whole
        # of this was satisfied by the wrong sentence. A §6 can be right about
        # the gate and still overclaim what the file holds.
        self.assertTrue(names_the_starting_byte(overclaim),
                        "this negative only means anything while the "
                        "overclaiming §6 still passes the STARTING_CLAIM hold")
        self.assertTrue(keeps_the_starting_byte_in_the_banner(SAMPLE))

    def test_a_missing_output_section_is_not_an_agreement(self):
        # The vacuity guard on its own: no §6 means nothing to disagree with,
        # and a reader would take that for a procedure that agrees.
        text = SAMPLE.split("## 6. Where the output goes")[0]
        self.assertTrue(written_captures(text))
        with self.assertRaises(AssertionError):
            listed_captures(text)

    def test_a_usage_block_naming_no_capture_is_refused(self):
        # A docstring that lost its example, read as "no disagreement" rather
        # than as nothing to check.
        with self.assertRaises(AssertionError):
            usage_capture("A docstring with no usage block at all.")
        with self.assertRaises(AssertionError):
            usage_capture("Usage:\n  probe.py --i-mean-it\n")


if __name__ == '__main__':
    unittest.main()