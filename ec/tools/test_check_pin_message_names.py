#!/usr/bin/env python3
"""Offline cases for check_pin_message_names.py: the property, and the sweep.

**The case that decides whether the tool is worth having comes first.**
Issue #1363's check printed the measured triple in both slots and the three
`OWNERSHIP` pins in neither, while its prose said "440 clusters" and "400 of the
committed cluster_keys". A sweep that credited a key by a word appearing in the
message would find two of the three names there and report the line as naming
one, on a line where none is interpolated. `TheLineItWasWrittenFor` pastes the
pre-#1363 text verbatim, line breaks and quoting included, and asserts that all
three keys come out; the case beside it renders that same label and asserts the
words really are in it, so this is a control for the wrong implementation and
not only for this one.

**The sweep is asserted as a set, never as a count.** What the committed tree
has to satisfy is that the cases still violating the property are exactly the
ones `ALLOWLIST` excuses, keyed on a message prefix rather than a line number:
those numbers move under every edit above them in a 5,000-line file, and
#1363's own fix moved the check they key on by five. A count of `check()` calls, of
violations, or of allowlist entries is a value every merge that adds a check has
to edit, which is the trap `CLAUDE.md` names. The set fails in both directions
on its own -- a case fixed without its entry deleted is an entry that excuses
nothing, and a new violation is a case no entry covers.

**Both directions of the allowlist, because the second is the dangerous one.**
An entry that excuses nothing is the standing exemption a checker decays into,
and it is the direction a reader cannot get by reading the target: the case is
gone and only the allowlist still says so. The rotated-keys case is separate,
because an entry whose prefix still matches but whose keys have moved is the
other way that list rots -- it would excuse a set of pins nobody wrote down.

**The shapes, each with the reason it could have gone blind.** Six labels in the
target are an f-string concatenated onto a conditional tail, and reading a label
as unreadable because of its tail would have put six of the target's checks
outside the property, without saying so. `OWNERSHIP['buckets']` is interpolated
through a generator expression nested two f-strings deep, and a rule reading only
the top level would have reported the bucket-totals check, which is a correct
one. A lowercase dict and a constant built inside a function are not candidates,
which is a limit rather than a defect: treating a working table's keys as pins
would excuse keys nothing pins.

**No count of the tree is asserted anywhere**; the summary's figures are printed
and nothing holds them. Offline throughout: these cases read one committed `.py`
and sources built here. No EC, no laptop and no Windows box was reached, and
nothing in them is evidence about what the EC does with a byte -- the property
is about a message a Python tool prints.
"""
import ast
import contextlib
import importlib.util
import io
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "check_pin_message_names.py")
spec = importlib.util.spec_from_file_location("check_pin_message_names", TOOL)
cpn = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cpn)
TARGET = os.path.join(HERE, cpn.TARGET)

# The pre-#1363 text, transcribed from the committed target rather than
# paraphrased -- a paraphrase that happened to name a key would be a control
# passing for the wrong reason. It is the only case that matters: everything
# else in this file could pass on a tool that answered "the word is in the
# message".
PRE_FIX = '''\
OWNERSHIP = {"clusters": 440, "cluster_keys_kept": 400, "hand_names_kept": 4}

def self_test(own_clusters, committed_keys, kept, hand_kept, hand_keys):
    check(f"and the flip would renumber: {len(own_clusters)} clusters against "
          f"the committed {len(committed_keys)}, {kept} of the committed "
          f"cluster_keys surviving, {hand_kept} of the {len(hand_keys)} hand "
          f"names in annotations/xdata-cluster-names.csv (got "
          f"{len(own_clusters)}/{kept}/{hand_kept})",
          len(own_clusters) == OWNERSHIP["clusters"]
          and kept == OWNERSHIP["cluster_keys_kept"]
          and hand_kept == OWNERSHIP["hand_names_kept"])
'''


def target_source():
    with open(TARGET, encoding="utf-8") as f:
        return f.read()


def source_with(body, tables='ORACLE = {"a": 1, "b": 2}\n'):
    """A stand-in module, the constant first so a body can be a bare snippet."""
    return tables + body


def label_source(text):
    """The first `check()` label's own source text, interpolations and all."""
    for node in ast.walk(ast.parse(text)):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "check"):
            return ast.get_source_segment(text, node.args[0])
    return None


# The five names the pre-#1363 message interpolates, filled so the label can be
# rendered rather than read as source. The demonstration is about the text a
# reader sees on the red line, and rendering it is what makes that testable.
PRE_FIX_VALUES = {"own_clusters": list(range(440)),
                  "committed_keys": list(range(439)),
                  "kept": 400, "hand_kept": 4, "hand_keys": list(range(9))}


