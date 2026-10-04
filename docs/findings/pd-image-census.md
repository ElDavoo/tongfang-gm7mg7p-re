# The `ITE8850-PD` image: a consolidated map, a positive provenance answer, and one null worth the wording

**Issue #26. Written 2026-09-26.** Issue #21 found a fourth closed-source
program in the EC firmware dump — a self-contained `ITE8850-PD`
USB-Power-Delivery 8051 image at file `0x20000`-`0x2FFFF` — and said that
beyond "it exists and it is not the EC" nothing about it was mapped. This is
the write-up for the map. The map itself is
[`../../ec/annotations/pd-image.md`](../../ec/annotations/pd-image.md), its
tool is `ec/tools/pd_image_census.py`, and nothing here retracts anything.

## Three parts of the issue's premise were already committed, and this says so rather than re-deriving them

The issue asks to "map the image's own structure" and to "decide whether the
region belongs in #20's Ghidra scope as a second program with its own project."
Planning against the literal wording would have spent the PR re-deriving
committed ground, and `CLAUDE.md`'s calibration rule says a claim that is
already settled elsewhere should say where it is settled rather than be
restated more weakly:

1. **The separate-program conclusion, the vector table and the C startup are
   all already committed.** [`lightbar-bat-flow.md`](../../ec/annotations/lightbar-bat-flow.md)
   §2 argues the four independent facts; `ec/ghidra/README.md` records that
   `discover_vector_table()` finds six slots on the PD bytes; and
   `ec/decompiled/pd/0500.c` already carries the `c_startup_idata_clear`
   annotation. The new page cross-references §2 and does not re-argue it.
2. **The Ghidra question is already decided, and the answer is not what the
   issue supposes.** The issue offers "a second program with its own project"
   as an option. It is *already* in #20's scope as **the third program of the
   existing `ec.gpr`** — `ec/ghidra/project/ec.rep/idata/~index.dat` lists
   `bank0.bin`, `bank1.bin`, `pd.bin`; `ec/ghidra/manifest.csv` carries the
   `pd` row at 541 functions, 541 decompiled, 0 failed, 541 seeds, 541
   annotations applied; and `ec/annotations/ghidra-functions.csv` holds **541
   `pd`-scoped rows**. The deliverable here is to *state* that, not to decide
   it, and the page states it. (This sentence said 535/499/498, and the 499
   and the 498 were already stale when it was written — the manifest reached
   535 before this page did. 541 is what `ec/ghidra/manifest.csv` carries
   today: issue #489's 37 `pd` rows, then issue #1101's six `0x07D0` accessor
   stubs, which are also in
   [`pd-07d0-accessor-stubs.md`](pd-07d0-accessor-stubs.md).)
3. **The `docs/findings.md` one-liner already exists.** §3a says the
   `0x07E2`-`0x07E5` reference count was "counting the wrong program" and that
   all 38 sites are in "a second 8051 program sharing the flash dump — an
   `ITE8850-PD` USB-Power-Delivery image at file offset `0x20000` … therefore
   its own XDATA allocation." What §3a cannot carry is *where the map is* and
   *what the provenance turned out to be*, and that is what this adds.

Two smaller corrections to the issue's text, for the record rather than for
the argument: it cites "`lightbar-bat-flow.md` §2.1" and there is no §2.1 — the
strings are in §2 fact 1. And "`trace_xdata_refs.py` already understands the
region" is true but is a different axis: that tool understands `0x20000` as an
XDATA *site-labelling region* (`REGIONS`/`PD_MARKER`), not as a program to
characterise. **That tool is not grown**; the new one reads the same
convention and imports nothing from it.

## What was run, and what the numbers are

Everything is offline and reproducible from the committed tree.

| command | result |
|---|---|
| `dd if=ec/firmware/GMxMGxx_11.800 of=/tmp/pd.bin bs=64k skip=2 count=1` | 64 KiB, sha256 `30fe7fb8…` |
| `python3 ec/tools/pd_image_census.py` | five sections, every number quoted below |
| `python3 ec/tools/pd_image_census.py --check` | CSV reproduced byte for byte, and `all <n> pinned figure(s) re-derive` over every figure in §7's block |
| `python3 ec/tools/pd_image_census.py --check --section <name>` | each name re-derives its own section's figures; a name that reaches none is refused, not passed |
| `python3 ec/tools/test_pd_image_census.py` | `OK` — the case count is in the run's own last line, which is where a reader should take it from |
| `python3 ec/tools/pd_image_census.py --self-test` | the same suite, through the flag, and the exit code a gate would read |
| `r2 -a 8051` on `/tmp/pd.bin` at `0x0`, `0xa799`, `0xd663`, `0xe1c0`, `0x10f1`, `0x1229` | the transcripts on the page, verbatim |

