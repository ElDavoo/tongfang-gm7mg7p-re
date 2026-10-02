#!/usr/bin/env python3
r"""`ecrw_fake.py` held to `ecrw.py`: the mirror, measured rather than promised.

`ecrw.py` runs `ctypes.WinDLL("kernel32", ...)` at module scope, so it cannot
be imported off Windows -- which is the whole reason the fixture exists, and
the reason this comparison has to be static. Neither file is imported here:
`install()` under a shared interpreter
(`tools/test_windows_tools_shared_interpreter.py`) would leave `sys.modules`
pointing at the fixture for a sibling suite to inherit, and `ast.parse` over
the two sources answers everything asserted below.

The fixture used to claim the real module's *whole* surface in three places.
It does not carry it: `_ioctl`, `read_dword` and `read_dword_unaligned` are the
real class's own interior, no tool reaches them, and their two docstrings have
been reworded to the surface it does carry. What is asserted here is the
narrower claim those sentences were reaching for:

    the fixture carries every member of `ecrw.Ec` that a tool in
    `windows/tools/` reaches, with identical signatures; the members it omits
    are exactly those no tool reaches, and that residual is named below.

The one case that is not a comparison of behaviour: an unpatched `read_dword`
on the fixture raises `AttributeError` today, and that is deliberate. Giving
it a `bytes(4)` body would turn the loud failure into a silent four-zero answer
on the MMRD path, which is the path `test_ecrw.py` guards hardest. Adding the
member is therefore a decision to be made against a caller that exists, not a
gap to be closed here -- and if a tool ever reaches one, `RESIDUAL` below has to
have its entry deleted, which is what makes this suite go red.

Nothing here opens an EC, reads a register back or touches Windows.
`docs/findings/ecrw-fake-mirror-surface.md` is the write-up.
"""
import ast
import functools
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ECRW = HERE / 'ecrw.py'
FAKE = HERE / 'ecrw_fake.py'

# The members of `ecrw.Ec` no tool in this directory reaches, and so the only
# ones the fixture may omit. Each is the real class's own interior: `_ioctl`
# is how `read`/`write` issue their IOCTLs, and the two `read_dword*` methods
# are what `--block` and the `mmrd` escape are built on. No tool that binds
# `ecrw` reaches them: `test_ecrw.py` does call the dword pair, against the real
# module behind a fake `ctypes.WinDLL`, which is the point of it and which
# `binds_ec` is what leaves out of the population.
#
# An allowlist with `ec/tools/check_pin_message_names.py`'s discipline: an entry
# that stops violating has to be deleted rather than left standing, because a
# residual entry nobody re-reads is how "the fake mirrors the real class"
# became a sentence nothing checked. A member that stops belonging here is a
# red run in `ResidualTests`, and deleting the entry is what makes it green
# again -- the signal is a tool reaching it, not a table that wants tidying.
RESIDUAL = ('_ioctl', 'read_dword', 'read_dword_unaligned')


def parse_text(source):
    """`source` as an `ast`, so both files can be read without importing them."""
    return ast.parse(source)


def class_of(tree, name):
    """The top-level class `name`, or None. Not recursive by intent.

    A `None` rather than a raise so the non-vacuity cases can report which of
    the two files lost the class; every case below is a comparison between two
    of them and would otherwise report the same `AttributeError` twice.
    """
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == name:
            return node
    return None


def members(node):
    """`{name: signature}` for every method of a class node.

    Signatures rather than names: `ast.unparse` of the `arguments` node keeps
    `read(self, addr, timeout=None)` and `read(self, addr)` apart, which is the
    case the claim is about and the one a name-set comparison cannot see.
    """
    return {m.name: ast.unparse(m.args) for m in node.body
            if isinstance(m, ast.FunctionDef)}


def base_classes(node):
    """A class node's bases, unparsed. `RuntimeError` is the whole of it here."""
    return [ast.unparse(base) for base in node.bases]


def module_function(tree, name):
    """The top-level `def name`'s signature string, or None."""
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return ast.unparse(node.args)
    return None


