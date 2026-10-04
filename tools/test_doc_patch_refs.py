#!/usr/bin/env python3
"""Offline checks for `tools/check_doc_patch_refs.py`'s invariants.

The tool holds two directions that `tools/test_agent_gates_patches.py` does not
and cannot: that every `docs/ci/agent-gates-*.patch` name in the files it reads
resolves to a file, and that every prepared change on disk is named somewhere.
The sibling holds each patch *header's* `git apply` line to the file it came
from; this holds the prose around the patch set, which is a different surface
and breaks the same way. #745's fold deleted `agent-gates-testdata-index.patch`
and left six references to repoint by hand across five files, and nothing in the
tree noticed a miss.

**"Every" is bounded by the file set, and the bound is named.** The reference
direction reads `REFERENCE_GLOBS` -- `**/*.md` and `docs/ci/**/*.patch` -- and
not the `.py` population, which is out of scope and is listed by file and by
path in the tool's own docstring and in
`docs/findings/doc-patch-ref-file-sets.md`. Every case here that says "every"
means every reference in that set.

**What is pinned here is the refusal, not the count.** Every case below is a way
the check can be wrong in the direction that matters: a pattern that quietly
stops matching (the §14b defect -- a run that reads nothing exits 0 and looks
like a clean tree), a pattern loose enough to match prose that was never naming a
file, a declared set that stops being read, and an exemption that widens or
rots. No expected population is asserted, for the reason
`tools/test_readme_suite_table.py`'s docstring gives: an expected count turns
every added reference into a failure, which is the wrong trade.

Two things are pinned by name. `HISTORICAL` is pinned in **both** directions,
one case per key. A key that has stopped being absent -- a patch reappearing
under that name -- and a key that has stopped being cited -- the reference being
edited away -- are the two ways an exemption rots with nobody touching the prose,
and either one left unchecked is a `HISTORICAL` entry that reads as a decision
and is not one. Both failures name the key. `PREPARED_NON_PATCH` is pinned the
same way, for the same reason and for a file a glob over `.patch` cannot see.

Every mutation happens in a `tempfile` scratch tree, and the tool itself writes
only into the trees it is handed, so nothing here touches `docs/ci/`.
"""
import io
import contextlib
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import check_doc_patch_refs as tool  # noqa: E402

HERE = Path(__file__).resolve().parent
REPO = HERE.parent


def quiet(fn, *argv, **kwargs):
    """Run one of the tool's reporting functions with its transcript captured.

    The printing is exercised on the way through; what is asserted is the
    return value and, in the one case that is about wording, the captured
    stdout. Without this a refusal's own lines land in the suite's output and
    the next real failure is the one to read.
    """
    sink = io.StringIO()
    with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
        rc = fn(*argv, **kwargs)
    return sink.getvalue(), rc


