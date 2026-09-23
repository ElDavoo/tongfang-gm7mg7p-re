// OemQkeyDxe.efi: Ghidra x86:LE:64:default decompile, unedited
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
  
  DAT_00000c80 = *(longlong *)(param_2 + 0x60);
  DAT_00000c78 = param_2;
  FUN_0000095c();
  psVar3 = (short *)FUN_0000095c();
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
        if ((DAT_00000ca8 != (undefined8 *)0x0) ||
           (lVar5 = (**(code **)(DAT_00000c80 + 0x140))(0xc00,0,0xca8), -1 < lVar5)) {
          (*(code *)*DAT_00000ca8)(DAT_00000ca8,0xcb0);
        }
        return;
      }
      if ((DAT_00000c10 == *(longlong *)(psVar3 + 4)) && (DAT_00000c18 == *(longlong *)(psVar3 + 8))
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
  bool bVar4;
  ulonglong local_res8 [2];
  byte local_res18 [8];
  undefined4 local_res20 [2];
  undefined8 local_808 [2];
  undefined1 local_7f8 [1997];
  char local_2b;
  
  local_res8[0] = param_1 & 0xffffffffffffff00;
  if (DAT_00000c98 == 0) {
    DAT_00000c88 = *(longlong *)(param_2 + 0x60);
    DAT_00000c90 = *(longlong *)(param_2 + 0x58);
    DAT_00000c98 = param_2;
  }
  local_808[0] = 0x7d8;
  lVar2 = (**(code **)(DAT_00000c90 + 0x48))(0xc20,0xbe0,local_res20,local_808,local_7f8);
  if (lVar2 < 0) {
    return lVar2;
  }
  lVar2 = (**(code **)(DAT_00000c88 + 0x140))(0xbd0,0,0xc70);
  if (lVar2 < 0) {
    return lVar2;
  }
  lVar2 = (**(code **)(DAT_00000c70 + 0x18))(local_res18,1,0x34);
  if (lVar2 < 0) {
    return lVar2;
  }
  uVar3 = 0;
  lVar2 = FUN_00000894('b',0xa3,7);
  if (((lVar2 < 0) || (lVar2 = FUN_00000894('b',0xa2,0x82), lVar2 < 0)) ||
     (lVar2 = FUN_00000730('b',0xa4), lVar2 < 0)) {
LAB_00000579:
    bVar1 = (byte)local_res8[0];
  }
  else {
    bVar1 = in(0x66);
    if ((bVar1 & 1) == 0) {
      do {
        if (0x1ffff < uVar3) goto LAB_00000579;
        FUN_00000a28(0xf);
        bVar1 = in(0x66);
        uVar3 = uVar3 + 1;
      } while ((bVar1 & 1) == 0);
      if (0x1ffff < uVar3) goto LAB_00000579;
    }
    bVar1 = in(0x62);
  }
  if (local_res18[0] < 0x25) {
    if (local_res18[0] == 1) {
      local_res8[0] = (ulonglong)local_res8[0]._1_7_ << 8;
      bVar1 = bVar1 & 0xed | 0x21;
      goto LAB_00000697;
    }
    if (local_res18[0] != 0) {
      if ((byte)(local_res18[0] - 0x21) < 5) {
        local_res8[0] = (ulonglong)local_res8[0]._1_7_ << 8;
        if (local_res18[0] == 0x21) {
          bVar1 = (bVar1 & 0xc0) + 0x29;
        }
        else if (local_res18[0] == 0x22) {
          bVar1 = (bVar1 & 0xc0) + 0x39;
        }
        else if (local_res18[0] == 0x23) {
          bVar1 = (bVar1 & 0xc0) + 0x2d;
        }
        else {
          if (local_res18[0] != 0x24) goto LAB_00000697;
          bVar1 = (bVar1 & 0xc0) + 0x3d;
        }
        local_2b = '\x01';
        goto LAB_00000697;
      }
      local_res8[0] = CONCAT71(local_res8[0]._1_7_,1);
      if (0xf < local_res18[0]) {
        if (0x13 < local_res18[0]) {
          if (local_res18[0] < 0x16) {
            local_2b = '\0';
          }
          else if (local_res18[0] < 0x18) {
            local_2b = '\x01';
          }
        }
        local_res18[0] = local_res18[0] & 0xf;
        (**(code **)(DAT_00000c70 + 0x10))(local_res18,1,0x34);
      }
      local_res18[0] = local_res18[0] | 0x10;
      if (local_2b == '\0') {
        bVar1 = bVar1 | 3;
        if (local_res18[0] == 0x14) {
LAB_00000687:
          bVar1 = bVar1 & 0xef | 0x20;
          goto LAB_00000697;
        }
        bVar4 = local_res18[0] == 0x15;
      }
      else {
        if (local_2b != '\x01') goto LAB_00000697;
        bVar1 = bVar1 & 0xfd | 1;
        if (local_res18[0] == 0x16) goto LAB_00000687;
        bVar4 = local_res18[0] == 0x17;
      }
      if (bVar4) {
        bVar1 = bVar1 | 0x30;
      }
      goto LAB_00000697;
    }
  }
  local_res8[0] = (ulonglong)local_res8[0]._1_7_ << 8;
  bVar1 = bVar1 | 0x33;
LAB_00000697:
  lVar2 = FUN_00000894('b',0xa3,7);
  if ((-1 < lVar2) && (lVar2 = FUN_00000894('b',0xa2,0x82), -1 < lVar2)) {
    FUN_00000894('b',0xa5,bVar1);
  }
  (**(code **)(DAT_00000c90 + 0x58))(0xc20,0xbe0,local_res20[0],local_808[0],local_7f8);
  (**(code **)(DAT_00000c90 + 0x58))(0xc30,0xbc0,3,1,local_res8);
  return 0;
}