@functools.lru_cache(maxsize=1)
def tool_modules():
    """The `.py` files in this directory, parsed, as a tuple.

    Cached because the reached-set walk runs once per case and re-parsing a
    dozen files each time buys nothing over the whole directory's runtime.
    Returns trees rather than paths so a case cannot be tempted to open one.
    """
    return tuple((path.name, ast.parse(path.read_text()))
                 for path in sorted(HERE.glob('*.py')))


def binds_ec(tree):
    """Whether a module binds `Ec` from `ecrw` at module level.

    Read off the parse, not out of the text, and at module level only. Both
    halves matter: a `from ecrw import ...` inside a docstring or a suite's
    comment names the module without needing anything of it, and a suite in
    this directory does import `ecrw_fake` -- which is not the same module and
    is the fixture under test.
    """
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == 'ecrw':
            return any(alias.name == 'Ec' for alias in node.names)
    return False


def reached_by_tools(names):
    """Which of `names` -- `ecrw.Ec`'s members -- a tool in here reaches.

    Derived from the tools' own sources rather than listed, so a tool that
    starts calling a fourth member is covered by the property below instead of
    by whoever edits a table. It is `FakeSurfaceTests`' derivation applied to
    the class rather than to the module.

    Two rules, and both err toward counting too much rather than too little,
    because that is the direction that makes the comparison strict: a member
    wrongly believed reached has to be on the fixture, and one wrongly believed
    unreached stays in `RESIDUAL`, which is where an allowance should not be.

    1. Any attribute spelled in a tool that binds `Ec`, whether or not the
       object it is spelled on is the handle -- the `self._fh.close()` on a file
       handle counts `close`, which no tool calls on an `Ec` and which the
       fixture carries anyway. Telling the handle from every other name in a
       module would need a dataflow analysis nothing here has a use for, and
       its only effect would be to make the residual larger. `close`'s place
       on the fixture rests on that blunt rule rather than on a call, so
       narrowing rule 1 would mean deciding `close` on purpose.
    2. The context-manager protocol, which is not spelled as an attribute at
       all: `with Ec() as ec` reaches `__enter__` and `__exit__`, and the `Ec()`
       call inside it reaches `__init__`.

    The population is the tools, not the suites: a `test_*.py` installs the
    fixture and then patches its own class over the tool, so a member it calls
    is not one the fixture owes. `binds_ec` is what excludes them, and it
    excludes the two files being compared for free -- neither has a module-level
    `from ecrw import` of its own.
    """
    reached = set()
    for _, tree in tool_modules():
        if not binds_ec(tree):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                reached.add(node.attr)
            elif isinstance(node, ast.Call) and _is_ec_construction(node):
                reached.add('__init__')
            elif isinstance(node, ast.With):
                for item in node.items:
                    if (isinstance(item.context_expr, ast.Call)
                            and _is_ec_construction(item.context_expr)):
                        reached |= {'__enter__', '__exit__'}
    return reached & set(names)


def _is_ec_construction(node):
    """`node` is a call of the bare name `Ec` -- an `Ec(...)`, not `ec.read`."""
    return isinstance(node.func, ast.Name) and node.func.id == 'Ec'