class ParseTests(unittest.TestCase):
    """The discovery, on inline text.

    Without these the set comparison in `LiveTreeTests` is one bad regex away
    from passing vacuously: an empty parse matches an empty population, which is
    the §14b defect the runner's empty-discovery guard exists for.
    """

    def test_both_backtick_spellings_are_read(self):
        # A `docs/ci/`-only pattern would hold 64% of this tree's references
        # and would not see three of the four deliberate ones, because the bare
        # spelling is how a table row's first cell and a sentence naming one
        # specific file have to be written.
        found = tool.references(
            "a `docs/ci/agent-gates-capture-claims.patch` and a bare "
            "`agent-gates-capture-claims.patch`")
        self.assertEqual([n for _k, n, _l in found],
                         ["agent-gates-capture-claims.patch"] * 2)

    def test_a_glob_shaped_span_is_not_a_name(self):
        # Prose describing the *set* is not prose naming one file. The `*` is
        # outside the character class for exactly this reason, and the shape is
        # live eight times in this tree.
        for text in ("`docs/ci/agent-gates-*.patch`",
                     "`agent-gates-*.patch`"):
            with self.subTest(text=text):
                self.assertEqual(tool.references(text), [])

    def test_the_yml_sibling_is_not_a_name(self):
        # `docs/ci/agent-gates-deep-schedule.yml` is a `cp` into
        # `.github/workflows/`, not a patch, and the pattern ends in `.patch`
        # rather than in a list of the files that are not patches.
        self.assertEqual(
            tool.references("`docs/ci/agent-gates-deep-schedule.yml` "
                            "`agent-gates-deep-schedule.yml`"), [])

    def test_a_link_is_read_and_its_name_is_the_last_component(self):
        # The only link onto a patch in the whole tree is
        # `../ci/<name>` from inside `docs/findings/`, and it is the same file
        # the `docs/ci/`-qualified spelling names.
        found = tool.references("[the patch](../ci/agent-gates-gap-text-check.patch)")
        self.assertEqual(found,
                         [(tool.KIND_LINK, "agent-gates-gap-text-check.patch", 1)])

    def test_a_url_is_not_a_repository_path(self):
        # The same `[^:)]` guard `check_doc_links` uses. Without it an external
        # URL ending in `.patch` resolves against this tree and is a miss
        # nobody can fix.
        self.assertEqual(
            tool.references("[x](https://example.invalid/a.patch)"), [])

    def test_one_line_in_both_spellings_is_two_references(self):
        # The committed tree's single link is written this way -- a backticked
        # path that is also the link's text -- and the population line is
        # arithmetic that has to come out right, so the shape is pinned rather
        # than left to whichever pattern runs first.
        found = tool.references("x [`agent-gates-a.patch`](../ci/agent-gates-a.patch)")
        self.assertEqual([k for k, _n, _l in found],
                         [tool.KIND_NAME, tool.KIND_LINK])


class RefusalTests(unittest.TestCase):
    """The refusals, on trees small enough to read the whole finding list."""

    def test_an_absent_name_is_reported_by_name_and_by_citing_file(self):
        with tool.mini_tree({"docs/note.md":
                             "gone: `agent-gates-never-existed.patch`\n",
                             "docs/ci/agent-gates-a.patch": "a\n"}) as root:
            found = tool.scan(root)
            self.assertEqual([(n, rel) for rel, _l, n in found.stale],
                             [("agent-gates-never-existed.patch", "docs/note.md")])
            self.assertEqual(quiet(tool.check_mode, found)[1], 1)

    def test_a_fourth_absent_name_is_refused(self):
        # The bound on the enumeration, stated rather than hidden: `HISTORICAL`
        # is two names wide and a name outside it is stale, so adding a third
        # absent reference cannot make the check pass by being tolerated.
        with tool.mini_tree({"docs/note.md": "`agent-gates-a.patch`\n"
                                             "`agent-gates-b.patch`\n",
                             "docs/ci/agent-gates-a.patch": "a\n"}) as root:
            found = tool.scan(root)
            self.assertEqual([n for _r, _l, n in found.stale],
                             ["agent-gates-b.patch"])

    def test_a_patch_nobody_names_is_reported(self):
        # The mirror of the stale half, and the half that broke in
        # `test_readme_suite_table.py`: a suite committed with no row.
        with tool.mini_tree({"docs/note.md": "no names here\n",
                             "docs/ci/agent-gates-a.patch": "a\n"}) as root:
            found = tool.scan(root)
            self.assertEqual(found.uncited, ["agent-gates-a.patch"])
            self.assertEqual(quiet(tool.check_mode, found)[1], 1)

    def test_an_empty_tree_is_refused_rather_than_read_as_clean(self):
        # The §14b shape. A run that located nothing and a run that found
        # nothing wrong look identical from the exit code alone, and the second
        # reading is the one that gets a broken pattern accepted.
        with tool.mini_tree({"docs/note.md": "nothing here\n"}) as root:
            found = tool.scan(root)
            self.assertFalse(found.refs)
            self.assertFalse(found.links)
            self.assertEqual(quiet(tool.check_mode, found)[1], 1)

    def test_verbose_names_the_line_and_the_default_does_not(self):
        with tool.mini_tree({"docs/one.md": "first\n`agent-gates-gone.patch`\n",
                             "docs/ci/agent-gates-a.patch": "a\n"}) as root:
            found = tool.scan(root)
            plain, _ = quiet(tool.report, found)
            loud, _ = quiet(tool.report, found, verbose=True)
            self.assertIn("STALE: agent-gates-gone.patch <- docs/one.md", plain)
            self.assertNotIn("docs/one.md:2:", plain)
            self.assertIn("docs/one.md:2: names `agent-gates-gone.patch`", loud)


