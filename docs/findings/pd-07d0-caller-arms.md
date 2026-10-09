# The thirteen PD caller arms for the 0x07D0 accessor stubs

## What this is

Thirteen `pd` functions that call the `0x07D0` accessor stubs, seeded in issue
#1286. They are fall-through cases inside larger dispatcher routines with no
incoming transfer from elsewhere. Named, cited to bank and address, with listings
and decompiles in `ec/decompiled/pd/`.

The thirteen, as they call the stubs:

| address | stub | address | stub | address | stub |
|---|---|---|---|---|---|
| 0x488F | 0x4C12 | 0x5131 | 0x52EF | 0x79B3 | 0x7B0D |
| 0x4932 | 0x4C12 | 0x51B2 | 0x52EF | 0x7A5A | 0x7B0D |
| 0x496C | 0x4C19 | 0x51E6 | 0x531F | 0x842F | 0x856F |
| 0x4989 | 0x4C19 | 0x51FE | 0x531F | 0x844B | 0x856F |
| 0x4AE9 | 0x4C20 |

Each calls its stub, then calls 0x347B and 0x104D in sequence, reading
0x07D0 through the stub. None are reached by a conditional or unconditional
transfer anywhere in the PD image — they are purely fall-through arms where a
larger dispatch exits to them.

## The byte-level collision at 0x4AE9

**0x4AE9 sits inside `pd/4D6F.asm`'s listing span (0x4A12–0x4E58) without
being spelled by it.** The listing begins with `ajmp 0x4b12` at 0x4A12, which
skips the block holding 0x4AE9, so nothing in that listing includes it. A
span-based test would say 2 of the 14 are covered; the parse test says 1 is
spelled. The difference is the whole reason for asking the parse: what a
function *lists* and what address range it covers are not the same thing, and
a parser-based census uses the first.

The seeding succeeded: Ghidra generated both the listing and decompile for
0x4AE9, and the committed files include them both. They do not collide with
4D6F: `call_graph.parse_listing()` on `pd/4AE9.asm` spells no address that
`pd/4D6F.asm` also spells.

## What the generated census says

All seven stubs now appear in `ec/annotations/call-graph-callees.csv`, each
with its correct inbound count. The regenerated census moved one line and
left six unmoved:

- `0x4C12`: `inbound=2` (the two sites at 0x488F and 0x4932)
- `0x4C19`: `inbound=2` (the two sites at 0x496C and 0x4989)
- `0x4C20`: `inbound=1` (the one site at 0x4AE9, per the existing row)
- `0x52EF`: `inbound=2` (the two sites at 0x5131 and 0x51B2)
- `0x531F`: `inbound=2` (the two sites at 0x51E6 and 0x51FE)
- `0x7B0D`: `inbound=2` (the two sites at 0x79B3 and 0x7A5A)
- `0x856F`: `inbound=2` (the two sites at 0x842F and 0x844B)

## Reproducing this

```console
$ python3 ec/tools/test_pd_07d0_caller_arms.py
  Ran 11 tests; OK.
$ python3 ec/tools/call_graph.py --check
call-graph-callees.csv: 1854 rows, no diff
$ python3 ec/tools/verify_reassembly.py --check
  listing digests: 2747 compared against the committed report, 0 disagreement(s)
```

## Sources

The listing and decompile for each address are cited in
`ec/annotations/ghidra-functions.csv` to that address's own pair of files,
and to the firmware image itself:

| address | files | firmware |
|---|---|---|
| 0x488F | `ec/decompiled/pd/488F.asm`; `ec/decompiled/pd/488F.c` | `ec/firmware/GMxMGxx_11.800` at file 0x20000 |
| 0x4932 | `ec/decompiled/pd/4932.asm`; `ec/decompiled/pd/4932.c` | `ec/firmware/GMxMGxx_11.800` at file 0x20000 |
| 0x496C | `ec/decompiled/pd/496C.asm`; `ec/decompiled/pd/496C.c` | `ec/firmware/GMxMGxx_11.800` at file 0x20000 |
| 0x4989 | `ec/decompiled/pd/4989.asm`; `ec/decompiled/pd/4989.c` | `ec/firmware/GMxMGxx_11.800` at file 0x20000 |
| 0x4AE9 | `ec/decompiled/pd/4AE9.asm`; `ec/decompiled/pd/4AE9.c` | `ec/firmware/GMxMGxx_11.800` at file 0x20000 |
| 0x5131 | `ec/decompiled/pd/5131.asm`; `ec/decompiled/pd/5131.c` | `ec/firmware/GMxMGxx_11.800` at file 0x20000 |
| 0x51B2 | `ec/decompiled/pd/51B2.asm`; `ec/decompiled/pd/51B2.c` | `ec/firmware/GMxMGxx_11.800` at file 0x20000 |
| 0x51E6 | `ec/decompiled/pd/51E6.asm`; `ec/decompiled/pd/51E6.c` | `ec/firmware/GMxMGxx_11.800` at file 0x20000 |
| 0x51FE | `ec/decompiled/pd/51FE.asm`; `ec/decompiled/pd/51FE.c` | `ec/firmware/GMxMGxx_11.800` at file 0x20000 |
| 0x79B3 | `ec/decompiled/pd/79B3.asm`; `ec/decompiled/pd/79B3.c` | `ec/firmware/GMxMGxx_11.800` at file 0x20000 |
| 0x7A5A | `ec/decompiled/pd/7A5A.asm`; `ec/decompiled/pd/7A5A.c` | `ec/firmware/GMxMGxx_11.800` at file 0x20000 |
| 0x842F | `ec/decompiled/pd/842F.asm`; `ec/decompiled/pd/842F.c` | `ec/firmware/GMxMGxx_11.800` at file 0x20000 |
| 0x844B | `ec/decompiled/pd/844B.asm`; `ec/decompiled/pd/844B.c` | `ec/firmware/GMxMGxx_11.800` at file 0x20000 |

No live test ran. No hardware is reachable from the CI environment. These
functions were seeded from their committed annotations and exported with
Ghidra in headless mode.
