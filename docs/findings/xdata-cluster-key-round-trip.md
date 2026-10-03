# A census row's `cluster_key` is the hash of that row, and it is held by a case rather than argued in prose (issue #896)

**Nothing here is a hardware claim.** No register was read back, no image was
opened, and no laptop, EC or Windows machine is involved. Both censuses are
files: the committed `ec/annotations/xdata-clusters.csv` and a regeneration of
it written to a scratch directory under `/tmp` by the same committed tool. No
firmware, no BIOS and no Windows code is touched, and **no upstream deliverable
is produced**, so there is nothing to send to `Wer-Wolf/uniwill-laptop` or
`tuxedo-drivers`.

**The calibration comes first, and it is the narrow claim the issue itself
makes: nothing published moves.** §4 re-derives the measurement on this tree and
gets the same result the two prior records got; `ec/annotations/*.csv`,
`registers.yaml` and `ec/ghidra/xdata-symbols.csv` are byte-untouched, and so
are `xdata_register_map.py` and `xdata_moved_ranks.py`. What is below is that
the property had been **asserted for the function and never for the census**, and
that the issue's own account of the surrounding checks is wrong in a way that
matters. §2 corrects it.

## 1. What was already measured, and what this change adds

**The claim is not new.** The issue asks for a case, and the measurement it
asks for was made by hand before:

- [`xdata-names-file-census-anchor.md`](xdata-names-file-census-anchor.md), in
  *The part-2 decision, and its proof*: *"Re-derived independently while
  implementing: recomputing `cluster_key(row.program, row.addrs)` over all 439
  committed `xdata-clusters.csv` rows gives 439 matches, 0 mismatches."*
- The issue's own run, over the same census on the merged tree.

Neither is a case. Nothing re-derived a key from a census row, so a hand edit of
one row's `addrs` would leave every prose claim in the tree still standing while
the row stopped being the cluster its key names. **This change makes the
measurement run in the default sweep; it does not find a mismatch**, and §4 is
this run's figure rather than a new number for the two records above.

**Why the property is load-bearing past the census.** `cluster_key` is a
content hash over the program and the sorted membership, so a key that survived
a re-derivation carries the same membership in both generations. That is the
premise [`xdata-moved-ranks-second-count.md`](xdata-moved-ranks-second-count.md)
§6 declined to touch two sibling `b.get(k) or a[k]` reads on, and it is the
premise two docstrings in `ec/tools/xdata_moved_ranks.py` already lean on:
`flip_table()`'s, for the `a_to_b`/`both`/`b_to_a`/`neither` split, and
`across_report()`'s, which is the one place a tool *states* the premise rather
than relying on it — it prints `shared keys whose committed membership differs
between the two censuses: … this is zero by construction and is printed rather
than assumed`. **That line is now a measurement with a case behind it rather
than an assertion about a hash.** §6 of that write-up keeps its argument and
gains a note beside it.

**And what was genuinely unheld is narrower than "nothing".** `cluster_key` is
defined once and called from exactly one place outside the test file: the single
`key = cluster_key(g, members)` in the census builder that writes the row. The
test file's own calls are synthetic literals (`[0x0E, 0x30, 0x40]`), which is
the coverage the issue describes and is not the property — a synthetic literal
is not a row. So the issue's central observation survives its other halves
being wrong: **nothing anywhere re-derived a key from a census row, and that is
now false.**

## 2. The correction: "every existing check green" is wrong, and the real gap is narrower

The issue says a hand-edited `addrs` cell would leave `pd_keys`, `complete`,
the `program` column and `flip_table`'s `shared` reading a row that does not
match its own key **with every existing check green**. That is not what the
tree does today, and the write-up says so rather than repeating it.

**A hand edit does go red in the cheap gate.** `xdata_register_map.py`'s
`check()` regenerates from the committed decompiled tree and byte-compares both
committed CSVs against the fresh generation, and `.github/scripts/agent-gates.sh`
runs `python3 "$tool" --check && python3 "$tool" --self-test` for this tool on
every push. Editing one `addrs` cell makes the clusters CSV differ from the
generation, and the gate is red. **The issue's claim that nothing would notice is
false**, and the correction belongs here because a write-up that repeated it
would send the next reader looking for a hole that is not there.

