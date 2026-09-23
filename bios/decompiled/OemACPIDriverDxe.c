// OemACPIDriverDxe.efi: Ghidra x86:LE:64:default decompile, unedited
// ==== FUN_00000260 @ 00000260

undefined8 * FUN_00000260(undefined8 *param_1,ulonglong param_2)

{
  ulonglong uVar1;
  ulonglong uVar2;
  undefined8 *puVar3;
  
  uVar2 = param_2 & 7;
  puVar3 = param_1;
  for (uVar1 = param_2 >> 3; uVar1 != 0; uVar1 = uVar1 - 1) {
    *puVar3 = 0;
    puVar3 = puVar3 + 1;
  }
  for (; uVar2 != 0; uVar2 = uVar2 - 1) {
    *(undefined1 *)puVar3 = 0;
    puVar3 = (undefined8 *)((longlong)puVar3 + 1);
  }
  return param_1;
}


// ==== entry @ 000002c0

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void entry(undefined8 param_1,longlong param_2)

{
  ulonglong uVar1;
  longlong *plVar2;
  
  DAT_000008d8 = *(undefined8 *)(param_2 + 0x60);
  uVar1 = 0;
  _DAT_000008e0 = 0;
  if (*(longlong *)(param_2 + 0x68) != 0) {
    plVar2 = *(longlong **)(param_2 + 0x70);
    do {
      if ((DAT_00000880 == *plVar2) && (DAT_00000888 == plVar2[1])) {
        _DAT_000008e0 = (*(longlong **)(param_2 + 0x70))[uVar1 * 3 + 2];
        break;
      }
      uVar1 = uVar1 + 1;
      plVar2 = plVar2 + 3;
    } while (uVar1 < *(ulonglong *)(param_2 + 0x68));
  }
  _DAT_000008d0 = param_2;
  FUN_00000334(param_1,param_2);
  return;
}


// ==== FUN_00000334 @ 00000334

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

longlong FUN_00000334(undefined8 param_1,longlong param_2)

{
  longlong lVar1;
  undefined8 local_res8 [2];
  undefined1 local_res18 [16];
  
  if (DAT_000008f8 == 0) {
    _DAT_000008e8 = *(undefined8 *)(param_2 + 0x60);
    _DAT_000008f0 = *(undefined8 *)(param_2 + 0x58);
    DAT_000008f8 = param_2;
  }
  local_res8[0] = param_1;
  lVar1 = (**(code **)(DAT_000008d8 + 0x40))(10,0x10,0x900);
  if (-1 < lVar1) {
    FUN_00000260(DAT_00000900,0x10);
    *(undefined4 *)DAT_00000900 = 0x53414441;
    *(int *)((longlong)DAT_00000900 + 5) = (int)DAT_00000900;
    *(undefined2 *)((longlong)DAT_00000900 + 9) = 0x10;
    (**(code **)(DAT_000008d8 + 0x148))(local_res8,0x870,0x900,0);
    (**(code **)(DAT_000008d8 + 0x170))(0x200,8,0x41c,0,0x860,local_res18);
    lVar1 = 0;
  }
  return lVar1;
}


// ==== FUN_000004d8 @ 000004d8

undefined8
FUN_000004d8(int *param_1,char *param_2,char *param_3,undefined8 param_4,longlong *param_5)

{
  char cVar1;
  int *piVar2;
  char *pcVar3;
  int *piVar4;
  uint uVar5;
  ulonglong uVar6;
  int local_res20 [2];
  
  do {
    uVar6 = 0;
    cVar1 = *param_3;
    while (cVar1 != '\0') {
      uVar6 = uVar6 + 1;
      cVar1 = param_3[uVar6];
    }
    local_res20[0] = 0x5f5f5f5f;
    FUN_000007a0((undefined8 *)local_res20,(undefined8 *)param_3,uVar6);
    uVar5 = 0;
    if (param_2 != (char *)0x0) {
      pcVar3 = (char *)0x0;
      do {
        piVar4 = (int *)(pcVar3 + (longlong)param_1);
        if (*piVar4 == local_res20[0]) goto LAB_0000053f;
        uVar5 = uVar5 + 1;
        pcVar3 = (char *)(ulonglong)uVar5;
      } while (pcVar3 < param_2);
    }
    piVar4 = (int *)0x0;
LAB_0000053f:
    if (piVar4 == (int *)0x0) {
      return 0x800000000000000e;
    }
    piVar2 = piVar4;
    if ((*(char *)((longlong)piVar4 + -1) + 0xa4U & 0xfd) == 0) {
      piVar2 = (int *)((longlong)piVar4 + -1);
    }
    if (*(char *)((longlong)piVar2 + -1) == '\b') {
      *(undefined8 *)((longlong)param_5 + 0x1c) = 0;
      param_5[1] = (longlong)piVar2;
      param_5[2] = (longlong)(piVar4 + 1);
      *param_5 = (longlong)piVar2 + -1;
      *(undefined4 *)(param_5 + 3) = 3;
      return 0;
    }
    param_2 = param_2 + (longlong)((longlong)param_1 + (4 - (longlong)piVar4));
    param_1 = piVar4 + 1;
  } while( true );
}


