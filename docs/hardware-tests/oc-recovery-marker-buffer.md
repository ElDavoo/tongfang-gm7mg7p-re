# Is the OC recovery marker buffer ever populated, and does it hold the pattern that would trigger recovery?

**Status: not run.** The pipeline that wrote this file has no machine to run
it on — `CLAUDE.md` is explicit that the GitHub-hosted runners cannot reach
the hardware. Everything below is preparation. Nothing in this file, in
`ec/annotations/registers.yaml`, or in
[`../findings/0741-bit7-oc-recovery.md`](../findings/0741-bit7-oc-recovery.md)
says a live read of these bytes has happened, and no `status:` moves on the
strength of a procedure that has not been executed.

The finding this serves has already settled the static side: `0xCFC6` is a scan
loop that looks for `0x14` and `0x32` at different offsets in the region
`0x0B00-0x0BFC`, and raises the BIOS's overclock-recovery request when both are
found. What static evidence cannot settle is whether the region ever holds either
marker byte on this machine, which is the runtime fact this procedure addresses.

## 1. The two questions, and what each read decides

**Q1 — does the marker buffer ever hold non-zero bytes?**

The region is initialized to zero by `0x2896` at startup. If a read at rest
shows the entire span as zero, that is consistent with the region never being
written since init. If it shows any non-zero bytes, then at minimum some writer
reached the region at some point after boot.

- `0x0B00-0x0BFC` reads all `0x00` across all arms — consistent with the
  region being unwritten since init or the writes occurring at rare moments not
  captured by the sample.
- `0x0B00-0x0BFC` holds one or more non-zero bytes — the region has been
  written at least once since boot.

**Q2 — if non-zero, does the buffer hold the pattern `0x14` and `0x32` at different offsets?**

If the region holds non-zero bytes, check whether `0x14` appears at one offset
and `0x32` appears at a different offset. This is the exact condition that would
raise the BIOS request via `0xCFC6`'s scan. Per the finding's §2, the two calls
per iteration read the same address, so they must be at different offsets.

- `0x14` and `0x32` both present at **different** offsets — the marker pattern
  that `0xCFC6` would act on exists in the buffer.
- One marker present but not both — the pattern is incomplete; the request would
  not raise.
- Neither marker present — the pattern is absent; the request would not raise
  even if the region holds other non-zero bytes.

## 2. Before you start

- Root, and `CONFIG_DEVMEM=y`. `ec/tools/ecmem.py` maps physical `0xFE410000`
  through `/dev/mem` itself, which is the window the DSDT's `ECRR` uses and
  so the same bytes the Windows driver reads. On this machine the window is listed
  under `INTC1036:00` in `/proc/iomem`. Check the build first:
  `grep DEVMEM /boot/config-$(uname -r)`. See `ec/tools/ecmem.py`'s own docstring
  for validation of the read path and cross-checks against the `uniwill-laptop`
  regmap debugfs.
- **A cold boot, and the read as early as you can get it.** The marker writers
  (if any) may run during initialization or later. If they run and then the region
  is cleared, a read after login would miss them. §3 takes three samples and
  §4 says what the spread means.
- The machine otherwise idle, AC state noted. `0x1666` and `0x166A` are
  board-identification bytes and are not expected to move, but record them
  rather than assume.

## 3. The read

`ecmem.py read` prints one byte; this is a 255-byte region plus two latch bytes,
so a tool that takes a page and count is more practical. Use
`ec/tools/sample-marker-buffer.py` to capture the region in the standard format:

```sh
python3 ec/tools/sample-marker-buffer.py 0x0B 0xFF > evidence/ec-watch/<date>-oc-recovery-marker-buffer.txt
```

where `<date>` is the run's YYYY-MM-DD. The tool reads `0x0B00-0x0BFE` (255
bytes: the scan region `0x0B00-0x0BFC` plus the neighbours `0x0BFD-0x0BFE`),
plus `0x0816` (the latch) and `0x0741` (the request bit), and outputs a
capture in the committed format so grading is mechanical.

Run it **three times, ten seconds apart**, so a byte being rewritten shows up as
a spread rather than as a single value captured mid-update.

```sh
sample() {
  echo "# sample $1, $(date -Is), ~$(awk '{print $1}' /proc/uptime)s after boot"
  python3 ec/tools/sample-marker-buffer.py 0x0B 0xFF
  echo
}
{
  sample 1; sleep 10
  sample 2; sleep 10
  sample 3
} > evidence/ec-watch/<date>-oc-recovery-marker-buffer.txt
```

(Replace `<date>` with the run's date before running — it is a placeholder, not
a shell expansion. The `~Ns` is seconds since boot from `/proc/uptime`, which is
what makes the file worth keeping in a year.)

## 4. Reading the result

Record the three samples verbatim before interpreting any of them. Then:

1. **The 255-byte region `0x0B00-0x0BFC`** decides Q1. Report whether it reads
   entirely zero or whether any byte is non-zero. If any byte differs between
   samples, that byte is live and the single-sample reading of it was luck; say
   so in the result rather than quoting the last one.

2. **Search for `0x14` and `0x32` at different offsets**, answering Q2. If Q1
   found the region all-zero, Q2 does not apply. If Q1 found non-zero bytes,
   report the offsets of any `0x14` and `0x32` found. The offsets must be
   different for the pattern to match `0xCFC6`'s scan — one byte cannot be both
   `0x14` and `0x32`.

3. **`0x0816` (the latch)** and **`0x0741` bit 7 (the request)** accompany the
   buffer reads. Report their values. Per the finding's §5, `0x0816` is a latch
   and the request bit is set when the latch reads `0x03`. The combination helps
   confirm whether the recovery path has fired.

**What none of this settles.** A buffer reading all zero after boot does not
prove there is no writer. The write could be rare, triggered by a specific event
not captured in the sample, or could have happened between samples. The finding's
§7 is explicit on this: the region's writer is not found by any static method,
so something unknown writes it through a path these tools cannot see. A negative
read (all zeros) is consistent with no writes, but it is not evidence that no
writer exists — it is a statement about what was captured, not about the code.

## 5. Where the output goes

Name the file the way the existing captures do:

```
evidence/ec-watch/<date>-oc-recovery-marker-buffer.txt
```

`<date>` is that run's YYYY-MM-DD. Keep all three §3 samples in that one file, in
the order they were taken, with a line between them saying which sample it is and
roughly how long after boot it was — the boot-relative time is the part that
decides whether the reading describes the initialization window or a later event,
and it is the part that cannot be recovered later.
