// OemApControlDxe.efi: Ghidra x86:LE:64:default decompile, unedited
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
  
  DAT_00000df0 = *(longlong *)(param_2 + 0x60);
  DAT_00000de8 = param_2;
  FUN_00000b10();
  psVar3 = (short *)FUN_00000b10();
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
        if ((DAT_00000e18 != (undefined8 *)0x0) ||
           (lVar5 = (**(code **)(DAT_00000df0 + 0x140))(0xd90,0,0xe18), -1 < lVar5)) {
          (*(code *)*DAT_00000e18)(DAT_00000e18,0xe20);
        }
        return;
      }
      if ((DAT_00000db0 == *(longlong *)(psVar3 + 4)) && (DAT_00000db8 == *(longlong *)(psVar3 + 8))
         ) goto LAB_000003e9;
    }
    else if (*psVar3 == 4) goto LAB_00000380;
    psVar3 = (short *)((longlong)psVar3 + (ulonglong)(ushort)psVar3[1]);
  } while( true );
}


// ==== FUN_00000438 @ 00000438

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

undefined8 FUN_00000438(ulonglong param_1,longlong param_2)

{
  undefined1 uVar1;
  byte bVar2;
  char cVar3;
  char cVar4;
  char cVar5;
  ulonglong local_res8;
  
  cVar5 = DAT_ff43000a;
  cVar4 = DAT_ff430008;
  cVar3 = DAT_ff430007;
  bVar2 = DAT_ff430005;
  uVar1 = DAT_ff430004;
  if (DAT_00000e08 == 0) {
    DAT_00000df8 = *(undefined8 *)(param_2 + 0x60);
    _DAT_00000e00 = *(undefined8 *)(param_2 + 0x58);
    DAT_00000e08 = param_2;
  }
  local_res8 = param_1 & 0xffffffffffffff00;
  if (((DAT_ff430006 != -1) && (DAT_ff430007 != -1)) && (DAT_ff430008 != -1)) {
    FUN_00000a14(param_1,param_2,0x6c,DAT_ff430006);
    FUN_00000a14(param_1,param_2,0x6d,cVar3);
    FUN_00000a14(param_1,param_2,0x6e,cVar4);
  }
  if (cVar5 != -1) {
    FUN_00000a74(param_1,param_2,0x66,(undefined1 *)&local_res8);
    FUN_00000a14(param_1,param_2,0x65,uVar1);
    FUN_00000a14(param_1,param_2,0x66,(byte)local_res8 & 0xe0 | bVar2);
  }
  FUN_0000053c();
  return 0;
}


// ==== FUN_0000053c @ 0000053c

/* WARNING: Type propagation algorithm not settling */
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_0000053c(void)

