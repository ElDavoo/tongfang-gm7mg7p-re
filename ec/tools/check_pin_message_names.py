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

**The entries under `xdata_register_map.py`, and what each is.**
`ORACLE["extmem_refs"]` is real but mitigated: the measured sum is printed and
the pin is not, but the two component pins are printed expected-then-got on
this same line, so a moved sum localises to a component that did not move --
which is itself the evidence the sum moved.
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

**The scope is a named list, and the reason it is not the tree.** `check` is
defined across `ec/tools/` with unrelated signatures --
`check_capture_claims.check(path, index, verbose)` and
`check_findings_frozen.check(repo)` among them -- so a tree-wide walk of the
callee name `check` would read those as census assertions: the call is matched
by bare name and the callee is **not** resolved per module, so `check(path,
index, verbose)` reads as an assertion with no predicate at all. `TARGETS` is
therefore the set of modules whose `check(label, cond)` is the one this is
about, named rather than derived, and `--population` prints what a walk over
every module under `POPULATION_DIRS` actually finds so a reader sees the
population this is not covering instead of trusting the scope is right. How
many modules that is changes whenever a tool is added or removed, so the figure
is that command's output rather than a number kept in this docstring; the
method is `--population`.

**What the callee name costs inside a target, and one coincidence it leans
on.** A call with one positional argument is not an assertion, which is what
disambiguates `export_ownership.py`'s two definitions of `check`: the
module-level `check(args)` that is the `--check` mode's own dispatch, and the
`check(label, cond)` nested in `self_test` that this census is about. That is a
coincidence of two signatures, not a property of either definition, and it is
why the scope paragraph has to say it -- a reader who assumed the filter
resolves callees would be wrong about both files. The other name the filter
cannot resolve is a *held* predicate: a check passing a precomputed boolean has
no `Subscript` under its second argument, so it can only ever read as a clean
one, which is the direction that passes quietly.

Usage:
    python3 ec/tools/check_pin_message_names.py
    python3 ec/tools/check_pin_message_names.py --verbose
    python3 ec/tools/check_pin_message_names.py --population
