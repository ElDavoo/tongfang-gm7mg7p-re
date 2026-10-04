# What the ACPI interpreter does with an unaligned `MMRD`, and what it still does not establish (issue #1337)

`docs/findings/mmrd-unaligned-escape.md` closed with two named blanks. One was
the ACPI specification's text; the other was what the interpreter does with an
unaligned operand. It was right that neither is answerable from the ASL and the
vendor's `ACPIDriver.sys`: the ASL says what is *asked for*, and the vendor
driver sits on the other side of the interpreter boundary entirely. So the second
blank could only be closed by going to the interpreter itself.

This is that. Two interpreters whose source is public — ACPICA, the reference
implementation the specification is written against, and the copy of it the Linux
kernel builds — were fetched at a pinned revision into `evidence/acpi/` and read
for the two questions the issue asked, and the ACPI specification itself was
located and read for the part that governs them. Neither answer is the one the
question expected. The specification turns out to be silent about what to do with
a misaligned operand; the interpreters turn out to have no alignment test at all
— and also to split the access into four byte-wide reads before it ever gets that
far. Both of those are worth the queue slot on their own.

**Nothing here is evidence about the machine.** No Windows machine was reached,
no EC was opened, no `MMRD` was issued, and no register was read. What follows is
a static read of public source and what it says, and nothing about what this
laptop's interpreter does at run time. The interpreter source is in
`evidence/acpi/`, with its URL, revision, licence and retrieval date per file;
`evidence/acpi/fetch-acpi-sources.sh` re-derives both excerpts from a fresh fetch
and diffs them, and `tools/check_acpi_interpreter_sources.py` checks the same
evidence offline. The specification is cited and quoted rather than committed,
for a licence reason given where it applies.

---

## What the methods actually are, before "the specification" means anything

The issue asks about "the ACPI specification" as though it were one document. It
is not, and the committed DSDT says which part is even in play. Every line below
is checkable in `evidence/acpi/dsdt.dsl`, and
`tools/check_acpi_interpreter_sources.py` re-derives it rather than taking this
paragraph's word for it.

`MMRW`, `MMRB`, `MMRD`, `MMWB` and `MMWD` are **ASL method declarations, not AML
operators**. They are declared at `evidence/acpi/dsdt.dsl:50420`,
`:50475`, `:50481`, `:50487` and `:50492`, all in the body of a single device
opened at `:50374` and identified by hardware ID `INOU0000` at `:50376`. `MMRD`
adds nothing of its own — its whole body is a call to `MMRW` at `:50483` and the
`Return`.

`INOU` carries the rest of the AMI Aptio ACPI utility set alongside them — the
`UWOL` mutex at `:50378`, the `T1RD`…`T3WR` family, `SMRW`, `RIOP` — which is the
surface `windows/native/ACPIDriver.sys.analysis.md` catalogues. That identification
rests on the naming pattern and the `INOU0000` hardware ID, not on a vendor
document held in this repository; it is a reading, and the check measures the
structure it rests on rather than asserting the conclusion.

**The consequence, and it is the load-bearing one.** None of this is about the
core AML specification at all. What `MMRW` *uses* is core AML — `OperationRegion`,
`Field`, `Acquire`, the access keywords — declared at `:50422` (the `Acquire`),
`:50423` (the `OperationRegion`), and `:50424`, `:50429` and `:50434` (three
`Field` declarations). So "the specification text that is missing" is narrower
than the issue's phrasing and it is a different document: it is the core
specification's `Field` / access-width / operand-alignment text, plus whatever
AMI documents about the wrapper methods, and those are two documents with two
different provenance answers. Naming which document is missing at that
granularity is worth more than leaving "the specification" as one thing.

## What `MMRW` asks for, and what the interpreter does with it

```
OperationRegion (MMNM, SystemMemory, Arg0, 0x04)   # dsdt.dsl:50423
Field (MMNM, ByteAcc, NoLock, Preserve)            # :50424, :50429, :50434
{
    MM08,   8                                     # :50426
    MM16,   16                                    # :50431
    MM32,   32                                    # :50436
}
```

