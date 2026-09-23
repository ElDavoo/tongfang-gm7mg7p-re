// OemServiceDxe.efi: Ghidra x86:LE:64:default decompile, unedited
// ==== FUN_000002a0 @ 000002a0

undefined8 * FUN_000002a0(undefined8 *param_1,ulonglong param_2)

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


// ==== FUN_000002c0 @ 000002c0

undefined8 * FUN_000002c0(undefined8 *param_1,undefined8 *param_2,ulonglong param_3)

{
  ulonglong uVar1;
  undefined8 *puVar2;
  undefined8 *puVar3;
  ulonglong uVar4;
  byte bVar5;
  
  bVar5 = 0;
  puVar2 = (undefined8 *)((longlong)param_2 + (param_3 - 1));
  if ((param_2 < param_1) && (param_1 <= puVar2)) {
    puVar3 = (undefined8 *)((longlong)param_1 + (param_3 - 1));
    bVar5 = 1;
    uVar4 = param_3;
  }
  else {
    uVar4 = param_3 & 7;
    puVar2 = param_2;
    puVar3 = param_1;
    for (uVar1 = param_3 >> 3; uVar1 != 0; uVar1 = uVar1 - 1) {
      *puVar3 = *puVar2;
      puVar2 = puVar2 + 1;
      puVar3 = puVar3 + 1;
    }
  }
  for (; uVar4 != 0; uVar4 = uVar4 - 1) {
    *(undefined1 *)puVar3 = *(undefined1 *)puVar2;
    puVar2 = (undefined8 *)((longlong)puVar2 + (ulonglong)bVar5 * -2 + 1);
    puVar3 = (undefined8 *)((longlong)puVar3 + (ulonglong)bVar5 * -2 + 1);
  }
  return param_1;
}


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

void entry(undefined8 param_1,longlong param_2)

{
  FUN_0000037c(param_1,param_2);
  FUN_000004a4(param_1,param_2);
  return;
}


// ==== FUN_0000037c @ 0000037c

void FUN_0000037c(undefined8 param_1,longlong param_2)

{
  uint uVar1;
  int iVar2;
  short *psVar3;
  ulonglong uVar4;
  longlong lVar5;
  
  DAT_000013b8 = *(longlong *)(param_2 + 0x60);
  DAT_000013b0 = param_2;
  FUN_00001054();
  psVar3 = (short *)FUN_00001054();
  do {
    if (*psVar3 == -1) {
      psVar3 = (short *)0x0;
LAB_000003d0:
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
LAB_00000439:
        if ((DAT_000013e0 != (undefined8 *)0x0) ||
           (lVar5 = (**(code **)(DAT_000013b8 + 0x140))(&DAT_00001300,0,&DAT_000013e0), -1 < lVar5))
        {
          (*(code *)*DAT_000013e0)(DAT_000013e0,&DAT_000013e8);
        }
                    /* WARNING: Could not recover jumptable at 0x0000049b. Too many branches */
                    /* WARNING: Treating indirect jump as call */
        (**(code **)(DAT_000013b8 + 0x140))(&DAT_000012d0,0,&DAT_000013f0);
        return;
      }
      if ((DAT_00001348 == *(longlong *)(psVar3 + 4)) && (DAT_00001350 == *(longlong *)(psVar3 + 8))
         ) goto LAB_00000439;
    }
    else if (*psVar3 == 4) goto LAB_000003d0;
    psVar3 = (short *)((longlong)psVar3 + (ulonglong)(ushort)psVar3[1]);
  } while( true );
}


// ==== FUN_000004a4 @ 000004a4

longlong FUN_000004a4(undefined8 param_1,longlong param_2)

{
  longlong lVar1;
  ulonglong uVar2;
  undefined8 local_res18;
  undefined1 local_res20 [8];
  
  uVar2 = 0;
  if (DAT_000013d0 == 0) {
    DAT_000013c0 = *(longlong *)(param_2 + 0x60);
    DAT_000013c8 = *(undefined8 *)(param_2 + 0x58);
    DAT_000013d0 = param_2;
  }
  lVar1 = (**(code **)(DAT_000013c0 + 0x40))(6,0x20,&DAT_000013a0);
  if (-1 < lVar1) {
    FUN_000002a0(DAT_000013a0,0x20);
    lVar1 = (**(code **)(DAT_000013c0 + 0x40))(10,0x70000,DAT_000013a0 + 1);
    if (lVar1 < 0) {
      if (DAT_000013a0 != (undefined8 *)0x0) {
        (**(code **)(DAT_000013c0 + 0x48))();
      }
    }
    else {
      FUN_000002a0((undefined8 *)DAT_000013a0[1],0x70000);
      lVar1 = (**(code **)(DAT_000013c0 + 0x140))(&DAT_000012f0,0,&DAT_000013a8);
      if (lVar1 < 0) {
        DAT_000013a8 = uVar2;
      }
      DAT_000013a0[2] = 0x84c;
      DAT_000013a0[3] = 0x9c0;
      local_res18 = 0;
      lVar1 = (**(code **)(DAT_000013c0 + 0x148))(&local_res18,&DAT_000012c0,DAT_000013a0,0);
      if (-1 < lVar1) {
        (**(code **)(DAT_000013c0 + 0x170))(0x200,8,0x668,0,&DAT_00001338,local_res20);
        do {
          (**(code **)((longlong)&DAT_00001320 + uVar2))(param_1,param_2);
          uVar2 = uVar2 + 8;
        } while (uVar2 < 0x18);
        lVar1 = 0;
      }
    }
  }
  return lVar1;
}


