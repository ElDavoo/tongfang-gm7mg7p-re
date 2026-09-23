// OemGlobalNvsDxe.efi: Ghidra x86:LE:64:default decompile, unedited
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


// ==== FUN_000002b0 @ 000002b0

int FUN_000002b0(int param_1,undefined4 *param_2,undefined4 *param_3,undefined4 *param_4,
                undefined4 *param_5)

{
  undefined4 *puVar1;
  undefined4 uVar2;
  undefined4 uVar3;
  undefined4 uVar4;
  
  if (param_1 == 0) {
    puVar1 = (undefined4 *)cpuid_basic_info(0);
  }
  else if (param_1 == 1) {
    puVar1 = (undefined4 *)cpuid_Version_info(1);
  }
  else if (param_1 == 2) {
    puVar1 = (undefined4 *)cpuid_cache_tlb_info(2);
  }
  else if (param_1 == 3) {
    puVar1 = (undefined4 *)cpuid_serial_info(3);
  }
  else if (param_1 == 4) {
    puVar1 = (undefined4 *)cpuid_Deterministic_Cache_Parameters_info(4);
  }
  else if (param_1 == 5) {
    puVar1 = (undefined4 *)cpuid_MONITOR_MWAIT_Features_info(5);
  }
  else if (param_1 == 6) {
    puVar1 = (undefined4 *)cpuid_Thermal_Power_Management_info(6);
  }
  else if (param_1 == 7) {
    puVar1 = (undefined4 *)cpuid_Extended_Feature_Enumeration_info(7);
  }
  else if (param_1 == 9) {
    puVar1 = (undefined4 *)cpuid_Direct_Cache_Access_info(9);
  }
  else if (param_1 == 10) {
    puVar1 = (undefined4 *)cpuid_Architectural_Performance_Monitoring_info(10);
  }
  else if (param_1 == 0xb) {
    puVar1 = (undefined4 *)cpuid_Extended_Topology_info(0xb);
  }
  else if (param_1 == 0xd) {
    puVar1 = (undefined4 *)cpuid_Processor_Extended_States_info(0xd);
  }
  else if (param_1 == 0xf) {
    puVar1 = (undefined4 *)cpuid_Quality_of_Service_info(0xf);
  }
  else if (param_1 == -0x7ffffffe) {
    puVar1 = (undefined4 *)cpuid_brand_part1_info(0x80000002);
  }
  else if (param_1 == -0x7ffffffd) {
    puVar1 = (undefined4 *)cpuid_brand_part2_info(0x80000003);
  }
  else if (param_1 == -0x7ffffffc) {
    puVar1 = (undefined4 *)cpuid_brand_part3_info(0x80000004);
  }
  else {
    puVar1 = (undefined4 *)cpuid(param_1);
  }
  uVar2 = *puVar1;
  uVar3 = puVar1[1];
  uVar4 = puVar1[2];
  if (param_4 != (undefined4 *)0x0) {
    *param_4 = puVar1[3];
  }
  if (param_2 != (undefined4 *)0x0) {
    *param_2 = uVar2;
  }
  if (param_3 != (undefined4 *)0x0) {
    *param_3 = uVar3;
  }
  if (param_5 != (undefined4 *)0x0) {
    *param_5 = uVar4;
  }
  return param_1;
}


// ==== FUN_000002e0 @ 000002e0

void FUN_000002e0(void)

{
  return;
}


// ==== FUN_000002f0 @ 000002f0

ulonglong FUN_000002f0(void)

{
  ulonglong uVar1;
  undefined8 in_RAX;
  
  uVar1 = rdtsc();
  return CONCAT44((int)((ulonglong)in_RAX >> 0x20),(int)uVar1) | uVar1 & 0xffffffff00000000;
}


// ==== FUN_00000300 @ 00000300

void FUN_00000300(void)

{
  return;
}


// ==== FUN_00000310 @ 00000310

void FUN_00000310(void)

{
  return;
}


// ==== FUN_00000320 @ 00000320

ulonglong FUN_00000320(void)

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


// ==== entry @ 00000370

void entry(undefined8 param_1,longlong param_2)

{
  FUN_0000039c(param_1,param_2);
  FUN_000004b8(param_1,param_2);
  return;
}


