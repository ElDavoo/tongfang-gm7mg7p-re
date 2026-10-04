# Which side of the oracle a capture lands on is asked of the file, and the cTGP state table gets a reader (issue #1397)

`check_capture_claims.py` answered "is this a capture I can read a claim in"
three times, and all three times by **file extension**. `has_addr_column()` —
which #990 put *into this same file*, to answer that question of the file
instead — sat beside them unused by the two that mattered. The one that guarded
`registers.yaml` was the extension.

The cost is small and it is worth stating before anything else, because a reader
who finds the number first will over-read the rest: **routing by the column
changes no verdict on the committed corpus, and it costs no check either.**
Every `.csv` under `evidence/ec-watch/` carries an `addr` header and every
`.txt` does not, so the predicate and the extension agree on every committed
file. What this fixes is a hole that is *latent*, and the one thing that was
never latent: `registers.yaml`'s `CTGP_DB_CTRL / OFFSET` entry — a
`confirmed-working` status in the repository's source of truth, resting on
issue #8's live cTGP result — had **no reader at all**, because the capture
behind it is a table whose addresses are its *columns*. That is what
`read_ctgp_state_table.py` is for, and it is now held to the capture.

**Nothing here is a live test, and no capture is edited to make a tool green.**
`evidence/ec-watch/` is untouched; both tools read the committed bytes, which is
the same class of read as reading the prose beside them. The ctgp file's
*content* is a human's live result from 2026-09-23, already committed and
already cited; holding prose to it neither adds nor re-derives a hardware
observation.

## The equality is the finding

The first thing to check, and the reason this branch says what it says: **the
predicate and the extension agree on every committed file.** Every `.csv` under
`evidence/ec-watch/` carries an `addr` header and every `.txt` does not. So
routing by the column moves no verdict, and the issue's own census — measured on
an earlier tree — was not carried over, because a count of units in the prose is
not a property of the checker and any document here that quotes one is stale at
the next merge.

What a run shows, and the command is the record rather than a figure to keep:

```
$ python3 ec/tools/check_capture_claims.py --check --verbose 2>&1 >/dev/null \
      | grep -c "no addr column"
```

The skip lines are the same before and after the routing, and the same set of
units. **That equality is the whole of what this change costs and buys on the
committed corpus**: the routing is a de-duplication, not a behaviour change, and
the hole it closes is latent. Which is why the suite holds membership and the
skip's wording, and asserts no figure — a count of skips is a joint property of
the prose and the rules, and moves whenever a document is added.

## The price of a reader for each columnless capture

The other question the issue asked before writing anything: **what would a
reader for each `.txt` buy?** Priced by running `check()`'s own address and
count extraction over every unit that names each capture, so the price is
measured with the machinery under discussion rather than by a second reading of
the prose. Range bounds are excluded, because `0x0783-0x0787` names a window
rather than five bytes that moved in it.

The price is a property of the **capture** — what a reader for it could ever
answer — rather than of how many sentences happen to cite it today, so it is
stated that way:

| capture | shape | what a reader could check |
|---|---|---|
| `evidence/ec-watch/2026-09-23-ctgp-live.txt` | four address **columns** × five state rows | the addresses it names, as columns |
| `evidence/ec-watch/2026-09-23-0751-isolation.txt` | a per-change watch log with a machine-written `SUMMARY:` block | one denial, which the log answers |
| `evidence/ec-watch/2026-09-23-power-mode-cycle-0f00-final.txt` | an `ecrw.py dump`; the address is a line prefix, 16 bytes per line | nothing — **the prose naming it says "the capture saw all of them land" and names no address in the same unit** |
| `evidence/ec-watch/2026-09-23-power-mode-snapshot-dc.txt` | read-only reads, `0x049F = 0x0A` repeated | nothing, for the same reason |
| `evidence/ec-watch/2026-09-24-host-window-page-census.txt` | one line per **page** (`0x0800 0/256`), not per address | nothing, for the same reason |

**Two of these name no address in the unit that names them** — the addresses are
in the sentence before, and the sentence pointing at the file is the claim. A
reader for either would find nothing to check even once written, so neither is
worth its own issue. That is the plan's argument, and it survives re-measurement
unchanged: it is a property of the prose and would need re-deriving only if
somebody rewrote those sentences to name an address beside the file.

