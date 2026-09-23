// OemKbLightSupportDxe.efi: Ghidra x86:LE:64:default decompile, unedited
// ==== FUN_00000260 @ 00000260

void FUN_00000260(void)

{
  return;
}


// ==== FUN_00000270 @ 00000270

ulonglong FUN_00000270(void)

{
  ulonglong uVar1;
  undefined8 in_RAX;
  
  uVar1 = rdtsc();
  return CONCAT44((int)((ulonglong)in_RAX >> 0x20),(int)uVar1) | uVar1 & 0xffffffff00000000;
}


// ==== FUN_00000280 @ 00000280

void FUN_00000280(void)

{
  return;
}


// ==== FUN_00000290 @ 00000290

void FUN_00000290(void)

{
  return;
}


// ==== FUN_000002a0 @ 000002a0

ulonglong FUN_000002a0(void)

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

void entry(undefined8 param_1,longlong param_2)

{
  FUN_00000324(param_1,param_2);
  FUN_00000430();
  return;
}


// ==== FUN_00000324 @ 00000324

void FUN_00000324(undefined8 param_1,longlong param_2)

{
  uint uVar1;
  int iVar2;
  short *psVar3;
  ulonglong uVar4;
  longlong lVar5;
  
  DAT_000008d8 = *(longlong *)(param_2 + 0x60);
  DAT_000008d0 = param_2;
  FUN_00000764();
  psVar3 = (short *)FUN_00000764();
  do {
    if (*psVar3 == -1) {
      psVar3 = (short *)0x0;
LAB_00000378:
      if (psVar3 == (short *)0x0) {
        uVar4 = FUN_000002a0();
        FUN_00000290();
        uVar1 = in(0x1808);
        FUN_00000270();
        while (iVar2 = in(0x1808), (((uVar1 & 0xffffff) + 0x16b) - iVar2 >> 0x17 & 1) == 0) {
          FUN_00000260();
        }
        FUN_00000270();
        if ((uVar4 >> 9 & 1) == 0) {
          FUN_00000290();
        }
        else {
          FUN_00000280();
        }
LAB_000003e1:
        if ((DAT_000008e8 != (undefined8 *)0x0) ||
           (lVar5 = (**(code **)(DAT_000008d8 + 0x140))(0x890,0,0x8e8), -1 < lVar5)) {
          (*(code *)*DAT_000008e8)(DAT_000008e8,0x8f0);
        }
        return;
      }
      if ((DAT_000008a0 == *(longlong *)(psVar3 + 4)) && (DAT_000008a8 == *(longlong *)(psVar3 + 8))
         ) goto LAB_000003e1;
    }
    else if (*psVar3 == 4) goto LAB_00000378;
    psVar3 = (short *)((longlong)psVar3 + (ulonglong)(ushort)psVar3[1]);
  } while( true );
}


// ==== FUN_00000430 @ 00000430

undefined8 FUN_00000430(void)

{
  char cVar1;
  byte bVar2;
  longlong lVar3;
  ulonglong uVar4;
  
  cVar1 = DAT_ff430035;
  uVar4 = 0;
  lVar3 = FUN_00000648('b',0xa3,7);
  if (((-1 < lVar3) && (lVar3 = FUN_00000648('b',0xa2,0x8c), -1 < lVar3)) &&
     (lVar3 = FUN_000004e4('b',0xa4), -1 < lVar3)) {
    bVar2 = in(0x66);
    if ((bVar2 & 1) == 0) {
      do {
        if (0x1ffff < uVar4) goto LAB_000004ba;
        FUN_00000830(0xf);
        bVar2 = in(0x66);
        uVar4 = uVar4 + 1;
      } while ((bVar2 & 1) == 0);
      if (0x1ffff < uVar4) goto LAB_000004ba;
    }
    in(0x62);
  }
LAB_000004ba:
  if ((cVar1 == '\0') || (cVar1 == '\x01')) {
    FUN_00000710();
  }
  return 0;
}


// ==== FUN_000004e4 @ 000004e4

undefined8 FUN_000004e4(char param_1,undefined1 param_2)

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
      FUN_00000830(0xf);
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


