# `ec_watch.py` and `ecrw.py dump` no longer read the fan-tach page, and both pace their reads

(2026-10-03. Offline: argument handling and read-shape, proven against fakes.
No EC was opened, no register was read back, and neither tool has been run on
Windows or on the laptop. Every claim below about a sweep is about which
addresses reached the fake driver's call list and which sleeps reached
`time.sleep`.)

**The hazard #94 describes is a shape of *access*, not a shape of *range*.**
Reading the fan-tach bytes `0x0460-0x046F` through `ECRR` stalled the fans on a
sibling board, and the vendor's own software and `uniwill-laptop` both sleep
about 6 ms after every EC access
([HydroControl DESIGN.md §4.2](../related-projects.md)). The other readers in
`windows/tools/` already stay off the page —
`manual_fan_ctrl_probe.py`, `system_id_probe.py` and `ec_validate.py` build
watch sets that stop at `0x045F`, and `gpu_block_watch.py` and
`ctgp_dben_probe.py` name no address in it at all. The two that swept did not,
and one of them (`ecrw.py dump`) had no constant for the page at all. Both now
leave it out by default, behind `--include-fan-tach`, and both take a
`--gap-ms` that defaults to the 6 ms those sources report.

## 1. What changed, and what did not

| | before | after |
|---|---|---|
| `ec_watch.py` default range | `0x0000-0x07FF`, read whole | **unchanged**, minus the sixteen fan-tach bytes |
| `ec_watch.py --block` | one `readmany` over the whole range | one `readmany` per contiguous run of what is left |
| `ecrw.py dump` | walked straight through the page | excludes it; `--include-fan-tach` opts back in |
| inter-read gap | none, on either tool | `--gap-ms`, default 6 |
| `registers.yaml` | — | **untouched**; no `status:` moved |

The default *range* was left at `0x0000-0x07FF` deliberately. Narrowing it was
suggested by #94, but it changes what a bare invocation watches rather than how
safely it watches it, and it would stop the sweep reaching the `0x04xx` sensor
block the tool's busy/quiet split is built around. That is a decision about the
tool's purpose and belongs to whoever owns it. The narrow-range advice is in
the docstring and in the banner instead, where it informs without overriding.

**`registers.yaml` is untouched and no status moved.** Excluding addresses from
a read sweep is a change to a tool's defaults, not evidence about a register.
Nothing in this work observed a register.

## 2. Why the exclusion is exact under `--block`

A block read that *covers* the page is a wider access to it, not a narrower
one, so dropping the addresses and then reading the range they sat in would
have been no exclusion at all. The tool builds the read set first and reads
runs of that (`ecrw.block_runs`), and the reason a run cannot reach back into
the page is arithmetic:

- `0x0460` is dword-aligned, and the page is sixteen bytes, so every
  four-byte block that holds a fan-tach byte lies **wholly inside** the page.
- `readmany` covers a range with the aligned blocks *enclosing* it. A run that
  ends at `0x045F` is therefore covered by blocks up to `0x045C`, and a run
  that starts at `0x0470` by blocks from `0x0470`.
- Neither can have a page byte in it, for the same reason a boundary at a
  block-aligned address needs no special case.

So `0x0000-0x07FF` under `--block` becomes `(0x0000, 0x460)` and
`(0x0470, 0x390)` and the page is not read. This is checked against the fake
kernel32's recorded `MMRD` offsets in `windows/tools/test_ecrw.py` and against
the runs a fake `Ec` was handed in
`windows/tools/test_ec_watch_read_pacing.py`; the same reasoning is why
`ecrw.py dump` reads runs rather than rows, since a row that covered the page
would otherwise read past it.

## 3. What the gap is, and what it costs

The gap is taken after **every read call**, inside the sweep, not between
sweeps: `--interval` is a different axis and is where it was. On the byte path
a read call is one `ECRR`, so a full-range sweep costs one gap per address and
the banner's projection is a floor rather than an estimate.

**`--block` is not the paced path**, and the banner says so by counting what
it can see. `readmany` issues one IOCTL per four bytes without coming back to
the tool, so the gap is per call and a full-range `--block` sweep pays one gap
per run rather than one per address. The default range splits into two runs of
`0x460` and `0x390` bytes, so what falls between the two gaps is 508 IOCTLs in
a row, not four — an operator who wants the paced path wants the byte path.
That count is held by a case rather than by this sentence, over the calls the
fake kernel32 recorded, in `test_ecrw.py`'s `DumpPacingTests`.

The cost of the default is real and is printed before the loop starts rather
than discovered in it. At 6 ms per read, the default range projects about
twelve seconds a sweep against the ~150 ms the docstring used to promise. This
is what the banner prints for a 256-byte run, off a fake EC — the timestamp is
elided and no sweep ran, because none of this can:

