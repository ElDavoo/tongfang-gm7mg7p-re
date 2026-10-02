# The annotation CSVs a tool byte-compares are checkout-stable, per file

`.gitattributes` now covers every committed CSV a tool's `--check` compares
**byte for byte**, so a `core.autocrlf=true` Windows checkout can no longer fail
the per-commit gate for a contributor who did nothing wrong. The detector stays;
only the cause goes.

Every figure below was measured on the tree this change was built against, and
the commands are given so a reader can re-derive rather than trust. Two of the
figures in the issue that asked for this work were wrong, and they are corrected
here rather than quietly overwritten — see [What the issue got
right](#what-the-issue-got-right-and-what-it-did-not).

## The hazard, in the file's own terms

`ec/tools/call_graph.py`'s `check_table()` compares the committed table's bytes
against a freshly generated one and exits 1 on any difference. Its docstring
named the cause it was defending against: git's default `core.autocrlf=true`
rewrites LF to CRLF on a Windows checkout, so a table that is correct in the
repository arrives in the worktree with different bytes and `--check` reports a
difference nobody introduced.

The file's own precedent for this is the block covering the decompiled `.c`
trees, and its own warning at `:39-41` is why the answer here is not `binary`:
marking a file binary also disables the CRLF normalisation git applies to text
on the way **in**, which is a second and independent way for the same comparison
to stop matching.

## Which of `call_graph.py`'s three inputs are newline-sensitive

Measured, not assumed, by CRLF-ifying each input in `/tmp` — committed bytes
rewritten, repository untouched — and driving the real `--check` code path
through `call_graph.py`'s own functions:

| input | CRLF checkout | verdict |
|---|---|---|
| `ec/annotations/call-graph-callees.csv` | `--check` returns **1** | **sensitive** — the output table, compared as bytes |
| `ec/decompiled/index.csv` | recomputed table byte-identical | **absorbs** — no field carries an embedded newline |
| `ec/annotations/ghidra-functions.csv` | recomputed table byte-identical | **absorbs the line terminator, not the quoted field** |

The third row is the careful one. `csv.DictReader` under `newline=""` strips a
CR that *terminates* a line, so ordinary rows survive; it does **not** touch a
CR *inside* a quoted field. `ghidra-functions.csv` has exactly one such field —
`bank0/0EA2`'s `comment` carries an embedded blank line, and a CRLF checkout
turns its `\n\n` into `\r\n\r\n`, changing the parsed value by two characters:

```
LF   ...fixed period and a sensor wait.\n\n(An earlier reading of this comment sa
CRLF ...fixed period and a sensor wait.\r\n\r\n(An earlier reading of this comment
```

For `call_graph.py` the rendered table came out byte-identical anyway. That is a
measured coincidence for this one tool and this one file — the comment's
embedded newline reaches the census only through fields this tool does not
render — and it is **not** a property of the format. A tool that rendered that
column would see the difference. This is written as a per-tool, per-file
measurement rather than as "CSV absorbs CRLF", because the second reading is the
one that would mislead the next tool.

Both other inputs absorb for the ordinary reason: `index.csv` has no embedded
newline anywhere, so nothing survives translation to change a rendered byte.

## The covering set is wider than the minimum

Reading each tool's `--check` arm rather than assuming one tool's shape, the
byte-compared tables are:

| tool | table it byte-compares |
|---|---|
| `call_graph.py` | `ec/annotations/call-graph-callees.csv` |
| `citation_gap_scan.py` | `ec/ghidra/gap-citation-scan.csv` |
| `task_call_table.py` | `ec/annotations/task-call-table.csv` |
| `dsdt_ec_fields.py` | `ec/annotations/dsdt-ecmg-fields.csv` |
| `bucket_c_codemap.py` | `ec/annotations/bucket-c-codemap.csv` |
| `check_site_resolution.py` | `ec/annotations/site-resolution.csv` |
| `fan_table_defaults.py` | `ec/annotations/fan-table-defaults.csv` |
| `xdata_register_map.py` | `ec/annotations/xdata-registers.csv`, `xdata-clusters.csv` |
| `gen_xdata_symbols.py` | `ec/ghidra/xdata-symbols.csv` |
| `ifr_census.py` (`bios/`) | `bios/ifr/charge-questions.csv` |
| `census_native_c.py` (`windows/`) | `windows/ghidra/c-census.csv` |
| `walk_budget_census.py` | `ec/annotations/walk-budget-census.csv` |
| `trace_xdata_refs.py` | `ec/annotations/xdata-086x-dispatch-sites.csv` |
| `walk_flow_follow.py` | `ec/annotations/flow-follow-none-sites.csv` |
| `pd_entry_forms.py` | `ec/annotations/pd-entry-forms.csv` |
| `pd_image_census.py` | `ec/annotations/pd-image-strings.csv` |
| `pd_direct_offset_sites.py` | `ec/annotations/pd-direct-offset-sites.csv` |
| `find_indirect_xdata.py` | `ec/annotations/indirect-xdata-sites.csv` |
| `inc_dptr_sites.py` | `ec/annotations/xdata-inc-dptr-only.csv` |
| `census_xdata_writers.py` | `ec/annotations/manual-fan-ctrl-0751-writers.csv` |
| `code_pointer_sites.py` | `ec/annotations/code-pointer-sites.csv` |
| `pd_inline_arg_sites.py` | `ec/annotations/pd-inline-arg-sites.csv` |
| `pd_site_clusters.py` | `ec/annotations/pd-0x07d0-07cc-clusters.csv` |
| `xdata_span_survey.py` | `ec/annotations/pd-xdata-span-sites.csv` |

The rows from `walk_budget_census.py` down are the CRLF half, and they are
in the covering set for the same reason as the rest: a `--check` that compares
a CRLF table is a check the blanket has to reach, not a special case of it.
`xdata_span_survey.py` is the row that makes the reading a per-tool one rather
than a pattern — its `--check` takes the path as an argument instead of
defaulting to it, so the table it compares is named where it is pointed at
rather than on an argparse line.

Plus the two `call_graph.py` reads above, which are inputs rather than
comparisons but carry the same hazard for the reason the third row gives.

A tool that grows a `--check` is a deliberate addition to this table and to
`BYTE_COMPARED` in `test_gitattributes_coverage.py`, which is the moment
someone looks at it. That is why the list is named rather than discovered: a
regex that guessed which tables are byte-compared would report a coverage
property over a set it invented.

Of these, four appear in `.github/scripts/agent-gates.sh`: `call_graph.py`,
`citation_gap_scan.py`, `gen_xdata_symbols.py`, `xdata_register_map.py`. The
other checks are reachable by a human running the tool and not by the gate, so
covering them costs nothing and a future gate arm would not arrive to find the
table exposed.

`ec/decompiled/**/*.asm` is uncovered and measured harmless **for this tool**:
`citation_callers.py` reads listings with default newline handling, so universal
newlines absorb CRLF, and 0 of the 2,717 committed listings carry a CR. That is
a latent hazard for any future tool that byte-compares an `.asm`, not a claim
that the tree is safe for one.

## Why the form is per file, and not one rule

The CRLF tables are not drift. They are **correct output**: their generators
pass a bare `csv.writer(buf)` with no `lineterminator`, so csv's default `\r\n`
is precisely what they render, and a `--check` of one is green today. That is a
claim about the mechanism, and the set of tools doing it is larger than any list
here: some of these tables are written by a tool reached through `--check PATH`
rather than through a `--check` default, and some by a tool whose stdout is
redirected into the file. `CRLF_EMITTERS` in `test_gitattributes_coverage.py`
names the ones the suite re-reads, each asked for the property it is named for
so the list cannot quietly stop being true, and the ones it does not name are
held by the table-wide case — no `eol=lf` line may cover a file carrying a CR —
which reads the bytes rather than a list:

```
$ python3 ec/tools/walk_budget_census.py --check
ec/annotations/walk-budget-census.csv: this run reproduces it byte for byte (16 lines)
```

The LF tables are the ones whose tool passed `lineterminator="\n"`. The split
is therefore a property of each table's generator, and the form follows it:

| form | on an **LF** table | on a **CRLF** table |
|---|---|---|
| `text eol=lf` | correct — LF in the index *and* the worktree | **breaks a green check** — the worktree goes LF while the tool renders CRLF |
| `-text` | correct — bytes verbatim both ways | correct, and the only correct choice: it stops `autocrlf` normalising CRLF→LF **on the way in**, which is a whole-file diff plus a red check |

So the change is `-text` for `ec/annotations/*.csv` as a blanket, with the LF
tables named beneath it, and `text eol=lf` for the tables outside that
directory. Neither renormalises anything today, which is what keeps this change
to an attribute and the docstrings that named the old state.

**A CRLF-emitting tool's *input* being LF is not a contradiction.** This came up
while writing the test that holds the split, and it is worth stating because the
obvious way to write that test gets it wrong. `pd_image_census.py` names three
committed CSVs and emits CRLF, but only `pd-image-strings.csv` is the table it
writes and compares; `ghidra-functions.csv` is an *input* it reads, and that one
is correctly `eol=lf`, being hand-transcribed with an embedded newline in it. So
the property to hold is about the table a tool *compares*, not every CSV path a
tool mentions. `test_gitattributes_coverage.py` therefore reads each emitter's
`check_table(...)` argument — and each tool's `--check` default, which for most
of them is the `const=` on their own argparse call, and is the only place
`walk_budget_census.py` names its table at all. An earlier version of that case
asked each module for every `.csv` string it mentioned and so checked nothing,
or checked the wrong file; a case that resolves to zero files now fails rather
than passing.

**Why `text eol=lf` rather than `-text` for the LF set.** These are
human-transcribed text, not machine output. The `.gitattributes` precedent is
scoped to "the decompiled `.c` is machine output, and it is digested", and that
argument does not transfer to `ghidra-functions.csv` — the project's editable
surface (CLAUDE.md). Under `-text` a Windows contributor's edit to that one
quoted multi-line comment commits CRLF bytes verbatim, and a CR then lands
*inside* a parsed field, which is the failure measured above. `text eol=lf`
normalises it back on commit, so the round trip is lossless, and the file stays
ordinary text for diff and merge, which is how it is actually used.

The consequence is deliberate: **there is no single correct attribute for this
tree, and there cannot be one until the generators change.** That is the
follow-up below.

## What the issue got right, and what it did not

Three figures in the issue were right and are worth keeping, because each is a
property that had to be measured rather than assumed:

- `call-graph-callees.csv` is 1,841 data rows with zero CR bytes, and
  `git check-attr -a` returned nothing for it. Both still hold.
- `.gitattributes` was 44 lines covering only the Ghidra databases and the three
  decompiled `.c` trees, with no entry for any CSV. Both still hold.
- The three CRLF tables it named carry exactly the CR counts it gave:
  `bank-call-targets.csv` 5,999, `bank-relative-branch-targets.csv` 9,077,
  `pd-xdata-span-sites.csv` 1,025.

Two were wrong, and the first is why the naive fix would have broken checks
that are green today:

1. **"Do not silently renormalise the other 20 files."** The population is every
   CRLF-carrying CSV under `ec/annotations/` plus `ec/decompiled/index.csv` —
   several times the issue's count, and nearly all of it CRLF. A
   renormalisation scoped off an undercount is the failure this issue is about,
   so the correction matters more than the arithmetic, and the split moves as
   tools are added, so it is printed rather than written down:

   ```sh
   python3 - <<'PY'
   import glob
   files = sorted(glob.glob('ec/annotations/*.csv')) + ['ec/decompiled/index.csv']
   crlf = [f for f in files if b'\r' in open(f, 'rb').read()]
   print(len(crlf), 'CRLF of', len(files))
   PY
   ```

2. **The three named `check_table` docstrings.** There is no single owner of this
   shape. `call_graph.py`, `citation_gap_scan.py` and `task_call_table.py` all
   carried the claim that `.gitattributes` does not cover `ec/annotations/*.csv`,
   and all three are now false, so all three are corrected in place. Each also
   differs in a way worth recording rather than averaging: `task_call_table.py`
   is **not** in `agent-gates.sh` (its hazard was latent, not gate-reachable),
   and its `--write` opens the table without `newline=""` where the other two do,
   so on Windows it *produces* CRLF. No attribute addresses that.

## What is checked, and what is not

`ec/tools/test_gitattributes_coverage.py` holds the **rule**, never a census —
a count of the tree is a value every landing suite and every new table would have
to edit, which is the lock CLAUDE.md's "no totals of the repository's own text"
exists to prevent. It asserts that every byte-compared table above is matched by
some line, that no line covering one says `binary`, that no path matched by an
`eol=lf` line carries a CR today, and that `git check-attr` agrees — with the
attribute-file parse standing alone so the suite cannot pass vacuously on a
machine without git.

The last of those is the one this change most needs. Marking a CRLF-emitting
tool's table `eol=lf` would send it out as LF while the tool renders CRLF and
turn several green checks red at once, and the attribute would be the reason —
the worst way for a tree to go red. The case names the tool and the table.

Detection is held from the other side: a CRLF table is still rejected, with a
non-empty report. The attribute removes the cause, not the check, and a
`--check` softened to agree with a new attribute would report a drifted table as
clean.

## Follow-ups this opens

- **The CRLF-emitting tools should pass `lineterminator="\n"`, and their output
  be renormalised.** The scope is every tool whose committed table is CRLF, not
  the subset `CRLF_EMITTERS` names: the other tables are the same shape by the
  same mechanism, and a change scoped to the named subset would leave the tree
  with the two forms and no rule. That is the change which makes one rule
  possible instead of two, and it has to regenerate each table, so it is a
  commit with its own diff. `test_gitattributes_coverage.py` will say so when a
  tool it re-reads stops emitting CRLF, which is the signal to move that one.
- **`task_call_table.py` should write with `newline=""`**, as the other two
  `check_table` siblings already do. It is a CRLF producer on Windows today,
  which no read-side attribute addresses. It is also not in `agent-gates.sh`; if
  it is to be gated, that is a separate change.

## Not done here, deliberately

- **Renormalising the CRLF CSVs.** A real commit with its own diff, exactly as
  the issue warns, and out of scope for an attribute change.
- **`.github/` in any form**, including wiring the new checker into
  `agent-gates.sh`. The pipeline's token has no `workflow` scope, so a branch
  touching `.github/workflows/` fails at the very end rather than the start.
  `tools/run-tests.sh` already runs the suite.
- **Any live run.** Nothing here needs the physical machine or Windows. The CRLF
  checkout is *simulated* by rewriting committed bytes under `/tmp` and driving
  the real code path; no claim above rests on a checkout nobody performed.
  Confirming it on a real Windows machine is a human's one-line check —
  `git check-attr text eol -- ec/annotations/call-graph-callees.csv` after a
  `core.autocrlf=true` clone — and is left for them rather than asserted here.