def mirror_problems(real_source, fake_source):
    """Every way the fixture fails to mirror the real class, keyed by the rule.

    A dict of lists rather than one boolean, for two reasons that both cost
    something if they are got wrong. A failure names the member and the way it
    went wrong, which is the difference between a red run somebody can act on
    and one that says "something is wrong" about a fixture whose entire job is
    to be found standing still. And each rule is keyed separately so every case
    below asserts *this* function's view and the negative control perturbs the
    same one -- a control that exercised a second implementation of the rule
    would pass while the case it was written for was broken.

    Empty on the committed tree; the control is what stops that from being an
    accident of a parser that finds nothing.
    """
    real = members(class_of(parse_text(real_source), 'Ec'))
    fake = members(class_of(parse_text(fake_source), 'Ec'))
    reached = reached_by_tools(set(real))
    found = {'invented': [], 'resigned': [], 'unreached_missing': [],
             'unexplained': [], 'residual': []}
    for name in sorted(fake):
        if name not in real:
            found['invented'].append(f'{name} is on the fixture and not on '
                                     f'ecrw.Ec')
        elif fake[name] != real[name]:
            found['resigned'].append(f'{name} is ({fake[name]}) on the fixture '
                                     f'and ({real[name]}) on ecrw.Ec')
    for name in sorted(reached):
        # Presence only, and the signature is already covered: anything on both
        # sides was compared as a pair above, so a reached member that is here
        # at all is here with `ecrw.Ec`'s own argument list.
        if name not in fake:
            found['unreached_missing'].append(f'{name} is reached by a tool '
                                              f'and is not on the fixture')
    found['unexplained'] = [f'{name} is on the fixture and nothing in '
                            f'windows/tools reaches it'
                            for name in sorted(set(fake) - reached)]
    residual = sorted(set(real) - reached)
    if residual != sorted(RESIDUAL):
        found['residual'].append(
            f'the members no tool reaches are {residual}, not '
            f'{sorted(RESIDUAL)}')
    return found


def stub_pair():
    """A minimal but *clean* `ecrw.py` / `ecrw_fake.py`, as two source strings.

    Built from the committed class's member names and the derived reached set
    rather than by editing the committed files, and that is the whole reason
    this exists. A control that mutated `ECRW`/`FAKE` in place inherits
    whatever state those two files are in, so a tree already broken in the
    direction a control perturbs would make it fire for the wrong reason, and a
    tree broken in the direction it checks could mask the control entirely.
    `tools/test_windows_tools_shared_interpreter.py`'s `NegativeControlTests`
    writes its two one-line suites rather than editing anything for the same
    reason, and this follows that.

    The real side carries every member with the real signature; the fixture
    side carries the reached ones and leaves the rest out, which is the shape
    the committed pair has. So the derived reached set, the residual and the
    member sets are the committed ones, and the pair is accepted before
    anything is broken -- which the control asserts rather than assumes.
    """
    real = members(class_of(parse_text(ECRW.read_text()), 'Ec'))
    reached = reached_by_tools(set(real))

    def source(names):
        body = ['class Ec:']
        for name in sorted(names):
            body.append(f'    def {name}({real[name]}):')
            body.append('        pass')
        return '\n'.join(body) + '\n'

    return source(real), source(reached)


def grafted(source, mutate):
    """`source` re-parsed, `mutate` applied to its `Ec`, and unparsed back out.

    Through `ast.unparse` rather than a text edit because the mutations below
    are structural -- add a method, drop one, re-signature one -- and a text
    edit has to find the right line of a source nobody here controls. The
    result is only ever re-parsed, so the formatting `unparse` chooses is not
    part of what the control claims.
    """
    tree = parse_text(source)
    mutate(class_of(tree, 'Ec'))
    return ast.unparse(tree)


def method_snippet(source):
    """A `FunctionDef` parsed out of a `def` line written in a stub class.

    Built by parsing rather than by constructing an `ast.FunctionDef` by hand:
    the node type gained required fields between releases, and this has to keep
    parsing on whatever `python3` the runner finds.
    """
    return ast.parse(f'class _:\n{source}\n').body[0].body[0]