def rendered_label(text, **values):
    """The first `check()` label as a reader would see it printed.

    The label is written over five lines in the target, and `ast.parse` in
    `eval` mode will not take an implicit concatenation whose continuation is
    indented; reflowing it to one line is what the parser needs and changes
    nothing about the string.
    """
    reflowed = " ".join(part.strip() for part in label_source(text).splitlines())
    return eval(compile(ast.parse(reflowed, mode="eval"), "<label>", "eval"),
                {"len": len, **values})


def run_main(source, argv=()):
    """(rc, stdout, stderr) from `cpn.main()` over a scratch copy of the target.

    `HERE` is patched rather than a file under it, so the scratch module never
    has to be written into `ec/tools/`: a second `xdata_register_map.py` in the
    tree would be found by the runner's `find` and by every tool that resolves a
    sibling by name. `source=None` writes no file at all, which is the missing
    target rather than an empty one.
    """
    with tempfile.TemporaryDirectory() as tmp:
        if source is not None:
            with open(os.path.join(tmp, cpn.TARGET), "w", encoding="utf-8") as f:
                f.write(source)
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(cpn, "HERE", tmp), \
                mock.patch.object(sys, "argv", ["check_pin_message_names.py",
                                                *argv]), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = cpn.main()
    return rc, out.getvalue(), err.getvalue()


class TheLineItWasWrittenFor(unittest.TestCase):
    """The pre-#1363 case, and the controls that keep it from passing vacuously."""

    def test_all_three_pins_are_reported_from_a_message_naming_the_word(self):
        _tables, swept, violating = cpn.sweep(PRE_FIX)
        self.assertEqual(len(violating), 1, violating)
        _lineno, _label, keys = violating[0]
        self.assertEqual(keys, [("OWNERSHIP", "cluster_keys_kept"),
                                ("OWNERSHIP", "clusters"),
                                ("OWNERSHIP", "hand_names_kept")])
        self.assertEqual(swept, 1)

    def test_the_words_a_substring_sweep_would_have_matched_are_there(self):
        # The control for the wrong implementation, and the reason the case
        # above is worth a fixture. The label is *rendered*, not read as source:
        # the source text of the interpolations would match a substring sweep by
        # accident, because `own_clusters` contains `clusters`. Rendered, a sweep
        # crediting a key by a word in the message finds `clusters` and
        # `cluster_keys` there and reports one key named -- none is interpolated.
        text = rendered_label(PRE_FIX, **PRE_FIX_VALUES)
        self.assertIn("clusters", text)
        self.assertIn("cluster_keys", text)
        self.assertNotIn("hand_names_kept", text)

    def test_the_same_check_with_the_pins_named_passes(self):
        # The fix's shape, on the same three keys: pinned figures in the
        # expected slot, measured ones in the `got`. Nothing reports it, and the
        # pair is what says the difference is the message.
        fixed = PRE_FIX.replace(
            'f"and the flip would renumber: {len(own_clusters)} clusters against "\n'
            '          f"the committed {len(committed_keys)}, {kept} of the committed "\n'
            '          f"cluster_keys surviving, {hand_kept} of the {len(hand_keys)} hand "\n'
            '          f"names in annotations/xdata-cluster-names.csv (got "',
            'f"and the flip would renumber: {OWNERSHIP[\'clusters\']} clusters "\n'
            '          f"against the committed {len(committed_keys)}, "\n'
            '          f"{OWNERSHIP[\'cluster_keys_kept\']} of the committed cluster_keys "\n'
            '          f"surviving, {OWNERSHIP[\'hand_names_kept\']} of the {len(hand_keys)} "\n'
            '          f"hand names in annotations/xdata-cluster-names.csv (got "')
        self.assertNotEqual(fixed, PRE_FIX, "the fixture no longer matches its text")
        self.assertEqual(cpn.sweep(fixed)[2], [])

    def test_omitting_one_of_three_is_reported_with_its_line(self):
        source = source_with('''\
def self_test(x):
    check(f"the pin is {ORACLE['a']} (got {x})",
          x == ORACLE["a"] and x == ORACLE["b"])
''')
        _tables, _swept, violating = cpn.sweep(source)
        self.assertEqual(len(violating), 1)
        lineno, _label, keys = violating[0]
        self.assertEqual(keys, [("ORACLE", "b")])
        # The line the `check(` itself is on, read off the fixture rather than
        # written down: the report has to cite where the reader will look, and a
        # hand-counted number here is a number the fixture's next edit moves.
        opens = next(n for n, line in enumerate(source.splitlines(), 1)
                     if line.lstrip().startswith("check("))
        self.assertEqual(lineno, opens)

    def test_the_predicate_is_unchanged_by_the_fix(self):
        # A pin in the expected slot is only a pin if the `got` slot is still
        # what the tree measures, so the committed predicate must keep comparing
        # against `len(own_clusters)`, `kept` and `hand_kept` rather than
        # against the constant twice. The three fragments are the whole of that
        # predicate, held as text rather than as a line number so a change above
        # it does not move the case.
        committed = target_source()
        for fragment in ('len(own_clusters) == OWNERSHIP["clusters"]',
                         'kept == OWNERSHIP["cluster_keys_kept"]',
                         'hand_kept == OWNERSHIP["hand_names_kept"]'):
            self.assertIn(fragment, committed, fragment)


