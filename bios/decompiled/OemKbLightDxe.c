// OemKbLightDxe.efi: Ghidra x86:LE:64:default decompile, unedited
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
  
  DAT_00000f50 = *(longlong *)(param_2 + 0x60);
  DAT_00000f48 = param_2;
  FUN_00000c38();
  psVar3 = (short *)FUN_00000c38();
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
        if ((DAT_00000f78 != (undefined8 *)0x0) ||
           (lVar5 = (**(code **)(DAT_00000f50 + 0x140))(0xec0,0,0xf78), -1 < lVar5)) {
          (*(code *)*DAT_00000f78)(DAT_00000f78,0xf80);
        }
        return;
      }
      if ((DAT_00000ee0 == *(longlong *)(psVar3 + 4)) && (DAT_00000ee8 == *(longlong *)(psVar3 + 8))
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
  undefined8 uVar1;
  uint uVar2;
  longlong lVar3;
  wchar_t *pwVar4;
  ulonglong uVar5;
  undefined8 uVar6;
  byte bVar7;
  bool bVar8;
  undefined8 local_res8;
  undefined4 local_res18 [2];
  undefined8 local_res20;
  char cStack_d6;
  undefined1 local_c8 [15];
  wchar_t local_b9;
  char local_b7;
  wchar_t local_b1;
  char local_af;
  
  bVar7 = 0;
  if (DAT_00000f68 == 0) {
    DAT_00000f58 = *(longlong *)(param_2 + 0x60);
    DAT_00000f60 = *(longlong *)(param_2 + 0x58);
    DAT_00000f68 = param_2;
  }
  local_res20 = 0xb4;
  uVar6 = 0;
  local_res18[0] = 7;
  pwVar4 = (wchar_t *)&DAT_00000ea0;
  local_res8 = param_1;
  lVar3 = (**(code **)(DAT_00000f58 + 0x140))(0xea0,0,0xf40);
  if (-1 < lVar3) {
    uVar6 = 0xed0;
    pwVar4 = u_UniWillVariable_00000ef0;
    (**(code **)(DAT_00000f60 + 0x48))(0xef0,0xed0,local_res18,&local_res20,local_c8);
    uVar1 = _DAT_ff430014;
    local_res8 = _DAT_ff430024;
    uVar5 = local_res8;
    local_res8._2_1_ = (char)(_DAT_ff430024 >> 0x10);
    bVar8 = local_res8._2_1_ != local_b7;
    local_res8 = uVar5;
    if (bVar8) {
      pwVar4 = &local_b9;
      uVar6 = 8;
      (**(code **)(DAT_00000f40 + 0x10))(pwVar4,8,0x24);
    }
    cStack_d6 = (char)((ulonglong)uVar1 >> 0x10);
    if (cStack_d6 != local_af) {
      pwVar4 = &local_b1;
      uVar6 = 8;
      (**(code **)(DAT_00000f40 + 0x10))(pwVar4,8,0x14);
    }
  }
  FUN_00000b9c(pwVar4,uVar6,0x3c,(undefined1 *)&local_res8);
  if ((local_res8 & 1) == 0) {
    bVar7 = 3;
  }
  else {
    uVar2 = ((byte)local_res8 & 0xf8) - 0x10;
    if ((((byte)uVar2 < 0x39) &&
        (uVar6 = 0x100010101010101, (0x100010101010101U >> ((ulonglong)uVar2 & 0x3f) & 1) != 0)) ||
       (((byte)local_res8 & 0xf8) == 0x50)) {
      bVar7 = 4;
    }
    else {
      if (DAT_ff430011 == 1) {
        bVar7 = 2;
        uVar5 = 0;
      }
      else {
        uVar2 = DAT_ff430011 - 2;
        uVar5 = (ulonglong)uVar2;
        if (uVar2 == 0) {
          bVar7 = 1;
        }
      }
      FUN_000005a4(uVar5,uVar6);
    }
  }
  FUN_00000658(bVar7);
  return 0;
}


// ==== FUN_000005a4 @ 000005a4

void FUN_000005a4(undefined8 param_1,undefined8 param_2)

{
  uint uVar1;
  undefined1 uVar3;
  byte local_res8 [32];
  ulonglong uVar2;
  
  uVar1 = DAT_ff430011 - 1;
  uVar2 = (ulonglong)uVar1;
  if (uVar1 == 0) {
    FUN_00000b9c(0,param_2,0x66,local_res8);
    FUN_00000b3c(uVar2,param_2,0x66,local_res8[0] & 0xfb);
    FUN_00000b9c(uVar2,param_2,0x3c,local_res8);
    local_res8[0] = local_res8[0] | 6;
  }
  else {
    uVar1 = DAT_ff430011 - 2;
    uVar2 = (ulonglong)uVar1;
    if (uVar1 == 0) {
      FUN_00000b9c(0,param_2,0x66,local_res8);
      uVar3 = 0x66;
      local_res8[0] = local_res8[0] | 4;
      goto LAB_0000064b;
    }
    if (uVar1 != 1) {
      return;
    }
    FUN_00000b9c(1,param_2,0x66,local_res8);
    FUN_00000b3c(uVar2,param_2,0x66,local_res8[0] & 0xfb);
    FUN_00000b9c(uVar2,param_2,0x3c,local_res8);
    local_res8[0] = local_res8[0] & 0xfd;
  }
  uVar3 = 0x3c;
LAB_0000064b:
  FUN_00000b3c(uVar2,param_2,uVar3,local_res8[0]);
  return;
}


