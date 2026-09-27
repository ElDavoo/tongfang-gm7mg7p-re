# Census the retained 56 MB export, and reconcile the manifest row that calls it zero (issue #370)

(2026-09-27, issue #370. Static reading of committed files plus the commands
named below. No PE is opened, no Ghidra project is built, no vendor binary is
executed, and no laptop, EC or Windows machine is involved: this is text
already in the tree, counted.)

## What is in the retained export

`windows/decompiled/native/GamingCenter3_Cross.c` is **56,693,822 bytes** and
declares **64,588** functions. It was in no index, no listing and no census,
while the manifest row for the program it belongs to read `functions=0`. Both
files are committed, both were right about their own subject, and nothing in the
gate read either. `windows/ghidra/c-census.csv` is the missing third layer,
derived by `windows/tools/census_native_c.py`:

```
grep -c '^// ==== ' windows/decompiled/native/GamingCenter3_Cross.c     # 64588
python3 windows/tools/census_native_c.py --check
```

| export label | binary | separators | first addr | last addr | in project | count basis |
|---|---|---|---|---|---|---|
| `ACPIDriver` | `ACPIDriver.sys` | 55 | `140001000` | `140008060` | yes | `measured` |
| `ACPIDriverDll` | `ACPIDriverDll.dll` | 10,141 | `180001000` | `1801CA9F8` | yes | `measured` |
| `GC3_launcher` | `GamingCenter3_Cross.exe` | 1 | `180008000` | `180008000` | yes | `measured` |
| `GamingCenter3_Cross` | `GamingCenter3_Cross.dll` | **64,588** | `180DE2000` | `1818D1B40` | **no** | `carried-from-run` |
| `UEFI_Firmware` | `UEFI_Firmware.dll` | 407 | `180001000` | `1800110C0` | yes | `measured` |
| `clrcompression` | `clrcompression.dll` | 60 | `180001000` | `180008DC0` | yes | `measured` |

That is 75,252 declared functions across the six committed exports, of which
64,588 (85.8%) are the one no index row reaches
(`tail -n +2 windows/ghidra/index.csv | wc -l` gives the 10,664 the other five
contribute). None of those 10,664 addresses is declared in the retained export —
0 for every program, measured per program against the export's separator set — so
the 64,588 are additional rather than a second copy.

## Which binary, on two grounds that agree

**By range, with its limit stated.** The retained file's `0x180DE2000`–`0x1818D1B40`
is disjoint from every other export's range, so all 64,588 are the `.dll`'s and
0 are any other binary's. That limit is real and the tool prints it on every
run: `ACPIDriverDll.dll`, `UEFI_Firmware.dll` and `clrcompression.dll` are all
PE32+ at base `0x180000000` and their ranges overlap *each other*, so a range
resolves this file only because it happens to be disjoint. Ranges are not a
general attribution mechanism in this tree and are not presented as one.

**By the header's digest pairing.** The `// Source:` line is **byte-identical
across the five indexed exports** — the same five paths and the same five
SHA-256s — so it is the run's *target list*, not per-file provenance, and the
paths in it cannot say which binary a given export is. What it does carry is a
positional pairing: the exporter writes one joined `source=` list and one joined
`sha256=` list in the same target order (`ghidra/scripts/ExportDecompile.java`'s
`sourceFor()`), so the pair whose path names a binary is that binary's digest.
The retained file's line is the common five **plus a sixth pair**
(`.../GamingCenter3_Cross.dll`, `6663e63d…`), and that sixth digest appears in no
other header in the tree.

That digest is written down nowhere else. The manifest's `.dll` row carries an
empty `sha256`, and `windows/ghidra/native-binaries.csv` carries `runtime` for
that row. `binary_sha256` in the census is therefore the only committed record
of `GamingCenter3_Cross.dll`'s digest anywhere in this repository — a small
unprompted gain, and one that only falls out of doing the attribution properly
rather than reading the filename.

## What the counts are, and what they are not

- **64,588 is a separator count, so it is the *decompiled* count.** The
  *function* count is 64,591 with 3 failures, per the table already at
  `windows/decompiled/native/README.md`. The census carries both figures in
  adjacent columns and `count_basis` names which is which.
