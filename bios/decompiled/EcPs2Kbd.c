// EcPs2Kbd.efi: Ghidra x86:LE:64:default decompile, unedited
// ==== entry @ 00000260

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void entry(undefined8 param_1,longlong param_2)

{
  _DAT_00000ce8 = *(undefined8 *)(param_2 + 0x60);
  _DAT_00000ce0 = param_2;
  FUN_000004b8(param_1,param_2);
  return;
}


// ==== FUN_00000280 @ 00000280

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_00000280(undefined8 param_1)

{
  char *pcVar1;
  char *pcVar2;
  undefined8 *puVar3;
  longlong lVar4;
  undefined4 local_res18;
  undefined2 local_res1c;
  undefined8 *local_res20;
  undefined4 local_28;
  undefined4 local_24;
  undefined4 local_20;
  
  local_20 = 0;
  local_28 = 0xc0102;
  local_24 = 0xa0341d0;
  pcVar1 = (char *)FUN_00000914((char *)0x0,(undefined8 *)&local_28);
  pcVar2 = (char *)FUN_00000914((char *)0x0,(undefined8 *)&local_28);
  local_res18 = 0x60101;
  local_res1c = 0x1f00;
  pcVar1 = (char *)FUN_00000914(pcVar1,(undefined8 *)&local_res18);
  pcVar2 = (char *)FUN_00000914(pcVar2,(undefined8 *)&local_res18);
  (**(code **)(DAT_00000cf0 + 0x40))(4,0x10,&local_res20);
  puVar3 = FUN_00000914(pcVar1,(undefined8 *)&DAT_00000c70);
  *local_res20 = puVar3;
  lVar4 = DAT_00000cf0;
  local_res20[1] = 0;
  lVar4 = (**(code **)(lVar4 + 0x80))(local_res20 + 1,0xc20,0,*local_res20);
  if (-1 < lVar4) {
    _DAT_00000d60 = 0x6b8;
    _DAT_00000d68 = 0x6c4;
    _DAT_00000d70 = 0x6b8;
    _DAT_00000d78 = 0x6b8;
    _DAT_00000d80 = 0x6b8;
    lVar4 = (**(code **)(DAT_00000cf0 + 0x80))(local_res20 + 1,0xc30,0,0xd60);
    if (lVar4 < 0) {
      return;
    }
    (**(code **)(DAT_00000cf0 + 0x40))(4,0x10,&local_res20);
    puVar3 = FUN_00000914(pcVar2,(undefined8 *)&DAT_00000c60);
    *local_res20 = puVar3;
    local_res20[1] = 0;
    lVar4 = (**(code **)(DAT_00000cf0 + 0x80))(local_res20 + 1,0xc20,0,*local_res20);
    if (-1 < lVar4) {
      _DAT_00000d20 = 0x6b8;
      _DAT_00000d28 = 0x790;
      _DAT_00000d30 = 0x6b8;
      _DAT_00000d38 = 0x6b8;
      _DAT_00000d40 = 0x6b8;
      lVar4 = (**(code **)(DAT_00000cf0 + 0x80))(local_res20 + 1,0xc30,0,0xd20);
      if (lVar4 < 0) {
        return;
      }
      (**(code **)(DAT_00000cf0 + 0x70))(param_1);
      return;
    }
  }
  (**(code **)(DAT_00000cf0 + 0x48))();
  return;
}


// ==== FUN_000004b8 @ 000004b8

longlong FUN_000004b8(undefined8 param_1,longlong param_2)

{
  longlong lVar1;
  longlong lVar2;
  ushort local_res18 [4];
  undefined8 local_res20;
  undefined8 local_48 [2];
  
  local_res18[0] = 0;
  if (DAT_00000d00 == 0) {
    DAT_00000cf0 = *(longlong *)(param_2 + 0x60);
    DAT_00000cf8 = *(longlong *)(param_2 + 0x58);
    DAT_00000d00 = param_2;
  }
  lVar1 = FUN_0000085c(param_2);
  local_res20 = 0x60;
  lVar2 = (**(code **)(lVar1 + 0x50))(2,0x60,1);
  if ((-1 < lVar2) &&
     (lVar2 = (**(code **)(lVar1 + 0x58))(2,2,0,1,&local_res20,param_1,0), -1 < lVar2)) {
    local_res20 = 100;
    lVar2 = (**(code **)(lVar1 + 0x50))(2,100,1);
    if ((lVar2 < 0) ||
       (lVar2 = (**(code **)(lVar1 + 0x58))(2,2,0,1,&local_res20,param_1,0), lVar2 < 0)) {
      (**(code **)(lVar1 + 0x60))(0x60,1);
    }
    else {
      lVar2 = (**(code **)(DAT_00000cf0 + 0x50))(0x200,8,0x280,0,0xd08);
      if (-1 < lVar2) {
        lVar2 = (**(code **)(DAT_00000cf0 + 0xa8))(0xc50,DAT_00000d08,0xd48);
      }
      if (lVar2 < 0) {
        (**(code **)(lVar1 + 0x60))(100,1);
        (**(code **)(lVar1 + 0x60))(0x60,1);
      }
      else {
        local_48[0] = 2;
        lVar1 = (**(code **)(DAT_00000cf8 + 0x48))(0xca0,0xc88,0,local_48,local_res18);
        if (lVar1 == -0x7ffffffffffffff2) {
          local_res18[0] = 0xe307;
        }
        local_res18[0] = local_res18[0] | 2;
        local_48[0] = 2;
        lVar2 = (**(code **)(DAT_00000cf8 + 0x58))(0xca0,0xc88,2,2,local_res18);
      }
    }
  }
  return lVar2;
}


