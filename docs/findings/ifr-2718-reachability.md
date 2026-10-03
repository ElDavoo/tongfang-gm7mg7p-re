# Question `0xE9F` is `DynamicPageCount`, and it is a sentinel no page count takes — so the two routes to Intel's Advanced page in the IFR are a self-reference and a TSE choice

(2026-10-03. Static reading of `bios/ifr/Setup.en-US.ifr.txt` with
`bios/tools/ifr_refgraph.py`, which reads the committed dump through
`ifr_census`'s parser. No ROM is opened, no setup variable is read, no laptop
or Windows machine is involved. Every figure below is a property of the
committed firmware, not of this repository, and each is beside the command that
produces it.)

## The claim

**`0xE9F` is `DynamicPageCount`, a 16-bit variable on its own VarStore that
both suppressors test against `0xFFFF` — a sentinel, not a page count — and
which the IFR gives no setup-time path that writes. So there is no variable to
set to reveal Intel's Advanced page, and the only other `Ref` pointing at that
page points at it from inside itself.**

That is a negative answer to the issue's "is there a runtime-reachable
condition that shows the stock pages", and it is negative on the committed
evidence. What is left open is stated below rather than folded into it.

## `0xE9F`, resolved

`bios/tools/ifr_refgraph.py --question 0xE9F`:

```
QuestionId 0xE9F at line 27209
  kind     Numeric   prompt ''
  store    DynamicPageCount  B63BF800-F267-4F55-9217-E97FB3B69846  VarStoreId 0x33  0x2 bytes
  offset   0x0   size 16 bits   flags 0x11
  form     Setup / Save & Exit (FormId 0x271C)
  enclosing  DisableIf at line 26613: TRUE
```

An empty-prompt 16-bit `Numeric` at offset 0 of `DynamicPageCount`, whose
VarStore the dump declares at `Setup.en-US.ifr.txt:59`. It carries no prompt, so
nothing renders it, and it sits inside the block described next. Its
`Flags: 0x11` is *not* read here as a hidden flag: most statements in the dump
carrying `0x11` have a visible prompt, so what the bit means is not something
this evidence settles, and the question is hidden on the two facts above
alone.

**The declaration is inside a block the form set never opens.** It sits within
the `DisableIf` at `:26613` whose operand is a bare `True` at `:26614`, a block
that runs to `:27300` and holds a run of hidden numerics of this same shape.
A `DisableIf` on `True` disables unconditionally, so the IFR states **no
setup-time path that writes `0xE9F`**. That is a statement about the form set
and nothing more: whatever does write it is DXE/SMM code or the TSE itself, and
neither is in an IFR dump. The issue asks "what sets it"; the honest answer
from this evidence is *the IFR names no writer at all*.

**Both suppressors test the sentinel.** `--question 0xE9F` prints the two
conditions in the dump that read it, and both are the same expression:

| suppressor | in form | condition |
|---|---|---|
| `:397` | `0x2712` "Advanced" (the vendor's) | `EqIdValList QuestionId: 0xE9F, Values: [65535]` |
| `:1673` | `0x2718` "Advanced" (the stock one) | `EqIdValList QuestionId: 0xE9F, Values: [65535]` |

`0xFFFF` is not a page count any form set would produce; it is the "no dynamic
pages" value. So this variable is not a knob that reveals pages by being given
the right number — it is a flag that *suppresses* a breadcrumb when it holds
the sentinel, and the interesting question is what puts it there at runtime.

**`0xE9E` is the same shape on the neighbouring store.** It is
`DriverHlthEnable` on VarStore `0x34` at `:27207`, in the same `DisableIf`,
tested as `[65535]` by a third suppressor at `:1679`. The pair is what makes
this a stock AMI TSE idiom rather than a vendor invention, and it is held in
`test_ifr_refgraph.py` as the pair it is. `DriverHlthEnable` gates the Driver
Health page, which `0x2718` links at `:1681` — the two variables and the two
pages are one mechanism, an AMI driver-health-count arrangement, not a
vendor-invented page switch.

## The routes to `0x2718`

`bios/tools/ifr_refgraph.py --form 0x2718` prints every `Ref` in the dump that
targets the form, each with its enclosing condition blocks resolved. There are
two, and the issue's account of the second is wrong:

| referrer | from | gated by |
|---|---|---|
| `:66` | form `0x2710` "Setup", the stock root | nothing — no enclosing condition block |
| `:1675` | form `0x2718` **itself** | `SuppressIf` at `:1673`, `EqIdValList QuestionId: 0xE9F, Values: [65535]` |

**Correction to the issue: the second `Ref` is not in `0x2717`.** The issue
places it "in a `Ref` in `0x2717`". Form `0x2717` "Main" (`:1500`–`:1612`)
contains no `Ref` opcode at all — `--form 0x2717` returns the root's tab `Ref`
at `:65` and nothing else. The `Ref` at `:1675` sits inside `0x2718`, which
opens at `:1613`.

That is not a detail, because it changes what the referrer *is*. A `Ref` from
`0x2717` into `0x2718` would be a third route in, gated on the sentinel: leave
`0xE9F` unset and you could walk from Main into the stock Advanced. A `Ref`
from `0x2718` to `0x2718` is not a route in at all — it is the AMI dynamic-page
breadcrumb, a link the page carries to re-render itself, and it is suppressed
exactly when the sentinel is set. So the stock Main page does **not** lead to
the stock Advanced page, and the question's premise that it does is withdrawn.

**The first `Ref` is ungated, and that is a statement about the IFR.** The six
`Ref`s at `:65`–`:70` are `0x2710`'s tab list — Main, Advanced, Chipset,
Security, Boot, Save & Exit — and each is re-read from its opcode bytes and
checked to be under no `SuppressIf`/`GrayOutIf`/`DisableIf`. So *within this
form set*, nothing gates the stock tab list.

That is not the same as "the tabs are reachable". Which forms are shown as
top-level tabs is decided by `AMITSE`, not by the IFR, and `AMITSE` is not
decompiled (below). The honest reading of the first row is: **the gate on this
route, if there is one, is not in the IFR.**

## Which routes need no reflash

The issue asks which routes exist that do not need one. Per route, on the
committed evidence:

| route | status |
|---|---|
| The TSE opens root form `0x2710`, whose six tabs carry no condition | **not established.** The six `Ref`s at `:65`–`:70` are ungated, which is a fact about the IFR and not a claim the page is reachable. `0x2710` has no incoming `Ref`, which is what a TSE-opened root looks like — and also what an orphan looks like. Settling it needs the `AMITSE` decompile. |
| Set `DynamicPageCount` to a real page count | **not established, and the IFR works against it.** The variable lives in a `DisableIf(True)` block, so the form set states no path that writes it. Whether the OS can reach the store is separately unresolved — §6 establishes boot-services-only for the five stores it names, not for this one, and this one is absent from the OS-visible variable list while thirteen others are (below). `0xFFFF` is the sentinel, not a count. |
| Enter Advanced via the suppressed self-`Ref` at `:1675` | **not a route in.** It points at `0x2718` from inside `0x2718` and is suppressed exactly when the sentinel is set. It is a breadcrumb for a page you are already on. |
| Enter Advanced via a `Ref` in `0x2717` | **does not exist.** Form `0x2717` holds no `Ref` opcode. This corrects the issue's premise rather than answering it. |
| A `UniWillVariable` flag, as with the memory menu (§8) | **not found by this method.** `UniWillVariable` occurs zero times in the Setup dump and no `VarStore` line declares it — the scoped negative `bios/ifr/README.md` already records and `test_ifr_census.py` already holds. `DynamicPageCount` is on its own GUID `B63BF800-…`, not an alias of `UniWillVariable`, so §8's trick has no obvious analogue here. |

Every row is negative or open. That is the answer, and it is stated per route
rather than as a hedge below the table because the difference matters: a
candidate that is *not established* and a candidate that *does not exist* are
different findings, and a reader deciding whether to spend an afternoon on one
needs to know which they are looking at.

## What the variable list does and does not show

The issue's proposed procedure — check whether a `DynamicPageCount` variable
appears in the live variable list, and read it before and after entering setup
— rests on an assumption about the list that the list does not support.
`evidence/uefi/2026-09-19-variable-list.txt` is the **OS-visible** list, and
`grep -cw` returns zero for each of eight VarStore names this dump declares:
`Setup`, `CpuSetup`, `PchSetup`, `SaSetup`, `MeSetup`, `AMITSESetup`,
`DynamicPageCount` and `DriverHlthEnable`. The runtime `UniWillVariable`,
`OcSetup` and `HiiDB` are present. (`Setup` and `CpuSetup` do occur as
*substrings* — of `SetupMode`, `SetupCpuFeatures`,
`AmiHardwareSignatureSetupUpdateCountVar` and `CpuSetupVolatileData` — which is
why this is a whole-name reading and not a `grep` count.)

**That absence is unexplained rather than explained, because the list is not
blind to this dump's VarStores.** Thirteen others it declares *are* present as
whole names: `PlatformLang`, `PlatformLangCodes`, `Timeout`, `BootOrder`,
`SetupCpuFeatures`, `CpuSetupVolatileData`, `NBGopPlatformData`, `VendorKeys`,
`SetupMode`, `SecureBoot`, `AuditMode`, `DeployedMode` and `FixedBootGroup`. A
list that shows those would have shown `DynamicPageCount` had it been a store
the OS can see, so its absence is an observation about that store rather than a
property of the list.

**§6 covers the other names, not this one.** `docs/findings.md` §6 says AMI's
`Setup`, `SaSetup`, `PchSetup`, `CpuSetup` and `MeSetup` "are boot-services-only,
so neither Windows nor Linux can read or write them after boot" — a claim about
those five names, reached from their own absence. `DynamicPageCount` is on its
own GUID `B63BF800-…`, is not among them, and §6 makes no claim about it. This
write-up therefore does **not** claim the OS cannot reach it.

What survives is a fork this evidence does not close: `DynamicPageCount` is
boot-services-only like §6's five, or it is a store this dump declares that the
OS-visible list did not show. Nothing here distinguishes the two, and no row of
the route table above depends on choosing. What the fork does settle is the
procedure: a live variable-list read is not the observation that bears on the
routes, so the procedure below is re-scoped to the rendered menu — which the
IFR does constrain, and which both readings leave intact.

## What `AMITSE` would settle, and why it is not done here

`AMITSE` picks the top-level tabs, and answering "does it open `0x2710` here"
means reading it. It is **absent from `bios/ghidra/manifest.csv`** — no
`AMITSE`/`AmiTse` row in any casing — so it is *not decompiled*. That is a
different statement from the one `bios/ifr/README.md` records, which is that
`AMITSE` and `AMITSESetupData` **carry no HII package**; both are checked and
kept distinct, because "the module has no forms" and "the module has not been
decompiled" support different conclusions.

Adding it means `bios/tools/bios_extract.py --mode rebuild-project`, which
writes the committed BIOS project database, and `.gitattributes` marks
`*.gpr`/`*.rep` `-merge` precisely so that two branches which both rebuild one
refuse to merge rather than text-merging a database. With several agent pull
requests open, that is a collision this issue does not need to cause. The
command is recorded here so the follow-up needs no re-derivation:

```sh
python3 bios/tools/bios_extract.py --mode rebuild-project
```

**What it would answer:** whether `AMITSE` opens `0x2710` or the vendor's
`0x2711`, and whether it consults `UniWillVariable` (which the issue notes it
references by GUID, and which §8's memory-menu unlock depends on). That is the
one open question in this write-up with a known way to close it.

## Prepared procedure — NOT RUN

Nothing below has been performed. There is no laptop and no Windows machine
reachable from where this was written, and **no step here has produced an
observation.** It is written so a human at the machine can run it, and so the
one thing the IFR cannot say gets said.

The procedure is about the **rendered menu**, not about reading a variable:
`DynamicPageCount` is not in the OS-visible list at all, so there is nothing
recorded there to read, and — as the section above sets out — its absence
settles nothing either way.

1. Enter the BIOS setup the way this machine's own documentation or boot menu
   says to — **the hotkey is not recorded anywhere in this repository**, so
   take it from the vendor's spec rather than from this write-up, and note
   which key was used. Photograph the top-level tab list as it renders. Record
   it verbatim before touching anything.
2. Record which tab set it is: the stock one (`0x2717`–`0x271C`) or the
   vendor's (`0x2711`–`0x2715`). This is the observation that bears on the
   first route row, and it is a menu observation because the IFR cannot supply
   one.
3. If a *stock* Advanced tab appears, enter it and record whether the
   `OverClocking Performance Menu` (`0x27AA`, linked at `:1630`) is present and
   whether it opens. That page is the reason issue #119 wants `0x2718`, and
   this is the only route to it that no reflash could not also provide.
4. If no stock Advanced tab appears, stop there. Do **not** attempt to create
   one, and do not modify any variable to try: the evidence above says the IFR
   states no writer for `0xE9F`, so a write would be a blind write into a
   store whose accessibility this evidence does not settle.
5. Whatever is observed, record it in a new file under `evidence/` with the
   date and the ROM version, and open a follow-up issue citing it. A menu
   observation contradicts nothing here; it can only close the "not
   established" rows above.

## Reproducing every figure here

Each row of each table is a command, not a remembered number:

```sh
python3 bios/tools/ifr_refgraph.py --question 0xE9F    # the resolution, both suppressors
python3 bios/tools/ifr_refgraph.py --form 0x2718        # the two referrers and their gates
python3 bios/tools/ifr_refgraph.py --form 0x2717        # the correction: no Ref in it
python3 bios/tools/ifr_refgraph.py --roots              # forms no Ref names
python3 bios/tools/ifr_refgraph.py --check              # the reader against the dump
```

The tool reads only the committed dump — no ROM, no UEFIExtract, no
ifrextractor, no Ghidra — so every claim here is re-derivable from files in
review. `bios/tools/test_ifr_refgraph.py` holds each of them, and
`ifr_refgraph.py --self-test` holds the parsing against a hand-built fixture
where the answers are known.

**One note on scope.** `--roots` is deliberately not presented as a way to
identify a TSE-opened root. It reports forms that no `Ref` in this dump names,
and this dump holds several that are plainly not orphans (`0x2711` "Main",
`0x2713` "Security", `0x2714` "Boot" are the vendor's own pages, reached from
code rather than from a `Ref`). "No incoming `Ref`" is a statement about the
dump. `--orphans` is that set without `0x2710`, and is labelled "not reachable
by any `Ref` in this form set" — never "dead".
