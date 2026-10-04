# Per-dispatcher inline width, and the PD image's third CODE-table dispatcher

## The width was never a property of the shape

`pd_image_census.py` measures the call sites of the PD image's CODE-table
dispatchers, because those dispatchers pop the return address into DPTR and so
make every table in the program a literal in the image — the most plausible
route from a literal to a string, and the one worth measuring rather than
listing. It read a single window of `INLINE_TABLE_BYTES = 4` after each site,
for two of the image's three dispatchers.

Four is a width one of the three dispatchers walks, and it was held over the
other two:

| dispatcher | entry width | `lcall` sites | was it measured before? |
|---|---|---|---|
| `0x119C` `dispatch_code_table` | 3 | 9 | at 4 — straddling entries |
| `0x11C2` `dispatch_code_table_2byte_key` | 4 | 16 | at 4 — its own width |
| `0x11EF` *(unnamed)* | 6 | 3 | not at all |

The widths are derived, not declared: `pd_index_tables.py`'s `entry_stride()`
counts the `inc dptr` run feeding the branch that returns to each reader's own
zero-test, and the same derivation returns 3 for the main EC's reader at
`0x07151`, so it means the same thing in both images. The census now reads each
dispatcher at its own width, `CODE_TABLE_ENTRY_WIDTHS` in place of the single
constant.

**`0x119C` moves from a 4-byte window to a 3-byte one, which is the larger half
of what this changes and not the half the fix was aimed at.** A stride of 3 is
the same family as the main EC's reader, so it is easy to read past — but the
bytes at the first `0x119C` site, file `0x2136C`, split evenly at three and do
not split evenly at four:

```console
$ python3 -c '
import sys; sys.path.insert(0, "ec/tools")
from pd_image_census import read_region, CODE_TABLE_ENTRY_WIDTHS
region, _ = read_region()
for target, w in CODE_TABLE_ENTRY_WIDTHS.items():
    i = region.find(bytes([0x12, target >> 8, target & 0xFF]))
    raw = region[i + 3:i + 3 + 3 * w]
    print("0x%04X width %d at file 0x%05X" % (target, w, i + 0x20000))
    print("   own width: " + " | ".join(" ".join("%02x" % b for b in raw[n:n+w])
                                        for n in range(0, len(raw), w)))
    print("   as 4:     " + " | ".join(" ".join("%02x" % b for b in raw[n:n+4])
                                        for n in range(0, len(raw), 4)))
'
0x119C width 3 at file 0x2136C
   own width: 1e 09 01 | 13 af 02 | 13 dc 03
   as 4:     1e 09 01 13 | af 02 13 dc | 03
0x11C2 width 4 at file 0x213F6
   own width: 14 19 02 06 | 14 4c 03 01 | 14 52 04 01
   as 4:     14 19 02 06 | 14 4c 03 01 | 14 52 04 01
0x11EF width 6 at file 0x224FE
   own width: 25 32 00 00 00 05 | 25 11 00 00 00 08 | 00 00 25 7d 90 0a
   as 4:     25 32 00 00 | 00 05 25 11 | 00 00 00 08 | 00 00 25 7d | 90 0a
```

Only `0x11C2`'s two lines agree, which is the whole finding: a single window
over three dispatchers is right for at most one of them. What the six bytes of
a `0x11EF` entry *mean* is a separate question and is not answered here —
`docs/findings/table-reader-spellings.md` is the write-up that reaches this
dispatcher, and the entry layout is that issue's ground.

## The null does not move, and that is a property rather than luck

The measurement the census actually cares about is
`opens_a_pool_entry` — is the dispatcher's first `movc` reading text? That is
`(site + 3) in pool_starts`, where `pool_starts` is what
`string_candidates()` returns. **The width is not in it.** `site + 3` is where
the first `movc` reads whatever the stride is; the stride governs how far DPTR
advances *between* entries, never where the first one starts. So the width
decides what a row quotes and nothing else, and the null holds across the
widening rather than surviving it by luck.

That was verified against the committed image rather than assumed. With the
third dispatcher in the search, the three come back **9, 16 and 3 sites and 0
of the 28 open a pool entry**; the `0x11EF` sites are at file `0x224FE`,
`0x22867` and `0x2BCEE`, which are the addresses
`docs/findings/table-reader-spellings.md` already reports.