// ==== FUN_0000039c @ 0000039c

void FUN_0000039c(undefined8 param_1,longlong param_2)

{
  uint uVar1;
  int iVar2;
  short *psVar3;
  ulonglong uVar4;
  longlong lVar5;
  
  DAT_00001358 = *(longlong *)(param_2 + 0x60);
  DAT_00001350 = param_2;
  FUN_00001040();
  psVar3 = (short *)FUN_00001040();
  do {
    if (*psVar3 == -1) {
      psVar3 = (short *)0x0;
LAB_000003f0:
      if (psVar3 == (short *)0x0) {
        uVar4 = FUN_00000320();
        FUN_00000310();
        uVar1 = in(0x1808);
        FUN_000002f0();
        while (iVar2 = in(0x1808), (((uVar1 & 0xffffff) + 0x16b) - iVar2 >> 0x17 & 1) == 0) {
          FUN_000002e0();
        }
        FUN_000002f0();
        if ((uVar4 >> 9 & 1) == 0) {
          FUN_00000310();
        }
        else {
          FUN_00000300();
        }
LAB_00000459:
        if ((DAT_00001380 != (undefined8 *)0x0) ||
           (lVar5 = (**(code **)(DAT_00001358 + 0x140))(&DAT_000012d0,0,&DAT_00001380), -1 < lVar5))
        {
          (*(code *)*DAT_00001380)(DAT_00001380,&DAT_00001388);
        }
        FUN_00000fe0((longlong *)&DAT_000012e0,(longlong *)&DAT_00001390);
        return;
      }
      if ((DAT_00001300 == *(longlong *)(psVar3 + 4)) && (DAT_00001308 == *(longlong *)(psVar3 + 8))
         ) goto LAB_00000459;
    }
    else if (*psVar3 == 4) goto LAB_000003f0;
    psVar3 = (short *)((longlong)psVar3 + (ulonglong)(ushort)psVar3[1]);
  } while( true );
}


// ==== FUN_000004b8 @ 000004b8

longlong FUN_000004b8(undefined8 param_1,longlong param_2)

{
  longlong lVar1;
  undefined8 local_res8 [2];
  undefined1 local_res18 [16];
  
  if (DAT_00001370 == 0) {
    DAT_00001360 = *(undefined8 *)(param_2 + 0x60);
    DAT_00001368 = *(undefined8 *)(param_2 + 0x58);
    DAT_00001370 = param_2;
  }
  local_res8[0] = param_1;
  lVar1 = (**(code **)(DAT_00001358 + 0x40))(10,0x112,&DAT_00001398);
  if (-1 < lVar1) {
    FUN_00000260(DAT_00001398,0x112);
    (**(code **)(DAT_00001358 + 0x148))(local_res8,&DAT_000012a0,&DAT_00001398,0);
    (**(code **)(DAT_00001358 + 0x170))(0x200,8,0x57c,0,&DAT_00001290,local_res18);
    lVar1 = 0;
  }
  return lVar1;
}


// ==== FUN_0000057c @ 0000057c

void FUN_0000057c(longlong param_1)

