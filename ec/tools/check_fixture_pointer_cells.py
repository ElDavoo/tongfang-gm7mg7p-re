#!/usr/bin/env python3
"""Hold the call-graph fixture README's empty-cell claim to the CSVs beside it.

Issue #780 emptied six `evidence` cells in this fixture's two CSVs rather than
point them at a listing the real tree does not have, and wrote the six down in
the fixture's own `README.md` in the same edit. Both halves of that are
hand-kept and nothing held either. A reader who counts the cells the file's
own sentence describes finds twenty-three, not six, and the sentence is worded
so that its "so" presents the six as a count of them -- `CLAUDE.md`'s "assert
the claim, not the census" one level down. The correction is in
`docs/findings/fixture-empty-pointer-cells.md`; this is what holds the corrected
prose true.

**The derivation, and the claim, are different kinds of thing.** Which cells
carry no value is a function of two committed CSVs and no prose at all. Which
six of them #780 meant is a record of a decision, and there is no predicate in
either CSV that separates the six from the other seventeen: the write-up carries
the search that established that, over every column of both files, so the next
reader does not run it again. So the set and the kinds are derived here, the
addresses stay in the prose, and the three rules below are what hold one to the
other. No figure is hand-kept: a count of the tree is a value every emptied
cell moves, which is the lock `CLAUDE.md` names four times over.

**Which columns are pointer columns is structural, not an exemption list.** A
column qualifies when one of its cells names a path, read with `names_a_file()`
-- the same "has an extension" test `check_testdata_index.py` uses, over the
same `;`-separated tokens it uses, with one clause this file needs and that one
does not: a path has no spaces in it, and `ghidra-functions.csv`'s `comment`
cells are sentences that end in a period, which `splitext` alone reads as a
file whose extension is `.`. On the committed tree that leaves `evidence` and
`out_file` and nothing else: `also_in` holds program names (`bank0`/`bank1`),
and `name`, `comment`, `basis`, `type` and `size` are not paths. A fixture
directory carrying another pointer column is therefore covered with no edit
here, which is the same argument `check_testdata_index.py`'s self-indexed-
directory clause makes and its suite tests with a directory name the tool has
never seen.

**Three verdicts per cell, and none of them is "the file is not there."** A cell
carrying a value is `resolved` when this tool can read every one of its tokens
as a path and `unresolved` when one of them has a shape no path rule reads; a
cell carrying no value is `empty`, which is the finding this tool exists for and
is not an error by itself. Existence is deliberately not the question, and the
reason is measured: the fixture's two pointer columns are rooted at different
places -- `evidence` at the repository root, `out_file` at `ec/decompiled/` --
so answering needs a per-column base, which is the exemption list the clause
above exists to avoid, and ten of the 27 `out_file` values name a path that is
in neither place anyway. That is the condition
`docs/findings/testdata-index-evidence-column.md` records for pointing a check
at that column at all: a check that false-positives is worse than no check.
Answering against the real tree is `check_testdata_index.py`'s job and is
unchanged here, so between them the two cover the cell from both ends.

**The three kinds, in precedence order**, and each one's edge:

  * `synthetic` -- the address is carried by exactly one CSV in the fixture, and
    that CSV has no `seed_basis` column, so nothing in the fixture records how
    the row was seeded. `bank0,0EA3` is the one: a row of the decompilation
    record at an address `index.csv` has no row for, and #780's write-up calls
    it a synthetic row naming an address that is named nowhere. The clause
    needs the missing `seed_basis` column as much as the missing row, because
    `common,0D40` is equally uncorroborated by any other file and is *not*
    synthetic -- its own row says it was seeded by a transfer scan, which is a
    record of where it came from.
  * `documented` -- the fixture README's empty-cell paragraph names the
    address. This is prose, so it is the weakest evidence of the three and sits
    below `synthetic`, whose input is a column set rather than a sentence.
  * `transfer-seeded` -- the row's CSV carries a `seed_basis` column and this
    row reads `call-target`: the function is in the index because a transfer
    scan found a call to it, and the fixture has no listing of its own. The
    broadest of the three and the one that explains a class rather than a cell,
    which is why it is last.

  Anything left is `undocumented` and fails the run, which is the issue's own
  failure: a cell emptied in a later issue with no sentence beside it, on a row
  the transfer scan did not seed. A CSV with no `seed_basis` column and a
  pointer column in it lands there too, and says so, rather than having a rule
  invented for it.

**The README's empty-cell paragraph is located by shape, not by a line number.**
A block of non-blank lines outside a table, carrying the word `empty` in some
form and at least one backticked `0x` address, is that paragraph. The word is
matched as a stem because the file says "empty" and its write-ups say
"emptied", and the address requirement is what keeps a correction paragraph
*about* the empty cells from becoming a second one naming them. The addresses it
carries are the claim; the sentences that name them are printed beside every
`documented` entry, because that is where #780 wrote down why each one is empty
and re-deriving the reason here would be this tool guessing at a fixture.

**The reverse direction, because a claim can also be left behind.** An address
the paragraph names, whose pointer cells are all populated, is a finding: the
prose says the cell is empty and the CSVs do not. That is the #780 fix
explicitly declined -- repointing `bank0,0EA3` at the real `bank0/0EA2.asm`
fills a cell rather than emptying one, and a filled cell is not an empty one, so
no other rule here would report it -- and it is why a cell can be filled in as
well as emptied without the prose going stale.

**What this does not check, which is as much of the point:**

  * *Whether a cell carrying a value names a file that is there.* The verdicts
    above, and the reason they stop where they do.
  * *Whether an empty cell is the right answer.* This reports which cells carry
    no value and whether the README accounts for each. It has no opinion about
    `bank0,0EA3` needing one, which is #780's judgement and is left standing.
  * *The real tree's own indexes.* `ec/decompiled/index.csv` and
    `ec/annotations/ghidra-functions.csv` are a different owner, a far larger
    tree, and `pd,0x10BC`'s real `evidence` names three annotation documents
    rather than listings. Declined for the reason
    `docs/findings/testdata-index-evidence-column.md` gives.
  * *The reverse direction over listings.* A real `ec/decompiled/**` listing no
    cell names is `check_testdata_index.py`'s declared limit and is unchanged
    here; that write-up measures it at 2,711 files and 11 tokens.
  * *A column emptied in every cell.* The qualification rule above is what a
    fixture's `evidence` column is read by, and it needs one cell that names a
    path: the committed fixture's five populated cells are the only reason the
    other 22 are read at all. Empty every one and the column stops qualifying,
    its cells become invisible, and the run reaches nothing -- which it says,
    in the tallies and again as a finding, because the README's claim then has
    nothing behind it. What it cannot do is notice that a column used to be a
    pointer column and no longer is; the suite's own scratch corpus is built
    with a populated cell for the same reason, which is the second time that
    detail has turned out to be load-bearing.

**Nothing here reads a capture, an EC, or a laptop**, and nothing here reads a
file outside the fixture: three committed files, two CSVs and the markdown
beside them, with `open()`. A green run means those two CSVs and that README
agree with each other; it says nothing about whether any fixture is *correct*,
and an empty cell is reported as an empty cell -- "carries no value", never
"absent", the same calibration `ec/annotations/registers.yaml` carries for a
static scan.

Usage:
    python3 ec/tools/check_fixture_pointer_cells.py [--check]
"""
import argparse
import collections
import csv
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(HERE, os.pardir, os.pardir)
# The fixture this run reads, and the base a report's paths are made relative
# to. Both are globals rather than flags, for the reason
# `check_testdata_index.py` gives: `main()` has nothing to point a scratch tree
# at, and a `fixture=FIXTURE` default would bind at def-time and silently
# defeat the suite's patch. `REPO` is read only by `repo_relative()` --
# nothing here resolves a path, for the reason `verdict()` gives.
FIXTURE = os.path.join(HERE, "testdata", "call-graph")
README = "README.md"

