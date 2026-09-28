#usr/bin/env python3
"""Hold a cluster name to a shape before it can read as a citation in prose.

`ec/annotations/xdata-cluster-names.csv` is the one hand-edited surface the
XDATA census adds (`ec/README.md` is explicit that it must not join the
generated list in `agent-conflicts.yml`), and `ec/README.md` also says
"Adding a name is a one-row edit". So the file is designed to grow one row at
a time, by hand, with no gate on what a name may look like.

That matters because `check_cluster_citations.py`'s `name_re()` builds
`\\b(?:name1|name2|...)\\b` from the census's own `cluster_name` values and
applies it to **every unit that also makes a membership claim**. A name is
therefore a citation wherever those words appear, and the checker's own
docstring used to name the failure and decline to fix it: a name like
`charge-target` would be read as a citation in a sentence that only means the
words. Nothing held the next row to it. This is what holds it.

**Four rules, each returning `(name, what_would_pass)`.** Every one of them is a
refusal that names its offender and the shape that would pass, because a
cluster name is chosen by a human reading a membership and a bare `FAIL`
sends them back to this file to work out which of the four it was.

- **R1 `multi_slug`** — `\\A[a-z0-9]+(?:-[a-z0-9]+)+\\Z`. Two or more
  `-`-separated slugs. Refuses a single token (`gate`), an `_`-separated name
  (`charge_target`), a bare address slug (`0442`) and an address as written
  (`0x0442`). Fixing the separator is part of the rule: a name that could spell
  its words either way is a name `name_re()` matches in two forms.
- **R2 `inside_another_name`** — no name is a substring of another. Refuses
  `level-block` alongside `level-block-086x`, which `name_re()`'s longest-first
  sort currently keeps apart by construction rather than by rule.
- **R3 `collides_with_a_known_token`** — the name is not a known address
  spelling, does not carry a `0x`-prefixed known address, and does not equal a
  known function or symbol name once `-`/`_` are one separator.
- **R4 `prefixes_a_known_identifier`** — the name is not a `_`-delimited word
  prefix of a known identifier.

**The containment test in R3 is on the `0x` form, and that is forced by the
data rather than chosen.** Four committed names carry a bare four-hex slug that
is a real XDATA address — `flag-pair-0442`, `countdown-06c6`, `countdown-06cd`,
`fan-step-08a0` — so "contains no known address" read on the bare hex is red on
four of the nine names the check has to keep passing, and a rule that refuses
the file it is meant to protect is a rule that gets deleted. The `0x` form is
also the only one `check_cluster_citations.py`'s own `ADDRESS` regex matches,
so it is the same boundary that file already draws.

**R4, and not R3, is what catches `charge-target`.** The issue's own example is
two `-`-separated slugs, so R1 passes it; it is not a substring of a committed
name; and it is not an address. It is caught because the tree already uses the
same words for the same thing: `charge_target_update` and
`charge_target_minus_r3_times_0a47` in `ec/annotations/ghidra-functions.csv`,
and `CHARGE_TARGET_MV_0` / `CHARGE_TARGET_MV_1` at `0x0522`/`0x0523` in
`ec/ghidra/xdata-symbols.csv`. **Word prefix, not equality** — the name is
shorter than the identifiers, and an equality rule would pass it.

**What these rules cannot see, which is the rest of the point.** They are "not
found by this method" findings and every one of them belongs in the same
category as the caveat `ec/annotations/registers.yaml` carries for a static
scan.

- *A name too generic for the prose.* R1-R4 read the names file and four CSVs.
  They do not read `ec/`, `docs/` or `evidence/`, so they cannot see a name
  that is already being read as a citation in ordinary prose. The rule that
  would catch it — a name may not already occur as a whole token in a unit that
  makes no cluster claim — is red today on the committed names: measured on
  `main`, over the same files `check_cluster_citations.py` walks and the same
  unit split its `units()` makes, `mode-oem-init` occurs in 22 such units,
  `level-block-086x` in 18 and `counter-sweep` in 15, against 32 for
  `charge-target`. It is left out and recorded with the counts in
  `docs/findings/name-shape.md` rather than shipped red for the names the
  issue asks to keep passing.
- *`fan-level`, and names like it.* The issue's second example is caught by
  none of these four rules, and the reason is the row above: a distinctiveness
  rule that caught it is red on the committed file. **`fan-level` is not
  refused by this tool**, and a green run here is not a claim that it would be.
- *A collision with a symbol the census does not carry.* The vocabulary is four
  committed CSVs. A name that collides with a Windows-side class, a BIOS symbol
  or a prose word is outside all of them.
- *Whether a name is a good name.* Nothing here reads the `note` column's
  evidence or asks whether the name describes the membership it is attached to.

Nothing here resolves anything against the firmware. Every input is a committed
CSV, no image is opened, no register is read back, and no laptop, EC or Windows
machine is involved.

Usage:
    python3 ec/tools/cluster_name_shape.py
    python3 ec/tools/cluster_name_shape.py --names /tmp/names.csv
"""
import argparse
import csv
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EC = os.path.join(HERE, os.pardir)

