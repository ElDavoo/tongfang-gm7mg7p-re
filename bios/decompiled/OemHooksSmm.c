// OemHooksSmm.efi: Ghidra x86:LE:64:default decompile, unedited
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
  
  FUN_00001240();
  param_1[0x1f] = 0;
  if ((DAT_00002020 != 0) && ((in_CR4 >> 0x17 & 1) != 0)) {
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

void FUN_000010d0(longlong param_1,undefined8 param_2)

{
  MXCSR = *(undefined4 *)(param_1 + 0x50);
                    /* WARNING: Could not recover jumptable at 0x00001179. Too many branches */
                    /* WARNING: Treating indirect jump as call */
  (**(code **)(param_1 + 0x48))(param_1,param_2);
  return;
}


// ==== entry @ 0000117c

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

undefined8 entry(undefined8 param_1,longlong param_2)

{
  longlong lVar1;
  undefined8 *local_res8;
  undefined1 local_res10 [24];
  
  _DAT_00002058 = *(longlong *)(param_2 + 0x60);
  local_res8 = (undefined8 *)0x0;
  _DAT_00002050 = param_2;
  (**(code **)(_DAT_00002058 + 0x140))(&DAT_00002010,0,&local_res8);
  (*(code *)local_res8[1])(local_res8);
  DAT_00002170 = 0x8000000000000001;
  lVar1 = FUN_00001000((undefined8 *)&DAT_00002070);
  if (lVar1 == 0) {
    lVar1 = (**(code **)(DAT_00002060 + 0xd0))(0x2000,0,&local_res8);
    if (-1 < lVar1) {
      (*(code *)*local_res8)(local_res8,FUN_00001240,local_res10);
    }
    DAT_00002170 = 0;
    FUN_000010d0(0x2070,0xffffffffffffffff);
  }
  return DAT_00002170;
}


// ==== FUN_00001240 @ 00001240

void FUN_00001240(void)

{
  return;
}


