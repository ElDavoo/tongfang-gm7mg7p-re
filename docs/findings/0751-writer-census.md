# The `0x0751` writer census — "at least three paths" becomes ten sites and thirteen stores, and the number is not closed

(2026-10-01, issue #196. Static reading of `ec/firmware/GMxMGxx_11.800` and
three committed tables, plus the mode decode around each writer read in
`r2 -a 8051`. No capture opened, no EC, no hardware, no Windows.)

Issue #196 asked for every write site for `0x0751`, blind stores separated from
read-modify-writes, and the condition each store fires under. The
`MANUAL_FAN_CTRL` note in `ec/annotations/registers.yaml` and §9 of
`ec/annotations/manual-fan-ctrl-0751.md` both say **"at least three paths"**, and
nothing in the tree had counted them. This is that count.

**Ten writer sites, thirteen store instructions**, committed as
[`ec/annotations/manual-fan-ctrl-0751-writers.csv`](../../ec/annotations/manual-fan-ctrl-0751-writers.csv)
beside the site table, derived by
[`ec/tools/census_xdata_writers.py`](../../ec/tools/census_xdata_writers.py) on
every run. One of the thirteen is a blind store and twelve are
read-modify-writes. The count is **not closed**, for a reason with a figure
attached — see §4.

**"At least three" is corrected in place, not replaced.** §9's third path — the
`0x8942` arm clearing FAN BOOST at `0x8990` when both sensors are under 70 °C —
is one of the ten, and it is the only one of the ten whose gate is a
temperature. The other nine are the two boot-time defaults and seven stores
reached from a mode decode or a named flag bit. Both original sentences stay
where they were, each with this file named beside it.

## 1. What the count is a count *of*, and what it is not

`ec/annotations/manual-fan-ctrl-0751-sites.csv` holds 29 rows, one per
`MOV DPTR,#0x0751`. Eight of their `access` cells read `write` and nineteen read
only. The ten writer sites are those eight plus two more: `0xABE8` and `0xC741`
are two of the ten, and neither of them carries a direction at all in the
committed site table — each one's own eight-instruction window is
`mov dptr,#0x0751 ; jnb acc.1,+0x15` and stops there, with no `movx` in it, so
its cell is `no movx found in the decoded window`. The stores sit on the *other*
side of that branch, and
[`walk_flow_follow.py`](../../ec/tools/walk_flow_follow.py) is what reaches them.
That is why the count is ten and not eight, and it is a weaker claim for those
two rows than for the other eight: resolved past a branch is not resolved where
it sits.

The `access` cell counts reads and writes. It does not say what a write is, and
that is the whole of the gap this fills. The four shape questions §2 and §3 ask
were all unanswerable from the site table:

- is the stored value read from this byte, or is it something else entirely?
- if it is read, which bits does the store touch?
- how many stores does one site carry?
- and what has to be true for the site to run at all?

## 2. One blind store, twelve read-modify-writes

`access_shape` is derived, not read off a listing: a `movx @dptr,a` with a
`movx a,@dptr` still pending on the same DPTR is a `read-modify-write`, and one
without is a `blind-store`. Within a decoded window DPTR cannot move —
`walk_why()` returns at `is_dptr_rebuild()` and names the reload as the
terminator — so an intervening `movx` of either direction is on this same byte.

| | sites | stores |
|---|---|---|
| `read-modify-write` | 9 | 12 |
| `blind-store` | 1 | 1 |

**The one blind store is `0xA815`**, in the boot-time default routine §4 already
documents. The listing there is worth repeating for what the window does *not*
contain: the accumulator is zeroed by `clr a` at `0xA811`, which is in the
*previous* window, before the site's own `mov dptr,#0x0751`. So the site
writes `0x00` over the whole byte without having read it, and a bit a host set
in `0x0751` does not survive it. It is the only one of the thirteen that is
not a bit edit at all — a whole-byte write rather than a masked one.

**Ten of the other twelve are single-bit edits; two clear USER and TURBO
together.** `mask` is what the store did to the accumulator between the load
and the store, rendered:

| mask | stores | what it does to `0x0751` |
|---|---|---|
| `anl a,#0xbf` | 1 | clear bit 6, FAN BOOST |
| `xrl a,#0x40` | 3 | **toggle** bit 6 |
| `anl a,#0xef` | 1 | clear bit 4, TURBO |
| `orl a,#0x80` | 1 | set bit 7, USER |
| `anl a,#0x7f` | 2 | clear bit 7, USER |
| `orl a,#0x10` | 2 | set bit 4, TURBO |
| `anl a,#0x6f` | 2 | clear bits 7 and 4, USER and TURBO |

