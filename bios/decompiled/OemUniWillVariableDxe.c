// OemUniWillVariableDxe.efi: Ghidra x86:LE:64:default decompile, unedited
// ==== FUN_000002c0 @ 000002c0

void FUN_000002c0(void)

{
  return;
}


// ==== FUN_000002d0 @ 000002d0

ulonglong FUN_000002d0(void)

{
  ulonglong uVar1;
  undefined8 in_RAX;
  
  uVar1 = rdtsc();
  return CONCAT44((int)((ulonglong)in_RAX >> 0x20),(int)uVar1) | uVar1 & 0xffffffff00000000;
}


// ==== FUN_000002e0 @ 000002e0

void FUN_000002e0(void)

{
  return;
}


// ==== FUN_000002f0 @ 000002f0

void FUN_000002f0(void)

{
  return;
}


// ==== FUN_00000300 @ 00000300

ulonglong FUN_00000300(void)

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


// ==== entry @ 00000310

undefined8 entry(undefined8 param_1,longlong param_2)

{
  FUN_00000348(param_1,param_2);
  if (DAT_00000bf8 == 0) {
    DAT_00000bf0 = *(undefined8 *)(param_2 + 0x58);
    DAT_00000bf8 = param_2;
  }
  FUN_00000454();
  return 0;
}


// ==== FUN_00000348 @ 00000348

void FUN_00000348(undefined8 param_1,longlong param_2)

{
  uint uVar1;
  int iVar2;
  short *psVar3;
  ulonglong uVar4;
  longlong lVar5;
  
  DAT_00000be8 = *(longlong *)(param_2 + 0x60);
  DAT_00000be0 = param_2;
  FUN_000008e8();
  psVar3 = (short *)FUN_000008e8();
  do {
    if (*psVar3 == -1) {
      psVar3 = (short *)0x0;
LAB_0000039c:
      if (psVar3 == (short *)0x0) {
        uVar4 = FUN_00000300();
        FUN_000002f0();
        uVar1 = in(0x1808);
        FUN_000002d0();
        while (iVar2 = in(0x1808), (((uVar1 & 0xffffff) + 0x16b) - iVar2 >> 0x17 & 1) == 0) {
          FUN_000002c0();
        }
        FUN_000002d0();
        if ((uVar4 >> 9 & 1) == 0) {
          FUN_000002f0();
        }
        else {
          FUN_000002e0();
        }
LAB_00000405:
        if ((DAT_00000c08 != (undefined8 *)0x0) ||
           (lVar5 = (**(code **)(DAT_00000be8 + 0x140))(0xb70,0,0xc08), -1 < lVar5)) {
          (*(code *)*DAT_00000c08)(DAT_00000c08,0xc10);
        }
        return;
      }
      if ((DAT_00000b90 == *(longlong *)(psVar3 + 4)) && (DAT_00000b98 == *(longlong *)(psVar3 + 8))
         ) goto LAB_00000405;
    }
    else if (*psVar3 == 4) goto LAB_0000039c;
    psVar3 = (short *)((longlong)psVar3 + (ulonglong)(ushort)psVar3[1]);
  } while( true );
}


// ==== FUN_00000454 @ 00000454

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

longlong FUN_00000454(void)

