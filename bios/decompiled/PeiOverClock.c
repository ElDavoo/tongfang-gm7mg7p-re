// PeiOverClock.efi: Ghidra x86:LE:32:default decompile, unedited
// ==== entry @ ffcfbb49

int entry(void)

{
  int iVar1;
  
  iVar1 = FUN_ffcfbb55();
  if (-1 < iVar1) {
    iVar1 = 0;
  }
  return iVar1;
}


// ==== FUN_ffcfbb55 @ ffcfbb55

void FUN_ffcfbb55(void)

{
  undefined1 local_10 [2];
  int iStack_e;
  undefined1 *local_8;
  
  local_8 = local_10;
  InterruptDescriptorTableRegister();
  (**(code **)(**(int **)(iStack_e + -4) + 0x18))(*(int **)(iStack_e + -4),&DAT_ffcfbbc0);
  return;
}