Two things a driver author should take from that table rather than from the
count. `xrl a,#0x40` is a **toggle**, not a set and not a clear: three sites
invert FAN BOOST rather than driving it to a value, so a read-modify-write
guarantee does not extend to "the bit ends up where the EC wants it" — it
extends to "the bit the EC did not name survives". And `anl a,#0x6f` clears
USER and TURBO together, so a host that has set either of those two to express
a mode loses it to two of the ten sites.

**`0xA818` carries two stores, one of three sites that do.** Its window
ends on `max_insns (8) exhausted` rather than on a control-flow opcode, so it
is the one row whose `status` is `window-truncated` and the one row where a
larger window might hold more — `walk_budget_census.py` is where that mechanism
is committed. A truncated row is not a wrong row; it is a row that says its own
window was cut. The row count is the site's, not the instruction count's, and
`ec-07c4-07d5-sites.md` §2 is where that distinction is already drawn.

## 3. The condition each store fires under

`condition` is hand-filled off the listing, from a closed four-value vocabulary,
and every row carries a `condition_evidence` cell naming the branch it was read
from. `--check` carries the two hand-filled columns through rather than
regenerating them — the arrangement `xdata-0860-census-sites.csv` and
`check_site_census.py` already use — and holds them by two rules instead: the
vocabulary is closed, and a condition with no evidence cell is refused.

| condition | sites | what the evidence cells actually name |
|---|---|---|
| `boot-default` | 2 | `BIOS_OEM_2` (`0x0782`) bit 4, `DEFAULT_MODE`, behind the bit-5 one-shot |
| `temperature-gate` | 1 | CPU and GPU under `0x46` (70 °C) |
| `mode-decode` | 7 | two on `BIOS_INFO_3` (`0x049F`) bit 1, "Turbo mode supported"; two on the mode getter's return with bit 7 flipped, reached by a `jnz` that the `cjne` beside the store does not gate; one on `TRIGGER` (`0x0767`) bit 2 alone; two on an `XDATA_0440` test combined with another flag |
| `host-write-through` | **0** | see below |

**`mode-decode` is a category, not a claim that seven sites all decode the power
mode.** It is the bucket for a store whose gate turns on which mode is selected,
and the evidence column is what says which kind: of the seven, two gate on a
bit `registers.yaml` names as *Turbo mode supported*, two on the mode getter
`0xBB40`/`0xCA4C` — which reads `0x0751` itself and returns it masked with
`0x90`, so its input is this byte — one on a `TRIGGER` bit whose
relationship to the power mode is not established, and two on `XDATA_0440`
being non-zero combined with a second flag. A reader who wants "the sites that
decode the mode" is looking for the evidence cells, not the bucket.

**`host-write-through` is empty, and that is the answer issues #102 and #104
need.** The host writes `0x0751` over `ECRR`; that path is not a
`MOV DPTR,#0x0751` site, so no instruction for it exists to be found by this
method. The bucket is in the vocabulary, empty, and reported as empty on every
run with that reason attached — because a bucket quietly missing and a bucket
nobody looked for are the same file. **This is "not found by this method", never
"the host does not write it",** and the same discipline
`registers.yaml`'s own header caveat states.

What follows for a `platform_profile` implementation is narrow and worth
stating because the scoping question was the point of the issue: **a host write
to `0x0751` is reverted by some of these stores.** `0xAC06` and `0xC75F` clear
USER and TURBO, so a bit a host set in either of those two does not survive
them; `0x8990` clears bit 6 whenever both sensors are under 70 °C, without
ever testing bit 6. Every store found here is gated on a temperature, a BIOS
setup bit, a mode decode, or a named flag bit, and for **two of the ten the
mode decode reads this byte**. The getter at `0xBB40` and at `0xCA4C` returns
`0x0751 & 0x90`, and the `jnz` at `0xABE2` and at `0xC73B` is on that return
with bit 7 flipped — so the store at `0xAC06` and at `0xC75F` clears USER and
TURBO *because* the masked byte came back the way it did, and a host write
that changes what that mask reads is what steers execution into the store
that clears those two bits. That is a comparison against the byte's own
previous value rather than a reversion of it, and for #102 and #104 it is the
more useful half of the answer, not a weaker one. The other eight are gated
on a temperature, a BIOS setup bit or a named flag bit. So the reads at the
other nineteen sites are consumers rather than a write-back loop, as far as
this method can see. That is
consistent with the 2026-09-23 live capture already recorded in the
`MANUAL_FAN_CTRL` note, where a silent write persisted; this adds the static
counterpart. What it does **not** establish is how often any of those stores
runs, so whether a host write persists is a behavioural question and belongs
to the hardware run that is issue #167.

