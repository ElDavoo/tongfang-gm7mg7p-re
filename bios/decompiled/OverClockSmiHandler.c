// OverClockSmiHandler.efi: Ghidra x86:LE:64:default decompile, unedited
// ==== FUN_00001000 @ 00001000

undefined8 FUN_00001000(undefined8 *param_1)

{
  undefined8 unaff_RBX;
  undefined8 unaff_RBP;
  undefined8 unaff_RSI;
  undefined8 unaff_RDI;
  undefined8 unaff_R12;
  undefined8 unaff_R13;
  undefined8 unaff_R14;
  undefined8 unaff_R15;
  uint in_CR4;
  longlong in_SSP;
  undefined8 unaff_XMM6_Qa;
  undefined8 unaff_XMM6_Qb;
  undefined8 unaff_XMM7_Qa;
  undefined8 unaff_XMM7_Qb;
  undefined8 unaff_XMM8_Qa;
  undefined8 unaff_XMM8_Qb;
  undefined8 unaff_XMM9_Qa;
  undefined8 unaff_XMM9_Qb;
  undefined8 unaff_XMM10_Qa;
  undefined8 unaff_XMM10_Qb;
  undefined8 unaff_XMM11_Qa;
  undefined8 unaff_XMM11_Qb;
  undefined8 unaff_XMM12_Qa;
  undefined8 unaff_XMM12_Qb;
  undefined8 unaff_XMM13_Qa;
  undefined8 unaff_XMM13_Qb;
  undefined8 unaff_XMM14_Qa;
  undefined8 unaff_XMM14_Qb;
  undefined8 unaff_XMM15_Qa;
  undefined8 unaff_XMM15_Qb;
  undefined8 unaff_retaddr;
  undefined1 auStackX_8 [32];
  
  FUN_0000579c();
  param_1[0x1f] = 0;
  if ((DAT_000060a4 != 0) && ((in_CR4 >> 0x17 & 1) != 0)) {
    param_1[0x1f] = in_SSP + 8;
  }
  *param_1 = unaff_RBX;
  param_1[1] = auStackX_8;
  param_1[2] = unaff_RBP;
  param_1[3] = unaff_RDI;
  param_1[4] = unaff_RSI;
  param_1[5] = unaff_R12;
  param_1[6] = unaff_R13;
  param_1[7] = unaff_R14;
  param_1[8] = unaff_R15;
  param_1[9] = unaff_retaddr;
  *(undefined4 *)(param_1 + 10) = MXCSR;
  param_1[0xb] = unaff_XMM6_Qa;
  param_1[0xc] = unaff_XMM6_Qb;
  param_1[0xd] = unaff_XMM7_Qa;
  param_1[0xe] = unaff_XMM7_Qb;
  param_1[0xf] = unaff_XMM8_Qa;
  param_1[0x10] = unaff_XMM8_Qb;
  param_1[0x11] = unaff_XMM9_Qa;
  param_1[0x12] = unaff_XMM9_Qb;
  param_1[0x13] = unaff_XMM10_Qa;
  param_1[0x14] = unaff_XMM10_Qb;
  param_1[0x15] = unaff_XMM11_Qa;
  param_1[0x16] = unaff_XMM11_Qb;
  param_1[0x17] = unaff_XMM12_Qa;
  param_1[0x18] = unaff_XMM12_Qb;
  param_1[0x19] = unaff_XMM13_Qa;
  param_1[0x1a] = unaff_XMM13_Qb;
  param_1[0x1b] = unaff_XMM14_Qa;
  param_1[0x1c] = unaff_XMM14_Qb;
  param_1[0x1d] = unaff_XMM15_Qa;
  param_1[0x1e] = unaff_XMM15_Qb;
                    /* WARNING: Treating indirect jump as return */
  return 0;
}


// ==== FUN_000010d0 @ 000010d0

int FUN_000010d0(int param_1,undefined4 *param_2,undefined4 *param_3,undefined4 *param_4,
                undefined4 *param_5)

