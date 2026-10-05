# The owner state is a preflight now, and the rewrite is held by a check that fails if it is dropped (issue #572)

**2026-10-05.** `docs/findings/ghidra-project-owner.md` is the measurement: every
committed Ghidra project records `VALUE="dave"` in its `project.prp`, and
`analyzeHeadless` refuses a project owned by anyone else at the open, before a
pre-script runs. That document records the rewrite that fixes it — in the
disposable copy, never the tree. This one is about the two things that were still
missing after it landed, both of which #572's last "done looks like" bullet asks
for: **the owner state was never checked before the run**, and **nothing failed if
the rewrite was removed from a driver.**

Nothing here is hardware or Windows evidence. No register was read, no machine
was observed, and no `GCUService.exe` was involved. What was run is a headless
JVM over committed files, and both are named where they are described.

## The correction, first, because it changes what this is

#572 describes a tree that has since moved. Its central instruction — rewrite the
owner state in the scratch copy after the `copytree`, in both drivers — was
implemented, under **#293**, in `ghidra/project_owner.py`, and
`docs/findings/ghidra-project-owner.md` carries the end-to-end evidence including
a complete export run as a non-`dave` user. Both drivers already called it. Its
first three "done looks like" bullets were therefore satisfied when this change
started; the work here is the fourth, and the correction this document records so
nobody re-derives it from the issue text.

## The preflight: what it is, and what it is not

`ghidra_preflight()` in both drivers checked exactly one thing -- the exec bit on
Ghidra's native `decompile` binary -- so a copy still carrying the committed
owner got all the way to `analyzeHeadless` and surfaced as a `NotOwnerException`
inside a per-program log, minutes downstream, with the JVM already started. Each
driver now has an `owner_preflight(rep_dir)` next to it, called from inside the
function that makes the copy:

```
$ python3 ec/tools/build_ec_decompile.py --work /tmp/ecst --self-test
  project copy: rewrote dave -> runner
```

and, on a copy that was not retaken, the terminal gets this rather than a log:

```
error: the project copy is not openable as this user:
  ec.rep/project.prp: is owned by dave, not runner, so analyzeHeadless would raise NotOwnerException before it read an annotation
  Ghidra's ownership check reads that state at the open, before a pre-script runs
  and before an annotation is applied, so analyzeHeadless would abort the whole
  export having read nothing and say so only in the per-program log under the work
  directory. The copy is retaken by rewrite_owner() in ghidra/project_owner.py, which
  copy_project_for_export() calls after the copytree; if the copy still carries the
  committed owner, that call did not run.
  /tmp/…/project-copy/ec.rep
```

**What this establishes:** that a copy which is not openable as the running user
is refused before the run, on the terminal, naming the project and the rewrite that
should have retaken it.

**What it does not establish:** that the copy opens once the preflight passes.
That is a run's evidence, and the two runs below are it. The preflight reads one
`<STATE>` element; it says nothing about whether Ghidra would object to something
else in the database, and it says nothing about the `.gbf` records inside
`idata/` — which `docs/findings/ghidra-project-owner.md` measures as provenance
rather than the lock, and which this change deliberately does not re-open.

One design point is worth recording because it is what makes the preflight a check
rather than a message. It is called from **inside** `copy_project_for_export()`,
not beside it. Beside it, a `--self-test` that reached the function would still
never see a rewrite deleted from the function.

## The regression check, and the hole it had

**The EC `--self-test` did not test the call site.** It made its own copy and
called `rewrite_owner()` on it directly. That proved the helper works and said
nothing about whether `analyze()` still called it -- so deleting the rewrite from
the export path left every assertion in that self-test green while the default
export stopped running. The **BIOS `--self-test` had no owner assertion at all**,
so the two drivers could disagree about the one thing that decides whether either
of them opens its project.

Both self-tests now drive their own driver's `copy_project_for_export()`, and each
also asserts the other half — that the committed `project.prp` is byte-identical
afterwards — plus the preflight's own refusal on a copy that was never retaken.
A check of only the first half would go green on a rewrite aimed at the wrong
directory.

**The negative case, measured rather than asserted.** Deleting the
`rewrite_owner()` line from either driver's copy path and re-running its
`--self-test`:

| what was deleted | EC `--self-test` | BIOS `--self-test` |
|---|---|---|
| `rewrite_owner()` from `copy_project_for_export()` | exit 1, the preflight message above | exit 1, same shape, naming `bios.rep` |
| nothing (tree as committed) | `all assertions passed` | `all assertions passed` |

The suite `ghidra/test_check_project_owner_gate.py` goes red on the same two
edits, and on a third: an EC `--self-test` reverted to making its own copy.

## What the preflight cannot see, and the gate that can

A preflight inside a driver is local to that driver. It cannot see the other
driver, it cannot see the third site, and it disappears with the file it lives in.
`ghidra/check_project_owner_gate.py` is the one place they are visible together:
for each of the three committed projects, that `project.prp` is readable and
carries a non-empty OWNER; and for each driver that copies a project to scratch,
that its copy path reaches `project_owner.rewrite_owner`.

It reads committed text and parses two driver sources with `ast`. No image, no
Ghidra, no JVM, and it never opens a `.rep` — those are tens of megabytes of
`-merge`-marked binary. That is what puts it in the cheap tier.

**The third site is reported, not required.** `windows/tools/decompile_native.py`
opens the committed project in place and makes no scratch copy, so "retake the
copy" has nothing to attach to there. It is named in `NO_COPY_SITE` and `--check`
prints the omission, so it is a recorded state rather than a hole in a scan.

