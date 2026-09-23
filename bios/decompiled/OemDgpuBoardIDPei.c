// OemDgpuBoardIDPei.efi: Ghidra x86:LE:32:default decompile, unedited
// ==== entry @ fffac38d

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void entry(void)

{
  undefined4 in_ECX;
  undefined4 local_8;
  
  local_8 = in_ECX;
  FUN_fffac60c(in_ECX,&local_8,in_ECX);
  FUN_fffac3b2();
  return;
}


// ==== FUN_fffac3b2 @ fffac3b2

int __regparm3 FUN_fffac3b2(undefined4 param_1,int *param_2)

{
  int iVar1;
  undefined4 *puVar2;
  undefined4 local_c0 [45];
  undefined4 *local_c;
  undefined4 local_8;
  
  iVar1 = (**(code **)(*param_2 + 0x20))(param_2,&DAT_fffac688,0,0,&local_c);
  if (-1 < iVar1) {
    local_8 = 0xb4;
    iVar1 = (*(code *)*local_c)(local_c,u_UniWillVariable_fffacae8,&DAT_fffac6b8,0,&local_8,local_c0
                               );
    if (-1 < iVar1) {
      puVar2 = &DAT_fffaca50;
      iVar1 = 10;
      do {
        *puVar2 = local_c0[0];
        puVar2 = puVar2 + 4;
        iVar1 = iVar1 + -1;
      } while (iVar1 != 0);
      puVar2 = &DAT_fffac6f0;
      iVar1 = 0x35;
      do {
        *puVar2 = local_c0[0];
        puVar2 = puVar2 + 4;
        iVar1 = iVar1 + -1;
      } while (iVar1 != 0);
      FUN_fffac462();
      (&DAT_fffac6f0)[(uint)DAT_fffacb24 * 4] = DAT_fffacb28;
      FUN_fffac5ba();
      FUN_fffac5ba();
    }
    iVar1 = 0;
  }
  return iVar1;
}


// ==== FUN_fffac462 @ fffac462

/* WARNING: Type propagation algorithm not settling */

undefined4 FUN_fffac462(void)

{
  undefined4 uVar1;
  undefined1 uVar2;
  int iVar3;
  undefined4 in_ECX;
  undefined4 extraout_ECX;
  undefined4 *puVar4;
  int local_c0 [2];
  undefined4 *local_b8;
  undefined4 local_b4 [45];
  
  uVar2 = DAT_ff430039;
  local_c0[0] = 0;
  FUN_fffac5df(in_ECX,&local_b8);
  local_c0[1] = 0xb4;
  (*(code *)*local_b8)(local_b8,u_UniWillVariable_fffacae8,&DAT_fffac6b8,0,local_c0 + 1,local_b4);
  switch(uVar2) {
  case 0:
    local_b4[0] = 0x11231d05;
    break;
  case 1:
    local_b4[0] = 0x10851d05;
    break;
  case 2:
    local_b4[0] = 0x10881d05;
    break;
  case 3:
    local_b4[0] = 0x11221d05;
    break;
  case 4:
    local_b4[0] = 0x11161d05;
    break;
  case 5:
    local_b4[0] = 0x11351d05;
    break;
  case 6:
    local_b4[0] = 0x11211d05;
    break;
  case 7:
    local_b4[0] = 0x11361d05;
    break;
  case 8:
    local_b4[0] = 0x112b1d05;
    break;
  case 9:
    local_b4[0] = 0x112c1d05;
  }
  puVar4 = &DAT_fffac6e8;
  iVar3 = FUN_fffac5df(extraout_ECX,local_c0);
  if ((iVar3 == 0) && (*(int *)(local_c0[0] + 4) != 0)) {
    puVar4 = *(undefined4 **)(local_c0[0] + 4);
  }
  DAT_fffacb24 = 0;
  while (((uVar1 = puVar4[(uint)DAT_fffacb24 * 4], (char)((uint)uVar1 >> 0x18) != '\0' ||
          (((byte)((uint)uVar1 >> 0x10) & 0x1f) != 0x1f)) || (((byte)((uint)uVar1 >> 8) & 7) != 3)))
  {
    DAT_fffacb24 = DAT_fffacb24 + 1;
    if (0x45 < DAT_fffacb24) {
      DAT_fffacb28 = local_b4[0];
      return 0;
    }
  }
  DAT_fffacb28 = local_b4[0];
  return 0;
}


// ==== FUN_fffac5ba @ fffac5ba

void FUN_fffac5ba(void)

{
  undefined4 in_ECX;
  undefined1 local_10 [2];
  int iStack_e;
  undefined1 *local_8;
  
  local_8 = local_10;
  InterruptDescriptorTableRegister();
  (**(code **)(**(int **)(iStack_e + -4) + 0x18))(*(int **)(iStack_e + -4),in_ECX);
  return;
}


// ==== FUN_fffac5df @ fffac5df

void __regparm3
FUN_fffac5df(undefined4 param_1,undefined4 param_2,undefined4 param_3,undefined4 param_4,
            undefined4 param_5)

{
  undefined1 local_10 [2];
  int iStack_e;
  undefined1 *local_8;
  
  local_8 = local_10;
  InterruptDescriptorTableRegister();
  (**(code **)(**(int **)(iStack_e + -4) + 0x20))(*(int **)(iStack_e + -4),param_3,0,0,param_5);
  return;
}


// ==== FUN_fffac60c @ fffac60c

/* WARNING: Removing unreachable block (ram,0xfffac637) */
/* WARNING: Removing unreachable block (ram,0xfffac628) */
/* WARNING: Removing unreachable block (ram,0xfffac630) */
/* WARNING: Removing unreachable block (ram,0xfffac646) */

undefined4 FUN_fffac60c(undefined4 param_1,undefined4 *param_2)

{
  int iVar1;
  
  iVar1 = cpuid_Version_info(1);
  if (param_2 != (undefined4 *)0x0) {
    *param_2 = *(undefined4 *)(iVar1 + 0xc);
  }
  return 1;
}