// ==== FUN_000007c8 @ 000007c8

longlong FUN_000007c8(void)

{
  longlong lVar1;
  byte *pbVar2;
  byte local_res18 [8];
  byte local_res20 [8];
  
  pbVar2 = local_res18;
  lVar1 = (**(code **)(DAT_000013a0 + 0x18))(pbVar2,1,0x33);
  if (-1 < lVar1) {
    if (local_res18[0] == 0xff) {
      lVar1 = -0x7ffffffffffffffa;
    }
    else if (local_res18[0] < 8) {
      lVar1 = FUN_00000fb8(pbVar2,4,0x9f,local_res20);
      if (-1 < lVar1) {
        lVar1 = FUN_00000f58(pbVar2,4,0x9f,
                             (local_res18[0] << 3 ^ local_res20[0]) & 0x38 ^ local_res20[0] | 4);
      }
    }
    else {
      lVar1 = -0x7ffffffffffffff7;
    }
  }
  return lVar1;
}


// ==== FUN_00000a08 @ 00000a08

/* WARNING: Type propagation algorithm not settling */

void FUN_00000a08(void)

{
  longlong lVar1;
  longlong lVar2;
  undefined8 *puVar3;
  undefined1 uVar4;
  byte local_res8 [8];
  undefined4 local_res10 [2];
  undefined1 local_res18 [5];
  byte bStackX_1d;
  byte bStackX_1e;
  byte bStackX_1f;
  undefined8 local_res20;
  undefined1 local_e8 [9];
  byte local_df;
  byte local_de;
  byte local_dd;
  byte local_dc;
  
  local_res20 = 0xb4;
  local_res10[0] = 7;
  _local_res18 = 0;
  lVar1 = (**(code **)(DAT_000013c8 + 0x48))
                    (u_UniWillVariable_00001360,&DAT_00001310,local_res10,&local_res20,local_e8);
  if (-1 < lVar1) {
    puVar3 = (undefined8 *)local_res18;
    (**(code **)(DAT_000013a0 + 0x18))(puVar3,1,0x2e);
    if (local_res18._0_4_ != 0xff) {
      puVar3 = (undefined8 *)(ulonglong)local_df;
      if (CONCAT31(0,local_df) != local_res18._0_4_) {
        if (local_df == 1) {
          local_res18 = (undefined1  [5])0x8000000001;
        }
        else {
          if (local_df == 0xfe) {
            local_res18[4] = 0;
          }
          local_res18._0_4_ = CONCAT31(0,local_df);
        }
        (**(code **)(DAT_000013a0 + 0x10))(local_res18,1,0x2e);
        puVar3 = (undefined8 *)((longlong)local_res18 + 4);
        (**(code **)(DAT_000013a0 + 0x10))(puVar3,1,0x2f);
      }
    }
    if (local_res18._0_4_ != 0) {
      if (local_res18._0_4_ == 0xff) {
        lVar1 = FUN_00000fb8(puVar3,7,0x48,local_res8);
        if (lVar1 < 0) {
          return;
        }
        uVar4 = 0x48;
        local_res8[0] = local_res8[0] | 0x80;
      }
      else {
        lVar1 = (longlong)local_res18 + 4;
        lVar2 = (**(code **)(DAT_000013a0 + 0x18))(lVar1,1,0x2f);
        if ((-1 < lVar2) && (lVar2 = FUN_00000fb8(lVar1,7,0x48,local_res8), -1 < lVar2)) {
          local_res8[0] = local_res8[0] & 0x7f;
          if ((_local_res18 & 0x8000000000) != 0) {
            local_res8[0] = local_res8[0] | 0x80;
          }
          FUN_00000f58(lVar1,7,0x48,local_res8[0]);
        }
        lVar1 = (longlong)local_res18 + 5;
        lVar2 = (**(code **)(DAT_000013a0 + 0x18))(lVar1,1,0x30);
        if ((-1 < lVar2) && (bStackX_1d < 0xc9)) {
          if (local_de != bStackX_1d) {
            _local_res18 = CONCAT15(local_de,local_res18);
            lVar1 = (longlong)local_res18 + 5;
            (**(code **)(DAT_000013a0 + 0x10))(lVar1,1,0x30);
          }
          FUN_00000f58(lVar1,7,0x49,bStackX_1d);
        }
        lVar1 = (longlong)local_res18 + 6;
        lVar2 = (**(code **)(DAT_000013a0 + 0x18))(lVar1,1,0x31);
        if ((-1 < lVar2) && (bStackX_1e < 0xc9)) {
          if (local_dd != bStackX_1e) {
            _local_res18 = CONCAT16(local_dd,_local_res18);
            lVar1 = (longlong)local_res18 + 6;
            (**(code **)(DAT_000013a0 + 0x10))(lVar1,1,0x31);
          }
          FUN_00000f58(lVar1,7,0x4a,bStackX_1e);
        }
        puVar3 = (undefined8 *)((longlong)local_res18 + 7);
        lVar1 = (**(code **)(DAT_000013a0 + 0x18))(puVar3,1,0x32);
        if (lVar1 < 0) {
          return;
        }
        if (200 < bStackX_1f) {
          return;
        }
        local_res8[0] = bStackX_1f;
        if (local_dc != bStackX_1f) {
          _local_res18 = CONCAT17(local_dc,_local_res18);
          puVar3 = (undefined8 *)((longlong)local_res18 + 7);
          (**(code **)(DAT_000013a0 + 0x10))(puVar3,1,0x32);
          local_res8[0] = bStackX_1f;
        }
        uVar4 = 0x4b;
      }
      FUN_00000f58(puVar3,7,uVar4,local_res8[0]);
    }
  }
  return;
}


