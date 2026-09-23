// OemSWBoardIDDxe.efi: Ghidra x86:LE:64:default decompile, unedited
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

void entry(undefined8 param_1,longlong param_2)

{
  byte bVar1;
  
  bVar1 = (byte)param_1;
  FUN_0000032c(param_1,param_2);
  FUN_00000438(bVar1,param_2);
  return;
}


// ==== FUN_0000032c @ 0000032c

void FUN_0000032c(undefined8 param_1,longlong param_2)

{
  uint uVar1;
  int iVar2;
  short *psVar3;
  ulonglong uVar4;
  longlong lVar5;
  
  DAT_00000a98 = *(longlong *)(param_2 + 0x60);
  DAT_00000a90 = param_2;
  FUN_000007c4();
  psVar3 = (short *)FUN_000007c4();
  do {
    if (*psVar3 == -1) {
      psVar3 = (short *)0x0;
LAB_00000380:
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
LAB_000003e9:
        if ((DAT_00000ab8 != (undefined8 *)0x0) ||
           (lVar5 = (**(code **)(DAT_00000a98 + 0x140))(0xa50,0,0xab8), -1 < lVar5)) {
          (*(code *)*DAT_00000ab8)(DAT_00000ab8,0xac0);
        }
        return;
      }
      if ((DAT_00000a60 == *(longlong *)(psVar3 + 4)) && (DAT_00000a68 == *(longlong *)(psVar3 + 8))
         ) goto LAB_000003e9;
    }
    else if (*psVar3 == 4) goto LAB_00000380;
    psVar3 = (short *)((longlong)psVar3 + (ulonglong)(ushort)psVar3[1]);
  } while( true );
}


// ==== FUN_00000438 @ 00000438

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

undefined8 FUN_00000438(byte param_1,longlong param_2)

{
  byte bVar1;
  byte bVar2;
  longlong lVar3;
  ulonglong uVar4;
  
  bVar1 = DAT_ff43000f;
  uVar4 = 0;
  if (DAT_00000aa8 == 0) {
    _DAT_00000aa0 = *(undefined8 *)(param_2 + 0x58);
    DAT_00000aa8 = param_2;
  }
  out(0x70,0x7d);
  out(0x71,DAT_ff43000f);
  if (DAT_ff43000f == 0xff) {
    return 0;
  }
  if ((DAT_ff43000f & 1) != 0) {
    for (; (bVar2 = in(0x66), (bVar2 & 2) != 0 && (uVar4 < 0x20000)); uVar4 = uVar4 + 1) {
    }
    out(0x66,0x7c);
  }
  if ((DAT_ff43000f & 2) == 0) goto LAB_0000056b;
  uVar4 = 0;
  lVar3 = FUN_000006fc('b',0xa3,4);
  if (((-1 < lVar3) && (lVar3 = FUN_000006fc('b',0xa2,0x9f), -1 < lVar3)) &&
     (lVar3 = FUN_00000598('b',0xa4), -1 < lVar3)) {
    bVar2 = in(0x66);
    if ((bVar2 & 1) == 0) {
      do {
        if (0x1ffff < uVar4) goto LAB_0000052a;
        FUN_00000890(0xf);
        bVar2 = in(0x66);
        uVar4 = uVar4 + 1;
      } while ((bVar2 & 1) == 0);
      if (0x1ffff < uVar4) goto LAB_0000052a;
    }
    param_1 = in(0x62);
  }
LAB_0000052a:
  lVar3 = FUN_000006fc('b',0xa3,4);
  if ((-1 < lVar3) && (lVar3 = FUN_000006fc('b',0xa2,0x9f), -1 < lVar3)) {
    FUN_000006fc('b',0xa5,param_1 | 1);
  }
  out(0x70,0x79);
  out(0x71,0x9f);
LAB_0000056b:
  if ((bVar1 & 0x40) != 0) {
    out(0x70,0x7a);
    out(0x71,1);
  }
  return 0;
}


// ==== FUN_00000598 @ 00000598

undefined8 FUN_00000598(char param_1,undefined1 param_2)

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
      FUN_00000890(0xf);
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


// ==== FUN_00000610 @ 00000610

undefined8 FUN_00000610(char param_1)

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
      FUN_00000890(5000);
      bVar2 = in(uVar1);
      uVar5 = uVar5 + 1;
    } while ((bVar2 & 1) != 0);
    if (0x1ffff < uVar5) {
      return 0x8000000000000007;
    }
  }
  return 0;
}


// ==== FUN_00000698 @ 00000698

undefined8 FUN_00000698(char param_1)

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
      FUN_00000890(0xf);
      bVar2 = in(uVar1);
      uVar3 = uVar3 + 1;
    } while ((bVar2 & 2) != 0);
    if (0x1ffff < uVar3) {
      return 0x8000000000000007;
    }
  }
  return 0;
}


// ==== FUN_000006fc @ 000006fc

longlong FUN_000006fc(char param_1,undefined1 param_2,undefined1 param_3)

{
  byte bVar1;
  byte bVar2;
  longlong lVar3;
  ulonglong uVar4;
  undefined2 uVar5;
  
  lVar3 = FUN_00000698(param_1);
  uVar4 = 0;
  if (lVar3 < 0) {
    return lVar3;
  }
  FUN_00000610(param_1);
  FUN_00000598(param_1,param_2);
  FUN_00000698(param_1);
  uVar5 = 0x60;
  bVar1 = 100;
  if (param_1 != '`') {
    bVar1 = 0x66;
  }
  bVar2 = in((ushort)bVar1);
  if ((bVar2 & 2) != 0) {
    do {
      if (0x1ffff < uVar4) goto LAB_0000079e;
      FUN_00000890(0xf);
      bVar2 = in((ushort)bVar1);
      uVar4 = uVar4 + 1;
    } while ((bVar2 & 2) != 0);
    if (0x1ffff < uVar4) goto LAB_0000079e;
  }
  if (param_1 != '`') {
    uVar5 = 0x62;
  }
  out(uVar5,param_3);
LAB_0000079e:
  FUN_00000610(param_1);
  return lVar3;
}


// ==== FUN_000007c4 @ 000007c4

longlong FUN_000007c4(void)

{
  ulonglong uVar1;
  longlong *plVar2;
  
  uVar1 = 0;
  if (DAT_00000ab0 == 0) {
    DAT_00000ab0 = 0;
    if (*(ulonglong *)(DAT_00000a90 + 0x68) != 0) {
      plVar2 = *(longlong **)(DAT_00000a90 + 0x70);
      do {
        if ((DAT_00000a40 == *plVar2) && (DAT_00000a48 == plVar2[1])) {
          DAT_00000ab0 = (*(longlong **)(DAT_00000a90 + 0x70))[uVar1 * 3 + 2];
          return DAT_00000ab0;
        }
        uVar1 = uVar1 + 1;
        plVar2 = plVar2 + 3;
      } while (uVar1 < *(ulonglong *)(DAT_00000a90 + 0x68));
    }
  }
  return DAT_00000ab0;
}


// ==== FUN_00000830 @ 00000830

void FUN_00000830(uint param_1)

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


// ==== FUN_00000890 @ 00000890

longlong FUN_00000890(longlong param_1)

{
  FUN_00000830((uint)((ulonglong)(param_1 * 0x369e99) / 1000000));
  return param_1;
}


