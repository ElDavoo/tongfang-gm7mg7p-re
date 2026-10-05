# What `2026-09-23-power-mode-cycle-0f00-0f5f.csv` records: a whole fan table, written and rewritten

**Issue #1023.** Since #974, `check_testdata_row_claims.py`'s dated block has
named this file as the carrier of row 7's two literals on every run. Nothing in
the corpus recorded what the file contains. This page reads it, and reads the
sibling capture alongside it — because the dated rule resolves row 7's literals
in **this** file, while the `0xFD`/`0xC9` occurrences row 7's sentence is about
are in the sibling, which is why the two have to be read together.

Everything below is read off files already committed under `evidence/` and
`ec/annotations/`. No capture was opened, no EC was read, no register was
written or read back, and no writer is attributed. Offline throughout.

**The short of it: the file is not a partial sample of the fan table, it is the
whole thing.** All 47 addresses it records are addresses where the three
tables the service published on `Fan/Table` during the same capture differ from
each other, and every one of its 212 rows carries the value its burst's
published table gives that address. The `0xFF` transients are the *unused* slots
of a shorter table. The two `0x30`-apart blocks are the CPU and GPU copies of
the duty row, which is why they move identically. What looked like three
separate phenomena is one thing seen three ways, and it is already decoded.

## The commands

Every figure on this page comes from one of these. They read committed files
only.

```console
python3 windows/tools/fan_table_replay.py \
    --csv evidence/ec-watch/2026-09-23-power-mode-cycle-0f00-0f5f.csv \
    --final evidence/ec-watch/2026-09-23-power-mode-cycle-0f00-final.txt \
    --mqtt evidence/mqtt-capture/2026-09-23-power-mode-cycle.jsonl
```

```
6 write bursts, 6 Fan/Table publishes
  before first burst: M3T1
  burst 1 17:59:00.467-17:59:02.144 (47 bytes): EC = M2T1; last announced M2T1: MATCH
  burst 2 17:59:13.376-17:59:15.067 (43 bytes): EC = M1T1; last announced M1T1: MATCH
  burst 3 17:59:30.797-17:59:31.849 (16 bytes): EC = M3T1; last announced M3T1: MATCH
  burst 4 17:59:51.227-17:59:52.726 (47 bytes): EC = M2T1; last announced M2T1: MATCH
  burst 5 18:00:01.025-18:00:02.487 (43 bytes): EC = M1T1; last announced M1T1: MATCH
  burst 6 18:00:05.395-18:00:06.237 (16 bytes): EC = M3T1; last announced M3T1: MATCH
```

That output is `windows/tools/fan_table_replay.py`'s, committed and unchanged
by this page. It had been run on this capture before; what had not been written
down is *what the capture is*, which the rest of this page is. The remaining
figures — which addresses vary, the burst-by-burst equality, the `0xFF` slot
set — come from `ec/tools/test_power_mode_cycle_capture.py`, which reads the
same committed files and holds each claim below.

The sampling period named in `0x070A`'s section comes from the capture's own
timestamps, one command per figure:

```console
$ python3 -c 'import csv, datetime
ts = sorted({datetime.datetime.fromisoformat(r["ts"]) for r in csv.DictReader(
    open("evidence/ec-watch/2026-09-23-power-mode-cycle-0f00-0f5f.csv"))})
gaps = sorted({round((b - a).total_seconds(), 3) for a, b in zip(ts, ts[1:])})
print([g for g in gaps if 0.05 < g < 1])'
[0.202, 0.205, 0.206, 0.207, 0.208, 0.209, 0.21, 0.211, 0.213, 0.214, 0.217,
 0.219, 0.222, 0.225, 0.414, 0.417]
```

## The three phenomena are one

The corpus already knows the layout of this window.
`docs/findings/ec-fan-table-defaults.md` §2 records it from the service side:

```
0x0F00 + i   CPU entry[i+1].UpT        (i = 15: 0xFF)
0x0F11 + i   CPU entry[i].DownT        (i < 15; 0x0F10 is never written)
0x0F20 + i   CPU entry[i].Duty * 2     (duty in %, stored as 0-200)
0x0F30...    the same three rows for the GPU
```