**Layout.** In use `0x0000`-`0xF7B7`; `0xF7B8`-`0xFFFF` erased (2,120 bytes);
3,705 `0xFF` bytes in total, and that tail is the *only* 64-byte `0xFF` gap in
the region. So the image is packed with constant pools between functions, which
is why the string runs are scattered rather than one block. 541 committed
listings, 541 annotated rows, **0** addresses held by two listings.

**Vector table: six entries, where §2's table has five.** `0x00` and then
`0x03 + n * 8` — `0x00`, `0x03`, `0x0B`, `0x13`, `0x1B`, `0x23` — with
`0x26`-`0x3F` erased. The sixth is the serial vector, `ljmp 0x010E`.

**This is the one detail that is easy to get wrong in a way that does not look
like a mistake**, so it is worth stating as its own finding. 8-aligning the
whole table from `0x00` reads the padding between entries, and on these bytes
it finds an `LJMP` at `0x00` and nothing at the other five offsets. The result
is a one-entry table, which is a plausible-looking answer to the question, and
the failure would read as "this firmware has no handler there" rather than as a
wrong tool.
`test_eight_aligning_the_whole_table_reads_the_wrong_bytes` pins the wrong
answers, so an edit that "fixed" the walk to be 8-aligned goes red instead of
quietly producing a plausible table.

## The finding that was not on the issue's list: the vector table is a table

**All five interrupt entries are the same wrapper shape in two forms, and the
constant in each is a per-vector CODE address that selects a handler at run
time.** Three are long-form (`0x0056`, `0x00B2`, `0x010E`: `mov psw,#0x00`
plus eight explicit R0-R7 pushes) and two short-form (`0x0094`, `0x00F0`:
`mov psw,#0x10`, no R0-R7 pushes), identical within a form apart from the three
DPTR immediate bytes. Each does `mov dptr,#<CODE>`, `lcall 0x0050`, restores,
`reti`. The shared body is
`0x0050 call_10f1_then_jmp_1229`, and both routines it reaches are already
named in the annotations CSV:

```console
$ r2 -a 8051 -e scr.color=0 -q -c 'pD 0x10 @ 0x10f1' /tmp/pd.bin
            0x000010f1      e4             clr a
            0x000010f2      93             movc a, @a+dptr
            0x000010f3      fb             mov r3, a
            0x000010f4      7401           mov a, #0x1
            0x000010f6      93             movc a, @a+dptr
            0x000010f7      fa             mov r2, a
            0x000010f8      7402           mov a, #0x2
            0x000010fa      93             movc a, @a+dptr
            0x000010fb      f9             mov r1, a
            0x000010fc      22             ret
$ r2 -a 8051 -e scr.color=0 -q -c 'pD 0x0a @ 0x1229' /tmp/pd.bin
            0x00001229      8a83           mov dph, r2
            0x0000122b      8982           mov dpl, r1
```

`0x10F1 read3_code_to_r3r1` reads three CODE bytes at the CODE address the
wrapper loaded; `0x1229 load_dptr_then_indirect_jump` takes the middle and last
of them as a big-endian 16-bit CODE pointer and jumps there. So
`CODE 0x0152`/`0x0153` *is* the handler for vector `0x03`, and the five
`0x0151`/`0x0154`/`0x0157`/`0x015A`/`0x015D` are a 3-byte-stride selector table
whose last word sits at `0x015E`/`0x015F` — one byte before `ProtoVer:01.00 `
at `0x0160`. The handlers are therefore **fixed in the image**, not chosen at
run time: the table holds the constants `0xA8AE`, `0xF7AE`, `0xF7AF`, `0xF790`
and `0xF7B0`. `0xA8AE` is the committed `event_dispatch_ff80_ffe0`; the other
four are not committed entries and are not decoded.

