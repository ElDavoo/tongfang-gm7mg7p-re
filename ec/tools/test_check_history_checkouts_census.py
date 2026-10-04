#!/usr/bin/env python3
"""Census the per-workflow rule's over-reach, and account for every site #1046 named.

`test_check_history_checkouts_corpus.py` holds the *rule*: what the sweep reads,
what it refuses, and what it says about a claim. This holds a **question about
that rule's cost**, which is a different kind of case and would not sit beside
those answering "does this work": *a sentence naming a job of one workflow and
none of a second is flagged, and #1034 wrote that down as a known over-reach* --
how much does that cost, over the population the sweep actually reads? The rule's
own write-up declines to answer it ("No claim is made about how often the
over-reach would fire on a different tree"), so the number was taken by hand by
whoever read the report, and #1046 exists to make it derived.

**What is held here is a disposition, never a count.** Each row of `NAMED_SITES`
is a file and a fragment of one sentence, and what it asserts is *how that
sentence resolves* -- `quoted`, `names-a-job`, `flagged`, or `declined`. Those
are properties of a named sentence, they are what a reviewer can go and read, and
none of them moves because some unrelated file gained a depth claim. A count over
the tree does move, on every write-up that touches checkouts, which is why the
counts this suite needs are **printed** and the page quotes the print rather than
restating a figure beside the sentences. `CLAUDE.md`'s "No totals of the
repository's own text" is the rule; a claim that stands without its number is
the form it asks for.

**The fragments, not the line numbers, and that is the whole identity.** The
issue filed its census by `file:line`, and most of those line numbers no longer
describe the tree: `history-checkout-claims.md` has been amended since the issue
was filed, above the sentences it points at. A row keyed by a line would go red
for a rewrap and stay green for a sentence that changed meaning -- the inverse of
what a test is for. `ec/tools/history_checkout_sites.py` makes the same argument
at greater length for the corrected sites, and this suite takes its identity from
there rather than inventing a second one. What a line *would* buy is a visible
edit when a sentence moves, and `test_a_row_that_matches_two_sentences` below is
what catches that instead: a fragment that stops being unique has stopped
identifying anything, whichever file it drifted into.

**The flags in `history-checkout-claims.md` are the finding, and they are not in
the population.** That file is held by the `instrument-or-record` decline rule,
so the derived sweep does not read it and reports nothing at all -- which is why
the answer to the issue's question is a zero and why the zero is not a
measurement of the tree. `test_the_record_file_is_read_and_still_flagged` reads
that file with the rule's own `prose_sites()` and finds the sentences the issue
named, unchanged and still flagged. **Declining the file and clearing its
sentences are different answers**, and conflating them is how "the rule flags
nothing" would come to mean "the rule has nothing to say here".

**"Only" is a claim about prose, and the declined machinery is flagged too.**
Force-reading every file `instrument-or-record` holds -- which
`test_every_declined_file_is_read_and_only_prose_carries_a_flag` does -- finds the
checker's own report text and the pre-fix sentences its suites hold verbatim
judged by the same rule. Those are controls, and a control that is judged is not a
control, which is why the decline exists; but they are still sites the rule
flags, so a page saying every flagged site is in the record file would be wrong.
The claim this suite holds is the scoped one: every flagged site outside the
derived population that is not in the checker's own machinery is in the record
file.

**Not vacuous, in both directions.** A zero over a committed tree is what a
checker that has stopped finding anything also prints, so two cases give it
teeth: `test_the_over_reach_case_flags_where_the_committed_tree_has_none` pastes
the #1034 sentence verbatim over a scratch tree and requires it flagged, and
`test_a_multi_workflow_site_still_exists_to_be_a_zero_about` holds that the shape
is present at all. The second is a floor and the first is the control, and a floor
the sweep could satisfy with two files is not one -- which is the corpus suite's
own argument, applied here.

**A control is not judged, and this file is one.** `INSTRUMENT_PATTERNS`'s single
glob covers every suite written against this tool without an entry per suite, so
`test_this_suite_is_a_control_and_is_not_judged` says so rather than leaving it
implicit: the pre-fix sentences below live in this file's own source in the
author's voice, which is precisely what must never be judged. Writing the next
suite against the tool needs no edit to the rule for the same reason.

Nothing here needs the laptop, Windows, or a register: the checker's only
dependency is PyYAML, and every figure below is read out of committed files by
running it.
"""
import importlib.util
import fnmatch
import io
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location(
    'check_history_checkouts', HERE / 'check_history_checkouts.py')
