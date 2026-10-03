# The Ghidra projects are owned by `dave`, and that is the whole of why a non-owner cannot export (issue #293)

Every committed Ghidra project records an owner, and every one of them records
the same one:

```sh
$ for p in ec/ghidra/project/ec.rep bios/ghidra/project/bios.rep \
           windows/ghidra/project/uniwill_native.rep; do
    md5sum "$p/project.prp"
  done
e1337c31e3a1c901a8c23914915c2f7f  ec/ghidra/project/ec.rep/project.prp
e1337c31e3a1c901a8c23914915c2f7f  bios/ghidra/project/bios.rep/project.prp
e1337c31e3a1c901a8c23914915c2f7f  windows/ghidra/project/uniwill_native.rep/project.prp
```

Byte-identical, three times over, and `project.prp` is six lines of which line
four is

```xml
        <STATE NAME="OWNER" TYPE="string" VALUE="dave" />
```

`analyzeHeadless` refuses to open a project owned by another user, and it
refuses **before it reads anything** -- before a pre-script runs, before an
annotation is applied, before the export. Reproduced here on a clean tree with
no annotation rows added, copying the committed project to scratch and asking
Ghidra to open it as this user:

```
INFO  Opening project: /tmp/ownertest/proj/ec (HeadlessProject)
ERROR Abort due to Headless analyzer error: ghidra.util.NotOwnerException: Project is owned by dave
        at ghidra.app.util.headless.HeadlessAnalyzer.openProject(HeadlessAnalyzer.java:1811)
Caused by: ghidra.util.NotOwnerException: Project is owned by dave
        at ghidra.framework.data.DefaultProjectData.<init>(DefaultProjectData.java:133)
```

That is the whole failure, and it lands on the *documented, non-destructive*
path: `export-only` copies the committed project with
`shutil.copytree(PROJECT, copy_dir)`, so the copy inherits the owner and the
copy is what Ghidra refuses. `ec/ghidra/README.md`'s "How to use it" leads with
the export-only run, and that one cannot complete for anyone whose username is
not `dave`.

`docs/findings.md` §18 reported this as one of two pre-existing defects, and
several write-ups have since recorded the same wall -- `grep -rl
NotOwnerException docs/findings/` names the set rather than a count of it, which
a merge moves. It is now fixed, in the copy, by `ghidra/project_owner.py` --
and this document records which state gates the open, because that was the
question the issue asked to have answered rather than guessed.

**Nothing here is a hardware or Windows result.** The whole change is static
files and a headless JVM. No register was read, no machine was observed, and no
`GCUService.exe` was involved.

## Which state gates the open: `project.prp`, and not the `.gbf` records

This is the part worth stating carefully, because the answer is not the obvious
one and the issue explicitly asked for it to be established rather than assumed.

The username appears in the committed projects in two places. `project.prp`
carries it once, as the state Ghidra's ownership check reads. The `*.gbf`
database blobs under `idata/*/` carry it far more often:

```sh
$ for p in ec/ghidra/project/ec.rep bios/ghidra/project/bios.rep \
           windows/ghidra/project/uniwill_native.rep; do
    printf '%s: ' "$p"
    grep -rao dave "$p" | wc -l
  done
ec/ghidra/project/ec.rep: 5090 occurrences of 'dave'
bios/ghidra/project/bios.rep: 5987 occurrences of 'dave'
windows/ghidra/project/uniwill_native.rep: 76127 occurrences of 'dave'
```

(Measured on this tree; re-derive with the command above. These are counts over
committed binaries, so no change to this repository moves them.)

The `.gbf` occurrences are **not** the lock. Their structure says so. Every
`dave` in `ec/ghidra/project/ec.rep/idata/00/~00000000.db/db.1.gbf` is
immediately preceded by a `\x04` length prefix, and each sits in a
`\x0d"FUN_CODE_4a26" <0000> \x04"dave"` style record — a length-prefixed name,
then the same name as the value of a *user* field, repeating once per named
object. The names are 8051 register symbols (`ACC.0` through `ACC.7`, and the
rest of that family) and function symbols alike:

```sh
$ python3 - <<'PY'
import re, collections
d = open("ec/ghidra/project/ec.rep/idata/00/~00000000.db/db.1.gbf","rb").read()
keys = collections.Counter()
for m in re.finditer(b'dave', d):
    p = m.start()
    if d[p-1:p] != b'\x04':          # every one is length-prefixed
        continue
    for back in range(2, 40):
        q, n = p - back, d[p - back]
        if n and d[q-1] == 0 and 1 <= n <= back - 1:
            cand = d[q+1:q+1+n]
            if len(cand) == n and all(32 <= c < 127 for c in cand):
                keys[cand.decode()] += 1
                break
keys.pop("dave", None)   # the username pairs with itself; what is asked
                         # here is what it is paired *beside*
print(keys.most_common(6))
PY
[('FUN_CODE_4a26', 2), ('FUN_CODE_4874', 2), ('FUN_CODE_162a', 2), ('ACC.7', 1), ('ACC.6', 1), ('ACC.5', 1)]
```