**The space is CODE, and the repository said so before this page did.** The
`vector_wrapper_dp_…` rows in `ec/annotations/ghidra-functions.csv` each read
"loads DPTR with the CODE address `0x0151`", and `pd,0x0050` reads "reads three
CODE bytes at DPTR". An earlier draft of this write-up carried the constants as
XDATA, on the reasoning below about `pd-base-strides.csv`; that was wrong — a
`MOV DPTR` immediate does not name a space, and the path from `0x10F1` to the
jump has no `MOVX` in it. See `ec/annotations/pd-image.md` §2.1.

**What makes this a measurement and not a shape someone saw:** each of the
five CODE addresses has exactly **one** `MOV DPTR` site in the whole 64 KiB,
and it is the wrapper that loads it. And `ec/annotations/pd-base-strides.csv`
already lists all five among its 448 `unresolved` XDATA bases while saying what
they are *not*; that census scans `MOV DPTR` immediates and cannot know which
space the program means by one, so it is not contradicted — it is answered. It
is also the one **positive** referrer result in a tool whose headline result is
a null, which is why both are worth having.

The two wrapper forms differ — three push 13 registers and zero PSW, two push 5
and set PSW to `0x10`, which selects register bank 1. That is *consistent with*
the short-form handlers running in bank 1, and consistent with the two timer
vectors sitting on a different priority. **Which physical source drives which
vector, and why the two timer vectors are the short ones, is not established
here** and the page says so in the same paragraph as the observation.

## The null: 0 of 43 string-pool candidates has a `MOVC`-mediated referrer

**Not one of the 43 NUL-terminated printable candidates is named by a `MOV
DPTR,#addr` + `MOVC` pair.** The census reports `not found by this method` in
every row, and that wording is the finding rather than a disclaimer on it. It
looked for the 3-byte `90 hi lo` sequence for each candidate's address anywhere
in the 64 KiB, then for a `MOVC` within four bytes of the site. Not one
candidate is named by such a pair. The two address bytes of the pool head
`0xA799`, read on their own, occur zero times in the 64 KiB in either order.

**This is not evidence the strings are unreachable, and the page says so where
the number is.** Three ways this program reaches CODE that a literal `MOV DPTR`
scan cannot see are all present in the image: a `DPTR` carried in from a caller
(every `reader`/`writer`-typed row works that way), a `DPTR` built
arithmetically (`pd-index-geometry.md`'s `base + index * stride` idiom, which
this image uses heavily), and a `jmp @a+dptr` through a table whose address is
a caller's return address. The honest reading is: **the pool is reached by an
address this method cannot compute**, and resolving it means watching DPTR
writes rather than grepping for the addresses. That is follow-up work, named
on the page.

**The third of those is measured rather than only listed, because it is the
most plausible route from a literal in the image to a string.**
`0x119C dispatch_code_table`, `0x11C2 dispatch_code_table_2byte_key` and the
unnamed `0x11EF` pop the return address into DPTR and read the caller's inline
argument bytes with `movc`, so **every table in the program is a literal in the
image** — a string pointer would be too. All 28 `lcall` sites were checked, and
**none of their inline tables opens a pool entry**, each read at its own
dispatcher's entry width rather than at one window; that the width is
per-dispatcher, and why the 4 the census used to apply to all of them was wrong
for two of the three, is
[`pd-code-table-inline-width.md`](pd-code-table-inline-width.md). That is a
statement about these 28 sites and those three widths, which is why the page
quotes it that way; the suite also pins that forcing one width on every
dispatcher — 4 and 8, one of which over-reads `0x119C` and truncates `0x11EF`
— does not change the answer on this image, and plants a synthetic
string immediately after an `lcall` for each of the three to show the same code
path reports a hit when there is one.

**The census is not vacuously green, and that took a case rather than a claim.**
A suite that only measured the committed image would pin a null and prove
nothing about the code that produced it — the defect `docs/findings.md` §88
records for a suite whose cases all read the report. So
`test_the_census_finds_a_referrer_when_one_exists` builds a synthetic region
with a planted `mov dptr`/`movc` pair and asserts the same code path reports
it, and `test_a_broken_attribution_takes_the_suite_red` points
`owning_function()` at the wrong listing and asserts the pinned answer moves
with it. Both mutations were run against a copy of the tool and both take the
suite red; the numbers are on the page's §0.