**Three things `--check` genuinely does not do**, which is the gap this change
closes:

1. **It is a consequence of the round-trip holding, not a check *of* it.** It
   compares the committed file against one fresh generation from the same run,
   so it can say a row disagrees with what the writer would produce today, but
   not that a row's stored key is or is not the hash of its own columns.
   **It does localise, and precisely** — an earlier draft of this section
   claimed it could not, and the claim was wrong. `diff()` is documented *"First
   differing line named"* and prints that line's number with both sides, so the
   hand-edited `addrs` cell of §5 comes back on the run that catches it as
   `line 2: on disk "main-ec-001,…0x082F,0x0300-0x097B,…" != generated
   "main-ec-001,…0x082F 0x097B,0x0300-0x097B,…"` — the row named by number,
   with the differing field visible in each side. (`--check` takes the census to
   compare against through `--out-clusters`, so a doctored copy is a scratch path
   rather than the committed file.) **What it stops at is the first differing
   line:** doctoring three rows of one census copy yields one reported line and
   a non-zero exit, so the second and third want a second run. That is a real
   limit, and a far smaller one than the gap it was mistaken for.
2. **It reaches one census.** `--no-eq-guard` and `--export-ownership` are
   refused together with `--check` and `--self-test`, and refused again without
   scratch outputs. Both refusals are correct — each flag changes what the
   census says — and
   [`xdata-guard-off-key-distinctness.md`](xdata-guard-off-key-distinctness.md)
   already records that the guard-off census can therefore be reached only by
   the suite. This is the same census, reached here for the round-trip rather
   than for distinctness.
3. **It holds only while the decompiled tree stands still.** Both sides of its
   comparison come from the same run, so a change to `ec/decompiled/` moves
   them together; what it detects is a committed file that is not what this
   tree's generator produces, which is a weaker claim than "each row is the
   hash of its own columns".

So the property was not held, and the reason it survived `--check` is not that
`--check` is blind — it is that **`--check` checks a different thing and only
reaches where it reaches**.

## 3. The cases

`ec/tools/test_xdata_cluster_names.py::TheKeyIsTheHashOfItsRow`, over the two
censuses a `keyed_by()`/`flip_table()` pair is built from. The guard-off half is
the `guard_off()` regeneration this module already caches, so **it costs no
second census run** — the same sharing `TheGuardOffKeyDistinctness` does for
distinctness.

**`test_the_committed_census_holds_its_own_keys`** and
**`test_the_guard_off_census_holds_its_own_keys`** are one assertion over two
inputs, so they differ by a line rather than by a body. Each says: for every
row, `xrm.cluster_key(row["program"], [int(a, 16) for a in row["addrs"].split()])`
is the row's stored `cluster_key`.

**This recomputes the write path rather than a second reading of it.**
`cluster_rows_build` writes `"program": g` and `"addrs"` from the same `members`
the minting site hashed, `cluster_key` is that program and the `hexaddr`-sorted
join of that membership, and `hexaddr` is the tool's one `f"0x{addr:04X}"`. So
`int(a, 16)` over the `addrs` cell inverts the writer exactly rather than
approximately, and the CSV round trip is the only step between the two.

**`test_a_forged_row_is_named_with_both_keys`** is the negative control; §5 is
its transcript. It is the load-bearing case: the two above cannot be *shown*
capable of going red by anything in the committed tree, because the committed
tree agrees with itself. One helper, `key_mismatches()`, answers "which rows
disagree with their own key" for both censuses and all three forgeries — a
second copy of that question would already be
[`xdata-moved-ranks-second-count.md`](xdata-moved-ranks-second-count.md) §3's
shape, two places that know how a row is built and can disagree about it.