{
  undefined1 *puVar1;
  longlong lVar2;
  longlong lVar3;
  undefined8 uVar4;
  char cVar5;
  int **ppiVar6;
  ulonglong uVar7;
  uint uVar8;
  ulonglong uVar9;
  char local_res18 [8];
  undefined1 local_res20 [8];
  byte local_68 [8];
  ulonglong local_60;
  ulonglong local_58;
  longlong local_50;
  uint *local_48;
  longlong local_40;
  int *local_38;
  undefined4 local_30;
  undefined4 local_2c;
  undefined4 local_28;
  undefined4 local_24;
  
  local_res18[0] = '\0';
  local_30 = 0xec87d643;
  local_2c = 0x4bb5eba4;
  local_28 = 0x3e3fe5a1;
  local_24 = 0xa90db236;
  lVar2 = FUN_00000d8c();
  local_58 = 0;
  local_50 = 0;
  local_60 = 0x7d8;
  (**(code **)(DAT_00001358 + 0x138))(2,&DAT_000012b0,0,&local_58,&local_50);
  uVar7 = 0;
  if (local_58 != 0) {
    do {
      lVar3 = (**(code **)(DAT_00001358 + 0x98))(*(undefined8 *)(local_50 + uVar7 * 8));
      if (-1 < lVar3) {
        uVar9 = 0;
        if (*local_48 != 0) {
          do {
            DAT_00001398[uVar9 + 0xf] = *(undefined1 *)(uVar9 + *(longlong *)(local_48 + 2));
            uVar8 = (int)uVar9 + 1;
            uVar9 = (ulonglong)uVar8;
          } while (uVar8 < *local_48);
        }
      }
      uVar7 = uVar7 + 1;
    } while (uVar7 < local_58);
  }
  uVar8 = 0;
  (**(code **)(DAT_00001358 + 0x140))(&DAT_00001280,0,&local_40);
  lVar3 = *(longlong *)(local_40 + 8);
  if ((((*(char *)(lVar3 + 8) == '\t') || (*(char *)(lVar3 + 9) == -0x1b)) ||
      (*(char *)(lVar3 + 10) == -0x21)) || (*(char *)(lVar3 + 0xb) == '\b')) {
    DAT_00001398[0x110] = 1;
  }
  else {
    DAT_00001398[0x110] = 0;
  }
  ppiVar6 = &local_38;
  lVar3 = FUN_00000f10((ulonglong *)ppiVar6,uVar8);
  if (-1 < lVar3) {
    if (*local_38 == 0x54445344) {
      ppiVar6 = (int **)(local_38 + 9);
      FUN_00000ea0((int *)ppiVar6,(char *)((ulonglong)(uint)local_38[1] - 0x25),&DAT_00001310,
                   (ulonglong)DAT_00001398);
      if (*local_38 == 0x54445344) {
        ppiVar6 = (int **)(local_38 + 9);
        FUN_00000ea0((int *)ppiVar6,(char *)((ulonglong)(uint)local_38[1] - 0x25),&DAT_00001318,
                     0x112);
      }
    }
    cVar5 = (char)*local_38;
    uVar7 = 1;
    *(undefined1 *)((longlong)local_38 + 9) = 0;
    if (1 < (uint)local_38[1]) {
      do {
        cVar5 = cVar5 + *(char *)(uVar7 + (longlong)local_38);
        uVar7 = uVar7 + 1;
      } while (uVar7 < (uint)local_38[1]);
    }
    *(char *)((longlong)local_38 + 9) = -cVar5;
    FUN_00000cc4(CONCAT71((int7)((ulonglong)ppiVar6 >> 8),-cVar5),7,0x60,local_res20);
    DAT_00001398[1] = 0;
    DAT_00001398[2] = 1;
    local_60 = local_60 & -(ulonglong)(lVar2 != 0);
    lVar3 = (**(code **)(DAT_00001368 + 0x48))(u_Setup_00001320,&local_30,0,&local_60,lVar2);
    if ((lVar3 < 0) && (lVar3 == -0x7ffffffffffffffb)) {
      if (lVar2 != 0) {
        (**(code **)(DAT_00001360 + 0x48))(lVar2);
      }
      lVar2 = FUN_00000d60(local_60);
      if (lVar2 != 0) {
        (**(code **)(DAT_00001368 + 0x48))(u_Setup_00001320,&local_30,0,&local_60,lVar2);
      }
    }
    puVar1 = DAT_00001398;
    *DAT_00001398 = local_res20[0];
    FUN_00000cc4(puVar1,4,0x62,local_res18);
    DAT_00001398[5] = local_res18[0] == 'K';
    DAT_00001398[0xd] = *(undefined1 *)(lVar2 + 0x745);
    DAT_00001398[3] = *(undefined1 *)(lVar2 + 0x744);
    DAT_00001398[0x10f] = *(undefined1 *)(lVar2 + 0x4a0);
    DAT_00001398[4] = 1;
    uVar4 = FUN_00000900();
    DAT_00001398[6] = (char)uVar4 == '\0';
    if (DAT_e0008019 != 0xff) {
      lVar2 = 0x10de;
      if ((*(short *)(ulonglong)((uint)DAT_e0008019 * 0x100000 + 0xe0000000) == 0x10de) &&
         (lVar2 = 0x1e93,
         *(short *)(ulonglong)((uint)DAT_e0008019 * 0x100000 + 0xe0000002) == 0x1e93)) {
        DAT_00001398[0xe] = 1;
      }
      else {
        DAT_00001398[0xe] = 0;
      }
      if (param_1 != 0) {
        (**(code **)(DAT_00001358 + 0x70))();
        lVar2 = param_1;
      }
      FUN_00000cc4(lVar2,7,0x4c,local_68);
      DAT_00001398[0x111] = local_68[0] & 0xf;
    }
  }
  return;
}