NAMES_CSV = os.path.join(EC, "annotations", "xdata-cluster-names.csv")
REGISTERS_CSV = os.path.join(EC, "annotations", "xdata-registers.csv")
CLUSTERS_CSV = os.path.join(EC, "annotations", "xdata-clusters.csv")
FUNCTIONS_CSV = os.path.join(EC, "annotations", "ghidra-functions.csv")
SYMBOLS_CSV = os.path.join(EC, "ghidra", "xdata-symbols.csv")

# Four CSVs and one column each, and the recipe `vocabulary()` prints the size
# of. Three of the four are identifier namespaces -- the EC's own
# `snake_case` functions, the register names `xdata-registers.csv` carries, and
# the generated `xdata-symbols.csv` names -- and the fourth is the census's own
# `cluster_name` column, which `name_re()` reads its alternation from.
VOCABULARY_SOURCES = (
    (FUNCTIONS_CSV, "name"),
    (CLUSTERS_CSV, "cluster_name"),
    (REGISTERS_CSV, "name"),
    (SYMBOLS_CSV, "name"),
)

MULTI_SLUG = re.compile(r"\A[a-z0-9]+(?:-[a-z0-9]+)+\Z")


# --------------------------------------------------------------------------
# Reading. Nothing here validates a CSV's own columns; the four vocabulary
# sources are read for one name column each, and a column a file does not have
# reads as empty rather than raising, so a census regenerated before a column
# existed is a smaller vocabulary and not a crash.
# --------------------------------------------------------------------------

def names_of(path):
    """The `cluster_name` of every row of a names file, in file order.

    Not deduplicated, and not checked for uniqueness here either:
    `test_xdata_cluster_names.py::TheNamesFile` holds that, and a set would
    quietly turn R2's "is this name inside another" into "is this name seen
    twice", which is a different question with a different answer.
    """
    with open(path, newline="") as f:
        return [(r.get("cluster_name") or "").strip()
                for r in csv.DictReader(f)]


def vocabulary():
    """(identifiers, addresses) -- what a name may not collide with.

    The census's own `cluster_name` values are **subtracted** from the
    identifier set, which is the one step here that is not a plain read. Every
    name is by construction equal to its own row of `xdata-clusters.csv` -- the
    census carries the name the names file seeds -- so leaving them in makes
    R3's equality rule fire on all nine committed names and mean nothing at
    all. Name against name is R2's question, and R2 asks it over the rows of
    the names file itself.
    """
    found = set()
    for path, column in VOCABULARY_SOURCES:
        try:
            with open(path, newline="") as f:
                for row in csv.DictReader(f):
                    value = (row.get(column) or "").strip()
                    if value:
                        found.add(value)
        except FileNotFoundError:
            continue
    seeded = set()
    try:
        with open(CLUSTERS_CSV, newline="") as f:
            for row in csv.DictReader(f):
                value = (row.get("cluster_name") or "").strip()
                if value:
                    seeded.add(value)
    except FileNotFoundError:
        pass
    addresses = set()
    try:
        with open(REGISTERS_CSV, newline="") as f:
            addresses = {(r.get("addr") or "").strip() for r in csv.DictReader(f)}
    except FileNotFoundError:
        pass
    return found - seeded, addresses - {""}