{
  longlong lVar1;
  undefined2 *puVar2;
  byte *pbVar3;
  undefined8 uVar4;
  byte bVar5;
  undefined2 local_res8 [4];
  undefined1 local_res10 [8];
  byte local_res18 [8];
  byte local_res20 [8];
  byte local_58 [4];
  undefined2 local_54;
  undefined2 local_50;
  
  local_54 = 0;
  uVar4 = 0;
  local_50 = 0;
  puVar2 = (undefined2 *)&DAT_00000da0;
  (**(code **)(DAT_00000df8 + 0x140))(0xda0,0,0xde0);
  FUN_00000a74(puVar2,uVar4,0xa3,local_58);
  bVar5 = local_58[0];
  if ((char)local_58[0] < '\0') {
    FUN_00000a74(puVar2,uVar4,0x82,local_58);
    bVar5 = local_58[0];
  }
  else {
    pbVar3 = local_res20;
    uVar4 = 1;
    (**(code **)(DAT_00000de0 + 0x18))(pbVar3,1,0x52);
    if ((local_res20[0] & 0x40) == 0) {
      FUN_00000a74(pbVar3,uVar4,0x66,local_58);
      FUN_00000a14(pbVar3,uVar4,0x66,local_58[0] & 0xcf);
      local_res8[0]._0_1_ = 0;
      lVar1 = (**(code **)(DAT_00000df8 + 0x140))(0xda0,0,0xde0);
      if (-1 < lVar1) {
        (**(code **)(DAT_00000de0 + 0x10))(local_res8,1,0x26);
      }
    }
    else {
      local_res8[0]._0_1_ = 1;
      lVar1 = (**(code **)(DAT_00000df8 + 0x140))(0xda0,0,0xde0);
      if (-1 < lVar1) {
        (**(code **)(DAT_00000de0 + 0x10))(local_res8,1,0x26);
      }
      local_res8[0]._0_1_ = 0x14;
    }
    uVar4 = 0;
    puVar2 = (undefined2 *)&DAT_00000da0;
    lVar1 = (**(code **)(DAT_00000df8 + 0x140))(0xda0,0,0xde0);
    if (-1 < lVar1) {
      puVar2 = local_res8;
      uVar4 = 1;
      (**(code **)(DAT_00000de0 + 0x10))(puVar2,1,0x27);
    }
    FUN_00000a14(puVar2,uVar4,0xa3,bVar5 | 0x80);
    bVar5 = local_res20[0];
  }
  if ((bVar5 & 0x40) != 0) {
    local_res18[0] = 1;
    local_54 = _DAT_ff430004;
    FUN_00000a74(puVar2,uVar4,0x66,(undefined1 *)((longlong)&local_50 + 1));
    local_54 = (ushort)(local_res18[0] & 1) << 0xc | local_54 & 0xefff;
    FUN_00000a74((ulonglong)local_54,0xefff,0x3c,local_58);
    lVar1 = (**(code **)(DAT_00000df8 + 0x140))(0xda0,0,0xde0);
    if (-1 < lVar1) {
      (**(code **)(DAT_00000de0 + 0x10))(local_res18,1,0x26);
    }
    local_res10[0] = 0x14;
    lVar1 = (**(code **)(DAT_00000df8 + 0x140))(0xda0,0,0xde0);
    if (-1 < lVar1) {
      (**(code **)(DAT_00000de0 + 0x10))(local_res10,1,0x27);
    }
    uVar4 = 2;
    puVar2 = &local_54;
    local_54 = (local_50 ^ local_54) & 0x5fff ^ local_50;
    (**(code **)(DAT_00000de0 + 0x10))(puVar2,2,4);
    FUN_00000a14(puVar2,uVar4,0x65,(undefined1)local_54);
    FUN_00000a14(puVar2,uVar4,0x66,local_54._1_1_);
    bVar5 = bVar5 & 0xbf;
  }
  FUN_00000a14(puVar2,uVar4,0x82,bVar5);
  return;
}


// ==== FUN_000007e8 @ 000007e8

undefined8 FUN_000007e8(char param_1,undefined1 param_2)

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
      FUN_00000bdc(0xf);
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


// ==== FUN_00000860 @ 00000860

undefined8 FUN_00000860(char param_1)

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
      FUN_00000bdc(5000);
      bVar2 = in(uVar1);
      uVar5 = uVar5 + 1;
    } while ((bVar2 & 1) != 0);
    if (0x1ffff < uVar5) {
      return 0x8000000000000007;
    }
  }
  return 0;
}


// ==== FUN_000008e8 @ 000008e8

undefined8 FUN_000008e8(char param_1)

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
      FUN_00000bdc(0xf);
      bVar2 = in(uVar1);
      uVar3 = uVar3 + 1;
    } while ((bVar2 & 2) != 0);
    if (0x1ffff < uVar3) {
      return 0x8000000000000007;
    }
  }
  return 0;
}


// ==== FUN_0000094c @ 0000094c

longlong FUN_0000094c(char param_1,undefined1 param_2,undefined1 param_3)