# The two verdicts a pointer cell that carries a value is given, as strings
# because they are what a report prints and a test asserts against.
# `unresolved` is the calibration line made mechanical and never fails. Neither
# fails the run: the failures are an empty cell nothing accounts for and a named
# address with no empty cell behind it, which are judgements about the fixture
# rather than readings of a shape. The third verdict a cell can carry, `empty`,
# is the absence of a value rather than a reading of one, so it is the branch
# that builds an `Entry` and not a word this file compares against.
RESOLVED, UNRESOLVED = "resolved", "unresolved"

# The four kinds an empty cell is given, same reasoning. The first three are
# the three classes #780's write-up and this docstring name; the fourth is the
# residue, and it fails.
DOCUMENTED, SYNTHETIC = "documented", "synthetic"
TRANSFER_SEEDED, UNDOCUMENTED = "transfer-seeded", "undocumented"

# A backticked address, which is how the README spells one and how the CSVs do
# not. Requiring the backticks is what keeps a path, a flag or a `0x`-less hex
# token out of the claim: the fixture's tables quote `0x1400`/`0x1410` and
# `bank0,0EA2.asm`, and only the first is an address a paragraph is naming.
NAMED = re.compile(r"`0x([0-9a-fA-F]+)`")
# The word, as a stem, because the file says "empty" and every write-up about
# it says "emptied" or "empties"; a rule keyed on one spelling would be a
# vocabulary nobody would remember to keep in step.
EMPTIED = re.compile(r"\bempt", re.IGNORECASE)
# A sentence ends at a period followed by space. A period with no space after it
# is a dot in `ec/decompiled/…` or the end of the block, and treating either as
# a boundary would cut the one sentence that names the addresses in half.
SENTENCE = re.compile(r"(?<=\.)\s+")

