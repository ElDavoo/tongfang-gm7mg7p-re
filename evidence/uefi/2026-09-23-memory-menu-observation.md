# Memory Overclocking Menu unlock — human observation

Physical GM7MG7P, Windows 11, BIOS `N.1.09A08`, Control Center 3.1.39.0.
Machine log: `2026-09-23-MemoryOverClockSwitch-set.txt`.
Before/after variable dumps: `2026-09-23-UniWillVariable-before-memoc.bin`,
`2026-09-23-UniWillVariable-after-memoc.bin`.
Tool: `../../windows/tools/uniwill_set.py`. Analysis: `../../docs/findings.md` §7.

## What was changed

On 2026-09-23 the owner asked for the NVRAM byte to be set to 1. From an
elevated prompt, `uniwill_set.py set MemoryOverClockSwitch 1` changed
`UniWillVariable` offset 0x33 from 0x00 to 0x01. The attributes stayed
NV|BS|RT, and the readback matched. `cmp` of the two dumps differs at that
byte only. `MemoryOverClockSupport` (0x60) was deliberately left at 0 (see
findings §7 for why). Nothing else was written, and no Setup, CpuSetup or
SaSetup variable was touched from the OS.

The owner was asked to reboot without touching Control Center first, enter
BIOS setup, and look on the Advanced page for a "Memory" entry.

## Human observation after the reboot

The owner replied:

> yes it worked

Read in context ("it" being the instruction to look for the entry), this is
the observation that the "Memory" entry appeared on the Advanced page. It
is the live confirmation of the static chain
in findings §7: `UniWillVariable.MemoryOverClockSwitch` → `OemOcDxe` →
`Setup[0x7D7]` → the suppress-if around the vendor Advanced page's link to
the Memory Overclocking Menu.

## Scope

Confirmed: the menu link becomes visible after this one-byte change and a
reboot, with the BIOS's other settings as they were (in particular,
CpuSetup "OverClocking Feature" was evidently non-zero, since the link is
also suppressed when it is 0).

Not established: which options the menu shows on this machine (for example
whether "XMP profile 1/2" are offered, which depends on the fitted DIMMs'
SPD); whether any setting changed in the menu is honoured by memory
training on the i7-10875H; what `OemOcDxe`'s GPP_B22 write does on this
board; and whether the vendor service later writes 0x33 back to 0. No
screenshot or photo was taken, and whether anything inside the menu was
changed was not reported.
