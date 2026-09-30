# Which arm seeded the per-mode PL defaults, and did the fixed arm run?

**Status: not run.** The pipeline that wrote this file has no machine to run
it on — `CLAUDE.md` is explicit that the GitHub-hosted runners cannot reach
the hardware. Everything below is preparation. Nothing in this file, in
`ec/annotations/registers.yaml`, or in
[`../findings/mode-defaults-variant-selector.md`](../findings/mode-defaults-variant-selector.md)
says a live read of these bytes has happened, and no `status:` moves on the
strength of a procedure that has not been executed.

The finding this serves has already answered most of the issue statically, and
this file must not be read as though it were still needed for that. The three
seed tables are byte-identical over the sixteen bytes the copy reads, so
**whichever arm runs, the twelve defaults come out the same.** What static
evidence genuinely cannot reach is *which* arm last ran, and whether the
fixed-byte arm at `0x95C0` executed — because that is a run-time fact about
`0x0770`, not a property of the code.

## 1. The two questions, and what each read decides

**Q1 — did the fixed arm at `0x95C0` run?**

`0xB8C0` returns R7 = 1 when `0x0770 == 0x04`, and `0x95BB jnz` sends *that*
case into the block. So the fixed bytes (`0x0730 = 0x2D`, `0x0731 = 0x3C`,
`0x07A7`/`0x07A8 = 0x64`, `0x0737 = 0x01`) are written when `0x0770 == 0x04`
and skipped otherwise. `registers.yaml` records `0x3C` live at `0x0730`,
which is what the `movc` table path produces and not what the fixed arm
produces.

- `0x0770 == 0x04` **and** `0x0730 == 0x2D` — the fixed arm ran last.
- `0x0770 != 0x04` **and** `0x0730 == 0x3C` — the table path stands; the
  fixed arm did not run, or ran and was overwritten later.
- `0x0770 == 0x04` **and** `0x0730 == 0x3C` — the fixed arm ran and a later
  `movc` overwrote it. **Do not report this as "the fixed arm did not run".**

The third row is the one the polarity makes possible and the reason this
question needs an answer rather than an inference.

**Q2 — which seed arm last ran?**

`0x0A51`/`0x0A52` hold the seed pair big-endian, and there are three:
`0x61/0xFE`, `0x61/0xC8`, `0x61/0x92`. Reading them says which pair is
present, not which arm put it there. Two things stop that being a verdict:
`0xD9FE` rewrites the pair on every seeding pass, so the byte is a record of
the last pass rather than a property of the board; and **these two bytes have
writers outside `0x94D0`** — `trace_xdata_refs.py` finds writes at `0x8731`
and `0x966D` for `0x0A51`, and at `0xE3A5` and `0xE453` for `0x0A52`, all in
bank0. So a pair that disagrees with `0x07D3` is not a contradiction; it is
this read's first question of the seeder.

Read `0x07D3` alongside it: that is GFID, and the finding's chain says
`0x94D0` stores `0x61/0x92` whenever GFID != 3 and one of the other two when
GFID == 3. So a `0x0A52` of `0x92` **with a `0x07D3` high nibble of `0x30`**
is a combination `0x94D0` cannot produce — worth a second look, and worth
reporting as the observation it is rather than resolving from here.

## 2. Before you start

- Root, and `CONFIG_DEVMEM=y`. `ec/tools/ecmem.py` maps physical `0xFE410000`
  through `/dev/mem` itself, which is the window the DSDT's `ECRR` uses and
  so the same bytes the Windows arm reads. On this machine the window is listed
  under `INTC1036:00` in `/proc/iomem`. Check the build first:
  `grep DEVMEM /boot/config-$(uname -r)`.
- **A cold boot, and the read as early as you can get it.** The seeder runs
  during initialisation; if it runs again on a later event, the bytes you read
  after login describe that event, not the boot. §3 takes three samples and
  §4 says what the spread means.
- The machine otherwise idle, AC state noted. `0x1666` and `0x166A` are
  board-identification bytes and are not expected to move, but record them
  rather than assume.

## 3. The read

`ecmem.py read` prints one byte; this is a dozen addresses, so the loop is the
command. Take it **three times, ten seconds apart**, so a byte that is being
rewritten shows up as a spread rather than as a single value that happens to
have been captured mid-update.

