# `isPlaceholderName()` had two definitions and they had drifted (issue #626)

`ghidra/scripts/ExportDecompile.java` carried its own private copy of the
predicate that decides whether a name in the export is Ghidra's or a person's.
It tested `name.startsWith("entry")` where the canonical copy in
`ghidra/scripts/TongFang.java` tests `name.equals("entry")`, and both files'
docstrings claimed one definition used by every exporter. Both claims were
false, and the divergence had already reached committed output.

This is the write-up: the two definitions and what each answered, the fault in
the committed BIOS indexes, the two annotation rows that sat in Ghidra's
namespace, what this change did, and — the larger half — what it did **not** do,
because the BIOS re-export that would move the committed indexes is blocked.

Everything here is a static reading of committed files. No Ghidra run happened
for this change, no machine was observed, and nothing was seen in Windows. Every
figure is a measurement over `bios/ghidra/index.csv`,
`bios/ghidra/listing-index.csv` and `bios/annotations/ghidra-functions.csv` as
of **2026-10-03**, and each is given beside the command that produces it.

## 1. The two definitions, and what each one answered

| file | definition | `entry`-family test |
|---|---|---|
| `ghidra/scripts/TongFang.java` | `public static` | `name.equals("entry")` |
| `ghidra/scripts/ExportDecompile.java` | `private static` | `name.startsWith("entry")` |

The canonical one tests the *word*. The drifted one tested the whole *prefix*,
so it could not tell two things apart that `TongFang.java` deliberately
separates:

- a Ghidra seed — a module entry point Ghidra itself calls `entry`;
- a person's name that happens to begin with those five letters.

Which copy an exporter called decided the answer, and the two exporters did not
agree:

| output | exporter | predicate it called | reaches the BIOS? |
|---|---|---|---|
| `bios/ghidra/index.csv`'s `annotated` column | `ExportDecompile` | its own private copy | yes |
| the `[named]` marker on a `.c` | `ExportDecompile` | its own private copy | **no — EC only** |
| `bios/ghidra/listing-index.csv`'s `annotated` column | `ExportListing` | `TongFang` | yes |
| the `[named]` marker on an `.asm` | `ExportListing` | `TongFang` | yes |

**The `.c` row is the one that does not transfer, and the reason is a mode
rather than a fault.** `ExportDecompile` writes the marker in
`writeFunctionFile`, which runs only in **per-function** mode. The BIOS export
runs **per-program** — `bios_extract.py` passes `per-program` to it — and in
that mode a `.c` gets its `// ==== <name> @ <addr>` separator from
`printlnSeparator` instead, which never appends the marker. No file under
`bios/decompiled/` carries it:

```
$ grep -l '\[named\]' bios/decompiled/*.c | wc -l
0
```

The `// ==== entry @ 00000260` in `bios/decompiled/EcPs2Kbd.c` is what a BIOS
`.c` carries in that place instead: the function's Ghidra name, with no verdict
on whether a person chose it. So of the four outputs above, the drift reached
the BIOS through one of them — the wrong **`annotated` column**, §2 below — and
through none of the others.

So one function was written into two indexes by two exporters that disagreed
about it, and nothing in the tree could see it.

## 2. The fault, measured in the committed indexes

Joining the two indexes on `(program, addr)` and comparing the `annotated`
column, the disagreement is exactly these two rows:

```
$ python3 - <<'PY'
import csv
load = lambda f: {(r["program"], r["addr"]): r for r in csv.DictReader(open(f))}
i, l = load("bios/ghidra/index.csv"), load("bios/ghidra/listing-index.csv")
for k in sorted(set(i) & set(l)):
    if i[k]["annotated"] != l[k]["annotated"]:
        print(k, i[k]["name"], i[k]["annotated"], "vs", l[k]["annotated"])
PY
('OemGlobalNvsDxe', '00000370') entry_dispatch no vs yes
('PeiOverClock', 'FFCFBB49') entry_clamp_status no vs yes
```

Every other row of the two files agrees, and both files carry the same number
of rows. These two are the prefix's fault exactly: `entry_clamp_status` and
`entry_dispatch` are people's names, `ExportDecompile` called the drifted
predicate and marked both `no`, `ExportListing` called the canonical one and
marked both `yes`.