class HistoricalTests(unittest.TestCase):
    """`HISTORICAL`, one case per key and in both directions.

    Both halves of each key are the point. An entry that is only ever checked
    for *not firing* is a convention rather than a fact, and the issue asks for
    the opt-out to be a fact the suite can check; an entry that is only ever
    checked for firing is an entry that can rot without anybody noticing, which
    is the same silent-pass shape the empty-discovery guard above is for.
    """

    def test_every_key_is_one_of_these(self):
        # A count here is not the population: it is the size of the exemption,
        # and the exemption is what a new absent name would have to join. It is
        # pinned because a key appearing silently *widens* what this check
        # tolerates, which is the one direction a bare "is it still absent" test
        # would not notice. **This is a census of the enumeration, not of the
        # tree**, so it does not move as suites land or files are added -- and
        # the rule it exists to enforce is that the set below is the whole of
        # it, so a key added anywhere else goes red here rather than widening
        # the exemption quietly. That is why it stays, in the form of the
        # enumeration itself rather than a number beside it.
        #
        # `agent-gates-check-history-checkouts.patch` is the filename #1033
        # asked for and the same saturated `gate` list declined, exactly as
        # #745 declined the second. #1033's own case for it is in
        # docs/findings/history-checkouts-gate-wiring.md.
        #
        # `agent-gates-audit-call-targets-self-test.patch` is the filename #1094
        # asked for, declined one region further along: the tail of
        # `check_ghidra_tooling()` was already held, and two patches cut at one
        # anchor collide in both orders while each applies alone. The call
        # folds into `docs/ci/agent-gates-reassembly-bound-check.patch` and the
        # write-up names what was asked for beside what was prepared. Its own
        # case is in docs/findings/audit-call-targets-gate-arm.md.
        self.assertEqual(sorted(tool.HISTORICAL),
                         ["agent-gates-audit-call-targets-self-test.patch",
                          "agent-gates-check-history-checkouts.patch",
                          "agent-gates-claims-and-testdata.patch",
                          "agent-gates-testdata-index.patch"])

    def test_each_key_is_still_absent_from_docs_ci(self):
        for name in sorted(tool.HISTORICAL):
            with self.subTest(name=name):
                self.assertNotIn(name, tool.on_disk(REPO),
                                 f"{name} is in HISTORICAL and is on disk. The "
                                 f"exemption has nothing to exempt, and the "
                                 f"patch's own suite is the file that should "
                                 f"know it came back.")

    def test_each_key_is_still_cited(self):
        # Prose only, deliberately: this half of the enumeration is what says
        # the exemption is still earning its place, and the justification for a
        # historical name is a *prose* record of what the file was. A patch
        # header naming the key is not that, and `ReferenceSetTests` holds the
        # case that shows what counting it would cost.
        prose, _prepared = tool.reference_files(REPO)
        cited = {n for rel in prose
                 for _k, n, _l in tool.references(
                     (REPO / rel).read_text(encoding="utf-8"))}
        for name in sorted(tool.HISTORICAL):
            with self.subTest(name=name):
                self.assertIn(
                    name, cited,
                    f"{name} is in HISTORICAL and no markdown file names it "
                    f"any more. Either the reference was edited away -- which "
                    f"means the exemption is not earning its place -- or the "
                    f"edit missed a name, which is the miss this check exists "
                    f"to catch.")

    def test_a_key_that_stops_being_exempt_is_refused(self):
        # Both directions of the same claim, demonstrated rather than asserted
        # on a `tempfile` copy of the committed tree: a patch reappearing under
        # a historical name, and a reference to one being edited away. Both go
        # red, and both name the key rather than counting it.
        for name, restored in (("agent-gates-testdata-index.patch", True),
                               ("agent-gates-claims-and-testdata.patch", False)):
            with self.subTest(name=name, restored=restored):
                with tool.scratch_tree() as root:
                    if restored:
                        (root / "docs" / "ci" / name).write_text("a\n",
                                                                 encoding="utf-8")
                    else:
                        for rel in tool.markdown_files(root):
                            path = root / rel
                            text = path.read_text(encoding="utf-8")
                            if name in text:
                                path.write_text(text.replace(name, "a retired name"),
                                                encoding="utf-8")
                    found = tool.scan(root)
                    self.assertEqual(found.dead, [name])
                    self.assertEqual(quiet(tool.check_mode, found)[1], 1)