# What one run found. The disagreement lists are lists and the rest are counts,
# for the reason `check_testdata_index.py` keeps them apart: a tally is a census
# of what the run read and a finding is a judgement about one item of it, and a
# namedtuple field that is sometimes the number and sometimes the things is the
# arithmetic bug waiting for the next field.
Result = collections.namedtuple(
    "Result",
    "csvs columns cells unresolved entries addresses named noempty")

# One empty pointer cell, with the kind derived for it and the reason that kind
# was derived: the README's own sentence for a `documented` one, and the rule
# that fired for the rest, so a report can print the reason beside the cell
# rather than sending a reader to work out why the kind is what it is. `addr` is
# the row's address as the CSV spells it, `value` the same address as an integer
# or None when the row carries none this tool can read, and `row` the row's
# scope-and-address identity the way the fixture's own write-up names it
# (`bank0,0EA3`).
Entry = collections.namedtuple("Entry", "csv column row addr value kind why")


def names_a_file(token):
    """Whether the token is spelled like a path rather than like prose.

    Restated from `check_testdata_index.py`'s function of the same name rather
    than imported: a new tool is a new file here (`CLAUDE.md`), and that file is
    #780's, a live conflict surface another branch may be holding. The extension
    is the test, and the dot-name test is on the last component, because
    `../grade.py` is a tool and `.gitignore` is not.

    **The whitespace clause is the one thing restated with a change, and it is
    here because of what a column is rather than what a table cell is.** The
    reference tool reads backticked tokens out of a markdown table, where a
    token is a path by construction; this reads a whole CSV column, and
    `ghidra-functions.csv`'s `comment` cells are sentences that end in a period,
    which `splitext` reads as a file whose extension is `.`. A path has no
    spaces and a sentence has many, so the test is on the token as a whole.
    """
    if any(character.isspace() for character in token):
        return False
    stem, extension = os.path.splitext(os.path.basename(token))
    return bool(extension) and not stem.startswith(".")


def as_address(text):
    """The address as an integer, or None when it is not one this tool reads.

    Also restated, and for the same reason. The `0x` prefix, the case of the
    digits and the padding are the three ways the README and the CSVs spell one
    address, and every one of them is live: `0x0D20` in the prose against `0D20`
    in `index.csv`. A string compare would put every documented address outside
    the set it is supposed to be a member of.
    """
    text = text.strip()
    if text[:2].lower() == "0x":
        text = text[2:]
    try:
        return int(text, 16)
    except ValueError:
        return None


def read_table(path):
    """(header, rows) for one CSV, with the blank trailing line dropped."""
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))
    return (rows[0] if rows else []), [row for row in rows[1:] if row]


def cell(row, index):
    """The `index`th cell of a row, or nothing for a row that stops short.

    A short row is a real shape rather than a broken one -- a trailing column
    dropped from the last line of a file a hand edited -- and reading it as an
    empty cell is the honest answer for a column this tool is reporting on.
    """
    return row[index].strip() if index < len(row) else ""