// ==== FUN_00000c64 @ 00000c64

undefined8 FUN_00000c64(undefined8 param_1,longlong param_2)

{
  if (DAT_000013d0 == 0) {
    DAT_000013c0 = *(undefined8 *)(param_2 + 0x60);
    DAT_000013c8 = *(undefined8 *)(param_2 + 0x58);
    DAT_000013d0 = param_2;
  }
  FUN_00000a08();
  return 0;
}


// ==== FUN_00000c9c @ 00000c9c

longlong FUN_00000c9c(void)

{
  longlong lVar1;
  byte *pbVar2;
  byte bVar3;
  byte local_res18 [8];
  byte local_res20 [8];
  
  pbVar2 = local_res20;
  lVar1 = (**(code **)(DAT_000013a0 + 0x18))(pbVar2,1,0x34);
  if (-1 < lVar1) {
    if (local_res20[0] == 0xff) {
      lVar1 = -0x7ffffffffffffffa;
    }
    else if (local_res20[0] < 2) {
      lVar1 = FUN_00000fb8(pbVar2,7,0x4e,local_res18);
      if (-1 < lVar1) {
        if ((local_res20[0] == 0) || (local_res20[0] != 1)) {
          bVar3 = local_res18[0] & 0xf7;
        }
        else {
          bVar3 = local_res18[0] | 8;
        }
        if (bVar3 != local_res18[0]) {
          lVar1 = FUN_00000f58(CONCAT71((int7)((ulonglong)pbVar2 >> 8),local_res18[0]),7,0x4e,bVar3)
          ;
        }
      }
    }
    else {
      lVar1 = -0x7ffffffffffffff7;
    }
  }
  return lVar1;
}


// ==== FUN_00000d2c @ 00000d2c

undefined8 FUN_00000d2c(char param_1,undefined1 param_2)

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
      FUN_00001120(0xf);
      bVar2 = in(uVar1);
      uVar3 = uVar3 + 1;
    } while ((bVar2 & 2) != 0);
    if (0x1ffff < uVar3) {
      return 0x8000000000000007;
    }
  }
  out(uVar1,param_2);
  return 0;
}


// ==== FUN_00000da4 @ 00000da4

undefined8 FUN_00000da4(char param_1)

{
  undefined2 uVar1;
  byte bVar2;
  undefined1 uVar3;
  undefined2 uVar4;
  ulonglong uVar5;
  
  uVar5 = 0;
  uVar1 = 100;
  if (param_1 != '`') {
    uVar1 = 0x66;
  }
  bVar2 = in(uVar1);
  if ((bVar2 & 1) != 0) {
    do {
      if (0x1ffff < uVar5) {
        return 0x8000000000000007;
      }
      uVar4 = 0x60;
      if (param_1 != '`') {
        uVar4 = 0x62;
      }
      uVar3 = in(uVar4);
      out(0x80,uVar3);
      FUN_00001120(5000);
      bVar2 = in(uVar1);
      uVar5 = uVar5 + 1;
    } while ((bVar2 & 1) != 0);
    if (0x1ffff < uVar5) {
      return 0x8000000000000007;
    }
  }
  return 0;
}


