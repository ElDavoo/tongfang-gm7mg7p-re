# The census figures a page keeps restating, and the tool that stops holding them by hand

(2026-10-02, issue #342. Arithmetic over two committed CSVs and the constants
`xdata_register_map.py` pins them with. No decompile re-exported, no Ghidra
project touched, no EC opened, no capture taken, no hardware.)

Issue #342's complaint was not that a census figure was wrong. It was that the
figures are *transcribed*: `ec/annotations/xdata-register-map.md` opens on a
number and repeats it for the length of the file, `docs/findings.md` §3c
repeats it back, and issue #292's count rule reads table cells keyed on a
cluster id and, by its own docstring, leaves free text alone. That is a
legitimate line for a merge to have drawn. The figures being on the wrong side
of it is the defect, and it is not one a re-read can fix: the same sweep has to
be redone by hand after every census pass, which is why it was not.

So this is a tool, not a sweep. `ec/tools/check_census_figures.py` re-derives
the census from `ec/annotations/xdata-registers.csv` and
`ec/annotations/xdata-clusters.csv` -- the two files `xdata_register_map.py
--check` regenerates cell for cell, so a figure derived from them is the census
figure by construction rather than by assertion -- reads `ORACLE` and
`BUCKET_TOTALS` out of `xdata_register_map.py` by `ast`, and holds each declared
prose site to the result. `--print` emits the same figures as a markdown
fragment, so a page can cite a command instead of carrying a number.

## What the tool reads, and the two things it will not

It reads the two CSVs, the two constants, and the site list. It refuses
`ec/decompiled/`, and that refusal is the interesting half.

These `ORACLE` keys cannot be derived from the committed CSVs: `extmem_refs`,
`extmem_raw`, `extmem_commented`, `extmem_main_refs` and `symbol_main_refs`.
The reference counts among them are **split by token spelling**, and the reason
is one property of the data rather than one per key: an address the decompile
spells two ways is one row of `xdata-registers.csv` carrying one `refs` for the
address, not a split of it. `0x07D8` is `symbol+DAT_EXTMEM` on one row, and
nothing in the committed CSV says which of its references took which token.
`spellings_by_program` splits the *distinct* counts cleanly because it is a set;
the reference counts do not split because it is not. `xdata-clusters.csv` cannot
help either -- it sums addresses, not tokens.

Deriving them would mean re-reading `ec/decompiled/` with a second regex, which
is how this file's own preamble describes the trap: the census is always a lower
bound on the machine code, and a second reader of the tree would have its own
answer, so a disagreement between the two would arrive as a red run naming a
prose sentence that had done nothing wrong. So the tool declines them and
prints the reason beside each. **That is "not read by this method", never
"absent"** -- the caveat `ec/annotations/registers.yaml` and
`check_doc_figure_pins.py` both carry, and here it is the load-bearing half of
the tool rather than a decoration. `extmem_raw` in particular is pinned by
`ORACLE` and asserted by `--self-test`; what this tool declines is *its own* re-derivation
of it, and the site that names it is held by the `grep` printed beside it in
§1a, which is the shape the issue asked for in the first place.

The partition is asserted from both sides, not assumed: every `ORACLE` key is
either derived here or listed in `DECLINED` with a reason, and a key that has
become derivable while still being listed is a red run. That is what stops the
decline list from quietly becoming a place where inconvenient figures go to
die.

`xdata_register_map.py` has a second module-level dict, `OWNERSHIP`, and it
shares key names with `ORACLE` while disagreeing on two of them: `main_refs`,
where `OWNERSHIP` reads 9320 against `ORACLE`'s 14838, and `refs`, where it
reads 10178 against 15696. Both constants are therefore read **by name**. A
reader that took whichever dict it found first would be comparing two censuses
and reporting agreement or disagreement at random, which is a worse failure than
reading nothing.

## The three readings a site can have, and why two of them are not checked

