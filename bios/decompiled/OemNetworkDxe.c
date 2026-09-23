// OemNetworkDxe.efi: Ghidra x86:LE:64:default decompile, unedited
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
  
  DAT_00000828 = *(longlong *)(param_2 + 0x60);
  DAT_00000820 = param_2;
  FUN_000005d4();
  psVar3 = (short *)FUN_000005d4();
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
        if ((DAT_00000848 != (undefined8 *)0x0) ||
           (lVar5 = (**(code **)(DAT_00000828 + 0x140))(0x7b0,0,0x848), -1 < lVar5)) {
          (*(code *)*DAT_00000848)(DAT_00000848,0x850);
        }
        return;
      }
      if ((DAT_000007c0 == *(longlong *)(psVar3 + 4)) && (DAT_000007c8 == *(longlong *)(psVar3 + 8))
         ) goto LAB_000003e9;
    }
    else if (*psVar3 == 4) goto LAB_00000380;
    psVar3 = (short *)((longlong)psVar3 + (ulonglong)(ushort)psVar3[1]);
  } while( true );
}


// ==== FUN_00000438 @ 00000438

undefined8 FUN_00000438(ulonglong param_1,longlong param_2)

{
  longlong lVar1;
  ulonglong local_res8 [2];
  char local_res18 [8];
  undefined8 local_res20;
  undefined4 local_818;
  undefined4 local_814;
  undefined4 local_810;
  undefined4 local_80c;
  undefined4 local_808;
  undefined4 local_804;
  undefined4 local_800;
  undefined4 local_7fc;
  undefined8 local_7f8 [2];
  undefined1 local_7e8 [1852];
  char local_ac;
  char local_a6;
  char local_9d;
  
  if (DAT_00000838 == 0) {
    DAT_00000830 = *(longlong *)(param_2 + 0x58);
    DAT_00000838 = param_2;
  }
  local_7f8[0] = 8;
  local_818 = 0xec87d643;
  local_814 = 0x4bb5eba4;
  local_810 = 0x3e3fe5a1;
  local_80c = 0xa90db236;
  local_res20 = 0x7d8;
  local_808 = 0xd1405d16;
  local_804 = 0x46957afc;
  local_800 = 0x454112bb;
  local_7fc = 0xa295369d;
  local_res8[0] = param_1;
  lVar1 = (**(code **)(DAT_00000830 + 0x48))(2000,&local_818,local_res8,&local_res20,local_7e8);
  if (lVar1 < 0) {
    return 0;
  }
  lVar1 = (**(code **)(DAT_00000830 + 0x48))(0x7e0,&local_808,local_res8,local_7f8,local_res18);
  if (lVar1 < 0) {
    return 0;
  }
  if (local_9d == '\x01') {
    if (local_a6 == '\x01') {
      local_res18[0] = local_9d;
      local_ac = local_9d;
      goto LAB_0000056b;
    }
    local_res18[0] = '\0';
    local_ac = '\x02';
  }
  if (local_9d == '\0') {
    local_res18[0] = local_9d;
    local_ac = local_9d;
  }
LAB_0000056b:
  (**(code **)(DAT_00000830 + 0x58))
            (2000,&local_818,local_res8[0] & 0xffffffff,local_res20,local_7e8);
  (**(code **)(DAT_00000830 + 0x58))
            (0x7e0,&local_808,local_res8[0] & 0xffffffff,local_7f8[0],local_res18);
  return 0;
}


// ==== FUN_000005d4 @ 000005d4

longlong FUN_000005d4(void)

{
  ulonglong uVar1;
  longlong *plVar2;
  
  uVar1 = 0;
  if (DAT_00000840 == 0) {
    DAT_00000840 = 0;
    if (*(ulonglong *)(DAT_00000820 + 0x68) != 0) {
      plVar2 = *(longlong **)(DAT_00000820 + 0x70);
      do {
        if ((DAT_000007a0 == *plVar2) && (DAT_000007a8 == plVar2[1])) {
          DAT_00000840 = (*(longlong **)(DAT_00000820 + 0x70))[uVar1 * 3 + 2];
          return DAT_00000840;
        }
        uVar1 = uVar1 + 1;
        plVar2 = plVar2 + 3;
      } while (uVar1 < *(ulonglong *)(DAT_00000820 + 0x68));
    }
  }
  return DAT_00000840;
}


