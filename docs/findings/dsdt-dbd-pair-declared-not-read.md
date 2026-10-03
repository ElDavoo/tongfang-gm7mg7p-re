# The DSDT declares `DBD1`/`DBD2` and writes them, and reads them nowhere (issue #228)

`docs/findings.md` §3d records a divergence between the DSDT and the PD
firmware over `0x07D0`/`0x07D1`: the field list "declares `DBD1` and `DBD2` as
two independent 8-bit fields and leaves `0x07D2` unnamed, while the PD
firmware's 16-bit quantities straddle that field boundary in both directions."
The first half of that was never measured. This measures it, and what the
measurement supports is narrower than the sentence reads.

**The short version: the DSDT *declares* the pair as two scalars and *writes*
them, and never reads either one.** So "two independent 8-bit fields" is a
statement about a field list, not about a value the ASL ever loads, and no AML
object anywhere holds the two bytes as one quantity. The divergence §3d wanted
to record is real, but it is not between two *readings* of the same bytes — the
DSDT has only one direction, and it is out.

"Never reads" needs a stated reason, because the obvious one is false. The
file *does* contain a reader of these bytes — `ECRR`, which reaches them at a
computed base with no field name in the path at all. What it does not contain
is a **call** to it. See [The three names, each accounted for](#the-three-names-each-accounted-for).

The load-bearing correction is to the collision question, which §8 of
`ec/annotations/ec-0x07d1-sites.md` was leaving unassigned. It cannot arise
*between the DSDT and the PD image*, because it was posed as a conflict between
two readings and the DSDT has no reading. What survives is a disagreement
about **meaning**: the DSDT stores two independent bytes and the PD firmware
slides and loads them as halves of a word. A disagreement about meaning turns
into a fault only if something reads those bytes the other way too — and the
only candidate is the **EC** firmware, which owns the XDATA the DSDT writes.
So the question is whether *it* reads `0x07D0`/`0x07D1` as a word, which is
an EC-side question under #34's indirect-access blind spot, with the live half
belonging to the GPU-door run and #278.

Nothing here was read on hardware. No EC image was opened, no register read
back, no `_Qxx` fired. Every number is a static count over two committed files,
and no zero below is ever a verdict — see [What this does not
establish](#what-this-does-not-establish).

## The three names, each accounted for

```console
$ grep -c "DBD1" evidence/acpi/dsdt.dsl && grep -n "DBD1" evidence/acpi/dsdt.dsl
2
50687:                    ^^PCI0.LPCB.EC0.DBD1 = Local0
52249:                DBD1,   8,
$ grep -c "DBD2" evidence/acpi/dsdt.dsl && grep -n "DBD2" evidence/acpi/dsdt.dsl
2
50688:                    ^^PCI0.LPCB.EC0.DBD2 = Local1
52250:                DBD2,   8,
$ grep -c "ECMG" evidence/acpi/dsdt.dsl && grep -n "ECMG" evidence/acpi/dsdt.dsl
2
52193:            OperationRegion (ECMG, SystemMemory, 0xFE410000, 0x00010000)
52194:            Field (ECMG, AnyAcc, NoLock, Preserve)
```

(line numbers at `3246c60a`). `DBD1` and `DBD2` are each **one store and one
declaration**; `ECMG` is two declarations — the region and its field list — and
is used nowhere else.

The writer is the `T1WR` `Arg0 == 0x1173` arm, `dsdt.dsl:50680`-`:50692`, and
it is a pure writer:

```console
$ sed -n '50680,50692p' evidence/acpi/dsdt.dsl
                ElseIf ((Arg0 == 0x1173))
                {
                    ^^NPCF.DBAC = Zero
                    Local0 = Zero
                    Local1 = Zero
                    Local0 = (Arg1 * 0x08)
                    Local1 = (Arg2 * 0x08)
                    ^^PCI0.LPCB.EC0.DBD1 = Local0
                    ^^PCI0.LPCB.EC0.DBD2 = Local1
                    ^^NPCF.AMAT = Local0
                    ^^NPCF.AMIT = Local1
                    Notify (NPCF, 0xC0) // Hardware-Specific
                }
```

`AMAT` and `AMIT` are two more independent scalars off the same two locals,
each `Arg * 8` — not a concatenation of the first two into a wider value. There
is no load, no compare, no test of either field anywhere in the file.

**Those two names are not the only route AML has to those bytes**, so the two
hits do not by themselves prove there is no reader. That is worth checking
rather than assuming, and checking it is what turned up a **reader that an
earlier draft of this write-up denied existed** — it never reached `main`, so
there is nothing to retract in place here, only a premise to state correctly
the first time. `ECRR` and `ECRW` at `dsdt.dsl`
`:50497` and `:50504` are `\_SB.INOU` methods that compute
`Local0 = (0xFE410000 + Arg0)` — the base `ECMG` itself declares — and read or
write that byte through the `OperationRegion (MMNM, SystemMemory, Arg0, 0x04)`
that `MMRW` builds at `:50423`:

```console
$ sed -n '50497,50508p' evidence/acpi/dsdt.dsl
            Method (ECRR, 1, NotSerialized)
            {
                Local0 = (0xFE410000 + Arg0)
                Local1 = MMRW (Local0, Zero, Zero, Zero)
                Return (Local1)
            }

            Method (ECRW, 2, NotSerialized)
            {
                Local0 = (0xFE410000 + Arg0)
                MMRW (Local0, One, Zero, Arg1)
            }
```

So `ECRR (0x07D0)` reads the `DBD1` byte, and nothing in the expression is a
field name. **The premise "the declared names are the only route AML has to
`0x07D0`-`0x07D2`" is false as written**, and what it was standing in for
still needs saying on a different basis.

The basis it was standing in for holds. `ECRR` is a *reader with no caller*:

```console
$ grep -n "ECRR" evidence/acpi/dsdt.dsl
50497:            Method (ECRR, 1, NotSerialized)
$ grep -n "ECRW" evidence/acpi/dsdt.dsl
4437:                    CreateBitField (BUF0, 0x0C48, ECRW)
4438:                    ECRW = Zero
50504:            Method (ECRW, 2, NotSerialized)
$ grep -nE "\bECR[RW]\s*\(" evidence/acpi/dsdt.dsl; echo "(no match: nothing invokes either)"
(no match: nothing invokes either)
```

`ECRR`'s single occurrence is its own declaration. `ECRW`'s three are *not*
three callers — `:4437`-`:4438` are an unrelated `CreateBitField` over `BUF0`
in another scope that happens to share the name — which is why the check
counts invocations, the name followed by `(`, rather than mentions. A mention
count would refuse a correct file.

So the corrected claim is two halves and both are needed, because only the
first is a reason to doubt the second:

- `DBD1`/`DBD2` are the only route **through the `ECMG` field list**, and no
  `IndexField` or `CreateField` is declared over `ECMG` — the file's only
  `IndexField` sites are `:50592` and `:50611` (`IND0`/`DAT0` and `IND1`/`DAT1`)
  and its six `CreateField` sites are `TBF3` at `:20516`, two `GLVL` at `:41806`
  and `:41997`, and `RWFG`/`REOF`/`WRBF` at `:50768`-`:50770`, none over `ECMG`.
- The file's **other** route is computed-base, and none of the three
  computed-base methods is ever invoked: `ECRR`/`ECRW` above, and `SMRW` at
  `:50764`, which builds its three `CreateField`s over a base handed in as
  `Arg0` rather than one it hardcodes — so nothing in the file ties `SMRW` to
  this window, and nothing calls it either.

**No AML code loads `0x07D0`/`0x07D1`.** That survives, on the second reason
rather than the first, and `ec/tools/check_dsdt_ecmg_pair.py --check` holds it:

```console
$ python3 ec/tools/check_dsdt_ecmg_pair.py --check --print
the file's computed-base methods, and whether anything calls them:
  ECRR  0 call(s); declared at dsdt.dsl:50497
  ECRW  0 call(s); declared at dsdt.dsl:50504
  SMRW  0 call(s); declared at dsdt.dsl:50764
```

A caller appearing for any of the three turns the check red while the two-hit
name census stays green — which is the whole point, because a reader reached
through a computed base leaves no trace in the name counts at all.

One of the eight names `ecmg-asl-references.md` already listed as "written by
a `T1WR` arm and read nowhere" — `DBD1` at `:50687` and `DBD2` at `:50688`.
The measurement was in the tree before this issue; §3d and §6 simply never
cited it, and neither had been derived from the file itself.

## "Two independent 8-bit fields", read as disjoint bit ranges

Independence in ASL is not a matter of how the list is written: an element list
assigns bit ranges sequentially, so two elements under one `Offset` cannot
overlap however the list is edited. What *can* be measured is the anchor and
the width each name gets, and whether the second starts where the first ends:

```console
$ python3 ec/tools/check_dsdt_ecmg_pair.py --check --print
DBD1  2 hit(s): 1 declaration (1), 1 store (1)
DBD2  2 hit(s): 1 declaration (1), 1 store (1)
ECMG  2 hit(s): 2 declaration (2)
declared side by side under Offset (0x7D0): DBD1 bits 0-7, DBD2 bits 8-15 -- disjoint ranges, so two scalars
```

Both are 8 bits under `Offset (0x7D0)`, and `DBD2` begins at bit 8 — where
`DBD1` ends. So the pair really is two disjoint byte fields, which is the half
of the §3d sentence worth keeping. What is *not* established is any reading of
them as a value, because the ASL never reads them.

## The "unnamed `0x07D2`" clause is a fact about the list, not about that byte

`ECMG` is a 64 KiB `SystemMemory` region (`dsdt.dsl:52193`, `0xFE410000`,
length `0x00010000`), and its `Field` list at `:52194` is where the clause has
to be read:

```console
$ python3 ec/tools/check_dsdt_ecmg_pair.py --check --print
ECMG field list (dsdt.dsl:52194-52327, from dsdt.dsl:52193):
  28 anchors, 767 bits = 95 whole bytes and 7 spare of 65536
  751 named bits plus 16 unnamed-but-allocated; 23 gaps between consecutive anchors more than one byte apart
  0x07D3 declares 7 of its 8 bits
  2606 bytes between the first anchor (0x043E) and the last (0x0EA0) that no element allocates; longest such stretch 0x07D8-0x0E0C, 1589 bytes
  reconciles with dsdt-ecmg-fields.csv: 98 rows, 751 bits + 16 unnamed
```

`0x07D2` undeclared is the norm, not a hole cut around it. The list jumps
from `Offset (0x7C6)` straight to `Offset (0x7D0)`, so `0x07C7`-`0x07CF` is
undeclared the same way; between its first and last anchor the list leaves
2,606 of 2,659 bytes unallocated, in a longest unbroken stretch of
`0x07D8`-`0x0E0C`. It is the *allocation* that is the small fraction of the
region — of the region's 65,536 bytes the list claims 95 whole, as the tool
prints above, well under one percent — and one byte's absence from a list that
size carries no information on its own.

Both of those are **unallocated-byte** counts, and the distinction is not
cosmetic — it is the difference between two figures that look interchangeable
and are not. A multi-byte element fills bytes the anchor-to-anchor gap then
counts as empty: `Offset (0x7D4)` allocates `CPUA`, `DBAP`, `DBSP` and `CGCT`
across `0x07D4`-`0x07D7`, so the stretch after it begins at `0x07D8`, and
`Offset (0x744)` does the same for `0x0745`-`0x0747`. Adding up the 23
anchor-to-anchor gaps therefore double-counts every such continuation byte and
lands well above the complement. The figures above come from expanding the
element list to absolute byte addresses and taking the complement, which is
what `check_dsdt_ecmg_pair.py`'s `allocated_bytes` does; the gap count stays
in the tool as a separate figure with its own definition, because a gap count
and an undeclared-byte count are not the same measurement and only one of
them is in bytes.

The clause survives, restated, because it is load-bearing evidence for
something narrower than it reads as: `0x07D2` is the **third** byte of the
little-endian window the PD firmware works in (§4.3 of
`ec/annotations/ec-0x07d1-sites.md`), and the field list's boundary at
`Offset (0x7D3)` puts `0x07D2` outside the declaration entirely. That is what
makes the PD's 16-bit reads straddle the DSDT's field boundary — the DSDT's
own declaration stops one byte short of the quantity the PD reads. Dropping the
clause would lose the arithmetic; what it cannot support is reading it as a
fact about one byte being unusual.

The same list leaves **bit 7 of `0x07D3` undeclared**: four unnamed bits, then
`GFID`'s three, then straight to `Offset (0x7D4)`. Of the four bytes
`0x07D0`-`0x07D3`, `0x07D3` is the only one the EC image carries a direct
reference to — the other three are PD-image only — and #183 already owns it.
(That is a statement about these four bytes, not about the wider
`0x07C4`-`0x07D7` GPU block, several of whose bytes do have EC-side
references; `ec/annotations/dsdt-ecmg-fields.csv` carries the per-image split
for all of them.)

### Two corrections to the figures the issue was filed with

Both are stated here in the §4a-4d form, with the wrong figure left standing.

**The committed parse was eight bits short.** The issue's one-off ran this
against the same file:

```console
$ python3 - <<'EOF'
import re
lines=open('evidence/acpi/dsdt.dsl').read().split('\n')
seg=lines[52194:next(i for i in range(52194,len(lines)) if lines[i].strip().startswith('}'))]
off=re.compile(r'^\s*Offset\s*\((0x[0-9A-Fa-f]+)\)'); fld=re.compile(r'^\s*([A-Za-z0-9_]{0,4}),\s*(\d+),\s*$')
a=g=t=0
for l in seg:
    if off.match(l): a+=1
    elif fld.match(l): t+=int(fld.match(l).group(2))
print(f'{a} anchors, {t} bits = {t//8} bytes of 65536')
EOF
28 anchors, 759 bits = 94 bytes of 65536
```

*(Superseded, issue #228.)* The real total is the one printed above: **28
anchors, 767 bits**. The pattern requires a trailing comma, and iasl does not
put one after the list's last element — `MGOF,   8` at `:52327` carries none —
so `MGOF` was silently dropped. The shortfall is exactly the eight bits that
element declares, and nothing failed: the number was simply wrong. The tool's
pattern makes the comma optional, and its `--self-test` pins a fixture whose
last element has no comma so a later "tidy the pattern" cannot reintroduce it.

**"11 gaps between anchors" does not reproduce.** Under the natural reading —
consecutive `Offset` anchors more than one byte apart — it is the 23 the tool
prints. The issue gave no definition, so the figure cannot be recovered; the
definition is stated with the number rather than left to the reader. Only four
of the 28 anchors are adjacent to their predecessor (`0x0743`/`0x0744`,
`0x07C4`/`0x07C5`, `0x07C5`/`0x07C6`, `0x07D3`/`0x07D4`).

**The name lengths bound was a trap the parse had not noticed.** The same
pattern caps names at `{0,4}` characters. Every one of ECMG's 98 names is four
or fewer, so the cap never bit here — which is why it is worth removing rather
than keeping: a fifth character would drop the line with nothing to say so. The
reconciliation above is the backstop, and it is a real one: it is what would
have caught the `MGOF` dropout instead of silently reporting a smaller total.

## The collision question belongs to the EC, and here is where that lives

§8 of `ec/annotations/ec-0x07d1-sites.md` left this open and unassigned:

> Does the PD's 16-bit reading of `0x07D0`/`0x07D1` ever collide with the
> DSDT's two independent byte fields?

It cannot arise *as posed*, and the reason is not that nobody looked hard
enough — it is that the DSDT has no reading to collide *with*. The only
directions in the DSDT are two byte stores, both in one `T1WR` arm. What
survives the correction is the disagreement about **meaning** recorded above:
two independent byte stores on one side, overlapping 16-bit little-endian
windows on the other. That becomes a fault only if something reads those bytes
the other way as well, so the question moves off the DSDT entirely and onto
the firmware that owns the XDATA the DSDT writes:

- **The EC side**, and its indirect-access blind spot, is #34's. One scope note
  that this corrects rather than repeats: `ec/annotations/indirect-xdata-sites.md`
  §4 answers that issue for `0x07B9` and `0x07D0` only. `0x07D1` and `0x07D2`
  are outside the scope it walked, so #34 has *not* answered for these bytes
  and this does not claim it has.
- **The live half** is the GPU-door run over `0x07C4`-`0x07D7`,
  `docs/hardware-tests/gpu-tgp-07c4-07d7-door.md`. That document was written
  for #184, which is closed; **#278 owns the run.** No laptop is reachable from
  a pipeline runner, so the procedure is prepared and the observation is not
  made here.
- **`0x07D3`** is #183's, for the bit-7 gap this list leaves and for its
  direct-reference count, which `ec/annotations/dsdt-ecmg-fields.csv` carries
  per image and this write-up does not restate.

Note also that "the PD never combines them" would be as wrong as the sentence
being corrected. §4.3 of `ec/annotations/ec-0x07d1-sites.md` records that the PD
firmware's `0x8662`/`0x866A` copies `0x07D0` into `0x07D1`, so the *PD* does
combine them; every claim above is scoped to the DSDT and to the field list.

## What this does not establish

- **Nothing about the EC.** `0x07D0`/`0x07D1` keep
  `unknown-not-absent-DO-NOT-WRITE-BLIND` and no `status:`, `static_refs*` or
  `addr:` moved. A decode of what the DSDT writes is not evidence of what the EC
  does with the bytes, and the EC image's having no *direct* reference to any of
  `0x07D0`/`0x07D1`/`0x07D2` by this method is §4c's signal, not a verdict —
  the same blind spot that once made `0x07B9` look unwritten and working.
- **Nothing about the live machine.** The two-hit census is a property of one
  committed DSDT. Whether a different firmware revision adds a reader is
  exactly what `ec/tools/check_dsdt_ecmg_pair.py --check` turns red over; it is
  not evidence about what any board does.
- **No new `registers.yaml` row for `0x07D2`.** Inventing an entry to hold a
  "nobody named this" observation would put a row in the source of truth for
  register status that asserts nothing. The absence is already carried where it
  belongs, in the door document's own table.
- **No decode of what the two bytes mean.** `Arg1 * 8` with `Arg1` bounded by
  31 is arithmetic on the ASL. Naming the quantity is §4.3's open question,
  pointing at #26 and #67.

## Keeping it true

`ec/tools/check_dsdt_ecmg_pair.py` holds all of it, from two committed inputs
and with no firmware image open:

```console
$ python3 ec/tools/check_dsdt_ecmg_pair.py --check
$ python3 ec/tools/check_dsdt_ecmg_pair.py --self-test
$ python3 -m unittest discover -s ec/tools -p test_check_dsdt_ecmg_pair.py
```

`--check` fails when a name's hit count or classification moves, when a hit
falls outside both named spans, when any of the three computed-base methods
gains a caller, when a coverage figure moves, or when the `Field` parse and the
committed CSV's `width` column stop agreeing. The last of those is the one
that would have caught the `MGOF` dropout.

The accessor census is the one that has no counterpart in the name census, and
that is what it is for: a reader reached through `ECRR` adds no occurrence of
`DBD1`, leaves both hit counts exactly where they are, and passes every check
the two-hit claim makes on its own. Only counting calls finds it.

`--self-test` pins the refusals against fixtures, because a check that has
quietly stopped refusing looks exactly like a check that is working: a reader
added *inside* the writer arm (which stays inside a named span, so only the
classification sees it), a third site in a neighbouring arm, a deleted store, a
renamed writer arm, a `Field` list that no longer reconciles with its CSV, a
field that is no longer 8 bits wide, and a caller for `ECRR`.

The suite beside it asserts the properties of the committed tree — that the two
parsers reconcile, that the named plus unnamed split is the total, that every
hit falls inside a span, that the three accessors are declared and uncalled,
and that the undeclared-byte count and the gap sum are different quantities —
rather than restating the census, so there is one place a later DSDT revision
has to be edited and not two.

Neither the tool nor the suite is called from
`.github/scripts/agent-gates.sh`, which is a copy from `ElDavoo/agent-pipeline`;
adding a gate call there is an upstream change plus a re-copy, not a line in
this repository. The suite runs in CI regardless, because `.github/workflows/`
invokes `tools/run-tests.sh`, which finds every `test_*.py` in the tree.