That is a 96-byte window holding two fans' worth of a 16-entry curve, and the
`0x30` stride the issue noticed is simply the CPU half and the GPU half. Each
half is three rows — `UpT`, `DownT`, `Duty` — so the window has six rows of
sixteen, and the dump's three `0x30`-apart row-pairs are
(`UpT` CPU, `UpT` GPU), (`DownT` CPU, `DownT` GPU) and (`Duty` CPU,
`Duty` GPU).

Which is what makes the issue's byte-identity observation fall out rather than
need explaining. In all three published tables the CPU and GPU `Duty` rows are
equal, so `0x0F20` and `0x0F50` hold the same sixteen bytes and the dump's
`0F20`/`0F50` pair matches. The `UpT` and `DownT` rows differ between fans —
every table, both rows — so `0F00`/`0F30` and `0F10`/`0F40` do not. The
identical pair is not a coincidence of this capture; it is a property of the
service's tables, and it is the `Duty` row that is identical.

**The `0x30`-apart block pair the issue found is entries 8..15 of the `Duty`
row, on both halves.** `0x0F28-0x0F2F` is CPU `Duty` entries 8-15 and
`0x0F58-0x0F5F` is the same eight entries of the GPU row. Both start
`8C AA C8 C8 C8 C8 C8 C8` because `M3T1`'s top duty is 100 % and the last duty
repeats — `ec-fan-table-defaults.md` §2 states that rule, and it is what puts
`C8` in six of the eight bytes rather than only in the last. Both are then
driven flat to `0x6E`, which is 110, which is `M2T1`'s 55 %; both return as
`8C AA AA AA AA AA AA AA`, which is `M1T1`'s 85 %; and a third, separate event
takes the trailing six `AA` back to `C8`, which is `M3T1` again. The whole cycle
then repeats about fifty seconds later.

So the "restore pass does not restore" observation is real, and it is not a
quirk of the EC. Each burst writes a *different table*, so the block is not
being restored to a remembered value — it is being set to whichever table that
burst carries. `M2T1`'s top duty is 55 %, `M1T1`'s is 85 %, `M3T1`'s is 100 %,
and the seven bytes that read `AA` after the second burst are `M1T1`'s 85 %,
which is the correct value for the table in force at that moment. The third
write touches only six of the eight, taking `0x0F2A`-`0x0F2F` back to `C8` and
leaving `0x0F28` and `0x0F29` alone, because `M1T1` gives entries 8 and 9 the
same 70 % and 85 % `M3T1` does — those two are already the right bytes for the
table coming back, so there is no change for the capture to log. That write is
not a repair; it is the next mode.

## The `0xFF` transients: unused slots of a shorter table

This is the issue's open half, and it does not stay open.

Eight addresses in the capture are written `0xFF` and read back: `0x0F08`,
`0x0F09`, `0x0F19`, `0x0F1A`, and the same four at `+0x30` on the GPU half.
`0xFF` is the vendor's marker for an unused step —
`ec-fan-table-defaults.md` §2 says "Unused steps are `0xFF`" — and each publish
says how many steps it has: `M2T1` carries `CpuTemp_DefaultMaxLevel` 8, `M1T1`
carries 10, `M3T1` carries 11. That level is an upper bound on what a table
fills, not the address where the blanks start: no row fills a slot past its
level, but the blank tail begins *at* the declared level for the `UpT` rows of
`M1T1` and `M3T1` and one slot *past* it for `M2T1`'s. The two rows do not cut
at the same entry either — in every table the `DownT` row's `0xFF` starts one
entry earlier than the `UpT` row's — so which addresses are unused depends on
the row and on the table, not on the level alone. What is not in question is
the direction: a longer table has fewer `0xFF` entries, and the capture's
`0xFF` writes and read-backs track exactly that.

Which is what the capture shows. `0x0F09` and `0x0F1A` are real in `M3T1` and
`0xFF` in the other two; `0x0F08` and `0x0F19` are real in both `M1T1` and
`M3T1` and `0xFF` in `M2T1`. Each is a slot that a longer table uses and a
shorter one does not, so a mode switch writes `0xFF` over it and the switch back
writes the value again. **Nothing about `0xFF` here is anomalous, and no
meaning for it is missing from the corpus** — the write-up that had not been
made is this one.

