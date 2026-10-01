#!/usr/bin/env python3
r"""Offline checks; no EC is opened, no capture is read, no procedure is run.

#402 gave one procedure a hold in both directions: every artifact its "Where the
output goes" section names is produced by a command or saved by a hand step, and
every path a command writes is named. `CaptureHandoffTests` in
`windows/tools/test_gpu_block_watch.py` holds it for the door document, and its
helpers are door-shaped -- `command_output_paths()` keeps a token only if it
carries a `/` or `\`, which the door satisfies by spelling `evidence\ec-watch\`
out and which no sibling procedure does. Copied as-is the check would come back
with an empty producer set for every sibling and read every list entry as
unaccounted-for: a green-to-red inversion rather than a no-op. The hand-saved
allowance has the same problem in the other direction, `HUMAN_SAVED_SUFFIXES`
being `frozenset({".pml"})` and sibling procedures hand-saving a `.txt`.

So this is the generalised hold, and it is a new file rather than another class
in the door's suite: that module binds `ecrw_fake` and imports
`gpu_block_watch` at module scope, which is fine for a suite about one tool's
watch table and not a shape a repository-wide document check should have. The
~30 lines of heading-boundary parsing the two files share are a deliberate
non-merge, for the same reason the door's own copy of the watch table is
duplicated rather than imported. The door's two #402 tests still pass unchanged
and the door is held here too.

**What this is not.** It reads documents and a directory listing. It does not
open a capture, run a probe, or touch a machine, and a green run says the lists
and the commands in these documents agree with each other -- not that any run
produced anything. The directory half is a spelling check: `evidence/ec-watch/`
existing says the name points at a place the tree has, and says nothing about
what is or is not in it. `docs/findings/hardware-test-artifact-handoff.md` is the
write-up; the two decisions it records are the path convention (a §6 entry's
prefix is normalised away against a bare command filename) and what counts as a
hand-saved artifact.
"""
import fnmatch
import posixpath
import re
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
PROCEDURES = REPO / "docs" / "hardware-tests"

# The section that answers "where does this run's file go", by shape rather than
# by number: it is §6 in one procedure, §7 in two, §8 in three. Asking for a
# fixed heading would make the next renumber a red run for a document that
# stopped being wrong, which is the kind of edit a check buys by accident.
OUTPUT_HEADING = re.compile(r"^## \d+\. Where the output goes\s*$")

# A §6 entry is a path with a directory and a basename carrying an extension,
# which is what every list in `HELD` below is and what a sentence in prose is
# not. The assertion is a shape, not a name: a block that stops being a file
# list is a procedure that has stopped saying where its output goes, and it must
# raise rather than hand the direction checks an empty set to compare.
PATH_ENTRY = re.compile(r"^[^|\s/\\]+(?:[/\\][^|\s/\\]+)+?\.[A-Za-z0-9]+$")

# The file extension a producer token has to carry, and the three that do not
# count even when it does. `.py`, `.sh` and `.md` are the tools and the documents
# themselves -- `ec/tools/ecmem.py`, `ec/tools/grade_0751_isolation.py` -- which
# a §3 block names as an input. The rule names none of them, so it keeps
# working when a §3 grows a `--dump` or a `--marks`. A letter is required first
# because the flag values these procedures pass are numbers: `--interval 0.5`
# would otherwise read as a producer called `0.5`.
EXTENSION = re.compile(r"\.([A-Za-z][A-Za-z0-9]*)$")
NOT_AN_ARTIFACT = frozenset({"py", "sh", "md"})

# A flag, by either spelling, is what puts a token in a producer position. Not
# a list of known output flags: §3's command grows a `--dump` and this picks the
# new one up with nothing edited.
FLAG = re.compile(r"^--?[A-Za-z][\w-]*$")
REDIRECT = frozenset({">", ">>"})