class ReferenceSetTests(unittest.TestCase):
    """The declared reference set, and the three populations inside it.

    A widening is only worth taking if it can be shown to widen. These pin
    that a `docs/ci/*.patch` is read as a reference source at all -- the class
    no prose grep can see -- and that widening did not drag the two verdicts
    that must stay narrow along with it.
    """

    def test_a_patch_header_is_read_as_a_reference_source(self):
        # A `.patch` naming another `.patch` is a real reference: a fold that
        # renames one leaves the other's header naming a file that is gone, and
        # nothing in the tree notices. `tools/test_agent_gates_patches.py` case 6
        # does not cover this -- it holds each header's own `git apply` line,
        # not a cross-reference between two headers.
        #
        # Discovery is what is pinned, not the verdict on a diff body. A future
        # patch that adds markdown containing a backticked patch name would
        # contribute a `+`-line reference, which is a diff rather than a
        # citation; `docs/findings/doc-patch-ref-file-sets.md` records that as a
        # limit, and pinning it here would make a caveat look like a decision.
        with tool.mini_tree({"docs/note.md": "a sibling\n",
                             "docs/ci/agent-gates-a.patch": "a patch\n",
                             "docs/ci/agent-gates-b.patch":
                                 "# see `agent-gates-a.patch` for context\n"}) as root:
            found = tool.scan(root)
            self.assertIn(("docs/ci/agent-gates-b.patch", tool.KIND_NAME,
                           "agent-gates-a.patch", 1), found.refs,
                          "a backticked name in a prepared change's own header "
                          "is a reference")
            self.assertFalse(found.stale,
                             "and it resolves against docs/ci/ like any other")

    def test_the_declared_set_is_prose_plus_the_prepared_headers(self):
        # The scope is a decision and is held as one, so a future edit that
        # widens or narrows it has to move this. Both halves are named rather
        # than globbed bare, and the count is deliberately not here.
        self.assertEqual(tool.REFERENCE_GLOBS,
                         ("**/*.md", "docs/ci/**/*.patch"))
        prose, prepared = tool.reference_files(REPO)
        self.assertTrue(prose and prepared)
        self.assertTrue(all(rel.endswith(".md") for rel in prose))
        self.assertTrue(all(rel.startswith("docs/ci/") and rel.endswith(".patch")
                            for rel in prepared),
                        "and the second half is docs/ci's own headers, not a "
                        "bare `*.patch` -- `linux/patches/` holds two upstream "
                        "driver patches that are outside the subject")

    def test_historical_liveness_is_read_over_prose_only(self):
        # The consequence of the widening, handled rather than left: if "still
        # cited" were evaluated over the whole set, a patch's own header would
        # satisfy it alone and every markdown reference to the key could be
        # deleted with nothing going red.
        #
        # The one non-prose reference to this key in the tree is a bare mention
        # in a patch header, which is not a parsed reference at all, so the case
        # writes the parsed spelling to have something to hold.
        key = "agent-gates-testdata-index.patch"
        with tool.scratch_tree() as root:
            header = root / "docs" / "ci" / "agent-gates-capture-claims.patch"
            header.write_text("# naming `" + key + "` from a sibling header\n",
                              encoding="utf-8")
            self.assertIn(("docs/ci/agent-gates-capture-claims.patch", 1),
                          {(rel, line) for rel, _k, _n, line
                           in tool.read_refs(root)},
                          "the header citation is a reference to the check, and "
                          "it is asserted on the file it came from: this key is "
                          "named in the tree's prose too, so asserting the name "
                          "alone would pass on that and pin nothing")
            for rel in tool.markdown_files(root):
                path = root / rel
                text = path.read_text(encoding="utf-8")
                if key in text:
                    path.write_text(text.replace(key, "a retired name"),
                                    encoding="utf-8")
            found = tool.scan(root)
            self.assertEqual(found.uncited_keys, [key])
            self.assertEqual(found.dead, [key],
                             "every markdown citation is gone and the key is "
                             "still reported dead, so the exemption cannot be "
                             "kept alive by the patch that documents its own "
                             "deletion")
            self.assertEqual(quiet(tool.check_mode, found)[1], 1)