{
  longlong lVar1;
  undefined8 uVar2;
  undefined1 *puVar3;
  undefined8 uVar4;
  undefined1 local_res8 [8];
  undefined1 local_res10 [8];
  undefined1 local_res18 [8];
  undefined4 local_res20 [2];
  undefined8 local_e8 [2];
  undefined4 local_d8;
  undefined2 local_d4;
  undefined1 local_d2;
  undefined1 local_d1;
  undefined1 local_d0;
  undefined1 local_cf;
  undefined1 local_ce;
  undefined1 local_cd;
  undefined1 local_cc;
  undefined1 local_cb;
  undefined1 local_ca;
  undefined1 local_c9 [8];
  undefined1 local_c1 [8];
  undefined1 local_b9 [8];
  undefined1 local_b1 [8];
  undefined4 local_a9;
  undefined1 local_a5;
  undefined8 local_a4;
  undefined4 local_9c;
  undefined2 local_98;
  undefined1 local_96;
  undefined8 local_94;
  undefined8 local_8c;
  undefined8 local_84;
  undefined4 local_7c;
  undefined2 local_78;
  undefined1 local_76;
  undefined2 local_74;
  undefined1 local_72;
  undefined4 local_71 [22];
  
  local_res20[0] = 7;
  uVar4 = 0xb80;
  local_e8[0] = 0xb4;
  uVar2 = 0xba0;
  lVar1 = (**(code **)(DAT_00000bf0 + 0x48))(0xba0,0xb80,local_res20,local_e8,&local_d8);
  FUN_0000084c(uVar2,uVar4,0x40,local_res8);
  FUN_0000084c(uVar2,uVar4,0x3c,local_res10);
  FUN_0000084c(uVar2,uVar4,0x3d,local_res18);
  if (lVar1 < 0) {
    local_d8 = 0xffffffff;
    puVar3 = local_c9;
    lVar1 = 8;
    local_d4 = _DAT_ff430004;
    local_d2 = local_res8[0];
    local_d1 = local_res10[0];
    local_d0 = local_res18[0];
    local_cf = DAT_ff43002e;
    local_ce = DAT_ff430030;
    local_cd = DAT_ff430031;
    local_cc = DAT_ff430032;
    local_cb = DAT_ff430037;
    local_ca = 10;
    do {
      *puVar3 = puVar3[0xff430024 - (longlong)local_c9];
      puVar3[8] = puVar3[0xff430014 - (longlong)local_c9];
      puVar3[0x10] = puVar3[0xff43003a - (longlong)local_c9];
      puVar3[0x18] = puVar3[0xff430042 - (longlong)local_c9];
      puVar3 = puVar3 + 1;
      lVar1 = lVar1 + -1;
    } while (lVar1 != 0);
    local_a9 = 0xffffffff;
    local_a5 = 0xff;
    local_a4 = 0;
    local_9c = 0xf0000;
    local_98 = 0;
    local_96 = 0;
    local_94 = 0;
    local_8c = 0;
    local_84 = 0;
    local_7c = 0x10000;
    local_78 = 0xff01;
    local_76 = 4;
    local_74 = 0;
    local_72 = 1;
    FUN_00000a40(local_71,0xff,0x4c);
    lVar1 = (**(code **)(DAT_00000bf0 + 0x58))(0xba0,0xb80,local_res20[0],local_e8[0],&local_d8);
  }
  return lVar1;
}


// ==== FUN_00000620 @ 00000620

undefined8 FUN_00000620(char param_1,undefined1 param_2)

{
  undefined2 uVar1;
  byte bVar2;
  ulonglong uVar3;
  
  uVar3 = 0;
  uVar1 = 100;
  if (param_1 != '`') {
    uVar1 = 0x66;
  }
  bVar2 = in(uVar1);
  if ((bVar2 & 2) != 0) {
    do {
      if (0x1ffff < uVar3) {
        return 0x8000000000000007;
      }
      FUN_000009b4(0xf);
      bVar2 = in(uVar1);
      uVar3 = uVar3 + 1;
    } while ((bVar2 & 2) != 0);
    if (0x1ffff < uVar3) {
      return 0x8000000000000007;
    }
  }
  out(uVar1,param_2);
  return 0;
}


// ==== FUN_00000698 @ 00000698

undefined8 FUN_00000698(char param_1)

{
  undefined2 uVar1;
  byte bVar2;
  undefined1 uVar3;
  undefined2 uVar4;
  ulonglong uVar5;
  
  uVar5 = 0;
  uVar1 = 100;
  if (param_1 != '`') {
    uVar1 = 0x66;
  }
  bVar2 = in(uVar1);
  if ((bVar2 & 1) != 0) {
    do {
      if (0x1ffff < uVar5) {
        return 0x8000000000000007;
      }
      uVar4 = 0x60;
      if (param_1 != '`') {
        uVar4 = 0x62;
      }
      uVar3 = in(uVar4);
      out(0x80,uVar3);
      FUN_000009b4(5000);
      bVar2 = in(uVar1);
      uVar5 = uVar5 + 1;
    } while ((bVar2 & 1) != 0);
    if (0x1ffff < uVar5) {
      return 0x8000000000000007;
    }
  }
  return 0;
}


// ==== FUN_00000720 @ 00000720

undefined8 FUN_00000720(char param_1)

{
  undefined2 uVar1;
  byte bVar2;
  ulonglong uVar3;
  
  uVar3 = 0;
  uVar1 = 100;
  if (param_1 != '`') {
    uVar1 = 0x66;
  }
  bVar2 = in(uVar1);
  if ((bVar2 & 2) != 0) {
    do {
      if (0x1ffff < uVar3) {
        return 0x8000000000000007;
      }
      FUN_000009b4(0xf);
      bVar2 = in(uVar1);
      uVar3 = uVar3 + 1;
    } while ((bVar2 & 2) != 0);
    if (0x1ffff < uVar3) {
      return 0x8000000000000007;
    }
  }
  return 0;
}