The rule that decided the design is this repository's own: a wrong figure stays
visible beside its correction (`CLAUDE.md`, `docs/findings.md` §4a-4d). A
checker that demanded every number on a page match the current census would
therefore be red on `docs/findings.md` §3c's parenthetical -- which is *right*
to keep #181's "is unchanged" visible -- and would be teaching everyone to
delete their corrections. So a site declares which of three readings it is:

* **`live`** -- the line claims a figure about this tree, and is held to it.
* **`historical`** -- a superseded figure, kept on purpose beside the correction
  that names the tree it was measured on.
* **`attributed`** -- a measurement the page is restating from someone else.
  §3c's opening paragraph counts `DAT_EXTMEM_` out of `ec/decompiled/*/*.c`
  itself, and those numbers are the thing being corrected; a checker that turned
  red on them would be red on the correction.

`historical` and `attributed` rows are counted, printed with their reason, and
never fail the run. They are not unchecked because they matter less -- they are
unchecked because the page is *right* to keep them. Their markers are still
resolved, so a marker that stops resolving is how the tool says the page moved.

A `live` line's figures must all be claimed: one key per figure, positionally,
with `skip` for a number on the line the site does not claim. A line that grows
a figure nobody claimed is a red run rather than a silent gap, and
`ec/README.md`'s `registers.yaml` count is a real instance -- it is declared
`skip`, with the reason in the row.

Markers are **content, not line numbers**, because `CLAUDE.md` says to cite by
name for the reason line numbers move. `lines_after` exists only because a
console transcript puts the figure on its own line: the marker names the
`grep | wc -l` command and the figure is under it. The alternative was a marker
naming the number, which is the expected value in everything but name.

## What the sweep found, on this tree

The issue's own table is two census passes stale, so every figure below was
re-measured rather than taken from it. `python3 ec/tools/check_census_figures.py
--print` prints all of them with the derivation beside each.

`docs/findings.md` §3c's table read `1,063 | 157 | 1,172` /
`13,937 | 864 | 14,801` / `41 | 0 | 41`. The committed census reads **1,218** /
**157** / **1,326**, **14,838** / **858** / **15,696**, and **184** / **6** /
**190**. Its sentence under the table read "41 of the 1,063 XDATA addresses the
main EC touches carry a name, and 1,022 do not"; the same figures are **184** of
**1,218**, and **1,034** do not. The `96% of the register file is still
DAT_EXTMEM_xxxx` that went with it is gone rather than restated: a percentage
whose rounding the sentence never gave is a figure that cannot be re-derived,
which is a decline, not a correction.

The named row is a third kind of error rather than a staler copy of the two above
it: its **label** decides which figure it takes. `172` is
`ORACLE["symbol_main_distinct"]` -- the rows the main EC writes *under* the
symbol in the exported C -- which is the spelling question, not the naming one,
and it does not belong under a row called "named from `registers.yaml`". The
two differ wherever an address carries a name and is still written
`DAT_EXTMEM_xxxx`, and that is every address the PD image reaches:
`gen_xdata_symbols.py` refuses to name that program, so the PD cell is **6**
where the spelled count is zero. The census does publish a whole-corpus naming
count after all, `named_in_tree`, and `derive()` now splits it the way the row
does -- a partition rather than two halves, since a `both` row is already in the
main EC's cell.

The load-bearing false sentence was §3c's #181 parenthetical -- "*the other
number here -- the 41 main-EC addresses the decompile spells by symbol -- is
unchanged*". `ORACLE["symbol_main_distinct"]` reads 172 on the committed tree.
The #181 claim was true on #181's tree; the symbol table grew under it, by #194
and #179/#180/#183 among others, and a claim about a measurement being
*stable* is the one kind of claim a census pass takes away silently. The
parenthetical stays as written, with the correction beside it, and the tool now
holds the correction's figures.

