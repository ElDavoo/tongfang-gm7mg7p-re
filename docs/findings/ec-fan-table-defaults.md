# The EC's own fan tables: where they live, what they say, and how far they are from the vendor's

(2026-09-30. Static reading of `ec/firmware/GMxMGxx_11.800` and committed
files. No image is opened for writing, no register is read back, and no
laptop, EC or Windows machine is involved: every byte below comes out of the
committed image through `ec/tools/fan_table_defaults.py`, and every table is
reproducible with the commands in §7.)

**The comparison `windows/vendor-ec-map.md` closed issue #92's predecessor
with open is now done, and the answer is that the EC's tables are not the
vendor's.** They are the same *shape* — which is what
`ec/annotations/manual-fan-ctrl-0751.md` §6 could already say from the bytes
— and a different curve: the EC's `UpT` rows are a uniform 3–4 °C ladder
where the service's are hand-set per level, and the top duty differs in every
mode. A Linux driver that reads the EC's tables over the mailbox gets a real
curve, and a quieter one than Windows applies in two modes out of three.

Two results are not about the comparison, and both change what the selector
means:

- **`0x0782` bit 2 selects between two byte-identical Office tables.** Turbo
  and Gaming are byte-identical too, so the four slots hold **two** distinct
  CPU tables and **two** distinct GPU tables, not four of either.
- **Nothing writes `0x0F5D`/`0x0F5E` as "ready."** The second copy is 48
  bytes to `0x0F30`, which covers `0x0F5F` *inclusive*, so the mailbox bytes
  are the GPU table's own last three duty slots. That is the whole of the
  writeback, and it answers the issue's third sub-question.

Nothing here is a behavioural test. These are the bytes the handler would
copy, on the code that copies them.
`../../docs/hardware-tests/fan-table-defaults-0f5d.md` is the unrun procedure
that would settle it.

## 1. Where the tables live

The handler is bank0 `0x888D`, `fan_table_mailbox_handler`, listed at
`ec/decompiled/bank0/888D.asm` / `.c` and decoded in
`ec/annotations/manual-fan-ctrl-0751.md` §6. It takes a CODE pointer base the
EC seeds at `0x8653`:

```
0x8653  7e 60      mov   r6, #0x60
0x8655  7f f2      mov   r7, #0xf2
0x8657  90 08 e6   mov   dptr, #0x08e6
0x865a  ee         mov   a, r6
0x865b  f0         movx  @dptr, a          ; 0x08E6 = 0x60
0x865c  a3         inc   dptr
0x865d  ef         mov   a, r7
0x865e  f0         movx  @dptr, a          ; 0x08E7 = 0xF2
```

So the base is **`0x60F2`**, big-endian in `0x08E6`/`0x08E7`, and the handler
adds to its *low* byte — `add a,#0x0c` at `0x88BB` and friends, applied to
the byte it re-reads from `0x08E7`, so an offset that carried out would wrap
into a different pair rather than the next one. Two helpers build the pointer
into `0x0A47`/`0x0A48`: `0xBC4F` adds nothing, and `0xBCCB` adds the byte the
branch computed. The four offsets the branches can produce, and what each
resolves to:

| slot | `0x0F5F` | `0x0782` bit 2 | helper | CPU CODE | GPU CODE |
| --- | --- | --- | --- | --- | --- |
| `0x60F2` | 2 | — | `0xBC4F` | `0x56A2` | `0x5762` |
| `0x60F6` | 3 | 0 | `0xBCCB` | `0x56D2` | `0x5792` |
| `0x60FA` | 3 | 1 | `0xBCCB` | `0x5702` | `0x57C2` |
| `0x60FE` | 1 | — | `0xBCCB` | `0x5672` | `0x5732` |

`0x60F2` is a table of big-endian CODE pointer **pairs**, so each slot names
two 48-byte blobs. All eight addresses are below `0x8000`, which puts them in
the common area: their file offset in the 256 KiB dump *is* their runtime
address, and no `make_bank_image.py` run is needed. That is not an
assumption — the tool goes through `trace_xdata_refs.offset_for_runtime()` and
**refuses** a slot at or above `0x8000` rather than reading it at its own
address, because which bank is mapped is not in the byte.

