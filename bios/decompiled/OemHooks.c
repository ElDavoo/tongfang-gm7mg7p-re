// OemHooks.efi: Ghidra x86:LE:64:default decompile, unedited
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
  
  DAT_00000d88 = *(longlong *)(param_2 + 0x60);
  DAT_00000d80 = param_2;
  FUN_00000a9c();
  psVar3 = (short *)FUN_00000a9c();
  do {
    if (*psVar3 == -1) {
      psVar3 = (short *)0x0;
LAB_00000380:
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
LAB_000003e9:
        if ((DAT_00000da8 != (undefined8 *)0x0) ||
           (lVar5 = (**(code **)(DAT_00000d88 + 0x140))(0xd10,0,0xda8), -1 < lVar5)) {
          (*(code *)*DAT_00000da8)(DAT_00000da8,0xdb0);
        }
        return;
      }
      if ((DAT_00000d20 == *(longlong *)(psVar3 + 4)) && (DAT_00000d28 == *(longlong *)(psVar3 + 8))
         ) goto LAB_000003e9;
    }
    else if (*psVar3 == 4) goto LAB_00000380;
    psVar3 = (short *)((longlong)psVar3 + (ulonglong)(ushort)psVar3[1]);
  } while( true );
}


// ==== FUN_00000438 @ 00000438

void FUN_00000438(undefined8 param_1,longlong param_2)