chc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(chc)

# `workflow()` is the sibling suite's synthetic-workflow builder, imported for
# the reason `test_check_history_checkouts_corpus.py` imports it: a second
# builder would be a second answer to "what does a workflow file look like", and
# the control below is a sentence and not the YAML around it.
from test_check_history_checkouts import workflow  # noqa: E402

# The files the issue's census was measured over, as the paths it names them.
# **Named, not counted.** The issue listed `docs/findings/*.md` plus four
# readmes, and this is that set written out; the size of it is not held, because
# a write-up added under `docs/findings/` changes the answer to "how many files
# is that" every time and nothing else.
ISSUE_POPULATION = ("docs/findings/",) + (
    "docs/findings.md",
    "tools/README.md",
    "ec/README.md",
    "ec/ghidra/README.md",
)

# Which of those readmes the sweep reads and finds carrying no depth claim. Held
# by name rather than as a count for two reasons: a count is satisfied by any two
# files, so a sweep that had narrowed would leave it green, and the *direction*
# of the change is the finding -- these two lost their claims when
# `tools/README.md`'s per-suite table was removed in favour of each suite's own
# docstring, which is a tree event and not a defect. A readme that gains one is a
# new claim nothing holds, so the case that reads this says so rather than
# treating the set as settled.
CARRYING_NO_CLAIM = (
    "ec/README.md",
    "tools/README.md",
)

# The write-up that holds the retracted sentences and is therefore declined by
# `instrument-or-record`. It is named here because the finding is about it: every
# flagged site outside the derived population that is not one of the checker's own
# controls lives in this one file, and it is the file the sweep refuses to read.
RECORD_FILE = "docs/findings/history-checkout-claims.md"

# What each disposition means, resolved by the case below rather than read off a
# constant. `quoted` is `MARKED` reading the claim as someone else's words,
# `names-a-job` is every readable workflow the sentence names having a job of it
# named, `flagged` is the rule broken, and `declined` is the file the walk holds.
QUOTED = "quoted"
NAMES_JOB = "names-a-job"
FLAGGED = "flagged"
DECLINED = "declined"

