// OemACPIDriverHookDxe.efi: Ghidra x86:LE:64:default decompile, unedited
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

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void entry(undefined8 param_1,longlong param_2)

{
  longlong lVar1;
  undefined8 local_res18;
  undefined8 local_res20;
  
  FUN_000003a4(param_1,param_2);
  local_res18 = 0;
  local_res20 = 0;
  if (DAT_00000750 == 0) {
    DAT_00000740 = *(longlong *)(param_2 + 0x60);
    _DAT_00000748 = *(undefined8 *)(param_2 + 0x58);
    DAT_00000750 = param_2;
  }
  lVar1 = (**(code **)(DAT_00000740 + 0x50))(0x200,8,0x4c0,0,&local_res18);
  if (-1 < lVar1) {
    (**(code **)(DAT_00000740 + 0xa8))(0x6c0,local_res18,&local_res20);
  }
  return;
}


// ==== FUN_000003a4 @ 000003a4

void FUN_000003a4(undefined8 param_1,longlong param_2)

{
  uint uVar1;
  int iVar2;
  short *psVar3;
  ulonglong uVar4;
  longlong lVar5;
  
  DAT_00000738 = *(longlong *)(param_2 + 0x60);
  DAT_00000730 = param_2;
  FUN_0000052c();
  psVar3 = (short *)FUN_0000052c();
  do {
    if (*psVar3 == -1) {
      psVar3 = (short *)0x0;
LAB_000003f8:
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
LAB_00000461:
        if ((DAT_00000760 != (undefined8 *)0x0) ||
           (lVar5 = (**(code **)(DAT_00000738 + 0x140))(0x6e0,0,0x760), -1 < lVar5)) {
          (*(code *)*DAT_00000760)(DAT_00000760,0x768);
        }
        FUN_000004cc((longlong *)&DAT_000006f0,(longlong *)&DAT_00000770);
        return;
      }
      if ((DAT_00000700 == *(longlong *)(psVar3 + 4)) && (DAT_00000708 == *(longlong *)(psVar3 + 8))
         ) goto LAB_00000461;
    }
    else if (*psVar3 == 4) goto LAB_000003f8;
    psVar3 = (short *)((longlong)psVar3 + (ulonglong)(ushort)psVar3[1]);
  } while( true );
}


// ==== FUN_000004cc @ 000004cc

undefined8 FUN_000004cc(longlong *param_1,longlong *param_2)

{
  ulonglong uVar1;
  longlong *plVar2;
  longlong lVar3;
  ulonglong uVar4;
  longlong *plVar5;
  
  lVar3 = DAT_00000730;
  uVar4 = 0;
  *param_2 = 0;
  uVar1 = *(ulonglong *)(lVar3 + 0x68);
  if (uVar1 != 0) {
    plVar2 = *(longlong **)(lVar3 + 0x70);
    plVar5 = plVar2;
    do {
      if ((*param_1 == *plVar5) && (param_1[1] == plVar5[1])) {
        *param_2 = plVar2[uVar4 * 3 + 2];
        return 0;
      }
      uVar4 = uVar4 + 1;
      plVar5 = plVar5 + 3;
    } while (uVar4 < uVar1);
  }
  return 0x800000000000000e;
}


// ==== FUN_0000052c @ 0000052c

longlong FUN_0000052c(void)

{
  if (DAT_00000758 == 0) {
    FUN_000004cc((longlong *)&DAT_000006d0,&DAT_00000758);
  }
  return DAT_00000758;
}