**Distinctness is a separate property, and the two do not imply each
other.** This section previously argued that the round-trip *did* imply it —
that two rows carrying one program and one sorted membership under two different
keys would each have to disagree with their own row to do it, so a census these
cases accept already has `duplicate_keys() == {}` — and used that to justify not
re-asserting distinctness. **The premise was true and the conclusion was false**,
because `duplicate_keys()` counts the opposite shape: two `cluster_id`s under
*one* key, not one membership under two keys. The witness is a row copied
verbatim under a second id — same program, same `addrs`, same `cluster_key`. That
census passes every case in this class: the copy is self-consistent, its key
genuinely is the hash of its own columns, so the round-trip reports nothing and
§4's pair count is zero. Copying the committed `main-ec-001` under
`main-ec-001-dup`, `key_mismatches()` returns `{}` while `duplicate_keys()`
returns `{'ke794087e13a6': ['main-ec-001', 'main-ec-001-dup']}`, and no hash
changes anywhere. That census is now the negative control's third forgery, held
as a case rather than argued here.

The two properties are therefore **independent in both directions**: a census
can pass distinctness with every row wrong (the shape the issue describes), and a
census can pass the round-trip while two ranks share one key, with no hash change
involved at all. Each is caught by a case the other misses — `TheContentKey` and
`TheGuardOffKeyDistinctness` for the first, this class for the second — so
holding both means a failure names which one moved. Distinctness is not
re-asserted here, and the reason is now the first rather than the second:
**`TheContentKey` and `TheGuardOffKeyDistinctness` already hold it over these
same two censuses**, so a further copy here would re-check a property two other
classes already hold rather than cover a gap. This matters beyond the prose,
because `flip_table()`'s own docstring says a committed census whose ranks share
a key comes back as `collapsed`, and `duplicate_keys()` is the precondition
guarding exactly that.

**Row totals are not asserted.** Nothing here pins 439 or 445. The count appears
in the failure message, where a reader chasing a bad row sees it, and nowhere
else — the reasoning `TheGuardOffKeyDistinctness` states for itself, and the
hazard `CLAUDE.md` names: a test that asserts a count of the tree is a value
every merge has to edit. **One hand-kept total this change would have made stale
is in the diff**: `guard_off()`'s docstring said how many cases shared the cached
regeneration and enumerated two of the classes holding it. That total is deleted
rather than recomputed, per `CLAUDE.md`; the classes are named in its place.

**The `e169a0e4` pair is still held by nothing.** `TheContentKey`'s docstring
names that census and its guard-off regeneration as the fourth, unreached one;
the new class does not make it look otherwise, and a reader counting the classes
rather than reading them would put the wrong number on the censuses this suite
reaches.

## 4. The measurement, this run

Both censuses, one command, everything the regeneration writes under `/tmp`. The
script is reproduced in full below the transcript so the figure is
re-derivable rather than quoted:

```console
$ python3 /tmp/key-round-trip.py
committed : 439 rows, 0 mismatch(es) {}, 0 (program, sorted-addrs) pair(s) carrying two keys
guard-off : 445 rows, 0 mismatch(es) {}, 0 (program, sorted-addrs) pair(s) carrying two keys
```

```python
import csv, importlib.util, os, subprocess, sys, tempfile
from pathlib import Path

HERE = Path("ec/tools")
spec = importlib.util.spec_from_file_location("xrm", HERE / "xdata_register_map.py")
xrm = importlib.util.module_from_spec(spec); spec.loader.exec_module(xrm)


def census(path, label):
    with open(path, newline="") as f:
        rows = {r["cluster_id"]: r for r in csv.DictReader(f)}
    bad, per_membership = {}, {}
    for cid, row in sorted(rows.items()):
        addrs = [int(a, 16) for a in row["addrs"].split()]
        got = xrm.cluster_key(row["program"], addrs)
        if got != row["cluster_key"]:
            bad[cid] = (row["cluster_key"], got)
        per_membership.setdefault((row["program"], tuple(sorted(addrs))),
                                  set()).add(row["cluster_key"])
    two = {m: k for m, k in per_membership.items() if len(k) > 1}
    print(f"{label}: {len(rows)} rows, {len(bad)} mismatch(es) {bad}, "
          f"{len(two)} (program, sorted-addrs) pair(s) carrying two keys")


census("ec/annotations/xdata-clusters.csv", "committed ")
tmp = tempfile.mkdtemp(prefix="xdata-key-")
oc, orr = os.path.join(tmp, "clusters.csv"), os.path.join(tmp, "registers.csv")
subprocess.run([sys.executable, str(HERE / "xdata_register_map.py"),
                "--no-eq-guard", "--out-clusters", oc, "--out-registers", orr],
               capture_output=True, text=True, check=True)
census(oc, "guard-off ")
```