{
  undefined4 *puVar1;
  undefined4 uVar2;
  undefined4 uVar3;
  undefined4 uVar4;
  
  if (param_1 == 0) {
    puVar1 = (undefined4 *)cpuid_basic_info(0);
  }
  else if (param_1 == 1) {
    puVar1 = (undefined4 *)cpuid_Version_info(1);
  }
  else if (param_1 == 2) {
    puVar1 = (undefined4 *)cpuid_cache_tlb_info(2);
  }
  else if (param_1 == 3) {
    puVar1 = (undefined4 *)cpuid_serial_info(3);
  }
  else if (param_1 == 4) {
    puVar1 = (undefined4 *)cpuid_Deterministic_Cache_Parameters_info(4);
  }
  else if (param_1 == 5) {
    puVar1 = (undefined4 *)cpuid_MONITOR_MWAIT_Features_info(5);
  }
  else if (param_1 == 6) {
    puVar1 = (undefined4 *)cpuid_Thermal_Power_Management_info(6);
  }
  else if (param_1 == 7) {
    puVar1 = (undefined4 *)cpuid_Extended_Feature_Enumeration_info(7);
  }
  else if (param_1 == 9) {
    puVar1 = (undefined4 *)cpuid_Direct_Cache_Access_info(9);
  }
  else if (param_1 == 10) {
    puVar1 = (undefined4 *)cpuid_Architectural_Performance_Monitoring_info(10);
  }
  else if (param_1 == 0xb) {
    puVar1 = (undefined4 *)cpuid_Extended_Topology_info(0xb);
  }
  else if (param_1 == 0xd) {
    puVar1 = (undefined4 *)cpuid_Processor_Extended_States_info(0xd);
  }
  else if (param_1 == 0xf) {
    puVar1 = (undefined4 *)cpuid_Quality_of_Service_info(0xf);
  }
  else if (param_1 == -0x7ffffffe) {
    puVar1 = (undefined4 *)cpuid_brand_part1_info(0x80000002);
  }
  else if (param_1 == -0x7ffffffd) {
    puVar1 = (undefined4 *)cpuid_brand_part2_info(0x80000003);
  }
  else if (param_1 == -0x7ffffffc) {
    puVar1 = (undefined4 *)cpuid_brand_part3_info(0x80000004);
  }
  else {
    puVar1 = (undefined4 *)cpuid(param_1);
  }
  uVar2 = *puVar1;
  uVar3 = puVar1[1];
  uVar4 = puVar1[2];
  if (param_4 != (undefined4 *)0x0) {
    *param_4 = puVar1[3];
  }
  if (param_2 != (undefined4 *)0x0) {
    *param_2 = uVar2;
  }
  if (param_3 != (undefined4 *)0x0) {
    *param_3 = uVar3;
  }
  if (param_5 != (undefined4 *)0x0) {
    *param_5 = uVar4;
  }
  return param_1;
}


// ==== FUN_00001130 @ 00001130

void FUN_00001130(longlong param_1,undefined8 param_2)

{
  MXCSR = *(undefined4 *)(param_1 + 0x50);
                    /* WARNING: Could not recover jumptable at 0x000011d9. Too many branches */
                    /* WARNING: Treating indirect jump as call */
  (**(code **)(param_1 + 0x48))(param_1,param_2);
  return;
}


// ==== FUN_00001240 @ 00001240

void FUN_00001240(void)

{
  return;
}


// ==== FUN_00001250 @ 00001250

ulonglong FUN_00001250(void)

{
  ulonglong uVar1;
  undefined8 in_RAX;
  
  uVar1 = rdtsc();
  return CONCAT44((int)((ulonglong)in_RAX >> 0x20),(int)uVar1) | uVar1 & 0xffffffff00000000;
}


// ==== FUN_00001260 @ 00001260

void FUN_00001260(void)

{
  return;
}


// ==== FUN_00001270 @ 00001270

void FUN_00001270(void)

{
  return;
}


// ==== FUN_00001280 @ 00001280

ulonglong FUN_00001280(void)

