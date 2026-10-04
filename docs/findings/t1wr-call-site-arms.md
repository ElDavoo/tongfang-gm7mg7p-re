# No committed Windows input calls T1WR, and the CPU power limits do not go through it either

(Issue #1343. Static reading of committed files: the decompiled C# trees, the
Ghidra decompiles of the driver and its DLL, the `evidence/acpi/dsdt.dsl`
dump, and a `disasm.sh` listing of every committed PE. No laptop, no EC, no
Windows machine and no register readback is involved: every claim below is a
reading of a file in this repository, and each is given with the command that
produces it. `windows/tools/t1wr_sites.py --self-check` re-derives the four
structural facts the answer rests on and exits non-zero if any of them moves.)

`windows/tools/t1wr_callers.py` (issue #131) searched for a caller of `T1WR` by
**argument value** and found none. Its own source says why that search has to
stop: thirteen of `T1WR`'s nineteen `Arg0` values are two hex digits and three
decimal ones, and each was measured against the committed trees before being
left out — `0x81`-`0x85` collide with `ECSpec.User_Fan_Level1`..`Level5`, and
`0x83`-`0x85` with ILSpy's own `Invalid MethodBodyBlock: Invalid method header`
markers. A search that cannot tell a `T1WR` argument from a fan level is not a
search.

**This is the other direction, and it reaches the same negative by a method the
first one could not use.** Reading by call site rather than by value is
possible because the kernel handler fixes the input-buffer layout, and that is
what converts "which nineteen values were searched for" into "which arm does
this call land on".

## The reading key: a caller's `Arg0` is the first four bytes of its buffer

`ACPIDriver.sys`'s `0x9C40A4DC` handler is `FUN_140002614`, reached from the
dispatch chain in `windows/decompiled/native/ACPIDriver.c`. It reads
`*(undefined1 **)(param_2 + 0x18)` — the IRP's `SystemBuffer` — and builds the
ACPI evaluation buffer itself (excerpt, with the middle bytes of each run
elided; `0x52573154` is `'T1WR'` and `0x43696541` is `'AeiC'` read back
little-endian):

```
  local_424 = 0x52573154;                              // 'T1WR' as an immediate
  local_41c = 3;                                       // ArgumentCount
  local_420 = 0x28;                                    // Length
  _local_418 = CONCAT17(puVar1[3],CONCAT16(puVar1[2],CONCAT15(puVar1[1],CONCAT14(*puVar1,0x40000))));
  local_410 = 0x40000;
  local_40c = puVar1[4]; ... local_409 = puVar1[7];
  local_408 = 0x40000;
  local_404 = puVar1[8]; ... local_401 = puVar1[0xb];
  local_428 = 0x43696541;                              // 'AeiC'
```

So the three arguments are `SystemBuffer[0..3]`, `[4..7]` and `[8..11]`, each
with `Length = 0x40000`. **A caller's `Arg0` is what it put in the first four
bytes of the twelve-byte buffer** — a fact about the call site, not about a
value that could be a fan level somewhere else in the tree.

`t1wr_sites.py`'s `parse_handler_layout()` re-derives those slices from the
decompile rather than asserting them, and the suite holds the result against the
file. This is the one place the answer is load-bearing, so a re-export that
changed which offsets the handler reads would fail there rather than quietly
change what "Arg0" means.

One shape worth recording, because it is why the search can be scoped to one
IOCTL at all: the three `TempWrite` handlers are not the same function.
`T1WR`'s and `T2WR`'s build the evaluation buffer word by word as above;
`TempWrite3`'s handler instead `memcpy_s`s `0x80` bytes and passes
`ArgumentCount = 1`. That matches the DSDT, where `T3WR` writes one field
(`\_SB.INOU.T3PC`) and `T1WR` dispatches on three.

## Reachability, one row per `T1WR` arm

The table below is `windows/tools/t1wr_sites.py`'s own output. The arm list and
the `.dsl` line numbers are `ec/tools/dsdt_ec_fields.py`'s `T1WR_ARMS`, imported
rather than copied, so there is one answer to "which arms does `T1WR` dispatch
on" in this repository.

| `Arg0` | `dsdt.dsl` | reachable from a committed site | the arm reaches |
|---|---|---|---|
| `0x81` | `:50637` | no | `APL1` |
| `0x82` | `:50641` | no | `APL2` |
| `0x83` | `:50645` | no | — |
| `0x84` | `:50646` | no | `APL4` |
| `0x85` | `:50650` | no | `APTN`, `APTC` |
| `0x86` | `:50655` | no | — |
| `0x87` | `:50656` | no | — |
| `0x71` | `:50657` | no | — (reads nothing) |
| `0x1171` | `:50658` | no | `CTWA` |
| `0x71` | `:50667` | **unreachable** — see below | `CTWA` |
| `0x1172` | `:50675` | no | — |
| `0x1173` | `:50680` | no | `DBD1`, `DBD2` |
| `0x2273` | `:50693` | no | — |
| `0x73` | `:50700` | no | `DBEN`, `CPUA`, `DBAP` |
| `0x74` | `:50719` | no | — |
| `0x1175` | `:50720` | no | — |
| `0x75` | `:50725` | no | `WHMS` |
| `0x1176` | `:50730` | no | `CGCT` |
| `0x76` | `:50735` | no | — |
| `0x61` | `:50739` | no | — |

**Every row is "not found by this method."** That is the whole result, and the
method is one the by-value search could not run at all.

The `0x71` row at `:50667` is unreachable for a reason internal to the ASL
rather than to the search, and it is worth stating so a future table does not
count it as a second reachable arm: the `ElseIf ((Arg0 == 0x71)){}` at
`:50657` matches any caller passing `0x71` and leaves the chain before
`:50658` is tried, so a `T1WR(0x71)` caller reaches the first arm and **cannot**
reach the second. `dsdt_ec_fields.py`'s `T1WR_REDUNDANT` is that pair, and the
suite checks the reachability table against it.

## What the managed layer actually found

The three `ReadACPI`/`WriteACPI` call sites in the decrypted service, each
carrying the IOCTL as a literal at the call site, are the shape that makes the
search work at all:

| IOCTL | ACPI method | site |
|---|---|---|
| `0x9C40A488` | `ECRR` | `MyECIO/AcpiCtrl.cs:190`, `ReadACPI(2621482120u, …)` |
| `0x9C40A48C` | `ECRW` | `MyECIO/AcpiCtrl.cs:212`, `WriteACPI(2621482124u, …)` |
| `0x9C40A4A0` | `PCRD` | `MyECIO/AcpiCtrl.cs:236`, `ReadACPI(2621482144u, …)` |

None of them is `0x9C40A4DC`. That constant — `IOCTL_GPD_ACPI_TMPWRITE1 =
2621482204u` — is **declared** in the same file and passed to nothing: every
call to the one helper that could send it passes one of the three codes above.
This is a dataflow result rather than a term-list miss, which is the difference
that matters; `t1wr_callers.py`'s census counted the constant once and could not
say what it was or was not connected to.

`2621482204u`, `IOCTL_GPD_ACPI_TMPWRITE1` and `0x9C40A4DC` are one site rather
than three spellings, and the suite holds that — a tool that reported three
would be counting a spelling rather than a caller.

## The CPU power limits go through `ECRW`, not `T1WR`

The second question issue #1343 asks is whether anything in the committed
Windows stack writes `APL1`/`APL2`/`APL4` (`0x0783`-`0x0785`) or
`APTC`/`APTN` (`0x0786`) at all. The answer is yes, and it does not involve
`T1WR`.

`windows/decompiled/v3.1.39.0/ec-callsites.csv` is the committed census of the
writes: `SetPL1Value`/`SetPL2Value`/`SetPL4Value` write `0x0783`/`0x0784`/
`0x0785` and `SetCpuTccOffset` writes `0x0786`, and
`ec/annotations/registers.yaml` already names both sources. Those rows do not
say which IOCTL carries them, so the tool resolves it: `t1wr_sites.py`'s
`ioctl_of_method()` walks the callee chain from each writer until it reaches a
`DeviceIoControl`, which for all four runs
`SetPLxValue` → `EcCtrl.Write` → `MyEcCtrl.Write` → `AcpiCtrl.Write` →
`WriteACPI(2621482124u, …)` → `WriteEC`.

**All four addresses route through `0x9C40A48C`, `ECRW`.** That is the shape a
Linux driver wants: a plain byte write at `0xFE410000 + addr`, with no `T1WR`
dispatch and no three-argument buffer in the way. It is a routing fact — which
IOCTL carries the write — and it says nothing about what the EC does with the
value, which is what `registers.yaml`'s `present-untested` is for and what this
work does not move.

## The native layer

`ACPIDriverDll.dll`'s `TempWrite1` (`0x180003F80`) is the wrapper that issues
`0x9C40A4DC`, and the disassembly shows it plainly:

```
   180003f98:	89 0d 02 8d 27 00    	mov    %ecx,0x278d02(%rip)        # 0x18027cca0
   18000401d:	4c 8d 05 7c 8c 27 00 	lea    0x278c7c(%rip),%r8        # 0x18027cca0
   18000402c:	ba dc a4 40 9c       	mov    $0x9c40a4dc,%edx
   18000403f:	ff 15 f3 77 1c 00    	call   *0x1c77f3(%rip)        # 0x1801cb838
```

That is the **export itself**, not a caller of it, and the tool reports it that
way: it is a site that *issues* the code, its `Arg0` is whatever the caller
passed in `ecx`, and it is not resolved. `ACPIDriver.sys` compares against
`0x9C40A4dc` in its own dispatch — `cmp $0x9c40a4dc,%eax` — which is the kernel
comparing a code it received, not a site issuing one; the `mov $…, %edx` rule is
what keeps the two apart.

**No committed PE calls a `TempWrite*` export**, and no other committed PE
carries a `mov $0x9c40a4dc,%edx` site. The positive control rides along: the
DLL is known to define `TempWrite1`, so a native layer that found nothing there
would have read no listing rather than found nothing, and `--self-check` fails
if that probe comes back zero.

## What this does not establish

Every negative above is **"not found by this method"**, and the method is only as
good as the inputs it could reach. These are the ones it could not:

- **The still-encrypted 3.1.6.0 and 3.9.18.0 method bodies.** Re-decrypting
  them is `windows/antitamper/README.md`'s separate work; this tool names them
  as unreadable rather than reaching for them.
- **The installer payloads.** `setup.exe` and `UniwillService_3.1.6.0_STD.exe`
  are Inno wrappers; disassembling one gives the wrapper's code.
- **The UWP front end's native core.** The 27 MB `GamingCenter3_Cross` is staged
  out of the `.msixbundle` by `windows/tools/extract.sh` and is not a plain file
  under `vendor/`. Its `.appxsym` PDB is a name table, so a name there is not a
  call site — that input belongs to `t1wr_callers.py`'s by-value question, not
  to this one.
- **Anything in firmware**, including an ACPI component that calls `T1WR`. The
  DSDT only declares `\_SB.NPCF` `External`; no input in this repository can
  reach a caller there.

The tool prints this list with its output rather than burying it, and the
readability probes make a zero distinguishable from a scan that never opened the
file. `t1wr_callers.py`'s census and this one are **two closed negatives reached
by different methods**, which is why both are worth having: the by-value method
has a proven blind spot on thirteen of the arms, and the by-call-site method has
one of its own (it resolves one hop of wrapper forwarding and no further).

One hazard, bounded: `AcpiCtrl.WriteACPI` marshals eight bytes into its buffer
while the `T1WR` handler reads twelve, so a caller reusing that helper for
`T1WR` would under-fill it. That is a fact about two committed decompiles; what
the I/O manager does with the remainder is a runtime question and is not claimed.

## What it opens

- **The `0x75` / `WHMS` arm and the `0x1171` / `CTWA` pair** are now unreachable
  by *measurement* rather than by omission. If a Linux driver wants the EC's
  charge-limit write timeout or its CPU temperature warning threshold, `T1WR` is
  not the route from any committed Windows caller — so the question becomes what
  a direct write to those bytes does, which is `ec/annotations/registers.yaml`'s
  `present-untested` to answer and needs the machine.
- **The `ECRW` route is the one worth a driver.** `APL1`/`APL2`/`APL4` and
  `APTC`/`APTN` are written by the vendor stack through a plain byte write at
  `0xFE410000 + addr`. That is the shape `uniwill-laptop` already has for the
  rest of the EC, and this is the first measurement that the power-limit
  registers are reachable that way rather than only through an ACPI method.
- **The dispatch side is a separate question** and is untouched: what
  `MMRW`/`MMWB`/`MMWD`'s handlers do with their buffer is issue #1338, and this
  is the caller side of one IOCTL.

## Where the two shared files now point

`windows/native/ACPIDriverDll.dll.analysis.md`'s "Who calls `TempWrite1`" and
`windows/native/ACPIDriver.sys.analysis.md`'s "Which userspace process sends
these IOCTLs" both record the first negative, obtained by value. Each now says
that a second negative was obtained by a different method, so a reader does not
take the agreement of the two as a fact rather than as a coincidence of methods.