def tokens_of(value):
    """The pointers one cell names, `;`-separated and stripped.

    The separator is restated from `check_testdata_index.py` for its stated
    reason: the committed `bank0,0EA2` row names a listing and its `.c` side by
    side, and a cell read whole is a token no path rule can match.
    """
    return [piece.strip() for piece in value.split(";") if piece.strip()]


def pointer_columns(header, rows):
    """The columns of one CSV that point at a file, decided by what they hold.

    Structural, for the reason the docstring gives: a fixture carrying a
    pointer column this file has never seen is read with no edit here. The test
    is over a cell's `;`-separated tokens rather than over the cell, because the
    one multi-pointer cell in the committed tree is `;`-joined and a cell read
    whole has spaces in it. A column holding no path at all -- every cell empty,
    or every cell a program name -- is not a pointer column as far as this tool
    can read it, and the cell count the report prints is what makes that visible
    rather than green.
    """
    out = []
    for index, column in enumerate(header):
        if any(names_a_file(token) for row in rows
               for token in tokens_of(cell(row, index))):
            out.append((index, column))
    return out


def verdict(value):
    """(verdict, note) for one pointer cell that carries a value.

    The module docstring says why existence is not the question; what is left
    is whether the cell can be read as a path at all. `resolved` means every
    one of its tokens is one, `unresolved` means one of them has a shape no
    path rule reads -- "not resolved by this method", never "the file is
    absent", the line `ec/annotations/registers.yaml` carries and this tool
    repeats. A cell is as bad as its worst token, because a reader wants every
    half of a `;`-joined cell to be a path.
    """
    tokens = tokens_of(value)
    for token in tokens:
        if not names_a_file(token):
            return UNRESOLVED, token
    return RESOLVED, "; ".join(tokens)


def repo_relative(path):
    """Repository-relative, so a report can be pasted into an editor.

    A `relpath` over a path the caller already made relative resolves against
    the working directory instead, which turns a scratch tree's report into a
    chain of `..` out of an unrelated root. The base is the `REPO` global rather
    than a fresh `HERE/../..`, and the suite patches it the way it patches
    `FIXTURE`, so a run over a `tempfile` reports scratch-relative paths.
    """
    return os.path.relpath(path, REPO)


def documented(text):
    """{address: [the sentence naming it, ...]} for the README's claim.

    The block rule is the docstring's: a non-table paragraph carrying the word
    `empty` and at least one backticked address. Every sentence naming an
    address is kept rather than the first, so a later edit that splits the
    paragraph leaves the claim intact and the report showing both halves.
    """
    named = collections.defaultdict(list)
    for block in text.split("\n\n"):
        if block.startswith("|") or block.startswith("#"):
            continue
        addresses = {as_address(token) for token in NAMED.findall(block)}
        if not addresses or not EMPTIED.search(block):
            continue
        for sentence in SENTENCE.split(" ".join(block.split("\n"))):
            found = {as_address(token) for token in NAMED.findall(sentence)}
            for address in found & addresses:
                named[address].append(sentence.strip())
    return dict(named)


def seed_basis(header, row):
    """The row's `seed_basis`, or None when the CSV has no such column.

    Read by name because a position is right on the day it lands and wrong
    after the next column is added -- the same argument
    `check_testdata_index.py` makes for reading its own `evidence` column.
    None is not "not seeded": it is "this file records no seed basis", which is
    a fact about the CSV and lands the cell in `undocumented` with the reason
    attached rather than being guessed at.
    """
    if "seed_basis" not in header:
        return None
    return cell(row, header.index("seed_basis"))


def row_identity(header, row):
    """`scope,addr` when the CSV names a scope, else the one it has.

    The scope column is read by name over the two spellings the two committed
    CSVs use, `program` and `scope`, because `bank0,0EA3` is how the fixture's
    own write-up and `call_graph.py` both name a row and a report that says
    `0EA3` sends the reader looking in the wrong file first. A CSV with neither
    column is named by its address alone, and one with no `addr` column is
    named by its scope -- a trailing comma on a row with no address in it is a
    punctuation mistake, not an identity.
    """
    address = cell(row, header.index("addr")) if "addr" in header else ""
    scope = next((cell(row, header.index(column))
                  for column in ("program", "scope") if column in header), None)
    if scope is None:
        return address
    return f"{scope},{address}" if address else scope


