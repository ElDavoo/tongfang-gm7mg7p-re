# The 0x0436 Linux probe: an unchecked column mapping, a path that missed §7, and a summary that aborted on `unknown` (issue #216)

`linux/battery-trace/remain-capacity-probe` is the Linux arm of
[`remain-capacity-0436.md`](../hardware-tests/remain-capacity-0436.md), the
procedure for the one question this page opened: is `0x0436`/`0x0437` a
remaining capacity or a periodic counter. Its Windows sibling got a dry run and
an offline suite (`windows/tools/ec_validate.py`, `test_ec_validate.py`); the
Linux arm got neither, and it is the arm a Linux-only human runs — §4 needs no
Windows at all. This is the dry run and the suite, and the defects the dry run
surfaced in the block they exercise.

**None of this is hardware evidence.** No `/dev/mem` was opened, no register was
read, and nothing has been run on the laptop — `CLAUDE.md` is explicit that the
runners cannot reach the machine, and
[`remain-capacity-0436.md`](../hardware-tests/remain-capacity-0436.md) opens with
"**Status: not run.**" The control-flow defects below were reproduced offline
against a synthetic `power_supply` tree and a fake EC reader, and the path
defect was read out of a committed checker. That is enough to show a control-flow
and a file-path property, and is **not** enough to say anything about what
`0x0436` holds. `XDATA_0436_PAIR` stays `present-untested`; §8's grading is still
a human's, and a dry run is not what it is waiting for.

## 1. The address→column mapping was unchecked

Every sample ran

```console
mapfile -t b < <($ECM read "${ADDRS[@]}" | cut -d= -f2)
```

and then filled `b[0]..b[7]` into design / full / current / `ec_u16` **by
position**. The only guard was `[ "${#b[@]}" -ne "${#ADDRS[@]}" ]`, a count.
`cut -d= -f2` throws the address away, so nothing in the script knew which
address a given value had come from.

That is correct today for a reason outside this file:
`ec/tools/ecmem.py`'s `read()` builds `{a: m[a] for a in addrs}` and Python dicts
keep insertion order, so the printed order matches the argument order. Nothing
held it. If `ecmem.py` ever sorted its output, renamed a key, or printed a
diagnostic, every column would rotate by one and the capture would be committed
under a header that reads correctly.

The failure is demonstrated, not asserted. Driven by a reader that answers the
same eight addresses one position out — against the synthetic `power_supply`
tree, so every value below is a fixture byte and none of it is a reading of this
EC — the script as it stood wrote this row to disk and exited 0:

```console
2026-10-03T15:18:26+00:00,baseline,0,Discharging,50,50000000,50000,1000000,12000000,0xde34,13534,13534000,48214,30738,61594
```

`ec_0402_design` is 30738 (`0x7812`) where the reader answered 0x1234,
`ec_0404_full` is 48214 where it answered 0x5678, and `ec_u16` is 13534 where it
answered 0xdef0. Every value is a byte the reader really did print for some
address, in a file whose header is correct, and the closing summary reported on
it without a murmur. This is the same class as #189 and #168: a silent wrong
answer that reads as a result.

