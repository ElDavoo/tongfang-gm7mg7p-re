// OemDisplayModeDxe.efi: Ghidra x86:LE:64:default decompile, unedited
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
  
  DAT_000008a8 = *(longlong *)(param_2 + 0x60);
  DAT_000008a0 = param_2;
  FUN_00000628();
  psVar3 = (short *)FUN_00000628();
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
        if ((DAT_000008c8 != (undefined8 *)0x0) ||
           (lVar5 = (**(code **)(DAT_000008a8 + 0x140))(0x810,0,0x8c8), -1 < lVar5)) {
          (*(code *)*DAT_000008c8)(DAT_000008c8,0x8d0);
        }
        return;
      }
      if ((DAT_00000830 == *(longlong *)(psVar3 + 4)) && (DAT_00000838 == *(longlong *)(psVar3 + 8))
         ) goto LAB_000003e9;
    }
    else if (*psVar3 == 4) goto LAB_00000380;
    psVar3 = (short *)((longlong)psVar3 + (ulonglong)(ushort)psVar3[1]);
  } while( true );
}


// ==== FUN_00000438 @ 00000438

longlong FUN_00000438(ulonglong param_1,longlong param_2)

{
  longlong lVar1;
  ulonglong local_res8 [2];
  undefined4 local_res18 [2];
  undefined4 local_res20 [2];
  undefined4 local_b08;
  undefined4 local_b04;
  undefined4 local_b00;
  undefined4 local_afc;
  undefined4 local_af8;
  undefined4 local_af4;
  undefined4 local_af0;
  undefined4 local_aec;
  undefined8 local_ae8;
  undefined8 local_ae0;
  undefined8 local_ad8 [2];
  undefined1 local_ac8 [98];
  char local_a66;
  undefined1 local_a08 [295];
  char local_8e1;
  undefined1 local_7e8 [1836];
  char local_bc;
  
  local_res8[0] = param_1 & 0xffffffff00000000;
  local_res18[0] = 0;
  local_ae8 = 0x7d8;
  local_b08 = 0xec87d643;
  local_b04 = 0x4bb5eba4;
  local_b00 = 0x3e3fe5a1;
  local_afc = 0xa90db236;
  local_ad8[0] = 0xb4;
  local_res20[0] = 7;
  local_af8 = 0x72c5e28c;
  local_af4 = 0x43a17783;
  local_af0 = 0xd7fa6787;
  local_aec = 0xa4afcc3f;
  local_ae0 = 0x21d;
  if (DAT_000008b8 == 0) {
    DAT_000008b0 = *(longlong *)(param_2 + 0x58);
    DAT_000008b8 = param_2;
  }
  lVar1 = (**(code **)(DAT_000008b0 + 0x48))(0x840,0x820,local_res20,local_ad8,local_ac8);
  if (((-1 < lVar1) &&
      (lVar1 = (**(code **)(DAT_000008b0 + 0x48))(0x860,&local_b08,local_res8,&local_ae8,local_7e8),
      -1 < lVar1)) &&
     (lVar1 = (**(code **)(DAT_000008b0 + 0x48))(0x870,&local_af8,local_res18,&local_ae0,local_a08),
     -1 < lVar1)) {
    if (local_a66 != local_bc) {
      local_bc = local_a66;
      if (local_a66 == '\x04') {
        local_8e1 = local_a66;
      }
      else if (local_a66 == '\x02') {
        local_8e1 = '\x01';
      }
      (**(code **)(DAT_000008b0 + 0x58))
                (0x860,&local_b08,local_res8[0] & 0xffffffff,local_ae8,local_7e8);
      (**(code **)(DAT_000008b0 + 0x58))(0x870,&local_af8,local_res18[0],local_ae0,local_a08);
      out(0xcf9,0xe);
    }
    lVar1 = 0;
  }
  return lVar1;
}


// ==== FUN_00000628 @ 00000628

longlong FUN_00000628(void)

{
  ulonglong uVar1;
  longlong *plVar2;
  
  uVar1 = 0;
  if (DAT_000008c0 == 0) {
    DAT_000008c0 = 0;
    if (*(ulonglong *)(DAT_000008a0 + 0x68) != 0) {
      plVar2 = *(longlong **)(DAT_000008a0 + 0x70);
      do {
        if ((DAT_00000800 == *plVar2) && (DAT_00000808 == plVar2[1])) {
          DAT_000008c0 = (*(longlong **)(DAT_000008a0 + 0x70))[uVar1 * 3 + 2];
          return DAT_000008c0;
        }
        uVar1 = uVar1 + 1;
        plVar2 = plVar2 + 3;
      } while (uVar1 < *(ulonglong *)(DAT_000008a0 + 0x68));
    }
  }
  return DAT_000008c0;
}