{
  byte bVar1;
  longlong lVar2;
  undefined8 uVar3;
  ulonglong uVar4;
  byte bVar5;
  undefined8 local_res8 [2];
  undefined4 local_res18 [2];
  undefined8 local_res20;
  undefined4 local_ae8;
  undefined4 local_ae4;
  undefined4 local_ae0;
  undefined4 local_adc;
  undefined4 local_ad8;
  undefined4 local_ad4;
  undefined4 local_ad0;
  undefined4 local_acc;
  undefined8 local_ac8 [2];
  undefined1 local_ab8 [1091];
  undefined1 local_675;
  undefined4 local_663;
  undefined4 local_65f;
  undefined2 local_65b;
  undefined1 local_659;
  undefined4 local_624;
  undefined1 local_620;
  undefined2 local_59c;
  char local_374;
  undefined1 local_2d8 [9];
  char local_2cf;
  
  local_res18[0] = 0;
  bVar1 = 0xff;
  local_ac8[0] = 0x7d8;
  local_ae8 = 0xec87d643;
  local_ae4 = 0x4bb5eba4;
  local_ae0 = 0x3e3fe5a1;
  local_adc = 0xa90db236;
  local_res20 = 699;
  local_ad8 = 0xb08f97ff;
  local_ad4 = 0x4193e6e8;
  local_ad0 = 0x9e5e97a9;
  local_acc = 0x32db0a9b;
  if (DAT_00000d98 == 0) {
    DAT_00000d90 = *(longlong *)(param_2 + 0x58);
    DAT_00000d98 = param_2;
  }
  local_res8[0] = param_1;
  lVar2 = FUN_000008f0('b',0xa3,7);
  if ((-1 < lVar2) && (lVar2 = FUN_000008f0('b',0xa2,0x50), -1 < lVar2)) {
    FUN_000008f0('b',0xa5,0);
  }
  lVar2 = (**(code **)(DAT_00000d90 + 0x48))(0xd30,&local_ad8,local_res18,&local_res20,local_2d8);
  if (lVar2 < 0) {
    return;
  }
  uVar3 = 0xd48;
  lVar2 = (**(code **)(DAT_00000d90 + 0x48))(0xd48,&local_ae8,local_res18,local_ac8,local_ab8);
  if (-1 < lVar2) {
    FUN_00000a00(uVar3,0x42,(undefined1 *)local_res8);
    if (local_374 == '\x01') {
      bVar5 = (byte)local_res8[0] | 3;
    }
    else {
      bVar5 = (byte)local_res8[0] & 0xfc;
    }
    FUN_000009b8(uVar3,0x42,bVar5);
    FUN_00000a00(uVar3,0x58,(undefined1 *)local_res8);
    if (local_2cf == '\x01') {
      bVar5 = (byte)local_res8[0] | 0x80;
    }
    else {
      bVar5 = (byte)local_res8[0] & 0x7f;
    }
    FUN_000009b8(uVar3,0x58,bVar5);
  }
  out(0x70,0xf0);
  out(0x71,2);
  uVar4 = 0;
  lVar2 = FUN_000008f0('b',0xa3,7);
  if (((-1 < lVar2) && (lVar2 = FUN_000008f0('b',0xa2,0x4c), -1 < lVar2)) &&
     (lVar2 = FUN_0000078c('b',0xa4), -1 < lVar2)) {
    bVar5 = in(0x66);
    if ((bVar5 & 1) == 0) {
      do {
        if (0x1ffff < uVar4) goto LAB_0000063b;
        FUN_00000b68(0xf);
        bVar5 = in(0x66);
        uVar4 = uVar4 + 1;
      } while ((bVar5 & 1) == 0);
      if (0x1ffff < uVar4) goto LAB_0000063b;
    }
    bVar1 = in(0x62);
  }
LAB_0000063b:
  bVar5 = bVar1 & 0xf;
  if ((((bVar1 & 0xf) == 0) || (bVar5 == 1)) || (bVar5 == 2)) goto LAB_00000752;
  if (bVar5 == 3) {
    local_663 = 0xa06a6501;
    local_65f = 0x71634372;
    local_65b = 0x6aa0;
    local_624 = 0x13131a01;
    local_620 = 0x1b;
    local_59c = 0x1b1b;
LAB_00000744:
    local_659 = 0x2f;
  }
  else {
    if (((bVar5 == 4) || (bVar5 == 5)) || (bVar5 == 6)) goto LAB_00000752;
    if (bVar5 != 7) {
      if (bVar5 != 8) {
        local_675 = 0;
        goto LAB_00000752;
      }
      local_663 = 0xa06f4101;
      local_65f = 0x6f403069;
      local_65b = 0x69a0;
      local_624 = 0x1e1e1501;
      local_620 = 0x20;
      local_59c = 0x2020;
      goto LAB_00000744;
    }
    local_663 = 0xa06e6101;
    local_65f = 0x795f497b;
    local_65b = 0x70a0;
    local_659 = 0x31;
    local_624 = 0x11111601;
    local_620 = 0x1c;
    local_59c = 0x1c1c;
  }
  local_675 = 1;
LAB_00000752:
  (**(code **)(DAT_00000d90 + 0x58))(0xd48,&local_ae8,local_res18[0],0x7d8,local_ab8);
  return;
}


// ==== FUN_0000078c @ 0000078c

undefined8 FUN_0000078c(char param_1,undefined1 param_2)

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
      FUN_00000b68(0xf);
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


// ==== FUN_00000804 @ 00000804

undefined8 FUN_00000804(char param_1)

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
      FUN_00000b68(5000);
      bVar2 = in(uVar1);
      uVar5 = uVar5 + 1;
    } while ((bVar2 & 1) != 0);
    if (0x1ffff < uVar5) {
      return 0x8000000000000007;
    }
  }
  return 0;
}


// ==== FUN_0000088c @ 0000088c

undefined8 FUN_0000088c(char param_1)

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
      FUN_00000b68(0xf);
      bVar2 = in(uVar1);
      uVar3 = uVar3 + 1;
    } while ((bVar2 & 2) != 0);
    if (0x1ffff < uVar3) {
      return 0x8000000000000007;
    }
  }
  return 0;
}


// ==== FUN_000008f0 @ 000008f0

longlong FUN_000008f0(char param_1,undefined1 param_2,undefined1 param_3)