Both are `hand-decoded` rows with cited evidence, and the listing beside each
one is committed too — `bios/ghidra/listings/OemGlobalNvsDxe/00000370.asm` and
`bios/ghidra/listings/PeiOverClock/FFCFBB49.asm` — and each carries the marker,
because `ExportListing` called the canonical predicate:

```
$ head -1 bios/ghidra/listings/PeiOverClock/FFCFBB49.asm
; PeiOverClock @ FFCFBB49   entry_clamp_status   [named]
```

So what these two rows lost is not the marker: it is the agreement. A reader who
opens either listing sees a named function, and the index row beside it says
`annotated=no` with nothing to explain the difference — which is the disagreement
`ExportListing` and `ExportDecompile` made and nothing in the tree could report.

## 3. The other half: two annotation rows inside Ghidra's namespace

`grade_name_basis.reserved_prefix_problems()` reports every committed
annotation row whose name the predicate would match — the rule issue #602 added
for the EC. Over the EC CSV it reports nothing. Over the BIOS CSV it reported
two rows, and both were named the bare `entry`:

| row | was | now |
|---|---|---|
| `EcPs2Kbd` `0x260` | `entry` | `module_entry_store_module_globals_and_call` |
| `Setup` `0x000004B0` | `entry` | `module_entry_call_two_helpers_with_both_arguments` |

Both are `type: module-entry`, and both comments already described the routine
in full; only the name was wrong. The names follow the convention the rest of
that column uses (`module_entry_scan_and_apply` on `OemApControlDxe 0x310`,
`module_entry_register_signal_event` on `OemPowerModeDxe 0x310`,
`overclock_module_entry` on `DxeOverClock 0x00000364`), and the comments now say
why the row names the function at all rather than resting on Ghidra's word for
it.

**Calibration for anyone re-deriving this**, because the count is easy to get
wrong in both directions:

```
$ python3 -c "
import csv
rows = [r for r in csv.DictReader(open('bios/ghidra/index.csv')) if r['name'].startswith('entry')]
print(len(rows), sum(1 for r in rows if r['name'] == 'entry'))"
11 9
```

Of the rows in `bios/ghidra/index.csv` whose name begins `entry`, nine are the
bare name and two are `entry_*`. The bare ones backed by a
`ghidra-functions.csv` row are `EcPs2Kbd 0x260`, `Setup 0x000004B0` and
`OemOcDxe 0x3D0` — three, where a quick reading of the scan's own output suggests
two. `OemOcDxe`'s row is deliberately nameless: its comment records that the
hand-written restatement names no symbol for it, so the row carries the address
and the comment and leaves the name alone. It is not at fault and it is not
touched. Every other bare `entry` row is a Ghidra seed with no CSV row at all,
is correctly `annotated=no`, and must not be "fixed".

## 4. What this change did

- `ExportDecompile.java`'s private copy is deleted and both its call sites — the
  `annotated` column and the `[named]` marker — now call
  `TongFang.isPlaceholderName()`. Deleting rather than making the two bodies
  identical, because two identical copies are still two copies and these two
  had already drifted once. The marker call site sits in `writeFunctionFile`, so
  it is the EC's that reach it (§1); both are repointed because the file has one
  predicate to call and a second copy of it is what drifted.
- The two rows above are renamed. `TongFang.java` is not edited: its docstring
  already claimed one definition used by every exporter, and that claim is true
  now rather than aspirational.
- `bios/tools/test_entry_namespace.py` holds the same claims, each a property and
  not a count: the predicate is defined once and `public static`, the drifted
  `startsWith("entry")` is in no script, and the reserved-prefix scan over the
  BIOS CSV is empty. It is discovered by `bash tools/run-tests.sh` with no gate
  edit, because `.github/scripts/agent-gates.sh` is template-copied and the
  push token cannot land a change to it.

`grade_name_basis.reserved_prefix_problems()` over `bios/annotations/ghidra-functions.csv`
now returns an empty list, which is what lets
[`../../ec/annotations/README.md`](../../ec/annotations/README.md)'s rule 5
widen past "EC-scoped". **That widening is not done here** — landing it means a
caller in `bios_extract.py` plus edits to every file that states the EC-only
scope, which is its own change. This one produces the measurement it needs and
holds it.

## 5. What is NOT done: the BIOS re-export

**The committed indexes still carry the old names and still disagree.** Nothing
in this change rewrites `bios/ghidra/index.csv`,
`bios/ghidra/listing-index.csv` or any `.c`/`.asm` header, because those files
are the output of a Ghidra run and none was performed. As of this commit:

- both renamed rows still read `entry` in `bios/ghidra/index.csv` and
  `bios/ghidra/listing-index.csv`;
- `PeiOverClock FFCFBB49` and `OemGlobalNvsDxe 0x370` still read `no` in the
  index and `yes` in the listing export — §2's table is unchanged by this
  commit.

`bios_extract.py --check` does **not** catch the stale names, and will not: it
joins on `(scope, addr)` and never compares `name`. That is by design — names
change as the reading improves and a rename must not fail a check that a stale
export cannot answer — but it means the renames above are not observable in the
committed output until the re-export lands.

The re-export is blocked on **#572**, and the block is real rather than
ceremonial: `bios/ghidra/project/bios.rep/project.prp` carries
`STATE NAME="OWNER" VALUE="dave"`, and `bios_extract.py` copies the project
byte-for-byte before running headless against the copy, so the default
`export-only` mode aborts with `NotOwnerException` before opening anything. The
known workaround — `-Duser.name=dave`, recorded in `docs/findings.md` — is
deliberately **not** used here, per the issue's instruction not to work around
the owner problem.

What remains after #572 lands is the export itself. `ec/tools/test_named_marker_agreement.py`
asserts, for every row of `index.csv`, that the `[named]` marker on the file its
`out_file` names **and** on the listing beside it both equal that row's
`annotated == "yes"`. On the BIOS the first of those has nothing to read — the
export is per-program, so `out_file` names a whole-program file such as
`OemGlobalNvsDxe.c` rather than a per-function one, and no BIOS `.c` carries a
marker to be right or wrong (§1). So the BIOS relation is the second half, and
**it is red today**, on exactly the two rows of §2:

```
$ python3 - <<'PY'
import csv, os
idx = {(r["program"], r["addr"]): r for r in csv.DictReader(open("bios/ghidra/index.csv"))}
lst = {(r["program"], r["addr"]): r for r in csv.DictReader(open("bios/ghidra/listing-index.csv"))}
for k, row in sorted(idx.items()):
    l = lst.get(k)
    if l is None: continue
    p = os.path.join("bios/ghidra/listings", l["out_file"])
    if not os.path.isfile(p): continue
    marked = "[named]" in open(p, errors="replace").readline()
    if marked != (row["annotated"] == "yes"):
        print(k, row["name"], "index says", row["annotated"], "marker says", marked)
PY
('OemGlobalNvsDxe', '00000370') entry_dispatch index says no marker says True
('PeiOverClock', 'FFCFBB49') entry_clamp_status index says no marker says True
```

That is the same two rows, and it is the sharpest statement of the fault: the
listings beside them are **right** and the index column is **wrong**, so the
re-export is what turns this relation green, and until it lands the relation is
still broken in committed output. A follow-up must not carry the `.c` half over
from the EC test: reading a BIOS `.c` for a marker means reading a file that
never carries one, which reports every row as unmarked and every `annotated=yes`
row as a fault — the false negative that test's `None`-versus-`False`
distinction exists to prevent, reached from the other direction.

## 6. Why the existing self-test did not catch it

Worth stating plainly, because the issue's "a change to either copy is a red
test" is wrong and the wrongness is the argument for the new suite.
`build_ec_decompile.py --self-test` holds `grade_name_basis.py`'s Python
transcription against the Java in both directions, and its regex requires the
literal `public static boolean isPlaceholderName`. Pointed at
`ExportDecompile.java` it matches nothing and yields an empty list; pointed at
`TongFang.java` it matched, and the check passed. It could confirm the canonical
copy agreed with the Python and was **structurally unable to notice a second
copy existed**.

So deleting the private copy is not the red test — the count of definitions is,
and `bios/tools/test_entry_namespace.py` is what holds it. That is the general
shape: a guard that reads one file cannot fail on a second one, however careful
it is about the first.

## 7. Adjacent divergence, recorded and not fixed

`ExportDecompile.java` still carries private copies of `readContext`,
`readBasis`, `labelFor`, `assertDistinctLabels`, `sourceFor`, `get` and `stem`,
and its `readBasis` splits with a naive `split(",", -1)` where `TongFang` uses
the RFC4180 `splitCsvLine`. That is a real and wider divergence than the
predicate was, it is not what this issue asks for, and it is a follow-up. It is
recorded here so the next reader knows the private helpers in that file are
duplicates by design-and-luck rather than by accident.