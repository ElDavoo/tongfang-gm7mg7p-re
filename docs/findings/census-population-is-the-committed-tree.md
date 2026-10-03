# The census of `test_*.py:NNN` was counting a directory, and a directory is not this repository (issue #916)

(2026-10-03. Static reading of committed files plus two runs of
`ec/tools/census_test_line_pins.py` against this tree and against a working tree
carrying untracked files. No image is opened, no register is read back, and no
laptop, EC or Windows machine is involved: this is a census of text about text,
the same framing as [`doc-figure-pin-audit.md`](doc-figure-pin-audit.md) and
[`test-line-pin-census.md`](test-line-pin-census.md). **No figure of the
repository's own text is stated below** — the two denominators the change is
about are properties, and the command that prints them is named where a reader
would want them.)

## The claim

**`census_test_line_pins.py` published its two denominators as measurements of
this repository while computing them from a filesystem walk, so any untracked
file in the working tree moved a figure that a committed write-up quotes.** One
walk was serving two jobs: resolving a pin against the tree the tool is running
in, which is right, and *counting* that tree, which is not — because the count is
quoted in `test-line-pin-census.md` and the point of quoting it is that a reader
re-running the command gets the same number.

This is the same defect in a different dress from
[`no-append-logs.md`](no-append-logs.md): a figure that every merge has to
re-derive is a figure nobody re-derives correctly, and the reason it drifted
here rather than there is that the drift was *invisible*. The walk and
`git ls-files` agree on a clean checkout, and CI has a clean checkout.

## The defect, reproduced

Drop a markdown file carrying a citation into a test file into a directory the
walk does not prune, and **the markdown denominator moves**, with no commit
anywhere:

```console
$ mkdir -p scratch && printf 'see `ec/tools/test_census_test_line_pins.py:NNN`\n' > scratch/n.md
$ python3 ec/tools/census_test_line_pins.py | sed -n '1p;4p'
$ rm -rf scratch
```

**One of the two denominators, not both, and which one is not a matter of
degree.** Each denominator counts files of its own kind, so each moves only from
an untracked file of that kind: a dropped markdown file moves the markdown
denominator and cannot move the test-file denominator, because nothing about a
`.md` adds a `test_*.py` to the population, and an untracked `test_*.py` moves
the test-file denominator and leaves the markdown one where it was. Measured on
this tree against the pre-change tool, that is the whole of what the block above
does and does not do:

- the markdown denominator reads one higher with `scratch/n.md` present than
  without it;
- the test-file denominator reads the same either way — *not moved by this
  method*, rather than immune, since the untracked `test_*.py` above is what
  moves it;
- the record count is unmoved too, and stays unmoved unless the citation carries
  a real line number. `NNN` is a placeholder the reader substitutes: the census
  reads a citation, so a file carrying the literal `NNN` is a markdown file and
  nothing more. Which line the substitution names is not the point — what makes
  the record count move is that the file carries a *resolvable* citation at all.

A real line number is left out of this block on purpose, because a write-up that
demonstrated the defect with a live one would add a record to the census that
the per-pin table has no row for. A reader who substitutes one sees the record
count move as well, and still sees the test-file denominator where it was.

`scratch/` is one of the directories this repository's `.gitignore` names, and
the same drop under a dot-directory the prune list does not name — `.claude-pr/`,
which is the directory #916's own reproduction used — moved the markdown
denominator identically. Under `.claude/` it did not move at all, because
`PRUNED` already names that one; that is the narrowness of the old rule, and it
is why the two cases in the suite are a named directory and a dot-directory
rather than two dotted ones.

No figure from that run is transcribed here, for the reason the header gives.
The pair of commands *is* the reproduction, and what it prints is a function of
the tree the reader is standing in — including any scratch file they have open in
another window, which is the defect. `read` now names the reading that produced
it, so a reader can tell which of the two they are looking at without reading
the tool.

**Why it was never caught, stated so it is not mistaken for a claim about other
trees.** On a clean checkout the walk and `git ls-files` return the same set —
verified on this tree, where the two agree for both denominators. That is the
defect's whole hiding place, and it is also why the one case that holds the
denominators cannot be the case that guards the split. It is *not* a claim that
they agree everywhere: the reproduction above is a counterexample on this tree,
one directory away.

## The two readings, and which is which

`population()` is now the one place the census decides what its corpus is, and
it returns the paths *and* the sentence naming where they came from.

| root | reading | what the figures are |
|---|---|---|
| the top of a work tree | `git ls-files`, then the `PRUNED` components dropped | a measurement of **this repository** |
| anything else | today's walk, unchanged | a measurement of **that tree**, and the run says so |

The second row covers a tempdir, a copy of the repository, a subdirectory of a
work tree, and a machine with no `git` on `PATH`. All four are real: the suite's
own fixtures are tempdirs, and `test-line-pin-census.md` staged a copy to get
reproducible figures at all.

**The committed reading is the default, not because a walk is wrong but because
the run's numbers are published as measurements of this repository.** A walk
counts whatever is in the directory it stands in — an untracked scratch page, a
`git worktree` of this repository under `.claude/` (which is why `.claude/` was
already pruned, and which a walk can only exclude by name), another clone's
checkout, a build artifact. None of those is a claim about the tree this
repository has.