# Every site #1046 named, keyed by file and by a fragment of the sentence the
# issue was pointing at, with the disposition that sentence resolves to today.
#
# The two that changed disposition since the issue was filed are the two the
# issue predicted would not: `testdata-row-claims-repair-measurement.md`'s pair
# are both *quoted*, not flagged. The issue's own reading -- "quotations #1031
# cannot flag away" -- was a prediction about a rule that has since landed, and
# the tree says it was wrong. `xdata-moved-ranks-pin-decisions.md` is the third
# kind: it names `implement`, so it passes on the rule rather than by exemption.
#
# The record file's rows are `declined` here and `flagged` when the file is read,
# and both facts are asserted -- see `test_the_record_file_is_read_and_still_flagged`.
NAMED_SITES = (
    ("docs/findings/history-checkout-claim-per-workflow.md",
     "is full-depth and claude.yml is shallow throughout",
     QUOTED,
     "#1034's own worked example, pasted into a fenced block. The issue called "
     "this the clearest possible statement of the mention/claim coarseness, and "
     "it is: the rule reads it as someone else's words, which is the answer to "
     "the question rather than a defect in the sentence"),
    ("docs/findings/history-checkout-claim-per-workflow.md",
     "job is full-depth, as `agent-fix.yml`'s is too",
     QUOTED,
     "the over-reach example, also quoted -- the page says of it that it is 'a "
     "true positive under the rule as stated', which is a statement about the "
     "rule and not a claim about a checkout"),
    ("docs/findings/testdata-row-claims-repair-measurement.md",
     "still says** *\"both of ci.yml's checkouts are default-depth\"*",
     QUOTED,
     "one of the issue's two, quoting `verify_reassembly.py`'s retracted wording "
     "outright"),
    ("docs/findings/testdata-row-claims-repair-measurement.md",
     "this read \"`ci.yml:39` is `fetch-depth: 0` now\"",
     QUOTED,
     "the issue's other, and the falsification of its prediction: it is a "
     "correction-in-place note whose retracted wording is inside the quotes, so "
     "the quotation rule does reach it"),
    ("docs/findings.md",
     "this sentence read \"the agent stages have one (`fetch-depth: 0`) and `ci.yml`'s two checkouts do not\"",
     QUOTED,
     "correction-in-place, §4a-4d's pattern; the retracted sentence is in the "
     "quotes beside the sentence that replaced it"),
    ("docs/findings.md",
     "this read \"`claude.yml:72`'s `fetch-depth: 1`\", naming the file's stem",
     QUOTED,
     "the issue's second `docs/findings.md` site, and the same shape"),
    ("docs/findings/xdata-moved-ranks-pin-decisions.md",
     "`agent-implement.yml`'s `implement` job checks out with `fetch-depth: 0`",
     NAMES_JOB,
     "corrected since the issue was filed and now names the job, so it passes on "
     "the rule rather than by exemption -- a third disposition the issue did not "
     "have a category for"),
    (RECORD_FILE,
     "Seven committed sentences described what this repository's CI checkouts can do",
     DECLINED,
     "still flagged when the file is read: names `ci.yml`, no job of it"),
    (RECORD_FILE,
     "They were wrong in *two* directions, not one",
     DECLINED,
     "still flagged when the file is read"),
    (RECORD_FILE,
     "The sentence that is true in both directions, and is now what both tools carry",
     DECLINED,
     "still flagged when the file is read, for `claude.yml` -- the one job id "
     "that is its own filename's stem, which `job_text()` blanks out and so "
     "cannot be found in the name it is required to carry"),
    (RECORD_FILE,
     "The issue text and the plan both said `claude.yml`'s was \"the only shallow checkout\"",
     DECLINED,
     "still flagged when the file is read; it is quoting the retracted claim and "
     "the quotation rule does not reach it, because the sentence itself is the "
     "correction's own voice"),
    (RECORD_FILE,
     "The four line numbers are the depth word's line, as the tool reports them everywhere",
     DECLINED,
     "the sentence the issue named at its `:229`, and it has moved rather than "
     "stopped flagging: the `>` blockquotes added above it pushed it down. "
     "Correcting the issue's own line arithmetic is part of the accounting, "
     "because a reader who went to `:229` would land on prose that is not this"),
    (RECORD_FILE,
     "Nothing here runs it, and the fact that `ci.yml` puts it in a full-depth checkout",
     DECLINED,
     "the issue's `:280`, moved further still by the same additions, and also "
     "still flagged"),
)

# The sentence #1034 wrote the rule for, verbatim from that page's *defect*
# section: it names a job of `ci.yml` and none of `claude.yml`, and the rule as
# stated reports the second. Pasted rather than paraphrased for the reason
# `PRE_FIX_AGENT_PIPELINE` is in the corpus suite: a reword that happened to name
# a job, or that lost the wrap, would be a control passing for the wrong reason.
TWO_WORKFLOW_SENTENCE = (
    "# ci.yml's `gates` job is full-depth and claude.yml is shallow throughout\n")


def squash(sentence):
    """The text the report prints for a sentence, run together.

    The tool's own two steps rather than a copy of them: `readable()` strips the
    source quoting a reader does not want and `history_checkout_sites.py` calls
    the result a one-line `squash()`. A fragment taken off a source sentence's
    opening words need not match the text the matcher sees, which is a case the
    corpus suite's sibling documents at greater length.
    """
    return " ".join(chc.readable(sentence).split())