// ==== FUN_00000900 @ 00000900

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

undefined8 FUN_00000900(void)

{
  ulonglong uVar1;
  undefined1 uVar2;
  uint local_18;
  undefined4 local_14;
  undefined4 local_10;
  undefined4 local_c;
  
  uVar2 = 4;
  FUN_000002b0(1,&local_18,&local_14,&local_10,&local_c);
  local_18 = local_18 & 0xfff0ff0;
  if (local_18 == 0x806e0) {
    uVar1 = (ulonglong)_DAT_e0000002;
    if ((_DAT_e0000002 < 0x3e34) ||
       (((((0x3e36 < _DAT_e0000002 && (_DAT_e0000002 != 0x3ecc)) && (_DAT_e0000002 != 0x3ed0)) &&
         (_DAT_e0000002 != 0x5904)) &&
        ((uVar1 = (ulonglong)(_DAT_e0000002 - 0x9b51), 0x20 < _DAT_e0000002 - 0x9b51 ||
         ((0x100010001U >> (uVar1 & 0x3f) & 1) == 0)))))) goto LAB_00000a8f;
LAB_00000a8d:
    uVar2 = 0;
  }
  else {
    if (local_18 == 0x906e0) {
      uVar1 = 0x3ec2;
      if (0x3ec2 < _DAT_e0000002) {
        if (_DAT_e0000002 != 0x3ec4) {
          if ((_DAT_e0000002 == 0x3ec6) || (_DAT_e0000002 == 0x3eca)) goto LAB_000009cf;
          if (_DAT_e0000002 != 0x5910) {
            if ((_DAT_e0000002 == 0x5918) || (_DAT_e0000002 == 0x591f)) goto LAB_000009cf;
            if (_DAT_e0000002 != 0x9b44) goto LAB_00000a8f;
          }
        }
LAB_00000a49:
        uVar2 = 3;
        goto LAB_00000a8f;
      }
      if ((_DAT_e0000002 != 0x3ec2) && (_DAT_e0000002 != 0x3e0f)) {
        uVar1 = (ulonglong)(_DAT_e0000002 - 0x3e10);
        if ((_DAT_e0000002 - 0x3e10 & 0xfffffffd) == 0) goto LAB_00000a49;
        if ((_DAT_e0000002 != 0x3e18) && (_DAT_e0000002 != 0x3e1f)) {
          if (_DAT_e0000002 == 0x3e20) goto LAB_00000a49;
          uVar1 = (ulonglong)(_DAT_e0000002 - 0x3e30);
          if (3 < _DAT_e0000002 - 0x3e30) goto LAB_00000a8f;
        }
      }
    }
    else {
      local_18 = local_18 - 0xa0650;
      uVar1 = (ulonglong)local_18;
      if (local_18 != 0) {
        if (local_18 != 0x10) goto LAB_00000a8f;
        if (_DAT_e0000002 != 0x9b51) {
          if (_DAT_e0000002 == 0x9b60) {
            uVar2 = 2;
            goto LAB_00000a8f;
          }
          if ((_DAT_e0000002 != 0x9b61) && (_DAT_e0000002 != 0x9b71)) goto LAB_00000a8f;
        }
        goto LAB_00000a8d;
      }
      if ((_DAT_e0000002 != 0x9b33) && (_DAT_e0000002 != 0x9b43)) {
        if (_DAT_e0000002 == 0x9b44) goto LAB_00000a49;
        if (_DAT_e0000002 != 0x9b53) {
          if (_DAT_e0000002 == 0x9b54) goto LAB_00000a49;
          if (_DAT_e0000002 != 0x9b63) {
            if (_DAT_e0000002 == 0x9b64) goto LAB_00000a49;
            if (_DAT_e0000002 != 0x9b73) goto LAB_00000a8f;
          }
        }
      }
    }
LAB_000009cf:
    uVar2 = 1;
  }
LAB_00000a8f:
  return CONCAT71((int7)(uVar1 >> 8),uVar2);
}


