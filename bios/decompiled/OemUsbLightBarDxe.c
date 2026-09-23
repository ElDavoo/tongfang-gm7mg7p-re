// OemUsbLightBarDxe.efi: Ghidra x86:LE:64:default decompile, unedited
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
  
  DAT_000008f0 = *(longlong *)(param_2 + 0x60);
  DAT_000008e8 = param_2;
  FUN_00000670();
  psVar3 = (short *)FUN_00000670();
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
        if ((DAT_00000918 != (undefined8 *)0x0) ||
           (lVar5 = (**(code **)(DAT_000008f0 + 0x140))(0x860,0,0x918), -1 < lVar5)) {
          (*(code *)*DAT_00000918)(DAT_00000918,0x920);
        }
        return;
      }
      if ((DAT_00000880 == *(longlong *)(psVar3 + 4)) && (DAT_00000888 == *(longlong *)(psVar3 + 8))
         ) goto LAB_000003e9;
    }
    else if (*psVar3 == 4) goto LAB_00000380;
    psVar3 = (short *)((longlong)psVar3 + (ulonglong)(ushort)psVar3[1]);
  } while( true );
}


// ==== FUN_00000438 @ 00000438

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

undefined8 FUN_00000438(undefined8 param_1,longlong param_2)

{
  longlong lVar1;
  undefined8 local_res8;
  undefined8 local_res18;
  undefined8 local_res20;
  undefined8 local_8b8;
  undefined4 local_8b0;
  undefined4 local_8ac;
  undefined1 local_8a8 [31];
  undefined1 local_889 [2];
  char local_887;
  undefined1 local_881 [2];
  char local_87f;
  undefined1 local_7e8 [1856];
  undefined1 local_a8;
  
  if (DAT_00000908 == 0) {
    DAT_000008f8 = *(longlong *)(param_2 + 0x60);
    DAT_00000900 = *(longlong *)(param_2 + 0x58);
    DAT_00000908 = param_2;
  }
  local_res18 = 0xb4;
  local_res8 = CONCAT44((int)((ulonglong)param_1 >> 0x20),7);
  lVar1 = (**(code **)(DAT_000008f8 + 0x140))(0x840,0,0x8e0);
  if ((-1 < lVar1) &&
     (lVar1 = (**(code **)(DAT_00000900 + 0x48))(0x890,0x870,&local_res8,&local_res18,local_8a8),
     -1 < lVar1)) {
    local_res20 = CONCAT53(uRam00000000ff43003d,CONCAT12(DAT_ff43003c,_DAT_ff43003a));
    local_8b8 = CONCAT53(uRam00000000ff430045,CONCAT12(DAT_ff430044,_DAT_ff430042));
    if (DAT_ff43003c != local_887) {
      (**(code **)(DAT_000008e0 + 0x10))(local_889,8,0x3a);
    }
    if (local_8b8._2_1_ != local_87f) {
      (**(code **)(DAT_000008e0 + 0x10))(local_881,8,0x42);
    }
  }
  local_res18 = 0x7d8;
  local_8b8 = 0x4bb5eba4ec87d643;
  local_8b0 = 0x3e3fe5a1;
  local_8ac = 0xa90db236;
  lVar1 = (**(code **)(DAT_00000900 + 0x48))(0x8b0,&local_8b8,&local_res8,&local_res18,local_7e8);
  if (lVar1 < 0) {
    return 0;
  }
  if (DAT_ff43003c == '\0') {
    local_a8 = 0;
  }
  else if (DAT_ff430044 == '\x01') {
    local_a8 = 1;
  }
  else if (DAT_ff430044 == '\x02') {
    local_a8 = 2;
  }
  else if (DAT_ff430044 == '\x05') {
    local_a8 = 5;
  }
  else if (DAT_ff430044 == '\n') {
    local_a8 = 10;
  }
  else {
    if (DAT_ff430044 != '\r') {
      if (DAT_ff430044 == '\x13') {
        local_a8 = 0x13;
        goto LAB_00000637;
      }
      if (DAT_ff430044 == ' ') {
        local_a8 = 0x20;
        goto LAB_00000637;
      }
      if (DAT_ff430044 == '!') {
        local_a8 = 0x21;
        goto LAB_00000637;
      }
    }
    local_a8 = 0xd;
  }
LAB_00000637:
  (**(code **)(DAT_00000900 + 0x58))(0x8b0,&local_8b8,local_res8 & 0xffffffff,local_res18,local_7e8)
  ;
  return 0;
}


// ==== FUN_00000670 @ 00000670

longlong FUN_00000670(void)

{
  ulonglong uVar1;
  longlong *plVar2;
  
  uVar1 = 0;
  if (DAT_00000910 == 0) {
    DAT_00000910 = 0;
    if (*(ulonglong *)(DAT_000008e8 + 0x68) != 0) {
      plVar2 = *(longlong **)(DAT_000008e8 + 0x70);
      do {
        if ((DAT_00000850 == *plVar2) && (DAT_00000858 == plVar2[1])) {
          DAT_00000910 = (*(longlong **)(DAT_000008e8 + 0x70))[uVar1 * 3 + 2];
          return DAT_00000910;
        }
        uVar1 = uVar1 + 1;
        plVar2 = plVar2 + 3;
      } while (uVar1 < *(ulonglong *)(DAT_000008e8 + 0x68));
    }
  }
  return DAT_00000910;
}