// ==== FUN_0000085c @ 0000085c

longlong FUN_0000085c(longlong param_1)

{
  longlong lVar1;
  longlong lVar2;
  longlong *plVar3;
  
  lVar2 = *(longlong *)(param_1 + 0x68);
  plVar3 = *(longlong **)(param_1 + 0x70);
  while( true ) {
    if (lVar2 == 0) {
      return 0;
    }
    lVar1 = FUN_00000a34(plVar3);
    if (lVar1 == 0) break;
    plVar3 = plVar3 + 3;
    lVar2 = lVar2 + -1;
  }
  return plVar3[2];
}


// ==== FUN_00000894 @ 00000894

undefined8 FUN_00000894(undefined8 param_1)

{
  undefined8 local_res10 [3];
  
  local_res10[0] = 0;
  (**(code **)(DAT_00000cf0 + 0x40))(4,param_1,local_res10);
  return local_res10[0];
}


// ==== FUN_000008c0 @ 000008c0

longlong FUN_000008c0(char *param_1)

{
  uint uVar1;
  longlong lVar2;
  
  if (param_1 == (char *)0x0) {
    return 0;
  }
  lVar2 = 0;
  while( true ) {
    if ((*param_1 == '\x7f') && (param_1[1] == -1)) {
      return lVar2 + 4;
    }
    uVar1 = (uint)(byte)param_1[3] * 0x100 + (uint)(byte)param_1[2];
    if ((*param_1 == '\0') || (uVar1 == 0)) break;
    lVar2 = lVar2 + (ulonglong)uVar1;
    param_1 = param_1 + (ulonglong)(byte)param_1[3] * 0x100 + (ulonglong)(byte)param_1[2];
  }
  return lVar2;
}


// ==== FUN_00000914 @ 00000914

undefined8 * FUN_00000914(char *param_1,undefined8 *param_2)

{
  undefined8 *puVar1;
  longlong lVar2;
  ulonglong uVar3;
  undefined8 *puVar4;
  
  if (param_2 == (undefined8 *)0x0) {
    if (param_1 == (char *)0x0) {
      param_1 = (char *)&DAT_00000c80;
    }
    puVar1 = FUN_000009ec(param_1);
  }
  else {
    if (param_1 == (char *)0x0) {
      uVar3 = 0;
    }
    else {
      lVar2 = FUN_000008c0(param_1);
      uVar3 = lVar2 - 4;
    }
    puVar1 = (undefined8 *)
             FUN_00000894((ulonglong)*(byte *)((longlong)param_2 + 2) + 4 +
                          (ulonglong)*(byte *)((longlong)param_2 + 3) * 0x100 + uVar3);
    puVar4 = puVar1;
    if (uVar3 != 0) {
      FUN_00000b60(puVar1,(undefined8 *)param_1,uVar3);
      puVar4 = (undefined8 *)((longlong)puVar1 + uVar3);
    }
    FUN_00000b60(puVar4,param_2,(ulonglong)*(ushort *)((longlong)param_2 + 2));
    *(undefined4 *)
     ((longlong)puVar4 +
     (ulonglong)*(byte *)((longlong)param_2 + 2) +
     (ulonglong)*(byte *)((longlong)param_2 + 3) * 0x100) = DAT_00000c80;
  }
  return puVar1;
}


// ==== FUN_000009ec @ 000009ec

undefined8 * FUN_000009ec(char *param_1)

{
  ulonglong uVar1;
  undefined8 *puVar2;
  
  uVar1 = FUN_000008c0(param_1);
  puVar2 = (undefined8 *)FUN_00000894(uVar1);
  FUN_00000b60(puVar2,(undefined8 *)param_1,uVar1);
  return puVar2;
}


// ==== FUN_00000a34 @ 00000a34

longlong FUN_00000a34(longlong *param_1)

{
  longlong *plVar1;
  longlong *plVar2;
  longlong lVar3;
  
  plVar2 = (longlong *)&DAT_00000c40;
  plVar1 = param_1;
  if ((((ulonglong)param_1 & 7) != 0) && (((ulonglong)param_1 & 7) == 0)) {
    lVar3 = 8;
    do {
      if ((char)*plVar1 != (char)*plVar2) break;
      plVar1 = (longlong *)((longlong)plVar1 + 1);
      plVar2 = (longlong *)((longlong)plVar2 + 1);
      lVar3 = lVar3 + -1;
    } while (lVar3 != 0);
  }
  for (; (plVar1 <= param_1 + 1 && (*plVar1 == *plVar2)); plVar1 = plVar1 + 1) {
    plVar2 = plVar2 + 1;
  }
  while( true ) {
    if (param_1 + 2 <= plVar1) {
      return 0;
    }
    if ((char)*plVar1 != (char)*plVar2) break;
    plVar1 = (longlong *)((longlong)plVar1 + 1);
    plVar2 = (longlong *)((longlong)plVar2 + 1);
  }
  return (longlong)((int)(char)*plVar1 - (int)(char)*plVar2);
}


// ==== FUN_00000b60 @ 00000b60

undefined8 * FUN_00000b60(undefined8 *param_1,undefined8 *param_2,ulonglong param_3)

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


