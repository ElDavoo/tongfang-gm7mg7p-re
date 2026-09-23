// OemDgpuBoardIDDxe.efi: Ghidra x86:LE:64:default decompile, unedited
// ==== FUN_00000300 @ 00000300

void FUN_00000300(void)

{
  return;
}


// ==== FUN_00000310 @ 00000310

ulonglong FUN_00000310(void)

{
  ulonglong uVar1;
  undefined8 in_RAX;
  
  uVar1 = rdtsc();
  return CONCAT44((int)((ulonglong)in_RAX >> 0x20),(int)uVar1) | uVar1 & 0xffffffff00000000;
}


// ==== FUN_00000320 @ 00000320

void FUN_00000320(void)

{
  return;
}


// ==== FUN_00000330 @ 00000330

void FUN_00000330(void)

{
  return;
}


// ==== FUN_00000340 @ 00000340

ulonglong FUN_00000340(void)

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


// ==== entry @ 00000350

void entry(ulonglong param_1,longlong param_2)

{
  FUN_0000036c(param_1,param_2);
  FUN_00000478(param_1,param_2);
  return;
}


// ==== FUN_0000036c @ 0000036c

void FUN_0000036c(undefined8 param_1,longlong param_2)

{
  uint uVar1;
  int iVar2;
  short *psVar3;
  ulonglong uVar4;
  longlong lVar5;
  
  DAT_000014e8 = *(longlong *)(param_2 + 0x60);
  DAT_000014e0 = param_2;
  FUN_00001118();
  psVar3 = (short *)FUN_00001118();
  do {
    if (*psVar3 == -1) {
      psVar3 = (short *)0x0;
LAB_000003c0:
      if (psVar3 == (short *)0x0) {
        uVar4 = FUN_00000340();
        FUN_00000330();
        uVar1 = in(0x1808);
        FUN_00000310();
        while (iVar2 = in(0x1808), (((uVar1 & 0xffffff) + 0x16b) - iVar2 >> 0x17 & 1) == 0) {
          FUN_00000300();
        }
        FUN_00000310();
        if ((uVar4 >> 9 & 1) == 0) {
          FUN_00000330();
        }
        else {
          FUN_00000320();
        }
LAB_00000429:
        if ((DAT_00001510 != (undefined8 *)0x0) ||
           (lVar5 = (**(code **)(DAT_000014e8 + 0x140))(&DAT_000013d0,0,&DAT_00001510), -1 < lVar5))
        {
          (*(code *)*DAT_00001510)(DAT_00001510,&DAT_00001518);
        }
        return;
      }
      if ((DAT_000013f8 == *(longlong *)(psVar3 + 4)) && (DAT_00001400 == *(longlong *)(psVar3 + 8))
         ) goto LAB_00000429;
    }
    else if (*psVar3 == 4) goto LAB_000003c0;
    psVar3 = (short *)((longlong)psVar3 + (ulonglong)(ushort)psVar3[1]);
  } while( true );
}


// ==== FUN_00000478 @ 00000478

longlong FUN_00000478(ulonglong param_1,longlong param_2)

{
  longlong lVar1;
  ulonglong local_res8;
  undefined8 local_res18;
  undefined1 local_res20 [8];
  undefined4 local_238;
  undefined4 local_234;
  undefined4 local_230;
  undefined4 local_22c;
  undefined1 local_228 [295];
  char local_101;
  
  local_res18 = 0;
  local_res8 = param_1 & 0xffffffff00000000;
  local_238 = 0x72c5e28c;
  local_234 = 0x43a17783;
  local_230 = 0xd7fa6787;
  local_22c = 0xa4afcc3f;
  if (DAT_00001500 == 0) {
    DAT_000014f0 = *(longlong *)(param_2 + 0x60);
    DAT_000014f8 = *(longlong *)(param_2 + 0x58);
    DAT_00001500 = param_2;
  }
  (**(code **)(DAT_000014f0 + 0x170))(0x200,8,0x750,0,&DAT_000013c0,local_res20);
  local_res18 = 0x21d;
  lVar1 = (**(code **)(DAT_000014f8 + 0x48))
                    (u_SaSetup_00001430,&local_238,&local_res8,&local_res18,local_228);
  if (-1 < lVar1) {
    if ((local_101 == '\x04') || (local_101 == '\x01')) {
      (**(code **)(DAT_000014f0 + 0x170))(0x200,8,0x8c4,0,&DAT_000013c0,local_res20);
    }
    lVar1 = 0;
  }
  return lVar1;
}


// ==== FUN_000008c4 @ 000008c4

void FUN_000008c4(longlong param_1)