// ==== FUN_00000658 @ 00000658

longlong FUN_00000658(byte param_1)

{
  longlong lVar1;
  longlong lVar2;
  undefined4 local_res10 [2];
  undefined8 local_res18;
  undefined4 local_7f8;
  undefined4 local_7f4;
  undefined4 local_7f0;
  undefined4 local_7ec;
  undefined1 local_7e8 [2002];
  byte local_16;
  undefined1 local_14;
  undefined1 local_13;
  undefined1 local_12;
  
  local_res18 = 0x7d8;
  local_7f8 = 0xec87d643;
  local_7f4 = 0x4bb5eba4;
  local_7f0 = 0x3e3fe5a1;
  local_7ec = 0xa90db236;
  lVar1 = (**(code **)(DAT_00000f60 + 0x48))(0xf10,&local_7f8,local_res10,&local_res18,local_7e8);
  if (lVar1 < 0) {
    return lVar1;
  }
  if (param_1 < 2) {
    local_16 = 0;
    goto LAB_000008bf;
  }
  if (param_1 == 2) {
    local_16 = 2;
    if (DAT_ff430026 == '\0') {
      local_12 = 0;
    }
    else if (DAT_ff430016 == 1) {
      local_12 = 1;
    }
    else if (DAT_ff430016 == 2) {
      local_12 = 2;
    }
    else {
      if (DAT_ff430016 != 3) {
        if (DAT_ff430016 == 5) {
          local_12 = 4;
          goto LAB_000008bf;
        }
        if (DAT_ff430016 == 0x12) {
          local_12 = 5;
          goto LAB_000008bf;
        }
        if (DAT_ff430016 == 0x13) {
          local_12 = 6;
          goto LAB_000008bf;
        }
      }
      local_12 = 3;
    }
  }
  else if (param_1 == 3) {
    if (DAT_ff430026 == '\0') {
      local_14 = 0;
      local_16 = param_1;
    }
    else if (DAT_ff430016 == 2) {
      local_14 = 1;
      local_16 = param_1;
    }
    else {
      if (DAT_ff430016 != 3) {
        if (DAT_ff430016 == 5) {
          local_14 = 3;
          local_16 = param_1;
          goto LAB_000008bf;
        }
        if (DAT_ff430016 == 9) {
          local_14 = 4;
          local_16 = param_1;
          goto LAB_000008bf;
        }
        if (DAT_ff430016 == 10) {
          local_14 = 5;
          local_16 = param_1;
          goto LAB_000008bf;
        }
      }
      local_14 = 2;
      local_16 = param_1;
    }
  }
  else if (param_1 == 4) {
    if (DAT_ff430026 == '\0') {
      local_13 = 0;
      local_16 = param_1;
    }
    else {
      if (DAT_ff430016 < 7) {
        if (DAT_ff430016 == 6) {
          local_13 = 8;
          local_16 = param_1;
          goto LAB_000008bf;
        }
        if (DAT_ff430016 == 1) {
          local_13 = 6;
          local_16 = param_1;
          goto LAB_000008bf;
        }
        if (DAT_ff430016 == 2) {
          local_13 = 1;
          local_16 = param_1;
          goto LAB_000008bf;
        }
        if (DAT_ff430016 != 3) {
          if (DAT_ff430016 == 4) {
            local_13 = 7;
            local_16 = param_1;
            goto LAB_000008bf;
          }
          if (DAT_ff430016 == 5) {
            local_13 = 3;
            local_16 = param_1;
            goto LAB_000008bf;
          }
        }
      }
      else {
        if (DAT_ff430016 == 9) {
          local_13 = 4;
          local_16 = param_1;
          goto LAB_000008bf;
        }
        if (DAT_ff430016 == 10) {
          local_13 = 5;
          local_16 = param_1;
          goto LAB_000008bf;
        }
        if (DAT_ff430016 == 0xe) {
          local_13 = 9;
          local_16 = param_1;
          goto LAB_000008bf;
        }
        if (DAT_ff430016 == 0x11) {
          local_13 = 10;
          local_16 = param_1;
          goto LAB_000008bf;
        }
        if (DAT_ff430016 == 0x15) {
          local_13 = 0xb;
          local_16 = param_1;
          goto LAB_000008bf;
        }
      }
      local_13 = 2;
      local_16 = param_1;
    }
  }
LAB_000008bf:
  lVar2 = (**(code **)(DAT_00000f60 + 0x58))(0xf10,&local_7f8,local_res10[0],local_res18,local_7e8);
  lVar1 = 0;
  if (lVar2 < 0) {
    lVar1 = lVar2;
  }
  return lVar1;
}


