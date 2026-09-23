// OemManufactureModeDxe.efi: Ghidra x86:LE:64:default decompile, unedited
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

void entry(ulonglong param_1,longlong param_2)

{
  FUN_0000032c(param_1,param_2);
  FUN_00000438(param_1,param_2);
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
  
  DAT_00000b08 = *(longlong *)(param_2 + 0x60);
  DAT_00000b00 = param_2;
  FUN_000007e4();
  psVar3 = (short *)FUN_000007e4();
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
        if ((DAT_00000b28 != (undefined8 *)0x0) ||
           (lVar5 = (**(code **)(DAT_00000b08 + 0x140))(0xa70,0,0xb28), -1 < lVar5)) {
          (*(code *)*DAT_00000b28)(DAT_00000b28,0xb30);
        }
        return;
      }
      if ((DAT_00000a90 == *(longlong *)(psVar3 + 4)) && (DAT_00000a98 == *(longlong *)(psVar3 + 8))
         ) goto LAB_000003e9;
    }
    else if (*psVar3 == 4) goto LAB_00000380;
    psVar3 = (short *)((longlong)psVar3 + (ulonglong)(ushort)psVar3[1]);
  } while( true );
}


// ==== FUN_00000438 @ 00000438

longlong FUN_00000438(ulonglong param_1,longlong param_2)

{
  byte bVar1;
  longlong lVar2;
  ulonglong uVar3;
  ulonglong local_res8;
  undefined4 local_res18 [2];
  char local_res20 [8];
  undefined8 local_28;
  undefined4 local_20;
  undefined4 local_1c;
  undefined4 local_18;
  undefined4 local_14;
  
  local_res18[0] = 0;
  if (DAT_00000b18 == 0) {
    DAT_00000b10 = *(longlong *)(param_2 + 0x58);
    DAT_00000b18 = param_2;
  }
  local_28 = 7;
  uVar3 = 0;
  local_res8 = param_1;
  lVar2 = FUN_0000071c('b',0xa3,7);
  if (-1 < lVar2) {
    lVar2 = FUN_0000071c('b',0xa2,0xa4);
    if (-1 < lVar2) {
      lVar2 = FUN_000005b8('b',0xa4);
      if (-1 < lVar2) {
        bVar1 = in(0x66);
        if ((bVar1 & 1) == 0) {
          do {
            if (0x1ffff < uVar3) goto LAB_000004df;
            FUN_000008b0(0xf);
            bVar1 = in(0x66);
            uVar3 = uVar3 + 1;
          } while ((bVar1 & 1) == 0);
          if (0x1ffff < uVar3) goto LAB_000004df;
        }
        bVar1 = in(0x62);
        goto LAB_000004e2;
      }
    }
  }
LAB_000004df:
  bVar1 = (byte)local_res8;
LAB_000004e2:
  lVar2 = (**(code **)(DAT_00000b10 + 0x48))(0xac0,0xa80,local_res18,&local_28,local_res20);
  if (((-1 < lVar2) && ((bVar1 & 1) != 0)) && (local_res20[0] == '\x01')) {
    local_res20[0] = '\0';
    local_20 = 0xe770bb69;
    local_1c = 0x4d04bcb4;
    local_18 = 0xff23979e;
    local_14 = 0xacfe5694;
    local_res8 = local_res8 & 0xffffffffffffff00;
    (**(code **)(DAT_00000b10 + 0x58))(0xaa0,&local_20,2,1,&local_res8);
    lVar2 = (**(code **)(DAT_00000b10 + 0x58))(0xac0,0xa80,local_res18[0],local_28,local_res20);
    out(0xcf9,0xe);
  }
  return lVar2;
}


// ==== FUN_000005b8 @ 000005b8

undefined8 FUN_000005b8(char param_1,undefined1 param_2)

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
      FUN_000008b0(0xf);
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


// ==== FUN_00000630 @ 00000630

undefined8 FUN_00000630(char param_1)

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
      FUN_000008b0(5000);
      bVar2 = in(uVar1);
      uVar5 = uVar5 + 1;
    } while ((bVar2 & 1) != 0);
    if (0x1ffff < uVar5) {
      return 0x8000000000000007;
    }
  }
  return 0;
}


// ==== FUN_000006b8 @ 000006b8

undefined8 FUN_000006b8(char param_1)

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
      FUN_000008b0(0xf);
      bVar2 = in(uVar1);
      uVar3 = uVar3 + 1;
    } while ((bVar2 & 2) != 0);
    if (0x1ffff < uVar3) {
      return 0x8000000000000007;
    }
  }
  return 0;
}


// ==== FUN_0000071c @ 0000071c

longlong FUN_0000071c(char param_1,undefined1 param_2,undefined1 param_3)

{
  byte bVar1;
  byte bVar2;
  longlong lVar3;
  ulonglong uVar4;
  undefined2 uVar5;
  
  lVar3 = FUN_000006b8(param_1);
  uVar4 = 0;
  if (lVar3 < 0) {
    return lVar3;
  }
  FUN_00000630(param_1);
  FUN_000005b8(param_1,param_2);
  FUN_000006b8(param_1);
  uVar5 = 0x60;
  bVar1 = 100;
  if (param_1 != '`') {
    bVar1 = 0x66;
  }
  bVar2 = in((ushort)bVar1);
  if ((bVar2 & 2) != 0) {
    do {
      if (0x1ffff < uVar4) goto LAB_000007be;
      FUN_000008b0(0xf);
      bVar2 = in((ushort)bVar1);
      uVar4 = uVar4 + 1;
    } while ((bVar2 & 2) != 0);
    if (0x1ffff < uVar4) goto LAB_000007be;
  }
  if (param_1 != '`') {
    uVar5 = 0x62;
  }
  out(uVar5,param_3);
LAB_000007be:
  FUN_00000630(param_1);
  return lVar3;
}


// ==== FUN_000007e4 @ 000007e4

longlong FUN_000007e4(void)

{
  ulonglong uVar1;
  longlong *plVar2;
  
  uVar1 = 0;
  if (DAT_00000b20 == 0) {
    DAT_00000b20 = 0;
    if (*(ulonglong *)(DAT_00000b00 + 0x68) != 0) {
      plVar2 = *(longlong **)(DAT_00000b00 + 0x70);
      do {
        if ((DAT_00000a60 == *plVar2) && (DAT_00000a68 == plVar2[1])) {
          DAT_00000b20 = (*(longlong **)(DAT_00000b00 + 0x70))[uVar1 * 3 + 2];
          return DAT_00000b20;
        }
        uVar1 = uVar1 + 1;
        plVar2 = plVar2 + 3;
      } while (uVar1 < *(ulonglong *)(DAT_00000b00 + 0x68));
    }
  }
  return DAT_00000b20;
}


// ==== FUN_00000850 @ 00000850

void FUN_00000850(uint param_1)

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


// ==== FUN_000008b0 @ 000008b0

longlong FUN_000008b0(longlong param_1)

{
  FUN_00000850((uint)((ulonglong)(param_1 * 0x369e99) / 1000000));
  return param_1;
}