def kind_of(header, row, value, named, carried):
    """(kind, why) for one empty cell, by the precedence the docstring gives.

    `carried` is the set of CSV names that have a row at `value`, so the
    `synthetic` clause can ask whether anything else in the fixture corroborates
    the address without re-reading the tables. `synthetic` is first because it
    is the only one of the three that is read off a column set rather than off a
    sentence, and `documented` is prose: a row nothing else in the fixture
    mentions is a fact about the files whether or not the README says so.
    """
    basis = seed_basis(header, row)
    if value is not None and len(carried) == 1 and basis is None:
        return (SYNTHETIC,
                "no other CSV in the fixture carries a row at this address and "
                "this one records no `seed_basis`, so nothing says where the "
                "row came from")
    if value is not None and value in named:
        return DOCUMENTED, " ".join(named[value])
    if basis == "call-target":
        return (TRANSFER_SEEDED,
                "`seed_basis=call-target`: the row is here because a transfer "
                "scan found a call to it, and the fixture has no listing of "
                "its own")
    if basis is None:
        return (UNDOCUMENTED,
                "this CSV has no `seed_basis` column, so nothing records why "
                "the cell carries no value")
    return (UNDOCUMENTED,
            f"`seed_basis={basis or '(empty)'}` is not a reason this tool "
            "reads, and the README's empty-cell paragraph does not name the "
            "address")


def check(fixture=None):
    """A `Result` for one fixture directory.

    `fixture` is the committed path by default, defaulted at call time so a
    caller that patches the global and a caller that passes the argument are the
    same thing -- a `fixture=FIXTURE` default would bind at def-time and
    silently defeat the suite's patch. There is no `repo` parameter because
    nothing here resolves a path against a base; see `verdict()`.

    The CSVs are every `*.csv` in the directory rather than the two the
    committed fixture has, for the same reason the pointer-column rule is
    structural: the next fixture carrying a CSV is read with no edit here.
    """
    if fixture is None:
        fixture = FIXTURE
    with open(os.path.join(fixture, README), encoding="utf-8") as f:
        named = documented(f.read())

    tables, order = {}, []
    for name in sorted(os.listdir(fixture)):
        if name.endswith(".csv") and os.path.isfile(
                os.path.join(fixture, name)):
            tables[name] = read_table(os.path.join(fixture, name))
            order.append(name)

    # Which CSVs carry a row at each address, so the `synthetic` clause is a
    # lookup rather than a second pass over both tables.
    carried = collections.defaultdict(set)
    for name, (header, rows) in tables.items():
        if "addr" not in header:
            continue
        index = header.index("addr")
        for row in rows:
            value = as_address(cell(row, index))
            if value is not None:
                carried[value].add(name)

    columns = cells = 0
    unresolved, entries = [], []
    for name in order:
        header, rows = tables[name]
        for index, column in pointer_columns(header, rows):
            columns += 1
            for row in rows:
                value = cell(row, index)
                cells += 1
                if value:
                    found, note = verdict(value)
                    if found == UNRESOLVED:
                        unresolved.append((repo_relative(os.path.join(fixture,
                                                                      name)),
                                            column, row_identity(header, row),
                                            note))
                    continue
                # The address as the row spells it and as the integer it is,
                # computed once: `Entry` carries both because a report should
                # quote the row and a set should hold the value.
                spelling = (cell(row, header.index("addr"))
                            if "addr" in header else "")
                value = as_address(spelling)
                kind, why = kind_of(header, row, value, named,
                                    carried.get(value, set()))
                entries.append(Entry(repo_relative(os.path.join(fixture, name)),
                                     column, row_identity(header, row), spelling,
                                     value, kind, why))
    addresses = {entry.value for entry in entries}

    # The reverse direction. A named address with no empty cell behind it is the
    # prose left behind by a cell that was filled in, which the cell-by-cell
    # rules above cannot see because a filled-in cell now carries a value.
    noempty = [(address, " ".join(sentences))
               for address, sentences in sorted(named.items())
               if address not in addresses]
    if not named:
        # Nothing to hold the derivation to. Reported rather than passed, for
        # the reason the tallies are printed whether or not they found anything:
        # a run that checked nothing and a run that found nothing look the same
        # from the exit code alone.
        noempty.append((None, "no paragraph in the fixture README names an "
                              "address for a cell carrying no value, so there "
                              "is no claim here to hold the derivation to"))

    return Result(order, columns, cells, unresolved, entries, len(addresses),
                  len(named), noempty)