// ==== FUN_00000910 @ 00000910

undefined8 FUN_00000910(char param_1,undefined1 param_2)

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
      FUN_00000d04(0xf);
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


// ==== FUN_00000988 @ 00000988

undefined8 FUN_00000988(char param_1)

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
      FUN_00000d04(5000);
      bVar2 = in(uVar1);
      uVar5 = uVar5 + 1;
    } while ((bVar2 & 1) != 0);
    if (0x1ffff < uVar5) {
      return 0x8000000000000007;
    }
  }
  return 0;
}


// ==== FUN_00000a10 @ 00000a10

undefined8 FUN_00000a10(char param_1)

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
      FUN_00000d04(0xf);
      bVar2 = in(uVar1);
      uVar3 = uVar3 + 1;
    } while ((bVar2 & 2) != 0);
    if (0x1ffff < uVar3) {
      return 0x8000000000000007;
    }
  }
  return 0;
}


// ==== FUN_00000a74 @ 00000a74

longlong FUN_00000a74(char param_1,undefined1 param_2,undefined1 param_3)

{
  byte bVar1;
  byte bVar2;
  longlong lVar3;
  ulonglong uVar4;
  undefined2 uVar5;
  
  lVar3 = FUN_00000a10(param_1);
  uVar4 = 0;
  if (lVar3 < 0) {
    return lVar3;
  }
  FUN_00000988(param_1);
  FUN_00000910(param_1,param_2);
  FUN_00000a10(param_1);
  uVar5 = 0x60;
  bVar1 = 100;
  if (param_1 != '`') {
    bVar1 = 0x66;
  }
  bVar2 = in((ushort)bVar1);
  if ((bVar2 & 2) != 0) {
    do {
      if (0x1ffff < uVar4) goto LAB_00000b16;
      FUN_00000d04(0xf);
      bVar2 = in((ushort)bVar1);
      uVar4 = uVar4 + 1;
    } while ((bVar2 & 2) != 0);
    if (0x1ffff < uVar4) goto LAB_00000b16;
  }
  if (param_1 != '`') {
    uVar5 = 0x62;
  }
  out(uVar5,param_3);
LAB_00000b16:
  FUN_00000988(param_1);
  return lVar3;
}


// ==== FUN_00000b3c @ 00000b3c

longlong FUN_00000b3c(undefined8 param_1,undefined8 param_2,undefined1 param_3,undefined1 param_4)

{
  longlong lVar1;
  longlong lVar2;
  
  lVar1 = FUN_00000a74('b',0xa3,7);
  if (((-1 < lVar1) && (lVar1 = FUN_00000a74('b',0xa2,param_3), -1 < lVar1)) &&
     (lVar2 = FUN_00000a74('b',0xa5,param_4), lVar1 = 0, lVar2 < 0)) {
    lVar1 = lVar2;
  }
  return lVar1;
}


// ==== FUN_00000b9c @ 00000b9c

longlong FUN_00000b9c(undefined8 param_1,undefined8 param_2,undefined1 param_3,undefined1 *param_4)

{
  byte bVar1;
  undefined1 uVar2;
  longlong lVar3;
  ulonglong uVar4;
  
  uVar4 = 0;
  lVar3 = FUN_00000a74('b',0xa3,7);
  if (((-1 < lVar3) && (lVar3 = FUN_00000a74('b',0xa2,param_3), -1 < lVar3)) &&
     (lVar3 = FUN_00000910('b',0xa4), -1 < lVar3)) {
    bVar1 = in(0x66);
    if ((bVar1 & 1) == 0) {
      do {
        if (0x1ffff < uVar4) {
          return -0x7ffffffffffffff9;
        }
        FUN_00000d04(0xf);
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


// ==== FUN_00000c38 @ 00000c38

longlong FUN_00000c38(void)

{
  ulonglong uVar1;
  longlong *plVar2;
  
  uVar1 = 0;
  if (DAT_00000f70 == 0) {
    DAT_00000f70 = 0;
    if (*(ulonglong *)(DAT_00000f48 + 0x68) != 0) {
      plVar2 = *(longlong **)(DAT_00000f48 + 0x70);
      do {
        if ((DAT_00000eb0 == *plVar2) && (DAT_00000eb8 == plVar2[1])) {
          DAT_00000f70 = (*(longlong **)(DAT_00000f48 + 0x70))[uVar1 * 3 + 2];
          return DAT_00000f70;
        }
        uVar1 = uVar1 + 1;
        plVar2 = plVar2 + 3;
      } while (uVar1 < *(ulonglong *)(DAT_00000f48 + 0x68));
    }
  }
  return DAT_00000f70;
}


// ==== FUN_00000ca4 @ 00000ca4

void FUN_00000ca4(uint param_1)

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


// ==== FUN_00000d04 @ 00000d04

longlong FUN_00000d04(longlong param_1)

{
  FUN_00000ca4((uint)((ulonglong)(param_1 * 0x369e99) / 1000000));
  return param_1;
}