{
  byte bVar1;
  char cVar2;
  longlong lVar3;
  ulonglong uVar4;
  undefined4 local_res8 [2];
  undefined4 local_res18 [2];
  undefined8 local_res20;
  undefined4 local_318;
  undefined4 local_314;
  undefined4 local_310;
  undefined4 local_30c;
  undefined8 local_308;
  longlong *local_300;
  undefined8 *local_2f8 [2];
  undefined4 local_2e8 [48];
  undefined1 local_228 [295];
  char local_101;
  
  local_res18[0] = 0;
  local_res20 = 0;
  local_318 = 0x72c5e28c;
  local_314 = 0x43a17783;
  local_310 = 0xd7fa6787;
  local_30c = 0xa4afcc3f;
  if (param_1 != 0) {
    (**(code **)(DAT_000014f0 + 0x70))();
  }
  lVar3 = (**(code **)(DAT_000014f0 + 0x140))(&DAT_000013a0,0,&local_300);
  if (-1 < lVar3) {
    lVar3 = (**(code **)(DAT_000014f0 + 0x140))(&DAT_00001390,0,local_2f8);
    if (-1 < lVar3) {
      cVar2 = FUN_00000df8();
      bVar1 = DAT_e0008019;
      if (((cVar2 != '\x02') && (DAT_e0008019 != 0xff)) &&
         (*(short *)(((ulonglong)DAT_e0008019 + 0xe00) * 0x100000) == 0x10de)) {
        local_res20 = 0x21d;
        (**(code **)(DAT_000014f8 + 0x48))
                  (u_SaSetup_00001430,&local_318,local_res18,&local_res20,local_228);
        if ((local_101 == '\x04') || (local_101 == '\x01')) {
          local_res8[0] = 0x108b1d05;
          local_308 = 0xb4;
          lVar3 = (**(code **)(DAT_000014f8 + 0x48))
                            (u_UniWillVariable_00001410,&DAT_000013e0,0,&local_308,local_2e8);
          if (-1 < lVar3) {
            local_res8[0] = local_2e8[0];
          }
          uVar4 = (ulonglong)bVar1 << 0x14 | 0x40;
          *(undefined4 *)(uVar4 + 0xe0000000) = local_res8[0];
          *(undefined4 *)(*local_300 + 0x2c) = *(undefined4 *)(uVar4 + 0xe0000000);
          (*(code *)*local_2f8[0])
                    (local_2f8[0],2,2,(int)((ulonglong)bVar1 << 0x14) + -0x1fffffc0,1,local_res8);
        }
      }
    }
  }
  return;
}


// ==== FUN_00000df8 @ 00000df8

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_00000df8(void)

{
  ushort uVar1;
  
  if (DAT_000013f0 != -1) {
    return;
  }
  uVar1 = _DAT_e00f8002 & 0xffe0;
  if (uVar1 != 0x280) {
    if (uVar1 == 0x680) {
      DAT_000013f0 = 1;
      return;
    }
    if (uVar1 != 0x9d80) {
      if (uVar1 == 0xa300) {
        DAT_000013f0 = 1;
        return;
      }
      DAT_000013f0 = 0xff;
      return;
    }
  }
  DAT_000013f0 = 2;
  return;
}


// ==== FUN_00000f50 @ 00000f50

undefined8 FUN_00000f50(char param_1)

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
      FUN_000011e4(0xf);
      bVar2 = in(uVar1);
      uVar3 = uVar3 + 1;
    } while ((bVar2 & 2) != 0);
    if (0x1ffff < uVar3) {
      return 0x8000000000000007;
    }
  }
  return 0;
}


// ==== FUN_00001118 @ 00001118

longlong FUN_00001118(void)

{
  ulonglong uVar1;
  longlong *plVar2;
  
  uVar1 = 0;
  if (DAT_00001508 == 0) {
    DAT_00001508 = 0;
    if (*(ulonglong *)(DAT_000014e0 + 0x68) != 0) {
      plVar2 = *(longlong **)(DAT_000014e0 + 0x70);
      do {
        if ((DAT_000013b0 == *plVar2) && (DAT_000013b8 == plVar2[1])) {
          DAT_00001508 = (*(longlong **)(DAT_000014e0 + 0x70))[uVar1 * 3 + 2];
          return DAT_00001508;
        }
        uVar1 = uVar1 + 1;
        plVar2 = plVar2 + 3;
      } while (uVar1 < *(ulonglong *)(DAT_000014e0 + 0x68));
    }
  }
  return DAT_00001508;
}


// ==== FUN_00001184 @ 00001184

void FUN_00001184(uint param_1)

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
      FUN_00000300();
    }
    bVar6 = uVar3 != 0;
    uVar3 = uVar3 - 1;
  } while (bVar6);
  return;
}


// ==== FUN_000011e4 @ 000011e4

longlong FUN_000011e4(longlong param_1)

{
  FUN_00001184((uint)((ulonglong)(param_1 * 0x369e99) / 1000000));
  return param_1;
}