FENCE = re.compile(r"^```[^\n]*\n(.*?)^```", re.S | re.M)
HEADING = re.compile(r"^#{1,6} ")


# The one per-document table. A document is held iff it carries a
# `## N. Where the output goes` section whose first fenced block is a file list;
# `HELD` names those and `EXCLUDED` the ones that do not, and the two together
# partition the directory so a new procedure cannot arrive unheld without this
# suite going red.
#
# `command_producers` is a *claim*, verified below against the suite's own parse
# rather than counted: it says whether this document's run sections have a
# command argument that writes a file at all. It is the honest half of the
# `ac-autoboot` case, whose three §3 arms are `ecmem.py read`/`write` calls that
# print to stdout and whose only artifact is the text file an operator assembles
# by hand -- a document with no producer is not a document this check is silent
# about, it is one this check says out loud.
#
# `hand_saved` is per document, per name, and tied to a named step: a basename
# glob, the heading of the section that earns it, and a phrase from that
# section, all three asserted present in the source document. A *glob* rather
# than a suffix, because `manual-fan-ctrl-0751-isolation.md` §6 lists six dump
# `.txt` files that §3 does produce by redirection, and a per-document `.txt`
# allowance would excuse those six the moment their commands disappeared.
HELD = {
    "ac-autoboot-0726-0765.md": {
        "command_producers": False,
        # The only section that says the file is assembled by a person, so it
        # is the only one that can be the anchor. That the anchor is the output
        # section itself is stated rather than hidden: the claim being tied to
        # a step is what matters, and here the step is the prose of §7.
        "hand_saved": {
            "*-ac-autoboot-0726-0765.txt":
                ("## 7.", "joined by the operator's wall clock"),
        },
    },
    "ctgp-dben-07c4-bit3.md": {
        "command_producers": True,
        "hand_saved": {},
    },
    "gpu-tgp-07c4-07d7-door.md": {
        "command_producers": True,
        # The door's own `.pml` allowance, carried over as a table entry rather
        # than as a constant. Not weakened: the step it names is the step
        # `CaptureHandoffTests` asserts against §4a.
        "hand_saved": {
            "*-procmon.pml": ("### 4a.", "File ▸ Save As"),
        },
    },
    "level-block-0860-086e.md": {
        "command_producers": True,
        "hand_saved": {},
    },
    "manual-fan-ctrl-0751-isolation.md": {
        "command_producers": True,
        "hand_saved": {
            "*-snapshot.txt":
                ("## 2.", "is the format to copy for the snapshot"),
        },
    },
    "oem4-07a6-bit0.md": {
        "command_producers": True,
        # The snapshot is the human's, and §2 is the only section that says so:
        # §3's commands produce the two CSVs and the two load-defaults dumps and
        # nothing else, so the record of the starting power mode and profile has
        # to be an allowance tied to the step behind it rather than a blank.
        "hand_saved": {
            "*-snapshot.txt": ("## 2.", "in the snapshot style of"),
        },
    },
    "remain-capacity-0436.md": {
        "command_producers": True,
        "hand_saved": {},
    },
    "system-id-0456-bit6-divisor.md": {
        "command_producers": True,
        "hand_saved": {
            "*-snapshot.txt": ("## 2.", "in the snapshot style of"),
        },
    },
    "mode-defaults-variant-read.md": {
        # The `ac-autoboot` case, and for the same reason: §3's command is a
        # `for` over `ecmem.py read`, which prints to stdout and writes no
        # file, so there is no producer anywhere outside the output section --
        # and `run_sections()` excludes that section deliberately, so the
        # redirection in §5 is not counted as one either. The capture is the
        # operator's, and the anchor is the section that says so.
        "command_producers": False,
        "hand_saved": {
            "*-mode-defaults-variant.txt":
                ("## 5.", "it is a placeholder, not a shell expansion"),
        },
    },
}

