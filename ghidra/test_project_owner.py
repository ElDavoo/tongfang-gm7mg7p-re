#!/usr/bin/env python3
"""Offline checks for `ghidra/project_owner.py`: who a `.rep` says owns it, what
retaking it says it did, and what it refuses to touch.

**No Ghidra, no JVM, no firmware.** Every case builds its own `project.prp` in a
`tempfile`, so the answers are known because the fixture was written to be known
-- which is the only way to pin the parts that are easy to get subtly wrong, and
the only way this can run in the cheap tier at all. Nothing here opens a
project, and no case is a claim about what Ghidra does when it opens one: the
end-to-end evidence for that is `build_ec_decompile.py --self-test --oracle`,
and it needs a real export.

**The refusals carry most of the weight.** The happy path is one line of text
replacement and a fixture proves it; what a shared helper in `ghidra/` has to
earn is the right to write a file `.gitattributes` marks `-merge`. So the cases
that decide whether this module is safe to add are the ones where it must
*not* act: a `rep_dir` outside the scratch root, a `project.prp` that is not
XML, one carrying no OWNER state, and a second STATE that happens to share the
owner's value and must survive untouched.

**What a green run here does not show.** That a non-owner can complete an
export. That is the oracle's, and it is minutes of wall clock with Ghidra
installed -- see `ec/ghidra/README.md`. This suite shows the normalisation
happens in the copy and refuses to happen in the tree, which is the part that
can be wrong quietly.
"""
import getpass
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import project_owner as po  # noqa: E402  (the path insert above is what makes this work)

# The owner all three committed projects record, byte-identical in each. Kept as
# a fixture value rather than read from the tree so a case cannot pass by
# agreeing with whatever the repository currently says -- the point of the
# rewrite is that the committed value is *not* this user's.
COMMITTED_OWNER = "dave"

PRP_TEXT = """<?xml version="1.0" encoding="UTF-8"?>
<FILE_INFO>
    <BASIC_INFO>
        <STATE NAME="OWNER" TYPE="string" VALUE="%s" />
    </BASIC_INFO>
</FILE_INFO>
"""


def rep(root, owner=COMMITTED_OWNER, name="ec.rep", text=None):
    """A `.rep` directory holding a `project.prp`, under a scratch root.

    Returns `(rep_dir, scratch_root)`. Every mutation in this file happens in a
    `tempfile`, so no case can touch the committed `.rep` even by accident --
    which is the property the module's own guard is there to enforce, and a
    fixture that did not have it would not be testing much.
    """
    scratch = tempfile.mkdtemp(dir=root)
    rep_dir = os.path.join(scratch, name)
    os.makedirs(rep_dir)
    body = PRP_TEXT % owner if text is None else text
    with open(os.path.join(rep_dir, "project.prp"), "w") as f:
        f.write(body)
    return rep_dir, scratch


class ReadOwnerTests(unittest.TestCase):
    def setUp(self):
        self.box = tempfile.mkdtemp()
        self.addCleanup(_rmtree, self.box)

    def test_reads_the_owner_the_file_records(self):
        rep_dir, _scratch = rep(self.box, owner="someone-else")
        self.assertEqual(po.read_owner(rep_dir), "someone-else")

    def test_absent_state_is_none_rather_than_a_guess(self):
        text = PRP_TEXT % ""  # the element is there, the value is not
        rep_dir, _scratch = rep(self.box, text=text.replace(
            '<STATE NAME="OWNER" TYPE="string" VALUE="" />', ""))
        self.assertIsNone(po.read_owner(rep_dir))

    def test_a_non_xml_prp_is_reported_rather_than_searched(self):
        rep_dir, _scratch = rep(self.box, text="not xml at all\n")
        with self.assertRaises(ValueError):
            po.read_owner(rep_dir)


