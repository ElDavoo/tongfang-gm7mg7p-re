# `EC_ADDR_FAN_DEFAULT` is the CPU TCC offset, not a fan-curve default

The standalone form of the note
[`power-profile-gm7mg7p.md`](../../docs/findings/power-profile-gm7mg7p.md)
carries in one line — *"`0x0786` is not the fan default … prose in the PR body,
not part of this patch"* — with the byte-level evidence that line did not have.

**Nothing here is submitted.** No pull request, issue or comment has been
opened against `Wer-Wolf/uniwill-laptop` or anywhere else; issue #10 owns the
submission and a human does it. See `CLAUDE.md`.

## 1. The upstream quote, verbatim

From `uniwill-acpi.c` at `BASE_COMMIT` (`5a24248`), lines 254-255, quoted in
[`upstream-excerpt.txt`](gm7mg7p-dmi-entry/upstream-excerpt.txt) (a partial
quotation, so the excerpt's own line numbers are not a stable citation):

```c
  254: #define EC_ADDR_FAN_DEFAULT		0x0786
  255: #define FAN_CURVE_LENGTH		5
```

Read together those two lines describe a five-element array of default fan
curve values based at `0x0786`. The pair is the whole of the disagreement: a
fan-curve default is something the EC *indexes with*, and the two lines are
the only place in the driver where `0x0786` is given that meaning.

**At `5a24248` neither constant is referenced anywhere in the tree.** Each
occurs exactly once, at its own `#define`, and `0x0786` appears nowhere else in
`uniwill-acpi.c` — so at that commit upstream has no read or write path to the
address, and this is a rename with no behavioural consequence to reason about.
An absence is not quotable out of the excerpt, so here is the scan instead, in
a throwaway checkout outside this repository. Run once, on 2026-10-02:

```console
$ cd <throwaway> && git init -q . && git fetch -q --depth 1 \
      https://github.com/Wer-Wolf/uniwill-laptop 5a24248f6422a0b673a47cbfd65e19a98eb4c8a9 \
      && git checkout -q FETCH_HEAD
$ git rev-parse HEAD
5a24248f6422a0b673a47cbfd65e19a98eb4c8a9
$ grep -rn 'EC_ADDR_FAN_DEFAULT\|FAN_CURVE_LENGTH\|0x0786' .
./uniwill-acpi.c:254:#define EC_ADDR_FAN_DEFAULT		0x0786
./uniwill-acpi.c:255:#define FAN_CURVE_LENGTH		5
```

The rev is the one `linux/patches/BASE_COMMIT` pins, so re-running those two
lines with the rev read out of that file is the whole re-check. Two limits are
worth stating rather than leaving for a reader to infer. It is a recorded run
and not a gate: `upstream-excerpt.txt` is a deliberate partial quotation (per
[`dmi-descriptor-evidence.md`](../../docs/findings/dmi-descriptor-evidence.md)),
the whole 90 KB file is not vendored here, and no offline gate fetches it — so
the excerpt could never have shown this absence, and nothing re-derives the grep
above. And it is scoped to the commit named: a later upstream commit may well
reference the address, and this says nothing about one. What is claimed is what
`git rev-parse HEAD` printed in the block.

## 2. What the EC's own bytes do with the address

Bank0 `0x9492`-`0x94A9`, from the committed
[`948D.asm`](../../ec/decompiled/bank0/948D.asm):

```
9492     90 07 86 mov      DPTR, #0x786
9495     e0 - -   movx     A, @DPTR
9496     30 e7 11 jnb      0xe7, 0x94aa     ; bit 7 clear -> the byte is ignored
9499     90 07 41 mov      DPTR, #0x741
949C     e0 - -   movx     A, @DPTR
949D     30 e0 0a jnb      0xe0, 0x94aa     ; AP_OEM bit 0 clear -> ignored
94A0     90 07 86 mov      DPTR, #0x786
94A3     e0 - -   movx     A, @DPTR
94A4     54 7f -  anl      A, #0x7f         ; strip the enable
94A6     90 0a 4a mov      DPTR, #0xa4a
94A9     f0 - -   movx     @DPTR, A         ; replace the computed TCC target
```

Three things a fan-curve element would not do:

1. **The top bit is an enable, tested before anything else and then stripped.**
   `FAN_CURVE_LENGTH 5` wants five data bytes; this reserves one bit of the
   first for a gate that gates itself.
2. **The value replaces rather than indexes.** `0x0A4A` already holds a TCC
   target that was selected by bracketing `GPU_TEMP` (`0x044F`) against a CODE
   table. `0x0786 & 0x7f` overwrites it. No addition, no comparison, no address
   built from the byte — all three of which a five-element array at this base
   would need.
3. **It is the same routine that seeds the per-mode TCC defaults.**
   `seed_tcc_defaults_from_ba36` (`0x9334`) writes `MODE_TCC_OFFSET_DEFAULTS`
   at `0x07D8`/`0x07D9`/`0x07DA` and then runs straight into the block above,
   so the selected per-mode default is what this byte overrides.

The full walk, its caveats, and what it does *not* establish are in
[`xdata-0786-tcc-offset-verdict.md`](../../docs/findings/xdata-0786-tcc-offset-verdict.md).

## 3. The same address under two other names

| source | spelling | reading |
|---|---|---|
| this machine's DSDT `ECMG` field list | `APTC` (7 bits) + `APTN` (bit 7) | CPU TCC offset with an enable bit |
| Control Center Service 3.1.39.0, `MyFanManager_RamFan1p5.SetCpuTccOffset` | `1926` | CPU TCC offset, written `value \| 0x80` |
| Control Center Service 3.1.39.0, `MyFanManager*.GetFanTablePWMDefault` | `1926`-`1930` | five default-PWM values, read into `DefaultPWM` and used as PWM |
| ECSpec 3.1.6.0 and 3.1.39.0 | `ADDR_L1_PWM_DEFAULT_MYFAN3 = 1926` | fan default — and `GetFanTablePWMDefault` reads that block as a fan default in the same build |
| upstream `uniwill-laptop` | `EC_ADDR_FAN_DEFAULT`, `FAN_CURVE_LENGTH 5` | fan default, unreferenced upstream |

So the EC agrees with the DSDT and with `SetCpuTccOffset` on 3.1.39.0, and
disagrees with two constants — one of which the same service version honours
the other way. Upstream's is the odd one out: nothing at `5a24248` reads or
writes the address at all, so the rename has no upstream behaviour to preserve
either way. On the vendor side the block is read **both** ways and this note
does not claim to settle which the vendor intended; the upstream argument does
not depend on it, because it rests on what the EC's own instructions do with
the byte.

## 4. Draft upstream PR body

Drafted to be lifted verbatim by whoever submits. Per
[`gm7mg7p-power-profile/PR_DESCRIPTION.md`](gm7mg7p-power-profile/PR_DESCRIPTION.md),
this is a rename on its own, and the two prepared patches for this board
should not carry it:

> **Rename `EC_ADDR_FAN_DEFAULT` to the CPU TCC offset**
>
> `EC_ADDR_FAN_DEFAULT` (`0x0786`) is not a fan-curve default on the boards
> where I have checked it. In the TongFang GM7MG7P / GM5MG7Y EC firmware it is
> the CPU TCC (thermal control centre) offset, with bit 7 as an enable rather
> than data, and `FAN_CURVE_LENGTH 5` describes an array this EC does not have
> at that address.
>
> The EC firmware at bank0 `0x9492`-`0x94A9` reads the byte behind a `jnb`
> on its own bit 7, tests `AP_OEM` (`0x0741`) bit 0, and stores
> `0x0786 & 0x7f` over an already-computed TCC target in `0x0A4A`. The value
> replaces that target; nothing indexes with it, adds to it, or builds an
> address from it. It sits in the routine that also seeds the per-mode TCC
> offset defaults (`0x07D8`-`0x07DA`), and overrides the selected one.
>
> This is corroborated from two independent directions on that board: the
> DSDT's `ECMG` field list declares `APTC` as 7 bits followed by a 1-bit
> `APTN`, and the vendor's own service writes `value | 0x80` to the same
> address from a method called `SetCpuTccOffset`. In the driver as of
> `5a24248` — the base this diff applies to — neither constant is referenced
> anywhere in the tree, so there is no upstream behaviour to preserve either
> way and the change is a rename plus its uses.
>
> One caveat I do not want to paper over: that same vendor service *also* reads
> `0x0786`-`0x078A` as a five-element array of default fan PWM values
> (`GetFanTablePWMDefault`, in three of its fan-manager classes, each feeding a
> `DefaultPWM` field that is then used as PWM). So on this board the block is
> read both ways — as a TCC offset and as a fan curve — and I cannot tell you
> from the decompilation which the vendor intended. What I can show is that the
> *EC* never treats the address as a base: no site adds to it, indexes it, or
> builds an address from it, which is what the array reading would require.
> That is the whole basis of the rename.
>
> The read is static. I have not written the address on hardware and confirmed
> the EC acts on it; what I have is the instruction sequence, which is
> unambiguous about the shape of the value. If you would rather not take a
> static-only claim, this is easy to hold — but the name is wrong for at least
> this board, and the fix is a `#define` and its uses.

**Scope this change should keep.** A rename plus its uses, nothing else.
Whether `FAN_CURVE_LENGTH` has any correct use elsewhere is a separate
question, and the sibling block at `0x0787`-`0x078D` on this board is open —
do not fold either into this.

## 5. Calibration

- **This is a static claim.** `0x0786` stays `present-untested` in
  [`registers.yaml`](../../ec/annotations/registers.yaml); nothing in this note
  moves a status, because nothing here is a live test of the byte. What would
  move it is a live write with bit 7 and `0x0741` bit 0 both set, reading
  `0x098C` and `0x0463` back — a human's step at the machine, described in
  [`xdata-0786-tcc-offset-verdict.md`](../../docs/findings/xdata-0786-tcc-offset-verdict.md) §6.
- **"Four direct sites" means four by these methods.** A store through a
  run-time-built DPTR is invisible to both `scan_refs.py` and
  `trace_xdata_refs.py`, and the indirect-XDATA scan resolves none of its
  anchored `movx @Ri` sites in this image. Not found by this method, never
  absent.
- **The `live` reading settles nothing.** The 2026-09-23 capture records
  `0x00`, and per `jnb 0xe7` a `0x00` byte is one the EC ignores outright —
  consistent with this reading, and not evidence for it.
- **The upstream scan in §1 is a recorded run, not a gate.** It was run once,
  against the rev `BASE_COMMIT` pins, and §1 carries the commands. The
  committed excerpt cannot stand in for it: reading an absence out of a partial
  quotation is the mistake, and it is scoped to that one commit.
- **The temperature bracketing is on the other side of the override.** The
  consuming path is temperature-*shaped*; `0x0786` itself is not
  temperature-*indexed*. Keeping those apart is what the fan-curve reading
  would erase, so the PR body above says "replaces" and not "is selected by".