`2026-09-23-0751-isolation.txt` is the one that is not zero and not cTGP. It is
a per-change watch log, so the addresses are in its text, but its rows are
per-block rather than per-change and `docs/findings/power-profile-gm7mg7p.md`'s
unit names `0x0751`, `0x07C5` and `0x07C6` — of which the capture's own text
says only `0x0751` moved. **A reader for it would find one claim to check, and
it is a denial the log answers.** That is a real finding and it is not this
issue's; it is priced here so the price is on the record rather than
rediscovered.

Two `ec/tools/testdata/*.txt` fixtures also come up in the same scan and are
**not captures**: one is headed `# CONSTRUCTED INPUT, NOT A CAPTURE`, and both
are inputs to a grader. They are named here so a reader pricing captures does
not go looking for them.

**The cTGP table is the only one worth writing, and that is the issue's own
"starting with one".** It is the capture a `confirmed-working` status in the
source of truth rests on, and it is the only columnless capture where the
address and the capture's own structure are the same thing.

## The trap the routing has to avoid

`read_capture()` pointed at a `.txt` **does not raise.** It returns a silent
zero — a `DictReader` over prose has no `addr` fieldname, so every row yields
`None` and `per` stays empty:

```
$ python3 -c "
import os, sys; sys.path.insert(0, 'ec/tools')
from check_capture_claims import read_capture, WATCH, REPO
for n in sorted(os.listdir(os.path.join(REPO, WATCH))):
    if n.endswith('.txt'):
        per, rows, distinct = read_capture(os.path.join(REPO, WATCH, n))
        print(f'{n}: rows={rows} distinct={distinct} per={per}')"
2026-09-23-0751-isolation.txt: rows=16 distinct=0 per={}
2026-09-23-ctgp-live.txt: rows=6 distinct=0 per={}
2026-09-23-power-mode-cycle-0f00-final.txt: rows=5 distinct=0 per={}
2026-09-23-power-mode-snapshot-dc.txt: rows=40 distinct=0 per={}
2026-09-24-host-window-page-census.txt: rows=255 distinct=0 per={}
```

So widening `main()`'s index to "read every named capture" — the obvious way to
give the cTGP table an oracle entry — would put each of those files in as an
**empty oracle**, and every claim naming one would be reported as a
**disagreement that does not exist**: an empty `per` says every address is
absent, which is exactly what a presence claim says it must not be. Routing a
*capture* to the reader that can read it is the fix; routing a *claim* into a
reader that cannot is the bug. That is why the index is built from files that
have a column, and why the cTGP table comes in through its own reader.

## What the reader answers, and what it refuses

`read_ctgp_state_table.py` reads the header's address columns and answers one
question: **is this address a column of this table.**

| claim | answer | why |
|---|---|---|
| a unit attributes a movement to `0x0743` | **held** — `0x0743` is a column | the affirmative rule, and the one worth automating |
| a unit names `0x07C4` | **not read by this method** | the columns are the capture's *watch set*; not-watched is not did-not-move |
| a unit states a count | **not read by this method** | a row is a *state*, not a change; the table has no per-address count |

The second row is the one that had to be right, and getting it wrong was a real
false red rather than a hypothetical: `docs/hardware-tests/ctgp-dben-07c4-bit3.md`
says the capture "watched the dGPU's *enforced power limit*, not `0x07C4`" —
a **denial**, and correct prose. A reader that reported every address as an
attribution would have flagged that sentence as a disagreement over a capture
that agrees with it.

**Polarity is deliberately not in the reader**, and the reason is worth stating
rather than leaving to a reader of the code. The obvious second rule is to
invert the presence check for a denial, the way `check_capture_claims.py` does.
It would change **no verdict** — an address with no column is unread under
either polarity — and the walk it needs fires on none of the units in the
corpus. So it is left out rather than imported for the one sentence it would
*describe* wrongly, and the refusal's own wording is written to cover both: it
says the byte's movement is unread, not that the capture denies it.

The third row is refused rather than answered `0`, and the distinction is the
whole of the calibration rule here: **"there is no count in this table" and "the
count is zero" are different sentences, and only the first is true.**
`check_capture_claims.py` applies `COUNT` to everything in its index, which is
one more reason this file must not be in it.