# The two documents the helpers cannot read, excluded by a stated rule rather
# than by a fallback. `doc_section`'s raising on a missing heading is correct --
# it fails loudly instead of passing vacuously -- so neither is made to parse.
EXCLUDED = {
    "pd-controller-enumeration.md": (
        "§7 is prose naming a destination (`evidence/pd-controller/`, a "
        "directory this tree does not have) and naming no file. There is no "
        "fenced block and nothing to compare against a command."
    ),
    "xdata-06c2-06db-sweep.md": (
        "a report of a run that already happened: §2 is 'How it was run' and "
        "§4 names six captures committed under `evidence/ec-watch/`. There is "
        "no 'Where the output goes' section at all."
    ),
}


def procedures():
    """Every procedure document in the directory, by file name."""
    return sorted(p.name for p in PROCEDURES.glob("*.md"))


def split_sections(text):
    """-> [(heading, body)] for every `## ` section, in document order.

    Bounded at the next `## ` and not at the next heading, so a `###` block
    inside a run section is read as part of it. That is deliberate and it is
    also the hole the producer-position rule exists to close:
    `level-block-0860-086e.md` §3's `### Reading the capture` names
    `<date>-086x-level-block.csv` as an argument to the grader, and a rule that
    counted every path-shaped token in the section would let that line stand in
    for §3's `--csv` and keep a §6 entry accounted for after the command that
    wrote it had been deleted.
    """
    lines = text.splitlines()
    starts = [i for i, line in enumerate(lines) if line.startswith("## ")]
    out = []
    for n, i in enumerate(starts):
        end = starts[n + 1] if n + 1 < len(starts) else len(lines)
        out.append((lines[i], "\n".join(lines[i + 1:end])))
    return out


def output_section(text):
    """The procedure's "Where the output goes" body.

    Raises rather than returning an empty section, for the reason
    `doc_section` gives in the door's suite: an empty span makes every check
    built on it pass vacuously, which is the one outcome worse than a document
    that says nothing at all.
    """
    for heading, body in split_sections(text):
        if OUTPUT_HEADING.match(heading):
            return body
    raise AssertionError("no '## N. Where the output goes' section")


def run_sections(text):
    """Every `## ` section except the output section, as its body."""
    return [body for heading, body in split_sections(text)
            if not OUTPUT_HEADING.match(heading)]


def first_block(section):
    """The section's first fenced block, its body lines.

    The block rather than the prose around it, because that prose counts the
    set and a check reading it would be holding a count against itself.
    """
    match = FENCE.search(section)
    if match is None:
        raise AssertionError("the section has no fenced block")
    return match.group(1)


def listed_artifacts(text):
    """The output section's file list, as `{name: entry}`, both spellings.

    Every line has to be a path with a directory and an extension, and the block
    has to be non-empty. Both raise instead of yielding a short list, because a
    block that stopped being a file list would otherwise leave the direction
    checks comparing a smaller set against a smaller set and reporting nothing.
    """
    out = {}
    for line in first_block(output_section(text)).splitlines():
        entry = line.strip()
        if not entry:
            continue
        if not PATH_ENTRY.match(entry):
            raise AssertionError(
                f"the output section's first block holds a line that is not a "
                f"path: {entry!r}")
        out[posixpath.basename(entry.replace("\\", "/"))] = \
            entry.replace("\\", "/")
    if not out:
        raise AssertionError("the output section names no artifacts at all")
    return out


def command_tokens(block):
    """The token stream of a console block, minus the comment lines.

    `rem` is how a cmd batch spells a comment and these procedures are Windows
    consoles; dropping those lines is what keeps §3's own explanation of a flag
    from being read as a use of it. A leading `$` is a prompt and goes with it.
    Line continuations are not joined -- a `^` is its own token, carries no
    extension, and drops out, and joining would fuse a flag onto the token
    before it.
    """
    for line in block.splitlines():
        stripped = line.strip()
        if stripped.startswith("rem ") or stripped == "rem":
            continue
        if stripped.startswith("$"):
            stripped = stripped[1:].strip()
        for token in stripped.split():
            yield token