{
  byte bVar1;
  byte bVar2;
  longlong lVar3;
  ulonglong uVar4;
  undefined2 uVar5;
  
  lVar3 = FUN_0000088c(param_1);
  uVar4 = 0;
  if (lVar3 < 0) {
    return lVar3;
  }
  FUN_00000804(param_1);
  FUN_0000078c(param_1,param_2);
  FUN_0000088c(param_1);
  uVar5 = 0x60;
  bVar1 = 100;
  if (param_1 != '`') {
    bVar1 = 0x66;
  }
  bVar2 = in((ushort)bVar1);
  if ((bVar2 & 2) != 0) {
    do {
      if (0x1ffff < uVar4) goto LAB_00000992;
      FUN_00000b68(0xf);
      bVar2 = in((ushort)bVar1);
      uVar4 = uVar4 + 1;
    } while ((bVar2 & 2) != 0);
    if (0x1ffff < uVar4) goto LAB_00000992;
  }
  if (param_1 != '`') {
    uVar5 = 0x62;
  }
  out(uVar5,param_3);
LAB_00000992:
  FUN_00000804(param_1);
  return lVar3;
}


// ==== FUN_000009b8 @ 000009b8

void FUN_000009b8(undefined8 param_1,undefined1 param_2,undefined1 param_3)

{
  longlong lVar1;
  
  lVar1 = FUN_000008f0('b',0xa3,4);
  if (-1 < lVar1) {
    lVar1 = FUN_000008f0('b',0xa2,param_2);
    if (-1 < lVar1) {
      FUN_000008f0('b',0xa5,param_3);
    }
  }
  return;
}


// ==== FUN_00000a00 @ 00000a00

longlong FUN_00000a00(undefined8 param_1,undefined1 param_2,undefined1 *param_3)

{
  byte bVar1;
  undefined1 uVar2;
  longlong lVar3;
  ulonglong uVar4;
  
  uVar4 = 0;
  lVar3 = FUN_000008f0('b',0xa3,4);
  if (((-1 < lVar3) && (lVar3 = FUN_000008f0('b',0xa2,param_2), -1 < lVar3)) &&
     (lVar3 = FUN_0000078c('b',0xa4), -1 < lVar3)) {
    bVar1 = in(0x66);
    if ((bVar1 & 1) == 0) {
      do {
        if (0x1ffff < uVar4) {
          return -0x7ffffffffffffff9;
        }
        FUN_00000b68(0xf);
        bVar1 = in(0x66);
        uVar4 = uVar4 + 1;
      } while ((bVar1 & 1) == 0);
      if (0x1ffff < uVar4) {
        return -0x7ffffffffffffff9;
      }
    }
    uVar2 = in(0x62);
    *param_3 = uVar2;
    lVar3 = 0;
  }
  return lVar3;
}


// ==== FUN_00000a9c @ 00000a9c

longlong FUN_00000a9c(void)

{
  ulonglong uVar1;
  longlong *plVar2;
  
  uVar1 = 0;
  if (DAT_00000da0 == 0) {
    DAT_00000da0 = 0;
    if (*(ulonglong *)(DAT_00000d80 + 0x68) != 0) {
      plVar2 = *(longlong **)(DAT_00000d80 + 0x70);
      do {
        if ((DAT_00000d00 == *plVar2) && (DAT_00000d08 == plVar2[1])) {
          DAT_00000da0 = (*(longlong **)(DAT_00000d80 + 0x70))[uVar1 * 3 + 2];
          return DAT_00000da0;
        }
        uVar1 = uVar1 + 1;
        plVar2 = plVar2 + 3;
      } while (uVar1 < *(ulonglong *)(DAT_00000d80 + 0x68));
    }
  }
  return DAT_00000da0;
}


// ==== FUN_00000b08 @ 00000b08

void FUN_00000b08(uint param_1)

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


// ==== FUN_00000b68 @ 00000b68

longlong FUN_00000b68(longlong param_1)

{
  FUN_00000b08((uint)((ulonglong)(param_1 * 0x369e99) / 1000000));
  return param_1;
}


