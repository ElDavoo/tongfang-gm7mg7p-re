# Mission

## Functional goal

Unlock everything the BIOS and the EC on this machine have to offer, and
write the interface for it — a Linux kernel driver (either an addition to
upstream `uniwill-laptop`, or a new driver where that's the wrong fit, e.g.
`ite_8291_lb` for the lightbar). Where feasible, unlock hidden/locked BIOS
setup menus too.

## Technical goal (what achieving the functional goal requires)

Complete reverse engineering of all three closed-source components in the
stack: the Windows userspace driver/service (`GCUService.exe` and friends),
the BIOS/UEFI firmware, and the EC firmware. `docs/findings.md` is the
running record of what that's turned up so far; `ec/annotations/registers.yaml`
is the register-level detail.

For the EC, "complete" has a concrete end state: **a C codebase that mirrors
the EC firmware function for function** — decompiled from
`ec/firmware/GMxMGxx_11.800`, symbolized from `registers.yaml`, every function
cited back to its bank and address. The vendor's original source is not
available; this is its reconstruction, and annotated disassembly is a step
towards it, not a substitute. Ghidra's 8051 decompiler is the starting point
(issue #20, `ec/ghidra/README.md`), and that project now exists: the EC's
three programs are imported, seeded and exported to `ec/decompiled/`, with
`ec/annotations/ghidra-functions.csv` as the layer that keeps improving it.
`.github/actions/project-setup` installs the toolchain for every agent run.

## What "done" looks like, incrementally

There is no single PR that finishes this. Progress looks like: one more
register's real behaviour confirmed, one more Windows class decrypted, one
more BIOS menu entry understood, one more upstream contribution opened. The
GitHub issue tracker is the actual work queue — `docs/findings.md` §5 and
the open issues at any time are a better answer to "what's left" than this
file, which won't be kept in lockstep with either.

## Standing constraints this implies for automated work

- **Cloud agents cannot touch the physical laptop or a Windows machine.**
  Issues labelled `needs-hardware-test` or `windows` still get planned and
  implemented, but the deliverable is the *preparation* — a script, a
  documented procedure, a static analysis — never a claimed test result.
  Running it and recording what happened is a human step, every time. See
  `CLAUDE.md`.
- **Static analysis is not proof.** `docs/findings.md` §4 records two cases
  where confident conclusions from static evidence alone (a resting
  voltage, a zero-reference static scan) were wrong. Anything written here
  or in an issue/PR should carry the same calibration: cite the evidence
  file, name the method's blind spots, don't upgrade "not found" to
  "absent" or "accepted" to "works."
- **The backlog should not run dry.** `.github/workflows/agent-followups.yml`
  reads each merged PR against this file and the open issue list, and opens
  whatever follow-up work it reveals — so finishing one issue is expected
  to produce zero or more new ones, not to shrink the queue to nothing
  while the mission above is still open.