```
  baseline: 0x0700-0x07FF (256 bytes), sweeping every 0.25s
  256 read call(s) per sweep, 6 ms apart: about 1.5s a sweep. Narrow the
  range, not the gap, for something that has to keep up with a transient.
```

That tension is the reason the banner exists rather than a footnote. What the
tool is for is *which address moved*, not *when to the millisecond*: a
settings write persists in the EC, so a twelve-second sweep still catches it,
more coarsely. A run that has to keep up with a transient wants a narrower
range, which is what the banner says and what `--start 0x0700 --len 0x100`
gives.

**An empty sweep is reported, not printed.** A range wholly inside the page —
`--start 0x0460 --len 0x10` — now has nothing left to read, and a sweep with
nothing in it would print a baseline and then "nothing moved", which reads as an
observation about the EC rather than as the refusal to read it that it is. Both
tools say so on stderr and exit non-zero, issuing no read at all.
`ecrw.py dump` marks a partly-excluded byte `--` in the hexdump for the same
reason: a zero there would read as a byte the EC returned.

## 4. What this does not establish

- **Not that 6 ms is the right gap on this machine.** It is the figure a
  committed source reports for this access, recorded in
  `docs/related-projects.md`, and it was measured on a *different* board. No
  interval in this repository has been validated against this EC.
- **Not that reading the fan-tach page stalls this machine's fans.** It has
  never been observed to here, which `docs/related-projects.md` records rather
  than this work establishing. #94 asks for the exclusion on a sibling board's
  evidence alone.
- **Not that the exclusion is necessary.** It is the conservative default given
  a report from a sibling board and no evidence of harm here. `--include-fan-tach`
  exists so the reading stays falsifiable by a human at the machine.
- **Not that a paced sweep is harmless.** The gap is HydroControl's figure, not
  a measurement; a run that wants the 150 ms behaviour has `--gap-ms 0`, and
  that is the unpaced tool this default stopped being.
- **The gap is per read call, so it does not pace the IOCTLs inside a
  `readmany`.** A `readmany` issues one IOCTL per four bytes, so a run of
  `0x460` bytes is 280 IOCTLs back to back under a single gap, and a
  full-range `--block` sweep is 508 of them with one gap between the two runs.
  Said above because it is the limit of the promise rather than a detail.

## 5. Where the offline evidence is

```console
$ bash tools/run-tests.sh windows/tools
```

- `windows/tools/test_ec_watch_read_pacing.py` — which addresses a sweep
  reads, with and without `--include-fan-tach`, on both paths; that a range
  inside the page is refused rather than swept; and that `--gap-ms` reaches
  `time.sleep` at the default and at an operator's own value. The sleeps are
  recorded rather than taken, so the 6 ms default costs the suite no 6 ms.
- `windows/tools/test_ecrw.py`'s `DumpPacingTests` — the same question against
  a fake `ctypes.WinDLL`, so a stray read shows up on the wire rather than only
  in the printed hexdump.

## 6. What this opens

- **One `FAN_TACH` rather than one per tool.** `ec_watch.py`, `ecrw.py`,
  `manual_fan_ctrl_probe.py`, `system_id_probe.py` and `ec_validate.py` each
  carry the range, and `test_ecrw.py` a copy of it. Unifying them is worth
  doing and is deliberately *not* done here: `windows/tools/` is deployed as a
  directory, `ecrw_fake.py` publishes exactly three names, and hoisting the
  constant into `ecrw.py` would make `ec_watch.py` fail to import under every
  offline suite in that directory until the fixture grew a fourth export — a
  change to a shared fixture with the whole directory as its blast radius. It
  wants a decision about the fixture's shape first.
- **`ec_watch.py`'s default range is still the open question**, deliberately
  left alone here. A 2 KiB sweep at 6 ms is twelve seconds; whether that is the
  right default for the tool, or whether a narrower one should be, is a
  decision about what the tool is for.
- **What the paced default does to prose written against the unpaced one.**
  `grade_0751_isolation.py`'s printed `ZERO_SCOPE_NOTE` and the bus-traffic
  sections of the 0751 and `oem4-07a6-bit0` runbooks all restated the sweep as
  `ECRR` reads with `--interval` slept between sweeps and nothing between
  bytes; they now describe the per-read gap and name this file. Their read
  counts did not move — pacing changes how long a sweep takes, not how many
  reads it issues — but the runbooks had a second claim resting on the burst
  shape, that their run put more traffic on the bus than any run before it, and
  that is a claim about rate rather than count. Still open: the documents
  decline to put a number on the sampling period, and whether the banner's
  projection of a sweep's duration should now stand in for one is undecided.
- **Whether the gap belongs at the driver instead.** Both tools now pace what
  they ask the vendor driver to do, and a Linux driver would want the same
  answer from `acpi_call`. Nothing here settles where the pacing should live.
  What #94 leaves open is the other half: whether any interval at all is
  validated against this EC, which no argument here can settle either.