def rel(path):
    """The path as a reader would name it, and as given when it is not in the
    tree -- a scratch names file `--names /tmp/...` points at is named by the
    argument that pointed at it, not by a walk up out of the repository."""
    short = os.path.relpath(path, EC)
    return path if short.startswith(os.pardir) else short


def words(name):
    """The name as one identifier: `-` and `_` are one separator, case aside.

    R3 and R4 are the same question asked of a `kebab-case` name and a
    `snake_case` identifier -- "is this the same words the tree already uses
    for the same thing?" -- and an EC identifier is spelled one way and a
    cluster name the other. Lowercased because the symbol half of the
    vocabulary is `UPPER_CASE` and `CHARGE_TARGET_MV_0` is the same three words
    as `charge-target`; R1 fixes the name itself to lowercase, so this is only
    ever folding the vocabulary's own spelling down to the name's.
    """
    return name.replace("-", "_").lower()


def prefixed_by(identifiers, name):
    """The identifiers of which the name is a `_`-delimited word prefix.

    Excludes an exact match, which is R3's question and is reported there, so a
    name that is a known identifier is one line rather than two.
    """
    want = words(name) + "_"
    return sorted(i for i in identifiers
                  if words(i) != words(name) and words(i).startswith(want))


# --------------------------------------------------------------------------
# The four rules. Each returns a list of `(name, what_would_pass)`, so
# `problems()` is the concatenation of four lists and no rule is a special case
# to the caller.
# --------------------------------------------------------------------------

def multi_slug(names):
    """R1: two or more `-`-separated slugs of `[a-z0-9]`.

    Fixing the separator is the point as much as the count is. A name that
    could spell the same words `charge-target` and `charge_target` is a name
    `name_re()` can match in two forms, and the two forms do not have to mean
    the same membership the second time one of them is typed.
    """
    return [(n, f"{n!r} is not a multi-slug: the shape is two or more "
              f"`-`-separated slugs of [a-z0-9] (`gate-block`, "
              f"`flag-pair-0442`) and not a single token, not `_`-separated, and "
              f"not an address as written") for n in names
            if not MULTI_SLUG.fullmatch(n)]


def inside_another_name(names):
    """R2: no name is a substring of another.

    `name_re()` sorts longest-first so `counter-sweep-06c6` cannot be read as
    `counter-sweep` inside it, which is a construction rather than a rule: it
    holds only because the sort is there, and nothing checks that the sort and
    the names file were written in the same decade. `level-block` is the shape
    this is for, refused alongside the `level-block-086x` that contains it.
    """
    return [(n, f"{n!r} is a substring of {other!r} in the same file, so "
              f"check_cluster_citations.py's name_re() keeps them apart by "
              f"sorting longest-first rather than by any rule; a name that is "
              f"not inside another would pass")
            for n in names
            for other in names
            if other != n and n in other]


def collides_with_a_known_token(names, identifiers, addresses):
    """R3: not an address, not a symbol, not a function, once normalised.

    Three sub-shapes, reported as one rule because a name is checked once and
    gets one line: it is the first of the three that applies that is named, and
    the other two would say the same thing about the same row.

    The containment arm reads the `0x` form only, and the module docstring says
    why at the length it needs: four of the nine committed names carry a bare
    four-hex slug that is a real address, so the bare-hex reading is red on
    nearly half the file this exists to protect.
    """
    out = []
    for n in names:
        lowered = n.lower()
        spelled = sorted(a for a in addresses if a.lower() == lowered)
        if spelled:
            out.append((n, f"{n!r} is the XDATA address {spelled[0]} spelled as a "
                          f"name, so a prose citation of the address is a "
                          f"citation of this cluster; a name that is not an "
                          f"address would pass"))
            continue
        carried = sorted(a for a in addresses
                         if a.lower().startswith("0x") and a.lower() in lowered)
        if carried:
            out.append((n, f"{n!r} carries the XDATA address {carried[0]} as a "
                          f"slug, which is the one form the checker's ADDRESS "
                          f"regex matches; a name that spells no `0x` address "
                          f"would pass"))
            continue
        same = sorted(i for i in identifiers if words(i) == words(n))
        if same:
            out.append((n, f"{n!r} normalises to {words(n)}, which is a name the "
                          f"census already uses ({same[0]}); a name that is not "
                          f"a function or symbol would pass"))
    return out