**The second figure is the issue's other half, stated as a measurement rather
than as a case.** Zero `(program, sorted addrs)` pairs carrying two keys means a
key in both censuses does mean the same cluster in both, which is the premise
§6 of the second-count write-up and `flip_table()`'s docstring rely on.

**The figures are this run's, not a standing census.** Both come from the
committed tree the command reads, and re-running it against a different tree is
what would move them. Nothing else in the suite pins them.

## 5. The negative control

A hold case that has never gone red has never been shown capable of it. The
committed tree agrees with itself by construction, so the cases above can only
be *shown* falsifiable by handing them a census that does not. The control case
does that permanently, in both directions a hand edit of a census goes: one row's
`addrs` changed under a key left alone, and its inverse, one row's key copied
onto another. Both are **forgeries** — `cluster_key` is a content hash over the
program and the sorted membership, so a row that disagrees with its own key is
not something the tool emits. That is the point rather than a flaw in the
fixture: the row these cases exist to catch cannot come from the generator, only
from a census assembled by something else.

**A third forgery goes the other way and the case asserts the helper does *not*
see it.** A row copied verbatim under a second id — same program, same `addrs`,
same key — is a census this class accepts, and `duplicate_keys()` rejects it.
That is the witness §3's independence claim rests on, held as a case so the claim
cannot quietly go back to being an implication: an assertion the helper is
expected to *fail* to make, beside the assertion that the predicate those cases
*do* run on catches what the helper cannot. It is also the one forgery a census
assembled by something else could actually produce, since duplicating a row is
something a merge does and corrupting an `addrs` cell is not.

**Against the real guard-off census, doctored on disk.** A `/tmp` script over the
committed tree rebuilds the guard-off regeneration, drops the last address from
one row *of the census file*, points `guard_off()` at the copy and lets
`unittest` report:

```console
$ python3 /tmp/doctor-key-round-trip.py
the real guard-off census: 445 rows, 445 distinct cluster_key
forged: main-ec-001 lost its last address and still carries kb224d2c2f0c2

.F
======================================================================
FAIL: test_the_guard_off_census_holds_its_own_keys (tcn.TheKeyIsTheHashOfItsRow.test_the_guard_off_census_holds_its_own_keys)
----------------------------------------------------------------------
Traceback (most recent call last):
  File ".../ec/tools/test_xdata_cluster_names.py", line 1381, in test_the_guard_off_census_holds_its_own_keys
    self.census_holds_its_own_keys(self.guard_off, "guard-off")
  File ".../ec/tools/test_xdata_cluster_names.py", line 1365, in census_holds_its_own_keys
    self.assertEqual(
AssertionError: {'main-ec-001': ('kb224d2c2f0c2', 'kcf122b7b13d8')} != {}
- {'main-ec-001': ('kb224d2c2f0c2', 'kcf122b7b13d8')}
+ {} : guard-off census: 1 of 445 row(s) whose stored cluster_key is not the hash of their own program and addrs -- main-ec-001 holds kb224d2c2f0c2, its own row hashing to kcf122b7b13d8

----------------------------------------------------------------------
Ran 3 tests in 0.014s

FAILED (failures=1)
```

