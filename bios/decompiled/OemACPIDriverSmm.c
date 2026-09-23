// OemACPIDriverSmm.efi: Ghidra x86:LE:64:default decompile, unedited
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
  
  FUN_000015ac();
  param_1[0x1f] = 0;
  if ((DAT_00002090 != 0) && ((in_CR4 >> 0x17 & 1) != 0)) {
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


// ==== FUN_00001180 @ 00001180

undefined8 * FUN_00001180(undefined8 *param_1,undefined8 *param_2,ulonglong param_3)

{
  ulonglong uVar1;
  undefined8 *puVar2;
  undefined8 *puVar3;
  ulonglong uVar4;
  byte bVar5;
  
  bVar5 = 0;
  puVar2 = (undefined8 *)((longlong)param_2 + (param_3 - 1));
  if ((param_2 < param_1) && (param_1 <= puVar2)) {
    puVar3 = (undefined8 *)((longlong)param_1 + (param_3 - 1));
    bVar5 = 1;
    uVar4 = param_3;
  }
  else {
    uVar4 = param_3 & 7;
    puVar2 = param_2;
    puVar3 = param_1;
    for (uVar1 = param_3 >> 3; uVar1 != 0; uVar1 = uVar1 - 1) {
      *puVar3 = *puVar2;
      puVar2 = puVar2 + 1;
      puVar3 = puVar3 + 1;
    }
  }
  for (; uVar4 != 0; uVar4 = uVar4 - 1) {
    *(undefined1 *)puVar3 = *(undefined1 *)puVar2;
    puVar2 = (undefined8 *)((longlong)puVar2 + (ulonglong)bVar5 * -2 + 1);
    puVar3 = (undefined8 *)((longlong)puVar3 + (ulonglong)bVar5 * -2 + 1);
  }
  return param_1;
}


// ==== FUN_000011c0 @ 000011c0

void FUN_000011c0(void)

{
  return;
}


// ==== FUN_000011d0 @ 000011d0

ulonglong FUN_000011d0(void)

{
  ulonglong uVar1;
  undefined8 in_RAX;
  
  uVar1 = rdtsc();
  return CONCAT44((int)((ulonglong)in_RAX >> 0x20),(int)uVar1) | uVar1 & 0xffffffff00000000;
}


// ==== FUN_000011e0 @ 000011e0

void FUN_000011e0(void)

{
  return;
}


// ==== FUN_000011f0 @ 000011f0

void FUN_000011f0(void)

{
  return;
}


// ==== FUN_00001200 @ 00001200

ulonglong FUN_00001200(void)

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


// ==== entry @ 00001230

longlong entry(ulonglong param_1,longlong param_2)

{
  longlong lVar1;
  longlong *plVar2;
  
  FUN_000012a4(param_1,param_2);
  plVar2 = (longlong *)&DAT_00002100;
  DAT_00002200 = -0x7fffffffffffffff;
  lVar1 = FUN_00001000((undefined8 *)&DAT_00002100);
  if (lVar1 == 0) {
    lVar1 = FUN_000014dc(plVar2,param_2);
    if ((-1 < lVar1) || (DAT_00002200 < 0)) {
      DAT_00002200 = lVar1;
    }
    FUN_000010d0(0x2100,0xffffffffffffffff);
  }
  lVar1 = DAT_00002200;
  if (DAT_00002200 < 0) {
    FUN_00001648();
  }
  return lVar1;
}


// ==== FUN_000012a4 @ 000012a4

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_000012a4(ulonglong param_1,longlong param_2)

{
  uint uVar1;
  int iVar2;
  short *psVar3;
  longlong lVar4;
  longlong *plVar5;
  ulonglong uVar6;
  ulonglong local_res8;
  longlong local_res10;
  longlong local_res18;
  
  DAT_000020c8 = *(longlong *)(param_2 + 0x60);
  local_res10 = 0;
  DAT_000020c0 = param_2;
  local_res8 = param_1;
  (**(code **)(DAT_000020c8 + 0x140))(&DAT_00002050,0,&local_res10);
  (**(code **)(local_res10 + 8))(local_res10,&DAT_000020d0);
  DAT_000020d8 = 1;
  _DAT_000020e0 = 0xe0000000;
  (**(code **)(DAT_000020c8 + 0x140))(&DAT_00002060,0,&local_res18);
  local_res8 = 0;
  lVar4 = local_res18;
  (**(code **)(local_res18 + 0x18))(local_res18,&local_res8,0);
  DAT_00002210 = FUN_00001618(lVar4,local_res8);
  (**(code **)(local_res18 + 0x18))(local_res18,&local_res8,DAT_00002210);
  DAT_00002208 = local_res8 >> 5;
  FUN_00001684();
  psVar3 = (short *)FUN_00001684();
LAB_00001398:
  if (*psVar3 == -1) {
    psVar3 = (short *)0x0;
LAB_000013a3:
    if (psVar3 == (short *)0x0) {
      uVar6 = FUN_00001200();
      FUN_000011f0();
      uVar1 = in(0x1808);
      FUN_000011d0();
      while (iVar2 = in(0x1808), (((uVar1 & 0xffffff) + 0x16b) - iVar2 >> 0x17 & 1) == 0) {
        FUN_000011c0();
      }
      FUN_000011d0();
      if ((uVar6 >> 9 & 1) == 0) {
        FUN_000011f0();
      }
      else {
        FUN_000011e0();
      }
LAB_0000140c:
      uVar6 = 0;
      plVar5 = *(longlong **)(DAT_000020d0 + 0xa0);
      if (*(ulonglong *)(DAT_000020d0 + 0x98) != 0) {
        do {
          if ((DAT_00002020 == *plVar5) && (DAT_00002028 == plVar5[1])) break;
          uVar6 = uVar6 + 1;
          plVar5 = plVar5 + 3;
        } while (uVar6 < *(ulonglong *)(DAT_000020d0 + 0x98));
      }
      if ((DAT_000020f0 != (undefined8 *)0x0) ||
         (lVar4 = (**(code **)(DAT_000020c8 + 0x140))(&DAT_00002050,0,&DAT_000020f0), -1 < lVar4)) {
        (*(code *)*DAT_000020f0)(DAT_000020f0,&DAT_000020f8);
      }
      return;
    }
    if ((DAT_00002080 == *(longlong *)(psVar3 + 4)) && (DAT_00002088 == *(longlong *)(psVar3 + 8)))
    goto LAB_0000140c;
  }
  else if (*psVar3 == 4) goto LAB_000013a3;
  psVar3 = (short *)((longlong)psVar3 + (ulonglong)(ushort)psVar3[1]);
  goto LAB_00001398;
}


// ==== FUN_000014dc @ 000014dc

longlong FUN_000014dc(longlong *param_1,undefined8 param_2)

{
  longlong lVar1;
  longlong lVar2;
  longlong *local_res8;
  undefined8 local_res10;
  undefined8 *local_res18;
  undefined8 local_res20;
  undefined1 local_18 [16];
  
  local_res20 = 0;
  local_res8 = param_1;
  local_res10 = param_2;
  lVar1 = (**(code **)(DAT_000020c8 + 0x140))(&DAT_00002040,0,&local_res8);
  if ((-1 < lVar1) &&
     (lVar1 = (**(code **)(DAT_000020d0 + 0xd0))(&DAT_00002070,0,&local_res18), -1 < lVar1)) {
    local_res10 = 0xffffffffffffffff;
    lVar1 = (*(code *)*local_res18)(local_res18,&LAB_0000149c,&local_res10,local_18);
    if (-1 < lVar1) {
      *(undefined1 *)(*local_res8 + 4) = (undefined1)local_res10;
      FUN_000015b0(local_res8,8);
      lVar2 = (**(code **)(DAT_000020d0 + 0xa8))(&local_res20,0x2000,0,&DAT_00002220);
      lVar1 = 0;
      if (lVar2 < 0) {
        lVar1 = lVar2;
      }
    }
  }
  return lVar1;
}


// ==== FUN_000015ac @ 000015ac

void FUN_000015ac(void)

{
  return;
}


// ==== FUN_000015b0 @ 000015b0

void FUN_000015b0(undefined8 *param_1,ulonglong param_2)

{
  if (param_1 != &DAT_00002220) {
    FUN_00001180(&DAT_00002220,param_1,param_2);
  }
  return;
}


// ==== FUN_000015d4 @ 000015d4

ulonglong FUN_000015d4(ulonglong param_1)

{
  ulonglong in_RAX;
  ulonglong uVar1;
  ulonglong *puVar2;
  
  uVar1 = 0;
  if (DAT_00002208 != 0) {
    puVar2 = (ulonglong *)(DAT_00002210 + 8);
    in_RAX = DAT_00002210;
    do {
      if ((*puVar2 <= param_1) && (in_RAX = puVar2[1], param_1 < *puVar2 + in_RAX)) {
        return CONCAT71((int7)(in_RAX >> 8),1);
      }
      uVar1 = uVar1 + 1;
      puVar2 = puVar2 + 4;
    } while (uVar1 < DAT_00002208);
  }
  return in_RAX & 0xffffffffffffff00;
}


// ==== FUN_00001618 @ 00001618

undefined8 FUN_00001618(undefined8 param_1,undefined8 param_2)

{
  longlong lVar1;
  undefined8 local_res18 [2];
  
  lVar1 = (**(code **)(DAT_000020d0 + 0x50))(6,param_2,local_res18);
  if (lVar1 < 0) {
    local_res18[0] = 0;
  }
  return local_res18[0];
}


// ==== FUN_00001648 @ 00001648

void FUN_00001648(void)

{
  ulonglong uVar1;
  
  uVar1 = FUN_000015d4(DAT_00002210);
  if ((char)uVar1 != '\0') {
                    /* WARNING: Could not recover jumptable at 0x0000166e. Too many branches */
                    /* WARNING: Treating indirect jump as call */
    (**(code **)(DAT_000020d0 + 0x58))();
    return;
  }
                    /* WARNING: Could not recover jumptable at 0x0000167d. Too many branches */
                    /* WARNING: Treating indirect jump as call */
  (**(code **)(DAT_000020c8 + 0x48))(DAT_00002210);
  return;
}


// ==== FUN_00001684 @ 00001684

longlong FUN_00001684(void)

{
  ulonglong uVar1;
  longlong *plVar2;
  
  uVar1 = 0;
  if (DAT_000020e8 == 0) {
    DAT_000020e8 = 0;
    if (*(ulonglong *)(DAT_000020c0 + 0x68) != 0) {
      plVar2 = *(longlong **)(DAT_000020c0 + 0x70);
      do {
        if ((DAT_00002030 == *plVar2) && (DAT_00002038 == plVar2[1])) {
          DAT_000020e8 = (*(longlong **)(DAT_000020c0 + 0x70))[uVar1 * 3 + 2];
          return DAT_000020e8;
        }
        uVar1 = uVar1 + 1;
        plVar2 = plVar2 + 3;
      } while (uVar1 < *(ulonglong *)(DAT_000020c0 + 0x68));
    }
  }
  return DAT_000020e8;
}