def command_producers(text):
    """Basenames of the files the procedure's own commands write.

    A token counts only in a producer position -- directly after a flag, or as
    the target of a `>`/`>>` redirection -- and only if it carries a file
    extension that is not `.py`, `.sh` or `.md`. The second half is the tools:
    `windows\\tools\\ecrw.py` and `ec\\tools\\grade_0751_isolation.py` are named
    in the same blocks as the flags and are inputs to the run, and dropping them
    by extension needs no rule naming either.
    """
    found = set()
    for body in run_sections(text):
        for block in FENCE.finditer(body):
            previous = None
            for token in command_tokens(block.group(1)):
                if (previous is not None
                        and (FLAG.match(previous) or previous in REDIRECT)):
                    extension = EXTENSION.search(token)
                    if (extension is not None
                            and extension.group(1).lower()
                            not in NOT_AN_ARTIFACT):
                        found.add(posixpath.basename(
                            token.replace("\\", "/")))
                previous = token
    return found


def anchored(text, heading):
    """The body of the named heading, bounded at the next heading of any level.

    Needed at `###` as well as `##` because the door's hand-saved step lives in
    §4a, which has a §4b sibling under the same parent. A missing heading
    raises rather than yielding an empty span, for the reason the other readers
    here give: an empty span makes the check that uses it pass vacuously, and
    this one is what stops an allowance outliving the step it cites.
    """
    lines = text.splitlines()
    for start, line in enumerate(lines):
        if line.startswith(heading):
            break
    else:
        raise AssertionError(f"no {heading} heading in the document")
    body = lines[start + 1:]
    for i, line in enumerate(body):
        if HEADING.match(line):
            return "\n".join(body[:i])
    return "\n".join(body)


def accounted_artifacts(entries, producers, hand_saved):
    """The listed artifacts no command writes and no hand-saved step saves.

    Two producers and only two, because a run has two: a file the command
    passes to a tool, or a file a person saves by hand. A third kind of entry --
    one neither accounts for -- is what #402 found in the door's §8, and this
    is the check that would have found it in every other procedure too.
    """
    return sorted(name for name in entries
                  if name not in producers
                  and not any(fnmatch.fnmatchcase(name, pattern)
                              for pattern in hand_saved))


def unlisted_artifacts(producers, entries):
    """The files a command writes that the output section does not name.

    One direction only, kept out of `accounted_artifacts` so that helper's
    contract stays single: a capture that lands where the index will not find it
    is the other half of the same defect class, and it is the half
    `ctgp-dben-07c4-bit3.md` was failing in.
    """
    return sorted(producers - set(entries))


def missing_directories(entries):
    """The listed entries whose directory is a real path the tree lacks.

    This is the half the basename comparison gives up, and it is given back here
    rather than absorbed: matching on a bare filename means `evidence/ec-watch/`
    is not compared against a command argument, so the directory is checked on
    its own. A directory spelled with a placeholder is skipped -- it is a
    template, and there is nothing in the tree to check it against.
    """
    out = []
    for entry in entries.values():
        directory = posixpath.dirname(entry)
        if not directory or "<" in directory:
            continue
        if not (REPO / directory).is_dir():
            out.append(entry)
    return sorted(out)


def allowance_problems(text, hand_saved):
    """The hand-saved allowances whose anchor or quoted step is not there.

    A table of globs is a table of promises about steps somebody takes by hand,
    and a promise nobody re-reads is how a `.txt` exemption outlives the
    `File ▸ Save As` that justified it. Each entry is refused unless both its
    heading and its phrase are still in the document it exempts.
    """
    problems = []
    for pattern, (heading, phrase) in sorted(hand_saved.items()):
        try:
            section = anchored(text, heading)
        except AssertionError:
            problems.append(f"{pattern}: {heading} is no longer in the document")
            continue
        if phrase not in section:
            problems.append(
                f"{pattern}: {heading} no longer says {phrase!r}")
    return problems