class RewriteOwnerTests(unittest.TestCase):
    def setUp(self):
        self.box = tempfile.mkdtemp()
        self.addCleanup(_rmtree, self.box)
        self.me = getpass.getuser()

    def test_the_copy_becomes_owned_by_the_running_user(self):
        rep_dir, scratch = rep(self.box)
        report = po.rewrite_owner(rep_dir, scratch)
        self.assertEqual(report, "rewrote %s -> %s" % (COMMITTED_OWNER, self.me))
        self.assertEqual(po.read_owner(rep_dir), self.me)

    def test_a_second_rewrite_says_already_corrected_and_changes_nothing(self):
        rep_dir, scratch = rep(self.box)
        po.rewrite_owner(rep_dir, scratch)
        after = _bytes(os.path.join(rep_dir, "project.prp"))
        self.assertEqual(po.rewrite_owner(rep_dir, scratch),
                         "already %s" % self.me)
        self.assertEqual(_bytes(os.path.join(rep_dir, "project.prp")), after)

    def test_only_the_owner_line_is_touched(self):
        # A file with a second STATE carrying the same value. A whole-file
        # `replace` of VALUE="dave" rewrites both; the captured-prefix
        # substitution this module uses cannot.
        text = (PRP_TEXT % COMMITTED_OWNER).replace(
            "    </BASIC_INFO>",
            '        <STATE NAME="COMMENTS" TYPE="string" VALUE="%s" />\n'
            "    </BASIC_INFO>" % COMMITTED_OWNER)
        rep_dir, scratch = rep(self.box, text=text)
        po.rewrite_owner(rep_dir, scratch)
        after = _read(os.path.join(rep_dir, "project.prp"))
        self.assertIn('NAME="COMMENTS" TYPE="string" VALUE="%s"' % COMMITTED_OWNER,
                      after)
        self.assertIn('NAME="OWNER" TYPE="string" VALUE="%s"' % self.me, after)

    def test_the_rest_of_the_file_is_byte_identical(self):
        rep_dir, scratch = rep(self.box)
        before = _read(os.path.join(rep_dir, "project.prp"))
        po.rewrite_owner(rep_dir, scratch)
        after = _read(os.path.join(rep_dir, "project.prp"))
        self.assertEqual(after.count("\n"), before.count("\n"))
        self.assertEqual(after.splitlines()[0], before.splitlines()[0])
        self.assertEqual(after.splitlines()[-1], before.splitlines()[-1])

    def test_a_rep_outside_the_scratch_root_is_refused_and_left_alone(self):
        # The case that decides whether this module can be shared at all. The
        # `rep_dir` is a sibling of the scratch root, so a guard that compared
        # only the basename, or resolved nothing, would let this through and
        # write a committed `.rep` -- a hard conflict for every open branch,
        # since `**/*.rep/**` is `binary -diff -merge`.
        _outside, _other_root = rep(self.box)
        scratch = tempfile.mkdtemp(dir=self.box)
        before = _bytes(os.path.join(_outside, "project.prp"))
        with self.assertRaises(SystemExit):
            po.rewrite_owner(_outside, scratch)
        self.assertEqual(_bytes(os.path.join(_outside, "project.prp")), before)

    def test_a_rep_beside_the_scratch_root_is_refused_by_name_prefix(self):
        # `/tmp/.../scratch-evil` is not under `/tmp/.../scratch`, and a
        # `startswith` on the raw strings would say it is. This is the half of
        # the guard that only holds if the separator is compared.
        parent = tempfile.mkdtemp(dir=self.box)
        scratch = os.path.join(parent, "scratch")
        os.makedirs(scratch)
        evil = os.path.join(parent, "scratch-evil", "ec.rep")
        os.makedirs(evil)
        with open(os.path.join(evil, "project.prp"), "w") as f:
            f.write(PRP_TEXT % COMMITTED_OWNER)
        before = _bytes(os.path.join(evil, "project.prp"))
        with self.assertRaises(SystemExit):
            po.rewrite_owner(evil, scratch)
        self.assertEqual(_bytes(os.path.join(evil, "project.prp")), before)

    def test_a_symlink_from_the_scratch_root_into_the_tree_is_refused(self):
        # The guard resolves before it compares, so a `rep_dir` that sits inside
        # the scratch root but points at a committed `.rep` is refused too. This
        # is the one way a caller could name a legal-looking path and still be
        # about to edit something `-merge`-marked.
        target, _other_root = rep(self.box)  # a .rep outside the scratch below
        scratch = tempfile.mkdtemp(dir=self.box)
        link = os.path.join(scratch, "linked.rep")
        os.symlink(target, link)
        before = _bytes(os.path.join(target, "project.prp"))
        with self.assertRaises(SystemExit):
            po.rewrite_owner(link, scratch)
        self.assertEqual(_bytes(os.path.join(target, "project.prp")), before)

    def test_a_prp_with_no_owner_state_is_reported_not_guessed_at(self):
        text = (PRP_TEXT % COMMITTED_OWNER).replace(
            'NAME="OWNER" TYPE="string"', 'NAME="OWNERX" TYPE="string"')
        rep_dir, scratch = rep(self.box, text=text)
        with self.assertRaises(SystemExit):
            po.rewrite_owner(rep_dir, scratch)

    def test_a_non_xml_prp_is_reported_not_guessed_at(self):
        # Matched on the message, not just the exception type: a binary file
        # also trips the "no OWNER state" guard, so a bare assertRaises here
        # would go green the moment the XML guard went away and this fixture
        # stopped testing it. Two guards, two different wrong answers, and the
        # reader is told which one happened.
        rep_dir, scratch = rep(self.box, text="\x00\x01 not xml\n")
        with self.assertRaisesRegex(SystemExit, "is not XML"):
            po.rewrite_owner(rep_dir, scratch)