// ==== FUN_00000784 @ 00000784

longlong FUN_00000784(char param_1,undefined1 param_2,undefined1 param_3)

{
  byte bVar1;
  byte bVar2;
  longlong lVar3;
  ulonglong uVar4;
  undefined2 uVar5;
  
  lVar3 = FUN_00000720(param_1);
  uVar4 = 0;
  if (lVar3 < 0) {
    return lVar3;
  }
  FUN_00000698(param_1);
  FUN_00000620(param_1,param_2);
  FUN_00000720(param_1);
  uVar5 = 0x60;
  bVar1 = 100;
  if (param_1 != '`') {
    bVar1 = 0x66;
  }
  bVar2 = in((ushort)bVar1);
  if ((bVar2 & 2) != 0) {
    do {
      if (0x1ffff < uVar4) goto LAB_00000826;
      FUN_000009b4(0xf);
      bVar2 = in((ushort)bVar1);
      uVar4 = uVar4 + 1;
    } while ((bVar2 & 2) != 0);
    if (0x1ffff < uVar4) goto LAB_00000826;
  }
  if (param_1 != '`') {
    uVar5 = 0x62;
  }
  out(uVar5,param_3);
LAB_00000826:
  FUN_00000698(param_1);
  return lVar3;
}


// ==== FUN_0000084c @ 0000084c

longlong FUN_0000084c(undefined8 param_1,undefined8 param_2,undefined1 param_3,undefined1 *param_4)

{
  byte bVar1;
  undefined1 uVar2;
  longlong lVar3;
  ulonglong uVar4;
  
  uVar4 = 0;
  lVar3 = FUN_00000784('b',0xa3,7);
  if (((-1 < lVar3) && (lVar3 = FUN_00000784('b',0xa2,param_3), -1 < lVar3)) &&
     (lVar3 = FUN_00000620('b',0xa4), -1 < lVar3)) {
    bVar1 = in(0x66);
    if ((bVar1 & 1) == 0) {
      do {
        if (0x1ffff < uVar4) {
          return -0x7ffffffffffffff9;
        }
        FUN_000009b4(0xf);
        bVar1 = in(0x66);
        uVar4 = uVar4 + 1;
      } while ((bVar1 & 1) == 0);
      if (0x1ffff < uVar4) {
        return -0x7ffffffffffffff9;
      }
    }
    uVar2 = in(0x62);
    *param_4 = uVar2;
    lVar3 = 0;
  }
  return lVar3;
}


// ==== FUN_000008e8 @ 000008e8

longlong FUN_000008e8(void)

{
  ulonglong uVar1;
  longlong *plVar2;
  
  uVar1 = 0;
  if (DAT_00000c00 == 0) {
    DAT_00000c00 = 0;
    if (*(ulonglong *)(DAT_00000be0 + 0x68) != 0) {
      plVar2 = *(longlong **)(DAT_00000be0 + 0x70);
      do {
        if ((DAT_00000b60 == *plVar2) && (DAT_00000b68 == plVar2[1])) {
          DAT_00000c00 = (*(longlong **)(DAT_00000be0 + 0x70))[uVar1 * 3 + 2];
          return DAT_00000c00;
        }
        uVar1 = uVar1 + 1;
        plVar2 = plVar2 + 3;
      } while (uVar1 < *(ulonglong *)(DAT_00000be0 + 0x68));
    }
  }
  return DAT_00000c00;
}


// ==== FUN_00000954 @ 00000954

void FUN_00000954(uint param_1)

{
  uint uVar1;
  int iVar2;
  uint uVar3;
  int iVar4;
  uint uVar5;
  bool bVar6;
  
  uVar5 = param_1 & 0x3fffff;
  uVar3 = param_1 >> 0x16;
  do {
    uVar1 = in(0x1808);
    iVar4 = (uVar1 & 0xffffff) + uVar5;
    uVar5 = 0x400000;
    while (iVar2 = in(0x1808), ((uint)(iVar4 - iVar2) >> 0x17 & 1) == 0) {
      FUN_000002c0();
    }
    bVar6 = uVar3 != 0;
    uVar3 = uVar3 - 1;
  } while (bVar6);
  return;
}


// ==== FUN_000009b4 @ 000009b4

longlong FUN_000009b4(longlong param_1)

{
  FUN_00000954((uint)((ulonglong)(param_1 * 0x369e99) / 1000000));
  return param_1;
}


// ==== FUN_00000a40 @ 00000a40

undefined4 * FUN_00000a40(undefined4 *param_1,undefined1 param_2,ulonglong param_3)

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