So these are Ghidra's per-object `User` attributions baked into the database:
**provenance recorded about who last saved**, one record per named object, not
a single record that decides whether the project opens.

The strongest evidence is not the structure reading at all, it is that
**rewriting `project.prp` alone is sufficient for a complete export**.
`docs/findings/named-without-a-row.md` records that explicitly: correcting the
owner **in the copy only** and changing nothing else gave a full export across
the three programs and a `diff -r` against the committed tree reporting no
differing files. `docs/findings/reset-vector-dptr-targets.md` reproduced the
failure as a control on a clean tree and then needed the same correction to get
past it. This change reproduces the result again: after the rewrite the same
`analyzeHeadless` invocation that raised `NotOwnerException` above gets past
the open. Which error comes next depends on the invocation -- an `-import` of a
real image now completes outright, and a `-process` naming a program the copy
does not hold stops later with `Requested project program file(s) not found`
rather than at the open. Either way the ownership check is what is gone.

**What this does not establish.** Nothing here reads Ghidra's source, so "the
`.gbf` records are provenance rather than the lock" is a statement about what
was measured and what a completed export shows, not about how Ghidra's
internals work. And a measurement finding no second gate is never promoted to
"there is no second gate" -- if a future Ghidra version starts reading the
owner out of the database, this document is where that would be recorded.

## The mechanism, and the alternative that was rejected

`rewrite_owner()` rewrites the `OWNER` state in the `.rep` **in the disposable
scratch copy**, after the `copytree` and before the first `analyzeHeadless`, in
both drivers:

- `analyze()` in `ec/tools/build_ec_decompile.py`, once for all three programs
  (the copy is made once and they share it)
- the export path in `bios/tools/bios_extract.py`, before `post_scripts`

The committed `.rep` is never opened for writing. That is not only the house
rule but the only reviewable one: `.gitattributes` marks `**/*.rep/**`
`binary -diff -merge`, so a change to a committed `.rep` is a hard conflict
against every open branch rather than a diff anyone can read.

### What the BIOS run did and did not change, measured

`bios_extract.py` writes `bios/decompiled/` and `bios/ghidra/` by design, so
running it here changed committed files -- which is a different thing from
changing a project database, and worth keeping the two apart. Those changes
are **not** this change's. A control run of the same driver at `HEAD`, with the
JVM workaround instead of the rewrite, changed **the same files by the same
amounts**; `cmp` over `git ls-files bios/decompiled bios/ghidra` in both trees
is what compares the two runs, and it is the file set that matches rather than
a line count that a merge would move. They are the committed BIOS export being
stale against the annotations as they stand -- module-entry functions picking
up names their rows already carry. The drift was reverted rather than
committed, since fixing it belongs to whatever change owns the annotations. The
owner rewrite is what let the run happen at all; it is not what these rows say.

**`JAVA_TOOL_OPTIONS=-Duser.name=<owner>` was rejected**, and several write-ups
used it. It makes the JVM assert an identity the user does not have, and the
export-only post-scripts *write* to the copy -- so every record they add would
be attributed to an account nobody is logged in as. It is a workaround to stop
depending on, not a mechanism to ship. It also only helps a caller that happens
to be starting a JVM, which is why the rewrite is a plain function with no
subprocess in it.

**`-takeOwnership` was looked for and is not there.** The issue's plan stage
asked for this to be checked under the Ghidra `.github/actions/project-setup`
installs, and recorded either answer. Measured:

```sh
$ analyzeHeadless -help 2>&1 | grep -in 'owner\|ownership\|readOnly'
17:           [-readOnly]
```

Ghidra 12.1.3 has `-readOnly` and no ownership flag, so the decision rule falls
to the rewrite, which is what shipped. If a later version adds one, the rewrite
becomes redundant rather than wrong.

## The end-to-end proof, run as a user who is not `dave`

This is the check `ec/ghidra/README.md` names as the acceptance check for the
whole EC pipeline and the one nothing in CI runs, so it is also the check that
has to work for the change to mean anything. Run on a tree where the committed
owner is `dave` and the runner is not:

```
$ python3 ec/tools/build_ec_decompile.py --work /tmp/ecoracle --self-test --oracle
  ...
  project copy: rewrote dave -> runner
  ...
  ok    bank0 0xB1F0: the export contains an lcall to 0xbf08 at 0xB200
  ok    bank0 0xB1F0: the export contains the DAT_EXTMEM 0x09c7 increment followed by its 0x3b compare
  all assertions passed
```