class TheCommittedTree(unittest.TestCase):
    """The property and the recorded sweep, against `xdata_register_map.py`."""

    def test_the_sweep_reads_something(self):
        # A clean run over an empty population is the failure, not a pass.
        _tables, rows = cpn.checks(target_source())
        self.assertTrue(rows, "the sweep found no check() call in the target")
        self.assertTrue(any(read for _l, _lab, read, _n in rows),
                        "no check() in the target reads a module constant, so "
                        "the population is empty for a reason worth seeing")

    def test_the_sweep_is_exactly_the_recorded_set(self):
        # Keyed on a message prefix and not on a line number, because the line
        # numbers move: #1363's own fix shifted that check by five, and an entry
        # keyed on `:3609` would have needed editing for a change that fixed a
        # different check.
        _tables, _swept, violating = cpn.sweep(target_source())
        recorded = {}
        for _lineno, label, keys in violating:
            entry = cpn.allowed(label, keys)
            self.assertIsNotNone(entry, f"a case the allowlist does not excuse: {keys}")
            recorded[entry[0]] = keys
        self.assertEqual(recorded,
                         {prefix: sorted(wanted)
                          for prefix, (wanted, _why) in cpn.ALLOWLIST.items()})

    def test_the_check_holding_the_cost_of_the_flip_names_its_three_pins(self):
        # #1363's fix, held without naming a line: the one check whose predicate
        # reads `OWNERSHIP["clusters"]` exists exactly once, and its message
        # interpolates all three of the pins it reads.
        _tables, rows = cpn.checks(target_source())
        found = [row for row in rows if ("OWNERSHIP", "clusters") in row[2]]
        self.assertEqual(len(found), 1, found)
        lineno, _label, read, named = found[0]
        for key in ("clusters", "cluster_keys_kept", "hand_names_kept"):
            self.assertIn(("OWNERSHIP", key), read,
                          f":{lineno} no longer reads {key!r}; the sweep below "
                          f"would pass for a reason this case would catch")
            self.assertIn(("OWNERSHIP", key), named,
                          f":{lineno} reads OWNERSHIP[{key!r}] and names none of it")

    def test_every_entry_carries_its_reason(self):
        # An allowlist entry with no reason is the standing exemption this tool
        # exists to refuse, and the sweep write-up's verdicts are why these five
        # are here rather than the six.
        for prefix, (keys, why) in cpn.ALLOWLIST.items():
            self.assertTrue(keys, prefix)
            self.assertGreater(len(why.strip()), 40,
                               f"{prefix!r} excuses a set of pins with a stub "
                               f"of a reason")


