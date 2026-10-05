# The PD `0x260` record block, sampled live: whether the PD image's XDATA is the memory ECMG reads, and what is in the records

**Status: not run.** Nothing in this document has been observed. No capture has
been taken on this machine for this procedure, no register has been read back,
and no result section exists here because there is nothing to put in one. The
pipeline cannot reach the hardware (`CLAUDE.md`, "Cloud agents cannot reach the
hardware"), so this is a procedure for a human at the laptop: numbered steps,
exact commands, and the reading each one is capable of supporting written down
*before* the run rather than after it.

Two separable questions, and the procedure runs both because they cost one
capture each in the same block:

1. **Map separation.** Is the PD image's XDATA the same memory the ECMG window
   reads? `ec/annotations/pd-xdata-overlap.md` §7's first runtime step names it:
   read `0x04A6`/`0x04A7` across a period in which the PD controller is active
   and see whether the reported cycle count is disturbed.
2. **Record contents.** `0x260` is a stride, not a count
   (`ec/annotations/pd-index-geometry.md` §5, which states no record count
   because bounding one needs the index registers' ranges and its §4 resolved
   none). Dumping the records across a renegotiation and diffing them says what
   changes and how many distinct slots are ever touched, which is the nearest
   thing to a record-contents answer this read path can give.

Issue #1151. The static reading this grades against is
`ec/annotations/pd-index-geometry.md`; the overlap question is
`ec/annotations/pd-xdata-overlap.md`, whose §5.1 counts the two images' sites
over `0x0400`-`0x07FF` and §7 asks for exactly this run. The window this
procedure is bounded by was measured on this machine by
`docs/hardware-tests/xdata-06c2-06db-sweep.md` §3.

**The third question this procedure cannot answer, said up front.** "Read what
the index registers hold" is not achievable through a memory window. A memory
read observes *state*; it does not observe a register at the moment a site
runs. `pd-index-geometry.md` §5's "one caller found means one found by this
method" caveat applies to whatever is read back, and no tool in this tree
drives a trace or a debugger. What would settle it is named in §4. It is named
here, before the run, so that a result read as an index-register measurement is
refused rather than published.

## 1. What the code predicts

Re-derivable from the committed image and from the tool that produced it:

```console
$ cd ec/tools
$ python3 pd_index_geometry.py ../firmware/GMxMGxx_11.800 --bases
```

- **The record stride is `0x260`, not `0x60`** (`pd-index-geometry.md` §3.2).
  Every one of the sites where both index terms resolve to an identified
  register resolves them to the *same* register, and `Rn × 0x60 + Rn × 0x200`
  is `Rn × 0x260`. **Not one site names two different registers** — that zero
  is the load-bearing part of §3.2, and `pd_index_geometry.py --self-test`
  holds it to the image.
- **`0x260` is a property of the `0x0400`-`0x04A8` run, not of the whole
  image** (§7.4). No site with a `0x5E`, `0x77`, `0x17`, `0x67` or `0x04`
  stride applies a `0x200 ×` page term, so those families' effective strides
  are their own constants, and `pd_index_geometry.py --self-test` is what
  holds that over the whole image rather than over the run. Every step below
  that places an address at `base + n × 0x260` is therefore a claim about the
  `0x60` and `0x1F` families only, and `pd_index_block_readability.py` places
  no other family at a higher slot for that reason.
- **`0x260` is a stride, not a count, and not a total size** (§5). Nothing here
  predicts how many records there are, and a capture cannot supply that number:
  bounding one needs the index registers' ranges.
- **No index range is bounded by the decode** (§4). The observed literal index
  loads at the four sites are none, and nothing bounds the rest.

## 2. What this machine can read at all, and what it cannot

The host maps the EC through a 64 KiB memory-mapped window. On this machine
that window maps `0x0000`-`0x07FF` and `0x0C00`-`0x0FFF`, and **every byte of
`0x0800`-`0x0BFF` and of `0x1000`-`0xFFFF` reads `0xFF`** whatever the EC holds
(`xdata-06c2-06db-sweep.md` §3, committed at
`evidence/ec-watch/2026-09-24-host-window-page-census.txt`). That is consistent
with the window not mapping those pages; it is not a statement about what the
EC holds there, and it is the reading `docs/findings.md` §4g already takes for
`0x0A40`-`0x0A5F`.

Derived from the committed base list in `ec/annotations/pd-base-strides.csv` and
that window constant, per stride family — a base is *readable* when its first
byte is one a capture can sample, which is inside the window and off the fan
page (§2b says what the second half of that costs):

```console
$ python3 pd_index_block_readability.py --table
```

| stride | bases | readable | not readable |
|---|---:|---:|---:|
| `0x60` | 37 | 37 | 0 |
| `0x5E` | 9 | 0 | 9 |
| `0x17` | 7 | 0 | 7 |
| `0x77` | 4 | 0 | 4 |
| `0x67` | 6 | 6 | 0 |
| `0x1F` | 2 | 2 | 0 |
| `0x04` | 2 | 2 | 0 |

**A run that quietly omits the `0x08xx` arrays reads as a complete result and is
not one.** Every base of the `0x5E`, `0x77` and `0x17` families is inside
`0x0800`-`0x0BFF` and none of them can be sampled through this path at all. Per
`docs/findings.md` §4e the vendor's `ECRW` path goes through the same window, so
a different read path is unlikely to help; **if one is known or found, record it
and say how it was obtained**, and add its rows to the run's own note rather
than to this file.

### 2a. The fan page splits the block in two

`ec_timer_capture.py` refuses `0x0460`-`0x046F` before it opens anything
(issue #94: reading those bytes stalled the fans on a sibling board). **The
fan page sits inside the `0x0400`-`0x04A8` range**, so the range as the issue
writes it is refused by that guard, and the steps below specify the split
instead. `ec/tools/test_pd_index_block_readability.py` holds that split to the
tool's own `check_addrs`, in both directions: the range as written is refused,
and the split is the range less exactly the fan page.

It is also inside a `0x260` record: **23 of the `0x60` family's slot-0 records
span the fan page**, so a record can be cut by it and not only by the window
edge. §2b counts that, and `pd_index_block_readability.py` holds the count to
`check_addrs` address by address, so "readable" means the same thing in the
table, in the grader's per-address note, and in the `--addrs` the steps
actually run.

### 2b. How much of a record a capture can actually read

A record can start inside the window and run out of it, because the window
ends at `0x07FF` and its next page it maps is `0x0C00`. A record can also span
the fan page, which `ec_timer_capture.py` refuses rather than reads (§2a). So
**"inside the window" is not the same question as "readable by this run"**, and
the figure below answers the second one: `bytes of that record a capture can
read` counts only the bytes inside the window *and* off the fan page, because
those are the ones `ec_timer_capture.py` will actually sample, which is what
makes it the length of an `--addrs` argument rather than a count of addresses
that merely exist. `grade_pd_index_block.py` prints that figure beside every
address for the same reason, and a record reported as wholly read is not.

```console
$ python3 pd_index_block_readability.py --slots
```

| stride | slot | bases whose first byte is sampleable | bytes of that record a capture can read, min-max |
|---|---:|---:|---:|
| `0x60` | 0 | 37 | 592-608 |
| `0x60` | 1 | 37 | 248-416 |
| `0x60` | 2 | 0 | -- |
| `0x1F` | 0 | 2 | 608-608 |
| `0x1F` | 1 | 2 | 250-251 |
| `0x1F` | 2 | 0 | -- |

So for the `0x60` family slot 0 **begins** at a readable byte for every base and
leaves between 592 and 608 of its 608 bytes sampleable: the twenty-three lower
figures are records spanning `0x0460`-`0x046F`, and the sixteen bytes that is
worth are exactly the fan page this run cannot read. Slot 1 starts inside the
window at every base and is cut short by the window edge, and **no slot-2 record
starts inside it**.

Two consequences the steps rely on: the record-contents arm can sample two
slots rather than one, and it can only do so over what each slot leaves
readable, which is `0x0400`-`0x065F` less the fan page and then
`0x0660`-`0x07FF`. A record reported as wholly read at slot 0 is one that does
not span the fan page, and the `0x0400` record is not one of them.

## 3. How to run it

All reads go through the physical ECMG window (`0xFE410000`, the `MMRW` path the
vendor's `ECRW` takes) with `ec/tools/ec_timer_capture.py`, which maps
`/dev/mem` read-only and never opens it for writing. It refuses the fan page and
any address outside the host window before it reads anything, so a command that
gets as far as a CSV has already passed both.

Run from `ec/tools`, as root. Substitute the date in each capture name, the way
the existing captures under `evidence/ec-watch/` are named.

**0. Confirm the window on the machine you are at.** Cheap, and it is what
makes the rest of this document's numbers about *this* machine rather than
about the one the census was taken on:

```console
$ sudo python3 ec_timer_capture.py --census > <date>-pd-block-window-census.txt
$ grep -E '^#   0x' <date>-pd-block-window-census.txt
```

If the `# runs:` lines do not say `0x0000-0x07ff holds data` and
`0x0800-0x0bff all 0xFF`, **stop**: the rest of the run's arithmetic is
arithmetic over a window this machine does not have.

**1. Arm A, idle — the requested block, PD controller quiet.** The `0x0400`
`0x04A8` bases of §2, which is where `0x04A6`/`0x04A7` live. This is the
map-separation arm's baseline:

```console
$ sudo python3 ec_timer_capture.py --interval 0.01 --seconds 180 \
      --addrs 0x0400-0x045f,0x0470-0x04a8 \
      --csv <date>-pd-block-base-idle-linux.csv \
      --note "idle: PD controller quiet, nothing plugged"
```

**2. Arm A, active — the same block across a renegotiation, with marks.** Start
it, then perform the actions in order, one at a time, several seconds apart, so
each mark opens a window that is not also another action's: unplug a USB-C PD
source if one is attached; plug one in and let it negotiate; renegotiate (plug
and unplug again, or move the source to a port that renegotiates); leave it
attached. `--auto-mark` stamps the AC changes from sysfs and `--mark-input`
stamps your own key presses, but **the plug and unplug are yours to mark on
stdin** — no sysfs file reflects them:

```console
$ { echo "operator: unplugging the USB-C PD source"; sleep 15; \
     echo "operator: plugging the USB-C PD source in"; sleep 20; \
     echo "operator: renegotiating"; } \
  | sudo python3 ec_timer_capture.py --interval 0.01 --seconds 180 \
      --addrs 0x0400-0x045f,0x0470-0x04a8 \
      --auto-mark --mark --mark-input /dev/input/event7 \
      --csv <date>-pd-block-base-active-linux.csv \
      --note "active: USB-C PD source attached and renegotiated"
```

Replace `/dev/input/event7` with a real evdev node from `cat /proc/bus/input/devices`
if the hotkey device is numbered differently, or drop `--mark-input` if there is
none. The reader does not grab it, so every other reader still gets every event.

**3. Arm B, idle — the records themselves.** Slot 0 of every `0x60` and `0x1F`
record as far as §2b says it can be read, plus slot 1's readable prefix. The
`--addrs` below is that range written out, and it is the split form rather than
`0x0400-0x065F` because the fan page sits inside it. This is ~1000 addresses, so
the interval is wider than arm A's; **a record byte that changes faster than the
interval can step past a sample**, which is why the grader calls its
distinct-value counts floors over the interval rather than counts of values:

```console
$ sudo python3 ec_timer_capture.py --interval 0.05 --seconds 180 \
      --addrs 0x0400-0x045f,0x0470-0x065f,0x0660-0x07ff \
      --csv <date>-pd-block-records-idle-linux.csv \
      --note "idle: record-contents arm, slot 0 as far as the window and fan page allow, slot 1's prefix"
```

**4. Arm B, active — the same records across a same sequence of actions:**

```console
$ { echo "operator: unplugging the USB-C PD source"; sleep 30; \
     echo "operator: plugging the USB-C PD source in"; sleep 30; \
     echo "operator: renegotiating"; } \
  | sudo python3 ec_timer_capture.py --interval 0.05 --seconds 180 \
      --addrs 0x0400-0x045f,0x0470-0x065f,0x0660-0x07ff \
      --auto-mark --mark --mark-input /dev/input/event7 \
      --csv <date>-pd-block-records-active-linux.csv \
      --note "active: record-contents arm across the PD actions"
```

**5. Grade them.** Offline, over any capture; it opens no EC:

```console
$ python3 grade_pd_index_block.py <date>-pd-block-base-active-linux.csv
$ python3 grade_pd_index_block.py <date>-pd-block-base-idle-linux.csv \
      --active <date>-pd-block-base-active-linux.csv
$ python3 grade_pd_index_block.py <date>-pd-block-records-active-linux.csv \
      --mark-relative
```

**The Windows arm is not covered here.** `windows/tools/ec_watch.py` over the
same block with the Control Center started and stopped is a separate run on a
separate machine (issue #1064's `pd-controller-enumeration.md` is a different
run again — a bus and Type-C census, not an aliasing question; do not fold them
together, and do not close #1064 with anything produced here). It is named here
as an arm this procedure does not cover, not as work this procedure defers.

## 4. What this cannot conclude

Written before the run, on purpose. A negative that reads as a positive is the
whole failure mode here, and it is much easier to state the rule in advance
than to unpick it afterwards.

- **The separation question is one-sided, and the grader says so per run.** A
  **quiet** `0x04A6`/`0x04A7` across a renegotiation is *consistent with* the
  two maps being separate and **does not prove it** — a separate map would
  leave the byte undisturbed exactly as a shared one might over this span. It
  rules nothing in and nothing out. A `0x04A6` that **moves** in step with a
  renegotiation mark **does** prove overlap, and `pd-xdata-overlap.md`'s
  independent-map verdict is then wrong. One direction is evidence; the other
  is not, and a table that printed both alike would be claiming the second.
- **A quiet byte anywhere else means "not reached on the paths watched, over
  this span"** — never absent, never unused, never zero. This is the same rule
  `docs/findings.md` keeps for a static scan's zero hits, applied to a live
  capture: the read path watched a set of paths for a span, and a byte that did
  not move is one nothing reached in that time.
- **An address outside the host window was not observed at all.** It reads
  `0xFF` for the whole run, which is indistinguishable from a value that never
  changes; the grader marks those lines rather than grading them, and the
  `0x08xx` families are outside the window for slot 0. **A constant there is a
  fact about the host, not about the EC.**
- **A distinct-value count is a floor.** A byte stepping faster than the sample
  interval is one value in the capture and two on the hardware. The grader
  prints the interval beside the counts for exactly this reason.
- **A difference between the idle and active captures is a difference between
  two states, not an attribution.** It cannot say which state caused it, and a
  byte that changed in *both* captures changed for a reason neither state
  explains.
- **Nothing here reads an index register**, so nothing here bounds a record
  count. `pd-index-geometry.md` §5 states no count for that reason and §4
  bounds no index range. **This procedure cannot answer "what do the index
  registers hold", and no result from it should be written up as though it
  did.** What would settle it: a trace of the PD controller's XDATA as a site
  runs, or a debugger stopped at the site — neither of which any tool in this
  tree drives, which is why this sentence is here rather than in a results
  section.
- **No `registers.yaml` `status:` moves on the strength of this run until it
  has run**, and none could move on a procedure that has not.

## 5. Where the output goes

Name the files the way the existing captures are named, under `evidence/ec-watch/`.

```
evidence/ec-watch/<date>-pd-block-window-census.txt
evidence/ec-watch/<date>-pd-block-base-idle-linux.csv
evidence/ec-watch/<date>-pd-block-base-active-linux.csv
evidence/ec-watch/<date>-pd-block-records-idle-linux.csv
evidence/ec-watch/<date>-pd-block-records-active-linux.csv
```

Nothing here has been produced. When the run happens, the report belongs in a
new `docs/findings/` write-up and the capture CSVs beside the existing ones
under `evidence/ec-watch/`; `docs/hardware-tests/` is where the procedure
lives, not what it found.