`Acquire (UWOL, 0xFFFF)` at `:50422` guards it and `Release (UWOL)` at `:50471`
unlocks. `MMRD` asks for `MM32` at whatever address it was handed. There is no
branch on `Arg0 & 3` anywhere in the method, which
`docs/findings/mmrd-unaligned-escape.md` already established and which nothing
here contradicts.

Three things decide what that becomes, and all three are read out of the committed
excerpt rather than from memory.

### Nothing in the region-access path tests the operand's address

`AcpiExSystemMemorySpaceHandler` is where a `SystemMemory` access of a given
width actually happens. It opens by validating **the width**, and the validation
is a switch over 8, 16, 32 and 64 —
`evidence/acpi/acpica-region-access-excerpt.c.txt:84` — `/* Validate and translate the bit width */`
— with everything else rejected as `AE_AML_OPERAND_VALUE`.

There is an alignment test in the function, and it is the only one in the path.
It is behind `#ifdef ACPI_MISALIGNMENT_NOT_SUPPORTED` at
`evidence/acpi/acpica-region-access-excerpt.c.txt:115` — `#ifdef ACPI_MISALIGNMENT_NOT_SUPPORTED`
— and computes the residue four lines below it, returning `AE_AML_ALIGNMENT` when
it is non-zero at `:123`. The flag is defined in one place, and it is defined for
Itanium only: `evidence/acpi/acpica-region-access-excerpt.c.txt:446` — `#define ACPI_MISALIGNMENT_NOT_SUPPORTED`
— under `#if defined (__IA64__) || defined (__ia64__)`, with a comment saying x86-64
supports misaligned transfers so there is no need to define it. This machine is
x86-64. So on any target this repository cares about that check does not exist in
the compiled binary.

With it compiled out, the access is a pointer derived from the address that was
asked for — `evidence/acpi/acpica-region-access-excerpt.c.txt:134` — `LogicalAddrPtr = Mm->LogicalAddress +`
— and then a load at that pointer. ACPICA's own comment above the load says
plainly that it does not break a wide transfer into byte-sized chunks, because
the AML asked for that width. `ACPI_GET32` is a bare dereference, and the macro
header above it warns: `evidence/acpi/acpica-region-access-excerpt.c.txt:482` — `* get into potential alignment issues -- see the STORE macros below.`

So for a width of 32 the answer to the issue's question is: a straight four-byte
copy at whatever address was handed down, with no alignment test anywhere on the
path. That is the answer for ACPICA.

It is also the answer for the kernel. Linux `v6.6` still carries ACPICA under
`drivers/acpi/acpica/` and builds it, and the copy is the same code with kernel
naming: the same width switch, the same
`#ifdef ACPI_MISALIGNMENT_NOT_SUPPORTED` at
`evidence/acpi/linux-acpi-region-access-excerpt.c.txt:100`, the same pointer
arithmetic at `:118`, the same `ACPI_GET32` at `:151`, the same warning in
`drivers/acpi/acpica/acmacros.h` at
`evidence/acpi/linux-acpi-region-access-excerpt.c.txt:439`. Two implementations,
one answer. That matters for the reason this issue exists: it is the difference
between "the interpreter might test alignment" and "the interpreter does not".

### But `MMRW` never asks for a width of 32

This is the part the issue did not anticipate, and it inverts the practical
conclusion. The `Field` declarations are all `ByteAcc`, and the access type is
decoded before any of this. `AcpiExDecodeFieldAccess` switches on the encoded
access type and returns the access granularity — and `AML_FIELD_ACCESS_BYTE`,
which is what `ByteAcc` encodes, returns 8, not the field's declared 32
(`evidence/acpi/acpica-region-access-excerpt.c.txt:204`, the case label, with
the `BitLength = 8` it returns four lines below it). `WordAcc`, `DWordAcc` and
`QWordAcc` are in the same switch, returning 16, 32 and 64. The return value
becomes `AccessByteWidth` at `evidence/acpi/acpica-region-access-excerpt.c.txt:267` — `ACPI_DIV_8 (AccessBitWidth);`
— and the width handed to the region handler is that access width times eight,
not the field's bit length: `evidence/acpi/acpica-region-access-excerpt.c.txt:324` — `ACPI_MUL_8 (ObjDesc->CommonField.AccessByteWidth), Value);`.
The kernel's copy is the same at
`evidence/acpi/linux-acpi-region-access-excerpt.c.txt:196` and `:261`.