// ==== FUN_00000a98 @ 00000a98

undefined8 FUN_00000a98(char param_1,undefined1 param_2)

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
      FUN_000010d0(0xf);
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


// ==== FUN_00000b10 @ 00000b10

undefined8 FUN_00000b10(char param_1)

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
      FUN_000010d0(5000);
      bVar2 = in(uVar1);
      uVar5 = uVar5 + 1;
    } while ((bVar2 & 1) != 0);
    if (0x1ffff < uVar5) {
      return 0x8000000000000007;
    }
  }
  return 0;
}


// ==== FUN_00000b98 @ 00000b98

undefined8 FUN_00000b98(char param_1)

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
      FUN_000010d0(0xf);
      bVar2 = in(uVar1);
      uVar3 = uVar3 + 1;
    } while ((bVar2 & 2) != 0);
    if (0x1ffff < uVar3) {
      return 0x8000000000000007;
    }
  }
  return 0;
}


// ==== FUN_00000bfc @ 00000bfc

longlong FUN_00000bfc(char param_1,undefined1 param_2,undefined1 param_3)

{
  byte bVar1;
  byte bVar2;
  longlong lVar3;
  ulonglong uVar4;
  undefined2 uVar5;
  
  lVar3 = FUN_00000b98(param_1);
  uVar4 = 0;
  if (lVar3 < 0) {
    return lVar3;
  }
  FUN_00000b10(param_1);
  FUN_00000a98(param_1,param_2);
  FUN_00000b98(param_1);
  uVar5 = 0x60;
  bVar1 = 100;
  if (param_1 != '`') {
    bVar1 = 0x66;
  }
  bVar2 = in((ushort)bVar1);
  if ((bVar2 & 2) != 0) {
    do {
      if (0x1ffff < uVar4) goto LAB_00000c9e;
      FUN_000010d0(0xf);
      bVar2 = in((ushort)bVar1);
      uVar4 = uVar4 + 1;
    } while ((bVar2 & 2) != 0);
    if (0x1ffff < uVar4) goto LAB_00000c9e;
  }
  if (param_1 != '`') {
    uVar5 = 0x62;
  }
  out(uVar5,param_3);
LAB_00000c9e:
  FUN_00000b10(param_1);
  return lVar3;
}


// ==== FUN_00000cc4 @ 00000cc4

longlong FUN_00000cc4(undefined8 param_1,undefined1 param_2,undefined1 param_3,undefined1 *param_4)

