#!/usr/bin/env python3
"""Does a committed `group` cell still agree with the rule that produced it?

**The failure this exists to make impossible.** `grade_name_basis.py --check`
compares each committed `name_basis` cell against a fresh grading of the same
row, and the two have to be separate keys. An earlier version wrote the
computed grade straight over `name_basis` and then compared that key *with
itself*, so the check could not fail: hand-editing a committed grade passed a
per-commit gate, and the line it printed was reporting a tautology. That is
recorded, with the fix, under "Two bugs worth recording, because both were
silent" in `docs/findings/name-basis-and-groups.md`, and this module is the
same discipline applied to the grouping half, which never had it at all.
`group_functions.py --check` ran the naming rules, the cross-bank refusal, the
vocabulary and the evidence-path guard, and never once called `group_rows()` --
so a `group` cell edited to any other in-vocabulary value passed the gate, and
`--apply` then reverted the edit without saying so.

**Why this is its own file, and the second reason is the one that binds.**
`group_functions.py` is the file the fix has to reopen, so new logic in it is
new merge surface in the hottest file of the annotation layer; and
`group_functions` imports *this* module, so an import back the other way is a
cycle at import time rather than a style note. The shape that avoids both is
that `drift_problems()` takes rows **already keyed** by `(scope,
norm_addr(addr))` and does the comparison and the message formatting and
nothing else -- the caller keys both sides with the helper it already has, so
neither the address normalisation nor the two maps' construction is written
twice here.

**What is compared, and what is deliberately left out.** The two cells that
carry a rule's verdict: `group` and `group_basis`. `comment` and `evidence`
reproduce exactly on the committed tree as well -- 0 disagreements, every row,
both components -- so the comparison *could* be widened to all four cells and
is not. A `comment` is prose a human may legitimately want to reword, and a
check that refuses over a reworded comment is a gate people route around.
`CELLS` is the widening point and it is one line. This is a decision rather
than an oversight, and it is written down so that whoever widens it knows the
measurement has already been taken; `docs/findings/group-check-drift-and-shared-basis.md`
carries it and the command that produced it.

**What a zero here means.** Nothing is inferred from row counts. The questions
this module answers are about two dictionaries in one process. No hardware is
reachable from a GitHub-hosted runner, so nothing here is a behavioural result
about the machine.
"""

# The cells compared, and the order both sides are printed in. Index `i` of
# either value shape documented on `drift_problems` is `CELLS[i]`, which is
# what lets one loop read both of them.
CELLS = ("group", "group_basis")


def drift_problems(committed_by_key, computed_by_key, rel_path):
    """The rows whose committed cells disagree with the rule, as messages.

    Two dictionaries keyed the same way, and **two separate values**: that is
    the whole contract, and it is why they are two parameters rather than two
    fields on one record. `grade_name_basis.py` learned this the expensive way
    -- writing the computed value over the committed one left `check()`
    comparing a value with itself, which is a comparison that cannot fail no
    matter what the file says. Here the two shapes differ, so a caller that
    built both maps from one value could not satisfy them by accident:

      committed_by_key[key] = (group, group_basis, name)
      computed_by_key[key]  = the (group, group_basis, comment, evidence)
                               tuple `group_functions.group_rows()` returns

    `computed_by_key` carries no name: the name in a refusal is the one the
    annotation row gives the function, so it is read from the committed side,
    where the annotation CSV and the group file are still the same function.

    The cells compared are `CELLS` -- the first `len(CELLS)` entries of either
    value. `name` sits outside that count by construction: it is carried, not
    graded, and `group_rows()` has no opinion about it.

    Two directions, both refusals:

      * a cell that disagrees with the rule, which is the hand-edit this
        exists for;
      * a committed row the rule produces **nothing** for. That is the case
        where a group row outlived the annotated function it was derived from,
        or never had one, and it is not reachable by comparing cells: there is
        no computed cell to compare against.

    The other direction -- an annotated function with no group row at all --
    is already `check()`'s own "no group for annotated <scope> <addr>"
    refusal, and is deliberately not repeated here.
    """
    out = []
    for key in sorted(committed_by_key):
        committed = committed_by_key[key]
        scope, addr = key
        computed = computed_by_key.get(key)
        if computed is None:
            out.append("%s %s %s (%s): has a group row, and no annotated "
                       "function carries this scope and address, so the rule "
                       "has nothing to group it from and --apply would delete "
                       "the row." % (rel_path, scope, addr, committed[2]))
            continue
        for i, cell in enumerate(CELLS):
            if committed[i] != computed[i]:
                out.append("%s %s %s (%s): committed %s %s, the rule gives %s"
                           % (rel_path, scope, addr, committed[2], cell,
                              _cells(committed), _cells(computed)))
    return out


def _cells(values):
    """The compared cells as `group/group_basis`.

    Both sides of a disagreement are printed whole rather than one cell at a
    time, because a hand-edit and a rule that has moved underneath the file
    look identical from the offending cell alone: `ungrouped/type` is a
    plausible reading either way until the reader can also see what the rule
    expects.
    """
    return "/".join(values[i] for i in range(len(CELLS)))