```sh
for a in 0x07D3 0x1666 0x166A 0x0770 0x0A50 0x0A51 0x0A52 \
         0x0730 0x0731 0x0732 0x0733 0x0734 0x0735 0x0736 0x0737 \
         0x07A7 0x07A8 0x07A9 0x07AA 0x0782; do
  printf '%s ' "$a"; python3 ec/tools/ecmem.py read "$a"
done
```

Run it three times and keep all three outputs. If a byte differs between
samples, that byte is live and the single-sample reading of it was luck; say
so in the result rather than quoting the last one.

If `ecmem.py read` is not the tool you have to hand, the Windows arm is
equivalent and needs no root: `python windows\tools\ecrw.py read 0x07D3` (and
the same for each address), which needs the vendor's `UWACPIDriver.sys` from
Control Center 3.1.39.0. `windows/tools/ecrw.py`'s docstring has the setup.

## 4. Reading the result

Record the three samples verbatim before interpreting any of them. Then:

1. **`0x0770`** decides Q1. It has three direct read sites in the image and no
   writer this repository can find, so it is a *configuration* byte in
   practice — if it reads `0x04` at boot on this machine, the fixed arm runs
   on every seeding pass, and `registers.yaml`'s live `0x3C` needs explaining
   rather than the §3/Q1 table's first row being assumed.
2. **`0x0A51`/`0x0A52`** decides Q2, against the three pairs in the finding.
   Report the pair, not "the arm" — the finding already establishes the three
   arms agree on the output.
3. **`0x07D3`** is the discriminator itself. Report the whole byte, not the
   masked field: the finding's chain is on the high nibble, and the low nibble
   is the one part of the byte this analysis has never accounted for.
4. **The twelve defaults** are a check on the finding, not new evidence about
   the EC. If they read `3C 3C A5 01 / 23 23 A5 01 / 4B 4B A5 01`, the
   `movc` path accounts for them and §5 of the finding holds. If they read
   anything else, **the finding is wrong and the tool's derived values are
   wrong** — say so plainly rather than explaining the difference away.

**What none of this settles.** Whether the EC *acts* on the twelve bytes. The
static evidence is a write direction, and a read of the destination does not
turn a write into a behaviour. If the question behind all of it is "can a
Linux driver write `0x0751` and have the PLs follow", this read does not
answer that; `manual-fan-ctrl-0751-isolation.md` is the procedure for it.

## 5. Where the output goes

Name the file the way the existing captures do, so the three samples are
readable next to the 2026-09-23 record in `registers.yaml`:

```
evidence/ec-watch/<date>-mode-defaults-variant.txt
```

`<date>` is that run's YYYY-MM-DD. Keep all three §3 samples in that one
file, in the order they were taken, with a line between them saying which
sample it is and roughly how long after boot it was — the boot-relative time
is the part that decides whether the reading describes initialisation or a
later event, and it is the part that cannot be recovered later.

`ecmem.py read` prints to stdout and writes no file, so the capture is
assembled by redirecting §3's loop. The address list is repeated here rather
than pointed at, because a command in this section that a reader cannot paste
is a command that gets typed from memory. **Replace `<date>` with the run's
date before running it** — it is a placeholder, not a shell expansion:

```sh
addrs="0x07D3 0x1666 0x166A 0x0770 0x0A50 0x0A51 0x0A52 \
       0x0730 0x0731 0x0732 0x0733 0x0734 0x0735 0x0736 0x0737 \
       0x07A7 0x07A8 0x07A9 0x07AA 0x0782"
sample() {
  echo "# sample $1, $(date -Is), ~$(awk '{print $1}' /proc/uptime)s after boot"
  for a in $addrs; do printf '%s ' "$a"; python3 ec/tools/ecmem.py read "$a"; done
  echo
}
{
  sample 1; sleep 10
  sample 2; sleep 10
  sample 3
} > evidence/ec-watch/<date>-mode-defaults-variant.txt
```

The `~Ns` is seconds since boot from `/proc/uptime`, which is what makes the
file worth keeping in a year: a reading with no boot-relative time cannot be
placed against the seeding pass it is supposed to describe. The `sleep 10` is
§3's spacing, written in so the three samples cannot be taken back to back by
accident.
