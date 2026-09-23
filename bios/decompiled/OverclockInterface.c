// OverclockInterface.efi: Ghidra x86:LE:64:default decompile, unedited
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


// ==== FUN_00000310 @ 00000310

int FUN_00000310(int param_1,undefined4 *param_2,undefined4 *param_3,undefined4 *param_4,
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


// ==== FUN_00000380 @ 00000380

void FUN_00000380(void)

{
  return;
}


// ==== FUN_00000390 @ 00000390

ulonglong FUN_00000390(void)

{
  ulonglong uVar1;
  undefined8 in_RAX;
  
  uVar1 = rdtsc();
  return CONCAT44((int)((ulonglong)in_RAX >> 0x20),(int)uVar1) | uVar1 & 0xffffffff00000000;
}


// ==== FUN_000003a0 @ 000003a0

void FUN_000003a0(void)

{
  return;
}


// ==== FUN_000003b0 @ 000003b0

void FUN_000003b0(void)

{
  return;
}


// ==== FUN_000003c0 @ 000003c0

ulonglong FUN_000003c0(void)

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


// ==== entry @ 000003c4

void entry(ulonglong param_1,longlong param_2)

{
  uint uVar1;
  int iVar2;
  longlong lVar3;
  ulonglong uVar4;
  uint uVar5;
  
  DAT_00002330 = *(undefined8 *)(param_2 + 0x60);
  DAT_00002338 = *(undefined8 *)(param_2 + 0x58);
  DAT_00002328 = param_2;
  FUN_00001eb0();
  lVar3 = FUN_00001f1c();
  if (lVar3 == 0) {
    uVar4 = FUN_000003c0();
    FUN_000003b0();
    uVar1 = in(0x1808);
    FUN_00000390();
    while( true ) {
      iVar2 = in(0x1808);
      uVar5 = ((uVar1 & 0xffffff) + 0x16b) - iVar2;
      param_1 = (ulonglong)uVar5;
      if ((uVar5 >> 0x17 & 1) != 0) break;
      FUN_00000380();
    }
    FUN_00000390();
    if ((uVar4 >> 9 & 1) == 0) {
      FUN_000003b0();
    }
    else {
      FUN_000003a0();
    }
  }
  FUN_00000470(param_1,param_2);
  return;
}


// ==== FUN_00000470 @ 00000470

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

undefined8 FUN_00000470(undefined8 param_1,longlong param_2)

{
  longlong lVar1;
  undefined8 uVar2;
  undefined8 local_res8;
  undefined1 local_res10 [24];
  undefined8 uVar3;
  
  uVar3 = 0;
  uVar2 = 0;
  DAT_00002328 = param_2;
  if (param_2 == 0) {
    uVar3 = 0x8000000000000002;
  }
  else {
    DAT_00002330 = *(longlong *)(param_2 + 0x60);
    DAT_00002338 = *(longlong *)(param_2 + 0x58);
    _DAT_00002888 = 0x21d;
    local_res8 = param_1;
    lVar1 = (**(code **)(DAT_00002338 + 0x48))
                      (u_SaSetup_000022b8,&DAT_00002240,0,&DAT_00002888,&DAT_000023a0);
    if (-1 < lVar1) {
      _DAT_00002888 = 699;
      lVar1 = (**(code **)(DAT_00002338 + 0x48))
                        (u_CpuSetup_000022c8,&DAT_000021d0,0,&DAT_00002888,&DAT_000025c0);
      if (((-1 < lVar1) && (DAT_00002777 != '\0')) && (uVar3 = uVar2, DAT_00002778 != '\0')) {
        uVar2 = 0x200;
        (**(code **)(DAT_00002330 + 0x170))(0x200,8,0x5d4,0,&DAT_00002250,local_res10);
        lVar1 = FUN_00000740(uVar2,0xc00,&local_res8);
        if (-1 < lVar1) {
          (**(code **)(DAT_00002330 + 0x140))(&DAT_00002200,0,&DAT_00002398);
          DAT_00002880 = *DAT_00002398;
          *(undefined4 *)(DAT_00002880 + 0x7bf) = (undefined4)local_res8;
          FUN_000007ac();
        }
      }
    }
  }
  return uVar3;
}


// ==== FUN_00000740 @ 00000740

longlong FUN_00000740(undefined8 param_1,ulonglong param_2,undefined8 *param_3)

{
  longlong lVar1;
  undefined8 local_res10 [3];
  
  local_res10[0] = 0xffffffff;
  lVar1 = (**(code **)(DAT_00002330 + 0x28))
                    (1,10,(ulonglong)((param_2 & 0xfff) != 0) + (param_2 >> 0xc),local_res10);
  if (lVar1 < 0) {
    *param_3 = 0;
    lVar1 = -0x7ffffffffffffff7;
  }
  else {
    *param_3 = local_res10[0];
  }
  return lVar1;
}


// ==== FUN_000007ac @ 000007ac

void FUN_000007ac(void)

{
  longlong lVar1;
  ulonglong uVar2;
  longlong lVar3;
  undefined1 local_res8 [8];
  undefined4 local_res10 [2];
  undefined1 local_res18 [8];
  longlong local_res20;
  longlong local_58;
  ulonglong local_50;
  longlong local_48;
  longlong local_40;
  longlong local_38;
  undefined8 *local_30;
  undefined4 local_28;
  undefined4 local_24;
  undefined4 local_20;
  undefined4 local_1c;
  
  local_res20 = 0;
  local_28 = 0x22d85435;
  local_24 = 0x43dbf24a;
  local_20 = 0x5601047d;
  local_1c = 0xb121df06;
  lVar1 = (**(code **)(DAT_00002330 + 0x140))(&DAT_00002210,0,&local_30);
  if (lVar1 == 0) {
    lVar1 = (**(code **)(DAT_00002330 + 0x138))(2,&DAT_000021e0,0,&local_50,&local_48);
    uVar2 = 0;
    if (local_50 != 0) {
      do {
        (**(code **)(DAT_00002330 + 0x98))
                  (*(undefined8 *)(local_48 + uVar2 * 8),&DAT_000021e0,&local_res20);
        local_40 = 0;
        local_res10[0] = 0;
        lVar1 = (**(code **)(local_res20 + 0x10))
                          (local_res20,&local_28,0,&local_40,local_res8,local_res18,local_res10);
        if (lVar1 == 0) break;
        uVar2 = uVar2 + 1;
      } while (uVar2 < local_50);
    }
    (**(code **)(DAT_00002330 + 0x48))(local_48);
    if (local_res20 != 0) {
      lVar3 = 0;
      local_58 = 0;
      while (lVar1 == 0) {
        lVar1 = (**(code **)(local_res20 + 0x18))
                          (local_res20,&local_28,0x19,lVar3,&local_58,&local_40,local_res10);
        if (-1 < lVar1) {
          local_38 = 0;
          lVar1 = (*(code *)*local_30)(local_30,local_58,*(undefined4 *)(local_58 + 4),&local_38);
          local_58 = 0;
          lVar3 = lVar3 + 1;
        }
      }
    }
  }
  return;
}


// ==== FUN_00000928 @ 00000928

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_00000928(void)

{
  ulonglong uVar1;
  ulonglong uVar2;
  byte bVar3;
  ulonglong uVar4;
  undefined8 local_18;
  undefined2 local_10;
  
  uVar4 = 0;
  FUN_00000260(&local_18,10);
  uVar2 = uVar4;
  if (DAT_00002803 != 0) {
    do {
      bVar3 = (char)uVar2 + 1;
      uVar4 = (ulonglong)bVar3;
      *(undefined1 *)((longlong)&local_18 + uVar2) = DAT_00002691;
      uVar2 = uVar4;
    } while (bVar3 < DAT_00002803);
  }
  if ((DAT_00002804 != '\0') && ((byte)(DAT_00002804 - DAT_00002803) != 0)) {
    uVar1 = (ulonglong)(byte)(DAT_00002804 - DAT_00002803);
    uVar2 = uVar4;
    do {
      uVar4 = (ulonglong)(byte)((char)uVar2 + 1);
      *(undefined1 *)((longlong)&local_18 + uVar2) = DAT_00002692;
      uVar1 = uVar1 - 1;
      uVar2 = uVar4;
    } while (uVar1 != 0);
  }
  if ((DAT_00002805 != '\0') && ((byte)(DAT_00002805 - DAT_00002804) != 0)) {
    uVar1 = (ulonglong)(byte)(DAT_00002805 - DAT_00002804);
    uVar2 = uVar4;
    do {
      uVar4 = (ulonglong)(byte)((char)uVar2 + 1);
      *(undefined1 *)((longlong)&local_18 + uVar2) = DAT_00002693;
      uVar1 = uVar1 - 1;
      uVar2 = uVar4;
    } while (uVar1 != 0);
  }
  if ((DAT_00002806 != '\0') && ((byte)(DAT_00002806 - DAT_00002805) != 0)) {
    uVar1 = (ulonglong)(byte)(DAT_00002806 - DAT_00002805);
    uVar2 = uVar4;
    do {
      uVar4 = (ulonglong)(byte)((char)uVar2 + 1);
      *(undefined1 *)((longlong)&local_18 + uVar2) = DAT_00002694;
      uVar1 = uVar1 - 1;
      uVar2 = uVar4;
    } while (uVar1 != 0);
  }
  if ((DAT_00002807 != '\0') && ((byte)(DAT_00002807 - DAT_00002806) != 0)) {
    uVar1 = (ulonglong)(byte)(DAT_00002807 - DAT_00002806);
    uVar2 = uVar4;
    do {
      uVar4 = (ulonglong)(byte)((char)uVar2 + 1);
      *(undefined1 *)((longlong)&local_18 + uVar2) = DAT_00002695;
      uVar1 = uVar1 - 1;
      uVar2 = uVar4;
    } while (uVar1 != 0);
  }
  if ((DAT_00002808 != '\0') && ((byte)(DAT_00002808 - DAT_00002807) != 0)) {
    uVar1 = (ulonglong)(byte)(DAT_00002808 - DAT_00002807);
    uVar2 = uVar4;
    do {
      uVar4 = (ulonglong)(byte)((char)uVar2 + 1);
      *(undefined1 *)((longlong)&local_18 + uVar2) = DAT_00002696;
      uVar1 = uVar1 - 1;
      uVar2 = uVar4;
    } while (uVar1 != 0);
  }
  if ((DAT_00002809 != '\0') && ((byte)(DAT_00002809 - DAT_00002808) != 0)) {
    uVar1 = (ulonglong)(byte)(DAT_00002809 - DAT_00002808);
    uVar2 = uVar4;
    do {
      uVar4 = (ulonglong)(byte)((char)uVar2 + 1);
      *(undefined1 *)((longlong)&local_18 + uVar2) = DAT_00002697;
      uVar1 = uVar1 - 1;
      uVar2 = uVar4;
    } while (uVar1 != 0);
  }
  if ((DAT_0000280a != '\0') && ((byte)(DAT_0000280a - DAT_00002809) != 0)) {
    uVar2 = (ulonglong)(byte)(DAT_0000280a - DAT_00002809);
    do {
      *(undefined1 *)((longlong)&local_18 + uVar4) = DAT_00002698;
      uVar2 = uVar2 - 1;
      uVar4 = (ulonglong)(byte)((char)uVar4 + 1);
    } while (uVar2 != 0);
  }
  _DAT_00002300 = local_18;
  _DAT_00002308 = local_10;
  return;
}


// ==== FUN_00001e14 @ 00001e14

uint FUN_00001e14(void)

{
  uint local_18;
  undefined4 local_14;
  undefined4 local_10;
  undefined4 local_c [3];
  
  FUN_00000310(1,&local_18,&local_14,&local_10,local_c);
  return local_18 & 0xfff0ff0;
}


// ==== FUN_00001e48 @ 00001e48

uint FUN_00001e48(void)

{
  uint local_18;
  undefined4 local_14;
  undefined4 local_10;
  undefined4 local_c [3];
  
  FUN_00000310(1,&local_18,&local_14,&local_10,local_c);
  return local_18 & 0xf;
}


// ==== FUN_00001e7c @ 00001e7c

uint FUN_00001e7c(void)

{
  uint uVar1;
  uint uVar2;
  
  uVar1 = FUN_00001e48();
  uVar2 = FUN_00001e14();
  if ((uVar2 == 0xa0650) && ((uVar1 == 1 || (uVar1 - 4 < 2)))) {
    uVar2 = 0xa0601;
  }
  else {
    uVar2 = uVar2 & 0xffffff00;
  }
  return uVar2;
}


// ==== FUN_00001eb0 @ 00001eb0

longlong FUN_00001eb0(void)

{
  ulonglong uVar1;
  longlong *plVar2;
  
  uVar1 = 0;
  if (DAT_00002340 == 0) {
    DAT_00002340 = 0;
    if (*(ulonglong *)(DAT_00002328 + 0x68) != 0) {
      plVar2 = *(longlong **)(DAT_00002328 + 0x70);
      do {
        if ((DAT_00002230 == *plVar2) && (DAT_00002238 == plVar2[1])) {
          DAT_00002340 = (*(longlong **)(DAT_00002328 + 0x70))[uVar1 * 3 + 2];
          return DAT_00002340;
        }
        uVar1 = uVar1 + 1;
        plVar2 = plVar2 + 3;
      } while (uVar1 < *(ulonglong *)(DAT_00002328 + 0x68));
    }
  }
  return DAT_00002340;
}


// ==== FUN_00001f1c @ 00001f1c

void FUN_00001f1c(void)

{
  short *psVar1;
  
  psVar1 = (short *)FUN_00001eb0();
  do {
    if (*psVar1 == -1) {
      psVar1 = (short *)0x0;
LAB_00001f53:
      if ((psVar1 == (short *)0x0) ||
         ((DAT_00002278 == *(longlong *)(psVar1 + 4) && (DAT_00002280 == *(longlong *)(psVar1 + 8)))
         )) {
        return;
      }
    }
    else if (*psVar1 == 4) goto LAB_00001f53;
    psVar1 = (short *)((longlong)psVar1 + (ulonglong)(ushort)psVar1[1]);
  } while( true );
}