# A procedure small enough to reason about, written once and used for the
# negatives below. It is not a paraphrase of a real one on purpose: the cases
# that matter here are the ones a real document cannot be made to produce
# without breaking something else, and a fixture keeps them honest. The prose
# in §6 is what the allowance cases anchor on, so it carries a phrase a
# rewording can break.
SAMPLE = """\
# A procedure with one run and one output section

## 3. The run

```console
rem  the capture, one per arm
python windows\\tools\\probe.py --csv <date>-thing-ac.csv
python windows\\tools\\probe.py --csv <date>-thing-gate-closed.csv
```

## 6. Where the output goes

Name the files the way the existing captures are named.

```
evidence/ec-watch/<date>-thing-ac.csv
evidence/ec-watch/<date>-thing-gate-closed.csv
```
"""


class ArtifactHandoffTests(unittest.TestCase):
    """Every held procedure, against its own commands, in both directions."""

    @classmethod
    def setUpClass(cls):
        cls.texts = {name: (PROCEDURES / name).read_text(encoding="utf-8")
                     for name in HELD}

    def test_the_held_and_excluded_tables_partition_the_procedures(self):
        # Both halves, because each is a way for a document to escape the hold
        # silently: a procedure in neither table is unchecked, and a name in
        # both is checked twice with whichever table is read last.
        self.assertEqual(sorted(set(HELD) | set(EXCLUDED)), procedures())
        self.assertEqual(set(HELD) & set(EXCLUDED), set())
        for name in HELD:
            self.assertTrue((PROCEDURES / name).is_file(), name)
        for name in EXCLUDED:
            self.assertTrue((PROCEDURES / name).is_file(), name)

    def test_every_exclusion_states_why(self):
        # The whole weight of an exclusion is the sentence that gives it, and an
        # empty string would let a document out of the hold for no stated
        # reason. Held in the suite rather than left in a comment beside it,
        # because a comment is not checked by anything.
        for name, reason in sorted(EXCLUDED.items()):
            self.assertTrue(reason.strip(),
                            f"{name} is excluded with no reason")
            self.assertGreater(len(reason.split()), 8,
                               f"{name}: the reason is too short to be one")

    def test_every_held_document_names_a_file_list(self):
        # The vacuity guard, and the same one `doc_section` gives in the door's
        # suite: a reader that found nothing would leave the two direction
        # checks below comparing empty sets and reporting nothing. The block has
        # to parse as paths, not merely to exist, so a section that replaced its
        # file list with a sentence is red rather than a shorter list.
        for name, text in sorted(self.texts.items()):
            entries = listed_artifacts(text)
            self.assertTrue(entries, name)
            for entry in entries.values():
                self.assertIn("/", entry, f"{name}: {entry}")

    def test_the_command_producer_claim_matches_what_the_commands_produce(self):
        # The claim, not the census. A count of producers moves every time a
        # procedure's §3 grows a command; whether this document has one at all
        # is the thing that decides how its list is read, so that is what the
        # table carries and what is checked here. It is also what keeps
        # `ac-autoboot-0726-0765.md` honest: it has no producer, the table says
        # so, and its single artifact is held to a hand-saved step instead.
        for name, text in sorted(self.texts.items()):
            producers = command_producers(text)
            self.assertEqual(bool(producers),
                             HELD[name]["command_producers"],
                             f"{name}: command_producers")

    def test_every_artifact_the_output_section_names_has_a_producer(self):
        # Direction A, the general form of #402: an entry no run produces, so an
        # operator following the procedure had to hand-make it or had nothing to
        # hand in. This is where `ctgp-dben-07c4-bit3.md` failed in both
        # directions at once -- two names no command wrote, and the one name a
        # command did write absent from the list.
        for name, text in sorted(self.texts.items()):
            unaccounted = accounted_artifacts(
                listed_artifacts(text), command_producers(text),
                HELD[name]["hand_saved"])
            self.assertEqual(
                unaccounted, [],
                f"{name}: artifacts no run produces: {unaccounted}")

    def test_every_artifact_a_command_produces_is_named(self):
        # Direction B, and the half #402's door suite kept out of the helper so
        # that helper's contract stays one: a capture that lands where the index
        # will not find it is a file nobody grades and nobody cites.
        for name, text in sorted(self.texts.items()):
            unlisted = unlisted_artifacts(command_producers(text),
                                          listed_artifacts(text))
            self.assertEqual(
                unlisted, [],
                f"{name}: files a command writes and the list does not name: "
                f"{unlisted}")

    def test_every_listed_artifact_directory_is_in_the_tree(self):
        # What the basename comparison gives up, given back here. Matching a
        # bare command filename against a §6 entry carrying the
        # `evidence/ec-watch/` prefix means the directory half is not compared,
        # so it is checked on its own -- a spelling check, and nothing more: a
        # directory existing says the name points somewhere real, not that any
        # run put anything in it.
        for name, text in sorted(self.texts.items()):
            missing = missing_directories(listed_artifacts(text))
            self.assertEqual(
                missing, [],
                f"{name}: listed artifacts in a directory the tree does not "
                f"have: {missing}")

    def test_every_hand_saved_allowance_names_a_step_that_is_still_there(self):
        # Without this the allowance table is a constant: a glob that keeps
        # exempting a file after the step behind it stopped saving one, which is
        # the defect the door's own `.pml` was tied to §4a to prevent.
        for name, text in sorted(self.texts.items()):
            problems = allowance_problems(text, HELD[name]["hand_saved"])
            self.assertEqual(problems, [], f"{name}: {problems}")


