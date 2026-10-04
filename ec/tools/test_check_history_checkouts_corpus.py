#!/usr/bin/env python3
"""Offline checks for the *derived* checkout-claim population. A scratch tree and the real one.

`test_check_history_checkouts.py` holds the rule and the two tools' five
corrected sentences. This holds the thing that changed under it: `PROSE_FILES`
is gone, the population is a walk of the tree, and everything that follows from
that -- the decline rules, the quotation rule, the per-workflow verdict over a
population nobody listed -- is only worth something if a reader has seen it
reject the text that was wrong and accept the text that was right.

**`test_check_history_checkouts.py` cannot show any of this on its own, and the
reason is the whole reason this file exists.** A checker that had quietly stopped
finding anything prints the same clean report as one that is working, and the
prose half is a report: it never fails a tree, so nothing on the committed tree
can tell the two apart. A count would not help either -- a count is satisfied by
any ten files, which is the same reason that suite pins the *set* of
`chc.PROSE_FILES` rather than its length. So the committed cases here pin the
derived file set as a list, pin the three #1009 markdown sites by name, and pin
the quotation count as a floor: each of those three goes red if the walk stops,
and each of them is a claim about *which* files rather than how many.

**The scratch-tree cases are the ones with teeth**, and they are pasted
verbatim from the pre-#1031 sources for the same reason that suite pastes its
own: a paraphrase that happened to name a job, or that lost the wrap a claim
sits across, would be a control passing for the wrong reason. The `workflow()`
builder and the tool's own constants are **imported** from that suite rather
than copied, which is what #1037 established and what leaves its controls a
single copy that cannot drift from the sources they were pasted from.

**Named `test_check_history_checkouts_corpus.py` rather than the shorter
`test_checkout_claim_corpus.py`** so that the `instrument-or-record` decline
rule's one glob, `ec/tools/test_check_history_checkouts*.py`, covers this file
without a second entry in a hand-kept list. A list of this checker's own suites
is the same defect one level up that #1031 is about: a fourth suite written
against the tool next year would have to be added to it by hand, and a list
nobody remembers to extend fails open.
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

# `workflow()` is the synthetic-workflow builder, and it is imported rather than
# copied so that the workflows these cases build are the same shape the sibling
# suite's twenty-four cases build. A second builder would be a second answer to
# "what does a workflow file look like", and the control here is a sentence and
# not the YAML around it.
from test_check_history_checkouts import workflow  # noqa: E402

# The four #1009 control sites, in the form that had to be found: the two tools'
# own sites and the three markdown ones. Each is named by `file` and by the job
# id its corrected sentence carries, which is the half that makes it a control
# -- a walk that found two of the three would leave a count green, and a reader
# that had found the file for the wrong reason would pass a site whose sentence
# names no job.
CONTROL_SITES = (
    ("docs/agent-pipeline.md", ("implement", "fix", "review", "resolve")),
    ("ec/ghidra/README.md", ("gates",)),
    ("docs/findings.md", ("gates", "workflows")),
)

# The files the derived walk finds a depth claim in, pinned as the *set*. A
# count is satisfied by any sixteen files, so a walk that had narrowed to the
# two tools and happened to find ten sites would leave a length assertion green.
# This list is what #1031 measured — thirteen files on the branch's own tree —
# and the `#1032` × `#1031` merge added three more, each a write-up `main`
# landed after the fork and the walk had therefore never seen: #1032's
# `history-checkout-prompt-reach.md`, and #1033's
# `history-checkouts-gate-wiring.md` and the prepared
# `docs/ci/agent-gates-capture-claims.patch`. **That is the sweep working
# rather than drifting**: three files nobody listed entered a population that is
# derived, and the two claims they carried that named `ci.yml` without a job
# were found by it and corrected per `docs/findings.md` §4a-4d. A file leaving
# or entering the population is a finding about the tree and this is where it
# is read.
EXPECTED_CORPUS_FILES = (
    ".github/scripts/agent-gates.sh",
    "docs/agent-pipeline.md",
    "docs/ci/agent-gates-capture-claims.patch",
    "docs/findings.md",
    "docs/findings/checkout-claim-corpus.md",
    "docs/findings/committed-checkout-triples-held.md",
    "docs/findings/history-checkout-claim-per-workflow.md",
    "docs/findings/history-checkout-prompt-reach.md",
    "docs/findings/history-checkout-run-contract.md",
    "docs/findings/history-checkout-site-identity.md",
    "docs/findings/history-checkouts-gate-wiring.md",
    "docs/findings/per-workflow-rule-census.md",
    "docs/findings/provenance-clone-depth-behaviour.md",
    "docs/findings/testdata-index-repair-census.md",
    "docs/findings/testdata-row-claims-repair-measurement.md",
    "docs/findings/xdata-moved-ranks-pin-decisions.md",
    "ec/ghidra/README.md",
    "ec/tools/history_checkout_sites.py",
    "ec/tools/measure_index_repair_visibility.py",
    "ec/tools/test_verify_provenance_clone_depth.py",
    "ec/tools/verify_reassembly.py",
)
# `tools/README.md` left the population on 2026-10-02: its depth claims were in
# the per-suite table rows, and the table was removed in favour of each suite's
# own docstring, where the same claims already were.
#
# `per-workflow-rule-census.md` entered it the other way, on 2026-10-04 with
# #1046: a write-up about this rule that names a workflow and a depth word, so
# the sweep found it and judged it. It carries one site, and it names a job of
# every workflow it names -- the first draft did not, and reddened the tool
# instead, which is why the correction was to name the job in the prose rather
# than to exempt the page.

# **`docs/agent-pipeline.md:103` as it stood before #1031**, verbatim from the
# pre-fix source. It is the new control and the reason one is needed: the three
# #1009 sites are all *already corrected*, so a checker that had quietly stopped
# flagging anything would pass every one of them. This one is the pre-fix
# wording of a sentence #1031 corrected, and it is four claims wide -- it names
# four workflows and no job of any of them -- so it fails once per workflow and
# a case that only checked the count would miss a widening that went half-way.
#
# A fifth file's worth of silence is the other half of the point: this text lives
# at a path nothing in the tree listed before #1031, and the issue's own words
# for the defect it wants fixed are "a fourth copy in a fifth file is a row in
# the report instead of a fourth sentence nobody reads".
PRE_FIX_AGENT_PIPELINE = (
    "The mode audits a `listing_digest` migration against two committed "
    "revisions (`docs/findings.md` §14f), so how deep the clone is is part of "
    "its contract the way the assembler is part of `--report`'s: the agent "
    "stages check out with `fetch-depth: 0` (`agent-implement.yml:118`, "
    "`agent-fix.yml:116`, `agent-review.yml:85`, `agent-conflicts.yml:156`) "
    "and can run it.")

# The two quotations, one per shape a retraction takes in this corpus. **Neither
# is exempt and both are reported**: a boundary rule cannot tell a correction's
# quotation from a claim, so the sweep says which it found and declines to judge
# it, with the `file:line` a reader would otherwise have had to go looking for.
# Dropping them silently would be the same as dropping a file from the walk --
# the suite could not tell a quotation from a site nobody looked at.
QUOTED_IN_QUOTES = (
    'The sentence read "both of ci.yml\'s checkouts are default-depth", which '
    'was false of every tree since #407.')
QUOTED_IN_A_FENCE = (
    "```\n"
    "# both of ci.yml's checkouts are default-depth and cannot resolve it\n"
    "```\n")


class ScratchTree(unittest.TestCase):
    """A throwaway repository root the walk is pointed at with `prose_sites()`."""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root)
        self.put(".github/workflows/ci.yml", workflow("CI", {
            "gates": [{"uses": True, "depth": 0},
                      {"run": ".github/scripts/agent-gates.sh"}],
            "workflows": [{"uses": True}],
        }))
        self.put(".github/workflows/agent-implement.yml", workflow("Implement", {
            "implement": [{"uses": True, "depth": 0}],
        }))
        self.put(".github/workflows/agent-fix.yml", workflow("Fix", {
            "fix": [{"uses": True, "depth": 0}],
        }))
        self.put(".github/workflows/agent-review.yml", workflow("Review", {
            "review": [{"uses": True, "depth": 0}],
        }))
        self.put(".github/workflows/agent-conflicts.yml", workflow("Conflicts", {
            "resolve": [{"uses": True, "depth": 0}],
        }))
        self.put(".github/workflows/claude.yml", workflow("Claude", {
            "claude": [{"uses": True}],
        }))

    def put(self, rel, text):
        """A file at `rel` under the scratch root."""
        path = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        return path

    def sites(self):
        """(sites, files, declined) over the scratch tree."""
        workflows, unreadable = chc.load_workflows(self.root)
        files, declined = chc.walk_prose_files(self.root)
        return chc.prose_sites(self.root, workflows, unreadable, files, declined), \
            files, declined

    def problems(self):
        """(depth problems, prose problems, files, declined) over the tree."""
        workflows, unreadable = chc.load_workflows(self.root)
        files, declined = chc.walk_prose_files(self.root)
        sites = chc.prose_sites(self.root, workflows, unreadable, files, declined)
        return chc.depth_problems(workflows), chc.prose_problems(sites), files, declined


class CorpusTests(ScratchTree):
    """The walk: what it reads, what it refuses, and what it says about a claim."""

    def test_a_fifth_file_is_in_the_population_with_nothing_listing_it(self):
        # The issue's own sentence, and the reason a typed list cannot be fixed
        # by adding an entry. The path is chosen to be one no earlier list held:
        # not `PROSE_FILES`' two tools, not a `.md` beside them, and not the
        # three #1009 corrected. A checker reading the old constant would report
        # nothing at all here and exit 0.
        self.put("docs/some/where/else.md", PRE_FIX_AGENT_PIPELINE + "\n")
        _depth, prose, files, _declined = self.problems()
        self.assertIn("docs/some/where/else.md", files)
        self.assertEqual(len(prose), 4, prose)
        for workflow_name in ("agent-implement.yml", "agent-fix.yml",
                              "agent-review.yml", "agent-conflicts.yml"):
            self.assertTrue(
                any(workflow_name in p for p in prose),
                f"{workflow_name} was not reported: {prose}")

    def test_the_pre_fix_sentence_is_found_where_the_corrected_one_would_pass(self):
        # The pair that keeps the first case from passing for the wrong reason.
        # Without the corrected form beside it, a checker that flagged *every*
        # sentence naming a workflow would pass the case above. It names both of
        # `ci.yml`'s jobs rather than none, which is the shape the four #1009
        # corrections ended in, and it has to be a *site* rather than silence:
        # a sentence naming no workflow at all is not one, and would have made
        # this case pass without anything reading it.
        self.put("docs/notes.md",
                 "# ci.yml's `gates` job checks out with `fetch-depth: 0` and "
                 "its `workflows` job is the default-depth one\n")
        sites, _files, _declined = self.sites()
        found = [s for s in sites if s[0] == "docs/notes.md"]
        self.assertEqual(len(found), 1,
                         f"a corrected sentence is not one site, so the case "
                         f"above would pass without anything reading it: {found}")
        self.assertFalse(found[0][5], "the corrected sentence was read as quoted")
        _depth, prose, _files, _declined = self.problems()
        self.assertEqual(prose, [], f"a sentence naming both jobs was flagged:\n{prose}")

    def test_a_claim_quoted_in_double_quotes_is_reported_and_not_flagged(self):
        self.put("docs/notes.md", QUOTED_IN_QUOTES + "\n")
        sites, _files, _declined = self.sites()
        found = [s for s in sites if s[0] == "docs/notes.md"]
        self.assertEqual(len(found), 1, found)
        self.assertTrue(found[0][5], "the quotation was not recognised as one")
        self.assertEqual(chc.prose_problems(sites), [])

    def test_a_claim_pasted_into_a_fenced_block_is_reported_and_not_flagged(self):
        self.put("docs/notes.md", QUOTED_IN_A_FENCE)
        sites, _files, _declined = self.sites()
        found = [s for s in sites if s[0] == "docs/notes.md"]
        self.assertEqual(len(found), 1, found)
        self.assertTrue(found[0][5], "the fenced block was not recognised")
        self.assertEqual(chc.prose_problems(sites), [])

    def test_a_job_of_the_second_workflow_named_is_read_for_that_workflow(self):
        # The verdict must not depend on which name sorts first, and this pins
        # that it does not. `agent-fix.yml` sorts before `ci.yml`, the sentence
        # names only `fix`, and the report has to name `ci.yml` -- the one with
        # no job of it -- and *not* `agent-fix.yml`, whose job it carries. A
        # reader that stopped at the first name would flag the other one and
        # pass this. #1034 is what made the rule per workflow rather than per
        # sentence; this is the case that keeps that from narrowing back.
        self.put("docs/notes.md",
                 "# agent-fix.yml's `fix` job is full-depth and ci.yml is "
                 "default-depth throughout\n")
        _depth, prose, _files, _declined = self.problems()
        self.assertEqual(len(prose), 1, prose)
        head = prose[0].split(" -- ", 1)[0]
        self.assertIn("names ci.yml and no job of it", head)
        self.assertNotIn("agent-fix.yml", head)

    def test_a_code_span_around_one_term_is_not_a_quotation(self):
        # The floor, and the one that made the first draft of the quote rule
        # useless. A markdown sentence writes `fetch-depth: 0` in backticks as a
        # matter of course, so reading any code span as someone else's words
        # would exempt every claim in every markdown file and leave the rule
        # asserting nothing at all -- the sweep would go green by finding less.
        self.put("docs/notes.md",
                 "# ci.yml's checkouts are `fetch-depth: 0` and the agent "
                 "stages are shallow\n")
        _depth, prose, _files, _declined = self.problems()
        self.assertEqual(len(prose), 1, f"a code span was read as a quotation:\n{prose}")
        self.assertIn("names ci.yml and no job of it", prose[0].split(" -- ", 1)[0])

    def test_a_bold_claim_in_the_authors_own_voice_is_judged(self):
        # The other half of the same floor, and the reason bold and italic are
        # not in `MARKED` at all: they are how this repository emphasises a
        # sentence in its own voice, and §86's corrected claim is one. Reading
        # emphasis as quotation would both mislabel it in the report and excuse
        # the very claim the rule exists for.
        self.put("docs/notes.md",
                 "**ci.yml checks out with `fetch-depth: 0` throughout.**\n")
        _depth, prose, _files, _declined = self.problems()
        self.assertEqual(len(prose), 1, f"a bolded claim was excused:\n{prose}")

    def test_a_decline_names_its_rule_and_is_not_a_finding_about_a_sentence(self):
        # The two halves of the scope vocabulary, side by side, because keeping
        # them apart is the whole of the calibration rule here. `vendor/` is out
        # of scope for the walk; the same sentence written in a file that *is*
        # read is judged. A report that conflated them would be claiming
        # something about prose it never opened.
        self.put("vendor/control-center-1.2.3/notes.md",
                 "# ci.yml checks out with `fetch-depth: 0` throughout\n")
        self.put("docs/notes.md",
                 "# ci.yml checks out with `fetch-depth: 0` throughout\n")
        _depth, prose, files, declined = self.problems()
        self.assertNotIn("vendor/control-center-1.2.3/notes.md", files)
        held = [rel for rule, rel in declined
                if rule == "vendored-input"]
        self.assertIn("vendor", held, f"vendor/ was not declined by rule: {declined}")
        self.assertEqual(len(prose), 1, prose)
        self.assertTrue(prose[0].startswith("docs/notes.md:"), prose[0])

    def test_a_deployed_decompile_tree_is_declined_and_a_git_directory_is_not_read(self):
        # The other two rules, so that widening the walk cannot quietly start
        # reading machine output or version-control internals. `decompiled/` is
        # where a depth word is a string somebody typed rather than a claim.
        self.put("ec/decompiled/README.md",
                 "# ci.yml checks out with `fetch-depth: 0` throughout\n")
        self.put(".git/objects/README",
                 "# ci.yml checks out with `fetch-depth: 0` throughout\n")
        _depth, prose, files, declined = self.problems()
        self.assertEqual(prose, [], f"a declined path was judged:\n{prose}")
        for rule, rel in (("generated-output", "ec/decompiled"),
                          ("repository-internal", ".git")):
            self.assertIn((rule, rel), declined, f"{rule} did not hold: {declined}")
        self.assertNotIn("ec/decompiled/README.md", files)

    def test_the_checks_own_machinery_is_declined_by_the_same_rule(self):
        # The rule that is a glob rather than a list, and the reason a fourth
        # suite written against this tool next year needs no edit here. This
        # file is matched by `ec/tools/test_check_history_checkouts*.py` and is
        # holding `PRE_FIX_AGENT_PIPELINE` in its own source -- a claim in the
        # author's voice, which is precisely what must not be judged.
        self.put("ec/tools/test_check_history_checkouts.py",
                 PRE_FIX_AGENT_PIPELINE + "\n")
        _depth, prose, files, declined = self.problems()
        self.assertEqual(prose, [], f"the check's own suite was judged:\n{prose}")
        self.assertIn(("instrument-or-record",
                       "ec/tools/test_check_history_checkouts.py"), declined)
        self.assertTrue(
            any(fnmatch.fnmatchcase("ec/tools/test_check_history_checkouts_corpus.py",
                                    pattern)
                for pattern in chc.INSTRUMENT_PATTERNS),
            "this suite is not matched by the glob that is supposed to cover it, "
            "so the rule only holds because of a hand-kept entry -- which is the "
            "defect one level up that this change is about")

    def test_a_file_that_is_not_text_is_not_a_candidate_and_is_not_declined(self):
        # The third of the three answers, and the one that is easiest to get
        # wrong in the direction that looks like rigour. A `.bin` under the
        # repository root is neither read (it carries no prose) nor *declined*
        # (nothing refused it) -- it is not a candidate, and a report that listed
        # every one of them would be listing the tree rather than scoping it.
        self.put("ec/firmware/blob.bin", "# ci.yml is `fetch-depth: 0`\n")
        _depth, prose, files, declined = self.problems()
        self.assertNotIn("ec/firmware/blob.bin", files)
        self.assertEqual(prose, [])
        self.assertNotIn("ec/firmware/blob.bin",
                         [rel for _rule, rel in declined])


class CommittedCorpusTests(unittest.TestCase):
    """The derived population against the tree as it stands."""

    def setUp(self):
        self.workflows, self.unreadable = chc.load_workflows(str(REPO))
        self.files, self.declined = chc.walk_prose_files(str(REPO))
        self.sites = chc.prose_sites(str(REPO), self.workflows, self.unreadable,
                                     self.files, self.declined)

    def test_the_corpus_is_the_list_of_files_this_measured(self):
        # The set, not the length, for the reason the module docstring gives: a
        # count is satisfied by any thirteen files. This is also the case that
        # goes red if `PROSE_FILES` ever comes back -- the two tools are in the
        # list, but eleven other files are, and a constant naming two of them
        # could not produce it.
        found = {rel for rel, *_rest in self.sites}
        self.assertEqual(
            found, set(EXPECTED_CORPUS_FILES),
            "the derived population's file set moved. A file leaving it is "
            "usually a file that stopped being prose about checkouts, and one "
            "entering it is a claim this sweep has not judged -- read the site "
            "before changing this list.")

    def test_the_corpus_is_large_enough_to_be_a_sweep(self):
        # The floor beneath the list above, and it is a floor on the walk rather
        # than on the sites: a checker that had narrowed its population back to
        # a couple of files could satisfy a short list, and this is what it
        # could not. The number is deliberately far below what the walk reads on
        # this tree, so that adding a file is not a failure -- the walk's total
        # is printed on every run rather than pinned here, because it moves
        # every time a new or untracked text file appears, and a figure written
        # beside the sentences is what this change exists to stop.
        self.assertGreaterEqual(
            len(self.files), 300,
            f"the walk read only {len(self.files)} text file(s), which is a "
            f"narrowed population rather than a tree")

    def test_each_of_the_three_corrected_markdown_sites_is_still_a_site(self):
        # The three #1009 corrected in markdown, by file and by the job id the
        # corrected sentence carries. A walk that found two of the three would
        # leave a count green, and a file found for the wrong reason -- named by
        # some other sentence in it -- would pass a site whose own claim names
        # no job, so the job id is checked in the site itself and not beside it.
        by_file = {}
        for rel, _line, sentence, _named, _jobs, _quoted in self.sites:
            by_file.setdefault(rel, []).append(sentence)
        for rel, jobs in CONTROL_SITES:
            with self.subTest(site=rel):
                self.assertIn(rel, by_file,
                              f"{rel} carries no depth claim this sweep found")
                self.assertTrue(
                    any(all(j in s for j in jobs) for s in by_file[rel]),
                    f"no sentence in {rel} names {jobs}, which is what the "
                    f"#1009 correction put there")

    def test_no_judged_site_names_a_workflow_and_no_job(self):
        # The rule, over the derived population rather than over two named tools.
        # Written as it is -- over the sites, not over the tool's own verdict --
        # so that a walk which found nothing at all would fail it on the count
        # the case above holds, rather than passing on an empty list.
        unfixed = [f"{rel}:{line}" for rel, line, _s, _n, jobs, quoted in self.sites
                   if not quoted and any(j is None for j in jobs.values())]
        self.assertEqual(
            unfixed, [],
            "a derived site names a workflow and no job of it. Either correct it "
            "and leave the old wording visible per docs/findings.md §4a-4d, or "
            "record why it is a quotation -- and note that a claim the rule "
            "cannot see is not a claim that is not there.")

    def test_the_quotations_are_reported_rather_than_dropped(self):
        # The floor on the quote rule, and the reason it is a count and not
        # nothing: `prose_problems()` skips a quoted site, so a quote rule that
        # matched nothing would leave every site judged and every case above
        # green. The retractions in the tree are the population here -- this
        # suite's sibling pastes four, the #1009 write-up holds all four in a
        # table, and §14f and `ec/ghidra/README.md` each carry one.
        quoted = [f"{rel}:{line}" for rel, line, _s, _n, _j, quoted in self.sites
                  if quoted]
        self.assertGreaterEqual(
            len(quoted), 5,
            f"only {len(quoted)} quoted claim(s) found. A retraction quotes the "
            f"sentence it retracts, so this number going to zero means the quote "
            f"rule stopped matching -- and every site above would then be judged "
            f"against a defect it does not have.")

    def test_each_decline_rule_still_holds_on_the_committed_tree(self):
        # All four, and the paths resolved rather than the patterns, so a rule
        # that has stopped matching is a failure naming what it should have
        # matched. `vendor/` is the one the plan names outright: the walk must
        # not start reading it, and the report must say it did not.
        held = {}
        for rule, rel in self.declined:
            held.setdefault(rule, []).append(rel)
        self.assertIn("vendor", held.get("vendored-input", []))
        self.assertIn(".git", held.get("repository-internal", []))
        self.assertIn("ec/decompiled", held.get("generated-output", []))
        for rel in held.get("vendored-input", []) + \
                held.get("generated-output", []):
            self.assertFalse(rel.startswith("vendor/") and rel in self.files,
                             f"{rel} was both declined and read")
        for rel in held.get("instrument-or-record", []):
            self.assertNotIn(rel, self.files,
                             f"{rel} was declined and also read")
        self.assertIn("ec/tools/check_history_checkouts.py",
                      held.get("instrument-or-record", []),
                      "the checker itself is not declined, so it would be judged "
                      "on the sentences its own docstring quotes")
        self.assertIn("ec/tools/test_check_history_checkouts_corpus.py",
                      held.get("instrument-or-record", []),
                      "this suite is not declined, and it holds a pre-fix claim "
                      "in its own source")

    def test_this_changes_own_write_up_is_in_the_corpus_and_is_not_flagged(self):
        # The self-consistency claim, and it is worth a case because it is the
        # one a reviewer will check by hand: a write-up *about* the sweep is
        # itself a `.md` under `docs/findings/`, so it is in the population, and
        # it is the one place where a sentence about checkouts could most easily
        # go stale — it quotes thirteen of them in the table above, next to what
        # each says now. It needs no `instrument-or-record` exclusion, and this
        # is what holds it to that. The first draft of that page did redden the
        # tool, on a sentence about `claude.yml`'s job id; the correction names
        # no depth word at all rather than reaching for an exemption.
        page = "docs/findings/checkout-claim-corpus.md"
        self.assertIn(page, EXPECTED_CORPUS_FILES)
        sites = [s for s in self.sites if s[0] == page]
        self.assertTrue(sites, f"{page} is not in its own population, so the "
                               f"claim that it needs no exclusion is untested")
        unfixed = [f"{s[0]}:{s[1]}" for s in sites
                   if not s[5] and any(j is None for j in s[4].values())]
        self.assertEqual(
            unfixed, [],
            f"the write-up about the sweep breaks the rule the sweep asserts: "
            f"{unfixed}. Either name the job, or quote the sentence -- and a "
            f"page that had to be exempted would be the same defect one level "
            f"up that this change is about.")

    def test_the_report_prints_the_corpus_figure_and_every_decline(self):
        # The report is this half's product, and a figure it computed but did
        # not print is a figure a reader cannot check -- which is the whole
        # reason the suite pins the derived set as a list.
        out = io.StringIO()
        with redirect_stdout(out):
            chc.report(str(REPO))
        text = out.getvalue()
        self.assertIn("The prose population is derived, not listed", text)
        for rule, _names, _why in chc.DECLINE_RULES:
            self.assertIn(f"declined by `{rule}`", text)
        self.assertIn("quoted -- not judged", text)


if __name__ == '__main__':
    unittest.main()