**The fix** reads the whole `key=value` lines instead of cutting the keys away,
and compares each parsed key against the address that position asked for before
any column is filled. A mismatch refuses the run and names the index, the
expected address and the one received. The expected string is built once, next
to `ADDRS` and beside the existing `0x0400-0x045F` page bound check, and it is
the exact string `ecmem.py`'s `__main__` prints — its `f'{a:#06x}'` and the
script's `printf '%#06x'` agree, `0x0402` for `0x402`. Comparison is
case-insensitive so a case change in the reader's own format is not mistaken for
a rotation. This is the Linux counterpart of `ec_validate.py`'s in-code
`check_page`: a bound asserted in the tool rather than in the procedure prose.

The count guard stays and stays **first**. A short read says more about a line
that is not there at all than anything the key check could say, and the plan
named that ordering before the code was written.

## 2. §4's command did not reach §7's path

`docs/hardware-tests/remain-capacity-0436.md` §4 tells a human to run

```console
sudo linux/battery-trace/remain-capacity-probe <date>-0436-capacity.csv
```

The script `cd`s to the repository root on the way in and took `$1` literally,
so the bare name was created at the top of the tree. §7 promised the capture
lands under `evidence/ec-watch/` already named, "no rename step, and no second
file to reconcile" — and a human following §4 verbatim ends up with exactly the
stray CSV that sentence denies.

**This fixes the tool, not §4's command text**, and three reasons decided it, the
third being the one that did:

1. §4 is the invocation a Linux-only human runs. A doc-only fix repairs the
   command for whoever re-reads §4 after this lands; a tool-side fix repairs it
   for the person who typed it from the page as it stands.
2. **Nothing committed could have caught the doc-only version.**
   `tools/test_hardware_test_artifacts.py` holds a procedure's file list against
   its commands **on the basename only** —
   [`hardware-test-artifact-handoff.md`](hardware-test-artifact-handoff.md)
   records that as "the decision: normalise the prefix, not the command" — and
   running its parser over this procedure shows the single producer for
   `<date>-0436-capacity.csv` comes from §3's `--csv`. §4's bare token is not in a
   producer position at all, because `linux/battery-trace/remain-capacity-probe`
   does not match that checker's flag shape. **§4's destination directory was
   invisible to every check on the tree.** That is read out of the checker, not
   out of a run, and it is why this gap survived a write-up that looked for
   exactly it.
3. A tool-side change leaves §4's command tokens and §7's file list untouched, so
   that suite stays green without being edited. No capture depends on the old
   behaviour: §7's paragraph was already corrected, and nothing has been run.

The rule the tool now applies: an output name with no `/` resolves under
`evidence/ec-watch/`; anything carrying one is used as given, relative to the
repository root the script has already `cd`'d to. The resolved path is printed
before the first sample and repeated at the end, so a run says where it is
writing before it writes anything — which has to include the truncation, since
opening `$OUT` with `>` destroys whatever a previous run left at that name.

**Left out on the record, so review can disagree visibly:** the alternative is a
one-line rewrite of §4's command to carry `evidence/ec-watch/`. Nothing here
depends on the choice.

## 3. `charge_now` = `unknown` aborted the summary

`sample()` guards the value — a non-numeric `charge_now` is blanked and
`charge_mwh` is left empty — but the **summary** then read
`FIRST["$phase,charge_mwh"]` for a key the guard had deliberately never written.
Under `set -u` reading an element that was never written is fatal rather than
empty. Reproduced against the script as it stood, with a synthetic tree
publishing `unknown` for the whole run:

```console
linux/battery-trace/remain-capacity-probe: line 148: FIRST["$phase,$series"]: unbound variable
```

(the `line 148` is bash's own, in the summary block, and is not a pin — the
line moves with any edit and the failure does not.)

The capture was **complete and on disk** — every row of all three phases — and
the run died before its closing report. So a human loses the summary of a
capture they cannot re-take, and the file itself looks fine.

Had it survived, the answer would have been worse than the crash. `printf '%8d'`
on an empty operand prints `0 -> 0 (+0)` for a series no sample ever published —
a plausible-looking number for a series that does not exist, which is the failure
mode `CLAUDE.md`'s calibration rule is about.

**The fix** checks each series' first/last for presence before formatting it. A
series with no value prints as *not published this phase* and is skipped. Zero is
never substituted. The "nothing fell" verdict no longer claims "charge_mwh
included" when `charge_mwh` was not published in every phase, and it draws no
conclusion about whether the pack moved in the phases that have none to compare
against.

A partly-published `charge_mwh` turned up while checking the fix, and is the
reason the rule is "every phase" rather than "some phase". A driver that
publishes `charge_now` for baseline and `unknown` for the rest leaves a run
where `charge_mwh` exists and the summary said "nothing at all, charge_mwh
included" — calling two phases flat that had no reading to be flat. The verdict
now names the phases that published nothing, and separates the two ways it can
be incomplete: published in none, or published in some.

## 4. The summary heading asserted a premise it did not check

The block printed `moved down with charge_mwh:` whenever **any** series fell, and
only bailed out early when none did. So an `ec_u16` that fell while `charge_now`
stayed flat was listed under a heading asserting `charge_mwh` fell — and whether
the pair fell *with the pack* is the discrimination §8 grades on ("§5.2 says it
fell by a matching magnitude" against "the pair did not fall with the pack"). A
suite for this block that documented that line as-is would have been worse than
no suite.

The heading is now conditioned on `charge_mwh` itself having fallen. When it did
not, the block says so and lists what did. The wording stays in the script's
existing "reports rather than concludes" voice, and is scoped to the phases that
published the series, for the same reason as the verdict above.

The early `exit 0` on "nothing fell at all" — which is why no full-capacity bound
report appears in that case — is left exactly as it was, and a case pins it, so
it reads as chosen rather than accidental. The flat-run case asserts the two
absences that `exit 0` is what produces: that `(charge_mwh fell; no other series
did)` is absent and the bound report is absent. Neither the exit status nor the
verdict line distinguishes the early exit from the fall-through, so without those
two the property is described rather than held — deleting the one line makes
both red.

## The dry run

One mode, in the shape `probe-6005.py` established — a mode that opens no device
node and needs no root — but **opt-in rather than default**, which is the one
deliberate difference: a real run of this probe is `sudo` and ten minutes of
discharge by default, and a tool whose default were the harmless mode would be one
merge away from grading a capture nobody asked for. It opens no `/dev/mem`, needs
no root, writes no capture, and runs one sample per phase with no sleep. Flags are parsed
before the positional output path, and the two fixture flags are **refused
outside `--dry-run`** — a flag that could point a real run at something other than
this EC is not one to leave lying around.

| flag | meaning |
|---|---|
| `--dry-run` | no `/dev/mem`, no root, no file written, one sample per phase |
| `--sysfs-dir DIR` | `BAT0`/`AC0` come from `DIR` instead of `/sys/class/power_supply`, so the real `charge_now` guard is exercised rather than reimplemented |
| `--ec-reader CMD` | replaces `$ECM`, invoked with the same contract (`CMD read <addrs…>`), so a case can supply answers in any order |

Without `--ec-reader`, a dry run substitutes a built-in reader that prints one
distinguishable byte per address in argument order, so `--dry-run` alone is
useful to a human reviewing the columns. `--sysfs-dir` is made absolute
**before** the `cd "$(dirname "$0")/../.."`, so a relative fixture means what was
typed rather than what the repository root looks like; the output path is the
one resolved against the repository root the `cd` has already moved to, and is
made absolute there, so an argument that already carries a `/` is left alone.

**What the dry run substitutes, and what it does not.** It substitutes its
*inputs* — a fake reader and a fake `power_supply` tree — with the tool's own
parsing, guarding and formatting code running unmodified between them. It
**substitutes nothing about the values**: nothing is checked against anything
except that each column got the bytes from the address it names. A dry run is not
evidence about `0x0436`, and no case in the suite should be read as though it
were.

One thing the dry run deliberately does **not** do is write a file. A
`--dry-run`-with-output mode would make the CSV's header and append behaviour
testable at the file level, and it would break parity with the lightbar probe's
dry run. The file-level property is pinned directly instead, by a case that
asserts the script's own source text and says in its docstring that no offline
run can show it: the header is opened with `>` and rows go through `tee -a`, so
a re-run rewrites the capture rather than extending the one before it. That is
the opposite of `ec_validate.py --csv`, and §7 of the procedure states the
difference.

## Why the phase counts are a default and not a constant

The dry run takes one sample per phase, which means no phase can show a series
falling — the summary's arithmetic is per phase. So `BASELINE`, `DISCHARGE`,
`RECOVERY` and `STEP` are **defaults** in a dry run and an explicit environment
setting still wins over them. Without that, the block naming what fell is
unreachable offline, and the case for defect 4 would have nothing to run.

## What this does not claim

It proves the tool's own rules: that a column gets the bytes from the address it
names, that a rotated or overlong answer is refused, that a dry run writes
nothing, that a bare output name resolves where §7 says, and that the summary
reports an unpublished series, a partly-published one and a flat `charge_mwh` as
what they are.

It says nothing about `0x0436`/`0x0437`. Every defect here was found by reading
the script and by running it against fixtures, not by watching it behave on a
machine, and nothing in this write-up claims a hardware run.
`ec/annotations/registers.yaml` is untouched, `XDATA_0436_PAIR` stays
`present-untested`, and `docs/findings.md` §4g's `0x0436`/`0x0438` correction
stands where it is.