**What the null is.** A statement about a scan for NUL-terminated printable
runs over these 28 sites, each at its own dispatcher's entry width. Not an
absence of strings, and not a claim about any other route — the tool's
docstring keeps the scoping sentence that says so, restated from "these 25
sites and these 4 bytes" to "these 28 sites and each dispatcher's own entry
width". A wider window remains available as an explicit argument and is a
different measurement, which the suite pins as one.

## The reconciliation was two searches that happened to agree

`pd_index_tables.py --self-test` iterated the census's own
`CODE_TABLE_DISPATCHERS`, so it could only confirm that the two tools agreed
about the dispatchers both already named: a fourth one in this image would have
been in neither tool's list, so neither search and neither check would have seen
it. It now reconciles over `READERS` — the set this tool derives from the
bytes — in three checks:

- `set(committed) == set(READERS)` and every per-dispatcher count equal, so a
  dispatcher one tool has and the other lacks is red in whichever tool holds it;
- `CODE_TABLE_DISPATCHERS` equals `READERS`, which is what turns "a fourth
  dispatcher" red rather than into a silent omission;
- `CODE_TABLE_ENTRY_WIDTHS`'s keys equal `READERS` **and its values equal
  `STRIDES`**, so the census's declared widths are held against strides read
  off each reader's own loop and the two cannot drift into two true-looking
  constants.

No import direction changes: the census declares, this tool derives, and the
check holds them equal.

A check nobody has seen fail is not a check, so each was run against a mutated
copy of the census:

```console
$ python3 ec/tools/pd_index_tables.py --self-test     # unmutated
self-test passed
```

| mutation | what went red |
|---|---|
| `0x11EF` dropped from `CODE_TABLE_DISPATCHERS` | the site-count equality **and** the constant-identity check |
| `CODE_TABLE_ENTRY_WIDTHS[0x11EF]` set to 4 | the width check |
| `CODE_TABLE_ENTRY_WIDTHS[0x119C]` left at 4 | the width check |

The census's own suite carries the same argument from the other side: the
per-dispatcher width is pinned case by case, and the planted-string fixture runs
once for each dispatcher, so a third dispatcher added with the wrong width or a
scan that never looked at it could not leave the null green for the wrong
reason. Both mutations were run against a copy of the census:

| mutation | what went red |
|---|---|
| all three widths set to 4 | `test_each_dispatcher_is_read_at_its_own_entry_width` |
| `opens_a_pool_entry` hardcoded to `False` | `test_a_planted_code_table_string_is_found`, once per dispatcher |

A third — dropping `0x11EF` from the search loop alone, leaving the constant —
takes the null case, the figure case and the planted fixture red as well,
because the site counts and the pinned figure both move.

## Ordering against the entry-layout question

`docs/findings/table-reader-spellings.md` reaches `0x11EF` through a search and
asks what its 6-byte entries are; this one changes what the census *measures*
at each dispatcher's width. They touch `pd_image_census.py` and the
`code_table_inline` line respectively, and neither regenerates the other's
output: `pd_index_tables.py --spans-csv` is byte-identical across this change.

```console
$ python3 ec/tools/pd_index_tables.py --spans-csv | diff - ec/annotations/pd-index-table-spans.csv
$ echo $?
0
```

Land this one first and the entry-layout one second, so the per-dispatcher
widths are re-derived against a `pd_index_tables.py` whose entry verdicts are
already settled. If the order is reversed the only re-work is re-running
`--check` and the suite: the widths come from `entry_stride()` and do not depend
on what an entry means, so no figure here moves either way.

## Left out

- **A name for `0x11EF`.** It has no row in `ghidra-functions.csv`, and a name
  needs a `name_basis` that CSV's vocabulary accepts. Both this write-up and
  `ec/annotations/pd-image.md` cite it by address alone; adding the row is a
  separate naming issue.
- **What its entries mean.** Nothing here decodes an entry. The census keeps
  reporting `opens_a_pool_entry`, which asks only whether the first `movc` reads
  text.
- **`decode_index_table.py`'s 3-byte rule.** `pd_index_tables.py` already
  carries the main EC's rule over another stride and says so per row, and that
  stays. The analogy to `decode_table()` is about the census's own window, not
  about that column.
- **Anything behavioural.** No table here is claimed to execute, no register is
  read, and no `status:` in `ec/annotations/registers.yaml` moves. Every input
  is `ec/firmware/GMxMGxx_11.800`, already committed.

## Reproducing it

```console
$ python3 ec/tools/pd_image_census.py --check
$ python3 ec/tools/pd_image_census.py --self-test
$ python3 ec/tools/pd_index_tables.py --self-test
```
