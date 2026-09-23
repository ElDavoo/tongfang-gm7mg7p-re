// OemHddHeadParkSmm.efi: Ghidra x86:LE:64:default decompile, unedited
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
  
  FUN_0000139c();
  param_1[0x1f] = 0;
  if ((DAT_00002060 != 0) && ((in_CR4 >> 0x17 & 1) != 0)) {
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


// ==== entry @ 00001180

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

longlong entry(undefined8 param_1,longlong param_2)

{
  longlong lVar1;
  undefined *puVar2;
  undefined8 *puVar3;
  longlong local_res8 [4];
  
  _DAT_000020b8 = *(longlong *)(param_2 + 0x60);
  local_res8[0] = 0;
  _DAT_000020b0 = param_2;
  (**(code **)(_DAT_000020b8 + 0x140))(&DAT_00002040,0,local_res8);
  puVar3 = &DAT_000020c0;
  (**(code **)(local_res8[0] + 8))(local_res8[0]);
  puVar2 = &DAT_000020d0;
  DAT_000021d0 = -0x7fffffffffffffff;
  lVar1 = FUN_00001000((undefined8 *)&DAT_000020d0);
  if (lVar1 == 0) {
    lVar1 = FUN_000012c0(puVar2,(ulonglong)puVar3);
    if ((-1 < lVar1) || (DAT_000021d0 < 0)) {
      DAT_000021d0 = lVar1;
    }
    FUN_000010d0(0x20d0,0xffffffffffffffff);
  }
  return DAT_000021d0;
}


// ==== FUN_000012c0 @ 000012c0

void FUN_000012c0(undefined8 param_1,ulonglong param_2)

{
  int iVar1;
  longlong lVar2;
  undefined8 local_res8;
  ulonglong local_res10;
  undefined8 *local_res18;
  undefined8 *local_res20;
  undefined8 *local_28;
  undefined1 local_20 [8];
  undefined1 local_18 [8];
  undefined1 local_10 [8];
  
  local_res8 = param_1;
  local_res10 = param_2;
  lVar2 = (**(code **)(DAT_000020c0 + 0xd0))(&DAT_00002030,0,&local_res18);
  if (-1 < lVar2) {
    local_res10 = local_res10 & 0xffffffff00000000;
    (*(code *)*local_res18)(local_res18,&LAB_00001594,&local_res10,local_20);
  }
  lVar2 = (**(code **)(DAT_000020c0 + 0xd0))(&DAT_00002050,0,&local_res20);
  if (-1 < lVar2) {
    iVar1 = 3;
    local_res8 = 3;
    do {
      if (iVar1 != 3) {
        (*(code *)*local_res20)(local_res20,FUN_0000159c,&local_res8,local_18);
        iVar1 = (int)local_res8;
      }
      iVar1 = iVar1 + 1;
      local_res8 = CONCAT44(local_res8._4_4_,iVar1);
    } while (iVar1 < 6);
  }
  lVar2 = (**(code **)(DAT_000020c0 + 0xd0))(0x2000,0,&local_28);
  if (-1 < lVar2) {
    (*(code *)*local_28)(local_28,&LAB_00001220,local_10);
  }
  return;
}


// ==== FUN_0000139c @ 0000139c

void FUN_0000139c(void)

{
  return;
}


// ==== FUN_000013a0 @ 000013a0

undefined8 FUN_000013a0(undefined8 *param_1)

{
  ulonglong uVar1;
  undefined8 uVar2;
  int iVar3;
  longlong *plVar4;
  ulonglong uVar5;
  longlong *plVar6;
  longlong *plVar7;
  longlong *plVar8;
  longlong lVar9;
  
  uVar5 = 0;
  uVar1 = *(ulonglong *)(DAT_000020c0 + 0x98);
  if (uVar1 != 0) {
    plVar7 = *(longlong **)(DAT_000020c0 + 0xa0);
    plVar6 = plVar7 + 2;
    do {
      plVar8 = (longlong *)&DAT_00002020;
      plVar4 = plVar7;
      if ((((ulonglong)plVar7 & 7) != 0) && (((ulonglong)plVar7 & 7) == 0)) {
        lVar9 = 8;
        do {
          if ((char)*plVar4 != (char)*plVar8) break;
          plVar4 = (longlong *)((longlong)plVar4 + 1);
          plVar8 = (longlong *)((longlong)plVar8 + 1);
          lVar9 = lVar9 + -1;
        } while (lVar9 != 0);
      }
      for (; (plVar4 <= plVar6 + -1 && (*plVar4 == *plVar8)); plVar4 = plVar4 + 1) {
        plVar8 = plVar8 + 1;
      }
      for (; plVar4 < plVar6; plVar4 = (longlong *)((longlong)plVar4 + 1)) {
        if ((char)*plVar4 != (char)*plVar8) {
          iVar3 = (int)(char)*plVar4 - (int)(char)*plVar8;
          goto LAB_0000144b;
        }
        plVar8 = (longlong *)((longlong)plVar8 + 1);
      }
      iVar3 = 0;
LAB_0000144b:
      if (iVar3 == 0) break;
      uVar5 = uVar5 + 1;
      plVar7 = plVar7 + 3;
      plVar6 = plVar6 + 3;
    } while (uVar5 < uVar1);
  }
  if (uVar5 < uVar1) {
    uVar2 = 0;
    *param_1 = *(undefined8 *)(*(longlong *)(DAT_000020c0 + 0xa0) + 0x10 + uVar5 * 0x18);
  }
  else {
    uVar2 = 0x800000000000000e;
  }
  return uVar2;
}


// ==== FUN_000014b0 @ 000014b0

void FUN_000014b0(undefined8 param_1)

{
  longlong lVar1;
  undefined1 local_res10 [8];
  undefined8 local_res18;
  undefined8 *local_res20;
  undefined4 local_18;
  undefined4 local_14;
  undefined4 local_10;
  undefined4 local_c;
  
  local_18 = 0x55cfba41;
  local_14 = 0x4f3c34b8;
  local_10 = 0x3ae0fbe;
  local_c = 0x4e134975;
  lVar1 = (**(code **)(DAT_000020c0 + 0xd0))(&DAT_00002010,0,&local_res20);
  if (-1 < lVar1) {
    local_res18 = 10;
    (*(code *)*local_res20)(u_OemHddHeadPark_00002068,&local_18,local_res10,&local_res18,param_1);
  }
  return;
}


// ==== FUN_0000152c @ 0000152c

void FUN_0000152c(void)

{
  longlong lVar1;
  longlong local_res8 [4];
  undefined4 local_18;
  undefined4 local_14;
  undefined4 local_10;
  undefined4 local_c;
  
  local_18 = 0x55cfba41;
  local_14 = 0x4f3c34b8;
  local_10 = 0x3ae0fbe;
  local_c = 0x4e134975;
  lVar1 = (**(code **)(DAT_000020c0 + 0xd0))(&DAT_00002010,0,local_res8);
  if (-1 < lVar1) {
    (**(code **)(local_res8[0] + 0x10))(u_OemHddHeadPark_00002068,&local_18,0,0,0);
  }
  return;
}


// ==== FUN_0000159c @ 0000159c

void FUN_0000159c(undefined8 param_1,int *param_2)

{
  longlong lVar1;
  char local_18 [24];
  
  if (*param_2 - 4U < 2) {
    lVar1 = FUN_000014b0(local_18);
    if (lVar1 < 0) {
      return;
    }
    if (local_18[0] == '\x01') {
      FUN_0000152c();
      return;
    }
  }
  FUN_000015d4();
  return;
}


// ==== FUN_000015d4 @ 000015d4

longlong FUN_000015d4(void)

{
  undefined4 *puVar1;
  longlong lVar2;
  ulonglong uVar3;
  ulonglong uVar4;
  undefined4 *local_res8;
  undefined1 local_a8;
  byte local_a7;
  longlong local_a6;
  undefined8 local_98;
  undefined8 uStack_90;
  undefined4 local_88;
  undefined4 uStack_84;
  undefined4 uStack_80;
  undefined4 uStack_7c;
  undefined4 local_78;
  undefined4 uStack_74;
  undefined4 uStack_70;
  undefined4 uStack_6c;
  undefined1 local_68;
  undefined8 local_58;
  undefined8 uStack_50;
  undefined4 local_48;
  undefined4 uStack_44;
  undefined4 uStack_40;
  undefined4 uStack_3c;
  undefined4 local_38;
  undefined4 uStack_34;
  undefined4 uStack_30;
  undefined4 uStack_2c;
  undefined1 local_28;
  
  out(0x80,0x77);
  lVar2 = FUN_000014b0(&local_a8);
  uVar3 = 0;
  if (lVar2 < 0) {
    out(0x80,0x78);
  }
  else {
    local_res8 = (undefined4 *)0x0;
    lVar2 = FUN_000013a0(&local_res8);
    puVar1 = local_res8;
    if (lVar2 < 0) {
      out(0x80,0x79);
    }
    else {
      uVar4 = uVar3;
      if (local_a7 != 0) {
        do {
          *puVar1 = *(undefined4 *)(uVar4 + local_a6);
          FUN_00001730((undefined4 *)&local_98,0,0x31);
          local_28 = local_68;
          local_58 = local_98;
          uStack_50 = uStack_90;
          uStack_84 = CONCAT13(0xe0,(undefined3)uStack_84);
          local_38 = local_78;
          uStack_34 = uStack_74;
          uStack_30 = uStack_70;
          uStack_2c = uStack_6c;
          local_48 = local_88;
          uStack_44 = uStack_84;
          uStack_40 = uStack_80;
          uStack_3c = uStack_7c;
          lVar2 = (**(code **)(puVar1 + 0x1a))
                            (puVar1,&local_58,*(undefined1 *)(uVar4 + 8 + local_a6),
                             *(undefined1 *)(uVar4 + 9 + local_a6),
                             *(undefined4 *)(uVar4 + 10 + local_a6));
          uVar3 = uVar3 + 1;
          uVar4 = uVar4 + 0xe;
        } while (uVar3 < local_a7);
      }
      FUN_0000152c();
      out(0x80,0x88);
    }
  }
  return lVar2;
}


// ==== FUN_00001730 @ 00001730

undefined4 * FUN_00001730(undefined4 *param_1,undefined1 param_2,ulonglong param_3)

{
  ulonglong uVar1;
  longlong lVar2;
  undefined4 *puVar3;
  
  puVar3 = param_1;
  if (3 < param_3) {
    if (((ulonglong)param_1 & 3) != 0) {
      lVar2 = 4 - ((ulonglong)param_1 & 3);
      param_3 = param_3 - lVar2;
      for (; lVar2 != 0; lVar2 = lVar2 + -1) {
        *(undefined1 *)puVar3 = param_2;
        puVar3 = (undefined4 *)((longlong)puVar3 + 1);
      }
    }
    for (uVar1 = param_3 >> 2; uVar1 != 0; uVar1 = uVar1 - 1) {
      *puVar3 = CONCAT22(CONCAT11(param_2,param_2),CONCAT11(param_2,param_2));
      puVar3 = puVar3 + 1;
    }
    param_3 = param_3 & 3;
  }
  for (; param_3 != 0; param_3 = param_3 - 1) {
    *(undefined1 *)puVar3 = param_2;
    puVar3 = (undefined4 *)((longlong)puVar3 + 1);
  }
  return param_1;
}