class PreparedNonPatchTests(unittest.TestCase):
    """The one named prepared change that is not a `.patch`, both ways.

    `docs/ci/agent-gates-deep-schedule.yml` is a `cp` into
    `.github/workflows/`, and the `.patch` glob on the live side cannot see it.
    So the on-disk half is a named entry held in both directions, the way
    `HISTORICAL` is, and the name parse is left alone.
    """

    def setUp(self):
        self.name = sorted(tool.PREPARED_NON_PATCH)[0]

    def test_the_named_entry_is_on_disk_and_is_cited(self):
        # The reciprocal, on the committed tree and in both halves.
        with self.subTest(direction="on disk"):
            self.assertIn(self.name, tool.on_disk(REPO),
                          f"{self.name} is in PREPARED_NON_PATCH and is not in "
                          f"docs/ci/. Either it was renamed, which is the "
                          f"verdict below, or the constant is stale.")
        with self.subTest(direction="cited"):
            self.assertNotIn(self.name, tool.scan(REPO).uncited,
                             f"{self.name} is on disk and nothing in the files "
                             f"this check reads names it.")

    def test_deleting_it_goes_red_by_name(self):
        # The direction the `.patch` glob cannot hold: with the file gone the
        # glob simply matches one fewer thing, and nothing reports the loss.
        with tool.scratch_tree() as root:
            (root / "docs" / "ci" / self.name).unlink()
            found = tool.scan(root)
            self.assertEqual(found.missing, [self.name])
            self.assertEqual(found.uncited, [],
                             "and not a stale-name finding as well: the file "
                             "is not there to be named, and the two verdicts "
                             "want different edits")
            self.assertEqual(quiet(tool.check_mode, found)[1], 1)

    def test_editing_every_citation_of_it_away_goes_red(self):
        # The issue's done clause, and the tree it could not go red on. The
        # name is stripped from every prose file, which is the shape of a real
        # edit; a prepared change left on disk that nothing in the write-ups
        # names is the mirror of a stale name.
        #
        # Prose and not the whole declared set, and that is a measured
        # distinction rather than a convenience: the one place
        # `docs/ci/agent-gates-capture-claims.patch` names this file is a `+`
        # line at :197, a comment the patch adds to a Python file. A diff body
        # is not a citation, and letting one sustain this would make the
        # verdict true of nothing.
        with tool.scratch_tree() as root:
            stripped = 0
            for rel in tool.markdown_files(root):
                path = root / rel
                text = path.read_text(encoding="utf-8")
                if self.name in text:
                    path.write_text(text.replace(self.name, "a retired change"),
                                    encoding="utf-8")
                    stripped += 1
            self.assertGreater(stripped, 1,
                               "the yml is named in more than one file, or "
                               "'every citation' is being satisfied by one edit")
            # The boundary this case rests on, asserted rather than assumed: a
            # non-prose mention of the yml survives the strip, so the red below
            # is the prose-only rule and not the absence of any mention. If
            # that line ever goes away, this fails and says why it mattered --
            # a diff body is not a citation, and this is the one place the tree
            # has one.
            _prose, prepared = tool.reference_files(root)
            self.assertTrue(
                [rel for rel in prepared
                 if self.name in (root / rel).read_text(encoding="utf-8")],
                "a `+` line in a patch body still names the yml after the prose "
                "strip. The citation is read over prose precisely because a "
                "diff body must not sustain a prepared change's liveness; with "
                "nothing left outside prose this case would pass for the wrong "
                "reason.")
            found = tool.scan(root)
            self.assertEqual(found.uncited, [self.name])
            self.assertEqual(found.missing, [])
            self.assertEqual(quiet(tool.check_mode, found)[1], 1)

    def test_a_patch_nobody_names_is_still_uncited_alongside_the_named_entry(self):
        # The two halves of the live direction reaching one verdict, so a
        # `mini_tree` fixture that has the yml and no citation of it is not
        # ambiguous about which file is the finding.
        with tool.mini_tree({"docs/note.md": "nothing here\n",
                             "docs/ci/agent-gates-a.patch": "a\n",
                             "docs/ci/" + self.name: "a\n"}) as root:
            found = tool.scan(root)
            self.assertEqual(found.uncited, ["agent-gates-a.patch", self.name])