```python
import csv, importlib.util, os, subprocess, sys, tempfile, unittest
from pathlib import Path

HERE = Path("ec/tools").resolve()
spec = importlib.util.spec_from_file_location(
    "tcn", HERE / "test_xdata_cluster_names.py")
tcn = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tcn)

tmp = tempfile.mkdtemp(prefix="xdata-doctor-")
out_clusters, out_registers = (os.path.join(tmp, "clusters.csv"),
                               os.path.join(tmp, "registers.csv"))
subprocess.run([sys.executable, str(tcn.TOOL), "--no-eq-guard",
                "--out-clusters", out_clusters, "--out-registers", out_registers],
               capture_output=True, text=True, check=True)

with open(out_clusters, newline="") as f:
    rows = list(csv.DictReader(f))
    fields = list(rows[0])
print(f"the real guard-off census: {len(rows)} rows, "
      f"{len({r['cluster_key'] for r in rows})} distinct cluster_key")
rows[0]["addrs"] = " ".join(rows[0]["addrs"].split()[:-1])
print(f"forged: {rows[0]['cluster_id']} lost its last address and still "
      f"carries {rows[0]['cluster_key']}")
with open(out_clusters, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)

tcn.guard_off = lambda: (tmp, out_clusters, out_registers, "")
unittest.TextTestRunner(verbosity=1).run(
    unittest.TestLoader().loadTestsFromName("TheKeyIsTheHashOfItsRow", tcn))
```

**Three things about that failure are the design.** It names **the row**, not a
count. It names **both keys**, so a reader can see which is stored and which the
row hashes to without re-running anything — where `diff()` prints the row's two
*versions* and leaves the reader to find the differing field, some way in on
either side. And it names **every** offending row in one run, which §2's
`--check` limit says it does not. The committed-census case and the negative
control stayed green, which is the control working: the forgery was in the
guard-off copy, and the committed census was never touched.

## 6. Calibration: what is and is not claimed

- **No mismatch was found, and none is predicted.** §4 measures zero over two
  censuses, the two prior records in §1 measured zero, and nothing here refutes
  `TheContentKey`'s distinctness assertion or `cluster_key`'s content hash.
  This is a case behind a true property, not a defect found.
- **This is not a claim about any real cluster.** It says a census row is
  self-consistent. It says nothing about whether the membership the row names is
  the membership a human would choose, which is the judgement
  [`xdata-names-file-census-anchor.md`](xdata-names-file-census-anchor.md)'s
  residual note records and nothing reads.
- **`--check` is not weakened and no refusal is relaxed.** `--no-eq-guard` and
  `--export-ownership` are still refused with `--check` and `--self-test` and
  still refused without scratch outputs;
  `ec/tools/test_xdata_register_map.py::Refusals` and
  [`xdata-no-eq-guard-refusal-contract.md`](xdata-no-eq-guard-refusal-contract.md)
  are untouched. The two `b.get(k) or a[k]` reads stay as they are: §1
  **vindicates** that decision with a measurement rather than overturning it,
  and rewriting them would be a claim the content-hash property does not support.
- **The `e169a0e4` pair is still unheld**, for the reason §3 gives. Both its
  censuses need that commit's decompiled tree, which no case in this suite has;
  re-deriving them is a human's job.
- **The class is appended at the end of the file, and that is load-bearing.**
  Prose line pins across the tree resolve into `test_xdata_cluster_names.py`'s
  line numbers, some of them held as literals by
  `ec/tools/test_census_test_line_pins.py`, so a class inserted *above* an
  existing one lands each of those pins on a different line. Appending moves
  none of them. The same constraint is why `key_mismatches()` is a method on the
  class rather than a module-level helper beside `clusters_of()`: a new
  module-level function would have to go above the first class, which is the one
  place in this file that moves everything. `TheNamesShape`'s own docstring
  claimed the file's last class position and is corrected in place beside the
  reason.

## 7. What this opens

- **The round-trip is now held where the census is read, and it is still not
  held where the tree moved.** Two of the four censuses
  [`xdata-guard-off-key-distinctness.md`](xdata-guard-off-key-distinctness.md)
  §1 enumerates are reachable by a case and two are not. This closes the
  round-trip half of that gap for the same two, and leaves the `e169a0e4` pair
  exactly as open as it was.
- **Distinctness and round-trip are now held separately, which is the more
  useful order.** Neither implies the other: a census can pass distinctness with
  every row wrong (the shape the issue describes), and a census can pass the
  round-trip while two ranks share one key — a row duplicated verbatim under a
  second id, with no hash change anywhere. Holding both means a failure names
  which of the two moved.
- **Nothing is opened in another repository.** No upstream deliverable is
  produced by this change.