## What the run prints

```
$ python3 ec/tools/read_ctgp_state_table.py --check
```

Three things, and the figures are **not** quoted here on purpose: this write-up
is itself prose under `ROOTS` that names the capture, so committing it moves
the run's own counts — a transcript pasted above would be wrong the moment the
file lands, and wrong in a way no later edit would catch.

- **One refusal line per claim this shape cannot answer**, on stderr, naming
  the file, the line and the address — `docs/hardware-tests/ctgp-dben-07c4-bit3.md`
  is the standing example, and it is a *refusal* because the table has no
  `0x07C4` column, not because the sentence is wrong.
- **A closing line saying how many were not read and that none of them is a
  disagreement**, so a reader who scrolls past the per-claim lines still sees
  that nothing failed.
- **A summary line naming the held claims, and the header they were read from.**
  The header is printed rather than only the verdict, so a reader can check the
  columns against the file without opening it.

The held claims are `registers.yaml`'s `CTGP_DB_CTRL / OFFSET` note and
`docs/findings/dmi-descriptor-evidence.md`'s unit. The held figure is printed
for the reason the checker's own figures are: **a run that read nothing and a
run that held everything both exit 0**, and the figure is the only thing that
tells them apart.

`check_capture_claims.py` is unchanged on the same tree — the same claims
checked against the same captures, every one agreeing — which is the equality
above restated in the place a reader looks for it.

## What this does not do

- **It does not say the routing fixed anything.** It says the hole was latent
  and is now closed. On the committed corpus the two readings agree, and a
  future `.csv` without an `addr` header is what separates them.
- **It does not give the other four `.txt` captures a reader.** They are priced
  above, stay outside the oracle, and are reported per unit in `--verbose` as
  *not read by this method*. Where there is no reader, the write-up says so
  rather than reporting a silent zero.
- **It does not move a `status:`.** `CTGP_DB_CTRL / OFFSET` was already
  `confirmed-working`; this holds the prose to the capture that already
  substantiates it. **No register was read back**, and nothing here is
  behavioural evidence about the firmware.
- **It does not touch the bare-date / `addr`-column deferral.** The docstring's
  last bullet points that work at `check_testdata_row_claims.py`; it is still
  there and is not reopened.
- **It does not touch the `denial` skip.** That is the other named blind side
  of the checker's docstring, and #1265 covers it on the sibling tool's
  population.

## What the routing costs, and why it is not optimised away

`has_addr_column()` opens the file, so routing by it rather than by the
extension reads a header **once per capture named per unit that names it** —
`captures_in()` is called for every unit in `ROOTS`, so a capture a dozen
documents cite is opened a dozen times. The run is a little slower for it, and
the measurement is with

```
$ time python3 ec/tools/check_capture_claims.py --check
```

**A memo would make that near-free, and is declined for the reason
[`testdata-row-claims-no-addr-column.md`](testdata-row-claims-no-addr-column.md)
gives for the same decision in the sibling tool**: a second answer to "does this
file have an `addr` column", held in a dict, is the same class of drift as the
two extension readings this issue exists to remove — and it would drift
*silently*, since a cache populated from a file that changed mid-run is not a
thing anything reports. Half a second on a walk this size is a cheap price for
a predicate with one definition, and the corpus it walks is already read whole
by the textual readers beside it.

## One named, deliberate staleness

`docs/ci/agent-gates-capture-claims.patch` already carries
`check_capture_claims.py`, so **this change needs no gate patch at all**. The
patch is left byte-identical, and the reason is the one
[`testdata-row-claims-no-addr-column.md`](testdata-row-claims-no-addr-column.md)
gives for its own: it is a prepared change a human lands later, the CLI is
unchanged, nothing executes it, and editing a file nothing runs is one more
conflict surface for no gain. **Named here so the human landing that gate knows
a new tool arrived ungated** — `read_ctgp_state_table.py` is ungated for the
same reason `check_capture_dates.py` and `check_capture_names.py` are: the
push token has no `workflow` scope, so a branch touching `.github/` fails at the
end of the pull request. `tools/run-tests.sh` is what runs both tools.