# The unaligned `MMRD` escape, and the two sources that would have to say it is safe (issue #439)

The write-up for [issue
#439](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/439), which is
#147's literal question made askable. `ecrw.py` now has a
`read_dword_unaligned` and an `mmrd` command that issue exactly one `MMRD` at
an unaligned EC offset, and `manual_fan_ctrl_probe.py`'s docstring carries the
runnable command beside the aligned ones. That is the whole of the change.

**Nothing here is evidence about the machine.** No Windows box was reached, no
EC was opened, no `MMRD` was issued, and no register was read. The escape has
never met the driver on this machine or any other, exactly as the `--block`
path it sits beside has not. What follows is what the committed DSDT says, what
a grep of it did not find, and the two sources this repository does not hold
and would need before the question could be answered without a human.

---

## What the ASL says

`MMRD` is one line, and it adds nothing:

```
Method (MMRD, 1, NotSerialized)                    # dsdt.dsl:50481
{
    Local1 = MMRW (Arg0, Zero, 0x02, Zero)         # :50483
    Return (Local1)
}
```

`Arg0` reaches `MMRW` unchanged, which is the whole reason
`ecrw.py:read_dword` adds `EC_BASE` itself where `ECRR` does not have to:
`ECRR` computes `Local0 = (0xFE410000 + Arg0)` at `:50499` and passes *that*,
where `MMRD` passes the operand it was given. The window the address has to
fall in is declared once, at `:52193`:

```
OperationRegion (ECMG, SystemMemory, 0xFE410000, 0x00010000)
```

`MMRW` opens its own region at exactly the address it is handed
(`:50423`, `OperationRegion (MMNM, SystemMemory, Arg0, 0x04)`) and declares
`MM32, 32` over it (`:50436`). The access is a 32-bit `Field` read with
`ByteAcc` and `NoLock`, guarded by `Acquire (UWOL, 0xFFFF)` and released at
`:50471`.

## What a grep of the DSDT does not find

Nothing in `MMRW` tests the alignment of `Arg0`. It reads the width out of
`Arg1`/`Arg2` and dispatches on those; there is no branch on `Arg0 & 3`, and
`MMRD` does not test it either.

Two greps of the committed 53,349-line `evidence/acpi/dsdt.dsl` back that up,
and both are worth stating in the form CLAUDE.md asks for: **not found by this
method.** `grep -ci Assert` returns 0 — the dump contains no `Assert`
statement, so there is no ASL-level operand assertion anywhere in it to
constrain this. `grep -in align` returns nothing at all. Neither result is a
statement that the ASL permits an unaligned `MMRD`; it is a statement about one
text file, and the rule that would decide the question is not in that file.

## The two sources this repository does not hold

**The ACPI specification.** Its text is not committed here, so nothing in this
repository says what it requires or allows of an unaligned `SystemMemory`
operand, and this write-up does not paraphrase it from memory. Per the
calibration rule: not found by this method, and importing the specification is
a separate act with its own provenance.

**The Windows ACPI driver.** `ACPI.sys` is not in the tree either.
`windows/decompiled/native/` holds the *vendor's* `ACPIDriver`, which is the
thing that receives the IOCTL and hands the operand down as a physical address
— it is not the component that interprets the AML. So whether Windows splits an
unaligned operand into byte accesses, faults on it, or loads a `Field` at an
odd offset and lets it stand is **not established here**, and no static reading
of `ACPIDriver.sys` can settle it, because that file is on the other side of
the boundary.

Those two are the reason the escape exists rather than a note saying the
access is safe. The answer is a human at the physical machine with the vendor
driver loaded and an elevated shell.

## The escape's shape, and the three decisions in it

`Ec.read_dword_unaligned(addr)` and the `mmrd ADDR` command. Three choices are
worth a reader's attention because the alternatives were available and each
would have changed what the tool could do by accident.

**A separate method, not a keyword on `read_dword`.** `readmany` calls
`read_dword` at every block it covers, so a `read_dword(addr,
allow_unaligned=True)` puts an unaligned four-byte access one argument away
from every `--block` sweep in this repository — and an unaligned dword is a
four-byte access whose last byte is somewhere else, which over the fan-tach
page is precisely the access #94 is about. A distinct name makes the aligned
path incapable of it by construction rather than by discipline.
`test_the_escape_is_the_only_unaligned_mmrd_any_block_path_issues` sweeps all
three real watch sets and asserts every offset any of them puts on the wire is
4-aligned; that is the check, and it is the one that would catch a leak.

**The command line takes an EC offset; `EC_BASE` is added in the tool**, so
`ecrw.py mmrd 0x0751` and not `0xFE410751`. Every other command in the file
speaks EC offsets (`read 0x7b9`, `dump 0x0700 0x100`) and the tool exists to
do the addition the ASL does not; making one command speak physical would put
the arithmetic on the operator for no gain.

**One address, one IOCTL.** Not `nargs="+"`. What makes this an escape rather
than a second sweep path is that it issues exactly one `MMRD` and does nothing
else; a multi-address form is a trivial follow-up and is left out on purpose
rather than by omission.

The bound is the other half of what the method does *not* change. Alignment is
loosened and the window is not: `addr + 3` must still land inside
`0x0000-0xFFFF`, so the last unaligned start accepted is `0xFFFD`, and
`0xFFFE`, `0x10000` and negatives raise the same `ValueError`, before any
IOCTL, that `read_dword` raises.

## What the output deliberately does not say

`ecrw.py mmrd 0x0751` prints the physical address and the four bytes, and
nothing else:

```
0xFE410751: 51 52 53 54
```

**No little-endian integer rendering, and no per-byte EC-offset labels.**
Labelling `buf[0]` as the byte at `0x0751` is the reading under test —
`windows/native/ACPIDriver.sys.analysis.md` says so, that the copy-back is
four byte stores out of the ACPI output buffer in the order that buffer holds
them and that ACPI materialises an integer result little-endian, so `buf[0]`
*is* the lowest of the four. A tool that printed the offsets would make its
own output a confirmation of that reading rather than a measurement of it, and
a human comparing two lines would be comparing an assumption with a
measurement. So the four bytes come back bare and the comparison to make is
against the aligned `dump 0x0750 0x08 --block` line beside them.
`test_the_mmrd_command_prints_the_physical_address_and_four_bare_bytes`
asserts the whole line, so a label added later fails rather than passing
quietly.

That reading's status is unchanged by this work. Nothing here issued an
`MMRD`; the analysis file's "What this does not establish" list is exactly as
true as it was, and this is one more reason it is.

## What this does not settle

**#94.** The escape touches no watch set and adds no address to any of them, so
no sweep's read count or byte count moves and nothing in the probe's committed
arithmetic had to be restated. #94 is still the open question of what this
traffic does to a fan, and a readback that matches is still not evidence the EC
acts on a four-byte access the way it acts on a byte one (CLAUDE.md). An
unaligned `MMRD` that returns plausible bytes would be a result about the
access width; it would not be a result about the flag, and it would not make a
wider read safe across the window.

**The hardware answer.** Whether the BIOS returns anything at all for an
unaligned operand, in what byte order, and whether the ACPI driver splits it,
faults on it or refuses it, is a human at the physical machine, with the
vendor stack's driver loaded and an elevated shell — no laptop and no Windows
box is reachable from this pipeline. What is committed here is that the
question can be put, and not what it answers to.
