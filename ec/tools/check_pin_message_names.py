#!/usr/bin/env python3
"""Does a `check()` name every pin its own predicate holds?

`xdata_register_map.py --self-test` prints one line per assertion, and a reader
turning a red line to a failing argument needs the *pinned* figure and the
*measured* one both on it. Issue #1363 is a check that printed the measured one
in both slots: the cost-of-the-flip line interpolated `len(own_clusters)`,
`kept` and `hand_kept` twice and `OWNERSHIP["clusters"]`,
`["cluster_keys_kept"]` and `["hand_names_kept"]` not at all, so moving any one
of them by one produced a `FAIL` whose every column agreed with itself and whose
missing number was the number being held. **The exit code was 1 before the fix
and 1 after it** -- the difference was only ever in the text, so the status a
caller reads could not have told the two apart either.

**The property, and not a count of the tree.** Every `check()` whose predicate
subscripts a module-level constant names that key in its message's f-string.
There is no figure here of how many `check()` calls exist, and none of how many
obey: a census would be a number every merge has to edit, and a count passes on
the wrong population. The cases this reports are the ones the six-case sweep in
`docs/findings/xdata-check-message-pin-sweep.md` read, and the write-up carries
the per-case verdict for each.

**A substring does not detect the defect this exists for.** The message #1363
fixed says "440 clusters" and "400 of the committed cluster_keys" in plain
English, and interpolates none of the three keys it compares against. A sweep
that credited a key whose name appeared in the message would find `clusters`
and `cluster_keys` there and report one key named, on a line where none is.
And `OWNERSHIP['lost']` is a tuple whose only legal rendering is the `none` the
message already falls through to, so it has no name in the prose to be found
either. The test is therefore on the *subscript expression being interpolated*:
`checks()` reads the parse, finds `Subscript(Name(...), "key")` nodes under the
message, and asks whether the predicate's are among them.

**A stale allowlist entry is a failure, not a leftover.** Each entry is keyed on
a literal prefix of a check's own message text -- not on a line number, which
moves under every edit above it in a 5,000-line file, and which did move by five
on the fix this tool was written beside. An allowlisted case that no longer
violates must have its entry deleted, so the list shrinks as cases are fixed and
cannot decay into a standing exemption. That is the failure mode that would make
this tool worse than no tool: a checker whose allowlist only ever grows, exempting
`ORACLE["main_refs"]` from a check nobody reads any more.

**The five entries, and what each is.** `ORACLE["extmem_refs"]` is real but
mitigated: the measured sum is printed and the pin is not, but the two component
pins are printed expected-then-got on this same line, so a moved sum localises
to a component that did not move -- which is itself the evidence the sum moved.
`DIRECTION_INVARIANT["assign_shaped"]` is real and unmitigated: neither the pin
nor the measured `sum(shaped.values())` it was compared against appears on its
line, so a perturbation yields a `FAIL` whose whole content is about the
`*`-dereference stores. `ORACLE["both"]` and
`ORACLE["main_distinct"]`/`["main_refs"]` are mitigated --
each is named, as expected-then-got, by a sibling check over a different
measurement of the same key, so a moved pin turns both lines red.
`PER_PROGRAM["both_main_buckets"]`/`["both_pd_buckets"]` share a line with
`ORACLE["both"]` and do **not** share its verdict: the message prints the
measured five-tuples in both slots and neither pin, which is the #1363 shape
again. `OWNERSHIP["lost"]` is the `()` case. The write-up gives the reasoning
per case; the reasons are repeated here because an allowlist entry with no
reason is the standing exemption this tool is built to prevent.

**And what this tool is not.** It is not in `.github/scripts/agent-gates.sh`, and
cannot be until a human adds it there with a token that has `workflow` scope;
`.github/` is out of this repository's agent reach by construction. It is run by
its suite, which asserts the sweep over the committed tree, and by hand otherwise.

**The scope is one module, and the reason is a name collision.** `check` is
defined by twenty-one modules in `ec/tools/` with unrelated signatures --
`check_capture_claims.check(path, index, verbose)` and
`check_findings_frozen.check(repo)` among them -- so a tree-wide walk of the
callee name `check` would read those as census assertions. What is measured is
`xdata_register_map.py`, whose `check(label, cond)` is the one this is about;
`check(args)` at its end is the `--check` mode's own dispatch, has one
positional argument, and is not an assertion.

Usage:
    python3 ec/tools/check_pin_message_names.py
    python3 ec/tools/check_pin_message_names.py --verbose
"""
import argparse
import ast
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EC = os.path.join(HERE, os.pardir)
REPO = os.path.join(EC, os.pardir)

# The one module measured; see the scope paragraph in the docstring. Spelled
# relative to this directory so a checkout anywhere answers the same.
TARGET = "xdata_register_map.py"