The mode names in that table are the service's, from `SetFanMode`'s `0x0751`
values (`0x00` Gaming, `0xA0` Office, `0x10` Turbo). The mailbox's own
numbering is the other way round, 1 Turbo / 2 Gaming / 3 Office, and
`RefreshDefaultFanTableAll` (`FanTable_Manager1p5.cs:790`) asks for them as
`RefreshDefaultFanTable(ref DefaultFanTable_Gaming, 2)`, `…_Office, 3`,
`…_Turbo, 1`. **There are three numberings for "which table" on this path** —
the `0x0751` mode bits, the `0x0F5F` selector, and `0x0782` bit 2 — and the
table above is the join. `ec/tools/test_fan_table_defaults.py`
`TheModeMapping` parses the three calls back out of the committed `.cs` and
holds the tool's selectors against them, because a join that silently
inverted one of the two would still have produced four plausible-looking
tables.

## 2. The tables, in the vendor's own field names

Decoded through the layout `windows/tools/fan_table_replay.py`'s `ec_image()`
documents, which is `SetEcFanTable` (`FanTable_Manager1p5.cs:556`) and its
inverse `GetEcFanTable` (`:499`): `0x0F00+i` is entry `i+1`'s `UpT`,
`0x0F11+i` is entry `i`'s `DownT`, and `0x0F20+i` is entry `i`'s `Duty` × 2.
Unused steps are `0xFF` and the last duty repeats. The tool re-encodes every
decode through `ec_image()` as a round-trip, so the layout is the vendor's
and not a second copy of it.

| mode | fan | `UpT`, levels 1.. | `DownT`, levels 0.. | `Duty`, levels 0.. |
| --- | --- | --- | --- | --- |
| Office, `0x0782` bit 2 = 0 | CPU | 54 58 62 66 69 72 75 78 | 48 50 63 67 70 73 76 78 | 0 30 30 35 45 45 50 50 50 |
| | GPU | 53 54 58 61 64 67 68 69 | 48 55 59 62 65 68 69 70 | 0 30 30 35 45 45 50 50 50 |
| Office, `0x0782` bit 2 = 1 | CPU | *(identical to the row above)* | *(identical)* | *(identical)* |
| | GPU | *(identical to the row above)* | *(identical)* | *(identical)* |
| Gaming | CPU | 54 58 62 66 69 72 75 78 81 84 | 48 50 61 65 68 71 74 77 80 83 | 0 30 30 35 45 45 50 50 65 75 90 |
| | GPU | 54 54 58 61 64 67 70 73 76 79 | 48 48 57 60 63 66 69 72 75 78 | 0 30 30 35 45 45 50 50 65 75 90 |
| Turbo | CPU | *(identical to Gaming)* | *(identical)* | *(identical)* |
| | GPU | *(identical to Gaming)* | *(identical)* | *(identical)* |

Committed as `ec/annotations/fan-table-defaults.csv`, one row per slot and
fan, and held to the image by `fan_table_defaults.py --check`.

**`0x0F10` is the one byte neither side touches.** `SetEcFanTable` never
writes it, `GetEcFanTable` never reads it, and the EC's blobs have `0x00`
there — it is the gap between the two step rows, and `decode_blob()` therefore
never looks at it. It is the one offset in a half the round-trip through the
vendor's writer cannot cover, and it is named rather than counted as covered.

## 3. Two of the four slots are duplicates

Comparing the 48-byte blobs directly:

| pair | identical? |
| --- | --- |
| Turbo CPU `0x5672` vs Gaming CPU `0x56A2` | **yes, all 48 bytes** |
| Turbo GPU `0x5732` vs Gaming GPU `0x5762` | **yes, all 48 bytes** |
| Office bit-2-clear CPU `0x56D2` vs bit-2-set CPU `0x5702` | **yes, all 48 bytes** |
| Office bit-2-clear GPU `0x5792` vs bit-2-set GPU `0x57C2` | **yes, all 48 bytes** |

So the four selectors reach **two** distinct CPU tables and **two** distinct
GPU tables, and Office differs from both Gaming and Turbo — which is what
makes these two findings rather than one. The suite holds the identities as
the pairs they name and separately holds that Office is *not* Gaming, because
"all four tables are the same bytes" would otherwise satisfy the first two
cases and make both findings vacuous.

**What this says about `0x0782` bit 2.** `registers.yaml` documents it as the
Office fan-table type, and `manual-fan-ctrl-0751.md` §6 records that its
getter is never called. On the one path where the EC reads it, it selects
between two tables that are byte for byte the same, so **a driver writing the
Office curve would be indifferent to the bit either way.** That is a fact
about this firmware image and not a statement that the bit is unused: either
the EC ships a duplicate, or a differentiated Office table is missing from
this build. Which one is not decidable from the image.

`0x0782` stays `present-untested`, deliberately: this work reads the bit
statically and establishes nothing about its behaviour, and per `CLAUDE.md` a
`status:` is for a behavioural observation.

## 4. What the EC writes back as "ready"

