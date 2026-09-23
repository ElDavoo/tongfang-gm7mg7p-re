/*
 * OemOcDxe (BIOS 1.09, DXE, x64): hand-annotated from the unedited Ghidra
 * output in OemOcDxe.c next to this file. Function addresses are the RVAs
 * there. Variable offsets are resolved against:
 *   - UniWillVariable: windows/decompiled/v3.1.39.0/GCUService/MyControlCenter/NVRAM_STRUCT.cs
 *     (180 bytes, the layout windows/tools/uefi_var.py decodes)
 *   - CpuSetup (0x2BB bytes) and Setup (0x7D8 bytes): bios/ifr/Setup.en-US.ifr.txt
 * The C below restates what the decompile does with names attached. It is
 * not the vendor's source; anything marked "inferred" is a reading, not a
 * fact taken from the binary.
 *
 * What this module decides on every boot:
 *   1. EC 0x0741 bit 7 set  -> overclocking recovery: turn CpuSetup's
 *      "OverClocking Feature" off, raise UniWillVariable.OverClockRecoveryFlag,
 *      clear the EC bit.
 *   2. otherwise            -> copy UniWillVariable.MemoryOverClockSwitch into
 *      Setup[0x7D7], which is the byte that un-suppresses the "Memory"
 *      (Memory Overclocking Menu) link on the vendor Advanced page; if the
 *      switch is 1 and OC is enabled, drive PCH pad GPP_B22's TX state high;
 *      and copy the Control Center's CPU core-voltage values into CpuSetup.
 */

/* ---- EC access (FUN_00000f38 / FUN_00000dd4 / FUN_00000e4c / FUN_00000ed4) ----
 * ACPI EC ports: command/status 0x66, data 0x62 (the helpers take 'b' = 0x62;
 * '`' = 0x60 would select the KBC pair 0x64/0x60). Each command waits for
 * IBF=0, drains OBF, writes the command to 0x66, and optionally a data byte
 * to 0x62. The vendor commands used here are:
 *   0xA3 <hi>   0xA2 <lo>   -> set EC RAM address (inferred)
 *   0xA4        -> read the byte at that address from 0x62 (inferred)
 *   0xA5 <val>  -> write it (inferred)
 * "Inferred" because the command semantics come from use, not from the EC
 * side: OemUniWillVariableDxe (FUN_0000084c) uses the same 0xA3 07 / 0xA2 lo
 * / 0xA4 sequence to fill UniWillVariable.ProjectID from lo = 0x40, i.e. EC
 * 0x0740, which is the confirmed PROJECT_ID register
 * (ec/annotations/registers.yaml).
 */
static EFI_STATUS EcRead0741 (UINT8 *Data);   /* 0xA3 07, 0xA2 41, 0xA4, read 0x62 */
static EFI_STATUS EcWrite0741 (UINT8 Data);   /* 0xA3 07, 0xA2 41, 0xA5 Data     */

#define EC_0741_OC_RECOVERY   BIT7   /* bit 0 of the same byte is "AP exist" */

/* ---- entry (0x3D0) -> library constructors (0x3EC) -> OemOcDxeMain (0x4F8) ---- */
EFI_STATUS OemOcDxeMain (VOID)                                        /* 0x4F8 */
{
  UINT8 Ec0741;   /* decompile: seeded from the low byte of ImageHandle and only
                     overwritten if the EC read succeeds, so a failed read tests
                     an uninitialised value (as decompiled; not observed) */

  gRT = gST->RuntimeServices;
  EcRead0741 (&Ec0741);
  if (Ec0741 & EC_0741_OC_RECOVERY) {
    OcRecovery ();                                                    /* 0x67C */
    EcWrite0741 (Ec0741 & 0x7F);
  } else {
    SyncOcVariables ();                                               /* 0x7A8 */
  }
  return EFI_SUCCESS;
}

/* ---- 0x67C ---- */
static VOID OcRecovery (VOID)
{
  CPU_SETUP        CpuSetup;      /* 0x2BB bytes, gCpuSetupGuid b08f97ff-... */
  NVRAM_STRUCT     Uwv;           /* 0xB4 bytes, UniWillVariable 9f33f85c-... */

  gRT->GetVariable (L"CpuSetup", &gCpuSetupGuid, &Attr1, &Size1, &CpuSetup);
  gRT->GetVariable (L"UniWillVariable", &gUniWillGuid, &Attr2, &Size2, &Uwv);
  Uwv.OverClockRecoveryFlag      = 1;   /* +0x5C; GCUService shows a notice and clears it */
  CpuSetup.OverclockingSupport   = 0;   /* +0x1B7 "OverClocking Feature" */
  gRT->SetVariable (L"CpuSetup", ...);
  gRT->SetVariable (L"UniWillVariable", ...);
}