# A module-level dict is a candidate constant: name and all-caps, because that
# is the convention every pin in `ec/tools/` follows and because a lowercase
# dict is a local working table. The limit is a real one -- the target also
# holds module-level tables that are not pin tables at all (`XSPACE_FORM` is an
# address-to-mnemonic lookup, `PAIR_TYPE_DIR` a vocabulary map), and a check
# reading one of those would be asked to name the key in its message. None is
# asked today, and `--verbose` names every table treated as a constant so a
# reader can see the population rather than trust it.
ORACLE_NAME = re.compile(r"^[A-Z][A-Z0-9_]*$")

# The sweep's residue, one entry per violating check, keyed on a literal prefix
# of that check's own message text. Each value is the keys the check reads and
# does not name, and the reason it is not reported; both are compared at run
# time, so an entry that has stopped describing its check fails rather than
# excusing a different set of keys under a message that happens to start the
# same way. A prefix is matched against the message's leading *literal run* -- the
# concatenated constant parts before the first interpolation -- so a prefix can
# never span a hole and be a function of a runtime value.
#
# The line each entry resolves to today is printed by the run, and is deliberately
# not written here: #1363's own fix moved this check five lines down, and an
# allowlist of line numbers would have needed editing for that.
ALLOWLIST = {
    "oracle: DAT_EXTMEM_ only, what issue #132 counted": (
        (("ORACLE", "extmem_refs"),),
        "real, mitigated: the measured sum is printed and the pin is not, but "
        "the two component pins are printed expected-then-got on this same "
        "line, so a moved sum localises to a component that did not move -- "
        "which is itself the evidence the sum moved"),
    "and the split partitions the census rather than re-counting it": (
        (("ORACLE", "both"),
         ("PER_PROGRAM", "both_main_buckets"),
         ("PER_PROGRAM", "both_pd_buckets")),
        "three cases and they do not agree. ORACLE['both'] is benign: the pin "
        "is printed expected-then-got by the 'PD-only, N touched by both' check "
        "a few lines below, over a different measurement of the same key. The "
        "two PER_PROGRAM bucket tuples are the #1363 shape again -- the message "
        "prints the measured five-tuples in both slots and neither pin -- and "
        "they are the sharpest thing left, because a five-tuple has no short "
        "rendering the line could interpolate"),
    "the only occurrences the second pass accepts and the census does not": (
        (("DIRECTION_INVARIANT", "assign_shaped"),),
        "real and unmitigated: the message prints DIRECTION_INVARIANT"
        "['deref_surplus'] and the measured surplus list, so a perturbation of "
        "assign_shaped yields a FAIL whose whole content is about the "
        "`*`-dereference stores and carries neither the pin nor the measured "
        "sum(shaped.values()) it was compared against. Nothing else reads the "
        "key"),
    "and the pass loses no address, which is the one thing it must never do": (
        (("OWNERSHIP", "lost"),),
        "benign with a caveat worth keeping: the pin is (), whose only legal "
        "rendering is the 'none' the message already falls through to when the "
        "measured set is empty, and the measured lost-address set is the "
        "informative part. A *moved* pin would be a baked-in allowance, and the "
        "line's own prose -- the one thing it must never do -- is what "
        "contradicts it"),
    "and the default census is unchanged, so the committed CSVs are still": (
        (("ORACLE", "main_distinct"), ("ORACLE", "main_refs")),
        "benign: the message is pure prose and carries no figure at all, but "
        "the 'oracle: the full census, both spellings' check above asserts the "
        "same pair against the same measured quantity, expected-then-got"),
}


def oracles(tree):
    """The names of every module-level UPPER_CASE dict constant in `tree`.

    Module level only, and that is a limit rather than a simplification: a
    constant built inside a function is not a candidate, so a check that pins
    one is not measured here. None is in the target today, and the summary says
    how many tables were treated as constants so a reader can see the population
    rather than trust it.
    """
    found = set()
    for node in tree.body:
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Dict):
            continue
        target = node.targets[0]
        if isinstance(target, ast.Name) and ORACLE_NAME.match(target.id):
            found.add(target.id)
    return found


def subscripts(node, tables):
    """{(table, key)} for every `TABLE["key"]` under `node`.

    The subscript expression and nothing else. A key whose name appears in the
    message's *prose* is not a `Subscript`, which is the whole difference
    between this tool and a substring search: the line #1363 fixed says
    "440 clusters" and "400 of the committed cluster_keys" and interpolates
    none of the three keys.
    """
    found = set()
    for sub in ast.walk(node):
        if not isinstance(sub, ast.Subscript):
            continue
        if not (isinstance(sub.value, ast.Name) and sub.value.id in tables):
            continue
        key = sub.slice
        if isinstance(key, ast.Constant) and isinstance(key.value, str):
            found.add((sub.value.id, key.value))
    return found