## 4. Why the number is not closed, with a figure

`walk_branch_arms.descend()` charges a `movx` to no address once DPTR has been
rebuilt at run time, and reports it in the `unattributed` column. Across the
`0x0751` arm table that is **100 stores over its 171 rows**, and any of them
could be a `0x0751` writer that no site scan can name. The figure is read out
of the committed arms table on every run and held by `--self-test`, so the gap
is a number that moves rather than a caveat that gets copied forward.

That blind spot is issue #34, and it stays open. Three further limits are the
tree's own and are not new:

- **Indirect access.** A byte reached through a computed DPTR, a
  register-indirect `movx @Ri` or a table lookup has no `MOV DPTR,#0x0751` site,
  so it cannot appear in this table at all. This is the same shape
  `check_site_census.py` records as "the sweep's blind spot".
- **A write the classification can see and the scan cannot place.** A site
  whose window says `write` and which holds no `movx @dptr,a` would be
  `unresolved`, with the reason in the row. No `0x0751` site is one today; the
  status is in the vocabulary and the suite builds the case, because a status
  nothing can construct is a status nothing can check.
- **A window cut by the budget.** One row of ten, `0xA818`, as §2 says.

So the honest form of the claim is: **ten writer sites and thirteen stores, as
found by a window scan over `MOV DPTR,#0x0751` plus one branch-followed segment
per unresolved site, over one firmware image.** A reader who needs a closed
count needs issue #34 closed first.

## 5. What did not move

**The status stays `present-untested`.** Per `CLAUDE.md`, a write being stored
is not evidence the EC acts on it. §7 of
`docs/hardware-tests/manual-fan-ctrl-0751-isolation.md` keys
`confirmed-working` and `confirmed-inert` on a behavioural observation, and this
change adds none. `static_refs`, `static_refs_main_ec` and
`static_refs_pd_image` are unchanged too: the census reads the same 29 sites and
adds none.

**The "no value reaches a PL or a fan table" negative survives untouched.**
Every store found is a bit edit to or a whole-byte write of `0x0751` itself; no
store reads a PL block, a fan-table byte, or any other address in the same
window. §5 of `manual-fan-ctrl-0751.md` and §9.3's negative are not disturbed by
this and are not re-argued here.

**§9.5's "what this section does not say" is left as written.** The arm walk was
never a writer census and still is not; this is a site scan with a store
classifier, and the two miss different things.

**No ranking of the conditions.** Nothing static supports a claim about which
gate is reached oftenest, or whether any of them is ever true at run time.

## 6. Reproducing it

```console
$ python3 ec/tools/census_xdata_writers.py --self-test ec/firmware/GMxMGxx_11.800
$ python3 ec/tools/census_xdata_writers.py ec/firmware/GMxMGxx_11.800 0x0751
$ python3 ec/tools/census_xdata_writers.py --check
$ python3 ec/tools/test_census_xdata_writers.py
```

`--self-test` is the oracle: ten byte fixtures transcribed by hand from
`r2 -a 8051` against a `make_bank_image.py` bank image, so the store scan is
graded by a second disassembler rather than by its own decoder. `--check` takes
the address from the committed table rather than from the command line, refuses
an address given alongside it, and **fails on a missing file rather than
creating it** — a `--check` that writes the table it is checking has stopped
checking it.

The gate call is prepared rather than landed, for the reason every file in
`docs/ci/` gives: `.github/scripts/agent-gates.sh` is copied from the
agent-pipeline template and the pipeline's push token has no `workflow` scope.
It is [`docs/ci/agent-gates-0751-writer-census.patch`](../../docs/ci/agent-gates-0751-writer-census.patch),
to be applied with `git apply`. **Until a human lands it, nothing runs
`--check` or `--self-test` per commit, and a PR that breaks one of them merges
green.**

## 7. The questions this opens

- **`0x075B`/`0x075C` want the same census** (issue #123 owns the bytes, not the
  count). The tool is address-parameterised for exactly this and the two would
  be the next table; a fan duty byte with a read-modify-write at every site is
  the interesting answer.
- **The PL bytes** — the same question, and the one §5's negative is about.
- **The `TRIGGER` bit and `0x0440`** gate three of the ten stores and neither
  register's relationship to the power mode is established. `XDATA_0440` has no
  name and 43 references.
- **The mode getter at `0xBB40` and `0xCA4C`** is called by two of the ten. It
  reads `0x0751` and returns it masked with `0x90`, the two bits that separate
  the three vendor modes, so its input is this byte rather than another
  register. §3 of `manual-fan-ctrl-0751.md` covers the mode setters from the
  other side.
- **Issue #34.** The 100 unattributed stores are the reason the count is open.