{
  byte in_CF;
  byte in_PF;
  byte in_AF;
  byte in_ZF;
  byte in_SF;
  byte in_TF;
  byte in_IF;
  byte in_OF;
  byte in_NT;
  byte in_AC;
  byte in_VIF;
  byte in_VIP;
  byte in_ID;
  
  return (ulonglong)(in_NT & 1) * 0x4000 | (ulonglong)(in_OF & 1) * 0x800 |
         (ulonglong)(in_IF & 1) * 0x200 | (ulonglong)(in_TF & 1) * 0x100 |
         (ulonglong)(in_SF & 1) * 0x80 | (ulonglong)(in_ZF & 1) * 0x40 |
         (ulonglong)(in_AF & 1) * 0x10 | (ulonglong)(in_PF & 1) * 4 | (ulonglong)(in_CF & 1) |
         (ulonglong)(in_ID & 1) * 0x200000 | (ulonglong)(in_VIP & 1) * 0x100000 |
         (ulonglong)(in_VIF & 1) * 0x80000 | (ulonglong)(in_AC & 1) * 0x40000;
}


// ==== entry @ 00001290

longlong entry(longlong param_1,ulonglong param_2)

{
  longlong lVar1;
  
  FUN_000012e0(param_1,param_2);
  lVar1 = FUN_00001420();
  if (lVar1 < 0) {
    FUN_000013b0();
  }
  return lVar1;
}


// ==== FUN_000012e0 @ 000012e0

void FUN_000012e0(longlong param_1,ulonglong param_2)

{
  FUN_00005684(param_1,param_2);
  FUN_0000569c(param_1,param_2);
  FUN_000056ac(param_1,param_2);
  FUN_000057a0(param_1,param_2);
  FUN_000058e0();
  FUN_00005950();
  FUN_00005960();
  FUN_00005a14();
  FUN_00005a48();
  return;
}


// ==== FUN_000013b0 @ 000013b0

void FUN_000013b0(void)

{
  FUN_00005820();
  return;
}


// ==== FUN_000013e0 @ 000013e0

void FUN_000013e0(longlong param_1)

{
  if ((-1 < param_1) || (DAT_00006240 < 0)) {
    DAT_00006240 = param_1;
  }
  thunk_FUN_00001130(0x6140,0xffffffffffffffff);
  return;
}


// ==== FUN_00001420 @ 00001420

undefined8 FUN_00001420(void)

{
  longlong lVar1;
  
  DAT_00006240 = 0x8000000000000001;
  lVar1 = FUN_00001000((undefined8 *)&DAT_00006140);
  if (lVar1 == 0) {
    lVar1 = FUN_000055e0();
    FUN_000013e0(lVar1);
  }
  return DAT_00006240;
}


// ==== FUN_00001480 @ 00001480

undefined1 FUN_00001480(void)

{
  ulonglong uVar1;
  undefined1 local_28;
  uint local_18 [6];
  
  local_18[0] = 0;
  local_18[1] = 0;
  local_18[2] = 0;
  local_18[3] = 0;
  uVar1 = FUN_00005790(0x1a0);
  FUN_000010d0(6,local_18,local_18 + 1,local_18 + 2,local_18 + 3);
  if (((local_18[0] & 2) == 0) && ((uVar1 & 0x4000000000) == 0)) {
    local_28 = 0;
  }
  else {
    local_28 = 1;
  }
  return local_28;
}


// ==== FUN_00001520 @ 00001520

bool FUN_00001520(void)

{
  ulonglong uVar1;
  
  uVar1 = FUN_00005790(0xce);
  return (uVar1 & 0x20000000) != 0;
}


// ==== FUN_00001570 @ 00001570

bool FUN_00001570(void)

{
  ulonglong uVar1;
  
  uVar1 = FUN_00005790(0xce);
  return (uVar1 & 0x10000000) != 0;
}


// ==== FUN_000015c0 @ 000015c0