class NonVacuityTests(unittest.TestCase):
    """The parse found something, in both files and in the tools.

    First, because every case below compares two parses against each other and
    an empty parse against an empty expectation passes silently -- the same
    defect `tools/test_readme_suite_table.py`'s `ParseTests` and
    `run-tests.sh`'s empty-glob guard exist for. A suite asserting a relation
    between two files can pass that way as readily as one asserting a census.
    """

    @classmethod
    def setUpClass(cls):
        cls.real = parse_text(ECRW.read_text())
        cls.fake = parse_text(FAKE.read_text())
        cls.real_members = members(class_of(cls.real, 'Ec'))
        cls.fake_members = members(class_of(cls.fake, 'Ec'))
        cls.reached = reached_by_tools(set(cls.real_members))

    def test_both_files_carry_the_class_the_comparison_is_over(self):
        # Without this the cases below compare two `None`s, and
        # `members(None)` is a `TypeError` naming neither file.
        for path, tree in ((ECRW, self.real), (FAKE, self.fake)):
            with self.subTest(file=path.name):
                self.assertIsNotNone(
                    class_of(tree, 'Ec'),
                    f'{path.name} has no top-level class Ec, so there is '
                    f'nothing to compare and every case below would pass or '
                    f'error for the wrong reason')

    def test_the_real_class_carries_more_than_one_member(self):
        # One member is what a file left half-written by a bad merge looks
        # like, and it would satisfy every comparison below against a fixture
        # carrying the same one member.
        self.assertGreater(len(self.real_members), 1, self.real_members)

    def test_the_fixture_class_is_not_empty(self):
        self.assertTrue(self.fake_members,
                        'ecrw_fake.Ec has no members, so the fixture carries '
                        'nothing and every comparison here is against empty')

    def test_some_tool_reaches_some_member(self):
        # The population the reached-set derivation walks. Empty means no tool
        # in this directory binds `ecrw` at module level any more, which would
        # make `RESIDUAL` the whole class and the reached-set property vacuous.
        self.assertTrue(self.reached,
                        'no member of ecrw.Ec is reached by any tool in '
                        'windows/tools')


class MirrorTests(unittest.TestCase):
    """The fixture's member set against the real class's, both directions.

    The claim being held is the narrow one the fixture's docstrings now state,
    and each case says why it is that claim and not a nearby one. Every case
    reads one key of `mirror_problems` rather than comparing the sets itself, so
    the negative control at the bottom perturbs the same code these do -- a
    control written against a second copy of the rule would stay green while
    one of these was broken.
    """

    @classmethod
    def setUpClass(cls):
        cls.problems = mirror_problems(ECRW.read_text(), FAKE.read_text())

    def assertNoProblems(self, key, what):
        found = self.problems[key]
        self.assertFalse(found, f'{what}:\n  ' + '\n  '.join(found))

    def test_the_fixture_invents_no_member(self):
        # Direction one: nothing the real class does not have. An invented
        # member is a name no tool can reach and no real call can satisfy, so
        # it is the fixture growing a surface of its own -- which is the second
        # implementation its own docstring disclaims.
        self.assertNoProblems(
            'invented', 'ecrw_fake.Ec carries members ecrw.Ec does not have')

    def test_the_fixture_re_signatures_nothing(self):
        # The half a member-set comparison cannot see, and why the signatures
        # are parsed rather than counted. `read(self, addr)` and
        # `read(self, addr, timeout=None)` are the same name and different
        # contracts, and a tool that reached the second would be handed the
        # first without a word from either file.
        self.assertNoProblems(
            'resigned',
            'ecrw_fake.Ec re-signatures a member ecrw.Ec has (fixture first)')

    def test_every_member_a_tool_reaches_is_on_the_fixture(self):
        # Direction two, and the property that replaced "the whole surface":
        # a member a tool calls has to be there for it, with the set derived
        # from the tools rather than listed, so a tool growing a fourth call
        # fails here without anybody editing a table.
        self.assertNoProblems(
            'unreached_missing',
            'a tool in windows/tools reaches a member of ecrw.Ec that the '
            'fixture does not carry: an unpatched call would die on a missing '
            'attribute instead of being answered')

    def test_the_fixture_carries_nothing_a_tool_does_not_reach(self):
        # The other half of the last case, and together they make the fixture's
        # member set *equal* to the reached set rather than a superset of it.
        # That is what makes the omission of `_ioctl` and the dword pair a
        # decision: a member carried with nothing behind it is a default
        # waiting for the one call that wanted a value and would get silence
        # instead of the failure it should have had.
        self.assertNoProblems(
            'unexplained',
            'ecrw_fake.Ec carries members nothing in windows/tools reaches')


