# `0x07CC` is re-graded, and the rule that grades it is now written down and
# checked (2026-09-27, issue #32)

`USB_C_POWER_PRIORITY` (`0x07CC`) was graded `present-untested` on a count of
six sites, **every one of them in the ITE8850-PD image**: `static_refs_main_ec:
0`, `static_refs_pd_image: 6`. `present-untested` is defined in
`registers.yaml`'s own header as "static-scan finds real references, not yet
exercised live", so on that count it asserted EC-side presence on evidence the
per-image split had already emptied. `ec/annotations/static-refs-audit.md` §2
flagged it and, in its own words, declined to fix it: "re-grading it is a
vocabulary question this audit deliberately does not open."

This is the answer to that question, plus the rule, plus a check that holds the
rule. It is bookkeeping on calibration: **no `static_refs*` count moves, no
register's behaviour changes, and nothing here needs hardware.** No live test
ran, none is claimed, and none is needed — the tool reads a committed YAML file
and the counts beside it are re-derived from the committed image by
`check_register_counts.py`, which is unaffected by this change. Live behaviour
of `0x07CC` is issue #8 and stays open whatever the grade.

## The decision: `unknown-not-absent`, the value already in the file

The issue offers two options. This takes the first, and the second is worth
naming as declined rather than skipped: **no new vocabulary value is
warranted.** The header already defines `unknown-not-absent` in exactly these
words —

> `unknown-not-absent`: the references that made it look present turned out to
> belong to the PD image, so the EC image has none — and per the note above
> that is not "absent" either

— and `0x07CC` is that case. The argument for adding a value would have to be
that the existing one is the wrong name, and it is not: five sibling PD-only
entries have carried it since the lightbar retraction, it is defined in the
file's own idiom, and CLAUDE.md asks for existing values rather than invented
ones. The useful finding is not "a value was missing" but "a value that was
already correct had been under-applied to one entry" — and that is only
visible against a whole-file sweep, which is below.

**Left out of scope deliberately, and named so it is not smuggled:** a distinct
`pd-image-only` value. It would need `0x07D0`, `0x07D1`, `0x07D6`, `0x07D7` and
`0x07E2`-`0x07E5` moved onto it too, splitting one value that means one thing
into two, on no evidence. The value it would distinguish from is `absent`, and
the two already differ in the way that matters: both are "not found by this
method", and the header's `absent` note is where the `0x07B9` blind spot is
recorded. Adding a third name for one of the two would make the reader's job
harder, not easier.

## The sweep, over the whole file rather than the audit's snapshot

`static-refs-audit.md` audits 29 addresses as it stood when it was written;
`registers.yaml` now holds **160 entries / 192 addresses**, so an entry added
since would not appear in its table. The sweep below enumerates every entry in
the file, which is the mechanical form of the issue's "and to any other entry
the audit table shows in the same position":

| position | entries | status |
| --- | ---: | --- |
| every address `main_ec: 0`, some PD-image site | 6 — `0x07D0`, `0x07D1`, `0x07E2`-`0x07E5` (one entry), `0x07D6`, `0x07D7`, `0x07CC` | 5 × `unknown-not-absent` (two with the `-DO-NOT-WRITE-BLIND` suffix), **1 × `present-untested` = `0x07CC`** |
| partly split (some addresses EC-side, some not) | **0** | — |
| zero sites in either image | 6 | `absent` ×2, `unknown-not-absent` ×3, `confirmed-not-this-mechanism` ×1 |

Two things fall out, and both are about the *rule* rather than the row.

**`0x07CC` was the only entry in the file claiming EC-side presence on a
PD-only count.** So the issue's "any other entry" resolves to nothing else —
which is worth more as a stated sweep over 160 entries than as a spot check of
29, because entries added later are covered by the tool rather than by a
sentence written today.