void FUN_000015c0(undefined1 param_1,undefined1 param_2,undefined1 param_3,undefined1 param_4,
                 undefined1 param_5,undefined1 param_6,undefined1 param_7,undefined1 param_8,
                 byte param_9,char param_10,char param_11,char param_12,char param_13,char param_14,
                 char param_15,char param_16)

{
  byte local_18;
  byte local_17;
  
  local_17 = 0;
  if (param_9 != 0) {
    for (local_18 = 0; local_18 < param_9; local_18 = local_18 + 1) {
      (&DAT_000060f0)[local_17] = param_1;
      local_17 = local_17 + 1;
    }
  }
  if (param_10 != '\0') {
    for (local_18 = 0; local_18 < (byte)(param_10 - param_9); local_18 = local_18 + 1) {
      (&DAT_000060f0)[local_17] = param_2;
      local_17 = local_17 + 1;
    }
  }
  if (param_11 != '\0') {
    for (local_18 = 0; local_18 < (byte)(param_11 - param_10); local_18 = local_18 + 1) {
      (&DAT_000060f0)[local_17] = param_3;
      local_17 = local_17 + 1;
    }
  }
  if (param_12 != '\0') {
    for (local_18 = 0; local_18 < (byte)(param_12 - param_11); local_18 = local_18 + 1) {
      (&DAT_000060f0)[local_17] = param_4;
      local_17 = local_17 + 1;
    }
  }
  if (param_13 != '\0') {
    for (local_18 = 0; local_18 < (byte)(param_13 - param_12); local_18 = local_18 + 1) {
      (&DAT_000060f0)[local_17] = param_5;
      local_17 = local_17 + 1;
    }
  }
  if (param_14 != '\0') {
    for (local_18 = 0; local_18 < (byte)(param_14 - param_13); local_18 = local_18 + 1) {
      (&DAT_000060f0)[local_17] = param_6;
      local_17 = local_17 + 1;
    }
  }
  if (param_15 != '\0') {
    for (local_18 = 0; local_18 < (byte)(param_15 - param_14); local_18 = local_18 + 1) {
      (&DAT_000060f0)[local_17] = param_7;
      local_17 = local_17 + 1;
    }
  }
  if (param_16 != '\0') {
    for (local_18 = 0; local_18 < (byte)(param_16 - param_15); local_18 = local_18 + 1) {
      (&DAT_000060f0)[local_17] = param_8;
      local_17 = local_17 + 1;
    }
  }
  return;
}


// ==== FUN_000018b0 @ 000018b0

void FUN_000018b0(undefined1 *param_1,undefined1 *param_2,undefined1 *param_3,undefined1 *param_4,
                 undefined1 *param_5,undefined1 *param_6,undefined1 *param_7,undefined1 *param_8,
                 undefined1 *param_9,undefined1 *param_10,undefined1 *param_11,undefined1 *param_12,
                 undefined1 *param_13,undefined1 *param_14,undefined1 *param_15,undefined1 *param_16
                 )

