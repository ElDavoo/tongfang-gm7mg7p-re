// OemACRecoveryDxe.efi: Ghidra x86:LE:64:default decompile, unedited
// ==== entry @ 000002c0

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void entry(undefined8 param_1,longlong param_2)

{
  _DAT_000005f8 = *(undefined8 *)(param_2 + 0x60);
  _DAT_000005f0 = param_2;
  FUN_000002e0(param_1,param_2);
  return;
}


// ==== FUN_000002e0 @ 000002e0

longlong FUN_000002e0(undefined8 param_1,longlong param_2)

{
  longlong lVar1;
  undefined4 local_res8;
  undefined4 uStackX_c;
  undefined4 local_res18 [2];
  undefined8 local_res20;
  undefined4 local_7e8;
  undefined4 local_7e4;
  undefined4 local_7e0;
  undefined4 local_7dc;
  undefined8 local_7d8 [2];
  undefined1 local_7c8 [95];
  char local_769;
  undefined1 local_708 [27];
  undefined1 local_6ed;
  
  local_res20 = 0x6f2;
  local_7e8 = 0x4570b7f1;
  local_7e4 = 0x4943ade8;
  local_7e0 = 0x6440c38d;
  local_7dc = 0x84238472;
  local_7d8[0] = 0xb4;
  _local_res8 = CONCAT44((int)((ulonglong)param_1 >> 0x20),7);
  if (DAT_00000608 == 0) {
    DAT_00000600 = *(longlong *)(param_2 + 0x58);
    DAT_00000608 = param_2;
  }
  lVar1 = (**(code **)(DAT_00000600 + 0x48))(0x590,0x580,&local_res8,local_7d8,local_7c8);
  if (-1 < lVar1) {
    (**(code **)(DAT_00000600 + 0x48))(0x5b0,&local_7e8,local_res18,&local_res20,local_708);
    if (local_769 == '\0') {
      local_6ed = 1;
    }
    if (local_769 == '\x01') {
      local_6ed = 0;
    }
    (**(code **)(DAT_00000600 + 0x58))(0x5b0,&local_7e8,local_res18[0],local_res20,local_708);
    lVar1 = 0;
  }
  return lVar1;
}