class CommittedCensus(unittest.TestCase):
    """The issue's census over the derived population, and every site it named."""

    @classmethod
    def setUpClass(cls):
        cls.workflows, cls.unreadable = chc.load_workflows(str(REPO))
        cls.files, cls.declined = chc.walk_prose_files(str(REPO))
        cls.sites = chc.prose_sites(str(REPO), cls.workflows, cls.unreadable,
                                    cls.files, cls.declined)
        cls.problems = chc.prose_problems(cls.sites)
        # The record file, read the one way the walk will not. `prose_sites()`
        # takes the file list as an argument precisely so a case can point it at
        # a set the walk would not choose; nothing is reimplemented here, and a
        # second copy of the sentence splitter is a second answer to "what is a
        # site".
        cls.record = chc.prose_sites(str(REPO), cls.workflows, cls.unreadable,
                                     files=[RECORD_FILE], declined=[])

    def named_in(self, pool, rel, fragment):
        """The sites of `pool` in `rel` whose text carries `fragment`."""
        return [s for s in pool if s[0] == rel and fragment in squash(s[2])]

    def disposition_of(self, site):
        """-> what *the walk* makes of this site, resolved rather than read off a row.

        Three answers are properties of the sentence and computed from the rule's
        own outputs, so a row cannot agree with itself by being wrong twice.
        `declined` is the fourth and is not a property of the sentence at all: it
        is a property of where the sentence is, decided by the walk rather than by
        the rule, and it says nothing about whether the sentence would survive
        being read. `verdict_of()` below is the other half, and keeping the two
        apart is the whole point — a declined file and a cleared one are the same
        silence for different reasons.
        """
        if site[0] not in self.files:
            return DECLINED
        if site[5]:
            return QUOTED
        return FLAGGED if any(job is None for job in site[4].values()) else NAMES_JOB

    def verdict_of(self, site):
        """-> what the rule makes of this sentence, having been read.

        `quoted` and `names-a-job` are the rule's own two passing answers; the
        third is that it is broken. Nothing here consults the walk, so a site
        reached by naming its file rather than by the walk is judged the same way
        a site the walk found would be.
        """
        if site[5]:
            return QUOTED
        return FLAGGED if any(job is None for job in site[4].values()) else NAMES_JOB

    def test_every_site_the_issue_named_resolves_to_the_disposition_recorded(self):
        # The accounting, one row at a time. This is what the issue asked for and
        # what a plan-time reading of it got wrong: it is not a number, it is
        # these sentences and how each one lands now. A row that changes
        # disposition goes red by name, and the message says what the other
        # answer would be, because "a site that stopped being flagged" and "a
        # file that stopped being read" are the same silence for different reasons.
        for rel, fragment, expected, why in NAMED_SITES:
            with self.subTest(site=f"{rel}: {fragment[:48]}"):
                pool = self.record if rel == RECORD_FILE else self.sites
                found = self.named_in(pool, rel, fragment)
                self.assertEqual(
                    len(found), 1,
                    f"{rel} carries {len(found)} sites this row can mean by "
                    f"{fragment!r}. A fragment that matches nothing has stopped "
                    f"identifying a sentence; one that matches several is holding "
                    f"more than one, and either way the row is stale rather than "
                    f"the tree being wrong. Found:\n"
                    + "\n".join(f"  {s[0]}:{s[1]} {squash(s[2])[:120]}"
                                for s in pool if s[0] == rel))
                self.assertEqual(
                    self.disposition_of(found[0]), expected,
                    f"{rel}: {fragment!r} now resolves differently. {why}. The "
                    f"sentence is:\n  {squash(found[0][2])}")

    def test_a_row_that_matches_two_sentences_is_a_stale_row_and_not_a_drift(self):
        # The other half of a fragment-keyed identity, and the one #1030 asked
        # for on `history_checkout_sites.py`: a row matching two sites is a row
        # carrying more than one sentence of its file. It is checked separately
        # from the case above so the message names this rather than telling a
        # reader to go and re-read a disposition.
        for rel, fragment, _expected, _why in NAMED_SITES:
            with self.subTest(row=f"{rel}: {fragment[:48]}"):
                pool = self.record if rel == RECORD_FILE else self.sites
                self.assertLessEqual(
                    len(self.named_in(pool, rel, fragment)), 1,
                    f"{rel}: {fragment!r} matches more than one sentence:\n"
                    + "\n".join(f"  {s[1]} {squash(s[2])[:120]}"
                                for s in self.named_in(pool, rel, fragment)))

    def test_the_issue_population_is_read_and_which_of_it_carries_nothing(self):
        # The set the issue measured over, resolved against the walk rather than
        # asserted as a count. **Every file in it is read, and two of the four
        # readmes carry no depth claim** -- `tools/README.md` and `ec/README.md`,
        # whose claims were in the per-suite table rows that `tools/README.md`
        # has since removed. Read-and-found-nothing is not the same answer as
        # unread, or as declined, and this holds the three apart by name: a file
        # that stopped being prose about checkouts is not thereby a finding about
        # it, and a file the walk refuses is out of scope rather than clean.
        carriers = {s[0] for s in self.sites}
        unread = [rel for rel in ISSUE_POPULATION[1:] if rel not in self.files]
        empty = [rel for rel in ISSUE_POPULATION[1:]
                 if rel in self.files and rel not in carriers]
        for rel in ISSUE_POPULATION[1:]:
            with self.subTest(readme=rel):
                self.assertIn(
                    rel, self.files,
                    f"{rel} is not read by the walk at all, so nothing here can "
                    f"say whether it still carries a depth claim")
        self.assertTrue(
            any(s[0].startswith(ISSUE_POPULATION[0]) for s in self.sites),
            "no write-up under docs/findings/ carries a depth claim, so the "
            "population the issue measured over is not the one the sweep reads")
        self.assertEqual(
            sorted(empty), sorted(CARRYING_NO_CLAIM),
            "which of the readmes the issue named now carry no depth claim has "
            "moved. That is a finding about the tree and not a failure -- but a "
            "readme that *gains* one is a new claim nothing is holding, so the "
            "list is named rather than left to a count.")
        for rel in unread:
            with self.subTest(declined=rel):
                held = [rule for rule, held_rel in self.declined
                        if held_rel == rel]
                self.assertTrue(
                    held,
                    f"{rel} is not read by the walk and is not declined by any "
                    f"rule either -- it is a file this method has no opinion "
                    f"about, which is 'not found by this method' and not a "
                    f"finding about a sentence")

    def test_a_multi_workflow_site_still_exists_to_be_a_zero_about(self):
        # The floor under the answer, and a floor on the *shape* rather than on a
        # count: the sweep must still find sentences that name more than one
        # readable workflow, or "the over-reach fires on nothing" is a statement
        # about a population that no longer contains the case. Asserted over the
        # sweep's own sites rather than a number, so a write-up that adds one is
        # not a failure and a sweep that found none is.
        overreach_shape = [s for s in self.sites
                           if len([n for n in s[3] if n in self.workflows]) > 1]
        self.assertTrue(
            overreach_shape,
            "no committed sentence names more than one readable workflow, so the "
            "census's zero is about a population the shape has left. That may be "
            "right; it is not a measurement of the rule until a sentence of that "
            "shape exists to be measured on")

    def test_the_over_reach_case_flags_where_the_committed_tree_has_none(self):
        # The teeth for the committed-tree zero, and the pair of it with the case
        # above: the shape is present, and this is the same shape over a scratch
        # tree, where it must be flagged. Without this a sweep that had stopped
        # judging anything would print the same zero.
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root)
        os.makedirs(os.path.join(root, ".github", "workflows"))
        for name, jobs in (("ci.yml", ("gates", "workflows")),
                           ("claude.yml", ("claude",))):
            with open(os.path.join(root, ".github", "workflows", name),
                      "w", encoding="utf-8") as handle:
                handle.write(workflow(name, {job: [{"uses": True, "depth": 0}]
                                             for job in jobs}))
        os.makedirs(os.path.join(root, "docs"))
        with open(os.path.join(root, "docs", "notes.md"), "w",
                  encoding="utf-8") as handle:
            handle.write(TWO_WORKFLOW_SENTENCE)
        workflows, unreadable = chc.load_workflows(root)
        sites = chc.prose_sites(root, workflows, unreadable)
        problems = chc.prose_problems(sites)
        self.assertEqual(
            len(problems), 1,
            f"#1034's own sentence, over a scratch tree, was not flagged once:\n"
            f"{problems}\n  sites:\n"
            + "\n".join(f"  {s[0]}:{s[1]} {squash(s[2])[:120]}" for s in sites))
        self.assertIn("names claude.yml and no job of it",
                      problems[0].split(" -- ", 1)[0])
        self.assertNotIn("ci.yml", problems[0].split(" -- ", 1)[0])

    def test_no_multi_workflow_site_on_the_committed_tree_is_flagged(self):
        # The census's answer, as a claim about the sentences rather than a
        # figure: of the sites that name more than one readable workflow, every
        # one either is quoted or names a job of every workflow it names. A new
        # site that breaks it is named here, which is the shape the message needs
        # to be actionable rather than a restatement of the count.
        unfixed = [f"{s[0]}:{s[1]}" for s in self.sites
                   if len([n for n in s[3] if n in self.workflows]) > 1
                   and not s[5] and any(job is None for job in s[4].values())]
        self.assertEqual(
            unfixed, [],
            "a sentence naming more than one workflow names no job of one of them. "
            "That is the over-reach the rule documents, and it is a defect in the "
            "sentence unless the sentence is quoting someone else's -- see "
            "docs/findings/history-checkout-claim-per-workflow.md for the shape, "
            "and note that a site this case cannot see is not a site that is not "
            "there")

    def test_the_record_file_is_read_and_still_flagged(self):
        # The finding, and the half that makes the zero honest. Over the derived
        # population the rule flags nothing, because the sentences it would flag
        # are in the file `instrument-or-record` holds. Read, they are all still
        # there and all still flagged.
        self.assertEqual(
            self.problems, [],
            "the derived population now has a flagged site, so the census's "
            "answer is no longer a zero over the tree and this page's claim is "
            "stale")
        self.assertTrue(
            all(s[3] for s in self.record),
            "reading the record file produced a site naming no workflow at all, "
            "which means the sentence splitter and the site builder disagree "
            "about what this file contains")
        flagged = [s for s in self.record if self.verdict_of(s) == FLAGGED]
        self.assertTrue(
            flagged,
            f"{RECORD_FILE} is read here and nothing in it is flagged. Either the "
            f"sentences the issue named were corrected -- in which case their "
            f"rows above are stale and this page's central claim is wrong -- or "
            f"the read did not reach them, which is the sweep failing rather than "
            f"the tree being clean")
        # The record file's rows, by fragment, so each is a property of the rows
        # above rather than a figure that can drift away from them.
        for rel, fragment, _expected, _why in NAMED_SITES:
            if rel != RECORD_FILE:
                continue
            with self.subTest(site=fragment[:48]):
                site = self.named_in(self.record, rel, fragment)
                self.assertEqual(
                    len(site), 1,
                    f"the record file no longer carries the site {fragment!r}")
                self.assertEqual(
                    self.verdict_of(site[0]), FLAGGED,
                    f"{rel}: {fragment!r} is read by this case and is no longer "
                    f"flagged, so the decline is no longer the only thing standing "
                    f"between the sentence and the rule")

    def test_every_declined_file_is_read_and_only_prose_carries_a_flag(self):
        # The *scoped* form of the claim, and the case that keeps the page's
        # wording honest. A force-read of every file `instrument-or-record` holds
        # finds flagged sites outside the record file too -- the checker's own
        # report text, and the pre-fix sentences its suites carry verbatim -- so
        # "every flagged site is in the record file" would be false and a reader
        # is entitled to be told which are which.
        #
        # What is asserted is a property of *which files* the flags live in, not a
        # count: the flags outside the derived population are the record file's
        # plus the checker's own machinery's, and anything else appearing there
        # is a file the rule should have read. A count would be a figure every
        # suite written against this tool moves, which is the same trap
        # `NAMED_SITES` avoids by keying on fragments.
        #
        # The machinery side is named from the checker's own `INSTRUMENT_PATTERNS`
        # rather than listed here: a hand-kept list of this checker's own files is
        # the defect one level up that #1031 is about.
        machinery = set()
        for pattern in chc.INSTRUMENT_PATTERNS:
            machinery.update(
                rel for _rule, rel in self.declined
                if fnmatch.fnmatchcase(rel, pattern))
        self.assertTrue(
            machinery,
            "no declined file matches INSTRUMENT_PATTERNS, so the control side of "
            "this case has nothing to separate and 'only prose carries a flag' is "
            "not being checked against anything")
        self.assertNotIn(
            RECORD_FILE, machinery,
            f"{RECORD_FILE} is prose the rule should be judging, so it is being "
            f"excluded as machinery and this case would pass on a decline of the "
            f"wrong rule")
        outside = []
        for rel in sorted({rel for _rule, rel in self.declined}):
            if not (REPO / rel).is_file():
                continue  # a declined *directory* holds no sentence to read
            with self.subTest(declined=rel):
                sites = chc.prose_sites(str(REPO), self.workflows,
                                        self.unreadable, files=[rel], declined=[])
                # `verdict_of()` per site rather than a `zip()` against
                # `prose_problems()`: that function emits nothing for a quoted
                # site, so zipping it against the sites pairs each problem with
                # whichever site happens to share its index and reports a flag
                # against a sentence that carries none.
                outside.extend((rel, site[1], squash(site[2]))
                               for site in sites
                               if self.verdict_of(site) == FLAGGED)
        unexpected = sorted({rel for rel, _line, _text in outside
                             if rel != RECORD_FILE and rel not in machinery})
        self.assertEqual(
            unexpected, [],
            "a declined file that is neither the record file nor the checker's own "
            "machinery carries a flagged site, so 'only prose carries a flag' is no "
            "longer what this tree holds:\n"
            + "\n".join(f"  {rel}:{line} {text[:120]}"
                        for rel, line, text in outside))
        self.assertTrue(
            any(rel == RECORD_FILE for rel, _l, _t in outside),
            "the record file is read here and carries no flag, so the page's claim "
            "that the decline is what hides these is not being tested")
        # The split, printed rather than asserted: a reader can see how the flags
        # divide without the page carrying a figure that the next suite moves.
        print(f"census[flags outside the derived population]: "
              f"{len(outside)} across record file and the checker's own "
              f"machinery, which is the whole of them")

    def test_the_record_file_is_held_by_the_decline_and_not_by_its_extension(self):
        # The two halves of the finding kept apart, because "declined" and "no
        # longer flagged" are the same silence for different reasons and only one
        # of them is a scope fact. The rule that holds the file is named and its
        # reason comes from the rule itself rather than from a restatement here.
        held = [rule for rule, rel in self.declined if rel == RECORD_FILE]
        self.assertEqual(
            held, ["instrument-or-record"],
            f"{RECORD_FILE} is not held by exactly the `instrument-or-record` "
            f"rule, which is the one the case above reads around")
        self.assertNotIn(
            RECORD_FILE, self.files,
            f"{RECORD_FILE} is both read and declined, so the derived population "
            f"and the case above are not reading the same set")

    def test_this_page_is_in_the_corpus_and_breaks_no_rule(self):
        # The self-consistency claim. A write-up about this census is itself a
        # `.md` under `docs/findings/`, so it is in the population the rule reads,
        # and it is the one place where a sentence about checkouts could go stale
        # next to a table of other people's sentences about checkouts. It needs no
        # exemption, and it had to earn that: the first draft of *this page*
        # described the scratch-tree control in the shape the control is pasted
        # in, and this case reddened the tool on it -- a sentence naming `ci.yml`'s
        # `gates` job and mentioning `claude.yml` without naming its job. The fix
        # was to name the job in the prose, which is the correction
        # `checkout-claim-corpus.md` records for its own first draft.
        page = "docs/findings/per-workflow-rule-census.md"
        self.assertIn(
            page, self.files,
            f"{page} is not read by the walk, so the claim that it needs no "
            f"exemption is untested")
        sites = [s for s in self.sites if s[0] == page]
        self.assertTrue(
            sites,
            f"{page} carries no depth claim naming a workflow, so nothing here "
            f"judges it and this case exercises nothing. That is allowed -- a page "
            f"making no such claim is out of scope for the rule -- but it means the "
            f"page is not being held to the rule it measures")
        unfixed = [f"{s[0]}:{s[1]}" for s in sites
                   if not s[5] and any(job is None for job in s[4].values())]
        self.assertEqual(
            unfixed, [],
            f"the page measuring the rule breaks the rule the sweep asserts: "
            f"{unfixed}. Either name the job, or quote the sentence -- and a page "
            f"that had to be exempted would be the same defect one level up that "
            f"this change is about")

    def test_this_suite_is_a_control_and_is_not_judged(self):
        # The glob that keeps working without an entry per suite. The two
        # pre-fix sentences below are in this file's source in the author's
        # voice, which is exactly what must not be judged; and a suite written
        # against this tool next year is covered by the same glob for the same
        # reason. Named here because "a list nobody remembers to extend fails
        # open" is the argument the corpus suite makes for the rule, and this is
        # the same argument applied to this file.
        self.assertTrue(
            any(fnmatch.fnmatchcase(
                "ec/tools/test_check_history_checkouts_census.py", pattern)
                for pattern in chc.INSTRUMENT_PATTERNS),
            "this suite is not matched by the glob that is supposed to hold it, "
            "so it is judged on the retracted sentences its own source carries")
        self.assertNotIn(
            "ec/tools/test_check_history_checkouts_census.py", self.files,
            "this suite is read by the walk despite being a control")

    def test_the_census_figures_are_printed_rather_than_asserted(self):
        # The counts, once, where a reader can see them. Nothing here asserts
        # one: they move on every write-up that touches checkouts, which is the
        # whole reason this suite exists rather than a figure in the page. The
        # tool prints its own on every run and `history_checkout_sites.py` prints
        # the corrected sites beside the line each matched; this is the census
        # counterpart, and the page quotes it rather than restating it.
        out = io.StringIO()
        with redirect_stdout(out):
            chc.report(str(REPO))
        text = out.getvalue()
        self.assertIn("The prose population is derived, not listed", text)
        self.assertIn("declined by `instrument-or-record`", text)

        def census(pool, label):
            quoted = [s for s in pool if s[5]]
            multi = [s for s in pool
                     if len([n for n in s[3] if n in self.workflows]) > 1]
            print(f"census[{label}]: {len(pool)} site(s) in "
                  f"{len({s[0] for s in pool})} file(s); "
                  f"{len(quoted)} quoted; {len(multi)} naming more than one "
                  f"readable workflow; {len(chc.prose_problems(pool))} flagged")

        census(self.sites, "derived population")
        census([s for s in self.sites
                if s[0].startswith(ISSUE_POPULATION[0])
                or s[0] in ISSUE_POPULATION[1:]], "#1046's population")
        census(self.record, f"{RECORD_FILE}, which the walk holds")