{
  longlong lVar1;
  undefined1 *puVar2;
  char *pcVar3;
  byte local_28;
  byte local_27;
  byte local_26;
  char acStack_21 [6];
  undefined1 uStack_1b;
  undefined1 uStack_1a;
  undefined1 uStack_19;
  undefined1 local_18 [5];
  undefined1 uStack_13;
  undefined1 uStack_12;
  undefined1 uStack_11;
  
  puVar2 = local_18;
  for (lVar1 = 7; puVar2 = puVar2 + 1, lVar1 != 0; lVar1 = lVar1 + -1) {
    *puVar2 = 0;
  }
  pcVar3 = acStack_21 + 2;
  for (lVar1 = 7; lVar1 != 0; lVar1 = lVar1 + -1) {
    *pcVar3 = '\0';
    pcVar3 = pcVar3 + 1;
  }
  acStack_21[1] = 1;
  local_18[0] = DAT_000060f0;
  local_26 = 0;
  local_27 = 0;
  for (local_28 = 1; local_28 < DAT_000060fc; local_28 = local_28 + 1) {
    if ((&DAT_000060f0)[(int)(local_28 - 1)] == (&DAT_000060f0)[local_28]) {
      local_18[local_26] = (&DAT_000060f0)[local_28];
      acStack_21[(ulonglong)local_27 + 1] = acStack_21[(ulonglong)local_27 + 1] + '\x01';
    }
    if ((byte)(&DAT_000060f0)[local_28] < (byte)(&DAT_000060f0)[(int)(local_28 - 1)]) {
      local_26 = local_26 + 1;
      local_27 = local_27 + 1;
      local_18[local_26] = (&DAT_000060f0)[local_28];
      acStack_21[(ulonglong)local_27 + 1] = acStack_21[(longlong)(int)(local_27 - 1) + 1] + '\x01';
    }
  }
  *param_1 = local_18[0];
  *param_2 = local_18[1];
  *param_3 = local_18[2];
  *param_4 = local_18[3];
  *param_5 = local_18[4];
  *param_6 = uStack_13;
  *param_7 = uStack_12;
  *param_8 = uStack_11;
  *param_9 = acStack_21[1];
  *param_10 = acStack_21[2];
  *param_11 = acStack_21[3];
  *param_12 = acStack_21[4];
  *param_13 = acStack_21[5];
  *param_14 = uStack_1b;
  *param_15 = uStack_1a;
  *param_16 = uStack_19;
  return;
}


// ==== FUN_00005530 @ 00005530

undefined8 FUN_00005530(void)

{
  undefined8 uVar1;
  undefined8 *local_20;
  ulonglong local_18;
  undefined1 local_10 [16];
  
  uVar1 = (**(code **)(DAT_00006118 + 0xd0))(&DAT_00006080,0,&local_20);
  local_18 = (ulonglong)DAT_000060a0;
  (*(code *)*local_20)(local_20,&LAB_00001b80,&local_18,local_10,uVar1);
  (**(code **)(DAT_00006118 + 0xd0))(&DAT_00006020,0,&DAT_00006258);
  uVar1 = (**(code **)(DAT_00006118 + 0xd0))(&DAT_00006010,0,&DAT_00006260);
  return uVar1;
}


// ==== FUN_000055e0 @ 000055e0

undefined8 FUN_000055e0(void)

{
  undefined8 uVar1;
  undefined1 local_2e4 [4];
  undefined8 local_2e0;
  longlong local_2d8;
  undefined1 local_2c8 [439];
  char local_111;
  
  local_2e0 = 699;
  local_2d8 = (**(code **)(DAT_00006110 + 0x48))
                        (u_CpuSetup_000060b8,0x6000,local_2e4,&local_2e0,local_2c8);
  if ((local_2d8 < 0) || (local_111 == '\0')) {
    uVar1 = 0;
  }
  else {
    uVar1 = FUN_00005790(0x35);
    DAT_000060fc = (undefined2)((ulonglong)uVar1 >> 0x10);
    uVar1 = FUN_00005530();
  }
  return uVar1;
}


// ==== FUN_00005684 @ 00005684

undefined8 FUN_00005684(undefined8 param_1,longlong param_2)

{
  DAT_00006108 = *(undefined8 *)(param_2 + 0x60);
  DAT_00006100 = param_2;
  return 0;
}


// ==== FUN_0000569c @ 0000569c

undefined8 FUN_0000569c(undefined8 param_1,longlong param_2)

{
  DAT_00006110 = *(undefined8 *)(param_2 + 0x58);
  return 0;
}


// ==== FUN_000056ac @ 000056ac

undefined8 FUN_000056ac(undefined8 param_1,longlong param_2)

{
  longlong local_res8 [4];
  
  local_res8[0] = 0;
  (**(code **)(*(longlong *)(param_2 + 0x60) + 0x140))(&DAT_00006060,0,local_res8);
  (**(code **)(local_res8[0] + 8))(local_res8[0],&DAT_00006118);
  return 0;
}


// ==== FUN_000056ec @ 000056ec

uint FUN_000056ec(void)