class TheAllowlist(unittest.TestCase):
    """Both directions, and the two ways an entry rots."""

    def test_a_stale_entry_is_a_failure(self):
        source = source_with('''\
def self_test(x):
    check(f"the pin is {x} (got {x})", x == ORACLE["a"])
''')
        stale = {"a message no check in the tree has": ((("ORACLE", "b"),), "why")}
        with mock.patch.dict(cpn.ALLOWLIST, stale, clear=True):
            rc, out, err = run_main(source)
        self.assertEqual(rc, 1)
        self.assertIn("excuses nothing", err)
        self.assertNotIn("excuses nothing", out,
                         "the finding must not reach the report stream")

    def test_fixing_a_case_without_deleting_its_entry_goes_red(self):
        # The rule this is the case behind, in the direction a fix actually
        # arrives in: the `OWNERSHIP['lost']` check with the pin named in its
        # message no longer violates anything, and the entry that excused it is
        # now standing on nothing. Nothing would say so if the tool only checked
        # the violations.
        source = source_with('''\
def self_test(lost, got):
    check(f"and the pass loses no address, which is the one thing it must "
          f"never do (lost: {', '.join(sorted(got)) or 'none'}; pinned: "
          f"{len(OWNERSHIP['lost'])})", got == set(OWNERSHIP["lost"]))
''', tables='OWNERSHIP = {"lost": ()}\n')
        self.assertEqual(cpn.sweep(source)[2], [], "the fixture still violates")
        rc, _out, err = run_main(source)
        self.assertEqual(rc, 1)
        self.assertIn("excuses nothing", err)
        self.assertIn("and the pass loses no address", err)

    def test_an_entry_whose_keys_have_moved_does_not_excuse_them(self):
        # The other way the list rots. The prefix still matches, so a
        # prefix-only comparison would keep excusing a set of pins nobody wrote
        # down; the keys are compared for that reason.
        source = source_with('''\
def self_test(x):
    check(f"and the pass loses no address, which is the one thing it must "
          f"never do (lost: {x})",
          x == ORACLE["a"] and x == ORACLE["b"])
''')
        _tables, _swept, violating = cpn.sweep(source)
        self.assertEqual(len(violating), 1)
        self.assertIsNone(cpn.allowed(violating[0][1], violating[0][2]))

    def test_an_entry_keyed_on_text_survives_the_check_moving(self):
        # Nine blank lines put the same check nine lines lower than it would
        # otherwise sit. The entry does not move and the report prints wherever
        # it resolved to -- which is what #1363's own five-line shift would have
        # broken.
        source = source_with("\n" * 9 + '''\
def self_test(x):
    check(f"and the default census is unchanged, so the committed CSVs are "
          f"still what a plain run produces", x == ORACLE["a"] and x == ORACLE["b"])
''')
        wanted = (("ORACLE", "a"), ("ORACLE", "b"))
        entry = {"and the default census is unchanged, so the committed CSVs "
                 "are still": (wanted, "a reason long enough to be a reason")}
        with mock.patch.dict(cpn.ALLOWLIST, entry, clear=True):
            _tables, _swept, violating = cpn.sweep(source)
            rc, _out, err = run_main(source)
        self.assertEqual(rc, 0, err)
        self.assertEqual(violating[0][2], sorted(wanted))
        self.assertGreater(violating[0][0], 10,
                           "the fixture no longer puts the check low in the file")

    def test_a_prefix_may_not_span_an_interpolation(self):
        # An entry written across a hole would be a function of a runtime value,
        # so a key is matched against the leading literal run only.
        source = source_with('''\
def self_test(x):
    check(f"the pin is {x} clusters and the other is "
          f"{ORACLE['a']} of them", x == ORACLE["a"] and x == ORACLE["b"])
''')
        _tables, _swept, violating = cpn.sweep(source)
        self.assertEqual(violating[0][1], "the pin is ")
        across = {"the pin is {x} clusters and the other is ":
                  ((("ORACLE", "b"),), "a reason long enough to be a reason")}
        with mock.patch.dict(cpn.ALLOWLIST, across, clear=True):
            self.assertIsNone(cpn.allowed(violating[0][1], violating[0][2]))