**The walk survives, and the subdirectory case is the reason it is not just "use
git".** `git -C ec/tools rev-parse --show-toplevel` *succeeds* and answers with
the repository's top, so a check that only asked whether it succeeded would
census the whole repository from a subdirectory and report the result as that
subdirectory's — the same defect, one level up. The tool therefore compares
`--show-toplevel` against the root it was given, as realpaths, and falls back
when they differ. `REPO` is built out of `__file__` with `os.pardir` and is not
the same *string* git would answer with, which is why the comparison is on
realpaths rather than on the two strings.

**Why `git ls-files` and not a longer exclusion list.** The scratch directories
this repository actually uses are named, not dotted: `.gitignore` lists `/tmp/`,
`/out/` and `/scratch/`, and a rule that pruned dot-directories would have caught
the dot-directory case and passed the named one. An exclusion list is a guess at
the names; the index is the answer.

## What the rule does not claim

- **A file that is tracked but listed in `.gitignore` is still in the
  population.** `git ls-files` is the index, not the working directory. Stating
  this matters because without it "the committed tree" reads as "the clean
  tree", which is a different and much weaker claim — and one that would put the
  population at the mercy of whatever happens to be untracked.
- **`PRUNED` currently removes nothing on the committed reading.** Checked
  against this tree: `git ls-files` reports no committed markdown and no
  committed `test_*.py` under `vendor/`, and nothing at all under `.claude/`.
  That is what is true *of this tree today*, not a property of the rule — a
  future `git add -f` of a vendored page would make it do something. It is
  applied on both readings so the constant means the same thing either way, and
  so the `read` line's `excluding …` half is a statement about the census rather
  than about the source.
- **A pin into an untracked file is now `unresolved-path`,** with the same "not
  read by this method" caveat every other negative here carries. That is the
  intended consequence: a citation into a file the repository does not carry is
  not a claim about this repository. It is also a *behaviour change* for anyone
  running the tool over a working tree mid-edit, which is why the run names its
  reading.
- **The census is still a census and not a check.** Nothing here makes it fail
  on drift, and the split changes no exit code.

## The denominators are held as claims, not as numerals

Both are held in `test_census_test_line_pins.py`, and neither is held as a
number. Each case computes the expected set with `git ls-files` *in the test* and
compares the tool's population against it, minus `SELF_DOC` and the pruned
components.

That is deliberate and it is the reading of "held by cases" that this repository
can afford. A literal — `assertEqual(<N>, len(markdown(REPO)))` — is a value
every merge that lands a write-up has to edit, and two branches bumping it from
different bases is a merge conflict; that is `no-append-logs.md`'s first case and
CLAUDE.md's "No totals of the repository's own text". The claim form holds the
denominator without a numeral anyone has to bump. Its limit is stated in the
case's own comment: on a clean checkout the walk answers it identically, so it
holds the denominator rather than guarding the split, and the cases that guard
the split are the ones run on trees the walk gets wrong.

## The other populations in the tree, named rather than fixed

There is no single answer in the tree for "which files does this tool's
population mean", and this change makes **the census's** answer written down and
explicit rather than making the tree consistent. Two sibling tools answer the
same question differently, and one consumer now sits beside the census's
answer:

- `measure_mark_provenance.py`'s `all_python_files()` walks the repository
  pruning only `(".git", "__pycache__")` — not `vendor/`, not `.claude/`. It
  measures which Python files carry a MARK row, so an untracked scratch script
  can enter that set too, by the same mechanism.
- `check_citation_lines.py` names its two markdown files outright and walks
  nothing, so it is not exposed to this at all; it is a third answer rather than
  a third instance of the same one.
- `check_pin_table_rows.py` reconciles the per-pin table and calls
  `census.walk(root, "")` for its own whole-tree index of *citing* markdown
  paths, beside the census's own population for the pins. The two now answer
  slightly different questions for a citing path: the census will not resolve a
  pin into an untracked page, and the table's index will still say the page is
  present. That divergence is deliberate in the narrow sense that the table is
  checking the tree's contents rather than the census's corpus, and it is worth
  a reader knowing about.

Unifying them is a different change with a different blast radius, and it is
recorded here rather than done. What this change removes is the *absence* of an
answer for the tool whose figures are published.

## What was left out, and why

- **No `--root` flag.** The module-level `REPO` already is the root the tool is
  given, and the suite drives it by patching that constant. A flag would be a new
  mode on an existing tool for no behaviour the constant does not already
  provide.
- **No gate, and no `.github/` edit.** The census is still not in
  `agent-gates.sh` and cannot be from an agent branch: the plan stage's push token
  has no `workflow` scope. That standing is prose plus
  `test_the_tool_is_not_in_the_cheap_gate`, and it is unchanged here.
- **Nothing was re-derived in `test-line-pin-census.md`** beyond the console
  block and the note beside it, both of which the change makes false rather than
  merely stale. The dated per-merge blocks there are records of the trees they
  were measured on and stay written where they were measured
  ([`../findings.md`](../findings.md) §4a-4d); re-deriving them is the trap
  `no-append-logs.md` is about.
- **No figure in this file is a count of the repository's own text**, so none of
  it goes stale on the next write-up that lands.