{
  uint local_18;
  undefined4 local_14;
  undefined4 local_10;
  undefined4 local_c [3];
  
  FUN_000010d0(1,&local_18,&local_14,&local_10,local_c);
  return local_18 & 0xfff0ff0;
}


// ==== FUN_00005720 @ 00005720

uint FUN_00005720(void)

{
  uint local_18;
  undefined4 local_14;
  undefined4 local_10;
  undefined4 local_c [3];
  
  FUN_000010d0(1,&local_18,&local_14,&local_10,local_c);
  return local_18 & 0xf;
}


// ==== FUN_00005754 @ 00005754

uint FUN_00005754(void)

{
  uint uVar1;
  uint uVar2;
  
  uVar1 = FUN_00005720();
  uVar2 = FUN_000056ec();
  if ((uVar2 == 0xa0650) && ((uVar1 == 1 || (uVar1 - 4 < 2)))) {
    uVar2 = 0xa0601;
  }
  else {
    uVar2 = uVar2 & 0xffffff00;
  }
  return uVar2;
}


// ==== thunk_FUN_00001130 @ 00005788

void thunk_FUN_00001130(longlong param_1,undefined8 param_2)

{
  MXCSR = *(undefined4 *)(param_1 + 0x50);
                    /* WARNING: Could not recover jumptable at 0x000011d9. Too many branches */
                    /* WARNING: Treating indirect jump as call */
  (**(code **)(param_1 + 0x48))(param_1,param_2);
  return;
}


// ==== FUN_00005790 @ 00005790

undefined8 FUN_00005790(undefined4 param_1)

{
  undefined8 uVar1;
  
  uVar1 = rdmsr(param_1);
  return uVar1;
}


// ==== FUN_0000579c @ 0000579c

void FUN_0000579c(void)

{
  return;
}


// ==== FUN_000057a0 @ 000057a0

undefined8 FUN_000057a0(longlong param_1,ulonglong param_2)

{
  longlong lVar1;
  longlong local_res8;
  ulonglong local_res10 [3];
  
  local_res8 = param_1;
  local_res10[0] = param_2;
  (**(code **)(DAT_00006108 + 0x140))(&DAT_00006070,0,&local_res8);
  local_res10[0] = 0;
  lVar1 = local_res8;
  (**(code **)(local_res8 + 0x18))(local_res8,local_res10,0);
  DAT_00006250 = FUN_00005874(lVar1,local_res10[0]);
  (**(code **)(local_res8 + 0x18))(local_res8,local_res10,DAT_00006250);
  DAT_00006248 = local_res10[0] >> 5;
  return 0;
}


// ==== FUN_00005820 @ 00005820

undefined8 FUN_00005820(void)

{
  FUN_000058a4();
  return 0;
}


// ==== FUN_00005830 @ 00005830

ulonglong FUN_00005830(ulonglong param_1)

{
  ulonglong in_RAX;
  ulonglong uVar1;
  ulonglong *puVar2;
  
  uVar1 = 0;
  if (DAT_00006248 != 0) {
    puVar2 = (ulonglong *)(DAT_00006250 + 8);
    in_RAX = DAT_00006250;
    do {
      if ((*puVar2 <= param_1) && (in_RAX = puVar2[1], param_1 < *puVar2 + in_RAX)) {
        return CONCAT71((int7)(in_RAX >> 8),1);
      }
      uVar1 = uVar1 + 1;
      puVar2 = puVar2 + 4;
    } while (uVar1 < DAT_00006248);
  }
  return in_RAX & 0xffffffffffffff00;
}


// ==== FUN_00005874 @ 00005874

undefined8 FUN_00005874(undefined8 param_1,undefined8 param_2)

{
  longlong lVar1;
  undefined8 local_res18 [2];
  
  lVar1 = (**(code **)(DAT_00006118 + 0x50))(6,param_2,local_res18);
  if (lVar1 < 0) {
    local_res18[0] = 0;
  }
  return local_res18[0];
}


// ==== FUN_000058a4 @ 000058a4

void FUN_000058a4(void)