def prefixes_a_known_identifier(names, identifiers):
    """R4: not the `_`-delimited word prefix of a known identifier.

    The rule the issue's own example needs and its three named rules do not
    reach: `charge-target` passes R1 (two slugs), R2 (inside nothing committed)
    and R3 (not an address, not equal to any identifier), and is caught here by
    the four identifiers the tree already spells the same words as --
    `charge_target_update`, `charge_target_minus_r3_times_0a47`,
    `CHARGE_TARGET_MV_0` and `CHARGE_TARGET_MV_1`.
    """
    out = []
    for n in names:
        hits = prefixed_by(identifiers, n)
        if hits:
            # The three *shortest*, not the first three: an identifier a name
            # is a word prefix of is closest to the shortest of them, and that
            # is the one a reader wants to look at. The count is beside the
            # sample rather than inside it, so a truncated list never reads as
            # the whole of it. `gate` is the width this has to survive.
            near = sorted(hits, key=lambda i: (len(i), i))[:3]
            out.append((n, f"{n!r} normalises to {words(n)}, which is the word "
                          f"prefix of {len(hits)} identifier(s) the tree already "
                          f"uses ({', '.join(near)}"
                          f"{', ...' if len(hits) > len(near) else ''}); a name "
                          f"that is not a word prefix of one would pass"))
    return out


# --------------------------------------------------------------------------
# The refusal.
# --------------------------------------------------------------------------

def problems(names=None, identifiers=None, addresses=None):
    """[(name, what_would_pass)] for every rule every name trips.

    All four rules run and a name that trips two is two lines, not one: the
    rules are independent, and collapsing them to the first that fires would
    make a rule that has gone quiet indistinguishable from a name that only
    ever tripped that one. `names`, `identifiers` and `addresses` are
    parameters rather than reads of the committed files so a caller can hold
    the rules against a constructed set -- which is what
    `test_xdata_cluster_names.py::TheNamesShape` does, because a check that has
    only ever passed has not been shown capable of going red.
    """
    if names is None:
        names = names_of(NAMES_CSV)
    if identifiers is None or addresses is None:
        found, held = vocabulary()
        identifiers = found if identifiers is None else identifiers
        addresses = held if addresses is None else addresses
    return (multi_slug(names)
            + inside_another_name(names)
            + collides_with_a_known_token(names, identifiers, addresses)
            + prefixes_a_known_identifier(names, identifiers))


def main() -> int:
    ap = argparse.ArgumentParser(
        description="refuse a cluster name whose shape lets it read as a "
                    "citation in prose that only means the words")
    ap.add_argument("--names", default=NAMES_CSV,
                    help=f"names CSV to check (default: {NAMES_CSV})")
    args = ap.parse_args()

    names = names_of(args.names)
    identifiers, addresses = vocabulary()
    found = problems(names, identifiers, addresses)
    for name, why in found:
        print(f"{name}: {why}", file=sys.stderr)
    if found:
        print(f"{len(found)} cluster name(s) of {len(names)} in "
              f"{rel(args.names)} refused, against a vocabulary of "
              f"{len(identifiers)} identifier(s) and {len(addresses)} "
              f"address(es)", file=sys.stderr)
        return 1
    # Silent on the clean case. Nothing to report is not a finding, and a names
    # file with no problems is the state this exists to keep -- so the run that
    # finds nothing says nothing, and the caller is the line
    # `xdata_register_map.py --self-test` prints.
    return 0


if __name__ == "__main__":
    sys.exit(main())