{
  byte bVar1;
  undefined1 uVar2;
  longlong lVar3;
  ulonglong uVar4;
  
  uVar4 = 0;
  lVar3 = FUN_00000bfc('b',0xa3,param_2);
  if (((-1 < lVar3) && (lVar3 = FUN_00000bfc('b',0xa2,param_3), -1 < lVar3)) &&
     (lVar3 = FUN_00000a98('b',0xa4), -1 < lVar3)) {
    bVar1 = in(0x66);
    if ((bVar1 & 1) == 0) {
      do {
        if (0x1ffff < uVar4) {
          return -0x7ffffffffffffff9;
        }
        FUN_000010d0(0xf);
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


// ==== FUN_00000d60 @ 00000d60

undefined8 FUN_00000d60(undefined8 param_1)

{
  undefined8 local_res10 [3];
  
  local_res10[0] = 0;
  (**(code **)(DAT_00001360 + 0x40))(4,param_1,local_res10);
  return local_res10[0];
}


// ==== FUN_00000d8c @ 00000d8c

longlong FUN_00000d8c(void)

{
  longlong lVar1;
  
  lVar1 = FUN_00000d60(0x7d8);
  if (lVar1 != 0) {
    (**(code **)(DAT_00001360 + 0x168))(lVar1,0x7d8,0);
  }
  return lVar1;
}


// ==== FUN_00000dc8 @ 00000dc8

undefined8
FUN_00000dc8(int *param_1,char *param_2,char *param_3,undefined8 param_4,longlong *param_5)

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
    FUN_000011c0((undefined8 *)local_res20,(undefined8 *)param_3,uVar6);
    uVar5 = 0;
    if (param_2 != (char *)0x0) {
      pcVar3 = (char *)0x0;
      do {
        piVar4 = (int *)(pcVar3 + (longlong)param_1);
        if (*piVar4 == local_res20[0]) goto LAB_00000e2f;
        uVar5 = uVar5 + 1;
        pcVar3 = (char *)(ulonglong)uVar5;
      } while (pcVar3 < param_2);
    }
    piVar4 = (int *)0x0;
LAB_00000e2f:
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


// ==== FUN_00000ea0 @ 00000ea0

longlong FUN_00000ea0(int *param_1,char *param_2,char *param_3,ulonglong param_4)

{
  longlong lVar1;
  longlong local_38 [2];
  byte *local_28;
  
  lVar1 = FUN_00000dc8(param_1,param_2,param_3,param_4,local_38);
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


// ==== FUN_00000f10 @ 00000f10

longlong FUN_00000f10(ulonglong *param_1,uint param_2)

{
  longlong lVar1;
  ulonglong uVar2;
  ulonglong uVar3;
  longlong lVar4;
  uint local_res10 [2];
  int *local_res18;
  longlong local_res20;
  undefined1 local_38 [16];
  
  uVar2 = 0;
  local_res18 = (int *)0x0;
  uVar3 = 0;
  local_res10[0] = param_2;
  lVar1 = (**(code **)(DAT_00001360 + 0x140))(&DAT_000012f0,0,&local_res20);
  if (lVar1 < 0) {
    lVar1 = -0x5ffffffffffffffe;
  }
  else {
    lVar4 = 0;
    lVar1 = (**(code **)(local_res20 + 8))(0,&local_res18,local_res10,local_38);
    if (-1 < lVar1) {
      do {
        if (*local_res18 == 0x50434146) {
          if (local_res10[0] == 2) {
            uVar3 = (ulonglong)(uint)local_res18[10];
          }
          if ((local_res10[0] & 0x1c) != 0) {
            uVar2 = *(ulonglong *)(local_res18 + 0x23);
          }
        }
        if ((uVar3 != 0) && (uVar2 != 0)) goto LAB_00000fc3;
        lVar4 = lVar4 + 1;
        lVar1 = (**(code **)(local_res20 + 8))(lVar4,&local_res18,local_res10,local_38);
      } while (-1 < lVar1);
      if (uVar2 == 0) {
        if (uVar3 == 0) {
          return lVar1;
        }
        *param_1 = uVar3;
      }
      else {
LAB_00000fc3:
        *param_1 = uVar2;
      }
      lVar1 = 0;
    }
  }
  return lVar1;
}


// ==== FUN_00000fe0 @ 00000fe0

undefined8 FUN_00000fe0(longlong *param_1,longlong *param_2)

{
  ulonglong uVar1;
  longlong *plVar2;
  longlong lVar3;
  ulonglong uVar4;
  longlong *plVar5;
  
  lVar3 = DAT_00001350;
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


// ==== FUN_00001040 @ 00001040

longlong FUN_00001040(void)

{
  if (DAT_00001378 == 0) {
    FUN_00000fe0((longlong *)&DAT_000012c0,&DAT_00001378);
  }
  return DAT_00001378;
}


// ==== FUN_00001070 @ 00001070

void FUN_00001070(uint param_1)

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
      FUN_000002e0();
    }
    bVar6 = uVar3 != 0;
    uVar3 = uVar3 - 1;
  } while (bVar6);
  return;
}


// ==== FUN_000010d0 @ 000010d0

longlong FUN_000010d0(longlong param_1)

{
  FUN_00001070((uint)((ulonglong)(param_1 * 0x369e99) / 1000000));
  return param_1;
}


// ==== FUN_000011c0 @ 000011c0

undefined8 * FUN_000011c0(undefined8 *param_1,undefined8 *param_2,ulonglong param_3)

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