The resting dump carries the same thing statically: `0xFF` runs at
`0x0F0A-0x0F0F`, `0x0F1B-0x0F1F`, `0x0F3A-0x0F3F` and `0x0F4B-0x0F4F`, which
are the tail of each row from `M3T1`'s declared level of 11 onward — `0x0F0A` is
entry 11 itself, so the `UpT` run begins at the level rather than beyond it, and
`0x0F1B` is the `DownT` row cutting the one entry earlier.

**A correction to the issue as filed.** It lists nine `0xFF` addresses and
includes `0x0F48`. `0x0F48` is not one of them: it oscillates `0x3E`↔`0x44`
across the capture and never takes `0xFF`. The eighth address is `0x0F49`. The
issue's list is right about every other member of the set.

## What the capture is, as a whole

Every address the capture holds a row for is an address where the three
published tables differ. There is no address in it that is constant across
`M2T1`, `M1T1` and `M3T1`, and there is no address where they differ that the
capture omits.

That is the expected shape and it is worth stating, because it is what makes
the file usable as an oracle: `ec_watch` logs *changes*, so a table write
appears in the capture only where it changed something. A capture that held
every address in the window regardless would be recording the window, not the
event. This one records the event — which is why `fan_table_replay.py` can
reconstruct each burst's table from it and match all six against what the
service announced.

Going burst by burst and comparing every row's `new` value against the table
that burst carried: no row disagrees. The pre-burst state is `M3T1`, and the
resting dump `2026-09-23-power-mode-cycle-0f00-final.txt` is `M3T1` byte for
byte across the window.

**What this does not establish.** That the vendor's writes land is what
`docs/findings.md` §7 already says, and it is not what this page adds. Nothing
here says the EC *acts* on any byte of the table — that is §7's open question
and it is still open, because a byte that reaches the right value is not a byte
the EC has been observed to use. And no writer is attributed from this capture:
it is a passive watch, so it records what changed, never who changed it. The
match against `Fan/Table` is evidence about *which values* the window took, and
the service is the source of those values; it is not an observation of the EC
accepting a table.

## `0x070A` is a free-running sawtooth

The issue's other half is what `0x070A` does across the cycles, and the answer
is that it is not being poked at all.

In the sibling `2026-09-23-power-mode-cycle-0700-07ff.csv` — which is where the
`0xFD`/`0xC9` occurrences are, since the dated rule resolves row 7's literals in
the carrier — `0x070A` steps forward on every row and wraps:
`0xFE`→`0x00` at 17:58:24.418, `0xFE`→`0x00` at 17:58:51.011, and `0xFF`→`0x01`
at 18:00:09.782. Every step is `+1`, `+2` or `+3`, and the byte is monotone
modulo 256 across the whole capture — those three wraps are the only places its
value descends.

`0xC9` and `0xFD` are therefore points a ramp passes through on its way up.
They are not values the byte settled on and not a host write. The `0xC9` at
18:00:29.852 is the last row the file holds for that address, and the capture
ends four milliseconds later — that is where the recording stopped, not a
conclusion about the byte.

**The static side names a different writer than the mailbox.**
`0x070A` appears in `ec/annotations/manual-fan-ctrl-0751-arms.csv` only inside
`kind=callee` rows for `0x8B14` and `0x8C46`, always as `0x070A r+w`, and in no
`kind=arm` row. `ec/annotations/ghidra-functions.csv` describes
`ramp_1804_1809_toward_0461_0469` at bank0 `0x8C46` as incrementing `0x070A` on
the path guarded by `0x07C5` bit 7, `0x0741` bit 0 and `0x07C6` bit 2, and
`ramp_1804_toward_0670_and_set_1809` at `0x8DE0` as incrementing it too, on
passes where `0x070A` modulo an incoming rate byte is zero. Both are EC-side
ramp routines stepping a counter.

So the evidence points at an EC-side fan ramp rather than a host mailbox poke,
and that is as far as this goes. The mailbox the issue had in mind —
`0x0F5D`/`0x0F5E`, which the service writes `0xFD`/`0xC9` to as a ready token —
is a different address, and it is in **this** capture, not the sibling.