The host's handshake (`RefreshDefaultFanTable`,
`FanTable_Manager1p5.cs:827`) writes the selector to `0x0F5F`, then `0xFD` to
`0x0F5D` and `0xC9` to `0x0F5E`, and polls `IsReadyToRead` (`:814`) every
500 ms until the EC has overwritten both. The EC's answer is a side effect,
not a store:

```
0x88ec  90 0a 4b   mov   dptr, #0x0a4b
0x88ef  74 0f      mov   a, #0x0f
0x88f1  f0         movx  @dptr, a
0x88f2  a3         inc   dptr
0x88f3  74 00      mov   a, #0x00
0x88f5  f0         movx  @dptr, a           ; destination 0x0F00
...
0x890b  b4 30 f6   cjne  a, #0x30, 0x8904   ; 48 bytes
0x890e  90 0a 4b   mov   dptr, #0x0a4b
0x8911  74 0f      mov   a, #0x0f
0x8913  f0         movx  @dptr, a
0x8914  a3         inc   dptr
0x8915  74 30      mov   a, #0x30
0x8917  f0         movx  @dptr, a           ; destination 0x0F30
...
0x892e  b4 30 f6   cjne  a, #0x30, 0x8927   ; 48 more
```

`0x0F30` + `0x30` − 1 is `0x0F5F`, so the second copy's range is
`0x0F30..0x0F5F` **inclusive** and covers the mailbox. `0x0F5D`, `0x0F5E` and
`0x0F5F` are the GPU blob's own offsets `0x2D`, `0x2E`, `0x2F` — the last
three duty slots:

| slot | `0x0F5D` | `0x0F5E` | `0x0F5F` | as a duty |
| --- | --- | --- | --- | --- |
| Gaming / Turbo | `0xB4` | `0xB4` | `0xB4` | 90 %, 90 %, 90 % |
| Office (either) | `0x64` | `0x64` | `0x64` | 50 %, 50 %, 50 % |

Neither `0xB4` nor `0x64` is the magic, so `IsReadyToRead` — which returns
ready when *both* `0x0F5D` and `0x0F5E` differ from `0xFD`/`0xC9` — unblocks.
No site writes those three addresses on purpose. `scan_refs.py` finds **one**
direct `mov dptr,#0x0F5D` site, **zero** for `0x0F5E` and **two** for
`0x0F5F`, and the handler reaches all three by `inc dptr` from `0x0F5D`
(`888D.asm:8898`) — the same computed-`DPTR` blind spot
`manual-fan-ctrl-0751.md` §6 works through on `0x0F00`. **A zero here is "not
found by this method", never absent.**

The writeback is not a handshake token, and it is not unique to the mailbox:
`0x0F5F` is GPU duty entry 15, so the selector the host writes there is
itself a duty slot until the copy overwrites it. Any driver polling
`0x0F5D`/`0x0F5E` is reading two numbers out of the middle of a fan curve,
which is worth knowing before it treats a match as a handshake acknowledgement.

## 5. The comparison

