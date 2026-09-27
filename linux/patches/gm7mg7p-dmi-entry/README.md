# gm7mg7p-dmi-entry

The prepared `uniwill-laptop` DMI entry for this board, for issue #10.

**No stage in this pipeline opens a pull request against
`Wer-Wolf/uniwill-laptop`.** CLAUDE.md's rule, and it is a rule rather than a
preference: the mission eventually means a PR there, and the deliverable for
that work is a patch and a description committed *here*, for a human to review
and submit themselves. Everything in this directory exists to be submitted by a
person.

## What is here

| file | what it is |
|---|---|
| `feature-map.csv` | the editable surface. One row per candidate feature, including the excluded ones, with the `registers.yaml` status and a reason per row |
| `PR_DESCRIPTION.md` | the upstream PR body, verbatim as a human pastes it |
| `uniwill-acpi-dm-gm7mg7p.patch` | **not written.** See below |
| `../../../../tools/check_dmi_descriptor.py` | the checker that holds all of the above to the evidence |

`feature-map.csv` is the source of truth and the thing to edit. The map is a
CSV rather than prose for the reason the rest of this repository keeps
structured sources in machine-readable files: `tools/check_dmi_descriptor.py`
reads it, and a claim that is prose cannot be checked against
`ec/annotations/registers.yaml`.

## The patch is missing, and that is the state this directory is in

The patch is the one deliverable here that needs the network. It is a diff
against `uniwill-acpi.c` at `BASE_COMMIT`, and **the driver source is not
vendored in this repository** — `linux/patches/` holds a patch and a
`BASE_COMMIT`, nothing else. The `curl` that would have fetched it was refused
in the environment this was written in, so the bit names, the struct field
names and the table row syntax could not be read off the real file.

**They were not written from memory, and that is the point.** The plan for this
issue is explicit that a plausible-looking bit name is the exact overclaim
CLAUDE.md's calibration rule exists to prevent, and a patch that applies
cleanly with invented constants is the worst artifact this repository could
ship: it would pass every mechanical check here and be wrong on hardware.

This is not a new wall. `ec/annotations/static-refs-audit.md` hit it already,
for the same reason, on the same missing file: `PRIMARY_FAN`/`SECONDARY_FAN`,
`TOUCHPAD_TOGGLE` and `USB_POWERSHARE` have no EC address recorded anywhere in
this repository, and that file's recorded answer was to leave the cells out and
name the features rather than invent addresses. This directory does the same,
and says so in every row that is affected.

`python3 tools/check_dmi_descriptor.py --check` **exits non-zero on the
committed tree, and that is correct.** It is red because the patch is absent,
not because a claim is wrong; the refusal text names the file. Every rule that
does not need the patch ran, and its results stand. A checker that passed while
the artifact it exists to police is incomplete would be the failure mode
`tools/run-tests.sh` refuses in its own empty-discovery guard.

## Producing the patch

```sh
curl -fsSL -o /tmp/uw.tar.gz \
  https://codeload.github.com/Wer-Wolf/uniwill-laptop/tar.gz/5a24248f6422a0b673a47cbfd65e19a98eb4c8a9
tar xzf /tmp/uw.tar.gz -C /tmp
```

`5a24248` is `linux/patches/BASE_COMMIT`, and the same rev is what
`linux/nix/uniwill-laptop.nix` fetches — the checker's rule 3 compares all
three, so a patch cut against anything else is a red run.

Then, from `/tmp/uniwill-laptop-5a24248f6422a0b673a47cbfd65e19a98eb4c8a9`:

1. Read the `UNIWILL_FEATURE_*` enum and the `uniwill_dmi[]` table out of
   `uniwill-acpi.c`. **Do not take them from this repository's prose** — the
   names in `ec/annotations/registers.yaml` are *this* repository's, and only
   two of them map onto upstream's spellings.
2. Add the row. One row, additive: nothing already in the table may be edited,
   and the checker's rule 4 refuses a patch that removes a line. That rule is
   the guard for every *other* Uniwill board in the table, and it is the one
   `git apply --check` waves straight through.
3. Give the patch a `#` header naming the base rev, the way the patches in
   `docs/ci/` do. Rule 3 reads the rev out of it; the existing
   `linux/patches/uniwill-laptop-force_charge_limit.patch` has no header at all,
   so there is no precedent to copy from *in this directory*.
4. Fill each `unsourced` cell in `feature-map.csv` with the real spelling and
   set its `bit_source` to `upstream@5a24248`. Then flip `in_descriptor` to
   `yes` for the ones whose `registers.yaml` status is `confirmed-*` and whose
   address is recorded. Rule 6 enforces that, so the flip cannot outrun the
   evidence.
5. `git apply --check` the result against the pristine tree, and record the
   command in `PR_DESCRIPTION.md` rather than asserting it anywhere that runs
   without the network.

## Before you submit

- [ ] The patch exists, is additive, and is cut against `BASE_COMMIT`.
- [ ] `python3 tools/check_dmi_descriptor.py --check` exits 0.
- [ ] The `unsourced` cells are either filled from the real source or still
      say `unsourced` **with the reason that is still true**. Do not fill one
      from memory to make the count look better.
- [ ] The keyboard-backrightness question is settled or is still worded as
      open. It is the one row where a human with the machine can change the
      answer, and `PR_DESCRIPTION.md` currently excludes it.
- [ ] Nothing in this repository has been pushed to `Wer-Wolf/uniwill-laptop`,
      and the submitter is a person.

## What the map is held to

Every `registers_status` in `feature-map.csv` is a value the header comment of
`ec/annotations/registers.yaml` itself declares. The checker parses that
comment rather than carrying its own copy of the list, for the reason
`ec/tools/check_status_vocabulary.py` makes about not having a second copy:
two lists drift apart silently, and a list nothing checks is a list nothing
keeps true. A status typed into the map by hand and left behind by a later
`registers.yaml` edit is a red run rather than a wrong descriptor.

The map is **read-only with respect to status**. It packages statuses already
recorded; it does not change any. If a row shows a status that ought to
change, that is a follow-up issue with its own evidence, not an edit here —
which also keeps a branch that *does* edit one from colliding with this.
