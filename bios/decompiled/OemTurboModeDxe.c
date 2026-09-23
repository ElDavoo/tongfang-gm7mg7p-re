// OemTurboModeDxe.efi: Ghidra x86:LE:64:default decompile, unedited
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
  if (DAT_00000b50 == 0) {
    DAT_00000b40 = *(longlong *)(param_2 + 0x60);
    DAT_00000b48 = *(undefined8 *)(param_2 + 0x58);
    DAT_00000b50 = param_2;
  }
  (**(code **)(DAT_00000b40 + 0x170))(0x200,0x10,0x494,0,0xab0,local_res18);
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
  
  DAT_00000b38 = *(longlong *)(param_2 + 0x60);
  DAT_00000b30 = param_2;
  FUN_00000840();
  psVar3 = (short *)FUN_00000840();
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
        if ((DAT_00000b60 != (undefined8 *)0x0) ||
           (lVar5 = (**(code **)(DAT_00000b38 + 0x140))(0xac0,0,0xb60), -1 < lVar5)) {
          (*(code *)*DAT_00000b60)(DAT_00000b60,0xb68);
        }
        return;
      }
      if ((DAT_00000ae0 == *(longlong *)(psVar3 + 4)) && (DAT_00000ae8 == *(longlong *)(psVar3 + 8))
         ) goto LAB_00000445;
    }
    else if (*psVar3 == 4) goto LAB_000003dc;
    psVar3 = (short *)((longlong)psVar3 + (ulonglong)(ushort)psVar3[1]);
  } while( true );
}


// ==== FUN_00000494 @ 00000494

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_00000494(void)

{
  char cVar1;
  byte bVar2;
  longlong lVar3;
  uint uVar4;
  ulonglong uVar5;
  undefined8 local_res18 [2];
  int local_c8 [48];
  
  cVar1 = DAT_ff430036;
  uVar5 = 0;
  lVar3 = FUN_00000778('b',0xa3,4);
  bVar2 = (byte)local_res18[0];
  if (-1 < lVar3) {
    lVar3 = FUN_00000778('b',0xa2,0x9f);
    bVar2 = (byte)local_res18[0];
    if (-1 < lVar3) {
      lVar3 = FUN_00000614('b',0xa4);
      bVar2 = (byte)local_res18[0];
      if (-1 < lVar3) {
        bVar2 = in(0x66);
        if ((bVar2 & 1) == 0) {
          do {
            bVar2 = (byte)local_res18[0];
            if (0x1ffff < uVar5) goto LAB_00000521;
            FUN_0000090c(0xf);
            bVar2 = in(0x66);
            uVar5 = uVar5 + 1;
          } while ((bVar2 & 1) == 0);
          bVar2 = (byte)local_res18[0];
          if (0x1ffff < uVar5) goto LAB_00000521;
        }
        bVar2 = in(0x62);
      }
    }
  }
LAB_00000521:
  if (cVar1 != -1) {
    local_res18[0] = 0xb4;
    (**(code **)(DAT_00000b48 + 0x48))(0xaf0,0xad0,0,local_res18,local_c8);
    if (((((_DAT_e0000054 & 8) == 0) ||
         (uVar4 = *(uint *)((((ulonglong)(_DAT_e0008018 >> 8) & 0xff) + 0xe00) * 0x100000),
         (short)uVar4 != 0x10de)) ||
        (((uVar4 = uVar4 >> 0x10, uVar4 == 0x1c91 || (uVar4 == 0x1f10)) &&
         (local_c8[0] != 0x105e1d05)))) || (cVar1 == '\0')) {
      bVar2 = bVar2 & 0xfc;
    }
    else if (cVar1 == '\x01') {
      bVar2 = bVar2 & 0xfe | 2;
    }
    else if (cVar1 == '\x02') {
      bVar2 = bVar2 & 0xfd | 1;
    }
    lVar3 = FUN_00000778('b',0xa3,4);
    if ((-1 < lVar3) && (lVar3 = FUN_00000778('b',0xa2,0x9f), -1 < lVar3)) {
      FUN_00000778('b',0xa5,bVar2);
    }
  }
  return;
}


// ==== FUN_00000614 @ 00000614

undefined8 FUN_00000614(char param_1,undefined1 param_2)

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
      FUN_0000090c(0xf);
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


// ==== FUN_0000068c @ 0000068c

undefined8 FUN_0000068c(char param_1)

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
      FUN_0000090c(5000);
      bVar2 = in(uVar1);
      uVar5 = uVar5 + 1;
    } while ((bVar2 & 1) != 0);
    if (0x1ffff < uVar5) {
      return 0x8000000000000007;
    }
  }
  return 0;
}


// ==== FUN_00000714 @ 00000714

undefined8 FUN_00000714(char param_1)

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
      FUN_0000090c(0xf);
      bVar2 = in(uVar1);
      uVar3 = uVar3 + 1;
    } while ((bVar2 & 2) != 0);
    if (0x1ffff < uVar3) {
      return 0x8000000000000007;
    }
  }
  return 0;
}


// ==== FUN_00000778 @ 00000778

longlong FUN_00000778(char param_1,undefined1 param_2,undefined1 param_3)

{
  byte bVar1;
  byte bVar2;
  longlong lVar3;
  ulonglong uVar4;
  undefined2 uVar5;
  
  lVar3 = FUN_00000714(param_1);
  uVar4 = 0;
  if (lVar3 < 0) {
    return lVar3;
  }
  FUN_0000068c(param_1);
  FUN_00000614(param_1,param_2);
  FUN_00000714(param_1);
  uVar5 = 0x60;
  bVar1 = 100;
  if (param_1 != '`') {
    bVar1 = 0x66;
  }
  bVar2 = in((ushort)bVar1);
  if ((bVar2 & 2) != 0) {
    do {
      if (0x1ffff < uVar4) goto LAB_0000081a;
      FUN_0000090c(0xf);
      bVar2 = in((ushort)bVar1);
      uVar4 = uVar4 + 1;
    } while ((bVar2 & 2) != 0);
    if (0x1ffff < uVar4) goto LAB_0000081a;
  }
  if (param_1 != '`') {
    uVar5 = 0x62;
  }
  out(uVar5,param_3);
LAB_0000081a:
  FUN_0000068c(param_1);
  return lVar3;
}


// ==== FUN_00000840 @ 00000840

longlong FUN_00000840(void)

{
  ulonglong uVar1;
  longlong *plVar2;
  
  uVar1 = 0;
  if (DAT_00000b58 == 0) {
    DAT_00000b58 = 0;
    if (*(ulonglong *)(DAT_00000b30 + 0x68) != 0) {
      plVar2 = *(longlong **)(DAT_00000b30 + 0x70);
      do {
        if ((DAT_00000aa0 == *plVar2) && (DAT_00000aa8 == plVar2[1])) {
          DAT_00000b58 = (*(longlong **)(DAT_00000b30 + 0x70))[uVar1 * 3 + 2];
          return DAT_00000b58;
        }
        uVar1 = uVar1 + 1;
        plVar2 = plVar2 + 3;
      } while (uVar1 < *(ulonglong *)(DAT_00000b30 + 0x68));
    }
  }
  return DAT_00000b58;
}


// ==== FUN_000008ac @ 000008ac

void FUN_000008ac(uint param_1)

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


// ==== FUN_0000090c @ 0000090c

longlong FUN_0000090c(longlong param_1)

{
  FUN_000008ac((uint)((ulonglong)(param_1 * 0x369e99) / 1000000));
  return param_1;
}