**No entry is partly split**, so the rule needs no per-address judgement about
which half of a mixed entry counts. An entry is wholly EC-side, wholly
PD-only, or has no sites. (That is a property of this file today, not a law:
`0x04A6` is 3 EC-side / 4 PD-side and would be a mixed entry, so the rule is
written per address anyway and the tool prints a `partly split` count for
exactly that reason. The count is 0 and is printed so a future mixed entry
shows up rather than being absorbed silently.)

## The rule, as written into the header

`registers.yaml`'s `# status values:` comment now carries two rules in the
file's own `#   value : gloss` idiom, and
`ec/tools/check_status_vocabulary.py` enforces both:

1. **Vocabulary closure.** Every `status:` is a value the header declares,
   optionally carrying a declared suffix. The tool **parses the declared list
   out of the header comment** rather than carrying its own copy, so the
   comment stays the single source of truth and the two cannot drift apart
   silently again.
2. **Count warrant.** `present-untested` — the one value whose entire warrant
   is a reference count — requires `static_refs_main_ec` ≥ 1 for **every**
   address in the entry. Per address, not per entry, so a mixed entry is
   caught on the address that fails rather than excused by a neighbour that
   passes.

Writing rule 1 down surfaced that the comment was itself incomplete. Three
things the file uses were never declared: `confirmed-working-partially` (one
entry, `0x07A6`), `confirmed-not-this-mechanism` (one entry,
`LIGHTBAR_AC_*`), and the `-DO-NOT-WRITE-BLIND` suffix convention (two
entries, `0x07D0` and `0x07D1`). A list nothing checked was a list nothing
kept true. The converse holds too and is worth saying out loud rather than
leaving a reader to wonder which way the drift runs: **`confirmed-inert` was
declared and no entry uses it.** It names a real state — a write proven live
to be accepted and ignored — so it stays; the one entry that was downgraded out
of it, `0x0726`, says in its own note that the real verdict is unknown, which
is the calibration rule refusing exactly the grade the value would have
carried.

## The exemption, and why it is stated rather than implied

Rule 2 applies to `present-untested` **only**. The four statuses whose warrant
is a *live* observation — `confirmed-working`, `confirmed-working-partially`,
`confirmed-inert`, `confirmed-not-this-mechanism` — are exempt, because a live
observation is a different kind of evidence from a scan: a direct
`MOV DPTR` scan cannot see a byte reached through indirect addressing.

The committed proof that the exemption has a user is
`LIGHTBAR_AC_CTRL / RED / GREEN / BLUE` (`0x0748`-`0x074B`):
`confirmed-not-this-mechanism`, and **zero sites in either image**. A rule
demanding EC-side sites of a live-refuted byte would re-introduce the error
this repo has already paid for once — `0x07B9` is a byte Windows demonstrably
writes and works, with zero direct sites anywhere in the image, and that is the
retraction `docs/findings.md` §4c records. So the exemption is written into
the header, printed beside the rule on every `--check` run, and pinned by a
`--self-test` case per exempted status.

The other direction of the same care: **re-grading `0x07CC` says nothing about
whether the EC touches that byte.** The EC image still references `0x07CC` zero
times by this method, which is the `0x07B9` blind spot's own phrasing —
"not found by this method" — and not "the EC does not implement it". Whether
the EC acts on the byte is open, and stays open as #8.

## Two questions this surfaces, and does not answer

Both are recorded rather than absorbed: a second decision folded into this one
makes the diff harder to review for no gain, and CLAUDE.md asks for a finding
that opens a question to say so.

**1. `absent` on a zero-in-both-images count — `0x0726` and `0x0765`.** Both
carry `absent` on `main_ec: 0, pd_image: 0`, which is the identical shape to
`0x07B9`, `0x07C7` and `0x07C8`, and those three carry `unknown-not-absent`.
`0x0726`'s own note is explicit: "DOWNGRADED from earlier (wrong)
`confirmed-inert` call … Real verdict: unknown". The same calibration rule
CLAUDE.md states — a static scan finding zero references means "not found by
this method", never "absent" — reaches these two on the same logic. This is a
second decision about a *different value*, on entries the issue did not name,
and `check_status_vocabulary.py` deliberately does not encode it: the tool
refuses a status whose *warrant* is a count with no sites behind it, which is
not the same question as whether `absent` is the right word for a zero in both
images. **Open.**