{
  ulonglong uVar1;
  
  uVar1 = FUN_00005830(DAT_00006250);
  if ((char)uVar1 != '\0') {
                    /* WARNING: Could not recover jumptable at 0x000058ca. Too many branches */
                    /* WARNING: Treating indirect jump as call */
    (**(code **)(DAT_00006118 + 0x58))();
    return;
  }
                    /* WARNING: Could not recover jumptable at 0x000058d9. Too many branches */
                    /* WARNING: Treating indirect jump as call */
  (**(code **)(DAT_00006108 + 0x48))(DAT_00006250);
  return;
}


// ==== FUN_000058e0 @ 000058e0

undefined8 FUN_000058e0(void)

{
  return 0;
}


// ==== FUN_000058e4 @ 000058e4

longlong FUN_000058e4(void)

{
  ulonglong uVar1;
  longlong *plVar2;
  
  uVar1 = 0;
  if (DAT_00006120 == 0) {
    DAT_00006120 = 0;
    if (*(ulonglong *)(DAT_00006100 + 0x68) != 0) {
      plVar2 = *(longlong **)(DAT_00006100 + 0x70);
      do {
        if ((DAT_00006050 == *plVar2) && (DAT_00006058 == plVar2[1])) {
          DAT_00006120 = (*(longlong **)(DAT_00006100 + 0x70))[uVar1 * 3 + 2];
          return DAT_00006120;
        }
        uVar1 = uVar1 + 1;
        plVar2 = plVar2 + 3;
      } while (uVar1 < *(ulonglong *)(DAT_00006100 + 0x68));
    }
  }
  return DAT_00006120;
}


// ==== FUN_00005950 @ 00005950

undefined8 FUN_00005950(void)

{
  FUN_000058e4();
  return 0;
}


// ==== FUN_00005960 @ 00005960

undefined8 FUN_00005960(void)

{
  uint uVar1;
  int iVar2;
  short *psVar3;
  ulonglong uVar4;
  
  psVar3 = (short *)FUN_000058e4();
  do {
    if (*psVar3 == -1) {
      psVar3 = (short *)0x0;
LAB_0000599d:
      if (psVar3 == (short *)0x0) {
        uVar4 = FUN_00001280();
        FUN_00001270();
        uVar1 = in(0x1808);
        FUN_00001250();
        while (iVar2 = in(0x1808), (((uVar1 & 0xffffff) + 0x16b) - iVar2 >> 0x17 & 1) == 0) {
          FUN_00001240();
        }
        FUN_00001250();
        if ((uVar4 >> 9 & 1) == 0) {
          FUN_00001270();
        }
        else {
          FUN_00001260();
        }
        return 0;
      }
      if ((DAT_00006090 == *(longlong *)(psVar3 + 4)) && (DAT_00006098 == *(longlong *)(psVar3 + 8))
         ) {
        return 0;
      }
    }
    else if (*psVar3 == 4) goto LAB_0000599d;
    psVar3 = (short *)((longlong)psVar3 + (ulonglong)(ushort)psVar3[1]);
  } while( true );
}


// ==== FUN_00005a14 @ 00005a14

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

undefined8 FUN_00005a14(void)

{
  DAT_00006128 = 1;
  _DAT_00006130 = 0xe0000000;
  return 0;
}


// ==== FUN_00005a2c @ 00005a2c

undefined8 FUN_00005a2c(void)

{
  undefined8 uVar1;
  
  if (DAT_00006138 == (undefined8 *)0x0) {
    return 0x800000000000000f;
  }
                    /* WARNING: Could not recover jumptable at 0x00005a43. Too many branches */
                    /* WARNING: Treating indirect jump as call */
  uVar1 = (*(code *)*DAT_00006138)();
  return uVar1;
}


// ==== FUN_00005a48 @ 00005a48

void FUN_00005a48(void)

{
  longlong lVar1;
  
  lVar1 = (**(code **)(DAT_00006118 + 0xd0))(&DAT_00006040,0,&DAT_00006138);
  if (lVar1 < 0) {
    DAT_00006138 = 0;
  }
  return;
}


