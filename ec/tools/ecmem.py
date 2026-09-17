#!/usr/bin/env python3
"""Read/write EC RAM through the memory-mapped ECMG window (physical 0xFE410000).

This is the same path the vendor's ACPIDriver.sys ECRW method takes
(docs/findings.md 4e: MMRW(0xFE410000 + Arg0, ...)), so a write here lands
exactly where Windows' own writes land. Needs root and CONFIG_DEVMEM; on
this machine the window is listed under INTC1036:00 in /proc/iomem and
/dev/mem access to it works despite IO_STRICT_DEVMEM (2026-09-17, 7.2.6).
Reads were cross-checked against the uniwill-laptop regmap debugfs dump
for 0x43E/0x44F/0x456/0x7A6/0x7B9/0x7CC/0x7E2 before the first write.

Usage:
  ecmem.py read 0x7b9 [0x7d0 ...]
  ecmem.py write 0x7b9=60 0x7d0=55
Values are one byte. Reads back after each write and prints both.
"""
import mmap
import os
import sys

BASE = 0xFE410000
SIZE = 0x10000


def _map(write=False):
    fd = os.open('/dev/mem', (os.O_RDWR if write else os.O_RDONLY) | os.O_SYNC)
    prot = mmap.PROT_READ | (mmap.PROT_WRITE if write else 0)
    return mmap.mmap(fd, SIZE, mmap.MAP_SHARED, prot, offset=BASE)


def read(addrs):
    m = _map()
    return {a: m[a] for a in addrs}


def write(pairs):
    m = _map(write=True)
    out = {}
    for a, v in pairs:
        before = m[a]
        m[a] = v
        out[a] = (before, v, m[a])
    return out


if __name__ == '__main__':
    if len(sys.argv) < 3 or sys.argv[1] not in ('read', 'write'):
        sys.exit(__doc__)
    if sys.argv[1] == 'read':
        for a, v in read([int(x, 0) for x in sys.argv[2:]]).items():
            print(f'{a:#06x}={v:#04x}')
    else:
        pairs = [(int(k, 0), int(v, 0))
                 for k, v in (x.split('=') for x in sys.argv[2:])]
        for a, (b, w, r) in write(pairs).items():
            print(f'{a:#06x}: was {b:#04x} wrote {w:#04x} readback {r:#04x}')