**2. What a single site is worth when it resolves no further.** Several
`present-untested` entries pass rule 2 on one EC-side site that is a DPTR
handoff or a `none` cell. `XDATA_0420` is the clearest case: 1 EC-side site
against 11 in the PD image, and its own note says the site "is neither a read
nor a store, and whether the byte is touched at all is not established". Rule
2 asks whether an EC-side site *exists*; it does not ask what the site *does*,
and widening it that way would make it a rule about something other than the
reference count. **Open.**

## Re-running it

Every command below reads committed inputs only — no image, no Ghidra, no
network, no hardware — and leaves the tree unchanged. Measured on this runner
from the repo root.

```console
$ python3 ec/tools/check_status_vocabulary.py --check ; echo "exit=$?"
  0x07D0                           unknown-not-absent-DO-NOT-WRITE-BLIND     DBD1 (DSDT name; ECSpec calls the same byte BATTERY_CHARGE_LIMIT_DOWN)
  0x07D1                           unknown-not-absent-DO-NOT-WRITE-BLIND     DBD2 (DSDT name; no vendor constant, no committed Windows writer)
  0x07E2 0x07E3 0x07E4 0x07E5      unknown-not-absent                        LIGHTBAR_BAT_CTRL / RED / GREEN / BLUE
  0x07CC                           unknown-not-absent                        USB_C_POWER_PRIORITY
  0x07D6                           unknown-not-absent                        DBSP (DSDT)
  0x07D7                           unknown-not-absent                        CGCT (DSDT)
160 entries: 6 PD-only (no EC-side site on any address, at least one PD-image site), 0 partly split. Every PD-only entry is listed above with the status it carries.
count rule: present-untested needs static_refs_main_ec >= 1 on every address; exempt, because their warrant is a live observation: confirmed-working, confirmed-working-partially, confirmed-inert, confirmed-not-this-mechanism
exit=0

$ python3 ec/tools/check_status_vocabulary.py --self-test ; echo "exit=$?"
  self-test passed
exit=0

$ python3 ec/tools/gen_xdata_symbols.py --check ; echo "exit=$?"
ec/ghidra/xdata-symbols.csv: 192 symbols match a fresh generation from ec/annotations/registers.yaml
exit=0
```

(The generator prints absolute paths, since it builds them from its own
location; the line above is the same one with the repo root elided.)

$ python3 ec/tools/check_register_counts.py ec/firmware/GMxMGxx_11.800 ; echo "exit=$?"
160 entries / 192 addresses: every static_refs, static_refs_main_ec and static_refs_pd_image reproduced from ec/firmware/GMxMGxx_11.800
exit=0
```

**The positive control**, because a check that has never been seen to refuse is
not evidence of anything. First with exactly one variable changed: the
committed file, header and all, with `0x07CC`'s `status:` put back to
`present-untested`. `--registers` takes any path, so the pre-change file is
constructed rather than committed (nothing under `ec/tools/testdata/` here, for
the same reason `--self-test`'s fixtures are constructed dicts: a committed
copy of the file this change edited is a second source of truth that goes stale
the moment either moves).

```console
$ mkdir -p /tmp/pre-32
$ python3 - <<'PY'
src = open("ec/annotations/registers.yaml").read()
old = """    static_refs_pd_image: 6
    status: unknown-not-absent"""
new = """    static_refs_pd_image: 6
    status: present-untested"""
assert src.count(old) == 1, src.count(old)
open("/tmp/pre-32/registers.yaml", "w").write(src.replace(old, new))
PY
$ python3 ec/tools/check_status_vocabulary.py --check --registers /tmp/pre-32/registers.yaml ; echo "exit=$?"
  REFUSED  USB_C_POWER_PRIORITY 0x07CC: present-untested is warranted by a reference count and this address has static_refs_main_ec = 0, so there is no EC-side site to warrant it with. A status whose warrant is a live observation (confirmed-working, confirmed-working-partially, confirmed-inert, confirmed-not-this-mechanism) is exempt from that; this is not one