class Shapes(unittest.TestCase):
    """The forms the walk has to read, each for the case that made it matter."""

    def test_a_label_concatenated_onto_a_conditional_is_still_measured(self):
        source = source_with('''\
def self_test(x, flag):
    check(f"the pin is {ORACLE['a']}" + (f" -- off by {x}" if flag else ""),
          x == ORACLE["a"] and x == ORACLE["b"])
''')
        _tables, _swept, violating = cpn.sweep(source)
        self.assertEqual(len(violating), 1)
        self.assertEqual(violating[0][2], [("ORACLE", "b")])
        self.assertEqual(violating[0][1], "the pin is ")

    def test_a_pin_nested_in_a_generator_inside_the_message_is_named(self):
        # `OWNERSHIP['buckets']` is rendered through a comprehension two
        # f-strings deep. A rule reading only the top level would report the
        # bucket-totals check, which is one of the correct ones.
        source = source_with('''\
def self_test(fired):
    check("and its bucket totals, "
          f"{' '.join(f'{k} {v}' for k, v in ORACLE['a'].items())} "
          f"(got {' '.join(f'{k} {fired.get(k, 0)}' for k in ORACLE['a'])})",
          all(fired.get(k, 0) == v for k, v in ORACLE["a"].items()))
''')
        self.assertEqual(cpn.sweep(source)[2], [])

    def test_a_lowercase_dict_is_not_a_candidate_constant(self):
        # A limit rather than a defect: a local working table is not a pin
        # table, and treating its keys as one would excuse keys nothing pins.
        source = source_with('''\
def self_test(x):
    oracle = {"a": 1}
    check(f"the pin is {x}", x == oracle["a"])
''', tables="")
        self.assertEqual(cpn.sweep(source)[2], [])

    def test_a_constant_built_inside_a_function_is_not_read_either(self):
        # The other half of the same rule, and held because the summary's
        # constant count is what a reader would use to judge the scope.
        source = source_with('''\
def self_test(x):
    ORACLE = {"a": 1}
    check(f"the pin is {x}", x == ORACLE["a"])
''', tables="")
        self.assertEqual(cpn.sweep(source)[2], [])

    def test_the_mode_dispatch_is_not_an_assertion(self):
        # `check(args)` at the end of the target is the `--check` mode calling
        # itself: one positional argument, no predicate. Counting it would have
        # made the swept figure wrong by one for a reason no reader could see.
        source = source_with('''\
def check(args):
    return 0

def main(args):
    check(args)
''')
        self.assertEqual(cpn.sweep(source)[1], 0)

    def test_another_callee_of_the_same_name_is_not_swept(self):
        # The scope is one module precisely because twenty-one modules in `ec/tools/`
        # define `check` with unrelated signatures. The call is matched by the
        # bare name, so an attributed callee is not this census.
        source = source_with('''\
def self_test(x):
    other.check(f"the pin is {x}", x == ORACLE["a"])
    check_equal(f"the pin is {x}", x == ORACLE["a"])
''')
        self.assertEqual(cpn.sweep(source)[1], 0)


class TheRun(unittest.TestCase):
    """`main()` as a consumer sees it: the exit code and the stream split."""

    def test_a_clean_target_exits_zero_with_an_empty_stderr(self):
        rc, out, err = run_main(target_source())
        self.assertEqual(rc, 0, err)
        self.assertEqual(err, "")
        self.assertIn("check() call(s) swept", out)

    def test_a_violation_exits_one_with_the_finding_on_stderr_only(self):
        # The stream split is the case. A report a reader cannot route to a
        # stream is not a contract: the summary stays on stdout and the finding
        # goes to stderr, because those two are read by different consumers. The
        # allowlist is emptied so the count is the one finding under test and not
        # five entries pointing at a fixture none of them describes.
        with mock.patch.dict(cpn.ALLOWLIST, {}, clear=True):
            rc, out, err = run_main(PRE_FIX)
        self.assertEqual(rc, 1)
        self.assertIn("'clusters'", err)
        self.assertIn("1 problem(s)", err)
        self.assertNotIn("'clusters'", out)
        self.assertIn("check() call(s) swept", out)

    def test_a_missing_target_is_a_usage_error_not_a_clean_run(self):
        rc, _out, err = run_main(None)
        self.assertEqual(rc, 2)
        self.assertIn("cannot be read", err)

    def test_an_unparseable_target_is_refused_rather_than_read_as_clean(self):
        rc, _out, err = run_main("ORACLE = {")
        self.assertEqual(rc, 2)
        self.assertIn("does not parse", err)

    def test_verbose_names_the_population_and_what_each_entry_keyed_on(self):
        rc, out, err = run_main(target_source(), ["--verbose"])
        self.assertEqual(rc, 0, err)
        self.assertIn("ORACLE, OWNERSHIP", out)
        self.assertIn("keyed on ", out)
        quiet_rc, quiet, _quiet_err = run_main(target_source())
        self.assertEqual(quiet_rc, rc)
        self.assertNotIn("keyed on ", quiet)


class TheCommand(unittest.TestCase):
    """The process, which is what a caller outside this file would run."""

    def test_the_committed_tree_exits_zero(self):
        proc = subprocess.run([sys.executable, TOOL], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stderr, "")

    def test_help_is_reached_by_something(self):
        # Otherwise nothing runs it, and a checker whose help no invocation
        # reaches is a checker whose usage nobody can discover.
        proc = subprocess.run([sys.executable, TOOL, "--help"],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0)
        self.assertIn("Usage:", proc.stdout)
        self.assertIn("check_pin_message_names", proc.stdout)

    def test_an_unknown_flag_is_a_usage_error(self):
        proc = subprocess.run([sys.executable, TOOL, "--not-a-flag"],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2)


if __name__ == "__main__":
    unittest.main()