The read reaches that code by a path worth naming, because "the field read is
split" is a claim about a route and not about a file, and every hop of it is in
the excerpt. An `ACPI_TYPE_LOCAL_REGION_FIELD` source object is dispatched to
`AcpiExReadDataFromField` at
`evidence/acpi/acpica-region-access-excerpt.c.txt:459` — `Status = AcpiExReadDataFromField (WalkState, StackDesc, &ObjDesc);`
— that calls `AcpiExExtractFromField` at `:467`, which is where a field read
becomes a value and where the access count is decided. Each datum then goes
`AcpiExFieldDatumIo` → `AcpiExAccessRegion` → the address-space dispatch: the
`AcpiExFieldDatumIo` call site for `AcpiExAccessRegion` is at `:337`, and the
dispatch the write-up quotes above is inside `AcpiExAccessRegion` — the
function's own banner and signature are at `:313`, which is what places the
`exfldio.c` 273-278 fragment there rather than in `AcpiExFieldDatumIo`. The
kernel's copy carries the same three hops at
`evidence/acpi/linux-acpi-region-access-excerpt.c.txt:374`, `:382` and `:275`.

`AcpiExExtractFromField` then decides how many accesses to issue. It has a
single-access shortcut, but it applies only when the field is exactly one datum
wide (`evidence/acpi/acpica-region-access-excerpt.c.txt:349` —
`(ObjDesc->CommonField.StartFieldBitOffset == 0) &&`), and a 32-bit field over a
byte-wide access granularity is four datums, not one: `DatumCount` rounds the
field's bit length up to the access width at
`evidence/acpi/acpica-region-access-excerpt.c.txt:371` — `DatumCount = ACPI_ROUND_UP_TO (`
— and the loop that follows issues one `AcpiExFieldDatumIo` per datum, advancing
the offset by `AccessByteWidth` each time.

**So `MMRD` at an unaligned address is four separate one-byte region reads at
four consecutive addresses, not one four-byte read.** The interpreter splits it
before the address ever reaches the width-sensitive load, because the ASL said
`ByteAcc` — which it says for all three of its fields, 8, 16 and 32 alike. An
unaligned `MMRD` is, in these two interpreters, exactly as expensive as four
aligned byte reads of the same four bytes.

That is a real result, and it is worth being precise about what it does and does
not license. It does not mean an unaligned dword is safe in general: the
four-byte path is real and is what a `DWordAcc` field would take, and that is
where the hazard above still bites. It means the specific escape this
repository added is not the case that was in doubt.