// ==== FUN_00000e2c @ 00000e2c

undefined8 FUN_00000e2c(char param_1)

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
      FUN_00001120(0xf);
      bVar2 = in(uVar1);
      uVar3 = uVar3 + 1;
    } while ((bVar2 & 2) != 0);
    if (0x1ffff < uVar3) {
      return 0x8000000000000007;
    }
  }
  return 0;
}


// ==== FUN_00000e90 @ 00000e90

longlong FUN_00000e90(char param_1,undefined1 param_2,undefined1 param_3)

{
  byte bVar1;
  byte bVar2;
  longlong lVar3;
  ulonglong uVar4;
  undefined2 uVar5;
  
  lVar3 = FUN_00000e2c(param_1);
  uVar4 = 0;
  if (lVar3 < 0) {
    return lVar3;
  }
  FUN_00000da4(param_1);
  FUN_00000d2c(param_1,param_2);
  FUN_00000e2c(param_1);
  uVar5 = 0x60;
  bVar1 = 100;
  if (param_1 != '`') {
    bVar1 = 0x66;
  }
  bVar2 = in((ushort)bVar1);
  if ((bVar2 & 2) != 0) {
    do {
      if (0x1ffff < uVar4) goto LAB_00000f32;
      FUN_00001120(0xf);
      bVar2 = in((ushort)bVar1);
      uVar4 = uVar4 + 1;
    } while ((bVar2 & 2) != 0);
    if (0x1ffff < uVar4) goto LAB_00000f32;
  }
  if (param_1 != '`') {
    uVar5 = 0x62;
  }
  out(uVar5,param_3);
LAB_00000f32:
  FUN_00000da4(param_1);
  return lVar3;
}


// ==== FUN_00000f58 @ 00000f58

longlong FUN_00000f58(undefined8 param_1,undefined1 param_2,undefined1 param_3,undefined1 param_4)

{
  longlong lVar1;
  longlong lVar2;
  
  lVar1 = FUN_00000e90('b',0xa3,param_2);
  if (((-1 < lVar1) && (lVar1 = FUN_00000e90('b',0xa2,param_3), -1 < lVar1)) &&
     (lVar2 = FUN_00000e90('b',0xa5,param_4), lVar1 = 0, lVar2 < 0)) {
    lVar1 = lVar2;
  }
  return lVar1;
}


// ==== FUN_00000fb8 @ 00000fb8

longlong FUN_00000fb8(undefined8 param_1,undefined1 param_2,undefined1 param_3,undefined1 *param_4)

{
  byte bVar1;
  undefined1 uVar2;
  longlong lVar3;
  ulonglong uVar4;
  
  uVar4 = 0;
  lVar3 = FUN_00000e90('b',0xa3,param_2);
  if (((-1 < lVar3) && (lVar3 = FUN_00000e90('b',0xa2,param_3), -1 < lVar3)) &&
     (lVar3 = FUN_00000d2c('b',0xa4), -1 < lVar3)) {
    bVar1 = in(0x66);
    if ((bVar1 & 1) == 0) {
      do {
        if (0x1ffff < uVar4) {
          return -0x7ffffffffffffff9;
        }
        FUN_00001120(0xf);
        bVar1 = in(0x66);
        uVar4 = uVar4 + 1;
      } while ((bVar1 & 1) == 0);
      if (0x1ffff < uVar4) {
        return -0x7ffffffffffffff9;
      }
    }
    uVar2 = in(0x62);
    *param_4 = uVar2;
    lVar3 = 0;
  }
  return lVar3;
}


// ==== FUN_00001054 @ 00001054

longlong FUN_00001054(void)

{
  ulonglong uVar1;
  longlong *plVar2;
  
  uVar1 = 0;
  if (DAT_000013d8 == 0) {
    DAT_000013d8 = 0;
    if (*(ulonglong *)(DAT_000013b0 + 0x68) != 0) {
      plVar2 = *(longlong **)(DAT_000013b0 + 0x70);
      do {
        if ((DAT_000012e0 == *plVar2) && (DAT_000012e8 == plVar2[1])) {
          DAT_000013d8 = (*(longlong **)(DAT_000013b0 + 0x70))[uVar1 * 3 + 2];
          return DAT_000013d8;
        }
        uVar1 = uVar1 + 1;
        plVar2 = plVar2 + 3;
      } while (uVar1 < *(ulonglong *)(DAT_000013b0 + 0x68));
    }
  }
  return DAT_000013d8;
}


// ==== FUN_000010c0 @ 000010c0

void FUN_000010c0(uint param_1)

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


// ==== FUN_00001120 @ 00001120

longlong FUN_00001120(longlong param_1)

{
  FUN_000010c0((uint)((ulonglong)(param_1 * 0x369e99) / 1000000));
  return param_1;
}