class LiveTreeTests(unittest.TestCase):
    """The invariant itself, against the committed tree.

    No count is compared. What is asserted is that the population is not empty
    and that the run is clean, which are the two claims that are true of the
    tree rather than of this tool, and a tree that changes under either of them
    should fail here rather than quietly change what the check measures.
    """

    def setUp(self):
        self.found = tool.scan(REPO)

    def test_the_population_is_not_empty(self):
        self.assertTrue(
            self.found.refs and self.found.patches,
            "no patch name found, or no patch in docs/ci/. If this suite is the "
            "only one left, the discovery rule is wrong, not the tree.")

    def test_no_reference_names_a_file_that_is_not_there(self):
        self.assertFalse(
            [(rel, name) for rel, _l, name in self.found.stale],
            f"{len(self.found.stale)} reference(s) name a patch that is not in "
            f"docs/ci/:\n  " + "\n  ".join(
                f"{rel} names `{name}`" for rel, _l, name in self.found.stale)
            + "\nA fold or a rename moves the name; the prose has to move with "
              "it. Check the patch's own suite (`tools/test_agent_gates_patches.py`) "
              "first -- if the patch is really gone, the reference is the thing "
              "that is wrong, and `HISTORICAL` is where a deliberate one goes.")

    def test_every_prepared_change_on_disk_is_named_by_something(self):
        self.assertFalse(
            self.found.uncited,
            f"{len(self.found.uncited)} prepared change(s) in docs/ci/ are "
            f"named by nothing this check reads:\n  " + "\n  ".join(
                self.found.uncited)
            + "\nA prepared change nobody can find is the mirror of a stale "
              "name, and it is the half that broke in "
              "`tools/test_readme_suite_table.py`.")

    def test_every_named_non_patch_change_is_on_disk(self):
        self.assertFalse(
            self.found.missing,
            f"{len(self.found.missing)} name(s) in PREPARED_NON_PATCH are not "
            f"in docs/ci/:\n  " + "\n  ".join(self.found.missing)
            + "\nA rename or a delete of one is invisible to a glob that has "
              "stopped matching it, which is why the written-down expectation "
              "is compared against discovery in both directions.")

    def test_no_historical_key_is_dead(self):
        # The two directions the `dead` verdict is derived from, asserted
        # directly as well as through it: a key that has stopped being absent
        # and a key that has stopped being cited are different mistakes and
        # arrive at `dead` by different routes.
        self.assertEqual(len(self.found.absent), len(tool.HISTORICAL),
                         "every key is still absent from docs/ci/")
        self.assertFalse(self.found.uncited_keys,
                         "and every key is still cited by some markdown file")
        self.assertFalse(
            self.found.dead,
            f"{len(self.found.dead)} key(s) in HISTORICAL are no longer doing "
            f"the work they were added for:\n  " + "\n  ".join(self.found.dead)
            + "\nEither the name is on disk again or no markdown file names it "
              "any more. Both are recorded in HistoricalTests.")

    def test_the_check_exits_zero_on_the_committed_tree(self):
        self.assertEqual(quiet(tool.check_mode, self.found)[1], 0)

    def test_the_link_onto_a_patch_resolves(self):
        # The markdown links in the tree onto a patch -- one in
        # `xdata-census-self-test-gate.md` from #777's tree, one in
        # `pin-table-row-reconciliation.md` from #942's -- and the reason this
        # tool reads links at all: `check_doc_links` cannot see either, because
        # its pattern ends in `\.md`.
        self.assertTrue(self.found.links,
                        "no markdown link onto a patch was found. The ones on "
                        "this tree are in `docs/findings/xdata-census-self-test-gate.md` "
                        "and `docs/findings/pin-table-row-reconciliation.md`; "
                        "if they have been rewritten as prose that is fine, but "
                        "their disappearing from a link is not something to pass over.")
        on_disk = set(self.found.patches)
        for rel, _kind, name, _line in self.found.links:
            with self.subTest(file=rel, name=name):
                self.assertIn(name, on_disk,
                              f"{rel} links onto `{name}`, which is not in "
                              f"docs/ci/. A markdown link is what a reader "
                              f"clicks, so this is the one reference in the "
                              f"tree whose breakage is a 404 rather than a "
                              f"stale sentence -- and it is the one shape "
                              f"`check_doc_links` cannot see.")


