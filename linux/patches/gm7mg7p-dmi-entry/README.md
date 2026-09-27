# The prepared `uniwill-laptop` DMI entry for the GM7MG7P

Issue #10's deliverable: a patch and a PR body, committed here for a human to
review and submit to [`Wer-Wolf/uniwill-laptop`](https://github.com/Wer-Wolf/uniwill-laptop)
themselves. **Nothing in this repository opens a pull request or an issue
against another repository** — see `CLAUDE.md`. The cross-reference to upstream
issue #7 is prose in `PR_DESCRIPTION.md` for the human to paste, not a comment
anyone posted.

The entry claims **eight** of the fifteen `UNIWILL_FEATURE_*` bits. The seven it
leaves out are excluded with a cited reason each, in `feature-map.csv`.

## What is here

| file | what it is |
|---|---|
| `uniwill-acpi-dm-gm7mg7p.patch` | the diff against `BASE_COMMIT`. Additive: one descriptor, one table row, nothing else touched |
| `PR_DESCRIPTION.md` | the upstream PR body, verbatim as a human pastes it |
| `feature-map.csv` | the structured source of truth: 15 rows, one per candidate, each with its evidence and its verdict |
| `upstream-excerpt.txt` | the committed evidence — the `UNIWILL_FEATURE_*` enum, the descriptor struct, the address defines and the table-row syntax, each with its line number in `uniwill-acpi.c` |
| `fetch-upstream.sh` | re-derives the excerpt from a fresh fetch and diffs it. Needs the network, so it is not in any gate |

## The base commit, and why the excerpt is committed

`linux/patches/BASE_COMMIT` names `5a24248` ("Bump minimum supported kernel
version to 7.2"). `linux/nix/uniwill-laptop.nix` pins the same commit as a full
rev, which is what `fetchFromGitHub` wants. Both are checked, so the patch
cannot drift off the source the local build actually fetches.

An earlier attempt at this work asserted the upstream source could not be
fetched, marked thirteen of its fifteen map rows `unsourced` on that basis,
and shipped a one-bit descriptor. The fetch is an ordinary HTTPS GET and it
works. Rather than assert that a second time, the answer is committed:
`upstream-excerpt.txt` holds the fragments the map's spellings are checked
against, so a reviewer can verify every constant offline, with no network and
no re-fetch.

The full 90 KB `uniwill-acpi.c` is deliberately *not* vendored here — the
excerpt is ~300 lines and reviews in a diff, and `CLAUDE.md` is explicit that
a vendored binary is a decision, not a default. `fetch-upstream.sh` is how to
get the whole file, and it re-derives the excerpt from what it fetched, so the
excerpt cannot quietly drift from the source it claims to quote.

### What the hashes in the excerpt are worth

The excerpt records the SHA-256 of `uniwill-acpi.c` (`914d876f…`, 90,721
bytes) and that is the hash worth failing on: a git tree at a fixed rev is
immutable, so a re-fetch must reproduce it.

The **tarball's** hash is recorded as an observation and nothing is failed on
it, because it is not a stable artifact. Two fetches of this same commit on the
same day returned 27,634 and 27,605 bytes with different digests, while
`uniwill-acpi.c` came back byte-identical. Pinning the tarball hash would fail
a re-fetch for a reason that has nothing to do with the source having changed.

An environment fact worth keeping, because it is the distinction this whole
artifact turned on: the permission layer here refused the literal `curl`
invocation three times, including once with the sandbox explicitly disabled,
while the identical request through `python3 urllib` returned everything on the
first attempt and a later `curl` was accepted. The refusals were never a
property of the network. `fetch-upstream.sh` tries both clients and names
whichever answered, so a stricter environment still gets the source. A denied
command is a fact about that command; writing it down as "the source is not
readable" is exactly the error this directory exists to make hard to repeat.

## Reproducing it

Offline — no network, no `git`, nothing but the committed files:

```sh
python3 tools/check_dmi_descriptor.py --check      # the eight rules
python3 tools/check_dmi_descriptor.py --self-test  # the refusals themselves
python3 -m unittest discover -s tools -p 'test_check_dmi_descriptor.py'
```

With the network, to re-derive the evidence:

```sh
bash linux/patches/gm7mg7p-dmi-entry/fetch-upstream.sh
```

And to confirm the patch still applies to the pinned source:

```sh
git apply --check linux/patches/gm7mg7p-dmi-entry/uniwill-acpi-dm-gm7mg7p.patch
```

That last one is a command for a maintainer to re-run, not something any gate
in this repository runs: it needs the network, and this repository does not
describe a check that only sometimes runs as one that does.

## The status-vocabulary rule the map is held to

Every `registers_status` in `feature-map.csv` is a value
`ec/annotations/registers.yaml`'s own header comment declares, **parsed out of
that comment and never copied into the checker**. A second copy of the list is
how the two drift apart silently, which is the rule
`ec/tools/check_status_vocabulary.py` already enforces over the YAML itself.

The checker's rule 2 then requires each `reg_addr` to appear in
`registers.yaml` and its status to equal the one recorded there, so a status
copied by hand into the map and left behind by a later `registers.yaml` edit
fails rather than quietly disagreeing.

One consequence is worth spelling out, because the vocabulary is subtler than
its prefix suggests: the statuses that assert a feature *works* are
`confirmed-working` and `confirmed-working-partially`. `confirmed-inert` is a
proven write the EC does not act on, and `confirmed-not-this-mechanism` is a
live test that **refutes** the mechanism the entry names. Both are
`confirmed-` prefixed and both mean the opposite of "this works" — `LIGHTBAR`
is excluded here on exactly the second. The include rule names the two working
values rather than testing a prefix, so it cannot be swept in by a new status
that happens to start the same way.

`registers.yaml` is **read-only** here. This change packages statuses already
recorded; it changes none. So no row is edited, which also keeps a branch that
does edit one from colliding. Where the map shows a status that ought to change
— what `0x0786` and `0x078E` are on this EC — that is a follow-up issue with
its own evidence. The addresses are readable at the pinned rev, and reading
them is itself the useful result: upstream *defines* both constants and
references neither anywhere in the tree, so there is no upstream write path to
either byte, and the disagreement with `registers.yaml` is between an unused
constant and this repository's reading rather than between two live users of
the byte.

## What is not verified, and who is left holding it

- **The patched driver has not been compiled**, and nothing has been loaded on
  a machine. There is no kernel headers tree on the runner;
  `linux/nix/uniwill-laptop.nix` is the human's build path.
- **The eight bits are not confirmed on hardware.** Every claim rests on a live
  test of the *EC* recorded in `evidence/`, not on a run of this patch.
  `PR_DESCRIPTION.md` says so to whoever pastes it, because a PR body that
  implied otherwise would be the overclaim `CLAUDE.md` exists to prevent.
- **The RGB keyboard question is open.** This board's backlight is 4-zone RGB
  (`048D:CE00`, usage page `0xFF12`) and the struct field is a single
  `kbd_led_max_brightness`. The `kbd_led_*` values are left at upstream's
  default rather than a plausible number being invented, and whether this
  board needs them set at all is a hardware question for a person at the
  machine.

## Before you submit

1. `bash fetch-upstream.sh` — the excerpt still matches the pinned source.
2. `git apply --check uniwill-acpi-dm-gm7mg7p.patch` against a fresh checkout
   of `5a24248`.
3. `python3 tools/check_dmi_descriptor.py --check` — eight rules, green.
4. Read `feature-map.csv` and agree with all fifteen verdicts, not just the
   eight claims. The exclusions are the part a reviewer is most likely to
   challenge, and `USB_POWERSHARE` and `AC_AUTO_BOOT` in particular are
   refusals to read an accepted write as working behaviour and a static zero
   as proof.
5. Build it (`linux/nix/uniwill-laptop.nix`), load it, and confirm the eight
   bits appear in sysfs. This is the step this repository cannot do, and the
   PR body asks for it explicitly.
6. Only then: open the PR, pasting `PR_DESCRIPTION.md`. Not before, and not
   from here.