"""
import argparse
import ast
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EC = os.path.join(HERE, os.pardir)
REPO = os.path.join(EC, os.pardir)

# The modules measured, spelled relative to the repository root so a checkout
# anywhere answers the same and so a sibling under `windows/tools/` or
# `bios/tools/` can be added without a second resolution rule. See the scope
# paragraph in the docstring: this is a list because the callee name cannot be
# resolved per module, not because a tree-wide walk was tried and abandoned.
TARGETS = (
    "ec/tools/xdata_register_map.py",
    "ec/tools/export_ownership.py",
)

# Where `--population` walks. A reader asking what is not covered gets the
# answer from running it, so the directories are named here rather than the
# count of what they hold.
POPULATION_DIRS = ("ec/tools", "windows/tools", "bios/tools")

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
#
# Per module, because the entries are only ever read against the module whose
# checks they describe. A flat list scored every target at once, so pointing
# this at a module with no entries emitted one "excuses nothing" line per
# census entry -- the entry was not stale, it was simply about a different file.
# An empty dict is the correct end state for a module whose cases are all
# fixed, and the sweep is what turns a case added back into a case no entry
# covers.
ALLOWLIST = {
    "ec/tools/xdata_register_map.py": {
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
    },
    # Empty because every case the sweep found here is fixed: each `check()`
    # line it reported now names its own pins expected-then-got, which
    # `test_export_ownership_pin_messages.py` asserts by perturbing each one.
    # An entry here would be an exemption for a case that does not exist.
    # `SHARE_ORACLE` arrived with #1651 and its checks are named on the same
    # terms; docs/findings/export-ownership-pin-messages.md is the write-up.
    "ec/tools/export_ownership.py": {},
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


def allowed(target, label, keys):
    """(entry-prefix, why) for the allowlist entry covering this case, or None.

    Scoped to `target`, because an entry describes one module's check and
    reading it against another module's case is how a flat list came to report
    every census entry as stale the moment this was pointed at a second file.

    The keys are compared too, not just the message prefix: an entry whose
    prefix still matches but whose keys have moved is a rotated entry, and it
    has to be rewritten rather than left to excuse a set nobody wrote down.
    """
    for prefix, (wanted, why) in ALLOWLIST.get(target, {}).items():
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
        entry = allowed(tool, label, keys)
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
    # an allowlist that can only grow is how a checker certifies a defect. It is
    # read against this target's own entries only -- every entry in the map,
    # which is what made the first widened run report five stale entries that
    # were all about a different module.
    for prefix, (wanted, _why) in sorted(ALLOWLIST.get(tool, {}).items()):
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


def population(dirs=POPULATION_DIRS):
    """Report lines for every module under `dirs`, one per module that defines one.

    This is the answer to "what is `TARGETS` not covering?", printed rather
    than asserted: a module's row is a fact about the tree and goes stale on
    every merge that adds a tool, so nothing holds it to a value. What a reader
    can check is the standing caveat in the docstring -- the callee is matched
    by bare name and is not resolved per module -- which is why a row can name
    a module whose `check` is `check(path, index, verbose)` and every one of
    whose swept calls is not an assertion.

    The closing lines name the modules carrying an unnamed pin, because they
    are the actionable part of a list long enough to need one, and because "the
    named scope covers every case" is a claim about the tree that this mode
    exists to let a reader refute. Each named module is an *unresolved question*, not a
    confirmed case: it needs its own `check` read before it could join
    `TARGETS`, which is a decision this tool does not make.
    """
    out = [f"population: every module under {', '.join(dirs)} defining `check`, "
           f"by the bare-name walk `sweep()` uses. The callee is not resolved "
           f"per module, so a `check` with another signature reads as an "
           f"assertion here; see the docstring."]
    flagged = []
    for relpath in sorted(dirs):
        directory = os.path.join(REPO, relpath)
        if not os.path.isdir(directory):
            continue
        for name in sorted(os.listdir(directory)):
            if not name.endswith(".py"):
                continue
            path = os.path.join(directory, name)
            rel = os.path.relpath(path, REPO)
            with open(path, encoding="utf-8") as f:
                text = f.read()
            try:
                tables, swept, violating = sweep(text)
            except SyntaxError as e:
                out.append(f"  {rel}: does not parse ({e})")
                continue
            if not swept and not tables:
                continue
            marked = " *" if rel in TARGETS else ""
            if violating and rel not in TARGETS:
                flagged.append(rel)
            out.append(f"  {rel}{marked}: {len(tables)} constant(s), "
                       f"{swept} call(s) swept, {len(violating)} unnamed pin(s)")
    out.append("* in TARGETS, and so swept for real; every other row is what a "
               "tree-wide walk of the bare name would answer, which is why the "
               "scope is a list.")
    out.append("modules with an unnamed pin outside TARGETS, each a question "
               "this tool does not answer: "
               + (", ".join(flagged) if flagged else "none"))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--verbose", action="store_true",
                    help="name every table treated as a constant and the "
                         "allowlist prefix each known case resolved by, so a "
                         "reader can see the population rather than trust it")
    ap.add_argument("--population", action="store_true",
                    help="report every module under the tool directories that "
                         "defines `check`, rather than sweeping TARGETS, so a "
                         "reader can see what the named scope is not covering")
    args = ap.parse_args()

    if args.population:
        for line in population():
            print(line)
        return 0

    out, problems = [], []
    for relpath in TARGETS:
        path = os.path.join(REPO, relpath)
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        except OSError as e:
            print(f"{relpath} cannot be read: {e}", file=sys.stderr)
            return 2
        try:
            tables, swept, violating = sweep(text)
        except SyntaxError as e:
            print(f"{relpath} does not parse: {e}", file=sys.stderr)
            return 2
        target_out, target_problems = report(tables, swept, violating,
                                             relpath, args.verbose)
        out.extend(target_out)
        problems.extend(target_problems)

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