class ResidualTests(unittest.TestCase):
    """What the fixture omits is named here, and the naming is checked both ways.

    `RESIDUAL` is the claim that replaced "the whole protocol" in the fixture's
    own words: these three are the real class's interior, no tool in this
    directory reaches them, and a member added to that list without a caller
    behind it is a silent default waiting to be found by something that cannot
    write -- which is why the check is equality in both directions rather than
    containment.
    """

    def test_the_members_no_tool_reaches_are_exactly_the_named_residual(self):
        found = mirror_problems(ECRW.read_text(), FAKE.read_text())['residual']
        self.assertFalse(
            found,
            '\n  '.join(found) + '\n'
            '  A member that has stopped belonging in RESIDUAL has had its '
            'entry deleted and belongs on the fixture; that deletion is what '
            'makes this green, so this is the signal to add it -- not a table '
            'that wants tidying.\n'
            '  A member that has started belonging there is a new default with '
            'no caller behind it: give it one and a decision about its body, '
            'or leave it off the real class.')

    def test_every_named_residual_member_is_absent_from_the_fixture(self):
        # The named set is also a claim about the fixture, not only about the
        # derivation: an entry naming a member the fixture already carries is
        # an allowance covering a name it has stopped exempting.
        # `mirror_problems` would also catch this, as `unexplained`; asserted
        # separately because it is a different mistake -- a stale exemption
        # rather than a stray member -- and the message should say so.
        fake = members(class_of(parse_text(FAKE.read_text()), 'Ec'))
        carried = sorted(set(RESIDUAL) & set(fake))
        self.assertFalse(
            carried,
            f'ecrw_fake.Ec carries {carried}, which the suite names as a '
            f'member no tool reaches: the exemption has outlived the gap it '
            f'was written for')


class SharedNameTests(unittest.TestCase):
    """`EcError`'s base and `block_runs`'s signature: module-level surface.

    `FakeSurfaceTests` already holds that every name a tool binds from `ecrw`
    is one the fixture exports. These two are the rest of it: the base is what
    keeps the two classes substitutable, and `block_runs` is the third name
    `install()` publishes and one tool binds, so it is surface in the same
    sense `Ec` is.
    """

    def test_the_two_error_classes_share_a_base(self):
        # Cheap, true, and asserted rather than asserted-about: the fixture's
        # `EcError` docstring claims the base is load-bearing because
        # `ec_watch.py` wraps its run in `except EcError`. Nothing in the tree
        # demonstrates that -- every handler catches the class object a tool
        # bound at import, not its base -- so the justification is *not* restated
        # here as settled. What is checked is the substitution it rests on:
        # matching the base keeps the two interchangeable and costs nothing,
        # and a fixture that diverged would be a fixture whose exception no
        # longer looked like the real one to anything catching broadly.
        real = base_classes(class_of(parse_text(ECRW.read_text()), 'EcError'))
        fake = base_classes(class_of(parse_text(FAKE.read_text()), 'EcError'))
        self.assertEqual(fake, real,
                         f'ecrw_fake.EcError is based on {fake} and '
                         f'ecrw.EcError on {real}')

    def test_block_runs_has_the_same_signature_in_both_files(self):
        real = module_function(parse_text(ECRW.read_text()), 'block_runs')
        fake = module_function(parse_text(FAKE.read_text()), 'block_runs')
        self.assertIsNotNone(real, 'ecrw.py has no module-level block_runs')
        self.assertIsNotNone(fake, 'ecrw_fake.py has no module-level block_runs')
        self.assertEqual(fake, real,
                         f'ecrw_fake.block_runs is ({fake}) and ecrw.block_runs '
                         f'is ({real})')