`xdata-register-map.md`'s "issue #132's own counts ... are all unchanged, and
all still pinned" had already been corrected once, in #557's note, and *that*
correction had drifted since: it named 147 symbol-spelled main-EC addresses
(172 today) and called `pd_only` / `both` unchanged at 109 / 48 (108 / 49). The
note stays; a second dated correction carries the current figures and says that
only the top-two pair is still unchanged. The same page's §2 sentence carried a
figure no census key expressed -- "the same holds for the other 166 named
main-EC addresses" is the total less the one address the sentence is about --
and calling that "the total" would not have repaired it, because the sentence
is a claim about *spelling*: **zero** of an address's mentions sit under a
`DAT_EXTMEM_xxxx` token. That is true of the addresses the main EC writes under
their symbol and false of the named ones, three of which carry a name and are
still written `DAT_EXTMEM_` (`0x078B`, `0x07A5`, `0x0803`). So the sentence now
reads over the set the figure measures -- the addresses the main EC spells by
symbol -- rather than calling those "named main-EC addresses", which is the
naming/spelling conflation the `named_main` derivation above already separates.
§5's two narrative figures beside the `main-ec-002` table row --
"33 named registers land" and "109 addresses reached by one mode tick" -- had
drifted behind the row they sit under, which already read 34 and 92.

`ec/README.md` carried the census size twice, as **1,171** and **1,172**. Both
are **1,326**. Its `registers.yaml` counts were left alone and declared `skip`:
that file has 184 entries of which fifteen carry a *list* of addresses, so "how
many addresses" has more than one answer, and the tool that owns that question
is `check_register_counts.py`, not this one. Two figures left explicitly
unmeasured is a better outcome than two replaced by numbers nobody here checked.

## The row/line conflation, which was the sharpest thing in the issue

`xdata_register_map.py` printed `{len(rows)} rows match a fresh generation` --
data rows -- and, on a mismatch, `{len(on_disk.splitlines())} on disk vs
{len(generated.splitlines())} generated` -- **file lines, header included**. The
same noun for two different quantities, in one tool, on adjacent lines. That is
why a correct `--check` line read as a row count for a year, and why
`docs/findings.md` carries a sentence explaining an ambiguity the tool itself
manufactured.

The fix is one word in one message: `diff()` now says `N lines on disk vs M
lines generated`. The number cannot be made to mean both things at once, so
naming it in both messages is the whole of the fix. §1b's correction paragraph,
which already worked the ambiguity out in prose, now says that the tool says so
itself.

## What this does not establish

Nothing about the machine. Every figure above is arithmetic over files already
committed, and no EC was opened, no register read back and no capture taken. If
a future pass wants a figure to be confirmed against the firmware rather than
against the census's own reading of a decompile, that is a `needs-hardware-test`
issue and a human at the machine.

The tool also runs by hand. It is **not** in `.github/scripts/agent-gates.sh`,
and cannot be until a human adds it there with a token that has `workflow`
scope; `.github/` is out of this repository's agent reach by construction. A
checker nobody runs is the shape of defect #819 was, so the standing is stated
in the tool's own docstring rather than left for a reader to assume a gate
exists.

## Follow-ups this opens

- **The gate line is a human's.** One line in `.github/scripts/agent-gates.sh`
  makes the sweep a gate rather than a habit. It is the whole of what is left,
  and it is deliberately not done here.
- **The site list is short and says so.** What is declared is what the sweep
  found, not every figure on every page: a census pass re-derives the declared
  set mechanically and finds the rest by reading. The next candidate is
  `xdata-06c2-06db-timers.md`, which quotes `BUCKET_TOTALS` in prose.
- **`xdata_program_keyed_table.py` is the model worth copying.** §2's per-program
  spelling table was already generated rather than transcribed, and it is the
  reason this sweep did not have to touch it. Two tables on one page, one
  derived and one hand-maintained, is the shape that produced #342.