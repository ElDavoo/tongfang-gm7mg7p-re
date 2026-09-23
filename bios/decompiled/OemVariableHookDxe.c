// OemVariableHookDxe.efi: Ghidra x86:LE:64:default decompile, unedited
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
  
  DAT_00000778 = *(longlong *)(param_2 + 0x60);
  DAT_00000770 = param_2;
  FUN_00000518();
  psVar3 = (short *)FUN_00000518();
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
        if ((DAT_00000798 != (undefined8 *)0x0) ||
           (lVar5 = (**(code **)(DAT_00000778 + 0x140))(0x710,0,0x798), -1 < lVar5)) {
          (*(code *)*DAT_00000798)(DAT_00000798,0x7a0);
        }
        return;
      }
      if ((DAT_00000720 == *(longlong *)(psVar3 + 4)) && (DAT_00000728 == *(longlong *)(psVar3 + 8))
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
  undefined8 local_res18 [2];
  undefined4 local_718;
  undefined4 local_714;
  undefined4 local_710;
  undefined4 local_70c;
  undefined1 local_708 [68];
  char local_6c4;
  undefined1 local_4ea;
  undefined1 local_4de;
  
  if (DAT_00000788 == 0) {
    DAT_00000780 = *(longlong *)(param_2 + 0x58);
    DAT_00000788 = param_2;
  }
  local_718 = 0x4570b7f1;
  local_714 = 0x4943ade8;
  local_710 = 0x6440c38d;
  local_70c = 0x84238472;
  local_res18[0] = 0x6f2;
  local_res8[0] = param_1;
  lVar1 = (**(code **)(DAT_00000780 + 0x48))(0x730,&local_718,local_res8,local_res18,local_708);
  if ((-1 < lVar1) && (local_6c4 == '\x01')) {
    local_4de = 0;
    local_4ea = 0;
    (**(code **)(DAT_00000780 + 0x58))
              (0x730,&local_718,local_res8[0] & 0xffffffff,local_res18[0],local_708);
  }
  return 0;
}


// ==== FUN_00000518 @ 00000518

longlong FUN_00000518(void)

{
  ulonglong uVar1;
  longlong *plVar2;
  
  uVar1 = 0;
  if (DAT_00000790 == 0) {
    DAT_00000790 = 0;
    if (*(ulonglong *)(DAT_00000770 + 0x68) != 0) {
      plVar2 = *(longlong **)(DAT_00000770 + 0x70);
      do {
        if ((DAT_00000700 == *plVar2) && (DAT_00000708 == plVar2[1])) {
          DAT_00000790 = (*(longlong **)(DAT_00000770 + 0x70))[uVar1 * 3 + 2];
          return DAT_00000790;
        }
        uVar1 = uVar1 + 1;
        plVar2 = plVar2 + 3;
      } while (uVar1 < *(ulonglong *)(DAT_00000770 + 0x68));
    }
  }
  return DAT_00000790;
}


