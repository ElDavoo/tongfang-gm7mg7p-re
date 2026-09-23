// OemDDSSupportDxe.efi: Ghidra x86:LE:64:default decompile, unedited
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
  
  DAT_00000db0 = *(longlong *)(param_2 + 0x60);
  DAT_00000da8 = param_2;
  FUN_00000a70();
  psVar3 = (short *)FUN_00000a70();
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
        if ((DAT_00000dd8 != (undefined8 *)0x0) ||
           (lVar5 = (**(code **)(DAT_00000db0 + 0x140))(0xd30,0,0xdd8), -1 < lVar5)) {
          (*(code *)*DAT_00000dd8)(DAT_00000dd8,0xde0);
        }
        return;
      }
      if ((DAT_00000d60 == *(longlong *)(psVar3 + 4)) && (DAT_00000d68 == *(longlong *)(psVar3 + 8))
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
  undefined8 local_res8 [2];
  undefined1 local_res18 [16];
  
  local_res8[0] = 0;
  if (DAT_00000dc8 == 0) {
    DAT_00000db8 = *(longlong *)(param_2 + 0x60);
    _DAT_00000dc0 = *(undefined8 *)(param_2 + 0x58);
    DAT_00000dc8 = param_2;
  }
  (**(code **)(DAT_00000db8 + 0x170))(0x200,0x10,0x570,0,0xd20,local_res18);
  (**(code **)(DAT_00000db8 + 0x170))(0x200,0x10,0x4e4,0,0xd50,local_res8);
  return 0;
}


// ==== FUN_00000944 @ 00000944

undefined8 FUN_00000944(char param_1)

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
      FUN_00000b3c(0xf);
      bVar2 = in(uVar1);
      uVar3 = uVar3 + 1;
    } while ((bVar2 & 2) != 0);
    if (0x1ffff < uVar3) {
      return 0x8000000000000007;
    }
  }
  return 0;
}


// ==== FUN_00000a70 @ 00000a70

longlong FUN_00000a70(void)

{
  ulonglong uVar1;
  longlong *plVar2;
  
  uVar1 = 0;
  if (DAT_00000dd0 == 0) {
    DAT_00000dd0 = 0;
    if (*(ulonglong *)(DAT_00000da8 + 0x68) != 0) {
      plVar2 = *(longlong **)(DAT_00000da8 + 0x70);
      do {
        if ((DAT_00000d10 == *plVar2) && (DAT_00000d18 == plVar2[1])) {
          DAT_00000dd0 = (*(longlong **)(DAT_00000da8 + 0x70))[uVar1 * 3 + 2];
          return DAT_00000dd0;
        }
        uVar1 = uVar1 + 1;
        plVar2 = plVar2 + 3;
      } while (uVar1 < *(ulonglong *)(DAT_00000da8 + 0x68));
    }
  }
  return DAT_00000dd0;
}


// ==== FUN_00000adc @ 00000adc

void FUN_00000adc(uint param_1)

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


// ==== FUN_00000b3c @ 00000b3c

longlong FUN_00000b3c(longlong param_1)

{
  FUN_00000adc((uint)((ulonglong)(param_1 * 0x369e99) / 1000000));
  return param_1;
}


