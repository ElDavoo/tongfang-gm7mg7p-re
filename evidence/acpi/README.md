# ACPI evidence — the committed DSDT, and the interpreter source behind issue #1337

Two kinds of file live here, and the difference is the point.

The `dsdt.dsl` is **this machine's**: a full `iasl` disassembly of the DSDT
that the BIOS on this laptop shipped, committed because every claim about what
the ASL says is checkable against it offline.

The `.c.txt` excerpts are **not this machine's**: they are bounded, verbatim
fragments of two public interpreters' source, fetched at a pinned revision so
that issue [#1337](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/1337)
could be answered from outside the laptop. Each carries its own `Project:`,
`Revision:`, `Licence:` and `Retrieved:` header, and
`fetch-acpi-sources.sh` re-derives every fragment from a fresh fetch and diffs
it against what is committed, so a drifted excerpt reds rather than sitting
there quoting source that has moved.

Why fragments and not whole upstream files: a whole file is a decision rather
than a default, and a bounded excerpt reviews in a diff.
`linux/patches/gm7mg7p-dmi-entry/upstream-excerpt.txt` states the case, and
these excerpts follow the same convention — `sed -n A,Bp` ranges, upstream's own
line numbers reproduced as prefixes, so a line cited in a write-up means the same
line here and in the upstream tree.

Nothing in this directory is hardware evidence. No EC was opened, no register
was read, and no method was invoked; the excerpts are static reads of source
that has not been executed. The write-up that reads them,
`docs/findings/acpi-interpreter-region-access.md`, carries the null for the part
that cannot be answered from here.

The **ACPI Specification is deliberately not in this directory**, and that is a
licence decision rather than an omission: the UEFI Forum's notice on it is "All
Rights Reserved", with permission granted only for an implementer's internal
electronic copy or an unmodified print, neither of which is a transcription
committed to a public repository. It is cited to release, section and page in the
write-up instead, with the sentences the argument rests on quoted there.

## Files

- **`dsdt.dsl`** — the full disassembled DSDT. Referenced for the `ECMG`
  operation-region field-list gap around `0x07B9`, the cycle-count gated
  capacity-rescaling logic in `_BIF`/`_BST`, and the `INOU` utility methods
  `MMRW`/`MMRB`/`MMRD`/`MMWB`/`MMWD` that `ecrw.py`'s `mmrd` command reaches.
- **`acpica-region-access-excerpt.c.txt`** — the `SystemMemory` region handler,
  the `Field` access-type decode, the whole route a field read takes from the
  resolver to the address-space dispatch, and the field read loop, from ACPICA,
  the ACPI reference implementation. Carries the width switch that validates an
  access's *width* and the alignment test that is compiled out on everything but
  Itanium, and the access-width decoding that turns `ByteAcc` into one-byte
  accesses. The route fragments are there because "the field read is split" is a
  claim about a route: each hop is quoted so a reader can check the order rather
  than take it from the write-up. Retrieved from `acpica/acpica` at revision
  `e85aa3bebaae81ed1e6d163511ac7e1eafe732cf`.
- **`linux-acpi-region-access-excerpt.c.txt`** — the same decision points and
  the same route in the copy of ACPICA the Linux kernel builds under
  `drivers/acpi/acpica/`, plus the kernel's own `acpi_evaluate_integer`, which
  is the operating-system side of the boundary and the only part of it this
  repository's end product runs on. Retrieved from `torvalds/linux` at revision
  `ffc253263a1375a65fa6c9f62a893e9767fbebfa` (tag `v6.6`).
- **`fetch-acpi-sources.sh`** — re-derives both excerpts from a fresh fetch and
  diffs them against the committed files. **It needs the network and is
  therefore not part of any gate.** `tools/check_acpi_interpreter_sources.py`
  checks the same excerpts offline — provenance fields, and that every pointer
  the write-up makes into one of the `.c.txt` excerpts lands on a line that
  really contains the text it quotes, whether the pointer spells out the path
  or is a bare `:NNN` inheriting the one before it — and that is what a
  reviewer can run without egress. Pointers into `dsdt.dsl` are locators and
  are not held to that rule; the write-up's use of the DSDT is re-derived from
  the file separately.

## Licences

Both excerpts are quoted under the licence their own source file declares, and
each file names its identifier in its `Licence:` field. The identifiers come
from each upstream file's own `SPDX-License-Identifier` line, and because those
lines sit **above** every excerpted `sed` range they would not appear in the
fragments at all — so each excerpt carries a short fragment carrying its SPDX
line, which makes the header text rather than a claim about it what the
`Licence:` field rests on.

- **ACPICA** — `BSD-3-Clause OR GPL-2.0-only`, on line 10 of every file quoted
  (`exregion.c`, `exprep.c`, `exfldio.c`, `exresolv.c`, `exfield.c`,
  `actypes.h`, `acmacros.h`).
- **Linux** — two different identifiers, and the distinction is worth stating
  rather than rounding to one: the four `drivers/acpi/acpica/` files quoted are
  `BSD-3-Clause OR GPL-2.0`, and `drivers/acpi/utils.c`, also quoted, is
  `GPL-2.0-or-later`.

Quoting them here is what those licences permit, and nothing here
redistributes a build of either.