def lead(node):
    """The label's own text before its first interpolation, or None.

    Used only to key the allowlist, and None is a decline rather than a miss: an
    entry cannot be written against a label whose leading text is not a literal,
    so such a check is reported if it violates and is never excused. `+` is
    followed because six labels in the target are an f-string concatenated with a
    conditional tail, and reading the label as unreadable because of its tail
    would have put six committed checks outside the property.
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        out = []
        for part in node.values:
            if isinstance(part, ast.FormattedValue):
                break
            out.append(part.value)
        return "".join(out)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left, right = lead(node.left), lead(node.right)
        return left if left else right
    return None


def checks(text):
    """(tables, [(lineno, label, read, named)]) for every `check()` with a predicate.

    `read` is the set of `(table, key)` the predicate subscripts and `named` the
    set the label interpolates; the property this tool asserts is `read <=
    named`, and both halves are returned so a reader can see which one is
    missing rather than only that something is.

    A call with one positional argument is not here at all: `check(args)` is the
    `--check` mode's own dispatch at the end of the target, not an assertion.
    Every other call is measured whatever its label is, because the question --
    does the printed text interpolate this subscript -- is answerable by walking
    the label expression rather than by reading its type. The one shape this
    cannot see is a label held in a name and formatted elsewhere, which reads as
    every pin the predicate holds being unnamed: a false positive, and the
    direction that fails loudly rather than passing quietly.
    """
    tree = ast.parse(text)
    tables = oracles(tree)
    rows = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "check"):
            continue
        if len(node.args) < 2:
            continue
        rows.append((node.lineno, lead(node.args[0]) or "",
                     subscripts(node.args[1], tables),
                     subscripts(node.args[0], tables)))
    rows.sort()
    return tables, rows


def sweep(text):
    """(tables, swept, violating) over one module's source.

    `swept` is how many `check()` calls were read, which the summary prints and
    nothing asserts -- a figure of the tree is a claim every merge has to edit.
    """
    tables, rows = checks(text)
    violating = [(lineno, label, sorted(read - named))
                 for lineno, label, read, named in rows if read - named]
    return (tables, len(rows), violating)


def allowed(label, keys):
    """(entry-prefix, why) for the allowlist entry covering this case, or None.

    The keys are compared too, not just the message prefix: an entry whose
    prefix still matches but whose keys have moved is a rotated entry, and it
    has to be rewritten rather than left to excuse a set nobody wrote down.
    """
    for prefix, (wanted, why) in ALLOWLIST.items():
        if label.startswith(prefix) and sorted(wanted) == keys:
            return (prefix, why)
    return None


def report(tables, swept, violating, tool, verbose):
    """(report lines, problems) -- stdout is the report, stderr is what fails.

    The split is the contract: an allowlisted case is a line of the report, and
    only a violation or a stale entry goes to the stream a caller reads the
    verdict from.
    """
    out, problems, covered = [], [], set()
    for lineno, label, keys in violating:
        entry = allowed(label, keys)
        if entry is None:
            problems.append(
                f"{tool}:{lineno}: the predicate reads "
                + ", ".join(f"{t}[{k!r}]" for t, k in keys)
                + ", and the message names none of them -- a perturbation "
                  "yields a FAIL whose every column agrees with itself")
            continue
        covered.add(entry[0])
        out.append(f"  known  {tool}:{lineno}  "
                   + ", ".join(f"{t}[{k!r}]" for t, k in keys))
        out.append(f"         {entry[1]}")
        if verbose:
            out.append(f"         keyed on {entry[0]!r}")

    # The other direction, which a reader cannot get from reading the target. An
    # entry that excuses nothing is the standing exemption this tool refuses, and
    # an allowlist that can only grow is how a checker certifies a defect.
    for prefix, (wanted, _why) in sorted(ALLOWLIST.items()):
        if prefix in covered:
            continue
        problems.append(f"{tool}: the allowlist entry {prefix!r} excuses nothing "
                        f"-- the check it names no longer reads "
                        + ", ".join(f"{t}[{k!r}]" for t, k in wanted)
                        + " without naming it, or the message was reworded. "
                          "Delete the entry if the case is fixed, or rewrite it "
                          "if the message moved")

    out.append(f"{tool}: {len(tables)} module-level constant(s) read"
               + (f" ({', '.join(sorted(tables))})" if verbose else "")
               + f", {swept} check() call(s) swept, {len(violating)} reading a "
               f"pin their message does not name, {len(covered)} of those known "
               f"and listed above")
    return out, problems


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--verbose", action="store_true",
                    help="name every table treated as a constant and the "
                         "allowlist prefix each known case resolved by, so a "
                         "reader can see the population rather than trust it")
    args = ap.parse_args()

    path = os.path.join(HERE, TARGET)
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        print(f"{TARGET} cannot be read: {e}", file=sys.stderr)
        return 2
    try:
        tables, swept, violating = sweep(text)
    except SyntaxError as e:
        print(f"{TARGET} does not parse: {e}", file=sys.stderr)
        return 2

    out, problems = report(tables, swept, violating,
                           os.path.relpath(path, REPO), args.verbose)
    for line in out:
        print(line)
    for line in problems:
        print(line, file=sys.stderr)
    if problems:
        print(f"{len(problems)} problem(s).", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
