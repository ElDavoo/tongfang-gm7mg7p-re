#!/usr/bin/env python3
r"""Issue #8: does the EC's cTGP/DynamicBoost block (0x0743-0x0746) actually
move the dGPU's enforced power limit? Read-modify-restore, values kept within
the GPU's own reported max_limit."""
import subprocess, sys, time
from ecrw import Ec  # run from windows/tools/, next to ecrw.py

SMI = r"C:\Windows\System32\nvidia-smi.exe"

def enforced():
    out = subprocess.check_output(
        [SMI, "--query-gpu=enforced.power.limit,power.default_limit,power.max_limit",
         "--format=csv,noheader,nounits"], text=True).strip()
    return out

def show(ec, tag):
    regs = " ".join(f"{a:04X}={ec.read(a):02X}" for a in (0x0743, 0x0744, 0x0745, 0x0746))
    print(f"  {tag}: EC[{regs}]  enforced/default/max = {enforced()} W")

def hold(ec, tag, secs=8):
    t0 = time.time()
    last = None
    while time.time() - t0 < secs:
        e = enforced()
        if e != last:
            print(f"    +{time.time()-t0:4.1f}s enforced/default/max = {e} W")
            last = e
        time.sleep(0.5)

def main():
    ec = Ec()
    o43, o44, o46 = ec.read(0x0743), ec.read(0x0744), ec.read(0x0746)
    print(f"baseline 0x0743=0x{o43:02X} 0x0744=0x{o44:02X} 0x0746=0x{o46:02X}")
    show(ec, "start")
    try:
        # 1) DynamicBoost max 5 -> 0: expect enforced to drop toward default (115).
        print("\n[1] set 0x0746 (DB max) = 0")
        ec.write(0x0746, 0x00); hold(ec, "db0")
        show(ec, "after DB=0")
        ec.write(0x0746, o46); time.sleep(2); show(ec, "restored DB")

        # 2) enable cTGP (0x0743 bit2) with offset 0x0744 already 0x0A: expect
        #    enforced toward default+10 = 125, within max 140.
        print("\n[2] set 0x0743 bit2 (cTGP enable), offset 0x0744 =", hex(o44))
        ec.write(0x0743, o43 | 0x04); hold(ec, "ctgp")
        show(ec, "after cTGP on")
    finally:
        ec.write(0x0743, o43); ec.write(0x0744, o44); ec.write(0x0746, o46)
        time.sleep(2); show(ec, "final restore")

if __name__ == "__main__":
    main()