// ==== FUN_000005b0 @ 000005b0

longlong FUN_000005b0(int *param_1,char *param_2,char *param_3,ulonglong param_4)

{
  longlong lVar1;
  longlong local_38 [2];
  byte *local_28;
  
  lVar1 = FUN_000004d8(param_1,param_2,param_3,param_4,local_38);
  if (lVar1 < 0) {
    return lVar1;
  }
  if (*local_28 < 2) {
    if (1 < param_4) {
      return -0x7ffffffffffffffe;
    }
    *local_28 = (byte)param_4;
  }
  else if (*local_28 == 10) {
    local_28[1] = (byte)param_4;
  }
  else if (*local_28 == 0xb) {
    *(short *)(local_28 + 1) = (short)param_4;
  }
  else if (*local_28 == 0xc) {
    *(int *)(local_28 + 1) = (int)param_4;
  }
  else {
    if (*local_28 != 0xe) {
      return -0x7ffffffffffffffe;
    }
    *(ulonglong *)(local_28 + 1) = param_4;
  }
  return 0;
}


// ==== FUN_000007a0 @ 000007a0

undefined8 * FUN_000007a0(undefined8 *param_1,undefined8 *param_2,ulonglong param_3)

{
  bool bVar1;
  ulonglong uVar2;
  ulonglong uVar3;
  undefined8 *puVar4;
  byte bVar5;
  
  bVar5 = 0;
  bVar1 = false;
  uVar2 = (longlong)param_2 - (longlong)param_1;
  puVar4 = param_1;
  if (param_2 < param_1) {
    uVar2 = -uVar2;
    if (param_1 <= (undefined8 *)(param_3 + (longlong)param_2)) {
      puVar4 = (undefined8 *)(param_3 + (longlong)param_1);
      bVar1 = true;
      bVar5 = 1;
      param_2 = (undefined8 *)(param_3 + (longlong)param_2);
    }
  }
  if ((7 < param_3) && (7 < uVar2)) {
    uVar2 = (ulonglong)param_2 & 7;
    uVar3 = (ulonglong)puVar4 & 7;
    if (bVar1) {
      param_2 = (undefined8 *)((longlong)param_2 + -1);
      puVar4 = (undefined8 *)((longlong)puVar4 + -1);
    }
    if ((uVar2 == uVar3) && (uVar2 != 0)) {
      if (!bVar1) {
        uVar2 = 8 - uVar2;
      }
      param_3 = param_3 - uVar2;
      for (; uVar2 != 0; uVar2 = uVar2 - 1) {
        *(undefined1 *)puVar4 = *(undefined1 *)param_2;
        param_2 = (undefined8 *)((longlong)param_2 + (ulonglong)bVar5 * -2 + 1);
        puVar4 = (undefined8 *)((longlong)puVar4 + (ulonglong)bVar5 * -2 + 1);
      }
    }
    if (bVar1) {
      param_2 = (undefined8 *)((longlong)param_2 + -7);
      puVar4 = (undefined8 *)((longlong)puVar4 + -7);
    }
    for (uVar2 = param_3 >> 3; uVar2 != 0; uVar2 = uVar2 - 1) {
      *puVar4 = *param_2;
      param_2 = param_2 + (ulonglong)bVar5 * -2 + 1;
      puVar4 = puVar4 + (ulonglong)bVar5 * -2 + 1;
    }
    param_3 = param_3 & 7;
    if (param_3 == 0) {
      return param_1;
    }
    if (bVar1) {
      param_2 = param_2 + 1;
      puVar4 = puVar4 + 1;
    }
  }
  if (bVar1) {
    param_2 = (undefined8 *)((longlong)param_2 + -1);
    puVar4 = (undefined8 *)((longlong)puVar4 + -1);
  }
  for (; param_3 != 0; param_3 = param_3 - 1) {
    *(undefined1 *)puVar4 = *(undefined1 *)param_2;
    param_2 = (undefined8 *)((longlong)param_2 + (ulonglong)bVar5 * -2 + 1);
    puVar4 = (undefined8 *)((longlong)puVar4 + (ulonglong)bVar5 * -2 + 1);
  }
  return param_1;
}