Which is where this capture's rows for those two addresses are worth reading
carefully, because what they support is narrower than "the mailbox was not
poked". They hold twelve rows between them, six each, and every one is a duty
value — `0xC8`, `0x6E` or `0xAA`, the same three the blocks take. Every one of
the twelve also lands in the same sweep as at least one other GPU duty slot in
`0x0F5A`-`0x0F5F`, so these rows move with their row rather than on their own.
That is what the capture recorded.

**What it cannot show is a poke that did not last a sweep.** `ec_watch` samples
the window on an interval and logs only a byte whose value differs from the
previous sweep, so a value written and overwritten between two samples leaves no
row at all. The sweep period in this capture is about 0.21 s — the gaps between
successive logged timestamps — while the handshake `ec-fan-table-defaults.md`
§4 describes is short-lived by design: the host writes the two ready tokens and
then polls `IsReadyToRead` every 500 ms until the EC has overwritten both. A
poke whose token window fell between two sweeps is fully consistent with these
twelve rows. So the claim is the narrow one: **not one of the rows this capture
holds for those two addresses carries a ready-token value** — not that the
mailbox went untouched.

The half that does not depend on ruling a poke out survives untouched, and it
is the better evidence anyway. `ec-fan-table-defaults.md` §4's reading is that
these are duty slots the copy overwrites: `0x0F5D`, `0x0F5E` and `0x0F5F` are
the GPU blob's own offsets `0x2D`, `0x2E` and `0x2F`, its last three duty
slots, so a driver polling them is reading two numbers out of the middle of a
fan curve rather than a handshake. Every row here for those two addresses is one
of the three duty values, in the same sweeps as the rest of their row, which is
what that reading predicts.

## Two corrections to the issue's citations

- **The `0xFD`/`0xC9` sentence is in `ec/tools/testdata/README.md`, row 7,
  third column.** `docs/findings/testdata-row-claims-report-naming.md` contains
  no `0xFD`, no `0xC9` and no "magic"; it is about report wording, and it
  declined to narrow the set by the prose's "power-mode-cycle" wording for the
  reason #794 gave. What its "1 of 6" passage does quote is one row of the CSV
  — `2026-09-23T17:59:01.727+02:00,0x0F58,0x8C,0x6E` — which is presumably the
  line the issue meant.
- **There is no `registers.yaml` entry for the fan table**, and there is no
  entry for any address in `0x0F00`-`0x0F5F`. That absence is load-bearing and
  deliberate: `tools/check_power_profile.py`'s rule 2 *requires* `0x0F00` to
  have no entry, because the prepared upstream patch's claim about that address
  **is** the absence. This page adds no entry and changes no `status:`; nothing
  here is a behavioural observation, and a `status:` is for one.

## On the carrier line itself

`dated_claim()`'s docstring already refuses to be read as a topic. It names "the
file that *satisfied* the claim, which is not the capture the sentence was
about", and says a report line is not the place to have quietly decided which
file a sentence meant. So the line naming this file has never been a statement
about which file the sentence was about — it is the price of the rule, printed.

This page is the prose that was missing. It leaves row 7 alone rather than
narrowing it, and the reason is worth recording: `ec/tools/testdata/README.md`
is a long shared table several pull requests touch, *and* its row-7 sentence is
the input `check_testdata_row_claims.py` parses. Narrowing the sentence would
move what the dated block resolves against, which is a behaviour change to a
checker and not a documentation edit. Saying so here answers the same question
— a reader has no way to know the report picked the carrier for them — without
either cost.

## What is still open

- **Whether the EC acts on the fan table.** Unchanged by this page and stated
  as unchanged: a byte reaching the right value is not evidence the EC uses it.
  `docs/findings.md` §7 records this as the question a Linux platform profile
  hinges on, and it still needs its own live test at the machine.
- **Who wrote `0x070A` in the live run.** The static annotations name EC-side
  routines that increment it, and the capture is consistent with a ramp. That is
  not an observation of the writer, and this page does not claim one.

Both need hardware this pipeline cannot reach, so neither is closed here. No
register was written or read back and no live test ran; nothing in this page is
hardware evidence.