// ==== FUN_0000055c @ 0000055c

undefined8 FUN_0000055c(char param_1)

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
      FUN_00000830(5000);
      bVar2 = in(uVar1);
      uVar5 = uVar5 + 1;
    } while ((bVar2 & 1) != 0);
    if (0x1ffff < uVar5) {
      return 0x8000000000000007;
    }
  }
  return 0;
}


// ==== FUN_000005e4 @ 000005e4

undefined8 FUN_000005e4(char param_1)

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
      FUN_00000830(0xf);
      bVar2 = in(uVar1);
      uVar3 = uVar3 + 1;
    } while ((bVar2 & 2) != 0);
    if (0x1ffff < uVar3) {
      return 0x8000000000000007;
    }
  }
  return 0;
}


// ==== FUN_00000648 @ 00000648

longlong FUN_00000648(char param_1,undefined1 param_2,undefined1 param_3)

{
  byte bVar1;
  byte bVar2;
  longlong lVar3;
  ulonglong uVar4;
  undefined2 uVar5;
  
  lVar3 = FUN_000005e4(param_1);
  uVar4 = 0;
  if (lVar3 < 0) {
    return lVar3;
  }
  FUN_0000055c(param_1);
  FUN_000004e4(param_1,param_2);
  FUN_000005e4(param_1);
  uVar5 = 0x60;
  bVar1 = 100;
  if (param_1 != '`') {
    bVar1 = 0x66;
  }
  bVar2 = in((ushort)bVar1);
  if ((bVar2 & 2) != 0) {
    do {
      if (0x1ffff < uVar4) goto LAB_000006ea;
      FUN_00000830(0xf);
      bVar2 = in((ushort)bVar1);
      uVar4 = uVar4 + 1;
    } while ((bVar2 & 2) != 0);
    if (0x1ffff < uVar4) goto LAB_000006ea;
  }
  if (param_1 != '`') {
    uVar5 = 0x62;
  }
  out(uVar5,param_3);
LAB_000006ea:
  FUN_0000055c(param_1);
  return lVar3;
}


// ==== FUN_00000710 @ 00000710

longlong FUN_00000710(void)

{
  longlong lVar1;
  longlong lVar2;
  undefined1 in_R9B;
  
  lVar1 = FUN_00000648('b',0xa3,7);
  if (((-1 < lVar1) && (lVar1 = FUN_00000648('b',0xa2,0x8c), -1 < lVar1)) &&
     (lVar2 = FUN_00000648('b',0xa5,in_R9B), lVar1 = 0, lVar2 < 0)) {
    lVar1 = lVar2;
  }
  return lVar1;
}


// ==== FUN_00000764 @ 00000764

longlong FUN_00000764(void)

{
  ulonglong uVar1;
  longlong *plVar2;
  
  uVar1 = 0;
  if (DAT_000008e0 == 0) {
    DAT_000008e0 = 0;
    if (*(ulonglong *)(DAT_000008d0 + 0x68) != 0) {
      plVar2 = *(longlong **)(DAT_000008d0 + 0x70);
      do {
        if ((DAT_00000880 == *plVar2) && (DAT_00000888 == plVar2[1])) {
          DAT_000008e0 = (*(longlong **)(DAT_000008d0 + 0x70))[uVar1 * 3 + 2];
          return DAT_000008e0;
        }
        uVar1 = uVar1 + 1;
        plVar2 = plVar2 + 3;
      } while (uVar1 < *(ulonglong *)(DAT_000008d0 + 0x68));
    }
  }
  return DAT_000008e0;
}


// ==== FUN_000007d0 @ 000007d0

void FUN_000007d0(uint param_1)

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
      FUN_00000260();
    }
    bVar6 = uVar3 != 0;
    uVar3 = uVar3 - 1;
  } while (bVar6);
  return;
}


// ==== FUN_00000830 @ 00000830

longlong FUN_00000830(longlong param_1)

{
  FUN_000007d0((uint)((ulonglong)(param_1 * 0x369e99) / 1000000));
  return param_1;
}