def report(result):
    """Print the derivation and the findings, and return how many findings.

    The derivation goes to stdout and the findings to stderr, so a reader can
    paste the first and see the second in a runner's log. An `undocumented`
    entry is in both, which is the same double the reference tool prints: the
    tally is a census of what the run read and the finding is a judgement about
    one of them.

    The header line reads the `FIXTURE` global rather than the fixture the
    `Result` was derived from, for the reason `check_testdata_index.py`'s
    `report()` prints its `INDEX` global: a run pointed at a scratch tree has
    to have it patched too, or the report names the committed fixture above a
    derivation taken from a `tempfile`.
    """
    print(f"pointer cells in {repo_relative(os.path.join(FIXTURE, README))}, "
          f"derived from the CSVs beside it")
    # Grouped by address rather than printed one cell at a time, because an
    # address with a cell in both CSVs is one entry in the claim and two lines
    # in the files, and printing the cells flat would make the reader do the
    # grouping to see the set the tallies count. Sorted by address value, so two
    # runs print in the same order.
    def by_address(text):
        """(address value, spelling), so the report is in address order.

        The value rather than the string because the CSVs spell `0D40` and
        `DEAD` and a string sort puts the second first, and the spelling as the
        tiebreak because two rows may spell one address differently.
        """
        return as_address(text) or 0, text

    groups = collections.OrderedDict()
    for entry in result.entries:
        groups.setdefault(entry.addr, []).append(entry)
    for address in sorted(groups, key=by_address):
        group = groups[address]
        print(f"  {address}  {group[0].kind}")
        for entry in group:
            print(f"      {entry.csv}  {entry.column}  {entry.row}")
        if group[0].kind == DOCUMENTED:
            print(f"      README.md: \"{group[0].why}\"")

    for where, column, row, note in result.unresolved:
        print(f"{where}: the `{column}` cell at {row} names `{note}`, which is "
              f"not shaped like a path -- not resolved by this method, not "
              f"absent", file=sys.stderr)
    for entry in result.entries:
        if entry.kind == UNDOCUMENTED:
            print(f"{entry.csv}: the `{entry.column}` cell at {entry.row} "
                  f"carries no value and nothing accounts for it -- "
                  f"{entry.why}", file=sys.stderr)
    for address, sentence in result.noempty:
        if address is None:
            print(f"the fixture README: {sentence}", file=sys.stderr)
            continue
        print(f"the fixture README names `0x{address:04X}` for a cell carrying "
              f"no value, and no pointer cell in the CSVs is empty for it: "
              f"\"{sentence}\"", file=sys.stderr)

    empty = len(result.entries)
    findings = (sum(1 for e in result.entries if e.kind == UNDOCUMENTED)
                + len(result.noempty))
    if findings:
        print(f"{findings} disagreement(s) between the fixture's CSVs and the "
              f"README beside them", file=sys.stderr)
    kinds = collections.Counter(group[0].kind for group in groups.values())
    print(f"{len(result.csvs)} fixture CSV(s), {result.columns} pointer "
          f"column(s), {result.cells} pointer cell(s): "
          f"{result.cells - empty - len(result.unresolved)} resolved, "
          f"{len(result.unresolved)} unresolved, {empty} empty")
    print(f"{empty} empty cell(s), {result.addresses} address(es): "
          f"{kinds[DOCUMENTED]} documented, {kinds[SYNTHETIC]} synthetic, "
          f"{kinds[TRANSFER_SEEDED]} transfer-seeded, "
          f"{kinds[UNDOCUMENTED]} undocumented")
    print(f"{result.named} named address(es), "
          f"{result.named - len(result.noempty)} of them empty here")
    return findings


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    # Accepted and not branched on, for the reason `check_testdata_index.py`
    # gives: the check is the whole of what this tool does, so `--check` is the
    # default and the flag is a gate's spelling of it.
    ap.add_argument("--check", action="store_true",
                    help="hold the fixture's README to the CSVs beside it "
                         "(the default, and the gate's entry point)")
    ap.parse_args()
    return 1 if report(check(FIXTURE)) else 0


if __name__ == "__main__":
    sys.exit(main())
