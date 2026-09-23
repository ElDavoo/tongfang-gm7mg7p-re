# tongfang-gm7mg7p-re

Reverse-engineering notes, tools, and vendor artifacts for the embedded
controller and RGB/battery subsystems of a PCSpecialist-branded TongFang
**GM7MG7P** (Uniwill platform **GM5MG7Y**), toward:

1. A correct DMI descriptor / feature list for upstream
   [`uniwill-laptop`](https://github.com/Wer-Wolf/uniwill-laptop) (this board
   isn't in its match table).
2. Resolving a real discrepancy: Windows caps battery charging on this
   machine, Linux currently doesn't, and the reason turned out to be more
   specific than "unsupported register" — see `docs/findings.md`.
3. Getting the lightbar working under Linux, which turned out to need a
   different driver (`ite_8291_lb`) rather than a fix to `uniwill-laptop`.

**Start here:** [`docs/findings.md`](docs/findings.md) — the full narrative,
written to include the two points where an earlier conclusion turned out to
be wrong and why, not just the parts that held up. Other people have
reverse-engineered sibling Uniwill boards (HydroControl, mech-forza-control,
w568w's charge-limit fix). [`docs/related-projects.md`](docs/related-projects.md)
says what each found and which of it holds on this machine.

## Mission

Those three items are where the work started. The goal they sit under is
bigger ([`docs/MISSION.md`](docs/MISSION.md) is the canonical copy):

- **Functional:** unlock everything the BIOS and the EC on this machine have
  to offer, and write the Linux interface for it: a kernel driver, either an
  addition to upstream `uniwill-laptop` or a new driver where that's the
  wrong fit (like `ite_8291_lb` for the lightbar). Where feasible, unlock
  hidden/locked BIOS setup menus too.
- **Technical:** that requires complete reverse engineering of all three
  closed-source components in the stack: the Windows userspace service
  (`GCUService.exe` and friends), the BIOS/UEFI firmware, and the EC
  firmware. For the EC, the end state is a C codebase that mirrors the
  firmware function for function: decompiled, symbolized from
  `registers.yaml`, and cited back to bank and address. It's a
  reconstruction, since the vendor's source isn't available. That
  reconstruction is under way: `ec/ghidra/README.md` has the committed
  Ghidra project, 2,676 decompiled functions, and the annotation layer that
  improves them (issue #20).

No single change finishes it. Progress is one more register's behaviour
confirmed, one more Windows class decrypted, one more BIOS menu entry
understood, one more upstream contribution prepared. The
[issue tracker](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues) is the
work queue.

## Automation

Issues here run through [`agent-pipeline`](https://github.com/ElDavoo/agent-pipeline):
file an issue, get a planned, implemented, reviewed, CI-passing pull
request without clicking anything in between. Agents run on GitHub-hosted
runners with no access to the laptop or to Windows, so hardware and Windows
issues come back as prepared scripts and procedures for a human to run,
never as claimed results. `docs/agent-pipeline.md` covers what's specific
to this copy. Issue and pull request creation is limited to collaborators,
and anything filed by someone without write access waits for the owner's
approval before an agent reads it.

Every merged pull request is also read against `docs/MISSION.md` and the
open issue list by `.github/workflows/agent-followups.yml`, which opens
whatever follow-up work it reveals — the queue is meant to keep refilling
itself rather than running dry while the mission is incomplete.

## Layout

```
docs/                    findings.md (start here), hardware-identity.md,
                          related-projects.md (other Uniwill RE work),
                          hardware-tests/ (procedures written for a human at
                          the machine to run -- never run by the pipeline)
ec/                       EC firmware (ITE 8051, banked), disassembly tools,
                          the register cross-reference (annotations/registers.yaml)
windows/                  Decompiled vendor Windows service, anti-tamper notes,
                          extraction pipeline
bios/                     BIOS 1.09 Setup IFR and decompiled vendor Oem* modules,
                          regenerated from vendor/ by bios/tools/bios_extract.py
linux/                    uniwill-laptop patch, NixOS module config, battery
                          tracing scripts used to gather the evidence below
vendor/                   Vendor binaries as shipped (BIOS/EC update package,
                          three Control Center versions) -- inputs, not outputs
evidence/                 Traces, screenshots, ACPI dump, HID report descriptors
                          that specific claims in docs/findings.md cite
```

## Quick facts

See `docs/hardware-identity.md` for the full table. Short version: Uniwill
`PROJECT_ID_CML_GAMING` (0x0F), ITE EC firmware `V14.6`, two ITE 8291 HID
RGB controllers on different USB ports (one claimed by the kernel, one not).

## Status

Research/scaffolding stage — see the GitHub issue tracker for concrete next
steps. Issues tagged `windows` need to run vendor code under Windows (a VM
is enough for the anti-tamper work); everything else is doable from Linux
with the tools already in `ec/tools/` and `windows/tools/`.

## A note on the vendor files in `vendor/`

These are the vendor's own BIOS/EC update package and Control Center
installers, kept here (this repo is private) so every claim in
`docs/findings.md` and `ec/annotations/registers.yaml` is independently
re-derivable from a committed input, not just from an unrepeatable analysis
session. They are not redistributed anywhere from here; if any of this work
is later cited in a public upstream PR, cite it by the specific evidence
(register addresses, firmware offsets, register names) rather than by
linking these binaries.