**What the check does not claim**, stated because it is the direction this could
overclaim in: it does not claim a project opens, that the committed `.rep`
survives a run byte-identical, or that the rewrite is *sufficient* for the open
rather than merely present in the copy path. Joining a copy and a rewrite in one
module's call graph is weaker than showing the rewrite is applied to *that* copy;
deciding that needs the argument each call site passes, which is a dataflow pass
over code whose every real instance is one function doing both. What it rules out
is the failure that actually happened -- the rewrite deleted from the copy path --
and it rules it out without going red on a rename.

**The gate wiring is a prepared patch, not an edit.**
`docs/ci/agent-gates-project-owner-gate.patch` adds two `python3` lines inside
`check_ghidra_tooling()` and **no `gate` line**, because the `gate` list and both
top-level gaps a `check_*()` function could take are saturated by the other
prepared patches in `docs/ci/`; `tools/test_agent_gates_patches.py` applies every
ordered pair and is what decides. The token has no `workflow` scope, so the patch
lands by a human's `git apply`.

## Both exports ran, on this tree, with this change in it

The issue asked for this and said what to do with either answer, so it is reported
as it happened rather than as an expectation.

```
$ python3 ec/tools/build_ec_decompile.py --work /tmp/ecoracle2
  project copy: rewrote dave -> runner
  === export-only ===
  bank0    functions=755   decompiled=755   failed=0   disassembled=23674  bytes
  bank1    functions=698   decompiled=698   failed=0   disassembled=25431  bytes
  common   functions=753   decompiled=753   failed=0   disassembled=19790  bytes
  pd       functions=541   decompiled=541   failed=0   disassembled=10303  bytes

$ python3 bios/tools/bios_extract.py --work /tmp/biosrun
  38 of 38 modules decompiled with zero failures
```

Both reached the exporters rather than aborting at the project open, and neither
touched a committed `.rep`: `md5sum` of `ec/ghidra/project/ec.rep/project.prp` is
the `e1337c31…` digest `docs/findings/ghidra-project-owner.md` records, before and
after.

**The exports were not a no-op against the committed outputs, and the drift is
not this change's.** Both runs changed committed files, which are reverted here.
The EC drift has **two sources, in two different annotations files**, and a
follow-up needs both or it lands on the wrong one. One is the rename —
`DAT_EXTMEM_0464` becomes `MAIN_FAN_RPM_0` and its siblings — and it comes from
`ec/annotations/registers.yaml` taking those names with
`ec/ghidra/xdata-symbols.csv` regenerated from it and no re-export following.
The other is `ec/annotations/ghidra-functions.csv`: its rows' comment text and
`name_basis` cells have moved on since the committed export was made, so a
re-export moves text into the `.c` files that they do not carry today.
`ec/decompiled/bank0/BD5D.c` still reads `neither address has an entry in
ec/annotations/registers.yaml.` under `name_basis: code-shape`, where its CSV row
carries the corrected sentence naming `MAIN_FAN_RPM` and `name_basis:
ec-register`; `ec/decompiled/bank1/8844.c` still lacks the `CORRECTION
2026-10-04 (issue #1332)` paragraph its row carries. The BIOS drift is the
committed export being stale against its annotations in the way
`docs/findings/ghidra-project-owner.md` already describes — the `seed_basis` and
`name` columns disagree with `bios/annotations/ghidra-functions.csv` — plus one
difference that is not annotation staleness, the `evidence` column's quoting on
the `OemOcDxe` rows, which the next section names. The reproduction for all of it
is the export itself — re-running each driver shows which files move and against
which CSV — so this states which columns and which annotations file disagree
rather than how many cells do. Neither half is a claim about the firmware, and
fixing either belongs to whatever change owns the annotations that moved.
`python3 ec/tools/build_ec_decompile.py --work /tmp/eck --check` exits 0 on the
committed tree after the revert.

**What the runs establish, narrowly:** that with the rewrite in place the default
export-only mode gets past the open for a user who is not the recorded one. They
do not re-establish the `project.prp`-alone claim — that measurement is
`docs/findings/ghidra-project-owner.md`'s, and this change did not vary it.

## What this opens

- **`--mode rebuild-project` is still not covered, and this change does not move
  it.** It writes the committed `.gpr`/`.rep` rather than copying one, so there is
  no scratch copy for the rewrite or the preflight to attach to.
- **`windows/tools/decompile_native.py` needs its own decision**, unchanged from
  `docs/findings/ghidra-project-owner.md`: its export mode opens the committed
  project in place. The new check names that rather than requiring a mechanism
  the site does not have.
- **The committed EC and BIOS exports are stale against their annotations**, which
  this change measured by running them and is not the right change to fix. Both are
  re-exportable now that the open works, which is what unblocks them. On the EC
  side that staleness spans two annotations files, so a follow-up has to look at
  both `ec/annotations/registers.yaml` (via the generated
  `ec/ghidra/xdata-symbols.csv`) and `ec/annotations/ghidra-functions.csv`
  (comment text and `name_basis`), not only the first.
- **`bios/ghidra/index.csv` carries an `evidence` column that disagrees with its
  own source**, separately from any annotation having moved: on the module-entry
  rows it joins `bios/decompiled/OemOcDxe.annotated.c` and
  `bios/decompiled/OemOcDxe.c` with a comma inside one quoted field, where
  `bios/annotations/ghidra-functions.csv` separates them with `;`, and
  `join_index()` copies the annotation's cell verbatim. So a re-export rewrites
  those cells whichever annotation is current, which makes it a committed-tree
  defect in its own right rather than more staleness — worth its own change, and
  named here so it is not folded into the staleness one. It is `index.csv` only:
  `listing-index.csv` has the same header but leaves `evidence` empty on every
  row, so it has nothing to disagree about.
- **The `.gbf` provenance strings** (`dave`, and two absolute build paths) are
  still there, still real, and still not gated by anything.