One place the two halves of issue #181's collision are separable, worth
recording because it is the concrete reason the CSV has two columns: `+INF` at
`0x07D1` has **76** `MOV DPTR,#0x07D1` sites and `-INF` at `0x07D6` has
**142**, and not one is followed by a `MOVC`. On an 8051 those two
instructions are byte-identical, so those 218 sites are XDATA references to the
numbers `0x07D1`/`0x07D6` that happen to coincide with two string offsets — a
collision, not a reference.

## Provenance: **both**, and the EC update is the route that matters

The issue's question was "does `vendor/bios-1.09/BIOS_1.09.zip` contain the
same `ITE8850-PD` blob, or a different version of it? … which in turn
constrains whether it is one chip or two." Answered, and **not** with a null.

**`grep -rla 'ITE8850-PD' vendor/` returns nothing, and that null is an
artefact.** Every member of the zip large enough to hold the marker is DEFLATE,
so the bytes are not in the container a reader greps. (The one member stored
uncompressed is `GM7MG7P/ecflash.nsh`, 29 bytes of plaintext, which does not
contain it either — a first draft of this page said "every non-empty member is
DEFLATE" and the suite's case for it caught the overclaim.) Inflating the
members:

- `GM7MG7P/GMxMGxx_11.800` carries the region at `0x20000` and the marker at
  `0x20040`, and is **byte-identical** to the committed
  `ec/firmware/GMxMGxx_11.800` (both sha256 `158d1c64…`).
- `GM7MG7P/GMxMGxxN109A08.ROM` (13 MiB SPI image) carries **five**
  byte-identical copies of the 64 KiB region (each sha256 `30fe7fb8…`) at
  `0x020000`, `0x45CA2C`, `0x49CA4C`, `0x4DCA6C`, `0x51CA8C`, and the whole
  256 KiB EC image at `0x43CA2C`, **byte-identical, 0 differing bytes**.
- The other six members: the marker is **not found by this method**, by the
  same inflation. The container holds 8 non-empty members and the two above are
  named, which is where the 6 comes from — a number `pd_image_census.py`
  derives from `zipfile`'s `infolist()` and pins as `prov_zip_members` /
  `prov_zip_other_members`, because this line said seven until something
  measured it.
- `GM7MG7P/ecflash.nsh` is 29 bytes read from the zip: `IFUX64.efi GMxMGxx_11.800
  0 1`. That is **one write of the whole 256 KiB**, `0x20000` region included.

**So the answer is both, and the PD firmware ships with the EC update.**

**The comparison that gives the wrong answer, recorded so nobody repeats it.**
Comparing the ROM's *first* 256 KiB against the `.800` reports **82,281**
differing bytes out of 262,144 and reads as an older EC revision. Both readings
are wrong, and structurally: `0x00000`-`0x3FFFF` of a 13 MiB SPI image is the
BIOS region and has no reason to resemble the EC firmware. The comparison to
make is at `0x43CA2C`, and it is 0. This is on the page rather than left out
because the failure mode is specific and repeatable — the wrong comparison
produces a *large* number rather than an obviously-broken one, and "the ROM
ships a different EC revision" is a conclusion that would survive into a
write-up.

**What this settles about one chip or two, and what it does not.** It narrows
it. A single 256 KiB write that updates the EC firmware and the PD firmware
together is consistent with a shared SPI flash, which is what an EC handing a
payload to a *different* device would not be, so
`lightbar-bat-flow.md` §2's handoff story gets harder to sustain. It does
**not** establish how many dies are involved: one flash holding two images is
compatible with one die running both programs, with two dies behind one flash,
and with a die that hands the second image to a part over a link this evidence
does not name. That is a hardware observation, and the procedure for it is
[`../hardware-tests/pd-controller-enumeration.md`](../hardware-tests/pd-controller-enumeration.md).

## The host-facing surface, and the seed it does not get

18 of the 498 `pd`-scoped annotation rows are typed `dispatch`, and the census
lists all 18 with their addresses. Three of them — `0x0F45`, `0x10FD`, `0xB24C`
— dispatch on a *pointer kind* register (R3 = 1 / 0 / `0xFE` / default) and
select XDATA versus internal RAM versus CODE for a load; they are dispatchers
and they are not host-facing, which is worth saying because "18 dispatch
routines" without it is a number with no referent.

The XDATA block a host would plausibly touch is `0xFF80` (5 `MOV DPTR` sites),
`0xFFE0` (6), `0xFFE1` (4), `0xFFE2` (4), `0xFFD0` (2), `0xFFD5` (2), with
`0xFFE3` and `0xFFD1` at **0 — not found by this method**.

**Three things that census is not, all on the page.** It is a count of how
often the program *names* an XDATA address, not of what it does with it —
`trace_xdata_refs.py` is that tool. Those three addresses are in the census
because `0xA8AE event_dispatch_ff80_ffe0`'s committed annotation already
pointed at them, so **the search was seeded, not exhaustive**. And nothing here
says `0xFFE0`-`0xFFE2` is an I2C/SMBus or EC-mailbox register block, that any
of it is writable from the host, or that it is the only host-facing block; no
register in that range is named and none is claimed to be. Whether a Linux
driver could talk to this program at all depends on where it runs, which is
§5's open question and the machine's.

## What the new files are, and what a shared file got

All new work is in new files, per `CLAUDE.md`:

| file | what |
|---|---|
| `ec/tools/pd_image_census.py` | the tool: layout, vectors, string census, dispatch surface, provenance. `--csv`, `--check`, `--self-test` |
| `ec/tools/test_pd_image_census.py` | 51 cases, its own file per the same rule |
| `ec/annotations/pd-image.md` | the map, with a `pd_image_census.py --check`-held pinned-figures block |
| `ec/annotations/pd-image-strings.csv` | the 43-row string census, machine-readable |
| `docs/hardware-tests/pd-controller-enumeration.md` | **Status: not run.** The procedure |
| this file | the write-up |

Three shared files get a pointer and nothing else: one numbered section at the
end of `../findings.md`, one sentence at the end of `lightbar-bat-flow.md` §2
(noting that its five-row table is completed to six), and one sentence in
`ec/README.md`'s existing `0x20000`-`0x2FFFF` paragraph. **`§3a` of
`../findings.md` is not edited** — it already carries the existence line and
it is correct.

**Nothing under `ec/decompiled/pd/` or in `ec/annotations/ghidra-functions.csv`
is touched, and no `registers.yaml` `status:` moves.** No register's status
actually changes on this evidence; `USB_C_POWER_PRIORITY` (`0x07CC`) stays
`present-untested`, because a static decode of a second program's bytes is not
evidence about an EC register in either direction. Naming the PD routines after
the protocol states their strings describe is the obvious next step and is
deliberately not done: a `ghidra-functions.csv` row needs a `name_basis` the
CSV's vocabulary accepts, none of the string-derived anchors is anchored to a
referring routine yet (§ the null above), and a rename churns
`ec/decompiled/pd/*.c` paths across 541 functions.

## Not in any gate, for the reason

`.github/scripts/agent-gates.sh` and the rest of `.github/` are pipeline files,
and this branch's token has no `workflow` scope, so a branch touching them
fails at the very end. `pd_image_census.py` is therefore **runnable and cited
standalone**, exactly as `../findings.md` §88 records for
`test_check_history_checkouts_run.py` ("Not in any gate, for the reason…").
Registering it is a human's change and is named as a follow-up. No
`docs/ci/*.patch` either: `prepared-gate-patches.md` documents that the prepared
set rots and that a non-applying patch is worse than none. What the gate *does*
pick up is `python3 -m py_compile` over `ec/tools/*.py`, which only proves the
two new files compile.

## Follow-ups this PR should surface

1. **Seed PD state-machine rows into `ghidra-functions.csv`** from the anchors
   §3.1's null has not yet produced, with a `name_basis` the vocabulary
   accepts. Blocked on resolving how the string pool is reached.
2. **Register `pd_image_census.py` in `agent-gates.sh`** — a human's change.
3. **Resolve the string-pool reference**, by watching DPTR writes rather than
   by grepping for the addresses. The lead is in `0x119C`/`0x11C2` and the
   indexed `base + n * stride` accesses.
4. **Decide the `MISSION.md`/`CLAUDE.md`/`README.md` framing**, if a human
   wants the PD image called a fourth closed-source component. Not done here:
   a mission change lands in all three files together, across the two most
   contended files in the tree, and the existing framing is defensible —
   `docs/MISSION.md` already says "the EC's **three programs** are imported,
   seeded and exported", and a second 8051 image inside the EC firmware
   component is the third of those, not a fourth stack component.
5. **Which of the five ROM copies a flash tool writes**, and whether the
   descriptor table makes the other four live. Static bytes do not say.