1 refusal(s). A refusal is a shape a status is not allowed to take, not an argument that the grade is wrong.
  0x07D0                           unknown-not-absent-DO-NOT-WRITE-BLIND     DBD1 (DSDT name; ECSpec calls the same byte BATTERY_CHARGE_LIMIT_DOWN)
  …
  0x07CC                           present-untested                          USB_C_POWER_PRIORITY
  …
160 entries: 6 PD-only (no EC-side site on any address, at least one PD-image site), 0 partly split. Every PD-only entry is listed above with the status it carries.
exit=1
```

(The header comment is unchanged between the two files, so the vocabulary the
control runs against is the one that ships. Only the grade differs, which is
the whole variable.)

**The same tool over the whole file as it stood before this change** — the base
commit below, so the two controls differ in exactly the two things this change
edited rather than in one — catches the other half of the drift in the same
run: the three forms the header used but never declared, and the one grade the
count rule refuses.

```console
$ git show 9bb8fca1:ec/annotations/registers.yaml > /tmp/pre-32/base-registers.yaml
$ python3 ec/tools/check_status_vocabulary.py --check --registers /tmp/pre-32/base-registers.yaml ; echo "exit=$?"
  REFUSED  OEM_4 (CHARGING_PROFILE_MASK): status 'confirmed-working-partially' is not a value the header comment declares (one of: confirmed-working, confirmed-inert, present-untested, absent, unknown-not-absent)
  REFUSED  DBD1 (…BATTERY_CHARGE_LIMIT_DOWN): status 'unknown-not-absent-DO-NOT-WRITE-BLIND' is not a value the header comment declares (…)
  REFUSED  DBD2 (…): status 'unknown-not-absent-DO-NOT-WRITE-BLIND' is not a value the header comment declares (…)
  REFUSED  LIGHTBAR_AC_CTRL / RED / GREEN / BLUE: status 'confirmed-not-this-mechanism' is not a value the header comment declares (…)
  REFUSED  USB_C_POWER_PRIORITY 0x07CC: present-untested is warranted by a reference count and this address has static_refs_main_ec = 0, so there is no EC-side site to warrant it with. …
5 refusal(s). A refusal is a shape a status is not allowed to take, not an argument that the grade is wrong.
exit=1
```

The first four are the vocabulary-closure rule reading the old comment against
the old entries, and the fifth is the count rule. Four of the five are not
about `0x07CC` at all, which is the more useful half: a list nothing checked
had drifted in three places, and the sweep in the table above is what a reader
would have had to do by hand to find them.

`gen_xdata_symbols.py` is a **generator**, never an editor: it reads
`registers.yaml` and never writes it, so a symbol rename cannot imply a
`status:` change. Exactly one cell moved in `ec/ghidra/xdata-symbols.csv` —
`0x07CC`'s `register_status` — and the `name` column is untouched, so no
Ghidra export and no `--mode rebuild-project` is involved. That the diff is one
cell and not a renamed symbol is the check that the re-grade moved no evidence
either.

## What the file is, and where the rule is held

| | |
| --- | --- |
| the rule | `ec/annotations/registers.yaml`, the `# status values:` header comment |
| the check | `ec/tools/check_status_vocabulary.py` — `--check` and `--self-test`, in `.github/scripts/agent-gates.sh` |
| the grade | `0x07CC`'s `status:` and the re-grade paragraph appended to its `note:`, the old reading left standing |
| the sweep | this file, and the tool's `--check` output |
| the question the audit declined to open | `ec/annotations/static-refs-audit.md` §2, answered in its §9 |

`static-refs-audit.md` §2's table row (`present-untested | present-untested`)
and its sentence about not opening the vocabulary question **stay as written**,
per the retraction pattern in `docs/findings.md` §4a-4d. §9 is the file's own
established shape for a later development: §6, §7 and §8 each state one
"rather than by editing the sections above".