/* ---- 0x7A8 ---- */
static VOID SyncOcVariables (VOID)
{
  CPU_SETUP     CpuSetup;         /* 0x2BB */
  NVRAM_STRUCT  Uwv;              /* 0xB4  */
  SETUP_DATA    Setup;            /* 0x7D8, gSetupGuid ec87d643-... */

  gRT->GetVariable (L"CpuSetup", ...);
  gRT->GetVariable (L"UniWillVariable", ...);
  gRT->GetVariable (L"Setup", ...);

  /* The menu gate. Setup[0x7D7] is question 0xEC6 in the IFR; the vendor
   * Advanced form 0x2712 shows Ref "Memory" -> form 0x27B1 "Memory
   * Overclocking Menu" only when 0xEC6 == 1 and CpuSetup[0x1B7] != 0. */
  Setup.Oem7D7 = Uwv.MemoryOverClockSwitch;                          /* +0x33 */

  if (Uwv.MemoryOverClockSwitch == 1) {
    MemOcGpio ();                                                     /* 0x5D8 */
  }

  if (Uwv.ApExistFlag == 1) {                                        /* +0x5D */
    /* Control Center's CPU core-voltage values -> Intel OC knobs */
    switch (Uwv.ICpuCoreVoltageOffsetRangeType) {                    /* +0x66 */
    case 0:  CpuSetup.CoreVoltageOffsetPrefix = 0;                    /* +0x1BF */
             CpuSetup.CoreVoltageOffset = Uwv.ICpuCoreVoltageOffsetValue;        /* +0x1BD <- +0x3A */
             break;
    case 1:  CpuSetup.CoreVoltageOffsetPrefix = 1;
             CpuSetup.CoreVoltageOffset = Uwv.ICpuCoreVoltageOffsetNegativeValue; /* <- +0x64 */
             break;
    case 2:  if (Uwv.ICpuCoreVoltageOffsetNegativeValue == 0) {
               CpuSetup.CoreVoltageOffsetPrefix = 0;
               CpuSetup.CoreVoltageOffset = Uwv.ICpuCoreVoltageOffsetValue;
             } else {
               CpuSetup.CoreVoltageOffsetPrefix = 1;
               CpuSetup.CoreVoltageOffset = Uwv.ICpuCoreVoltageOffsetNegativeValue;
             }
             break;
    }
    CpuSetup.CoreVoltage = Uwv.ICpuCoreVoltageValue;   /* +0x1C0 "Core Voltage" <- +0x34
                                                          (set in all three cases) */
  }

  /* Ranges the service reads back as its slider limits. Written as two
   * 32-bit stores, so the adjacent minimums become 0. Matches the live
   * dumps in evidence/uefi/ (0x36 = 0x07D0, 0x3C = 0x0064). */
  Uwv.ICpuCoreVoltageMaximum       = 2000;  Uwv.ICpuCoreVoltageMinimum       = 0;
  Uwv.ICpuCoreVoltageOffsetMaximum = 100;   Uwv.ICpuCoreVoltageOffsetMinimum = 0;

  gRT->SetVariable (L"Setup", ...);
  gRT->SetVariable (L"CpuSetup", ...);
  gRT->SetVariable (L"UniWillVariable", ...);
}

/* ---- 0x5D8: only when MemoryOverClockSwitch == 1 ----
 * The tables at RVA 0x1550 (17 entries) and 0x1750 (15 entries) are Intel's
 * GPIO_GROUP_INFO for CNL/CML-H and -LP PCHs (0x1E bytes each: PID, PadOwn,
 * HostOwn, GpiIs, GpiIe, GpiGpeSts, GpiGpeEn, SmiSts, SmiEn, NmiSts, NmiEn,
 * PadCfgLock, PadCfgLockTx, PadCfgOffset, PadPerGroup). The H/LP choice
 * (0x1100) is the 00:1F.0 device ID: 0x068x/0xA30x -> H, 0x028x/0x9D8x -> LP.
 * Group 1 of the H table is PID 0x6E, PadCfg 0x790, 26 pads: GPP_B.
 * PCR MMIO is 0xFD000000 | PID << 16 | offset (SBREG_BAR); the TX-lock
 * change goes through the P2SB sideband registers at 00:1F.1 (0x1270) with
 * opcode 0x13, the value Intel's reference code names GpioLockUnlock. */
static VOID MemOcGpio (VOID)
{
  CPU_SETUP CpuSetup;

  gRT->GetVariable (L"CpuSetup", ...);
  if (CpuSetup.OverclockingSupport != 1)                             /* +0x1B7 */
    return;
  if (IsPchLp () || GppB.PadPerGroup <= 22)                          /* 0x1158; an unknown */
    return;                                                          /* ID uses the H table */
  if (PadOwnership (GPP_B, 22) != HOST)                              /* 0x0C30: PCR[0x6E][0x38] bits 25:24 */
    return;

  /* 0x119C */
  WasLocked = PadCfgLockTx (GPP_B) & BIT22;                          /* PCR[0x6E][0x8C] */
  if (WasLocked) SbiClearLockTx (GPP_B, BIT22);                      /* 0x0D2C */
  MmioOr32 (PCR (0x6E, 0x790 + 22 * 0x10), BIT0);                    /* GPP_B22 DW0: GPIOTXState = 1 */
  if (WasLocked) SbiSetLockTx (GPP_B, BIT22);                        /* 0x0D80 */
  /* Nothing in this module drives the pad low when the switch is 0. What
   * GPP_B22 is wired to on this board is not known from the BIOS; a DIMM
   * voltage select would fit the "memory overclock" name, and is only that:
   * a guess, untested. */
}
