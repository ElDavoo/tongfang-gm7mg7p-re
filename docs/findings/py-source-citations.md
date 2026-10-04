# The committed Python sources' line citations into one tool, and a checker that holds them

# The finding

`ec/tools/xdata_register_map.py` is a large file that is edited often, and the
committed Python sources that cite into it were citing a file that had since
moved under them. The population was measured on **`ad595588`** — the command
below is what measures it — and **every citation in it named the wrong code**.
Not one was low by an offset and not one resolved to the statement it was about:

| citing site | cited | what is on that line now | the code the sentence names | now |
|---|---|---|---|---|
| `test_xdata_cluster_names.py`'s `guard_off()` | `:263` | a blank line; the lines above it are `--map`'s docstring on `cluster_id` | `ap.add_argument("--no-eq-guard", ...)` | `:4481` |
| `test_xdata_register_map.py`'s `dispatch_names()` | `:3634`, `:3637` | a `--self-test` comment and the `check(...)` call for the counter sweep | the `--thresholds` and `--floors` `default=list(...)` in `main()` | `:4472`, `:4475` |
| `test_xdata_register_map.py`'s `test_the_defaults_still_point_into_the_committed_tree` | `:3677-3680`, `:3687-3697` | an f-string continuation inside a `--self-test` sweep record, and the `direction_invariant(...)` call with its comment | the two committed-output refusals' `ap.error(...)` reasons | `:4521`, `:4541` |
| `test_xdata_guard_off_row_join.py`'s `test_the_key_moving_rows_sit_in_exactly_the_moved_keys` | `:2600-2610` | a dict of one cluster's fields in `cluster_rows_build()`, `"shared_functions"` through `"co_reading_dominant"` | `cluster_key()` — the content hash of program plus sorted members | `:1997` |
| `inc_dptr_sites.py`'s module docstring | `:2241-2249` | `parent[x] = parent[parent[x]]` in the union-find `find()` inside `components()` | `scan()`'s `a`/`a+1` pair fold | `:1861` |
| `test_xdata_cluster_names.py`'s `TheExportOwnershipClusters` | `:4347-4354` | `shared = sorted(cid for cid, n in claimed.items() if n > 1)` in `print_carry()` | the after-census built in-process, `own_map = load_ownership()` | `:3794` |

The citing site is named by its function or class rather than by a line, per
`CLAUDE.md`: a `file:NNN` into a source that other pull requests also edit is
true only until the next merge grows it. The *cited* numbers are the finding and
are stated, because they are a property of a named tree; the checker holds each
one to the line its code is on, so a stale row is a red run rather than a
sentence that reads correctly.

A `:NNN` that resolves to a different statement is not a broken link. It is a
sentence that reads exactly as well with the wrong number as with the right one,
nothing in the tree is red over it, and a reader following it lands somewhere
else and has no way to know. Each row above was produced by running the checker
in this change; before it existed, each was a `grep -n` over one committed file.

The commands that measure the population, on any tree:

```sh
grep -rn 'xdata_register_map\.py:[0-9]' --include='*.py' . \
  | grep -v '^./ec/tools/xdata_register_map.py:'
python3 ec/tools/check_py_citations.py
```

# Why the first row matters most

`test_xdata_cluster_names.py`'s `guard_off()` docstring documents **how the
guard-off census is actually built** — the run behind
`docs/findings/xdata-06c2-06db-timers.md` §6a, §4.4's whole 439 → 445
derivation, and `xdata-4-4-identity-rederivation.md`. It reads: the committed
tool run with `--no-eq-guard`, "which is the switch that *re-runs the census
with the `==` rejection turned off*". The switch's `add_argument` is at `:4481`;
the quoted phrase is the tool's own module docstring at `:289`. `:263` was
`--map`'s paragraph about `cluster_id`. So the suite whose docstring is the
recipe for the guard-off census sent a re-deriver to a paragraph that never
declared the flag, and the recipe's whole point is that a future reader can
re-run the measurement from the committed tree without a commit pointer.

Note the two-line structure of the correction. The quoted phrase and the flag
are in different places, and only one of them is what the sentence is *for*.
Re-pointing the citation at `:289` would have made it true-looking and wrong in
the other direction; the docstring now says which is which.

# The controls had decayed too, which is the argument for the checker

The issue this change closes offered two citations as controls — sites a sweep
must not "fix", because they were already right. **On `ad595588` neither was
right any more.** `TheExportOwnershipClusters` docstring's `:4347-4354` *was*
the after-census build when the issue's sweep ran; it is `print_carry()`'s
stderr tail now, because `xdata_register_map.py` got *shorter* between the two
trees — `git diff --stat 7ce9f6c HEAD -- ec/tools/xdata_register_map.py` is
where that shows. So a citation that was right decays exactly like one that was
wrong, and nothing but a checker would have said so.

That is the whole reason the durable half is a checker and not a corrected
table. A table is right once; a checker is right until the next edit. The
negative case the suite asserts is the issue's own done test: insert one line
above an anchor in a scratch copy of `xdata_register_map.py`, and a cited
number in a **test** source goes red.

# What is declined, and why that is a count and not a note

Some further `xdata_register_map.py:NNN` sites are in committed `*.py` and are
**not** claims about the code:

- `ec/tools/test_check_doc_figure_pins.py` — literals in `test_a_file_path_in_the_cell_is_not_a_figure`
  and `test_an_unheld_row_naming_a_pin_is_reported`, inside that suite's own
  `TABLE` and `verdicts_of()` input. A fixture's literal is the checker's
  expectation, not a claim about the line it names.
- `ec/tools/check_eq_guard_citations.py` — an illustrative sentence in that
  tool's `POINTER` comment, which spells the citation two ways to say they are
  one claim.

The checker **declines and counts** these rather than skipping them silently, so
"checked nothing" and "found nothing" cannot read alike from the summary line,
and so a reader can tell a claim from a fixture by whether a locator declared
it. Both files are in `CITATIONS` with an empty locator list precisely so their
sites come out *declined* rather than unexamined.

# Why this is not a wider `CITATIONS` in `check_eq_guard_citations.py`

The issue offered two ways to hold the class: widen the sibling's `CITATIONS`,
or write the census down as a committed table. Neither is what this does, and
the reason is the tree rather than a preference.

Most of these citations are not about the `--no-eq-guard` mechanism at all. The
pair fold is a claim about `scan()`, the `list(...)` defaults are about
`main()`'s argparse, and `cluster_key()` is about the clustering. Holding them
in a tool whose declared identity is *"the `--no-eq-guard` mechanism's own
pins"* would mean either putting a different mechanism's claims in a tool about
this one, or holding unrelated claims under `--no-eq-guard` anchors — which is
precisely the "a number that resolves to a different thing" defect that tool
exists to catch. It would also mean editing the sibling and its suite, both
shared files with pull requests in flight.

So: **a new tool in a new file, with a new suite in a new file**, per
`CLAUDE.md`'s "a new tool is a new file, not another mode bolted onto an
existing one". The sibling's `CITATIONS` and its `TREE` are untouched, and the
decline is recorded in the new tool's docstring so the next reader does not
re-litigate it.

# Scope, deliberately

This is one population: hand-written line citations into one tool, from
committed Python files. It does not touch the wider `.py:NNN` census, and it
does not re-open any of it. #868 owns `xdata-086x-dispatch.md:286-288` and
states that its fix needs the general tool; #869 owns the files citing a
generated CSV by line outside `check_citation_lines.py`'s `ROW_SCOPE`; #870 owns
the pointers in `XDATA_0860`'s 2026-09-24 block; #1050 is the open question of
whether the supersession vocabulary has been counted over the wider class at
all.

Nothing here is a claim about the EC, the firmware, or any register's behaviour.
Every number is a `grep` over a committed text file, and the tool opens no
image, no CSV and no Ghidra project. No hardware and no Windows: no live run is
needed, planned, or implied.

# Where the numbers came from, and what would falsify this

Every figure in the table is a property of `ad595588`, named as `TREE` in the
tool and printed in its failure text. The plan this work was built from measured
on `7ce9f6c`, and every one of its anchors had since moved.

The issue's own proposed corrections were stale in the same way, which is worth
recording because transcribing them would have landed fresh wrong pins — the
defect this write-up is about, one generation down. Of the numbers it proposed
for the `list(...)` defaults and the two refusals, `:4546` and `:4578` are a
`--no-writer-axis` comment and a blank line on this tree, `:4985` and `:5007`
are both blank lines, and the `:2367` it gave for the pair fold is inside a
comment about byte order. `sed -n '4546p;4578p;4985p;5007p;2367p'
ec/tools/xdata_register_map.py` prints them.

A number here is falsified by any of: the checker going red (it re-derives
every anchor from the tool's own source on every run); a locator that stops
matching because its sentence was reworded (reported, not passed); or an anchor
that goes missing or ambiguous (a **stale declaration**, reported as such and
never as an absence — `CLAUDE.md`'s rule, and `ec/annotations/registers.yaml`'s
own caveat on the same point).

# Follow-ups this opens

- **The gate is prepared, not landed.** `docs/ci/agent-gates-py-source-citations.patch`
  wires the checker into `.github/scripts/agent-gates.sh`, on the convention
  `docs/ci/agent-gates-findings-frozen.patch` sets: that file is copied from the
  `agent-pipeline` template and this branch's push token has no `workflow`
  scope, so editing it fails at the end of a pull request rather than at the
  start of one. A human lands it with `git apply`.
  **Both ends of that patch were placed by measurement, not by picking a spot.**
  `.github/scripts/agent-gates.sh` is the most contended file in the repository
  — every line of its `gate` list, all of `check_ghidra_tooling()`'s body and
  all of `check_doc_links()`'s is some prepared patch's hunk context — so
  sweeping every (definition site, call site) pair against what
  `tools/test_agent_gates_patches.py` requires of a prepared patch is what found
  the pair that compose. That suite now holds this patch in its `PATCHES` list,
  so the composition is proved rather than asserted.
- **The population is declared, not discovered.** A further site in a declaring
  file is declined and counted rather than held, which is the point at which this
  either grows a locator or earns its own tool. Whether the *other* committed
  `.py` files — `windows/tools/`, `bios/tools/`, the root `tools/` — carry
  citations of the same shape is not measured here and is the open question
  #1050 is about.
- **Some locators name a bare `:NNN`** the sentence writes after a full one, the
  corpus's own shorthand. They are declared separately from their partners
  because they are separate claims, and a sweep that rewrote a sentence to drop
  the shorthand would find those locators missing and go red, which is the right
  answer and worth knowing before it happens.