It completed rather than aborting with `NotOwnerException`. What that shows is
narrower than the whole block: the **export-only path** -- the one
`ec/ghidra/README.md`'s "How to use it" leads with, and the one nearly every
open `ec-firmware` issue is verified with -- now runs to completion for a
contributor whose username is not that one. **`--mode rebuild-project` is not
covered and does not work yet**, for the reason "What this opens" below gives.
Afterwards:

```sh
$ md5sum ec/ghidra/project/ec.rep/project.prp
e1337c31e3a1c901a8c23914915c2f7f  ec/ghidra/project/ec.rep/project.prp
$ git status --porcelain
```

— the digest is the one recorded at the top of this document, and the tree
carries only this change's own files. The BIOS export was run the same way and
reached 38 of 38 modules decompiled with zero failures.

## The invariant that makes the tool safe to add

`rewrite_owner(rep_dir, scratch_root)` takes the scratch root as a required
argument and **refuses any `rep_dir` outside it**. The failure that prevents is
specific and expensive: a future caller aiming this at
`ec/ghidra/project/ec.rep` would edit a file that is `-merge`-marked, and the
result is a conflict against every open branch with no reviewable diff. Putting
the guard in the signature means the next caller cannot avoid it, and it fires
before the file is opened rather than after.

That guard is a test case, not a comment, and the refusal is asserted against
the **real committed paths** -- not only against a fixture that could drift away
from them. `ghidra/test_project_owner.py` also pins the second half, which is
the half that matters most: a check of "the copy is yours" alone would go green
on a rewrite aimed at the wrong directory, so the suite asserts the committed
`project.prp` is byte-identical after a rewrite as well.

Every guard in the helper was checked by removing it and confirming the suite
goes red -- the scratch-root guard, the `realpath` resolution inside it, the
non-XML guard, the idempotence guard, and the captured-prefix substitution. An
assertion nobody has seen fail is not an assertion, and the non-XML case
initially passed for the wrong reason (a binary file also trips the "no OWNER
state" guard), so that one is matched on the message rather than only on the
exception type. The symlink case matters for the same reason: a `rep_dir` that
*looks* like it is under the scratch root but resolves into the tree is refused,
and dropping the `realpath` turns that suite case red.

## What this opens

- **#572's stated blocker is gone, and only the export is left of it.** Two
  documents name the BIOS re-export as blocked on the owner state: the
  `**CORRECTION (2026-10-03, issue #626)**` block in `ec/ghidra/README.md`,
  which ends by calling #572 the remaining step, and
  `docs/findings/entry-namespace-two-copies.md`. Both say the default
  `export-only` mode aborts with `NotOwnerException`, which is no longer true of
  the BIOS driver. Both now carry the correction in place beside the sentence, so
  whoever picks #572 up reads the remaining step rather than rediscovering a wall
  that is not there.

  Measured here, on two copies of the committed BIOS project, one variable:

  ```sh
  $ analyzeHeadless <copy> bios -process -noanalysis -readOnly   # un-rewritten copy
  ERROR Abort due to Headless analyzer error: ghidra.util.NotOwnerException: Project is owned by dave
  $ analyzeHeadless <copy> bios -process -noanalysis -readOnly   # the same copy, after rewrite_owner
  INFO  REPORT: Processing read-only project file: /EcPs2Kbd.efi (HeadlessAnalyzer)
  ...                                                             # exits zero
  ```

  The rewrite is what the difference turns on. This is the open only — no
  post-script ran, so it says nothing about the export itself, which is exactly
  what is left of #572.
- **`--mode rebuild-project` is not covered, deliberately.** It writes the
  committed `.gpr`/`.rep` rather than copying one, so there is no scratch copy
  for the rewrite to attach to, and normalising the committed project is the
  thing `**/*.rep/**` being `-merge`-marked rules out. It is also the mode an
  agent branch cannot usefully run. The export-only path is the one
  `ec/ghidra/README.md` tells a reader to use and the one nearly every open
  `ec-firmware` issue is verified with, so that is what this fixes.
- **`windows/tools/decompile_native.py` is the third site, and it needs its own
  decision.** Its export mode opens the committed project in place and makes no
  scratch copy, so "normalise the copy" has nothing to attach to. It is
  untouched here and no open `ec-firmware` issue depends on it.
- **The `dave` strings inside the `.gbf` blobs are a small information leak** --
  a username, and in two Windows blobs the absolute build paths
  `/home/dave/git/tongfang-gm7mg7p-re/...`. They are real, they are in a
  committed artefact, and removing them means rewriting a `-merge`-marked
  binary to fix something that gates nothing. **A follow-up issue, not this
  change.**
- **`pd_9028_render_probe.py` has its own `retake_owner()`**, and
  `rebuild_provenance.py` passes `-Duser.name` to the JVM. Both work and both
  predate this; consolidating them onto the shared helper is a separate,
  mechanical change that would touch three suites for no behaviour gain.