- **The 3 failures are not re-derivable from the file.** A function that fails
  to decompile emits no separator, so no command over the `.c` recovers them.
  Their basis reads `carried-from-run`, and the tool says so rather than
  inferring 64,591 as `separators + 3` — that addition would be a fabricated
  figure, and the columns sit next to each other precisely so a reader can be
  tempted to do it.
- **A false sentence was already in the tree.** `…/native/README.md` said "The
  three failures are in the manifest and the index, not rounded away." On the
  committed tree that is not true of this program: the `.dll` manifest row is
  `0,0,0,0,0,not-in-project`, and `grep -c 'failed'` is 0 in both index CSVs.
  Corrected in place beside the sentence, with the wrong version left visible.
- **The header names a generator that cannot re-derive it.** The file says it
  was generated by `windows/tools/decompile_native.py`; the string it prints is
  written by the shared exporter `ghidra/scripts/ExportDecompile.java`, and no
  committed code can re-derive *this* export because the program is not in the
  project. So the census measures the **file** and never trusts the header for a
  count — the header is used only to name the binary, and only when it resolves
  to exactly one.

## The manifest reconciliation, and what was left out

**The `.dll` row's zeros are not overwritten.** `write_manifest()` regenerates
that row from `PROJECT_EXCLUDED` on every Ghidra run, so a hand-edited count
there is destroyed by the next export and reappears as a silent diff. Putting
64,591 into a generated file is a claim that does not survive the next build.
The census row carries the measured figures **and** the manifest's, in adjacent
columns — the zeros sitting beside the real number, which is the reader
confusion the issue found.

The same reason rules out a new column in `manifest.csv`: `MANIFEST_HEADER` is
written by `write_manifest()` from `PROJECT_EXCLUDED`, so a column is a tool
change landing in a generated artefact and needs a Ghidra run to populate. The
census CSV is the same information with none of that coupling. A human who wants
the manifest to carry the measurement is looking at a follow-up issue, not this
one.

**No gate edit, and that is deliberate.** `decompile_native.py --check` is
already invoked by the cheap gate at `.github/scripts/agent-gates.sh`, so the
reconciliation lands in CI with no `.github/` change — a prepared patch nobody
applies is a gate that does not run. `do_check()` re-derives the census and
fails if any `PROJECT_EXCLUDED` program has no row, if a row's `project_*`
figures drift from the manifest, or if a `not-in-project` row carries a non-zero
count labelled `measured`.

## What this settles, and what it does not

**It settles:** what is in the six committed exports, to the separator, with the
count re-derivable by the command above; which binary each belongs to, on two
grounds that agree; how much of the native Windows function surface this
repository holds is unindexed; and the digest of the one binary whose manifest
row cannot name it.

**It does not settle:** what any of those 64,588 functions *do*. A count is a
measurement of a file's shape, not a behaviour, and this says nothing about
whether the Control Center's EC-facing logic lives in these 64,588 or in the
indexed five. That is the question the issue opens, and a static address census
cannot answer it either way. It matters: per `docs/MISSION.md` the Windows
component is `GCUService.exe` **and friends**, and until this says what the
friends are, the register-level Windows work that exists — #320's `T1WR` caller
census, #334's `ec-callsites.csv` reach — cannot be said to have looked at the
vendor stack rather than at five binaries of it. Searching the retained export
for EC-facing behaviour is the next piece of work, and this census is the
prerequisite for it, not a substitute.

Two further limits, both real. The export carries `FUN_…` names because the
default build decompiles without the PDB; resolving them against
`GamingCenter3_Cross.pdb` is separate work. And the retained `.c` has no
machine code beside it — its `.asm` cannot be re-exported, because the program
is not in the committed project — so nothing in this repository can check a
claim about what it does against code it can read.

## Re-deriving every figure above

```
python3 windows/tools/census_native_c.py              # the table, from the files
python3 windows/tools/census_native_c.py --check      # the committed CSV is current
python3 windows/tools/census_native_c.py --write      # regenerate it after a re-export
grep -c '^// ==== ' windows/decompiled/native/GamingCenter3_Cross.c
```

`c-digests.csv` is untouched and still says one row per committed `.c`. The two
are different claims and neither replaces the other: a digest says a file has
not moved, a census says what is in it.
