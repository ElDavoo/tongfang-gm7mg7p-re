# Ask the EC for its own fan table, once per mode, and read what it writes

**Status: not run (issue #100).** This procedure was written by the pipeline
for a human at the physical GM7MG7P. `CLAUDE.md` is explicit that the
GitHub-hosted runners cannot reach the hardware, and nothing below has been
observed: no register has been written, no register has been read back, and
no result is recorded anywhere in this repository. The tools
(`../../windows/tools/ecrw.py`, `../../windows/tools/ec_watch.py`) and the
static decode the run is meant to confirm
([`../findings/ec-fan-table-defaults.md`](../findings/ec-fan-table-defaults.md))
are committed; the reading is not. §7 says what a result has to say, and
`0x0782` and the whole `0x0F00-0x0F5F` window stay at the status they hold
today — a `status:` move is for a *behavioural observation*, and a prepared
procedure is not one.

**This is the live half of a static finding, and it is the half that matters
for a driver.** §2 of the write-up has the EC's own per-mode tables decoded
out of CODE, and they are **not** the tables the vendor service applies. That
is a statement about bytes in an image. This procedure is what would settle
whether the EC really copies them into `0x0F00-0x0F5F` on request, and what a
driver reading the mailbox would then get.

**The one thing this run cannot settle** is the `0x0782` bit 2 question from
§3 of the write-up. The two Office tables are byte-identical, so a run that
fetched Office once with the bit clear and once with it set would see the
same bytes either way and could not tell a duplicate from a missing table. Run
the Office handshake **twice**, flipping `0x0782` bit 2 between them, purely
as a control: if the two fetches differ, the static reading was wrong and
that is a result; if they match, the run has confirmed the duplicate and
nothing more.

## 1. The question

The vendor service's `RefreshDefaultFanTable`
(`FanTable_Manager1p5.cs:827`) gets the EC's own default curve per mode over
a three-byte mailbox, and `RefreshDefaultFanTableAll` (`:790`) runs it for
Gaming, Office and Turbo when the EC version changes or the local JSONs are
missing. On this machine it never ran: the 2026-09-23 capture did not
exercise it, and the stored `DefaultFanTable_*.json` files are dated
2025-06-23.

The EC side is decoded — bank0 `0x888D`, `fan_table_mailbox_handler`
(`ec/annotations/manual-fan-ctrl-0751.md` §6) — and the tables it copies are
decoded in the write-up. What is unobserved is the copy. Three questions,
in the order they matter:

1. **Does the handler fire on the magic, and does `0x0F00-0x0F5F` come to
   hold the decoded bytes?** This is the whole point. A confirmation here
   turns §2 of the write-up from "the bytes the handler would copy" into "the
   bytes the EC put there".
2. **Does the writeback unblock `IsReadyToRead` as §4 of the write-up says?**
   That is, do `0x0F5D`/`0x0F5E` come to hold the GPU table's own last two
   duty slots (`0xB4` for Gaming and Turbo, `0x64` for Office) rather than
   something else?
3. **Does the copy survive the service's next action, and does anything else
   move?** The service rewrites the whole bundle on a mode switch, so this is
   about the window *between* the handshake and the next switch.

## 2. Before you start

- **Windows, Control Center 3.1.39.0 installed, the vendor's ACPI driver
  present and started, an elevated shell.** `python windows\tools\ecrw.py
  read 0x0F00` printing a value is the check.
- **AC plugged in for the whole session.** The service rewrites the whole
  bundle on every AC ↔ battery change, which would drown the thing being
  measured.
- **The Control Center service running, and left running.** A driver would
  meet the service in this state, and stopping it is not what this run is
  about. One consequence is named in §6: the service also clears and sets
  `0x0741` bit 0, so the handshake's own clear is not the only one that can
  land.
- **Do not switch power modes during a run.** The service rewrites
  `0x0F00-0x0F5F` on every mode switch, and the handshake writes `0x0F5F`
  rather than `0x0751`, so a mode switch is the one thing in this session
  that would put bytes in the window that the handshake did not.
- **The fan-speed readout, noted by hand and by wall clock, for each
  handshake.** The CSV carries no fan speed. The Control Center's own RPM
  display is the number this machine is sold on and is the same quantity the
  `PRIMARY_FAN`/`SECONDARY_FAN` sysfs was confirmed against
  ([`../findings.md`](../findings.md)); on a Linux pass the sysfs is the same
  number. A duty is not a speed — it is what the fan is being asked for, not
  what it is doing — so `0x075B`/`0x075C` corroborate a direction and never
  establish one.
- **The current mode as the vendor UI reports it**, and the starting
  `0x0751`, written down.

### Safety

**The magic parks two duty slots above 100 %.** `0x0F5D` and `0x0F5E` are GPU
duty entries 13 and 14 (§4 of the write-up), and the handshake writes
`0xFD` and `0xC9` into them. On the doubled scale where `0xC8` is 100 %, those
are **126.5 % and 100.5 %**. Nothing clamps them in the window; whether the
EC clamps them on the way to a fan is exactly what is not established. Keep
the handshake short, and **if the fans audibly change, restore immediately**
(§4's restore line) rather than finishing the step.

**Clearing `0x0741` bit 0 is the state the PL clear waits for.**
`manual-fan-ctrl-0751.md` §4 records a main-EC routine that zeroes
PL1/PL2/PL4 at `0xA833`–`0xA83B` precisely when `0x0741` bit 0 is **clear**,
and §6 records that this is the same condition the service deliberately parks
the EC in for this handshake. Whether the two can overlap depends on when that
routine runs, which is unresolved. **Corrected 2026-10-03 (issue #109), the
sentence above is left as written:** that routine is reached on two of the
divide-down scheduler's nine cases, so it is a recurring polled task and the
overlap is **possible**; whether it happens during *this* handshake is still
open, and that is what watching the PLs would show — see
[`../findings/a7c8-dispatch-slot-and-pl-race.md`](../findings/a7c8-dispatch-slot-and-pl-race.md).
**Watch `0x0783`, `0x0784` and `0x0785` alongside the window** (§3's watch
set widens to cover them) and report any movement — a PL register going to
zero around a handshake would be the first evidence that the overlap is real,
and it is the thing most worth catching while the machine is in front of you.

**Do not read `0x0460`–`0x046F`.** Reading the fan-tachometer registers
through `ECRR` stalled the fans on a sibling board, and both the OEM software
and `uniwill-laptop` sleep 6 ms after every EC access because of it
([`../related-projects.md`](../related-projects.md), issue #94). Nothing in
this procedure's watch set is on that page: `ec_watch.py` reads a contiguous
range with one `readmany` per sweep, so the whole 165-byte watch set is
**two** `ECRR` reads per sweep, not 165.

**Write `0x0F5D`, `0x0F5E`, `0x0F5F`, `0x0741` and `0x0782`, and nothing
else.** Every one of those is named in §3 with its value, and `ecrw.py write`
refuses without `--i-mean-it` so the command has to be typed deliberately.
**Write no more of the window than the handshake needs** — the restore in §4
puts back a full `0x60`-byte dump, which is the one wide write in the
procedure and the reason the pre-dump in §3 is not optional.

## 3. The run

**Anchor first.** The restore in §4 needs the bytes the service had written,
taken *before* anything is disturbed, and the anchor doubles as the "before"
side of the comparison:

```console
python windows\tools\ecrw.py dump 0x0F00 0x60 > <date>-0f5d-before.txt
python windows\tools\ecrw.py read 0x0741 0x0782 0x0751 0x0F5D 0x0F5E 0x0F5F
```

`0x0F5D`–`0x0F5F` should already be *something*: they are the GPU table's
last three duty slots, so after a mode switch they hold the service's duty
for that mode. **Record what they hold.** If they already differ from
`0xFD`/`0xC9`, then `IsReadyToRead` would have returned ready before the
handshake started, and §1's second question has a precondition failure to
report.

**The watch set is two passes per handshake.** `ec_watch` takes one
contiguous range and reads it with a single `readmany` per sweep, so the set
is the window itself, and `0x0741`-`0x0785` — `AP_OEM`, `0x0751`, the two
fan-duty bytes `0x075B`/`0x075C`, `0x0782` and PL1/PL2/PL4 in one 69-byte
read. 165 bytes per sweep, two ECRR reads. `20 s` and `--interval 0.25` are
`ec_watch`'s own defaults for a range this size; **no interval here is
validated**, and issue #94 is the open work that would make these tools safe
by default. **If the fans audibly change, stop and restore (§4).**

**Pass 1 — one handshake per mode, service running.** For each mode: start
the two watchers, run the handshake in the second shell, wait the watchers
out. `0x0F5F` is 2 for Gaming, 3 for Office, 1 for Turbo.

```console
rem  Terminal 1, watchers. Start these, then the handshake, then wait.
python windows\tools\ec_watch.py --start 0x0F00 --len 0x60 --seconds 20 ^
        --interval 0.25 --csv <date>-0f5d-gaming-window.csv
python windows\tools\ec_watch.py --start 0x0741 --len 0x45 --seconds 20 ^
        --interval 0.25 --csv <date>-0f5d-gaming-pl.csv
python windows\tools\ec_watch.py --start 0x0F00 --len 0x60 --seconds 20 ^
        --interval 0.25 --csv <date>-0f5d-office-window.csv
python windows\tools\ec_watch.py --start 0x0741 --len 0x45 --seconds 20 ^
        --interval 0.25 --csv <date>-0f5d-office-pl.csv
python windows\tools\ec_watch.py --start 0x0F00 --len 0x60 --seconds 20 ^
        --interval 0.25 --csv <date>-0f5d-turbo-window.csv
python windows\tools\ec_watch.py --start 0x0741 --len 0x45 --seconds 20 ^
        --interval 0.25 --csv <date>-0f5d-turbo-pl.csv
```

```console
rem  Terminal 2, the handshake. <sel> is 0x02, 0x03, 0x01 for Gaming, Office,
rem  Turbo. Do this once per mode, between that mode's two watchers.
rem
rem  1. clear AP_OEM bit 0 -- the same gate the service clears
python windows\tools\ecrw.py write 0x0741=0x0E --i-mean-it
rem  2. the selector, then the magic. Order matters only in that the magic is
rem    what 0x888D tests, so writing the selector first is what the service
rem    does and what a driver should do.
python windows\tools\ecrw.py write 0x0F5F=0x02 --i-mean-it
python windows\tools\ecrw.py write 0x0F5D=0xFD 0x0F5E=0xC9 --i-mean-it
rem  3. poll, exactly as IsReadyToRead does: every 500 ms, until BOTH differ
rem    from the magic, three times max. Record what it read each time.
python windows\tools\ecrw.py read 0x0F5D 0x0F5E
rem  4. set AP_OEM bit 0 again -- before the restore, as the service does
python windows\tools\ecrw.py write 0x0741=0x0F --i-mean-it
```

`0x0E` and `0x0F` are `0x0741` with bit 0 clear and set. **Read `0x0741` and
write back that value with bit 0 changed**, rather than the literals — if the
service has it at something other than `0x0E`/`0x0F`, the literals clobber
the other bits, and `0x0741` is the AP-present gate the whole fan path runs
behind.

**Pass 2 — the `0x0782` bit 2 control, service stopped.** `sc stop` on the
Control Center service, confirmed with the vendor UI gone. Two more Office
handshakes, `0x0F5F` = 3, with the bit cleared and set, watchers running as
in pass 1. **This is a control, not the main run:** it is the only part of
this procedure that can say anything about `0x0782`, and §1 already says what
it cannot.

```console
python windows\tools\ecrw.py read 0x0782
python windows\tools\ecrw.py write 0x0782=0x9C --i-mean-it
python windows\tools\ec_watch.py --start 0x0F00 --len 0x60 --seconds 20 ^
        --interval 0.25 --csv <date>-0f5d-office-b2-clear-window.csv
python windows\tools\ec_watch.py --start 0x0741 --len 0x45 --seconds 20 ^
        --interval 0.25 --csv <date>-0f5d-office-b2-clear-pl.csv
python windows\tools\ecrw.py write 0x0782=0x9D --i-mean-it
python windows\tools\ec_watch.py --start 0x0F00 --len 0x60 --seconds 20 ^
        --interval 0.25 --csv <date>-0f5d-office-b2-set-window.csv
python windows\tools\ec_watch.py --start 0x0741 --len 0x45 --seconds 20 ^
        --interval 0.25 --csv <date>-0f5d-office-b2-set-pl.csv
rem  ... and the handshake block above, with 0x0F5F=0x03, once per state.
```

`0x9C` and `0x9D` are `0x0782` with bit 2 clear and set, **conditional on the
byte actually reading `0x9D` first** — `windows/vendor-ec-map.md` records
`0x9D` on this machine, and `0x0782` carries the BIOS default-mode bit and
the Q-key bit alongside bit 2, so a literal is a hazard here and a
read-modify-write is not. **Set the bit back to what it was before the
session ends**, whatever the outcome, and restart the service before you
close the lid.

## 4. Restore, and do it even if a step failed

The handshake overwrites 96 bytes with the EC's own table. The service will
put its own back on the next mode switch, but nothing guarantees a mode switch
happens, so restore from the §3 anchor by hand:

```console
rem  Put the service's table back. 0x0F60 is 0x0F00-0x0F5F, every byte of it,
rem  so this is the one wide write in the procedure -- which is why the §3
rem  anchor is not optional.
python windows\tools\ecrw.py write 0x0F5D=<before> 0x0F5E=<before> 0x0F5F=<before> --i-mean-it
rem  ... and the rest of the window from <date>-0f5d-before.txt.
rem
rem  Then confirm: the dump must equal the anchor.
python windows\tools\ecrw.py dump 0x0F00 0x60 > <date>-0f5d-after.txt
fc <date>-0f5d-before.txt <date>-0f5d-after.txt
```

**Do this even if a handshake failed, timed out, or you stopped the run
part-way.** The window now holds the EC's table rather than the service's,
and on a machine whose fan curve is a real thing that is not a state to leave
it in. `0x0782` and `0x0741` go back to their pre-run values too — §3's
`read` of both is the record.

## 5. Where the output goes

Everything into `evidence/ec-watch/`, named `<date>-0f5d-*` where `<date>` is
the run's `YYYY-MM-DD`. The two `.txt` files are the before/after anchors of
§3 and §4 and the only ones that have to exist for the restore to be provable;
the rest are the captures §7 grades.

```
evidence/ec-watch/<date>-0f5d-before.txt
evidence/ec-watch/<date>-0f5d-after.txt
evidence/ec-watch/<date>-0f5d-gaming-window.csv
evidence/ec-watch/<date>-0f5d-gaming-pl.csv
evidence/ec-watch/<date>-0f5d-office-window.csv
evidence/ec-watch/<date>-0f5d-office-pl.csv
evidence/ec-watch/<date>-0f5d-turbo-window.csv
evidence/ec-watch/<date>-0f5d-turbo-pl.csv
evidence/ec-watch/<date>-0f5d-office-b2-clear-window.csv
evidence/ec-watch/<date>-0f5d-office-b2-clear-pl.csv
evidence/ec-watch/<date>-0f5d-office-b2-set-window.csv
evidence/ec-watch/<date>-0f5d-office-b2-set-pl.csv
```

The hand-written record is a short note beside them, not a file of its own:
the starting mode, what `0x0F5D`–`0x0F5F` held before the first handshake,
the fan-speed reading and wall-clock time for each of the five handshakes,
and which row of §7's table the run turned out to be. **A note is the
operator's and the commands cannot produce it**, which is the same allowance
`manual-fan-ctrl-0751-isolation.md` §2 carries for its snapshot.

## 6. Reading the capture

Each `--csv` is `ec_watch`'s own format: `ts,addr,old,new` per change, plus
`MARK` rows. There is no grader for this run and none is needed — the
questions in §1 are three byte comparisons, and a grader that turned them into
a verdict would be a second thing to keep honest.

- **The window after the magic** is what the decode predicted. Compare
  `<date>-0f5d-gaming-window.csv` against the committed
  `ec/annotations/fan-table-defaults.csv` row for that mode and fan, through
  `windows/tools/fan_table_replay.py`'s `ec_image()` layout. §7 has the
  command. **A mismatch is a result**, and §7 says what it means.
- **The `quiet` column is the interesting one.** `ec_watch` separates
  addresses that changed many times from ones that changed once or twice, and
  a settings write looks like the second. Ninety-six bytes changing in one
  burst is the copy; anything else that moved in the window is a second
  writer and is worth naming.
- **`0x0F5D`/`0x0F5E` are duty slots, so their "new" values are duties.**
  `0xB4` is 90 % and `0x64` is 50 %, and a value of `0xC8` or above is not a
  duty the service ever wrote.
- **The PL file** is the one to read first if anything moved. `0x0783`–`0x0785`
  going to zero while `0x0741` bit 0 was clear is the `0xA833` overlap
  becoming real, and that is a bigger result than the fan table. The same
  file says whether the service set `0x0741` bit 0 back before the run's own
  write did: if it did, the handshake was racing the service, and the capture
  has to say so before any of it is read as the EC's.

## 7. What a result has to say

Every outcome below is reportable, and which one happened decides what moves
in the repository:

| what the capture shows | what it means | what it changes |
| --- | --- | --- |
| The window equals the committed CSV, `0x0F5D`/`0x0F5E` land on `0xB4`/`0x64`, and the two Office fetches are byte-identical | The static decode is confirmed on hardware | §2 and §4 of the write-up can say the copy was observed; the `0x0782` bit 2 duplicate is confirmed for this build; a driver may read the mailbox. `0x0782` itself is still not a `confirmed-working` byte — this shows the *fetch*, not the bit |
| The window differs from the committed CSV in named bytes | The static decode is **wrong**, and §2 of the write-up has to be corrected in place per `CLAUDE.md` §4a-4d | a correction, not a new section; the CSV follows the image, not the capture |
| The window does not change at all | The handler does not fire on this EC, or fires somewhere other than `0x888D` | the negative is a result: the static reading of the trigger is wrong, and the write-up's §6 "still the mailbox" has to be revisited |
| The PL bytes go to zero while `0x0741` bit 0 was clear | The `0xA833` overlap is real | the biggest result in this document, and it is a hardware hazard rather than a fan-curve fact. It belongs in `manual-fan-ctrl-0751.md` §4 and in the issue that chases `0x851B`'s framing |
| `0x0F5D`/`0x0F5E` land on something other than the GPU table's own bytes | §4's writeback mechanism is wrong, and the readiness handshake is doing something this reading missed | a correction to §4, and the `IsReadyToRead` story has to be re-derived |
| The service rewrote the window between handshakes with no mode switch | There is a second writer of `0x0F00-0x0F5F` on this path | a new register-census row and a follow-up issue; `manual-fan-ctrl-0751.md` §5's negative would need re-scoping |

**Commit the captures, not a summary.** `evidence/ec-watch/<date>-0f5d-*.csv`
and the before/after dumps, then say in the write-up which row of the table
above happened. A one-line "confirmed" with no capture behind it is worth
nothing here, and the whole point of the file is that a human owns the
observation.

## 8. Reproducing the comparison offline

Once a capture exists, the decode and the comparison re-run with no hardware
at all — that is what `fan_table_defaults.py` is for, and it is how a
committed capture gets checked against the image rather than against prose:

```console
rem  the static decode, which is what the capture is being compared to
python ec\tools\fan_table_defaults.py
python ec\tools\fan_table_defaults.py --check
rem
rem  the capture's burst history, replayed backwards from the after-anchor.
rem  --mqtt is a capture this repository already holds rather than one this
rem  run writes, so it goes in through a variable: a bare path on the command
rem  line reads as an artifact the run produced, and the output list above
rem  would then owe an entry for a file from 2026-09-23.
set MQTT=evidence\mqtt-capture\2026-09-23-power-mode-cycle.jsonl
python windows\tools\fan_table_replay.py --csv <date>-0f5d-gaming-window.csv ^
        --final <date>-0f5d-after.txt --mqtt %MQTT%
```

The last command will report `no published table` for the states this
procedure produced, and **that is the expected answer**: the EC's table is not
any of `M1T1`/`M2T1`/`M3T1`, which is the finding. It is worth running
anyway, because a state it *does* name would mean the service had rewritten
the window and the capture is not the handshake's.

## 9. Related

- [`../findings/ec-fan-table-defaults.md`](../findings/ec-fan-table-defaults.md)
  — the static decode this run confirms or refutes.
- [`../../ec/annotations/manual-fan-ctrl-0751.md`](../../ec/annotations/manual-fan-ctrl-0751.md)
  §4 and §6 — the handler decode, and the `0x0A833` PL clear this procedure's
  watch set exists to catch.
- [`../../windows/vendor-ec-map.md`](../../windows/vendor-ec-map.md),
  "Fan tables" — the host half, the service's applied tables, and the sentence
  this run closes.
- [`manual-fan-ctrl-0751-isolation.md`](manual-fan-ctrl-0751-isolation.md) —
  the same window under a different question, with the graded-capture
  machinery this one deliberately does not use.