// ==== FUN_00000730 @ 00000730

undefined8 FUN_00000730(char param_1,undefined1 param_2)

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
      FUN_00000a28(0xf);
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


// ==== FUN_000007a8 @ 000007a8

undefined8 FUN_000007a8(char param_1)

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
      FUN_00000a28(5000);
      bVar2 = in(uVar1);
      uVar5 = uVar5 + 1;
    } while ((bVar2 & 1) != 0);
    if (0x1ffff < uVar5) {
      return 0x8000000000000007;
    }
  }
  return 0;
}


// ==== FUN_00000830 @ 00000830

undefined8 FUN_00000830(char param_1)

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
      FUN_00000a28(0xf);
      bVar2 = in(uVar1);
      uVar3 = uVar3 + 1;
    } while ((bVar2 & 2) != 0);
    if (0x1ffff < uVar3) {
      return 0x8000000000000007;
    }
  }
  return 0;
}


// ==== FUN_00000894 @ 00000894

longlong FUN_00000894(char param_1,undefined1 param_2,undefined1 param_3)

{
  byte bVar1;
  byte bVar2;
  longlong lVar3;
  ulonglong uVar4;
  undefined2 uVar5;
  
  lVar3 = FUN_00000830(param_1);
  uVar4 = 0;
  if (lVar3 < 0) {
    return lVar3;
  }
  FUN_000007a8(param_1);
  FUN_00000730(param_1,param_2);
  FUN_00000830(param_1);
  uVar5 = 0x60;
  bVar1 = 100;
  if (param_1 != '`') {
    bVar1 = 0x66;
  }
  bVar2 = in((ushort)bVar1);
  if ((bVar2 & 2) != 0) {
    do {
      if (0x1ffff < uVar4) goto LAB_00000936;
      FUN_00000a28(0xf);
      bVar2 = in((ushort)bVar1);
      uVar4 = uVar4 + 1;
    } while ((bVar2 & 2) != 0);
    if (0x1ffff < uVar4) goto LAB_00000936;
  }
  if (param_1 != '`') {
    uVar5 = 0x62;
  }
  out(uVar5,param_3);
LAB_00000936:
  FUN_000007a8(param_1);
  return lVar3;
}


// ==== FUN_0000095c @ 0000095c

longlong FUN_0000095c(void)

{
  ulonglong uVar1;
  longlong *plVar2;
  
  uVar1 = 0;
  if (DAT_00000ca0 == 0) {
    DAT_00000ca0 = 0;
    if (*(ulonglong *)(DAT_00000c78 + 0x68) != 0) {
      plVar2 = *(longlong **)(DAT_00000c78 + 0x70);
      do {
        if ((DAT_00000bf0 == *plVar2) && (DAT_00000bf8 == plVar2[1])) {
          DAT_00000ca0 = (*(longlong **)(DAT_00000c78 + 0x70))[uVar1 * 3 + 2];
          return DAT_00000ca0;
        }
        uVar1 = uVar1 + 1;
        plVar2 = plVar2 + 3;
      } while (uVar1 < *(ulonglong *)(DAT_00000c78 + 0x68));
    }
  }
  return DAT_00000ca0;
}


// ==== FUN_000009c8 @ 000009c8

void FUN_000009c8(uint param_1)

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


// ==== FUN_00000a28 @ 00000a28

longlong FUN_00000a28(longlong param_1)

{
  FUN_000009c8((uint)((ulonglong)(param_1 * 0x369e99) / 1000000));
  return param_1;
}


