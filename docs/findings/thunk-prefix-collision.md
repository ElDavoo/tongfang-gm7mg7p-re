# Seven rows whose names Ghidra owned (issue #602)

The write-up for [issue #602](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/602),
which found seven rows of `ec/annotations/ghidra-functions.csv` that applied and
were still recorded as not having applied, and asked whether to fix that by
narrowing `isPlaceholderName()` or by renaming them. It was the rename. This
file records why, what moved, what the fix does not establish, and the four
things it found on the way that are not this issue.

`docs/findings.md` §18 carries the summary; the numbers it quotes are now
1,872 rows, 0 applied-but-unflagged, 25 named-without-a-row, 1,897 named.
`ec/annotations/subsystems.md` §2 carries the same correction against its own
census, with its own two stale paragraphs corrected beside it.

---

## The fault, stated precisely

`ec/decompiled/index.csv`'s `annotated` column is not a judgement about
annotations. It is `isPlaceholderName(name) ? "no" : "yes"` — **did Ghidra name
this symbol, or did a person**. Ghidra reserves a set of prefixes for its own
placeholder names, and a row that starts a name with one of them has answered
that question wrong. The annotation is applied, the name is honest, the comment
is cited, and the export reports `annotated=no`.

That is why the fault was so quiet. There is no error to read and nothing to
grep for: the row resolves, `annotations_unmatched` stays 0, the `.c` exists
and declares the function the index names, and every existence check in
`build_ec_decompile.py --check` passes. The only symptom is a number in a
column that means something other than what a reader assumes it means.

Seven rows were in that state, all `type: forwarder`, all `basis: hand-decoded`,
all `name_basis: code-shape`, and all six of the bank1 ones three bytes of
`ljmp`:

| scope | addr | was | now | evidence |
|---|---|---|---|---|
| `bank1` | `0xF113` | `thunk_to_f275` | `forward_to_f275` | `ec/decompiled/bank1/F113.asm`, `F113.c` |
| `bank1` | `0xF116` | `thunk_to_f290` | `forward_to_f290` | `ec/decompiled/bank1/F116.asm`, `F116.c` |
| `bank1` | `0xF119` | `thunk_to_f2ad` | `forward_to_f2ad` | `ec/decompiled/bank1/F119.asm`, `F119.c` |
| `bank1` | `0xF11C` | `thunk_to_f2ca` | `forward_to_f2ca` | `ec/decompiled/bank1/F11C.asm`, `F11C.c` |
| `bank1` | `0xF11F` | `thunk_to_f2f3` | `forward_to_f2f3` | `ec/decompiled/bank1/F11F.asm`, `F11F.c` |
| `bank1` | `0xF123` | `thunk_to_f198` | `forward_to_f198` | `ec/decompiled/bank1/F123.asm`, `F123.c` |
| `pd` | `0x7059` | `thunk_call_122f` | `call_122f` | `ec/decompiled/pd/7059.asm`, `7059.c` |

`thunk_` is Ghidra's prefix for an auto-thunk. The seven rows chose it
themselves, for an honest reason — they *are* forwarders — and that is the whole
tragedy: a correct name for the wrong reason is still unreadable.

## Why the rename, and not the predicate

The issue offered two routes. Narrowing `isPlaceholderName()` with an exact-match
exception for these seven names is the wrong tool for three reasons, and none of
them is a matter of taste.

**The fault is in the row, not in the predicate.** A hand-chosen name that
begins with a prefix Ghidra owns is choosing a name out of the tool's reserved
namespace, and the repository already had a convention for saying "forwarder"
without borrowing it: `forward_to_<addr>`, which **eleven** committed rows
already carried before this change and **seventeen** carry after. `thunk` is not
banned as a word either — `bank1_switch_thunk_to_81c5` names a function *about*
thunk-ness and sits exactly where it should, mid-name. Thunk-ness belongs in
the middle of a name, not at the front of one.

**An exception list is a silent undercount waiting to happen.** It hardcodes
*person-chosen* names into the tool that answers "did Ghidra name this, or did a
person", which is knowledge that belongs in the CSV and nowhere else. It also
needs a human to add the next row, and the failure mode of a human-maintained
list of exceptions is that it is quietly incomplete — which is the exact bug
being fixed, reproduced one layer down.

**The predicate is the riskier edit.** `isPlaceholderName()` is consulted by
every exporter and by the index. A change there moves the `annotated` column and
the `[named]` marker across the whole export, and the two copies of it had
*already* drifted apart (below), which is direct evidence that the function is
not as stable as its "one definition, used by every exporter" docstring claims.
The predicate was not the thing that needed changing, so it was not the thing
that got changed.

`pd 0x7059` follows the `call_a747` / `call_3894_then_jmp_2de3` population rather
than `forward_to_*`, and that is a distinction with a reason rather than a
preference: it is the one forwarder here that is a single `lcall` and not an
`ljmp`, so `call_` says what the bytes do and `forward_to_` would not. Its
comment already read "A single lcall 0x122F with no setup of its own".

## Why the rule needs no exception list

Because the collision is findable from the committed CSV alone, with no Ghidra
run, no project, and no export. Scanning every `name` cell against the ten tests
in the canonical `isPlaceholderName()` is a few lines against committed inputs,
and it is the same scan the new check runs. Run today it reports zero on the EC
— the seven are gone — and it is the BIOS figure that is left:

```python
>>> import csv, sys; sys.path.insert(0, "ec/tools")
>>> import grade_name_basis as g
>>> for path in ("ec/annotations/ghidra-functions.csv",
...             "bios/annotations/ghidra-functions.csv"):
...     rows = list(csv.DictReader(open(path, newline=""), strict=True))
...     print(path, len(rows), len(g.reserved_prefix_problems(rows)))
ec/annotations/ghidra-functions.csv 1872 0
bios/annotations/ghidra-functions.csv 788 2
```

The same scan against `main` reported **`7`** on the EC, and those seven are the
seven in the table above — which is how the issue could have been diagnosed
before it was filed, and why the check needs no exception list. The BIOS figure
is 2, not 4: the canonical predicate matches `entry` and not
`entry_clamp_status` / `entry_dispatch`. The other two are the drifted copy's
doing, and that is the whole of follow-up #1 — see below.

That is the generalisation, and it is why the check is a rule and not a list:
the population is finite, the predicate is small, and the two are both committed
inputs. The zero is what `build_ec_decompile.py --self-test` now asserts, rather
than leaving to a reader.

`grade_name_basis.reserved_prefix_problems()` now runs that scan on the EC, and
`build_ec_decompile.py --self-test` holds the Python list of prefixes against
the Java it was transcribed from — every literal present, and no test in
`isPlaceholderName()` that the Python does not know about. Editing one without
the other is a red self-test, which turns the "one definition" docstring from a
memory into a guard.

## What moved, measured

The anti-regression evidence is the diff, and it is worth stating what it
actually says rather than what was expected:

- **`ec/decompiled/index.csv`: exactly 7 rows.** The seven names, and their
  `annotated` column flipping `no` → `yes`. No other row in the 2,710-line
  index moved, which is the direct answer to the issue's "without moving any
  genuine Ghidra auto-thunk off `annotated=no`".
- **`ec/ghidra/c-digests.csv`: 8, not 7.** The eighth is
  `ec/decompiled/pd/B3ED.c`, the one committed `.c` in the tree that *calls*
  `pd 0x7059` and therefore carries the new name at its call site. The bodies of
  the seven themselves are byte-identical; a call site is not a body.
- **The `[named]` marker moved on both file kinds, for those seven only.** The
  `.c` files get it from `ExportDecompile.java:207` and the `.asm` headers from
  `ExportListing.java:256`, and after the re-export the two agree exactly:
  **1,897 `[named]` `.c` headers and 1,897 `[named]` `.asm` headers**, which is
  also the manifest's `functions_named`. The `.c` export carries 2,710 addresses
  and the listing export 2,707; that three-address difference is pre-existing and
  has nothing to do with this change.
- **`ec/ghidra/manifest.csv`: `functions_named` for `bank1` and `pd` only**
  (599 → 605 and 501 → 502), summing with bank0's 693 and common's 97 to 1,897.
  `annotations_applied` (786 / 684 / 497) and `annotations_unmatched` (0) did not
  move, because the same rows still apply at the same addresses. No
  `status:`-adjacent claim moved, and `ec/ghidra/xdata-symbols.csv` is untouched
  — no `registers.yaml` row changed, so no symbol rename can imply one.
- **The ledger closes in the right direction.** `build_ec_decompile.py --check`
  prints `1872 annotation row(s) - 0 unflagged + 25 unnamed-by-CSV = 1897 named
  function(s)`, and the 25 is unchanged at 15 `auto` / 9 `call-target` / 1
  `vector`. The seven moved out of the second column and did not disturb the
  first.

The other generated files follow the name, and each was regenerated by the
tool that owns it rather than edited:

| file | rows | what moved |
|---|---|---|
| `ec/decompiled/listing-index.csv` | 7 | the same seven, from the listing exporter |
| `ec/ghidra/cross-decoder.csv` | 7 | the name column |
| `ec/ghidra/reassembly.csv` | 7 | the name column (see the note on the assembler below) |
| `ec/annotations/call-graph-callees.csv` | 1 | `pd 0x7059`, whose own `annotated` column moved with it |
| `ec/annotations/xdata-clusters.csv` | 3 | the name inside the clusters' prose function lists |
| `ec/annotations/xdata-registers.csv` | 12 | the same, across the registers that cite them |
| `ec/annotations/xdata-export-ownership.csv` | 24 | 7 renames **and** 17 pre-existing corrections — see below |

The census CSVs' diffs are the six `forward_to_*` names and nothing else: no
cluster, membership or cluster key moved, which is what `xdata_register_map.py
--check` and `--self-test` both confirm against a fresh generation.

### One generated file could not be regenerated here, and why

`ec/ghidra/reassembly.csv` is written by `verify_reassembly.py --report`, which
re-encodes every committed listing with `sdas8051` and records the assembler's
own version string per row. The sandbox this ran in has `sdas8051 V02.00`; the
committed report was produced by CI's apt `sdcc`, which reports
`05.50.4+NoICE+SDCCmods-WIP-R14`. Running `--report` here therefore rewrote
**2,705 of 2,707 rows** — assembler-build churn that has nothing to do with a
rename, and a diff that would have buried the seven rows inside it. That run was
discarded.

What replaced it is the seven `name` cells, and that is not a hand-edit of a
guess: `listing_digest` covers the instruction lines and not the header, which
is a measured fact rather than an assumption — after the seven `.asm` headers
changed, `verify_reassembly.py --check` still reported "2,707 listing digests
compared against the committed report, 0 disagreements". So a regeneration on
the pinned assembler changes the `name` column and nothing else, which is
exactly the diff CI will produce. Worth stating plainly because the file is a
build product: **the committed `reassembly.csv` here is the pinned
regeneration's diff, not a run of it on this machine.**

`verify_reassembly.py --check` does not compare the `name` column, so nothing in
the gate would have caught the seven names going stale. That gap is real and is
left as it stands — closing it means deciding what the column is for.

## Two corrections to the premises

**`annotation_ledger()` never identified the seven by the prefix.**
`build_ec_decompile.py`'s `annotation_ledger()` keys on `(scope, addr)` and
compares the index's `annotated` against whether a CSV row backs the address.
It reads no name at all. The prefix assumption lived in two other places: a
pinned self-test that asserted `len(_abu) == 7 and
all(name.startswith("thunk_"))`, and the `--check` message that told the user
"`isPlaceholderName()` matched the name they chose" without having checked that
it had. Both are now stated without the assumption — the assertion is *no index
row a CSV row backs may be reported `annotated=no`*, which is prefix-free and
holds for cases that have nothing to do with `thunk_`, and the message reports
the disagreement and names the rows instead of asserting a cause. The
`annotation_ledger()` docstring, which used `thunk_` as its worked example, now
states the route-independent reason instead.

**The open question was not where `ec/ghidra/README.md` carried it.** That file's
open question is whether a non-zero `annotations_unmatched` should fail
`--check` — a different counter. The one the issue quotes lived in
`docs/findings.md` §18 and in the `annotation_ledger()` docstring. The decision
is recorded in `ec/ghidra/README.md` anyway, in the annotation-layer section,
which is the right home for a naming rule that section governs.

## Found on the way, and deliberately not fixed here

**The two copies of `isPlaceholderName()` have already drifted apart.**

- `ghidra/scripts/TongFang.java:135` — `name.equals("entry")`
- `ghidra/scripts/ExportDecompile.java:334` — `name.startsWith("entry")`

Both files carry a docstring claiming one definition used by every exporter.
Neither claim is true today, independently of this issue. Blast radius,
measured rather than guessed:

- **EC: zero.** No exported EC function is named `entry*`, so reconciling the two
  copies moves no EC row, and this change's re-export is unaffected by it. The
  1,897/1,897 `[named]` agreement above is the check on that.
- **BIOS: four CSV-backed rows reported `annotated=no` on the same fault** —
  `EcPs2Kbd 0x260` (`entry`) and `Setup 0x000004B0` (`entry`), which the
  canonical predicate also matches and which are therefore correctly `no`; plus
  `PeiOverClock FFCFBB49` (`entry_clamp_status`) and `OemGlobalNvsDxe 0x370`
  (`entry_dispatch`), which the canonical predicate does **not** match. The two
  copies visibly disagree in committed output: both `entry_*` rows are `no` in
  `bios/ghidra/index.csv` and `yes` in `bios/ghidra/listing-index.csv`, because
  `ExportDecompile` writes the first and `ExportListing` the second.

`entry_clamp_status` and `entry_dispatch` are people's names that happen to begin
with those five letters, and the drifted copy cannot tell them from a module
entry point. That is the whole argument for the `equals` half of the new rule
being an exact match, and for modelling the rule on the canonical copy rather
than on the drifted one — a check built on the latter would pin the drift as
correct.

Fixing it means re-exporting the BIOS: a different component, a different driver
(`bios/tools/bios_extract.py`), and a 49 MB project. **Out of scope here, and
follow-up #1.** The BIOS export is not re-exported by this change and no BIOS
row was touched.

**Pre-existing drift picked up by regenerating, not caused by it.**
`ec/annotations/xdata-export-ownership.csv` was stale on `main`: 17 rows still
carried the `FUN_CODE_*` placeholders Ghidra gave those addresses, while
`ec/decompiled/index.csv` had carried `ff_filler_not_a_function_*` since issue
#561's re-export. Running `export_ownership.py --map` corrects all 17, which is
why that file's diff is 24 rows rather than 7. The correction is the tool's own
output and moves the file toward the index it is supposed to describe; it was
not made by hand and it is not part of this change's reasoning.

**A column list that is missing one.** `ec/ghidra/README.md` lists the CSV
columns as `scope,addr,name,signature,type,comment,evidence,basis` and omits
`name_basis`, which the file has carried since #135 added it. Left alone here to
keep this diff about the rename; it is a one-cell fix whenever that file is next
open for something else.

**A gate comment that is wrong about a mode being red.**
`.github/scripts/agent-gates.sh` carries a long comment explaining why
`xdata_register_map.py --self-test` is *deliberately not run* in the cheap tier:
it is "red on `main` for a reason no census change can clear", because the
annotation CSV named three functions (`bank1:0x9CE8`, `0x9D53`, `0xE2D3`) that
`index.csv` still spelt `FUN_CODE_*`. That is no longer true, and was not true
before this change either: `ec/decompiled/index.csv` already carried
`seed_1c12_trio_or_update_1c11_1c15_1c16`, `seed_1c12_trio_9f_or_run_0x9d7a_ladder`
and `dispatch_036c_low3_then_seed_1c00_block` for those three addresses. Run
now, `xdata_register_map.py --self-test` prints **all assertions passed**.

So a mode that is switched off on the strength of a reason that no longer
exists is switched off for nothing. That is worth its own look — the cheap
tier's own doctrine is that "a deferral nobody can see is a check that gets
dropped", and here the deferral is well documented and still wrong. Not fixed
here: `.github/scripts/` is pipeline infrastructure that CLAUDE.md says not to
edit casually, and this change has no business in it. The comment is also not
harmful in the direction that matters most — leaving the mode off is the
conservative choice, and turning it on belongs to whoever owns the pipeline.

## What this does not establish

Nothing here is a hardware or Windows observation, and nothing claims to be. No
register was read, written or read back; no interrupt, fan or charge behaviour
was exercised. The change is a naming decision plus a regenerated static export,
and the proof is the diff of that export and the two checks that count it.

Nor does it establish anything about the seven *functions*. `forward_to_f275`
describes three bytes at `0xF113` exactly as `thunk_to_f275` did; the reading
behind both names, and the evidence each row cites, are untouched. The
`annotated` column never claimed to be a statement about the code.

And the reserved-prefix rule is a statement about names in the EC's committed
CSV, measured at the date of writing. It is not a claim that no other component,
or no future row, will collide — it is a check, and it fires on the next one
that does.

---

## Follow-ups

1. **The two copies of `isPlaceholderName()`, and the four BIOS rows their
   divergence explains.** `ghidra/scripts/TongFang.java:135` says
   `equals("entry")` and `ghidra/scripts/ExportDecompile.java:334` says
   `startsWith("entry")`, while both docstrings claim one definition. Reconciling
   means re-exporting the BIOS (`bios/tools/bios_extract.py`, 49 MB project) and
   is provably zero-impact on the EC. The two `entry_*` rows are visibly wrong in
   committed output today: `annotated=no` in `bios/ghidra/index.csv` and `yes` in
   `bios/ghidra/listing-index.csv`.
2. **The same scan, generalised, and the `name`-column gap in
   `verify_reassembly.py --check`.** The prefix collision was findable from the
   committed CSV alone with no Ghidra run, and the same scan over
   `bios/annotations/ghidra-functions.csv` is the whole of follow-up #1's
   diagnosis — which is an argument for the scan living in a tool rather than in
   a one-off, worth its own issue once the two-derivation question is settled.
   Separately, `--check` there compares `listing_digest` and `outcome` but not
   `name`, so a rename silently goes stale in that report (as it would have here
   without the regeneration).
3. **A gate comment that is wrong about a mode being red.** See above: the cheap
   tier defers `xdata_register_map.py --self-test` for a reason that stopped
   being true, and the mode passes today.
4. **`ec/ghidra/README.md`'s column list omits `name_basis`**, which the CSV has
   carried since #135.
