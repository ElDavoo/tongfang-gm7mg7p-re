// OemPowerModeDxe.efi: Ghidra x86:LE:64:default decompile, unedited
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
  undefined1 local_res18 [16];
  
  FUN_00000388(param_1,param_2);
  if (DAT_00000c70 == 0) {
    DAT_00000c60 = *(longlong *)(param_2 + 0x60);
    DAT_00000c68 = *(undefined8 *)(param_2 + 0x58);
    DAT_00000c70 = param_2;
  }
  (**(code **)(DAT_00000c60 + 0x170))(0x200,8,0x494,0,0xbc0,local_res18);
  return 0;
}


// ==== FUN_00000388 @ 00000388

void FUN_00000388(undefined8 param_1,longlong param_2)

{
  uint uVar1;
  int iVar2;
  short *psVar3;
  ulonglong uVar4;
  longlong lVar5;
  
  DAT_00000c58 = *(longlong *)(param_2 + 0x60);
  DAT_00000c50 = param_2;
  FUN_00000938();
  psVar3 = (short *)FUN_00000938();
  do {
    if (*psVar3 == -1) {
      psVar3 = (short *)0x0;
LAB_000003dc:
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
LAB_00000445:
        if ((DAT_00000c80 != (undefined8 *)0x0) ||
           (lVar5 = (**(code **)(DAT_00000c58 + 0x140))(0xbd0,0,0xc80), -1 < lVar5)) {
          (*(code *)*DAT_00000c80)(DAT_00000c80,0xc88);
        }
        return;
      }
      if ((DAT_00000bf0 == *(longlong *)(psVar3 + 4)) && (DAT_00000bf8 == *(longlong *)(psVar3 + 8))
         ) goto LAB_00000445;
    }
    else if (*psVar3 == 4) goto LAB_000003dc;
    psVar3 = (short *)((longlong)psVar3 + (ulonglong)(ushort)psVar3[1]);
  } while( true );
}


// ==== FUN_00000494 @ 00000494

longlong FUN_00000494(void)

{
  byte bVar1;
  undefined1 uVar2;
  longlong lVar3;
  longlong lVar4;
  uint uVar5;
  ulonglong uVar6;
  undefined8 uVar7;
  undefined1 local_res18 [8];
  byte local_res20 [8];
  undefined4 local_8c8;
  undefined4 local_8c4;
  undefined8 local_8c0;
  undefined8 local_8b8 [2];
  undefined1 local_8a8 [47];
  char local_879;
  undefined1 local_7e8 [1999];
  char local_19;
  byte local_17;
  
  bVar1 = DAT_ff430034;
  local_8c8 = 7;
  local_8b8[0] = 0x7d8;
  lVar3 = (**(code **)(DAT_00000c68 + 0x48))(0xc00,0xba0,&local_8c4,local_8b8,local_7e8);
  if (lVar3 < 0) {
    return lVar3;
  }
  local_8c0 = 0xb4;
  uVar6 = 0xc10;
  lVar3 = (**(code **)(DAT_00000c68 + 0x48))(0xc10,0xbe0,&local_8c8,&local_8c0,local_8a8);
  if (lVar3 < 0) {
    return lVar3;
  }
  if (local_879 != -1) goto LAB_00000569;
  uVar5 = (uint)bVar1;
  uVar6 = (ulonglong)(uVar5 - 0x21);
  if (uVar5 - 0x21 == 0) {
LAB_00000563:
    local_879 = '\0';
  }
  else {
    uVar6 = (ulonglong)(uVar5 - 0x22);
    if (uVar5 - 0x22 != 0) {
      uVar5 = uVar5 - 0x23;
      uVar6 = (ulonglong)uVar5;
      if ((uVar5 == 0) || (uVar5 != 1)) goto LAB_00000563;
    }
    local_879 = '\x01';
  }
LAB_00000569:
  local_19 = local_879;
  FUN_0000089c(uVar6,4,0x9f,local_res20);
  if (local_19 == '\0') {
    local_res18[0] = 0xa0;
  }
  else if (local_19 == '\x01') {
    local_res18[0] = 0;
  }
  else if (local_19 == '\x02') {
    local_res18[0] = 0x10;
  }
  uVar2 = local_res18[0];
  local_17 = local_res20[0] >> 1 & 1;
  (**(code **)(DAT_00000c68 + 0x58))(0xc10,0xbe0,local_8c8,local_8c0,local_8a8);
  uVar7 = 0xc00;
  lVar3 = (**(code **)(DAT_00000c68 + 0x58))(0xc00,0xba0,local_8c4,local_8b8[0],local_7e8);
  uVar7 = CONCAT71((int7)((ulonglong)uVar7 >> 8),0x62);
  lVar4 = FUN_000007d4('b',0xa3,7);
  if (-1 < lVar4) {
    uVar7 = CONCAT71((int7)((ulonglong)uVar7 >> 8),0x62);
    lVar4 = FUN_000007d4('b',0xa2,0x51);
    if (-1 < lVar4) {
      uVar7 = CONCAT71((int7)((ulonglong)uVar7 >> 8),0x62);
      FUN_000007d4('b',0xa5,uVar2);
    }
  }
  FUN_0000089c(uVar7,7,0x51,local_res18);
  return lVar3;
}