class NegativeControlTests(unittest.TestCase):
    """The same comparison, on a tree where each way it can break is made.

    Without this, everything above is satisfied by a parser that finds nothing
    -- a live failure mode here, because `class_of` returns `None` for a class
    that is not there rather than raising, and a comparison of two `None`s is a
    comparison of two empty dicts. Each control mutates a scratch copy of one
    of the two committed files and asserts the *same* `mirror_problems` the
    cases above read reports it under the key that case owns, so a control
    cannot go green while the case it was written for is broken.

    `tools/test_windows_tools_shared_interpreter.py`'s `NegativeControlTests` is
    the precedent, and the reason this class is here at all.
    """

    @classmethod
    def setUpClass(cls):
        cls.clean_real, cls.clean_fake = stub_pair()

    def assertRejected(self, key, real_source, fake_source):
        """`mirror_problems` must report `key` on a tree broken that way."""
        found = mirror_problems(real_source, fake_source)[key]
        self.assertTrue(
            found,
            f'the comparison reported nothing under {key!r} on a tree where '
            f'it is broken, so nothing above is asserting anything: '
            f'{mirror_problems(real_source, fake_source)}')
        return found

    def test_the_control_tree_is_clean_before_anything_is_broken(self):
        # So a failure below is the mutation rather than the fixtures: the
        # pair has to be one the comparison accepts, or "the control fired"
        # and "the control was already red" are indistinguishable.
        self.assertEqual(mirror_problems(self.clean_real, self.clean_fake),
                         {'invented': [], 'resigned': [], 'unreached_missing':
                          [], 'unexplained': [], 'residual': []})

    def test_a_member_added_to_the_real_class_is_reported(self):
        # The residual grows, and it is the equality in `RESIDUAL` that
        # rejects it -- not a rule naming the new member, which is the point:
        # the suite cannot know what a future member will be called, so what it
        # holds is that the set of omissions is named rather than implied.
        def add(cls):
            cls.body.append(method_snippet(
                '    def read_word(self, addr):\n        pass'))

        self.assertRejected('residual', grafted(self.clean_real, add),
                            self.clean_fake)

    def test_a_member_dropped_from_the_real_class_is_reported(self):
        # Direction one: the fixture carries a name the real class has lost,
        # which no real call could satisfy. Dropped rather than re-signatured
        # so this is the shape a bad merge or a partial revert takes.
        def drop(cls):
            cls.body = [m for m in cls.body
                        if getattr(m, 'name', None) != 'write']

        self.assertRejected('invented', grafted(self.clean_real, drop),
                            self.clean_fake)

    def test_a_re_signatured_member_is_reported(self):
        # The case a name-set comparison cannot see at all, and the reason the
        # signatures are parsed rather than counted: `read` is on both sides
        # under the same name, and only its argument list says otherwise.
        def resignature(cls):
            for method in cls.body:
                if getattr(method, 'name', None) == 'read':
                    method.args = method_snippet(
                        '    def read(self, addr, timeout=None):\n'
                        '        pass').args

        self.assertRejected('resigned',
                            grafted(self.clean_real, resignature),
                            self.clean_fake)

    def test_a_member_dropped_from_the_fixture_is_reported(self):
        # Direction two, and the one the design rests on: the reached set is
        # derived from the tools, so a fixture that stopped carrying something
        # a tool calls is caught without anybody editing a table.
        def drop(cls):
            cls.body = [m for m in cls.body
                        if getattr(m, 'name', None) != 'readmany']

        found = self.assertRejected('unreached_missing', self.clean_real,
                                    grafted(self.clean_fake, drop))
        self.assertTrue(any('readmany' in p for p in found), found)

    def test_a_member_added_to_the_fixture_is_reported(self):
        # And the other half of the same pair: a fixture carrying a member
        # nothing reaches. Without this the `unexplained` rule would hold on a
        # tree where the derivation had stopped finding any tool at all, which
        # is the same vacuous pass the non-vacuity cases guard against.
        def add(cls):
            cls.body.append(method_snippet(
                '    def read_word(self, addr):\n        return 0x00'))

        self.assertRejected('unexplained', self.clean_real,
                            grafted(self.clean_fake, add))


if __name__ == '__main__':
    unittest.main()