{
  byte bVar1;
  byte bVar2;
  longlong lVar3;
  ulonglong uVar4;
  undefined2 uVar5;
  
  lVar3 = FUN_000008e8(param_1);
  uVar4 = 0;
  if (lVar3 < 0) {
    return lVar3;
  }
  FUN_00000860(param_1);
  FUN_000007e8(param_1,param_2);
  FUN_000008e8(param_1);
  uVar5 = 0x60;
  bVar1 = 100;
  if (param_1 != '`') {
    bVar1 = 0x66;
  }
  bVar2 = in((ushort)bVar1);
  if ((bVar2 & 2) != 0) {
    do {
      if (0x1ffff < uVar4) goto LAB_000009ee;
      FUN_00000bdc(0xf);
      bVar2 = in((ushort)bVar1);
      uVar4 = uVar4 + 1;
    } while ((bVar2 & 2) != 0);
    if (0x1ffff < uVar4) goto LAB_000009ee;
  }
  if (param_1 != '`') {
    uVar5 = 0x62;
  }
  out(uVar5,param_3);
LAB_000009ee:
  FUN_00000860(param_1);
  return lVar3;
}


// ==== FUN_00000a14 @ 00000a14

longlong FUN_00000a14(undefined8 param_1,undefined8 param_2,undefined1 param_3,undefined1 param_4)

{
  longlong lVar1;
  longlong lVar2;
  
  lVar1 = FUN_0000094c('b',0xa3,7);
  if (((-1 < lVar1) && (lVar1 = FUN_0000094c('b',0xa2,param_3), -1 < lVar1)) &&
     (lVar2 = FUN_0000094c('b',0xa5,param_4), lVar1 = 0, lVar2 < 0)) {
    lVar1 = lVar2;
  }
  return lVar1;
}


// ==== FUN_00000a74 @ 00000a74

longlong FUN_00000a74(undefined8 param_1,undefined8 param_2,undefined1 param_3,undefined1 *param_4)

{
  byte bVar1;
  undefined1 uVar2;
  longlong lVar3;
  ulonglong uVar4;
  
  uVar4 = 0;
  lVar3 = FUN_0000094c('b',0xa3,7);
  if (((-1 < lVar3) && (lVar3 = FUN_0000094c('b',0xa2,param_3), -1 < lVar3)) &&
     (lVar3 = FUN_000007e8('b',0xa4), -1 < lVar3)) {
    bVar1 = in(0x66);
    if ((bVar1 & 1) == 0) {
      do {
        if (0x1ffff < uVar4) {
          return -0x7ffffffffffffff9;
        }
        FUN_00000bdc(0xf);
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


// ==== FUN_00000b10 @ 00000b10

longlong FUN_00000b10(void)

{
  ulonglong uVar1;
  longlong *plVar2;
  
  uVar1 = 0;
  if (DAT_00000e10 == 0) {
    DAT_00000e10 = 0;
    if (*(ulonglong *)(DAT_00000de8 + 0x68) != 0) {
      plVar2 = *(longlong **)(DAT_00000de8 + 0x70);
      do {
        if ((DAT_00000d80 == *plVar2) && (DAT_00000d88 == plVar2[1])) {
          DAT_00000e10 = (*(longlong **)(DAT_00000de8 + 0x70))[uVar1 * 3 + 2];
          return DAT_00000e10;
        }
        uVar1 = uVar1 + 1;
        plVar2 = plVar2 + 3;
      } while (uVar1 < *(ulonglong *)(DAT_00000de8 + 0x68));
    }
  }
  return DAT_00000e10;
}


// ==== FUN_00000b7c @ 00000b7c

void FUN_00000b7c(uint param_1)

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


// ==== FUN_00000bdc @ 00000bdc

longlong FUN_00000bdc(longlong param_1)

{
  FUN_00000b7c((uint)((ulonglong)(param_1 * 0x369e99) / 1000000));
  return param_1;
}