class LoosenedDiscriminatorTests(unittest.TestCase):
    """The same checks over text the suite builds, in every direction.

    Without these the suite above is a set of green runs and nothing says the
    discriminator has teeth: a rule loosened to "any name goes" would pass every
    procedure in `HELD` and each of them would still be green. Every case here
    is a shape a real document cannot be put into without something else going
    red first, which is why they are built rather than edited.
    """

    def test_the_bare_filename_rule_accounts_for_a_prefixed_entry(self):
        # The decision, asserted green. The door spells `evidence\ec-watch\`
        # in its command and its siblings pass a bare filename; matching on the
        # basename is what makes the two comparable, and this is the case that
        # would go red if it were dropped for the strict reading.
        producers = command_producers(SAMPLE)
        self.assertEqual(producers, {"<date>-thing-ac.csv",
                                     "<date>-thing-gate-closed.csv"})
        self.assertEqual(
            accounted_artifacts(listed_artifacts(SAMPLE), producers, {}), [])

    def test_an_entry_no_producer_and_no_allowance_is_reported(self):
        # The `ctgp-dben-07c4-bit3.md` shape, and the negative that stops the
        # basename rule from being a blanket pass: the two lists here differ, and
        # the entry neither side of the difference is written is reported.
        text = SAMPLE.replace(
            "python windows\\tools\\probe.py --csv <date>-thing-ac.csv\n", "")
        self.assertEqual(
            accounted_artifacts(listed_artifacts(text),
                                command_producers(text), {}),
            ["<date>-thing-ac.csv"])

    def test_a_producer_the_list_does_not_name_is_reported(self):
        # The other direction, on the same edit: a §3 that writes a file the
        # output section forgot is a capture that lands where the index will not
        # find it.
        text = SAMPLE.replace("evidence/ec-watch/<date>-thing-ac.csv\n", "")
        self.assertEqual(
            unlisted_artifacts(command_producers(text),
                               listed_artifacts(text)),
            ["<date>-thing-ac.csv"])

    def test_a_reference_outside_a_producer_position_cannot_account(self):
        # The hole the producer-position rule exists to close, and the reason it
        # is a rule rather than a list of known output flags. SAMPLE's grader
        # line names the same capture as §3's `--csv` does, with no flag in
        # front of it; delete the command and the listing must still be reported,
        # where a path-shaped-token rule would have kept it quiet.
        text = SAMPLE.replace(
            "python windows\\tools\\probe.py --csv <date>-thing-ac.csv\n",
            "python ec\\tools\\grade.py <date>-thing-ac.csv\n")
        self.assertEqual(command_producers(text),
                         {"<date>-thing-gate-closed.csv"})
        self.assertEqual(
            accounted_artifacts(listed_artifacts(text),
                                command_producers(text), {}),
            ["<date>-thing-ac.csv"])

    def test_a_tool_is_not_a_producer(self):
        # The extension half of the rule, named rather than incidental. A tool
        # path has an extension like anything else and is an input to the run,
        # so a §3 that grows `python windows\\tools\\grade.py --csv out.csv` is
        # fine and one that grows `--grader windows\\tools\\grade.py` contributes
        # nothing.
        text = SAMPLE.replace(
            "python windows\\tools\\probe.py --csv <date>-thing-ac.csv",
            "python windows\\tools\\grade.py --grader windows\\tools\\probe.py")
        self.assertEqual(command_producers(text),
                         {"<date>-thing-gate-closed.csv"})

    def test_an_allowance_in_one_document_does_not_cover_another(self):
        # The door's own negative, generalised: its §8 assertion refuses a
        # `.txt` artifact outright, and a blanket `.txt` allowance would be the
        # loosening that made that assertion necessary. An allowance is keyed by
        # the document it was granted for.
        hand_saved = {"*-snapshot.txt": ("## 6.", "the existing captures")}
        self.assertEqual(allowance_problems(SAMPLE, hand_saved), [])
        self.assertEqual(
            accounted_artifacts({"<date>-thing-ac.csv": ""},
                                {"<date>-thing-gate-closed.csv"}, hand_saved),
            ["<date>-thing-ac.csv"])
        self.assertEqual(
            accounted_artifacts({"<date>-snapshot.txt": ""}, set(), hand_saved),
            [])

    def test_an_allowance_whose_step_is_gone_is_refused(self):
        # The table cannot outlive the step it cites, in both halves: a heading
        # that has moved and a phrase that has been reworded are the two ways it
        # rots, and either one leaves a glob exempting a file nobody saves.
        hand_saved = {"*-snapshot.txt": ("## 6.", "the existing captures")}
        self.assertTrue(allowance_problems(
            SAMPLE.replace("## 6.", "## 7."), hand_saved))
        self.assertTrue(allowance_problems(
            SAMPLE.replace("the existing captures", "the captures"),
            hand_saved))

    def test_a_missing_file_list_raises_rather_than_yielding_nothing(self):
        # The vacuity guard, once, on the side that would otherwise be silent: a
        # document whose output section lost its block, or whose block stopped
        # being a file list, must be a red run and not a shorter list the
        # direction checks pass against.
        for text, why in (
                (SAMPLE.split("## 6. Where the output goes")[0],
                 "the section is gone"),
                (SAMPLE.split("## 6. Where the output goes")[0]
                 + "\n## 6. Where the output goes\n\nprose, not a list.\n",
                 "the block is gone"),
                (SAMPLE.replace(
                    "evidence/ec-watch/<date>-thing-ac.csv",
                    "the capture, under evidence/ec-watch/"),
                 "a line of the block is not a path"),
                (SAMPLE.replace("```\nevidence", "```\n```\n```\nevidence"),
                 "the first block is empty")):
            with self.assertRaises(AssertionError, msg=why):
                listed_artifacts(text)


if __name__ == '__main__':
    unittest.main()