**And it is not only the escape.** `windows/tools/ecrw.py`'s `--block` sweeps
reach the EC through `MMRD` as well — `readmany` calls `read_dword`, which
issues `IOCTL_MMRD` — so on these two interpreters an *aligned* `--block` sweep
is four byte-wide region accesses too, not one four-byte access. That is the
correction recorded beside the two standing sentences that said otherwise,
`manual_fan_ctrl_probe.py`'s `block_span` and
`docs/findings/mmrd-unaligned-escape.md`; neither file's arithmetic changes, and
both keep the alignment discipline for reasons that are about what the *tool*
requests rather than about what the interpreter issues. It is also a statement
about *these two interpreters*, read from source, and not a measurement of this
machine's own interpreter — the gap is the subject of
[What this does not establish](#what-this-does-not-establish) below, and nothing
here has run on the machine.

## The byte order: which of the four is the lowest address

The second question was how a returned `Integer` is laid down in the output
buffer, which is the fact `read_dword_unaligned`'s docstring and
`windows/native/ACPIDriver.sys.analysis.md`'s little-endian reading both turn on.
It splits in two, and only one of the halves is the interpreter's to decide.

**The interpreter half, settled by the same read.** `AcpiExExtractFromField`
assembles the field least-significant-datum-first: the priming read is the datum
at offset zero and becomes the low bits —
`evidence/acpi/acpica-region-access-excerpt.c.txt:385` — `MergedDatum = RawDatum >> ObjDesc->CommonField.StartFieldBitOffset;`
— and each subsequent datum is shifted up by the access width before being merged
at `:414`. So for `MM32`, the byte at the lowest address becomes the
least-significant byte of the returned Integer, and on little-endian x86 the order
of the four is the order the interpreter read them in. The kernel's copy assembles
the same way.

The specification agrees, and says so in one word. §19.3.5 "ASL Data Types",
printed page 898 (PDF page 968) of the same release:

> **Integer** — An n-bit little-endian unsigned integer.

That is the AML Integer object defined as little-endian, and it is the fact
`ecrw.py`'s docstring and the vendor analysis were both leaning on without a
citation. It is now cited — to the specification, not to a reading of a
disassembly.

**The operating-system half, which the interpreter does not decide.** How that
Integer becomes bytes in a buffer is a fact about the OS interface. The Linux
evidence is a null rather than an answer: `acpi_evaluate_integer` on `v6.6` does
not go through the old `ACPI_METHOD_ARGUMENT` marshalling at all, but asks for a
single `union acpi_object` back and reads the integer out of it at
`evidence/acpi/linux-acpi-region-access-excerpt.c.txt:421` — `*data = element.integer.value;`

**A correction the second half needed.** The struct the vendor driver indexes into
is neither a specification artifact nor an ACPICA one. Searching the full text of
two specification releases for `ACPI_METHOD_ARGUMENT` returns nothing, and
searching ACPICA returns only an internal AML opcode constant of that name. The
struct is Microsoft's, from the WinDDG interface — `ACPI_METHOD_ARGUMENT_V1`, a
`Type` and a `DataLength` and a union of `ULONG Argument` against `UCHAR Data[]` —
documented at Microsoft Learn's `_ACPI_METHOD_ARGUMENT_V1 (acpiioct.h)` page, which
describes the integer case as the `Argument` member containing "an integer value of
type ULONG". A native `ULONG` is in native byte order, so on x86 the reading
`windows/native/ACPIDriver.sys.analysis.md` takes — that `buf[0]` is the lowest of
the four — is consistent with the documented member type.

Consistent is not the same as established, and the gap is worth naming rather than
papering over. No public Microsoft page retrieved says the return value occupies
`Argument[0]`, and none of them states a byte order; the AMLI-era wording that
would settle the first was searched for across Microsoft Learn, two Windows SDK
header trees, Wine and ReactOS and did not turn up. So the last step — that the
slot the vendor driver reads is the one carrying the return value — is still a
reading of that driver's disassembly rather than a documented fact. `ecrw.py mmrd`'s
refusal to print per-byte EC-offset labels was the right call and is unchanged: the
comparison it invites is still against the aligned `dump` line beside it, on the
machine.

## The specification

This half of the blank closes, but not in the shape the issue asked for, and the
difference is worth a paragraph of its own.

**The text is not committed, because the licence does not allow it.** The ACPI
Specification is published by the UEFI Forum, and its notice is explicit:
"Copyright ©2024, Unified Extensible Firmware Interface (UEFI) Forum, Inc. All
Rights Reserved", with permission granted "to any person implementing this
specification to maintain an electronic version of this work accessible by its
internal personnel, and to print a copy of this specification in hard copy form, in
whole or in part … provided no modification is made to the Specification." Committing
a transcription of it into a public repository is neither an internal electronic copy
nor a hard-copy print, and it is not a judgement the implement stage of this pipeline
is placed to make. So the citation is below, the operative sentence is quoted, and
the rest is named precisely enough to go and read. That is the discipline the rest of
the evidence here follows, arrived at from the other end: an excerpt whose provenance
cannot be committed is cited, not vendored.

**What the specification says.** *Advanced Configuration and Power Interface
(ACPI) Specification*, Release 6.5 Errata A, UEFI Forum, November 2024, §19.6.47
"Field (Declare Field Objects)", printed page 944 (PDF page 1014), at
<https://uefi.org/sites/default/files/resources/ACPI_Spec_6.5a_Final.pdf>. Release
6.6, §19.6.48, says the same thing. Under `Arguments`, `AccessType`:

> In general, accesses within the parent object are performed naturally aligned.

two sentences later:

> The exceptions to natural alignment are the access types used for a non-linear
> SMBus device.

and, on what an explicit `AccessType` is for:

> If desired, AccessType set to a value other than AnyAcc can be used to force
> minimum access width.

Three things follow, and the third is the one the issue wanted. The specification
**does** state a rule — accesses within the parent object are naturally aligned,
with SMBus the only named exception. It does **not** say what an implementation must
do when handed an operand that is not, and that was checked rather than assumed. The
substring `unalign` does not occur in the extracted text of either release, and
the occurrences of `align` in release 6.6 were read through rather than sampled:
they are FADT register-block alignment, table field offsets, resource-descriptor
`AddressAlignment`, bit-level typing in the data-types table, and the two
`Field`/`IndexField` statements quoted here. Not one is about an operand that is
not aligned. That is a statement about one PDF's text layer, and a rendering that
failed to extract would not have shown up in it. The specification prescribes no split, no prohibition, and no
defined behaviour. So the first question has the specification on the record, and
the specification does not settle it.

**And the `ByteAcc` question underneath it.** The specification never prose-defines
`ByteAcc`. The keyword is listed in the grammar and given no definition; the only
operational meaning it acquires is in Table 19.34, "OperationRegion Address Spaces
and Access Types", where the `EmbeddedControl` row reads `ByteAcc` and "Byte access
only". That row is not binding here, because `ECMG` — the 64 KiB window at
`0xFE410000` this whole exchange reads through — is declared
`OperationRegion (ECMG, SystemMemory, 0xFE410000, 0x00010000)` at
`evidence/acpi/dsdt.dsl:52193`, and the `SystemMemory` row of that same table
permits every access type. So `MMRW`'s three `ByteAcc` declarations are the ASL
author's own narrowing rather than a constraint the region type imposed, which is a
better reason to think they were deliberate than "the vendor picked the safe option"
would have been.

## What this does not establish

**This machine's interpreter.** `ACPI.sys` is a Microsoft kernel driver, and its
source is not public. That is a correction to the issue's own premise rather than
a finding: the issue's title offers "an interpreter whose code is public" as the
settling source, and no public-source interpreter settles a question about a
closed-source one. Two implementations of the same specification agreeing is
strong evidence about the specification and about what a conforming interpreter
does. It is not a reading of this machine's driver, and nothing here should be
quoted as one.

The file that would answer it, for this machine's build, is a symbol-level listing
or a disassembly of the field-access routine from the `ACPI.sys` that ships in the
matching Windows image — the same treatment `ACPIDriver.sys` already has in
`windows/native/`. That is a vendor binary and would not be citable as source in
any case, which is the second half of why this question stays open: the answer
exists, it just is not a document anyone can quote.

**Whether the interpreter on this machine splits the access.** Both readings above
are static reads of public source at a pinned revision. Neither was executed, on
this machine or any other. A firmware that is not the reference implementation is
a different code path, and the specification's version that a given BIOS claims
conformance to is itself part of the open question.

**What the BIOS returns.** Nothing here reaches the EC. Whether the four bytes
`MMRD` reads back are the four at that window in the order this write-up describes
is still a human at the physical machine with the vendor stack loaded and an
elevated shell — `ecrw.py mmrd 0x0751` is that run, and
`linux/battery-trace/` is not where it happens.

**The AMI documentation.** Whether AMI published anything about whether `MMRW`
was intended to be alignment-safe is a recorded null, and it is the only one this
issue leaves open that is not a statement about a machine at all. The `INOU0000`
identification is carried by the naming pattern and the hardware ID, not by a
document in this repository, and that is stated above rather than asserted flat.

**Nothing about #94.** No watch set is touched and no address is added to any of
them. An `MMRD` that returns plausible bytes would still be a result about the
access and not about the flag — a register write being accepted is not evidence
the EC acts on it, and `ec/annotations/registers.yaml` changes nothing here.