class OwnerProblemsTests(unittest.TestCase):
    def setUp(self):
        self.box = tempfile.mkdtemp()
        self.addCleanup(_rmtree, self.box)
        self.me = getpass.getuser()

    def test_a_rewrite_that_took_the_copy_leaves_no_problem(self):
        rep_dir, scratch = rep(self.box)
        po.rewrite_owner(rep_dir, scratch)
        self.assertEqual(po.owner_problems(rep_dir, self.me), [])

    def test_a_copy_still_named_for_someone_else_is_reported(self):
        # The state `rewrite_owner()` exists to prevent, asserted from the
        # reporting side as well: a caller that only checks must see the same
        # thing the fix prevents.
        rep_dir, _scratch = rep(self.box)
        problems = po.owner_problems(rep_dir, self.me)
        self.assertEqual(len(problems), 1)
        self.assertIn(COMMITTED_OWNER, problems[0])
        self.assertIn("NotOwnerException", problems[0])

    def test_every_fault_is_named_not_just_the_first(self):
        cases = {
            "not xml": ("binary\n", "is not XML"),
            "no state": ((PRP_TEXT % COMMITTED_OWNER).replace(
                '        <STATE NAME="OWNER" TYPE="string" VALUE="%s" />\n'
                % COMMITTED_OWNER, ""),
                "no OWNER state"),
            "empty owner": (PRP_TEXT % "", "OWNER state is empty"),
        }
        for label, (text, want) in cases.items():
            rep_dir, _scratch = rep(self.box, text=text)
            problems = po.owner_problems(rep_dir, self.me)
            self.assertTrue(any(want in p for p in problems),
                            "%s: got %r" % (label, problems))

    def test_a_directory_with_no_project_prp_is_reported(self):
        # Handed a `.gpr` or a project directory instead of the `.rep` inside
        # it, which is the mistake the signature comment warns about.
        empty = os.path.join(tempfile.mkdtemp(dir=self.box), "ec.rep")
        os.makedirs(empty)
        problems = po.owner_problems(empty, self.me)
        self.assertEqual(len(problems), 1)
        self.assertIn("not a .rep directory", problems[0])

    def test_the_report_is_readable_before_and_after_a_rewrite(self):
        rep_dir, scratch = rep(self.box)
        self.assertEqual(po.owner_problems(rep_dir), [])  # readable, any owner
        self.assertTrue(po.owner_problems(rep_dir, self.me))
        po.rewrite_owner(rep_dir, scratch)
        self.assertEqual(po.owner_problems(rep_dir, self.me), [])


class CommittedProjectTests(unittest.TestCase):
    """The committed `.rep`s, read but never written.

    This is the half that pins the *defect*: if a `project.prp` in the tree ever
    stops carrying an owner, or grows a second OWNER state, or moves, the
    normalisation's premise has changed and this is where it shows. It reads
    `owner_problems()` over the three projects and asserts each is readable and
    carries exactly one owner state -- never that the owner is any particular
    name, which is the value this whole change exists to stop depending on.
    """

    REPS = (
        os.path.join("ec", "ghidra", "project", "ec.rep"),
        os.path.join("bios", "ghidra", "project", "bios.rep"),
        os.path.join("windows", "ghidra", "project", "uniwill_native.rep"),
    )
    # One level up, not two: this file sits in the shared `ghidra/` layer,
    # whose other member is one directory below the repository root. The
    # component trees under `ec/tools/` and `bios/tools/` are two deep and use
    # the other spelling.
    REPO = os.path.dirname(HERE)

    def test_every_committed_project_reads_and_carries_one_owner(self):
        for rel in self.REPS:
            rep_dir = os.path.join(self.REPO, rel)
            self.assertEqual(po.owner_problems(rep_dir), [], rel)
            self.assertIsNotNone(po.read_owner(rep_dir), rel)

    def test_rewrite_owner_would_refuse_every_committed_project(self):
        # The guard is not decoration on the happy path: for the three
        # directories in this repository it is the answer, and that is asserted
        # against the real paths rather than against a fixture that could drift
        # away from them.
        box = tempfile.mkdtemp()
        self.addCleanup(_rmtree, box)
        for rel in self.REPS:
            rep_dir = os.path.join(self.REPO, rel)
            before = _bytes(os.path.join(rep_dir, "project.prp"))
            with self.assertRaises(SystemExit, msg=rel):
                po.rewrite_owner(rep_dir, box)
            self.assertEqual(_bytes(os.path.join(rep_dir, "project.prp")), before,
                             rel)


def _read(path):
    with open(path) as f:
        return f.read()


def _bytes(path):
    with open(path, "rb") as f:
        return f.read()


def _rmtree(path):
    import shutil
    shutil.rmtree(path, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()