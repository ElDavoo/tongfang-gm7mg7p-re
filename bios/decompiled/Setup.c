// Setup.efi: Ghidra x86:LE:64:default decompile, unedited
// ==== FUN_000002c0 @ 000002c0

longlong FUN_000002c0(char *param_1,char *param_2,longlong param_3)

{
  char cVar1;
  char cVar2;
  char *pcVar3;
  char *pcVar4;
  
  do {
    pcVar3 = param_1;
    pcVar4 = param_2;
    if (param_3 == 0) break;
    param_3 = param_3 + -1;
    pcVar4 = param_2 + 1;
    pcVar3 = param_1 + 1;
    cVar2 = *param_2;
    cVar1 = *param_1;
    param_1 = pcVar3;
    param_2 = pcVar4;
  } while (cVar1 == cVar2);
  return (ulonglong)(byte)pcVar3[-1] - (ulonglong)(byte)pcVar4[-1];
}


// ==== FUN_000002e0 @ 000002e0

undefined8 * FUN_000002e0(undefined8 *param_1,undefined8 *param_2,ulonglong param_3)

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


// ==== FUN_00000320 @ 00000320

undefined1 * FUN_00000320(undefined1 *param_1,longlong param_2,undefined1 param_3)

{
  undefined1 *puVar1;
  
  puVar1 = param_1;
  for (; param_2 != 0; param_2 = param_2 + -1) {
    *puVar1 = param_3;
    puVar1 = puVar1 + 1;
  }
  return param_1;
}


// ==== FUN_00000340 @ 00000340

undefined8 * FUN_00000340(undefined8 *param_1,ulonglong param_2)

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


// ==== FUN_000003a0 @ 000003a0

int FUN_000003a0(int param_1,undefined8 param_2,undefined4 *param_3,undefined4 *param_4,
                undefined4 *param_5,undefined4 *param_6)

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
  if (param_5 != (undefined4 *)0x0) {
    *param_5 = puVar1[3];
  }
  if (param_3 != (undefined4 *)0x0) {
    *param_3 = uVar2;
  }
  if (param_4 != (undefined4 *)0x0) {
    *param_4 = uVar3;
  }
  if (param_6 != (undefined4 *)0x0) {
    *param_6 = uVar4;
  }
  return param_1;
}


// ==== FUN_000003d0 @ 000003d0

int FUN_000003d0(int param_1,undefined4 *param_2,undefined4 *param_3,undefined4 *param_4,
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


// ==== FUN_00000400 @ 00000400

undefined2 * FUN_00000400(undefined2 *param_1,longlong param_2,undefined2 param_3)

{
  undefined2 *puVar1;
  
  puVar1 = param_1;
  for (; param_2 != 0; param_2 = param_2 + -1) {
    *puVar1 = param_3;
    puVar1 = puVar1 + 1;
  }
  return param_1;
}


// ==== FUN_00000420 @ 00000420

void FUN_00000420(void)

{
  return;
}


// ==== FUN_00000430 @ 00000430

ulonglong FUN_00000430(void)

{
  ulonglong uVar1;
  undefined8 in_RAX;
  
  uVar1 = rdtsc();
  return CONCAT44((int)((ulonglong)in_RAX >> 0x20),(int)uVar1) | uVar1 & 0xffffffff00000000;
}


// ==== FUN_00000440 @ 00000440

void FUN_00000440(void)

{
  return;
}


// ==== FUN_00000450 @ 00000450

void FUN_00000450(void)

{
  return;
}


// ==== FUN_00000483 @ 00000483

undefined8 FUN_00000483(undefined8 *param_1)

{
  undefined8 uVar1;
  bool bVar2;
  
  uVar1 = rdrand();
  bVar2 = (bool)rdrandIsValid();
  if (!bVar2) {
    return 0;
  }
  *param_1 = uVar1;
  return 1;
}


// ==== FUN_000004a0 @ 000004a0

ulonglong FUN_000004a0(void)

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


// ==== entry @ 000004b0

void entry(undefined8 param_1,longlong param_2)

{
  FUN_000004dc(param_1,param_2);
  FUN_00000c6c(param_1,param_2);
  return;
}


// ==== FUN_000004dc @ 000004dc

void FUN_000004dc(undefined8 param_1,longlong param_2)

{
  uint uVar1;
  int iVar2;
  longlong lVar3;
  ulonglong uVar4;
  undefined4 local_res8 [2];
  
  DAT_00029478 = *(longlong *)(param_2 + 0x60);
  DAT_00029488 = *(undefined8 *)(param_2 + 0x58);
  DAT_00029470 = param_2;
  DAT_00029480 = param_1;
  FUN_0001f8dc();
  lVar3 = FUN_0001f90c((longlong *)&DAT_00025398);
  if (lVar3 == 0) {
    uVar4 = FUN_000004a0();
    FUN_00000450();
    uVar1 = in(0x1808);
    FUN_00000430();
    while (iVar2 = in(0x1808), (((uVar1 & 0xffffff) + 0x16b) - iVar2 >> 0x17 & 1) == 0) {
      FUN_00000420();
    }
    FUN_00000430();
    if ((uVar4 >> 9 & 1) == 0) {
      FUN_00000450();
    }
    else {
      FUN_00000440();
    }
  }
  if ((DAT_000294d8 != (undefined8 *)0x0) ||
     (lVar3 = (**(code **)(DAT_00029478 + 0x140))(&DAT_00023910,0,&DAT_000294d8), -1 < lVar3)) {
    (*(code *)*DAT_000294d8)(DAT_000294d8,&DAT_000294e0);
  }
  (**(code **)(DAT_00029478 + 0x140))(&DAT_000237c0,0,&DAT_000294e8);
  (**(code **)(DAT_00029478 + 0x140))(&DAT_000237a0,0,&DAT_00029508);
  (**(code **)(DAT_00029478 + 0x140))(&DAT_00023700,0,&DAT_000294f8);
  (**(code **)(DAT_00029478 + 0x140))(&DAT_00023990,0,&DAT_000294f0);
  (**(code **)(DAT_00029478 + 0x140))(&DAT_00023740,0);
  FUN_0001f18c((longlong *)&DAT_00023940,&DAT_00029518);
  FUN_000003d0(1,(undefined4 *)0x0,(undefined4 *)0x0,local_res8,(undefined4 *)0x0);
  return;
}


// ==== FUN_00000680 @ 00000680

void FUN_00000680(undefined8 param_1,short param_2,byte *param_3,ulonglong param_4)

{
  ulonglong local_res20;
  char local_818 [2056];
  
  local_res20 = param_4;
  FUN_0001c184(local_818,0x400,0x140,param_3,&local_res20);
  FUN_00021068(param_1,param_2);
  return;
}


// ==== FUN_000006d8 @ 000006d8

undefined8 FUN_000006d8(undefined8 param_1)

{
  ushort uVar1;
  wchar_t *pwVar2;
  
  pwVar2 = u_American_Megatrends_00025b40;
  if (*(longlong *)(DAT_00029470 + 0x18) != 0) {
    pwVar2 = *(wchar_t **)(DAT_00029470 + 0x18);
  }
  uVar1 = 5;
  if (*(int *)(DAT_00029470 + 0x20) != 0) {
    uVar1 = (ushort)((uint)*(undefined4 *)(DAT_00029470 + 0x20) >> 0x10);
  }
  FUN_00000680(param_1,0xe,&DAT_00025b68,(ulonglong)pwVar2);
  FUN_00000680(param_1,0x10,(byte *)u__d__02d_00025b70,(ulonglong)uVar1);
  FUN_00000680(param_1,0x14,(byte *)u__s__d__02d_x64_00025b90,0x25b80);
  FUN_00000680(param_1,0x16,(byte *)u__s__s_00025be0,0x25bc8);
  FUN_00000680(param_1,0x12,(byte *)u_UEFI__d__d__PI__d__d_00025bf0,
               (ulonglong)*(ushort *)(DAT_00029470 + 10));
  FUN_00000680(param_1,0x43,&DAT_00025c1c,3);
  FUN_00000680(param_1,0x45,&DAT_00025c1c,0x14);
  return 0;
}


// ==== FUN_0000083c @ 0000083c

void FUN_0000083c(void)

{
  longlong lVar1;
  undefined8 *local_res8 [4];
  
  local_res8[0] = (undefined8 *)0x0;
  lVar1 = (**(code **)(DAT_00029478 + 0x40))(4,0x18,local_res8);
  if (-1 < lVar1) {
    local_res8[0][2] = 0x6d8;
    *local_res8[0] = &DAT_0002b380;
    local_res8[0][1] = DAT_0002b388;
    *DAT_0002b388 = local_res8[0];
    DAT_0002b388 = local_res8[0];
  }
  return;
}


// ==== FUN_000008a4 @ 000008a4

void FUN_000008a4(char *param_1,ulonglong param_2)

{
  char *pcVar1;
  undefined **ppuVar2;
  char cVar3;
  ulonglong uVar4;
  undefined8 uVar5;
  longlong lVar6;
  char *pcVar7;
  code *pcVar8;
  longlong lVar9;
  uint *puVar10;
  undefined8 *puVar11;
  ulonglong uVar12;
  ulonglong uVar13;
  ulonglong uVar14;
  char *local_res8;
  ulonglong local_res10;
  longlong local_res18;
  char *local_res20;
  undefined8 *local_58;
  longlong local_50;
  char local_48 [32];
  
  uVar14 = 0;
  builtin_strncpy(local_48,"\x04\x03\x14",4);
  local_48[4] = '\0';
  local_48[5] = '\0';
  local_48[6] = '\0';
  local_48[7] = '\0';
  local_50 = 0;
  local_58 = (undefined8 *)0x0;
  local_res18 = 0;
  local_res20 = (char *)0x0;
  local_48[8] = '\0';
  local_48[9] = '\0';
  local_48[10] = '\0';
  local_48[0xb] = '\0';
  local_48[0xc] = '\0';
  local_48[0xd] = '\0';
  local_48[0xe] = '\0';
  local_48[0xf] = '\0';
  local_48[0x10] = '\0';
  local_48[0x11] = '\0';
  local_48[0x12] = '\0';
  local_48[0x13] = '\0';
  if ((((DAT_00029260 == '\0') &&
       (local_res8 = param_1, local_res10 = param_2,
       lVar6 = (**(code **)(DAT_00029478 + 0x140))(&DAT_000237c0,0,&local_50), -1 < lVar6)) &&
      (lVar6 = (**(code **)(DAT_00029478 + 0x140))(&DAT_000237a0,0,&local_58), -1 < lVar6)) &&
     ((lVar6 = (**(code **)(DAT_00029478 + 0x98))(DAT_00029268,&DAT_00023550,&local_res18),
      -1 < lVar6 &&
      (lVar6 = (**(code **)(DAT_00029478 + 0x98))(DAT_00029268,&DAT_00023500,&local_res20),
      -1 < lVar6)))) {
    for (puVar10 = (uint *)(local_res18 + 0x14);
        puVar10 < (uint *)((ulonglong)*(uint *)(local_res18 + 0x10) + local_res18);
        puVar10 = (uint *)((longlong)puVar10 + (ulonglong)(*puVar10 & 0xffffff))) {
      if (*(char *)((longlong)puVar10 + 3) == '\x02') {
        (**(code **)(DAT_00029478 + 0x160))(local_48 + 4,(longlong)puVar10 + 6,0x10);
        (**(code **)(DAT_00029478 + 0x160))(&DAT_00024188,(longlong)puVar10 + 6,0x10);
        break;
      }
    }
    pcVar7 = FUN_0001d5b8(local_res20,local_48);
    lVar6 = (**(code **)(DAT_00029478 + 0x148))
                      (&DAT_00024178,&DAT_00023690,pcVar7,&DAT_00023800,&PTR_DAT_00024160,0);
    if ((-1 < lVar6) &&
       (lVar6 = (*(code *)*local_58)(local_58,local_res18,DAT_00024178,&DAT_00024180), -1 < lVar6))
    {
      DAT_00029260 = '\x01';
      pcVar8 = FUN_0000083c;
      uVar13 = uVar14;
      while (pcVar8 != (code *)0x0) {
        (*pcVar8)();
        puVar11 = &DAT_00025cb8 + uVar13;
        uVar13 = uVar13 + 1;
        pcVar8 = (code *)*puVar11;
      }
      pcVar8 = FUN_0001a8a0;
      uVar13 = uVar14;
      while (puVar11 = DAT_0002b380, pcVar8 != (code *)0x0) {
        (*pcVar8)(DAT_00024180,1);
        ppuVar2 = &PTR_LAB_00025cc8 + uVar13;
        uVar13 = uVar13 + 1;
        pcVar8 = (code *)*ppuVar2;
      }
      for (; lVar6 = local_50, uVar5 = DAT_00024180, (undefined8 **)puVar11 != &DAT_0002b380;
          puVar11 = (undefined8 *)*puVar11) {
        (*(code *)puVar11[2])(DAT_00024180);
      }
      local_res10 = 0;
      local_res8 = (char *)0x0;
      lVar9 = (**(code **)(local_50 + 0x18))(local_50,DAT_00024180,0,&local_res10);
      if (lVar9 == -0x7ffffffffffffffb) {
        (**(code **)(DAT_00029478 + 0x40))(4,local_res10,&local_res8);
        lVar9 = (**(code **)(lVar6 + 0x18))(lVar6,uVar5,local_res8,&local_res10);
      }
      if (lVar9 < 0) {
        local_res10 = 6;
        (**(code **)(DAT_00029478 + 0x40))(4,6,&local_res8);
        (**(code **)(DAT_00029478 + 0x160))(local_res8,s_en_US_00025c24,local_res10);
      }
      pcVar7 = local_res8;
      uVar12 = uVar14;
      uVar13 = local_res10;
      if (local_res10 != 0) {
        do {
          pcVar1 = pcVar7 + uVar12;
          uVar4 = uVar12;
          if (*pcVar1 == '\0') break;
          for (; ((uVar4 < uVar13 && (pcVar7[uVar4] != ';')) && (pcVar7[uVar4] != '\0'));
              uVar4 = uVar4 + 1) {
          }
          if ((*pcVar1 == 'x') && (pcVar1[1] == '-')) {
            if (pcVar7[uVar4] != ';') {
              if (((pcVar7[uVar4] == '\0') && (uVar12 != 0)) && (pcVar1[-1] == ';')) {
                pcVar1[-1] = '\0';
                uVar13 = uVar12 - 1;
                pcVar7 = local_res8;
                local_res10 = uVar13;
              }
              goto LAB_00000c04;
            }
            (**(code **)(DAT_00029478 + 0x160))(pcVar1,pcVar7 + uVar4 + 1,(uVar13 - uVar4) + -1);
            uVar13 = (uVar12 - uVar4) + local_res10 + 1;
            pcVar7 = local_res8;
            local_res10 = uVar13;
          }
          else {
LAB_00000c04:
            uVar12 = uVar4 + 1;
          }
        } while (uVar12 < uVar13);
      }
      cVar3 = *pcVar7;
      while (cVar3 != '\0') {
        uVar14 = uVar14 + 1;
        cVar3 = pcVar7[uVar14];
      }
      local_res10 = uVar14 + 1;
      (**(code **)(DAT_00029488 + 0x58))
                (u_PlatformLastLangCodes_00025c30,&DAT_00024198,3,local_res10,pcVar7);
      if (local_res8 != (char *)0x0) {
        (**(code **)(DAT_00029478 + 0x48))();
      }
    }
  }
  return;
}


// ==== FUN_00000c6c @ 00000c6c

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

undefined8 FUN_00000c6c(undefined8 param_1,longlong param_2)

{
  char cVar1;
  longlong lVar2;
  wchar_t *pwVar3;
  undefined *puVar4;
  char *pcVar5;
  char *local_res8;
  longlong local_res18 [2];
  
  if (DAT_000294a8 == 0) {
    DAT_00029498 = *(undefined8 *)(param_2 + 0x60);
    DAT_000294a0 = *(undefined8 *)(param_2 + 0x58);
    DAT_000294a8 = param_2;
  }
  local_res8 = (char *)0x0;
  DAT_0002b3a0 = &DAT_0002b3a0;
  puVar4 = &DAT_00024198;
  DAT_0002b3a8 = &DAT_0002b3a0;
  pwVar3 = u_PlatformLastLangCodes_00025c30;
  DAT_0002b380 = &DAT_0002b380;
  DAT_0002b388 = &DAT_0002b380;
  _DAT_0002b390 = &DAT_0002b390;
  _DAT_0002b398 = &DAT_0002b390;
  _DAT_0002b370 = &DAT_0002b370;
  _DAT_0002b378 = &DAT_0002b370;
  DAT_00029268 = param_1;
  (**(code **)(DAT_00029488 + 0x48))(u_PlatformLastLangCodes_00025c30,&DAT_00024198,0,&local_res8,0)
  ;
  FUN_000008a4((char *)pwVar3,(ulonglong)puVar4);
  local_res18[0] = 0;
  local_res8 = (char *)0x0;
  lVar2 = FUN_0001f24c(u_PlatformLastLangCodes_00025c30,&DAT_00024198,(longlong *)&local_res8,
                       local_res18);
  pcVar5 = local_res8;
  if (lVar2 < 0) {
    pcVar5 = (char *)0x0;
  }
  else if ((local_res8 != (char *)0x0) && (local_res18[0] != 0)) {
    (**(code **)(DAT_00029488 + 0x58))
              (u_PlatformLangCodes_00025c60,&DAT_000234a0,6,local_res18[0],local_res8);
  }
  local_res18[0] = 0;
  lVar2 = (**(code **)(DAT_00029488 + 0x48))(u_PlatformLang_00025c88,&DAT_000234a0,0,local_res18,0);
  if (lVar2 != -0x7ffffffffffffffb) {
    lVar2 = 0;
    if ((pcVar5 == (char *)0x0) || (cVar1 = *pcVar5, cVar1 == '\0')) {
      lVar2 = 6;
      (**(code **)(DAT_00029478 + 0x40))(4,6,&local_res8);
      (**(code **)(DAT_00029478 + 0x160))(local_res8,s_en_US_00025c24,6);
    }
    else {
      while ((cVar1 != ';' && (cVar1 != '\0'))) {
        lVar2 = lVar2 + 1;
        cVar1 = pcVar5[lVar2];
      }
      (**(code **)(DAT_00029478 + 0x40))(4,lVar2 + 1,&local_res8);
      (**(code **)(DAT_00029478 + 0x160))(local_res8,pcVar5,lVar2);
      local_res8[lVar2] = '\0';
    }
    (**(code **)(DAT_00029488 + 0x58))(u_PlatformLang_00025c88,&DAT_000234a0,7,lVar2,local_res8);
    (**(code **)(DAT_00029478 + 0x48))(local_res8);
  }
  (**(code **)(DAT_00029478 + 0x48))(pcVar5);
  return 0;
}


// ==== FUN_00000ec0 @ 00000ec0

longlong FUN_00000ec0(undefined8 param_1,undefined8 param_2,short param_3,undefined1 param_4,
                     undefined8 param_5,undefined8 *param_6)

{
  longlong lVar1;
  longlong lVar2;
  undefined8 *puVar3;
  longlong lVar4;
  undefined8 local_38;
  undefined8 local_30;
  short local_28;
  undefined1 local_26;
  undefined8 local_20;
  undefined8 *local_18;
  undefined8 local_10;
  
  local_20 = param_5;
  local_10 = DAT_00024180;
  local_18 = param_6;
  if (param_6 != (undefined8 *)0x0) {
    *param_6 = 0;
  }
  lVar4 = 0;
  DAT_00029270 = &local_38;
  lVar1 = -0x7ffffffffffffffd;
  puVar3 = DAT_0002b3a0;
  local_38 = param_1;
  local_30 = param_2;
  local_28 = param_3;
  local_26 = param_4;
  if (PTR_FUN_000239a8 != (undefined *)0x0) {
    lVar2 = 0;
    do {
      if (((*(short *)((longlong)&DAT_000239a4 + lVar2) == param_3) &&
          (lVar1 = (**(code **)((longlong)&PTR_FUN_000239a8 + lVar2))(DAT_00024180,1,0,param_3),
          puVar3 = DAT_0002b3a0, lVar1 != -0x7ffffffffffffffd)) ||
         ((*(short *)((longlong)&DAT_000239a4 + lVar2) == 0x1001 &&
          (lVar1 = (**(code **)((longlong)&PTR_FUN_000239a8 + lVar2))(DAT_00024180,1,0,param_3),
          puVar3 = DAT_0002b3a0, lVar1 != -0x7ffffffffffffffd)))) break;
      lVar4 = lVar4 + 1;
      lVar2 = lVar4 * 0x10;
      puVar3 = DAT_0002b3a0;
    } while ((&PTR_FUN_000239a8)[lVar4 * 2] != (undefined *)0x0);
  }
  while (((undefined8 **)puVar3 != &DAT_0002b3a0 &&
         ((*(short *)(puVar3 + 2) != param_3 ||
          (lVar1 = (*(code *)puVar3[3])(&local_38), lVar1 == -0x7ffffffffffffffd))))) {
    puVar3 = (undefined8 *)*puVar3;
  }
  DAT_00029270 = (undefined8 *)0x0;
  return lVar1;
}


// ==== FUN_00000ff4 @ 00000ff4

void FUN_00000ff4(longlong param_1,ulonglong param_2,byte *param_3)

{
  char cVar1;
  byte bVar2;
  char cVar3;
  ulonglong uVar4;
  
  uVar4 = 0;
  if (param_2 != 0) {
    do {
      if (uVar4 == param_2 - 1) {
        cVar1 = *(char *)(param_1 + uVar4 * 2);
        cVar3 = '\0';
      }
      else {
        cVar3 = *(char *)(param_1 + uVar4 * 2);
        if ((byte)(cVar3 - 0x30U) < 10) {
          cVar3 = cVar3 + -0x30;
        }
        else if ((byte)(cVar3 + 0xbfU) < 6) {
          cVar3 = cVar3 + -0x37;
        }
        else {
          cVar3 = cVar3 + -0x57;
        }
        cVar1 = *(char *)(param_1 + 2 + uVar4 * 2);
      }
      if ((byte)(cVar1 - 0x30U) < 10) {
        bVar2 = cVar1 - 0x30;
      }
      else if ((byte)(cVar1 + 0xbfU) < 6) {
        bVar2 = cVar1 - 0x37;
      }
      else {
        bVar2 = cVar1 + 0xa9;
      }
      uVar4 = uVar4 + 2;
      *param_3 = cVar3 << 4 | bVar2;
      param_3 = param_3 + 1;
    } while (uVar4 < param_2);
  }
  return;
}


// ==== FUN_00001074 @ 00001074

void FUN_00001074(longlong param_1,ulonglong *param_2,longlong param_3)

{
  char cVar1;
  short sVar2;
  byte bVar3;
  ushort uVar4;
  ulonglong uVar5;
  short *psVar6;
  
  psVar6 = (short *)(param_1 + 4);
  for (uVar5 = 0;
      (((sVar2 = psVar6[-2],
        0x19 < (ushort)(sVar2 - 0x47U) &&
        (6 < (ushort)(sVar2 - 0x3aU) && (ushort)(sVar2 - 0x30U) < 0x37) &&
        (sVar2 = psVar6[-1],
        0x19 < (ushort)(sVar2 - 0x47U) &&
        (6 < (ushort)(sVar2 - 0x3aU) && (ushort)(sVar2 - 0x30U) < 0x37))) &&
       (sVar2 = *psVar6,
       0x19 < (ushort)(sVar2 - 0x47U) &&
       (6 < (ushort)(sVar2 - 0x3aU) && (ushort)(sVar2 - 0x30U) < 0x37))) &&
      ((sVar2 = psVar6[1],
       0x19 < (ushort)(sVar2 - 0x47U) &&
       (6 < (ushort)(sVar2 - 0x3aU) && (ushort)(sVar2 - 0x30U) < 0x37) && (uVar5 < *param_2 - 1))));
      uVar5 = uVar5 + 1) {
    cVar1 = (char)psVar6[-2];
    if ((byte)(cVar1 - 0x30U) < 10) {
      bVar3 = cVar1 - 0x30;
    }
    else if ((byte)(cVar1 + 0xbfU) < 6) {
      bVar3 = cVar1 - 0x37;
    }
    else {
      bVar3 = cVar1 + 0xa9;
    }
    uVar4 = (ushort)(bVar3 & 0xf) << 4;
    *(ushort *)(param_3 + uVar5 * 2) = uVar4;
    cVar1 = (char)psVar6[-1];
    if ((byte)(cVar1 - 0x30U) < 10) {
      bVar3 = cVar1 - 0x30;
    }
    else if ((byte)(cVar1 + 0xbfU) < 6) {
      bVar3 = cVar1 - 0x37;
    }
    else {
      bVar3 = cVar1 + 0xa9;
    }
    uVar4 = (bVar3 | uVar4) << 4;
    *(ushort *)(param_3 + uVar5 * 2) = uVar4;
    cVar1 = (char)*psVar6;
    if ((byte)(cVar1 - 0x30U) < 10) {
      bVar3 = cVar1 - 0x30;
    }
    else if ((byte)(cVar1 + 0xbfU) < 6) {
      bVar3 = cVar1 - 0x37;
    }
    else {
      bVar3 = cVar1 + 0xa9;
    }
    uVar4 = (bVar3 | uVar4) << 4;
    *(ushort *)(param_3 + uVar5 * 2) = uVar4;
    cVar1 = (char)psVar6[1];
    if ((byte)(cVar1 - 0x30U) < 10) {
      bVar3 = cVar1 - 0x30;
    }
    else if ((byte)(cVar1 + 0xbfU) < 6) {
      bVar3 = cVar1 - 0x37;
    }
    else {
      bVar3 = cVar1 + 0xa9;
    }
    psVar6 = psVar6 + 4;
    *(ushort *)(param_3 + uVar5 * 2) = bVar3 | uVar4;
  }
  *param_2 = uVar5;
  *(undefined2 *)(param_3 + uVar5 * 2) = 0;
  return;
}


// ==== FUN_00001268 @ 00001268

longlong FUN_00001268(longlong param_1,undefined8 *param_2,ulonglong *param_3)

{
  short sVar1;
  char cVar2;
  longlong lVar3;
  ulonglong uVar4;
  ulonglong uVar5;
  short *psVar6;
  
  uVar5 = 0;
  psVar6 = (short *)(param_1 + 10);
  while( true ) {
    sVar1 = *psVar6;
    uVar4 = (ulonglong)((ushort)(sVar1 - 0x30U) < 0x37);
    if ((ushort)(sVar1 - 0x3aU) < 7) {
      uVar4 = 0;
    }
    cVar2 = (char)uVar4;
    if ((ushort)(sVar1 - 0x47U) < 0x1a) {
      cVar2 = '\0';
    }
    if (cVar2 == '\0') break;
    uVar5 = uVar5 + 1;
    psVar6 = psVar6 + 1;
  }
  lVar3 = (**(code **)(DAT_00029478 + 0x40))(4,uVar5 >> 1,param_2);
  if (-1 < lVar3) {
    FUN_00000ff4(param_1 + 10,uVar5,(byte *)*param_2);
    lVar3 = 0;
    *param_3 = uVar5 >> 1;
  }
  return lVar3;
}


// ==== FUN_00001320 @ 00001320

longlong FUN_00001320(short *param_1,undefined8 param_2)

{
  short sVar1;
  longlong lVar2;
  short *psVar3;
  longlong lVar4;
  short *psVar5;
  char *local_res8 [2];
  ulonglong local_res18;
  char *local_res20;
  
  local_res8[0] = (char *)0x0;
  psVar3 = (short *)PTR_u_PATH__00025e68;
  lVar4 = 0;
  psVar5 = param_1;
  do {
    sVar1 = *psVar5;
    while ((sVar1 != 0x26 && (sVar1 != 0))) {
      lVar4 = lVar4 + 1;
      sVar1 = param_1[lVar4];
    }
    if (param_1[lVar4] == 0) {
      return -0x7ffffffffffffff2;
    }
    lVar4 = lVar4 + 1;
    psVar5 = param_1 + lVar4;
    lVar2 = 0;
    if (psVar5 != psVar3) {
      lVar2 = FUN_000002c0((char *)psVar5,(char *)psVar3,10);
      psVar3 = (short *)PTR_u_PATH__00025e68;
    }
  } while (lVar2 != 0);
  lVar4 = FUN_00001268((longlong)(param_1 + lVar4),local_res8,&local_res18);
  if (-1 < lVar4) {
    if ((((local_res8[0] == (char *)0x0) || (local_res18 < 4)) ||
        (local_res18 < *(ushort *)(local_res8[0] + 2))) ||
       ((4 < (byte)(*local_res8[0] - 1U) && (*local_res8[0] != '\x7f')))) {
      lVar4 = -0x7ffffffffffffff2;
    }
    else {
      local_res20 = local_res8[0];
      lVar4 = (**(code **)(DAT_00029478 + 0xb8))(&DAT_00023690,&local_res20,param_2);
    }
    (**(code **)(DAT_00029478 + 0x48))(local_res8[0]);
  }
  return lVar4;
}


// ==== FUN_000017b4 @ 000017b4

longlong FUN_000017b4(ulonglong param_1,short *param_2,longlong *param_3)

{
  longlong lVar1;
  short *psVar2;
  ulonglong uVar3;
  ulonglong local_res8;
  ulonglong local_res10 [2];
  longlong local_res20;
  longlong local_e8;
  byte local_e0 [16];
  undefined1 local_d0 [8];
  undefined1 local_c8 [160];
  
  local_res20 = 0;
  if (param_2 == (short *)0x0) {
    *param_3 = 0;
  }
  else {
    local_res8 = param_1;
    lVar1 = (**(code **)(DAT_00029478 + 0x140))(&DAT_00023700,0,&local_e8);
    if (lVar1 < 0) {
      return lVar1;
    }
    if (param_2 == (short *)PTR_u_GUID__00025e58) {
      lVar1 = 0;
    }
    else {
      lVar1 = FUN_000002c0((char *)param_2,PTR_u_GUID__00025e58,10);
    }
    if (lVar1 == 0) {
      lVar1 = FUN_00001320(param_2,local_d0);
      if (lVar1 < 0) {
        return -0x7ffffffffffffff2;
      }
      local_res10[0] = 0x20;
      FUN_00000ff4((longlong)(param_2 + 5),0x20,local_e0);
      if (param_2[0x25] == 0x26) {
        if (param_2 + 0x26 == (short *)PTR_u_NAME__00025e48) {
          lVar1 = 0;
        }
        else {
          lVar1 = FUN_000002c0((char *)(param_2 + 0x26),PTR_u_NAME__00025e48,10);
        }
        if (lVar1 == 0) {
          psVar2 = param_2 + 0x2b;
          local_res10[0] = 0x50;
          FUN_00001074((longlong)psVar2,local_res10,(longlong)local_c8);
          if (psVar2[local_res10[0] * 4] != 0x26) {
            *param_3 = (longlong)(psVar2 + local_res10[0] * 4);
            return -0x7ffffffffffffffe;
          }
          local_res10[0] = 0;
          lVar1 = (**(code **)(DAT_00029488 + 0x48))
                            (local_c8,local_e0,&local_res8,local_res10,local_res20);
          if (lVar1 == -0x7ffffffffffffffb) {
            (**(code **)(DAT_00029478 + 0x40))(4,local_res10[0],&local_res20);
            lVar1 = (**(code **)(DAT_00029488 + 0x48))
                              (local_c8,local_e0,&local_res8,local_res10,local_res20);
          }
          if (lVar1 < 0) {
            if (local_res20 != 0) {
              (**(code **)(DAT_00029478 + 0x48))();
            }
            local_res8 = CONCAT44(local_res8._4_4_,7);
            local_res20 = 0;
            local_res10[0] = 0;
          }
          uVar3 = local_res10[0];
          lVar1 = (**(code **)(local_e8 + 0x20))(local_e8,param_2,local_res20,local_res10,param_3);
          do {
            if (lVar1 != -0x7ffffffffffffff9) {
              if (lVar1 != -0x7ffffffffffffffe) {
                if (-1 < lVar1) {
                  (**(code **)(DAT_00029488 + 0x58))
                            (local_c8,local_e0,local_res8 & 0xffffffff,uVar3,local_res20);
                  (**(code **)(DAT_00029478 + 0x48))(local_res20);
                  return 0;
                }
                return lVar1;
              }
              if (local_res20 != 0) {
                return -0x7ffffffffffffffe;
              }
            }
            if (local_res20 != 0) {
              (**(code **)(DAT_00029478 + 0x48))();
            }
            lVar1 = (**(code **)(DAT_00029478 + 0x40))(4,local_res10[0],&local_res20);
            uVar3 = local_res10[0];
            if (lVar1 < 0) {
              return lVar1;
            }
            lVar1 = (**(code **)(local_e8 + 0x20))(local_e8,param_2,local_res20,local_res10,param_3)
            ;
          } while( true );
        }
      }
      *param_3 = (longlong)(param_2 + 0x25);
    }
    else {
      *param_3 = (longlong)param_2;
    }
  }
  return -0x7ffffffffffffffe;
}


// ==== FUN_00001a5c @ 00001a5c

undefined8 FUN_00001a5c(void)

{
  undefined8 uVar1;
  uint uVar2;
  ulonglong uVar4;
  undefined1 local_18;
  ulonglong uVar3;
  
  uVar4 = 0;
  if ((DAT_00029270 == 0) || (*(longlong *)(DAT_00029270 + 8) == 0x1000)) {
    uVar1 = 0x8000000000000003;
  }
  else {
    if (*(longlong *)(DAT_00029270 + 8) == 1) {
      if (**(byte **)(DAT_00029270 + 0x18) == 0) {
        uVar4 = 0xa0;
        uVar3 = 0;
      }
      else {
        uVar2 = **(byte **)(DAT_00029270 + 0x18) - 1;
        uVar3 = (ulonglong)uVar2;
        if (uVar2 != 0) {
          if (uVar2 == 1) {
            uVar4 = 0x10;
          }
          else {
            uVar4 = (ulonglong)local_18;
          }
        }
      }
      FUN_0001ba3c(uVar3,uVar4,0x51,(char)uVar4);
    }
    uVar1 = 0;
  }
  return uVar1;
}


// ==== FUN_00001b1c @ 00001b1c

longlong FUN_00001b1c(short param_1,longlong param_2)

{
  undefined8 *puVar1;
  longlong lVar2;
  undefined8 *local_res10;
  
  local_res10 = (undefined8 *)0x0;
  lVar2 = -0x7ffffffffffffffe;
  puVar1 = DAT_0002b3a0;
  if (param_2 != 0) {
    for (; (undefined8 **)puVar1 != &DAT_0002b3a0; puVar1 = (undefined8 *)*puVar1) {
      if (*(short *)(puVar1 + 2) == param_1) {
        return -0x7ffffffffffffffd;
      }
    }
    lVar2 = (**(code **)(DAT_00029478 + 0x40))(4,0x20,&local_res10);
    if (-1 < lVar2) {
      *(short *)(local_res10 + 2) = param_1;
      local_res10[3] = param_2;
      *local_res10 = &DAT_0002b3a0;
      local_res10[1] = DAT_0002b3a8;
      *DAT_0002b3a8 = local_res10;
      DAT_0002b3a8 = local_res10;
    }
  }
  return lVar2;
}


// ==== FUN_00001bd8 @ 00001bd8

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

undefined8 FUN_00001bd8(undefined8 *param_1,undefined8 *param_2,longlong param_3,byte *param_4)

{
  byte bVar1;
  byte bVar2;
  byte bVar3;
  byte bVar4;
  byte bVar5;
  byte bVar6;
  byte bVar7;
  short sVar8;
  bool bVar9;
  bool bVar10;
  longlong lVar11;
  longlong lVar12;
  wchar_t *pwVar13;
  short *psVar14;
  longlong lVar15;
  short *psVar16;
  short local_1f8 [2];
  undefined4 local_1f4;
  undefined2 local_1f0;
  short local_1e8;
  short local_1e6 [11];
  byte local_1d0;
  byte local_1cf;
  byte local_1ce;
  undefined8 local_1c8;
  undefined2 local_1c0;
  undefined8 local_1b8;
  undefined2 local_1b0;
  undefined8 local_1a8;
  undefined2 local_1a0;
  undefined8 local_198;
  undefined2 local_190;
  undefined8 local_188;
  undefined2 local_180;
  short local_178 [4];
  wchar_t local_170 [4];
  wchar_t local_168 [4];
  wchar_t local_160 [4];
  wchar_t local_158 [4];
  wchar_t local_150 [4];
  wchar_t local_148 [4];
  wchar_t local_140 [2];
  wchar_t awStack_13c [2];
  wchar_t awStack_138 [2];
  wchar_t awStack_134 [2];
  wchar_t local_130 [2];
  wchar_t local_12c;
  wchar_t local_128 [4];
  wchar_t awStack_120 [4];
  wchar_t local_118;
  wchar_t local_110 [4];
  wchar_t awStack_108 [4];
  wchar_t local_100 [2];
  wchar_t awStack_fc [2];
  wchar_t awStack_f8 [2];
  wchar_t awStack_f4 [2];
  wchar_t local_f0;
  undefined8 local_e8;
  short local_dc;
  wchar_t awStack_da [4];
  short asStack_d2 [73];
  
  local_168._0_4_ = u_Drive_00025e70._8_4_;
  bVar9 = true;
  local_118 = u_Keyboard_00025e80[8];
  local_158._0_4_ = u_Mouse_00025e98._8_4_;
  local_148._0_4_ = u_Point_00025ea8._8_4_;
  local_1c0 = DAT_00025ec0;
  local_170 = (wchar_t  [4])u_Drive_00025e70._0_8_;
  local_178[0] = 0x48;
  local_178[1] = 0x75;
  local_178[2] = 0x62;
  local_178[3] = 0;
  local_f0 = u_SmartCard_Reader_00025ec8[0x10];
  local_128 = (wchar_t  [4])u_Keyboard_00025e80._0_8_;
  awStack_120 = (wchar_t  [4])u_Keyboard_00025e80._8_8_;
  local_1b0 = DAT_00025ef8;
  local_160 = (wchar_t  [4])u_Mouse_00025e98._0_8_;
  local_150 = (wchar_t  [4])u_Point_00025ea8._0_8_;
  local_1a0 = DAT_00025f08;
  local_1c8 = _DAT_00025eb8;
  local_190 = DAT_00025f18;
  local_110 = (wchar_t  [4])u_SmartCard_Reader_00025ec8._0_8_;
  awStack_108 = (wchar_t  [4])u_SmartCard_Reader_00025ec8._8_8_;
  local_180 = DAT_00025f28;
  local_1b8 = _DAT_00025ef0;
  local_1a8 = _DAT_00025f00;
  local_1f4 = DAT_00025f2c;
  local_1f0 = DAT_00025f30;
  local_198 = _DAT_00025f10;
  local_188 = _DAT_00025f20;
  local_130 = (wchar_t  [2])u_None_00025f38._16_4_;
  local_12c = u_None_00025f38[10];
  local_100 = (wchar_t  [2])u_SmartCard_Reader_00025ec8._16_4_;
  awStack_fc = (wchar_t  [2])u_SmartCard_Reader_00025ec8._20_4_;
  awStack_f8 = (wchar_t  [2])u_SmartCard_Reader_00025ec8._24_4_;
  awStack_f4 = (wchar_t  [2])u_SmartCard_Reader_00025ec8._28_4_;
  local_1f8[0] = 0x20;
  local_1f8[1] = 0;
  local_140 = (wchar_t  [2])u_None_00025f38._0_4_;
  awStack_13c = (wchar_t  [2])u_None_00025f38._4_4_;
  awStack_138 = (wchar_t  [2])u_None_00025f38._8_4_;
  awStack_134 = (wchar_t  [2])u_None_00025f38._12_4_;
  (**(code **)(param_3 + 8))(param_4);
  bVar1 = param_4[6];
  bVar2 = param_4[5];
  bVar3 = param_4[3];
  bVar4 = *param_4;
  bVar5 = param_4[1];
  bVar6 = param_4[2];
  bVar7 = param_4[4];
  local_1d0 = param_4[7];
  local_1cf = param_4[8];
  local_1ce = param_4[9];
  FUN_00000320((undefined1 *)&local_e8,0xa0,0);
  FUN_000002e0(&local_e8,(undefined8 *)local_140,0x14);
  psVar14 = &local_dc;
  if ((byte)(bVar3 - 1) < 0x7e) {
    FUN_0001d994((ulonglong)bVar3,&local_1e8,10,'\0');
    psVar14 = &local_1e8;
    lVar12 = 0;
    sVar8 = local_1e8;
    while (sVar8 != 0) {
      psVar14 = psVar14 + 1;
      lVar12 = lVar12 + 1;
      sVar8 = *psVar14;
    }
    if (lVar12 * 2 != 0) {
      FUN_000002e0((undefined8 *)&local_dc,(undefined8 *)&local_1e8,lVar12 * 2);
    }
    if (&local_dc + lVar12 != local_1f8) {
      FUN_000002e0((undefined8 *)(&local_dc + lVar12),(undefined8 *)local_1f8,2);
    }
    if (awStack_da + lVar12 != local_170) {
      FUN_000002e0((undefined8 *)(awStack_da + lVar12),(undefined8 *)local_170,10);
    }
    psVar14 = asStack_d2 + lVar12 + 1;
    if (1 < bVar3) {
      *psVar14 = 0x73;
      psVar14 = asStack_d2 + lVar12 + 2;
    }
    bVar9 = false;
  }
  lVar12 = 0;
  if ((byte)(bVar4 - 1) < 0x7e) {
    if (!bVar9) {
      if (psVar14 != (short *)&local_1f4) {
        FUN_000002e0((undefined8 *)psVar14,(undefined8 *)&local_1f4,4);
      }
      psVar14 = psVar14 + 2;
    }
    FUN_0001d994((ulonglong)bVar4,&local_1e8,10,'\0');
    psVar16 = &local_1e8;
    sVar8 = local_1e8;
    while (sVar8 != 0) {
      psVar16 = psVar16 + 1;
      lVar12 = lVar12 + 1;
      sVar8 = *psVar16;
    }
    if ((lVar12 * 2 != 0) && (psVar14 != &local_1e8)) {
      FUN_000002e0((undefined8 *)psVar14,(undefined8 *)&local_1e8,lVar12 * 2);
    }
    psVar16 = psVar14 + lVar12;
    if (psVar16 != local_1f8) {
      FUN_000002e0((undefined8 *)psVar16,(undefined8 *)local_1f8,2);
    }
    if (psVar16 + 1 != local_128) {
      FUN_000002e0((undefined8 *)(psVar16 + 1),(undefined8 *)local_128,0x10);
    }
    psVar14 = psVar16 + 9;
    if (1 < bVar4) {
      *psVar14 = 0x73;
      psVar14 = psVar16 + 10;
    }
    bVar9 = false;
  }
  lVar12 = 0;
  if ((byte)(bVar5 - 1) < 0x7e) {
    if (!bVar9) {
      if (psVar14 != (short *)&local_1f4) {
        FUN_000002e0((undefined8 *)psVar14,(undefined8 *)&local_1f4,4);
      }
      psVar14 = psVar14 + 2;
    }
    lVar11 = 10;
    FUN_0001d994((ulonglong)bVar5,&local_1e8,10,'\0');
    psVar16 = &local_1e8;
    lVar15 = lVar12;
    sVar8 = local_1e8;
    while (sVar8 != 0) {
      psVar16 = psVar16 + 1;
      lVar15 = lVar15 + 1;
      sVar8 = *psVar16;
    }
    if ((lVar15 * 2 != 0) && (psVar14 != &local_1e8)) {
      FUN_000002e0((undefined8 *)psVar14,(undefined8 *)&local_1e8,lVar15 * 2);
    }
    psVar14 = psVar14 + lVar15;
    if (psVar14 != local_1f8) {
      FUN_000002e0((undefined8 *)psVar14,(undefined8 *)local_1f8,2);
    }
    pwVar13 = psVar14 + 1;
    if (bVar5 == 1) {
      if (pwVar13 != local_160) {
        FUN_000002e0((undefined8 *)pwVar13,(undefined8 *)local_160,10);
      }
    }
    else {
      if (pwVar13 != (wchar_t *)&local_1c8) {
        FUN_000002e0((undefined8 *)pwVar13,&local_1c8,8);
      }
      lVar11 = 8;
    }
    bVar9 = false;
    psVar14 = (short *)((longlong)pwVar13 + lVar11);
  }
  if ((byte)(bVar6 - 1) < 0x7e) {
    if (!bVar9) {
      if (psVar14 != (short *)&local_1f4) {
        FUN_000002e0((undefined8 *)psVar14,(undefined8 *)&local_1f4,4);
      }
      psVar14 = psVar14 + 2;
    }
    FUN_0001d994((ulonglong)bVar6,&local_1e8,10,'\0');
    psVar16 = &local_1e8;
    lVar15 = lVar12;
    sVar8 = local_1e8;
    while (sVar8 != 0) {
      psVar16 = psVar16 + 1;
      lVar15 = lVar15 + 1;
      sVar8 = *psVar16;
    }
    if ((lVar15 * 2 != 0) && (psVar14 != &local_1e8)) {
      FUN_000002e0((undefined8 *)psVar14,(undefined8 *)&local_1e8,lVar15 * 2);
    }
    psVar16 = psVar14 + lVar15;
    if (psVar16 != local_1f8) {
      FUN_000002e0((undefined8 *)psVar16,(undefined8 *)local_1f8,2);
    }
    if (psVar16 + 1 != local_150) {
      FUN_000002e0((undefined8 *)(psVar16 + 1),(undefined8 *)local_150,10);
    }
    psVar14 = psVar16 + 6;
    if (1 < bVar6) {
      *psVar14 = 0x73;
      psVar14 = psVar16 + 7;
    }
    bVar9 = false;
  }
  bVar10 = false;
  if ((byte)(bVar7 - 1) < 0x7e) {
    if (!bVar9) {
      if (psVar14 != (short *)&local_1f4) {
        FUN_000002e0((undefined8 *)psVar14,(undefined8 *)&local_1f4,4);
      }
      psVar14 = psVar14 + 2;
    }
    FUN_0001d994((ulonglong)bVar7,&local_1e8,10,'\0');
    psVar16 = &local_1e8;
    lVar15 = lVar12;
    sVar8 = local_1e8;
    while (sVar8 != 0) {
      psVar16 = psVar16 + 1;
      lVar15 = lVar15 + 1;
      sVar8 = *psVar16;
    }
    if ((lVar15 * 2 != 0) && (psVar14 != &local_1e8)) {
      FUN_000002e0((undefined8 *)psVar14,(undefined8 *)&local_1e8,lVar15 * 2);
    }
    psVar16 = psVar14 + lVar15;
    if (psVar16 != local_1f8) {
      FUN_000002e0((undefined8 *)psVar16,(undefined8 *)local_1f8,2);
    }
    if (psVar16 + 1 != local_178) {
      FUN_000002e0((undefined8 *)(psVar16 + 1),(undefined8 *)local_178,6);
    }
    psVar14 = psVar16 + 4;
    bVar9 = bVar10;
    if (1 < bVar7) {
      *psVar14 = 0x73;
      psVar14 = psVar16 + 5;
    }
  }
  if (bVar2 != 0) {
    if (!bVar9) {
      if (psVar14 != (short *)&local_1f4) {
        FUN_000002e0((undefined8 *)psVar14,(undefined8 *)&local_1f4,4);
      }
      psVar14 = psVar14 + 2;
    }
    FUN_0001d994((ulonglong)bVar2,&local_1e8,10,'\0');
    psVar16 = &local_1e8;
    lVar15 = lVar12;
    sVar8 = local_1e8;
    while (sVar8 != 0) {
      psVar16 = psVar16 + 1;
      lVar15 = lVar15 + 1;
      sVar8 = *psVar16;
    }
    if ((lVar15 * 2 != 0) && (psVar14 != &local_1e8)) {
      FUN_000002e0((undefined8 *)psVar14,(undefined8 *)&local_1e8,lVar15 * 2);
    }
    psVar14 = psVar14 + lVar15;
    if (psVar14 != local_1f8) {
      FUN_000002e0((undefined8 *)psVar14,(undefined8 *)local_1f8,2);
    }
    if (psVar14 + 1 != local_110) {
      FUN_000002e0((undefined8 *)(psVar14 + 1),(undefined8 *)local_110,0x20);
    }
    if (1 < bVar2) {
      psVar14[0x11] = 0x73;
    }
  }
  if (param_1 != &local_e8) {
    FUN_000002e0(param_1,&local_e8,0xa0);
  }
  bVar9 = true;
  FUN_00000320((undefined1 *)&local_e8,0xa0,0);
  FUN_000002e0(&local_e8,(undefined8 *)local_140,0x14);
  psVar14 = &local_dc;
  if (bVar1 != 0) {
    FUN_0001d994((ulonglong)bVar1,&local_1e8,10,'\0');
    psVar14 = &local_1e8;
    lVar15 = lVar12;
    sVar8 = local_1e8;
    while (sVar8 != 0) {
      psVar14 = psVar14 + 1;
      lVar15 = lVar15 + 1;
      sVar8 = *psVar14;
    }
    if (lVar15 * 2 != 0) {
      FUN_000002e0((undefined8 *)&local_dc,(undefined8 *)&local_1e8,lVar15 * 2);
    }
    if (&local_dc + lVar15 != local_1f8) {
      FUN_000002e0((undefined8 *)(&local_dc + lVar15),(undefined8 *)local_1f8,2);
    }
    if (awStack_da + lVar15 != (wchar_t *)&local_1b8) {
      FUN_000002e0((undefined8 *)(awStack_da + lVar15),&local_1b8,8);
    }
    psVar14 = asStack_d2 + lVar15;
    if (1 < bVar1) {
      *psVar14 = 0x73;
      psVar14 = asStack_d2 + lVar15 + 1;
    }
    bVar9 = false;
  }
  bVar1 = local_1d0;
  if (local_1d0 != 0) {
    if (!bVar9) {
      if (psVar14 != (short *)&local_1f4) {
        FUN_000002e0((undefined8 *)psVar14,(undefined8 *)&local_1f4,4);
      }
      psVar14 = psVar14 + 2;
    }
    FUN_0001d994((ulonglong)bVar1,&local_1e8,10,'\0');
    psVar16 = &local_1e8;
    lVar15 = lVar12;
    sVar8 = local_1e8;
    while (sVar8 != 0) {
      psVar16 = psVar16 + 1;
      lVar15 = lVar15 + 1;
      sVar8 = *psVar16;
    }
    if ((lVar15 * 2 != 0) && (psVar14 != &local_1e8)) {
      FUN_000002e0((undefined8 *)psVar14,(undefined8 *)&local_1e8,lVar15 * 2);
    }
    psVar16 = psVar14 + lVar15;
    if (psVar16 != local_1f8) {
      FUN_000002e0((undefined8 *)psVar16,(undefined8 *)local_1f8,2);
    }
    if (psVar16 + 1 != (short *)&local_1a8) {
      FUN_000002e0((undefined8 *)(psVar16 + 1),&local_1a8,8);
    }
    psVar14 = psVar16 + 5;
    if (1 < bVar1) {
      *psVar14 = 0x73;
      psVar14 = psVar16 + 6;
    }
    bVar9 = false;
  }
  bVar1 = local_1cf;
  if (local_1cf != 0) {
    if (!bVar9) {
      if (psVar14 != (short *)&local_1f4) {
        FUN_000002e0((undefined8 *)psVar14,(undefined8 *)&local_1f4,4);
      }
      psVar14 = psVar14 + 2;
    }
    FUN_0001d994((ulonglong)bVar1,&local_1e8,10,'\0');
    psVar16 = &local_1e8;
    lVar15 = lVar12;
    sVar8 = local_1e8;
    while (sVar8 != 0) {
      psVar16 = psVar16 + 1;
      lVar15 = lVar15 + 1;
      sVar8 = *psVar16;
    }
    if ((lVar15 * 2 != 0) && (psVar14 != &local_1e8)) {
      FUN_000002e0((undefined8 *)psVar14,(undefined8 *)&local_1e8,lVar15 * 2);
    }
    psVar16 = psVar14 + lVar15;
    if (psVar16 != local_1f8) {
      FUN_000002e0((undefined8 *)psVar16,(undefined8 *)local_1f8,2);
    }
    if (psVar16 + 1 != (short *)&local_198) {
      FUN_000002e0((undefined8 *)(psVar16 + 1),&local_198,8);
    }
    psVar14 = psVar16 + 5;
    bVar9 = bVar10;
    if (1 < bVar1) {
      *psVar14 = 0x73;
      psVar14 = psVar16 + 6;
    }
  }
  bVar1 = local_1ce;
  if (local_1ce != 0) {
    if (!bVar9) {
      if (psVar14 != (short *)&local_1f4) {
        FUN_000002e0((undefined8 *)psVar14,(undefined8 *)&local_1f4,4);
      }
      psVar14 = psVar14 + 2;
    }
    FUN_0001d994((ulonglong)bVar1,&local_1e8,10,'\0');
    psVar16 = &local_1e8;
    while (local_1e8 != 0) {
      psVar16 = psVar16 + 1;
      lVar12 = lVar12 + 1;
      local_1e8 = *psVar16;
    }
    if ((lVar12 * 2 != 0) && (psVar14 != &local_1e8)) {
      FUN_000002e0((undefined8 *)psVar14,(undefined8 *)&local_1e8,lVar12 * 2);
    }
    psVar14 = psVar14 + lVar12;
    if (psVar14 != local_1f8) {
      FUN_000002e0((undefined8 *)psVar14,(undefined8 *)local_1f8,2);
    }
    if (psVar14 + 1 != (short *)&local_188) {
      FUN_000002e0((undefined8 *)(psVar14 + 1),&local_188,8);
    }
    if (1 < bVar1) {
      psVar14[5] = 0x73;
    }
  }
  if (param_2 != &local_e8) {
    FUN_000002e0(param_2,&local_e8,0xa0);
  }
  return 0;
}


// ==== FUN_00002678 @ 00002678

char FUN_00002678(ushort *param_1,undefined8 param_2,longlong param_3,undefined8 param_4)

{
  char cVar1;
  byte *pbVar2;
  undefined8 local_68;
  undefined1 local_38 [48];
  
  FUN_00023370((undefined4 *)&local_68,0,0x30);
  cVar1 = (**(code **)(param_3 + 0x10))(local_38,0x30);
  if (cVar1 != -1) {
    FUN_0001daf4((byte *)&local_68,&DAT_00025f50,local_38,param_4);
  }
  pbVar2 = (byte *)&local_68;
  while ((char)local_68 != '\0') {
    *param_1 = (ushort)local_68 & 0xff;
    param_1 = param_1 + 1;
    pbVar2 = pbVar2 + 1;
    local_68 = (ulonglong)*pbVar2;
  }
  *param_1 = 0;
  return cVar1;
}


// ==== FUN_00002cd4 @ 00002cd4

void FUN_00002cd4(undefined2 param_1,undefined8 *param_2)

{
  undefined8 uVar1;
  longlong lVar2;
  undefined8 local_res10;
  
  local_res10 = 0;
  lVar2 = DAT_0002b360;
  FUN_0001e7c4(DAT_0002b360,param_1,&local_res10,0);
  uVar1 = FUN_0001b514(lVar2,local_res10);
  FUN_0001e7c4(DAT_0002b360,param_1,&local_res10,uVar1);
  *param_2 = uVar1;
  return;
}


// ==== FUN_00002e20 @ 00002e20

void FUN_00002e20(longlong param_1)

{
  undefined2 uVar1;
  ulonglong uVar2;
  byte *local_res8 [4];
  
  FUN_00000680(DAT_0002b360,0x17d8,(byte *)u__d__02d____d__02d_MHz_00025fd0,
               (ulonglong)*(uint *)(param_1 + 0x24) / 1000000);
  uVar2 = (ulonglong)*(byte *)(param_1 + 0x2a) / 100;
  FUN_00000680(DAT_0002b360,0x17da,(byte *)u__d__02d___00026000,uVar2);
  uVar1 = 0x17e7;
  if (*(char *)(param_1 + 0x28) == '\0') {
    uVar1 = 0x17e8;
  }
  FUN_00002cd4(uVar1,local_res8);
  FUN_00000680(DAT_0002b360,0x17dc,local_res8[0],uVar2);
                    /* WARNING: Could not recover jumptable at 0x00002f03. Too many branches */
                    /* WARNING: Treating indirect jump as call */
  (**(code **)(DAT_00029478 + 0x48))(local_res8[0]);
  return;
}


// ==== FUN_00003020 @ 00003020

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_00003020(undefined8 *param_1)

{
  longlong lVar1;
  int local_res10 [2];
  byte local_res18 [8];
  undefined4 local_res20 [2];
  ulonglong in_stack_ffffffffffffff88;
  undefined4 local_68 [2];
  undefined8 *local_60;
  undefined8 local_58;
  undefined4 local_50;
  undefined4 local_4c;
  undefined4 local_48;
  undefined4 local_44;
  undefined4 local_40;
  int local_38;
  char local_28;
  char local_27;
  
  lVar1 = (**(code **)(DAT_00029478 + 0x140))(&DAT_000234b0,0,&local_60);
  if (-1 < lVar1) {
    lVar1 = (*(code *)local_60[8])(local_res10);
    if ((-1 < lVar1) && (local_res10[0] == 0)) {
      lVar1 = (*(code *)local_60[7])(local_res18);
      if ((-1 < lVar1) && ((local_res18[0] & 0xf) == 0)) {
        local_res20[0] = 0x30;
        if ((undefined8 *)&local_50 != param_1) {
          FUN_000002e0((undefined8 *)&local_50,param_1,0x30);
        }
        local_48 = 0;
        local_40 = 0;
        local_50 = 0x50000;
        local_4c = 0x1b;
        local_44 = 0x1c;
        (*(code *)*local_60)
                  (0,&local_50,0x30,local_res20,in_stack_ffffffffffffff88 & 0xffffffffffffff00,8);
      }
    }
  }
  local_58 = 0x21d;
  lVar1 = (**(code **)(DAT_00029488 + 0x48))
                    (u_SaSetup_00026070,&DAT_000238f0,local_68,&local_58,&DAT_00029530);
  if (-1 < lVar1) {
    _DAT_00029581 = *(uint *)((longlong)param_1 + 0x1c) / 10000;
    (**(code **)(DAT_00029488 + 0x58))
              (u_SaSetup_00026070,&DAT_000238f0,local_68[0],local_58,&DAT_00029530);
    FUN_000002e0((undefined8 *)&local_50,(undefined8 *)&DAT_00029780,0x30);
    if (((*(int *)(param_1 + 3) != local_38) || (*(char *)(param_1 + 5) != local_28)) ||
       (*(char *)((longlong)param_1 + 0x29) != local_27)) {
      local_res10[0] = CONCAT31(local_res10[0]._1_3_,1);
      (**(code **)(DAT_00029488 + 0x58))(u_WdtPersistentData_00026048,&DAT_00023730,3,1,local_res10)
      ;
    }
  }
  return;
}


// ==== FUN_00003230 @ 00003230

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_00003230(void)

{
  longlong lVar1;
  undefined8 *puVar2;
  int local_res8 [2];
  byte local_res10 [16];
  undefined2 local_res20;
  undefined1 local_res22;
  undefined1 local_res23;
  undefined1 local_res24;
  undefined1 local_res25;
  undefined1 local_res26;
  bool local_res27;
  undefined8 local_108 [2];
  undefined8 local_f8;
  undefined8 uStack_f0;
  undefined8 local_e8;
  undefined8 uStack_e0;
  undefined8 local_d8;
  undefined8 uStack_d0;
  undefined1 local_c8 [168];
  
  FUN_00000340((undefined8 *)&local_res20,8);
  if ((DAT_00029288 == 0) &&
     (lVar1 = (**(code **)(DAT_00029478 + 0x140))(&DAT_000234b0,0), lVar1 < 0)) {
    local_res27 = false;
    local_res25 = 0;
  }
  else {
    local_108[0] = 8;
    (**(code **)(DAT_00029488 + 0x48))
              (u_IccAdvancedSetupDataVar_00026018,&DAT_00023580,0,local_108,&local_res20);
    if (DAT_00029278 == '\0') {
      FUN_00000320(&DAT_00029750,0x30,0);
      _DAT_00029764 = CONCAT31(DAT_00029764_1,1);
      lVar1 = FUN_00020a08((undefined8 *)&DAT_00029750);
      if (-1 < lVar1) {
        DAT_00029278 = '\x01';
      }
    }
    puVar2 = (undefined8 *)FUN_0001b544(0x300);
    if (puVar2 == (undefined8 *)0x0) {
      return;
    }
    lVar1 = FUN_00020790((undefined1 *)local_res8,local_res10 + 8,local_res10,puVar2);
    if (lVar1 < 0) {
      return;
    }
    local_e8 = CONCAT44(_DAT_00029764,_DAT_00029760);
    uStack_e0 = CONCAT44(uRam000000000002976c,DAT_00029768);
    DAT_0002927c._1_1_ = (undefined1)local_res8[0];
    DAT_0002927c._0_1_ = local_res10[8];
    local_res26 = (undefined1)local_res8[0];
    DAT_0002927c._2_1_ = 1 < local_res10[8] && local_res10[0] != 0;
    local_f8 = _DAT_00029750;
    uStack_f0 = uRam0000000000029758;
    local_d8 = CONCAT44(DAT_00029774,DAT_00029770);
    uStack_d0 = CONCAT62(_DAT_0002977a,CONCAT11(DAT_00029779,DAT_00029778));
    DAT_0002927c._3_1_ = 0;
    local_res20 = (undefined2)((ulonglong)(DAT_00029768 + 5000) / 10000);
    local_res22 = DAT_00029779;
    FUN_00002e20((longlong)&local_f8);
    local_res10[0] = 0x97;
    local_res10[1] = 0;
    local_res10[2] = 0;
    local_res10[3] = 0;
    local_res10[4] = 0;
    local_res10[5] = 0;
    local_res10[6] = 0;
    local_res10[7] = 0;
    (**(code **)(DAT_00029488 + 0x48))
              (u_SetupVolatileData_00026080,&DAT_00023710,0,local_res10,local_c8);
    (**(code **)(DAT_00029288 + 0x40))(local_res8);
    local_res27 = local_res8[0] == 0;
    if ((DAT_0002927c._2_1_ == '\0') || (local_res25 = 1, local_res8[0] != 0)) {
      local_res25 = 0;
    }
    local_res23 = DAT_00029770 != DAT_00029774;
    local_res24 = DAT_00029778 != '\0';
  }
  (**(code **)(DAT_00029488 + 0x58))
            (u_IccAdvancedSetupDataVar_00026018,&DAT_00023580,3,8,&local_res20);
  return;
}


// ==== FUN_00003458 @ 00003458

void FUN_00003458(longlong param_1)

{
  longlong lVar1;
  undefined1 local_res18 [8];
  ushort local_res20;
  undefined1 local_res22;
  char local_res26;
  char local_res27;
  undefined8 local_68;
  undefined8 local_60;
  undefined1 local_58 [8];
  undefined8 local_50 [2];
  undefined1 local_3c;
  int local_34;
  undefined1 local_28;
  undefined1 local_27;
  ushort local_24;
  
  local_68 = 0x21d;
  local_60 = 8;
  lVar1 = (**(code **)(DAT_00029478 + 0x140))(&DAT_00023720,0,local_58);
  if ((-1 < lVar1) && (FUN_00000340((undefined8 *)&local_res20,8), DAT_00029288 != 0)) {
    (**(code **)(DAT_00029488 + 0x48))
              (u_SaSetup_00026070,&DAT_000238f0,local_res18,&local_68,&DAT_00029530);
    lVar1 = (**(code **)(DAT_00029488 + 0x48))
                      (u_IccAdvancedSetupDataVar_00026018,&DAT_00023580,0,&local_60,&local_res20);
    if (-1 < lVar1) {
      if (DAT_00029280 == '\0') {
        DAT_0002974d = DAT_0002927c._1_1_;
      }
      if (local_res26 != DAT_0002974d) {
        FUN_00020918(local_res26);
        DAT_0002974d = local_res26;
        DAT_00029280 = '\x01';
        DAT_00029290 = 1;
      }
      FUN_00000320((undefined1 *)local_50,0x30,0);
      if (((DAT_00029280 == '\0') && (local_res27 != '\0')) && (DAT_00029279 != '\0')) {
        local_34 = (uint)local_res20 * 10000;
        DAT_00029290 = 1;
        DAT_00029279 = '\0';
        local_27 = local_res22;
        local_28 = 4;
        local_3c = 1;
        if (DAT_00029735 == '\0') {
          if (DAT_00029736 == '\0') {
            DAT_00029290 = 0;
            local_24 = local_24 & 0xffd7 | 0x10;
          }
          else if (DAT_00029736 == '\x01') {
            DAT_00029290 = 0;
            local_24 = local_24 & 0xffc7;
          }
        }
        else {
          DAT_00029290 = 1;
          local_24 = local_24 & 0xffcf | 8;
        }
        FUN_00003020(local_50);
      }
      if (param_1 != 0) {
        (**(code **)(DAT_00029478 + 0x70))(param_1);
      }
    }
  }
  return;
}


// ==== FUN_00003648 @ 00003648

void FUN_00003648(void)

{
  undefined1 uVar1;
  undefined1 local_res8 [16];
  undefined8 local_res18;
  
  uVar1 = DAT_000292ce;
  local_res18 = 6;
  DAT_000292ce = 1;
  (**(code **)(DAT_000294a0 + 0x48))
            (u_SecureVarPresent_000260a8,&DAT_000241f8,0,&local_res18,&DAT_000292c8);
  FUN_0001ebd4(6,&DAT_000292c8,&DAT_000241f8,u_SecureVarPresent_000260a8);
  local_res18 = 1;
  (**(code **)(DAT_000294a0 + 0x48))(u_SetupMode_000260d0,&DAT_000234a0,0,&local_res18,local_res8);
  FUN_0001ebd4(local_res18,local_res8,&DAT_000234a0,u_SetupMode_000260d0);
  local_res18 = 1;
  (**(code **)(DAT_000294a0 + 0x48))(u_SecureBoot_000260e8,&DAT_000234a0,0,&local_res18,local_res8);
  FUN_0001ebd4(local_res18,local_res8,&DAT_000234a0,u_SecureBoot_000260e8);
  local_res18 = 1;
  (**(code **)(DAT_000294a0 + 0x48))(u_VendorKeys_00026100,&DAT_000234a0,0,&local_res18,local_res8);
  FUN_0001ebd4(local_res18,local_res8,&DAT_000234a0,u_VendorKeys_00026100);
  local_res18 = 1;
  (**(code **)(DAT_000294a0 + 0x48))
            (u_VendorKeysNv_00026118,&DAT_00023780,0,&local_res18,local_res8);
  local_res18 = 1;
  (**(code **)(DAT_000294a0 + 0x48))(u_AuditMode_00026138,&DAT_000234a0,0,&local_res18,local_res8);
  FUN_0001ebd4(local_res18,local_res8,&DAT_000234a0,u_AuditMode_00026138);
  local_res18 = 1;
  (**(code **)(DAT_000294a0 + 0x48))
            (u_DeployedMode_00026150,&DAT_000234a0,0,&local_res18,local_res8);
  FUN_0001ebd4(local_res18,local_res8,&DAT_000234a0,u_DeployedMode_00026150);
  local_res18 = 1;
  (**(code **)(DAT_000294a0 + 0x48))
            (u_DeploymentModeNv_00026170,&DAT_000235c0,0,&local_res18,local_res8);
  DAT_000292ce = uVar1;
  return;
}


// ==== FUN_00003868 @ 00003868

void FUN_00003868(void)

{
  word *pwVar1;
  char cVar2;
  uint uVar3;
  undefined *puVar4;
  word *pwVar5;
  undefined1 uVar6;
  longlong lVar7;
  longlong lVar8;
  undefined2 uVar9;
  undefined *puVar10;
  longlong *plVar11;
  undefined **ppuVar12;
  word *pwVar13;
  word *pwVar14;
  undefined8 uVar15;
  byte bVar16;
  longlong *plVar17;
  ulonglong uVar18;
  word *local_res8;
  longlong *local_res10;
  longlong *local_res18;
  undefined8 local_res20;
  word *local_58;
  longlong local_50;
  longlong local_48 [2];
  
  bVar16 = 0;
  if (PTR_DAT_00025660 != (undefined *)0x0) {
    lVar8 = 0;
    ppuVar12 = &PTR_DAT_00025660;
    uVar18 = 0;
    do {
      puVar4 = *ppuVar12;
      puVar10 = &DAT_00023570;
      if (3 < bVar16) {
        puVar10 = &DAT_000234a0;
      }
      local_res8 = (word *)0x0;
      pwVar14 = (word *)0x0;
      (&DAT_000292c8)[uVar18] = 0;
      local_res20 = 0;
      lVar7 = (**(code **)(DAT_000294a0 + 0x48))(puVar4,puVar10,0,&local_res8,0);
      if (lVar7 == -0x7ffffffffffffffb) {
        local_res10 = (longlong *)0x0;
        (&DAT_000292c8)[uVar18] = 1;
        (**(code **)(DAT_00029498 + 0x40))(4,local_res8);
        pwVar14 = (word *)0x0;
        lVar7 = (**(code **)(DAT_000294a0 + 0x48))(*ppuVar12,puVar10,0,&local_res8,local_res10);
        if (-1 < lVar7) {
          if (local_res8 == (word *)0x0) {
            lVar7 = -0x7fffffffffffffe6;
          }
          else {
            pwVar14 = (word *)&local_res20;
            lVar7 = FUN_00022fc0(local_res10,(ulonglong)local_res8,(longlong *)pwVar14,
                                 (longlong *)0x0);
          }
          if (-1 < lVar7) {
            local_res18 = (longlong *)0x0;
            (**(code **)(DAT_00029498 + 0x40))(4,local_res8);
            local_58 = local_res8;
            pwVar14 = (word *)0x0;
            lVar8 = (**(code **)(DAT_000294a0 + 0x48))
                              (*(undefined8 *)((longlong)&PTR_u_dbxDefault_00025620 + lVar8),
                               &DAT_000234a0,0,&local_58,local_res18);
            pwVar5 = local_58;
            pwVar13 = local_res8;
            if (-1 < lVar8) {
              lVar8 = 0;
              plVar11 = local_res10;
              pwVar1 = local_58;
              while (pwVar1 <= pwVar13) {
                pwVar14 = pwVar5;
                lVar7 = FUN_0001edd4(plVar11,local_res18,(ulonglong)pwVar5);
                if (lVar7 == 0) {
                  (&DAT_000292c8)[uVar18] = 2;
                  uVar6 = (&DAT_000292c8)[uVar18];
                  if (pwVar5 < pwVar13) {
                    uVar6 = 3;
                  }
                  (&DAT_000292c8)[uVar18] = uVar6;
                  break;
                }
                uVar3 = *(uint *)(plVar11 + 2);
                if (0x6ffd3 < uVar3 - 0x2d) break;
                lVar8 = lVar8 + (ulonglong)uVar3;
                plVar11 = (longlong *)((longlong)plVar11 + (ulonglong)uVar3);
                pwVar1 = (word *)(lVar8 + (longlong)pwVar5);
              }
            }
            if (local_res18 != (longlong *)0x0) {
              (**(code **)(DAT_00029498 + 0x48))(local_res18);
              pwVar13 = local_res8;
            }
            plVar17 = (longlong *)0x0;
            plVar11 = local_res10;
            lVar8 = DAT_000292d0;
            if (pwVar13 != (word *)0x0) {
              do {
                lVar7 = FUN_0001edd4(plVar11,(longlong *)&DAT_00023960,0x10);
                if (lVar7 == 0) {
LAB_00003a9a:
                  local_48[0] = (ulonglong)*(uint *)((longlong)plVar11 + 0x14) + 0x2c +
                                (longlong)plVar11;
                  local_50 = (ulonglong)*(uint *)(plVar11 + 3) - 0x10;
                  if (lVar8 == 0) {
                    pwVar14 = (word *)&DAT_000292d0;
                    (**(code **)(DAT_00029498 + 0x140))(&DAT_00023640,0);
                    lVar8 = DAT_000292d0;
                    pwVar13 = local_res8;
                    if (DAT_000292d0 == 0) goto LAB_00003b4b;
                  }
                  (**(code **)(lVar8 + 0x10))
                            (lVar8,&DAT_00023510,1,local_48,&local_50,&DAT_00029298);
                  pwVar14 = IMAGE_DOS_HEADER_00000000.e_res_4_ + 2;
                  lVar8 = FUN_0001edd4((longlong *)&DAT_000241d8,(longlong *)&DAT_00029298,0x20);
                  if (lVar8 != 0) {
                    pwVar14 = IMAGE_DOS_HEADER_00000000.e_res_4_ + 2;
                    lVar7 = FUN_0001edd4((longlong *)&DAT_000241b8,(longlong *)&DAT_00029298,0x20);
                    lVar8 = DAT_000292d0;
                    pwVar13 = local_res8;
                    if (lVar7 != 0) goto LAB_00003b4b;
                  }
                  (&DAT_000292c8)[uVar18] = 4;
                  break;
                }
                pwVar14 = &IMAGE_DOS_HEADER_00000000.e_sp;
                lVar7 = FUN_0001edd4(plVar11,&DAT_00023760,0x10);
                if (lVar7 == 0) goto LAB_00003a9a;
LAB_00003b4b:
                uVar3 = *(uint *)(plVar11 + 2);
                if (0x6ffb4 < uVar3 - 0x4c) break;
                plVar17 = (longlong *)((longlong)plVar17 + (ulonglong)uVar3);
                plVar11 = (longlong *)((longlong)plVar11 + (ulonglong)uVar3);
              } while (plVar17 < pwVar13);
            }
          }
        }
        if (local_res10 != (longlong *)0x0) {
          (**(code **)(DAT_00029498 + 0x48))();
        }
      }
      cVar2 = (&DAT_000292c8)[uVar18];
      if (cVar2 == '\x01') {
        uVar9 = 0x19bd;
      }
      else if (cVar2 == '\x02') {
        uVar9 = 0x19be;
      }
      else if (cVar2 == '\x03') {
        uVar9 = 0x19bf;
      }
      else if (cVar2 == '\x04') {
        uVar9 = 0x19c0;
      }
      else {
        uVar9 = 0x19bc;
      }
      FUN_00005fa4(DAT_00029c60,uVar9,pwVar14,0x29940);
      uVar15 = 0;
      FUN_0002337e((undefined4 *)&DAT_00029ad0,400,0);
      FUN_00005fa4(DAT_00029c60,(&DAT_000262f8)[uVar18],uVar15,0x29ad0);
      FUN_0001c0f8(&DAT_000297b0,400,(byte *)u__s__5d__5d___s_00026198,0x29ad0);
      FUN_0001e908(DAT_00029c60,(&DAT_00026268)[uVar18],&DAT_000297b0);
      bVar16 = bVar16 + 1;
      uVar18 = (ulonglong)bVar16;
      lVar8 = uVar18 * 8;
      ppuVar12 = &PTR_DAT_00025660 + uVar18;
    } while (*ppuVar12 != (undefined *)0x0);
  }
  (**(code **)(DAT_000294a0 + 0x58))(u_SecureVarPresent_000260a8,&DAT_000241f8,2,6,&DAT_000292c8);
  FUN_00003648();
  return;
}


// ==== FUN_00003da8 @ 00003da8

/* WARNING: Removing unreachable block (ram,0x00003f0d) */
/* WARNING: Removing unreachable block (ram,0x00003f49) */
/* WARNING: Removing unreachable block (ram,0x00003f52) */
/* WARNING: Removing unreachable block (ram,0x00003f5a) */
/* WARNING: Removing unreachable block (ram,0x00003f62) */
/* WARNING: Removing unreachable block (ram,0x00003f76) */
/* WARNING: Removing unreachable block (ram,0x00003fa0) */
/* WARNING: Removing unreachable block (ram,0x00003fa7) */
/* WARNING: Removing unreachable block (ram,0x00003ffe) */
/* WARNING: Removing unreachable block (ram,0x00004005) */
/* WARNING: Removing unreachable block (ram,0x00004015) */
/* WARNING: Removing unreachable block (ram,0x0000401f) */
/* WARNING: Removing unreachable block (ram,0x00004023) */
/* WARNING: Removing unreachable block (ram,0x0000404a) */
/* WARNING: Removing unreachable block (ram,0x0000404d) */
/* WARNING: Removing unreachable block (ram,0x00004062) */
/* WARNING: Removing unreachable block (ram,0x00004067) */
/* WARNING: Removing unreachable block (ram,0x00004081) */
/* WARNING: Removing unreachable block (ram,0x00004079) */
/* WARNING: Removing unreachable block (ram,0x00004087) */
/* WARNING: Removing unreachable block (ram,0x000040a0) */
/* WARNING: Removing unreachable block (ram,0x000040e8) */

ulonglong FUN_00003da8(short *param_1,ulonglong param_2)

{
  uint uVar1;
  longlong lVar2;
  longlong lVar3;
  
  lVar2 = 0x5a4d;
  lVar3 = -0x7fffffffffffffeb;
  if (*param_1 == 0x5a4d) {
    uVar1 = *(uint *)(param_1 + 0x1e);
    lVar2 = 0x5a56;
    if ((*(short *)((longlong)param_1 + (ulonglong)uVar1) != 0x5a56) &&
       ((DAT_000292d0 != 0 ||
        ((lVar2 = (**(code **)(DAT_00029498 + 0x140))(&DAT_00023640,0,&DAT_000292d0), lVar3 = lVar2,
         -1 < lVar2 && (DAT_000292d0 != 0)))))) {
      lVar2 = (**(code **)(DAT_00029498 + 0x40))
                        (4,(ulonglong)(ushort)((short *)((longlong)param_1 + (ulonglong)uVar1))[3] *
                           0x28);
      lVar3 = lVar2;
    }
  }
  return CONCAT71((int7)((ulonglong)lVar2 >> 8),(byte)((ulonglong)lVar3 >> 0x3f)) ^ 1;
}


// ==== FUN_00004618 @ 00004618

void FUN_00004618(byte param_1,ushort param_2,longlong param_3,longlong param_4)

{
  undefined *puVar1;
  
  puVar1 = &DAT_00023570;
  if (3 < param_1) {
    puVar1 = &DAT_000234a0;
  }
  FUN_00022a5c(param_2,(longlong)(&PTR_DAT_00025660)[param_1],0,(longlong)puVar1,param_3,param_4);
  return;
}


// ==== FUN_00004664 @ 00004664

/* WARNING: Removing unreachable block (ram,0x000048bb) */

undefined8 FUN_00004664(longlong param_1,ushort param_2)

{
  bool bVar1;
  longlong lVar2;
  undefined *puVar3;
  ushort uVar4;
  ulonglong uVar5;
  longlong *plVar6;
  ushort uVar7;
  undefined8 local_res18;
  longlong local_res20;
  longlong *local_68;
  longlong local_60;
  longlong local_58;
  longlong local_50;
  undefined8 local_48;
  longlong local_40;
  
  local_58 = 0;
  local_50 = 0;
  bVar1 = true;
  local_68 = (longlong *)0x0;
  if ((param_2 < 7) && (local_res18 = 0, DAT_00029c60 = param_1, DAT_000292c0 != 0)) {
    lVar2 = FUN_00006518('\0',&local_48,&local_50,&local_58,&local_res18);
    if (-1 < lVar2) {
      uVar5 = (ulonglong)param_2;
      uVar7 = 0;
      if (param_2 == 6) {
        uVar5 = 0;
      }
      plVar6 = (longlong *)0x0;
      FUN_0002337e((undefined4 *)&DAT_00029ad0,400,0);
      do {
        uVar4 = (ushort)uVar5;
        if ((&PTR_DAT_00025660)[uVar5] == (undefined *)0x0) break;
        puVar3 = &DAT_00023570;
        if (3 < uVar4) {
          puVar3 = &DAT_000234a0;
        }
        plVar6 = (longlong *)0x0;
        local_res18 = 0;
        lVar2 = (**(code **)(DAT_000294a0 + 0x48))
                          ((&PTR_DAT_00025660)[uVar5],puVar3,0,&local_res18,0);
        if (lVar2 == -0x7ffffffffffffffb) {
          (**(code **)(DAT_00029498 + 0x40))(4,local_res18);
          plVar6 = (longlong *)0x0;
          lVar2 = (**(code **)(DAT_000294a0 + 0x48))
                            ((&PTR_DAT_00025660)[uVar5],puVar3,0,&local_res18,0);
          if (-1 < lVar2) {
            plVar6 = &local_40;
            lVar2 = (**(code **)(DAT_00029498 + 0x98))(local_48,&DAT_000237b0);
            if ((-1 < lVar2) &&
               (lVar2 = (**(code **)(local_40 + 8))(local_40,&local_60), -1 < lVar2)) {
              plVar6 = (longlong *)(&PTR_DAT_00025660)[uVar5];
              lVar2 = (**(code **)(local_60 + 8))(local_60,&local_res20,plVar6,0x8000000000000003,0)
              ;
              if (-1 < lVar2) {
                (**(code **)(local_res20 + 0x18))(local_res20);
                plVar6 = (longlong *)(&PTR_DAT_00025660)[uVar5];
                lVar2 = (**(code **)(local_60 + 8))
                                  (local_60,&local_res20,plVar6,0x8000000000000003,0);
                if (-1 < lVar2) {
                  plVar6 = local_68;
                  lVar2 = (**(code **)(local_res20 + 0x28))(local_res20,&local_res18);
                  (**(code **)(local_res20 + 0x10))(local_res20);
                  uVar7 = uVar7 + 1;
                  if (-1 < lVar2) goto LAB_000048c5;
                }
              }
            }
            bVar1 = false;
            FUN_00005fa4(param_1,0x19f1,plVar6,0x297b0);
            plVar6 = (longlong *)CONCAT71((int7)((ulonglong)plVar6 >> 8),1);
            (**(code **)(DAT_000292c0 + 0x20))(&DAT_000297b0,(&PTR_DAT_00025660)[uVar5],plVar6,0);
          }
        }
LAB_000048c5:
        uVar4 = uVar4 + 1;
        uVar5 = (ulonglong)uVar4;
        if (param_2 != 6) {
          uVar4 = 6;
          break;
        }
      } while (bVar1);
      if ((uVar4 == 6) && (bVar1)) {
        FUN_00005fa4(param_1,0x19f3,plVar6,0x29940);
        puVar3 = &DAT_00029940;
        FUN_0001c0f8(&DAT_00029ad0,400,&DAT_00029940,(ulonglong)uVar7);
        FUN_00005fa4(param_1,0x19f2,puVar3,0x297b0);
        (**(code **)(DAT_000292c0 + 0x20))(&DAT_000297b0,&DAT_00029ad0,1,0);
      }
    }
    if (local_58 != 0) {
      (**(code **)(DAT_00029498 + 0x48))();
    }
    if (local_50 != 0) {
      (**(code **)(DAT_00029498 + 0x48))();
    }
  }
  return 0;
}


// ==== FUN_0000568c @ 0000568c

ulonglong FUN_0000568c(undefined8 *param_1)

{
  short *psVar1;
  undefined8 uVar2;
  undefined1 uVar3;
  undefined4 local_18;
  undefined1 local_14;
  short *local_10;
  
  local_18 = 0x2419fe;
  local_14 = 0;
  local_10 = (short *)0x0;
  psVar1 = (short *)register0x00000020;
  if (param_1 != (undefined8 *)0x0) {
    if (DAT_000292b8 == (short *)0x0) {
      psVar1 = (short *)(**(code **)(DAT_00029498 + 0x40))(4,0x25,&DAT_000292b8);
      if ((longlong)psVar1 < 0) goto LAB_00005772;
      FUN_0001c0f8((char *)DAT_000292b8,0x4a,&DAT_000261e0,0x23650);
    }
    local_10 = DAT_000292b8;
    local_18 = CONCAT22(local_18._2_2_,0x19fe);
    uVar2 = DAT_00029c60;
    psVar1 = (short *)(**(code **)(DAT_000292c0 + 0x88))(DAT_00029c60,0x19fd,&local_18,1,0);
    if ((-1 < (longlong)psVar1) && (psVar1 = local_10, *local_10 != 0)) {
      psVar1 = (short *)FUN_0001d23c(uVar2,param_1);
      if (((longlong)psVar1 < 0) || (psVar1 = DAT_000292b8, uVar3 = 1, DAT_000292b8[0x24] != 0)) {
        uVar3 = 0;
      }
      return CONCAT71((int7)((ulonglong)psVar1 >> 8),uVar3);
    }
  }
LAB_00005772:
  return (ulonglong)psVar1 & 0xffffffffffffff00;
}


// ==== FUN_00005784 @ 00005784

void FUN_00005784(longlong param_1,byte param_2,byte param_3)

{
  word *pwVar1;
  char cVar2;
  longlong lVar3;
  ulonglong uVar4;
  undefined2 uVar6;
  word *pwVar7;
  byte bVar8;
  undefined *puVar9;
  ushort uVar10;
  char local_res10 [8];
  ushort local_res18 [4];
  word *local_res20;
  word *local_e8;
  word *local_e0;
  longlong local_d8;
  undefined8 local_d0 [2];
  undefined8 local_c0;
  undefined4 local_b8 [10];
  undefined2 local_90;
  undefined2 local_68;
  undefined8 uVar5;
  
  local_res20 = (word *)0x0;
  local_e0 = (word *)0x0;
  uVar5 = 0;
  local_d8 = 0;
  FUN_0002337e((undefined4 *)&DAT_00029ad0,400,0);
  local_res10[0] = '\x01';
  uVar10 = 0;
  local_res18[0] = 0;
  uVar6 = 0x19ca;
  if ((param_2 & 8) == 0) {
    uVar6 = 0x19c9;
  }
  FUN_00005fa4(param_1,uVar6,uVar5,0x297b0);
  FUN_00005fa4(param_1,0x19ed,uVar5,0x29940);
  puVar9 = &DAT_00029940;
  FUN_0001c0f8(&DAT_00029ad0,400,&DAT_00029940,(ulonglong)(&PTR_DAT_00025660)[param_3]);
  pwVar7 = (word *)CONCAT71((int7)((ulonglong)puVar9 >> 8),3);
  puVar9 = &DAT_00029ad0;
  (**(code **)(DAT_000292c0 + 0x20))(&DAT_000297b0,&DAT_00029ad0,pwVar7,local_res10);
  local_e8 = (word *)0x0;
  if (local_res10[0] == '\0') {
    lVar3 = FUN_00020f58((longlong)(&PTR_DAT_000256a0)[param_3],puVar9,(longlong)pwVar7,&local_res20
                         ,&local_e8);
LAB_00005aca:
    pwVar7 = local_res20;
    if (-1 < lVar3) {
      if (local_res20 != (word *)0x0) {
        if (local_res10[0] == '\x01') {
          FUN_00005fa4(param_1,0x19ee,local_res20,0x29940);
          lVar3 = local_d8;
          FUN_0001c0f8(&DAT_00029ad0,400,&DAT_00029940,(ulonglong)(&PTR_DAT_00025660)[param_3]);
          (**(code **)(DAT_000292c0 + 0x20))(&DAT_000297b0,&DAT_00029ad0,3,local_res10,lVar3);
        }
        pwVar7 = local_res20;
        if (local_res10[0] == '\0') {
          lVar3 = FUN_00004618(param_3,(ushort)param_2,(longlong)local_res20,(longlong)local_e8);
        }
        else {
          lVar3 = -0x7fffffffffffffeb;
        }
      }
      uVar6 = 0x19f0;
      if (-1 < lVar3) goto LAB_00005b72;
    }
  }
  else {
    bVar8 = (param_3 < 4) + 2;
    if (DAT_000292c0 != 0) {
      pwVar7 = (word *)&local_d8;
      lVar3 = FUN_00006518('\x01',&local_c0,(undefined8 *)pwVar7,&local_res20,&local_e8);
      if (-1 < lVar3) {
        if (local_res20 == (word *)0x0) goto LAB_00005aca;
        FUN_0002337e(local_b8,0x78,0);
        local_b8[0]._0_2_ = 0x19db;
        pwVar7 = (word *)0x0;
        local_90 = 0x19dc;
        local_68 = 0x19dd;
        lVar3 = (**(code **)(DAT_000292c0 + 0x68))
                          (DAT_00029c60,0x19da,0,local_b8,(ushort)bVar8,local_res18);
        if (-1 < lVar3) {
          if (local_res18[0] == 2) {
            uVar4 = FUN_00003da8((short *)local_res20,(ulonglong)local_e8);
            if ((char)uVar4 == '\0') goto LAB_00005b6d;
            (**(code **)(DAT_00029498 + 0x48))(local_res20);
            local_res20 = (word *)&DAT_00029298;
            local_e8 = IMAGE_DOS_HEADER_00000000.e_res_4_ + 2;
            local_res18[0] = 0;
          }
          if (local_res18[0] == 0) {
            uVar10 = 0x54;
          }
          if (local_e8 == (word *)0x0) {
            lVar3 = -0x7fffffffffffffe6;
          }
          else {
            lVar3 = FUN_00022fc0((longlong *)local_res20,(ulonglong)local_e8,(longlong *)0x0,
                                 (longlong *)0x0);
          }
          if (-1 < lVar3) {
            uVar10 = 0x28;
            local_res18[0] = (ushort)bVar8;
          }
          pwVar7 = (word *)&local_e0;
          pwVar1 = (word *)((ulonglong)uVar10 + (longlong)local_e8);
          lVar3 = (**(code **)(DAT_00029498 + 0x40))(4,pwVar1);
          if (-1 < lVar3) {
            pwVar7 = pwVar1;
            FUN_0002337e((undefined4 *)local_e0,(ulonglong)pwVar1,0);
            if (local_res18[0] == 0) {
              if (DAT_000292c0 == 0) {
                cVar2 = '\0';
              }
              else {
                uVar5 = FUN_0000568c(local_d0);
                cVar2 = (char)uVar5;
              }
              if (cVar2 == '\0') {
                FUN_000233d0(local_d0,&DAT_00023650,0x10);
              }
              pwVar7 = local_e8;
              lVar3 = FUN_00022e14((undefined8 *)local_e0,local_res20,(ulonglong)local_e8,local_d0,
                                   param_2);
              if (lVar3 < 0) goto LAB_00005b6d;
            }
            else if (local_res18[0] == bVar8) {
              FUN_00022d6c((undefined8 *)local_e0,CONCAT71((int7)((ulonglong)pwVar7 >> 8),param_2));
            }
            lVar3 = 0;
            FUN_000233d0((undefined8 *)((longlong)local_e0 + (ulonglong)uVar10),
                         (undefined8 *)local_res20,(ulonglong)local_e8);
            if (local_res20 != (word *)&DAT_00029298) {
              (**(code **)(DAT_00029498 + 0x48))();
            }
            local_res20 = local_e0;
            local_e8 = pwVar1;
            goto LAB_00005aca;
          }
        }
      }
    }
  }
LAB_00005b6d:
  uVar6 = 0x19ef;
LAB_00005b72:
  FUN_00005fa4(param_1,uVar6,pwVar7,0x29940);
  (**(code **)(DAT_000292c0 + 0x20))(&DAT_000297b0,&DAT_00029940,1,0);
  FUN_00003868();
  if (local_e0 != local_res20) {
    (**(code **)(DAT_00029498 + 0x48))(local_e0);
  }
  if (local_res20 != (word *)0x0) {
    (**(code **)(DAT_00029498 + 0x48))();
  }
  if (local_d8 != 0) {
    (**(code **)(DAT_00029498 + 0x48))();
  }
  return;
}


// ==== FUN_00005ee4 @ 00005ee4

void FUN_00005ee4(short *param_1,short *param_2)

{
  short sVar1;
  short *psVar2;
  longlong lVar3;
  
  lVar3 = 0;
  sVar1 = *param_1;
  psVar2 = param_1;
  while (sVar1 != 0) {
    psVar2 = psVar2 + 1;
    lVar3 = lVar3 + 1;
    sVar1 = *psVar2;
  }
  lVar3 = lVar3 * 2 - (longlong)param_2;
  do {
    sVar1 = *param_2;
    *(short *)(lVar3 + (longlong)param_1 + (longlong)param_2) = sVar1;
    param_2 = param_2 + 1;
  } while (sVar1 != 0);
  return;
}


// ==== FUN_00005f1c @ 00005f1c

short * FUN_00005f1c(char *param_1)

{
  char cVar1;
  short sVar2;
  longlong lVar3;
  longlong lVar4;
  short *local_res8;
  
  lVar4 = 0;
  if (param_1 == (char *)0x0) {
    local_res8 = (short *)0x0;
  }
  else {
    cVar1 = *param_1;
    lVar3 = lVar4;
    while (cVar1 != '\0') {
      lVar3 = lVar3 + 1;
      cVar1 = param_1[lVar3];
    }
    (**(code **)(DAT_00029498 + 0x40))(4,lVar3 * 2 + 2,&local_res8);
    if (local_res8 != (short *)0x0) {
      sVar2 = (short)*param_1;
      *local_res8 = sVar2;
      while (sVar2 != 0) {
        lVar4 = lVar4 + 2;
        param_1 = param_1 + 1;
        sVar2 = (short)*param_1;
        *(short *)(lVar4 + (longlong)local_res8) = sVar2;
      }
    }
  }
  return local_res8;
}


// ==== FUN_00005fa4 @ 00005fa4

void FUN_00005fa4(longlong param_1,undefined2 param_2,undefined8 param_3,longlong param_4)

{
  short sVar1;
  longlong lVar2;
  short *psVar3;
  undefined8 local_18 [2];
  
  if (param_4 != 0) {
    local_18[0] = 400;
    lVar2 = FUN_0001e7c4(param_1,param_2,local_18,param_4);
    if (lVar2 < 0) {
      psVar3 = &DAT_00026240;
      do {
        sVar1 = *psVar3;
        *(short *)(param_4 + -0x26240 + (longlong)psVar3) = sVar1;
        psVar3 = psVar3 + 1;
      } while (sVar1 != 0);
    }
  }
  return;
}


// ==== FUN_00005ff4 @ 00005ff4

ulonglong FUN_00005ff4(ulonglong param_1,undefined8 param_2)

{
  undefined8 uVar1;
  longlong lVar2;
  char *pcVar3;
  char *pcVar4;
  ulonglong local_res8;
  undefined8 local_res18 [2];
  
  uVar1 = DAT_00029c60;
  local_res18[0] = 0;
  local_res8 = param_1 & 0xffffffffffff0000;
  if ((DAT_000292e0 != (undefined8 *)0x0) ||
     (lVar2 = (**(code **)(DAT_00029498 + 0x140))(&DAT_000237c0,0,&DAT_000292e0), -1 < lVar2)) {
    pcVar4 = DAT_000292d8;
    pcVar3 = DAT_000292d8;
    if (DAT_000292d8 == (char *)0x0) {
      lVar2 = (*(code *)DAT_000292e0[3])(DAT_000292e0,uVar1,0,local_res18);
      if (lVar2 == -0x7ffffffffffffffb) {
        lVar2 = (**(code **)(DAT_00029498 + 0x40))(4,local_res18[0],&DAT_000292d8);
        if (lVar2 < 0) {
          return 0;
        }
        lVar2 = (*(code *)DAT_000292e0[3])(DAT_000292e0,uVar1,DAT_000292d8,local_res18);
      }
      if (lVar2 < 0) {
        return 0;
      }
      pcVar4 = DAT_000292d8;
      pcVar3 = DAT_000292d8;
      if (DAT_000292d8 == (char *)0x0) {
        return 0;
      }
    }
    do {
      for (; *pcVar4 != ';'; pcVar4 = pcVar4 + 1) {
        if (*pcVar4 == '\0') {
LAB_00006148:
          if ((short)local_res8 == 0) {
            lVar2 = (*(code *)*DAT_000292e0)(DAT_000292e0,uVar1,&local_res8,pcVar3,0,param_2,0);
          }
          else {
            lVar2 = (*(code *)DAT_000292e0[2])
                              (DAT_000292e0,uVar1,local_res8 & 0xffff,pcVar3,param_2,0);
          }
          if (-1 < lVar2) {
            return local_res8 & 0xffff;
          }
          return 0;
        }
      }
      if (*pcVar4 == '\0') goto LAB_00006148;
      *pcVar4 = '\0';
      if ((short)local_res8 == 0) {
        lVar2 = (*(code *)*DAT_000292e0)(DAT_000292e0,uVar1,&local_res8,pcVar3,0,param_2,0);
      }
      else {
        lVar2 = (*(code *)DAT_000292e0[2])(DAT_000292e0,uVar1,local_res8 & 0xffff,pcVar3,param_2,0);
      }
      *pcVar4 = ';';
      pcVar4 = pcVar4 + 1;
      pcVar3 = pcVar4;
    } while (-1 < lVar2);
  }
  return 0;
}


// ==== FUN_0000619c @ 0000619c

longlong FUN_0000619c(undefined8 param_1,longlong param_2)

{
  longlong local_res18 [2];
  
  local_res18[0] = 0;
  (**(code **)(DAT_00029498 + 0x40))(4,param_1,local_res18);
  if ((local_res18[0] != 0) && (param_2 != 0)) {
    (**(code **)(DAT_00029498 + 0x160))(local_res18[0],param_2,param_1);
  }
  return local_res18[0];
}


// ==== FUN_00006200 @ 00006200

void FUN_00006200(longlong *param_1,ulonglong *param_2)

{
  ulonglong uVar1;
  longlong lVar2;
  
  uVar1 = 0;
  if (*param_2 != 0) {
    lVar2 = 0;
    do {
      (**(code **)(DAT_00029498 + 0x48))(*(undefined8 *)(*param_1 + 0x10 + lVar2));
      uVar1 = uVar1 + 1;
      lVar2 = lVar2 + 0x20;
    } while (uVar1 < *param_2);
  }
  if (param_1 != (longlong *)0x0) {
    if ((*param_1 != 0) && (*param_2 != 0)) {
      (**(code **)(DAT_00029498 + 0x48))();
    }
    *param_1 = 0;
  }
  *param_2 = 0;
  return;
}


// ==== FUN_0000627c @ 0000627c

void FUN_0000627c(longlong *param_1,ulonglong *param_2,longlong param_3)

{
  short *psVar1;
  ulonglong uVar2;
  short sVar3;
  longlong *plVar4;
  longlong *plVar5;
  short *psVar6;
  undefined4 *puVar7;
  undefined4 *puVar8;
  ulonglong uVar9;
  char *pcVar10;
  longlong lVar11;
  ulonglong uVar12;
  wchar_t *pwVar13;
  
  psVar1 = (short *)(param_3 + 0x50);
  uVar12 = 0;
  lVar11 = 0;
  sVar3 = *psVar1;
  psVar6 = psVar1;
  while (sVar3 != 0) {
    psVar6 = psVar6 + 1;
    lVar11 = lVar11 + 1;
    sVar3 = *psVar6;
  }
  *param_2 = *param_2 + 1;
  uVar2 = lVar11 * 2 + 6;
  puVar7 = (undefined4 *)FUN_0000619c(*param_2 << 5,0);
  if (puVar7 != (undefined4 *)0x0) {
    FUN_0002337e(puVar7,*param_2 << 5,0);
    plVar4 = (longlong *)*param_1;
    if (plVar4 != (longlong *)0x0) {
      if (1 < *param_2) {
        uVar12 = 1;
        uVar9 = *param_2 - 1;
        plVar5 = plVar4;
        if (1 < uVar9) {
          do {
            if (*plVar5 != plVar5[4]) break;
            uVar12 = uVar12 + 1;
            plVar5 = plVar5 + 4;
          } while (uVar12 < uVar9);
        }
      }
      (**(code **)(DAT_00029498 + 0x160))(puVar7,plVar4,uVar12 * 0x20);
      (**(code **)(DAT_00029498 + 0x160))(puVar7 + uVar12 * 8 + 8,*param_1 + uVar12 * 0x20);
      (**(code **)(DAT_00029498 + 0x48))(*param_1);
    }
    lVar11 = *(longlong *)(puVar7 + uVar12 * 8 + 4);
    *(ulonglong *)(puVar7 + uVar12 * 8) = (ulonglong)(*(uint *)(param_3 + 0x48) & 0x10);
    *(undefined8 *)(puVar7 + uVar12 * 8 + 2) = *(undefined8 *)(param_3 + 8);
    puVar8 = (undefined4 *)FUN_0000619c(uVar2,lVar11);
    *(undefined4 **)(puVar7 + uVar12 * 8 + 4) = puVar8;
    if (puVar8 != (undefined4 *)0x0) {
      FUN_0002337e(puVar8,uVar2,0);
      pwVar13 = u_<_s>_00026250;
      pcVar10 = *(char **)(puVar7 + uVar12 * 8 + 4);
      if (*(longlong *)(puVar7 + uVar12 * 8) != 0x10) {
        pwVar13 = (wchar_t *)&DAT_00025b68;
      }
      FUN_0001c0f8(pcVar10,uVar2,(byte *)pwVar13,(ulonglong)psVar1);
      uVar9 = FUN_00005ff4((ulonglong)pcVar10,*(undefined8 *)(puVar7 + uVar12 * 8 + 4));
      *(short *)(puVar7 + uVar12 * 8 + 6) = (short)uVar9;
      FUN_0002337e(*(undefined4 **)(puVar7 + uVar12 * 8 + 4),uVar2,0);
      FUN_0001c0f8(*(char **)(puVar7 + uVar12 * 8 + 4),uVar2,&DAT_00025b68,(ulonglong)psVar1);
    }
    *param_1 = (longlong)puVar7;
  }
  return;
}


// ==== FUN_00006440 @ 00006440

void FUN_00006440(short *param_1,short *param_2,short param_3)

{
  short sVar1;
  longlong lVar2;
  longlong lVar3;
  short *psVar4;
  short *psVar5;
  short *psVar6;
  
  lVar2 = 0;
  psVar6 = param_1;
  if (*param_1 != 0) {
    do {
      psVar6 = psVar6 + 1;
      lVar2 = lVar2 + 1;
    } while (*psVar6 != 0);
    if (lVar2 != 0) {
      if (param_3 == 0) {
        psVar4 = &DAT_0002625c;
        for (psVar6 = param_2; (*psVar6 != 0 && (*psVar6 == *psVar4)); psVar6 = psVar6 + 1) {
          psVar4 = psVar4 + 1;
        }
        lVar2 = 0;
        psVar5 = param_1;
        if (*psVar6 == *psVar4) {
          do {
            lVar3 = lVar2;
            psVar5 = psVar5 + 1;
            lVar2 = lVar3 + 1;
          } while (*psVar5 != 0);
          if (lVar2 != 0) {
            psVar6 = param_1 + lVar3;
            do {
              if (*psVar6 == 0x5c) break;
              psVar6 = psVar6 + -1;
              lVar2 = lVar2 + -1;
            } while (lVar2 != 0);
            if (lVar2 != 0) {
              param_1[lVar2 + -1] = 0;
              return;
            }
          }
          *param_1 = 0;
          return;
        }
      }
      FUN_00005ee4(param_1,(short *)&DAT_00026264);
      FUN_00005ee4(param_1,param_2);
      return;
    }
  }
  lVar2 = (longlong)param_1 - (longlong)param_2;
  do {
    sVar1 = *param_2;
    *(short *)(lVar2 + (longlong)param_2) = sVar1;
    param_2 = param_2 + 1;
  } while (sVar1 != 0);
  return;
}


// ==== FUN_00006518 @ 00006518

longlong FUN_00006518(char param_1,undefined8 *param_2,undefined8 *param_3,undefined8 *param_4,
                     undefined8 *param_5)

{
  longlong lVar1;
  undefined4 *puVar2;
  short *psVar3;
  ulonglong uVar4;
  char *pcVar5;
  ulonglong uVar6;
  undefined4 *puVar7;
  undefined8 uVar8;
  bool bVar9;
  ushort local_78 [4];
  ulonglong local_70;
  longlong local_68;
  char *local_60;
  byte *local_58 [3];
  
  local_70 = 0;
  local_68 = 0;
  local_78[0] = 0;
  local_58[0] = (byte *)0x0;
  bVar9 = false;
  if (param_5 == (undefined8 *)0x0) {
    lVar1 = -0x7ffffffffffffffe;
  }
  else {
    uVar8 = 0;
    lVar1 = (**(code **)(DAT_00029498 + 0x138))(2,&DAT_000237b0,0,&local_70,&local_68);
    if (lVar1 < 0) {
      FUN_00005fa4(DAT_00029c60,0x19f9,uVar8,0x297b0);
      FUN_00005fa4(DAT_00029c60,0x19fa,uVar8,0x29940);
      (**(code **)(DAT_000292c0 + 0x20))(&DAT_000297b0,&DAT_00029940,1);
    }
    else {
      puVar2 = (undefined4 *)FUN_0000619c(local_70 * 0x28,0);
      if (puVar2 != (undefined4 *)0x0) {
        FUN_0002337e(puVar2,local_70 * 0x28,0);
        uVar6 = 0;
        puVar7 = puVar2;
        if (local_70 != 0) {
          do {
            lVar1 = (**(code **)(DAT_00029498 + 0x98))
                              (*(undefined8 *)(local_68 + uVar6 * 8),&DAT_00023690,local_58);
            if (lVar1 < 0) {
              *(undefined2 *)puVar7 = 0;
              *(undefined1 *)(puVar7 + 8) = 2;
            }
            else {
              local_60 = (char *)0x0;
              FUN_0001ee4c(local_58[0],&local_60);
              pcVar5 = local_60;
              psVar3 = FUN_00005f1c(local_60);
              uVar4 = FUN_00005ff4((ulonglong)pcVar5,psVar3);
              *(short *)puVar7 = (short)uVar4;
              lVar1 = DAT_00029498;
              *(undefined1 *)(puVar7 + 8) = 0;
              (**(code **)(lVar1 + 0x48))(psVar3);
              (**(code **)(DAT_00029498 + 0x48))(local_60);
            }
            uVar6 = uVar6 + 1;
            puVar7 = puVar7 + 10;
          } while (uVar6 < local_70);
        }
        local_78[0] = 0;
        lVar1 = (**(code **)(DAT_000292c0 + 0x68))
                          (DAT_00029c60,0x19c5,0,puVar2,local_70 & 0xffff,local_78);
        bVar9 = -1 < lVar1;
        (**(code **)(DAT_00029498 + 0x48))(puVar2);
      }
      uVar8 = *(undefined8 *)(local_68 + (ulonglong)local_78[0] * 8);
      *param_2 = uVar8;
      *param_5 = 0;
      if (param_1 != '\0') {
        lVar1 = FUN_0000678c(uVar8,bVar9,param_3,param_4,param_5);
      }
    }
    if (local_68 != 0) {
      (**(code **)(DAT_00029498 + 0x48))();
    }
  }
  return lVar1;
}


// ==== FUN_0000678c @ 0000678c

undefined8
FUN_0000678c(undefined8 param_1,char param_2,undefined8 *param_3,undefined8 *param_4,
            undefined8 *param_5)

{
  undefined2 uVar1;
  short sVar2;
  ulonglong uVar3;
  longlong lVar4;
  undefined8 uVar5;
  undefined8 *puVar6;
  undefined8 *puVar7;
  undefined4 *puVar8;
  undefined4 *puVar9;
  undefined2 *puVar10;
  longlong lVar11;
  short *psVar12;
  ulonglong uVar13;
  undefined8 *puVar14;
  short *psVar15;
  ushort local_158 [4];
  ulonglong local_150;
  longlong local_148;
  longlong local_140;
  ulonglong local_138;
  longlong local_130;
  longlong local_128;
  short local_118 [120];
  
  local_128 = 0;
  local_140 = 0;
  local_130 = 0;
  local_138 = 0;
  local_148 = 0;
  if (DAT_000292c0 == 0) {
    uVar5 = 0x8000000000000003;
  }
  else if (param_2 == '\x01') {
    puVar6 = (undefined8 *)(**(code **)(DAT_00029498 + 0x98))(param_1,&DAT_000237b0);
    if (-1 < (longlong)puVar6) {
      puVar6 = (undefined8 *)(**(code **)(local_128 + 8))(local_128,&local_148);
    }
    FUN_00006200(&local_130,&local_138);
    do {
      if (((longlong)puVar6 < 0) || (local_148 == 0)) {
        lVar11 = 0;
        psVar12 = local_118;
        while (local_118[0] != 0) {
          psVar12 = psVar12 + 1;
          lVar11 = lVar11 + 1;
          local_118[0] = *psVar12;
        }
        uVar5 = (**(code **)(DAT_00029498 + 0x40))(4,lVar11 * 2 + 2,param_3);
        psVar15 = (short *)*param_3;
        psVar12 = local_118;
        do {
          sVar2 = *psVar12;
          psVar12 = psVar12 + 1;
          *psVar15 = sVar2;
          psVar15 = psVar15 + 1;
        } while (sVar2 != 0);
        return uVar5;
      }
      puVar14 = (undefined8 *)0x0;
      local_158[0] = 0;
      FUN_0002337e((undefined4 *)local_118,0xf0,0);
      lVar11 = local_148;
      local_150 = 1;
      puVar6 = (undefined8 *)0x0;
      do {
        if ((longlong)puVar6 < 0) break;
        puVar14 = (undefined8 *)0x0;
        local_150 = 0;
        puVar6 = (undefined8 *)(**(code **)(lVar11 + 0x20))(lVar11);
        if (-1 < (longlong)puVar6) break;
        puVar7 = (undefined8 *)0x0;
        if ((puVar6 == (undefined8 *)0x8000000000000005) &&
           (puVar7 = (undefined8 *)FUN_0000619c(local_150,0), puVar7 != (undefined8 *)0x0)) {
          FUN_0002337e((undefined4 *)puVar7,local_150,0);
        }
        puVar14 = puVar7;
        puVar6 = (undefined8 *)(**(code **)(lVar11 + 0x20))(lVar11);
        if ((-1 < (longlong)puVar6) && (local_150 != 0)) {
          puVar14 = puVar7;
          FUN_0000627c(&local_130,&local_138,(longlong)puVar7);
        }
        (**(code **)(DAT_00029498 + 0x48))(puVar7);
      } while (local_150 != 0);
      lVar11 = local_130;
      uVar3 = local_138;
      if (local_138 == 0) {
        puVar6 = (undefined8 *)0x800000000000000e;
      }
      lVar4 = local_148;
      if (-1 < (longlong)puVar6) {
        puVar6 = (undefined8 *)0x0;
        if ((local_138 != 0) && (local_130 != 0)) {
          uVar13 = local_138 * 0x28;
          puVar8 = (undefined4 *)FUN_0000619c(uVar13,0);
          if ((puVar8 != (undefined4 *)0x0) && (FUN_0002337e(puVar8,uVar13,0), uVar3 != 0)) {
            puVar10 = (undefined2 *)(lVar11 + 0x18);
            puVar9 = puVar8;
            uVar13 = uVar3;
            do {
              uVar1 = *puVar10;
              puVar10 = puVar10 + 0x10;
              *(undefined2 *)puVar9 = uVar1;
              puVar9 = puVar9 + 10;
              uVar13 = uVar13 - 1;
            } while (uVar13 != 0);
          }
          puVar14 = (undefined8 *)0x0;
          puVar6 = (undefined8 *)
                   (**(code **)(DAT_000292c0 + 0x68))
                             (DAT_00029c60,0x19c6,0,puVar8,uVar3 & 0xffff,local_158);
        }
        lVar4 = local_148;
        if (-1 < (longlong)puVar6) {
          puVar6 = (undefined8 *)
                   (**(code **)(local_148 + 8))
                             (local_148,&local_140,
                              *(undefined8 *)((ulonglong)local_158[0] * 0x20 + 0x10 + lVar11),1,0);
          (**(code **)(local_148 + 0x10))(local_148);
          puVar14 = (undefined8 *)(ulonglong)local_158[0];
          local_148 = 0;
          FUN_00006440(local_118,*(short **)((longlong)puVar14 * 0x20 + 0x10 + lVar11),local_158[0])
          ;
          lVar4 = local_148;
          if ((-1 < (longlong)puVar6) &&
             (lVar4 = local_140, *(longlong *)((ulonglong)local_158[0] * 0x20 + lVar11) != 0x10)) {
            puVar14 = param_4;
            puVar6 = (undefined8 *)
                     (**(code **)(DAT_00029498 + 0x40))
                               (4,*(undefined8 *)((ulonglong)local_158[0] * 0x20 + 8 + lVar11));
            if (-1 < (longlong)puVar6) {
              *param_5 = *(undefined8 *)((ulonglong)local_158[0] * 0x20 + 8 + lVar11);
              puVar14 = (undefined8 *)*param_4;
              puVar6 = (undefined8 *)(**(code **)(local_140 + 0x20))(local_140,param_5);
            }
            (**(code **)(local_140 + 0x10))(local_140);
            local_140 = 0;
            lVar4 = local_140;
          }
        }
      }
      local_148 = lVar4;
      if (uVar3 == 0) {
        FUN_00005fa4(DAT_00029c60,0x19fb,puVar14,0x297b0);
        FUN_00005fa4(DAT_00029c60,0x19fc,puVar14,0x29940);
        (**(code **)(DAT_000292c0 + 0x20))(&DAT_000297b0,&DAT_00029940,1,0);
      }
      FUN_00006200(&local_130,&local_138);
    } while (puVar6 != (undefined8 *)0x8000000000000015);
    uVar5 = 0x8000000000000015;
  }
  else {
    uVar5 = 0x8000000000000015;
  }
  return uVar5;
}


// ==== FUN_00006bc0 @ 00006bc0

undefined8 FUN_00006bc0(undefined8 param_1,undefined2 param_2)

{
  longlong lVar1;
  longlong local_res18;
  undefined8 local_res20;
  undefined8 local_28;
  undefined8 local_20;
  
  local_res20 = 0;
  local_28 = 0;
  local_res18 = 0;
  local_20 = 0;
  if ((DAT_00029320 == 0) &&
     (lVar1 = (**(code **)(DAT_00029498 + 0x140))(&DAT_000237c0,0), lVar1 < 0)) {
    return 0;
  }
  lVar1 = FUN_0001d808(u_PlatformLang_00025c88,&DAT_00024230,0,&local_20,&local_res18);
  if (-1 < lVar1) {
    lVar1 = (**(code **)(DAT_00029320 + 8))
                      (DAT_00029320,local_res18,param_1,param_2,local_res20,&local_28,0);
    if ((lVar1 == -0x7ffffffffffffffb) &&
       (lVar1 = (**(code **)(DAT_00029498 + 0x40))(4,local_28,&local_res20), -1 < lVar1)) {
      lVar1 = (**(code **)(DAT_00029320 + 8))
                        (DAT_00029320,local_res18,param_1,param_2,local_res20,&local_28,0);
    }
    (**(code **)(DAT_00029498 + 0x48))(local_res18);
  }
  if (lVar1 < 0) {
    local_res20 = 0;
  }
  return local_res20;
}


// ==== FUN_00006d10 @ 00006d10

/* WARNING: Type propagation algorithm not settling */

ulonglong FUN_00006d10(void)

{
  longlong lVar1;
  ulonglong uVar2;
  ulonglong uVar3;
  ulonglong uVar4;
  ulonglong uVar5;
  longlong local_res8 [2];
  
  uVar3 = 0;
  local_res8[0] = 0;
  lVar1 = (**(code **)(DAT_00029498 + 0x140))(&DAT_00024208,0,local_res8);
  if (lVar1 < 0) {
    uVar2 = 0;
  }
  else {
    DAT_00029318 = **(ushort **)(local_res8[0] + 0x48);
    uVar2 = (ulonglong)DAT_00029318;
    DAT_00029300 = **(longlong **)(local_res8[0] + 0x50);
    uVar4 = uVar3;
    uVar5 = uVar2;
    DAT_0002b358 = DAT_00029318;
    if (DAT_00029318 != 0) {
      do {
        if (uVar3 + DAT_00029300 != 0) {
          lVar1 = (**(code **)(DAT_00029498 + 0x98))
                            (*(undefined8 *)(uVar3 + DAT_00029300 + 0x38),&DAT_00024208,
                             local_res8 + 1);
          uVar2 = (ulonglong)DAT_0002b358;
          uVar5 = (ulonglong)DAT_00029318;
          if (lVar1 < 0) {
            local_res8[1] = 0;
            DAT_0002b358 = DAT_0002b358 - 1;
            uVar2 = (ulonglong)DAT_0002b358;
          }
        }
        uVar4 = uVar4 + 1;
        uVar3 = uVar3 + 0x40;
      } while (uVar4 < uVar5);
    }
  }
  return uVar2;
}


// ==== FUN_00006e00 @ 00006e00

longlong FUN_00006e00(ulonglong param_1)

{
  ulonglong uVar1;
  longlong lVar2;
  
  if (((DAT_0002b358 == 0) || (DAT_00029318 == 0)) || (DAT_00029300 == 0)) {
    uVar1 = FUN_00006d10();
    DAT_0002b358 = (short)uVar1;
  }
  if (((DAT_0002b358 == 0) || (DAT_00029300 == 0)) || (DAT_00029318 <= param_1)) {
    lVar2 = 0;
  }
  else {
    lVar2 = DAT_00029300 + param_1 * 0x40;
  }
  return lVar2;
}


// ==== FUN_00006fb4 @ 00006fb4

void FUN_00006fb4(void)

{
  longlong lVar1;
  ulonglong uVar2;
  ulonglong uVar3;
  short sVar4;
  
  FUN_00006e00(0);
  uVar3 = 0;
  if (DAT_000292f8 == (short *)0x0) {
    lVar1 = (**(code **)(DAT_00029498 + 0x40))(4,0x356,&DAT_000292f8);
    if (lVar1 < 0) {
      return;
    }
    if (DAT_000292f8 == (short *)0x0) {
      return;
    }
  }
  sVar4 = DAT_0002b358;
  *DAT_000292f8 = DAT_0002b358;
  (**(code **)(DAT_000294a0 + 0x58))(u_HDDSecConfig_00026278,&DAT_00024250,2,0x356,DAT_000292f8);
  if (DAT_00029318 != 0) {
    do {
      if (sVar4 == 0) break;
      lVar1 = FUN_00006e00(uVar3);
      if (lVar1 != 0) {
        uVar2 = FUN_00006bc0(*(undefined8 *)(lVar1 + 8),*(undefined2 *)(lVar1 + 0x12));
        FUN_00000680(DAT_00029310,(&DAT_00026298)[uVar3],&DAT_00025b68,uVar2);
        sVar4 = sVar4 + -1;
      }
      uVar3 = uVar3 + 1;
    } while (uVar3 < DAT_00029318);
  }
  if (DAT_00029308 == 0) {
    (**(code **)(DAT_00029498 + 0x170))(0x200,8,&LAB_00006bb8,0,&DAT_00024240,&DAT_00029308);
  }
  return;
}


// ==== FUN_000070f8 @ 000070f8

void FUN_000070f8(longlong param_1,ulonglong param_2)

{
  undefined8 *puVar1;
  ushort uVar2;
  longlong *plVar3;
  longlong lVar4;
  ushort uVar5;
  byte bVar6;
  undefined2 local_res8 [4];
  uint local_res18 [4];
  
  local_res18[0] = 0;
  plVar3 = (longlong *)FUN_00006e00(param_2);
  if (plVar3 != (longlong *)0x0) {
    puVar1 = (undefined8 *)*plVar3;
    local_res8[0] = 0;
    lVar4 = (*(code *)*puVar1)(puVar1,local_res8);
    bVar6 = (byte)local_res8[0];
    if (-1 < lVar4) {
      bVar6 = (byte)local_res8[0] & 1;
    }
    *(ushort *)(param_1 + 2 + param_2 * 2) = (ushort)bVar6;
    local_res8[0] = 0;
    lVar4 = (*(code *)*puVar1)(puVar1,local_res8);
    if (-1 < lVar4) {
      bVar6 = (byte)local_res8[0] >> 1 & 1;
    }
    *(ushort *)(param_1 + 0xe + param_2 * 2) = (ushort)bVar6;
    local_res8[0] = 0;
    lVar4 = (*(code *)*puVar1)(puVar1,local_res8);
    if (-1 < lVar4) {
      bVar6 = (byte)local_res8[0] >> 2 & 1;
    }
    *(ushort *)(param_1 + 0x1a + param_2 * 2) = (ushort)bVar6;
    local_res8[0] = 0;
    lVar4 = (*(code *)*puVar1)(puVar1,local_res8);
    if (-1 < lVar4) {
      bVar6 = (byte)local_res8[0] >> 3 & 1;
    }
    *(ushort *)(param_1 + 0x26 + param_2 * 2) = (ushort)bVar6;
    lVar4 = (*(code *)puVar1[6])(puVar1,local_res18);
    if (-1 < lVar4) {
      uVar2 = (ushort)(local_res18[0] >> 0x10);
      uVar5 = uVar2 >> 1 & 1;
      *(ushort *)(param_1 + 0x32 + param_2 * 2) = uVar5;
      *(ushort *)(param_1 + 0x3e + param_2 * 2) = uVar2 & 1;
      *(undefined2 *)(param_1 + 0x4a + param_2 * 2) = 0;
      if ((((*(short *)(param_1 + 0x1a + param_2 * 2) != 0) && ((local_res18[0] & 0x10000) != 0)) ||
          (*(char *)((longlong)plVar3 + 0x15) != '\0')) || (uVar5 == 0)) {
        *(undefined2 *)(param_1 + 0x4a + param_2 * 2) = 1;
      }
    }
  }
  return;
}


// ==== FUN_00007230 @ 00007230

void FUN_00007230(void)

{
  longlong lVar1;
  ulonglong uVar2;
  byte bVar3;
  bool bVar5;
  ulonglong uVar4;
  
  uVar4 = 0;
  if (DAT_000292f8 == (undefined2 *)0x0) {
    lVar1 = (**(code **)(DAT_00029498 + 0x40))(4,0x356,&DAT_000292f8);
    if (lVar1 < 0) {
      return;
    }
    if (DAT_000292f8 == (undefined2 *)0x0) {
      return;
    }
  }
  uVar2 = FUN_00006d10();
  bVar5 = DAT_00029318 != 0;
  *DAT_000292f8 = (short)uVar2;
  if (bVar5) {
    do {
      FUN_000070f8((longlong)DAT_000292f8,uVar4);
      bVar3 = (char)uVar4 + 1;
      uVar4 = (ulonglong)bVar3;
    } while (bVar3 < DAT_00029318);
  }
  (**(code **)(DAT_000294a0 + 0x58))(u_HDDSecConfig_00026278,&DAT_00024250,2,0x356,DAT_000292f8);
  FUN_0001ebd4(0x356,DAT_000292f8,&DAT_00024250,u_HDDSecConfig_00026278);
  return;
}


// ==== FUN_000072fc @ 000072fc

undefined8 FUN_000072fc(longlong param_1,longlong *param_2,char param_3)

{
  longlong lVar1;
  undefined8 uVar2;
  ulonglong uVar3;
  undefined4 local_38 [12];
  
  FUN_0002337e(local_38,0x21,0);
  uVar3 = 0;
  do {
    *(undefined1 *)((longlong)local_38 + uVar3) = *(undefined1 *)(param_1 + uVar3 * 2);
    if (*(short *)(param_1 + uVar3 * 2) == 0) break;
    uVar3 = uVar3 + 1;
  } while (uVar3 < 0x21);
  lVar1 = (**(code **)(*param_2 + 0x10))(*param_2,param_3 == '\0',local_38);
  if (lVar1 < 0) {
    uVar2 = 0x800000000000000f;
  }
  else {
    (**(code **)(DAT_00029498 + 0x160))((longlong)param_2 + 0x17,local_38,0x21);
    if (param_3 == '\0') {
      *(undefined1 *)((longlong)param_2 + 0x15) = 1;
    }
    uVar2 = 0;
  }
  return uVar2;
}


// ==== FUN_000073b0 @ 000073b0

ulonglong FUN_000073b0(uint param_1,short *param_2,char param_3)

{
  undefined8 *puVar1;
  longlong *plVar2;
  ulonglong uVar3;
  ulonglong uVar4;
  byte bVar5;
  undefined2 local_res18 [4];
  undefined4 local_48 [12];
  
  uVar4 = 0;
  plVar2 = (longlong *)FUN_00006e00((ulonglong)param_1);
  uVar3 = 0;
  if (plVar2 != (longlong *)0x0) {
    puVar1 = (undefined8 *)*plVar2;
    local_res18[0] = 0;
    uVar3 = (*(code *)*puVar1)(puVar1,local_res18);
    if (-1 < (longlong)uVar3) {
      bVar5 = (byte)local_res18[0] >> 2;
      local_res18[0] = 0;
      uVar3 = (*(code *)*puVar1)(puVar1,local_res18);
      if ((-1 < (longlong)uVar3) && ((bVar5 & 1) == 0)) {
        if (*param_2 == 0) {
          uVar3 = (*(code *)puVar1[3])
                            (puVar1,param_3 == '\0',DAT_00029300 + 0x17 + (ulonglong)param_1 * 0x40)
          ;
        }
        else {
          FUN_0002337e(local_48,0x21,0);
          do {
            *(char *)((longlong)local_48 + uVar4) = (char)param_2[uVar4];
            if (param_2[uVar4] == 0) break;
            uVar4 = uVar4 + 1;
          } while (uVar4 < 0x21);
          uVar3 = (*(code *)puVar1[1])(puVar1,param_3 == '\0',local_48,0);
        }
        if (-1 < (longlong)uVar3) {
          return CONCAT71((int7)(uVar3 >> 8),1);
        }
      }
    }
  }
  return uVar3 & 0xffffffffffffff00;
}


// ==== FUN_000074cc @ 000074cc

/* WARNING: Removing unreachable block (ram,0x000074e9) */

void FUN_000074cc(ulonglong *param_1,byte param_2)

{
  byte bVar1;
  ulonglong uVar2;
  ulonglong local_res18 [2];
  
  bVar1 = param_2 & 7;
  if (param_2 != 0) {
    if (param_2 >> 3 != 0) {
      uVar2 = (ulonglong)(param_2 >> 3);
      do {
        FUN_000230d4(local_res18);
        *param_1 = local_res18[0];
        param_1 = param_1 + 1;
        uVar2 = uVar2 - 1;
      } while (uVar2 != 0);
    }
    if (bVar1 != 0) {
      FUN_000230d4(local_res18);
      do {
        *(char *)param_1 = (char)local_res18[0];
        param_1 = (ulonglong *)((longlong)param_1 + 1);
        local_res18[0] = local_res18[0] >> 8;
        bVar1 = bVar1 - 1;
      } while (bVar1 != 0);
    }
  }
  return;
}


// ==== FUN_00007918 @ 00007918

void FUN_00007918(longlong param_1,undefined4 param_2,undefined4 param_3,undefined8 param_4)

{
  undefined8 local_88 [2];
  uint local_78;
  undefined1 local_74;
  undefined4 local_70;
  undefined4 local_64;
  undefined8 local_48;
  undefined8 local_40;
  undefined4 local_38;
  undefined1 local_24;
  uint *local_20;
  undefined8 *local_18;
  
  FUN_00000340(&local_48,0x38);
  FUN_00000340((undefined8 *)&local_78,0x2c);
  FUN_00000340(local_88,0x10);
  local_78 = local_78 & 0xffffff06 | 6;
  local_20 = &local_78;
  local_38 = 0x1000;
  local_18 = local_88;
  local_48 = 5000000;
  local_24 = 0;
  local_74 = 4;
  local_70 = param_2;
  local_64 = param_3;
  local_40 = param_4;
  (**(code **)(param_1 + 8))(param_1,param_2,&local_48,0);
  return;
}


// ==== FUN_00007c50 @ 00007c50

longlong FUN_00007c50(void)

{
  char cVar1;
  longlong lVar2;
  longlong *plVar3;
  longlong lVar4;
  byte local_38 [8];
  longlong local_30;
  longlong local_28;
  undefined4 local_20;
  undefined4 local_1c;
  undefined4 local_18;
  undefined4 local_14;
  
  local_20 = 0xec87d643;
  local_1c = 0x4bb5eba4;
  local_18 = 0x3e3fe5a1;
  local_14 = 0xa90db236;
  local_28 = 0x7d8;
  (**(code **)(DAT_00029498 + 0x40))(4,0x7d8,&local_30);
  plVar3 = &local_28;
  lVar4 = local_30;
  lVar2 = FUN_0001ea50(plVar3,local_30,&local_20,u_Setup_000262c8);
  if (lVar2 < 0) {
    (**(code **)(DAT_00029498 + 0x48))(local_30);
  }
  else {
    FUN_0001ba9c(plVar3,lVar4,0x82,local_38);
    cVar1 = *(char *)(local_30 + 0x7cd);
    if (cVar1 == '\x01') {
      local_38[0] = local_38[0] & 0xfd | 1;
    }
    else if (cVar1 == '\0') {
      local_38[0] = local_38[0] | 3;
    }
    FUN_0001ba3c(CONCAT71((int7)((ulonglong)plVar3 >> 8),cVar1),lVar4,0x82,local_38[0]);
    FUN_0001ebd4(local_28,local_30,&local_20,u_Setup_000262c8);
    lVar2 = 0;
  }
  return lVar2;
}


// ==== FUN_00007d2c @ 00007d2c

ulonglong FUN_00007d2c(ulonglong param_1,undefined8 param_2)

{
  undefined8 uVar1;
  longlong lVar2;
  char *pcVar3;
  char *pcVar4;
  ulonglong local_res8;
  undefined8 local_res18 [2];
  
  uVar1 = DAT_0002a170;
  local_res18[0] = 0;
  local_res8 = param_1 & 0xffffffffffff0000;
  if ((DAT_00029368 != (undefined8 *)0x0) ||
     (lVar2 = (**(code **)(DAT_00029498 + 0x140))(&DAT_000237c0,0,&DAT_00029368), -1 < lVar2)) {
    pcVar4 = DAT_00029348;
    pcVar3 = DAT_00029348;
    if (DAT_00029348 == (char *)0x0) {
      lVar2 = (*(code *)DAT_00029368[3])(DAT_00029368,uVar1,0,local_res18);
      if (lVar2 == -0x7ffffffffffffffb) {
        lVar2 = (**(code **)(DAT_00029498 + 0x40))(4,local_res18[0],&DAT_00029348);
        if (lVar2 < 0) {
          return 0;
        }
        lVar2 = (*(code *)DAT_00029368[3])(DAT_00029368,uVar1,DAT_00029348,local_res18);
      }
      if (lVar2 < 0) {
        return 0;
      }
      pcVar4 = DAT_00029348;
      pcVar3 = DAT_00029348;
      if (DAT_00029348 == (char *)0x0) {
        return 0;
      }
    }
    do {
      for (; *pcVar4 != ';'; pcVar4 = pcVar4 + 1) {
        if (*pcVar4 == '\0') {
LAB_00007e80:
          if ((short)local_res8 == 0) {
            lVar2 = (*(code *)*DAT_00029368)(DAT_00029368,uVar1,&local_res8,pcVar3,0,param_2,0);
          }
          else {
            lVar2 = (*(code *)DAT_00029368[2])
                              (DAT_00029368,uVar1,local_res8 & 0xffff,pcVar3,param_2,0);
          }
          if (-1 < lVar2) {
            return local_res8 & 0xffff;
          }
          return 0;
        }
      }
      if (*pcVar4 == '\0') goto LAB_00007e80;
      *pcVar4 = '\0';
      if ((short)local_res8 == 0) {
        lVar2 = (*(code *)*DAT_00029368)(DAT_00029368,uVar1,&local_res8,pcVar3,0,param_2,0);
      }
      else {
        lVar2 = (*(code *)DAT_00029368[2])(DAT_00029368,uVar1,local_res8 & 0xffff,pcVar3,param_2,0);
      }
      *pcVar4 = ';';
      pcVar4 = pcVar4 + 1;
      pcVar3 = pcVar4;
    } while (-1 < lVar2);
  }
  return 0;
}


// ==== FUN_00007ed4 @ 00007ed4

void FUN_00007ed4(longlong *param_1,ulonglong *param_2,longlong param_3)

{
  short *psVar1;
  ulonglong uVar2;
  short sVar3;
  longlong *plVar4;
  longlong *plVar5;
  short *psVar6;
  undefined4 *puVar7;
  undefined4 *puVar8;
  ulonglong uVar9;
  wchar_t *pwVar10;
  longlong lVar11;
  ulonglong uVar12;
  wchar_t *pwVar13;
  
  psVar1 = (short *)(param_3 + 0x50);
  uVar12 = 0;
  lVar11 = 0;
  sVar3 = *psVar1;
  psVar6 = psVar1;
  while (sVar3 != 0) {
    psVar6 = psVar6 + 1;
    lVar11 = lVar11 + 1;
    sVar3 = *psVar6;
  }
  *param_2 = *param_2 + 1;
  uVar2 = lVar11 * 2 + 6;
  puVar7 = (undefined4 *)FUN_0000619c(*param_2 << 5,0);
  if (puVar7 != (undefined4 *)0x0) {
    FUN_0002337e(puVar7,*param_2 << 5,0);
    plVar4 = (longlong *)*param_1;
    if (plVar4 != (longlong *)0x0) {
      if (1 < *param_2) {
        uVar12 = 1;
        uVar9 = *param_2 - 1;
        plVar5 = plVar4;
        if (1 < uVar9) {
          do {
            if (*plVar5 != plVar5[4]) break;
            uVar12 = uVar12 + 1;
            plVar5 = plVar5 + 4;
          } while (uVar12 < uVar9);
        }
      }
      (**(code **)(DAT_00029498 + 0x160))(puVar7,plVar4,uVar12 * 0x20);
      (**(code **)(DAT_00029498 + 0x160))(puVar7 + uVar12 * 8 + 8,*param_1 + uVar12 * 0x20);
      (**(code **)(DAT_00029498 + 0x48))(*param_1);
    }
    lVar11 = *(longlong *)(puVar7 + uVar12 * 8 + 4);
    *(ulonglong *)(puVar7 + uVar12 * 8) = (ulonglong)(*(uint *)(param_3 + 0x48) & 0x10);
    *(undefined8 *)(puVar7 + uVar12 * 8 + 2) = *(undefined8 *)(param_3 + 8);
    puVar8 = (undefined4 *)FUN_0000619c(uVar2,lVar11);
    *(undefined4 **)(puVar7 + uVar12 * 8 + 4) = puVar8;
    if (puVar8 != (undefined4 *)0x0) {
      FUN_0002337e(puVar8,uVar2,0);
      pwVar13 = u_<_s>_00026250;
      pwVar10 = *(wchar_t **)(puVar7 + uVar12 * 8 + 4);
      if (*(longlong *)(puVar7 + uVar12 * 8) != 0x10) {
        pwVar13 = (wchar_t *)&DAT_00025b68;
      }
      FUN_0001e3b4(pwVar10,uVar2,pwVar13,psVar1);
      uVar9 = FUN_00007d2c((ulonglong)pwVar10,*(undefined8 *)(puVar7 + uVar12 * 8 + 4));
      *(short *)(puVar7 + uVar12 * 8 + 6) = (short)uVar9;
      FUN_0002337e(*(undefined4 **)(puVar7 + uVar12 * 8 + 4),uVar2,0);
      FUN_0001e3b4(*(wchar_t **)(puVar7 + uVar12 * 8 + 4),uVar2,(wchar_t *)&DAT_00025b68,psVar1);
    }
    *param_1 = (longlong)puVar7;
  }
  return;
}


// ==== FUN_00008098 @ 00008098

undefined8
FUN_00008098(undefined8 param_1,char param_2,undefined8 *param_3,undefined8 *param_4,
            undefined8 *param_5)

{
  short sVar1;
  ulonglong uVar2;
  longlong lVar3;
  undefined8 uVar4;
  undefined8 *puVar5;
  undefined8 *puVar6;
  undefined4 *puVar7;
  ushort uVar8;
  longlong lVar9;
  short *psVar10;
  ulonglong uVar11;
  undefined8 *puVar12;
  short *psVar13;
  ushort local_158 [4];
  ulonglong local_150;
  longlong local_148;
  longlong local_140;
  ulonglong local_138;
  longlong local_130;
  longlong local_128;
  short local_118 [120];
  
  local_128 = 0;
  local_140 = 0;
  local_130 = 0;
  local_138 = 0;
  local_158[0] = 0;
  local_148 = 0;
  if (DAT_00029350 == 0) {
    uVar4 = 0x8000000000000003;
  }
  else if (param_2 == '\x01') {
    puVar5 = (undefined8 *)(**(code **)(DAT_00029498 + 0x98))(param_1,&DAT_000237b0);
    if (-1 < (longlong)puVar5) {
      puVar5 = (undefined8 *)(**(code **)(local_128 + 8))(local_128,&local_148);
    }
    FUN_00006200(&local_130,&local_138);
    do {
      if (((longlong)puVar5 < 0) || (local_148 == 0)) {
        lVar9 = 0;
        psVar10 = local_118;
        while (local_118[0] != 0) {
          psVar10 = psVar10 + 1;
          lVar9 = lVar9 + 1;
          local_118[0] = *psVar10;
        }
        uVar4 = (**(code **)(DAT_00029498 + 0x40))(4,lVar9 * 2 + 2,param_3);
        psVar13 = (short *)*param_3;
        psVar10 = local_118;
        do {
          sVar1 = *psVar10;
          psVar10 = psVar10 + 1;
          *psVar13 = sVar1;
          psVar13 = psVar13 + 1;
        } while (sVar1 != 0);
        return uVar4;
      }
      puVar12 = (undefined8 *)0x0;
      local_158[0] = 0;
      FUN_0002337e((undefined4 *)local_118,0xf0,0);
      lVar9 = local_148;
      local_150 = 1;
      puVar5 = (undefined8 *)0x0;
      do {
        if ((longlong)puVar5 < 0) break;
        puVar12 = (undefined8 *)0x0;
        local_150 = 0;
        puVar5 = (undefined8 *)(**(code **)(lVar9 + 0x20))(lVar9);
        if (-1 < (longlong)puVar5) break;
        puVar6 = (undefined8 *)0x0;
        if ((puVar5 == (undefined8 *)0x8000000000000005) &&
           (puVar6 = (undefined8 *)FUN_0000619c(local_150,0), puVar6 != (undefined8 *)0x0)) {
          FUN_0002337e((undefined4 *)puVar6,local_150,0);
        }
        puVar12 = puVar6;
        puVar5 = (undefined8 *)(**(code **)(lVar9 + 0x20))(lVar9);
        if ((-1 < (longlong)puVar5) && (local_150 != 0)) {
          puVar12 = puVar6;
          FUN_00007ed4(&local_130,&local_138,(longlong)puVar6);
        }
        (**(code **)(DAT_00029498 + 0x48))(puVar6);
      } while (local_150 != 0);
      lVar9 = local_130;
      uVar2 = local_138;
      if (local_138 == 0) {
        puVar5 = (undefined8 *)0x800000000000000e;
      }
      lVar3 = local_148;
      if (-1 < (longlong)puVar5) {
        puVar5 = (undefined8 *)0x0;
        if ((local_138 != 0) && (puVar5 = (undefined8 *)0x0, local_130 != 0)) {
          uVar11 = local_138 * 0x28;
          puVar7 = (undefined4 *)FUN_0000619c(uVar11,0);
          if (puVar7 != (undefined4 *)0x0) {
            FUN_0002337e(puVar7,uVar11,0);
            uVar11 = 0;
            uVar8 = 0;
            if (uVar2 != 0) {
              do {
                uVar8 = uVar8 + 1;
                *(undefined2 *)(puVar7 + uVar11 * 10) =
                     *(undefined2 *)(uVar11 * 0x20 + 0x18 + lVar9);
                uVar11 = (ulonglong)uVar8;
              } while (uVar11 < uVar2);
            }
          }
          puVar12 = (undefined8 *)0x0;
          puVar5 = (undefined8 *)
                   (**(code **)(DAT_00029350 + 0x68))
                             (DAT_0002a170,0x19c6,0,puVar7,uVar2 & 0xffff,local_158);
        }
        lVar3 = local_148;
        if (-1 < (longlong)puVar5) {
          puVar5 = (undefined8 *)
                   (**(code **)(local_148 + 8))
                             (local_148,&local_140,
                              *(undefined8 *)((ulonglong)local_158[0] * 0x20 + 0x10 + lVar9),1,0);
          (**(code **)(local_148 + 0x10))();
          puVar12 = (undefined8 *)(ulonglong)local_158[0];
          local_148 = 0;
          FUN_00006440(local_118,*(short **)((longlong)puVar12 * 0x20 + 0x10 + lVar9),local_158[0]);
          lVar3 = local_148;
          if ((-1 < (longlong)puVar5) &&
             (lVar3 = local_140, *(longlong *)((ulonglong)local_158[0] * 0x20 + lVar9) != 0x10)) {
            puVar12 = param_4;
            puVar5 = (undefined8 *)
                     (**(code **)(DAT_00029498 + 0x40))
                               (4,*(undefined8 *)((ulonglong)local_158[0] * 0x20 + 8 + lVar9));
            if (-1 < (longlong)puVar5) {
              *param_5 = *(undefined8 *)((ulonglong)local_158[0] * 0x20 + 8 + lVar9);
              puVar12 = (undefined8 *)*param_4;
              puVar5 = (undefined8 *)(**(code **)(local_140 + 0x20))(local_140,param_5);
            }
            (**(code **)(local_140 + 0x10))();
            local_140 = 0;
            lVar3 = local_140;
          }
        }
      }
      local_148 = lVar3;
      if (uVar2 == 0) {
        FUN_00005fa4(DAT_0002a170,0x19fb,puVar12,0x29cc0);
        FUN_00005fa4(DAT_0002a170,0x19fc,puVar12,0x29e50);
        (**(code **)(DAT_00029350 + 0x20))(&DAT_00029cc0,&DAT_00029e50,1,0);
      }
      FUN_00006200(&local_130,&local_138);
    } while (puVar5 != (undefined8 *)0x8000000000000015);
    uVar4 = 0x8000000000000015;
  }
  else {
    uVar4 = 0x8000000000000015;
  }
  return uVar4;
}


// ==== FUN_000084e8 @ 000084e8

/* WARNING: Removing unreachable block (ram,0x0000864d) */
/* WARNING: Removing unreachable block (ram,0x00008689) */
/* WARNING: Removing unreachable block (ram,0x00008692) */
/* WARNING: Removing unreachable block (ram,0x0000869a) */
/* WARNING: Removing unreachable block (ram,0x000086a2) */
/* WARNING: Removing unreachable block (ram,0x000086b6) */
/* WARNING: Removing unreachable block (ram,0x000086e0) */
/* WARNING: Removing unreachable block (ram,0x000086e7) */
/* WARNING: Removing unreachable block (ram,0x0000873e) */
/* WARNING: Removing unreachable block (ram,0x00008745) */
/* WARNING: Removing unreachable block (ram,0x00008755) */
/* WARNING: Removing unreachable block (ram,0x0000875f) */
/* WARNING: Removing unreachable block (ram,0x00008763) */
/* WARNING: Removing unreachable block (ram,0x0000878a) */
/* WARNING: Removing unreachable block (ram,0x0000878d) */
/* WARNING: Removing unreachable block (ram,0x000087a2) */
/* WARNING: Removing unreachable block (ram,0x000087a7) */
/* WARNING: Removing unreachable block (ram,0x000087c1) */
/* WARNING: Removing unreachable block (ram,0x000087b9) */
/* WARNING: Removing unreachable block (ram,0x000087c7) */
/* WARNING: Removing unreachable block (ram,0x000087e0) */
/* WARNING: Removing unreachable block (ram,0x00008828) */

ulonglong FUN_000084e8(short *param_1,ulonglong param_2)

{
  uint uVar1;
  longlong lVar2;
  longlong lVar3;
  
  lVar2 = 0x5a4d;
  lVar3 = -0x7fffffffffffffeb;
  if (*param_1 == 0x5a4d) {
    uVar1 = *(uint *)(param_1 + 0x1e);
    lVar2 = 0x5a56;
    if ((*(short *)((longlong)param_1 + (ulonglong)uVar1) != 0x5a56) &&
       ((DAT_00029360 != 0 ||
        ((lVar2 = (**(code **)(DAT_00029498 + 0x140))(&DAT_00023640,0,&DAT_00029360), lVar3 = lVar2,
         -1 < lVar2 && (DAT_00029360 != 0)))))) {
      lVar2 = (**(code **)(DAT_00029498 + 0x40))
                        (4,(ulonglong)(ushort)((short *)((longlong)param_1 + (ulonglong)uVar1))[3] *
                           0x28);
      lVar3 = lVar2;
    }
  }
  return CONCAT71((int7)((ulonglong)lVar2 >> 8),(byte)((ulonglong)lVar3 >> 0x3f)) ^ 1;
}


// ==== FUN_00008850 @ 00008850

longlong FUN_00008850(char param_1,undefined8 *param_2,undefined8 *param_3,undefined8 *param_4,
                     undefined8 *param_5)

{
  longlong lVar1;
  undefined4 *puVar2;
  short *psVar3;
  ulonglong uVar4;
  char *pcVar5;
  ulonglong uVar6;
  undefined8 uVar7;
  ushort uVar8;
  bool bVar9;
  ushort local_78 [4];
  ulonglong local_70;
  longlong local_68;
  char *local_60;
  byte *local_58 [3];
  
  local_70 = 0;
  local_68 = 0;
  local_78[0] = 0;
  local_58[0] = (byte *)0x0;
  bVar9 = false;
  if (param_5 == (undefined8 *)0x0) {
    lVar1 = -0x7ffffffffffffffe;
  }
  else {
    uVar7 = 0;
    lVar1 = (**(code **)(DAT_00029498 + 0x138))(2,&DAT_000237b0,0,&local_70,&local_68);
    if (lVar1 < 0) {
      FUN_00005fa4(DAT_0002a170,0x19f9,uVar7,0x29cc0);
      FUN_00005fa4(DAT_0002a170,0x19fa,uVar7,0x29e50);
      (**(code **)(DAT_00029350 + 0x20))(&DAT_00029cc0,&DAT_00029e50,1);
    }
    else {
      puVar2 = (undefined4 *)FUN_0000619c(local_70 * 0x28,0);
      if (puVar2 != (undefined4 *)0x0) {
        FUN_0002337e(puVar2,local_70 * 0x28,0);
        uVar8 = 0;
        if (local_70 != 0) {
          uVar6 = 0;
          do {
            lVar1 = (**(code **)(DAT_00029498 + 0x98))
                              (*(undefined8 *)(local_68 + uVar6 * 8),&DAT_00023690,local_58);
            if (lVar1 < 0) {
              *(undefined2 *)(puVar2 + uVar6 * 10) = 0;
              *(undefined1 *)(puVar2 + uVar6 * 10 + 8) = 2;
            }
            else {
              local_60 = (char *)0x0;
              FUN_0001ee4c(local_58[0],&local_60);
              pcVar5 = local_60;
              psVar3 = FUN_00005f1c(local_60);
              uVar4 = FUN_00007d2c((ulonglong)pcVar5,psVar3);
              *(short *)(puVar2 + uVar6 * 10) = (short)uVar4;
              lVar1 = DAT_00029498;
              *(undefined1 *)(puVar2 + uVar6 * 10 + 8) = 0;
              (**(code **)(lVar1 + 0x48))(psVar3);
              (**(code **)(DAT_00029498 + 0x48))();
            }
            uVar8 = uVar8 + 1;
            uVar6 = (ulonglong)uVar8;
          } while (uVar6 < local_70);
        }
        local_78[0] = 0;
        lVar1 = (**(code **)(DAT_00029350 + 0x68))
                          (DAT_0002a170,0x19c5,0,puVar2,local_70 & 0xffff,local_78);
        bVar9 = -1 < lVar1;
        (**(code **)(DAT_00029498 + 0x48))(puVar2);
      }
      uVar7 = *(undefined8 *)(local_68 + (ulonglong)local_78[0] * 8);
      *param_2 = uVar7;
      *param_5 = 0;
      if (param_1 != '\0') {
        lVar1 = FUN_00008098(uVar7,bVar9,param_3,param_4,param_5);
      }
    }
    if (local_68 != 0) {
      (**(code **)(DAT_00029498 + 0x48))();
    }
  }
  return lVar1;
}


// ==== FUN_00008ad0 @ 00008ad0

void FUN_00008ad0(longlong param_1,byte param_2,undefined8 param_3)

{
  longlong lVar1;
  ulonglong uVar2;
  ushort uVar3;
  ulonglong uVar4;
  undefined8 uVar5;
  undefined8 **ppuVar6;
  undefined8 *puVar7;
  undefined *puVar8;
  char local_res10 [8];
  undefined8 *local_res18;
  undefined8 *local_res20;
  ulonglong local_48 [2];
  
  if (5 < param_2) {
    return;
  }
  local_res18 = (undefined8 *)0x0;
  local_res20 = (undefined8 *)0x0;
  local_res10[0] = '\0';
  FUN_00005fa4(param_1,0x19f4,param_3,0x29cc0);
  if (param_2 == 5) {
    FUN_00005fa4(param_1,0x19f6,param_3,0x29fe0);
    uVar5 = CONCAT71((int7)((ulonglong)param_3 >> 8),1);
  }
  else {
    uVar5 = 0;
    FUN_0002337e((undefined4 *)&DAT_00029fe0,400,0);
    FUN_00005fa4(param_1,0x19f5,uVar5,0x29e50);
    puVar8 = &DAT_00029e50;
    FUN_0001e3b4((wchar_t *)&DAT_00029fe0,400,(wchar_t *)&DAT_00029e50,(&PTR_DAT_00025660)[param_2])
    ;
    uVar5 = CONCAT71((int7)((ulonglong)puVar8 >> 8),3);
  }
  (**(code **)(DAT_00029350 + 0x20))(&DAT_00029cc0,&DAT_00029fe0,uVar5,local_res10);
  if (local_res10[0] == '\0') {
    FUN_00005fa4(param_1,0x19f7,uVar5,0x29e50);
    FUN_0002337e((undefined4 *)&DAT_00029fe0,400,0);
    FUN_0001e3b4((wchar_t *)&DAT_00029fe0,400,(wchar_t *)&DAT_00029e50,(&PTR_DAT_00025660)[param_2])
    ;
    (**(code **)(DAT_00029350 + 0x20))(&DAT_00029cc0,&DAT_00029fe0);
    if (local_res10[0] != '\0') goto LAB_00008d43;
    uVar2 = 0;
    uVar3 = 1;
    puVar7 = (undefined8 *)0x0;
  }
  else {
    ppuVar6 = &local_res20;
    lVar1 = FUN_00009500(param_2,0x19de,ppuVar6,local_48);
    if (lVar1 < 0) goto LAB_00008d43;
    FUN_00005fa4(param_1,0x19f4,ppuVar6,0x29cc0);
    FUN_00005fa4(param_1,0x19f8,ppuVar6,0x29e50);
    FUN_0002337e((undefined4 *)&DAT_00029fe0,400,0);
    FUN_0001e3b4((wchar_t *)&DAT_00029fe0,400,(wchar_t *)&DAT_00029e50,(&PTR_DAT_00025660)[param_2])
    ;
    (**(code **)(DAT_00029350 + 0x20))(&DAT_00029cc0,&DAT_00029fe0,3,local_res10);
    if (local_res10[0] != '\0') goto LAB_00008d43;
    uVar2 = local_48[0] + 0x28;
    lVar1 = (**(code **)(DAT_00029498 + 0x40))(4,uVar2);
    if (lVar1 < 0) goto LAB_00008d43;
    uVar4 = uVar2;
    FUN_0002337e((undefined4 *)local_res18,uVar2,0);
    FUN_00022d6c(local_res18,CONCAT71((int7)(uVar4 >> 8),2));
    FUN_000233d0(local_res18 + 5,local_res20,local_48[0]);
    uVar3 = 3;
    puVar7 = local_res18;
  }
  uVar2 = FUN_00004618(param_2,uVar3,(longlong)puVar7,uVar2);
  if (local_res10[0] == '\0') {
    if (-1 < (longlong)uVar2) {
      FUN_000095e4();
    }
    puVar8 = &DAT_000262d4;
    FUN_0001c0f8(&DAT_00029e50,400,&DAT_000262d4,uVar2);
    FUN_00005fa4(param_1,0x19f4,puVar8,0x29cc0);
    (**(code **)(DAT_00029350 + 0x20))(&DAT_00029cc0,&DAT_00029e50,1,0);
  }
LAB_00008d43:
  if (local_res20 != (undefined8 *)0x0) {
    (**(code **)(DAT_00029498 + 0x48))();
  }
  if (local_res18 != (undefined8 *)0x0) {
    (**(code **)(DAT_00029498 + 0x48))();
  }
  return;
}


// ==== FUN_00008d78 @ 00008d78

void FUN_00008d78(longlong param_1,byte param_2,byte param_3)

{
  ulonglong uVar1;
  ulonglong uVar2;
  ulonglong uVar3;
  longlong lVar4;
  undefined2 uVar5;
  byte bVar6;
  undefined8 uVar7;
  undefined *puVar8;
  ushort uVar9;
  char local_res10 [8];
  byte local_res18;
  ushort local_res20 [4];
  longlong *local_e8;
  ulonglong local_e0;
  longlong *local_d8;
  longlong local_d0;
  ulonglong local_c8;
  undefined8 local_c0;
  undefined4 local_b8 [10];
  undefined2 local_90;
  undefined2 local_68;
  
  local_e8 = (longlong *)0x0;
  local_d8 = (longlong *)0x0;
  local_d0 = 0;
  uVar7 = 0;
  local_res18 = param_3;
  FUN_0002337e((undefined4 *)&DAT_00029fe0,400,0);
  local_res10[0] = '\x01';
  uVar9 = 0;
  local_res20[0] = 0;
  uVar5 = 0x19ca;
  if ((param_2 & 8) == 0) {
    uVar5 = 0x19c9;
  }
  FUN_00005fa4(param_1,uVar5,uVar7,0x29cc0);
  FUN_00005fa4(param_1,0x19ed,uVar7,0x29e50);
  uVar3 = (ulonglong)param_3;
  puVar8 = &DAT_00029e50;
  local_c8 = uVar3;
  FUN_0001e3b4((wchar_t *)&DAT_00029fe0,400,(wchar_t *)&DAT_00029e50,(&PTR_DAT_00025660)[uVar3]);
  lVar4 = CONCAT71((int7)((ulonglong)puVar8 >> 8),3);
  puVar8 = &DAT_00029fe0;
  (**(code **)(DAT_00029350 + 0x20))(&DAT_00029cc0,&DAT_00029fe0,lVar4,local_res10);
  local_e0 = 0;
  if (local_res10[0] == '\0') {
    uVar2 = FUN_00020f58((longlong)(&PTR_DAT_000256a0)[uVar3],puVar8,lVar4,&local_e8,&local_e0);
  }
  else {
    bVar6 = (param_3 < 4) + 2;
    if (DAT_00029350 == 0) {
      uVar2 = 0x8000000000000003;
      goto LAB_0000916a;
    }
    uVar2 = FUN_00008850('\x01',&local_c0,&local_d0,&local_e8,&local_e0);
    if ((longlong)uVar2 < 0) goto LAB_0000916a;
    uVar3 = local_c8;
    param_3 = local_res18;
    if (local_e8 != (longlong *)0x0) {
      FUN_0002337e(local_b8,0x78,0);
      local_b8[0]._0_2_ = 0x19db;
      local_90 = 0x19dc;
      local_68 = 0x19dd;
      uVar2 = (**(code **)(DAT_00029350 + 0x68))
                        (DAT_0002a170,0x19da,0,local_b8,(ushort)bVar6,local_res20);
      if ((longlong)uVar2 < 0) goto LAB_0000916a;
      uVar2 = 0x8000000000000001;
      if (local_res20[0] == 2) {
        uVar3 = FUN_000084e8((short *)local_e8,local_e0);
        if ((char)uVar3 == '\0') goto LAB_0000916a;
        (**(code **)(DAT_00029498 + 0x48))(local_e8);
        local_e8 = (longlong *)&DAT_00029328;
        local_e0 = 0x20;
        local_res20[0] = 0;
      }
      if (local_res20[0] == 0) {
        uVar9 = 0x54;
      }
      if (local_e0 == 0) {
        lVar4 = -0x7fffffffffffffe6;
      }
      else {
        lVar4 = FUN_00022fc0(local_e8,local_e0,(longlong *)0x0,(longlong *)0x0);
      }
      if (-1 < lVar4) {
        uVar9 = 0x28;
        local_res20[0] = (ushort)bVar6;
      }
      uVar1 = uVar9 + local_e0;
      lVar4 = (**(code **)(DAT_00029498 + 0x40))(4,uVar1);
      if (lVar4 < 0) goto LAB_0000916a;
      uVar3 = uVar1;
      FUN_0002337e((undefined4 *)local_d8,uVar1,0);
      if (local_res20[0] == 0) {
        lVar4 = FUN_00022e14(local_d8,local_e8,local_e0,&DAT_00023650,param_2);
        if (lVar4 < 0) {
          (**(code **)(DAT_00029498 + 0x48))(local_d8);
          goto LAB_0000916a;
        }
      }
      else if (local_res20[0] == bVar6) {
        FUN_00022d6c(local_d8,CONCAT71((int7)(uVar3 >> 8),param_2));
      }
      uVar2 = 0;
      FUN_000233d0((undefined8 *)((longlong)local_d8 + (ulonglong)uVar9),local_e8,local_e0);
      if (local_e8 != (longlong *)&DAT_00029328) {
        (**(code **)(DAT_00029498 + 0x48))();
      }
      local_e8 = local_d8;
      uVar3 = local_c8;
      local_e0 = uVar1;
      param_3 = local_res18;
    }
  }
  if ((-1 < (longlong)uVar2) && (local_e8 != (longlong *)0x0)) {
    if (local_res10[0] == '\x01') {
      FUN_00005fa4(param_1,0x19ee,local_e8,0x29e50);
      lVar4 = local_d0;
      FUN_0001e3b4((wchar_t *)&DAT_00029fe0,400,(wchar_t *)&DAT_00029e50,(&PTR_DAT_00025660)[uVar3])
      ;
      (**(code **)(DAT_00029350 + 0x20))(&DAT_00029cc0,&DAT_00029fe0,3,local_res10,lVar4);
    }
    if (local_res10[0] == '\0') {
      uVar2 = FUN_00004618(param_3,(ushort)param_2,(longlong)local_e8,local_e0);
    }
    else {
      uVar2 = 0x8000000000000015;
    }
  }
LAB_0000916a:
  FUN_0001c0f8(&DAT_00029e50,400,&DAT_000262d4,uVar2);
  (**(code **)(DAT_00029350 + 0x20))(&DAT_00029cc0,&DAT_00029e50,1,0);
  FUN_000095e4();
  if (local_e8 != (longlong *)0x0) {
    (**(code **)(DAT_00029498 + 0x48))();
  }
  if (local_d0 != 0) {
    (**(code **)(DAT_00029498 + 0x48))();
  }
  return;
}


// ==== FUN_000091e4 @ 000091e4

/* WARNING: Removing unreachable block (ram,0x00009430) */

undefined8 FUN_000091e4(longlong param_1,ushort param_2)

{
  bool bVar1;
  longlong lVar2;
  undefined *puVar3;
  byte bVar4;
  longlong *plVar5;
  ulonglong uVar6;
  undefined8 local_res18;
  longlong local_res20;
  longlong *local_68;
  longlong local_60;
  longlong local_58;
  longlong local_50;
  undefined8 local_48;
  longlong local_40;
  
  local_58 = 0;
  local_50 = 0;
  bVar1 = true;
  local_68 = (longlong *)0x0;
  if ((param_2 < 7) && (local_res18 = 0, DAT_0002a170 = param_1, DAT_00029350 != 0)) {
    lVar2 = FUN_00008850('\0',&local_48,&local_50,&local_58,&local_res18);
    if (-1 < lVar2) {
      bVar4 = (byte)param_2;
      if (param_2 == 6) {
        bVar4 = 0;
      }
      uVar6 = 0;
      plVar5 = (longlong *)0x0;
      FUN_0002337e((undefined4 *)&DAT_00029fe0,400,0);
      do {
        if ((&PTR_DAT_00025660)[bVar4] == (undefined *)0x0) break;
        puVar3 = &DAT_00023570;
        if (3 < bVar4) {
          puVar3 = &DAT_000234a0;
        }
        plVar5 = (longlong *)0x0;
        local_res18 = 0;
        lVar2 = (**(code **)(DAT_000294a0 + 0x48))
                          ((&PTR_DAT_00025660)[bVar4],puVar3,0,&local_res18,0);
        if (lVar2 == -0x7ffffffffffffffb) {
          (**(code **)(DAT_00029498 + 0x40))(4,local_res18);
          plVar5 = (longlong *)0x0;
          lVar2 = (**(code **)(DAT_000294a0 + 0x48))
                            ((&PTR_DAT_00025660)[bVar4],puVar3,0,&local_res18,0);
          if (-1 < lVar2) {
            plVar5 = &local_40;
            lVar2 = (**(code **)(DAT_00029498 + 0x98))(local_48,&DAT_000237b0);
            if ((-1 < lVar2) &&
               (lVar2 = (**(code **)(local_40 + 8))(local_40,&local_60), -1 < lVar2)) {
              plVar5 = (longlong *)(&PTR_DAT_00025660)[bVar4];
              lVar2 = (**(code **)(local_60 + 8))(local_60,&local_res20,plVar5,0x8000000000000003,0)
              ;
              if (-1 < lVar2) {
                (**(code **)(local_res20 + 0x18))(local_res20);
                plVar5 = (longlong *)(&PTR_DAT_00025660)[bVar4];
                lVar2 = (**(code **)(local_60 + 8))
                                  (local_60,&local_res20,plVar5,0x8000000000000003,0);
                if (-1 < lVar2) {
                  plVar5 = local_68;
                  lVar2 = (**(code **)(local_res20 + 0x28))(local_res20,&local_res18);
                  (**(code **)(local_res20 + 0x10))(local_res20);
                  uVar6 = (ulonglong)(byte)((char)uVar6 + 1);
                  if (-1 < lVar2) goto LAB_0000943a;
                }
              }
            }
            bVar1 = false;
            FUN_00005fa4(param_1,0x19f1,plVar5,0x29cc0);
            plVar5 = (longlong *)CONCAT71((int7)((ulonglong)plVar5 >> 8),1);
            (**(code **)(DAT_00029350 + 0x20))(&DAT_00029cc0,(&PTR_DAT_00025660)[bVar4],plVar5,0);
          }
        }
LAB_0000943a:
        bVar4 = bVar4 + 1;
        if (param_2 != 6) {
          bVar4 = 6;
          break;
        }
      } while (bVar1);
      if ((bVar4 == 6) && (bVar1)) {
        FUN_00005fa4(param_1,0x19f3,plVar5,0x29e50);
        puVar3 = &DAT_00029e50;
        FUN_0001e3b4((wchar_t *)&DAT_00029fe0,400,(wchar_t *)&DAT_00029e50,uVar6);
        FUN_00005fa4(param_1,0x19f2,puVar3,0x29cc0);
        (**(code **)(DAT_00029350 + 0x20))(&DAT_00029cc0,&DAT_00029fe0,1,0);
      }
    }
    if (local_58 != 0) {
      (**(code **)(DAT_00029498 + 0x48))();
    }
    if (local_50 != 0) {
      (**(code **)(DAT_00029498 + 0x48))();
    }
  }
  return 0;
}


// ==== FUN_00009500 @ 00009500

void FUN_00009500(byte param_1,short param_2,undefined8 *param_3,ulonglong *param_4)

{
  longlong lVar1;
  undefined *puVar2;
  
  if (param_1 < 6) {
    *param_4 = 0;
    puVar2 = &DAT_00023570;
    if (3 < param_1) {
      puVar2 = &DAT_000234a0;
    }
    lVar1 = (**(code **)(DAT_000294a0 + 0x48))((&PTR_DAT_00025660)[param_1],puVar2,0,param_4,0);
    if (lVar1 == -0x7ffffffffffffffb) {
      (**(code **)(DAT_00029498 + 0x40))(4,*param_4,param_3);
      lVar1 = (**(code **)(DAT_000294a0 + 0x48))
                        ((&PTR_DAT_00025660)[param_1],puVar2,0,param_4,*param_3);
      if (-1 < lVar1) {
        FUN_00009fec(param_2,(longlong *)*param_3,param_4);
      }
    }
  }
  return;
}


// ==== FUN_000095e4 @ 000095e4

void FUN_000095e4(void)

{
  word *pwVar1;
  char cVar2;
  uint uVar3;
  undefined *puVar4;
  word *pwVar5;
  undefined1 uVar6;
  longlong lVar7;
  longlong lVar8;
  undefined2 uVar9;
  undefined *puVar10;
  longlong *plVar11;
  undefined **ppuVar12;
  word *pwVar13;
  word *pwVar14;
  undefined8 uVar15;
  byte bVar16;
  longlong *plVar17;
  ulonglong uVar18;
  word *local_res8;
  longlong *local_res10;
  longlong *local_res18;
  word *local_res20;
  undefined8 local_58;
  longlong local_50;
  longlong local_48 [2];
  
  bVar16 = 0;
  if (PTR_DAT_00025660 != (undefined *)0x0) {
    lVar8 = 0;
    ppuVar12 = &PTR_DAT_00025660;
    uVar18 = 0;
    do {
      puVar4 = *ppuVar12;
      puVar10 = &DAT_00023570;
      if (3 < bVar16) {
        puVar10 = &DAT_000234a0;
      }
      local_res8 = (word *)0x0;
      local_res20 = (word *)0x0;
      pwVar14 = (word *)0x0;
      (&DAT_00029358)[uVar18] = 0;
      local_58 = 0;
      lVar7 = (**(code **)(DAT_000294a0 + 0x48))(puVar4,puVar10,0,&local_res8,0);
      if (lVar7 == -0x7ffffffffffffffb) {
        local_res10 = (longlong *)0x0;
        (&DAT_00029358)[uVar18] = 1;
        (**(code **)(DAT_00029498 + 0x40))(4,local_res8);
        pwVar14 = (word *)0x0;
        lVar7 = (**(code **)(DAT_000294a0 + 0x48))(*ppuVar12,puVar10,0,&local_res8,local_res10);
        if (-1 < lVar7) {
          if (local_res8 == (word *)0x0) {
            lVar7 = -0x7fffffffffffffe6;
          }
          else {
            pwVar14 = (word *)&local_58;
            lVar7 = FUN_00022fc0(local_res10,(ulonglong)local_res8,(longlong *)pwVar14,
                                 (longlong *)0x0);
          }
          if (-1 < lVar7) {
            local_res18 = (longlong *)0x0;
            (**(code **)(DAT_00029498 + 0x40))(4,local_res8);
            local_res20 = local_res8;
            pwVar14 = (word *)0x0;
            lVar8 = (**(code **)(DAT_000294a0 + 0x48))
                              (*(undefined8 *)((longlong)&PTR_u_dbxDefault_00025620 + lVar8),
                               &DAT_000234a0,0,&local_res20,local_res18);
            pwVar5 = local_res20;
            pwVar13 = local_res8;
            if (-1 < lVar8) {
              lVar8 = 0;
              plVar11 = local_res10;
              pwVar1 = local_res20;
              while (pwVar1 <= pwVar13) {
                pwVar14 = pwVar5;
                lVar7 = FUN_0001edd4(plVar11,local_res18,(ulonglong)pwVar5);
                if (lVar7 == 0) {
                  (&DAT_00029358)[uVar18] = 2;
                  uVar6 = (&DAT_00029358)[uVar18];
                  if (pwVar5 < pwVar13) {
                    uVar6 = 3;
                  }
                  (&DAT_00029358)[uVar18] = uVar6;
                  break;
                }
                uVar3 = *(uint *)(plVar11 + 2);
                if (0x6ffd3 < uVar3 - 0x2d) break;
                lVar8 = lVar8 + (ulonglong)uVar3;
                plVar11 = (longlong *)((longlong)plVar11 + (ulonglong)uVar3);
                pwVar1 = (word *)(lVar8 + (longlong)pwVar5);
              }
            }
            if (local_res18 != (longlong *)0x0) {
              (**(code **)(DAT_00029498 + 0x48))(local_res18);
              pwVar13 = local_res8;
            }
            plVar17 = (longlong *)0x0;
            plVar11 = local_res10;
            lVar8 = DAT_00029360;
            if (pwVar13 != (word *)0x0) {
              do {
                lVar7 = FUN_0001edd4(plVar11,(longlong *)&DAT_00023960,0x10);
                if (lVar7 == 0) {
LAB_0000981b:
                  local_48[0] = (ulonglong)*(uint *)((longlong)plVar11 + 0x14) + 0x2c +
                                (longlong)plVar11;
                  local_50 = (ulonglong)*(uint *)(plVar11 + 3) - 0x10;
                  if (lVar8 == 0) {
                    pwVar14 = (word *)&DAT_00029360;
                    (**(code **)(DAT_00029498 + 0x140))(&DAT_00023640,0);
                    lVar8 = DAT_00029360;
                    pwVar13 = local_res8;
                    if (DAT_00029360 == 0) goto LAB_000098cc;
                  }
                  (**(code **)(lVar8 + 0x10))
                            (lVar8,&DAT_00023510,1,local_48,&local_50,&DAT_00029328);
                  pwVar14 = IMAGE_DOS_HEADER_00000000.e_res_4_ + 2;
                  lVar8 = FUN_0001edd4((longlong *)&DAT_00024298,(longlong *)&DAT_00029328,0x20);
                  if (lVar8 != 0) {
                    pwVar14 = IMAGE_DOS_HEADER_00000000.e_res_4_ + 2;
                    lVar7 = FUN_0001edd4((longlong *)&DAT_00024268,(longlong *)&DAT_00029328,0x20);
                    lVar8 = DAT_00029360;
                    pwVar13 = local_res8;
                    if (lVar7 != 0) goto LAB_000098cc;
                  }
                  (&DAT_00029358)[uVar18] = 4;
                  break;
                }
                pwVar14 = &IMAGE_DOS_HEADER_00000000.e_sp;
                lVar7 = FUN_0001edd4(plVar11,&DAT_00023760,0x10);
                if (lVar7 == 0) goto LAB_0000981b;
LAB_000098cc:
                uVar3 = *(uint *)(plVar11 + 2);
                if (0x6ffb4 < uVar3 - 0x4c) break;
                plVar17 = (longlong *)((longlong)plVar17 + (ulonglong)uVar3);
                plVar11 = (longlong *)((longlong)plVar11 + (ulonglong)uVar3);
              } while (plVar17 < pwVar13);
            }
          }
        }
        if (local_res10 != (longlong *)0x0) {
          (**(code **)(DAT_00029498 + 0x48))();
        }
      }
      cVar2 = (&DAT_00029358)[uVar18];
      if (cVar2 == '\x01') {
        uVar9 = 0x19bd;
      }
      else if (cVar2 == '\x02') {
        uVar9 = 0x19be;
      }
      else if (cVar2 == '\x03') {
        uVar9 = 0x19bf;
      }
      else if (cVar2 == '\x04') {
        uVar9 = 0x19c0;
      }
      else {
        uVar9 = 0x19bc;
      }
      FUN_00005fa4(DAT_0002a170,uVar9,pwVar14,0x29e50);
      uVar15 = 0;
      FUN_0002337e((undefined4 *)&DAT_00029fe0,400,0);
      FUN_00005fa4(DAT_0002a170,(&DAT_000262f8)[uVar18],uVar15,0x29fe0);
      FUN_0001e3b4((wchar_t *)&DAT_00029cc0,400,u__s__5d__5d___s_00026198,&DAT_00029fe0);
      FUN_0001e908(DAT_0002a170,(&DAT_00026268)[uVar18],&DAT_00029cc0);
      bVar16 = bVar16 + 1;
      uVar18 = (ulonglong)bVar16;
      lVar8 = uVar18 * 8;
      ppuVar12 = &PTR_DAT_00025660 + uVar18;
    } while (*ppuVar12 != (undefined *)0x0);
  }
  (**(code **)(DAT_000294a0 + 0x58))(u_SecureVarPresent_000260a8,&DAT_00024288,2,6,&DAT_00029358);
  FUN_00003648();
  return;
}


// ==== FUN_00009d1c @ 00009d1c

undefined8 FUN_00009d1c(longlong param_1,undefined8 param_2,undefined8 param_3,short param_4)

{
  undefined2 uVar1;
  longlong lVar2;
  byte bVar3;
  longlong lVar4;
  char cVar5;
  undefined8 uVar6;
  longlong lVar7;
  longlong lVar8;
  longlong lVar9;
  byte local_118;
  ushort local_114 [2];
  byte local_110;
  longlong local_108;
  ulonglong local_100;
  undefined4 local_f8 [10];
  undefined2 auStack_d0 [84];
  
  local_114[0] = 0;
  if ((DAT_00029270 != 0) && (*(longlong *)(DAT_00029270 + 8) == 0)) {
    lVar8 = 2;
    lVar9 = 1;
    cVar5 = '\x05';
    bVar3 = 0;
    if (param_4 == 0x29fe) {
      bVar3 = 5;
    }
    else if (param_4 == 0x29ff) {
      bVar3 = 4;
    }
    else if (param_4 == 0x2a00) {
      bVar3 = 3;
    }
    else if (param_4 != 0x2a01) {
      if (param_4 == 0x2a02) {
        bVar3 = 1;
      }
      else {
        if (param_4 != 0x2a03) {
          return 0;
        }
        bVar3 = 2;
      }
    }
    if (DAT_00029350 != 0) {
      local_118 = 0;
      lVar7 = 3;
      DAT_0002a170 = param_1;
      FUN_0002337e(local_f8,200,0);
      if ((&DAT_00029358)[bVar3] == '\0') {
        lVar2 = 4;
        cVar5 = '\x02';
        lVar7 = 1;
        local_118 = 4;
        lVar9 = 4;
        lVar8 = 0;
      }
      else {
        lVar2 = 0;
      }
      lVar4 = 4;
      local_110 = 4;
      if (param_4 == 0x29fe) {
        lVar4 = 3;
        cVar5 = cVar5 + -1;
        local_110 = 3;
        lVar7 = 4;
      }
      *(undefined2 *)(local_f8 + lVar8 * 10) = 0x19c9;
      *(undefined2 *)(local_f8 + lVar7 * 10) = 0x19ca;
      uVar1 = (&DAT_000262f8)[bVar3];
      *(undefined2 *)(local_f8 + lVar4 * 10) = 0x19cb;
      *(undefined2 *)(local_f8 + lVar9 * 10) = 0x19c8;
      uVar6 = 0;
      *(undefined2 *)(local_f8 + lVar2 * 10) = 0x19c7;
      lVar2 = (**(code **)(DAT_00029350 + 0x68))(param_1,uVar1,0,local_f8,cVar5,local_114);
      if (-1 < lVar2) {
        if ((local_114[0] == local_110) && ((&DAT_00029358)[bVar3] != '\0')) {
          FUN_00008ad0(param_1,bVar3,uVar6);
        }
        if (local_114[0] == (ushort)lVar8) {
          FUN_00008d78(param_1,3,bVar3);
        }
        if ((local_114[0] == (ushort)lVar7) && (param_4 != 0x29fe)) {
          FUN_00008d78(param_1,10,bVar3);
        }
        if (local_114[0] == (ushort)lVar9) {
          FUN_000091e4(param_1,(ushort)bVar3);
        }
        if (local_114[0] == local_118) {
          local_108 = 0;
          FUN_00009500(bVar3,(&DAT_000262f8)[bVar3],&local_108,&local_100);
          if (local_108 != 0) {
            (**(code **)(DAT_00029498 + 0x48))();
          }
        }
      }
    }
    return 0;
  }
  return 0x8000000000000003;
}


// ==== FUN_00009fec @ 00009fec

longlong FUN_00009fec(short param_1,longlong *param_2,ulonglong *param_3)

{
  uint uVar1;
  undefined8 *puVar2;
  char *pcVar3;
  longlong lVar4;
  longlong lVar5;
  ulonglong uVar6;
  wchar_t *pwVar7;
  undefined2 uVar8;
  longlong *plVar9;
  short sVar10;
  longlong unaff_RDI;
  char **ppcVar11;
  char *pcVar12;
  undefined8 uVar13;
  char *pcVar14;
  ushort local_res20 [4];
  undefined *puVar15;
  wchar_t *in_stack_ffffffffffffff68;
  char *local_88;
  char *local_80;
  wchar_t *local_78;
  char *local_70;
  char *local_68;
  ulonglong local_60;
  longlong local_58;
  ulonglong local_50;
  undefined8 local_48 [2];
  
  pcVar14 = (char *)0x0;
  local_48[0] = 0;
  if (DAT_00029350 == 0) {
    return unaff_RDI;
  }
  if (param_3 == (ulonglong *)0x0) {
    return unaff_RDI;
  }
  if (*param_3 == 0) {
    return unaff_RDI;
  }
  if (param_2 == (longlong *)0x0) {
    return unaff_RDI;
  }
  local_70 = (char *)0x0;
  ppcVar11 = (char **)0x0;
  local_88 = (char *)0x0;
  lVar4 = FUN_00022fc0(param_2,*param_3,(longlong *)0x0,(longlong *)&local_68);
  pcVar3 = local_68;
  if (-1 < lVar4) {
    ppcVar11 = &local_88;
    pcVar12 = local_68 + 1;
    lVar4 = (**(code **)(DAT_00029498 + 0x40))(4,(longlong)pcVar12 * 0x28);
    if (-1 < lVar4) {
      if (local_88 != (char *)0x0) {
        FUN_0002337e((undefined4 *)local_88,(longlong)pcVar12 * 0x28,0);
        ppcVar11 = &local_70;
        lVar4 = (**(code **)(DAT_00029498 + 0x40))(4,(longlong)pcVar3 << 3);
        if (lVar4 < 0) goto LAB_0000a5dc;
        if (local_70 != (char *)0x0) {
          ppcVar11 = (char **)0x0;
          FUN_0002337e((undefined4 *)local_70,(longlong)pcVar3 << 3,0);
          if (DAT_00029360 == 0) {
            ppcVar11 = (char **)&DAT_00029360;
            lVar4 = (**(code **)(DAT_00029498 + 0x140))(&DAT_00023640,0);
          }
          if (lVar4 < 0) goto LAB_0000a5dc;
          if (DAT_00029360 != 0) {
            ppcVar11 = &local_80;
            local_60 = 0x100;
            lVar4 = (**(code **)(DAT_00029498 + 0x40))(4);
            if (lVar4 < 0) goto LAB_0000a5dc;
            if (local_80 != (char *)0x0) {
              if (pcVar3 != (char *)0x0) {
                lVar4 = 0;
                plVar9 = param_2;
                do {
                  *(longlong **)(local_70 + (longlong)pcVar14 * 8) = plVar9;
                  local_58 = (longlong)plVar9 + (ulonglong)*(uint *)((longlong)plVar9 + 0x14) + 0x1c
                  ;
                  local_68 = (char *)((ulonglong)*(uint *)(plVar9 + 3) - 0x10);
                  local_50 = (((ulonglong)*(uint *)(plVar9 + 2) -
                              (ulonglong)*(uint *)((longlong)plVar9 + 0x14)) - 0x1c) /
                             (ulonglong)*(uint *)(plVar9 + 3);
                  FUN_0002337e((undefined4 *)&DAT_00029e50,400,0);
                  local_78 = (wchar_t *)0x0;
                  lVar5 = FUN_0001edd4(plVar9,&DAT_00023760,0x10);
                  if (lVar5 == 0) {
                    local_60 = 0x100;
                    FUN_0002337e((undefined4 *)local_80,0x100,0);
                    pcVar12 = local_68;
                    uVar6 = (**(code **)(DAT_00029360 + 8))
                                      (DAT_00029360,local_58 + 0x10,local_68,0,0,&local_80,&local_60
                                       ,0x13,(ulonglong)in_stack_ffffffffffffff68 &
                                             0xffffffff00000000);
                    if ((longlong)uVar6 < 0) {
                      pcVar12 = s______r_000261d8;
                      FUN_0001c128(local_80,local_60,(byte *)s______r_000261d8,uVar6);
                    }
                    local_78 = FUN_00005f1c(local_80);
                    FUN_00005fa4(DAT_0002a170,0x19e0,pcVar12,0x29e50);
                  }
                  else {
                    uVar13 = 0x10;
                    lVar5 = FUN_0001edd4(plVar9,(longlong *)&DAT_000235a0,0x10);
                    if (lVar5 == 0) {
                      uVar8 = 0x19e1;
LAB_0000a357:
                      FUN_00005fa4(DAT_0002a170,uVar8,uVar13,0x29e50);
                    }
                    else {
                      uVar13 = 0x10;
                      lVar5 = FUN_0001edd4(plVar9,(longlong *)&DAT_00023680,0x10);
                      if (lVar5 == 0) {
LAB_0000a352:
                        uVar8 = 0x19e3;
                        goto LAB_0000a357;
                      }
                      uVar13 = 0x10;
                      lVar5 = FUN_0001edd4(plVar9,(longlong *)&DAT_00023610,0x10);
                      if (lVar5 == 0) goto LAB_0000a352;
                      uVar13 = 0x10;
                      lVar5 = FUN_0001edd4(plVar9,(longlong *)&DAT_000236d0,0x10);
                      if (lVar5 == 0) goto LAB_0000a352;
                      uVar13 = 0x10;
                      lVar5 = FUN_0001edd4(plVar9,(longlong *)&DAT_00023960,0x10);
                      if (lVar5 == 0) {
                        uVar8 = 0x19e2;
                        goto LAB_0000a357;
                      }
                      FUN_0001e3b4((wchar_t *)&DAT_00029e50,10,(wchar_t *)&DAT_000262dc,plVar9);
                    }
                    (**(code **)(DAT_00029498 + 0x40))(4);
                    if (local_78 != (wchar_t *)0x0) {
                      FUN_0001e3b4(local_78,0x1c,u__X_____000261e8,*(undefined8 *)(local_58 + 0x10))
                      ;
                    }
                  }
                  FUN_0002337e((undefined4 *)&DAT_00029fe0,400,0);
                  FUN_0001e3b4((wchar_t *)&DAT_00029fe0,10,(wchar_t *)&DAT_000262dc,local_58);
                  ppcVar11 = (char **)&DAT_000261f8;
                  pcVar14 = pcVar14 + 1;
                  in_stack_ffffffffffffff68 = local_78;
                  FUN_0001e3b4((wchar_t *)&DAT_00029cc0,400,(wchar_t *)&DAT_000261f8,pcVar14);
                  pwVar7 = local_78;
                  if (local_78 != (wchar_t *)0x0) {
                    (**(code **)(DAT_00029498 + 0x48))();
                  }
                  uVar6 = FUN_00007d2c((ulonglong)pwVar7,&DAT_00029cc0);
                  *(short *)(local_88 + lVar4 + 0x28) = (short)uVar6;
                  local_88[lVar4 + 0x48] = '\0';
                  lVar4 = lVar4 + 0x28;
                  plVar9 = (longlong *)((longlong)plVar9 + (ulonglong)*(uint *)(plVar9 + 2));
                } while (pcVar14 < pcVar3);
              }
              uVar6 = DAT_0002a170;
              FUN_00005fa4(DAT_0002a170,0x19df,ppcVar11,0x29cc0);
              uVar6 = FUN_00007d2c(uVar6,&DAT_00029cc0);
              ppcVar11 = (char **)0x0;
              *(short *)local_88 = (short)uVar6;
              sVar10 = (short)pcVar3 + 1;
              local_88[0x20] = '\x01';
              local_res20[0] = 1;
              lVar4 = (**(code **)(DAT_00029350 + 0x68))
                                (DAT_0002a170,param_1,0,local_88,sVar10,local_res20);
              if (lVar4 < 0) goto LAB_0000a5dc;
              do {
                puVar2 = *(undefined8 **)(local_70 + (longlong)(int)(local_res20[0] - 1) * 8);
                if (param_1 == 0x19de) {
                  uVar6 = (ulonglong)*(uint *)(puVar2 + 2);
                  ppcVar11 = (char **)(((*param_3 - uVar6) - (longlong)puVar2) + (longlong)param_2);
                  FUN_000233d0(puVar2,(undefined8 *)(uVar6 + (longlong)puVar2),(ulonglong)ppcVar11);
                  *param_3 = *param_3 - uVar6;
                  break;
                }
                uVar1 = *(uint *)((longlong)puVar2 + 0x14);
                uVar13 = 0;
                FUN_0002337e((undefined4 *)&DAT_00029fe0,400,0);
                FUN_00005fa4(DAT_0002a170,
                             *(undefined2 *)(local_88 + (ulonglong)local_res20[0] * 0x28),uVar13,
                             0x29fe0);
                puVar15 = &DAT_0002a032;
                FUN_0001e3b4((wchar_t *)&DAT_00029e50,400,u__G__s_000262e8,
                             (longlong)puVar2 + (ulonglong)uVar1 + 0x1c);
                (**(code **)(DAT_00029350 + 0x58))(&DAT_00029cf8,&DAT_00029e50,10,local_48,puVar15);
                ppcVar11 = (char **)0x0;
                lVar4 = (**(code **)(DAT_00029350 + 0x68))
                                  (DAT_0002a170,param_1,0,local_88,sVar10,local_res20);
              } while (-1 < lVar4);
            }
          }
        }
      }
      if (-1 < lVar4) goto LAB_0000a630;
    }
  }
LAB_0000a5dc:
  if (lVar4 != -0x7fffffffffffffeb) {
    FUN_00005fa4(DAT_0002a170,0x19ef,ppcVar11,0x29e50);
    FUN_00005fa4(DAT_0002a170,param_1,ppcVar11,0x29cc0);
    (**(code **)(DAT_00029350 + 0x20))(&DAT_00029cc0,&DAT_00029e50,1,0);
  }
LAB_0000a630:
  if (local_88 != (char *)0x0) {
    (**(code **)(DAT_00029498 + 0x48))();
  }
  if (local_70 != (char *)0x0) {
    (**(code **)(DAT_00029498 + 0x48))();
  }
  if (local_80 != (char *)0x0) {
    (**(code **)(DAT_00029498 + 0x48))();
  }
  return unaff_RDI;
}


// ==== FUN_0000bc4c @ 0000bc4c

longlong FUN_0000bc4c(undefined8 param_1,undefined8 param_2,undefined8 param_3)

{
  longlong lVar1;
  longlong lVar2;
  undefined **ppuVar3;
  
  lVar2 = 0;
  ppuVar3 = &PTR_FUN_000264b0;
  do {
    lVar1 = (*(code *)*ppuVar3)(param_1,param_2,param_3);
    if (-1 < lVar1) {
      return lVar1;
    }
    lVar2 = lVar2 + 1;
    ppuVar3 = &PTR_FUN_000264b0 + lVar2;
  } while (*ppuVar3 != (undefined *)0x0);
  return lVar1;
}


// ==== FUN_0000bcc4 @ 0000bcc4

undefined8 FUN_0000bcc4(undefined8 param_1,undefined8 param_2,longlong param_3)

{
  undefined8 uVar1;
  longlong lVar2;
  char local_res18 [16];
  
  if (param_3 == 0) {
    uVar1 = 0x8000000000000002;
  }
  else {
    lVar2 = (**(code **)(DAT_00029498 + 0x118))(param_2,&DAT_00024348,0,0,0,4);
    if (((lVar2 < 0) &&
        (lVar2 = (**(code **)(param_3 + 0x30))(param_3,0,0xb,1,local_res18), -1 < lVar2)) &&
       (local_res18[0] == '\x03')) {
      return 0;
    }
    uVar1 = 0x8000000000000003;
  }
  return uVar1;
}


// ==== FUN_0000be60 @ 0000be60

undefined8 FUN_0000be60(undefined8 param_1,undefined8 *param_2)

{
  longlong lVar1;
  undefined8 uVar2;
  ulonglong uVar3;
  short *psVar4;
  char *pcVar5;
  longlong lVar6;
  char *pcVar7;
  char cVar8;
  longlong lVar9;
  char *local_res18;
  undefined8 *local_res20;
  short *local_28 [2];
  
  lVar9 = 0;
  local_res18 = (char *)0x0;
  lVar1 = (**(code **)(DAT_00029498 + 0x118))(param_1,&DAT_00023560,&local_res20,0,0,2);
  if (lVar1 < 0) {
LAB_0000bfd8:
    lVar1 = 0;
    uVar3 = (**(code **)(DAT_00029498 + 0x118))(param_1,&DAT_000238e0,&local_res20,0,0,2);
    if (((longlong)uVar3 < 0) ||
       (uVar3 = (*(code *)*local_res20)(local_res20,&DAT_00026490,local_28), psVar4 = local_28[0],
       (longlong)uVar3 < 0)) {
      return uVar3 & 0xffffffffffffff00;
    }
    for (; *psVar4 != 0; psVar4 = psVar4 + 1) {
      lVar9 = lVar9 + 1;
    }
    (**(code **)(DAT_00029498 + 0x40))(4,lVar9 * 2 + 2,param_2);
  }
  else {
    lVar1 = (*(code *)*local_res20)(local_res20,s_en_US_00025c24,local_28);
    psVar4 = local_28[0];
    if (lVar1 < 0) {
      cVar8 = *(char *)local_res20[2];
      lVar6 = lVar9;
      while (cVar8 != '\0') {
        lVar6 = lVar6 + 1;
        cVar8 = ((char *)local_res20[2])[lVar6];
      }
      (**(code **)(DAT_00029498 + 0x40))(4,lVar6 + 1,&local_res18);
      if (local_res18 != (char *)0x0) {
        pcVar7 = (char *)local_res20[2];
        pcVar5 = local_res18;
        do {
          cVar8 = *pcVar7;
          pcVar7 = pcVar7 + 1;
          *pcVar5 = cVar8;
          pcVar5 = pcVar5 + 1;
        } while (cVar8 != '\0');
        cVar8 = *local_res18;
        pcVar7 = local_res18;
        while (cVar8 != '\0') {
          pcVar5 = &DAT_0002648c;
          cVar8 = ';';
          do {
            if ((pcVar5 + -0x2648c)[(longlong)pcVar7] != cVar8) break;
            pcVar5 = pcVar5 + 1;
            cVar8 = *pcVar5;
          } while (cVar8 != '\0');
          if (*pcVar5 == '\0') break;
          pcVar7 = pcVar7 + 1;
          cVar8 = *pcVar7;
        }
        *pcVar7 = '\0';
        lVar1 = (*(code *)*local_res20)(local_res20,local_res18,local_28);
        (**(code **)(DAT_00029498 + 0x48))(local_res18);
        local_res18 = (char *)0x0;
      }
      psVar4 = local_28[0];
      if (lVar1 < 0) goto LAB_0000bfd8;
    }
    for (; *psVar4 != 0; psVar4 = psVar4 + 1) {
      lVar9 = lVar9 + 1;
    }
    lVar1 = DAT_00029498;
    (**(code **)(DAT_00029498 + 0x40))(4,lVar9 * 2 + 2,param_2);
  }
  uVar2 = FUN_0001dff0((wchar_t *)*param_2,(wchar_t *)&DAT_00025b68,local_28[0],lVar1);
  return CONCAT71((int7)((ulonglong)uVar2 >> 8),1);
}


// ==== FUN_0000c06c @ 0000c06c

ulonglong FUN_0000c06c(undefined8 param_1,undefined8 param_2,undefined8 param_3,undefined8 *param_4)

{
  longlong lVar1;
  undefined8 uVar2;
  ulonglong uVar3;
  short *psVar4;
  char *pcVar5;
  longlong lVar6;
  char *pcVar7;
  char cVar8;
  longlong lVar9;
  undefined *puVar10;
  char *local_38;
  longlong local_30;
  short *local_28 [2];
  
  lVar9 = 0;
  local_38 = (char *)0x0;
  lVar1 = (**(code **)(DAT_00029498 + 0x118))(param_1,&DAT_00023560,&local_30,0,0,2);
  if (lVar1 < 0) {
LAB_0000c20f:
    uVar3 = (**(code **)(DAT_00029498 + 0x118))(param_1,&DAT_000238e0,&local_30,0,0,2);
    if (-1 < (longlong)uVar3) {
      puVar10 = &DAT_00026490;
      uVar3 = (**(code **)(local_30 + 8))(local_30,param_2,param_3,&DAT_00026490,local_28);
      psVar4 = local_28[0];
      if (-1 < (longlong)uVar3) {
        for (; *psVar4 != 0; psVar4 = psVar4 + 1) {
          lVar9 = lVar9 + 1;
        }
        (**(code **)(DAT_00029498 + 0x40))(4,lVar9 * 2 + 2,param_4);
        goto LAB_0000c1f5;
      }
    }
    uVar3 = uVar3 & 0xffffffffffffff00;
  }
  else {
    lVar1 = (**(code **)(local_30 + 8))(local_30,param_2,param_3,s_en_US_00025c24,local_28);
    psVar4 = local_28[0];
    if (lVar1 < 0) {
      cVar8 = **(char **)(local_30 + 0x10);
      lVar6 = lVar9;
      while (cVar8 != '\0') {
        lVar6 = lVar6 + 1;
        cVar8 = (*(char **)(local_30 + 0x10))[lVar6];
      }
      (**(code **)(DAT_00029498 + 0x40))(4,lVar6 + 1,&local_38);
      if (local_38 != (char *)0x0) {
        pcVar7 = *(char **)(local_30 + 0x10);
        pcVar5 = local_38;
        do {
          cVar8 = *pcVar7;
          pcVar7 = pcVar7 + 1;
          *pcVar5 = cVar8;
          pcVar5 = pcVar5 + 1;
        } while (cVar8 != '\0');
        cVar8 = *local_38;
        pcVar7 = local_38;
        while (cVar8 != '\0') {
          pcVar5 = &DAT_0002648c;
          cVar8 = ';';
          do {
            if ((pcVar5 + -0x2648c)[(longlong)pcVar7] != cVar8) break;
            pcVar5 = pcVar5 + 1;
            cVar8 = *pcVar5;
          } while (cVar8 != '\0');
          if (*pcVar5 == '\0') break;
          pcVar7 = pcVar7 + 1;
          cVar8 = *pcVar7;
        }
        *pcVar7 = '\0';
        lVar1 = (**(code **)(local_30 + 8))(local_30,param_2,param_3,local_38,local_28);
        (**(code **)(DAT_00029498 + 0x48))(local_38);
        local_38 = (char *)0x0;
      }
      psVar4 = local_28[0];
      if (lVar1 < 0) goto LAB_0000c20f;
    }
    for (; *psVar4 != 0; psVar4 = psVar4 + 1) {
      lVar9 = lVar9 + 1;
    }
    puVar10 = DAT_00029498;
    (**(code **)(DAT_00029498 + 0x40))(4,lVar9 * 2 + 2,param_4);
LAB_0000c1f5:
    uVar2 = FUN_0001dff0((wchar_t *)*param_4,(wchar_t *)&DAT_00025b68,local_28[0],puVar10);
    uVar3 = CONCAT71((int7)((ulonglong)uVar2 >> 8),1);
  }
  return uVar3;
}


// ==== FUN_0000c2bc @ 0000c2bc

undefined8 FUN_0000c2bc(longlong param_1,undefined8 *param_2)

{
  longlong lVar1;
  longlong lVar2;
  ulonglong uVar3;
  byte *pbVar4;
  ulonglong uVar5;
  ulonglong uVar6;
  ulonglong uVar7;
  longlong local_res18;
  ulonglong local_res20;
  longlong local_38;
  ulonglong local_30;
  longlong local_28;
  ulonglong local_20;
  
  lVar1 = (**(code **)(DAT_00029498 + 0x138))(0,0,0,&local_res20,&local_res18);
  if (-1 < lVar1) {
    uVar5 = 0;
    if (local_res20 != 0) {
      do {
        local_38 = 0;
        lVar1 = (**(code **)(DAT_00029498 + 0x130))
                          (*(undefined8 *)(local_res18 + uVar5 * 8),&local_38,&local_30);
        if (-1 < lVar1) {
          uVar6 = 0;
          if (local_30 != 0) {
            do {
              lVar2 = (**(code **)(DAT_00029498 + 0x128))
                                (*(undefined8 *)(local_res18 + uVar5 * 8),
                                 *(undefined8 *)(local_38 + uVar6 * 8),&local_28);
              lVar1 = DAT_00029498;
              if (-1 < lVar2) {
                uVar7 = 0;
                if (local_20 != 0) {
                  pbVar4 = (byte *)(local_28 + 0x10);
                  do {
                    if (((*(longlong *)(pbVar4 + -8) == param_1) && ((*pbVar4 & 0x10) != 0)) &&
                       (uVar3 = 0, local_res20 != 0)) {
                      do {
                        if (*(longlong *)(local_res18 + uVar3 * 8) == *(longlong *)(pbVar4 + -0x10))
                        {
                          *param_2 = *(undefined8 *)(local_res18 + uVar3 * 8);
                          (**(code **)(lVar1 + 0x48))(local_28);
                          (**(code **)(DAT_00029498 + 0x48))(local_38);
                          (**(code **)(DAT_00029498 + 0x48))(local_res18);
                          return 0;
                        }
                        uVar3 = uVar3 + 1;
                      } while (uVar3 < local_res20);
                    }
                    uVar7 = uVar7 + 1;
                    pbVar4 = pbVar4 + 0x18;
                  } while (uVar7 < local_20);
                }
                if (local_28 != 0) {
                  (**(code **)(DAT_00029498 + 0x48))(local_28);
                }
              }
              uVar6 = uVar6 + 1;
            } while (uVar6 < local_30);
          }
          if (local_38 != 0) {
            (**(code **)(DAT_00029498 + 0x48))();
          }
        }
        uVar5 = uVar5 + 1;
      } while (uVar5 < local_res20);
    }
    if (local_res18 != 0) {
      (**(code **)(DAT_00029498 + 0x48))();
    }
  }
  return 0x800000000000000e;
}


// ==== FUN_0000c464 @ 0000c464

longlong FUN_0000c464(longlong param_1,longlong param_2,longlong *param_3,longlong *param_4)

{
  longlong lVar1;
  longlong lVar2;
  ulonglong uVar3;
  longlong unaff_RBX;
  ulonglong uVar4;
  longlong lVar5;
  ulonglong uVar6;
  ulonglong local_res8 [2];
  longlong local_res18;
  longlong local_res20;
  ulonglong local_58;
  ulonglong local_50;
  undefined8 local_48;
  
  *param_3 = 0;
  *param_4 = 0;
  local_res8[0] = 0;
  local_res18 = 0;
  if (((param_1 == 0) || (param_2 == 0)) ||
     (lVar1 = (**(code **)(DAT_00029498 + 0x138))(0,0,0,local_res8,&local_res18), lVar1 < 0)) {
    if (local_res18 != 0) {
      (**(code **)(DAT_00029498 + 0x48))();
    }
  }
  else {
    lVar1 = FUN_0001d774(local_res8[0]);
    uVar3 = 0;
    if (local_res8[0] != 0) {
      do {
        *(undefined1 *)(uVar3 + lVar1) = 0;
        uVar3 = uVar3 + 1;
      } while (uVar3 < local_res8[0]);
    }
    lVar2 = (**(code **)(DAT_00029498 + 0x130))(param_2);
    if (-1 < lVar2) {
      uVar3 = 0;
      if (local_50 != 0) {
        do {
          lVar2 = (**(code **)(DAT_00029498 + 0x128))(param_2);
          if (-1 < lVar2) {
            uVar6 = 0;
            if (local_58 != 0) {
              lVar2 = 0;
              do {
                if (((*(longlong *)(lVar2 + local_res20) == param_1) &&
                    ((*(byte *)(lVar2 + 0x10 + local_res20) & 8) != 0)) &&
                   (uVar4 = 0, local_res8[0] != 0)) {
                  do {
                    if (*(longlong *)(lVar2 + 8 + local_res20) ==
                        *(longlong *)(local_res18 + uVar4 * 8)) {
                      *(undefined1 *)(uVar4 + lVar1) = 1;
                    }
                    uVar4 = uVar4 + 1;
                  } while (uVar4 < local_res8[0]);
                }
                uVar6 = uVar6 + 1;
                lVar2 = lVar2 + 0x18;
              } while (uVar6 < local_58);
            }
            (**(code **)(DAT_00029498 + 0x48))(local_res20);
          }
          uVar3 = uVar3 + 1;
        } while (uVar3 < local_50);
      }
      (**(code **)(DAT_00029498 + 0x48))(local_48);
    }
    uVar3 = 0;
    if (local_res8[0] != 0) {
      do {
        if (*(char *)(uVar3 + lVar1) != '\0') {
          *param_3 = *param_3 + 1;
        }
        uVar3 = uVar3 + 1;
      } while (uVar3 < local_res8[0]);
    }
    if (*param_3 != 0) {
      lVar2 = FUN_0001d774(*param_3 << 3);
      uVar3 = 0;
      *param_4 = lVar2;
      if (local_res8[0] != 0) {
        lVar5 = 0;
        do {
          if (*(char *)(uVar3 + lVar1) != '\0') {
            *(undefined8 *)(lVar5 + lVar2) = *(undefined8 *)(local_res18 + uVar3 * 8);
            lVar5 = lVar5 + 8;
          }
          uVar3 = uVar3 + 1;
        } while (uVar3 < local_res8[0]);
      }
    }
    if (local_res18 != 0) {
      (**(code **)(DAT_00029498 + 0x48))();
    }
  }
  return unaff_RBX;
}


// ==== FUN_0000c67c @ 0000c67c

void FUN_0000c67c(longlong param_1,longlong param_2)

{
  longlong lVar1;
  longlong *plVar2;
  longlong extraout_RAX;
  longlong lVar3;
  longlong local_res18;
  longlong *local_res20;
  
  local_res18 = 0;
  local_res20 = (longlong *)0x0;
  FUN_0000c464(param_1,param_2,&local_res18,(longlong *)&local_res20);
  lVar1 = local_res18;
  plVar2 = local_res20;
  if (-1 < extraout_RAX) {
    for (; lVar1 != 0; lVar1 = lVar1 + -1) {
      lVar3 = (**(code **)(DAT_00029498 + 0x118))(*plVar2,&DAT_000234e0,0,0,0,4);
      if (lVar3 < 0) {
        FUN_0000c67c(param_1,*plVar2);
      }
      else {
        lVar3 = FUN_0001f0d4();
        if (-1 < lVar3) {
          *(longlong **)(DAT_00029390 + DAT_00029388 * 8) = plVar2;
          DAT_00029388 = DAT_00029388 + 1;
        }
      }
      plVar2 = plVar2 + 1;
    }
  }
  return;
}


// ==== FUN_0000c738 @ 0000c738

undefined8 FUN_0000c738(longlong param_1,longlong param_2,ulonglong *param_3,longlong *param_4)

{
  ulonglong uVar1;
  undefined8 uVar2;
  longlong lVar3;
  ulonglong uVar4;
  
  uVar4 = 0;
  *param_3 = 0;
  *param_4 = 0;
  uVar2 = FUN_0000c67c(param_1,param_2);
  uVar1 = DAT_00029388;
  if (DAT_00029388 != 0) {
    *param_3 = DAT_00029388;
    lVar3 = FUN_0001d774(uVar1 << 3);
    *param_4 = lVar3;
    if (*param_3 != 0) {
      do {
        *(undefined8 *)(lVar3 + uVar4 * 8) = **(undefined8 **)(DAT_00029390 + uVar4 * 8);
        uVar4 = uVar4 + 1;
      } while (uVar4 < *param_3);
    }
  }
  return uVar2;
}


// ==== FUN_0000ca58 @ 0000ca58

void FUN_0000ca58(longlong param_1)

{
  longlong lVar1;
  undefined2 local_38 [6];
  ushort local_2c;
  
  lVar1 = (**(code **)(DAT_00029478 + 0x140))(&DAT_00023660,0,&DAT_00029398);
  if (lVar1 == 0) {
    if (param_1 != 0) {
      (**(code **)(DAT_00029478 + 0x70))(param_1);
    }
    if (DAT_0002ab7e == '\x02') {
      local_38[0] = 0x5f01;
      (*(code *)*DAT_00029398)(DAT_00029398,0x15,local_38);
      FUN_00000680(DAT_0002a178,0x13a0,(byte *)u__02X_02X_000264f8,
                   (ulonglong)
                   (((uint)(local_2c >> 4) ^ (uint)(byte)local_2c) & 0xf ^
                   (uint)(byte)(local_2c >> 4)));
    }
  }
  return;
}


// ==== FUN_0000d400 @ 0000d400

void FUN_0000d400(undefined8 param_1)

{
  undefined1 uVar1;
  short sVar2;
  short sVar3;
  uint uVar4;
  longlong lVar5;
  char *pcVar6;
  char *pcVar7;
  short *psVar8;
  char *pcVar9;
  ulonglong uVar10;
  ulonglong uVar11;
  char *pcVar12;
  ushort uVar13;
  undefined2 *puVar14;
  char *pcVar15;
  char *pcVar16;
  undefined4 local_res10 [2];
  uint local_res18 [2];
  undefined1 local_res20 [8];
  char *local_c8;
  longlong local_c0;
  longlong local_b8;
  longlong local_b0;
  longlong local_a8;
  longlong local_a0;
  longlong local_98;
  char *local_90;
  char *local_88;
  undefined2 local_80;
  undefined1 local_72;
  undefined1 local_50 [16];
  
  pcVar12 = (char *)0x0;
  local_res10[0] = 0;
  lVar5 = (**(code **)(DAT_00029478 + 0x138))(2,&DAT_000236a0,0,&local_c8,&local_c0);
  pcVar6 = (char *)0x0;
  if (lVar5 < 0) {
    local_c8 = pcVar12;
  }
  if (local_c8 != (char *)0x0) {
    do {
      (**(code **)(DAT_00029478 + 0x98))
                (*(undefined8 *)(local_c0 + (longlong)pcVar6 * 8),&DAT_000236a0,&local_b0);
      (**(code **)(local_b0 + 0x70))(local_b0,local_50,&local_a8,&local_a0,&local_98);
      if (((local_a8 == 0) && (local_a0 == 0x17)) && (local_98 == 0)) {
        (**(code **)(DAT_00029478 + 0x108))(*(undefined8 *)(local_c0 + (longlong)pcVar6 * 8),0,0,1);
      }
      pcVar6 = (char *)(ulonglong)(byte)((char)pcVar6 + 1);
    } while (pcVar6 < local_c8);
  }
  lVar5 = local_c0;
  if (local_c0 != 0) {
    (**(code **)(DAT_00029478 + 0x48))();
  }
  DAT_000293a0 = 1;
  pcVar6 = (char *)FUN_0001b514(lVar5,0x100);
  if (pcVar6 != (char *)0x0) {
    pcVar7 = (char *)FUN_0001b514(lVar5,0x40);
    local_88 = pcVar7;
    if (pcVar7 != (char *)0x0) {
      lVar5 = (**(code **)(DAT_00029478 + 0x138))(2,&DAT_000234c0,0,&local_c8,&local_c0);
      pcVar16 = (char *)0x0;
      if (lVar5 < 0) {
        local_c8 = pcVar12;
      }
      if (local_c8 != (char *)0x0) {
        do {
          (**(code **)(DAT_00029478 + 0x98))
                    (*(undefined8 *)(local_c0 + (longlong)pcVar16 * 8),&DAT_00023690,&local_90);
          for (pcVar9 = local_90;
              (pcVar15 = pcVar12, *pcVar9 != '\x7f' &&
              ((*pcVar9 != '\x01' || (pcVar15 = pcVar9, pcVar9[1] != '\x01'))));
              pcVar9 = pcVar9 + *(ushort *)(pcVar9 + 2)) {
          }
          if (((pcVar15 != (char *)0x0) && (pcVar15[5] == '\x17')) && (pcVar15[4] == '\0')) {
            (**(code **)(DAT_00029478 + 0x98))
                      (*(undefined8 *)(local_c0 + (longlong)pcVar16 * 8),&DAT_000234c0,&local_b8);
            lVar5 = local_b8;
            (**(code **)(local_b8 + 0x28))(local_b8,local_res18,local_res20);
            sVar2 = *(short *)(&DAT_00026ac0 + (ulonglong)local_res18[0] * 2);
            sVar3 = *(short *)(&DAT_00026ad0 + (ulonglong)local_res18[0] * 2);
            psVar8 = (short *)FUN_0001b514(lVar5,0x200);
            if (psVar8 == (short *)0x0) {
              return;
            }
            FUN_00000340((undefined8 *)psVar8,0x200);
            local_res10[0] = 0x200;
            (**(code **)(local_b8 + 0x18))(local_b8,psVar8,local_res10);
            FUN_00000340((undefined8 *)&local_80,0x2a);
            if (&local_80 != psVar8 + 0x1b) {
              FUN_000002e0((undefined8 *)&local_80,(undefined8 *)(psVar8 + 0x1b),0x28);
            }
            pcVar7 = local_88;
            uVar13 = 0;
            uVar4 = 1;
            do {
              uVar10 = (ulonglong)uVar4;
              uVar11 = (ulonglong)uVar13;
              uVar13 = uVar13 + 2;
              uVar1 = *(undefined1 *)((longlong)&local_80 + uVar11);
              *(undefined1 *)((longlong)&local_80 + uVar11) =
                   *(undefined1 *)((longlong)&local_80 + uVar10);
              uVar4 = uVar13 + 1;
              *(undefined1 *)((longlong)&local_80 + uVar10) = uVar1;
            } while (uVar4 < 0x28);
            local_72 = 0;
            if (*psVar8 < 0) {
              puVar14 = &local_80;
              FUN_0001c128(pcVar6,0x100,(byte *)s__a_ATAPI_00026828,(ulonglong)puVar14);
              pcVar12 = s_N_A_00026838;
            }
            else {
              puVar14 = &local_80;
              FUN_0001c128(pcVar6,0x100,(byte *)s__a___d__dGB__000267f8,(ulonglong)puVar14);
              if ((psVar8[0x4c] == -1) || ((*(byte *)(psVar8 + 0x4e) & 0x40) == 0)) {
                pcVar12 = s_NOT_SUPPORTED_00026818;
              }
              else {
                pcVar12 = s_SUPPORTED_00026808;
              }
            }
            FUN_0001c128(pcVar7,0x40,(byte *)pcVar12,(ulonglong)puVar14);
            FUN_00000680(param_1,sVar2,&DAT_0002672c,(ulonglong)pcVar6);
            FUN_00000680(param_1,sVar3,&DAT_0002672c,(ulonglong)pcVar7);
            (**(code **)(DAT_00029478 + 0x48))(psVar8);
          }
          pcVar16 = (char *)(ulonglong)(byte)((char)pcVar16 + 1);
          pcVar12 = pcVar15;
        } while (pcVar16 < local_c8);
      }
      if (local_c0 != 0) {
        (**(code **)(DAT_00029478 + 0x48))();
      }
      (**(code **)(DAT_00029478 + 0x48))(pcVar6);
      pcVar6 = pcVar7;
    }
    (**(code **)(DAT_00029478 + 0x48))(pcVar6);
  }
  return;
}


// ==== FUN_0000d870 @ 0000d870

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_0000d870(undefined8 param_1)

{
  uint uVar1;
  longlong lVar2;
  uint *puVar3;
  uint uVar4;
  uint uVar5;
  char *pcVar6;
  undefined4 local_res10 [2];
  undefined8 local_res18 [2];
  undefined1 local_7f8 [927];
  undefined1 local_459;
  
  local_res10[0] = 0;
  uVar4 = _DAT_e00fd010 & 0xfffff000;
  local_res18[0] = 0x7d8;
  lVar2 = (**(code **)(DAT_00029488 + 0x48))
                    (u_Setup_000262c8,&DAT_00023710,local_res10,local_res18,local_7f8);
  pcVar6 = s_Supported_00026840;
  uVar5 = uVar4 + 0xb4;
  if (lVar2 < 0) {
    local_res10[0] = 3;
  }
  *(undefined4 *)(ulonglong)uVar5 = 0;
  puVar3 = (uint *)(ulonglong)(uVar4 + 0xb8);
  *(undefined4 *)(ulonglong)uVar5 = 0x1000;
  uVar4 = *puVar3;
  *(undefined4 *)(ulonglong)uVar5 = 4;
  uVar5 = *puVar3;
  if ((uVar4 >> 0x1e & 1) == 0) {
    pcVar6 = s_Not_supported_00026850;
  }
  FUN_00000680(param_1,0x1385,&DAT_0002672c,(ulonglong)pcVar6);
  uVar1 = uVar4 >> 0x1b & 7;
  if (uVar1 == 2) {
    pcVar6 = s_48_MHz_00026860;
  }
  else if (uVar1 == 4) {
    pcVar6 = s_30_MHz_00026868;
  }
  else if (uVar1 == 6) {
    pcVar6 = s_17_MHz_00026870;
  }
  else {
    pcVar6 = s_Invalid_Setting_00026878;
  }
  FUN_00000680(param_1,5000,&DAT_0002672c,(ulonglong)pcVar6);
  uVar1 = uVar4 >> 0x18 & 7;
  if (uVar1 == 2) {
    pcVar6 = s_48_MHz_00026860;
  }
  else if (uVar1 == 4) {
    pcVar6 = s_30_MHz_00026868;
  }
  else if (uVar1 == 6) {
    pcVar6 = s_17_MHz_00026870;
  }
  else {
    pcVar6 = s_Invalid_Setting_00026878;
  }
  FUN_00000680(param_1,0x138b,&DAT_0002672c,(ulonglong)pcVar6);
  uVar1 = uVar4 >> 0x15 & 7;
  if (uVar1 == 2) {
    pcVar6 = s_48_MHz_00026860;
  }
  else if (uVar1 == 4) {
    pcVar6 = s_30_MHz_00026868;
  }
  else if (uVar1 == 6) {
    pcVar6 = s_17_MHz_00026870;
  }
  else {
    pcVar6 = s_Invalid_Setting_00026878;
  }
  FUN_00000680(param_1,0x138e,&DAT_0002672c,(ulonglong)pcVar6);
  pcVar6 = s_Supported_00026840;
  if ((uVar4 >> 0x14 & 1) == 0) {
    pcVar6 = s_Not_supported_00026850;
  }
  FUN_00000680(param_1,0x1391,&DAT_0002672c,(ulonglong)pcVar6);
  uVar1 = uVar4 >> 0x11 & 7;
  if (uVar1 == 2) {
    pcVar6 = s_48_MHz_00026860;
  }
  else if (uVar1 == 4) {
    pcVar6 = s_30_MHz_00026868;
  }
  else if (uVar1 == 6) {
    pcVar6 = s_17_MHz_00026870;
  }
  else {
    pcVar6 = s_Invalid_Setting_00026878;
  }
  FUN_00000680(param_1,0x1394,&DAT_0002672c,(ulonglong)pcVar6);
  uVar5 = uVar5 >> 8 & 3;
  if (uVar5 == 0) {
    FUN_00000680(param_1,0x1397,&DAT_0002672c,0x26888);
    local_459 = 0;
LAB_0000db0b:
    if (uVar5 != 1) goto LAB_0000db7c;
  }
  else {
    if (uVar5 != 1) {
      FUN_00000680(param_1,0x1397,&DAT_0002672c,0x268a8);
      goto LAB_0000db0b;
    }
    FUN_00000680(param_1,0x1397,&DAT_0002672c,0x26898);
    local_459 = 1;
  }
  uVar5 = uVar4 & 0xf0;
  if (uVar5 < 5) {
    if (uVar5 == 0) {
      pcVar6 = s_512_KB_000268b4;
    }
    else if (uVar5 == 1) {
      pcVar6 = &DAT_000268bc;
    }
    else if (uVar5 == 2) {
      pcVar6 = &DAT_000268c4;
    }
    else {
      if (uVar5 != 3) goto LAB_0000db62;
      pcVar6 = &DAT_000268cc;
    }
  }
  else {
    pcVar6 = s_Reserved_000268a8;
    if (6 < uVar5 - 8) {
LAB_0000db62:
      pcVar6 = s_Not_present_000268f8;
    }
  }
  FUN_00000680(param_1,0x139a,&DAT_0002672c,(ulonglong)pcVar6);
LAB_0000db7c:
  uVar4 = uVar4 & 0xf;
  if (uVar4 == 0) {
    pcVar6 = s_512_KB_000268b4;
  }
  else if (uVar4 == 1) {
    pcVar6 = &DAT_000268bc;
  }
  else if (uVar4 == 2) {
    pcVar6 = &DAT_000268c4;
  }
  else if (uVar4 == 3) {
    pcVar6 = &DAT_000268cc;
  }
  else if (uVar4 == 4) {
    pcVar6 = &DAT_000268d4;
  }
  else if (uVar4 == 5) {
    pcVar6 = s_16_MB_000268dc;
  }
  else if (uVar4 == 6) {
    pcVar6 = s_32_MB_000268e4;
  }
  else {
    if (uVar4 != 7) {
      return;
    }
    pcVar6 = s_64_MB_000268ec;
  }
  FUN_00000680(param_1,0x139d,&DAT_0002672c,(ulonglong)pcVar6);
  return;
}


// ==== FUN_0000dc10 @ 0000dc10

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

byte FUN_0000dc10(undefined8 param_1,longlong param_2,longlong param_3)

{
  undefined1 uVar1;
  char cVar2;
  short sVar3;
  ulonglong uVar4;
  int iVar5;
  uint *puVar6;
  byte bVar7;
  ulonglong uVar8;
  byte bVar9;
  wchar_t *pwVar10;
  longlong lVar11;
  uint uVar12;
  bool bVar13;
  uint local_res10 [2];
  undefined8 local_res18;
  undefined4 local_res20;
  undefined4 uStackX_24;
  
  uVar12 = (uint)_DAT_e00f8002;
  uVar8 = (ulonglong)uVar12;
  if (uVar12 < 0x689) {
    if (_DAT_e00f8002 < 0x687) {
      uVar8 = (ulonglong)(uVar12 - 0x280);
      if (uVar12 - 0x280 == 0) {
LAB_0000dc92:
        iVar5 = 0;
        goto LAB_0000dc94;
      }
      uVar8 = (ulonglong)(uVar12 - 0x281);
      if (uVar12 - 0x281 != 0) {
        uVar12 = uVar12 - 0x285;
        uVar8 = (ulonglong)uVar12;
        if (uVar12 == 0) goto LAB_0000dc92;
        if (uVar12 != 1) goto LAB_0000dc64;
      }
    }
LAB_0000dc8b:
    iVar5 = 2;
  }
  else {
    if ((uVar12 == 0x9d85) || (uVar12 == 0xa303)) goto LAB_0000dc92;
    if (_DAT_e00f8002 - 0xa307 < 2) goto LAB_0000dc8b;
LAB_0000dc64:
    iVar5 = 1;
  }
  *(undefined1 *)(param_2 + 0x33) = 1;
LAB_0000dc94:
  if ((_DAT_e00f8002 < 0x690) ||
     (((0x691 < _DAT_e00f8002 && (_DAT_e00f8002 != 0xa309)) && (1 < _DAT_e00f8002 - 0xa310)))) {
    uVar1 = 0;
  }
  else {
    uVar1 = 1;
  }
  *(undefined1 *)(param_2 + 0x34) = uVar1;
  if (iVar5 == 0) {
    pwVar10 = u_Determines_how_SATA_controller_s_000269e0;
    sVar3 = 0x101d;
  }
  else {
    sVar3 = 0x101f;
    if (iVar5 == 1) {
      pwVar10 = u_Intel_RST_Premium_With_Intel_Opt_00026910;
      sVar3 = 0x101f;
    }
    else {
      pwVar10 = u_Intel_RST_With_Intel_Optane_Syst_00026980;
    }
  }
  FUN_00000680(param_1,sVar3,(byte *)pwVar10,uVar8);
  bVar9 = 0;
  uVar8 = 0;
  do {
    lVar11 = 0;
    cVar2 = FUN_0001b6e0();
    uVar12 = 8;
    if (cVar2 == '\x02') {
      uVar12 = 3;
    }
    if (uVar12 <= (uint)uVar8) {
      bVar13 = (bool)*(char *)(param_3 + 0x44) != (DAT_e00b800a == '\x04');
      if (bVar13) {
        *(bool *)(param_3 + 0x44) = DAT_e00b800a == '\x04';
      }
      bVar7 = 0;
      lVar11 = FUN_0001f90c((longlong *)&DAT_00023840);
      if (lVar11 != 0) {
        uVar8 = 0;
        bVar7 = 0;
        while( true ) {
          cVar2 = FUN_0001b6e0();
          uVar12 = 0x18;
          if (cVar2 == '\x02') {
            uVar12 = 0x10;
          }
          if (uVar12 <= (uint)uVar8) break;
          *(undefined1 *)(uVar8 + 0x3e + param_2) = *(undefined1 *)(uVar8 + 0x19 + lVar11);
          *(undefined1 *)(uVar8 + 0x56 + param_2) = *(undefined1 *)(uVar8 + 0x31 + lVar11);
          if (*(char *)(uVar8 + 0x19 + lVar11) == '\0') {
            *(undefined1 *)(uVar8 + 0xb8 + param_3) = 0;
            bVar7 = 1;
          }
          uVar8 = (ulonglong)((uint)uVar8 + 1);
        }
        uVar8 = 0;
        while( true ) {
          cVar2 = FUN_0001b6e0();
          uVar12 = 6;
          if (cVar2 == '\x02') {
            uVar12 = 4;
          }
          if (uVar12 <= (uint)uVar8) break;
          *(undefined1 *)(uVar8 + 0x6e + param_2) = *(undefined1 *)(uVar8 + 0x49 + lVar11);
          uVar8 = (ulonglong)((uint)uVar8 + 1);
        }
      }
      if (DAT_000293a0 == '\0') {
        FUN_0000d400(param_1);
      }
      return bVar9 | bVar13 | bVar7;
    }
    cVar2 = FUN_0001b6e0();
    if (cVar2 == '\x02') {
      if (uVar8 < 3) {
        local_res18 = *(undefined8 *)((longlong)&DAT_00029220 + uVar8 * 8 + lVar11);
      }
      else {
LAB_0000dd51:
        local_res20 = 0;
        uStackX_24 = 0;
        local_res18 = 0;
      }
    }
    else {
      if (7 < uVar8) goto LAB_0000dd51;
      local_res18 = *(undefined8 *)((longlong)&DAT_000291e0 + uVar8 * 8 + lVar11);
    }
    uVar12 = (uint)local_res18;
    uVar4 = FUN_000231d4(uVar12);
    if ((char)uVar4 == '\0') {
LAB_0000dda5:
      if (*(char *)(uVar8 + 0x56 + param_3) == '\x01') {
        *(undefined1 *)(uVar8 + 0x56 + param_3) = 0;
        bVar9 = 1;
      }
      *(undefined1 *)(uVar8 + 0x35 + param_2) = 0;
    }
    else {
      puVar6 = local_res10;
      FUN_00023290(uVar12,puVar6);
      if (local_res10[0] != 0) goto LAB_0000dda5;
      uVar12 = FUN_00023240(uVar12,(char)puVar6);
      if ((uVar12 & 0x1c00 | 0x200) >> 9 != local_res18._4_4_) goto LAB_0000dda5;
      *(undefined1 *)(uVar8 + 0x35 + param_2) = 1;
    }
    uVar8 = (ulonglong)((uint)uVar8 + 1);
  } while( true );
}


// ==== FUN_0000de9c @ 0000de9c

void FUN_0000de9c(undefined8 param_1,longlong param_2)

{
  longlong lVar1;
  char cVar2;
  longlong lVar3;
  ulonglong uVar4;
  uint uVar5;
  uint uVar6;
  ulonglong uVar7;
  wchar_t *pwVar8;
  undefined8 uVar9;
  byte bVar10;
  uint uVar11;
  undefined8 uVar12;
  uint uVar13;
  undefined8 uVar14;
  bool bVar15;
  
  lVar3 = FUN_0001f90c((longlong *)&DAT_00023860);
  if ((lVar3 != 0) && (lVar1 = lVar3 + 0x18, lVar1 != 0)) {
    uVar7 = 0;
    uVar9 = 0x18;
    uVar14 = 0x10;
    uVar12 = 1;
    while( true ) {
      cVar2 = FUN_0001b6e0();
      uVar13 = (uint)uVar14;
      uVar11 = (uint)uVar9;
      uVar5 = uVar11;
      if (cVar2 == '\x02') {
        uVar5 = uVar13;
      }
      uVar6 = (uint)uVar7;
      if (uVar5 <= uVar6) break;
      uVar11 = (uint)uVar12;
      uVar5 = uVar11 << ((byte)uVar7 & 0x1f);
      bVar10 = (byte)uVar12;
      if ((*(uint *)(lVar3 + 0x20) & uVar5) == 0) {
        if (uVar6 + 1 == (uint)*(byte *)(lVar3 + 0x1f)) {
          *(undefined1 *)(uVar7 + 0xf + param_2) = 4;
        }
        else if ((*(uint *)(lVar3 + 0x24) & uVar5) == 0) {
          *(undefined1 *)(uVar7 + 0xf + param_2) = 3;
        }
        else {
          uVar4 = uVar7 >> 2 & 0x3fffffff;
          uVar5 = uVar6 & 3;
          if (uVar5 == uVar11) {
            if (*(char *)(uVar4 + 1 + lVar1) != '\0') {
LAB_0000df74:
              *(undefined1 *)(uVar7 + 0xf + param_2) = 2;
              goto LAB_0000df4c;
            }
          }
          else {
            if (uVar5 == 2) {
              bVar15 = *(char *)(uVar4 + 1 + lVar1) == '\x03';
            }
            else {
              if (uVar5 != 3) goto LAB_0000df46;
              if ((byte)(*(char *)(uVar4 + 1 + lVar1) - 2U) <= bVar10) goto LAB_0000df74;
              bVar15 = *(byte *)(uVar4 + 0x18 + lVar1) == bVar10;
            }
            if (bVar15) goto LAB_0000df74;
          }
LAB_0000df46:
          *(undefined1 *)(uVar7 + 0xf + param_2) = 0;
        }
      }
      else {
        *(byte *)(uVar7 + 0xf + param_2) = bVar10;
      }
LAB_0000df4c:
      uVar7 = (ulonglong)(uVar6 + uVar11);
    }
    cVar2 = FUN_0001b6e0();
    uVar5 = uVar11;
    if (cVar2 == '\x02') {
      uVar5 = uVar13;
    }
    if (uVar5 < uVar11) {
      FUN_00023370((undefined4 *)(param_2 + 0xf + (ulonglong)uVar5),5,(ulonglong)(uVar11 - uVar5));
    }
    pwVar8 = u_Disabled_00026a90;
    if (*(byte *)(lVar3 + 0x1f) != 0) {
      pwVar8 = (wchar_t *)&DAT_00025c1c;
    }
    FUN_00000680(param_1,0xcf8,(byte *)pwVar8,(ulonglong)*(byte *)(lVar3 + 0x1f));
  }
  return;
}


// ==== FUN_0000dfe0 @ 0000dfe0

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_0000dfe0(undefined8 param_1)

{
  ushort uVar1;
  char cVar2;
  char *pcVar3;
  char *pcVar4;
  char local_res10 [8];
  
  pcVar3 = (char *)0x0;
  pcVar4 = pcVar3;
  if (((_DAT_e00f8002 & 0xffe0) - 0x280 & 0xfffffbff) == 0) {
    cVar2 = FUN_0001b6e0();
    if (cVar2 == '\x01') {
      pcVar4 = s_CML_PCH_H_00028130;
    }
    else if (cVar2 == '\x02') {
      pcVar4 = s_CML_PCH_LP_00028120;
    }
  }
  else {
    cVar2 = FUN_0001b6e0();
    if (cVar2 == '\x01') {
      pcVar4 = s_CNL_PCH_H_00028150;
    }
    else if (cVar2 == '\x02') {
      pcVar4 = s_CNL_PCH_LP_00028140;
    }
  }
  FUN_00000680(param_1,0x1356,&DAT_0002672c,(ulonglong)pcVar4);
  if (DAT_00024e00 == 0xff) {
    DAT_00024e00 = DAT_e00f8008;
  }
  FUN_0001c128(local_res10,3,&DAT_000284c4,(ulonglong)((DAT_00024e00 >> 4) + 0x41));
  FUN_00000680(param_1,0x135c,&DAT_0002672c,(ulonglong)local_res10);
  uVar1 = DAT_00024a60;
  do {
    if (uVar1 == 0xffff) {
      pcVar3 = s_Undefined_SKU_000284d0;
LAB_0000e119:
      FUN_00000680(param_1,0x1359,&DAT_0002672c,(ulonglong)pcVar3);
      return;
    }
    if (_DAT_e00f8002 == uVar1) {
      pcVar3 = *(char **)((longlong)pcVar3 * 0x10 + 0x24a68);
      goto LAB_0000e119;
    }
    pcVar3 = pcVar3 + 1;
    uVar1 = (&DAT_00024a60)[(longlong)pcVar3 * 8];
  } while( true );
}


// ==== FUN_0000e57c @ 0000e57c

void FUN_0000e57c(longlong *param_1)

{
  ulonglong uVar1;
  uint local_res8 [2];
  byte local_res10 [8];
  uint local_res18 [2];
  int local_res20 [2];
  ulonglong local_28 [2];
  
  FUN_000003d0(1,(undefined4 *)0x0,(undefined4 *)0x0,(undefined4 *)0x0,local_res8);
  if (((local_res8[0] & 0x10000000) != 0) &&
     (FUN_000003a0(0xb,0,(undefined4 *)local_res10,(undefined4 *)0x0,(undefined4 *)0x0,local_res18),
     (local_res18[0] & ~(-1 << (local_res10[0] & 0x1f))) != 0)) {
    return;
  }
  local_28[0] = 0;
  (**(code **)(DAT_0002b348 + 0x30))(DAT_0002b348,local_28);
  uVar1 = local_28[0];
  if ((local_28[0] != 0) && (DAT_000293ab == '\0')) {
    uVar1 = local_28[0] >> 1;
  }
  FUN_0001bd6c(2,0x1c,local_res20,local_res8);
  *(int *)(*param_1 + uVar1 * 4) = local_res20[0];
  *(uint *)(param_1[1] + uVar1 * 4) = local_res8[0];
  return;
}


// ==== FUN_0000e640 @ 0000e640

void FUN_0000e640(undefined8 param_1,ulonglong param_2)

{
  undefined8 uVar1;
  undefined8 local_res8;
  ulonglong local_res10;
  undefined1 local_58 [49];
  char local_27;
  
  local_res8 = 699;
  local_res10 = param_2;
  (**(code **)(DAT_00029488 + 0x48))
            (u_CpuSetup_00026ae0,&DAT_000235b0,&local_res10,&local_res8,&DAT_0002acc0);
  local_res8 = 0x33;
  (**(code **)(DAT_00029488 + 0x48))
            (u_SetupCpuFeatures_00026af8,&DAT_00023710,0,&local_res8,local_58);
  if (DAT_0002ad87 == '\0') {
    DAT_0002ad87 = '\x01';
    uVar1 = rdmsr(0xce);
    DAT_0002ad88 = (undefined1)((ulonglong)uVar1 >> 8);
    uVar1 = rdmsr(0x1ad);
    DAT_0002ad89 = (undefined1)uVar1;
    DAT_0002ad8a = (undefined1)((ulonglong)uVar1 >> 8);
    DAT_0002ad8b = (undefined1)((ulonglong)uVar1 >> 0x10);
    DAT_0002ad8c = (undefined1)((ulonglong)uVar1 >> 0x18);
    DAT_0002ad8d = (undefined1)((ulonglong)uVar1 >> 0x20);
    DAT_0002ad8e = (undefined1)((ulonglong)uVar1 >> 0x28);
    DAT_0002ad8f = (undefined1)((ulonglong)uVar1 >> 0x30);
    DAT_0002ad90 = (undefined1)((ulonglong)uVar1 >> 0x38);
    if (local_27 != '\0') {
      uVar1 = rdmsr(0x1ae);
      DAT_0002af02 = (undefined1)((ulonglong)uVar1 >> 0x38);
      DAT_0002aefb = (undefined1)uVar1;
      DAT_0002aefc = (undefined1)((ulonglong)uVar1 >> 8);
      DAT_0002aefd = (undefined1)((ulonglong)uVar1 >> 0x10);
      DAT_0002aefe = (undefined1)((ulonglong)uVar1 >> 0x18);
      DAT_0002aeff = (undefined1)((ulonglong)uVar1 >> 0x20);
      DAT_0002af00 = (undefined1)((ulonglong)uVar1 >> 0x28);
      DAT_0002af01 = (undefined1)((ulonglong)uVar1 >> 0x30);
      DAT_0002af03 = DAT_0002aefb;
      DAT_0002af04 = DAT_0002aefc;
      DAT_0002af05 = DAT_0002aefd;
      DAT_0002af06 = DAT_0002aefe;
      DAT_0002af07 = DAT_0002aeff;
      DAT_0002af08 = DAT_0002af00;
      DAT_0002af09 = DAT_0002af01;
      DAT_0002af0a = DAT_0002af02;
    }
    local_res8 = 699;
    DAT_0002ad91 = DAT_0002ad89;
    DAT_0002ad92 = DAT_0002ad8a;
    DAT_0002ad93 = DAT_0002ad8b;
    DAT_0002ad94 = DAT_0002ad8c;
    DAT_0002ad95 = DAT_0002ad8d;
    DAT_0002ad96 = DAT_0002ad8e;
    DAT_0002ad97 = DAT_0002ad8f;
    DAT_0002ad98 = DAT_0002ad90;
    (**(code **)(DAT_00029488 + 0x58))
              (u_CpuSetup_00026ae0,&DAT_000235b0,local_res10 & 0xffffffff,699,&DAT_0002acc0);
  }
  return;
}


// ==== FUN_0000e9dc @ 0000e9dc

void FUN_0000e9dc(void)

{
  byte bVar1;
  byte bVar2;
  uint uVar3;
  ulonglong uVar4;
  uint uVar5;
  uint local_res8 [2];
  uint local_res10 [2];
  uint local_res18 [2];
  undefined4 local_res20 [2];
  undefined8 local_88;
  undefined8 local_80;
  undefined1 local_78 [43];
  char local_4d;
  char local_4c;
  char local_4a;
  
  local_88 = 699;
  (**(code **)(DAT_00029488 + 0x48))
            (u_CpuSetup_00026ae0,&DAT_000235b0,local_res20,&local_88,&DAT_0002acc0);
  local_80 = 0x33;
  (**(code **)(DAT_00029488 + 0x48))(u_SetupCpuFeatures_00026af8,&DAT_00023710,0,&local_80,local_78)
  ;
  FUN_0001bd6c(3,0x80000018,(int *)local_res18,local_res8);
  if (local_res8[0] == 0) {
    uVar4 = 0;
    uVar5 = local_res18[0];
    do {
      if ((&DAT_0002ae39)[uVar4] == '\x02') {
        if (local_4a == '\a') {
          (&DAT_0002ae39)[uVar4] = 0;
        }
        else if ((local_4c == '\0') && (local_4d == '\0')) {
          (&DAT_0002ae39)[uVar4] = 1;
          DAT_0002ae3d = 0;
        }
        else {
          (&DAT_0002ae39)[uVar4] = 0;
          if (uVar4 == 4) {
            DAT_0002ae3d = 1;
          }
        }
      }
      if (uVar4 == 0) {
        bVar1 = (byte)uVar5;
        bVar2 = (byte)(uVar5 >> 4);
LAB_0000eb1f:
        uVar3 = (uint)(bVar1 & 0xf);
        bVar2 = ~bVar2 & 1;
      }
      else {
        if (uVar4 == 1) {
          bVar1 = (byte)(uVar5 >> 5);
          bVar2 = (byte)(uVar5 >> 9);
          goto LAB_0000eb1f;
        }
        if (uVar4 == 3) {
          bVar1 = (byte)(uVar5 >> 0xf);
          bVar2 = (byte)(uVar5 >> 0x13);
          goto LAB_0000eb1f;
        }
        if (uVar4 == 4) {
          bVar2 = (byte)(uVar5 >> 0x18);
          bVar1 = bVar2 >> 1;
          bVar2 = bVar2 >> 5;
          goto LAB_0000eb1f;
        }
        uVar3 = 0;
        bVar2 = 0;
      }
      if (((&DAT_0002adc6)[uVar4] == '\x01') && (bVar2 == 1)) {
        uVar5 = uVar3 << 0x10;
        FUN_0001bd6c(3,uVar5 | 0x80000118,(int *)local_res10,local_res8);
        if (local_res8[0] == 0) {
          (&DAT_0002adcb)[uVar4] =
               (short)(((ulonglong)local_res10[0] & 0xffff) * 100000 + 0x80000 >> 0x14);
          (&DAT_0002add5)[uVar4] =
               (short)((ulonglong)(local_res10[0] >> 0x10) * 100000 + 0x80000 >> 0x14);
        }
        FUN_0001bd6c(3,uVar5 | 0x80000518,(int *)local_res10,local_res8);
        if (local_res8[0] == 0) {
          (&DAT_0002ae1b)[uVar4] = (ushort)local_res10[0];
        }
        FUN_0001bd6c(3,uVar5 | 0x80000718,(int *)local_res10,local_res8);
        if (local_res8[0] == 0) {
          (&DAT_0002ae25)[uVar4] = (short)(local_res10[0] * 1000 + 0x1000 >> 0xd);
        }
        FUN_0001bd6c(3,uVar3 << 8 | 0x80000019,(int *)local_res10,local_res8);
        uVar5 = local_res18[0];
        if (local_res8[0] == 0) {
          (&DAT_0002ae2f)[uVar4] = (ushort)local_res10[0] & 0x7fff;
        }
      }
      uVar4 = uVar4 + 1;
    } while (uVar4 < 4);
    (**(code **)(DAT_00029488 + 0x58))
              (u_CpuSetup_00026ae0,&DAT_000235b0,local_res20[0],local_88,&DAT_0002acc0);
  }
  return;
}


// ==== FUN_0000ec88 @ 0000ec88

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_0000ec88(ulonglong param_1,ulonglong param_2)

{
  byte bVar1;
  uint *puVar2;
  undefined8 uVar3;
  undefined4 uVar4;
  longlong lVar5;
  char *pcVar6;
  char cVar7;
  uint uVar8;
  uint uVar9;
  longlong lVar10;
  ulonglong uVar11;
  char *pcVar12;
  ulonglong uVar13;
  ulonglong uVar14;
  byte bVar15;
  char *pcVar16;
  char *pcVar17;
  byte bVar18;
  uint uVar19;
  undefined *puVar20;
  ulonglong uVar21;
  wchar_t *pwVar22;
  char cVar23;
  char *pcVar24;
  undefined8 *puVar25;
  short sVar26;
  char *pcVar27;
  byte bVar28;
  ulonglong local_res8;
  ulonglong local_res10;
  undefined4 local_res18 [2];
  uint local_res20 [2];
  undefined8 local_108;
  ushort local_100;
  ushort local_fe;
  undefined2 local_fc;
  byte local_fa;
  byte local_f9;
  undefined4 local_f8;
  undefined8 local_f0;
  undefined4 *local_e8;
  longlong local_e0;
  uint local_d8;
  uint local_d4;
  undefined4 local_d0;
  undefined4 local_cc;
  undefined4 local_c8 [2];
  longlong local_c0;
  char local_b8 [16];
  undefined4 local_a8;
  undefined4 local_a4;
  undefined4 local_a0;
  undefined4 local_9c;
  ulonglong local_98;
  undefined1 local_90 [6];
  char local_8a;
  char local_88;
  undefined1 local_7c;
  char local_5f;
  undefined1 local_58 [24];
  
  local_108 = 0x97;
  local_res8 = param_1 & 0xffffffff00000000;
  local_res10 = param_2;
  lVar10 = (**(code **)(DAT_00029488 + 0x48))
                     (u_SetupVolatileData_00026080,&DAT_00023710,0,&local_108,&DAT_0002ac20);
  if (lVar10 < 0) {
    return;
  }
  lVar10 = (**(code **)(DAT_00029478 + 0x140))(&DAT_00023770,0);
  if (lVar10 < 0) {
    return;
  }
  puVar2 = *(uint **)(local_c0 + 0x10);
  *(undefined8 *)(puVar2 + 3) = *(undefined8 *)(puVar2 + 3);
  *(undefined8 *)(puVar2 + 9) = *(undefined8 *)(*(longlong *)(local_c0 + 0x10) + 0x24);
  uVar3 = rdmsr(0xce);
  uVar14 = 1;
  puVar2[8] = 0;
  puVar2[6] = (((uint)uVar3 >> 8 & 0xff) * 10000) / 100;
  FUN_000003d0(1,(undefined4 *)0x0,(undefined4 *)0x0,local_res20,(undefined4 *)0x0);
  if ((local_res20[0] & 0x800) == 0) {
LAB_0000eda0:
    pcVar24 = s_Disabled_00026b28;
  }
  else {
    uVar11 = rdmsr(0xc80);
    pcVar24 = s_Enabled_00026b20;
    if ((uVar11 & 0x80000000) == 0) goto LAB_0000eda0;
  }
  FUN_00000680(DAT_0002a438,0x1808,&DAT_0002672c,(ulonglong)pcVar24);
  FUN_00000680(DAT_0002a438,0x261,&DAT_0002672c,*(ulonglong *)(puVar2 + 3));
  FUN_00000680(DAT_0002a438,0x266,(byte *)u__d_MHz_00026b38,(ulonglong)puVar2[6]);
  FUN_00000680(DAT_0002a438,0x263,(byte *)u_0x_X_00026b48,(ulonglong)*puVar2);
  uVar3 = rdmsr(0x8b);
  uVar8 = (uint)((ulonglong)uVar3 >> 0x20);
  if (uVar8 != 0) {
    FUN_00000680(DAT_0002a438,0x14ea,&DAT_00026b54,(ulonglong)uVar8);
  }
  FUN_00000680(DAT_0002a438,0x14ed,(byte *)u__dCore_s_____dThread_s__00026b60,
               (ulonglong)*(byte *)((longlong)puVar2 + 0x16));
  uVar11 = 0;
  do {
    lVar10 = *(longlong *)(puVar2 + 9);
    lVar5 = uVar11 * 9;
    cVar7 = *(char *)(lVar5 + 1 + lVar10);
    if (cVar7 == '\x01') {
      cVar7 = *(char *)(lVar5 + 2 + lVar10);
      if (cVar7 == '\x01') {
        uVar21 = (ulonglong)*(uint *)(lVar5 + 3 + lVar10);
        sVar26 = 0x269;
LAB_0000eef9:
        pwVar22 = u__d_KB_00026b90;
        if (*(char *)((longlong)puVar2 + 0x16) == '\x01') goto LAB_0000eee2;
        FUN_00000680(DAT_0002a438,sVar26,(byte *)u__d_KB_x__d_00026ba0,uVar21);
      }
      else if (cVar7 == '\x02') {
        uVar21 = (ulonglong)*(uint *)(lVar5 + 3 + lVar10);
        sVar26 = 0x26c;
        goto LAB_0000eef9;
      }
    }
    else {
      if (cVar7 == '\x02') {
        uVar21 = (ulonglong)*(uint *)(lVar5 + 3 + lVar10);
        sVar26 = 0x26f;
        goto LAB_0000eef9;
      }
      if (cVar7 == '\x03') {
        sVar26 = 0x272;
      }
      else {
        if (cVar7 != '\x04') goto LAB_0000ef48;
        sVar26 = 0x275;
      }
      uVar21 = (ulonglong)(*(uint *)(lVar5 + 3 + lVar10) >> 10);
      pwVar22 = u__d_MB_000266c8;
LAB_0000eee2:
      FUN_00000680(DAT_0002a438,sVar26,(byte *)pwVar22,uVar21);
    }
LAB_0000ef48:
    bVar18 = (char)uVar11 + 1;
    uVar11 = (ulonglong)bVar18;
  } while (bVar18 <= (byte)puVar2[0xb]);
  uVar8 = FUN_0001bb38();
  uVar11 = FUN_0001bba0();
  uVar19 = (uint)uVar11 & 0xff;
  uVar9 = FUN_0001bb6c();
  pcVar24 = s_CoffeeLake_00026bd8;
  pcVar27 = s_WhiskeyLake_00026bc8;
  pcVar16 = s_CometLake_00026bb8;
  if ((uVar8 == 0x60660) || (uVar8 == 0x60670)) {
    pcVar17 = s_CannonLake_00026be8;
  }
  else if (uVar8 == 0x806e0) {
    if ((int)uVar9 < 0xb) goto LAB_0000efe6;
    if ((uVar9 == 0xc) && (1 < (ushort)(_DAT_e0010002 + 0xc160U))) goto LAB_0000efc3;
    pcVar17 = s_WhiskeyLake_00026bc8;
  }
  else if (uVar8 == 0x906e0) {
LAB_0000efe6:
    pcVar17 = s_CoffeeLake_00026bd8;
  }
  else if ((uVar8 == 0xa0650) || (uVar8 == 0xa0660)) {
LAB_0000efc3:
    pcVar17 = s_CometLake_00026bb8;
  }
  else {
    pcVar17 = (char *)0x0;
  }
  if ((uVar11 & 0xff) == 0) {
    puVar20 = &DAT_00026bf4;
    if (pcVar17 == (char *)0x0) {
LAB_0000f170:
      pcVar24 = s_BGA1510_00026c00;
    }
    else {
      cVar23 = *pcVar17;
      cVar7 = cVar23;
      pcVar12 = pcVar17;
      while ((cVar7 != '\0' && (cVar7 == *pcVar24))) {
        pcVar12 = pcVar12 + 1;
        pcVar24 = pcVar24 + 1;
        cVar7 = *pcVar12;
      }
      cVar7 = cVar23;
      pcVar6 = pcVar17;
      if (*pcVar12 != *pcVar24) {
        while ((cVar7 != '\0' && (cVar7 == *pcVar27))) {
          pcVar27 = pcVar27 + 1;
          cVar7 = pcVar6[1];
          pcVar6 = pcVar6 + 1;
        }
        pcVar24 = pcVar17;
        if (*pcVar6 != *pcVar27) {
          while ((cVar23 != '\0' && (cVar23 == *pcVar16))) {
            pcVar16 = pcVar16 + 1;
            cVar23 = pcVar24[1];
            pcVar24 = pcVar24 + 1;
          }
          if (*pcVar24 != *pcVar16) goto LAB_0000f170;
        }
      }
      pcVar24 = s_BGA1528_00026bf8;
    }
    goto LAB_0000f177;
  }
  if (uVar19 == 1) {
    puVar20 = &DAT_00026c18;
    if (pcVar17 != (char *)0x0) {
      cVar7 = *pcVar17;
      pcVar24 = pcVar17;
      while ((cVar7 != '\0' && (cVar7 == *pcVar16))) {
        pcVar24 = pcVar24 + 1;
        pcVar16 = pcVar16 + 1;
        cVar7 = *pcVar24;
      }
      if (*pcVar24 == *pcVar16) {
        pcVar24 = s_LGA1200_00026c20;
        goto LAB_0000f177;
      }
    }
    pcVar24 = s_LGA1151_00026c28;
    goto LAB_0000f177;
  }
  if (uVar19 == 2) {
    puVar20 = &DAT_00026c08;
    pcVar24 = s_BGA1392_00026c10;
    goto LAB_0000f177;
  }
  if (uVar19 != 3) {
    puVar20 = (undefined *)0x0;
    pcVar24 = s_Unknown_000266a8;
    goto LAB_0000f177;
  }
  puVar20 = &DAT_00026c30;
  if (pcVar17 == (char *)0x0) {
LAB_0000f084:
    pcVar24 = s_BGA1287_00026c40;
  }
  else {
    cVar23 = *pcVar17;
    cVar7 = cVar23;
    pcVar27 = pcVar17;
    while ((cVar7 != '\0' && (cVar7 == *pcVar24))) {
      pcVar27 = pcVar27 + 1;
      pcVar24 = pcVar24 + 1;
      cVar7 = *pcVar27;
    }
    pcVar12 = pcVar17;
    if (*pcVar27 != *pcVar24) {
      while ((cVar23 != '\0' && (cVar23 == *pcVar16))) {
        pcVar16 = pcVar16 + 1;
        cVar23 = pcVar12[1];
        pcVar12 = pcVar12 + 1;
      }
      if (*pcVar12 != *pcVar16) goto LAB_0000f084;
    }
    pcVar24 = s_BGA1440_00026c38;
  }
LAB_0000f177:
  FUN_00000680(DAT_0002a438,0x14e7,&DAT_0002672c,(ulonglong)pcVar24);
  if ((pcVar17 == (char *)0x0) || (puVar20 == (undefined *)0x0)) {
    FUN_00000680(DAT_0002a438,0x14e1,&DAT_0002672c,0x266a8);
  }
  else {
    FUN_00000680(DAT_0002a438,0x14e1,(byte *)u__a__a_00026c48,(ulonglong)pcVar17);
  }
  local_108 = 0x33;
  puVar25 = &local_108;
  lVar10 = (**(code **)(DAT_00029488 + 0x48))
                     (u_SetupCpuFeatures_00026af8,&DAT_00023710,&local_d0,puVar25,local_90);
  if (-1 < lVar10) {
    pcVar24 = s_Supported_00026840;
    bVar18 = 0;
    if (local_8a == '\0') {
      pcVar24 = s_Not_Supported_00026c58;
    }
    FUN_0001c128(local_b8,0xf,(byte *)pcVar24,(ulonglong)puVar25);
    pcVar24 = local_b8;
    FUN_00000680(DAT_0002a438,0x279,&DAT_0002672c,(ulonglong)pcVar24);
    pcVar27 = s_Supported_00026840;
    if (local_88 == '\0') {
      pcVar27 = s_Not_Supported_00026c58;
    }
    FUN_0001c128(local_b8,0xf,(byte *)pcVar27,(ulonglong)pcVar24);
    FUN_00000680(DAT_0002a438,0x27c,&DAT_0002672c,(ulonglong)local_b8);
    uVar3 = rdmsr(0x606);
    bVar28 = '\x02' << (((byte)uVar3 & 0xf) - 1 & 0x1f);
    if (bVar28 != 0) {
      uVar3 = rdmsr(0x614);
      uVar21 = (ulonglong)bVar28;
      FUN_00000680(DAT_0002a438,0x38f,(byte *)u__d__d_00026c68,0x7fff / uVar21);
      FUN_00000680(DAT_0002a438,0x392,(byte *)u__d__d_00026c68,
                   ((uint)((ulonglong)uVar3 >> 0x10) & 0x7fff) / uVar21);
      uVar3 = rdmsr(0x614);
      FUN_00000680(DAT_0002a438,0x39b,(byte *)u__d__d_00026c68,((uint)uVar3 & 0x7fff) / uVar21);
      local_f0 = rdmsr(0x610);
      FUN_00000680(DAT_0002a438,0x395,(byte *)u__d__d_00026c68,((uint)local_f0 & 0x7fff) / uVar21);
      FUN_00000680(DAT_0002a438,0x398,(byte *)u__d__d_00026c68,(local_f0._4_4_ & 0x7fff) / uVar21);
      uVar11 = rdmsr(0x1ad);
      if (DAT_000293a4 == '\0') {
        DAT_000293a4 = (char)uVar11;
      }
      FUN_00000680(DAT_0002a438,0x454,&DAT_00025c1c,uVar11 & 0xff);
      if (DAT_000293aa == '\0') {
        DAT_000293aa = (char)(uVar11 >> 8);
      }
      FUN_00000680(DAT_0002a438,0x457,&DAT_00025c1c,uVar11 >> 8 & 0xff);
      if (DAT_000293af == '\0') {
        DAT_000293af = (char)(uVar11 >> 0x10);
      }
      FUN_00000680(DAT_0002a438,0x45a,&DAT_00025c1c,uVar11 >> 0x10 & 0xff);
      if (DAT_000293a5 == '\0') {
        DAT_000293a5 = (char)(uVar11 >> 0x18);
      }
      FUN_00000680(DAT_0002a438,0x45d,&DAT_00025c1c,uVar11 >> 0x18 & 0xff);
      if (DAT_000293a9 == '\0') {
        DAT_000293a9 = (char)(uVar11 >> 0x20);
      }
      FUN_00000680(DAT_0002a438,0x460,&DAT_00025c1c,(uVar11 & 0xff00000000) >> 0x20);
      if (DAT_000293a6 == '\0') {
        DAT_000293a6 = (char)(uVar11 >> 0x28);
      }
      FUN_00000680(DAT_0002a438,0x463,&DAT_00025c1c,(uVar11 & 0xff0000000000) >> 0x28);
      if (DAT_000293b0 == '\0') {
        DAT_000293b0 = (char)(uVar11 >> 0x30);
      }
      FUN_00000680(DAT_0002a438,0x466,&DAT_00025c1c,(uVar11 & 0xff000000000000) >> 0x30);
      if (DAT_000293ae == '\0') {
        DAT_000293ae = (char)(uVar11 >> 0x38);
      }
      FUN_00000680(DAT_0002a438,0x469,&DAT_00025c1c,uVar11 >> 0x38);
      if (local_5f != '\0') {
        uVar11 = rdmsr(0x1ae);
        if (DAT_000293ac == '\0') {
          DAT_000293ac = (char)uVar11;
        }
        FUN_00000680(DAT_0002a438,0x43c,&DAT_00025c1c,uVar11 & 0xff);
        if (DAT_000293a2 == '\0') {
          DAT_000293a2 = (char)(uVar11 >> 8);
        }
        FUN_00000680(DAT_0002a438,0x43f,&DAT_00025c1c,uVar11 >> 8 & 0xff);
        if (DAT_000293b1 == '\0') {
          DAT_000293b1 = (char)(uVar11 >> 0x10);
        }
        FUN_00000680(DAT_0002a438,0x442,&DAT_00025c1c,uVar11 >> 0x10 & 0xff);
        if (DAT_000293a7 == '\0') {
          DAT_000293a7 = (char)(uVar11 >> 0x18);
        }
        FUN_00000680(DAT_0002a438,0x445,&DAT_00025c1c,uVar11 >> 0x18 & 0xff);
        if (DAT_000293a8 == '\0') {
          DAT_000293a8 = (char)(uVar11 >> 0x20);
        }
        FUN_00000680(DAT_0002a438,0x448,&DAT_00025c1c,(uVar11 & 0xff00000000) >> 0x20);
        if (DAT_000293a1 == '\0') {
          DAT_000293a1 = (char)(uVar11 >> 0x28);
        }
        FUN_00000680(DAT_0002a438,1099,&DAT_00025c1c,(uVar11 & 0xff0000000000) >> 0x28);
        if (DAT_000293ad == '\0') {
          DAT_000293ad = (char)(uVar11 >> 0x30);
        }
        FUN_00000680(DAT_0002a438,0x44e,&DAT_00025c1c,(uVar11 & 0xff000000000000) >> 0x30);
        if (DAT_000293a3 == '\0') {
          DAT_000293a3 = (char)(uVar11 >> 0x38);
        }
        FUN_00000680(DAT_0002a438,0x451,&DAT_00025c1c,uVar11 >> 0x38);
      }
      uVar11 = rdmsr(0xce);
      FUN_00000680(DAT_0002a438,0x2cd,&DAT_00025c1c,(ulonglong)(((byte)(uVar11 >> 0x21) & 3) + 1));
      if ((uVar11 >> 0x21 & 3) != 0) {
        uVar11 = rdmsr(0x648);
        rdmsr(0x614);
        FUN_00000680(DAT_0002a438,0x2d0,(byte *)u_Ratio__d_TAR__d_PL1__d__dW_00026c78,uVar11 & 0xff)
        ;
        uVar11 = rdmsr(0x649);
        FUN_00000680(DAT_0002a438,0x2d3,(byte *)u_Ratio__d_TAR__d_PL1__d__dW_00026c78,
                     uVar11 >> 0x10 & 0xff);
        uVar11 = rdmsr(0x64a);
        FUN_00000680(DAT_0002a438,0x2d6,(byte *)u_Ratio__d_TAR__d_PL1__d__dW_00026c78,
                     uVar11 >> 0x10 & 0xff);
        rdmsr(0x610);
        FUN_00000680(DAT_0002a438,0x2df,(byte *)u__d__dW__MSR__d__d__00026cb0,
                     (_DAT_fed159a0 & 0x7fff) / uVar21);
        rdmsr(0x610);
        FUN_00000680(DAT_0002a438,0x2e2,(byte *)u__d__dW__MSR__d__d__00026cb0,
                     (_DAT_fed159a4 & 0x7fff) / uVar21);
        uVar11 = rdmsr(0x64c);
        pwVar22 = u__d__Locked__00026cd8;
        if (-1 < (int)uVar11) {
          pwVar22 = u__d__Unlocked__00026cf0;
        }
        FUN_00000680(DAT_0002a438,0x2dc,(byte *)pwVar22,uVar11 & 0xff);
      }
      local_108 = 0xc;
      lVar10 = (**(code **)(DAT_00029488 + 0x48))
                         (u_CpuSetupVolatileData_00026d10,&DAT_000235b0,&local_res10,&local_108,
                          &local_100);
      uVar4 = (undefined4)local_res10;
      if (lVar10 < 0) {
        uVar4 = 6;
      }
      local_res10 = CONCAT44(local_res10._4_4_,uVar4);
      FUN_0001bd6c(3,0x80000018,(int *)&local_d4,&local_d8);
      if (local_d8 == 0) {
        local_f8 = CONCAT31(0x10000,(char)(local_d4 >> 9)) & 0xffffff01;
        local_f8 = CONCAT22(local_f8._2_2_,CONCAT11((char)(local_d4 >> 4),(undefined1)local_f8)) &
                   0xffff01ff;
        local_f8 = CONCAT13(local_f8._3_1_,CONCAT12((char)(local_d4 >> 0x13),(undefined2)local_f8))
                   & 0xff01ffff;
      }
      else {
        local_f8 = 0;
      }
      FUN_000003d0(1,&local_a8,&local_a4,&local_a0,&local_9c);
      local_100 = (ushort)local_a8 & 0x3ff0;
      local_fe = (ushort)((uint)local_a8 >> 0x10) & 0xfff;
      local_fa = (byte)local_a8 & 0xf;
      local_fc = _DAT_e0000002;
      uVar3 = rdmsr(0xce);
      local_f9 = (byte)((ulonglong)uVar3 >> 0x39) & 1;
      (**(code **)(DAT_00029488 + 0x58))
                (u_CpuSetupVolatileData_00026d10,&DAT_000235b0,local_res10 & 0xffffffff,0xc,
                 &local_100);
      FUN_000003d0(0x15,(undefined4 *)0x0,(undefined4 *)0x0,(undefined4 *)&local_res8,
                   (undefined4 *)0x0);
      if ((int)local_res8 == 19200000) {
        pcVar24 = s_Adjust_Nominal_Frequency__139_5M_00026d40;
      }
      else {
        pcVar24 = s_Adjust_Nominal_Frequency__139_5M_00026e80;
        if ((int)local_res8 != 24000000) {
          pcVar24 = s_Unexpected_Clock_Frequency__00026fc0;
        }
      }
      FUN_00000680(DAT_0002a438,0x24b,(byte *)u__d__dMHz_00026fe0,0);
      FUN_00000680(DAT_0002a438,0x24d,&DAT_0002672c,(ulonglong)pcVar24);
      local_108 = 0x10;
      lVar10 = (**(code **)(DAT_00029488 + 0x48))
                         (u_CpuSetupSgxEpochData_00026ff8,&DAT_000235b0,local_res18,&local_108,
                          local_58);
      if (lVar10 < 0) {
        local_res18[0] = 3;
      }
      (**(code **)(DAT_00029488 + 0x58))
                (u_CpuSetupSgxEpochData_00026ff8,&DAT_000235b0,local_res18[0],0x10,local_58);
      lVar10 = (**(code **)(DAT_00029478 + 0x140))(&DAT_00023490,0,&DAT_0002b348);
      if (-1 < lVar10) {
        uVar11 = rdmsr(0x35);
        uVar21 = uVar11 & 0xffff;
        uVar11 = uVar11 >> 0x10 & 0xffff;
        if (uVar11 == uVar21) {
          DAT_000293ab = 1;
        }
        local_e8 = (undefined4 *)FUN_0001b544(uVar11 << 2);
        local_e0 = FUN_0001b544(uVar11 << 3);
        if ((local_e8 != (undefined4 *)0x0) && (local_e0 != 0)) {
          (**(code **)(DAT_0002b348 + 0x30))(DAT_0002b348,&local_98);
          if (uVar21 != 0) {
            uVar13 = 0;
            do {
              if (uVar13 == local_98) {
                FUN_0000e57c((longlong *)&local_e8);
              }
              else {
                (**(code **)(DAT_0002b348 + 0x18))(DAT_0002b348,FUN_0000e57c,uVar13,0,0,&local_e8,0)
                ;
              }
              bVar18 = bVar18 + 1;
              uVar13 = (ulonglong)bVar18;
            } while (uVar13 < uVar21);
          }
          uVar21 = 0;
          if (uVar11 != 0) {
            do {
              FUN_00000680(DAT_0002a438,(&DAT_000272e0)[uVar21],&DAT_00025c1c,
                           (ulonglong)*(byte *)(local_e8 + uVar21));
              uVar21 = uVar21 + 1;
            } while (uVar21 < uVar11);
          }
          bVar18 = 0;
          local_7c = 0;
          if (1 < uVar11) {
            do {
              if ((char)((uint)*local_e8 >> 8) != (char)((uint)local_e8[uVar14] >> 8)) {
                local_7c = 1;
                break;
              }
              uVar14 = uVar14 + 1;
            } while (uVar14 < uVar11);
          }
          (**(code **)(DAT_00029488 + 0x58))
                    (u_SetupCpuFeatures_00026af8,&DAT_00023710,local_d0,0x33,local_90);
          if (*(char *)(*(longlong *)(local_c0 + 0x10) + 0x42) != '\0') {
            bVar28 = 0xff;
            if (uVar11 != 0) {
              uVar14 = 0;
              bVar15 = bVar18;
              do {
                bVar1 = *(byte *)((longlong)local_e8 + uVar14 * 4 + 1);
                if (bVar1 < bVar28) {
                  bVar28 = bVar1;
                }
                bVar15 = bVar15 + 1;
                uVar14 = (ulonglong)bVar15;
              } while (uVar14 < uVar11);
            }
            if (uVar11 != 0) {
              uVar14 = 0;
              bVar28 = bVar18;
              do {
                if (bVar18 < *(byte *)(local_e8 + uVar14)) {
                  bVar18 = *(byte *)(local_e8 + uVar14);
                }
                bVar28 = bVar28 + 1;
                uVar14 = (ulonglong)bVar28;
              } while (uVar14 < uVar11);
            }
            local_108 = 699;
            (**(code **)(DAT_00029488 + 0x48))
                      (u_CpuSetup_00026ae0,&DAT_000235b0,&local_cc,&local_108,&DAT_0002acc0);
            uVar14 = 0;
            DAT_0002ad91 = bVar18;
            DAT_0002ae79 = bVar18;
            if (uVar11 != 0) {
              do {
                (&DAT_0002af6f)[uVar14] = *(undefined1 *)(local_e8 + uVar14);
                uVar14 = uVar14 + 1;
              } while (uVar14 < uVar11);
            }
            (**(code **)(DAT_00029488 + 0x58))
                      (u_CpuSetup_00026ae0,&DAT_000235b0,local_cc,local_108,&DAT_0002acc0);
          }
          local_f0 = 699;
          lVar10 = (**(code **)(DAT_00029488 + 0x48))
                             (u_CpuSetup_00026ae0,&DAT_000235b0,local_c8,&local_f0,&DAT_0002acc0);
          if (-1 < lVar10) {
            if (DAT_0002acc3 == '\0') {
              uVar3 = rdmsr(0xce);
              DAT_0002acc2 = (undefined1)((ulonglong)uVar3 >> 8);
            }
            uVar3 = rdmsr(0xce);
            DAT_0002acc1 = (undefined1)((ulonglong)uVar3 >> 8);
            (**(code **)(DAT_00029488 + 0x58))
                      (u_CpuSetup_00026ae0,&DAT_000235b0,local_c8[0],local_f0,&DAT_0002acc0);
          }
          FUN_00001b1c(0x2731,0x10310);
          FUN_00001b1c(0x2732,0x10310);
          FUN_00001b1c(0x2733,0x10310);
          FUN_00001b1c(0x2734,0x10310);
          FUN_00001b1c(0x2735,0x10310);
          FUN_00001b1c(0x2736,0x10310);
          FUN_00001b1c(0x2737,0x10310);
          FUN_00001b1c(0x2738,0x10310);
          FUN_00001b1c(0x2729,0x10310);
          FUN_00001b1c(0x272a,0x10310);
          FUN_00001b1c(0x272b,0x10310);
          FUN_00001b1c(0x272c,0x10310);
          FUN_00001b1c(0x272d,0x10310);
          FUN_00001b1c(0x272e,0x10310);
          FUN_00001b1c(0x272f,0x10310);
          FUN_00001b1c(0x2730,0x10310);
          FUN_00001b1c(0x2727,0x10310);
          FUN_00001b1c(0x2739,0x10acc);
          FUN_00001b1c(0x2724,0x10dec);
          FUN_00001b1c(0x2725,0x110a0);
          FUN_00001b1c(0x2726,0x10f7c);
          FUN_00001b1c(0x2728,0xe888);
        }
      }
    }
  }
  return;
}


// ==== FUN_00010cd0 @ 00010cd0

undefined8 FUN_00010cd0(undefined8 param_1)

{
  ulonglong uVar1;
  bool bVar2;
  uint uVar3;
  longlong lVar4;
  undefined8 uVar5;
  ulonglong uVar6;
  short *psVar7;
  byte bVar8;
  int iVar9;
  longlong local_res8;
  
  lVar4 = FUN_0001b514(param_1,699);
  if (lVar4 == 0) {
    uVar5 = 0x8000000000000009;
  }
  else {
    bVar2 = FUN_000213f0(&DAT_000235b0,u_CpuSetup_00026ae0,699,lVar4);
    if (bVar2) {
      iVar9 = 0;
      uVar1 = rdmsr(0x1fb);
      uVar6 = uVar1 & 0xffffffff;
      uVar3 = (uint)uVar1;
      if (uVar3 != 0) {
        bVar8 = 0x1f;
        while (-1 < (int)uVar3) {
          bVar8 = bVar8 - 1;
          uVar3 = (int)uVar6 * 2;
          uVar6 = (ulonglong)uVar3;
        }
        iVar9 = 1 << (bVar8 & 0x1f);
      }
      *(int *)(lVar4 + 0xe3) = iVar9;
      psVar7 = FUN_0001b458((short *)0x0,0xe3);
      if (psVar7 != (short *)0x0) {
        bVar2 = FUN_000214e4(&DAT_000235b0,u_CpuSetup_00026ae0,699,lVar4,psVar7);
        if (!bVar2) {
          local_res8 = -0x7ffffffffffffff2;
        }
        (**(code **)(DAT_00029478 + 0x48))(lVar4);
        if (local_res8 < 0) {
          return 0x800000000000000e;
        }
        (**(code **)(DAT_00029478 + 0x48))(psVar7);
      }
      uVar5 = 0;
    }
    else {
      uVar5 = 0x800000000000000e;
    }
  }
  return uVar5;
}


// ==== FUN_000110a0 @ 000110a0

longlong FUN_000110a0(longlong param_1)

{
  bool bVar1;
  longlong lVar2;
  undefined8 *puVar3;
  short *psVar4;
  short *psVar5;
  short *psVar6;
  short *psVar7;
  undefined *puVar8;
  ulonglong uVar9;
  longlong lVar10;
  undefined1 local_res8 [2];
  short local_resa;
  undefined8 local_res10;
  undefined8 local_res18;
  undefined8 uVar11;
  
  psVar7 = (short *)0x0;
  local_res10 = 0;
  if (*(longlong *)(param_1 + 8) == 0) {
    return 0;
  }
  if (*(longlong *)(param_1 + 8) != 1) {
    return -0x7ffffffffffffffd;
  }
  if (*(short *)(param_1 + 0x10) != 0x2725) {
    return -0x7ffffffffffffffd;
  }
  lVar2 = FUN_0001b514(param_1,699);
  if (lVar2 == 0) {
    return -0x7ffffffffffffff2;
  }
  puVar8 = &DAT_000235b0;
  bVar1 = FUN_000213f0(&DAT_000235b0,u_CpuSetup_00026ae0,699,lVar2);
  if (!bVar1) {
    return -0x7ffffffffffffff2;
  }
  puVar3 = (undefined8 *)FUN_0001b514(puVar8,0x10);
  if (puVar3 == (undefined8 *)0x0) {
    return -0x7ffffffffffffff2;
  }
  bVar1 = FUN_000213f0(&DAT_000235b0,u_CpuSetupSgxEpochData_00026ff8,0x10,puVar3);
  if (!bVar1) {
    return -0x7ffffffffffffff2;
  }
  if (2 < *(byte *)(lVar2 + 0xe1)) {
    return -0x7ffffffffffffffd;
  }
  psVar4 = (short *)FUN_0001b544(400);
  if (psVar4 == (short *)0x0) {
LAB_00011194:
    (**(code **)(DAT_00029478 + 0x48))(lVar2);
    (**(code **)(DAT_00029478 + 0x48))(puVar3);
    return -0x7ffffffffffffff7;
  }
  psVar5 = (short *)FUN_0001b544(400);
  if (psVar5 == (short *)0x0) {
    (**(code **)(DAT_00029478 + 0x48))(psVar4);
    goto LAB_00011194;
  }
  psVar6 = (short *)FUN_0001b544(400);
  if (psVar6 == (short *)0x0) {
    (**(code **)(DAT_00029478 + 0x48))();
    (**(code **)(DAT_00029478 + 0x48))(psVar5);
    lVar10 = -0x7ffffffffffffff7;
    goto LAB_000114d8;
  }
  uVar9 = 200;
  FUN_0001cff0(psVar4,200,u_Warning__EPOCH_change____00027030);
  FUN_0001cff0(psVar5,uVar9,u_All_persistent_data_protected_by_00027070);
  FUN_0001cff0(psVar6,uVar9,u_Press__Y__if_you_wish_to_continu_00027130);
  uVar11 = 0;
  FUN_0001f4fc(0x47,(longlong)local_res8,psVar4,psVar5);
  if ((local_resa - 0x59U & 0xffdf) != 0) {
    (**(code **)(DAT_00029478 + 0x48))(psVar4);
    (**(code **)(DAT_00029478 + 0x48))(psVar5);
    (**(code **)(DAT_00029478 + 0x48))(psVar6);
    local_res18 = 699;
    lVar10 = (**(code **)(DAT_00029488 + 0x48))
                       (u_CpuSetup_00026ae0,&DAT_000235b0,0,&local_res18,&DAT_0002acc0,uVar11);
    if (lVar10 == 0) {
      if (*(char *)(lVar2 + 0xe1) != DAT_0002ada1) {
        *(char *)(lVar2 + 0xe1) = DAT_0002ada1;
        psVar7 = FUN_0001b458((short *)0x0,0xe1);
        bVar1 = FUN_000214e4(&DAT_000235b0,u_CpuSetup_00026ae0,699,lVar2,psVar7);
        if (!bVar1) {
          (**(code **)(DAT_00029478 + 0x48))(lVar2);
          return -0x7ffffffffffffff2;
        }
      }
      lVar10 = -0x7ffffffffffffffd;
    }
    goto LAB_000114d8;
  }
  if (*(char *)(lVar2 + 0xe1) == '\x01') {
    uVar11 = FUN_000230d4(&local_res10);
    if ((char)uVar11 != '\0') {
      *puVar3 = local_res10;
      uVar11 = FUN_000230d4(&local_res10);
      if ((char)uVar11 != '\0') {
        puVar3[1] = local_res10;
        *(undefined1 *)(lVar2 + 0xe1) = 0;
        psVar7 = FUN_0001b458((short *)0x0,0xe1);
        goto LAB_000113a6;
      }
    }
  }
  else {
LAB_000113a6:
    if (*(char *)(lVar2 + 0xe1) == '\x02') {
      *puVar3 = 0;
      puVar3[1] = 0;
      uVar9 = 200;
      *(undefined1 *)(lVar2 + 0xe2) = 1;
      FUN_0001cff0(psVar4,200,u_Please_make_sure_you_write_down_t_000271c0);
      FUN_0001cff0(psVar5,uVar9,u_They_will_not_be_visible_after_e_00027230);
      FUN_0001cff0(psVar6,uVar9,u_Press_any_key_to_continue_000272a0);
      FUN_0001f4fc(0x17,(longlong)local_res8,psVar4,psVar5);
      (**(code **)(DAT_00029478 + 0x48))(psVar4);
      (**(code **)(DAT_00029478 + 0x48))(psVar5);
      (**(code **)(DAT_00029478 + 0x48))(psVar6);
    }
    psVar7 = FUN_0001b458(psVar7,0xe2);
    if ((psVar7 == (short *)0x0) ||
       (bVar1 = FUN_000214e4(&DAT_000235b0,u_CpuSetup_00026ae0,699,lVar2,psVar7), bVar1)) {
      psVar7 = FUN_0001b458((short *)0x0,0);
      psVar7 = FUN_0001b458(psVar7,8);
      if ((psVar7 == (short *)0x0) ||
         (bVar1 = FUN_000214e4(&DAT_000235b0,u_CpuSetupSgxEpochData_00026ff8,0x10,puVar3,psVar7),
         bVar1)) {
        (**(code **)(DAT_00029478 + 0x48))(psVar7);
        (**(code **)(DAT_00029478 + 0x48))(lVar2);
        (**(code **)(DAT_00029478 + 0x48))(puVar3);
        return 0;
      }
    }
    (**(code **)(DAT_00029478 + 0x48))(psVar7);
  }
  lVar10 = -0x7ffffffffffffff2;
LAB_000114d8:
  (**(code **)(DAT_00029478 + 0x48))(lVar2);
  (**(code **)(DAT_00029478 + 0x48))(puVar3);
  return lVar10;
}


// ==== FUN_0001153c @ 0001153c

void FUN_0001153c(undefined8 param_1)

{
  if (DAT_000f0018 != 0xff) {
    FUN_00000680(param_1,0x1919,(byte *)u__02x__02x_000272f8,(ulonglong)DAT_000f0018);
  }
  return;
}


// ==== FUN_00012508 @ 00012508

void FUN_00012508(void)

{
  undefined8 local_res8;
  undefined1 local_13e8 [48];
  undefined1 local_13b8 [544];
  undefined1 local_1198 [704];
  undefined1 local_ed8 [1776];
  undefined1 local_7e8 [2016];
  
  local_res8 = 0x7d8;
  (**(code **)(DAT_00029488 + 0x48))(u_Setup_000262c8,&DAT_00023710,0,&local_res8,local_7e8);
  (**(code **)(DAT_00029488 + 0x58))(u_ColdReset_00027490,&DAT_00023710,2,local_res8,local_7e8);
  local_res8 = 0x21d;
  (**(code **)(DAT_00029488 + 0x48))(u_SaSetup_00026070,&DAT_000238f0,0,&local_res8,local_13b8);
  (**(code **)(DAT_00029488 + 0x58))(u_SaColdReset_000274a8,&DAT_000238f0,2,local_res8,local_13b8);
  local_res8 = 0x2e;
  (**(code **)(DAT_00029488 + 0x48))(u_MeSetup_00026320,&DAT_000238b0,0,&local_res8,local_13e8);
  (**(code **)(DAT_00029488 + 0x58))(u_MeColdReset_000274c0,&DAT_000238b0,2,local_res8,local_13e8);
  local_res8 = 699;
  (**(code **)(DAT_00029488 + 0x48))(u_CpuSetup_00026ae0,&DAT_000235b0,0,&local_res8,local_1198);
  (**(code **)(DAT_00029488 + 0x58))(u_CpuColdReset_000274d8,&DAT_000235b0,2,local_res8,local_1198);
  local_res8 = 0x6ec;
  (**(code **)(DAT_00029488 + 0x48))(u_PchSetup_00026308,&DAT_000238c0,0,&local_res8,local_ed8);
  (**(code **)(DAT_00029488 + 0x58))(u_PchColdReset_000274f8,&DAT_000238c0,2,local_res8,local_ed8);
  return;
}


// ==== FUN_00012730 @ 00012730

void FUN_00012730(void)

{
  longlong lVar1;
  int iVar2;
  undefined4 uVar3;
  undefined8 local_res8 [4];
  undefined1 local_68 [45];
  char local_3b;
  undefined1 local_38 [45];
  char local_b;
  
  local_res8[0] = 0x2e;
  (**(code **)(DAT_00029488 + 0x48))(u_MeColdReset_000274c0,&DAT_000238b0,0,local_res8,local_38);
  local_res8[0] = 0x2e;
  lVar1 = (**(code **)(DAT_00029488 + 0x48))(u_MeSetup_00026320,&DAT_000238b0,0,local_res8,local_68)
  ;
  if ((-1 < lVar1) && (local_3b != local_b)) {
    DAT_00029468 = 1;
    if (local_3b == '\x01') {
      uVar3 = 0;
      iVar2 = 0x20000000;
    }
    else {
      uVar3 = 0x20000000;
      iVar2 = 0;
    }
    FUN_00020524(iVar2,uVar3);
  }
  return;
}


// ==== FUN_000127dc @ 000127dc

undefined8 FUN_000127dc(char *param_1,char param_2,undefined8 *param_3)

{
  char cVar1;
  undefined8 uVar2;
  char *pcVar3;
  char *pcVar4;
  longlong lVar5;
  ulonglong uVar6;
  
  if (param_2 == '\0') {
    uVar2 = FUN_0001b544(1);
    *param_3 = uVar2;
  }
  else {
    uVar6 = 0;
    pcVar4 = param_1;
    do {
      pcVar4 = pcVar4 + uVar6;
      param_2 = param_2 + -1;
      lVar5 = 0;
      cVar1 = *pcVar4;
      while (cVar1 != '\0') {
        lVar5 = lVar5 + 1;
        cVar1 = pcVar4[lVar5];
      }
      uVar6 = lVar5 + 1;
    } while ((pcVar4[uVar6] != '\0') && (param_2 != '\0'));
    pcVar3 = (char *)FUN_0001b514(param_1,uVar6);
    *param_3 = pcVar3;
    if ((pcVar3 != (char *)0x0) && ((uVar6 != 0 && (pcVar3 != pcVar4)))) {
      FUN_000002e0((undefined8 *)pcVar3,(undefined8 *)pcVar4,uVar6);
    }
  }
  return 0;
}


// ==== FUN_00012864 @ 00012864

void FUN_00012864(void)

{
  bool bVar1;
  bool bVar2;
  char *pcVar3;
  char cVar4;
  byte bVar5;
  short sVar6;
  longlong lVar7;
  short *psVar8;
  short *psVar9;
  undefined2 uVar10;
  ulonglong uVar11;
  short *psVar12;
  undefined **ppuVar13;
  undefined *puVar14;
  undefined2 local_res18 [4];
  ulonglong local_res20;
  char *local_38;
  longlong local_30;
  
  (**(code **)(DAT_00029478 + 0x70))();
  bVar1 = false;
  bVar2 = false;
  lVar7 = (**(code **)(DAT_00029478 + 0x140))(&DAT_000236e0,0,&local_30);
  if (-1 < lVar7) {
    local_res18[0] = 0xfffe;
    do {
      lVar7 = (**(code **)(local_30 + 0x18))(local_30,local_res18,0,&local_38,0);
      pcVar3 = local_38;
      if (lVar7 < 0) break;
      if (*local_38 == '\x02') {
        FUN_000127dc(local_38 + (byte)local_38[1],local_38[5],&local_res20);
        uVar10 = 0x14d8;
        FUN_00000680(DAT_000293c0,0x14d8,&DAT_00027518,local_res20);
        uVar11 = local_res20;
        (**(code **)(DAT_00029478 + 0x48))();
        psVar8 = (short *)FUN_00021180(uVar11,uVar10);
        if (psVar8 != (short *)0x0) {
          ppuVar13 = &PTR_u_CometLake_U_LPDDR3_RVP_000254a8;
          uVar11 = 0;
          do {
            psVar12 = (short *)*ppuVar13;
            psVar9 = psVar8;
            if (*psVar8 != 0) {
              sVar6 = *psVar8;
              do {
                if (sVar6 != *psVar12) break;
                psVar9 = psVar9 + 1;
                psVar12 = psVar12 + 1;
                sVar6 = *psVar9;
              } while (sVar6 != 0);
            }
            if (*psVar9 == *psVar12) {
              FUN_00000680(DAT_000293c0,0x14d8,(byte *)u_0x_X___s__00027520,
                           (ulonglong)*(ushort *)(&DAT_000254a0 + uVar11 * 0x10));
              break;
            }
            uVar11 = uVar11 + 1;
            ppuVar13 = ppuVar13 + 2;
          } while (uVar11 < 0x18);
        }
        FUN_000127dc(pcVar3 + (byte)pcVar3[1],pcVar3[6],&local_res20);
        FUN_00000680(DAT_000293c0,0x14db,&DAT_00027518,local_res20);
        (**(code **)(DAT_00029478 + 0x48))(local_res20);
        bVar1 = true;
      }
      if (*local_38 == '\0') {
        FUN_00000680(DAT_000293c0,0x1378,(byte *)u__02d_a_02d_00027538,
                     (ulonglong)(byte)local_38[0x16]);
        lVar7 = FUN_0001b738();
        cVar4 = (**(code **)(lVar7 + 8))(0x8c);
        if (cVar4 == '\x01') {
          puVar14 = &DAT_00027550;
        }
        else if (cVar4 == '\x02') {
          puVar14 = &DAT_00027558;
        }
        else {
          puVar14 = &DAT_00027560;
        }
        FUN_00000680(DAT_000293c0,0x137b,&DAT_00025b68,(ulonglong)puVar14);
        bVar2 = true;
      }
    } while ((!bVar1) || (!bVar2));
    lVar7 = FUN_0001b738();
    bVar5 = (**(code **)(lVar7 + 8))(0x46);
    lVar7 = FUN_0001b738();
    (**(code **)(lVar7 + 8))(0xad);
    FUN_00000680(DAT_000293c0,0x1378,(byte *)u__02d_a_02d_00027538,(ulonglong)bVar5);
  }
  return;
}


// ==== FUN_00012b18 @ 00012b18

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_00012b18(longlong param_1,short param_2,undefined8 param_3,char *param_4)

{
  longlong lVar1;
  char *pcVar2;
  undefined8 local_res18;
  longlong local_res20;
  undefined1 local_88;
  uint local_87;
  undefined1 local_70 [8];
  undefined8 local_68;
  ushort local_5c;
  
  if (param_2 == 1) {
    local_res18 = 0x12;
    if (DAT_000293c0 == 0) {
      DAT_000293c0 = param_1;
    }
    lVar1 = (**(code **)(DAT_00029488 + 0x48))
                      (u_MeInfoSetup_00027598,&DAT_00023930,0,&local_res18,&local_88);
    if (-1 < lVar1) {
      FUN_00000680(param_1,0x137f,(byte *)u__d__d__d__d_00026538,(ulonglong)local_87);
    }
    FUN_00012864();
    FUN_00012d20();
    if (DAT_0002afe4 == '\x03') {
      pcVar2 = s_Consumer_SKU_00027568;
    }
    else {
      pcVar2 = s_Corporate_SKU_00027578;
      if (DAT_0002afe4 != '\x04') {
        pcVar2 = s_Unidentified_00027588;
      }
    }
    FUN_00000680(param_1,0x12f5,&DAT_0002672c,(ulonglong)pcVar2);
    lVar1 = (**(code **)(DAT_00029478 + 0x140))(&DAT_000234b0,0,&local_res20);
    if (-1 < lVar1) {
      lVar1 = FUN_000206a0(&local_68,&local_res20);
      if (-1 < lVar1) {
        FUN_00000680(param_1,0x1382,(byte *)u__d__d__d__d_00026538,(ulonglong)local_5c);
      }
    }
    lVar1 = FUN_0001f90c((longlong *)&DAT_00023970);
    if (((lVar1 == 0) || (lVar1 == -0x18)) ||
       (pcVar2 = s_Supported_00026840, (*(uint *)(lVar1 + 0xa0) & 0x110000) != 0x110000)) {
      pcVar2 = s_Unsupported_000275b0;
    }
    FUN_00000680(param_1,0x136c,&DAT_0002672c,(ulonglong)pcVar2);
    param_4 = s_Production_000275c0;
    if (-1 < _DAT_fed30200) {
      param_4 = s_Pre_Production_000275d0;
    }
    FUN_00000680(param_1,0x136f,&DAT_0002672c,(ulonglong)param_4);
  }
  FUN_0001f1ec(&DAT_00023520,8,FUN_0001335c,param_4,local_70);
  FUN_00012508();
  return;
}


// ==== FUN_00012d20 @ 00012d20

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_00012d20(void)

{
  byte bVar1;
  longlong lVar2;
  ushort *puVar3;
  ulonglong uVar4;
  uint uVar5;
  bool bVar6;
  ushort local_res18 [4];
  
  bVar1 = DAT_e00fe004;
  uVar4 = 0;
  local_res18[0] = 0;
  DAT_e00fe004 = bVar1;
  if ((_DAT_e00fe000 != -1) && ((_DAT_e00fe0cc & 3) == 0)) {
    uVar5 = _DAT_e00fe010 & 0xfffe0000;
    (**(code **)(DAT_00029478 + 0x70))();
    bVar6 = (bVar1 & 2) == 0;
    if (bVar6) {
      DAT_e00fe004 = 7;
    }
    if (uVar5 != 0) {
      lVar2 = FUN_00022898(uVar5,(short *)local_res18);
      if (-1 < lVar2) {
        if (local_res18[0] != 0) {
          puVar3 = &DAT_00024700;
          do {
            if ((local_res18[0] & 0xff) == *puVar3) {
              FUN_00000680(DAT_000293c0,0x14de,(byte *)u__02x__a_000275e0,
                           (ulonglong)(byte)local_res18[0]);
              goto LAB_00012e2d;
            }
            uVar4 = uVar4 + 1;
            puVar3 = puVar3 + 8;
          } while (uVar4 < 7);
          FUN_00000680(DAT_000293c0,0x14de,(byte *)u__02x_000275f0,(ulonglong)(byte)local_res18[0]);
        }
LAB_00012e2d:
        if (bVar6) {
          DAT_e00fe004 = bVar1;
        }
      }
    }
  }
  return;
}


// ==== FUN_00012e54 @ 00012e54

undefined4 FUN_00012e54(undefined4 param_1)

{
  bool bVar1;
  bool bVar2;
  longlong lVar3;
  undefined8 local_res10;
  undefined8 local_res18;
  char local_2788 [67];
  char local_2745;
  char local_2727;
  char local_2726;
  char local_2725;
  char local_2693;
  char local_268f;
  char local_2661;
  char local_265b;
  char local_2657;
  char local_2654;
  char local_2568 [67];
  char local_2525;
  char local_2507;
  char local_2506;
  char local_2505;
  char local_2473;
  char local_246f;
  char local_2441;
  char local_243b;
  char local_2437;
  char local_2434;
  char local_2348 [63];
  char local_2309;
  char local_2308;
  char local_22e9;
  char local_22df;
  char local_22d5;
  char local_228c;
  char local_226d;
  char local_226c;
  char local_2268;
  char local_215c;
  char local_2088 [63];
  char local_2049;
  char local_2048;
  char local_2029;
  char local_201f;
  char local_2015;
  char local_1fcc;
  char local_1fad;
  char local_1fac;
  char local_1fa8;
  char local_1e9c;
  char local_1dc8 [68];
  char local_1d84;
  char local_1871;
  char local_16d8 [68];
  char local_1694;
  char local_1181;
  undefined1 local_fe8 [1270];
  char local_af2;
  char local_af1;
  char local_8ac;
  undefined1 local_808 [1270];
  char local_312;
  char local_311;
  char local_cc;
  
  local_res10 = 0x7d8;
  bVar2 = false;
  lVar3 = (**(code **)(DAT_00029488 + 0x48))
                    (u_Setup_000262c8,&DAT_00023710,0,&local_res10,local_808);
  if (-1 < lVar3) {
    local_res10 = 0x21d;
    lVar3 = (**(code **)(DAT_00029488 + 0x48))
                      (u_SaSetup_00026070,&DAT_000238f0,0,&local_res10,local_2568);
    if (-1 < lVar3) {
      local_res10 = 699;
      lVar3 = (**(code **)(DAT_00029488 + 0x48))
                        (u_CpuSetup_00026ae0,&DAT_000235b0,0,&local_res10,local_2088);
      if (-1 < lVar3) {
        local_res10 = 0x6ec;
        lVar3 = (**(code **)(DAT_00029488 + 0x48))
                          (u_PchSetup_00026308,&DAT_000238c0,0,&local_res10,local_16d8);
        if (-1 < lVar3) {
          local_res10 = 0x7d8;
          lVar3 = (**(code **)(DAT_00029488 + 0x48))
                            (u_ColdReset_00027490,&DAT_00023710,0,&local_res10,local_fe8);
          if (-1 < lVar3) {
            local_res10 = 0x21d;
            lVar3 = (**(code **)(DAT_00029488 + 0x48))
                              (u_SaColdReset_000274a8,&DAT_000238f0,0,&local_res10,local_2788);
            if (-1 < lVar3) {
              local_res10 = 699;
              lVar3 = (**(code **)(DAT_00029488 + 0x48))
                                (u_CpuColdReset_000274d8,&DAT_000235b0,0,&local_res10,local_2348);
              if (-1 < lVar3) {
                local_res10 = 0x6ec;
                lVar3 = (**(code **)(DAT_00029488 + 0x48))
                                  (u_PchColdReset_000274f8,&DAT_000238c0,0,&local_res10,local_1dc8);
                if (-1 < lVar3) {
                  lVar3 = FUN_000002c0(local_16d8,local_1dc8,0x6ec);
                  if (((lVar3 != 0) || (lVar3 = FUN_000002c0(local_2088,local_2348,699), lVar3 != 0)
                      ) || (lVar3 = FUN_000002c0(local_2568,local_2788,0x21d), lVar3 != 0)) {
                    local_res18 = 0;
                    (**(code **)(DAT_00029478 + 0x80))(&local_res18,&DAT_000237f0,0,0);
                  }
                  if ((local_1694 != local_1d84) || (local_cc != local_8ac)) {
                    (**(code **)(DAT_00029488 + 0x58))(u_BootState_00027600,&DAT_00023890,0,0,0);
                  }
                  if (((((local_246f != local_268f) || (local_1181 != local_1871)) ||
                       ((local_1fcc != local_228c ||
                        ((((local_2525 != local_2745 || (local_2473 != local_2693)) ||
                          (local_2437 != local_2657)) ||
                         ((local_243b != local_265b || (local_2441 != local_2661)))))))) ||
                      (local_2434 != local_2654)) ||
                     (((local_2507 != local_2727 || (local_2506 != local_2726)) ||
                      ((local_2505 != local_2725 ||
                       (((local_1fad != local_226d || (local_1fac != local_226c)) ||
                        (local_1e9c != local_215c)))))))) {
                    bVar2 = true;
                  }
                  FUN_00012730();
                  FUN_0001b774('f',0x94);
                  if (DAT_00029290 != '\0') {
                    bVar2 = true;
                  }
                  if (((local_2049 != local_2309) || (local_2048 != local_2308)) ||
                     ((local_2029 != local_22e9 ||
                      ((local_201f != local_22df || (local_2015 != local_22d5)))))) {
                    bVar2 = true;
                  }
                  if (local_1fa8 != local_2268) {
                    bVar2 = true;
                  }
                  if ((local_312 != local_af2) ||
                     (bVar1 = DAT_00029468 != '\0', local_311 != local_af1)) {
                    bVar1 = true;
                  }
                  if (bVar1) {
                    param_1 = 3;
                  }
                  else if (bVar2) {
                    param_1 = 0;
                  }
                }
              }
            }
          }
        }
      }
    }
  }
  return param_1;
}


// ==== FUN_000132e0 @ 000132e0

void FUN_000132e0(int param_1)

{
  int iVar1;
  int iVar2;
  short *psVar3;
  short local_38 [10];
  undefined8 local_24 [3];
  
  if (DAT_0002974e == '\0') {
    DAT_0002974e = '\x01';
    iVar1 = FUN_00012e54(param_1);
    if (param_1 != iVar1) {
      if (iVar1 == 3) {
        FUN_000002e0(local_24,(undefined8 *)&DAT_00023850,0x10);
        iVar2 = 10;
        FUN_0001cff0(local_38,10,u_PCH_RESET_00027620);
        psVar3 = local_38;
        iVar1 = iVar2 + -7;
        iVar2 = iVar2 + 0x1a;
      }
      else {
        psVar3 = (short *)0x0;
        iVar2 = 0;
      }
      (**(code **)(DAT_00029488 + 0x68))(iVar1,0,iVar2,psVar3);
    }
  }
  return;
}


// ==== FUN_0001335c @ 0001335c

void FUN_0001335c(longlong param_1)

{
  longlong lVar1;
  undefined8 *local_res18 [2];
  
  lVar1 = (**(code **)(DAT_00029478 + 0x140))(&DAT_00023520,0,local_res18);
  if (-1 < lVar1) {
    (*(code *)*local_res18[0])(local_res18[0],FUN_000132e0);
    if (param_1 != 0) {
      (**(code **)(DAT_00029478 + 0x70))(param_1);
    }
  }
  return;
}


// ==== FUN_00013638 @ 00013638

ushort FUN_00013638(short *param_1,short param_2)

{
  short sVar1;
  ushort uVar2;
  
  sVar1 = *param_1;
  uVar2 = 0;
  while( true ) {
    if (sVar1 == 0) {
      return 0xffff;
    }
    if (sVar1 == param_2) break;
    uVar2 = uVar2 + 1;
    sVar1 = *(short *)((ulonglong)uVar2 * 7 + (longlong)param_1);
  }
  return uVar2;
}


// ==== FUN_00013670 @ 00013670

ushort FUN_00013670(short param_1)

{
  short sVar1;
  ushort uVar2;
  
  uVar2 = 0;
  if (*DAT_000293e8 != 0) {
    sVar1 = *DAT_000293e8;
    do {
      if (sVar1 == param_1) {
        return uVar2;
      }
      uVar2 = uVar2 + 1;
      sVar1 = DAT_000293e8[(ulonglong)uVar2 * 5];
    } while (sVar1 != 0);
  }
  return 0xffff;
}


// ==== FUN_000136b0 @ 000136b0

undefined8 FUN_000136b0(char *param_1,longlong param_2)

{
  longlong lVar1;
  ulonglong uVar2;
  longlong *plVar3;
  longlong *plVar4;
  
  if (((*param_1 == '\x04') && (param_1[1] == '\x01')) &&
     (lVar1 = FUN_0001edd4((longlong *)(param_1 + 4),(longlong *)(param_2 + 4),0x26), lVar1 == 0)) {
    plVar3 = (longlong *)
             (param_1 + (ulonglong)(byte)param_1[3] * 0x100 + (ulonglong)(byte)param_1[2]);
    if (((char)*plVar3 == '\x04') && (*(char *)((longlong)plVar3 + 1) == '\x04')) {
      _wcsupr((wchar_t *)((longlong)plVar3 + 2));
    }
    plVar4 = (longlong *)
             ((ulonglong)*(byte *)(param_2 + 2) + param_2 +
             (ulonglong)*(byte *)(param_2 + 3) * 0x100);
    if (((char)*plVar4 == '\x04') && (*(char *)((longlong)plVar4 + 1) == '\x04')) {
      _wcsupr((wchar_t *)((longlong)plVar4 + 2));
    }
    uVar2 = FUN_0001d7b4((char *)plVar4);
    lVar1 = FUN_0001edd4(plVar3,plVar4,uVar2);
    if (lVar1 == 0) {
      return 0;
    }
  }
  return 0x800000000000000e;
}


// ==== FUN_0001376c @ 0001376c

bool FUN_0001376c(longlong *param_1,longlong *param_2)

{
  longlong lVar1;
  longlong lVar2;
  ulonglong uVar3;
  
  if ((param_1 != (longlong *)0x0) && (param_2 != (longlong *)0x0)) {
    lVar1 = FUN_0001d7b4((char *)param_1);
    lVar2 = FUN_0001d7b4((char *)param_2);
    if (lVar1 == lVar2) {
      uVar3 = FUN_0001d7b4((char *)param_1);
      lVar1 = FUN_0001edd4(param_1,param_2,uVar3);
      if (lVar1 == 0) {
        return true;
      }
      lVar1 = FUN_000136b0((char *)param_1,(longlong)param_2);
      return lVar1 == 0;
    }
  }
  return false;
}


// ==== FUN_000137dc @ 000137dc

ulonglong FUN_000137dc(undefined8 param_1,short *param_2,longlong *param_3)

{
  bool bVar1;
  undefined8 *puVar2;
  undefined8 *puVar3;
  undefined7 extraout_var;
  short *psVar4;
  longlong *local_res20;
  
  puVar2 = (undefined8 *)(**(code **)(DAT_00029498 + 0x98))(param_1,&DAT_00023690);
  if (-1 < (longlong)puVar2) {
    puVar3 = (undefined8 *)(**(code **)(*param_3 + 0x58))();
    puVar2 = puVar3;
    for (; puVar3 != (undefined8 *)0x0; puVar3 = (undefined8 *)puVar3[3]) {
      bVar1 = FUN_0001376c(local_res20,(longlong *)puVar3[2]);
      puVar2 = (undefined8 *)CONCAT71(extraout_var,bVar1);
      if (bVar1) {
        FUN_0002337e((undefined4 *)param_2,0x100,0);
        for (psVar4 = (short *)*puVar3; *psVar4 != 0; psVar4 = psVar4 + 1) {
          *param_2 = *psVar4;
          param_2 = param_2 + 1;
        }
        *param_2 = 0;
        return CONCAT71((int7)((ulonglong)psVar4 >> 8),1);
      }
    }
  }
  return (ulonglong)puVar2 & 0xffffffffffffff00;
}


// ==== FUN_0001387c @ 0001387c

ulonglong FUN_0001387c(longlong param_1,undefined8 *param_2,longlong *param_3)

{
  bool bVar1;
  short *psVar2;
  undefined8 *puVar3;
  undefined7 extraout_var;
  longlong lVar5;
  undefined8 *puVar4;
  
  lVar5 = 0;
  for (psVar2 = (short *)(param_1 + 6); *psVar2 != 0; psVar2 = psVar2 + 1) {
    lVar5 = lVar5 + 1;
  }
  puVar3 = (undefined8 *)(**(code **)(*param_3 + 0x58))();
  puVar4 = puVar3;
  while( true ) {
    if (puVar3 == (undefined8 *)0x0) {
      return (ulonglong)puVar4 & 0xffffffffffffff00;
    }
    bVar1 = FUN_0001376c((longlong *)(param_1 + lVar5 * 2 + 8),(longlong *)puVar3[2]);
    puVar4 = (undefined8 *)CONCAT71(extraout_var,bVar1);
    if (bVar1) break;
    puVar3 = (undefined8 *)puVar3[3];
  }
  *param_2 = *puVar3;
  return CONCAT71(extraout_var,1);
}


// ==== FUN_000138f8 @ 000138f8

void FUN_000138f8(void)

{
  char cVar1;
  short *psVar2;
  longlong lVar3;
  bool bVar4;
  char *pcVar5;
  short sVar6;
  longlong lVar7;
  short *psVar8;
  short *psVar9;
  short *psVar10;
  ushort uVar11;
  ulonglong uVar12;
  undefined1 local_res10 [8];
  char *local_res18;
  undefined8 local_res20;
  undefined8 local_68;
  undefined8 *local_60;
  char *local_58;
  
  local_res18 = (char *)0x0;
  uVar11 = 0;
  if (DAT_000293e8 != (short *)0x0) {
    sVar6 = *DAT_000293e8;
    while (sVar6 != 0) {
      uVar11 = uVar11 + 1;
      sVar6 = DAT_000293e8[(ulonglong)uVar11 * 5];
    }
  }
  bVar4 = false;
  local_60 = (undefined8 *)0x0;
  local_res20 = 0;
  local_68 = 0;
  if ((DAT_000293d0 != 0) ||
     (lVar7 = (**(code **)(DAT_00029498 + 0x140))(&DAT_000237c0,0,&DAT_000293d0), -1 < lVar7)) {
    lVar7 = (**(code **)(DAT_000293d0 + 0x18))(DAT_000293d0,DAT_0002b1f8,local_res18,&local_res20);
    if (lVar7 == -0x7ffffffffffffffb) {
      lVar7 = (**(code **)(DAT_00029498 + 0x40))(4,local_res20,&local_res18);
      if (lVar7 < 0) {
        return;
      }
      lVar7 = (**(code **)(DAT_000293d0 + 0x18))(DAT_000293d0,DAT_0002b1f8,local_res18,&local_res20)
      ;
    }
    if ((-1 < lVar7) &&
       (lVar7 = FUN_0001d808(u_FboGroupNameData_00027640,&DAT_00024858,local_res10,&local_68,
                             (longlong *)&local_60), -1 < lVar7)) {
      local_58 = local_res18;
      do {
        pcVar5 = local_res18;
        for (; (*local_res18 != ';' && (*local_res18 != '\0')); local_res18 = local_res18 + 1) {
        }
        if ((*pcVar5 == 'x') && (pcVar5[1] == '-')) {
          if (*local_res18 == '\0') {
            bVar4 = true;
          }
        }
        else {
          cVar1 = *local_res18;
          *local_res18 = '\0';
          for (psVar2 = (short *)*local_60; psVar2 != (short *)0x0; psVar2 = *(short **)(psVar2 + 9)
              ) {
            lVar7 = 0;
            if (uVar11 != 0) {
              uVar12 = (ulonglong)uVar11;
              do {
                sVar6 = *(short *)(lVar7 + 2 + (longlong)DAT_000293e8);
                if (*psVar2 == sVar6) {
                  (**(code **)(DAT_000293d0 + 0x10))
                            (DAT_000293d0,DAT_0002b1f8,sVar6,pcVar5,*(undefined8 *)(psVar2 + 5),0);
                }
                else {
                  psVar8 = (short *)FUN_0001d774(0x100);
                  local_68 = 0x100;
                  (**(code **)(DAT_000293d0 + 8))
                            (DAT_000293d0,pcVar5,DAT_0002b1f8,
                             *(undefined2 *)(lVar7 + 2 + (longlong)DAT_000293e8),psVar8,&local_68,0)
                  ;
                  psVar10 = *(short **)(psVar2 + 1);
                  if (psVar10 != (short *)0x0) {
                    sVar6 = *psVar8;
                    psVar9 = psVar8;
                    while ((sVar6 != 0 && (sVar6 == *psVar10))) {
                      psVar9 = psVar9 + 1;
                      psVar10 = psVar10 + 1;
                      sVar6 = *psVar9;
                    }
                    if (*psVar9 == *psVar10) {
                      (**(code **)(DAT_000293d0 + 0x10))
                                (DAT_000293d0,DAT_0002b1f8,
                                 *(undefined2 *)(lVar7 + 2 + (longlong)DAT_000293e8),pcVar5,
                                 *(undefined8 *)(psVar2 + 5),0);
                    }
                  }
                  (**(code **)(DAT_00029498 + 0x48))(psVar8);
                }
                lVar7 = lVar7 + 10;
                uVar12 = uVar12 - 1;
              } while (uVar12 != 0);
            }
          }
          lVar7 = 0;
          *local_res18 = cVar1;
          if (cVar1 == '\0') break;
        }
        lVar7 = 0;
        local_res18 = local_res18 + 1;
      } while (!bVar4);
      while (lVar7 != 0) {
        lVar3 = *(longlong *)(lVar7 + 0x12);
        (**(code **)(DAT_00029498 + 0x48))(lVar7);
        lVar7 = lVar3;
      }
      (**(code **)(DAT_000294a0 + 0x58))(u_FboGroupNameData_00027640,&DAT_00024858,0,0,0);
      (**(code **)(DAT_00029498 + 0x48))(local_58);
      (**(code **)(DAT_00029498 + 0x48))(local_60);
    }
  }
  return;
}


// ==== FUN_00013c34 @ 00013c34

longlong FUN_00013c34(undefined8 param_1,undefined8 param_2)

{
  longlong lVar1;
  ulonglong uVar2;
  longlong local_res18;
  ulonglong local_res20;
  
  local_res20 = 0;
  local_res18 = 0;
  if ((DAT_000293d0 != (undefined8 *)0x0) ||
     (lVar1 = (**(code **)(DAT_00029498 + 0x140))(&DAT_000237c0,0,&DAT_000293d0), -1 < lVar1)) {
    lVar1 = (*(code *)DAT_000293d0[3])(DAT_000293d0,param_1,local_res18,&local_res20);
    if (lVar1 == -0x7ffffffffffffffb) {
      lVar1 = (**(code **)(DAT_00029498 + 0x40))(4,local_res20,&local_res18);
      if (lVar1 < 0) {
        return lVar1;
      }
      lVar1 = (*(code *)DAT_000293d0[3])(DAT_000293d0,param_1,local_res18,&local_res20);
    }
    if (-1 < lVar1) {
      uVar2 = 0;
      if (local_res20 != 0) {
        do {
          if (*(char *)(uVar2 + local_res18) == ';') break;
          uVar2 = uVar2 + 1;
        } while (uVar2 < local_res20);
      }
      if (uVar2 != local_res20) {
        *(undefined1 *)(uVar2 + local_res18) = 0;
      }
      lVar1 = (*(code *)*DAT_000293d0)(DAT_000293d0,param_1,param_2,local_res18,0,&DAT_00025f34,0);
      (**(code **)(DAT_00029498 + 0x48))(local_res18);
    }
  }
  return lVar1;
}


// ==== FUN_00013d6c @ 00013d6c

longlong FUN_00013d6c(ushort param_1,undefined8 param_2,undefined8 param_3,undefined8 param_4)

{
  longlong lVar1;
  longlong lVar2;
  longlong local_res10 [3];
  wchar_t local_28 [16];
  
  local_res10[1] = 0;
  local_res10[0] = 0;
  FUN_0001dff0(local_28,u_Boot_04X_00027668,(ulonglong)param_1,param_4);
  lVar1 = FUN_0001d808(local_28,&DAT_00024838,0,local_res10 + 1,local_res10);
  lVar2 = 0;
  if (-1 < lVar1) {
    lVar2 = local_res10[0];
  }
  return lVar2;
}


// ==== FUN_00013dc8 @ 00013dc8

void FUN_00013dc8(ushort param_1,longlong param_2)

{
  char cVar1;
  bool bVar2;
  char *pcVar3;
  undefined8 uVar4;
  char *pcVar5;
  longlong lVar6;
  ulonglong uVar7;
  short *psVar8;
  ulonglong uVar9;
  ulonglong uVar10;
  char *local_res18;
  undefined8 local_res20;
  undefined8 local_468 [2];
  short local_458 [264];
  wchar_t local_248 [264];
  
  local_res18 = (char *)0x0;
  local_res20 = 0;
  local_468[0] = 0;
  bVar2 = false;
  if ((0xff < param_1) &&
     ((DAT_000293d0 != 0 ||
      (lVar6 = (**(code **)(DAT_00029498 + 0x140))(&DAT_000237c0,0,&DAT_000293d0), -1 < lVar6)))) {
    lVar6 = (**(code **)(DAT_000293d0 + 0x18))(DAT_000293d0,DAT_0002b1f8,local_res18,&local_res20);
    if (lVar6 == -0x7ffffffffffffffb) {
      lVar6 = (**(code **)(DAT_00029498 + 0x40))(4,local_res20,&local_res18);
      if (lVar6 < 0) {
        return;
      }
      lVar6 = (**(code **)(DAT_000293d0 + 0x18))(DAT_000293d0,DAT_0002b1f8,local_res18,&local_res20)
      ;
    }
    pcVar5 = local_res18;
    pcVar3 = local_res18;
    if (-1 < lVar6) {
LAB_00013eef:
      do {
        for (; (uVar4 = DAT_0002b1f8, *local_res18 != ';' && (*local_res18 != '\0'));
            local_res18 = local_res18 + 1) {
        }
        if ((*pcVar3 == 'x') && (pcVar3[1] == '-')) {
          if (*local_res18 == '\0') {
            bVar2 = true;
          }
          local_res18 = local_res18 + 1;
        }
        else {
          cVar1 = *local_res18;
          uVar10 = (ulonglong)param_1;
          *local_res18 = '\0';
          local_468[0] = 0x100;
          lVar6 = (**(code **)(DAT_000293d0 + 8))
                            (DAT_000293d0,pcVar3,uVar4,uVar10,local_458,local_468,0);
          *local_res18 = cVar1;
          uVar7 = 0;
          if (lVar6 < 0) {
            if (cVar1 == '\0') break;
            *local_res18 = ';';
            local_res18 = local_res18 + 1;
            pcVar3 = local_res18;
            goto LAB_00013eef;
          }
          while (psVar8 = local_458, uVar9 = 0, local_458[0] != 0) {
            do {
              psVar8 = psVar8 + 1;
              uVar9 = uVar9 + 1;
            } while (*psVar8 != 0);
            if (uVar9 <= uVar7) break;
            if (local_458[uVar7] == 0x3a) {
              local_458[uVar7] = 0;
              break;
            }
            uVar7 = uVar7 + 1;
          }
          if (param_2 == 0) {
            FUN_0001dff0(local_248,(wchar_t *)&DAT_00025b68,local_458,uVar10);
          }
          else {
            FUN_0001dff0(local_248,u__s__s_00027680,local_458,param_2);
          }
          if (*local_res18 == '\0') {
            lVar6 = (**(code **)(DAT_000293d0 + 0x10))
                              (DAT_000293d0,DAT_0002b1f8,param_1,pcVar3,local_248,0);
            if (lVar6 < 0) goto LAB_0001408f;
            break;
          }
          *local_res18 = '\0';
          lVar6 = (**(code **)(DAT_000293d0 + 0x10))(DAT_000293d0);
          *local_res18 = ';';
          local_res18 = local_res18 + 1;
          if (lVar6 < 0) goto LAB_0001408f;
        }
        pcVar3 = local_res18;
      } while (!bVar2);
      if (pcVar5 != (char *)0x0) {
LAB_0001408f:
        (**(code **)(DAT_00029498 + 0x48))(pcVar5);
      }
    }
  }
  return;
}


// ==== FUN_000140b8 @ 000140b8

/* WARNING: Type propagation algorithm not settling */

longlong FUN_000140b8(ushort param_1,ulonglong param_2)

{
  longlong lVar1;
  longlong lVar2;
  longlong local_res18 [2];
  undefined8 local_18;
  undefined8 local_10;
  
  local_res18[0] = 0;
  local_18 = 0;
  local_res18[1] = 8;
  lVar2 = (**(code **)(DAT_000294a0 + 0x48))
                    (u_FboGfHiiHandle_00027690,&DAT_00024858,0,local_res18 + 1,&local_10);
  if (-1 < lVar2) {
    lVar2 = FUN_0001d808(u_FixedGfHiiLegacyDevData_000276b0,&DAT_00024858,0,&local_18,local_res18);
    lVar1 = local_res18[0];
    if (-1 < lVar2) {
      FUN_00000680(local_10,(ushort)*(byte *)((ulonglong)param_1 + local_res18[0]),&DAT_00025b68,
                   param_2);
      (**(code **)(DAT_00029498 + 0x48))(lVar1);
    }
  }
  return lVar2;
}


// ==== FUN_0001417c @ 0001417c

/* WARNING: Type propagation algorithm not settling */

longlong FUN_0001417c(ushort param_1,ulonglong param_2)

{
  longlong lVar1;
  longlong lVar2;
  longlong local_res18 [2];
  undefined8 local_18;
  undefined8 local_10;
  
  local_res18[0] = 0;
  local_18 = 0;
  local_res18[1] = 8;
  lVar2 = (**(code **)(DAT_000294a0 + 0x48))
                    (u_FboGfHiiHandle_00027690,&DAT_00024858,0,local_res18 + 1,&local_10);
  if (-1 < lVar2) {
    lVar2 = FUN_0001d808(u_FixedGfHiiUefiDevData_000276e0,&DAT_00024858,0,&local_18,local_res18);
    lVar1 = local_res18[0];
    if (-1 < lVar2) {
      FUN_00000680(local_10,(ushort)*(byte *)((ulonglong)param_1 + local_res18[0]),&DAT_00025b68,
                   param_2);
      (**(code **)(DAT_00029498 + 0x48))(lVar1);
    }
  }
  return lVar2;
}


// ==== FUN_00014240 @ 00014240

void FUN_00014240(longlong *param_1,longlong *param_2)

{
  longlong lVar1;
  undefined4 *puVar2;
  ulonglong uVar3;
  undefined4 *puVar4;
  ushort *puVar5;
  ulonglong uVar6;
  longlong local_res8;
  undefined4 *local_res18;
  
  local_res8 = 0;
  local_res18 = (undefined4 *)0x0;
  puVar4 = (undefined4 *)*param_1;
  if ((DAT_000293f8 != 0) &&
     (lVar1 = FUN_0001d808(u_FboLegacyDevOrder_00027710,&DAT_00024858,0,&local_res8,
                           (longlong *)&local_res18), -1 < lVar1)) {
    lVar1 = *param_1;
    if (puVar4 < (undefined4 *)(*param_2 + lVar1)) {
      do {
        puVar2 = local_res18;
        if (local_res18 < (undefined4 *)(local_res8 + (longlong)local_res18)) {
          do {
            uVar6 = 0;
            uVar3 = (ulonglong)*(ushort *)(puVar2 + 1) - 2 >> 1;
            if (uVar3 != 0) {
              puVar5 = (ushort *)((longlong)puVar2 + 6);
              do {
                if ((*(ushort *)((longlong)puVar4 + 6) & 0xff) == (*puVar5 & 0xff)) {
                  *puVar4 = *puVar2;
                  puVar2 = (undefined4 *)(local_res8 + (longlong)local_res18);
                  break;
                }
                uVar6 = uVar6 + 1;
                puVar5 = puVar5 + 1;
              } while (uVar6 < uVar3);
            }
            puVar2 = (undefined4 *)((longlong)puVar2 + (ulonglong)*(ushort *)(puVar2 + 1) + 4);
          } while (puVar2 < (undefined4 *)(local_res8 + (longlong)local_res18));
        }
        puVar4 = (undefined4 *)((longlong)puVar4 + (ulonglong)*(ushort *)(puVar4 + 1) + 4);
      } while (puVar4 < (undefined4 *)(*param_2 + lVar1));
    }
    (**(code **)(DAT_00029498 + 0x48))(local_res18);
  }
  return;
}


// ==== FUN_0001435c @ 0001435c

longlong FUN_0001435c(void)

{
  int iVar1;
  uint uVar2;
  ushort uVar3;
  longlong lVar4;
  int *piVar5;
  ulonglong uVar6;
  int *piVar7;
  int *piVar8;
  wchar_t *pwVar9;
  ulonglong uVar10;
  int *piVar11;
  int *piVar12;
  ulonglong local_res8;
  int *local_res10;
  int *local_res18;
  longlong local_res20;
  longlong local_268 [2];
  wchar_t local_258 [268];
  
  local_res18 = (int *)0x0;
  local_res8 = 0;
  local_res20 = 0;
  local_res10 = (int *)0x0;
  lVar4 = FUN_0001d808(u_OriFboLegacyDevOrder_00027738,&DAT_00024858,0,&local_res8,
                       (longlong *)&local_res18);
  piVar7 = local_res18;
  piVar8 = (int *)0x0;
  piVar11 = piVar7;
  if ((-1 < lVar4) && (piVar8 = (int *)0x0, 6 < local_res8)) {
    pwVar9 = (wchar_t *)&local_res20;
    lVar4 = FUN_0001d808(u_FixedHiiLegacyDevData_00027768,&DAT_00024858,0,(undefined8 *)pwVar9,
                         (longlong *)&local_res10);
    piVar8 = local_res10;
    if (lVar4 < 0) {
      return lVar4;
    }
    lVar4 = DAT_000293e8;
    uVar6 = local_res8;
    piVar12 = local_res10;
    if (piVar7 < (int *)(local_res8 + (longlong)piVar7)) {
      do {
        uVar10 = 0;
        iVar1 = *piVar7;
        if (iVar1 != 0xff) {
          uVar3 = FUN_00013670((short)iVar1);
          piVar5 = (int *)((ulonglong)uVar3 * 5);
          if (*(short *)(lVar4 + 4 + (ulonglong)uVar3 * 10) != 0) {
            for (piVar12 = piVar8;
                (piVar12 < (int *)(local_res20 + (longlong)piVar8) && (*piVar12 != iVar1));
                piVar12 = (int *)((longlong)piVar12 + (ulonglong)*(ushort *)(piVar12 + 1) + 4)) {
            }
          }
          local_res10 = piVar5;
          if (((ulonglong)*(ushort *)(piVar7 + 1) - 2 & 0xfffffffffffffffe) != 0) {
            do {
              if (*(short *)(lVar4 + 4 + (longlong)piVar5 * 2) != 0) {
                uVar6 = (ulonglong)(byte)*(undefined2 *)((longlong)piVar7 + uVar10 * 2 + 6);
                lVar4 = uVar6 * 0x45;
                FUN_0001dff0(local_258,(wchar_t *)&DAT_0002672c,
                             (ulonglong)*(ushort *)(lVar4 + 0x1e + DAT_000293f8) * 0x10 +
                             (ulonglong)*(ushort *)(lVar4 + 0x1c + DAT_000293f8),pwVar9);
                uVar2 = *(uint *)(uVar6 * 0x45 + 0x3d + DAT_000293f8);
                lVar4 = (**(code **)(DAT_00029498 + 0x140))(&DAT_00024858,0,local_268);
                if (-1 < lVar4) {
                  FUN_000137dc((ulonglong)uVar2,local_258,local_268);
                }
                pwVar9 = local_258;
                FUN_00000680(DAT_0002b1f8,*(short *)((longlong)piVar12 + uVar10 * 2 + 6),
                             &DAT_00025b68,(ulonglong)pwVar9);
                piVar5 = local_res10;
                lVar4 = DAT_000293e8;
              }
              uVar10 = (ulonglong)(ushort)((short)uVar10 + 1);
              uVar6 = local_res8;
              piVar11 = local_res18;
            } while (uVar10 < (ulonglong)*(ushort *)(piVar7 + 1) - 2 >> 1);
          }
        }
        piVar7 = (int *)((longlong)piVar7 + (ulonglong)*(ushort *)(piVar7 + 1) + 4);
      } while (piVar7 < (int *)(uVar6 + (longlong)piVar11));
    }
  }
  if (piVar11 != (int *)0x0) {
    (**(code **)(DAT_00029498 + 0x48))(piVar11);
  }
  if (piVar8 != (int *)0x0) {
    (**(code **)(DAT_00029498 + 0x48))(piVar8);
  }
  return 0;
}


// ==== FUN_000145e4 @ 000145e4

longlong FUN_000145e4(void)

{
  ushort uVar1;
  ushort uVar2;
  longlong lVar3;
  longlong lVar4;
  ulonglong uVar5;
  undefined4 *puVar6;
  uint *puVar7;
  uint *puVar8;
  uint *puVar9;
  undefined *puVar10;
  longlong *plVar11;
  uint *puVar12;
  uint *puVar13;
  ulonglong uVar14;
  uint *local_res8;
  uint *local_res10;
  uint *local_res18;
  longlong local_res20;
  longlong *local_68;
  longlong local_60;
  undefined4 local_58;
  undefined4 local_54;
  undefined4 local_50;
  undefined4 local_4c;
  
  local_58 = 0xc923ca9;
  local_54 = 0x4ac8df73;
  local_50 = 0xdd98d2b6;
  local_res10 = (uint *)0x0;
  local_4c = 0xfc990dc3;
  local_res18 = (uint *)0x0;
  local_res8 = (uint *)0x0;
  local_res20 = 0;
  lVar3 = FUN_0001d808(u_OriUefiDevOrder_00027798,&local_58,0,&local_res8,(longlong *)&local_res18);
  puVar8 = local_res18;
  puVar7 = (uint *)0x0;
  if ((-1 < lVar3) && (puVar7 = (uint *)0x0, &IMAGE_DOS_HEADER_00000000.e_crlc < local_res8)) {
    puVar10 = (undefined *)0x0;
    plVar11 = &local_res20;
    puVar6 = &local_58;
    lVar3 = FUN_0001d808(u_FixedHiiUefiDevData_000277b8,puVar6,0,plVar11,(longlong *)&local_res10);
    if (lVar3 < 0) {
      return lVar3;
    }
    puVar7 = local_res10;
    puVar9 = puVar8;
    puVar12 = local_res8;
    puVar13 = local_res8;
    if (puVar8 < (uint *)((longlong)local_res8 + (longlong)puVar8)) {
      do {
        uVar14 = 0;
        uVar2 = FUN_00013670((short)*puVar9);
        uVar5 = (ulonglong)uVar2;
        local_68 = (longlong *)(uVar5 * 5);
        uVar2 = 0;
        if ((*(short *)(DAT_000293e8 + 4 + uVar5 * 10) != 0) &&
           (puVar13 = puVar7, puVar7 < (uint *)(local_res20 + (longlong)puVar7))) {
          puVar6 = (undefined4 *)(ulonglong)*puVar9;
          do {
            if (*puVar13 == *puVar9) break;
            puVar13 = (uint *)((longlong)puVar13 + (ulonglong)(ushort)puVar13[1] + 4);
          } while (puVar13 < (uint *)(local_res20 + (longlong)puVar7));
        }
        if (((ulonglong)(ushort)puVar9[1] - 2 & 0xfffffffffffffffc) != 0) {
          do {
            lVar3 = FUN_00013d6c(*(ushort *)((longlong)puVar9 + uVar14 * 4 + 6),puVar6,puVar10,
                                 plVar11);
            if (lVar3 != 0) {
              if (*(short *)(DAT_000293e8 + 4 + uVar5 * 10) != 0) {
                local_68 = (longlong *)(lVar3 + 6);
                lVar4 = (**(code **)(DAT_00029498 + 0x140))(&DAT_00024858,0,&local_60);
                if (-1 < lVar4) {
                  FUN_0001387c(lVar3,&local_68,&local_60);
                }
                puVar10 = &DAT_00025b68;
                uVar1 = *(ushort *)((longlong)puVar13 + uVar14 * 2 + 6);
                puVar6 = (undefined4 *)(ulonglong)uVar1;
                plVar11 = local_68;
                FUN_00000680(DAT_0002b1f8,uVar1,&DAT_00025b68,(ulonglong)local_68);
              }
              (**(code **)(DAT_00029498 + 0x48))(lVar3);
            }
            uVar2 = uVar2 + 1;
            uVar14 = (ulonglong)uVar2;
            puVar7 = local_res10;
            puVar8 = local_res18;
            puVar12 = local_res8;
          } while (uVar14 < (ulonglong)(ushort)puVar9[1] - 2 >> 2);
        }
        puVar9 = (uint *)((longlong)puVar9 + (ulonglong)(ushort)puVar9[1] + 4);
      } while (puVar9 < (uint *)((longlong)puVar12 + (longlong)puVar8));
    }
  }
  if (puVar8 != (uint *)0x0) {
    (**(code **)(DAT_00029498 + 0x48))(puVar8);
  }
  if (puVar7 != (uint *)0x0) {
    (**(code **)(DAT_00029498 + 0x48))(puVar7);
  }
  return 0;
}


// ==== FUN_0001480c @ 0001480c

void FUN_0001480c(ushort param_1,byte param_2)

{
  short sVar1;
  uint uVar2;
  uint *puVar3;
  longlong lVar4;
  ulonglong uVar5;
  uint *puVar6;
  ushort uVar7;
  ushort uVar9;
  longlong lVar10;
  ulonglong *puVar11;
  uint *local_res18;
  ulonglong local_res20;
  wchar_t local_248 [264];
  ulonglong uVar8;
  
  uVar5 = 0;
  local_res18 = (uint *)0x0;
  local_res20 = 0;
  uVar8 = 0;
  uVar9 = 0;
  if (DAT_000293e8 == (short *)0x0) {
    uVar8 = 0;
  }
  else {
    sVar1 = *DAT_000293e8;
    while (sVar1 != 0) {
      uVar9 = (short)uVar8 + 1;
      uVar8 = (ulonglong)uVar9;
      sVar1 = DAT_000293e8[uVar8 * 5];
    }
    uVar8 = uVar5;
    if (uVar9 != 0) {
      do {
        if (DAT_000293e8[uVar8 * 5] == param_1) break;
        uVar7 = (short)uVar8 + 1;
        uVar8 = (ulonglong)uVar7;
      } while (uVar7 < uVar9);
    }
  }
  if (0x11 < param_2) {
    FUN_00013dc8(DAT_000293e8[uVar8 * 5 + 1],0);
    return;
  }
  puVar11 = &local_res20;
  if (DAT_000293d8 == '\0') {
    lVar4 = FUN_0001d808(u_OriFboLegacyDevOrder_00027738,&DAT_00024858,0,puVar11,
                         (longlong *)&local_res18);
  }
  else {
    lVar4 = FUN_0001d808(u_DefaultLegacyDevOrder_000277e0,&DAT_00024848,0,puVar11,
                         (longlong *)&local_res18);
    FUN_00014240((longlong *)&local_res18,(longlong *)&local_res20);
  }
  puVar3 = local_res18;
  if ((-1 < lVar4) && (5 < local_res20)) {
    for (puVar6 = local_res18; puVar6 < (uint *)(local_res20 + (longlong)local_res18);
        puVar6 = (uint *)((longlong)puVar6 + (ulonglong)(ushort)puVar6[1] + 4)) {
      if ((*puVar6 == (uint)param_1) && (2 < (ushort)puVar6[1])) {
        lVar4 = (ulonglong)(byte)*(undefined2 *)((longlong)puVar6 + (ulonglong)param_2 * 2 + 6) *
                0x45;
        lVar10 = (ulonglong)*(ushort *)(lVar4 + 0x1e + DAT_000293f8) * 0x10 +
                 (ulonglong)*(ushort *)(lVar4 + 0x1c + DAT_000293f8);
        goto LAB_0001499a;
      }
    }
  }
  goto LAB_00014a20;
  while (uVar5 = uVar5 + 1, uVar5 < 10) {
LAB_0001499a:
    if (*(char *)(uVar5 + lVar10) == ':') {
      lVar10 = lVar10 + 1 + uVar5;
      break;
    }
  }
  FUN_0001dff0(local_248,(wchar_t *)&DAT_0002672c,lVar10,puVar11);
  uVar2 = *(uint *)(lVar4 + 0x3d + DAT_000293f8);
  lVar4 = (**(code **)(DAT_00029498 + 0x140))(&DAT_00024858,0,&local_res18);
  if (-1 < lVar4) {
    FUN_000137dc((ulonglong)uVar2,local_248,(longlong *)&local_res18);
  }
  FUN_00013dc8(DAT_000293e8[uVar8 * 5 + 1],(longlong)local_248);
LAB_00014a20:
  if (puVar3 != (uint *)0x0) {
    (**(code **)(DAT_00029498 + 0x48))(puVar3);
  }
  return;
}


// ==== FUN_00014a50 @ 00014a50

void FUN_00014a50(ushort param_1,byte param_2)

{
  short sVar1;
  uint *puVar2;
  longlong lVar3;
  longlong lVar4;
  wchar_t *pwVar5;
  uint *puVar6;
  ushort uVar7;
  ushort uVar9;
  ulonglong *puVar11;
  uint *puVar12;
  uint *local_res18;
  ulonglong local_res20;
  longlong local_48;
  undefined4 local_40;
  undefined4 local_3c;
  undefined4 local_38;
  undefined4 local_34;
  ulonglong uVar8;
  ulonglong uVar10;
  
  uVar10 = 0;
  local_40 = 0xc923ca9;
  local_3c = 0x4ac8df73;
  local_38 = 0xdd98d2b6;
  uVar8 = 0;
  uVar7 = 0;
  local_34 = 0xfc990dc3;
  local_res18 = (uint *)0x0;
  local_res20 = 0;
  if (DAT_000293e8 == (short *)0x0) {
    uVar10 = 0;
  }
  else {
    sVar1 = *DAT_000293e8;
    while (sVar1 != 0) {
      uVar7 = (short)uVar8 + 1;
      uVar8 = (ulonglong)uVar7;
      sVar1 = DAT_000293e8[uVar8 * 5];
    }
    if (uVar7 != 0) {
      do {
        if (DAT_000293e8[uVar10 * 5] == param_1) break;
        uVar9 = (short)uVar10 + 1;
        uVar10 = (ulonglong)uVar9;
      } while (uVar9 < uVar7);
    }
  }
  if (param_2 < 0x12) {
    puVar11 = &local_res20;
    pwVar5 = u_DefaultUefiDevOrder_00027810;
    if (DAT_000293d8 == '\0') {
      pwVar5 = u_OriUefiDevOrder_00027798;
    }
    lVar3 = FUN_0001d808(pwVar5,&local_40,0,puVar11,(longlong *)&local_res18);
    puVar2 = local_res18;
    if (((-1 < lVar3) && (5 < local_res20)) &&
       (puVar12 = (uint *)(local_res20 + (longlong)local_res18), local_res18 < puVar12)) {
      puVar6 = local_res18;
      do {
        if ((*puVar6 == (uint)param_1) && (2 < (ushort)puVar6[1])) {
          lVar3 = FUN_00013d6c(*(ushort *)((longlong)puVar6 + (ulonglong)param_2 * 4 + 6),puVar12,
                               (ulonglong)param_1,puVar11);
          if (lVar3 != 0) {
            local_res18 = (uint *)(lVar3 + 6);
            lVar4 = (**(code **)(DAT_00029498 + 0x140))(&DAT_00024858,0,&local_48);
            puVar12 = (uint *)(lVar3 + 6);
            if (-1 < lVar4) {
              FUN_0001387c(lVar3,&local_res18,&local_48);
              puVar12 = local_res18;
            }
            FUN_00013dc8(DAT_000293e8[uVar10 * 5 + 1],(longlong)puVar12);
            (**(code **)(DAT_00029498 + 0x48))(lVar3);
          }
          break;
        }
        puVar6 = (uint *)((longlong)puVar6 + (ulonglong)(ushort)puVar6[1] + 4);
      } while (puVar6 < puVar12);
    }
    if (puVar2 != (uint *)0x0) {
      (**(code **)(DAT_00029498 + 0x48))(puVar2);
    }
  }
  else {
    FUN_00013dc8(DAT_000293e8[uVar10 * 5 + 1],0);
  }
  return;
}


// ==== FUN_00014f50 @ 00014f50

longlong FUN_00014f50(void)

{
  uint uVar1;
  ushort uVar2;
  ushort uVar3;
  longlong lVar4;
  byte bVar5;
  ulonglong uVar6;
  ushort *puVar7;
  int *piVar8;
  int iVar9;
  ushort *puVar10;
  char cVar11;
  ulonglong uVar12;
  char cVar13;
  ulonglong uVar14;
  int *piVar15;
  ushort local_res8;
  ushort local_res10;
  ulonglong local_res20;
  ushort *local_288;
  longlong local_280;
  int *local_278;
  longlong local_270;
  longlong local_268;
  wchar_t local_258 [268];
  
  local_288 = (ushort *)0x0;
  local_res20 = 0;
  local_278 = (int *)0x0;
  local_280 = 0;
  if (DAT_000293d8 == '\0') {
    lVar4 = FUN_0001d808(u_FboLegacyDevOrder_00027710,&DAT_00024858,0,&local_res20,
                         (longlong *)&local_288);
  }
  else {
    lVar4 = FUN_0001d808(u_DefaultLegacyDevOrder_000277e0,&DAT_00024848,0,&local_res20,
                         (longlong *)&local_288);
    FUN_00014240((longlong *)&local_288,(longlong *)&local_res20);
  }
  puVar7 = local_288;
  piVar8 = (int *)0x0;
  puVar10 = puVar7;
  if ((-1 < lVar4) && (piVar8 = (int *)0x0, 6 < local_res20)) {
    lVar4 = FUN_0001d808(u_FixedHiiLegacyDevData_00027768,&DAT_00024858,0,&local_280,
                         (longlong *)&local_278);
    if (lVar4 < 0) {
      return lVar4;
    }
    piVar8 = local_278;
    piVar15 = local_278;
    if (puVar7 < (ushort *)(local_res20 + (longlong)puVar7)) {
      do {
        uVar14 = 0;
        cVar13 = '\0';
        iVar9 = *(int *)puVar7;
        uVar12 = 0;
        cVar11 = '\0';
        if (iVar9 != 0xff) {
          uVar2 = FUN_00013670((short)iVar9);
          uVar3 = FUN_00013638(DAT_000293f0,(short)iVar9);
          if ((uVar2 != 0xffff) && (uVar3 != 0xffff)) {
            uVar6 = 0;
            local_268 = (ulonglong)uVar2 * 5;
            if (*(short *)(DAT_000293e8 + 4 + (ulonglong)uVar2 * 10) != 0) {
              for (piVar15 = piVar8;
                  (piVar15 < (int *)(local_280 + (longlong)piVar8) && (*piVar15 != iVar9));
                  piVar15 = (int *)((longlong)piVar15 + (ulonglong)*(ushort *)(piVar15 + 1) + 4)) {
              }
            }
            if (piVar15 < (int *)(local_280 + (longlong)piVar8)) {
              local_res10 = 0;
              if (((ulonglong)puVar7[2] - 2 & 0xfffffffffffffffe) == 0) {
LAB_000152b9:
                bVar5 = 0x12;
              }
              else {
                local_res8 = ((short)piVar15 - (short)piVar8) + 6;
                do {
                  if (*(short *)(DAT_000293e8 + 4 + local_268 * 2) != 0) {
                    uVar2 = puVar7[uVar6 + 3];
                    lVar4 = (ulonglong)(byte)uVar2 * 0x45;
                    FUN_0001dff0(local_258,(wchar_t *)&DAT_0002672c,
                                 (ulonglong)*(ushort *)(lVar4 + 0x1e + DAT_000293f8) * 0x10 +
                                 (ulonglong)*(ushort *)(lVar4 + 0x1c + DAT_000293f8),
                                 (ulonglong)local_res8);
                    uVar1 = *(uint *)((ulonglong)(byte)uVar2 * 0x45 + 0x3d + DAT_000293f8);
                    lVar4 = (**(code **)(DAT_00029498 + 0x140))(&DAT_00024858,0,&local_270);
                    if (-1 < lVar4) {
                      FUN_000137dc((ulonglong)uVar1,local_258,&local_270);
                    }
                    if (0x100 < *(ushort *)((longlong)piVar15 + uVar6 * 2 + 6)) {
                      FUN_00000680(DAT_0002b1f8,*(short *)((longlong)piVar15 + uVar6 * 2 + 6),
                                   &DAT_00025b68,(ulonglong)local_258);
                      FUN_000140b8(local_res8,(ulonglong)local_258);
                    }
                  }
                  lVar4 = uVar14 + (ulonglong)uVar3 * 0x12;
                  cVar11 = (char)uVar12;
                  if ((puVar7[uVar6 + 3] & 0xff00) == 0) {
                    lVar4 = lVar4 + uVar12;
                    uVar12 = (ulonglong)(byte)(cVar11 + 1);
                    (&DAT_0002b080)[lVar4] = (char)uVar14 + cVar11;
                  }
                  else {
                    uVar14 = (ulonglong)(byte)((char)uVar14 + 1);
                    (&DAT_0002b080)[lVar4 + uVar12] = 0x12;
                  }
                  cVar13 = (char)uVar14;
                  cVar11 = (char)uVar12;
                  if (0x11 < (uint)((int)uVar14 + (int)uVar12)) break;
                  local_res10 = local_res10 + 1;
                  local_res8 = local_res8 + 2;
                  uVar6 = (ulonglong)local_res10;
                } while (uVar6 < (ulonglong)puVar7[2] - 2 >> 1);
                piVar8 = local_278;
                puVar10 = local_288;
                if (cVar11 == '\0') goto LAB_000152b9;
                bVar5 = 0;
              }
              FUN_0001480c(*puVar7,bVar5);
              (&DAT_0002b060)[uVar3] = cVar11;
              if (cVar13 != '\0') {
                (&DAT_0002b060)[uVar3] = cVar13 + cVar11;
              }
            }
          }
        }
        puVar7 = (ushort *)((longlong)puVar7 + (ulonglong)puVar7[2] + 4);
      } while (puVar7 < (ushort *)(local_res20 + (longlong)puVar10));
    }
  }
  if (puVar10 != (ushort *)0x0) {
    (**(code **)(DAT_00029498 + 0x48))(puVar10);
  }
  if (piVar8 != (int *)0x0) {
    (**(code **)(DAT_00029498 + 0x48))(piVar8);
  }
  return 0;
}


// ==== FUN_00015348 @ 00015348

longlong FUN_00015348(void)

{
  ushort uVar1;
  ushort uVar2;
  longlong lVar3;
  wchar_t *pwVar4;
  byte bVar5;
  ulonglong uVar6;
  ushort uVar7;
  uint *puVar8;
  ulonglong uVar9;
  uint *puVar10;
  uint *puVar11;
  uint uVar12;
  longlong *plVar13;
  longlong *plVar14;
  ulonglong unaff_R13;
  uint *puVar15;
  char cVar16;
  ulonglong unaff_R15;
  undefined2 local_res8;
  undefined6 uStackX_a;
  longlong *local_res10;
  ulonglong local_res18;
  uint *local_res20;
  uint *local_88;
  longlong local_80;
  longlong local_78;
  longlong local_70;
  longlong local_68;
  undefined4 local_60;
  undefined4 local_5c;
  undefined4 local_58;
  undefined4 local_54;
  
  local_60 = 0xc923ca9;
  local_5c = 0x4ac8df73;
  local_58 = 0xdd98d2b6;
  local_88 = (uint *)0x0;
  local_54 = 0xfc990dc3;
  local_res20 = (uint *)0x0;
  pwVar4 = u_DefaultUefiDevOrder_00027810;
  local_res18 = 0;
  local_80 = 0;
  if (DAT_000293d8 == '\0') {
    pwVar4 = u_UefiDevOrder_00027838;
  }
  lVar3 = FUN_0001d808(pwVar4,&local_60,0,&local_res18,(longlong *)&local_res20);
  puVar10 = local_res20;
  puVar8 = (uint *)0x0;
  if ((-1 < lVar3) && (puVar8 = (uint *)0x0, 6 < local_res18)) {
    plVar13 = (longlong *)0x0;
    plVar14 = &local_80;
    lVar3 = FUN_0001d808(u_FixedHiiUefiDevData_000277b8,&local_60,0,plVar14,(longlong *)&local_88);
    if (lVar3 < 0) {
      return lVar3;
    }
    puVar8 = local_88;
    if (puVar10 < (uint *)(local_res18 + (longlong)puVar10)) {
      puVar15 = (uint *)CONCAT62(uStackX_a,local_res8);
      puVar11 = puVar10;
      do {
        uVar9 = 0;
        unaff_R13 = unaff_R13 & 0xffffffffffffff00;
        unaff_R15 = unaff_R15 & 0xffffffffffffff00;
        uVar1 = FUN_00013670((ushort)*puVar11);
        uVar6 = (ulonglong)(ushort)*puVar11;
        uVar2 = FUN_00013638(DAT_00029400,(ushort)*puVar11);
        if ((uVar1 != 0xffff) && (uVar2 != 0xffff)) {
          local_70 = (ulonglong)uVar1 * 5;
          uVar7 = 0;
          if ((*(short *)(DAT_000293e8 + 4 + (ulonglong)uVar1 * 10) != 0) &&
             (puVar15 = puVar8, puVar8 < (uint *)(local_80 + (longlong)puVar8))) {
            uVar6 = (ulonglong)*puVar11;
            do {
              if (*puVar15 == *puVar11) break;
              puVar15 = (uint *)((longlong)puVar15 + (ulonglong)(ushort)puVar15[1] + 4);
            } while (puVar15 < (uint *)(local_80 + (longlong)puVar8));
          }
          if (puVar15 < (uint *)(local_80 + (longlong)puVar8)) {
            if (((ulonglong)(ushort)puVar11[1] - 2 & 0xfffffffffffffffc) == 0) {
LAB_0001560c:
              bVar5 = 0x12;
            }
            else {
              uVar1 = ((short)puVar15 - (short)puVar8) + 6;
              do {
                local_78 = FUN_00013d6c(*(ushort *)((longlong)puVar11 + uVar9 * 4 + 6),uVar6,plVar13
                                        ,plVar14);
                plVar13 = (longlong *)0x0;
                if (local_78 != 0) {
                  if (*(short *)(DAT_000293e8 + 4 + local_70 * 2) != 0) {
                    plVar13 = &local_68;
                    local_res10 = (longlong *)(local_78 + 6);
                    plVar14 = DAT_00029498;
                    lVar3 = (*(code *)DAT_00029498[0x28])(&DAT_00024858,0);
                    if (-1 < lVar3) {
                      plVar13 = &local_68;
                      FUN_0001387c(local_78,&local_res10,plVar13);
                    }
                    if (0x100 < *(ushort *)((longlong)puVar15 + uVar9 * 2 + 6)) {
                      plVar13 = (longlong *)&DAT_00025b68;
                      plVar14 = local_res10;
                      FUN_00000680(DAT_0002b1f8,*(short *)((longlong)puVar15 + uVar9 * 2 + 6),
                                   &DAT_00025b68,(ulonglong)local_res10);
                      FUN_0001417c(uVar1,(ulonglong)local_res10);
                    }
                  }
                  (*(code *)DAT_00029498[9])(local_78);
                }
                uVar6 = (unaff_R15 & 0xff) + (ulonglong)uVar2 * 0x12 + (unaff_R13 & 0xff);
                if ((*(uint *)((longlong)puVar11 + uVar9 * 4 + 6) & 0xff000000) == 0) {
                  uVar12 = (int)unaff_R15 + (int)unaff_R13;
                  plVar13 = (longlong *)(ulonglong)uVar12;
                  unaff_R13 = CONCAT71((int7)(unaff_R13 >> 8),(char)unaff_R13 + '\x01');
                  (&DAT_0002b200)[uVar6] = (char)uVar12;
                }
                else {
                  (&DAT_0002b200)[uVar6] = 0x12;
                  unaff_R15 = CONCAT71((int7)(unaff_R15 >> 8),(char)unaff_R15 + '\x01');
                }
                if (0x11 < ((uint)unaff_R15 & 0xff) + ((uint)unaff_R13 & 0xff)) break;
                uVar7 = uVar7 + 1;
                uVar1 = uVar1 + 2;
                uVar9 = (ulonglong)uVar7;
              } while (uVar9 < (ulonglong)(ushort)puVar11[1] - 2 >> 2);
              puVar8 = local_88;
              puVar10 = local_res20;
              if ((char)unaff_R13 == '\0') goto LAB_0001560c;
              bVar5 = 0;
            }
            FUN_00014a50((ushort)*puVar11,bVar5);
            (&DAT_0002b1e0)[uVar2] = (char)unaff_R13;
            if ((char)unaff_R15 != '\0') {
              cVar16 = (char)unaff_R15 + (char)unaff_R13;
              unaff_R15 = CONCAT71((int7)(unaff_R15 >> 8),cVar16);
              (&DAT_0002b1e0)[uVar2] = cVar16;
            }
          }
        }
        puVar11 = (uint *)((longlong)puVar11 + (ulonglong)(ushort)puVar11[1] + 4);
      } while (puVar11 < (uint *)(local_res18 + (longlong)puVar10));
    }
  }
  if (puVar10 != (uint *)0x0) {
    (*(code *)DAT_00029498[9])(puVar10);
  }
  if (puVar8 != (uint *)0x0) {
    (*(code *)DAT_00029498[9])(puVar8);
  }
  return 0;
}


// ==== FUN_0001568c @ 0001568c

longlong FUN_0001568c(undefined8 param_1)

{
  int *piVar1;
  longlong lVar2;
  int *piVar3;
  ulonglong uVar4;
  short sVar5;
  int *piVar6;
  int *piVar7;
  ushort uVar8;
  bool bVar9;
  undefined2 local_res10 [4];
  ulonglong local_res18;
  int *local_res20;
  undefined4 local_48;
  undefined4 local_44;
  undefined4 local_40;
  undefined4 local_3c;
  
  local_48 = 0xc923ca9;
  local_44 = 0x4ac8df73;
  local_40 = 0xdd98d2b6;
  local_3c = 0xfc990dc3;
  local_res18 = 0;
  local_res10[0] = 0;
  local_res20 = (int *)0x0;
  if ((DAT_000293d0 == 0) &&
     (lVar2 = (**(code **)(DAT_00029498 + 0x140))(&DAT_000237c0,0), lVar2 < 0)) {
    return lVar2;
  }
  lVar2 = FUN_0001d808(u_FboLegacyDevOrder_00027710,&local_48,0,&local_res18,
                       (longlong *)&local_res20);
  if ((-1 < lVar2) && (6 < local_res18)) {
    piVar3 = (int *)FUN_0001d774(local_res18);
    piVar1 = local_res20;
    if (piVar3 == (int *)0x0) {
      lVar2 = -0x7ffffffffffffff7;
    }
    else {
      bVar9 = local_res20 < (int *)((longlong)local_res20 + local_res18);
      uVar4 = local_res18;
      piVar6 = piVar3;
      piVar7 = local_res20;
      while (bVar9) {
        if (*piVar7 != 0xff) {
          *piVar6 = *piVar7;
          *(short *)(piVar6 + 1) = ((short)((ulonglong)*(ushort *)(piVar7 + 1) - 2 >> 1) + 1) * 2;
          uVar8 = 0;
          if (((ulonglong)*(ushort *)(piVar7 + 1) - 2 & 0xfffffffffffffffe) != 0) {
            do {
              if (0x11 < uVar8) break;
              lVar2 = FUN_00013c34(param_1,local_res10);
              if (lVar2 < 0) {
                return lVar2;
              }
              uVar4 = (ulonglong)uVar8;
              uVar8 = uVar8 + 1;
              *(undefined2 *)((longlong)piVar6 + uVar4 * 2 + 6) = local_res10[0];
            } while ((ulonglong)uVar8 < (ulonglong)*(ushort *)(piVar7 + 1) - 2 >> 1);
          }
          piVar6 = (int *)((longlong)piVar6 + (ulonglong)*(ushort *)(piVar6 + 1) + 4);
          uVar4 = local_res18;
        }
        piVar7 = (int *)((longlong)piVar7 + (ulonglong)*(ushort *)(piVar7 + 1) + 4);
        bVar9 = piVar7 < (int *)((longlong)piVar1 + uVar4);
      }
      sVar5 = (short)piVar6 - (short)piVar3;
      if (sVar5 != 0) {
        (**(code **)(DAT_000294a0 + 0x58))
                  (u_FixedHiiLegacyDevData_00027768,&local_48,2,sVar5,piVar3);
      }
      (**(code **)(DAT_00029498 + 0x48))(piVar3);
      lVar2 = 0;
    }
  }
  return lVar2;
}


// ==== FUN_0001585c @ 0001585c

longlong FUN_0001585c(undefined8 param_1)

{
  undefined4 *puVar1;
  longlong lVar2;
  undefined4 *puVar3;
  ulonglong uVar4;
  short sVar5;
  undefined4 *puVar6;
  undefined4 *puVar7;
  ushort uVar8;
  bool bVar9;
  undefined2 local_res10 [4];
  ulonglong local_res18;
  undefined4 *local_res20;
  undefined4 local_48;
  undefined4 local_44;
  undefined4 local_40;
  undefined4 local_3c;
  
  local_48 = 0xc923ca9;
  local_44 = 0x4ac8df73;
  local_40 = 0xdd98d2b6;
  local_3c = 0xfc990dc3;
  local_res18 = 0;
  local_res10[0] = 0;
  local_res20 = (undefined4 *)0x0;
  if ((DAT_000293d0 == 0) &&
     (lVar2 = (**(code **)(DAT_00029498 + 0x140))(&DAT_000237c0,0), lVar2 < 0)) {
    return lVar2;
  }
  lVar2 = FUN_0001d808(u_UefiDevOrder_00027838,&local_48,0,&local_res18,(longlong *)&local_res20);
  if ((-1 < lVar2) && (6 < local_res18)) {
    puVar3 = (undefined4 *)FUN_0001d774(local_res18);
    puVar1 = local_res20;
    if (puVar3 == (undefined4 *)0x0) {
      lVar2 = -0x7ffffffffffffff7;
    }
    else {
      bVar9 = local_res20 < (undefined4 *)(local_res18 + (longlong)local_res20);
      puVar6 = puVar3;
      puVar7 = local_res20;
      while (bVar9) {
        *puVar6 = *puVar7;
        *(short *)(puVar6 + 1) = ((short)((ulonglong)*(ushort *)(puVar7 + 1) - 2 >> 2) + 1) * 2;
        uVar8 = 0;
        if (((ulonglong)*(ushort *)(puVar7 + 1) - 2 & 0xfffffffffffffffc) != 0) {
          do {
            if (0x11 < uVar8) break;
            lVar2 = FUN_00013c34(param_1,local_res10);
            if (lVar2 < 0) {
              return lVar2;
            }
            uVar4 = (ulonglong)uVar8;
            uVar8 = uVar8 + 1;
            *(undefined2 *)((longlong)puVar6 + uVar4 * 2 + 6) = local_res10[0];
          } while ((ulonglong)uVar8 < (ulonglong)*(ushort *)(puVar7 + 1) - 2 >> 2);
        }
        puVar6 = (undefined4 *)((longlong)puVar6 + (ulonglong)*(ushort *)(puVar6 + 1) + 4);
        puVar7 = (undefined4 *)((longlong)puVar7 + (ulonglong)*(ushort *)(puVar7 + 1) + 4);
        bVar9 = puVar7 < (undefined4 *)(local_res18 + (longlong)puVar1);
      }
      sVar5 = (short)puVar6 - (short)puVar3;
      if (sVar5 != 0) {
        (**(code **)(DAT_000294a0 + 0x58))(u_FixedHiiUefiDevData_000277b8,&local_48,2,sVar5,puVar3);
      }
      (**(code **)(DAT_00029498 + 0x48))(puVar3);
      lVar2 = 0;
    }
  }
  return lVar2;
}


// ==== FUN_00015c60 @ 00015c60

void FUN_00015c60(char param_1,undefined8 param_2,uint *param_3)

{
  short sVar1;
  uint uVar2;
  uint *puVar3;
  longlong lVar4;
  longlong lVar5;
  ulonglong uVar6;
  ushort uVar7;
  uint *puVar8;
  longlong *plVar9;
  ulonglong *puVar10;
  ushort uVar11;
  ushort uVar12;
  ulonglong local_res20;
  uint *local_248;
  longlong local_240;
  wchar_t local_238 [264];
  ulonglong uVar13;
  
  local_248 = (uint *)0x0;
  local_res20 = 0;
  uVar12 = 0;
  uVar7 = uVar12;
  if (DAT_000293e8 != (short *)0x0) {
    sVar1 = *DAT_000293e8;
    while (sVar1 != 0) {
      uVar7 = uVar7 + 1;
      sVar1 = DAT_000293e8[(ulonglong)uVar7 * 5];
    }
  }
  plVar9 = (longlong *)0x0;
  puVar10 = &local_res20;
  lVar4 = FUN_0001d808(param_2,param_3,0,puVar10,(longlong *)&local_248);
  puVar3 = local_248;
  if (-1 < lVar4) {
    if (param_1 == '\0') {
      if ((5 < local_res20) &&
         (uVar6 = local_res20, puVar8 = local_248,
         local_248 < (uint *)(local_res20 + (longlong)local_248))) {
        do {
          if (2 < (ushort)puVar8[1]) {
            uVar13 = 0;
            uVar12 = 0;
            if (uVar7 != 0) {
              do {
                uVar12 = (ushort)uVar13;
                if ((uint)(ushort)DAT_000293e8[uVar13 * 5] == *puVar8) break;
                uVar12 = uVar12 + 1;
                uVar13 = (ulonglong)uVar12;
              } while (uVar12 < uVar7);
            }
            if (uVar7 != uVar12) {
              if ((DAT_00024776 == '\0') || ((*(ushort *)((longlong)puVar8 + 6) & 0xff00) != 0)) {
                FUN_00013dc8(DAT_000293e8[(ulonglong)uVar12 * 5 + 1],0);
                uVar6 = local_res20;
              }
              else {
                lVar4 = (ulonglong)*(ushort *)((longlong)puVar8 + 6) * 0x45;
                lVar4 = (ulonglong)*(ushort *)(lVar4 + 0x1e + DAT_000293f8) * 0x10 +
                        (ulonglong)*(ushort *)(lVar4 + 0x1c + DAT_000293f8);
                uVar6 = 0;
                do {
                  if (*(char *)(uVar6 + lVar4) == ':') {
                    lVar4 = lVar4 + 1 + uVar6;
                    break;
                  }
                  uVar6 = uVar6 + 1;
                } while (uVar6 < 10);
                FUN_0001dff0(local_238,(wchar_t *)&DAT_0002672c,lVar4,puVar10);
                uVar2 = *(uint *)((ulonglong)*(ushort *)((longlong)puVar8 + 6) * 0x45 + 0x3d +
                                 DAT_000293f8);
                lVar4 = (*(code *)DAT_00029498[0x28])(&DAT_00024858,0,&local_240);
                if (-1 < lVar4) {
                  FUN_000137dc((ulonglong)uVar2,local_238,&local_240);
                }
                FUN_00013dc8(DAT_000293e8[(ulonglong)uVar12 * 5 + 1],(longlong)local_238);
                uVar6 = local_res20;
              }
            }
          }
          puVar8 = (uint *)((longlong)puVar8 + (ulonglong)(ushort)puVar8[1] + 4);
        } while (puVar8 < (uint *)(uVar6 + (longlong)puVar3));
      }
    }
    else if ((5 < local_res20) &&
            (puVar8 = local_248, local_248 < (uint *)(local_res20 + (longlong)local_248))) {
      do {
        if (2 < (ushort)puVar8[1]) {
          uVar6 = 0;
          uVar11 = uVar12;
          if (uVar7 != 0) {
            do {
              uVar11 = (ushort)uVar6;
              if ((uint)(ushort)DAT_000293e8[uVar6 * 5] == *puVar8) break;
              uVar11 = uVar11 + 1;
              uVar6 = (ulonglong)uVar11;
            } while (uVar11 < uVar7);
          }
          if (uVar7 != uVar11) {
            if ((DAT_00024776 == '\0') || ((*(uint *)((longlong)puVar8 + 6) & 0xff000000) != 0)) {
              param_3 = (uint *)0x0;
              FUN_00013dc8(DAT_000293e8[(ulonglong)uVar11 * 5 + 1],0);
            }
            else {
              lVar4 = FUN_00013d6c(*(ushort *)((longlong)puVar8 + 6),param_3,plVar9,puVar10);
              if (lVar4 != 0) {
                param_3 = (uint *)(lVar4 + 6);
                plVar9 = &local_240;
                puVar10 = DAT_00029498;
                local_248 = param_3;
                lVar5 = (*(code *)DAT_00029498[0x28])(&DAT_00024858,0);
                if (-1 < lVar5) {
                  plVar9 = &local_240;
                  FUN_0001387c(lVar4,&local_248,plVar9);
                  param_3 = local_248;
                }
                FUN_00013dc8(DAT_000293e8[(ulonglong)uVar11 * 5 + 1],(longlong)param_3);
                (*(code *)DAT_00029498[9])(lVar4);
              }
            }
          }
        }
        puVar8 = (uint *)((longlong)puVar8 + (ulonglong)(ushort)puVar8[1] + 4);
      } while (puVar8 < (uint *)(local_res20 + (longlong)puVar3));
    }
    (*(code *)DAT_00029498[9])(puVar3);
  }
  return;
}


// ==== FUN_00016048 @ 00016048

void FUN_00016048(void)

{
  wchar_t *pwVar1;
  
  DAT_00024776 = 1;
  if (DAT_000293d8 == '\0') {
    FUN_00015c60('\0',u_FboLegacyDevOrder_00027710,(uint *)&DAT_00024858);
    pwVar1 = u_UefiDevOrder_00027838;
  }
  else {
    FUN_00015c60('\0',u_DefaultLegacyDevOrder_000277e0,(uint *)&DAT_00024848);
    pwVar1 = u_DefaultUefiDevOrder_00027810;
  }
  FUN_00015c60('\x01',pwVar1,(uint *)&DAT_00024858);
  return;
}


// ==== FUN_000160a8 @ 000160a8

longlong FUN_000160a8(undefined8 param_1,ushort param_2)

{
  short sVar1;
  bool bVar2;
  short *psVar3;
  longlong lVar4;
  ulonglong uVar5;
  ulonglong uVar6;
  byte bVar7;
  ushort uVar8;
  undefined1 *puVar9;
  undefined8 local_res8;
  undefined8 local_res18;
  longlong local_res20;
  undefined4 local_378;
  undefined4 local_374;
  undefined4 local_370;
  undefined4 local_36c;
  undefined4 local_368;
  undefined4 local_364;
  undefined4 local_360;
  undefined4 local_35c;
  undefined4 local_358;
  undefined4 local_354;
  undefined4 local_350;
  undefined4 local_34c;
  undefined4 local_348;
  undefined4 local_344;
  undefined4 local_340;
  undefined4 local_33c;
  undefined4 local_338;
  undefined4 local_334;
  undefined4 local_330;
  undefined4 local_32c;
  undefined4 local_328;
  undefined4 local_324;
  undefined4 local_320;
  undefined4 local_31c;
  char *local_318;
  undefined8 local_310;
  longlong local_308;
  undefined1 local_300 [8];
  undefined8 local_2f8;
  undefined1 local_2f0 [40];
  undefined8 local_2c8 [40];
  undefined8 local_184 [41];
  
  local_368 = 0xdb9a1e3d;
  local_364 = 0x4abb45cb;
  local_360 = 0x38e53b85;
  local_35c = 0x2d2edb7f;
  local_308 = 0;
  local_358 = 0xec87d643;
  local_354 = 0x4bb5eba4;
  local_350 = 0x3e3fe5a1;
  local_34c = 0xa90db236;
  uVar8 = 0x1000;
  local_res20 = 0;
  bVar2 = false;
  local_378 = 0xde8ab926;
  local_374 = 0x4c23efda;
  local_370 = 0xfd98c4bb;
  local_36c = 0x6900aa29;
  local_310 = 0;
  local_318 = (char *)0x0;
  local_res8 = param_1;
  lVar4 = FUN_0001d808(u_CurrentSkipFboModule_00027858,&DAT_00024858,&local_res18,&local_310,
                       (longlong *)&local_318);
  if (lVar4 < 0) {
    DAT_00029408 = '\0';
  }
  else {
    DAT_00029408 = *local_318 != '\0';
    (**(code **)(DAT_00029498 + 0x48))();
  }
  if (DAT_00029408 == '\0') {
    uVar5 = (ulonglong)DAT_00024770;
    uVar6 = 0;
    if (DAT_00024770 != 0) {
      do {
        if (param_2 == ((ushort)uVar5 & 0xff)) {
          bVar2 = true;
        }
        uVar6 = (ulonglong)(byte)((char)uVar6 + 1);
        uVar5 = CONCAT71(0x247,(&DAT_00024770)[uVar6 * 3]);
      } while ((&DAT_00024770)[uVar6 * 3] != '\0');
      if (bVar2) {
        (**(code **)(DAT_000294a0 + 0x58))
                  (u_FixedBootOrderHii_00027888,&DAT_00024858,2,8,&local_res8);
        DAT_0002b1f8 = local_res8;
        lVar4 = (**(code **)(DAT_00029498 + 0x140))(&local_368,0,&local_308);
        if ((-1 < lVar4) &&
           (lVar4 = (**(code **)(local_308 + 0x30))
                              (local_308,&DAT_000293dc,&DAT_0002b040,&DAT_000293c8,&DAT_000293f8),
           lVar4 < 0)) {
          return lVar4;
        }
        lVar4 = (**(code **)(DAT_00029498 + 0x140))(&DAT_00024858,0,&local_res20);
        if (-1 < lVar4) {
          (**(code **)(local_res20 + 0x18))(&DAT_00024870);
          (**(code **)(local_res20 + 0x20))(&DAT_00024780);
          DAT_000293f0 = (short *)(**(code **)(local_res20 + 0x30))();
          DAT_00029400 = (short *)(**(code **)(local_res20 + 0x38))();
          DAT_000293e0 = (**(code **)(local_res20 + 0x40))();
          DAT_000293e8 = (**(code **)(local_res20 + 0x48))();
          FUN_000138f8();
        }
        (**(code **)(DAT_00029498 + 0x168))(&DAT_0002b060,0x12);
        (**(code **)(DAT_00029498 + 0x168))(&DAT_0002b1e0,0x12,0);
        (**(code **)(DAT_00029498 + 0x168))(local_2f0,0x23,0);
        FUN_0001568c(local_res8);
        FUN_00014f50();
        FUN_0001585c(local_res8);
        FUN_00015348();
        do {
          FUN_00001b1c(uVar8,0x14f04);
          psVar3 = DAT_000293f0;
          lVar4 = DAT_000293e8;
          uVar8 = uVar8 + 1;
        } while (uVar8 < 0x1200);
        uVar5 = 0;
        if (DAT_000293f0 != (short *)0x0) {
          sVar1 = *DAT_000293f0;
          while (sVar1 != 0) {
            uVar5 = (ulonglong)(ushort)((short)uVar5 + 1);
            sVar1 = *(short *)(uVar5 * 7 + (longlong)DAT_000293f0);
          }
          uVar6 = 0;
          if ((short)uVar5 != 0) {
            do {
              uVar8 = FUN_00013670(*(short *)(uVar6 * 7 + (longlong)psVar3));
              if ((uVar8 != 0xffff) && (*(short *)(lVar4 + 4 + (ulonglong)uVar8 * 10) != 0)) {
                local_2f0[*(ushort *)(lVar4 + 8 + (ulonglong)uVar8 * 10)] = (&DAT_0002b060)[uVar6];
              }
              bVar7 = (char)uVar6 + 1;
              uVar6 = (ulonglong)bVar7;
            } while ((ushort)bVar7 < (ushort)uVar5);
          }
        }
        psVar3 = DAT_00029400;
        uVar5 = 0;
        if (DAT_00029400 != (short *)0x0) {
          sVar1 = *DAT_00029400;
          while (sVar1 != 0) {
            uVar5 = (ulonglong)(ushort)((short)uVar5 + 1);
            sVar1 = *(short *)(uVar5 * 7 + (longlong)DAT_00029400);
          }
          uVar6 = 0;
          if ((short)uVar5 != 0) {
            do {
              uVar8 = FUN_00013670(*(short *)(uVar6 * 7 + (longlong)psVar3));
              if ((uVar8 != 0xffff) && (*(short *)(lVar4 + 4 + (ulonglong)uVar8 * 10) != 0)) {
                local_2f0[*(ushort *)(lVar4 + 8 + (ulonglong)uVar8 * 10)] = (&DAT_0002b1e0)[uVar6];
              }
              bVar7 = (char)uVar6 + 1;
              uVar6 = (ulonglong)bVar7;
            } while ((ushort)bVar7 < (ushort)uVar5);
          }
        }
        (**(code **)(DAT_000294a0 + 0x58))(u_FixedBootGroup_000278b0,&local_358,7,0x23,local_2f0);
        FUN_000233d0(local_2c8,(undefined8 *)&DAT_0002b080,0x144);
        FUN_000233d0(local_184,(undefined8 *)&DAT_0002b200,0x144);
        lVar4 = (**(code **)(DAT_000294a0 + 0x58))
                          (u_FixedBoot_000278d0,&local_378,7,0x288,local_2c8);
        if (lVar4 < 0) {
          (**(code **)(DAT_000294a0 + 0x58))(u_FixedBoot_000278d0,&local_378,0,0,0);
          (**(code **)(DAT_000294a0 + 0x58))(u_FixedBoot_000278d0,&local_378,7,0x288,local_2c8);
        }
        local_res18 = 0;
        local_348 = 0x7e07911a;
        local_344 = 0x4b0f4807;
        local_340 = 0x43f574a4;
        local_33c = 0xb407a91c;
        lVar4 = (**(code **)(DAT_00029498 + 0x80))(&local_res18,&local_348,0,&PTR_LAB_00024810);
        local_338 = 0x3677770f;
        local_334 = 0x43b2efb2;
        local_330 = 0x2b3aeb8;
        puVar9 = &LAB_00015fe8;
        local_32c = 0x824860e9;
        local_328 = 0x8c12a959;
        local_324 = 0x436270bc;
        local_320 = 0x5b837b4;
        local_31c = 0x6e91a114;
        (**(code **)(DAT_00029498 + 0x170))
                  (0x200,0x10,&LAB_00015fe8,&local_310,&DAT_00023540,&local_318);
        FUN_0001d8c8(&local_338,&LAB_00015fe8,puVar9,&local_318,&local_310);
        FUN_0001d8c8(&local_328,FUN_00016048,puVar9,&local_2f8,local_300);
        return lVar4;
      }
    }
  }
  return 0;
}


// ==== FUN_00016674 @ 00016674

undefined8 FUN_00016674(longlong param_1)

{
  longlong lVar1;
  undefined8 uVar2;
  undefined8 local_res8;
  
  local_res8 = 0;
  if ((param_1 != 0) &&
     (((DAT_00029410 != 0 ||
       (lVar1 = (**(code **)(DAT_00029498 + 0x140))(&DAT_000237c0,0,&DAT_00029410), -1 < lVar1)) &&
      (lVar1 = (**(code **)(DAT_00029410 + 0x18))(DAT_00029410,param_1,0,&local_res8),
      lVar1 == -0x7ffffffffffffffb)))) {
    uVar2 = FUN_0001d748(local_res8);
    lVar1 = (**(code **)(DAT_00029410 + 0x18))(DAT_00029410,param_1,uVar2,&local_res8);
    if (-1 < lVar1) {
      return uVar2;
    }
    (**(code **)(DAT_00029498 + 0x48))(uVar2);
  }
  return 0;
}


// ==== FUN_00016734 @ 00016734

longlong FUN_00016734(undefined8 param_1,undefined2 param_2,undefined2 param_3,char *param_4)

{
  char *pcVar1;
  char cVar2;
  char *pcVar3;
  longlong lVar4;
  longlong lVar5;
  ulonglong uVar6;
  char *pcVar7;
  ulonglong uVar8;
  ulonglong uVar9;
  char *local_res20;
  undefined8 local_138 [2];
  undefined1 local_128 [256];
  
  uVar9 = 0;
  local_138[0] = 0x80;
  if (param_4 == (char *)0x0) {
    lVar4 = -0x7ffffffffffffffe;
  }
  else {
    cVar2 = *param_4;
    uVar6 = uVar9;
    while (cVar2 != '\0') {
      uVar6 = uVar6 + 1;
      cVar2 = param_4[uVar6];
    }
    lVar4 = (**(code **)(DAT_00029498 + 0x40))(4,uVar6 + 1,&local_res20);
    if (-1 < lVar4) {
      cVar2 = *param_4;
      uVar6 = uVar9;
      while (cVar2 != '\0') {
        uVar6 = uVar6 + 1;
        cVar2 = param_4[uVar6];
      }
      (**(code **)(DAT_00029498 + 0x160))(local_res20,param_4,uVar6 + 1);
      cVar2 = *local_res20;
      pcVar3 = local_res20;
      while (cVar2 != '\0') {
        pcVar7 = pcVar3;
        uVar6 = uVar9;
        if (*pcVar3 != '\0') {
          do {
            if (*pcVar7 == ';') break;
            pcVar7 = pcVar7 + 1;
          } while (*pcVar7 != '\0');
          if (*pcVar7 != '\0') {
            *pcVar7 = '\0';
            pcVar7 = pcVar7 + 1;
          }
        }
        do {
          uVar8 = uVar6 + 1;
          pcVar1 = &DAT_000278e5 + uVar6;
          uVar6 = uVar8;
        } while (*pcVar1 != '\0');
        lVar5 = FUN_0001cf88(pcVar3,&DAT_000278e4,uVar8);
        if (lVar5 != 0) {
          lVar4 = (**(code **)(DAT_00029410 + 8))
                            (DAT_00029410,pcVar3,param_1,param_2,local_128,local_138,0);
          if (lVar4 < 0) break;
          (**(code **)(DAT_00029410 + 0x10))(DAT_00029410,param_1,param_3,pcVar3,local_128,0);
        }
        pcVar3 = pcVar7;
        cVar2 = *pcVar7;
      }
      (**(code **)(DAT_00029498 + 0x48))(local_res20);
    }
  }
  return lVar4;
}


// ==== FUN_000168d8 @ 000168d8

void FUN_000168d8(longlong param_1)

{
  bool bVar1;
  longlong lVar2;
  char *pcVar3;
  short *psVar4;
  undefined2 uVar5;
  undefined *puVar6;
  undefined1 *puVar7;
  longlong lVar8;
  longlong lVar9;
  ushort local_res18 [4];
  undefined4 local_res20 [2];
  undefined4 local_958;
  undefined4 local_954;
  undefined4 local_950;
  undefined4 local_94c;
  uint local_948;
  uint local_944;
  uint local_93c;
  uint local_938;
  undefined1 local_930 [8];
  undefined8 local_928;
  undefined8 local_920;
  undefined1 local_918 [6];
  undefined1 local_912 [250];
  undefined1 local_818 [1671];
  char local_191;
  char local_190;
  char local_18f;
  char local_18b;
  char local_187;
  
  local_920 = 0x14;
  local_928 = 0x7d8;
  lVar9 = 0;
  local_958 = 0xec87d643;
  local_res20[0] = 0;
  local_954 = 0x4bb5eba4;
  local_950 = 0x3e3fe5a1;
  bVar1 = false;
  local_94c = 0xa90db236;
  lVar2 = (**(code **)(DAT_000294a0 + 0x48))
                    (u_Setup_000262c8,&local_958,local_930,&local_928,local_818);
  if (-1 < lVar2) {
    if ((DAT_00029410 == 0) &&
       (lVar2 = (**(code **)(DAT_00029498 + 0x140))(&DAT_000237c0,0,&DAT_00029410), lVar2 < 0)) {
      return;
    }
    pcVar3 = (char *)FUN_00016674(param_1);
    if (pcVar3 != (char *)0x0) {
      if ((local_187 == '\0') && (local_18b == '\0')) {
        uVar5 = 0x1a0a;
        if (local_191 != '\0') {
          uVar5 = 0x1a0b;
        }
        FUN_00016734(param_1,uVar5,0x1a17,pcVar3);
        uVar5 = 0x1a1d;
        if (local_190 != '\x01') {
          uVar5 = 0x1a1c;
        }
        FUN_00016734(param_1,uVar5,0x1a18,pcVar3);
        uVar5 = 0x1a22;
        if (local_18f != '\x01') {
          uVar5 = 0x1a23;
        }
        FUN_00016734(param_1,uVar5,0x1a19,pcVar3);
      }
      lVar2 = (**(code **)(DAT_000294a0 + 0x48))
                        (u_PCRBitmap_000278f0,&DAT_00023880,local_res20,&local_920,&local_948);
      if (-1 < lVar2) {
        (**(code **)(DAT_00029498 + 0x168))(local_918,0x80,0);
        puVar7 = local_918;
        if ((local_948 & 1) != 0) {
          psVar4 = (short *)&DAT_00027908;
          lVar2 = lVar9;
          do {
            psVar4 = psVar4 + 1;
            lVar2 = lVar2 + 1;
          } while (*psVar4 != 0);
          (**(code **)(DAT_00029498 + 0x160))(local_918,&DAT_00027908,lVar2 * 2);
          puVar7 = local_918 + lVar2 * 2;
          bVar1 = true;
        }
        if ((local_948 & 2) != 0) {
          lVar2 = lVar9;
          if (bVar1) {
            psVar4 = (short *)&DAT_00027918;
            do {
              psVar4 = psVar4 + 1;
              lVar2 = lVar2 + 1;
            } while (*psVar4 != 0);
            puVar6 = &DAT_00027918;
          }
          else {
            psVar4 = (short *)&DAT_00027928;
            do {
              psVar4 = psVar4 + 1;
              lVar2 = lVar2 + 1;
            } while (*psVar4 != 0);
            puVar6 = &DAT_00027928;
          }
          (**(code **)(DAT_00029498 + 0x160))(puVar7,puVar6,lVar2 * 2);
          puVar7 = puVar7 + lVar2 * 2;
          bVar1 = true;
        }
        lVar2 = 4;
        if ((local_948 & 4) != 0) {
          lVar8 = lVar9;
          if (bVar1) {
            psVar4 = (short *)&DAT_00027938;
            do {
              psVar4 = psVar4 + 1;
              lVar8 = lVar8 + 1;
            } while (*psVar4 != 0);
            puVar6 = &DAT_00027938;
          }
          else {
            psVar4 = (short *)&DAT_00027948;
            do {
              psVar4 = psVar4 + 1;
              lVar8 = lVar8 + 1;
            } while (*psVar4 != 0);
            puVar6 = &DAT_00027948;
          }
          (**(code **)(DAT_00029498 + 0x160))(puVar7,puVar6,lVar8 * 2);
          puVar7 = puVar7 + lVar8 * 2;
          bVar1 = true;
        }
        if ((local_948 & 8) != 0) {
          lVar8 = lVar9;
          if (bVar1) {
            psVar4 = (short *)&DAT_00027958;
            do {
              psVar4 = psVar4 + 1;
              lVar8 = lVar8 + 1;
            } while (*psVar4 != 0);
            puVar6 = &DAT_00027958;
          }
          else {
            psVar4 = (short *)&DAT_00027968;
            do {
              psVar4 = psVar4 + 1;
              lVar8 = lVar8 + 1;
            } while (*psVar4 != 0);
            puVar6 = &DAT_00027968;
          }
          (**(code **)(DAT_00029498 + 0x160))(puVar7,puVar6,lVar8 * 2);
          puVar7 = puVar7 + lVar8 * 2;
          bVar1 = true;
        }
        if ((local_948 & 0x10) != 0) {
          lVar8 = lVar9;
          if (bVar1) {
            psVar4 = (short *)&DAT_00027978;
            do {
              psVar4 = psVar4 + 1;
              lVar8 = lVar8 + 1;
            } while (*psVar4 != 0);
            puVar6 = &DAT_00027978;
          }
          else {
            psVar4 = (short *)&DAT_00027988;
            do {
              psVar4 = psVar4 + 1;
              lVar8 = lVar8 + 1;
            } while (*psVar4 != 0);
            puVar6 = &DAT_00027988;
          }
          (**(code **)(DAT_00029498 + 0x160))(puVar7,puVar6,lVar8 * 2);
        }
        FUN_00000680(param_1,0x1a47,&DAT_00025b68,(ulonglong)local_918);
        (**(code **)(DAT_00029498 + 0x168))(local_918,0x80,0);
        puVar7 = local_918;
        bVar1 = false;
        if ((local_944 & 1) != 0) {
          psVar4 = (short *)&DAT_00027908;
          lVar8 = lVar9;
          do {
            psVar4 = psVar4 + 1;
            lVar8 = lVar8 + 1;
          } while (*psVar4 != 0);
          (**(code **)(DAT_00029498 + 0x160))(local_918,&DAT_00027908,lVar8 * 2);
          puVar7 = local_918 + lVar8 * 2;
          bVar1 = true;
        }
        if ((local_944 & 2) != 0) {
          lVar8 = lVar9;
          if (bVar1) {
            psVar4 = (short *)&DAT_00027918;
            do {
              psVar4 = psVar4 + 1;
              lVar8 = lVar8 + 1;
            } while (*psVar4 != 0);
            puVar6 = &DAT_00027918;
          }
          else {
            psVar4 = (short *)&DAT_00027928;
            do {
              psVar4 = psVar4 + 1;
              lVar8 = lVar8 + 1;
            } while (*psVar4 != 0);
            puVar6 = &DAT_00027928;
          }
          (**(code **)(DAT_00029498 + 0x160))(puVar7,puVar6,lVar8 * 2);
          puVar7 = puVar7 + lVar8 * 2;
          bVar1 = true;
        }
        if ((local_944 & 4) != 0) {
          lVar8 = lVar9;
          if (bVar1) {
            psVar4 = (short *)&DAT_00027938;
            do {
              psVar4 = psVar4 + 1;
              lVar8 = lVar8 + 1;
            } while (*psVar4 != 0);
            puVar6 = &DAT_00027938;
          }
          else {
            psVar4 = (short *)&DAT_00027948;
            do {
              psVar4 = psVar4 + 1;
              lVar8 = lVar8 + 1;
            } while (*psVar4 != 0);
            puVar6 = &DAT_00027948;
          }
          (**(code **)(DAT_00029498 + 0x160))(puVar7,puVar6,lVar8 * 2);
          puVar7 = puVar7 + lVar8 * 2;
          bVar1 = true;
        }
        if ((local_944 & 8) != 0) {
          lVar8 = lVar9;
          if (bVar1) {
            psVar4 = (short *)&DAT_00027958;
            do {
              psVar4 = psVar4 + 1;
              lVar8 = lVar8 + 1;
            } while (*psVar4 != 0);
            puVar6 = &DAT_00027958;
          }
          else {
            psVar4 = (short *)&DAT_00027968;
            do {
              psVar4 = psVar4 + 1;
              lVar8 = lVar8 + 1;
            } while (*psVar4 != 0);
            puVar6 = &DAT_00027968;
          }
          (**(code **)(DAT_00029498 + 0x160))(puVar7,puVar6,lVar8 * 2);
          puVar7 = puVar7 + lVar8 * 2;
          bVar1 = true;
        }
        if ((local_944 & 0x10) != 0) {
          if (bVar1) {
            psVar4 = (short *)&DAT_00027978;
            do {
              psVar4 = psVar4 + 1;
              lVar9 = lVar9 + 1;
            } while (*psVar4 != 0);
            puVar6 = &DAT_00027978;
          }
          else {
            psVar4 = (short *)&DAT_00027988;
            do {
              psVar4 = psVar4 + 1;
              lVar9 = lVar9 + 1;
            } while (*psVar4 != 0);
            puVar6 = &DAT_00027988;
          }
          (**(code **)(DAT_00029498 + 0x160))(puVar7,puVar6,lVar9 * 2);
        }
        FUN_00000680(param_1,0x1a44,&DAT_00025b68,(ulonglong)local_918);
        (**(code **)(DAT_00029498 + 0x168))(local_918,0x80,0);
        FUN_00000680(param_1,0x1a57,(byte *)u__d__d_00026c68,(ulonglong)(local_93c >> 0x10));
        (**(code **)(DAT_00029498 + 0x168))(local_918,0x80,0);
        puVar7 = local_912;
        do {
          local_res18[0] = (ushort)local_938 & 0xff;
          (**(code **)(DAT_00029498 + 0x160))(puVar7,local_res18,2);
          puVar7 = puVar7 + -2;
          local_938 = local_938 >> 8;
          lVar2 = lVar2 + -1;
        } while (lVar2 != 0);
        FUN_00000680(param_1,0x1a56,&DAT_00025b68,(ulonglong)local_918);
        (**(code **)(DAT_00029498 + 0x48))(pcVar3);
      }
    }
  }
  return;
}


// ==== FUN_000170c0 @ 000170c0

undefined8 FUN_000170c0(longlong param_1)

{
  short sVar1;
  bool bVar2;
  undefined8 uVar3;
  short *psVar4;
  undefined1 local_13b8 [1719];
  undefined2 local_d01;
  undefined1 local_cff;
  char local_cd8;
  undefined1 local_cc8 [704];
  undefined1 local_a08 [544];
  undefined1 local_7e8 [2016];
  
  sVar1 = *(short *)(param_1 + 0x10);
  if (*(ulonglong *)(param_1 + 8) < 2) {
    bVar2 = FUN_000213f0(&DAT_000238c0,u_PchSetup_00026308,0x6ec,local_13b8);
    if (bVar2) {
      bVar2 = FUN_000213f0(&DAT_000235b0,u_CpuSetup_00026ae0,699,local_cc8);
      if (bVar2) {
        bVar2 = FUN_000213f0(&DAT_000238f0,u_SaSetup_00026070,0x21d,local_a08);
        if (bVar2) {
          bVar2 = FUN_000213f0(&DAT_00023710,u_Setup_000262c8,0x7d8,local_7e8);
          if (bVar2) {
            if (sVar1 == 0x27c0) {
              local_cff = 3;
              local_d01 = 0x302;
              if (local_cd8 == '\0') {
                local_d01 = 0x300;
              }
            }
            psVar4 = FUN_0001b458((short *)0x0,0xdd);
            psVar4 = FUN_0001b458(psVar4,0xde);
            if (psVar4 != (short *)0x0) {
              FUN_000214e4(&DAT_000235b0,u_CpuSetup_00026ae0,699,local_cc8,psVar4);
              (**(code **)(DAT_00029478 + 0x48))();
            }
            psVar4 = FUN_0001b458((short *)0x0,0x6b7);
            psVar4 = FUN_0001b458(psVar4,0x6b8);
            psVar4 = FUN_0001b458(psVar4,0x6b9);
            if (psVar4 != (short *)0x0) {
              FUN_000214e4(&DAT_000238c0,u_PchSetup_00026308,0x6ec,local_13b8,psVar4);
              (**(code **)(DAT_00029478 + 0x48))(psVar4);
            }
          }
        }
      }
    }
    uVar3 = 0;
  }
  else {
    uVar3 = 0x8000000000000003;
  }
  return uVar3;
}


// ==== FUN_0001729c @ 0001729c

wchar_t * FUN_0001729c(undefined1 param_1,char param_2)

{
  longlong lVar1;
  char cVar2;
  char *pcVar3;
  undefined1 local_res18 [8];
  wchar_t *local_res20;
  longlong local_18;
  longlong local_10;
  
  local_res20 = (wchar_t *)0x0;
  lVar1 = (**(code **)(DAT_00029498 + 0x140))(&DAT_00024920,0,&local_10);
  if ((-1 < lVar1) &&
     (lVar1 = (**(code **)(local_10 + 0x40))(param_1,1,&local_18,local_res18), -1 < lVar1)) {
    pcVar3 = (char *)((ulonglong)*(byte *)(local_18 + 1) + local_18);
    while (param_2 != '\0') {
      cVar2 = param_2 + -1;
      if (*pcVar3 != '\0') {
        cVar2 = param_2;
      }
      pcVar3 = pcVar3 + 1;
      param_2 = cVar2;
    }
    lVar1 = 0;
    cVar2 = *pcVar3;
    while (cVar2 != '\0') {
      lVar1 = lVar1 + 1;
      cVar2 = pcVar3[lVar1];
    }
    lVar1 = (**(code **)(DAT_00029498 + 0x40))(4,lVar1 * 2 + 2,&local_res20);
    if (-1 < lVar1) {
      lVar1 = 0;
      cVar2 = *pcVar3;
      while (cVar2 != '\0') {
        lVar1 = lVar1 + 1;
        cVar2 = pcVar3[lVar1];
      }
      FUN_0001e3b4(local_res20,lVar1 * 2 + 2,(wchar_t *)&DAT_00027990,pcVar3);
      (**(code **)(DAT_00029498 + 0x48))(local_18);
      return local_res20;
    }
  }
  return (wchar_t *)0x0;
}


// ==== FUN_00017398 @ 00017398

undefined8 FUN_00017398(undefined8 param_1,undefined2 param_2)

{
  byte bVar1;
  longlong lVar2;
  char *pcVar3;
  byte bVar4;
  char cVar5;
  ulonglong uVar6;
  undefined2 local_res10 [4];
  longlong local_res18;
  longlong local_res20;
  char local_58 [80];
  
  local_res10[0] = param_2;
  FUN_00023370((undefined4 *)local_58,0,0x50);
  lVar2 = (**(code **)(DAT_00029498 + 0x140))(&DAT_00024920,0,&local_res20);
  uVar6 = 0;
  if ((-1 < lVar2) &&
     (lVar2 = (**(code **)(local_res20 + 0x40))(1,1,&local_res18,local_res10), -1 < lVar2)) {
    pcVar3 = local_58;
    do {
      bVar1 = *(byte *)(local_res18 + 8 + uVar6);
      bVar4 = bVar1 >> 4;
      if (bVar4 < 10) {
        cVar5 = bVar4 + 0x30;
      }
      else {
        cVar5 = bVar4 + 0x37;
      }
      bVar1 = bVar1 & 0xf;
      *pcVar3 = cVar5;
      if (bVar1 < 10) {
        cVar5 = bVar1 + 0x30;
      }
      else {
        cVar5 = bVar1 + 0x37;
      }
      pcVar3[1] = cVar5;
      uVar6 = uVar6 + 1;
      pcVar3 = pcVar3 + 2;
    } while (uVar6 < 0x10);
    FUN_00000680(param_1,0x1ac0,&DAT_0002672c,(ulonglong)local_58);
    (**(code **)(DAT_00029498 + 0x48))(local_res18);
    return 0;
  }
  return 0x8000000000000003;
}


// ==== FUN_00017494 @ 00017494

/* WARNING: Type propagation algorithm not settling */

undefined8 FUN_00017494(undefined8 param_1)

{
  short sVar1;
  char cVar2;
  char cVar3;
  byte bVar4;
  longlong lVar5;
  ushort uVar6;
  ulonglong uVar7;
  longlong local_res18;
  ulonglong local_res20;
  ulonglong local_68 [4];
  undefined8 local_48;
  short local_40 [5];
  char local_36;
  char local_35;
  
  lVar5 = (**(code **)(DAT_00029498 + 0x138))(2,&DAT_000236a0,0,&local_res20,local_68 + 3);
  if ((-1 < lVar5) && (uVar7 = 0, local_res20 != 0)) {
    do {
      local_48 = 0;
      local_68[0] = 0;
      local_68[1] = 0;
      local_68[2] = 0;
      (**(code **)(DAT_00029498 + 0x98))
                (*(undefined8 *)(local_68[3] + uVar7 * 8),&DAT_000236a0,&local_res18);
      (**(code **)(local_res18 + 0x30))(local_res18,2,0,4,local_40);
      cVar3 = local_35;
      cVar2 = local_36;
      sVar1 = local_40[0];
      (**(code **)(local_res18 + 0x70))(local_res18,&local_48,local_68,local_68 + 1,local_68 + 2);
      if ((cVar3 == '\x02') && (cVar2 == '\0')) {
        if (sVar1 != 0x10ec) {
          return 0;
        }
        uVar6 = *(ushort *)
                 (((((local_68[0] & 0xff) << 5 | (ulonglong)((uint)local_68[1] & 0x1f)) << 3 |
                   (ulonglong)((uint)local_68[2] & 7)) << 0xc | 0x10) + 0xe0000000) & 0xfffe;
        in(uVar6 + 5);
        in(uVar6 + 4);
        in(uVar6 + 3);
        in(uVar6 + 2);
        in(uVar6 + 1);
        bVar4 = in(uVar6);
        FUN_00000680(param_1,0x1acd,(byte *)u__02X__02X__02X__02X__02X__02X_000279b0,
                     (ulonglong)bVar4);
        return 0;
      }
      uVar7 = uVar7 + 1;
    } while (uVar7 < local_res20);
  }
  return 0;
}


// ==== FUN_00018160 @ 00018160

void FUN_00018160(uint param_1,uint param_2,char param_3,uint *param_4,undefined1 *param_5,
                 undefined1 *param_6)

{
  byte bVar1;
  int iVar2;
  uint *puVar3;
  uint uVar4;
  uint uVar5;
  ulonglong uVar6;
  
  *param_4 = 0;
  uVar4 = 0;
  uVar6 = 0;
  *param_5 = 0;
  puVar3 = &DAT_00027a30;
  *param_6 = 0;
  do {
    if ((param_1 <= *puVar3) && ((uint)(&DAT_00027a30)[(ulonglong)((int)uVar6 + 1) * 3] < param_1))
    {
      uVar4 = *(uint *)(uVar6 * 0xc + 0x27a34);
      break;
    }
    uVar5 = (int)uVar6 + 1;
    uVar6 = (ulonglong)uVar5;
    puVar3 = puVar3 + 3;
  } while (uVar5 < (-(uint)(param_3 != '\0') & 0x32) + 0x31);
  bVar1 = (&DAT_00027a38)[uVar6 * 0xc];
  if (bVar1 != 0) {
    uVar5 = 0;
    do {
      if ((bVar1 >> (uVar5 & 0x1f) & 1) != 0) {
        *param_6 = 0;
LAB_00018213:
        *param_4 = uVar5;
        break;
      }
      if (((uint)bVar1 & 4 << ((byte)uVar5 & 0x1f)) != 0) {
        *param_6 = 1;
        goto LAB_00018213;
      }
      uVar5 = uVar5 + 1;
    } while (uVar5 < 2);
    uVar5 = 100000000;
    if (99999999 < param_2) {
      uVar5 = param_2;
    }
    iVar2 = 0x411ab;
    if (*param_4 == 1) {
      iVar2 = 200000;
    }
    uVar6 = (ulonglong)
            ((int)(((ulonglong)uVar4 * 1000000000) / (ulonglong)((uVar5 / 100000) * iVar2)) + 500) /
            1000;
    if ((2 < uVar6) && (uVar6 <= (ulonglong)(-(uint)(param_3 != '\0') & 0x10) + 0xf)) {
      *param_5 = (char)uVar6;
    }
  }
  return;
}


// ==== FUN_0001829c @ 0001829c

undefined8 FUN_0001829c(longlong param_1)

{
  short sVar1;
  undefined8 uVar2;
  byte bVar3;
  longlong lVar4;
  short *psVar5;
  ulonglong uVar6;
  
  if (1 < *(ulonglong *)(param_1 + 8)) {
    return 0x8000000000000003;
  }
  lVar4 = FUN_0001b514(param_1,699);
  if (lVar4 == 0) {
    return 0x8000000000000009;
  }
  FUN_000213f0(&DAT_000235b0,u_CpuSetup_00026ae0,699,lVar4);
  uVar2 = rdmsr(0xce);
  sVar1 = *(short *)(param_1 + 0x10);
  bVar3 = (byte)((ulonglong)uVar2 >> 0x28);
  if (sVar1 == 0x2796) {
    if ((*(byte *)(lVar4 + 0x1b9) < bVar3) && (*(byte *)(lVar4 + 0x1b9) != 0)) {
      *(byte *)(lVar4 + 0x1b9) = bVar3;
    }
    *(undefined1 *)(lVar4 + 0xd1) = *(undefined1 *)(lVar4 + 0x1b9);
    psVar5 = FUN_0001b458((short *)0x0,0x1b9);
    uVar6 = 0xd1;
  }
  else {
    if (sVar1 == 0x2797) {
      bVar3 = (byte)((ulonglong)uVar2 >> 8);
      if ((*(byte *)(lVar4 + 0x1c4) < bVar3) && (*(byte *)(lVar4 + 0x1c4) != 0)) {
        *(byte *)(lVar4 + 0x1c4) = bVar3;
      }
      uVar6 = 0x1c4;
    }
    else if (sVar1 == 0x2798) {
      if ((*(byte *)(lVar4 + 0x20a) < bVar3) && (*(byte *)(lVar4 + 0x20a) != 0)) {
        *(byte *)(lVar4 + 0x20a) = bVar3;
      }
      uVar6 = 0x20a;
    }
    else {
      if (sVar1 != 0x2799) goto LAB_00018407;
      if ((*(byte *)(lVar4 + 0x20c) < bVar3) && (*(byte *)(lVar4 + 0x20c) != 0)) {
        *(byte *)(lVar4 + 0x20c) = bVar3;
      }
      uVar6 = 0x20c;
    }
    psVar5 = (short *)0x0;
  }
  psVar5 = FUN_0001b458(psVar5,uVar6);
  if (psVar5 != (short *)0x0) {
    FUN_000214e4(&DAT_000235b0,u_CpuSetup_00026ae0,699,lVar4,psVar5);
    (**(code **)(DAT_00029478 + 0x48))(psVar5);
  }
LAB_00018407:
  (**(code **)(DAT_00029478 + 0x48))(lVar4);
  return 0;
}


// ==== FUN_000187f4 @ 000187f4

undefined8 FUN_000187f4(void)

{
  longlong lVar1;
  ushort uVar2;
  undefined1 local_238 [8];
  undefined8 local_230;
  undefined1 local_228 [36];
  byte local_204;
  byte local_203;
  undefined2 local_202;
  undefined2 local_200;
  byte local_1fe;
  undefined2 local_1fd;
  undefined2 local_1fb;
  byte local_1f9;
  byte local_1f6;
  byte local_1f4;
  byte local_1f1;
  
  lVar1 = DAT_00029270;
  if ((DAT_00029270 == 0) || (*(ulonglong *)(DAT_00029270 + 8) < 2)) {
    return 0x8000000000000003;
  }
  if (*(longlong *)(DAT_00029270 + 8) != 0x1000) {
    return 0;
  }
  local_230 = 0x21d;
  (**(code **)(DAT_00029488 + 0x48))
            (u_SaSetup_00026070,&DAT_000238f0,local_238,&local_230,local_228);
  uVar2 = *(ushort *)(lVar1 + 0x10);
  if (uVar2 < 0x27a1) {
    local_1fb = local_1fd;
    if (uVar2 != 0x27a0) {
      if (uVar2 == 0x279b) {
        uVar2 = (ushort)local_204;
      }
      else {
        if (uVar2 != 0x279c) {
          local_1fb = local_200;
          if (uVar2 != 0x279d) {
            if (uVar2 == 0x279e) {
              uVar2 = (ushort)local_203;
              goto LAB_000188b3;
            }
            local_1fb = local_202;
            if (uVar2 != 0x279f) {
              return 0;
            }
          }
          goto LAB_00018900;
        }
        uVar2 = (ushort)local_1fe;
      }
LAB_000188b3:
      **(ushort **)(lVar1 + 0x18) = uVar2;
      return 0;
    }
  }
  else if (uVar2 != 0x27a1) {
    if (uVar2 == 0x27a2) {
      uVar2 = (ushort)local_1f9;
    }
    else if (uVar2 == 0x27a5) {
      uVar2 = (ushort)local_1f6;
    }
    else if (uVar2 == 0x27a6) {
      uVar2 = (ushort)local_1f4;
    }
    else {
      if (uVar2 != 0x27a9) {
        return 0;
      }
      uVar2 = (ushort)local_1f1;
    }
    goto LAB_000188b3;
  }
LAB_00018900:
  **(undefined2 **)(lVar1 + 0x18) = local_1fb;
  return 0;
}


// ==== FUN_00018928 @ 00018928

undefined8 FUN_00018928(longlong param_1)

{
  longlong lVar1;
  int *piVar2;
  longlong *plVar3;
  undefined8 uVar4;
  
  uVar4 = 0;
  if ((DAT_00029448 != 0) &&
     (plVar3 = (longlong *)(param_1 * 0x40 + DAT_00029448), plVar3 != (longlong *)0x0)) {
    lVar1 = *plVar3;
    piVar2 = *(int **)(lVar1 + 0x38);
    if (*(int *)(lVar1 + 0x40) == 1) {
      uVar4 = *(undefined8 *)(piVar2 + 0xe4);
    }
    if (*(int *)(lVar1 + 0x40) == 2) {
      if (*piVar2 == 0x54535224) {
        uVar4 = *(undefined8 *)(piVar2 + 0x18);
      }
      else {
        uVar4 = *(undefined8 *)(piVar2 + 0x52);
      }
    }
    return uVar4;
  }
  return 0;
}


// ==== FUN_00018978 @ 00018978

undefined2 FUN_00018978(void)

{
  longlong lVar1;
  undefined2 uVar2;
  longlong local_res8 [4];
  
  local_res8[0] = 0;
  lVar1 = (**(code **)(DAT_00029498 + 0x140))(&DAT_000249b8,0,local_res8);
  if (lVar1 < 0) {
    uVar2 = 0;
  }
  else {
    uVar2 = **(undefined2 **)(local_res8[0] + 0x48);
    DAT_00029448 = **(undefined8 **)(local_res8[0] + 0x50);
    DAT_00029438 = uVar2;
  }
  return uVar2;
}


// ==== FUN_000189d4 @ 000189d4

undefined8 FUN_000189d4(longlong param_1,longlong param_2)

{
  longlong lVar1;
  byte bVar2;
  undefined1 *puVar3;
  byte bVar4;
  undefined1 *puVar5;
  
  lVar1 = (**(code **)(DAT_00029498 + 0x40))(4);
  (**(code **)(DAT_00029498 + 0x168))(0,0x42);
  if (-1 < lVar1) {
    puVar3 = (undefined1 *)0x0;
    puVar5 = (undefined1 *)((longlong)IMAGE_DOS_HEADER_00000000.e_res_4_ + 5);
    do {
      *puVar3 = puVar3[param_1];
      if (puVar3[param_1] == '\0') break;
      bVar2 = (char)puVar3 + 1;
      puVar3 = (undefined1 *)(ulonglong)bVar2;
    } while (bVar2 < 0x21);
    bVar2 = 0;
    do {
      *puVar5 = *(undefined1 *)((ulonglong)bVar2 + param_2);
      if (*(char *)((ulonglong)bVar2 + param_2) == '\0') {
        return 0;
      }
      bVar4 = (char)puVar5 + 1;
      puVar5 = (undefined1 *)(ulonglong)bVar4;
      bVar2 = bVar2 + 1;
    } while (bVar4 < 0x42);
  }
  return 0;
}


// ==== FUN_00018a8c @ 00018a8c

longlong FUN_00018a8c(void)

{
  longlong lVar1;
  undefined8 *in_R9;
  longlong *in_stack_00000028;
  
  lVar1 = *in_stack_00000028;
  if (lVar1 == 0) {
    *in_R9 = 0;
  }
  lVar1 = (**(code **)(DAT_000294a0 + 0x48))(u_PlatformLang_00025c88,&DAT_000234a0,0,in_R9,lVar1);
  if ((lVar1 < 0) && (lVar1 == -0x7ffffffffffffffb)) {
    if (*in_stack_00000028 != 0) {
      (**(code **)(DAT_00029498 + 0x48))();
    }
    lVar1 = FUN_0001d748(*in_R9);
    *in_stack_00000028 = lVar1;
    if (lVar1 == 0) {
      lVar1 = -0x7ffffffffffffff7;
    }
    else {
      lVar1 = (**(code **)(DAT_000294a0 + 0x48))(u_PlatformLang_00025c88,&DAT_000234a0,0);
    }
  }
  return lVar1;
}


// ==== FUN_00018b3c @ 00018b3c

undefined8 FUN_00018b3c(undefined8 param_1,undefined2 param_2)

{
  longlong lVar1;
  undefined8 local_res20;
  undefined8 local_28;
  undefined8 local_20;
  
  local_res20 = 0;
  local_28 = 0;
  local_20 = 0;
  if ((DAT_00029450 == 0) &&
     (lVar1 = (**(code **)(DAT_00029498 + 0x140))(&DAT_000237c0,0,&DAT_00029450), lVar1 < 0)) {
    return 0;
  }
  lVar1 = FUN_00018a8c();
  if (-1 < lVar1) {
    lVar1 = (**(code **)(DAT_00029450 + 8))(DAT_00029450,0,param_1,param_2,local_res20,&local_28,0);
    if ((lVar1 == -0x7ffffffffffffffb) &&
       (lVar1 = (**(code **)(DAT_00029498 + 0x40))(4,local_28,&local_res20), -1 < lVar1)) {
      lVar1 = (**(code **)(DAT_00029450 + 8))
                        (DAT_00029450,0,param_1,param_2,local_res20,&local_28,0);
    }
    (**(code **)(DAT_00029498 + 0x48))(0);
  }
  if (lVar1 < 0) {
    local_res20 = 0;
  }
  return local_res20;
}


// ==== FUN_00018c7c @ 00018c7c

short FUN_00018c7c(undefined8 param_1,undefined8 param_2,short param_3)

{
  char *pcVar1;
  longlong lVar2;
  short local_res18 [4];
  char *local_res20;
  undefined8 local_28 [2];
  
  local_res20 = (char *)0x0;
  local_28[0] = 0;
  local_res18[0] = param_3;
  if ((DAT_00029450 != (undefined8 *)0x0) ||
     (lVar2 = (**(code **)(DAT_00029498 + 0x140))(&DAT_000237c0,0,&DAT_00029450), -1 < lVar2)) {
    if (DAT_00029418 == (char *)0x0) {
      lVar2 = (*(code *)DAT_00029450[3])(DAT_00029450,param_1,local_res20,local_28);
      if (lVar2 == -0x7ffffffffffffffb) {
        lVar2 = (**(code **)(DAT_00029498 + 0x40))(4,local_28[0],&local_res20);
        if (lVar2 < 0) {
          return 0;
        }
        lVar2 = (*(code *)DAT_00029450[3])(DAT_00029450,param_1,local_res20,local_28);
        if (lVar2 < 0) {
          return 0;
        }
      }
      if (local_res20 == (char *)0x0) {
        return 0;
      }
      DAT_00029418 = local_res20;
      pcVar1 = local_res20;
    }
    else {
      local_res20 = DAT_00029418;
      pcVar1 = DAT_00029418;
    }
    do {
      for (; *local_res20 != ';'; local_res20 = local_res20 + 1) {
        if (*local_res20 == '\0') {
          if (local_res18[0] == 0) {
            lVar2 = (*(code *)*DAT_00029450)(DAT_00029450,param_1,local_res18,pcVar1,0,param_2,0);
          }
          else {
            lVar2 = (*(code *)DAT_00029450[2])(DAT_00029450,param_1,local_res18[0],pcVar1,param_2,0)
            ;
          }
          if (lVar2 < 0) {
            return 0;
          }
          return local_res18[0];
        }
      }
      *local_res20 = '\0';
      if (local_res18[0] == 0) {
        lVar2 = (*(code *)*DAT_00029450)(DAT_00029450,param_1,local_res18,pcVar1,0,param_2,0);
      }
      else {
        lVar2 = (*(code *)DAT_00029450[2])(DAT_00029450,param_1,local_res18[0],pcVar1,param_2,0);
      }
      *local_res20 = ';';
      local_res20 = local_res20 + 1;
      pcVar1 = local_res20;
    } while (-1 < lVar2);
  }
  return 0;
}


// ==== FUN_00018e34 @ 00018e34

void FUN_00018e34(longlong *param_1,undefined2 param_2,undefined8 param_3,undefined2 param_4,
                 undefined2 param_5,undefined2 param_6)

{
  undefined8 local_28;
  undefined2 local_20;
  undefined2 local_1e;
  undefined1 local_1c;
  undefined4 local_1b;
  
  (**(code **)(DAT_00029498 + 0x168))(&local_28,0x11);
  local_28._2_2_ = param_5;
  local_28._4_2_ = param_6;
  local_20 = 0xdddf;
  local_1c = 0x14;
  local_1b = 0x200000;
  local_28._6_2_ = param_2;
  local_1e = param_4;
  FUN_00021748(param_1,&local_28,8,0x11,'\0','\0');
  return;
}


// ==== FUN_00018ed0 @ 00018ed0

undefined8 FUN_00018ed0(longlong *param_1)

{
  undefined8 *puVar1;
  undefined8 uVar2;
  
  puVar1 = (undefined8 *)FUN_0001b544(4);
  uVar2 = 0;
  if (puVar1 != (undefined8 *)0x0) {
    *(undefined4 *)puVar1 = 0x246820a;
    uVar2 = FUN_000217a4(param_1,puVar1,4);
    (**(code **)(DAT_00029478 + 0x48))(puVar1);
  }
  return uVar2;
}


// ==== FUN_00018f24 @ 00018f24

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_00018f24(undefined8 param_1)

{
  longlong *plVar1;
  longlong *plVar2;
  longlong *plVar3;
  longlong lVar4;
  longlong lVar5;
  longlong lVar6;
  longlong *plVar7;
  undefined1 *puVar8;
  undefined8 uVar9;
  
  plVar1 = FUN_00021668(param_1);
  plVar2 = FUN_00021668(param_1);
  plVar3 = FUN_00021668(param_1);
  lVar4 = FUN_00018928(0);
  if (((plVar1 != (longlong *)0x0) && (plVar2 != (longlong *)0x0)) && (plVar3 != (longlong *)0x0)) {
    lVar5 = FUN_00021888(plVar1);
    if (lVar5 != 0) {
      *(undefined1 *)(lVar5 + 0x12) = 0;
      lVar6 = FUN_00021888(plVar2);
      if (lVar6 != 0) {
        *(undefined1 *)(lVar6 + 0x12) = 0;
        *(undefined2 *)(lVar5 + 0x13) = 0x29df;
        *(undefined2 *)(lVar6 + 0x13) = 0x29e0;
        FUN_00021808(plVar3,0x1a69,0x30);
        FUN_00021808(plVar3,0x1a6a,0);
        FUN_000218e4(plVar1,0x1a5e);
        FUN_000218e4(plVar1,2);
        FUN_000218e4(plVar1,0x1a60);
        FUN_000218e4(plVar1,0x1a61);
        FUN_000218e4(plVar1,0x1a62);
        FUN_000218e4(plVar1,0x1a63);
        FUN_000218e4(plVar1,2);
        FUN_000218e4(plVar1,0x1a5f);
        FUN_000218e4(plVar1,2);
        uVar9 = 0;
        _DAT_0002b036 = FUN_00018c7c(DAT_00029440,u_Unknown_00027f00,0);
        FUN_000219f4(plVar1,0x1a64,uVar9,_DAT_0002b036);
        uVar9 = 0;
        DAT_0002b034 = FUN_00018c7c(DAT_00029440,&DAT_00027f10,0);
        FUN_000219f4(plVar1,0x1a65,uVar9,DAT_0002b034);
        uVar9 = 0;
        DAT_0002b030 = FUN_00018c7c(DAT_00029440,&DAT_00027f10,0);
        FUN_000219f4(plVar1,0x1a66,uVar9,DAT_0002b030);
        uVar9 = 0;
        DAT_0002b020 = FUN_00018c7c(DAT_00029440,&DAT_00027f10,0);
        FUN_000219f4(plVar1,0x1a67,uVar9,DAT_0002b020);
        FUN_00018ed0(plVar1);
        FUN_00021940(plVar1,0x291f,uVar9,4,0x1a68);
        FUN_00023168(plVar1);
        FUN_00018ed0(plVar1);
        FUN_00021940(plVar1,0x293f,uVar9,2,0x1a66);
        FUN_00023168(plVar1);
        uVar9 = 0;
        DAT_0002b032 = FUN_00018c7c(DAT_00029440,&DAT_00027f10,0);
        FUN_000219f4(plVar1,0x1a68,uVar9,DAT_0002b032);
        if ((lVar4 == 0) || (*(short *)(lVar4 + 0x3e) != 0x100)) {
          uVar9 = 0;
          DAT_0002b038 = FUN_00018c7c(DAT_00029440,u_NOT_INSTALLED_00027f18,0);
          FUN_000219f4(plVar1,0x1a6b,uVar9,DAT_0002b038);
        }
        uVar9 = 0;
        DAT_0002b03a = FUN_00018c7c(DAT_00029440,u_NOT_INSTALLED_00027f18,0);
        FUN_000219f4(plVar1,0x1a6c,uVar9,DAT_0002b03a);
        FUN_00018ed0(plVar1);
        FUN_00021940(plVar1,0x2900,uVar9,7,2);
        FUN_00023168(plVar1);
        FUN_000218e4(plVar1,2);
        FUN_00023108(plVar1,0x2900,0);
        uVar9 = 1;
        FUN_00023108(plVar1,0x291f,1);
        puVar8 = &LAB_0000297f;
        FUN_00018e34(plVar1,0x297f,uVar9,10,0x1a6f,0x1a70);
        FUN_00023168(plVar1);
        plVar7 = plVar1;
        FUN_00023168(plVar1);
        if ((lVar4 == 0) || (*(short *)(lVar4 + 0x3e) != 0x100)) {
          FUN_00023108(plVar1,0x2900,0);
          FUN_00023108(plVar1,0x291f,1);
          uVar9 = 0;
          FUN_00023108(plVar1,0x293f,0);
          puVar8 = (undefined1 *)0x295f;
          FUN_00018e34(plVar1,0x295f,uVar9,8,0x1a6d,0x1a6e);
          FUN_00023168(plVar1);
          FUN_00023168(plVar1);
          plVar7 = plVar1;
          FUN_00023168(plVar1);
        }
        plVar1 = (longlong *)FUN_00021d24(plVar7,(ulonglong)puVar8,0x29e7,plVar1,plVar2);
        FUN_000216bc(plVar1);
        FUN_000216bc(plVar2);
        FUN_000216bc(plVar3);
      }
    }
  }
  return;
}


// ==== FUN_00019368 @ 00019368

void FUN_00019368(undefined8 param_1)

{
  short sVar1;
  longlong *plVar2;
  longlong *plVar3;
  longlong lVar4;
  longlong lVar5;
  undefined8 uVar6;
  longlong *plVar7;
  code *pcVar8;
  ulonglong uVar9;
  ulonglong uVar10;
  undefined1 local_28 [2];
  short local_26;
  undefined2 local_24;
  short local_22;
  undefined1 local_1c;
  undefined2 local_1b;
  
  plVar2 = FUN_00021668(param_1);
  plVar3 = FUN_00021668(param_1);
  uVar9 = 0;
  if (((plVar2 != (longlong *)0x0) && (plVar3 != (longlong *)0x0)) &&
     (lVar4 = FUN_00021888(plVar2), lVar4 != 0)) {
    *(undefined1 *)(lVar4 + 0x12) = 0;
    lVar5 = FUN_00021888(plVar3);
    if (lVar5 != 0) {
      *(undefined1 *)(lVar5 + 0x12) = 0;
      *(undefined2 *)(lVar4 + 0x13) = 0x29e1;
      pcVar8 = FUN_00001a5c;
      *(undefined2 *)(lVar5 + 0x13) = 0x29e2;
      plVar7 = plVar2;
      FUN_000218e4(plVar2,0x1a5c);
      uVar10 = uVar9;
      if (DAT_00029438 != 0) {
        do {
          if (0x7ff < uVar9) break;
          lVar4 = *(longlong *)(DAT_00029448 + 8 + uVar9);
          if (DAT_00029440 == lVar4) {
            sVar1 = *(short *)(DAT_00029448 + 0x12 + uVar9);
          }
          else {
            uVar6 = FUN_00018b3c(lVar4,*(undefined2 *)(DAT_00029448 + 0x12 + uVar9));
            sVar1 = FUN_00018c7c(DAT_00029440,uVar6,0);
            (**(code **)(DAT_00029478 + 0x48))(uVar6);
          }
          FUN_00000340((undefined8 *)local_28,0xf);
          local_24 = 0x1a5d;
          pcVar8 = (code *)local_28;
          local_22 = (short)uVar10 + 0x29bf;
          local_1c = 4;
          local_1b = 0x29e7;
          plVar7 = plVar2;
          local_26 = sVar1;
          FUN_00021748(plVar2,(undefined8 *)pcVar8,0xf,0xf,'\0','\0');
          uVar10 = uVar10 + 1;
          uVar9 = uVar9 + 0x40;
        } while (uVar10 < DAT_00029438);
      }
      FUN_00021d24(plVar7,(ulonglong)pcVar8,0x271a,plVar2,plVar3);
      FUN_000216bc(plVar2);
      FUN_000216bc(plVar3);
    }
  }
  return;
}


// ==== FUN_000195e8 @ 000195e8

void FUN_000195e8(void)

{
  wchar_t *pwVar1;
  undefined4 local_68;
  undefined4 local_64;
  undefined4 local_60;
  undefined4 local_5c;
  undefined1 local_58 [80];
  
  local_68 = 0x2798f49d;
  pwVar1 = u_TcgStorageDynamicSetupVar_00027f38;
  local_64 = 0x480bf760;
  local_60 = 0x69915580;
  local_5c = 0x4077c240;
  (**(code **)(DAT_000294a0 + 0x58))(u_TcgStorageDynamicSetupVar_00027f38,&local_68,2,0x4a,local_58)
  ;
  DAT_00029438 = FUN_00018978();
  if (DAT_00029438 != 0) {
    FUN_00018f24(pwVar1);
    FUN_00019368(pwVar1);
    if (DAT_00029420 == 0) {
      (**(code **)(DAT_00029498 + 0x170))(0x200,8,&LAB_00019518,0,&DAT_000249a0,&DAT_00029420);
    }
  }
  return;
}


// ==== FUN_00019978 @ 00019978

undefined8 FUN_00019978(longlong param_1,longlong *param_2)

{
  longlong lVar1;
  undefined8 uVar2;
  ulonglong uVar3;
  undefined4 local_38 [12];
  
  FUN_0002337e(local_38,0x21,0);
  uVar3 = 0;
  do {
    *(undefined1 *)((longlong)local_38 + uVar3) = *(undefined1 *)(param_1 + uVar3 * 2);
    if (*(short *)(param_1 + uVar3 * 2) == 0) break;
    uVar3 = uVar3 + 1;
  } while (uVar3 < 0x21);
  lVar1 = (**(code **)(*param_2 + 0x10))(*param_2,1,local_38);
  if (lVar1 < 0) {
    uVar2 = 0x800000000000000f;
  }
  else {
    (**(code **)(DAT_00029498 + 0x160))((longlong)param_2 + 0x17,local_38,0x21);
    uVar2 = 0;
    *(undefined2 *)((longlong)param_2 + 0x14) = 0x100;
  }
  return uVar2;
}


// ==== FUN_00019a14 @ 00019a14

void FUN_00019a14(longlong param_1,longlong param_2)

{
  undefined8 *puVar1;
  longlong lVar2;
  byte bVar3;
  longlong *plVar4;
  undefined *puVar5;
  wchar_t *pwVar6;
  undefined *puVar7;
  wchar_t *pwVar8;
  bool bVar9;
  undefined2 local_res8 [4];
  uint local_res10 [2];
  undefined8 local_res18;
  undefined4 local_38;
  undefined4 local_34;
  undefined4 local_30;
  undefined4 local_2c;
  
  plVar4 = (longlong *)(param_2 * 0x40 + DAT_00029448);
  local_res10[0] = 0;
  local_res8[0] = 0;
  if (plVar4 == (longlong *)0x0) {
    return;
  }
  puVar1 = (undefined8 *)*plVar4;
  lVar2 = (*(code *)*puVar1)(puVar1,local_res8);
  if (lVar2 < 0) {
    return;
  }
  bVar3 = (byte)local_res8[0];
  *(byte *)(param_1 + 1) = bVar3 & 1;
  *(byte *)(param_1 + 2) = bVar3 >> 1 & 1;
  *(byte *)(param_1 + 4) = bVar3 >> 3 & 1;
  *(byte *)(param_1 + 3) = bVar3 >> 2 & 1;
  lVar2 = (*(code *)puVar1[6])(puVar1,local_res10);
  if (lVar2 < 0) {
    return;
  }
  if ((local_res10[0] & 0x10) == 0) {
    *(byte *)(param_1 + 5) = (byte)(local_res10[0] >> 0x11) & 1;
  }
  else {
    *(undefined1 *)(param_1 + 5) = 2;
  }
  local_38 = 0x38dc1092;
  bVar9 = DAT_00029458 == '\0';
  *(byte *)(param_1 + 6) = (byte)(local_res10[0] >> 0x10) & 1;
  local_34 = 0x4336ff7a;
  local_30 = 0xb5bf73a2;
  local_2c = 0x5f8a3619;
  local_res18 = 0;
  if (bVar9) {
    lVar2 = (**(code **)(DAT_00029498 + 0x140))(&local_38,0,&local_res18);
    if (-1 < lVar2) {
      DAT_00029458 = '\x01';
    }
    if (DAT_00029458 == '\0') {
      *(undefined1 *)(param_1 + 7) = 1;
      goto LAB_00019b26;
    }
  }
  *(undefined1 *)(param_1 + 7) = 0;
LAB_00019b26:
  puVar7 = &DAT_00027f10;
  puVar5 = &DAT_00027f10;
  if (*(char *)(param_1 + 1) != '\0') {
    puVar5 = &DAT_00027f70;
  }
  FUN_00018c7c(DAT_00029440,puVar5,DAT_0002b034);
  puVar5 = &DAT_00027f10;
  if (*(char *)(param_1 + 2) != '\0') {
    puVar5 = &DAT_00027f70;
  }
  FUN_00018c7c(DAT_00029440,puVar5,DAT_0002b030);
  puVar5 = &DAT_00027f10;
  if (*(char *)(param_1 + 3) != '\0') {
    puVar5 = &DAT_00027f70;
  }
  FUN_00018c7c(DAT_00029440,puVar5,DAT_0002b020);
  if (*(char *)(param_1 + 4) != '\0') {
    puVar7 = &DAT_00027f70;
  }
  FUN_00018c7c(DAT_00029440,puVar7,DAT_0002b032);
  pwVar8 = u_NOT_INSTALLED_00027f18;
  if (*(char *)(param_1 + 5) == '\0') {
    pwVar6 = u_NOT_INSTALLED_00027f18;
  }
  else {
    pwVar6 = u_UNKNOWN_00027f90;
    if (*(char *)(param_1 + 5) == '\x01') {
      pwVar6 = u_INSTALLED_00027f78;
    }
  }
  FUN_00018c7c(DAT_00029440,pwVar6,DAT_0002b038);
  if (*(char *)(param_1 + 6) != '\0') {
    pwVar8 = u_INSTALLED_00027f78;
  }
  FUN_00018c7c(DAT_00029440,pwVar8,DAT_0002b03a);
  return;
}


// ==== FUN_0001a8a0 @ 0001a8a0

void FUN_0001a8a0(undefined8 param_1,short param_2)

{
  longlong lVar1;
  char *local_res18 [2];
  
  local_res18[0] = (char *)0x0;
  if (param_2 == 1) {
    lVar1 = (**(code **)(DAT_00029478 + 0x140))(&DAT_00024a48,0,&DAT_0002b010);
    if ((-1 < lVar1) && (*DAT_0002b010 == 1)) {
      (**(code **)(DAT_0002b010 + 4))(DAT_0002b010,local_res18);
      if (local_res18[0][1] != '\0') {
        FUN_00000680(param_1,DAT_00024a38,&DAT_0002672c,0x28058);
      }
      if (local_res18[0][2] != '\0') {
        FUN_00000680(param_1,DAT_00024a3a,&DAT_0002672c,0x28058);
      }
      if (*local_res18[0] != '\0') {
        FUN_00000680(param_1,DAT_00024a3c,&DAT_0002672c,0x26840);
      }
      if (local_res18[0][3] != '\0') {
        FUN_00000680(param_1,DAT_00024a3e,&DAT_0002672c,0x26840);
      }
      if (*(uint *)(local_res18[0] + 4) != 0) {
        FUN_00000680(param_1,DAT_00024a40,&DAT_00026b54,(ulonglong)*(uint *)(local_res18[0] + 4));
        FUN_00000680(param_1,DAT_00024a42,&DAT_00026b54,
                     (ulonglong)(*(uint *)(local_res18[0] + 4) >> 4 & 0x3f));
        FUN_00000680(param_1,DAT_00024a44,&DAT_00026b54,
                     (ulonglong)(*(uint *)(local_res18[0] + 4) >> 10 & 0x1f));
        FUN_00000680(param_1,DAT_00024a46,&DAT_00026b54,
                     (ulonglong)(*(ushort *)(local_res18[0] + 6) & 0x1ff));
      }
    }
  }
  return;
}


// ==== FUN_0001afb0 @ 0001afb0

/* WARNING: Type propagation algorithm not settling */
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_0001afb0(void)

{
  char cVar1;
  uint *puVar2;
  longlong lVar3;
  undefined8 uVar4;
  uint uVar5;
  short *psVar7;
  undefined1 uVar8;
  undefined2 *puVar9;
  undefined1 uVar10;
  undefined8 *puVar11;
  int *piVar12;
  undefined1 local_res8 [8];
  short local_res10 [4];
  short local_res18 [4];
  undefined2 local_res20 [4];
  undefined4 *puVar13;
  undefined4 local_e8;
  ushort local_e4;
  undefined1 local_e2;
  undefined2 local_e1;
  undefined2 local_de;
  undefined1 local_dc;
  uint local_d8;
  undefined4 local_d4;
  undefined4 local_d0;
  uint local_cc;
  longlong local_c8;
  undefined2 local_c0 [2];
  int local_bc [3];
  uint local_b0 [2];
  undefined8 *local_a8;
  ulonglong local_a0;
  undefined8 uStack_98;
  undefined8 local_88;
  longlong local_80;
  uint local_78;
  ulonglong local_74;
  undefined8 uStack_6c;
  undefined1 local_60 [8];
  undefined1 local_58 [32];
  ulonglong uVar6;
  
  local_d0 = 0x30004;
  uVar6 = 0;
  local_c8 = 0;
  local_d4 = 0;
  uVar8 = 1;
  local_d8 = 1;
  puVar2 = (uint *)FUN_0001b544(4);
  if (puVar2 != (uint *)0x0) {
    lVar3 = FUN_000202e0(&local_d8,puVar2);
    if (lVar3 < 0) {
      if (lVar3 == -0x7ffffffffffffffb) {
        (**(code **)(DAT_00029478 + 0x48))(puVar2);
        puVar2 = (uint *)FUN_0001b544((ulonglong)local_d8 << 2);
        if (puVar2 == (uint *)0x0) goto LAB_0001b0ac;
        lVar3 = FUN_000202e0(&local_d8,puVar2);
      }
      if (lVar3 < 0) goto LAB_0001b0ac;
    }
    if (local_d8 != 0) {
      do {
        if ((char)puVar2[uVar6] == '\x03') {
          FUN_00000680(DAT_0002afc8,0x1328,&DAT_00025c1c,
                       (ulonglong)*(byte *)((longlong)puVar2 + uVar6 * 4 + 3));
          FUN_00000680(DAT_0002afc8,0x132b,&DAT_00025c1c,
                       (ulonglong)*(byte *)((longlong)puVar2 + uVar6 * 4 + 2));
          break;
        }
        uVar5 = (int)uVar6 + 1;
        uVar6 = (ulonglong)uVar5;
      } while (uVar5 < local_d8);
    }
  }
LAB_0001b0ac:
  puVar13 = &local_e8;
  puVar11 = &local_88;
  local_88 = 0xd;
  lVar3 = (**(code **)(DAT_00029488 + 0x48))
                    (u_MeSetupStorage_00028080,&DAT_000238b0,&local_d4,puVar11,puVar13);
  uVar10 = SUB81(puVar11,0);
  if (lVar3 < 0) {
    local_d4 = 7;
    local_e8 = 0x101;
    local_e4 = 0;
    local_e1 = 0;
    local_e2 = 0;
    local_de = 0;
  }
  local_dc = 0;
  lVar3 = FUN_00020d34(local_res10,local_res20);
  if (lVar3 < 0) {
LAB_0001b1dc:
    if (-1 < lVar3) {
      FUN_0001e7c4(DAT_0002afc8,
                   *(undefined2 *)((longlong)&local_d0 + (ulonglong)((int)local_a0 != 0) * 2),
                   local_60,local_58);
      FUN_00000680(DAT_0002afc8,0x1320,&DAT_00025b68,(ulonglong)local_58);
      uVar6 = local_a0 >> 0x20 & 0xffff;
      FUN_00000680(DAT_0002afc8,0x1323,(byte *)u__d__d__d__d_00026538,uVar6);
      uVar10 = (undefined1)uVar6;
    }
  }
  else if (local_res10[0] != 0xc) {
    lVar3 = (**(code **)(DAT_00029478 + 0x140))(&DAT_000234b0,0,&local_a8);
    if (-1 < lVar3) {
      lVar3 = (*(code *)local_a8[8])(local_bc);
      if ((lVar3 < 0) || (local_bc[0] != 0)) {
        lVar3 = -0x7ffffffffffffffd;
      }
      else {
        piVar12 = local_bc + 1;
        local_78 = 0x21ff;
        local_bc[1] = 0x18;
        lVar3 = (*(code *)*local_a8)
                          (0,&local_78,4,piVar12,(ulonglong)puVar13 & 0xffffffffffffff00,7);
        uVar10 = SUB81(piVar12,0);
        if (-1 < lVar3) {
          if ((((local_78 & 0x7f00) != 0x2100) || ((local_78 >> 0xf & 1) == 0)) ||
             ((local_78 & 0xff000000) != 0)) goto LAB_0001b25c;
          local_a0 = local_74;
          uStack_98 = uStack_6c;
        }
      }
    }
    goto LAB_0001b1dc;
  }
LAB_0001b25c:
  puVar9 = local_c0;
  psVar7 = local_res18;
  lVar3 = FUN_00020d34(psVar7,puVar9);
  if (-1 < lVar3) {
    local_cc = 1;
    if (local_res18[0] == 0xc) {
      FUN_0001fbe8((undefined8 *)psVar7,(uint)puVar9,&local_cc,uVar10,(uint *)&local_de);
    }
    else {
      FUN_0001ff68(psVar7,(uint)puVar9,&local_cc,uVar10,(uint *)&local_de);
    }
  }
  uVar6 = rdmsr(0x13a);
  uVar10 = (undefined1)local_e1;
  if ((uVar6 >> 0x20 & 1) != 0) {
    uVar10 = uVar8;
  }
  uVar6 = rdmsr(0x13a);
  if ((uVar6 & 0x20) != 0) {
    local_e1._1_1_ = uVar8;
  }
  local_e1 = CONCAT11(local_e1._1_1_,uVar10);
  uVar4 = FUN_00020c20();
  local_e8 = CONCAT13((char)uVar4 != '\0',(uint3)local_e8);
  lVar3 = (**(code **)(DAT_00029478 + 0x140))(&DAT_000234b0,0,&local_80);
  if (lVar3 < 0) {
    local_e8 = CONCAT13(1,(uint3)local_e8);
    goto LAB_0001b3de;
  }
  (**(code **)(local_80 + 0x40))(local_bc + 2);
  if (local_bc[2] != 0) {
    local_e8._0_3_ = (uint3)(ushort)local_e8;
    goto LAB_0001b3de;
  }
  local_e8._0_3_ = CONCAT12(1,(ushort)local_e8);
  if (local_e8._3_1_ != '\0') goto LAB_0001b3de;
  lVar3 = (**(code **)(DAT_00029478 + 0x140))(&DAT_000235e0,0,&local_c8);
  if (-1 < lVar3) {
    cVar1 = (**(code **)(local_c8 + 0x18))();
    if ((cVar1 == '\0') && (cVar1 = (**(code **)(local_c8 + 0x48))(), cVar1 == '\0')) {
      cVar1 = (**(code **)(local_c8 + 0x30))();
      local_e4 = local_e4 & 0xff00;
      if (cVar1 == '\0') goto LAB_0001b375;
    }
    local_e4 = CONCAT11(local_e4._1_1_,1);
  }
LAB_0001b375:
  lVar3 = FUN_0001fa64(0x20,local_b0);
  if (-1 < lVar3) {
    local_e8 = CONCAT31(local_e8._1_3_,(char)(local_b0[0] >> 2)) & 0xffffff01;
    local_e4 = CONCAT11((byte)(local_b0[0] >> 0x1d),(undefined1)local_e4) & 0x1ff;
  }
  if ((_DAT_e00b0064 >> 8 & 1) != 0) {
    local_e2 = uVar8;
  }
  lVar3 = FUN_0001fa64(7,(undefined4 *)local_res8);
  uVar8 = local_e8._1_1_;
  if (-1 < lVar3) {
    uVar8 = local_res8[0];
  }
  local_e8._0_2_ = CONCAT11(uVar8,(undefined1)local_e8);
LAB_0001b3de:
  if (puVar2 != (uint *)0x0) {
    (**(code **)(DAT_00029478 + 0x48))(puVar2);
  }
  (**(code **)(DAT_00029488 + 0x58))(u_MeSetupStorage_00028080,&DAT_000238b0,local_d4,0xd,&local_e8)
  ;
  (**(code **)(DAT_00029488 + 0x58))(u_MeBackupStorage_000280a0,&DAT_000238b0,2,0xd,&local_e8);
  return;
}


// ==== FUN_0001b458 @ 0001b458

short * FUN_0001b458(short *param_1,ulonglong param_2)

{
  ulonglong uVar1;
  short sVar2;
  longlong lVar3;
  short *psVar4;
  longlong lVar5;
  short local_48 [32];
  
  lVar3 = FUN_0001c0f8((char *)local_48,0x3c,(byte *)u__OFFSET__x_WIDTH__x_000280f8,param_2);
  lVar5 = 0;
  if (param_1 != (short *)0x0) {
    sVar2 = *param_1;
    psVar4 = param_1;
    while (sVar2 != 0) {
      psVar4 = psVar4 + 1;
      lVar5 = lVar5 + 1;
      sVar2 = *psVar4;
    }
    lVar3 = lVar3 + lVar5;
  }
  uVar1 = lVar3 * 2 + 2;
  psVar4 = (short *)FUN_0001b544(uVar1);
  if (psVar4 != (short *)0x0) {
    if (param_1 != (short *)0x0) {
      FUN_0001d16c(psVar4,uVar1 >> 1,param_1);
      (**(code **)(DAT_00029478 + 0x48))(param_1);
    }
    FUN_0001d16c(psVar4,uVar1 >> 1,local_48);
  }
  return psVar4;
}


// ==== FUN_0001b514 @ 0001b514

undefined8 FUN_0001b514(undefined8 param_1,undefined8 param_2)

{
  longlong lVar1;
  undefined8 local_res18 [2];
  
  lVar1 = (**(code **)(DAT_00029478 + 0x40))(4,param_2,local_res18);
  if (lVar1 < 0) {
    local_res18[0] = 0;
  }
  return local_res18[0];
}


// ==== FUN_0001b544 @ 0001b544

void FUN_0001b544(ulonglong param_1)

{
  undefined8 *puVar1;
  
  puVar1 = (undefined8 *)FUN_0001b514(param_1,param_1);
  if ((puVar1 != (undefined8 *)0x0) && (param_1 != 0)) {
    FUN_00000340(puVar1,param_1);
  }
  return;
}


// ==== FUN_0001b570 @ 0001b570

void FUN_0001b570(undefined8 param_1,ulonglong param_2,undefined8 *param_3)

{
  undefined8 *puVar1;
  
  puVar1 = (undefined8 *)FUN_0001b514(param_1,param_2);
  if (((puVar1 != (undefined8 *)0x0) && (param_2 != 0)) && (puVar1 != param_3)) {
    FUN_000002e0(puVar1,param_3,param_2);
  }
  return;
}


// ==== FUN_0001b5b0 @ 0001b5b0

undefined8 *
FUN_0001b5b0(undefined8 param_1,ulonglong param_2,ulonglong param_3,undefined8 *param_4)

{
  undefined8 *puVar1;
  
  puVar1 = (undefined8 *)FUN_0001b514(param_1,param_3);
  if (puVar1 != (undefined8 *)0x0) {
    if (param_3 != 0) {
      puVar1 = FUN_00000340(puVar1,param_3);
    }
    if ((puVar1 != (undefined8 *)0x0) && (param_4 != (undefined8 *)0x0)) {
      if (param_2 < param_3) {
        param_3 = param_2;
      }
      if ((param_3 != 0) && (puVar1 != param_4)) {
        FUN_000002e0(puVar1,param_4,param_3);
      }
      (**(code **)(DAT_00029478 + 0x48))(param_4);
    }
  }
  return puVar1;
}


// ==== FUN_0001b640 @ 0001b640

ulonglong FUN_0001b640(uint param_1,ulonglong param_2,undefined4 *param_3)

{
  ulonglong uVar1;
  ulonglong uVar2;
  ulonglong uVar3;
  
  uVar2 = param_2;
  if ((param_1 & 1) != 0) {
    uVar3 = (ulonglong)param_1;
    uVar2 = param_2 - 1;
    param_1 = param_1 + 1;
    *(undefined1 *)param_3 = *(undefined1 *)(uVar3 + 0xe0000000);
    param_3 = (undefined4 *)((longlong)param_3 + 1);
  }
  if ((1 < uVar2) && ((param_1 & 2) != 0)) {
    uVar3 = (ulonglong)param_1;
    uVar2 = uVar2 - 2;
    param_1 = param_1 + 2;
    *(undefined2 *)param_3 = *(undefined2 *)(uVar3 + 0xe0000000);
    param_3 = (undefined4 *)((longlong)param_3 + 2);
  }
  if (3 < uVar2) {
    uVar3 = uVar2 >> 2;
    uVar2 = uVar2 + uVar3 * -4;
    do {
      uVar1 = (ulonglong)param_1;
      param_1 = param_1 + 4;
      *param_3 = *(undefined4 *)(uVar1 + 0xe0000000);
      param_3 = param_3 + 1;
      uVar3 = uVar3 - 1;
    } while (uVar3 != 0);
  }
  if (1 < uVar2) {
    uVar3 = (ulonglong)param_1;
    uVar2 = uVar2 - 2;
    param_1 = param_1 + 2;
    *(undefined2 *)param_3 = *(undefined2 *)(uVar3 + 0xe0000000);
    param_3 = (undefined4 *)((longlong)param_3 + 2);
  }
  if (uVar2 != 0) {
    *(undefined1 *)param_3 = *(undefined1 *)((ulonglong)param_1 + 0xe0000000);
  }
  return param_2;
}


// ==== FUN_0001b6e0 @ 0001b6e0

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_0001b6e0(void)

{
  ushort uVar1;
  
  if (DAT_00024e01 != -1) {
    return;
  }
  uVar1 = _DAT_e00f8002 & 0xffe0;
  if (uVar1 != 0x280) {
    if (uVar1 == 0x680) {
      DAT_00024e01 = 1;
      return;
    }
    if (uVar1 != 0x9d80) {
      if (uVar1 == 0xa300) {
        DAT_00024e01 = 1;
        return;
      }
      DAT_00024e01 = 0xff;
      return;
    }
  }
  DAT_00024e01 = 2;
  return;
}


// ==== FUN_0001b738 @ 0001b738

longlong FUN_0001b738(void)

{
  if (DAT_00029490 == 0) {
    (**(code **)(DAT_00029478 + 0x140))(&DAT_00023590,0,&DAT_00029490);
  }
  return DAT_00029490;
}


// ==== FUN_0001b774 @ 0001b774

undefined8 FUN_0001b774(char param_1,undefined1 param_2)

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
      FUN_0001f9b8(0xf);
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


// ==== FUN_0001b7ec @ 0001b7ec

undefined8 FUN_0001b7ec(char param_1)

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
      FUN_0001f9b8(5000);
      bVar2 = in(uVar1);
      uVar5 = uVar5 + 1;
    } while ((bVar2 & 1) != 0);
    if (0x1ffff < uVar5) {
      return 0x8000000000000007;
    }
  }
  return 0;
}


// ==== FUN_0001b874 @ 0001b874

undefined8 FUN_0001b874(char param_1)

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
      FUN_0001f9b8(0xf);
      bVar2 = in(uVar1);
      uVar3 = uVar3 + 1;
    } while ((bVar2 & 2) != 0);
    if (0x1ffff < uVar3) {
      return 0x8000000000000007;
    }
  }
  return 0;
}


// ==== FUN_0001b8d8 @ 0001b8d8

longlong FUN_0001b8d8(char param_1,undefined1 param_2,undefined1 param_3)

{
  byte bVar1;
  byte bVar2;
  longlong lVar3;
  ulonglong uVar4;
  undefined2 uVar5;
  
  lVar3 = FUN_0001b874(param_1);
  uVar4 = 0;
  if (lVar3 < 0) {
    return lVar3;
  }
  FUN_0001b7ec(param_1);
  FUN_0001b774(param_1,param_2);
  FUN_0001b874(param_1);
  uVar5 = 0x60;
  bVar1 = 100;
  if (param_1 != '`') {
    bVar1 = 0x66;
  }
  bVar2 = in((ushort)bVar1);
  if ((bVar2 & 2) != 0) {
    do {
      if (0x1ffff < uVar4) goto LAB_0001b97a;
      FUN_0001f9b8(0xf);
      bVar2 = in((ushort)bVar1);
      uVar4 = uVar4 + 1;
    } while ((bVar2 & 2) != 0);
    if (0x1ffff < uVar4) goto LAB_0001b97a;
  }
  if (param_1 != '`') {
    uVar5 = 0x62;
  }
  out(uVar5,param_3);
LAB_0001b97a:
  FUN_0001b7ec(param_1);
  return lVar3;
}


// ==== FUN_0001b9a0 @ 0001b9a0

longlong FUN_0001b9a0(undefined8 param_1,undefined1 param_2,undefined1 *param_3)

{
  byte bVar1;
  undefined1 uVar2;
  longlong lVar3;
  ulonglong uVar4;
  
  uVar4 = 0;
  lVar3 = FUN_0001b8d8('b',0xa3,4);
  if (((-1 < lVar3) && (lVar3 = FUN_0001b8d8('b',0xa2,param_2), -1 < lVar3)) &&
     (lVar3 = FUN_0001b774('b',0xa4), -1 < lVar3)) {
    bVar1 = in(0x66);
    if ((bVar1 & 1) == 0) {
      do {
        if (0x1ffff < uVar4) {
          return -0x7ffffffffffffff9;
        }
        FUN_0001f9b8(0xf);
        bVar1 = in(0x66);
        uVar4 = uVar4 + 1;
      } while ((bVar1 & 1) == 0);
      if (0x1ffff < uVar4) {
        return -0x7ffffffffffffff9;
      }
    }
    uVar2 = in(0x62);
    *param_3 = uVar2;
    lVar3 = 0;
  }
  return lVar3;
}


// ==== FUN_0001ba3c @ 0001ba3c

longlong FUN_0001ba3c(undefined8 param_1,undefined8 param_2,undefined1 param_3,undefined1 param_4)

{
  longlong lVar1;
  longlong lVar2;
  
  lVar1 = FUN_0001b8d8('b',0xa3,7);
  if (((-1 < lVar1) && (lVar1 = FUN_0001b8d8('b',0xa2,param_3), -1 < lVar1)) &&
     (lVar2 = FUN_0001b8d8('b',0xa5,param_4), lVar1 = 0, lVar2 < 0)) {
    lVar1 = lVar2;
  }
  return lVar1;
}


// ==== FUN_0001ba9c @ 0001ba9c

longlong FUN_0001ba9c(undefined8 param_1,undefined8 param_2,undefined1 param_3,undefined1 *param_4)

{
  byte bVar1;
  undefined1 uVar2;
  longlong lVar3;
  ulonglong uVar4;
  
  uVar4 = 0;
  lVar3 = FUN_0001b8d8('b',0xa3,7);
  if (((-1 < lVar3) && (lVar3 = FUN_0001b8d8('b',0xa2,param_3), -1 < lVar3)) &&
     (lVar3 = FUN_0001b774('b',0xa4), -1 < lVar3)) {
    bVar1 = in(0x66);
    if ((bVar1 & 1) == 0) {
      do {
        if (0x1ffff < uVar4) {
          return -0x7ffffffffffffff9;
        }
        FUN_0001f9b8(0xf);
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


// ==== FUN_0001bb38 @ 0001bb38

uint FUN_0001bb38(void)

{
  uint local_18;
  undefined4 local_14;
  undefined4 local_10;
  undefined4 local_c [3];
  
  FUN_000003d0(1,&local_18,&local_14,&local_10,local_c);
  return local_18 & 0xfff0ff0;
}


// ==== FUN_0001bb6c @ 0001bb6c

uint FUN_0001bb6c(void)

{
  uint local_18;
  undefined4 local_14;
  undefined4 local_10;
  undefined4 local_c [3];
  
  FUN_000003d0(1,&local_18,&local_14,&local_10,local_c);
  return local_18 & 0xf;
}


// ==== FUN_0001bba0 @ 0001bba0

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

undefined8 FUN_0001bba0(void)

{
  ulonglong uVar1;
  undefined1 uVar2;
  uint local_18;
  undefined4 local_14;
  undefined4 local_10;
  undefined4 local_c;
  
  uVar2 = 4;
  FUN_000003d0(1,&local_18,&local_14,&local_10,&local_c);
  local_18 = local_18 & 0xfff0ff0;
  if (local_18 == 0x806e0) {
    uVar1 = (ulonglong)_DAT_e0000002;
    if ((_DAT_e0000002 < 0x3e34) ||
       (((((0x3e36 < _DAT_e0000002 && (_DAT_e0000002 != 0x3ecc)) && (_DAT_e0000002 != 0x3ed0)) &&
         (_DAT_e0000002 != 0x5904)) &&
        ((uVar1 = (ulonglong)(_DAT_e0000002 - 0x9b51), 0x20 < _DAT_e0000002 - 0x9b51 ||
         ((0x100010001U >> (uVar1 & 0x3f) & 1) == 0)))))) goto LAB_0001bd2f;
LAB_0001bd2d:
    uVar2 = 0;
  }
  else {
    if (local_18 == 0x906e0) {
      uVar1 = 0x3ec2;
      if (0x3ec2 < _DAT_e0000002) {
        if (_DAT_e0000002 != 0x3ec4) {
          if ((_DAT_e0000002 == 0x3ec6) || (_DAT_e0000002 == 0x3eca)) goto LAB_0001bc6f;
          if (_DAT_e0000002 != 0x5910) {
            if ((_DAT_e0000002 == 0x5918) || (_DAT_e0000002 == 0x591f)) goto LAB_0001bc6f;
            if (_DAT_e0000002 != 0x9b44) goto LAB_0001bd2f;
          }
        }
LAB_0001bce9:
        uVar2 = 3;
        goto LAB_0001bd2f;
      }
      if ((_DAT_e0000002 != 0x3ec2) && (_DAT_e0000002 != 0x3e0f)) {
        uVar1 = (ulonglong)(_DAT_e0000002 - 0x3e10);
        if ((_DAT_e0000002 - 0x3e10 & 0xfffffffd) == 0) goto LAB_0001bce9;
        if ((_DAT_e0000002 != 0x3e18) && (_DAT_e0000002 != 0x3e1f)) {
          if (_DAT_e0000002 == 0x3e20) goto LAB_0001bce9;
          uVar1 = (ulonglong)(_DAT_e0000002 - 0x3e30);
          if (3 < _DAT_e0000002 - 0x3e30) goto LAB_0001bd2f;
        }
      }
    }
    else {
      local_18 = local_18 - 0xa0650;
      uVar1 = (ulonglong)local_18;
      if (local_18 != 0) {
        if (local_18 != 0x10) goto LAB_0001bd2f;
        if (_DAT_e0000002 != 0x9b51) {
          if (_DAT_e0000002 == 0x9b60) {
            uVar2 = 2;
            goto LAB_0001bd2f;
          }
          if ((_DAT_e0000002 != 0x9b61) && (_DAT_e0000002 != 0x9b71)) goto LAB_0001bd2f;
        }
        goto LAB_0001bd2d;
      }
      if ((_DAT_e0000002 != 0x9b33) && (_DAT_e0000002 != 0x9b43)) {
        if (_DAT_e0000002 == 0x9b44) goto LAB_0001bce9;
        if (_DAT_e0000002 != 0x9b53) {
          if (_DAT_e0000002 == 0x9b54) goto LAB_0001bce9;
          if (_DAT_e0000002 != 0x9b63) {
            if (_DAT_e0000002 == 0x9b64) goto LAB_0001bce9;
            if (_DAT_e0000002 != 0x9b73) goto LAB_0001bd2f;
          }
        }
      }
    }
LAB_0001bc6f:
    uVar2 = 1;
  }
LAB_0001bd2f:
  return CONCAT71((int7)(uVar1 >> 8),uVar2);
}


// ==== FUN_0001bd38 @ 0001bd38

uint FUN_0001bd38(void)

{
  uint uVar1;
  uint uVar2;
  
  uVar1 = FUN_0001bb6c();
  uVar2 = FUN_0001bb38();
  if ((uVar2 == 0xa0650) && ((uVar1 == 1 || (uVar1 - 4 < 2)))) {
    uVar2 = 0xa0601;
  }
  else {
    uVar2 = uVar2 & 0xffffff00;
  }
  return uVar2;
}


// ==== FUN_0001bd6c @ 0001bd6c

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

longlong FUN_0001bd6c(int param_1,uint param_2,int *param_3,uint *param_4)

{
  longlong lVar1;
  int *piVar2;
  uint uVar3;
  uint *puVar4;
  uint local_48;
  int local_44;
  undefined8 local_40;
  int local_38;
  uint local_34;
  uint local_30;
  int local_2c;
  int local_28;
  uint local_24;
  
  lVar1 = FUN_0001c00c(param_1);
  if (lVar1 < 0) {
    return lVar1;
  }
  if (param_1 == 1) {
    local_44 = 0;
    local_48 = param_2 | 0x80000000;
    uVar3 = _DAT_e0000048 & 0xfffffffe;
    puVar4 = (uint *)(ulonglong)(uVar3 + 0x5da4);
    *puVar4 = local_48;
    FUN_0001c00c(1);
    local_48 = *puVar4;
    uVar3 = uVar3 + 0x5da0;
    local_44 = *(int *)(ulonglong)uVar3;
    FUN_0001f9b8(10);
    local_30 = *puVar4;
    local_2c = *(int *)(ulonglong)uVar3;
    if ((local_48 != local_30) && (local_44 != local_2c)) {
      return -0x7ffffffffffffffe;
    }
    *param_4 = local_48;
  }
  else {
    if (param_1 == 2) {
      local_38 = 0;
      local_34 = param_2 | 0x80000000;
      FUN_000002e0(&local_40,(undefined8 *)&local_38,8);
      wrmsr(0x150,local_40);
      FUN_0001c00c(2);
      local_40 = rdmsr(0x150);
      FUN_000002e0((undefined8 *)&local_38,&local_40,8);
      FUN_0001f9b8(10);
      local_40 = rdmsr(0x150);
      FUN_000002e0((undefined8 *)&local_28,&local_40,8);
      if ((local_34 != local_24) && (local_38 != local_28)) {
        return -0x7ffffffffffffffe;
      }
      *param_4 = local_34 & 0xff;
      if (param_3 == &local_38) {
        return lVar1;
      }
      piVar2 = &local_38;
      goto LAB_0001bfe4;
    }
    if (param_1 != 3) {
      return -0x7ffffffffffffffd;
    }
    local_48 = param_2 | 0x80000000;
    local_44 = 0;
    wrmsr(0x607,(ulonglong)local_48);
    FUN_0001c00c(3);
    local_40 = rdmsr(0x607);
    FUN_000002e0((undefined8 *)&local_48,&local_40,4);
    local_40 = rdmsr(0x608);
    FUN_000002e0((undefined8 *)&local_44,&local_40,4);
    FUN_0001f9b8(10);
    local_40 = rdmsr(0x607);
    FUN_000002e0((undefined8 *)&local_30,&local_40,4);
    local_40 = rdmsr(0x608);
    FUN_000002e0((undefined8 *)&local_2c,&local_40,4);
    if ((local_48 != local_30) && (local_44 != local_2c)) {
      return -0x7ffffffffffffffe;
    }
    *param_4 = local_48 & 0xff;
  }
  if (param_3 == &local_44) {
    return lVar1;
  }
  piVar2 = &local_44;
LAB_0001bfe4:
  FUN_000002e0((undefined8 *)param_3,(undefined8 *)piVar2,4);
  return lVar1;
}


// ==== FUN_0001c00c @ 0001c00c

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

undefined8 FUN_0001c00c(int param_1)

{
  undefined8 uVar1;
  byte bVar2;
  ushort uVar3;
  undefined8 local_res10;
  undefined8 local_res18;
  undefined8 local_res20;
  
  uVar1 = 0;
  uVar3 = 0;
  bVar2 = 1;
  do {
    if (param_1 == 1) {
      bVar2 = (byte)((uint)*(undefined4 *)(ulonglong)((_DAT_e0000048 & 0xfffffffe) + 0x5da4) >> 0x18
                    );
LAB_0001c0b3:
      bVar2 = bVar2 >> 7;
    }
    else if (param_1 == 2) {
      local_res10 = rdmsr(0x150);
      FUN_000002e0(&local_res20,&local_res10,8);
      bVar2 = local_res20._7_1_ >> 7;
    }
    else if (param_1 == 3) {
      local_res10 = rdmsr(0x607);
      FUN_000002e0(&local_res18,&local_res10,8);
      bVar2 = local_res18._3_1_;
      goto LAB_0001c0b3;
    }
    FUN_0001f9b8(1);
    uVar3 = uVar3 + 1;
    if (bVar2 != 1) {
      return 0;
    }
    if (999 < uVar3) {
      if (uVar3 == 1000) {
        uVar1 = 0x8000000000000012;
      }
      return uVar1;
    }
  } while( true );
}


// ==== FUN_0001c0f8 @ 0001c0f8

void FUN_0001c0f8(char *param_1,ulonglong param_2,byte *param_3,ulonglong param_4)

{
  ulonglong local_res20;
  
  local_res20 = param_4;
  FUN_0001c184(param_1,param_2 >> 1,0x140,param_3,&local_res20);
  return;
}


// ==== FUN_0001c128 @ 0001c128

void FUN_0001c128(char *param_1,ulonglong param_2,byte *param_3,ulonglong param_4)

{
  ulonglong local_res20;
  
  local_res20 = param_4;
  FUN_0001c184(param_1,param_2,0,param_3,&local_res20);
  return;
}


// ==== FUN_0001c150 @ 0001c150

undefined1 *
FUN_0001c150(undefined1 *param_1,undefined1 *param_2,longlong param_3,undefined8 param_4,
            longlong param_5)

{
  longlong lVar1;
  
  lVar1 = 0;
  if (0 < param_3) {
    do {
      if (param_2 <= param_1) {
        return param_1;
      }
      *param_1 = (char)param_4;
      if (param_5 != 1) {
        param_1[1] = (char)((ulonglong)param_4 >> 8);
      }
      param_1 = param_1 + param_5;
      lVar1 = lVar1 + 1;
    } while (lVar1 < param_3);
  }
  return param_1;
}


// ==== FUN_0001c184 @ 0001c184

ulonglong FUN_0001c184(char *param_1,ulonglong param_2,ulonglong param_3,byte *param_4,
                      ulonglong *param_5)

{
  ushort uVar1;
  bool bVar2;
  ulonglong uVar3;
  char cVar4;
  int iVar5;
  ulonglong uVar6;
  ulonglong uVar7;
  longlong lVar8;
  char *pcVar9;
  ulonglong uVar10;
  longlong lVar11;
  longlong lVar12;
  longlong lVar13;
  ulonglong uVar14;
  char *pcVar15;
  uint uVar16;
  ulonglong *puVar17;
  uint uVar18;
  ulonglong *puVar19;
  undefined8 *puVar20;
  byte *pbVar21;
  ulonglong uVar22;
  ulonglong uVar23;
  bool bVar24;
  ulonglong local_res18;
  byte *local_res20;
  char *local_d8;
  ulonglong local_d0;
  ulonglong local_c0;
  ulonglong local_b8;
  ulonglong *local_b0;
  ulonglong local_a8;
  ulonglong local_a0;
  ulonglong local_98;
  longlong local_90;
  ulonglong local_88;
  ulonglong local_80;
  char *local_78;
  undefined8 local_70;
  ulonglong local_48;
  
  puVar17 = (ulonglong *)0x0;
  local_b0 = (ulonglong *)0x0;
  if (param_2 == 0) {
    uVar23 = (ulonglong)((uint)param_3 & 0x2000);
    if ((param_3 & 0x2000) == 0) goto LAB_0001c1e3;
  }
  else {
    uVar23 = (ulonglong)((uint)param_3 & 0x2000);
    if (((param_3 & 0x2000) == 0) && (param_1 == (char *)0x0)) {
      return 0;
    }
  }
  if (param_4 == (byte *)0x0) {
    return 0;
  }
LAB_0001c1e3:
  uVar6 = 1;
  if ((param_3 & 0x40) == 0) {
    uVar14 = uVar6;
    if (1000000 < param_2) {
      return 0;
    }
  }
  else {
    if (1000000 < param_2) {
      return 0;
    }
    uVar14 = 2;
  }
  if ((param_3 >> 8 & 1) == 0) {
    uVar22 = FUN_0001d454((char *)param_4);
    if (1000000 < uVar22) {
      return 0;
    }
    local_98 = 0xff;
  }
  else {
    uVar6 = FUN_0001cfbc((short *)param_4,0xf4241);
    if (1000000 < uVar6) {
      return 0;
    }
    puVar17 = (ulonglong *)0x0;
    local_98 = 0xffff;
    uVar6 = 2;
  }
  local_80 = uVar6;
  if (uVar23 == 0) {
    if (param_2 == 0) {
      return 0;
    }
  }
  else {
    param_1 = (char *)((ulonglong)param_1 & -(ulonglong)(param_2 != 0));
  }
  local_78 = (char *)0x0;
  local_d0 = 0;
  local_d8 = (char *)0x0;
  if (param_1 != (char *)0x0) {
    local_78 = param_1;
    local_d8 = param_1 + (param_2 - 1) * uVar14;
  }
  if (uVar6 == 1) {
    iVar5 = 0;
  }
  else {
    iVar5 = (int)(char)param_4[1] << 8;
  }
  local_a8 = ((ulonglong)*param_4 | (longlong)iVar5) & local_98;
  local_res20 = param_4;
LAB_0001ce82:
  uVar23 = 1;
  if ((local_a8 != 0) && ((param_1 == (char *)0x0 || (param_1 < local_d8)))) {
    local_a0 = 0;
    uVar6 = 0;
    local_90 = 0;
    cVar4 = '\0';
    uVar22 = (ulonglong)((uint)param_3 & 0x2140);
    local_b8 = 1;
    bVar2 = false;
    bVar24 = false;
    local_c0 = 0;
    local_res18 = uVar22;
    if (local_a8 == 10) {
      pbVar21 = local_res20 + local_80;
      pcVar9 = &DAT_00028824;
      if (local_80 == 1) {
        iVar5 = 0;
      }
      else {
        iVar5 = (int)(char)pbVar21[1] << 8;
      }
      local_a8 = ((longlong)iVar5 | (ulonglong)*pbVar21) & local_98;
      if (local_a8 != 0xd) {
        pbVar21 = local_res20;
      }
      goto LAB_0001cabe;
    }
    if (local_a8 == 0xd) {
      pbVar21 = local_res20 + local_80;
      if (local_80 == 1) {
        iVar5 = 0;
      }
      else {
        iVar5 = (int)(char)pbVar21[1] << 8;
      }
      uVar10 = (longlong)iVar5 | (ulonglong)*pbVar21;
LAB_0001c59e:
      local_a8 = uVar10 & local_98;
      if ((uVar10 & local_98) == 10) {
        pcVar9 = &DAT_00028824;
      }
      else {
        pcVar9 = &DAT_00028828;
        pbVar21 = local_res20;
      }
      goto LAB_0001cabe;
    }
    puVar19 = param_5;
    pbVar21 = local_res20;
    uVar10 = uVar23;
    uVar7 = local_b8;
    if (local_a8 != 0x25) {
LAB_0001c312:
      pcVar9 = (char *)&local_a8;
LAB_0001c316:
      uVar22 = uVar22 | 0x400;
      local_res18 = uVar22;
      pbVar21 = local_res20;
      goto LAB_0001cabe;
    }
LAB_0001c335:
    while( true ) {
      local_b8 = uVar7;
      uVar23 = uVar10;
      local_res20 = pbVar21 + local_80;
      if (local_80 == 1) {
        iVar5 = 0;
      }
      else {
        iVar5 = (int)(char)local_res20[1] << 8;
      }
      local_a8 = ((ulonglong)*local_res20 | (longlong)iVar5) & local_98;
      uVar10 = uVar23;
      uVar7 = local_b8;
      if (local_a8 < 0x2e) break;
      if (local_a8 == 0x2e) {
        uVar22 = uVar22 | 0x800;
        pbVar21 = local_res20;
        local_res18 = uVar22;
      }
      else if (local_a8 == 0x30) {
        if ((uVar22 & 0x800) == 0) {
          uVar22 = uVar22 | 0x20;
          local_res18 = uVar22;
        }
LAB_0001c464:
        uVar6 = 0;
        while ((0x2f < local_a8 && (local_a8 < 0x3a))) {
          local_res20 = local_res20 + local_80;
          uVar6 = local_a8 + (uVar6 * 5 + -0x18) * 2;
          if (local_80 == 1) {
            iVar5 = 0;
          }
          else {
            iVar5 = (int)(char)local_res20[1] << 8;
          }
          local_a8 = ((ulonglong)*local_res20 | (longlong)iVar5) & local_98;
        }
        pbVar21 = local_res20 + -local_80;
        uVar10 = uVar6;
        local_c0 = uVar6;
        uVar7 = uVar6;
        if ((uVar22 & 0x800) == 0) {
          uVar22 = uVar22 | 0x200;
          local_a0 = uVar6;
          uVar10 = uVar23;
          local_res18 = uVar22;
          uVar7 = local_b8;
        }
      }
      else {
        if (local_a8 < 0x31) goto LAB_0001c4ef;
        if (local_a8 < 0x3a) goto LAB_0001c464;
        if ((local_a8 - 0x4c & 0xffffffffffffffdf) != 0) goto LAB_0001c4ef;
        uVar22 = uVar22 | 0x10;
        pbVar21 = local_res20;
        local_res18 = uVar22;
      }
    }
    if (local_a8 == 0x2d) {
      uVar22 = uVar22 | 1;
      pbVar21 = local_res20;
      local_res18 = uVar22;
      goto LAB_0001c335;
    }
    if (local_a8 != 0) {
      if (local_a8 == 0x20) {
        uVar22 = uVar22 | 4;
        pbVar21 = local_res20;
        local_res18 = uVar22;
      }
      else if (local_a8 == 0x2a) {
        if ((uVar22 & 0x800) == 0) {
          uVar22 = uVar22 | 0x200;
          if (puVar17 == (ulonglong *)0x0) {
            local_a0 = *puVar19;
            puVar19 = puVar19 + 1;
            param_5 = puVar19;
          }
          else {
            local_a0 = *puVar17;
            puVar17 = puVar17 + 1;
            local_b0 = puVar17;
          }
          pbVar21 = local_res20;
          local_res18 = uVar22;
        }
        else if (puVar17 == (ulonglong *)0x0) {
          uVar10 = *puVar19;
          puVar19 = puVar19 + 1;
          pbVar21 = local_res20;
          param_5 = puVar19;
          uVar7 = uVar10;
        }
        else {
          uVar10 = *puVar17;
          puVar17 = puVar17 + 1;
          pbVar21 = local_res20;
          uVar7 = uVar10;
          local_b0 = puVar17;
        }
      }
      else if (local_a8 == 0x2b) {
        uVar22 = uVar22 | 2;
        pbVar21 = local_res20;
        local_res18 = uVar22;
      }
      else {
        if (local_a8 != 0x2c) goto LAB_0001c4ef;
        uVar22 = uVar22 | 8;
        pbVar21 = local_res20;
        local_res18 = uVar22;
      }
      goto LAB_0001c335;
    }
    uVar23 = 0;
    local_b8 = 0;
    local_res20 = pbVar21;
LAB_0001c4ef:
    pbVar21 = local_res20;
    if (local_a8 < 0x68) {
      if (local_a8 == 0x67) {
        if (puVar17 == (ulonglong *)0x0) {
          uVar23 = *puVar19;
          param_5 = puVar19 + 1;
        }
        else {
          uVar23 = *puVar17;
          local_b0 = puVar17 + 1;
        }
        if (uVar23 == 0) {
          pcVar9 = s_<null_guid>_000287a8;
        }
        else {
          FUN_0001ceec();
          pcVar9 = (char *)&local_70;
          uVar6 = local_c0;
        }
        bVar2 = false;
        uVar23 = local_b8;
        goto LAB_0001cabe;
      }
      if (local_a8 == 10) {
        pbVar21 = local_res20 + local_80;
        pcVar9 = &DAT_00028824;
        if (local_80 == 1) {
          iVar5 = 0;
        }
        else {
          iVar5 = (int)(char)pbVar21[1] << 8;
        }
        local_a8 = ((longlong)iVar5 | (ulonglong)*pbVar21) & local_98;
        if (local_a8 != 0xd) {
          pbVar21 = local_res20;
        }
        goto LAB_0001cabe;
      }
      if (local_a8 == 0xd) {
        pbVar21 = local_res20 + local_80;
        if (local_80 == 1) {
          iVar5 = 0;
        }
        else {
          iVar5 = (int)(char)pbVar21[1] << 8;
        }
        uVar10 = (longlong)iVar5 | (ulonglong)*pbVar21;
        goto LAB_0001c59e;
      }
      if (local_a8 == 0x53) goto LAB_0001c787;
      if (local_a8 == 0x58) goto LAB_0001c87a;
      if (local_a8 == 0x61) goto LAB_0001c790;
      if (local_a8 == 99) {
        if (puVar17 == (ulonglong *)0x0) {
          uVar1 = (ushort)*puVar19;
          param_5 = puVar19 + 1;
        }
        else {
          uVar1 = (ushort)*puVar17;
          local_b0 = puVar17 + 1;
        }
        local_88 = (ulonglong)uVar1;
        pcVar9 = (char *)&local_88;
        goto LAB_0001c316;
      }
      if (local_a8 != 100) goto LAB_0001c312;
    }
    else {
      if (local_a8 == 0x70) {
        uVar22 = uVar22 & 0xffffffffffffffd9 | 0x10;
LAB_0001c87a:
        uVar22 = uVar22 | 0x20;
LAB_0001c87e:
        uVar22 = uVar22 | 0x80;
      }
      else {
        if (local_a8 == 0x72) {
          if (puVar17 == (ulonglong *)0x0) {
            uVar10 = *puVar19;
            param_5 = puVar19 + 1;
          }
          else {
            uVar10 = *puVar17;
            local_b0 = puVar17 + 1;
          }
          pcVar9 = (char *)&local_70;
          if ((longlong)uVar10 < 0) {
            if ((uVar10 & 0x7fffffffffffffff) - 1 < 0x21) {
              pcVar9 = (&PTR_s_Warning_Stale_Data_00028858)[uVar10];
LAB_0001c844:
              if (pcVar9 != (char *)&local_70) goto LAB_0001cabe;
            }
          }
          else if (uVar10 < 6) {
            pcVar9 = (&PTR_s_Success_00028830)[uVar10];
            goto LAB_0001c844;
          }
          FUN_0001ceec();
          uVar6 = local_c0;
          goto LAB_0001cabe;
        }
        if (local_a8 == 0x73) {
LAB_0001c787:
          uVar22 = uVar22 | 0x400;
          local_res18 = uVar22;
LAB_0001c790:
          if (puVar17 == (ulonglong *)0x0) {
            pcVar9 = (char *)*puVar19;
            param_5 = puVar19 + 1;
          }
          else {
            pcVar9 = (char *)*puVar17;
            local_b0 = puVar17 + 1;
          }
          if ((ulonglong *)pcVar9 == (ulonglong *)0x0) {
            uVar22 = uVar22 & 0xfffffffffffffbff;
            pcVar9 = s_<null_string>_00028798;
            local_res18 = uVar22;
          }
          uVar23 = uVar23 & -(ulonglong)((uVar22 & 0x800) != 0);
          goto LAB_0001cabe;
        }
        if (local_a8 == 0x74) {
          if (puVar17 == (ulonglong *)0x0) {
            uVar10 = *puVar19;
            param_5 = puVar19 + 1;
          }
          else {
            local_b0 = puVar17 + 1;
            uVar10 = *puVar17;
          }
          if (uVar10 == 0) {
            pcVar9 = s_<null_time>_000287f0;
          }
          else {
            FUN_0001ceec();
            pcVar9 = (char *)&local_70;
            uVar6 = local_c0;
          }
          goto LAB_0001cabe;
        }
        if (local_a8 != 0x75) {
          if (local_a8 != 0x78) goto LAB_0001c312;
          goto LAB_0001c87e;
        }
      }
      if (-1 < (char)uVar22) {
        uVar22 = uVar22 & 0xfffffffffffffffd | 0x4000;
      }
    }
    if ((uVar22 & 0x10) == 0) {
      if (puVar17 == (ulonglong *)0x0) {
        uVar6 = (ulonglong)(int)*puVar19;
        param_5 = puVar19 + 1;
      }
      else {
        uVar6 = (ulonglong)(int)*puVar17;
LAB_0001c8d3:
        local_b0 = puVar17 + 1;
      }
    }
    else {
      if (puVar17 != (ulonglong *)0x0) {
        uVar6 = *puVar17;
        goto LAB_0001c8d3;
      }
      uVar6 = *puVar19;
      param_5 = puVar19 + 1;
    }
    cVar4 = ((byte)uVar22 & 4) << 3;
    if ((uVar22 & 2) != 0) {
      cVar4 = '+';
    }
    bVar24 = (uVar22 & 8) != 0;
    if ((char)(byte)uVar22 < '\0') {
      uVar16 = 0x10;
      bVar24 = false;
      if (((uVar22 & 0x10) == 0) && (uVar18 = 0x10, (longlong)uVar6 < 0)) {
LAB_0001c95b:
        uVar16 = uVar18;
        uVar6 = uVar6 & 0xffffffff;
      }
    }
    else {
      uVar16 = 10;
      if ((uVar22 & 8) != 0) {
        uVar22 = uVar22 & 0xffffffffffffffdf;
        uVar23 = 1;
      }
      if (((longlong)uVar6 < 0) && (uVar22 >> 0xe == 0)) {
        cVar4 = '-';
        uVar6 = -uVar6;
      }
      else {
        uVar18 = 10;
        if (((uint)uVar22 & 0x4010) == 0x4000) goto LAB_0001c95b;
      }
    }
    local_70._0_1_ = 0;
    puVar20 = &local_70;
    uVar10 = uVar6;
    do {
      uVar7 = uVar10 / uVar16;
      puVar20 = (undefined8 *)((longlong)puVar20 + 1);
      *(undefined *)puVar20 = (&DAT_00028970)[uVar10 % (ulonglong)uVar16];
      uVar10 = uVar7;
    } while (uVar7 != 0);
    local_c0 = (longlong)puVar20 - (longlong)&local_70;
    if (uVar6 == 0) {
      local_c0 = local_c0 & -(ulonglong)(uVar23 != 0);
    }
    pcVar9 = (char *)((longlong)&local_70 + local_c0);
    local_90 = 3 - local_c0 % 3;
    if (local_c0 % 3 == 0) {
      local_90 = 0;
    }
    if ((bVar24) && (local_c0 != 0)) {
      local_c0 = local_c0 + (local_c0 - 1) / 3;
    }
    if (cVar4 != '\0') {
      local_c0 = local_c0 + 1;
      uVar23 = uVar23 + 1;
    }
    uVar22 = uVar22 | 0x1000;
    bVar2 = true;
    uVar6 = local_c0;
    local_res18 = uVar22;
    if (((uint)uVar22 & 0xa21) == 0x220) {
      uVar23 = local_a0;
    }
LAB_0001cabe:
    local_res20 = pbVar21;
    uVar16 = (uint)uVar22;
    lVar13 = (ulonglong)((uVar22 & 0x400) != 0) + 1;
    uVar18 = (-(uint)((uVar22 & 0x400) != 0) & 0xff00) + 0xff;
    if ((uVar22 >> 0xc & 1) == 0) {
      uVar6 = 0;
      pcVar15 = (char *)((longlong)pcVar9 + 1);
      while ((((local_c0 = uVar6, pcVar15[-1] != '\0' ||
               (((uVar22 & 0x400) != 0 && (*pcVar15 != '\0')))) &&
              ((uVar6 < uVar23 || ((uVar22 >> 0xb & 1) == 0)))) &&
             ((uVar18 & (int)CONCAT11(*pcVar15,pcVar15[-1])) != 0))) {
        uVar6 = uVar6 + 1;
        pcVar15 = pcVar15 + lVar13;
      }
    }
    else {
      lVar13 = -lVar13;
    }
    if (uVar23 < uVar6) {
      uVar23 = uVar6;
    }
    uVar10 = (ulonglong)(uVar16 & 0x201);
    local_48 = uVar10;
    pcVar15 = local_d8;
    if (uVar10 == 0x200) {
      local_d0 = local_d0 + (local_a0 - uVar23) * uVar14;
      if (((uVar22 >> 0xd & 1) == 0) && (param_1 != (char *)0x0)) {
        param_1 = FUN_0001c150(param_1,local_d8,local_a0 - uVar23,0x20,uVar14);
      }
    }
    uVar7 = uVar14;
    if (bVar2) {
      if (((cVar4 != '\0') && (local_d0 = local_d0 + uVar14, (uVar22 >> 0xd & 1) == 0)) &&
         (param_1 != (char *)0x0)) {
        lVar11 = 0;
        do {
          if (local_d8 <= param_1) break;
          *param_1 = cVar4;
          if (uVar14 != 1) {
            param_1[1] = '\0';
          }
          param_1 = param_1 + uVar14;
          lVar11 = lVar11 + 1;
        } while (lVar11 < 1);
      }
      local_d0 = local_d0 + (uVar23 - uVar6) * uVar14;
      if (((uVar22 & 0x2000) == 0) && (param_1 != (char *)0x0)) {
        param_1 = FUN_0001c150(param_1,local_d8,uVar23 - uVar6,(ulonglong)((uVar16 & 0x2000) + 0x30)
                               ,uVar14);
      }
    }
    else {
      local_d0 = local_d0 + (uVar23 - uVar6) * uVar14;
      if (((uVar22 & 0x2000) == 0) && (param_1 != (char *)0x0)) {
        param_1 = FUN_0001c150(param_1,pcVar15,uVar23 - uVar6,(ulonglong)((uVar16 & 0x2000) + 0x20),
                               uVar14);
      }
      if (((cVar4 != '\0') && (local_d0 = local_d0 + uVar7, (uVar22 & 0x2000) == 0)) &&
         (param_1 != (char *)0x0)) {
        lVar11 = 0;
        do {
          if (local_d8 <= param_1) break;
          *param_1 = cVar4;
          if (uVar7 != 1) {
            param_1[1] = '\0';
          }
          param_1 = param_1 + uVar7;
          lVar11 = lVar11 + 1;
        } while (lVar11 < 1);
      }
    }
    uVar6 = (ulonglong)(cVar4 != '\0');
    param_3 = uVar22;
    lVar11 = local_90;
    do {
      uVar3 = uVar6;
      if ((local_c0 <= uVar3) ||
         ((param_3 = local_res18, uVar10 = local_48, (char)*(ulonglong *)pcVar9 == '\0' &&
          ((lVar13 < 2 || (*(char *)((longlong)pcVar9 + 1) == '\0')))))) goto LAB_0001ce01;
      local_d0 = local_d0 + uVar7;
      uVar16 = (ushort)*(ulonglong *)pcVar9 & uVar18;
      if (((uVar22 & 0x2000) == 0) && (param_1 != (char *)0x0)) {
        lVar12 = 0;
        do {
          if (local_d8 <= param_1) break;
          *param_1 = (char)uVar16;
          if (uVar7 != 1) {
            param_1[1] = (char)(uVar16 >> 8);
          }
          param_1 = param_1 + uVar7;
          lVar12 = lVar12 + 1;
        } while (lVar12 < 1);
      }
      pcVar9 = (char *)((longlong)pcVar9 + lVar13);
      uVar6 = uVar3 + 1;
      if ((bVar24) && (lVar11 = lVar11 + 1, lVar11 == 3)) {
        lVar12 = 0;
        uVar6 = uVar3 + 2;
        if (local_c0 <= uVar6) goto LAB_0001ce01;
        local_d0 = local_d0 + uVar7;
        lVar11 = lVar12;
        if (((uVar22 & 0x2000) == 0) && (param_1 != (char *)0x0)) {
          lVar8 = 0;
          do {
            lVar11 = lVar12;
            if (local_d8 <= param_1) break;
            *param_1 = ',';
            if (uVar7 != 1) {
              param_1[1] = '\0';
            }
            param_1 = param_1 + uVar7;
            lVar8 = lVar8 + 1;
            lVar11 = 0;
          } while (lVar8 < 1);
        }
      }
    } while( true );
  }
  lVar13 = 0;
  if ((param_3 >> 0xd & 1) != 0) {
    return local_d0 / uVar14;
  }
  pcVar9 = param_1;
  do {
    if (local_d8 + uVar14 <= pcVar9) break;
    *pcVar9 = '\0';
    if (uVar14 != 1) {
      pcVar9[1] = '\0';
    }
    pcVar9 = pcVar9 + uVar14;
    lVar13 = lVar13 + 1;
  } while (lVar13 < 1);
  return ((longlong)param_1 - (longlong)local_78) / (longlong)uVar14;
LAB_0001ce01:
  if (uVar10 == 0x201) {
    local_d0 = local_d0 + (local_a0 - uVar23) * uVar7;
    if (((uVar22 & 0x2000) == 0) && (param_1 != (char *)0x0)) {
      param_1 = FUN_0001c150(param_1,local_d8,local_a0 - uVar23,0x20,uVar7);
    }
  }
  local_res20 = local_res20 + local_80;
  if (local_80 == 1) {
    iVar5 = 0;
  }
  else {
    iVar5 = (int)(char)local_res20[1] << 8;
  }
  local_a8 = ((longlong)iVar5 | (ulonglong)*local_res20) & local_98;
  puVar17 = local_b0;
  goto LAB_0001ce82;
}


// ==== FUN_0001ceec @ 0001ceec

void FUN_0001ceec(void)

{
  char *in_RCX;
  ulonglong in_RDX;
  ulonglong in_R8;
  byte *in_R9;
  
  FUN_0001c184(in_RCX,in_RDX,in_R8,in_R9,(ulonglong *)&stack0x00000028);
  return;
}


// ==== FUN_0001cf58 @ 0001cf58

longlong FUN_0001cf58(ushort param_1)

{
  int iVar1;
  
  if ((ushort)(param_1 - 0x30) < 10) {
    iVar1 = param_1 - 0x30;
  }
  else {
    if ((ushort)(param_1 - 0x61) < 0x1a) {
      param_1 = param_1 - 0x20;
    }
    iVar1 = param_1 - 0x37;
  }
  return (longlong)iVar1;
}


// ==== FUN_0001cf88 @ 0001cf88

longlong FUN_0001cf88(char *param_1,char *param_2,ulonglong param_3)

{
  if (param_3 == 0) {
    return 0;
  }
  for (; (((*param_1 != '\0' && (*param_2 != '\0')) && (*param_1 == *param_2)) && (1 < param_3));
      param_3 = param_3 - 1) {
    param_1 = param_1 + 1;
    param_2 = param_2 + 1;
  }
  return (longlong)((int)*param_1 - (int)*param_2);
}


// ==== FUN_0001cfbc @ 0001cfbc

ulonglong FUN_0001cfbc(short *param_1,ulonglong param_2)

{
  ulonglong uVar1;
  
  uVar1 = 0;
  if (((param_1 != (short *)0x0) && (param_2 != 0)) && (*param_1 != 0)) {
    do {
      if (param_2 - 1 <= uVar1) {
        return param_2;
      }
      uVar1 = uVar1 + 1;
    } while (param_1[uVar1] != 0);
    return uVar1;
  }
  return 0;
}


// ==== FUN_0001cff0 @ 0001cff0

undefined8 FUN_0001cff0(short *param_1,ulonglong param_2,short *param_3)

{
  short sVar1;
  ulonglong uVar2;
  longlong lVar3;
  
  if (((param_1 == (short *)0x0) || (param_3 == (short *)0x0)) || (1000000 < param_2)) {
    return 0x8000000000000002;
  }
  uVar2 = FUN_0001cfbc(param_3,param_2);
  if (param_2 <= uVar2) {
    return 0x8000000000000005;
  }
  if (param_3 <= param_1) {
    if (param_1 < param_3 + uVar2 + 1) {
      return 0x800000000000000f;
    }
    if (param_3 < param_1) goto LAB_0001d061;
  }
  if (param_3 < param_1 + param_2) {
    return 0x800000000000000f;
  }
LAB_0001d061:
  sVar1 = *param_3;
  if (sVar1 != 0) {
    lVar3 = (longlong)param_3 - (longlong)param_1;
    do {
      *param_1 = sVar1;
      param_1 = param_1 + 1;
      sVar1 = *(short *)(lVar3 + (longlong)param_1);
    } while (sVar1 != 0);
  }
  *param_1 = 0;
  return 0;
}


// ==== FUN_0001d08c @ 0001d08c

undefined8 FUN_0001d08c(short *param_1,ulonglong param_2,short *param_3,ulonglong param_4)

{
  short sVar1;
  ulonglong uVar2;
  longlong lVar3;
  
  if ((((param_1 == (short *)0x0) || (param_3 == (short *)0x0)) || (1000000 < param_2)) ||
     ((1000000 < param_4 || (param_2 == 0)))) {
    return 0x8000000000000002;
  }
  uVar2 = param_4;
  if (param_2 < param_4) {
    uVar2 = param_2;
  }
  uVar2 = FUN_0001cfbc(param_3,uVar2);
  if ((param_2 <= param_4) && (param_2 <= uVar2)) {
    return 0x8000000000000005;
  }
  if (param_4 < uVar2) {
    uVar2 = param_4;
  }
  if (param_3 <= param_1) {
    if (param_1 < param_3 + uVar2 + 1) {
      return 0x800000000000000f;
    }
    if (param_3 < param_1) goto LAB_0001d134;
  }
  if (param_3 < param_1 + param_2) {
    return 0x800000000000000f;
  }
LAB_0001d134:
  if (uVar2 != 0) {
    lVar3 = (longlong)param_3 - (longlong)param_1;
    do {
      sVar1 = *(short *)(lVar3 + (longlong)param_1);
      if (sVar1 == 0) break;
      *param_1 = sVar1;
      param_1 = param_1 + 1;
      uVar2 = uVar2 - 1;
    } while (uVar2 != 0);
  }
  *param_1 = 0;
  return 0;
}


// ==== FUN_0001d16c @ 0001d16c

undefined8 FUN_0001d16c(short *param_1,ulonglong param_2,short *param_3)

{
  ulonglong uVar1;
  ulonglong uVar2;
  short *psVar3;
  ulonglong uVar4;
  
  uVar4 = param_2;
  psVar3 = param_1;
  uVar1 = FUN_0001cfbc(param_1,param_2);
  uVar4 = uVar4 - uVar1;
  if ((((param_1 == (short *)0x0) || (param_3 == (short *)0x0)) || (1000000 < param_2)) ||
     (param_2 == 0)) {
    return 0x8000000000000002;
  }
  if (uVar4 == 0) {
    return 0x8000000000000004;
  }
  uVar2 = FUN_0001cfbc(param_3,uVar4);
  if (uVar4 <= uVar2) {
    return 0x8000000000000005;
  }
  if (param_3 <= psVar3) {
    if (psVar3 < param_3 + uVar2 + 1) {
      return 0x800000000000000f;
    }
    if (param_3 < psVar3) goto LAB_0001d20d;
  }
  if (param_3 < psVar3 + param_2) {
    return 0x800000000000000f;
  }
LAB_0001d20d:
  psVar3 = psVar3 + uVar1;
  for (; *param_3 != 0; param_3 = param_3 + 1) {
    *psVar3 = *param_3;
    psVar3 = psVar3 + 1;
  }
  *psVar3 = 0;
  return 0;
}


// ==== FUN_0001d23c @ 0001d23c

undefined8 FUN_0001d23c(undefined8 param_1,undefined8 *param_2)

{
  ushort uVar1;
  ushort uVar2;
  undefined8 uVar3;
  longlong lVar4;
  longlong lVar5;
  ulonglong uVar6;
  ushort local_18;
  ushort uStack_16;
  ushort uStack_14;
  ushort uStack_12;
  undefined8 local_10;
  
  lVar5 = DAT_000292b8;
  if ((DAT_000292b8 == 0) || (param_2 == (undefined8 *)0x0)) {
    uVar3 = 0x8000000000000002;
  }
  else {
    lVar4 = FUN_0001d374(DAT_000292b8,8,(longlong)&local_18,4);
    if ((-1 < lVar4) && (*(short *)(lVar5 + 0x10) == 0x2d)) {
      uVar6 = 2;
      uVar1 = uStack_16 << 8;
      uVar2 = uStack_16 >> 8;
      uStack_16 = local_18 << 8 | local_18 >> 8;
      local_18 = uVar1 | uVar2;
      lVar4 = FUN_0001d374(lVar5 + 0x12,4,(longlong)&uStack_14,2);
      if ((-1 < lVar4) && (*(short *)(lVar5 + 0x1a) == 0x2d)) {
        uStack_14 = uStack_14 << 8 | uStack_14 >> 8;
        lVar4 = FUN_0001d374(lVar5 + 0x1c,4,(longlong)&uStack_12,uVar6);
        if ((-1 < lVar4) && (*(short *)(lVar5 + 0x24) == 0x2d)) {
          uStack_12 = uStack_12 << 8 | uStack_12 >> 8;
          lVar4 = FUN_0001d374(lVar5 + 0x26,4,(longlong)&local_10,uVar6);
          if ((-1 < lVar4) &&
             ((*(short *)(lVar5 + 0x2e) == 0x2d &&
              (lVar5 = FUN_0001d374(lVar5 + 0x30,0xc,(longlong)&local_10 + 2,6), -1 < lVar5)))) {
            *param_2 = CONCAT26(uStack_12,CONCAT24(uStack_14,CONCAT22(uStack_16,local_18)));
            param_2[1] = local_10;
            return 0;
          }
        }
      }
    }
    uVar3 = 0x8000000000000003;
  }
  return uVar3;
}


// ==== FUN_0001d374 @ 0001d374

undefined8 FUN_0001d374(longlong param_1,ulonglong param_2,longlong param_3,ulonglong param_4)

{
  short sVar1;
  ushort uVar2;
  undefined8 uVar3;
  longlong lVar4;
  ulonglong uVar5;
  ulonglong uVar6;
  
  uVar6 = 0;
  if ((((param_1 == 0) || (param_3 == 0)) || (1000000 < param_2)) || ((param_2 & 1) != 0)) {
    uVar3 = 0x8000000000000002;
  }
  else if (param_4 < param_2 >> 1) {
    uVar3 = 0x8000000000000005;
  }
  else {
    uVar5 = uVar6;
    if (param_2 != 0) {
      do {
        sVar1 = *(short *)(param_1 + uVar5 * 2);
        if (((9 < (ushort)(sVar1 - 0x30U)) && (5 < (ushort)(sVar1 - 0x41U))) &&
           (5 < (ushort)(sVar1 - 0x61U))) break;
        uVar5 = uVar5 + 1;
      } while (uVar5 < param_2);
    }
    if (uVar5 == param_2) {
      if (param_2 != 0) {
        do {
          uVar2 = *(ushort *)(param_1 + uVar6 * 2);
          if ((uVar6 & 1) == 0) {
            lVar4 = FUN_0001cf58(uVar2);
            *(char *)((uVar6 >> 1) + param_3) = (char)lVar4 << 4;
          }
          else {
            uVar5 = uVar6 >> 1;
            lVar4 = FUN_0001cf58(uVar2);
            *(byte *)(uVar5 + param_3) = *(byte *)(uVar5 + param_3) | (byte)lVar4;
          }
          uVar6 = uVar6 + 1;
        } while (uVar6 < param_2);
      }
      uVar3 = 0;
    }
    else {
      uVar3 = 0x8000000000000003;
    }
  }
  return uVar3;
}


// ==== FUN_0001d454 @ 0001d454

ulonglong FUN_0001d454(char *param_1)

{
  ulonglong uVar1;
  
  uVar1 = 0;
  if ((param_1 != (char *)0x0) && (*param_1 != '\0')) {
    while (uVar1 < 1000000) {
      uVar1 = uVar1 + 1;
      if (param_1[uVar1] == '\0') {
        return uVar1;
      }
    }
    uVar1 = 0xf4241;
  }
  return uVar1;
}


// ==== FUN_0001d478 @ 0001d478

char * FUN_0001d478(char *param_1)

{
  bool bVar1;
  char *pcVar2;
  char *pcVar3;
  
  pcVar3 = (char *)0x0;
  if (param_1 != (char *)0x0) {
    bVar1 = FUN_0001d694(param_1);
    pcVar2 = param_1;
    if (bVar1) {
      for (; (*pcVar2 != '\x7f' || (pcVar2[1] != -1)); pcVar2 = pcVar2 + *(ushort *)(pcVar2 + 2)) {
      }
      pcVar3 = pcVar2 + ((ulonglong)*(ushort *)(pcVar2 + 2) - (longlong)param_1);
    }
  }
  return pcVar3;
}


// ==== FUN_0001d4c8 @ 0001d4c8

char * FUN_0001d4c8(char *param_1,char *param_2)

{
  bool bVar1;
  char *pcVar2;
  char *pcVar3;
  char *pcVar4;
  
  pcVar3 = (char *)0x0;
  if (param_1 == (char *)0x0) {
    param_1 = &DAT_00028980;
    if (param_2 != (char *)0x0) {
      param_1 = param_2;
    }
  }
  else if (param_2 != (char *)0x0) {
    bVar1 = FUN_0001d694(param_1);
    if (!bVar1) {
      return (char *)0x0;
    }
    bVar1 = FUN_0001d694(param_2);
    if (!bVar1) {
      return (char *)0x0;
    }
    pcVar4 = FUN_0001d478(param_1);
    pcVar3 = param_2;
    pcVar2 = FUN_0001d478(param_2);
    pcVar3 = (char *)FUN_0001b514(pcVar3,pcVar2 + -4 + (longlong)pcVar4);
    if (pcVar3 == (char *)0x0) {
      return (char *)0x0;
    }
    if ((pcVar4 != (char *)0x0) && (pcVar3 != param_1)) {
      pcVar3 = (char *)FUN_000002e0((undefined8 *)pcVar3,(undefined8 *)param_1,(ulonglong)pcVar4);
    }
    if (pcVar2 == (char *)0x0) {
      return pcVar3;
    }
    if (pcVar4 + -4 + (longlong)pcVar3 == param_2) {
      return pcVar3;
    }
    FUN_000002e0((undefined8 *)(pcVar4 + -4 + (longlong)pcVar3),(undefined8 *)param_2,
                 (ulonglong)pcVar2);
    return pcVar3;
  }
  pcVar4 = param_1;
  pcVar2 = FUN_0001d478(param_1);
  if (pcVar2 != (char *)0x0) {
    pcVar3 = (char *)FUN_0001b570(pcVar4,(ulonglong)pcVar2,(undefined8 *)param_1);
  }
  return pcVar3;
}


// ==== FUN_0001d5b8 @ 0001d5b8

char * FUN_0001d5b8(char *param_1,char *param_2)

{
  ushort uVar1;
  char *pcVar2;
  char *pcVar3;
  char *pcVar4;
  char *pcVar5;
  
  pcVar3 = (char *)0x0;
  if (param_2 == (char *)0x0) {
    pcVar4 = &DAT_00028980;
    if (param_1 != (char *)0x0) {
      pcVar4 = param_1;
    }
    pcVar5 = pcVar4;
    pcVar2 = FUN_0001d478(pcVar4);
    if (pcVar2 != (char *)0x0) {
      pcVar3 = (char *)FUN_0001b570(pcVar5,(ulonglong)pcVar2,(undefined8 *)pcVar4);
    }
  }
  else {
    uVar1 = *(ushort *)(param_2 + 2);
    pcVar4 = (char *)FUN_0001b514(param_1,(ulonglong)uVar1 + 4);
    if (pcVar4 != (char *)0x0) {
      if (((ulonglong)uVar1 != 0) && (pcVar4 != param_2)) {
        pcVar4 = (char *)FUN_000002e0((undefined8 *)pcVar4,(undefined8 *)param_2,(ulonglong)uVar1);
      }
      if (pcVar4 + *(ushort *)(pcVar4 + 2) != &DAT_00028980) {
        FUN_000002e0((undefined8 *)(pcVar4 + *(ushort *)(pcVar4 + 2)),(undefined8 *)&DAT_00028980,4)
        ;
      }
      pcVar3 = FUN_0001d4c8(param_1,pcVar4);
      (**(code **)(DAT_00029478 + 0x48))(pcVar4);
    }
  }
  return pcVar3;
}


// ==== FUN_0001d694 @ 0001d694

bool FUN_0001d694(char *param_1)

{
  ulonglong uVar1;
  ulonglong uVar2;
  
  uVar2 = 0;
  if (param_1 != (char *)0x0) {
    while( true ) {
      if ((*param_1 == '\x7f') && (param_1[1] == -1)) {
        return *(short *)(param_1 + 2) == 4;
      }
      uVar1 = (ulonglong)*(ushort *)(param_1 + 2);
      if ((((uVar1 < 4) || (~uVar2 < uVar1)) || (uVar2 = uVar2 + uVar1, 0xfffffffffffffffb < uVar2))
         || (((*param_1 == '\x04' && (param_1[1] == '\x04')) &&
             (*(short *)(param_1 + (uVar1 - 2)) != 0)))) break;
      param_1 = param_1 + uVar1;
    }
  }
  return false;
}


// ==== FUN_0001d748 @ 0001d748

undefined8 FUN_0001d748(undefined8 param_1)

{
  undefined8 local_res10 [3];
  
  local_res10[0] = 0;
  (**(code **)(DAT_00029498 + 0x40))(4,param_1,local_res10);
  return local_res10[0];
}


// ==== FUN_0001d774 @ 0001d774

longlong FUN_0001d774(undefined8 param_1)

{
  longlong lVar1;
  
  lVar1 = FUN_0001d748(param_1);
  if (lVar1 != 0) {
    (**(code **)(DAT_00029498 + 0x168))(lVar1,param_1,0);
  }
  return lVar1;
}


// ==== FUN_0001d7b4 @ 0001d7b4

longlong FUN_0001d7b4(char *param_1)

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


// ==== FUN_0001d808 @ 0001d808

longlong FUN_0001d808(undefined8 param_1,undefined8 param_2,undefined8 param_3,undefined8 *param_4,
                     longlong *param_5)

{
  longlong lVar1;
  
  if (*param_5 == 0) {
    *param_4 = 0;
  }
  lVar1 = (**(code **)(DAT_000294a0 + 0x48))();
  if ((lVar1 < 0) && (lVar1 == -0x7ffffffffffffffb)) {
    if (*param_5 != 0) {
      (**(code **)(DAT_00029498 + 0x48))();
    }
    lVar1 = FUN_0001d748(*param_4);
    *param_5 = lVar1;
    if (lVar1 == 0) {
      lVar1 = -0x7ffffffffffffff7;
    }
    else {
      lVar1 = (**(code **)(DAT_000294a0 + 0x48))(param_1,param_2,param_3,param_4,lVar1);
    }
  }
  return lVar1;
}


// ==== FUN_0001d8c8 @ 0001d8c8

void FUN_0001d8c8(undefined8 param_1,undefined8 param_2,undefined8 param_3,undefined8 *param_4,
                 undefined8 param_5)

{
  longlong lVar1;
  
  lVar1 = (**(code **)(DAT_00029498 + 0x50))(0x200,8,param_2,0,param_4);
  if (-1 < lVar1) {
    (**(code **)(DAT_00029498 + 0xa8))(param_1,*param_4,param_5);
  }
  return;
}


// ==== FUN_0001d920 @ 0001d920

char * FUN_0001d920(ulonglong param_1,char *param_2,int param_3,char param_4)

{
  undefined1 auVar1 [16];
  undefined1 auVar2 [16];
  ulonglong uVar3;
  char cVar4;
  
  uVar3 = param_1 & 0xffffffff;
  if (param_4 != '\0') {
    uVar3 = param_1;
  }
  if (param_3 == 10) {
    uVar3 = -param_1;
  }
  if (-1 < (longlong)param_1) {
    uVar3 = param_1;
  }
  if (uVar3 == 0) {
    *param_2 = '0';
    param_2 = param_2 + 1;
  }
  else {
    do {
      auVar1._8_8_ = 0;
      auVar1._0_8_ = (longlong)param_3;
      auVar2._8_8_ = 0;
      auVar2._0_8_ = uVar3;
      uVar3 = uVar3 / (ulonglong)(longlong)param_3;
      cVar4 = SUB161(auVar2 % auVar1,0);
      if (SUB168(auVar2 % auVar1,0) < 10) {
        cVar4 = cVar4 + '0';
      }
      else {
        cVar4 = cVar4 + 'W';
      }
      *param_2 = cVar4;
      param_2 = param_2 + 1;
    } while (uVar3 != 0);
  }
  if ((param_3 == 10) && ((longlong)param_1 < 0)) {
    *param_2 = '-';
    param_2 = param_2 + 1;
  }
  *param_2 = '\0';
  return param_2 + -1;
}


// ==== FUN_0001d994 @ 0001d994

short * FUN_0001d994(ulonglong param_1,short *param_2,int param_3,char param_4)

{
  char *pcVar1;
  short *psVar2;
  char local_108 [256];
  
  pcVar1 = FUN_0001d920(param_1,local_108,param_3,param_4);
  psVar2 = param_2;
  for (; local_108 <= pcVar1; pcVar1 = pcVar1 + -1) {
    *psVar2 = (short)*pcVar1;
    psVar2 = psVar2 + 1;
  }
  *psVar2 = 0;
  return param_2;
}


// ==== FUN_0001d9e4 @ 0001d9e4

int FUN_0001d9e4(byte *param_1,undefined8 *param_2,undefined8 param_3,int param_4)

{
  byte bVar1;
  bool bVar2;
  bool bVar3;
  char cVar4;
  uint uVar5;
  char cVar6;
  
  bVar3 = false;
  bVar2 = false;
  uVar5 = 0;
  cVar6 = '\x01';
  for (; (*param_1 == 0x20 || (*param_1 == 9)); param_1 = param_1 + param_4) {
  }
  if (*param_1 == 0) {
    *param_2 = param_1;
    return 0;
  }
  if (*param_1 == 0x2d) {
    cVar6 = -1;
    param_1 = param_1 + param_4;
  }
  if (*param_1 != 0x2b) goto LAB_0001da3b;
  do {
    param_1 = param_1 + param_4;
LAB_0001da3b:
    bVar1 = *param_1;
    if ((byte)(bVar1 - 0x30) < 10) {
      cVar4 = bVar1 - 0x30;
    }
    else {
      if (0x19 < (byte)((bVar1 & 0xdf) + 0xbf)) {
LAB_0001da8f:
        *param_2 = param_1;
        if ((bVar2) && (uVar5 = 0x7fffffff, cVar6 == -1)) {
          uVar5 = 0x80000000;
        }
        return (int)cVar6 * uVar5;
      }
      cVar4 = (bVar1 & 0xdf) - 0x37;
    }
    if (9 < cVar4) goto LAB_0001da8f;
    uVar5 = (int)cVar4 + uVar5 * 10;
    if (cVar6 == '\x01') {
      if (0x7fffffff < uVar5) {
        bVar2 = true;
        bVar3 = true;
      }
    }
    else {
      bVar2 = bVar3;
      if (0x80000000 < uVar5) {
        bVar2 = true;
        bVar3 = bVar2;
      }
    }
  } while( true );
}


// ==== _wcsupr @ 0001dac4

/* Library Function - Single Match
    _wcsupr
   
   Library: Visual Studio 2019 Release */

wchar_t * __cdecl _wcsupr(wchar_t *_Str)

{
  wchar_t wVar1;
  wchar_t *pwVar2;
  
  wVar1 = *_Str;
  pwVar2 = _Str;
  while (wVar1 != L'\0') {
    if ((ushort)(*pwVar2 + L'ﾟ') < 0x1a) {
      *pwVar2 = *pwVar2 + L'￠';
    }
    pwVar2 = pwVar2 + 1;
    wVar1 = *pwVar2;
  }
  return _Str;
}


// ==== FUN_0001daf4 @ 0001daf4

void FUN_0001daf4(byte *param_1,char *param_2,undefined8 param_3,undefined8 param_4)

{
  undefined8 local_res18;
  undefined8 local_res20;
  
  local_res18 = param_3;
  local_res20 = param_4;
  FUN_0001dbe4(param_1,0,param_2,(longlong)&local_res18);
  return;
}


// ==== FUN_0001db1c @ 0001db1c

char * FUN_0001db1c(ulonglong param_1)

{
  char *pcVar1;
  char *pcVar2;
  ulonglong uVar3;
  
  if (param_1 == 0) {
    return s_EFI_SUCCESS_00028998;
  }
  if ((longlong)param_1 < 0) {
    uVar3 = param_1 & 0x1fffffffffffffff;
    if ((param_1 & 0xa000000000000000) == 0xa000000000000000) {
      if (2 < uVar3) {
        return (char *)0x0;
      }
      pcVar1 = (char *)(uVar3 * 0x19);
      pcVar2 = s_EFI_INTERRUPT_PENDING_00024ee0;
      goto LAB_0001dbdf;
    }
    if ((param_1 & 0xc000000000000000) == 0xc000000000000000) {
      if (2 < uVar3) {
        return (char *)0x0;
      }
      pcVar1 = s_EFI_NOT_AVAILABLE_YET_00024f12 + uVar3 * 0x19 + 0x15;
    }
    else {
      if (0x1e < uVar3) {
        return (char *)0x0;
      }
      pcVar1 = s_EFI_DBE_BOF_00024f59 + uVar3 * 0x19 + 0xe;
    }
  }
  else {
    if ((param_1 & 0x2000000000000000) != 0) {
      if (1 < param_1) {
        return (char *)0x0;
      }
      pcVar1 = (char *)(param_1 * 0x23);
      pcVar2 = s_EFI_WARN_INTERRUPT_SOURCE_PENDIN_00024e90;
      goto LAB_0001dbdf;
    }
    if (4 < param_1) {
      return (char *)0x0;
    }
    pcVar1 = (char *)(param_1 * 0x1a + 0x24e06);
  }
  pcVar2 = (char *)0x0;
LAB_0001dbdf:
  return pcVar1 + (longlong)pcVar2;
}


// ==== FUN_0001dbe4 @ 0001dbe4

longlong FUN_0001dbe4(byte *param_1,longlong param_2,char *param_3,longlong param_4)

{
  byte bVar1;
  uint uVar2;
  char *pcVar3;
  ulonglong uVar4;
  byte *pbVar5;
  byte bVar6;
  int iVar7;
  byte *pbVar8;
  byte *pbVar9;
  longlong lVar10;
  uint *local_res18;
  byte *local_68;
  byte *local_60;
  byte local_58 [32];
  
  if ((param_1 == (byte *)0x0) || (param_3 == (char *)0x0)) {
    lVar10 = -1;
  }
  else {
    pbVar9 = param_1;
    if (param_2 != 1) {
      local_res18 = (uint *)(param_4 + -8);
      pbVar5 = (byte *)param_3;
      do {
        bVar6 = *pbVar5;
        if (bVar6 == 0) break;
        pbVar8 = pbVar5 + 1;
        if (bVar6 == 0x25) {
          if (*pbVar8 == 0x25) {
            pbVar8 = pbVar5 + 2;
            *pbVar9 = 0x25;
            goto LAB_0001dc50;
          }
          bVar6 = 0x20;
          if (*pbVar8 == 0x30) {
            bVar6 = 0x30;
            pbVar8 = pbVar5 + 2;
          }
          if (*pbVar8 == 0x2a) {
            local_res18 = local_res18 + 2;
            uVar2 = *local_res18;
            pbVar8 = pbVar8 + 1;
          }
          else {
            uVar2 = FUN_0001d9e4(pbVar8,&local_68,param_3,1);
            pbVar8 = local_68;
          }
          if ((*pbVar8 == 0x73) || (*pbVar8 == 0x61)) {
            for (pbVar5 = *(byte **)(local_res18 + 2); *pbVar5 != 0; pbVar5 = pbVar5 + 1) {
              param_2 = param_2 + -1;
              if (param_2 == 0) goto LAB_0001df97;
              *pbVar9 = *pbVar5;
              pbVar9 = pbVar9 + 1;
            }
LAB_0001df86:
            local_res18 = local_res18 + 2;
            pbVar8 = pbVar8 + 1;
          }
          else {
            if (*pbVar8 == 0x53) {
              for (pbVar5 = *(byte **)(local_res18 + 2); *(short *)pbVar5 != 0; pbVar5 = pbVar5 + 2)
              {
                param_2 = param_2 + -1;
                if (param_2 == 0) goto LAB_0001df97;
                *pbVar9 = *pbVar5;
                pbVar9 = pbVar9 + 1;
              }
              goto LAB_0001df86;
            }
            if (*pbVar8 == 99) {
              *pbVar9 = (byte)local_res18[2];
              pbVar9 = pbVar9 + 1;
              goto LAB_0001df86;
            }
            if ((*pbVar8 & 0xdf) == 0x47) {
              local_60 = pbVar9;
              param_3 = (char *)FUN_0001dfd0();
              pbVar9 = pbVar9 + (longlong)param_3;
              pbVar5 = local_60;
              if (*pbVar8 == 0x47) {
                for (; *pbVar5 != 0; pbVar5 = pbVar5 + 1) {
                  if ((byte)(*pbVar5 + 0x9f) < 0x1a) {
                    *pbVar5 = *pbVar5 - 0x20;
                  }
                }
              }
              param_2 = param_2 - (longlong)param_3;
              goto LAB_0001df86;
            }
            if (*pbVar8 == 0x72) {
              pcVar3 = FUN_0001db1c(*(ulonglong *)(local_res18 + 2));
              if (pcVar3 == (char *)0x0) {
                param_3 = s__s__X__000289a4;
                lVar10 = FUN_0001dfd0();
              }
              else {
                param_3 = &DAT_000289ac;
                lVar10 = FUN_0001dfd0();
              }
              pbVar9 = pbVar9 + lVar10;
              param_2 = param_2 - lVar10;
              goto LAB_0001df86;
            }
            bVar1 = *pbVar8;
            if (bVar1 == 0x6c) {
              pbVar8 = pbVar8 + 1;
            }
            if ((*pbVar8 == 100) || (*pbVar8 == 0x69)) {
              iVar7 = 10;
LAB_0001de7e:
              pbVar5 = local_58;
              if (*pbVar8 != 0x70 && bVar1 != 0x6c) {
                param_3 = FUN_0001d920((longlong)(int)*(ulonglong *)(local_res18 + 2),
                                       (char *)local_58,iVar7,'\0');
                if (local_58 < param_3) {
                  do {
                    bVar1 = *pbVar5;
                    *pbVar5 = *param_3;
                    pbVar5 = pbVar5 + 1;
                    *param_3 = bVar1;
                    param_3 = param_3 + -1;
                  } while (pbVar5 < param_3);
                }
              }
              else {
                param_3 = FUN_0001d920(*(ulonglong *)(local_res18 + 2),(char *)local_58,iVar7,'\x01'
                                      );
                if (local_58 < param_3) {
                  do {
                    bVar1 = *pbVar5;
                    *pbVar5 = *param_3;
                    pbVar5 = pbVar5 + 1;
                    *param_3 = bVar1;
                    param_3 = param_3 + -1;
                  } while (pbVar5 < param_3);
                }
              }
              if ((*pbVar8 == 0x58) || (*pbVar8 == 0x70)) {
                pbVar5 = local_58;
                bVar1 = local_58[0];
                while (bVar1 != 0) {
                  if ((byte)(*pbVar5 + 0x9f) < 0x1a) {
                    *pbVar5 = *pbVar5 - 0x20;
                  }
                  pbVar5 = pbVar5 + 1;
                  bVar1 = *pbVar5;
                }
              }
              uVar4 = 0;
              bVar1 = local_58[0];
              while (bVar1 != 0) {
                bVar1 = local_58[uVar4 + 1];
                uVar4 = uVar4 + 1;
              }
              while (uVar4 < uVar2) {
                uVar4 = uVar4 + 1;
                param_2 = param_2 + -1;
                if (param_2 == 0) goto LAB_0001df97;
                *pbVar9 = bVar6;
                pbVar9 = pbVar9 + 1;
              }
              pbVar5 = local_58;
              bVar6 = local_58[0];
              while (bVar6 != 0) {
                param_2 = param_2 + -1;
                if (param_2 == 0) {
LAB_0001df97:
                  *pbVar9 = 0;
                  return (longlong)pbVar9 - (longlong)param_1;
                }
                bVar6 = *pbVar5;
                pbVar5 = pbVar5 + 1;
                *pbVar9 = bVar6;
                pbVar9 = pbVar9 + 1;
                bVar6 = *pbVar5;
              }
              goto LAB_0001df86;
            }
            if (((*pbVar8 & 0xdf) == 0x58) || (*pbVar8 == 0x70)) {
              iVar7 = 0x10;
              goto LAB_0001de7e;
            }
          }
        }
        else {
          *pbVar9 = bVar6;
LAB_0001dc50:
          pbVar9 = pbVar9 + 1;
          param_2 = param_2 + -1;
        }
        pbVar5 = pbVar8;
      } while (param_2 != 1);
    }
    *pbVar9 = 0;
    lVar10 = (longlong)pbVar9 - (longlong)param_1;
  }
  return lVar10;
}


// ==== FUN_0001dfd0 @ 0001dfd0

void FUN_0001dfd0(void)

{
  byte *in_RCX;
  longlong in_RDX;
  char *in_R8;
  undefined1 local_res20 [8];
  
  FUN_0001dbe4(in_RCX,in_RDX,in_R8,(longlong)local_res20);
  return;
}


// ==== FUN_0001dff0 @ 0001dff0

void FUN_0001dff0(wchar_t *param_1,wchar_t *param_2,undefined8 param_3,undefined8 param_4)

{
  undefined8 local_res18;
  undefined8 local_res20;
  
  local_res18 = param_3;
  local_res20 = param_4;
  FUN_0001e018(param_1,0,param_2,(longlong)&local_res18);
  return;
}


// ==== FUN_0001e018 @ 0001e018

longlong FUN_0001e018(wchar_t *param_1,longlong param_2,wchar_t *param_3,longlong param_4)

{
  wchar_t wVar1;
  uint uVar2;
  wchar_t *pwVar3;
  char *pcVar4;
  ulonglong uVar5;
  ulonglong uVar6;
  wchar_t wVar7;
  uint *puVar8;
  wchar_t *_Str;
  longlong lVar9;
  wchar_t *pwVar10;
  bool bVar11;
  wchar_t *local_res18 [2];
  wchar_t local_78 [32];
  
  if ((param_1 == (wchar_t *)0x0) || (param_3 == (wchar_t *)0x0)) {
    lVar9 = -1;
  }
  else {
    _Str = param_1;
    if (param_2 != 1) {
      puVar8 = (uint *)(param_4 + -8);
      pwVar3 = param_3;
      do {
        uVar5 = 0;
        wVar7 = *pwVar3;
        if (wVar7 == L'\0') break;
        pwVar10 = pwVar3 + 1;
        if (wVar7 == L'%') {
          if (*pwVar10 == L'%') {
            pwVar10 = pwVar3 + 2;
            *_Str = L'%';
            goto LAB_0001e086;
          }
          wVar7 = L' ';
          if (*pwVar10 == L'0') {
            pwVar10 = pwVar3 + 2;
            wVar7 = L'0';
          }
          if (*pwVar10 == L'*') {
            puVar8 = puVar8 + 2;
            uVar2 = *puVar8;
            pwVar10 = pwVar10 + 1;
          }
          else {
            uVar2 = FUN_0001d9e4((byte *)pwVar10,local_res18,param_3,2);
            pwVar10 = local_res18[0];
          }
          if (*pwVar10 == L's') {
            for (pwVar3 = *(wchar_t **)(puVar8 + 2); *pwVar3 != L'\0'; pwVar3 = pwVar3 + 1) {
              param_2 = param_2 + -1;
              if (param_2 == 0) goto LAB_0001e381;
              *_Str = *pwVar3;
              _Str = _Str + 1;
            }
LAB_0001e363:
            puVar8 = puVar8 + 2;
            pwVar10 = pwVar10 + 1;
          }
          else {
            if ((*pwVar10 == L'S') || (*pwVar10 == L'a')) {
              for (pcVar4 = *(char **)(puVar8 + 2); *pcVar4 != '\0'; pcVar4 = pcVar4 + 1) {
                param_2 = param_2 + -1;
                if (param_2 == 0) goto LAB_0001e381;
                *_Str = (short)*pcVar4;
                _Str = _Str + 1;
              }
              goto LAB_0001e363;
            }
            if (*pwVar10 == L'c') {
              *_Str = *(wchar_t *)(puVar8 + 2);
              _Str = _Str + 1;
              goto LAB_0001e363;
            }
            if ((*pwVar10 & L'ß') != L'G') {
              if (*pwVar10 == L'r') {
                pcVar4 = FUN_0001db1c(*(ulonglong *)(puVar8 + 2));
                if (pcVar4 == (char *)0x0) {
                  param_3 = u__S__X__00028a18;
                  lVar9 = FUN_0001e3b4(_Str,param_2,u__S__X__00028a18,s_Status_Code_00024f30);
                }
                else {
                  param_3 = (wchar_t *)&DAT_00027990;
                  lVar9 = FUN_0001e3b4(_Str,param_2,(wchar_t *)&DAT_00027990,pcVar4);
                }
                _Str = _Str + lVar9;
                param_2 = param_2 - lVar9;
              }
              else {
                bVar11 = *pwVar10 != L'l';
                if (!bVar11) {
                  pwVar10 = pwVar10 + 1;
                }
                wVar1 = *pwVar10;
                if ((wVar1 == L'd') || (wVar1 == L'i')) {
                  param_3 = (wchar_t *)&IMAGE_DOS_HEADER_00000000.e_minalloc;
                }
                else {
                  if (((byte)wVar1 & 0xdf) != 0x58) goto LAB_0001e366;
                  param_3 = (wchar_t *)&IMAGE_DOS_HEADER_00000000.e_sp;
                }
                if (wVar1 != L'p' && bVar11) {
                  uVar6 = (ulonglong)(int)*(ulonglong *)(puVar8 + 2);
                }
                else {
                  uVar6 = *(ulonglong *)(puVar8 + 2);
                }
                FUN_0001d994(uVar6,local_78,(int)param_3,wVar1 == L'p' || !bVar11);
                if ((*pwVar10 == L'X') || (*pwVar10 == L'p')) {
                  _wcsupr(local_78);
                }
                pwVar3 = local_78;
                wVar1 = local_78[0];
                while (wVar1 != L'\0') {
                  pwVar3 = pwVar3 + 1;
                  uVar5 = uVar5 + 1;
                  wVar1 = *pwVar3;
                }
                while (uVar5 < uVar2) {
                  uVar5 = uVar5 + 1;
                  param_2 = param_2 + -1;
                  if (param_2 == 0) goto LAB_0001e381;
                  *_Str = wVar7;
                  _Str = _Str + 1;
                }
                pwVar3 = local_78;
                wVar7 = local_78[0];
                while (wVar7 != L'\0') {
                  param_2 = param_2 + -1;
                  if (param_2 == 0) goto LAB_0001e381;
                  wVar7 = *pwVar3;
                  pwVar3 = pwVar3 + 1;
                  *_Str = wVar7;
                  _Str = _Str + 1;
                  wVar7 = *pwVar3;
                }
              }
              goto LAB_0001e363;
            }
            puVar8 = puVar8 + 2;
            param_3 = u__08x__04x__04x__02x_02x__02x_02x_000289b0;
            lVar9 = FUN_0001e3b4(_Str,param_2,u__08x__04x__04x__02x_02x__02x_02x_000289b0,
                                 (ulonglong)**(uint **)puVar8);
            pwVar3 = _Str + lVar9;
            if (*pwVar10 == L'G') {
              _wcsupr(_Str);
            }
            param_2 = param_2 - lVar9;
            pwVar10 = pwVar10 + 1;
            _Str = pwVar3;
          }
        }
        else {
          *_Str = wVar7;
LAB_0001e086:
          param_2 = param_2 + -1;
          _Str = _Str + 1;
        }
LAB_0001e366:
        pwVar3 = pwVar10;
      } while (param_2 != 1);
    }
    *_Str = L'\0';
    lVar9 = (longlong)_Str - (longlong)param_1;
LAB_0001e38d:
    lVar9 = lVar9 >> 1;
  }
  return lVar9;
LAB_0001e381:
  *_Str = L'\0';
  lVar9 = (longlong)_Str - (longlong)param_1;
  goto LAB_0001e38d;
}


// ==== FUN_0001e3b4 @ 0001e3b4

void FUN_0001e3b4(wchar_t *param_1,longlong param_2,wchar_t *param_3,undefined8 param_4)

{
  undefined8 local_res20;
  
  local_res20 = param_4;
  FUN_0001e018(param_1,param_2,param_3,(longlong)&local_res20);
  return;
}


// ==== FUN_0001e3d4 @ 0001e3d4

char * FUN_0001e3d4(void)

{
  longlong lVar1;
  char *pcVar2;
  undefined8 local_res10 [3];
  
  local_res10[0] = 0;
  if (DAT_000294c0 == s_en_US_00025c24) {
    DAT_000294c0 = (char *)0x0;
  }
  lVar1 = FUN_0001d808(u_PlatformLang_00025c88,&DAT_000252c0,0,local_res10,(longlong *)&DAT_000294c0
                      );
  pcVar2 = s_en_US_00025c24;
  if (-1 < lVar1) {
    pcVar2 = DAT_000294c0;
  }
  DAT_000294c0 = pcVar2;
  return pcVar2;
}


// ==== FUN_0001e448 @ 0001e448

void FUN_0001e448(short *param_1,undefined8 param_2)

{
  short *psVar1;
  longlong lVar2;
  longlong lVar3;
  longlong lVar4;
  short sVar5;
  undefined8 *local_res8;
  
  lVar3 = 0;
  (**(code **)(DAT_00029498 + 0x40))(4,param_2,&local_res8);
  sVar5 = *param_1;
  psVar1 = param_1;
  lVar4 = lVar3;
  while (sVar5 != 0) {
    if ((sVar5 == 0x26) &&
       (lVar2 = FUN_0001edd4((longlong *)(psVar1 + 1),(longlong *)PTR_u_VALUE__00028a40,0xc),
       lVar2 == 0)) {
      do {
        lVar3 = lVar3 + 1;
        if (param_1[lVar3] == 0x26) break;
      } while (param_1[lVar3] != 0);
      sVar5 = param_1[lVar3];
      if (sVar5 == 0) break;
    }
    lVar3 = lVar3 + 1;
    *(short *)((longlong)local_res8 + lVar4 * 2) = sVar5;
    psVar1 = param_1 + lVar3;
    lVar4 = lVar4 + 1;
    sVar5 = *psVar1;
  }
  *(undefined2 *)((longlong)local_res8 + lVar4 * 2) = 0;
  FUN_000233d0((undefined8 *)param_1,local_res8,lVar4 * 2 + 2);
  (**(code **)(DAT_00029498 + 0x48))(local_res8);
  return;
}


// ==== FUN_0001e520 @ 0001e520

undefined8 * FUN_0001e520(char *param_1,char *param_2,undefined8 param_3,undefined8 param_4)

{
  bool bVar1;
  char cVar2;
  char *pcVar3;
  undefined8 *puVar4;
  char *pcVar5;
  char *pcVar6;
  char *pcVar7;
  ulonglong uVar8;
  char *pcVar9;
  char *pcVar10;
  char **ppcVar11;
  char *local_res10;
  char *local_res18 [2];
  
  local_res18[0] = (char *)param_3;
  local_res18[1] = (char *)param_4;
  pcVar7 = (char *)0x0;
  if ((param_1 != (char *)0x0) && (param_2 != (char *)0x0)) {
    ppcVar11 = &local_res10;
    pcVar6 = param_2;
    do {
      pcVar9 = (char *)0x0;
      pcVar3 = param_1;
      do {
        bVar1 = false;
        pcVar5 = pcVar3;
        pcVar10 = pcVar6;
        if (*pcVar6 != '\0') {
          cVar2 = *pcVar6;
          do {
            if (cVar2 == ';') break;
            if (cVar2 == '-') {
              bVar1 = true;
            }
            if (cVar2 != *pcVar5) break;
            if (*pcVar5 == '\0') goto LAB_0001e5ac;
            if (*pcVar5 == ';') break;
            pcVar10 = pcVar10 + 1;
            pcVar5 = pcVar5 + 1;
            cVar2 = *pcVar10;
          } while (cVar2 != '\0');
        }
        for (; (*pcVar5 != '\0' && (*pcVar5 != ';')); pcVar5 = pcVar5 + 1) {
        }
LAB_0001e5ac:
        if ((((bVar1) || (*pcVar10 == '\0')) || (*pcVar10 == ';')) &&
           (pcVar10 != pcVar6 && -1 < (longlong)pcVar10 - (longlong)pcVar6)) {
          pcVar7 = pcVar5;
          pcVar9 = pcVar3;
        }
        pcVar3 = pcVar5 + 1;
        if (*pcVar5 != ';') {
          pcVar3 = pcVar5;
        }
      } while (((*pcVar3 != '\0') && (*pcVar10 != '\0')) && (*pcVar10 != ';'));
      if (pcVar9 != (char *)0x0) {
        if (pcVar7 == (char *)0x0) {
          return (undefined8 *)0x0;
        }
        uVar8 = (longlong)pcVar7 - (longlong)pcVar9;
        local_res10 = param_2;
        puVar4 = (undefined8 *)FUN_0001d748(uVar8 + 1);
        if (puVar4 == (undefined8 *)0x0) {
          return (undefined8 *)0x0;
        }
        FUN_000233d0(puVar4,(undefined8 *)pcVar9,uVar8);
        *(undefined1 *)(uVar8 + (longlong)puVar4) = 0;
        return puVar4;
      }
      ppcVar11 = ppcVar11 + 1;
      pcVar6 = *ppcVar11;
    } while (pcVar6 != (char *)0x0);
  }
  return (undefined8 *)0x0;
}


// ==== FUN_0001e640 @ 0001e640

undefined8 FUN_0001e640(longlong param_1)

{
  longlong lVar1;
  undefined8 uVar2;
  undefined8 local_res8;
  
  local_res8 = 0;
  if ((param_1 != 0) &&
     (((DAT_000294c8 != 0 ||
       (lVar1 = (**(code **)(DAT_00029498 + 0x140))(&DAT_000252d0,0,&DAT_000294c8), -1 < lVar1)) &&
      (lVar1 = (**(code **)(DAT_000294c8 + 0x18))(DAT_000294c8,param_1,0,&local_res8),
      lVar1 == -0x7ffffffffffffffb)))) {
    uVar2 = FUN_0001d748(local_res8);
    lVar1 = (**(code **)(DAT_000294c8 + 0x18))(DAT_000294c8,param_1,uVar2,&local_res8);
    if (-1 < lVar1) {
      return uVar2;
    }
    (**(code **)(DAT_00029498 + 0x48))(uVar2);
  }
  return 0;
}


// ==== FUN_0001e700 @ 0001e700

longlong FUN_0001e700(char *param_1,undefined8 param_2,undefined8 param_3,undefined2 param_4,
                     undefined8 param_5,undefined8 param_6)

{
  char cVar1;
  longlong lVar2;
  longlong lVar3;
  char *pcVar4;
  
  lVar2 = DAT_000294c8;
  cVar1 = *param_1;
  lVar3 = -0x7ffffffffffffffe;
  while( true ) {
    if (cVar1 == '\0') {
      return lVar3;
    }
    cVar1 = *param_1;
    pcVar4 = param_1;
    while ((cVar1 != ';' && (*pcVar4 != '\0'))) {
      pcVar4 = pcVar4 + 1;
      cVar1 = *pcVar4;
    }
    cVar1 = *pcVar4;
    *pcVar4 = '\0';
    lVar3 = (**(code **)(lVar2 + 8))(lVar2,param_1,param_3,param_4,param_6,param_5,0);
    if (lVar3 != -0x7fffffffffffffe0) break;
    if (cVar1 == '\0') {
      return -0x7fffffffffffffe0;
    }
    param_1 = pcVar4 + 1;
    cVar1 = *param_1;
    lVar3 = -0x7fffffffffffffe0;
  }
  return lVar3;
}


// ==== FUN_0001e7c4 @ 0001e7c4

longlong FUN_0001e7c4(longlong param_1,undefined2 param_2,undefined8 param_3,undefined8 param_4)

{
  longlong lVar1;
  char *pcVar2;
  char *pcVar3;
  undefined8 *puVar4;
  longlong lVar5;
  
  if ((DAT_000294c8 != 0) ||
     (lVar1 = (**(code **)(DAT_00029498 + 0x140))(&DAT_000252d0,0,&DAT_000294c8), -1 < lVar1)) {
    pcVar2 = FUN_0001e3d4();
    pcVar3 = (char *)FUN_0001e640(param_1);
    if (pcVar3 != (char *)0x0) {
      puVar4 = FUN_0001e520(pcVar3,pcVar2,s_en_US_00025c24,s_en_US_00025c24);
      if (puVar4 == (undefined8 *)0x0) {
        lVar5 = -0x7ffffffffffffff2;
      }
      else {
        lVar5 = (**(code **)(DAT_000294c8 + 8))
                          (DAT_000294c8,puVar4,param_1,param_2,param_4,param_3,0);
        lVar1 = DAT_00029498;
        (**(code **)(DAT_00029498 + 0x48))(puVar4);
        if (lVar5 == -0x7fffffffffffffe0) {
          lVar5 = FUN_0001e700(pcVar3,lVar1,param_1,param_2,param_3,param_4);
        }
      }
      (**(code **)(DAT_00029498 + 0x48))(pcVar3);
      return lVar5;
    }
  }
  return -0x7ffffffffffffff2;
}


// ==== FUN_0001e908 @ 0001e908

longlong FUN_0001e908(undefined8 param_1,undefined2 param_2,undefined8 param_3)

{
  char cVar1;
  longlong lVar2;
  char *pcVar3;
  char *pcVar4;
  char *pcVar5;
  longlong local_res20;
  
  local_res20 = 0;
  if ((DAT_000294c8 == 0) &&
     (lVar2 = (**(code **)(DAT_00029498 + 0x140))(&DAT_000252d0,0,&DAT_000294c8), lVar2 < 0)) {
    lVar2 = -0x7ffffffffffffff2;
  }
  else {
    lVar2 = (**(code **)(DAT_000294c8 + 0x18))(DAT_000294c8,param_1,0,&local_res20);
    if (lVar2 == -0x7ffffffffffffffb) {
      pcVar3 = (char *)FUN_0001d748(local_res20);
      lVar2 = (**(code **)(DAT_000294c8 + 0x18))(DAT_000294c8,param_1,pcVar3,&local_res20);
      if ((-1 < lVar2) && (pcVar5 = pcVar3, pcVar4 = pcVar3, pcVar3 < pcVar3 + local_res20)) {
        do {
          for (; (*pcVar5 != ';' && (*pcVar5 != '\0')); pcVar5 = pcVar5 + 1) {
          }
          cVar1 = *pcVar5;
          *pcVar5 = '\0';
          lVar2 = (**(code **)(DAT_000294c8 + 0x10))(DAT_000294c8,param_1,param_2,pcVar4,param_3,0);
          if (lVar2 < 0) break;
          *pcVar5 = cVar1;
          pcVar5 = pcVar5 + 1;
          pcVar4 = pcVar5;
        } while (pcVar5 < pcVar3 + local_res20);
      }
      (**(code **)(DAT_00029498 + 0x48))(pcVar3);
    }
  }
  return lVar2;
}


// ==== FUN_0001ea50 @ 0001ea50

longlong FUN_0001ea50(longlong *param_1,undefined8 param_2,undefined8 param_3,undefined8 param_4)

{
  longlong lVar1;
  longlong lVar2;
  wchar_t *pwVar3;
  longlong local_28;
  undefined1 local_20 [8];
  
  local_28 = 0;
  if (((DAT_000294b0 == 0) &&
      (lVar1 = (**(code **)(DAT_00029498 + 0x140))(&DAT_000252f0,0,&DAT_000294b0), lVar1 < 0)) ||
     ((DAT_000294b8 == 0 &&
      (lVar1 = (**(code **)(DAT_00029498 + 0x140))(&DAT_000252e0,0,&DAT_000294b8), lVar1 < 0)))) {
    lVar2 = -0x7ffffffffffffff2;
  }
  else {
    lVar2 = (**(code **)(DAT_000294b0 + 8))(DAT_000294b0,&local_28,0,1,param_3,param_4);
    lVar1 = local_28;
    if (lVar2 == -0x7ffffffffffffffb) {
      pwVar3 = (wchar_t *)FUN_0001d748(local_28 + 0x70);
      lVar1 = FUN_0001e3b4(pwVar3,lVar1 + 0x70,(wchar_t *)&DAT_00025b68,
                           u_GUID_000000000000000000000000000_00025300);
      lVar2 = (**(code **)(DAT_000294b0 + 8))
                        (DAT_000294b0,&local_28,pwVar3 + lVar1,1,param_3,param_4);
      if (-1 < lVar2) {
        local_28 = *param_1;
        lVar2 = (**(code **)(DAT_000294b8 + 0x20))(DAT_000294b8,pwVar3,param_2,param_1,local_20);
        *param_1 = local_28;
      }
      (**(code **)(DAT_00029498 + 0x48))(pwVar3);
    }
  }
  return lVar2;
}


// ==== FUN_0001ebd4 @ 0001ebd4

longlong FUN_0001ebd4(undefined8 param_1,undefined8 param_2,undefined8 param_3,undefined8 param_4)

{
  short sVar1;
  short *psVar2;
  longlong lVar3;
  wchar_t *pwVar4;
  uint uVar5;
  longlong lVar6;
  ulonglong local_48;
  short *local_40;
  undefined1 local_38 [16];
  
  local_48 = 0;
  if (((DAT_000294b0 == 0) &&
      (lVar3 = (**(code **)(DAT_00029498 + 0x140))(&DAT_000252f0,0,&DAT_000294b0), lVar3 < 0)) ||
     ((DAT_000294b8 == 0 &&
      (lVar3 = (**(code **)(DAT_00029498 + 0x140))(&DAT_000252e0,0,&DAT_000294b8), lVar3 < 0)))) {
    lVar3 = -0x7ffffffffffffff2;
  }
  else {
    lVar3 = (**(code **)(DAT_000294b0 + 8))(DAT_000294b0,&local_48,0,1,param_3,param_4);
    if (lVar3 == -0x7ffffffffffffffb) {
      lVar6 = local_48 + 0x70;
      pwVar4 = (wchar_t *)FUN_0001d748(lVar6);
      lVar3 = FUN_0001e3b4(pwVar4,lVar6,(wchar_t *)&DAT_00025b68,
                           u_GUID_000000000000000000000000000_00025300);
      lVar3 = (**(code **)(DAT_000294b0 + 8))
                        (DAT_000294b0,&local_48,pwVar4 + lVar3,1,param_3,param_4);
      if (lVar3 < 0) {
        (**(code **)(DAT_00029498 + 0x48))();
      }
      else {
        FUN_0001e448(pwVar4,lVar6);
        lVar3 = (**(code **)(DAT_000294b8 + 0x18))
                          (DAT_000294b8,pwVar4,param_2,param_1,&local_40,local_38);
        if (-1 < lVar3) {
          uVar5 = 2;
          sVar1 = *local_40;
          psVar2 = local_40;
          while (sVar1 != 0) {
            psVar2 = psVar2 + 1;
            uVar5 = uVar5 + 2;
            sVar1 = *psVar2;
          }
          local_48 = (ulonglong)uVar5;
          lVar3 = (**(code **)(DAT_000294b0 + 8))(DAT_000294b0,&local_48,local_40,0,param_3,param_4)
          ;
          (**(code **)(DAT_00029498 + 0x48))(local_40);
        }
        (**(code **)(DAT_00029498 + 0x48))(pwVar4);
      }
    }
  }
  return lVar3;
}


// ==== FUN_0001edd4 @ 0001edd4

longlong FUN_0001edd4(longlong *param_1,longlong *param_2,ulonglong param_3)

{
  longlong *plVar1;
  longlong lVar2;
  ulonglong uVar3;
  
  plVar1 = (longlong *)((longlong)param_1 + param_3);
  if (7 < param_3) {
    uVar3 = (ulonglong)((uint)param_1 & 7);
    if ((((ulonglong)param_1 & 7) != 0) && (uVar3 == ((uint)param_2 & 7))) {
      lVar2 = 8 - uVar3;
      for (; (lVar2 != 0 && ((char)*param_1 == (char)*param_2));
          param_1 = (longlong *)((longlong)param_1 + 1)) {
        param_2 = (longlong *)((longlong)param_2 + 1);
        lVar2 = lVar2 + -1;
      }
    }
    for (; (param_1 <= plVar1 + -1 && (*param_1 == *param_2)); param_1 = param_1 + 1) {
      param_2 = param_2 + 1;
    }
  }
  while( true ) {
    if (plVar1 <= param_1) {
      return 0;
    }
    if ((char)*param_1 != (char)*param_2) break;
    param_1 = (longlong *)((longlong)param_1 + 1);
    param_2 = (longlong *)((longlong)param_2 + 1);
  }
  return (longlong)((int)(char)*param_1 - (int)(char)*param_2);
}


// ==== FUN_0001ee4c @ 0001ee4c

undefined8 FUN_0001ee4c(byte *param_1,undefined8 *param_2)

{
  byte bVar1;
  longlong lVar2;
  undefined8 *puVar3;
  char *pcVar4;
  byte *pbVar5;
  ulonglong uVar6;
  byte *pbVar7;
  ulonglong uVar8;
  undefined8 local_218;
  undefined8 uStack_210;
  byte local_208 [512];
  
  pbVar5 = local_208;
  do {
    bVar1 = *param_1;
    uVar6 = (ulonglong)bVar1;
    if (bVar1 == 1) {
      bVar1 = param_1[1];
      uVar8 = (ulonglong)bVar1;
      if (bVar1 != 1) {
        if (bVar1 == 2) {
          uVar6 = (ulonglong)param_1[4];
          pcVar4 = PTR_s_Pccard_Socket__i___00028b20;
LAB_0001f038:
          lVar2 = FUN_0001daf4(pbVar5,pcVar4,uVar6,2);
        }
        else {
          if (bVar1 != 4) {
            uVar6 = 1;
            goto LAB_0001eeda;
          }
          uVar8 = 4;
          pcVar4 = PTR_s_VenHw__g___00028b28;
LAB_0001f021:
          pbVar7 = param_1 + 4;
LAB_0001f025:
          lVar2 = FUN_0001daf4(pbVar5,pcVar4,pbVar7,uVar8);
        }
        goto LAB_0001f05b;
      }
      uVar8 = (ulonglong)param_1[4];
      uVar6 = (ulonglong)param_1[5];
      pcVar4 = PTR_s_PCI__X__X___00028b18;
LAB_0001f056:
      lVar2 = FUN_0001daf4(pbVar5,pcVar4,uVar6,uVar8);
    }
    else {
      if (bVar1 == 2) {
        uVar8 = (ulonglong)param_1[1];
        if (param_1[1] == 1) {
          uVar8 = (ulonglong)*(uint *)(param_1 + 8);
          uVar6 = (ulonglong)*(uint *)(param_1 + 4);
          pcVar4 = PTR_s_Acpi__x___x___00028b30;
        }
        else {
          uVar6 = 2;
LAB_0001eeda:
          pcVar4 = s_DevicePath_Type__i__SubType__i__00025378;
        }
        goto LAB_0001f056;
      }
      if (bVar1 == 3) {
        bVar1 = param_1[1];
        if (bVar1 != 1) {
          if (bVar1 == 2) {
            uVar8 = (ulonglong)*(ushort *)(param_1 + 6);
            uVar6 = (ulonglong)*(ushort *)(param_1 + 4);
            pcVar4 = PTR_s_SCSI__i___i___00028b60;
          }
          else {
            if (bVar1 != 5) {
              if (bVar1 == 10) {
                uVar8 = 10;
                pcVar4 = PTR_s_VenMsg__g___00028b68;
                goto LAB_0001eef5;
              }
              goto LAB_0001efc0;
            }
            uVar8 = (ulonglong)param_1[5];
            pcVar4 = s_USB__x__x___00028b08;
            uVar6 = (ulonglong)param_1[4];
          }
          goto LAB_0001f056;
        }
        if (param_1[4] == 0) {
          pcVar4 = s_Master_00028afc;
        }
        else {
          if (param_1[4] != 1) {
LAB_0001efc0:
            uVar6 = 3;
            goto LAB_0001eea6;
          }
          pcVar4 = (char *)u_Slave_00028988;
        }
        lVar2 = FUN_0001daf4(pbVar5,PTR_s_ATA__s___i___00028b58,pcVar4,
                             (ulonglong)*(ushort *)(param_1 + 6));
      }
      else if (bVar1 == 4) {
        bVar1 = param_1[1];
        uVar8 = (ulonglong)bVar1;
        if (bVar1 != 1) {
          if (bVar1 == 2) {
            uVar6 = (ulonglong)*(uint *)(param_1 + 4);
            pcVar4 = PTR_s_CDROM_Entry_i___00028b40;
            goto LAB_0001f038;
          }
          pcVar4 = PTR_s_VenMedia__g___00028b48;
          if (bVar1 == 3) {
LAB_0001eef5:
            local_218 = *(undefined8 *)(param_1 + 4);
            uStack_210 = *(undefined8 *)(param_1 + 0xc);
            pbVar7 = (byte *)&local_218;
            goto LAB_0001f025;
          }
          pcVar4 = PTR_DAT_00028b50;
          if (bVar1 == 4) goto LAB_0001f021;
          uVar6 = 4;
          goto LAB_0001eeda;
        }
        lVar2 = FUN_0001daf4(pbVar5,PTR_s_HD_Part_i__Sig__s___00028b38,
                             (ulonglong)*(uint *)(param_1 + 4),&DAT_00028b14);
      }
      else {
        if (bVar1 != 0x7f) {
          bVar1 = param_1[1];
LAB_0001eea6:
          uVar8 = (ulonglong)bVar1;
          pcVar4 = s_DevicePath_Type__i__SubType__i__00025378;
          goto LAB_0001f056;
        }
        lVar2 = 0;
      }
    }
LAB_0001f05b:
    pbVar5 = pbVar5 + lVar2;
    if (lVar2 == -1) {
      return 0x8000000000000003;
    }
    if ((*param_1 == 0x7f) && (param_1[1] == 0xff)) {
      puVar3 = (undefined8 *)FUN_0001d774(((longlong)pbVar5 - (longlong)local_208) + 1);
      *param_2 = puVar3;
      FUN_000233d0(puVar3,(undefined8 *)local_208,(longlong)pbVar5 - (longlong)local_208);
      return 0;
    }
    param_1 = param_1 + (ulonglong)param_1[3] * 0x100 + (ulonglong)param_1[2];
  } while( true );
}


// ==== FUN_0001f0d4 @ 0001f0d4

undefined8 FUN_0001f0d4(void)

{
  longlong lVar1;
  ulonglong uVar2;
  
  if (DAT_00029380 == 0) {
    uVar2 = 0x50;
  }
  else {
    if (DAT_00029390 == 0) {
      uVar2 = DAT_00029380 << 3;
    }
    else {
      if (DAT_00029388 <= (longlong)(DAT_00029380 + -1)) {
        return 0;
      }
      uVar2 = DAT_00029380 * 8 + 0x50;
    }
    if (uVar2 == 0) {
      return 0;
    }
  }
  lVar1 = FUN_0001d774(uVar2);
  if (lVar1 != 0) {
    (**(code **)(DAT_00029498 + 0x160))(lVar1,DAT_00029390,DAT_00029388 << 3);
    (**(code **)(DAT_00029498 + 0x48))(DAT_00029390);
    DAT_00029390 = lVar1;
    DAT_00029380 = uVar2 >> 3;
    return 0;
  }
  return 0x8000000000000009;
}


// ==== FUN_0001f18c @ 0001f18c

undefined8 FUN_0001f18c(longlong *param_1,longlong *param_2)

{
  ulonglong uVar1;
  longlong *plVar2;
  longlong lVar3;
  ulonglong uVar4;
  longlong *plVar5;
  
  lVar3 = DAT_00029470;
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


// ==== FUN_0001f1ec @ 0001f1ec

undefined8
FUN_0001f1ec(undefined8 param_1,undefined8 param_2,undefined8 param_3,undefined8 param_4,
            undefined8 param_5)

{
  undefined8 local_res20;
  
  local_res20 = param_4;
  (**(code **)(DAT_00029478 + 0x50))(0x200,param_2,param_3,0,&local_res20);
  (**(code **)(DAT_00029478 + 0xa8))(param_1,local_res20,param_5);
  (**(code **)(DAT_00029478 + 0x68))(local_res20);
  return local_res20;
}


// ==== FUN_0001f24c @ 0001f24c

longlong FUN_0001f24c(undefined8 param_1,undefined8 param_2,longlong *param_3,undefined8 *param_4)

{
  longlong lVar1;
  undefined8 local_res18;
  
  local_res18 = 0;
  *param_3 = 0;
  if (param_4 != (undefined8 *)0x0) {
    *param_4 = 0;
  }
  lVar1 = (**(code **)(DAT_00029488 + 0x48))(param_1,param_2,0,&local_res18,0);
  if (lVar1 == -0x7ffffffffffffffb) {
    lVar1 = FUN_0001b514(0x8000000000000005,local_res18);
    *param_3 = lVar1;
    if (lVar1 == 0) {
      lVar1 = -0x7ffffffffffffff7;
    }
    else {
      lVar1 = (**(code **)(DAT_00029488 + 0x48))(param_1,param_2,0,&local_res18,lVar1);
      if (lVar1 < 0) {
        (**(code **)(DAT_00029478 + 0x48))(*param_3);
        *param_3 = 0;
      }
      if (param_4 != (undefined8 *)0x0) {
        *param_4 = local_res18;
      }
    }
  }
  return lVar1;
}


// ==== FUN_0001f320 @ 0001f320

char * FUN_0001f320(char *param_1,longlong param_2,char *param_3,undefined8 param_4)

{
  char cVar1;
  char cVar2;
  longlong lVar3;
  char *pcVar4;
  ulonglong uVar5;
  char *pcVar6;
  char **ppcVar7;
  ulonglong uVar8;
  char *local_res18;
  char *local_res20;
  
  local_res20 = (char *)param_4;
  if (param_3 != (char *)0x0) {
    ppcVar7 = &local_res18;
    local_res18 = param_3;
    do {
      cVar2 = *param_3;
      uVar5 = 0;
      uVar8 = 3;
      if (cVar2 == '\0') {
LAB_0001f370:
        uVar5 = 0;
        cVar1 = cVar2;
        while (cVar1 != '\0') {
          uVar5 = uVar5 + 1;
          cVar1 = param_3[uVar5];
        }
      }
      else {
        do {
          uVar5 = uVar5 + 1;
        } while (param_3[uVar5] != '\0');
        if (uVar5 < 4) goto LAB_0001f370;
        uVar5 = 3;
      }
      if (param_2 == 0) {
        uVar5 = 0;
        if (cVar2 != '\0') {
          do {
            if (cVar2 == ';') break;
            uVar5 = uVar5 + 1;
            cVar2 = param_3[uVar5];
          } while (cVar2 != '\0');
          goto LAB_0001f40b;
        }
      }
      else {
LAB_0001f40b:
        if (uVar5 != 0) {
          cVar2 = *param_1;
          pcVar6 = param_1;
          while (cVar2 != '\0') {
            if (param_2 == 0) {
              for (; (*pcVar6 != '\0' && (*pcVar6 == ';')); pcVar6 = pcVar6 + 1) {
              }
              uVar8 = 0;
              cVar2 = *pcVar6;
              while ((cVar2 != '\0' && (cVar2 != ';'))) {
                uVar8 = uVar8 + 1;
                cVar2 = pcVar6[uVar8];
              }
              if (uVar5 <= uVar8) goto LAB_0001f3d8;
            }
            else {
LAB_0001f3d8:
              lVar3 = FUN_0001cf88(pcVar6,param_3,uVar5);
              if (lVar3 == 0) {
                pcVar4 = (char *)FUN_0001b544(uVar8 + 1);
                if (pcVar4 == (char *)0x0) {
                  return (char *)0x0;
                }
                if (uVar8 != 0) {
                  if (pcVar4 != pcVar6) {
                    pcVar6 = (char *)FUN_000002e0((undefined8 *)pcVar4,(undefined8 *)pcVar6,uVar8);
                    return pcVar6;
                  }
                  return pcVar4;
                }
                return pcVar4;
              }
            }
            pcVar6 = pcVar6 + uVar8;
            cVar2 = *pcVar6;
          }
          if ((param_2 != 0) || (uVar5 = uVar5 - 1, uVar5 == 0)) goto LAB_0001f410;
          do {
            if (param_3[uVar5] == '-') break;
            uVar5 = uVar5 - 1;
          } while (uVar5 != 0);
          goto LAB_0001f40b;
        }
      }
LAB_0001f410:
      ppcVar7 = ppcVar7 + 1;
      param_3 = *ppcVar7;
    } while (param_3 != (char *)0x0);
  }
  return (char *)0x0;
}


// ==== FUN_0001f454 @ 0001f454

longlong FUN_0001f454(longlong param_1,char param_2,ulonglong param_3,ulonglong *param_4)

{
  short sVar1;
  ulonglong uVar2;
  ulonglong uVar3;
  longlong lVar4;
  
  uVar2 = 0;
  if (param_1 == 0) {
    lVar4 = 0;
  }
  else {
    lVar4 = 1;
    uVar3 = uVar2;
    do {
      while ((((sVar1 = *(short *)(param_1 + uVar2 * 2), sVar1 != -0x10 && (sVar1 != -0xf)) &&
              (sVar1 != 0)) && ((uVar3 = uVar3 + lVar4, param_2 == '\0' || (uVar3 <= param_3))))) {
        uVar2 = uVar2 + 1;
      }
      if (*(short *)(param_1 + uVar2 * 2) == 0) break;
      if ((param_2 != '\0') && (param_3 < uVar3)) {
        *param_4 = uVar2;
        break;
      }
      lVar4 = (ulonglong)(*(short *)(param_1 + uVar2 * 2) != -0x10) + 1;
      uVar2 = uVar2 + 1;
    } while (*(short *)(param_1 + uVar2 * 2) != 0);
    lVar4 = uVar3 * 2;
  }
  return lVar4;
}


// ==== FUN_0001f4fc @ 0001f4fc

void FUN_0001f4fc(undefined8 param_1,longlong param_2,short *param_3,undefined8 param_4)

{
  longlong lVar1;
  ulonglong uVar2;
  ulonglong uVar3;
  undefined2 *puVar4;
  short *psVar5;
  short **ppsVar6;
  ulonglong *puVar7;
  ulonglong uVar8;
  longlong lVar9;
  ulonglong uVar10;
  short *local_res18;
  short *local_res20;
  undefined4 local_c8;
  undefined4 local_c4;
  undefined4 local_c0;
  undefined4 local_bc;
  ulonglong local_b8;
  ulonglong local_b0;
  ulonglong local_a8;
  short **local_a0;
  short *local_98;
  undefined8 local_90;
  int local_88;
  int local_84;
  int local_80;
  undefined1 local_7c;
  undefined8 *local_78;
  longlong local_70;
  longlong local_68;
  ulonglong local_60;
  undefined1 local_58 [24];
  
  local_c8 = 0xf31fcbb5;
  local_c4 = 0x4215b53d;
  local_c0 = 0x3361db81;
  local_bc = 0x6a98d4e4;
  local_res18 = param_3;
  local_res20 = (short *)param_4;
  lVar1 = (**(code **)(DAT_00029478 + 0x140))(&local_c8);
  uVar3 = 0;
  if (lVar1 < 0) {
    uVar10 = uVar3;
    if (local_res18 != (short *)0x0) {
      ppsVar6 = &local_res18;
      psVar5 = local_res18;
      do {
        puVar7 = (ulonglong *)0x0;
        uVar2 = FUN_0001f454((longlong)psVar5,'\0',0,(ulonglong *)0x0);
        if (uVar3 <= uVar2 >> 1) {
          uVar3 = FUN_0001f454((longlong)psVar5,'\0',0,puVar7);
          uVar3 = uVar3 >> 1;
        }
        ppsVar6 = ppsVar6 + 1;
        uVar10 = uVar10 + 1;
        psVar5 = *ppsVar6;
      } while (psVar5 != (short *)0x0);
    }
    lVar1 = *(longlong *)(DAT_00029470 + 0x40);
    if (&local_90 != *(undefined8 **)(lVar1 + 0x48)) {
      FUN_000002e0(&local_90,*(undefined8 **)(lVar1 + 0x48),0x18);
    }
    (**(code **)(lVar1 + 0x18))(lVar1,(longlong)local_90._4_4_,&local_68);
    (**(code **)(lVar1 + 0x40))(lVar1,0);
    (**(code **)(lVar1 + 0x28))(lVar1,param_1);
    local_b8 = local_70 - 3U;
    if (uVar10 < local_70 - 3U) {
      local_b8 = uVar10;
    }
    uVar10 = local_68 - 2U;
    if (uVar3 < local_68 - 2U) {
      uVar10 = uVar3;
    }
    uVar2 = (local_68 - uVar10) - 2 >> 1;
    uVar8 = (local_70 - local_b8) - 3 >> 1;
    local_a8 = uVar2;
    local_60 = uVar10;
    puVar4 = (undefined2 *)FUN_0001b544(uVar10 * 2 + 6);
    uVar3 = uVar10 * 2 + 4;
    if (uVar3 != 0) {
      FUN_00000400(puVar4,uVar3 >> 1,0x2500);
    }
    *puVar4 = 0x250c;
    *(undefined4 *)(puVar4 + uVar10 + 1) = 0x2510;
    (**(code **)(lVar1 + 0x38))(lVar1,uVar2,uVar8);
    lVar9 = uVar8 + 1;
    (**(code **)(lVar1 + 8))(lVar1,puVar4);
    local_98 = local_res18;
    if (local_res18 != (short *)0x0) {
      local_a0 = &local_res18;
      psVar5 = local_res18;
      do {
        local_98 = psVar5;
        if (local_b8 == 0) break;
        if (uVar3 != 0) {
          FUN_00000400(puVar4,uVar3 >> 1,0x20);
        }
        *puVar4 = 0x2502;
        *(undefined4 *)(puVar4 + uVar10 + 1) = 0x2502;
        (**(code **)(lVar1 + 0x38))(lVar1,uVar2);
        (**(code **)(lVar1 + 8))(lVar1);
        local_b0 = FUN_0001f454((longlong)psVar5,'\0',0,(ulonglong *)0x0);
        local_b0 = local_b0 >> 1;
        if (uVar10 < local_b0) {
          FUN_0001f454((longlong)psVar5,'\x01',uVar10,&local_b0);
          uVar10 = local_b0;
          psVar5 = (short *)FUN_0001b544(local_b0 * 2 + 2);
          FUN_0001d08c(psVar5,uVar10 + 1,local_98,uVar10 - 3);
          FUN_0001d16c(psVar5,uVar10 + 1,(short *)&DAT_00028b70);
          (**(code **)(lVar1 + 0x38))(lVar1,local_a8 + 1,lVar9);
          (**(code **)(lVar1 + 8))(lVar1,psVar5);
          (**(code **)(DAT_00029478 + 0x48))();
          uVar10 = local_60;
          uVar2 = local_a8;
        }
        else {
          (**(code **)(lVar1 + 0x38))(lVar1,(uVar10 - local_b0 >> 1) + 1 + uVar2,lVar9);
          (**(code **)(lVar1 + 8))(lVar1,psVar5);
        }
        lVar9 = lVar9 + 1;
        local_b8 = local_b8 - 1;
        local_a0 = local_a0 + 1;
        psVar5 = *local_a0;
        local_98 = psVar5;
      } while (psVar5 != (short *)0x0);
    }
    if (uVar3 != 0) {
      FUN_00000400(puVar4,uVar3 >> 1,0x2500);
    }
    *puVar4 = 0x2514;
    *(undefined4 *)(puVar4 + uVar10 + 1) = 0x2518;
    (**(code **)(lVar1 + 0x38))(lVar1,uVar2,lVar9);
    (**(code **)(lVar1 + 8))(lVar1,puVar4);
    (**(code **)(DAT_00029478 + 0x48))(puVar4);
    (**(code **)(lVar1 + 0x40))(lVar1,local_7c);
    (**(code **)(lVar1 + 0x38))(lVar1,(longlong)local_84,(longlong)local_80);
    (**(code **)(lVar1 + 0x28))(lVar1,(longlong)local_88);
    if (param_2 != 0) {
      while (lVar1 = (**(code **)(*(longlong *)(DAT_00029470 + 0x30) + 8))
                               (*(longlong *)(DAT_00029470 + 0x30),param_2), lVar1 < 0) {
        if (lVar1 == -0x7ffffffffffffffa) {
          (**(code **)(DAT_00029478 + 0x60))(1,*(longlong *)(DAT_00029470 + 0x30) + 0x10,local_58);
        }
      }
    }
  }
  else {
    (*(code *)*local_78)(param_1,param_2,&local_res18);
  }
  return;
}


// ==== FUN_0001f8dc @ 0001f8dc

longlong FUN_0001f8dc(void)

{
  if (DAT_000294d0 == 0) {
    FUN_0001f18c((longlong *)&DAT_00023820,&DAT_000294d0);
  }
  return DAT_000294d0;
}


// ==== FUN_0001f90c @ 0001f90c

void FUN_0001f90c(longlong *param_1)

{
  short *psVar1;
  
  psVar1 = (short *)FUN_0001f8dc();
  do {
    if (*psVar1 == -1) {
      psVar1 = (short *)0x0;
LAB_0001f93a:
      if ((psVar1 == (short *)0x0) ||
         ((*param_1 == *(longlong *)(psVar1 + 4) && (param_1[1] == *(longlong *)(psVar1 + 8))))) {
        return;
      }
    }
    else if (*psVar1 == 4) goto LAB_0001f93a;
    psVar1 = (short *)((longlong)psVar1 + (ulonglong)(ushort)psVar1[1]);
  } while( true );
}


// ==== FUN_0001f958 @ 0001f958

void FUN_0001f958(uint param_1)

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
      FUN_00000420();
    }
    bVar6 = uVar3 != 0;
    uVar3 = uVar3 - 1;
  } while (bVar6);
  return;
}


// ==== FUN_0001f9b8 @ 0001f9b8

longlong FUN_0001f9b8(longlong param_1)

{
  FUN_0001f958((uint)((ulonglong)(param_1 * 0x369e99) / 1000000));
  return param_1;
}


// ==== FUN_0001f9ec @ 0001f9ec

undefined8 FUN_0001f9ec(longlong param_1,undefined8 param_2,longlong *param_3)

{
  longlong lVar1;
  uint uVar2;
  ushort uVar3;
  
  uVar2 = 0;
  uVar3 = 0;
  if (*(short *)(param_1 + 0x1e) != 0) {
    do {
      if ((uint)*(ushort *)(param_1 + 2) < uVar2 + 0x24) {
        return 0x800000000000000e;
      }
      lVar1 = param_1 + 0x24 + (ulonglong)uVar2;
      if ((*(longlong *)(lVar1 + 8) == DAT_000236b0) &&
         (*(longlong *)(lVar1 + 0x10) == DAT_000236b8)) {
        *param_3 = lVar1;
        return 0;
      }
      uVar3 = uVar3 + 1;
      uVar2 = uVar2 + *(ushort *)(lVar1 + 2);
    } while (uVar3 < *(ushort *)(param_1 + 0x1e));
  }
  return 0x800000000000000e;
}


// ==== FUN_0001fa64 @ 0001fa64

longlong FUN_0001fa64(undefined4 param_1,undefined4 *param_2)

{
  longlong lVar1;
  int local_res18 [2];
  undefined4 local_res20 [2];
  undefined8 *local_28;
  uint local_20;
  undefined4 local_1c;
  undefined4 local_17;
  
  lVar1 = (**(code **)(DAT_00029478 + 0x140))(&DAT_000234b0,0,&local_28);
  if (-1 < lVar1) {
    lVar1 = (*(code *)local_28[8])(local_res18);
    if ((lVar1 < 0) || (local_res18[0] != 0)) {
      lVar1 = -0x7ffffffffffffffd;
    }
    else if (param_2 == (undefined4 *)0x0) {
      lVar1 = -0x7ffffffffffffffe;
    }
    else {
      local_20 = 0x203;
      local_res20[0] = 0xd;
      local_1c = param_1;
      lVar1 = (*(code *)*local_28)(0,&local_20,8,local_res20,0,7);
      if ((((-1 < lVar1) && ((local_20 & 0x7f00) == 0x200)) && ((local_20 >> 0xf & 1) != 0)) &&
         ((local_20 & 0xff000000) == 0)) {
        *param_2 = local_17;
      }
    }
  }
  return lVar1;
}


// ==== FUN_0001fb44 @ 0001fb44

longlong FUN_0001fb44(undefined4 param_1,undefined1 param_2,undefined4 param_3)

{
  longlong lVar1;
  int local_res10 [2];
  undefined4 local_res20 [2];
  undefined8 *local_28;
  undefined4 local_20;
  undefined4 local_1c;
  undefined1 local_18;
  undefined4 local_17;
  
  local_res10[0] = CONCAT31(local_res10[0]._1_3_,param_2);
  lVar1 = (**(code **)(DAT_00029478 + 0x140))(&DAT_000234b0,0,&local_28);
  if (-1 < lVar1) {
    lVar1 = (*(code *)local_28[8])(local_res10);
    if ((lVar1 < 0) || (local_res10[0] != 0)) {
      lVar1 = -0x7ffffffffffffffd;
    }
    else {
      local_20 = 0x303;
      local_18 = 4;
      local_res20[0] = 8;
      local_1c = param_1;
      local_17 = param_3;
      lVar1 = (*(code *)*local_28)(0,&local_20,0xd,local_res20,0,7);
    }
  }
  return lVar1;
}


// ==== FUN_0001fbe8 @ 0001fbe8

longlong FUN_0001fbe8(undefined8 *param_1,uint param_2,uint *param_3,undefined1 param_4,
                     uint *param_5)

{
  uint *puVar1;
  uint uVar2;
  longlong lVar3;
  uint *puVar4;
  ulonglong uVar5;
  uint local_res10 [2];
  int local_res20 [2];
  ulonglong uVar6;
  
  local_res20[0] = CONCAT31(local_res20[0]._1_3_,param_4);
  local_res10[0] = param_2;
  lVar3 = (**(code **)(DAT_00029478 + 0x140))(&DAT_000234b0,0);
  if (-1 < lVar3) {
    lVar3 = (*(code *)param_1[8])(local_res20);
    if ((lVar3 < 0) || (local_res20[0] != 0)) {
      lVar3 = -0x7ffffffffffffffd;
    }
    else {
      local_res10[0] = *param_3 + 8;
      uVar2 = 0x4d;
      if (0x4d < local_res10[0]) {
        uVar2 = local_res10[0];
      }
      puVar4 = (uint *)FUN_0001b544((ulonglong)uVar2);
      if ((ulonglong)*param_3 != 0) {
        FUN_00000340((undefined8 *)param_5,(ulonglong)*param_3);
      }
      if (puVar4 == (uint *)0x0) {
        lVar3 = -0x7fffffffffffffeb;
      }
      else {
        puVar4[0x11] = 0;
        uVar2 = *param_3;
        *(undefined1 *)puVar4 = 10;
        *puVar4 = *puVar4 & 0xffff82ff;
        *puVar4 = *puVar4 | 0x200;
        puVar4[0x12] = uVar2;
        *(undefined1 *)(puVar4 + 0x13) = 0;
        uVar6 = 0;
        do {
          uVar5 = uVar6 + 1;
          lVar3 = uVar6 + 1;
          uVar6 = uVar5;
        } while (s__home_hotham_dbg_dam_req_00028b78[lVar3] != '\0');
        puVar1 = puVar4 + 1;
        if ((uVar5 != 0) && (puVar1 != (uint *)s__home_hotham_dbg_dam_req_00028b78)) {
          FUN_000002e0((undefined8 *)puVar1,(undefined8 *)s__home_hotham_dbg_dam_req_00028b78,uVar5)
          ;
        }
        lVar3 = (*(code *)*param_1)(0,puVar4,0x4d,local_res10,0,7);
        if (-1 < lVar3) {
          if (((((*puVar4 & 0x7f00) == 0x200) && ((*puVar4 & 0x8000) != 0)) &&
              (*(char *)((longlong)puVar4 + 3) == '\0')) && (uVar2 = *puVar1, uVar2 <= *param_3)) {
            if ((uVar2 != 0) && (param_5 != puVar4 + 2)) {
              FUN_000002e0((undefined8 *)param_5,(undefined8 *)(puVar4 + 2),(ulonglong)uVar2);
            }
            *param_3 = *puVar1;
          }
          else {
            lVar3 = -0x7ffffffffffffff9;
          }
        }
        (**(code **)(DAT_00029478 + 0x48))(puVar4);
      }
    }
  }
  return lVar3;
}


// ==== FUN_0001fd70 @ 0001fd70

longlong FUN_0001fd70(undefined8 *param_1,undefined8 param_2,undefined4 param_3,undefined1 param_4,
                     undefined8 *param_5)

{
  longlong lVar1;
  uint *puVar2;
  ulonglong uVar3;
  undefined4 local_res18 [2];
  int local_res20 [2];
  ulonglong uVar4;
  
  local_res20[0] = CONCAT31(local_res20[0]._1_3_,param_4);
  local_res18[0] = param_3;
  lVar1 = (**(code **)(DAT_00029478 + 0x140))(&DAT_000234b0,0);
  if (-1 < lVar1) {
    lVar1 = (*(code *)param_1[8])(local_res20);
    if ((lVar1 < 0) || (local_res20[0] != 0)) {
      lVar1 = -0x7ffffffffffffffd;
    }
    else {
      local_res18[0] = 4;
      puVar2 = (uint *)FUN_0001b544(0x4e);
      if (puVar2 == (uint *)0x0) {
        lVar1 = -0x7fffffffffffffeb;
      }
      else {
        puVar2[0x11] = 0;
        *(undefined1 *)puVar2 = 10;
        *puVar2 = *puVar2 & 0xffff83ff;
        *puVar2 = *puVar2 | 0x300;
        puVar2[0x12] = 1;
        *(undefined1 *)(puVar2 + 0x13) = 0;
        if ((undefined8 *)((longlong)puVar2 + 0x4d) != param_5) {
          FUN_000002e0((undefined8 *)((longlong)puVar2 + 0x4d),param_5,1);
        }
        uVar4 = 0;
        do {
          uVar3 = uVar4 + 1;
          lVar1 = uVar4 + 1;
          uVar4 = uVar3;
        } while (s__home_hotham_dbg_dam_req_00028b78[lVar1] != '\0');
        if ((uVar3 != 0) && (puVar2 + 1 != (uint *)s__home_hotham_dbg_dam_req_00028b78)) {
          FUN_000002e0((undefined8 *)(puVar2 + 1),(undefined8 *)s__home_hotham_dbg_dam_req_00028b78,
                       uVar3);
        }
        lVar1 = (*(code *)*param_1)(0,puVar2,0x4e,local_res18,0,7);
        if (*(char *)((longlong)puVar2 + 3) != '\0') {
          lVar1 = -0x7ffffffffffffff9;
        }
        (**(code **)(DAT_00029478 + 0x48))(puVar2);
      }
    }
  }
  return lVar1;
}


// ==== FUN_0001feb0 @ 0001feb0

longlong FUN_0001feb0(void)

{
  longlong lVar1;
  undefined1 uVar2;
  short local_res8 [4];
  undefined2 local_res10 [4];
  uint local_res18 [2];
  int local_res20 [2];
  undefined4 local_28 [2];
  undefined8 *local_20 [2];
  
  lVar1 = FUN_00020d34(local_res8,local_res10);
  if (-1 < lVar1) {
    uVar2 = 9;
    if (local_res8[0] == 0xc) {
      uVar2 = 7;
    }
    lVar1 = (**(code **)(DAT_00029478 + 0x140))(&DAT_000234b0,0,local_20);
    if (-1 < lVar1) {
      lVar1 = (*(code *)local_20[0][8])(local_res20);
      if ((lVar1 < 0) || (local_res20[0] != 0)) {
        lVar1 = -0x7ffffffffffffffd;
      }
      else {
        local_res18[0] = 0x40a;
        local_28[0] = 4;
        lVar1 = (*(code *)*local_20[0])(0,local_res18,4,local_28,0,uVar2);
        if ((local_res18[0] & 0xff000000) != 0) {
          lVar1 = -0x7ffffffffffffff9;
        }
      }
    }
  }
  return lVar1;
}


// ==== FUN_0001ff68 @ 0001ff68

longlong FUN_0001ff68(undefined8 param_1,uint param_2,uint *param_3,undefined1 param_4,uint *param_5
                     )

{
  uint *puVar1;
  uint uVar2;
  longlong lVar3;
  uint *puVar4;
  uint local_res10 [4];
  int local_res20 [2];
  undefined8 *local_28 [2];
  
  local_res20[0] = CONCAT31(local_res20[0]._1_3_,param_4);
  local_res10[0] = param_2;
  lVar3 = (**(code **)(DAT_00029478 + 0x140))(&DAT_000234b0,0,local_28);
  if (-1 < lVar3) {
    lVar3 = (*(code *)local_28[0][8])(local_res20);
    if ((lVar3 < 0) || (local_res20[0] != 0)) {
      lVar3 = -0x7ffffffffffffffd;
    }
    else {
      local_res10[0] = *param_3 + 8;
      uVar2 = 0x11;
      if (0x11 < local_res10[0]) {
        uVar2 = local_res10[0];
      }
      puVar4 = (uint *)FUN_0001b544((ulonglong)uVar2);
      if ((ulonglong)*param_3 != 0) {
        FUN_00000340((undefined8 *)param_5,(ulonglong)*param_3);
      }
      if (puVar4 == (uint *)0x0) {
        lVar3 = -0x7ffffffffffffff7;
      }
      else {
        uVar2 = *param_3;
        puVar1 = puVar4 + 2;
        *puVar1 = 0;
        *(undefined1 *)puVar4 = 10;
        *puVar4 = *puVar4 & 0xffff8aff;
        *puVar4 = *puVar4 | 0xa00;
        puVar4[1] = 0x10050000;
        puVar4[3] = uVar2;
        *(undefined1 *)(puVar4 + 4) = 0;
        lVar3 = (*(code *)*local_28[0])(0,puVar4,0x11,local_res10,0,9);
        if (-1 < lVar3) {
          if (((((*puVar4 & 0x7f00) == 0xa00) && ((*puVar4 & 0x8000) != 0)) &&
              (*(char *)((longlong)puVar4 + 3) == '\0')) && (uVar2 = puVar4[1], uVar2 <= *param_3))
          {
            if ((uVar2 != 0) && (param_5 != puVar1)) {
              FUN_000002e0((undefined8 *)param_5,(undefined8 *)puVar1,(ulonglong)uVar2);
            }
            *param_3 = puVar4[1];
          }
          else {
            lVar3 = -0x7ffffffffffffff9;
          }
        }
        (**(code **)(DAT_00029478 + 0x48))(puVar4);
      }
    }
  }
  return lVar3;
}


// ==== FUN_000200dc @ 000200dc

longlong FUN_000200dc(undefined8 param_1,undefined8 param_2,undefined4 param_3,undefined1 param_4,
                     undefined8 *param_5)

{
  longlong lVar1;
  uint *puVar2;
  undefined4 local_res18 [2];
  int local_res20 [2];
  undefined8 *local_18 [2];
  
  local_res20[0] = CONCAT31(local_res20[0]._1_3_,param_4);
  local_res18[0] = param_3;
  lVar1 = (**(code **)(DAT_00029478 + 0x140))(&DAT_000234b0,0,local_18);
  if (-1 < lVar1) {
    lVar1 = (*(code *)local_18[0][8])(local_res20);
    if ((lVar1 < 0) || (local_res20[0] != 0)) {
      lVar1 = -0x7ffffffffffffffd;
    }
    else {
      local_res18[0] = 4;
      puVar2 = (uint *)FUN_0001b544(0x12);
      if (puVar2 == (uint *)0x0) {
        lVar1 = -0x7ffffffffffffff7;
      }
      else {
        puVar2[2] = 0;
        *(undefined1 *)puVar2 = 10;
        *puVar2 = *puVar2 & 0xffff8bff;
        *puVar2 = *puVar2 | 0xb00;
        puVar2[1] = 0x10050000;
        puVar2[3] = 1;
        *(undefined1 *)(puVar2 + 4) = 0;
        if ((undefined8 *)((longlong)puVar2 + 0x11) != param_5) {
          FUN_000002e0((undefined8 *)((longlong)puVar2 + 0x11),param_5,1);
        }
        lVar1 = (*(code *)*local_18[0])(0,puVar2,0x12,local_res18,0,9);
        if (*(char *)((longlong)puVar2 + 3) != '\0') {
          lVar1 = -0x7ffffffffffffff9;
        }
        (**(code **)(DAT_00029478 + 0x48))(puVar2);
      }
    }
  }
  return lVar1;
}


// ==== FUN_000201f4 @ 000201f4

longlong FUN_000201f4(void)

{
  longlong lVar1;
  undefined1 uVar2;
  short local_res8 [4];
  undefined2 local_res10 [4];
  int local_res18 [2];
  undefined4 local_res20 [2];
  uint local_28 [2];
  undefined8 *local_20 [2];
  
  lVar1 = FUN_00020d34(local_res8,local_res10);
  if (-1 < lVar1) {
    uVar2 = 9;
    if (local_res8[0] == 0xc) {
      uVar2 = 7;
    }
    lVar1 = (**(code **)(DAT_00029478 + 0x140))(&DAT_000234b0,0,local_20);
    if (-1 < lVar1) {
      lVar1 = (*(code *)local_20[0][8])(local_res18);
      if ((lVar1 < 0) || (local_res18[0] != 0)) {
        lVar1 = -0x7ffffffffffffffd;
      }
      else {
        FUN_00000340((undefined8 *)local_28,8);
        local_28[0] = 0x1b0a;
        local_res20[0] = 4;
        lVar1 = (*(code *)*local_20[0])(0,local_28,8,local_res20,0,uVar2);
        if ((-1 < lVar1) &&
           ((((local_28[0] & 0x7f00) != 0x1b00 || ((local_28[0] >> 0xf & 1) == 0)) ||
            ((local_28[0] & 0xff000000) != 0)))) {
          lVar1 = -0x7ffffffffffffff9;
        }
      }
    }
  }
  return lVar1;
}


// ==== FUN_000202e0 @ 000202e0

longlong FUN_000202e0(uint *param_1,uint *param_2)

{
  uint uVar1;
  undefined1 uVar2;
  longlong lVar3;
  uint *puVar4;
  short local_res18 [4];
  undefined2 local_res20 [4];
  int local_28;
  int local_24;
  undefined8 *local_20;
  
  lVar3 = FUN_00020d34(local_res18,local_res20);
  if (-1 < lVar3) {
    uVar2 = 9;
    if (local_res18[0] == 0xc) {
      uVar2 = 7;
    }
    lVar3 = (**(code **)(DAT_00029478 + 0x140))(&DAT_000234b0,0,&local_20);
    if (-1 < lVar3) {
      lVar3 = (*(code *)local_20[8])(&local_28);
      if ((lVar3 < 0) || (local_28 != 0)) {
        lVar3 = -0x7ffffffffffffffd;
      }
      else if (param_1 == (uint *)0x0) {
        lVar3 = -0x7ffffffffffffffe;
      }
      else {
        uVar1 = *param_1;
        puVar4 = (uint *)FUN_0001b544((ulonglong)uVar1 * 4 + 8);
        if (puVar4 == (uint *)0x0) {
          lVar3 = -0x7ffffffffffffff7;
        }
        else {
          *(undefined1 *)puVar4 = 10;
          *puVar4 = *puVar4 & 0xffff9cff;
          *puVar4 = *puVar4 | 0x1c00;
          local_24 = uVar1 * 4 + 8;
          lVar3 = (*(code *)*local_20)(0,puVar4,4,&local_24,0,uVar2);
          if (lVar3 < 0) {
            if (lVar3 == -0x7ffffffffffffffb) {
              *param_1 = puVar4[1];
            }
          }
          else if ((((*puVar4 & 0x7f00) == 0x1c00) && ((*puVar4 & 0x8000) != 0)) &&
                  (*(char *)((longlong)puVar4 + 3) == '\0')) {
            uVar1 = puVar4[1];
            *param_1 = uVar1;
            if (((ulonglong)uVar1 != 0) && (param_2 != puVar4 + 2)) {
              FUN_000002e0((undefined8 *)param_2,(undefined8 *)(puVar4 + 2),(ulonglong)uVar1 << 2);
            }
          }
          (**(code **)(DAT_00029478 + 0x48))(puVar4);
        }
      }
    }
  }
  return lVar3;
}


// ==== FUN_00020468 @ 00020468

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

longlong FUN_00020468(void)

{
  longlong lVar1;
  undefined8 uVar2;
  ulonglong uVar3;
  int local_res8 [2];
  undefined4 local_res10 [2];
  undefined4 local_res18 [2];
  undefined8 *local_res20;
  
  lVar1 = (**(code **)(DAT_00029478 + 0x140))(&DAT_000234b0,0,&local_res20);
  uVar3 = 0;
  if (-1 < lVar1) {
    (*(code *)local_res20[8])(local_res8);
    if (local_res8[0] == 0) {
      lVar1 = 0;
    }
    else {
      uVar2 = FUN_00020c20();
      if (((char)uVar2 == '\0') && (local_res8[0] == 3)) {
        local_res18[0] = 0x3f0;
        local_res10[0] = 4;
        (*(code *)*local_res20)(0,local_res18,4,local_res10,0,7);
        do {
          FUN_0001f9b8(1000000);
          uVar3 = uVar3 + 1;
        } while (uVar3 < 5);
        lVar1 = -0x7fffffffffffffee;
      }
      else {
        lVar1 = -0x7ffffffffffffffd;
      }
    }
  }
  return lVar1;
}


// ==== FUN_00020524 @ 00020524

longlong FUN_00020524(int param_1,undefined4 param_2)

{
  longlong lVar1;
  int local_res18 [2];
  undefined4 local_res20 [2];
  undefined8 *local_28;
  undefined4 local_20;
  int local_1c;
  undefined4 local_18;
  
  lVar1 = (**(code **)(DAT_00029478 + 0x140))(&DAT_000234b0,0,&local_28);
  if (-1 < lVar1) {
    lVar1 = (*(code *)local_28[8])(local_res18);
    if ((lVar1 < 0) || (local_res18[0] != 0)) {
      lVar1 = -0x7ffffffffffffffd;
    }
    else {
      local_20 = 0x14ff;
      local_res20[0] = 8;
      local_1c = param_1;
      local_18 = param_2;
      lVar1 = (*(code *)*local_28)(0,&local_20,0xc,local_res20,0,7);
      if ((-1 < lVar1) && (local_1c == 1)) {
        lVar1 = -0x7ffffffffffffff1;
      }
    }
  }
  return lVar1;
}


// ==== FUN_000205d8 @ 000205d8

longlong FUN_000205d8(undefined4 param_1)

{
  longlong lVar1;
  short local_res10 [4];
  undefined2 local_res18 [4];
  int local_res20 [2];
  undefined4 local_28 [2];
  uint local_20;
  undefined4 local_1c;
  undefined8 *local_18 [2];
  
  lVar1 = FUN_00020d34(local_res10,local_res18);
  if (lVar1 < 0) {
    return lVar1;
  }
  if (local_res10[0] != 0xc) {
    lVar1 = (**(code **)(DAT_00029478 + 0x140))(&DAT_000234b0,0,local_18);
    if (lVar1 < 0) {
      return lVar1;
    }
    lVar1 = (*(code *)local_18[0][8])(local_res20);
    if ((-1 < lVar1) && (local_res20[0] == 0)) {
      local_20 = 0x20ff;
      local_28[0] = 4;
      local_1c = param_1;
      lVar1 = (*(code *)*local_18[0])(0,&local_20,8,local_28,0,7);
      if (lVar1 < 0) {
        return lVar1;
      }
      if ((local_20 & 0xff000000) == 0) {
        return lVar1;
      }
      return -0x7ffffffffffffff9;
    }
  }
  return -0x7ffffffffffffffd;
}


// ==== FUN_000206a0 @ 000206a0

longlong FUN_000206a0(undefined8 *param_1,longlong *param_2)

{
  longlong lVar1;
  int local_res10 [2];
  undefined4 local_res18 [2];
  uint local_68 [3];
  undefined4 uStack_5c;
  undefined8 uStack_58;
  undefined8 local_50;
  undefined8 uStack_48;
  undefined8 local_40;
  undefined8 uStack_38;
  undefined8 local_30;
  undefined8 uStack_28;
  undefined8 local_20;
  undefined8 uStack_18;
  undefined8 local_10;
  
  lVar1 = (**(code **)(*param_2 + 0x40))(local_res10);
  if ((lVar1 < 0) || (local_res10[0] != 0)) {
    lVar1 = -0x7ffffffffffffffd;
  }
  else {
    local_68[0] = 0x1cff;
    local_68[1] = 0x50434d50;
    local_res18[0] = 0x60;
    lVar1 = (**(code **)*param_2)(0,local_68,8,local_res18,0,7);
    if ((((-1 < lVar1) && ((local_68[0] & 0x7f00) == 0x1c00)) && ((local_68[0] >> 0xf & 1) != 0)) &&
       (((local_68[0] & 0xff000000) == 0 && (local_68[2] == 0x50434d50)))) {
      *param_1 = CONCAT44(uStack_5c,0x50434d50);
      param_1[1] = uStack_58;
      param_1[2] = local_50;
      param_1[3] = uStack_48;
      param_1[4] = local_40;
      param_1[5] = uStack_38;
      param_1[6] = local_30;
      param_1[7] = uStack_28;
      param_1[8] = local_20;
      param_1[9] = uStack_18;
      param_1[10] = local_10;
    }
  }
  return lVar1;
}


// ==== FUN_00020790 @ 00020790

longlong FUN_00020790(undefined1 *param_1,undefined1 *param_2,byte *param_3,undefined8 *param_4)

{
  undefined8 uVar1;
  longlong lVar2;
  int local_358;
  byte local_354 [4];
  undefined4 local_350 [2];
  undefined8 *local_348 [2];
  undefined4 local_338;
  undefined4 local_334;
  int local_330;
  undefined4 local_32c;
  undefined4 local_328;
  undefined1 local_324;
  byte local_323;
  undefined1 local_322;
  undefined8 local_320 [97];
  
  uVar1 = FUN_00020c20();
  if ((char)uVar1 == '\0') {
    lVar2 = (**(code **)(DAT_00029478 + 0x140))(&DAT_000234b0,0,local_348);
    if (lVar2 < 0) {
      return lVar2;
    }
    lVar2 = (*(code *)local_348[0][8])(&local_358);
    if ((-1 < lVar2) && (local_358 == 0)) {
      lVar2 = (*(code *)local_348[0][7])(local_354);
      if ((lVar2 < 0) || ((local_354[0] & 0xf) != 0)) {
        return -0x7ffffffffffffffa;
      }
      local_330 = 0;
      local_32c = 0;
      local_328 = 0;
      local_350[0] = 0x318;
      local_338 = 0x50000;
      local_334 = 0x10;
      lVar2 = (*(code *)*local_348[0])(0,&local_338,0x14,local_350,0,8);
      if (lVar2 < 0) {
        return lVar2;
      }
      if (local_330 != 0) {
        lVar2 = -0x7ffffffffffffff9;
      }
      if (param_1 != (undefined1 *)0x0) {
        *param_1 = local_322;
      }
      if (param_2 != (undefined1 *)0x0) {
        *param_2 = local_324;
      }
      if (param_3 != (byte *)0x0) {
        *param_3 = local_323 >> 7;
      }
      if (param_4 == (undefined8 *)0x0) {
        return lVar2;
      }
      if (param_4 == local_320) {
        return lVar2;
      }
      FUN_000002e0(param_4,local_320,0x300);
      return lVar2;
    }
  }
  return -0x7ffffffffffffffd;
}


// ==== FUN_00020918 @ 00020918

longlong FUN_00020918(undefined1 param_1)

{
  undefined8 uVar1;
  longlong lVar2;
  int local_res10 [2];
  byte local_res18 [8];
  undefined4 local_res20 [2];
  undefined8 *local_38;
  undefined4 local_30;
  undefined8 local_2c;
  undefined8 local_24;
  undefined1 local_1c;
  undefined1 local_1b;
  undefined2 local_1a;
  
  uVar1 = FUN_00020c20();
  if ((char)uVar1 == '\0') {
    lVar2 = (**(code **)(DAT_00029478 + 0x140))(&DAT_000234b0,0,&local_38);
    if (lVar2 < 0) {
      return lVar2;
    }
    lVar2 = (*(code *)local_38[8])(local_res10);
    if ((-1 < lVar2) && (local_res10[0] == 0)) {
      lVar2 = (*(code *)local_38[7])(local_res18);
      if ((lVar2 < 0) || ((local_res18[0] & 0xf) != 0)) {
        return -0x7ffffffffffffffa;
      }
      local_res20[0] = 0x14;
      local_30 = 0x50000;
      local_2c = 0x11;
      local_24 = 4;
      local_1b = 0;
      local_1a = 0;
      local_1c = param_1;
      lVar2 = (*(code *)*local_38)(0,&local_30,0x18,local_res20,0,8);
      if (lVar2 < 0) {
        return lVar2;
      }
      if (local_2c._4_4_ == 0) {
        return lVar2;
      }
      return -0x7ffffffffffffff9;
    }
  }
  return -0x7ffffffffffffffd;
}


// ==== FUN_00020a08 @ 00020a08

longlong FUN_00020a08(undefined8 *param_1)

{
  undefined8 uVar1;
  longlong lVar2;
  int local_res10 [2];
  byte local_res18 [8];
  undefined4 local_res20 [2];
  undefined8 *local_58;
  undefined8 local_50;
  int local_48;
  undefined4 local_44;
  undefined4 local_40;
  undefined1 local_3c;
  undefined1 local_3b;
  
  uVar1 = FUN_00020c20();
  if ((char)uVar1 == '\0') {
    if (param_1 == (undefined8 *)0x0) {
      return -0x7ffffffffffffffe;
    }
    lVar2 = (**(code **)(DAT_00029478 + 0x140))(&DAT_000234b0,0,&local_58);
    if (lVar2 < 0) {
      return lVar2;
    }
    lVar2 = (*(code *)local_58[8])(local_res10);
    if ((-1 < lVar2) && (local_res10[0] == 0)) {
      lVar2 = (*(code *)local_58[7])(local_res18);
      if ((lVar2 < 0) || ((local_res18[0] & 0xf) != 0)) {
        return -0x7ffffffffffffffa;
      }
      local_3c = *(undefined1 *)((longlong)param_1 + 0x14);
      local_48 = 0;
      local_40 = 0;
      local_3b = *(undefined1 *)((longlong)param_1 + 0x15);
      local_res20[0] = 0x30;
      local_50._0_4_ = 0x50000;
      local_50._4_4_ = 0x1a;
      local_44 = 0x1c;
      lVar2 = (*(code *)*local_58)(0,&local_50,0x30,local_res20,0,8);
      if (lVar2 < 0) {
        return lVar2;
      }
      if (local_48 != 0) {
        lVar2 = -0x7ffffffffffffff9;
      }
      if (param_1 == &local_50) {
        return lVar2;
      }
      FUN_000002e0(param_1,&local_50,0x30);
      return lVar2;
    }
  }
  return -0x7ffffffffffffffd;
}


// ==== FUN_00020b40 @ 00020b40

longlong FUN_00020b40(undefined1 param_1)

{
  longlong lVar1;
  int local_res8 [2];
  byte local_res10 [8];
  undefined4 local_res18 [2];
  undefined8 *local_res20;
  undefined4 local_28;
  undefined4 local_24;
  int local_20;
  undefined4 local_1c;
  undefined4 local_18;
  undefined4 local_10;
  
  local_res8[0] = CONCAT31(local_res8[0]._1_3_,param_1);
  lVar1 = (**(code **)(DAT_00029478 + 0x140))(&DAT_000234b0,0,&local_res20);
  if (-1 < lVar1) {
    lVar1 = (*(code *)local_res20[8])(local_res8);
    if ((lVar1 < 0) || (local_res8[0] != 0)) {
      lVar1 = -0x7ffffffffffffffd;
    }
    else {
      lVar1 = (*(code *)local_res20[7])(local_res10);
      if ((lVar1 < 0) || ((local_res10[0] & 0xf) != 0)) {
        lVar1 = -0x7ffffffffffffffa;
      }
      else {
        local_20 = 0;
        local_18 = 0;
        local_10 = 0;
        local_res18[0] = 0x14;
        local_28 = 0x50000;
        local_24 = 0x26;
        local_1c = 0xc;
        lVar1 = (*(code *)*local_res20)(0,&local_28,0x20,local_res18,0,8);
        if ((-1 < lVar1) && (local_20 != 0)) {
          lVar1 = -0x7ffffffffffffff9;
        }
      }
    }
  }
  return lVar1;
}


// ==== FUN_00020c20 @ 00020c20

ulonglong FUN_00020c20(void)

{
  longlong lVar1;
  ulonglong uVar2;
  int iVar3;
  int local_res8 [2];
  undefined4 local_res10 [2];
  undefined8 *local_res18;
  undefined4 local_res20;
  int local_res24;
  undefined8 local_38;
  undefined1 local_30 [8];
  undefined1 local_28 [24];
  
  lVar1 = (**(code **)(DAT_00029478 + 0x140))(&DAT_00023950,0,local_30);
  if (lVar1 < 0) {
    uVar2 = (**(code **)(DAT_00029478 + 0x140))(&DAT_000234b0,0,&local_res18);
    if (-1 < (longlong)uVar2) {
      lVar1 = (*(code *)local_res18[8])(local_res8);
      if ((lVar1 < 0) || (local_res8[0] != 0)) {
        uVar2 = 0x8000000000000003;
        iVar3 = 1;
      }
      else {
        local_res20 = 0x1dff;
        local_res10[0] = 8;
        uVar2 = (*(code *)*local_res18)(0,&local_res20,4,local_res10,0,7);
        iVar3 = 1;
        if (-1 < (longlong)uVar2) {
          iVar3 = local_res24;
        }
      }
      if ((-1 < (longlong)uVar2) && (iVar3 == 0)) {
        lVar1 = (**(code **)(DAT_00029478 + 0x140))(&DAT_00023950,0,local_28);
        if (lVar1 == -0x7ffffffffffffff2) {
          local_38 = 0;
          lVar1 = (**(code **)(DAT_00029478 + 0x80))(&local_38,&DAT_00023950,0,0);
        }
        return CONCAT71((int7)((ulonglong)lVar1 >> 8),1);
      }
    }
    uVar2 = uVar2 & 0xffffffffffffff00;
  }
  else {
    uVar2 = CONCAT71((int7)((ulonglong)lVar1 >> 8),1);
  }
  return uVar2;
}


// ==== FUN_00020d34 @ 00020d34

undefined8 FUN_00020d34(undefined2 *param_1,undefined2 *param_2)

{
  longlong lVar1;
  undefined8 uVar2;
  
  lVar1 = FUN_0001f90c((longlong *)&DAT_00023530);
  if (lVar1 == 0) {
    uVar2 = 0x8000000000000003;
  }
  else {
    *param_1 = *(undefined2 *)(lVar1 + 0x1c);
    *param_2 = *(undefined2 *)(lVar1 + 0x1e);
    uVar2 = 0;
  }
  return uVar2;
}


// ==== FUN_00020d80 @ 00020d80

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

undefined8 FUN_00020d80(void)

{
  ulonglong uVar1;
  undefined1 uVar2;
  ulonglong uVar3;
  undefined7 uVar4;
  undefined7 extraout_var;
  
  uVar3 = FUN_000004a0();
  FUN_00000450();
  uVar2 = in(0x70);
  _DAT_fdc431fc = _DAT_fdc431fc & 0xfffdffff;
  uVar1 = (ulonglong)CONCAT31((int3)(_DAT_fdc431fc >> 8),uVar2) & 0xffffffffffffff80;
  out(0x70,(byte)uVar1 | 0x7d);
  uVar4 = (undefined7)(uVar1 >> 8);
  uVar2 = in(0x71);
  if ((uVar3 >> 9 & 1) != 0) {
    FUN_00000440();
    uVar4 = extraout_var;
  }
  return CONCAT71(uVar4,uVar2);
}


// ==== FUN_00020df0 @ 00020df0

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

undefined1 FUN_00020df0(byte param_1,undefined1 param_2)

{
  byte bVar1;
  ulonglong uVar2;
  undefined2 uVar3;
  undefined2 uVar4;
  
  bVar1 = 0;
  uVar2 = FUN_000004a0();
  FUN_00000450();
  if (param_1 < 0x80) {
    uVar4 = 0x70;
    bVar1 = in(0x70);
    uVar3 = 0x71;
    _DAT_fdc431fc = _DAT_fdc431fc & 0xfffdffff;
    bVar1 = bVar1 & 0x80;
  }
  else {
    uVar4 = 0x72;
    uVar3 = 0x73;
  }
  out(uVar4,param_1 & 0x7f | bVar1);
  out(uVar3,param_2);
  if ((uVar2 >> 9 & 1) != 0) {
    param_2 = FUN_00000440();
  }
  return param_2;
}


// ==== FUN_00020e94 @ 00020e94

undefined8 FUN_00020e94(longlong param_1)

{
  longlong lVar1;
  undefined8 uVar2;
  longlong local_res8 [4];
  
  local_res8[0] = param_1;
  lVar1 = (**(code **)(DAT_00029478 + 0x98))(DAT_00029480,&DAT_00023480,local_res8);
  if (lVar1 < 0) {
    uVar2 = 0;
  }
  else {
    uVar2 = *(undefined8 *)(local_res8[0] + 0x18);
  }
  return uVar2;
}


// ==== FUN_00020ed4 @ 00020ed4

undefined8
FUN_00020ed4(longlong param_1,undefined8 param_2,undefined1 param_3,longlong param_4,
            undefined8 *param_5,undefined8 *param_6)

{
  longlong lVar1;
  undefined8 uVar2;
  undefined1 local_res18 [8];
  longlong local_res20;
  
  if (param_1 != 0) {
    local_res18[0] = param_3;
    local_res20 = param_4;
    lVar1 = (**(code **)(DAT_00029478 + 0x98))(param_1,&DAT_000236c0,&local_res20);
    if (-1 < lVar1) {
      *param_5 = 0;
      *param_6 = 0;
      uVar2 = (**(code **)(local_res20 + 0x18))
                        (local_res20,param_2,0x19,0,param_5,param_6,local_res18);
      return uVar2;
    }
  }
  return 0x800000000000000e;
}


// ==== FUN_00020f58 @ 00020f58

longlong FUN_00020f58(longlong param_1,undefined8 param_2,longlong param_3,undefined8 *param_4,
                     undefined8 *param_5)

{
  longlong lVar1;
  longlong lVar2;
  longlong lVar3;
  ulonglong uVar4;
  ulonglong uVar5;
  undefined8 uVar6;
  undefined8 *puVar7;
  ulonglong *puVar8;
  longlong local_res18;
  ulonglong local_28 [2];
  
  puVar7 = param_4;
  local_res18 = param_3;
  lVar2 = FUN_00020e94(param_1);
  lVar3 = FUN_00020ed4(lVar2,param_1,(char)param_3,(longlong)puVar7,param_4,param_5);
  if (lVar3 < 0) {
    local_res18 = 0;
    uVar6 = 0;
    puVar8 = local_28;
    lVar3 = (**(code **)(DAT_00029478 + 0x138))(2,&DAT_000236c0,0,puVar8,&local_res18);
    if (-1 < lVar3) {
      uVar5 = 0;
      uVar4 = local_28[0];
      if (local_28[0] != 0) {
        do {
          lVar1 = *(longlong *)(local_res18 + uVar5 * 8);
          if ((lVar1 != lVar2) &&
             (lVar3 = FUN_00020ed4(lVar1,param_1,(char)uVar6,(longlong)puVar8,param_4,param_5),
             uVar4 = local_28[0], -1 < lVar3)) goto LAB_00021035;
          uVar5 = uVar5 + 1;
        } while (uVar5 < uVar4);
      }
      if (uVar5 == uVar4) {
        lVar3 = -0x7ffffffffffffff2;
      }
    }
LAB_00021035:
    if (local_res18 != 0) {
      (**(code **)(DAT_00029478 + 0x48))();
    }
  }
  else {
    lVar3 = 0;
  }
  return lVar3;
}


// ==== FUN_00021068 @ 00021068

short FUN_00021068(undefined8 param_1,short param_2)

{
  char *pcVar1;
  char cVar2;
  char *pcVar3;
  short sVar4;
  char *pcVar5;
  longlong lVar6;
  char *pcVar7;
  longlong lVar8;
  ulonglong uVar9;
  ulonglong uVar11;
  short local_res10 [4];
  ulonglong uVar10;
  
  local_res10[0] = param_2;
  pcVar5 = (char *)FUN_00021f60(param_1);
  uVar11 = 0;
  sVar4 = 0;
  if (pcVar5 != (char *)0x0) {
    lVar8 = -0x7ffffffffffffffe;
    cVar2 = *pcVar5;
    pcVar3 = pcVar5;
    while (cVar2 != '\0') {
      pcVar7 = pcVar3;
      uVar10 = uVar11;
      if (*pcVar3 != '\0') {
        do {
          if (*pcVar7 == ';') break;
          pcVar7 = pcVar7 + 1;
        } while (*pcVar7 != '\0');
        if (*pcVar7 != '\0') {
          *pcVar7 = '\0';
          pcVar7 = pcVar7 + 1;
        }
      }
      do {
        uVar9 = uVar10 + 1;
        pcVar1 = &DAT_000278e5 + uVar10;
        uVar10 = uVar9;
      } while (*pcVar1 != '\0');
      lVar6 = FUN_0001cf88(pcVar3,&DAT_000278e4,uVar9);
      if (lVar6 != 0) {
        if (local_res10[0] == 0) {
          lVar8 = (*(code *)*DAT_000294e8)(DAT_000294e8,param_1,local_res10);
        }
        else {
          lVar8 = (*(code *)DAT_000294e8[2])(DAT_000294e8,param_1);
        }
        if (lVar8 < 0) break;
      }
      pcVar3 = pcVar7;
      cVar2 = *pcVar7;
    }
    (**(code **)(DAT_00029478 + 0x48))(pcVar5);
    if (-1 < lVar8) {
      sVar4 = local_res10[0];
    }
  }
  return sVar4;
}


// ==== FUN_00021180 @ 00021180

longlong FUN_00021180(ulonglong param_1,undefined2 param_2)

{
  undefined8 uVar1;
  char *pcVar2;
  char *pcVar3;
  longlong lVar4;
  longlong lVar5;
  ulonglong local_res8;
  undefined2 local_res10 [4];
  char *local_res18;
  
  uVar1 = DAT_000293c0;
  lVar5 = 0;
  local_res18 = (char *)0x0;
  local_res8 = param_1;
  local_res10[0] = param_2;
  pcVar2 = (char *)FUN_00021f60(DAT_000293c0);
  if (pcVar2 != (char *)0x0) {
    FUN_0001f24c(u_PlatformLang_00025c88,&DAT_000234a0,(longlong *)&local_res18,(undefined8 *)0x0);
    pcVar3 = s__home_hotham_dbg_dam_req_00028b78 + 0x19;
    if (local_res18 != (char *)0x0) {
      pcVar3 = local_res18;
    }
    pcVar3 = FUN_0001f320(pcVar2,0,s__home_hotham_dbg_dam_req_00028b78 + 0x19,pcVar3);
    if (pcVar3 != (char *)0x0) {
      local_res8 = 0;
      lVar4 = (**(code **)(DAT_000294e8 + 8))
                        (DAT_000294e8,pcVar3,uVar1,&DAT_000014d8,local_res10,&local_res8,0);
      if (lVar4 == -0x7ffffffffffffffb) {
        lVar5 = FUN_0001b544(local_res8);
        if (lVar5 != 0) {
          lVar4 = (**(code **)(DAT_000294e8 + 8))
                            (DAT_000294e8,pcVar3,uVar1,&DAT_000014d8,lVar5,&local_res8,0);
          if (lVar4 < 0) {
            (**(code **)(DAT_00029478 + 0x48))(lVar5);
            lVar5 = 0;
          }
        }
      }
    }
    (**(code **)(DAT_00029478 + 0x48))(pcVar2);
    if (local_res18 != (char *)0x0) {
      (**(code **)(DAT_00029478 + 0x48))(local_res18);
    }
    if (pcVar3 != (char *)0x0) {
      (**(code **)(DAT_00029478 + 0x48))(pcVar3);
    }
  }
  return lVar5;
}


// ==== FUN_000212f0 @ 000212f0

longlong FUN_000212f0(undefined8 param_1,undefined8 param_2,longlong param_3)

{
  longlong lVar1;
  longlong lVar2;
  undefined1 local_res20 [8];
  ulonglong local_28 [2];
  
  if ((DAT_00029510 == 0) &&
     ((lVar1 = (**(code **)(DAT_00029478 + 0x140))(&DAT_00023870,0,&DAT_00029510), lVar1 < 0 ||
      (DAT_00029510 == 0)))) {
LAB_00021348:
    lVar1 = 0;
  }
  else {
    local_28[0] = 0;
    lVar1 = param_3;
    if (param_3 == 0) {
      lVar1 = (**(code **)(DAT_00029510 + 8))(DAT_00029510,local_28,local_res20,1,param_1,param_2);
      if (-1 < lVar1) {
        lVar1 = FUN_0001b544(2);
        return lVar1;
      }
      if ((lVar1 != -0x7ffffffffffffffb) || (lVar1 = FUN_0001b544(local_28[0]), lVar1 == 0))
      goto LAB_00021348;
    }
    lVar2 = (**(code **)(DAT_00029510 + 8))
                      (DAT_00029510,local_28,lVar1,param_3 == 0,param_1,param_2);
    if (lVar2 < 0) {
      lVar1 = 0;
    }
  }
  return lVar1;
}


// ==== FUN_000213f0 @ 000213f0

bool FUN_000213f0(undefined8 param_1,undefined8 param_2,undefined8 param_3,undefined8 param_4)

{
  short sVar1;
  short *psVar2;
  short *psVar3;
  wchar_t *pwVar4;
  char *pcVar5;
  longlong lVar6;
  longlong lVar7;
  undefined8 local_res18 [2];
  undefined1 local_28 [16];
  
  local_res18[0] = param_3;
  psVar3 = (short *)FUN_000212f0(param_1,param_2,0);
  lVar7 = 0;
  if (psVar3 != (short *)0x0) {
    pwVar4 = u_GUID_000000000000000000000000000_00028be0;
    lVar6 = lVar7;
    do {
      pwVar4 = pwVar4 + 1;
      lVar6 = lVar6 + 1;
    } while (*pwVar4 != L'\0');
    sVar1 = *psVar3;
    psVar2 = psVar3;
    while (sVar1 != 0) {
      psVar2 = psVar2 + 1;
      lVar7 = lVar7 + 1;
      sVar1 = *psVar2;
    }
    lVar7 = lVar6 * 2 + lVar7 * 2;
    pcVar5 = (char *)FUN_0001b544(lVar7 + 4);
    FUN_0001c0f8(pcVar5,lVar7 + 4,(byte *)u__s__s_00028b98,0x28be0);
    (**(code **)(DAT_00029478 + 0x48))(psVar3);
    if (pcVar5 != (char *)0x0) {
      lVar7 = (**(code **)(DAT_000294f8 + 0x20))(DAT_000294f8,pcVar5,param_4,local_res18,local_28);
      (**(code **)(DAT_00029478 + 0x48))(pcVar5);
      return -1 < lVar7;
    }
  }
  return false;
}


// ==== FUN_000214e4 @ 000214e4

bool FUN_000214e4(undefined8 param_1,undefined8 param_2,undefined8 param_3,undefined8 param_4,
                 short *param_5)

{
  short sVar1;
  short *psVar2;
  wchar_t *pwVar3;
  char *pcVar4;
  short *psVar5;
  longlong lVar6;
  ulonglong uVar7;
  longlong lVar8;
  short *psVar9;
  wchar_t *pwVar10;
  undefined1 local_38 [16];
  
  pwVar10 = u_GUID_000000000000000000000000000_00028be0;
  lVar8 = 0;
  pwVar3 = u_GUID_000000000000000000000000000_00028be0;
  lVar6 = lVar8;
  if (param_5 == (short *)0x0) {
    do {
      pwVar3 = pwVar3 + 1;
      lVar8 = lVar8 + 1;
    } while (*pwVar3 != L'\0');
    uVar7 = lVar8 * 2 + 0x42;
    pcVar4 = (char *)FUN_0001b544(uVar7);
    pwVar3 = u__s_OFFSET_0_WIDTH__016LX_00028ba8;
  }
  else {
    do {
      pwVar3 = pwVar3 + 1;
      lVar6 = lVar6 + 1;
    } while (*pwVar3 != L'\0');
    sVar1 = *param_5;
    psVar9 = param_5;
    while (sVar1 != 0) {
      psVar9 = psVar9 + 1;
      lVar8 = lVar8 + 1;
      sVar1 = *psVar9;
    }
    lVar8 = lVar6 * 2 + lVar8 * 2;
    pcVar4 = (char *)FUN_0001b544(lVar8 + 2);
    pwVar3 = u__s_s_00026398;
    uVar7 = lVar8 + 2;
  }
  FUN_0001c0f8(pcVar4,uVar7,(byte *)pwVar3,0x28be0);
  if (pcVar4 != (char *)0x0) {
    lVar8 = (**(code **)(DAT_000294f8 + 0x18))
                      (DAT_000294f8,pcVar4,param_4,param_3,&param_5,local_38);
    psVar9 = param_5;
    if (lVar8 < 0) {
      psVar9 = (short *)0x0;
    }
    (**(code **)(DAT_00029478 + 0x48))(pcVar4);
    psVar2 = (short *)0x0;
    if (psVar9 != (short *)0x0) {
      do {
        psVar5 = psVar2;
        pwVar10 = pwVar10 + 1;
        psVar2 = (short *)((longlong)psVar5 + 1);
      } while (*pwVar10 != L'\0');
      lVar8 = FUN_000212f0(param_1,param_2,(longlong)(psVar9 + (longlong)(psVar5 + 1)));
      (**(code **)(DAT_00029478 + 0x48))(psVar9);
      return lVar8 != 0;
    }
  }
  return false;
}


// ==== FUN_00021668 @ 00021668

longlong * FUN_00021668(undefined8 param_1)

{
  longlong *plVar1;
  longlong lVar2;
  
  plVar1 = (longlong *)FUN_0001b514(param_1,0x18);
  if (plVar1 != (longlong *)0x0) {
    lVar2 = FUN_0001b514(param_1,0x200);
    *plVar1 = lVar2;
    if (lVar2 != 0) {
      plVar1[2] = 0;
      plVar1[1] = 0x200;
      return plVar1;
    }
    (**(code **)(DAT_00029478 + 0x48))(plVar1);
  }
  return (longlong *)0x0;
}


// ==== FUN_000216bc @ 000216bc

void FUN_000216bc(longlong *param_1)

{
  if (*param_1 != 0) {
    (**(code **)(DAT_00029478 + 0x48))();
  }
                    /* WARNING: Could not recover jumptable at 0x000216e6. Too many branches */
                    /* WARNING: Treating indirect jump as call */
  (**(code **)(DAT_00029478 + 0x48))(param_1);
  return;
}


// ==== FUN_000216ec @ 000216ec

longlong FUN_000216ec(longlong *param_1,longlong param_2)

{
  ulonglong uVar1;
  longlong lVar2;
  undefined8 *puVar3;
  
  uVar1 = param_1[1];
  if (uVar1 < (ulonglong)(param_1[2] + param_2)) {
    puVar3 = FUN_0001b5b0(param_1,uVar1,param_2 + 0x200 + uVar1,(undefined8 *)*param_1);
    *param_1 = (longlong)puVar3;
    param_1[1] = param_1[1] + param_2 + 0x200;
  }
  lVar2 = param_1[2];
  param_1[2] = lVar2 + param_2;
  return *param_1 + lVar2;
}


// ==== FUN_00021748 @ 00021748

void FUN_00021748(longlong *param_1,undefined8 *param_2,undefined1 param_3,ulonglong param_4,
                 char param_5,char param_6)

{
  undefined8 *puVar1;
  byte bVar2;
  
  *(undefined1 *)param_2 = param_3;
  bVar2 = param_5 + (char)param_4 & 0x7fU | param_6 << 7;
  *(byte *)((longlong)param_2 + 1) = bVar2;
  puVar1 = (undefined8 *)FUN_000216ec(param_1,(ulonglong)(bVar2 & 0x7f));
  if ((param_4 != 0) && (puVar1 != param_2)) {
    FUN_000002e0(puVar1,param_2,param_4);
  }
  return;
}


// ==== FUN_000217a4 @ 000217a4

void FUN_000217a4(longlong *param_1,undefined8 *param_2,ulonglong param_3)

{
  undefined8 *puVar1;
  
  puVar1 = (undefined8 *)FUN_000216ec(param_1,param_3);
  if ((param_3 != 0) && (puVar1 != param_2)) {
    FUN_000002e0(puVar1,param_2,param_3);
  }
  return;
}


// ==== FUN_000217e0 @ 000217e0

void FUN_000217e0(longlong *param_1)

{
  undefined8 local_res10 [3];
  
  FUN_00021748(param_1,local_res10,0x29,2,'\0','\0');
  return;
}


// ==== FUN_00021808 @ 00021808

void FUN_00021808(longlong *param_1,undefined2 param_2,byte param_3)

{
  undefined1 local_28 [32];
  
  FUN_00000340((undefined8 *)local_28,0x1c);
  local_28[4] = param_3 & 0x30;
  local_28[5] = 0;
  local_28._2_2_ = param_2;
  FUN_000002e0((undefined8 *)(local_28 + 6),(undefined8 *)&stack0x00000028,1);
  FUN_00021748(param_1,(undefined8 *)local_28,9,7,'\0','\0');
  return;
}


// ==== FUN_00021888 @ 00021888

void FUN_00021888(longlong *param_1)

{
  undefined1 local_28 [10];
  undefined8 local_1e;
  
  FUN_00000340((undefined8 *)local_28,0x12);
  local_28._2_8_ = DAT_000234d0;
  local_1e = DAT_000234d8;
  FUN_00021748(param_1,(undefined8 *)local_28,0x5f,0x12,'\x03','\0');
  return;
}


// ==== FUN_000218e4 @ 000218e4

void FUN_000218e4(longlong *param_1,undefined2 param_2)

{
  undefined8 local_18;
  
  FUN_00000340(&local_18,7);
  local_18._4_2_ = 2;
  local_18._6_1_ = 0;
  local_18._2_2_ = param_2;
  FUN_00021748(param_1,&local_18,2,7,'\0','\0');
  return;
}


// ==== FUN_00021940 @ 00021940

longlong FUN_00021940(longlong *param_1,undefined2 param_2,undefined8 param_3,undefined2 param_4,
                     undefined2 param_5)

{
  longlong lVar1;
  undefined8 *in_stack_00000048;
  undefined8 local_38;
  undefined2 local_30;
  undefined2 local_2e;
  undefined2 local_2c;
  
  FUN_00000340(&local_38,0x26);
  local_38._2_2_ = param_5;
  lVar1 = param_1[2];
  local_38._4_2_ = 2;
  local_30 = 0xdddf;
  local_2c = 0;
  local_38._6_2_ = param_2;
  local_2e = param_4;
  FUN_00021748(param_1,&local_38,5,0x11,'\0','\x01');
  FUN_000217a4(param_1,(undefined8 *)*in_stack_00000048,in_stack_00000048[2]);
  FUN_000217e0(param_1);
  return *param_1 + lVar1;
}


// ==== FUN_000219f4 @ 000219f4

void FUN_000219f4(longlong *param_1,undefined2 param_2,undefined8 param_3,undefined2 param_4)

{
  undefined8 local_18;
  
  FUN_00000340(&local_18,8);
  local_18._4_2_ = 2;
  local_18._2_2_ = param_2;
  local_18._6_2_ = param_4;
  FUN_00021748(param_1,&local_18,3,8,'\0','\0');
  return;
}


// ==== FUN_00021a60 @ 00021a60

undefined8
FUN_00021a60(undefined8 param_1,undefined2 param_2,undefined8 *param_3,longlong *param_4,
            undefined8 *param_5,undefined8 *param_6)

{
  char *pcVar1;
  bool bVar2;
  bool bVar3;
  uint uVar4;
  longlong lVar5;
  char *pcVar6;
  char *pcVar7;
  int iVar8;
  longlong lVar9;
  ulonglong uVar10;
  ulonglong uVar11;
  undefined8 local_res8;
  undefined2 local_res10 [4];
  
  uVar10 = 4;
  local_res8 = param_1;
  local_res10[0] = param_2;
  if (param_6 != param_3) {
    FUN_000002e0(param_6,param_3,4);
  }
  lVar9 = 4;
  pcVar7 = (char *)((longlong)param_6 + 4);
  if (&local_res8 != param_3) {
    FUN_000002e0(&local_res8,param_3,4);
  }
  pcVar6 = (char *)((longlong)param_3 + 4);
  bVar2 = false;
  bVar3 = false;
  uVar4 = (uint)local_res8;
  do {
    if ((uVar4 & 0xffffff) <= uVar10) {
      return 0x800000000000000e;
    }
    if (((pcVar6[1] & 0x7fU) != 0) && (pcVar7 != pcVar6)) {
      FUN_000002e0((undefined8 *)pcVar7,(undefined8 *)pcVar6,(ulonglong)((byte)pcVar6[1] & 0x7f));
      uVar4 = (uint)local_res8;
    }
    pcVar7 = pcVar7 + ((byte)pcVar6[1] & 0x7f);
    lVar9 = lVar9 + (ulonglong)((byte)pcVar6[1] & 0x7f);
    if (*pcVar6 == '\x0e') {
      if ((*(longlong *)(pcVar6 + 2) == DAT_000249c8) &&
         (*(longlong *)(pcVar6 + 10) == DAT_000249d0)) {
        bVar2 = true;
      }
      else {
        bVar2 = false;
      }
    }
    else if ((*pcVar6 == '\x01') || (*pcVar6 == ']')) {
      if (pcVar6 + 2 != (char *)local_res10) {
        lVar5 = FUN_000002c0(pcVar6 + 2,(char *)local_res10,2);
        uVar4 = (uint)local_res8;
        if (lVar5 != 0) {
          bVar3 = false;
          goto LAB_00021b6c;
        }
      }
      bVar3 = true;
    }
LAB_00021b6c:
    if (((bVar2) && (bVar3)) && (pcVar1 = (char *)*param_4, ((pcVar6[1] ^ pcVar1[1]) & 0x7fU) == 0))
    {
      if (((pcVar1[1] & 0x7fU) == 0) || (pcVar6 == pcVar1)) {
        lVar5 = 0;
      }
      else {
        lVar5 = FUN_000002c0(pcVar6,pcVar1,(ulonglong)((byte)pcVar1[1] & 0x7f));
        uVar4 = (uint)local_res8;
      }
      if (lVar5 == 0) {
        if (param_5 == (undefined8 *)0x0) goto LAB_00021c35;
        pcVar1 = (char *)*param_5;
        break;
      }
    }
    uVar10 = uVar10 + ((byte)pcVar6[1] & 0x7f);
    pcVar6 = pcVar6 + ((byte)pcVar6[1] & 0x7f);
  } while( true );
  while( true ) {
    if (((pcVar1[1] & 0x7fU) == 0) || (pcVar6 == pcVar1)) {
      lVar5 = 0;
    }
    else {
      lVar5 = FUN_000002c0(pcVar6,pcVar1,(ulonglong)((byte)pcVar1[1] & 0x7f));
      uVar4 = (uint)local_res8;
    }
    if (lVar5 == 0) break;
    do {
      uVar10 = uVar10 + ((byte)pcVar6[1] & 0x7f);
      pcVar6 = pcVar6 + ((byte)pcVar6[1] & 0x7f);
      if (((ulonglong)uVar4 & 0xffffff) <= uVar10) goto LAB_00021c27;
    } while (((pcVar6[1] ^ pcVar1[1]) & 0x7fU) != 0);
  }
LAB_00021c27:
  if (((ulonglong)uVar4 & 0xffffff) <= uVar10) {
    return 0x800000000000000e;
  }
LAB_00021c35:
  uVar11 = (ulonglong)(*(byte *)(*param_4 + 1) & 0x7f);
  pcVar1 = (char *)(*param_4 + uVar11);
  if ((param_4[2] - uVar11 != 0) && (pcVar7 != pcVar1)) {
    FUN_000002e0((undefined8 *)pcVar7,(undefined8 *)pcVar1,param_4[2] - uVar11);
    uVar4 = (uint)local_res8;
  }
  pcVar7 = pcVar7 + (param_4[2] - uVar11);
  iVar8 = (int)lVar9 + (int)(param_4[2] - uVar11);
  if (param_5 != (undefined8 *)0x0) {
    if (((pcVar6[1] & 0x7fU) != 0) && (pcVar7 != pcVar6)) {
      FUN_000002e0((undefined8 *)pcVar7,(undefined8 *)pcVar6,(ulonglong)((byte)pcVar6[1] & 0x7f));
      uVar4 = (uint)local_res8;
    }
    pcVar7 = pcVar7 + ((byte)pcVar6[1] & 0x7f);
    iVar8 = iVar8 + ((byte)pcVar6[1] & 0x7f);
  }
  lVar9 = uVar10 + ((byte)pcVar6[1] & 0x7f);
  uVar10 = ((ulonglong)uVar4 & 0xffffff) - lVar9;
  if ((uVar10 != 0) && (pcVar7 != (char *)(lVar9 + (longlong)param_3))) {
    FUN_000002e0((undefined8 *)pcVar7,(undefined8 *)(lVar9 + (longlong)param_3),uVar10);
    uVar4 = (uint)local_res8;
  }
  local_res8 = CONCAT44(local_res8._4_4_,
                        uVar4 ^ (iVar8 + ((uVar4 & 0xffffff) - (int)lVar9) ^ uVar4) & 0xffffff);
  if (param_6 != &local_res8) {
    FUN_000002e0(param_6,&local_res8,4);
  }
  return 0;
}


// ==== FUN_00021d24 @ 00021d24

longlong FUN_00021d24(undefined8 param_1,ulonglong param_2,undefined2 param_3,longlong *param_4,
                     undefined8 *param_5)

{
  bool bVar1;
  ulonglong uVar2;
  undefined8 uVar3;
  longlong lVar4;
  ulonglong *puVar5;
  ulonglong *puVar6;
  ulonglong *puVar7;
  ulonglong *puVar8;
  longlong unaff_RBX;
  ulonglong *puVar9;
  uint uVar10;
  ulonglong uVar11;
  ulonglong local_res10;
  undefined2 local_res18;
  longlong *local_res20;
  ulonglong *local_68;
  ulonglong *local_60;
  undefined8 local_58;
  
  uVar3 = DAT_00029440;
  puVar6 = (ulonglong *)0x0;
  local_58 = DAT_00029440;
  local_68 = (ulonglong *)0x0;
  puVar7 = (ulonglong *)0x0;
  local_res10 = param_2;
  local_res18 = param_3;
  local_res20 = param_4;
  lVar4 = (**(code **)(DAT_00029508 + 0x20))(DAT_00029508,DAT_00029440,&local_68,0);
  if ((lVar4 == -0x7ffffffffffffffb) &&
     (puVar5 = (ulonglong *)FUN_0001b514(0x8000000000000005,local_68), puVar5 != (ulonglong *)0x0))
  {
    lVar4 = (**(code **)(DAT_00029508 + 0x20))(DAT_00029508,uVar3,&local_68,puVar5);
    if (-1 < lVar4) {
      local_68 = (ulonglong *)((longlong)local_68 + param_4[2]);
      puVar6 = (ulonglong *)FUN_0001b544((ulonglong)local_68);
      local_60 = puVar6;
      if ((puVar6 != (ulonglong *)0x0) &&
         (puVar8 = local_68, puVar7 = (ulonglong *)FUN_0001b544((ulonglong)local_68),
         puVar7 != (ulonglong *)0x0)) {
        uVar11 = 0x14;
        if (puVar6 != puVar5) {
          puVar8 = puVar6;
          FUN_000002e0(puVar6,puVar5,0x14);
        }
        uVar2 = puVar5[2];
        puVar9 = (ulonglong *)((longlong)puVar6 + 0x14);
        bVar1 = false;
        if (0x14 < (uint)uVar2) {
          do {
            puVar6 = (ulonglong *)(uVar11 + (longlong)puVar5);
            if (&local_res10 != puVar6) {
              puVar8 = &local_res10;
              FUN_000002e0(puVar8,puVar6,4);
            }
            uVar10 = (int)uVar11 + ((uint)*puVar6 & 0xffffff);
            uVar11 = (ulonglong)uVar10;
            if ((*(char *)((longlong)puVar6 + 3) == '\x02') &&
               (lVar4 = FUN_00021a60(puVar8,local_res18,puVar6,local_res20,param_5,puVar7),
               -1 < lVar4)) {
              bVar1 = true;
              puVar6 = puVar7;
            }
            if (&local_res10 != puVar6) {
              puVar8 = &local_res10;
              FUN_000002e0(puVar8,puVar6,4);
            }
            if (((local_res10 & 0xffffff) != 0) && (puVar9 != puVar6)) {
              puVar8 = puVar9;
              FUN_000002e0(puVar9,puVar6,(ulonglong)((uint)local_res10 & 0xffffff));
            }
            puVar6 = local_60;
            puVar9 = (ulonglong *)((longlong)puVar9 + (ulonglong)((uint)local_res10 & 0xffffff));
          } while (uVar10 < (uint)uVar2);
          if (bVar1) {
            local_68 = (ulonglong *)((longlong)puVar9 - (longlong)local_60);
            *(uint *)(local_60 + 2) = (uint)local_68;
            (**(code **)(DAT_00029508 + 0x10))(DAT_00029508,local_58,local_60);
          }
        }
      }
    }
    (**(code **)(DAT_00029478 + 0x48))(puVar5);
    if (puVar6 != (ulonglong *)0x0) {
      (**(code **)(DAT_00029478 + 0x48))(puVar6);
    }
    if (puVar7 != (ulonglong *)0x0) {
      (**(code **)(DAT_00029478 + 0x48))(puVar7);
    }
  }
  return unaff_RBX;
}


// ==== FUN_00021f60 @ 00021f60

longlong FUN_00021f60(undefined8 param_1)

{
  longlong lVar1;
  longlong lVar2;
  undefined1 local_res10 [8];
  ulonglong local_res18 [2];
  
  local_res18[0] = 0;
  lVar1 = (**(code **)(DAT_000294e8 + 0x18))(DAT_000294e8,param_1,local_res10,local_res18);
  if ((lVar1 == -0x7ffffffffffffffb) && (lVar1 = FUN_0001b544(local_res18[0]), lVar1 != 0)) {
    lVar2 = (**(code **)(DAT_000294e8 + 0x18))(DAT_000294e8,param_1,lVar1,local_res18);
    if (-1 < lVar2) {
      return lVar1;
    }
    (**(code **)(DAT_00029478 + 0x48))(lVar1);
  }
  return 0;
}


// ==== FUN_000222b8 @ 000222b8

longlong FUN_000222b8(undefined8 param_1,undefined8 param_2,longlong param_3,char *param_4)

{
  char *pcVar1;
  longlong lVar2;
  char *pcVar3;
  char *pcVar4;
  char *local_res20;
  undefined2 local_38;
  uint local_34;
  int local_30 [2];
  int *local_28;
  undefined8 local_20;
  int *local_18;
  longlong local_10;
  
  local_38 = 0;
  local_28 = (int *)0x0;
  local_18 = (int *)0x0;
  local_34 = 0xff;
  local_30[0] = 0xff;
  local_res20 = param_4;
  lVar2 = (**(code **)(DAT_00029498 + 0x98))(param_1,&DAT_000236a0,&local_10);
  if (-1 < lVar2) {
    if (*(short *)(local_10 + 0xe8) == -0x7f7a) {
      pcVar4 = (char *)0x0;
      pcVar1 = local_res20;
      if (local_res20 != (char *)0x0) {
        while (pcVar3 = pcVar1, *pcVar3 != '\x7f') {
          pcVar4 = pcVar3;
          pcVar1 = pcVar3 + (ulonglong)(byte)pcVar3[3] * 0x100 + (ulonglong)(byte)pcVar3[2];
        }
      }
      lVar2 = (**(code **)(DAT_00029498 + 0x108))(param_1,0,pcVar4,1);
      if ((-1 < lVar2) &&
         (lVar2 = (**(code **)(DAT_00029498 + 0xb8))(&DAT_000253b8,&local_res20,&local_20),
         -1 < lVar2)) {
        lVar2 = (**(code **)(DAT_00029498 + 0x118))(local_20,&DAT_000253b8,&local_28,0,0,1);
        if ((-1 < lVar2) && (*local_28 != 0)) {
          local_38 = CONCAT11(local_38._1_1_,1);
          lVar2 = (**(code **)(local_28 + 2))(local_28,&local_34);
          if (-1 < lVar2) {
            if (local_34 < *(uint *)(param_3 + 0x730)) {
              *(uint *)(param_3 + 0x730) = local_34;
              FUN_0001ebd4(2,param_3,&DAT_000253a8,u_Setup_000262c8);
            }
            lVar2 = (**(code **)(local_28 + 4))(local_28,local_30);
            if ((-1 < lVar2) && (local_30[0] != *(int *)(param_3 + 0x730))) {
              (**(code **)(local_28 + 6))(local_28);
            }
          }
        }
        lVar2 = (**(code **)(DAT_00029498 + 0x118))(local_20,&DAT_000253c8,&local_18,0,0,1);
        if ((-1 < lVar2) && (*local_18 != 0)) {
          local_38 = CONCAT11(1,(undefined1)local_38);
          if (*(char *)(param_3 + 0x734) == '\x01') {
            (**(code **)(local_18 + 2))();
          }
          else {
            (**(code **)(local_18 + 4))(local_18);
          }
        }
      }
      lVar2 = FUN_0001ebd4(2,&local_38,&DAT_000253a8,u_NBGopPlatformData_00028c50);
    }
    else {
      lVar2 = -0x7ffffffffffffffd;
    }
  }
  return lVar2;
}


// ==== FUN_000224c0 @ 000224c0

longlong FUN_000224c0(void)

{
  longlong lVar1;
  undefined8 uVar2;
  longlong lVar3;
  longlong extraout_RAX;
  ulonglong uVar4;
  ulonglong uVar5;
  short in_R9W;
  undefined2 local_88;
  longlong local_80;
  uint local_78;
  int local_74;
  longlong local_70;
  int *local_68;
  ulonglong local_60;
  ulonglong local_58;
  longlong local_50;
  longlong local_48;
  longlong local_40;
  int *local_38;
  undefined8 local_30;
  longlong local_28;
  
  local_80 = 0;
  local_88 = 0;
  local_58 = 0;
  local_50 = 0;
  local_60 = 0;
  local_40 = 0;
  local_68 = (int *)0x0;
  local_38 = (int *)0x0;
  local_74 = 0xff;
  local_78 = 0xff;
  local_70 = 0x7d8;
  if (*(longlong *)(DAT_00029270 + 8) == 1) {
    lVar3 = (**(code **)(DAT_00029498 + 0x40))(4,0x7d8,&local_80);
    if ((-1 < lVar3) &&
       (lVar3 = FUN_0001ea50(&local_70,local_80,&DAT_000253a8,u_Setup_000262c8), -1 < lVar3)) {
      local_70 = 2;
      local_28 = FUN_0001ea50(&local_70,&local_88,&DAT_000253a8,u_NBGopPlatformData_00028c50);
      lVar3 = (**(code **)(DAT_00029498 + 0x138))(2,&DAT_000236a0,0,&local_58,&local_50);
      if (-1 < lVar3) {
        uVar4 = 0;
        if (local_58 != 0) {
          do {
            lVar1 = *(longlong *)(local_50 + uVar4 * 8);
            lVar3 = (**(code **)(DAT_00029498 + 0x98))(lVar1,&DAT_000236a0,&local_30);
            if ((((-1 < lVar3) && (lVar3 = FUN_0000c2bc(lVar1,&local_48), -1 < lVar3)) &&
                (lVar3 = FUN_0000bc4c(lVar1,local_48,local_30), -1 < lVar3)) &&
               ((FUN_0000c464(local_48,lVar1,(longlong *)&local_60,&local_40), lVar1 = local_40,
                lVar3 = extraout_RAX, -1 < extraout_RAX && (uVar5 = 0, local_60 != 0)))) {
              do {
                uVar2 = *(undefined8 *)(lVar1 + uVar5 * 8);
                lVar3 = (**(code **)(DAT_00029498 + 0x118))(uVar2,&DAT_00023790,0,0,0,4);
                if (-1 < lVar3) {
                  if (in_R9W == 0x27f5) {
                    lVar3 = (**(code **)(DAT_00029498 + 0x118))(uVar2,&DAT_000253b8,&local_68,0,0,1)
                    ;
                    if ((-1 < lVar3) && (*local_68 != 0)) {
                      local_88 = CONCAT11(local_88._1_1_,1);
                      lVar3 = (**(code **)(local_68 + 2))(local_68,&local_78);
                      if (-1 < lVar3) {
                        if (local_78 < *(uint *)(local_80 + 0x730)) {
                          *(uint *)(local_80 + 0x730) = local_78;
                          local_70 = 0x7d8;
                          FUN_0001ebd4(0x7d8,local_80,&DAT_000253a8,u_Setup_000262c8);
                        }
                        lVar3 = (**(code **)(local_68 + 4))(local_68,&local_74);
                        if ((-1 < lVar3) && (local_74 != *(int *)(local_80 + 0x730))) {
                          lVar3 = (**(code **)(local_68 + 6))(local_68);
                          goto LAB_0002278c;
                        }
                      }
                    }
                  }
                  else {
LAB_0002278c:
                    if (((in_R9W == 0x27f6) &&
                        (lVar3 = (**(code **)(DAT_00029498 + 0x118))
                                           (uVar2,&DAT_000253c8,&local_38,0,0,1), -1 < lVar3)) &&
                       (*local_38 != 0)) {
                      local_88 = CONCAT11(1,(undefined1)local_88);
                      if (*(char *)(local_80 + 0x734) == '\x01') {
                        lVar3 = (**(code **)(local_38 + 2))();
                      }
                      else {
                        lVar3 = (**(code **)(local_38 + 4))(local_38);
                      }
                    }
                  }
                }
                uVar5 = uVar5 + 1;
              } while (uVar5 < local_60);
            }
            uVar4 = uVar4 + 1;
          } while (uVar4 < local_58);
        }
        if (-1 < local_28) {
          FUN_0001ebd4(2,&local_88,&DAT_000253a8,u_NBGopPlatformData_00028c50);
        }
      }
    }
  }
  else {
    lVar3 = 0;
  }
  return lVar3;
}


// ==== FUN_00022854 @ 00022854

undefined8 FUN_00022854(int param_1)

{
  uint uVar1;
  
  uVar1 = 0;
  do {
    if ((*(uint *)(ulonglong)(param_1 + 0x20) >> 0x1c & 1) != 0) {
      return 0;
    }
    FUN_0001f9b8(0x32);
    uVar1 = uVar1 + 1;
  } while (uVar1 < 4000);
  return 0x8000000000000012;
}


// ==== FUN_00022898 @ 00022898

longlong FUN_00022898(uint param_1,short *param_2)

{
  longlong lVar1;
  uint uVar2;
  char cVar3;
  uint *puVar4;
  uint *puVar5;
  undefined4 *puVar6;
  
  puVar4 = (uint *)(ulonglong)param_1;
  puVar5 = (uint *)(ulonglong)(param_1 + 0xf00);
  uVar2 = 0;
  *puVar5 = *(uint *)(ulonglong)(param_1 + 0xf00) | 0x20;
  while ((*puVar5 & 0x20) == 0) {
    FUN_0001f9b8(0x32);
    uVar2 = uVar2 + 1;
    if (3999 < uVar2) {
      return -0x7fffffffffffffee;
    }
  }
  puVar6 = (undefined4 *)(ulonglong)(param_1 + 0x20);
  *(undefined4 *)(ulonglong)(param_1 + 0x20) = 0x43f6020;
  lVar1 = FUN_00022854(param_1);
  if (lVar1 == -0x7fffffffffffffee) {
    *(uint *)(ulonglong)(param_1 + 0x18) = *(uint *)(ulonglong)(param_1 + 0x18) | 0x800;
    *puVar6 = 0x43f6020;
    lVar1 = FUN_00022854(param_1);
    if (lVar1 == -0x7fffffffffffffee) {
      lVar1 = -0x7ffffffffffffff9;
      goto LAB_0002295b;
    }
  }
  FUN_0001f9b8(4000);
  if (lVar1 < 0) {
LAB_0002295b:
    *puVar5 = *puVar5 & 0xffffffdf;
    return lVar1;
  }
  *puVar6 = 0x4302580;
  lVar1 = FUN_00022854(param_1);
  if (-1 < lVar1) {
    *puVar6 = 0x8430000;
    lVar1 = FUN_00022854(param_1);
    if (lVar1 == 0) {
      *param_2 = (short)*puVar6;
    }
    if (*param_2 == 0) {
      if ((*puVar4 & 0x30000) != 0) {
        lVar1 = -0x7ffffffffffffff9;
        goto LAB_00022a35;
      }
      cVar3 = 'e';
      *puVar4 = *puVar4 | 0x10000;
      *puVar4 = *puVar4 | 0x20000;
      do {
        if ((*(uint *)(ulonglong)(param_1 + 0x18) & 4) != 0) break;
        FUN_0001f9b8(1000);
        cVar3 = cVar3 + -1;
      } while (cVar3 != '\0');
      if (cVar3 != '\0') {
        *puVar6 = 0x8430000;
        lVar1 = FUN_00022854(param_1);
        if (lVar1 == 0) {
          *param_2 = (short)*puVar6;
        }
      }
      *puVar4 = *puVar4 & 0xfffdffff;
      *puVar4 = *puVar4 & 0xfffeffff;
    }
    if (-1 < lVar1) {
      *puVar6 = 0x4302180;
      lVar1 = FUN_00022854(param_1);
    }
  }
LAB_00022a35:
  *puVar5 = *puVar5 & 0xffffffdf;
  return lVar1;
}


// ==== FUN_00022a5c @ 00022a5c

longlong FUN_00022a5c(ushort param_1,longlong param_2,longlong param_3,longlong param_4,
                     longlong param_5,longlong param_6)

{
  uint uVar1;
  longlong lVar2;
  longlong lVar3;
  uint uVar4;
  longlong local_res10;
  undefined8 local_58 [6];
  
  if (((param_2 == 0) || (param_4 == 0)) ||
     ((param_1 != 1 &&
      (((param_5 == 0 || (param_6 == 0)) || (((param_1 & 4) != 0 && (param_3 == 0)))))))) {
    lVar3 = -0x7ffffffffffffffe;
  }
  else {
    local_res10 = 0;
    uVar4 = 6;
    lVar3 = param_4;
    lVar2 = (**(code **)(DAT_000294a0 + 0x48))(param_2,param_4,0,&local_res10,0);
    if ((lVar2 == -0x7ffffffffffffffb) && ((param_1 & 1) != 0)) {
      FUN_00022d6c(local_58,CONCAT71((int7)((ulonglong)lVar3 >> 8),2));
      uVar4 = 0x27;
      lVar2 = (**(code **)(DAT_000294a0 + 0x58))(param_2,param_4,0x27,0x28,local_58);
      if (lVar2 < 0) {
        return lVar2;
      }
    }
    lVar3 = 0;
    if (lVar2 != -0x7ffffffffffffff2) {
      lVar3 = lVar2;
    }
    if ((param_1 & 4) != 0) {
      lVar3 = (ulonglong)*(uint *)(param_5 + 0x10) + 0x10;
      lVar3 = (**(code **)(DAT_000294a0 + 0x58))
                        (param_3,&DAT_000234a0,uVar4,param_6 - lVar3,lVar3 + param_5);
    }
    if ((param_1 & 2) != 0) {
      uVar1 = uVar4 | 0x61;
      if ((param_1 & 8) == 0) {
        uVar1 = uVar4 | 0x21;
      }
      lVar3 = (**(code **)(DAT_000294a0 + 0x58))(param_2,param_4,uVar1,param_6,param_5);
      if (lVar3 == -0x7ffffffffffffff2) {
        lVar3 = 0;
      }
      else if (-1 < lVar3) {
        param_6 = 0;
        (**(code **)(DAT_000294a0 + 0x48))(param_2,param_4,0,&param_6,0);
        if (((param_1 & 8) != 0) && (local_res10 == param_6)) {
          lVar3 = -0x7fffffffffffffec;
        }
      }
    }
  }
  return lVar3;
}


// ==== FUN_00022d6c @ 00022d6c

void FUN_00022d6c(undefined8 *param_1,ulonglong param_2)

{
  undefined4 local_18;
  uint local_14;
  undefined4 uStack_10;
  undefined4 local_c;
  
  local_18 = 0x120307e5;
  local_14 = 0x14380a;
  uStack_10 = 0;
  local_c = 0;
  if (DAT_000294a0 != 0) {
    (**(code **)(DAT_000294a0 + 0x18))(&local_18,0);
    local_14 = local_14 & 0xffffff;
  }
  local_c = 0;
  uStack_10 = 0;
  FUN_000233d0(param_1,(undefined8 *)&local_18,0x10);
  if ((param_2 & 8) != 0) {
    *(undefined2 *)param_1 = 2000;
  }
  *(undefined4 *)(param_1 + 2) = 0x18;
  *(undefined4 *)((longlong)param_1 + 0x14) = 0xef10200;
  param_1[3] = DAT_00023600;
  param_1[4] = DAT_00023608;
  return;
}


// ==== FUN_00022e14 @ 00022e14

longlong FUN_00022e14(undefined8 *param_1,undefined8 param_2,ulonglong param_3,undefined8 *param_4,
                     undefined1 param_5)

{
  longlong lVar1;
  undefined8 *puVar2;
  undefined8 *puVar3;
  ulonglong local_res8;
  longlong local_res18 [2];
  
  local_res8 = 0x100;
  FUN_00022d6c(param_1,CONCAT71((int7)((ulonglong)param_2 >> 8),param_5));
  puVar3 = (undefined8 *)&DAT_000235a0;
  if (param_3 != 0x20) {
    puVar3 = (undefined8 *)0x0;
  }
  puVar2 = (undefined8 *)&DAT_00023680;
  if (param_3 != 0x30) {
    puVar2 = puVar3;
  }
  puVar3 = (undefined8 *)&DAT_00023610;
  if (param_3 != 0x40) {
    puVar3 = puVar2;
  }
  puVar2 = (undefined8 *)&DAT_000236d0;
  if (param_3 != 0x50) {
    puVar2 = puVar3;
  }
  puVar3 = (undefined8 *)&DAT_00023960;
  if (param_3 != 0x100) {
    puVar3 = puVar2;
  }
  if (0x100 < param_3) {
    if (((DAT_00029520 == 0) &&
        ((**(code **)(DAT_00029498 + 0x140))(&DAT_00023640,0,&DAT_00029520), DAT_00029520 == 0)) ||
       (local_res18[0] = FUN_0001b544(local_res8), local_res18[0] == 0)) {
      return -0x7fffffffffffffff;
    }
    lVar1 = (**(code **)(DAT_00029520 + 8))
                      (DAT_00029520,param_2,param_3,0,0,local_res18,&local_res8,0x13,0);
    if (local_res18[0] != 0) {
      (**(code **)(DAT_00029498 + 0x48))();
    }
    if (lVar1 < 0) {
      return lVar1;
    }
    puVar3 = &DAT_00023760;
  }
  if (puVar3 == (undefined8 *)0x0) {
    lVar1 = -0x7ffffffffffffffe;
  }
  else {
    param_1[5] = *puVar3;
    param_1[6] = puVar3[1];
    *(int *)(param_1 + 8) = (int)param_3 + 0x10;
    *(int *)(param_1 + 7) = (int)param_3 + 0x2c;
    *(undefined4 *)((longlong)param_1 + 0x3c) = 0;
    puVar3 = &DAT_00023650;
    if (param_4 != (undefined8 *)0x0) {
      puVar3 = param_4;
    }
    *(undefined8 *)((longlong)param_1 + 0x44) = *puVar3;
    *(undefined8 *)((longlong)param_1 + 0x4c) = puVar3[1];
    lVar1 = 0;
  }
  return lVar1;
}


// ==== FUN_00022fc0 @ 00022fc0

undefined8 FUN_00022fc0(longlong *param_1,ulonglong param_2,longlong *param_3,longlong *param_4)

{
  uint uVar1;
  undefined8 uVar2;
  longlong lVar3;
  ulonglong uVar4;
  longlong lVar5;
  ulonglong uVar6;
  longlong *plVar7;
  longlong local_res10;
  
  if ((param_2 < 0x70001) && (param_1 != (longlong *)0x0)) {
    local_res10 = 0;
    lVar5 = 0;
    uVar2 = 0x800000000000001a;
    for (; param_2 != 0; param_2 = param_2 - uVar4) {
      uVar1 = *(uint *)(param_1 + 2);
      uVar4 = (ulonglong)uVar1;
      if (param_2 < uVar4) break;
      uVar6 = 0;
      plVar7 = (longlong *)&DAT_000256e0;
      do {
        lVar3 = FUN_0001edd4(param_1,plVar7,0x10);
        if (lVar3 == 0) break;
        uVar6 = uVar6 + 1;
        plVar7 = plVar7 + 2;
      } while (uVar6 < 9);
      if ((((8 < uVar6) || (uVar1 < 0x2d)) || (0x70000 < uVar1)) ||
         (*(int *)((longlong)param_1 + 0x14) != 0)) {
        return 0x800000000000001a;
      }
      lVar5 = lVar5 + 1;
      uVar6 = 0x1c;
      if (0x1c < uVar4) {
        do {
          local_res10 = local_res10 + 1;
          uVar6 = uVar6 + *(uint *)(param_1 + 3);
        } while (uVar6 < uVar4);
      }
      param_1 = (longlong *)((longlong)param_1 + uVar4);
      uVar2 = 0;
    }
    if (param_3 != (longlong *)0x0) {
      *param_3 = local_res10;
    }
    if (param_4 != (longlong *)0x0) {
      *param_4 = lVar5;
    }
  }
  else {
    uVar2 = 0x800000000000001a;
  }
  return uVar2;
}


// ==== FUN_000230d4 @ 000230d4

undefined8 FUN_000230d4(undefined8 *param_1)

{
  undefined8 uVar1;
  uint uVar2;
  
  uVar2 = 0;
  do {
    uVar1 = FUN_00000483(param_1);
    if ((char)uVar1 != '\0') {
      return CONCAT71((int7)((ulonglong)uVar1 >> 8),1);
    }
    uVar2 = uVar2 + 1;
  } while (uVar2 < 10);
  return uVar1;
}


// ==== FUN_00023108 @ 00023108

void FUN_00023108(longlong *param_1,undefined2 param_2,undefined2 param_3)

{
  undefined8 *puVar1;
  undefined1 local_18;
  undefined1 local_17;
  undefined1 local_16;
  undefined1 local_15;
  undefined2 local_14;
  undefined2 local_12;
  
  local_18 = 0x19;
  local_17 = 0x82;
  local_16 = 0x12;
  local_15 = 6;
  local_14 = param_2;
  local_12 = param_3;
  puVar1 = (undefined8 *)FUN_000216ec(param_1,8);
  if (puVar1 != (undefined8 *)&local_18) {
    FUN_000002e0(puVar1,(undefined8 *)&local_18,8);
  }
  return;
}


// ==== FUN_00023168 @ 00023168

void FUN_00023168(longlong *param_1)

{
  undefined8 *puVar1;
  undefined2 local_res10 [12];
  
  local_res10[0] = 0x229;
  puVar1 = (undefined8 *)FUN_000216ec(param_1,2);
  if (puVar1 != (undefined8 *)local_res10) {
    FUN_000002e0(puVar1,(undefined8 *)local_res10,2);
  }
  return;
}


// ==== FUN_000231a0 @ 000231a0

undefined * FUN_000231a0(undefined4 *param_1)

{
  char cVar1;
  undefined *puVar2;
  
  cVar1 = FUN_0001b6e0();
  if (cVar1 == '\x02') {
    *param_1 = 0xf;
    puVar2 = &DAT_00025970;
  }
  else {
    *param_1 = 0x11;
    puVar2 = &DAT_00025770;
  }
  return puVar2;
}


// ==== FUN_000231d4 @ 000231d4

ulonglong FUN_000231d4(uint param_1)

{
  char cVar1;
  ulonglong uVar2;
  undefined *puVar3;
  ulonglong uVar4;
  uint local_res8 [8];
  
  uVar4 = (ulonglong)param_1;
  cVar1 = FUN_0001b6e0();
  uVar2 = uVar4 >> 0x18 & 0xff;
  if ((int)uVar2 == 4 - (uint)(cVar1 != '\x02')) {
    FUN_000231a0(local_res8);
    uVar2 = uVar4 >> 0x10 & 0xff;
    if ((uint)uVar2 < local_res8[0]) {
      puVar3 = FUN_000231a0(local_res8);
      uVar2 = uVar4 & 0xffff;
      if ((uint)uVar2 <
          (uint)*(ushort *)(puVar3 + ((uVar4 & 0xffffffff) >> 0x10 & 0xff) * 0x1e + 0x1c)) {
        return CONCAT71((int7)(uVar2 >> 8),1);
      }
    }
  }
  return uVar2 & 0xffffffffffffff00;
}


// ==== FUN_00023240 @ 00023240

undefined4 FUN_00023240(uint param_1,undefined1 param_2)

{
  undefined *puVar1;
  longlong lVar2;
  ulonglong uVar3;
  undefined1 local_res10 [24];
  
  uVar3 = (ulonglong)param_1;
  local_res10[0] = param_2;
  puVar1 = FUN_000231a0((undefined4 *)local_res10);
  lVar2 = ((uVar3 & 0xffffffff) >> 0x10 & 0xff) * 0x1e;
  return *(undefined4 *)
          ((ulonglong)(ushort)(*(short *)(puVar1 + lVar2 + 0x1a) + (short)uVar3 * 0x10) |
          ((ulonglong)(byte)puVar1[lVar2] | 0xfd00) << 0x10);
}


// ==== FUN_00023290 @ 00023290

ulonglong FUN_00023290(uint param_1,uint *param_2)

{
  ulonglong uVar1;
  undefined *puVar2;
  sbyte sVar3;
  longlong lVar4;
  ulonglong uVar5;
  undefined4 local_res18 [4];
  
  uVar5 = (ulonglong)param_1;
  uVar1 = FUN_000231d4(param_1);
  if ((char)uVar1 == '\0') {
    uVar1 = 0x8000000000000002;
  }
  else {
    uVar1 = uVar5 & 0xffff;
    puVar2 = FUN_000231a0(local_res18);
    lVar4 = ((uVar5 & 0xffffffff) >> 0x10 & 0xff) * 0x1e;
    sVar3 = (sbyte)(((uint)uVar1 & 7) << 2);
    *param_2 = (3 << sVar3 &
               *(uint *)((ulonglong)
                         (ushort)((short)(uVar1 >> 3) * 4 + *(short *)(puVar2 + lVar4 + 2)) |
                        ((ulonglong)(byte)puVar2[lVar4] | 0xfd00) << 0x10)) >> sVar3;
    uVar1 = (ulonglong)(0 >> sVar3);
  }
  return uVar1;
}


// ==== FUN_00023370 @ 00023370

undefined4 * FUN_00023370(undefined4 *param_1,undefined1 param_2,ulonglong param_3)

{
  ulonglong uVar1;
  longlong lVar2;
  undefined4 *puVar3;
  
  puVar3 = param_1;
  if (3 < param_3) {
    if (((ulonglong)param_1 & 3) != 0) {
      lVar2 = 4 - ((ulonglong)param_1 & 3);
      param_3 = param_3 - lVar2;
      for (; lVar2 != 0; lVar2 = lVar2 + -1) {
        *(undefined1 *)puVar3 = param_2;
        puVar3 = (undefined4 *)((longlong)puVar3 + 1);
      }
    }
    for (uVar1 = param_3 >> 2; uVar1 != 0; uVar1 = uVar1 - 1) {
      *puVar3 = CONCAT22(CONCAT11(param_2,param_2),CONCAT11(param_2,param_2));
      puVar3 = puVar3 + 1;
    }
    param_3 = param_3 & 3;
  }
  for (; param_3 != 0; param_3 = param_3 - 1) {
    *(undefined1 *)puVar3 = param_2;
    puVar3 = (undefined4 *)((longlong)puVar3 + 1);
  }
  return param_1;
}


// ==== FUN_0002337e @ 0002337e

undefined4 * FUN_0002337e(undefined4 *param_1,ulonglong param_2,undefined1 param_3)

{
  ulonglong uVar1;
  longlong lVar2;
  undefined4 *puVar3;
  
  puVar3 = param_1;
  if (3 < param_2) {
    if (((ulonglong)param_1 & 3) != 0) {
      lVar2 = 4 - ((ulonglong)param_1 & 3);
      param_2 = param_2 - lVar2;
      for (; lVar2 != 0; lVar2 = lVar2 + -1) {
        *(undefined1 *)puVar3 = param_3;
        puVar3 = (undefined4 *)((longlong)puVar3 + 1);
      }
    }
    for (uVar1 = param_2 >> 2; uVar1 != 0; uVar1 = uVar1 - 1) {
      *puVar3 = CONCAT22(CONCAT11(param_3,param_3),CONCAT11(param_3,param_3));
      puVar3 = puVar3 + 1;
    }
    param_2 = param_2 & 3;
  }
  for (; param_2 != 0; param_2 = param_2 - 1) {
    *(undefined1 *)puVar3 = param_3;
    puVar3 = (undefined4 *)((longlong)puVar3 + 1);
  }
  return param_1;
}


// ==== FUN_000233d0 @ 000233d0

undefined8 * FUN_000233d0(undefined8 *param_1,undefined8 *param_2,ulonglong param_3)

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