// ==== FUN_00000670 @ 00000670

undefined8 FUN_00000670(char param_1,undefined1 param_2)

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
      FUN_00000a04(0xf);
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


// ==== FUN_000006e8 @ 000006e8

undefined8 FUN_000006e8(char param_1)

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
      FUN_00000a04(5000);
      bVar2 = in(uVar1);
      uVar5 = uVar5 + 1;
    } while ((bVar2 & 1) != 0);
    if (0x1ffff < uVar5) {
      return 0x8000000000000007;
    }
  }
  return 0;
}


// ==== FUN_00000770 @ 00000770

undefined8 FUN_00000770(char param_1)

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
      FUN_00000a04(0xf);
      bVar2 = in(uVar1);
      uVar3 = uVar3 + 1;
    } while ((bVar2 & 2) != 0);
    if (0x1ffff < uVar3) {
      return 0x8000000000000007;
    }
  }
  return 0;
}


// ==== FUN_000007d4 @ 000007d4

longlong FUN_000007d4(char param_1,undefined1 param_2,undefined1 param_3)

{
  byte bVar1;
  byte bVar2;
  longlong lVar3;
  ulonglong uVar4;
  undefined2 uVar5;
  
  lVar3 = FUN_00000770(param_1);
  uVar4 = 0;
  if (lVar3 < 0) {
    return lVar3;
  }
  FUN_000006e8(param_1);
  FUN_00000670(param_1,param_2);
  FUN_00000770(param_1);
  uVar5 = 0x60;
  bVar1 = 100;
  if (param_1 != '`') {
    bVar1 = 0x66;
  }
  bVar2 = in((ushort)bVar1);
  if ((bVar2 & 2) != 0) {
    do {
      if (0x1ffff < uVar4) goto LAB_00000876;
      FUN_00000a04(0xf);
      bVar2 = in((ushort)bVar1);
      uVar4 = uVar4 + 1;
    } while ((bVar2 & 2) != 0);
    if (0x1ffff < uVar4) goto LAB_00000876;
  }
  if (param_1 != '`') {
    uVar5 = 0x62;
  }
  out(uVar5,param_3);
LAB_00000876:
  FUN_000006e8(param_1);
  return lVar3;
}


// ==== FUN_0000089c @ 0000089c

longlong FUN_0000089c(undefined8 param_1,undefined1 param_2,undefined1 param_3,undefined1 *param_4)

{
  byte bVar1;
  undefined1 uVar2;
  longlong lVar3;
  ulonglong uVar4;
  
  uVar4 = 0;
  lVar3 = FUN_000007d4('b',0xa3,param_2);
  if (((-1 < lVar3) && (lVar3 = FUN_000007d4('b',0xa2,param_3), -1 < lVar3)) &&
     (lVar3 = FUN_00000670('b',0xa4), -1 < lVar3)) {
    bVar1 = in(0x66);
    if ((bVar1 & 1) == 0) {
      do {
        if (0x1ffff < uVar4) {
          return -0x7ffffffffffffff9;
        }
        FUN_00000a04(0xf);
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


// ==== FUN_00000938 @ 00000938

longlong FUN_00000938(void)

{
  ulonglong uVar1;
  longlong *plVar2;
  
  uVar1 = 0;
  if (DAT_00000c78 == 0) {
    DAT_00000c78 = 0;
    if (*(ulonglong *)(DAT_00000c50 + 0x68) != 0) {
      plVar2 = *(longlong **)(DAT_00000c50 + 0x70);
      do {
        if ((DAT_00000bb0 == *plVar2) && (DAT_00000bb8 == plVar2[1])) {
          DAT_00000c78 = (*(longlong **)(DAT_00000c50 + 0x70))[uVar1 * 3 + 2];
          return DAT_00000c78;
        }
        uVar1 = uVar1 + 1;
        plVar2 = plVar2 + 3;
      } while (uVar1 < *(ulonglong *)(DAT_00000c50 + 0x68));
    }
  }
  return DAT_00000c78;
}


// ==== FUN_000009a4 @ 000009a4

void FUN_000009a4(uint param_1)

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


// ==== FUN_00000a04 @ 00000a04

longlong FUN_00000a04(longlong param_1)

{
  FUN_000009a4((uint)((ulonglong)(param_1 * 0x369e99) / 1000000));
  return param_1;
}