**What this is compared against.** The `DefaultFanTable_*.json` files the
issue names live in `UserFanTables\` on the machine and are **not in this
repository**. What is committed is the `Fan/Table` MQTT capture, and
`fan_table_replay.py` already proved those publishes equal the bytes the
service wrote into `0x0F00-0x0F5F`, byte for byte, across all seven table
states of the 2026-09-23 power-mode cycle. So this compares against the
tables the service actually **applies** — `M1T1` (Gaming), `M2T1` (Office),
`M3T1` (Turbo) — which is a different claim from a comparison against the
stored-default files, and is labelled as one here and in the tool's docstring.

No mode matches on any row, on either fan:

| mode | `Duty` EC | `Duty` service | top duty, EC vs service |
| --- | --- | --- | --- |
| Office | 0 30 30 35 45 45 50 50 50 | 0 30 30 35 45 48 50 55 55 | **50 % vs 55 %** |
| Gaming | 0 30 30 35 45 45 50 50 65 75 90 | 0 30 30 35 45 48 50 55 70 85 | **90 % vs 85 %** |
| Turbo | 0 30 30 35 45 45 50 50 65 75 90 | 0 30 30 35 45 48 50 55 70 85 100 | **90 % vs 100 %** |

The shape difference is in the ramps, and the tool measures it rather than
leaving it to the eye. Taking the distinct consecutive differences of a row:

| row | EC | service |
| --- | --- | --- |
| `UpT`, Gaming CPU | `{3, 4}` | `{2, 4, 5, 8}` |
| `Duty`, Gaming CPU | `{0, 5, 10, 15, 30}` | `{0, 2, 3, 5, 10, 15, 30}` |

**The EC's `UpT` rows are a uniform 3–4 °C ladder on all six tables**; the
service's are hand-set, with an 8 °C jump at level 8 of the Gaming CPU
ramp. **The EC's `Duty` rows step by 5 %**; the service's step by 2, 3, 5,
10, 15 and 30. The EC's `DownT` rows are the same ladder with one wider first
jump — 48 → 50 → 61 on the CPU tables, 48 → 48 → 57 on the GPU ones — so
"a uniform ladder" is a claim about `UpT` and about the steady state of
`Duty`, and not about all three rows.

The consequence for a driver is the one the issue was opened for. Reading
the EC's own curve over the mailbox is clean and needs no shipped table, and
it gets you **50 % instead of 55 % in Office, 90 % instead of 85 % in Gaming,
and 90 % instead of 100 % in Turbo** — quieter than the vendor's curve in
two modes out of three, louder in one. Which of the two a Linux driver should
apply is a design call, not a reverse-engineering question, and the point of
this comparison is that both are now in hand rather than one being a
presumption about the other.

## 6. What this does not say

- **Nothing here is a live test.** No register was written, none was read
  back, and no fan was observed. These are the bytes the handler would copy,
  on the code that copies them. `0x0782` and the whole `0x0F00-0x0F5F` window
  stay at the status they hold today.
- **The trigger is still the mailbox.** `manual-fan-ctrl-0751.md` §6's
  negative stands: no `0x0751` site reaches this code and the selector is
  read from `0x0F5F`, never from the mode byte, so a mode change alone does
  not reload the table. Whether some other path also calls the copy is not
  something a site scan can rule out.
- **The pointer table's extent was not determined.** `0x60F2` holds more
  pairs past the four the handler reaches; where it ends, and what selects
  the rest, is not read here.
- **The two Office slots being identical is a fact about this image.** It
  does not say the EC ships a duplicate rather than this build missing a
  differentiated table. Both readings fit the bytes.

## 7. Reproducing it

```console
$ python3 ec/tools/fan_table_defaults.py                 # the decode and the comparison
$ python3 ec/tools/fan_table_defaults.py --csv | diff - ec/annotations/fan-table-defaults.csv
$ python3 ec/tools/fan_table_defaults.py --check
$ python3 ec/tools/fan_table_defaults.py --self-test
$ python3 ec/tools/test_fan_table_defaults.py
$ python3 ec/tools/scan_refs.py ec/firmware/GMxMGxx_11.800 0x0F5D 0x0F5E 0x0F5F 0x0F00
```

The `--self-test` holds an oracle transcribed from
`ec/annotations/manual-fan-ctrl-0751.md` §6 rather than from the tool's own
output, and the suite holds the write-up's figures against the image rather
than against a transcription of either. A firmware whose tables moved makes
both red.

The handler's own decoding is in
`ec/annotations/manual-fan-ctrl-0751.md` §6 and is not repeated here; this
write-up adds the pointer resolution, the decoded contents, the two
byte-identities, the writeback mechanism and the comparison.
`windows/vendor-ec-map.md` "Fan tables" is where the host half and the
service's applied tables are recorded, and the sentence this closes is the
last paragraph of that section.

## 8. What this opens

- **The duplicate Office table is the follow-up seed.** If `0x0782` bit 2
  selects between two byte-identical tables, either the EC ships a duplicate
  or a differentiated Office table is missing from this firmware. A driver
  that writes the Office curve is indifferent to the bit either way, which is
  worth knowing before anything is built on it.
- **The EC-vs-service duty gap is a driver design call**, not a
  reverse-engineering question: a Linux author now has both curves and can
  choose. Worth recording in the power-profile discussion, where
  `linux/patches/gm7mg7p-power-profile/` is deciding what to write.
- **The mailbox bytes are duty slots.** Anything that polls `0x0F5D`/`0x0F5E`
  for readiness is reading two entries of a fan curve, and a driver that
  treats a match as an acknowledgement is relying on that. The hazard is
  quantified in `docs/hardware-tests/fan-table-defaults-0f5d.md`.
- **No `0x0F00` entry in `registers.yaml`, deliberately.**
  `ec/tools/check_power_profile.py` names `0x0F00` as the one address
  permitted to sit outside the file ("Only the fan table is allowed to be
  outside the file") and `linux/patches/gm7mg7p-power-profile/profile-map.csv`
  relies on that empty cell while citing this mechanism, so adding one flips
  that gate's rule 1 from "empty is right" to a failure. Doing it properly is
  its own issue against the open power-profile PR, and the byte-identity
  result is the thing to say in it.