class ScratchTree(unittest.TestCase):
    """The declined-file read, over a tree of the case's own, not the repository.

    The committed case reads the record file out of the real repository with the
    real checker, which is the measurement. This one asks whether that read is
    possible *by construction* -- a file the walk holds, reached by handing
    `prose_sites()` the list rather than the walk's -- because a case that
    force-read a path the walk would have declined is only measuring the
    committed tree if the walk declines it for the reason the case believes.
    """

    def test_the_record_path_is_declined_by_rule_and_still_readable_by_naming_it(self):
        # The path is the record file's own, not an invented one, because the
        # point is that *this* path is the one the walk declines. A scratch file
        # at some other path would not be declined at all -- the rule matches a
        # named path and a glob, not a directory -- and the read below would then
        # prove nothing about a declined file.
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root)
        os.makedirs(os.path.join(root, ".github", "workflows"))
        with open(os.path.join(root, ".github", "workflows", "ci.yml"), "w",
                  encoding="utf-8") as handle:
            handle.write(workflow("CI", {"gates": [{"uses": True, "depth": 0}]}))
        os.makedirs(os.path.join(root, "docs", "findings"))
        with open(os.path.join(root, RECORD_FILE), "w",
                  encoding="utf-8") as handle:
            handle.write("# ci.yml has two checkouts and both are full-depth\n")
        workflows, unreadable = chc.load_workflows(root)
        files, declined = chc.walk_prose_files(root)
        self.assertNotIn(RECORD_FILE, files,
                         f"{RECORD_FILE} was read by the walk even though it is "
                         f"held by rule, so the read below is not a read past a "
                         f"decline")
        self.assertIn(("instrument-or-record", RECORD_FILE), declined,
                      f"{RECORD_FILE} is not held by the rule the committed case "
                      f"reads around")
        read = chc.prose_sites(root, workflows, unreadable,
                               files=[RECORD_FILE], declined=[])
        self.assertEqual(len(read), 1, read)
        self.assertEqual(len(chc.prose_problems(read)), 1,
                         "a claim read out of a declined file was not judged, so "
                         "the committed case's flags are coming from somewhere "
                         "else than the sentences it says they are")


if __name__ == '__main__':
    unittest.main()