class RenameTests(unittest.TestCase):
    """The issue's "done" clause, on a `tempfile` copy of the committed tree.

    The point of the copy is the *real* population: "the gate goes red for every
    stale reference" is a claim about this tree's references, and a fixture of
    two lines would satisfy it without anything being true.
    """

    def test_renaming_a_patch_goes_red_on_every_reference_to_it(self):
        with tool.scratch_tree() as root:
            target = "agent-gates-0751-self-test.patch"
            self.assertIn(target, tool.on_disk(root))
            (root / "docs" / "ci" / target).rename(
                root / "docs" / "ci" / "agent-gates-renamed.patch")
            found = tool.scan(root)

            cited = [(rel, line) for rel, _k, n, line in tool.read_refs(root)
                     if n == target]
            self.assertGreater(len(cited), 1,
                               "the target has to be named more than once for "
                               "'every reference' to mean anything")
            self.assertEqual([(rel, line) for rel, line, _n in found.stale],
                             cited,
                             "every reference in the files this check reads to "
                             "the renamed patch is stale, in the order the tree "
                             "holds them -- a check that stopped at the first "
                             "would leave the rest to the manual sweep this "
                             "exists to end")
            self.assertEqual(found.uncited, ["agent-gates-renamed.patch"],
                             "and the renamed file is uncited, which is the "
                             "other half of a rename: the new name has not been "
                             "documented anywhere")
            self.assertEqual(quiet(tool.report, found)[1], len(cited) + 1,
                             "one finding per stale reference plus the "
                             "uncited rename, and `check_mode` turns any of "
                             "them into a non-zero exit")
            self.assertEqual(quiet(tool.check_mode, found)[1], 1)


if __name__ == "__main__":
    unittest.main()
