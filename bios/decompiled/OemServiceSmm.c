// OemServiceSmm.efi: Ghidra x86:LE:64:default decompile, unedited
// ==== FUN_00001000 @ 00001000

undefined8 FUN_00001000(undefined8 *param_1)

{
  undefined8 unaff_RBX;
  undefined8 unaff_RBP;
  undefined8 unaff_RSI;
  undefined8 unaff_RDI;
  undefined8 unaff_R12;
  undefined8 unaff_R13;
  undefined8 unaff_R14;
  undefined8 unaff_R15;
  uint in_CR4;
  longlong in_SSP;
  undefined8 unaff_XMM6_Qa;
  undefined8 unaff_XMM6_Qb;
  undefined8 unaff_XMM7_Qa;
  undefined8 unaff_XMM7_Qb;
  undefined8 unaff_XMM8_Qa;
  undefined8 unaff_XMM8_Qb;
  undefined8 unaff_XMM9_Qa;
  undefined8 unaff_XMM9_Qb;
  undefined8 unaff_XMM10_Qa;
  undefined8 unaff_XMM10_Qb;
  undefined8 unaff_XMM11_Qa;
  undefined8 unaff_XMM11_Qb;
  undefined8 unaff_XMM12_Qa;
  undefined8 unaff_XMM12_Qb;
  undefined8 unaff_XMM13_Qa;
  undefined8 unaff_XMM13_Qb;
  undefined8 unaff_XMM14_Qa;
  undefined8 unaff_XMM14_Qb;
  undefined8 unaff_XMM15_Qa;
  undefined8 unaff_XMM15_Qb;
  undefined8 unaff_retaddr;
  undefined1 auStackX_8 [32];
  
  FUN_00007ecc();
  param_1[0x1f] = 0;
  if ((DAT_0000a2f0 != 0) && ((in_CR4 >> 0x17 & 1) != 0)) {
    param_1[0x1f] = in_SSP + 8;
  }
  *param_1 = unaff_RBX;
  param_1[1] = auStackX_8;
  param_1[2] = unaff_RBP;
  param_1[3] = unaff_RDI;
  param_1[4] = unaff_RSI;
  param_1[5] = unaff_R12;
  param_1[6] = unaff_R13;
  param_1[7] = unaff_R14;
  param_1[8] = unaff_R15;
  param_1[9] = unaff_retaddr;
  *(undefined4 *)(param_1 + 10) = MXCSR;
  param_1[0xb] = unaff_XMM6_Qa;
  param_1[0xc] = unaff_XMM6_Qb;
  param_1[0xd] = unaff_XMM7_Qa;
  param_1[0xe] = unaff_XMM7_Qb;
  param_1[0xf] = unaff_XMM8_Qa;
  param_1[0x10] = unaff_XMM8_Qb;
  param_1[0x11] = unaff_XMM9_Qa;
  param_1[0x12] = unaff_XMM9_Qb;
  param_1[0x13] = unaff_XMM10_Qa;
  param_1[0x14] = unaff_XMM10_Qb;
  param_1[0x15] = unaff_XMM11_Qa;
  param_1[0x16] = unaff_XMM11_Qb;
  param_1[0x17] = unaff_XMM12_Qa;
  param_1[0x18] = unaff_XMM12_Qb;
  param_1[0x19] = unaff_XMM13_Qa;
  param_1[0x1a] = unaff_XMM13_Qb;
  param_1[0x1b] = unaff_XMM14_Qa;
  param_1[0x1c] = unaff_XMM14_Qb;
  param_1[0x1d] = unaff_XMM15_Qa;
  param_1[0x1e] = unaff_XMM15_Qb;
                    /* WARNING: Treating indirect jump as return */
  return 0;
}


// ==== FUN_000010d0 @ 000010d0

void FUN_000010d0(longlong param_1,undefined8 param_2)

{
  MXCSR = *(undefined4 *)(param_1 + 0x50);
                    /* WARNING: Could not recover jumptable at 0x00001179. Too many branches */
                    /* WARNING: Treating indirect jump as call */
  (**(code **)(param_1 + 0x48))(param_1,param_2);
  return;
}


// ==== FUN_00001180 @ 00001180

undefined8 * FUN_00001180(undefined8 *param_1,undefined8 *param_2,ulonglong param_3)

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


// ==== FUN_000011c0 @ 000011c0

undefined8 * FUN_000011c0(undefined8 *param_1,ulonglong param_2)

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


// ==== FUN_000011e0 @ 000011e0

undefined1 * FUN_000011e0(undefined1 *param_1,longlong param_2,undefined1 param_3)

{
  undefined1 *puVar1;
  
  puVar1 = param_1;
  for (; param_2 != 0; param_2 = param_2 + -1) {
    *puVar1 = param_3;
    puVar1 = puVar1 + 1;
  }
  return param_1;
}


// ==== FUN_00001200 @ 00001200

longlong FUN_00001200(char *param_1,char *param_2,longlong param_3)

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


// ==== FUN_00001260 @ 00001260

void FUN_00001260(void)

{
  return;
}


// ==== FUN_00001270 @ 00001270

ulonglong FUN_00001270(void)

{
  ulonglong uVar1;
  undefined8 in_RAX;
  
  uVar1 = rdtsc();
  return CONCAT44((int)((ulonglong)in_RAX >> 0x20),(int)uVar1) | uVar1 & 0xffffffff00000000;
}


// ==== FUN_00001280 @ 00001280

void FUN_00001280(void)

{
  return;
}


// ==== FUN_00001290 @ 00001290

void FUN_00001290(void)

{
  return;
}


// ==== FUN_000012a0 @ 000012a0

ulonglong FUN_000012a0(void)

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


// ==== entry @ 000012b0

ulonglong entry(ulonglong param_1,longlong param_2)

{
  longlong lVar1;
  ulonglong uVar2;
  
  FUN_00001338(param_1,param_2);
  DAT_0000d920 = 0x8000000000000001;
  lVar1 = FUN_00001000((undefined8 *)&DAT_0000d820);
  if (lVar1 == 0) {
    uVar2 = FUN_00001f08(param_1,param_2);
    if ((-1 < (longlong)uVar2) || ((longlong)DAT_0000d920 < 0)) {
      DAT_0000d920 = uVar2;
    }
    FUN_000010d0(0xd820,0xffffffffffffffff);
  }
  uVar2 = DAT_0000d920;
  if ((longlong)DAT_0000d920 < 0) {
    FUN_00008c50();
  }
  return uVar2;
}


// ==== FUN_00001338 @ 00001338

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_00001338(ulonglong param_1,longlong param_2)

{
  uint uVar1;
  int iVar2;
  short *psVar3;
  longlong lVar4;
  longlong *plVar5;
  ulonglong uVar6;
  ulonglong local_res8;
  longlong local_res10;
  longlong local_res18;
  
  DAT_0000d788 = *(longlong *)(param_2 + 0x60);
  local_res10 = 0;
  DAT_0000d780 = param_2;
  local_res8 = param_1;
  (**(code **)(DAT_0000d788 + 0x140))(&DAT_00009080,0,&local_res10);
  (**(code **)(local_res10 + 8))(local_res10,&DAT_0000d790);
  (**(code **)(DAT_0000d788 + 0x140))(&DAT_00009090,0,&local_res18);
  local_res8 = 0;
  lVar4 = local_res18;
  (**(code **)(local_res18 + 0x18))(local_res18,&local_res8,0);
  DAT_0000d930 = FUN_00008c20(lVar4,local_res8);
  (**(code **)(local_res18 + 0x18))(local_res18,&local_res8,DAT_0000d930);
  DAT_0000d928 = local_res8 >> 5;
  FUN_00008c8c();
  psVar3 = (short *)FUN_00008c8c();
LAB_00001419:
  if (*psVar3 == -1) {
    psVar3 = (short *)0x0;
LAB_00001424:
    if (psVar3 == (short *)0x0) {
      uVar6 = FUN_000012a0();
      FUN_00001290();
      uVar1 = in(0x1808);
      FUN_00001270();
      while (iVar2 = in(0x1808), (((uVar1 & 0xffffff) + 0x16b) - iVar2 >> 0x17 & 1) == 0) {
        FUN_00001260();
      }
      FUN_00001270();
      if ((uVar6 >> 9 & 1) == 0) {
        FUN_00001290();
      }
      else {
        FUN_00001280();
      }
LAB_0000148d:
      DAT_0000d7f8 = 1;
      _DAT_0000d800 = 0xe0000000;
      uVar6 = 0;
      plVar5 = *(longlong **)(DAT_0000d790 + 0xa0);
      if (*(ulonglong *)(DAT_0000d790 + 0x98) != 0) {
        do {
          if ((DAT_00009050 == *plVar5) && (DAT_00009058 == plVar5[1])) break;
          uVar6 = uVar6 + 1;
          plVar5 = plVar5 + 3;
        } while (uVar6 < *(ulonglong *)(DAT_0000d790 + 0x98));
      }
      if ((DAT_0000d808 != (undefined8 *)0x0) ||
         (lVar4 = (**(code **)(DAT_0000d788 + 0x140))(&DAT_00009080,0,&DAT_0000d808), -1 < lVar4)) {
        (*(code *)*DAT_0000d808)(DAT_0000d808,&DAT_0000d810);
      }
      return;
    }
    if ((DAT_0000a2e0 == *(longlong *)(psVar3 + 4)) && (DAT_0000a2e8 == *(longlong *)(psVar3 + 8)))
    goto LAB_0000148d;
  }
  else if (*psVar3 == 4) goto LAB_00001424;
  psVar3 = (short *)((longlong)psVar3 + (ulonglong)(ushort)psVar3[1]);
  goto LAB_00001419;
}


// ==== FUN_00001530 @ 00001530

undefined8 FUN_00001530(longlong param_1,char *param_2)

{
  char cVar1;
  longlong lVar2;
  undefined1 *puVar3;
  char *pcVar4;
  ulonglong uVar5;
  
  if ((*(int *)(param_1 + 0x20) == 0) || ((*(byte *)(param_1 + 0x14) & 2) == 0)) {
    puVar3 = (undefined1 *)(param_1 + 0x24);
  }
  else {
    lVar2 = (ulonglong)*(uint *)(param_1 + 0x20) + param_1;
    *(undefined1 *)(lVar2 + 0x24) = 10;
    puVar3 = (undefined1 *)(lVar2 + 0x25);
  }
  *puVar3 = 2;
  uVar5 = 0;
  pcVar4 = puVar3 + 1;
  if (*param_2 != '\0') {
    do {
      uVar5 = uVar5 + 1;
    } while (param_2[uVar5] != '\0');
    if ((uVar5 != 0) && (pcVar4 != param_2)) {
      FUN_00001180((undefined8 *)pcVar4,(undefined8 *)param_2,uVar5);
    }
  }
  lVar2 = 0;
  cVar1 = *param_2;
  while (cVar1 != '\0') {
    lVar2 = lVar2 + 1;
    cVar1 = param_2[lVar2];
  }
  pcVar4[lVar2] = '\x03';
  *(uint *)(param_1 + 0x14) = *(uint *)(param_1 + 0x14) | 2;
  *(int *)(param_1 + 0x20) = ((int)(pcVar4 + lVar2) - (int)param_1) + -0x23;
  return 0;
}


// ==== FUN_000015c4 @ 000015c4

ulonglong FUN_000015c4(longlong param_1,char *param_2)

{
  char cVar1;
  uint uVar2;
  ulonglong in_RAX;
  char *pcVar3;
  ulonglong uVar4;
  longlong lVar5;
  ulonglong uVar6;
  int iVar7;
  ulonglong uVar8;
  ulonglong uVar9;
  char *pcVar10;
  uint uVar11;
  int iVar12;
  uint uVar13;
  
  uVar2 = *(uint *)(param_1 + 0x20);
  uVar9 = 0;
  if (uVar2 != 0) {
    pcVar10 = (char *)(param_1 + 0x24);
    uVar8 = uVar9;
    uVar4 = uVar9;
    do {
      uVar11 = (uint)uVar8;
      iVar12 = (int)uVar4;
      if (*pcVar10 == '\x02') {
        pcVar10 = pcVar10 + 1;
        cVar1 = *pcVar10;
        pcVar3 = pcVar10;
        uVar8 = uVar9;
        while (iVar7 = (int)uVar8, cVar1 != '\x03') {
          pcVar3 = pcVar3 + 1;
          uVar8 = (ulonglong)(iVar7 + 1);
          cVar1 = *pcVar3;
        }
        cVar1 = *param_2;
        uVar4 = uVar9;
        while (cVar1 != '\0') {
          uVar4 = uVar4 + 1;
          cVar1 = param_2[uVar4];
        }
        if ((uVar4 == uVar8) && (lVar5 = FUN_00007e98(pcVar10,param_2,uVar8), lVar5 == 0)) {
          return 1;
        }
        in_RAX = (ulonglong)(iVar7 + 1U);
        uVar13 = iVar12 + 2 + iVar7;
        uVar4 = (ulonglong)uVar13;
        pcVar10 = pcVar10 + (iVar7 + 1U);
        uVar8 = (ulonglong)uVar11;
        if (uVar11 != 0) {
          uVar8 = uVar9;
        }
        uVar6 = uVar9;
        pcVar3 = pcVar10;
        if (*pcVar10 == '\x02') {
          while( true ) {
            iVar12 = (int)uVar6;
            if (pcVar3[1] == '\x03') break;
            uVar6 = (ulonglong)(iVar12 + 1);
            pcVar3 = pcVar3 + 1;
          }
          in_RAX = (ulonglong)(iVar12 + 2U);
          uVar4 = (ulonglong)(uVar13 + 2 + iVar12);
          pcVar10 = pcVar10 + (iVar12 + 2U);
          if ((int)uVar8 != 0) {
            uVar8 = uVar9;
          }
        }
      }
      if (*pcVar10 == '\n') {
        pcVar10 = pcVar10 + 1;
        uVar4 = (ulonglong)((int)uVar4 + 1);
        uVar8 = (ulonglong)((int)uVar8 + 1);
      }
    } while (((int)uVar8 != 3) && ((uint)uVar4 < uVar2));
  }
  return in_RAX & 0xffffffffffffff00;
}


// ==== FUN_000016bc @ 000016bc

char * FUN_000016bc(longlong param_1,char *param_2)

{
  char cVar1;
  uint uVar2;
  char *pcVar3;
  ulonglong uVar4;
  longlong lVar5;
  char *pcVar6;
  bool bVar7;
  ulonglong uVar8;
  uint uVar9;
  ulonglong uVar10;
  int iVar11;
  uint uVar12;
  int iVar13;
  ulonglong uVar14;
  char *local_res8;
  
  uVar2 = *(uint *)(param_1 + 0x20);
  uVar14 = 0;
  local_res8 = (char *)0x0;
  if (uVar2 == 0) {
    return (char *)0x0;
  }
  pcVar6 = (char *)(param_1 + 0x24);
  uVar10 = uVar14;
  uVar4 = uVar14;
  while( true ) {
    uVar9 = (uint)uVar10;
    iVar11 = (int)uVar4;
    bVar7 = false;
    if (*pcVar6 == '\x02') {
      pcVar6 = pcVar6 + 1;
      cVar1 = *pcVar6;
      pcVar3 = pcVar6;
      uVar10 = uVar14;
      while (iVar13 = (int)uVar10, cVar1 != '\x03') {
        pcVar3 = pcVar3 + 1;
        uVar10 = (ulonglong)(iVar13 + 1);
        cVar1 = *pcVar3;
      }
      cVar1 = *param_2;
      uVar4 = uVar14;
      while (cVar1 != '\0') {
        uVar4 = uVar4 + 1;
        cVar1 = param_2[uVar4];
      }
      bVar7 = false;
      if (uVar4 == uVar10) {
        lVar5 = FUN_00007e98(pcVar6,param_2,uVar10);
        bVar7 = false;
        if (lVar5 == 0) {
          bVar7 = true;
        }
      }
      pcVar6 = pcVar6 + (iVar13 + 1);
      uVar12 = iVar11 + 2 + iVar13;
      uVar4 = (ulonglong)uVar12;
      uVar10 = (ulonglong)uVar9;
      if (uVar9 != 0) {
        uVar10 = uVar14;
      }
      uVar8 = uVar14;
      pcVar3 = pcVar6;
      if (*pcVar6 == '\x02') {
        while( true ) {
          iVar11 = (int)uVar8;
          if (pcVar3[1] == '\x03') break;
          uVar8 = (ulonglong)(iVar11 + 1);
          pcVar3 = pcVar3 + 1;
        }
        if (bVar7) {
          uVar2 = iVar11 + 1;
          lVar5 = (**(code **)(DAT_0000d7a0 + 0x50))(6,uVar2,&local_res8);
          if (lVar5 < 0) {
            return (char *)0x0;
          }
          if ((ulonglong)uVar2 != 0) {
            FUN_000011c0((undefined8 *)local_res8,(ulonglong)uVar2);
          }
          if (iVar11 != 0) {
            if (local_res8 != pcVar6 + 1) {
              FUN_00001180((undefined8 *)local_res8,(undefined8 *)(pcVar6 + 1),uVar8);
              return local_res8;
            }
            return local_res8;
          }
          return local_res8;
        }
        pcVar6 = pcVar6 + (iVar11 + 2);
        uVar4 = (ulonglong)(uVar12 + 2 + iVar11);
        if ((int)uVar10 != 0) {
          uVar10 = uVar14;
        }
      }
    }
    if (*pcVar6 == '\n') {
      if (bVar7) {
        return (char *)0x0;
      }
      pcVar6 = pcVar6 + 1;
      uVar4 = (ulonglong)((int)uVar4 + 1);
      uVar10 = (ulonglong)((int)uVar10 + 1);
    }
    if ((int)uVar10 == 3) break;
    if (uVar2 <= (uint)uVar4) {
      return (char *)0x0;
    }
  }
  return (char *)0x0;
}


// ==== FUN_00001824 @ 00001824

char * FUN_00001824(longlong param_1,uint *param_2)

{
  ulonglong uVar1;
  char *pcVar3;
  longlong lVar4;
  char *pcVar5;
  ulonglong uVar6;
  uint uVar7;
  ulonglong uVar8;
  int iVar9;
  ulonglong uVar10;
  char *local_res8;
  ulonglong uVar2;
  
  uVar8 = (ulonglong)*(uint *)(param_1 + 0x20);
  pcVar5 = (char *)(param_1 + 0x24);
  uVar6 = 0;
  local_res8 = (char *)0x0;
  uVar2 = uVar6;
  uVar10 = uVar6;
  if (*(uint *)(param_1 + 0x20) != 0) {
    do {
      iVar9 = (int)uVar2;
      uVar10 = (ulonglong)((int)uVar10 + 1);
      if (*pcVar5 != '\n') {
        uVar10 = uVar6;
      }
      if ((int)uVar10 == 3) {
        pcVar5 = pcVar5 + 1;
        iVar9 = iVar9 + 1;
        uVar2 = uVar6;
        do {
          uVar1 = uVar2 + 1;
          lVar4 = uVar2 + 1;
          uVar2 = uVar1;
        } while (s__File_0000a690[lVar4] != '\0');
        uVar7 = 0;
        if (pcVar5[-5 - uVar1] == '\x02') {
          uVar2 = uVar6;
          for (pcVar3 = pcVar5 + (-4 - uVar1); uVar7 = (uint)uVar2, *pcVar3 != '\x03';
              pcVar3 = pcVar3 + 1) {
            uVar2 = (ulonglong)(uVar7 + 1);
          }
        }
        lVar4 = FUN_00007e98(pcVar5 + (-4 - uVar1),s__File_0000a690,(ulonglong)uVar7);
        if (lVar4 == 0) {
          uVar7 = (int)uVar8 - iVar9;
          *param_2 = uVar7;
          if (uVar7 == 0) {
            return (char *)0x0;
          }
          lVar4 = (**(code **)(DAT_0000d7a0 + 0x50))(6,uVar7,&local_res8);
          if (lVar4 < 0) {
            return (char *)0x0;
          }
          if ((ulonglong)*param_2 != 0) {
            FUN_000011c0((undefined8 *)local_res8,(ulonglong)*param_2);
          }
          if ((ulonglong)*param_2 != 0) {
            if (local_res8 != pcVar5) {
              FUN_00001180((undefined8 *)local_res8,(undefined8 *)pcVar5,(ulonglong)*param_2);
              return local_res8;
            }
            return local_res8;
          }
          return local_res8;
        }
      }
      pcVar5 = pcVar5 + 1;
      uVar2 = (ulonglong)(iVar9 + 1U);
    } while (iVar9 + 1U < (uint)uVar8);
  }
  return (char *)0x0;
}


// ==== FUN_0000192c @ 0000192c

ulonglong FUN_0000192c(byte *param_1)

{
  byte bVar1;
  bool bVar2;
  uint uVar3;
  ulonglong in_RAX;
  undefined7 uVar4;
  undefined7 in_register_00000011;
  bool bVar5;
  bool bVar6;
  
  if (param_1 != (byte *)0x0) {
    if (*param_1 == 0x2d) {
      param_1 = param_1 + 1;
    }
    if (param_1 != (byte *)0x0) {
      do {
        if (*param_1 != 0x30) break;
        param_1 = param_1 + 1;
      } while (param_1 != (byte *)0x0);
      if ((param_1 == (byte *)0x0) ||
         (in_RAX = CONCAT71((int7)(in_RAX >> 8),*param_1 + 0xa8), (*param_1 + 0xa8 & 0xdf) != 0)) {
        bVar2 = false;
      }
      else {
        if (param_1[-1] != 0x30) goto LAB_000019a4;
        param_1 = param_1 + 1;
        bVar2 = true;
      }
      do {
        uVar4 = (undefined7)(in_RAX >> 8);
        if ((param_1 == (byte *)0x0) || (bVar1 = *param_1, (bVar1 & 0xdf) == 0)) {
          return CONCAT71(uVar4,1);
        }
        if (bVar2) {
          in_RAX = CONCAT71(uVar4,bVar1 - 0x30);
          if ((9 < (byte)(bVar1 - 0x30)) &&
             (uVar3 = (int)CONCAT71(in_register_00000011,bVar1) - 0x41, in_RAX = (ulonglong)uVar3,
             5 < (byte)uVar3)) {
            bVar5 = (byte)(bVar1 + 0x9f) < 5;
            bVar6 = (byte)(bVar1 + 0x9f) == 5;
            goto LAB_00001999;
          }
        }
        else {
          bVar5 = (byte)(bVar1 - 0x30) < 9;
          bVar6 = (byte)(bVar1 - 0x30) == 9;
LAB_00001999:
          if (!bVar5 && !bVar6) break;
        }
        param_1 = param_1 + 1;
      } while( true );
    }
  }
LAB_000019a4:
  return in_RAX & 0xffffffffffffff00;
}


// ==== FUN_000019a8 @ 000019a8

ulonglong FUN_000019a8(char *param_1,undefined8 param_2)

{
  char *pcVar1;
  char cVar2;
  undefined7 uVar3;
  ulonglong local_res8 [4];
  
  uVar3 = (undefined7)((ulonglong)param_2 >> 8);
  cVar2 = *param_1;
  pcVar1 = param_1;
  while ((cVar2 != '\0' && (cVar2 == ' '))) {
    pcVar1 = pcVar1 + 1;
    cVar2 = *pcVar1;
  }
  for (; (*pcVar1 != '\0' && (*pcVar1 == '0')); pcVar1 = pcVar1 + 1) {
  }
  if ((*pcVar1 + 0xa8U & 0xdf) == 0) {
    FUN_00007f98(param_1,CONCAT71(uVar3,cVar2),local_res8);
  }
  else {
    FUN_00007ef4(param_1,CONCAT71(uVar3,cVar2),local_res8);
  }
  return local_res8[0];
}


// ==== FUN_000019fc @ 000019fc

void FUN_000019fc(longlong param_1)

{
  if ((ulonglong)*(uint *)(param_1 + 0x20) != 0) {
    FUN_000011c0((undefined8 *)(param_1 + 0x24),(ulonglong)*(uint *)(param_1 + 0x20));
  }
  *(undefined4 *)(param_1 + 0x20) = 0;
  return;
}


// ==== FUN_00001b2c @ 00001b2c

undefined8 FUN_00001b2c(longlong param_1)

{
  char cVar1;
  char *pcVar2;
  longlong lVar3;
  char *pcVar4;
  ulonglong uVar5;
  longlong *plVar6;
  ulonglong uVar7;
  
  pcVar4 = (char *)(param_1 + 0x24);
  uVar5 = 0;
  do {
    *pcVar4 = '\x02';
    uVar7 = 0;
    pcVar2 = *(char **)((longlong)&PTR_DAT_000090e0 + uVar5);
    pcVar4 = pcVar4 + 1;
    if (*pcVar2 != '\0') {
      do {
        uVar7 = uVar7 + 1;
      } while (pcVar2[uVar7] != '\0');
      if ((uVar7 != 0) && (pcVar4 != pcVar2)) {
        FUN_00001180((undefined8 *)pcVar4,(undefined8 *)pcVar2,uVar7);
      }
    }
    lVar3 = 0;
    cVar1 = **(char **)((longlong)&PTR_DAT_000090e0 + uVar5);
    while (cVar1 != '\0') {
      lVar3 = lVar3 + 1;
      cVar1 = (*(char **)((longlong)&PTR_DAT_000090e0 + uVar5))[lVar3];
    }
    pcVar4 = pcVar4 + lVar3;
    *pcVar4 = '\x03';
    *(undefined4 *)(pcVar4 + 1) = *(undefined4 *)((longlong)&DAT_000090f8 + uVar5);
    for (plVar6 = *(longlong **)((longlong)&PTR_DAT_000090f0 + uVar5); *plVar6 != 0;
        plVar6 = (longlong *)((longlong)plVar6 + 0xc)) {
      pcVar4[5] = '\x02';
      uVar7 = 0;
      pcVar2 = (char *)*plVar6;
      pcVar4 = pcVar4 + 6;
      cVar1 = *pcVar2;
      while (cVar1 != '\0') {
        uVar7 = uVar7 + 1;
        cVar1 = pcVar2[uVar7];
      }
      if ((uVar7 != 0) && (pcVar4 != pcVar2)) {
        FUN_00001180((undefined8 *)pcVar4,(undefined8 *)pcVar2,uVar7);
      }
      lVar3 = 0;
      cVar1 = *(char *)*plVar6;
      while (cVar1 != '\0') {
        lVar3 = lVar3 + 1;
        cVar1 = ((char *)*plVar6)[lVar3];
      }
      pcVar4 = pcVar4 + lVar3;
      *pcVar4 = '\x03';
      *(int *)(pcVar4 + 1) = (int)plVar6[1];
    }
    pcVar4[5] = '\n';
    uVar5 = uVar5 + 0x24;
    pcVar4 = pcVar4 + 6;
  } while (uVar5 < 0x318);
  *(int *)(param_1 + 0x20) = ((int)pcVar4 - (int)param_1) + -0x24;
  *(undefined4 *)(param_1 + 0x14) = 0x16;
  return 0;
}


// ==== FUN_00001c4c @ 00001c4c

undefined8 FUN_00001c4c(void)

{
  longlong lVar1;
  int *piVar2;
  uint uVar3;
  ulonglong uVar4;
  
  lVar1 = DAT_0000d770;
  uVar4 = 0;
  if (DAT_0000d770 != 0) {
    if (*(int *)(DAT_0000d770 + 0x10) == 1) {
      if ((uint)*(byte *)(DAT_0000d770 + 0x24) * 0x100 + (uint)*(byte *)(DAT_0000d770 + 0x25) == 0)
      {
        if ((ulonglong)*(uint *)(DAT_0000d770 + 0x20) != 0) {
          FUN_000011c0((undefined8 *)(DAT_0000d770 + 0x24),(ulonglong)*(uint *)(DAT_0000d770 + 0x20)
                      );
        }
        *(undefined4 *)(lVar1 + 0x14) = 2;
        *(undefined8 *)(lVar1 + 0x18) = 0x8000000000000003;
        FUN_00001530(lVar1,s_Unsupported_tool_version__0000a6b8);
      }
      else {
        *(undefined8 *)(DAT_0000d770 + 0x18) = 0;
        *(undefined4 *)(lVar1 + 0x14) = 0;
        FUN_00001b2c(lVar1);
      }
    }
    else {
      piVar2 = &DAT_000090f8;
      do {
        if (*(int *)(DAT_0000d770 + 0x10) == *piVar2) {
          (**(code **)((longlong)&PTR_LAB_000090fc + uVar4 * 0x24))(DAT_0000d770);
          return 0;
        }
        uVar3 = (int)uVar4 + 1;
        uVar4 = (ulonglong)uVar3;
        piVar2 = piVar2 + 9;
      } while (uVar3 < 0x16);
    }
  }
  return 0;
}


// ==== FUN_00001cfc @ 00001cfc

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

ulonglong FUN_00001cfc(undefined8 param_1,longlong param_2)

{
  ulonglong uVar1;
  longlong lVar2;
  uint *puVar3;
  uint uVar4;
  char local_res18 [8];
  undefined8 local_res20;
  undefined1 *local_28;
  undefined8 *local_20;
  undefined8 local_18;
  undefined1 local_10 [8];
  ulonglong uVar5;
  
  uVar5 = 0;
  local_18 = 0;
  if (DAT_0000d7e8 == 0) {
    DAT_0000d798 = *(longlong *)(param_2 + 0x60);
    DAT_0000d7d0 = *(longlong *)(param_2 + 0x58);
    DAT_0000d7e8 = param_2;
  }
  uVar1 = uVar5;
  if ((((DAT_0000d7d8 != (undefined8 *)0x0) ||
       (uVar1 = (**(code **)(DAT_0000d798 + 0x140))(&DAT_00009e18,0,&DAT_0000d7d8),
       -1 < (longlong)uVar1)) &&
      ((*(code *)*DAT_0000d7d8)(DAT_0000d7d8,local_res18), local_res18[0] != '\0')) &&
     (uVar1 = (*(code *)DAT_0000d7d8[1])(DAT_0000d7d8,&DAT_0000d7a0), -1 < (longlong)uVar1)) {
    lVar2 = FUN_000084fc();
    DAT_0000d7a8 = 1;
    if (lVar2 != 0) {
      DAT_0000d7d0 = lVar2;
    }
    DAT_0000d7b8 = 0;
    FUN_00008390();
    uVar1 = FUN_00008418();
    DAT_0000d7b8 = 1;
  }
  if (-1 < (longlong)uVar1) {
    uVar1 = (**(code **)(DAT_0000d798 + 0x140))(&DAT_00009020,0,&DAT_0000d778);
    if ((longlong)uVar1 < 0) {
      DAT_0000d778 = 0;
    }
    else {
      uVar1 = (**(code **)(DAT_0000d798 + 0x140))(&DAT_00009060,0,&local_28);
      if ((-1 < (longlong)uVar1) &&
         (uVar1 = (**(code **)(DAT_0000d7a0 + 0xd0))(&DAT_000090a0,0,&local_20),
         -1 < (longlong)uVar1)) {
        local_res20 = 0xffffffffffffffff;
        uVar1 = (*(code *)*local_20)(local_20,FUN_00001c4c,&local_res20,local_10);
        if (-1 < (longlong)uVar1) {
          *local_28 = (undefined1)local_res20;
          puVar3 = &DAT_000090f8;
          DAT_0000d770 = *(undefined8 *)(local_28 + 8);
          do {
            if ((short)*puVar3 == -1) {
              *(undefined2 *)puVar3 = 0;
              *puVar3 = *puVar3 | (int)uVar5 + 1U | 0x80000000;
            }
            uVar4 = (int)uVar5 + 1;
            uVar5 = (ulonglong)uVar4;
            puVar3 = puVar3 + 9;
          } while (uVar4 < 0x16);
          DAT_000090c0 = (undefined1)local_res20;
          _DAT_000090c8 = *(undefined8 *)(local_28 + 8);
          uVar1 = (**(code **)(DAT_0000d7a0 + 0xa8))(&local_18,&DAT_00009000,0,&DAT_000090c0);
        }
      }
    }
  }
  return uVar1;
}


// ==== FUN_00001f08 @ 00001f08

ulonglong FUN_00001f08(undefined8 param_1,longlong param_2)

{
  ulonglong uVar1;
  longlong lVar2;
  char local_res18 [16];
  
  if (DAT_0000d7e8 == 0) {
    DAT_0000d798 = *(longlong *)(param_2 + 0x60);
    DAT_0000d7d0 = *(longlong *)(param_2 + 0x58);
    DAT_0000d7e8 = param_2;
  }
  local_res18[0] = '\0';
  if (DAT_0000d7e8 == 0) {
    DAT_0000d798 = *(longlong *)(param_2 + 0x60);
    DAT_0000d7d0 = *(longlong *)(param_2 + 0x58);
    DAT_0000d7e8 = param_2;
  }
  uVar1 = (**(code **)(DAT_0000d798 + 0x140))(&DAT_00009e18,0,&DAT_0000d7d8);
  if (((-1 < (longlong)uVar1) &&
      ((*(code *)*DAT_0000d7d8)(DAT_0000d7d8,local_res18), local_res18[0] != '\0')) &&
     (uVar1 = (*(code *)DAT_0000d7d8[1])(DAT_0000d7d8,&DAT_0000d7a0), -1 < (longlong)uVar1)) {
    lVar2 = FUN_000084fc();
    DAT_0000d7a8 = 1;
    if (lVar2 != 0) {
      DAT_0000d7d0 = lVar2;
    }
    DAT_0000d7b8 = 0;
    FUN_00008390();
    FUN_00008418();
    DAT_0000d7b8 = 1;
    uVar1 = FUN_00001cfc(param_1,param_2);
  }
  return uVar1;
}


// ==== FUN_00002028 @ 00002028

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_00002028(longlong param_1,int param_2)

{
  byte *pbVar1;
  undefined8 uVar2;
  ulonglong uVar3;
  char *pcVar4;
  ushort uVar5;
  longlong lVar6;
  ushort local_res10 [4];
  byte local_88 [128];
  
  if (param_2 == 0) {
    uVar5 = _DAT_ff43000b;
    if (0x4b0 < _DAT_ff43000b) {
      uVar5 = 0;
    }
    FUN_000019fc(param_1);
    pbVar1 = &DAT_0000a6fc;
  }
  else {
    if (param_2 != 1) {
      if (param_2 == 2) {
        pcVar4 = s__SetGC_0000a6ec;
        pbVar1 = (byte *)FUN_000016bc(param_1,s__SetGC_0000a6ec);
        uVar2 = FUN_0000192c(pbVar1);
        if ((char)uVar2 == '\0') {
          (**(code **)(DAT_0000d7a0 + 0x58))();
          FUN_000019fc(param_1);
          FUN_00001530(param_1,s__SetGC__Set_GPU_OverClocking__Ma_0000a750);
          pcVar4 = s_Sample___Set_120__>_OverClocking_0000a788;
        }
        else {
          uVar3 = FUN_000019a8((char *)pbVar1,pcVar4);
          uVar5 = (ushort)uVar3;
          FUN_000019fc(param_1);
          if (uVar5 < 0x4b1) {
            lVar6 = 0xb;
            goto LAB_00002142;
          }
          (**(code **)(DAT_0000d7a0 + 0x58))(pbVar1);
          FUN_000019fc(param_1);
          FUN_00001530(param_1,s_GPU_OverClocking__Maxmum_is_1200_0000a708);
          pcVar4 = s_please_type_number_0_1200_0000a730;
        }
      }
      else {
        if (param_2 != 3) {
          return;
        }
        pcVar4 = s__SetMC_0000a6f4;
        pbVar1 = (byte *)FUN_000016bc(param_1,s__SetMC_0000a6f4);
        uVar2 = FUN_0000192c(pbVar1);
        if ((char)uVar2 == '\0') {
          (**(code **)(DAT_0000d7a0 + 0x58))();
          FUN_000019fc(param_1);
          FUN_00001530(param_1,s__SetMC__Set_VRAM_OverClocking__M_0000a808);
          pcVar4 = s_Sample___Set_150__>_OverClocking_0000a840;
        }
        else {
          uVar3 = FUN_000019a8((char *)pbVar1,pcVar4);
          FUN_000019fc(param_1);
          uVar5 = (ushort)uVar3;
          if (uVar5 < 0x3e9) {
            lVar6 = 0xd;
LAB_00002142:
            local_res10[0] = uVar5;
            lVar6 = FUN_00002648((longlong)local_res10,2,lVar6);
            FUN_00004614(param_1,lVar6);
            (**(code **)(DAT_0000d7a0 + 0x58))(pbVar1);
            return;
          }
          (**(code **)(DAT_0000d7a0 + 0x58))(pbVar1);
          FUN_000019fc(param_1);
          FUN_00001530(param_1,s_VRAM_OverClocking__Maxmum_is_100_0000a7c0);
          pcVar4 = s_please_type_number_0_1000_0000a7e8;
        }
      }
      goto LAB_0000223d;
    }
    uVar5 = _DAT_ff43000d;
    if (1000 < _DAT_ff43000d) {
      uVar5 = 0;
    }
    FUN_000019fc(param_1);
    pbVar1 = &DAT_0000a700;
  }
  FUN_00008b40(local_88,0x80,pbVar1,(ulonglong)uVar5);
  pcVar4 = (char *)local_88;
LAB_0000223d:
  FUN_00001530(param_1,pcVar4);
  return;
}


// ==== FUN_0000225c @ 0000225c

void FUN_0000225c(longlong param_1)

{
  *(undefined4 *)(param_1 + 0x14) = 2;
  FUN_000019fc(param_1);
  FUN_00001530(param_1,s__Help___Display_OC_command__0000a878);
  FUN_00001530(param_1,s__GetGC___Display_current_GPU_ove_0000a898);
  FUN_00001530(param_1,s__GetMC___Display_current_GPU_mem_0000a8d0);
  FUN_00001530(param_1,s__SetGC___Set_GPU_overclocking_0000a910);
  FUN_00001530(param_1,s__SetMC___Set_GPU_memory_overcloc_0000a938);
  return;
}


// ==== FUN_000022c4 @ 000022c4

undefined8 FUN_000022c4(longlong param_1)

{
  undefined8 uVar1;
  int iVar2;
  
  uVar1 = FUN_000015c4(param_1,s__GetGC_0000a6dc);
  if ((char)uVar1 == '\0') {
    uVar1 = FUN_000015c4(param_1,s__GetMC_0000a6e4);
    if ((char)uVar1 == '\0') {
      uVar1 = FUN_000015c4(param_1,s__SetGC_0000a6ec);
      if ((char)uVar1 == '\0') {
        uVar1 = FUN_000015c4(param_1,s__SetMC_0000a6f4);
        if ((char)uVar1 == '\0') {
          FUN_000015c4(param_1,s__Help_0000a6d4);
          *(undefined8 *)(param_1 + 0x18) = 0;
          FUN_0000225c(param_1);
          return 0;
        }
        *(undefined8 *)(param_1 + 0x18) = 0;
        iVar2 = 3;
      }
      else {
        *(undefined8 *)(param_1 + 0x18) = 0;
        iVar2 = 2;
      }
    }
    else {
      *(undefined8 *)(param_1 + 0x18) = 0;
      iVar2 = 1;
    }
  }
  else {
    *(undefined8 *)(param_1 + 0x18) = 0;
    iVar2 = 0;
  }
  FUN_00002028(param_1,iVar2);
  return 0;
}


// ==== FUN_0000236c @ 0000236c

void FUN_0000236c(longlong param_1,int param_2)

{
  longlong lVar1;
  byte *pbVar2;
  undefined8 uVar3;
  ulonglong uVar4;
  char *pcVar5;
  byte bVar6;
  byte local_res10 [8];
  byte local_88 [128];
  
  if (param_2 == 0) {
    bVar6 = DAT_ff43000f;
    if (0x7f < DAT_ff43000f) {
      bVar6 = 0;
    }
    FUN_000019fc(param_1);
    FUN_00008b40(local_88,0x80,&DAT_0000a6fc,(ulonglong)bVar6);
    pcVar5 = (char *)local_88;
  }
  else {
    if (param_2 != 1) {
      if (param_2 != 2) {
        return;
      }
      local_res10[0] = 0;
      lVar1 = FUN_00002648((longlong)local_res10,1,0xf);
      FUN_00004614(param_1,lVar1);
      return;
    }
    pcVar5 = s__SetBID_0000a970;
    pbVar2 = (byte *)FUN_000016bc(param_1,s__SetBID_0000a970);
    uVar3 = FUN_0000192c(pbVar2);
    if ((char)uVar3 == '\0') {
      (**(code **)(DAT_0000d7a0 + 0x58))();
      FUN_000019fc(param_1);
      pcVar5 = s__SetBID__SW_Board_ID_Maxmum_valu_0000a9e8;
    }
    else {
      uVar4 = FUN_000019a8((char *)pbVar2,pcVar5);
      FUN_000019fc(param_1);
      local_res10[0] = (byte)uVar4;
      if (local_res10[0] < 0x80) {
        lVar1 = FUN_00002648((longlong)local_res10,1,0xf);
        FUN_00004614(param_1,lVar1);
        FUN_00008b40(local_88,0x80,(byte *)s_Set_Board_ID_is__x_0000a988,uVar4 & 0xff);
        FUN_00001530(param_1,(char *)local_88);
        (**(code **)(DAT_0000d7a0 + 0x58))(pbVar2);
        return;
      }
      (**(code **)(DAT_0000d7a0 + 0x58))(pbVar2);
      FUN_000019fc(param_1);
      FUN_00001530(param_1,s_SW_Board_ID_Maxmum_value_is_0x7F_0000a9a0);
      pcVar5 = s_Please_type_number_0_0x7F_0000a9c8;
    }
  }
  FUN_00001530(param_1,pcVar5);
  return;
}


// ==== FUN_000024f0 @ 000024f0

void FUN_000024f0(longlong param_1)

{
  *(undefined4 *)(param_1 + 0x14) = 2;
  FUN_000019fc(param_1);
  FUN_00001530(param_1,s__Help___Display_SW_board_ID_comm_0000aa18);
  FUN_00001530(param_1,s__GetBID___Display_current_SW_boa_0000aa48);
  FUN_00001530(param_1,s__SetBID___Set_SW_Board_ID_value_0000aa80);
  FUN_00001530(param_1,s__ClearBID___Clear_SW_Board_ID_va_0000aaa8);
  FUN_00001530(param_1,s__________________________________0000aad0);
  FUN_00001530(param_1,s________SW_Board_ID_table_________0000aaf8);
  FUN_00001530(param_1,s__________________________________0000aad0);
  FUN_00001530(param_1,s____BIT0__LCD_Q_key____0000ab20);
  FUN_00001530(param_1,s____BIT1__EC_Battery_Boost____0000ab48);
  FUN_00001530(param_1,s__________________________________0000aad0);
  return;
}


// ==== FUN_00002648 @ 00002648

undefined8 FUN_00002648(longlong param_1,uint param_2,longlong param_3)

{
  undefined8 *puVar1;
  undefined8 uVar2;
  longlong lVar3;
  ulonglong uVar4;
  undefined8 *puVar5;
  ulonglong uVar6;
  ulonglong uVar7;
  longlong lVar8;
  ulonglong uVar9;
  ulonglong uVar10;
  ulonglong uVar11;
  undefined8 local_1018 [512];
  
  uVar9 = (ulonglong)param_2;
  uVar7 = (ulonglong)((uint)param_3 & 0xfff);
  uVar6 = 0;
  if (DAT_0000d778 == (undefined8 *)0x0) {
    uVar2 = 0x8000000000000001;
  }
  else if (uVar9 + param_3 < 0x22001) {
    (*(code *)DAT_0000d778[4])();
    if (param_2 != 0) {
      lVar8 = (param_3 - uVar7) + 0xff430000;
      do {
        lVar3 = (*(code *)*DAT_0000d778)(lVar8,0x1000,local_1018);
        if (lVar3 < 0) {
          return 0x8000000000000007;
        }
        uVar10 = (ulonglong)((uint)uVar7 & 0xfff);
        puVar1 = (undefined8 *)(uVar6 + param_1);
        uVar4 = 0x1000 - uVar10;
        puVar5 = (undefined8 *)((longlong)local_1018 + uVar10);
        uVar11 = uVar9 - uVar6;
        if (uVar11 < uVar4) {
          uVar6 = uVar9;
          if ((uVar11 != 0) && (puVar5 != puVar1)) {
            FUN_00001180(puVar5,puVar1,uVar11);
          }
        }
        else {
          if ((uVar4 != 0) && (puVar5 != puVar1)) {
            FUN_00001180(puVar5,puVar1,uVar4);
          }
          uVar6 = uVar6 + (0x1000 - uVar10);
        }
        lVar3 = (*(code *)DAT_0000d778[1])(lVar8,0x1000);
        if (lVar3 < 0) {
          return 0x8000000000000007;
        }
        lVar3 = (*(code *)DAT_0000d778[2])(lVar8,0x1000,local_1018);
        if (lVar3 < 0) {
          return 0x8000000000000007;
        }
        lVar8 = lVar8 + 0x1000;
        uVar7 = uVar7 + uVar6;
      } while (uVar9 != uVar6);
    }
    (*(code *)DAT_0000d778[5])();
    uVar2 = 0;
  }
  else {
    uVar2 = 0x8000000000000004;
  }
  return uVar2;
}


// ==== FUN_000027bc @ 000027bc

undefined8 FUN_000027bc(undefined8 *param_1,uint param_2,longlong param_3)

{
  undefined8 uVar1;
  ulonglong uVar2;
  
  if ((param_1 == (undefined8 *)0x0) || (uVar2 = (ulonglong)param_2, 0x22000 < uVar2 + param_3)) {
    uVar1 = 0x8000000000000002;
  }
  else {
    if ((uVar2 != 0) && (param_1 != (undefined8 *)(param_3 + 0xff430000))) {
      FUN_00001180(param_1,(undefined8 *)(param_3 + 0xff430000),uVar2);
    }
    uVar1 = 0;
  }
  return uVar1;
}


// ==== FUN_00002804 @ 00002804

void FUN_00002804(undefined1 param_1)

{
  longlong lVar1;
  undefined4 local_res10 [2];
  undefined8 local_res18;
  undefined8 *local_res20;
  undefined1 local_c8 [14];
  undefined1 local_ba;
  
  local_res18 = 0xb4;
  local_res10[0] = 7;
  lVar1 = (**(code **)(DAT_0000d790 + 0xd0))(&DAT_00009040,0,&local_res20);
  if (-1 < lVar1) {
    lVar1 = (*(code *)*local_res20)
                      (u_UniWillVariable_0000ab80,&DAT_000090b0,local_res10,&local_res18,local_c8);
    if (-1 < lVar1) {
      local_ba = param_1;
      (*(code *)local_res20[2])
                (u_UniWillVariable_0000ab80,&DAT_000090b0,local_res10[0],local_res18,local_c8);
    }
  }
  return;
}


// ==== FUN_000028ac @ 000028ac

void FUN_000028ac(longlong param_1,int param_2)

{
  byte bVar1;
  byte *pbVar2;
  undefined8 uVar3;
  ulonglong uVar4;
  longlong lVar5;
  char *pcVar6;
  undefined1 local_res10 [8];
  byte local_88 [128];
  
  bVar1 = DAT_ff430012;
  if (param_2 == 0) {
    pcVar6 = s__SetTDR_0000ab70;
    pbVar2 = (byte *)FUN_000016bc(param_1,s__SetTDR_0000ab70);
    uVar3 = FUN_0000192c(pbVar2);
    if ((char)uVar3 != '\0') {
      uVar4 = FUN_000019a8((char *)pbVar2,pcVar6);
      FUN_000019fc(param_1);
      local_res10[0] = (char)uVar4;
      lVar5 = FUN_00002648((longlong)local_res10,1,0x12);
      FUN_00004614(param_1,lVar5);
      FUN_00008b40(local_88,0x80,(byte *)s_Set_OemTDR_is__03d_0000aba8,uVar4 & 0xff);
      FUN_00001530(param_1,(char *)local_88);
      FUN_00002804((char)uVar4);
      (**(code **)(DAT_0000d7a0 + 0x58))(pbVar2);
      return;
    }
    (**(code **)(DAT_0000d7a0 + 0x58))();
    FUN_000019fc(param_1);
    pcVar6 = s__SetTDR__Set_OemTDR_value_from_0_0000abc0;
  }
  else {
    if (param_2 != 1) {
      return;
    }
    FUN_000019fc(param_1);
    FUN_00008b40(local_88,0x80,&DAT_0000aba0,(ulonglong)bVar1);
    pcVar6 = (char *)local_88;
  }
  FUN_00001530(param_1,pcVar6);
  return;
}


// ==== FUN_000029cc @ 000029cc

void FUN_000029cc(longlong param_1)

{
  *(undefined4 *)(param_1 + 0x14) = 2;
  FUN_000019fc(param_1);
  FUN_00001530(param_1,s__Help___Display_OemTDR_command__0000abf0);
  FUN_00001530(param_1,s__GetTDR___Display_current_TDR_va_0000ac18);
  FUN_00001530(param_1,s__SetTDR___Set_TDR_value__0000ac40);
  return;
}


// ==== FUN_00002ac4 @ 00002ac4

void FUN_00002ac4(longlong param_1)

{
  longlong lVar1;
  longlong lVar2;
  uint *puVar3;
  byte local_108 [256];
  
  FUN_000019fc(param_1);
  FUN_00001530(param_1,s__Help___Display_all__Notebook_Ty_0000ad50);
  FUN_00001530(param_1,s__Type___Get_current__Notebook_Ty_0000ad80);
  FUN_00001530(param_1,s__Set___Set_Notebook_Type__suppor_0000adb0);
  puVar3 = &DAT_00009518;
  lVar1 = 2;
  do {
    FUN_00008b40(local_108,0x100,(byte *)s__Set__d__>__s_0000ade0,(ulonglong)*puVar3);
    FUN_00001530(param_1,(char *)local_108);
    puVar3 = puVar3 + 3;
    lVar1 = lVar1 + -1;
  } while (lVar1 != 0);
  FUN_00001530(param_1,s__Mode___Set_Notebook_Mode__suppo_0000adf0);
  lVar2 = 4;
  puVar3 = &DAT_00009538;
  lVar1 = 4;
  do {
    FUN_00008b40(local_108,0x100,(byte *)s__Mode__d__>__s_0000ae20,(ulonglong)*puVar3);
    FUN_00001530(param_1,(char *)local_108);
    puVar3 = puVar3 + 3;
    lVar1 = lVar1 + -1;
  } while (lVar1 != 0);
  FUN_00001530(param_1,s__Table___Set_Myfan3_Mode__suppor_0000ae38);
  puVar3 = &DAT_00009658;
  do {
    FUN_00008b40(local_108,0x100,(byte *)s__Table__d__>__s_0000ae68,(ulonglong)*puVar3);
    FUN_00001530(param_1,(char *)local_108);
    puVar3 = puVar3 + 3;
    lVar2 = lVar2 + -1;
  } while (lVar2 != 0);
  return;
}


// ==== FUN_00002c20 @ 00002c20

void FUN_00002c20(longlong param_1)

{
  byte bVar1;
  char *pcVar2;
  byte bVar3;
  ulonglong uVar4;
  uint uVar5;
  undefined8 uVar6;
  byte local_res10 [24];
  byte local_108 [256];
  
  (*(code *)PTR_FUN_000090d8)(local_res10,1,0x34);
  bVar1 = 0;
  uVar5 = (uint)local_res10[0];
  bVar3 = 0;
  do {
    if (uVar5 == (&DAT_00009518)[(ulonglong)bVar3 * 3]) {
      pcVar2 = s_Current_Notebook_Type___s_0000ae80;
      uVar6 = *(undefined8 *)((longlong)&PTR_s_Standard_00009510 + (ulonglong)bVar3 * 0xc);
      goto LAB_00002d2e;
    }
    bVar3 = bVar3 + 1;
  } while (bVar3 < 2);
  uVar4 = 0;
  do {
    if (uVar5 == (&DAT_00009658)[uVar4 * 3]) {
      uVar6 = *(undefined8 *)((longlong)&PTR_s_SwitchTable1Office_00009650 + uVar4 * 0xc);
      goto LAB_00002cfc;
    }
    bVar3 = (char)uVar4 + 1;
    uVar4 = (ulonglong)bVar3;
  } while (bVar3 < 4);
LAB_00002c96:
  if ((uVar5 != ((&DAT_00009538)[(ulonglong)bVar1 * 3] & 0xf)) &&
     (uVar5 != (&DAT_00009538)[(ulonglong)bVar1 * 3])) goto code_r0x00002cb5;
  uVar6 = *(undefined8 *)((longlong)&PTR_s_FanOfficeMode_00009530 + (ulonglong)bVar1 * 0xc);
LAB_00002cfc:
  pcVar2 = s_Current_Notebook_Mode___s_0000aea0;
LAB_00002d2e:
  FUN_00008b40(local_108,0x100,(byte *)pcVar2,uVar6);
  FUN_000019fc(param_1);
  pcVar2 = (char *)local_108;
  goto LAB_00002d4a;
code_r0x00002cb5:
  bVar1 = bVar1 + 1;
  if (3 < bVar1) {
    if (((byte)(local_res10[0] - 2) < 0x12) || (0x17 < local_res10[0])) {
      *(undefined8 *)(param_1 + 0x18) = 0x8000000000000002;
      FUN_000019fc(param_1);
      pcVar2 = s_ERROR__invalid_Notebook_Type__0000aec0;
LAB_00002d4a:
      FUN_00001530(param_1,pcVar2);
    }
    return;
  }
  goto LAB_00002c96;
}


// ==== FUN_00002d5c @ 00002d5c

void FUN_00002d5c(longlong param_1)

{
  byte *pbVar1;
  undefined8 uVar2;
  ulonglong uVar3;
  undefined *puVar4;
  longlong lVar5;
  byte bVar6;
  uint *puVar7;
  byte local_res10 [8];
  byte local_118 [256];
  
  puVar4 = &DAT_0000ad34;
  pbVar1 = (byte *)FUN_000016bc(param_1,&DAT_0000ad34);
  uVar2 = FUN_0000192c(pbVar1);
  lVar5 = 2;
  if ((char)uVar2 == '\x01') {
    uVar3 = FUN_000019a8((char *)pbVar1,puVar4);
    local_res10[0] = (byte)uVar3;
    (**(code **)(DAT_0000d7a0 + 0x58))(pbVar1);
    uVar3 = 0;
    do {
      if ((uint)local_res10[0] == (&DAT_00009518)[uVar3 * 3]) {
        (*(code *)PTR_FUN_000090d0)(local_res10,1,0x34);
        FUN_00008b40(local_118,0x100,(byte *)s_Set_Notebook_Type___s_s_0000aef0,
                     *(undefined8 *)((longlong)&PTR_s_Standard_00009510 + uVar3 * 0xc));
        FUN_000019fc(param_1);
        FUN_00001530(param_1,(char *)local_118);
        return;
      }
      bVar6 = (char)uVar3 + 1;
      uVar3 = (ulonglong)bVar6;
    } while (bVar6 < 2);
  }
  FUN_000019fc(param_1);
  *(undefined8 *)(param_1 + 0x18) = 0x8000000000000002;
  FUN_00001530(param_1,s_invalid_parameter__supported_val_0000af08);
  puVar7 = &DAT_00009518;
  do {
    FUN_00008b40(local_118,0x100,(byte *)s__Set__d__>__s_0000ade0,(ulonglong)*puVar7);
    FUN_00001530(param_1,(char *)local_118);
    puVar7 = puVar7 + 3;
    lVar5 = lVar5 + -1;
  } while (lVar5 != 0);
  (**(code **)(DAT_0000d7a0 + 0x58))(pbVar1);
  return;
}


// ==== FUN_00002ed4 @ 00002ed4

void FUN_00002ed4(longlong param_1)

{
  byte *pbVar1;
  undefined8 uVar2;
  ulonglong uVar3;
  char *pcVar4;
  longlong lVar5;
  byte bVar6;
  uint *puVar7;
  byte local_res10 [8];
  byte local_118 [256];
  
  pcVar4 = s__Mode_0000ad3c;
  pbVar1 = (byte *)FUN_000016bc(param_1,s__Mode_0000ad3c);
  uVar2 = FUN_0000192c(pbVar1);
  lVar5 = 4;
  if ((char)uVar2 == '\x01') {
    uVar3 = FUN_000019a8((char *)pbVar1,pcVar4);
    local_res10[0] = (byte)uVar3;
    (**(code **)(DAT_0000d7a0 + 0x58))(pbVar1);
    uVar3 = 0;
    do {
      if ((uint)local_res10[0] == (&DAT_00009538)[uVar3 * 3]) {
        (*(code *)PTR_FUN_000090d0)(local_res10,1,0x34);
        FUN_00008b40(local_118,0x100,(byte *)s_Set_Notebook_Mode___s_s_0000af30,
                     *(undefined8 *)((longlong)&PTR_s_FanOfficeMode_00009530 + uVar3 * 0xc));
        FUN_000019fc(param_1);
        FUN_00001530(param_1,(char *)local_118);
        return;
      }
      bVar6 = (char)uVar3 + 1;
      uVar3 = (ulonglong)bVar6;
    } while (bVar6 < 4);
  }
  FUN_000019fc(param_1);
  *(undefined8 *)(param_1 + 0x18) = 0x8000000000000002;
  FUN_00001530(param_1,s_invalid_parameter__supported_val_0000af08);
  puVar7 = &DAT_00009538;
  do {
    FUN_00008b40(local_118,0x100,(byte *)s__Mode__d__>__s_0000ae20,(ulonglong)*puVar7);
    FUN_00001530(param_1,(char *)local_118);
    puVar7 = puVar7 + 3;
    lVar5 = lVar5 + -1;
  } while (lVar5 != 0);
  (**(code **)(DAT_0000d7a0 + 0x58))(pbVar1);
  return;
}


// ==== FUN_0000304c @ 0000304c

void FUN_0000304c(longlong param_1)

{
  byte *pbVar1;
  undefined8 uVar2;
  ulonglong uVar3;
  char *pcVar4;
  undefined1 uVar5;
  byte bVar6;
  uint *puVar7;
  longlong lVar8;
  byte local_res10 [8];
  undefined4 local_res18 [2];
  undefined8 local_res20;
  undefined8 *local_208 [2];
  undefined1 local_1f8 [47];
  undefined1 local_1c9;
  byte local_138 [256];
  
  pcVar4 = s__Table_0000ad44;
  pbVar1 = (byte *)FUN_000016bc(param_1,s__Table_0000ad44);
  uVar2 = FUN_0000192c(pbVar1);
  lVar8 = 4;
  if ((char)uVar2 == '\x01') {
    uVar3 = FUN_000019a8((char *)pbVar1,pcVar4);
    local_res10[0] = (byte)uVar3;
    (**(code **)(DAT_0000d7a0 + 0x58))(pbVar1);
    uVar3 = 0;
    do {
      if ((uint)local_res10[0] == (&DAT_00009658)[uVar3 * 3]) {
        (*(code *)PTR_FUN_000090d0)(local_res10,1,0x34);
        bVar6 = local_res10[0];
        local_res20 = 0xb4;
        local_res18[0] = 7;
        uVar5 = 0;
        lVar8 = (**(code **)(DAT_0000d790 + 0xd0))(&DAT_00009040,0,local_208);
        if ((lVar8 < 0) ||
           (lVar8 = (*(code *)*local_208[0])
                              (u_UniWillVariable_0000ab80,&DAT_000090b0,local_res18,&local_res20,
                               local_1f8), lVar8 < 0)) goto LAB_00003231;
        if (bVar6 == 0x21) {
LAB_000031fd:
          uVar5 = 0;
        }
        else if (bVar6 == 0x22) {
LAB_000031f9:
          uVar5 = 1;
        }
        else {
          if (bVar6 == 0x23) goto LAB_000031fd;
          if (bVar6 == 0x24) goto LAB_000031f9;
        }
        local_1c9 = uVar5;
        (*(code *)local_208[0][2])
                  (u_UniWillVariable_0000ab80,&DAT_000090b0,local_res18[0],local_res20,local_1f8);
LAB_00003231:
        FUN_00008b40(local_138,0x100,(byte *)s_Set_Myfan3_Table___s_s_0000af48,
                     *(undefined8 *)((longlong)&PTR_s_SwitchTable1Office_00009650 + uVar3 * 0xc));
        FUN_000019fc(param_1);
        FUN_00001530(param_1,(char *)local_138);
        return;
      }
      bVar6 = (char)uVar3 + 1;
      uVar3 = (ulonglong)bVar6;
    } while (bVar6 < 4);
  }
  FUN_000019fc(param_1);
  *(undefined8 *)(param_1 + 0x18) = 0x8000000000000002;
  FUN_00001530(param_1,s_invalid_parameter__supported_val_0000af08);
  puVar7 = &DAT_00009658;
  do {
    FUN_00008b40(local_138,0x100,(byte *)s__Table__d__>__s_0000ae68,(ulonglong)*puVar7);
    FUN_00001530(param_1,(char *)local_138);
    puVar7 = puVar7 + 3;
    lVar8 = lVar8 + -1;
  } while (lVar8 != 0);
  (**(code **)(DAT_0000d7a0 + 0x58))(pbVar1);
  return;
}


// ==== FUN_00003288 @ 00003288

undefined8 FUN_00003288(longlong param_1)

{
  undefined8 uVar1;
  
  *(undefined8 *)(param_1 + 0x18) = 0;
  uVar1 = FUN_000015c4(param_1,s__Help_0000a6d4);
  if ((char)uVar1 == '\0') {
    uVar1 = FUN_000015c4(param_1,s__Type_0000ad2c);
    if ((char)uVar1 == '\0') {
      uVar1 = FUN_000015c4(param_1,&DAT_0000ad34);
      if ((char)uVar1 == '\0') {
        uVar1 = FUN_000015c4(param_1,s__Mode_0000ad3c);
        if ((char)uVar1 == '\0') {
          uVar1 = FUN_000015c4(param_1,s__Table_0000ad44);
          if ((char)uVar1 == '\0') {
            *(undefined8 *)(param_1 + 0x18) = 0x8000000000000003;
            FUN_00002ac4(param_1);
            return 0x8000000000000003;
          }
          FUN_0000304c(param_1);
        }
        else {
          FUN_00002ed4(param_1);
        }
      }
      else {
        FUN_00002d5c(param_1);
      }
    }
    else {
      FUN_00002c20(param_1);
    }
  }
  else {
    FUN_00002ac4(param_1);
  }
  return 0;
}


// ==== FUN_00003340 @ 00003340

void FUN_00003340(longlong param_1,undefined8 param_2)

{
  byte *pbVar1;
  undefined8 uVar2;
  ulonglong uVar3;
  longlong lVar4;
  char *pcVar5;
  byte local_res10 [8];
  byte local_res18 [8];
  byte local_88 [128];
  
  if ((int)param_2 == 0) {
    FUN_000082f4(param_1,param_2,0x3c,local_res18);
    if ((local_res18[0] & 0xf9) == 1) {
      pcVar5 = s__SetKBL_0000af80;
      pbVar1 = (byte *)FUN_000016bc(param_1,s__SetKBL_0000af80);
      uVar2 = FUN_0000192c(pbVar1);
      if ((char)uVar2 == '\0') {
        (**(code **)(DAT_0000d7a0 + 0x58))();
        FUN_000019fc(param_1);
        FUN_00001530(param_1,s__SetKBL__Set_KB_Light_Board_ID_0000b030);
        pcVar5 = s_Sample___SetKBL_1__>_Set_KB_Four_0000b050;
      }
      else {
        uVar3 = FUN_000019a8((char *)pbVar1,pcVar5);
        local_res10[0] = (byte)uVar3;
        FUN_000019fc(param_1);
        if ((byte)(local_res10[0] - 1) < 3) {
          lVar4 = FUN_00002648((longlong)local_res10,1,0x11);
          FUN_00004614(param_1,lVar4);
          FUN_000019fc(param_1);
          FUN_00008b40(local_88,0x80,&DAT_0000afc4,(ulonglong)local_res10[0]);
          FUN_00001530(param_1,(char *)local_88);
          (**(code **)(DAT_0000d7a0 + 0x58))(pbVar1);
          return;
        }
        (**(code **)(DAT_0000d7a0 + 0x58))(pbVar1);
        FUN_000019fc(param_1);
        FUN_00001530(param_1,s_The_KB_Board_ID__Four_light_1__S_0000afd0);
        pcVar5 = s_please_type_number_1_3_0000b010;
      }
    }
    else {
      FUN_000019fc(param_1);
      pcVar5 = s_This_command_is_not_applicable_f_0000af90;
    }
  }
  else {
    if ((int)param_2 != 1) {
      return;
    }
    FUN_000082f4(param_1,param_2,0x3c,local_res18);
    local_res10[0] = local_res18[0];
    FUN_000019fc(param_1);
    FUN_00008b40(local_88,0x80,(byte *)s_KB_Light_Board_ID_is_0x_02X__0000b088,
                 (ulonglong)local_res10[0]);
    pbVar1 = local_88;
    lVar4 = param_1;
    FUN_00001530(param_1,(char *)pbVar1);
    FUN_000082f4(lVar4,pbVar1,0x3d,local_res18);
    local_res10[0] = local_res18[0];
    FUN_00008b40(local_88,0x80,(byte *)s_KB_language_type_is_0x_02X__0000b0a8,
                 (ulonglong)local_res18[0]);
    pcVar5 = (char *)local_88;
  }
  FUN_00001530(param_1,pcVar5);
  return;
}


// ==== FUN_0000350c @ 0000350c

void FUN_0000350c(longlong param_1)

{
  *(undefined4 *)(param_1 + 0x14) = 2;
  FUN_000019fc(param_1);
  FUN_00001530(param_1,s__Help___Display_all_KBLBID_comma_0000b0c8);
  FUN_00001530(param_1,s__SetKBL___Set_current_KB_Light_B_0000b0f0);
  FUN_00001530(param_1,s__GetKBL___Get_current_KB_Light_B_0000b120);
  FUN_00001530(param_1,s__Your_setting_will_be_applied_af_0000b160);
  return;
}


// ==== FUN_00003564 @ 00003564

undefined8 FUN_00003564(longlong param_1)

{
  undefined8 uVar1;
  
  uVar1 = FUN_000015c4(param_1,s__Help_0000a6d4);
  if ((char)uVar1 == '\0') {
    uVar1 = FUN_000015c4(param_1,s__SetKBL_0000af80);
    if ((char)uVar1 == '\0') {
      uVar1 = FUN_000015c4(param_1,s__GetKBL_0000af88);
      if ((char)uVar1 == '\0') goto LAB_000035c0;
      *(undefined8 *)(param_1 + 0x18) = 0;
      uVar1 = 1;
    }
    else {
      *(undefined8 *)(param_1 + 0x18) = 0;
      uVar1 = 0;
    }
    FUN_00003340(param_1,uVar1);
  }
  else {
LAB_000035c0:
    *(undefined8 *)(param_1 + 0x18) = 0;
    FUN_0000350c(param_1);
  }
  return 0;
}


// ==== FUN_000035d4 @ 000035d4

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_000035d4(longlong param_1)

{
  byte local_98 [128];
  
  FUN_00008b40(local_98,0x80,(byte *)s__02X__02X__02X__02X__02X__02X__0_0000b190,
               _DAT_ff430014 & 0xff);
  FUN_00001530(param_1,(char *)local_98);
  FUN_00008b40(local_98,0x80,(byte *)s__02X__02X__02X__02X__02X__02X__0_0000b1b8,
               _DAT_ff43001c & 0xff);
  FUN_00001530(param_1,(char *)local_98);
  FUN_00008b40(local_98,0x80,(byte *)s__02X__02X__02X__02X__02X__02X__0_0000b190,
               _DAT_ff430024 & 0xff);
  FUN_00001530(param_1,(char *)local_98);
  return;
}


// ==== FUN_0000377c @ 0000377c

void FUN_0000377c(longlong param_1,int param_2)

{
  byte *pbVar1;
  undefined8 uVar2;
  ulonglong uVar3;
  longlong lVar4;
  undefined8 *puVar5;
  char *pcVar6;
  byte *pbVar7;
  ulonglong uVar8;
  byte bVar9;
  byte local_res10 [8];
  char local_res18 [8];
  undefined4 local_res20 [2];
  byte local_118 [8];
  undefined8 local_110;
  undefined8 *local_108 [2];
  undefined1 local_f8 [15];
  undefined8 local_e9;
  undefined8 local_e1 [21];
  
  local_res18[0] = '\0';
  if (param_2 == 0) goto LAB_000039ae;
  if (param_2 != 1) {
    return;
  }
  pcVar6 = s__SetData_0000af70;
  pbVar1 = (byte *)FUN_000016bc(param_1,s__SetData_0000af70);
  uVar8 = 0;
  bVar9 = local_res10[0];
  do {
    pbVar7 = pbVar1;
    pbVar1 = pbVar7;
    if (*pbVar7 != 0) {
      do {
        if (*pbVar1 == 0x20) goto LAB_000037dd;
        pbVar1 = pbVar1 + 1;
      } while (*pbVar1 != 0);
      if (*pbVar1 == 0x20) {
LAB_000037dd:
        *pbVar1 = 0;
        pbVar1 = pbVar1 + 1;
      }
    }
    uVar2 = FUN_0000192c(pbVar7);
    if ((char)uVar2 == '\0') {
      (**(code **)(DAT_0000d7a0 + 0x58))();
      FUN_000019fc(param_1);
      FUN_00001530(param_1,s__SetData__Set_Data_Bytes__0000b1e8);
      FUN_00001530(param_1,s__SetData_<8_digits_or_8_hexes>_0000b208);
      pcVar6 = s_SetData___SetData_0x08_0x03_0x0A_0000b228;
LAB_000039fc:
      FUN_00001530(param_1,pcVar6);
      return;
    }
    uVar3 = FUN_000019a8((char *)pbVar7,pcVar6);
    local_res10[0] = (byte)uVar3;
    if ((uVar8 == 0) &&
       ((0x1a < local_res10[0] ||
        (pcVar6 = (char *)0x4100100, bVar9 = local_res10[0],
        (0x4100100U >> ((uint)uVar3 & 0x1f) & 1) == 0)))) {
      (**(code **)(DAT_0000d7a0 + 0x58))(pbVar7);
      FUN_000019fc(param_1);
      FUN_00001530(param_1,s__SetData__Set_Data_Bytes__0000b1e8);
      FUN_00001530(param_1,s__SetData_<8_digits_or_8_hexes>_0000b208);
      pcVar6 = s_SetData___SetData_0x08_0x03_0x0A_0000b268;
      goto LAB_000039fc;
    }
    local_118[uVar8] = local_res10[0];
    if (bVar9 == 8) {
      lVar4 = uVar8 + 0x14;
LAB_00003864:
      pcVar6 = (char *)FUN_00002648((longlong)local_res10,1,lVar4);
      FUN_00004614(param_1,(longlong)pcVar6);
    }
    else if (bVar9 == 0x14) {
      pcVar6 = (char *)FUN_00002648((longlong)local_res10,1,uVar8 + 0x1c);
      FUN_00004614(param_1,(longlong)pcVar6);
      local_res18[0] = '\x01';
    }
    else if (bVar9 == 0x1a) {
      lVar4 = uVar8 + 0x24;
      goto LAB_00003864;
    }
    uVar8 = uVar8 + 1;
  } while (uVar8 < 8);
  local_110 = 0xb4;
  local_res20[0] = 7;
  lVar4 = (**(code **)(DAT_0000d790 + 0xd0))(&DAT_00009040,0,local_108);
  if (-1 < lVar4) {
    lVar4 = (*(code *)*local_108[0])
                      (u_UniWillVariable_0000ab80,&DAT_000090b0,local_res20,&local_110,local_f8);
    if (bVar9 == 0x1a) {
      if (-1 < lVar4) {
        puVar5 = &local_e9;
LAB_00003945:
        FUN_00008e40(puVar5,(undefined8 *)local_118,8);
      }
    }
    else if ((bVar9 == 8) && (-1 < lVar4)) {
      puVar5 = local_e1;
      goto LAB_00003945;
    }
    (*(code *)local_108[0][2])
              (u_UniWillVariable_0000ab80,&DAT_000090b0,local_res20[0],local_110,local_f8);
  }
  if (local_res18[0] == '\x01') {
    lVar4 = FUN_00002648((longlong)local_res18,1,0x2c);
    FUN_00004614(param_1,lVar4);
  }
  (**(code **)(DAT_0000d7a0 + 0x58))(pbVar7);
LAB_000039ae:
  FUN_000035d4(param_1);
  return;
}


// ==== FUN_00003a08 @ 00003a08

void FUN_00003a08(longlong param_1)

{
  *(undefined4 *)(param_1 + 0x14) = 2;
  FUN_000019fc(param_1);
  FUN_00001530(param_1,s__Help___Display_all_LEDKB_comman_0000b2a8);
  FUN_00001530(param_1,s__GetStatus___Display_current_key_0000b2e0);
  FUN_00001530(param_1,s__SetData___Value__8____Set_Data_B_0000b320);
  FUN_00001530(param_1,s__Your_setting_will_be_applied_af_0000b160);
  return;
}


// ==== FUN_00003a60 @ 00003a60

undefined8 FUN_00003a60(longlong param_1)

{
  undefined8 uVar1;
  
  uVar1 = FUN_000015c4(param_1,s__Help_0000a6d4);
  if ((char)uVar1 == '\0') {
    uVar1 = FUN_000015c4(param_1,s__GetStatus_0000af60);
    if ((char)uVar1 != '\0') {
      *(undefined8 *)(param_1 + 0x18) = 0;
      FUN_000035d4(param_1);
      return 0;
    }
    uVar1 = FUN_000015c4(param_1,s__SetData_0000af70);
    if ((char)uVar1 != '\0') {
      *(undefined8 *)(param_1 + 0x18) = 0;
      FUN_0000377c(param_1,1);
      return 0;
    }
  }
  *(undefined8 *)(param_1 + 0x18) = 0;
  FUN_00003a08(param_1);
  return 0;
}


// ==== FUN_00003ad8 @ 00003ad8

void FUN_00003ad8(longlong param_1)

{
  longlong lVar1;
  uint *puVar2;
  byte local_108 [256];
  
  FUN_000019fc(param_1);
  FUN_00001530(param_1,s__Help___Display_all_Adaptor_Type_0000b388);
  FUN_00001530(param_1,s__Type___Get_current_Adaptor_Type_0000b3b8);
  FUN_00001530(param_1,s__Set___Set_Adaptor_Type__support_0000b3e8);
  puVar2 = &DAT_000098a8;
  lVar1 = 8;
  do {
    FUN_00008b40(local_108,0x100,(byte *)s__Set__d__>__s_0000ade0,(ulonglong)*puVar2);
    FUN_00001530(param_1,(char *)local_108);
    puVar2 = puVar2 + 3;
    lVar1 = lVar1 + -1;
  } while (lVar1 != 0);
  return;
}


// ==== FUN_00003b7c @ 00003b7c

void FUN_00003b7c(longlong param_1)

{
  char *pcVar1;
  byte bVar2;
  ulonglong uVar3;
  byte local_res10 [24];
  byte local_108 [256];
  
  (*(code *)PTR_FUN_000090d8)(local_res10);
  uVar3 = 0;
  do {
    if ((uint)local_res10[0] == (&DAT_000098a8)[uVar3 * 3]) {
      FUN_00008b40(local_108,0x100,(byte *)s_Current_Adaptor_Type___s_0000b418,
                   *(undefined8 *)((longlong)&PTR_DAT_000098a0 + uVar3 * 0xc));
      FUN_000019fc(param_1);
      pcVar1 = (char *)local_108;
      goto LAB_00003c15;
    }
    bVar2 = (char)uVar3 + 1;
    uVar3 = (ulonglong)bVar2;
  } while (bVar2 < 8);
  *(undefined8 *)(param_1 + 0x18) = 0x8000000000000002;
  FUN_000019fc(param_1);
  pcVar1 = s_ERROR__invalid_Adaptor_Type__0000b438;
LAB_00003c15:
  FUN_00001530(param_1,pcVar1);
  return;
}


// ==== FUN_00003c28 @ 00003c28

void FUN_00003c28(longlong param_1)

{
  byte *pbVar1;
  undefined8 uVar2;
  ulonglong uVar3;
  undefined *puVar4;
  longlong lVar5;
  byte bVar6;
  uint *puVar7;
  byte local_res10 [8];
  byte local_118 [256];
  
  puVar4 = &DAT_0000ad34;
  pbVar1 = (byte *)FUN_000016bc(param_1,&DAT_0000ad34);
  uVar2 = FUN_0000192c(pbVar1);
  lVar5 = 8;
  if ((char)uVar2 == '\x01') {
    uVar3 = FUN_000019a8((char *)pbVar1,puVar4);
    local_res10[0] = (byte)uVar3;
    (**(code **)(DAT_0000d7a0 + 0x58))(pbVar1);
    uVar3 = 0;
    do {
      if ((uint)local_res10[0] == (&DAT_000098a8)[uVar3 * 3]) {
        (*(code *)PTR_FUN_000090d0)(local_res10,1,0x33);
        FUN_00008b40(local_118,0x100,(byte *)s_Set_Adaptor_Type___s_s_0000b458,
                     *(undefined8 *)((longlong)&PTR_DAT_000098a0 + uVar3 * 0xc));
        FUN_000019fc(param_1);
        FUN_00001530(param_1,(char *)local_118);
        return;
      }
      bVar6 = (char)uVar3 + 1;
      uVar3 = (ulonglong)bVar6;
    } while (bVar6 < 8);
  }
  FUN_000019fc(param_1);
  *(undefined8 *)(param_1 + 0x18) = 0x8000000000000002;
  FUN_00001530(param_1,s_invalid_parameter__supported_val_0000af08);
  puVar7 = &DAT_000098a8;
  do {
    FUN_00008b40(local_118,0x100,(byte *)s__Set__d__>__s_0000ade0,(ulonglong)*puVar7);
    FUN_00001530(param_1,(char *)local_118);
    puVar7 = puVar7 + 3;
    lVar5 = lVar5 + -1;
  } while (lVar5 != 0);
  (**(code **)(DAT_0000d7a0 + 0x58))(pbVar1);
  return;
}


// ==== FUN_00003e24 @ 00003e24

void FUN_00003e24(longlong param_1)

{
  FUN_000019fc(param_1);
  FUN_00001530(param_1,s__Help___Display_all_MeUnlock_com_0000b478);
  FUN_00001530(param_1,s__Set___Set_to_Unlock_ME_region_o_0000b4b0);
  FUN_00001530(param_1,s__Get___Get_current_status_0000b500);
  FUN_00001530(param_1,s_Note__Unlock_Lock_Intel_ME_regio_0000b520);
  return;
}


// ==== FUN_00003e74 @ 00003e74

void FUN_00003e74(longlong param_1)

{
  byte *pbVar1;
  undefined8 uVar2;
  ulonglong uVar3;
  longlong lVar4;
  byte *pbVar5;
  undefined *puVar6;
  char *pcVar7;
  byte bVar8;
  byte local_res10 [8];
  
  puVar6 = &DAT_0000ad34;
  pbVar1 = (byte *)FUN_000016bc(param_1,&DAT_0000ad34);
  uVar2 = FUN_0000192c(pbVar1);
  if ((char)uVar2 != '\x01') {
LAB_00003f50:
    FUN_000019fc(param_1);
    *(undefined8 *)(param_1 + 0x18) = 0x8000000000000002;
    FUN_00001530(param_1,s_invalid_parameter__supported_val_0000af08);
    FUN_00001530(param_1,s__Set_1__>_Unlock_only_one_time__0000b618);
    FUN_00001530(param_1,s__Set_0__>_Lock_default__0000b640);
    (**(code **)(DAT_0000d7a0 + 0x58))(pbVar1);
    return;
  }
  uVar3 = FUN_000019a8((char *)pbVar1,puVar6);
  pbVar5 = pbVar1;
  pcVar7 = DAT_0000d7a0;
  (**(code **)(DAT_0000d7a0 + 0x58))();
  bVar8 = (byte)uVar3;
  if (1 < bVar8) goto LAB_00003f50;
  lVar4 = FUN_000082f4(pbVar5,pcVar7,0x41,local_res10);
  if (lVar4 < 0) {
    FUN_000019fc(param_1);
    pcVar7 = s_Operate_ME_Lock_Unlock_failed__0000b578;
    goto LAB_00003ee8;
  }
  lVar4 = param_1;
  FUN_000019fc(param_1);
  if (bVar8 == 0) {
    pcVar7 = s_Lock_ME_region__0000b598;
    bVar8 = local_res10[0] & 0xef;
LAB_00003f27:
    lVar4 = param_1;
    FUN_00001530(param_1,pcVar7);
    local_res10[0] = bVar8;
  }
  else if (bVar8 == 1) {
    bVar8 = local_res10[0] | 0x10;
    pcVar7 = s_Unlock_ME_region___will_be_appli_0000b5b0;
    goto LAB_00003f27;
  }
  lVar4 = FUN_00008294(lVar4,pcVar7,0x41,local_res10[0]);
  if (-1 < lVar4) {
    return;
  }
  FUN_000019fc(param_1);
  pcVar7 = s_Write_ME_Lock_Unlock_value_faile_0000b5f0;
LAB_00003ee8:
  FUN_00001530(param_1,pcVar7);
  return;
}


// ==== FUN_000040b8 @ 000040b8

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_000040b8(longlong param_1)

{
  byte local_98 [128];
  
  FUN_00008b40(local_98,0x80,(byte *)s_1AH____02X__02X__02X__02X__02X___0000b6d8,
               _DAT_ff43003a & 0xff);
  FUN_00001530(param_1,(char *)local_98);
  FUN_00008b40(local_98,0x80,(byte *)s_14H____02X__02X__02X__02X__02X___0000b708,
               _DAT_ff43004a & 0xff);
  FUN_00001530(param_1,(char *)local_98);
  FUN_00008b40(local_98,0x80,(byte *)s_08H____02X__02X__02X__02X__02X___0000b738,
               _DAT_ff430042 & 0xff);
  FUN_00001530(param_1,(char *)local_98);
  return;
}


// ==== FUN_0000424c @ 0000424c

void FUN_0000424c(longlong param_1,int param_2)

{
  byte bVar1;
  byte *pbVar2;
  undefined8 uVar3;
  ulonglong uVar4;
  longlong lVar5;
  undefined8 *puVar6;
  wchar_t *pwVar7;
  char *pcVar8;
  undefined *puVar9;
  byte *pbVar10;
  ulonglong uVar11;
  byte bVar12;
  undefined4 local_res10 [2];
  byte local_res18 [8];
  undefined8 local_res20;
  undefined8 *local_118;
  byte local_110 [8];
  byte local_108 [8];
  byte local_100 [8];
  undefined1 local_f8 [31];
  undefined8 local_d9;
  undefined8 local_d1 [19];
  
  (**(code **)(DAT_0000d790 + 0xd0))(&DAT_00009040,0,&DAT_0000d938);
  if (param_2 == 0) {
    FUN_000040b8(param_1);
    return;
  }
  if (param_2 != 1) {
    return;
  }
  pcVar8 = s__SetMode_0000b6c8;
  pbVar2 = (byte *)FUN_000016bc(param_1,s__SetMode_0000b6c8);
  uVar11 = 0;
  bVar12 = (byte)local_res10[0];
  do {
    pbVar10 = pbVar2;
    pbVar2 = pbVar10;
    if (*pbVar10 != 0) {
      do {
        if (*pbVar2 == 0x20) goto LAB_000042d4;
        pbVar2 = pbVar2 + 1;
      } while (*pbVar2 != 0);
      if (*pbVar2 == 0x20) {
LAB_000042d4:
        *pbVar2 = 0;
        pbVar2 = pbVar2 + 1;
      }
    }
    uVar3 = FUN_0000192c(pbVar10);
    if ((char)uVar3 == '\0') {
LAB_000043b1:
      (**(code **)(DAT_0000d7a0 + 0x58))(pbVar10);
      FUN_000019fc(param_1);
      FUN_00001530(param_1,s__SetMode___Value__8____Set_8_Dat_0000b768);
      FUN_00001530(param_1,s__example____SetMode_0x1A_0x05_0x_0000b7a0);
      FUN_00001530(param_1,s______SetMode_0x14_0x00_0x01_0xff_0000b7f0);
      pcVar8 = s______SetMode_0x08_0x02_0x03_0x05_0000b840;
      goto LAB_000043f7;
    }
    uVar4 = FUN_000019a8((char *)pbVar10,pcVar8);
    bVar1 = (byte)uVar4;
    if ((uVar11 == 0) &&
       ((0x1a < bVar1 ||
        (pcVar8 = (char *)0x4100100, bVar12 = bVar1, (0x4100100U >> ((uint)uVar4 & 0x1f) & 1) == 0))
       )) goto LAB_000043b1;
    local_res18[uVar11] = bVar1;
    if (bVar12 == 8) {
      local_110[uVar11] = bVar1;
    }
    else if (bVar12 == 0x14) {
      local_100[uVar11] = bVar1;
    }
    else if (bVar12 == 0x1a) {
      local_108[uVar11] = bVar1;
    }
    uVar11 = uVar11 + 1;
  } while (uVar11 < 8);
  local_res20 = 0xb4;
  local_res10[0] = 7;
  lVar5 = (**(code **)(DAT_0000d790 + 0xd0))(&DAT_00009040,0,&local_118);
  if (-1 < lVar5) {
    lVar5 = (*(code *)*local_118)
                      (u_UniWillVariable_0000ab80,&DAT_000090b0,local_res10,&local_res20,local_f8);
    if (bVar12 == 0x1a) {
      if (-1 < lVar5) {
        puVar6 = &local_d9;
LAB_00004413:
        FUN_00008e40(puVar6,(undefined8 *)local_res18,8);
      }
    }
    else if ((bVar12 == 8) && (-1 < lVar5)) {
      puVar6 = local_d1;
      goto LAB_00004413;
    }
    (*(code *)local_118[2])
              (u_UniWillVariable_0000ab80,&DAT_000090b0,local_res10[0],local_res20,local_f8);
  }
  if (local_110[0] == 8) {
    pbVar2 = local_110;
    puVar9 = &DAT_00009960;
    pwVar7 = u_OemULB08_0000b888;
  }
  else if (local_108[0] == 0x1a) {
    pbVar2 = local_108;
    puVar9 = &DAT_00009970;
    pwVar7 = u_OemULB1A_0000b8a0;
  }
  else {
    if (local_100[0] != 0x14) goto LAB_000044ae;
    pbVar2 = local_100;
    puVar9 = &DAT_00009980;
    pwVar7 = u_OemULB14_0000b8b8;
  }
  (**(code **)(DAT_0000d938 + 0x10))(pwVar7,puVar9,7,8,pbVar2);
LAB_000044ae:
  (**(code **)(DAT_0000d7a0 + 0x58))(pbVar10);
  pcVar8 = s__Your_setting_will_be_applied_af_0000b160;
LAB_000043f7:
  FUN_00001530(param_1,pcVar8);
  return;
}


// ==== FUN_000044ec @ 000044ec

void FUN_000044ec(longlong param_1)

{
  *(undefined4 *)(param_1 + 0x14) = 2;
  FUN_000019fc(param_1);
  FUN_00001530(param_1,s__Help___Display_all_USB_Light_Ba_0000b8d0);
  FUN_00001530(param_1,s___Please_type_three_commands_1AH_0000b910);
  FUN_00001530(param_1,s__GetMode___Display_current_USB_l_0000b958);
  FUN_00001530(param_1,s__SetMode___Value__8____Set_8_Dat_0000b768);
  FUN_00001530(param_1,s__example____SetMode_0x1A_0x05_0x_0000b7a0);
  FUN_00001530(param_1,s______SetMode_0x14_0x00_0x01_0xff_0000b7f0);
  FUN_00001530(param_1,s______SetMode_0x08_0x02_0x03_0x05_0000b840);
  FUN_00001530(param_1,s__Your_setting_will_be_applied_af_0000b160);
  return;
}


// ==== FUN_00004580 @ 00004580

undefined8 FUN_00004580(longlong param_1)

{
  undefined8 uVar1;
  
  uVar1 = FUN_000015c4(param_1,s__Help_0000a6d4);
  if ((char)uVar1 == '\0') {
    uVar1 = FUN_000015c4(param_1,s__GetMode_0000b6b8);
    if ((char)uVar1 != '\0') {
      *(undefined8 *)(param_1 + 0x18) = 0;
      (**(code **)(DAT_0000d790 + 0xd0))(&DAT_00009040,0,&DAT_0000d938);
      FUN_000040b8(param_1);
      return 0;
    }
    uVar1 = FUN_000015c4(param_1,s__SetMode_0000b6c8);
    if ((char)uVar1 != '\0') {
      *(undefined8 *)(param_1 + 0x18) = 0;
      FUN_0000424c(param_1,1);
      return 0;
    }
  }
  *(undefined8 *)(param_1 + 0x18) = 0;
  FUN_000044ec(param_1);
  return 0;
}


// ==== FUN_00004614 @ 00004614

void FUN_00004614(longlong param_1,longlong param_2)

{
  char *pcVar1;
  
  if (param_2 < 0) {
    *(longlong *)(param_1 + 0x18) = param_2;
    if (param_2 == -0x7fffffffffffffff) {
      FUN_000019fc(param_1);
      pcVar1 = s_Flash_protocol_not_exist__0000a698;
    }
    else if (param_2 == -0x7ffffffffffffffc) {
      FUN_000019fc(param_1);
      pcVar1 = s_Data_size_exceed__0000b9e8;
    }
    else if (param_2 == -0x7ffffffffffffff9) {
      FUN_000019fc(param_1);
      pcVar1 = s_Flash_access_failed__0000ba00;
    }
    else {
      FUN_000019fc(param_1);
      pcVar1 = s_Unknow_error__0000ba18;
    }
    *(undefined4 *)(param_1 + 0x14) = 2;
    FUN_00001530(param_1,pcVar1);
  }
  return;
}


// ==== FUN_000046a4 @ 000046a4

void FUN_000046a4(undefined2 param_1,undefined1 param_2,undefined1 param_3,undefined1 param_4)

{
  longlong lVar1;
  undefined4 local_e8 [2];
  undefined8 local_e0;
  undefined8 *local_d8 [2];
  undefined1 local_c8 [4];
  undefined2 local_c4;
  undefined1 local_c2;
  undefined1 local_c1;
  undefined1 local_c0;
  
  local_e0 = 0xb4;
  local_e8[0] = 7;
  lVar1 = (**(code **)(DAT_0000d790 + 0xd0))(&DAT_00009040,0,local_d8);
  if (-1 < lVar1) {
    lVar1 = (*(code *)*local_d8[0])
                      (u_UniWillVariable_0000ab80,&DAT_000090b0,local_e8,&local_e0,local_c8);
    if (-1 < lVar1) {
      local_c4 = param_1;
      local_c2 = param_2;
      local_c1 = param_3;
      local_c0 = param_4;
      (*(code *)local_d8[0][2])
                (u_UniWillVariable_0000ab80,&DAT_000090b0,local_e8[0],local_e0,local_c8);
    }
  }
  return;
}


// ==== FUN_0000478c @ 0000478c

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_0000478c(longlong param_1,undefined8 param_2)

{
  ushort uVar1;
  byte *pbVar2;
  undefined8 uVar3;
  ulonglong uVar4;
  longlong lVar5;
  uint uVar6;
  byte *pbVar7;
  undefined1 *puVar8;
  undefined *puVar9;
  char *pcVar10;
  undefined8 uVar11;
  ushort uVar12;
  int iVar13;
  ushort uVar14;
  byte local_res10 [8];
  byte local_res18 [8];
  byte local_res20 [8];
  byte local_d8;
  undefined1 local_d7;
  undefined1 local_d6 [6];
  undefined2 local_d0;
  undefined1 local_c8 [4];
  undefined2 local_c4;
  byte local_b8 [128];
  
  uVar14 = _DAT_ff430004;
  local_c8[0] = 0;
  local_d0 = 0;
  lVar5 = param_1;
  uVar3 = param_2;
  FUN_000082f4(param_1,param_2,0x66,(undefined1 *)((longlong)&local_d0 + 1));
  uVar12 = _DAT_ff430004;
  uVar11 = 1;
  iVar13 = (int)param_2;
  if (iVar13 < 9) {
    if (iVar13 == 8) {
      puVar9 = &DAT_0000b9b8;
      pbVar2 = (byte *)FUN_000016bc(param_1,&DAT_0000b9b8);
      uVar3 = FUN_0000192c(pbVar2);
      if ((char)uVar3 == '\0') {
        (**(code **)(DAT_0000d7a0 + 0x58))();
        FUN_000019fc(param_1);
        FUN_00001530(param_1,s__BL__Breath_Led_support__0000be18);
        FUN_00001530(param_1,s__BL_1__>_Breath_Led_support_on__0000be38);
        pcVar10 = s__BL_0__>_Breath_Led_support_off__0000be58;
      }
      else {
        uVar4 = FUN_000019a8((char *)pbVar2,puVar9);
        local_res10[0] = (byte)uVar4;
        if (local_res10[0] < 2) {
          uVar12 = 0xffbf;
          uVar1 = (ushort)(local_res10[0] & 1) << 6;
          goto LAB_00005373;
        }
        (**(code **)(DAT_0000d7a0 + 0x58))(pbVar2);
        FUN_000019fc(param_1);
        pcVar10 = s_Value_of_Param__BL_invalid__Valu_0000be80;
      }
      goto LAB_0000543f;
    }
    if (iVar13 == 0) {
      uVar14 = 0;
      FUN_000082f4(lVar5,uVar3,0x3c,local_res18);
      local_res20[0] = local_res18[0] & 1;
      if (local_res20[0] != 0) {
        local_res20[0] = local_res18[0] & 0xf8;
        if (local_res20[0] < 0x39) {
          if (0x28 < local_res20[0] - 0x10) {
LAB_00004c9a:
            FUN_000027bc((undefined8 *)local_res20,1,0x11);
            if (local_res20[0] != 1) goto LAB_00005386;
          }
        }
        else {
          uVar6 = local_res20[0] - 0x48;
          if ((0x30 < uVar6) || ((0x1010000000101U >> ((ulonglong)uVar6 & 0x3f) & 1) == 0))
          goto LAB_00004c9a;
        }
      }
      local_res10[0] = 0;
      FUN_00002648((longlong)local_res10,1,0x26);
      FUN_00002648((longlong)local_res10,1,0x27);
    }
    else {
      if (iVar13 != 1) {
        if (iVar13 == 2) {
          puVar9 = &DAT_0000b9a0;
          pbVar2 = (byte *)FUN_000016bc(param_1,&DAT_0000b9a0);
          uVar3 = FUN_0000192c(pbVar2);
          if ((char)uVar3 == '\0') {
            (**(code **)(DAT_0000d7a0 + 0x58))();
            FUN_000019fc(param_1);
            FUN_00001530(param_1,s__AP__Airplane_mode_support__0000ba68);
            FUN_00001530(param_1,s__AP_1__>_Airplane_mode_support_o_0000ba88);
            pcVar10 = s__AP_0__>_Airplane_mode_support_o_0000bab0;
          }
          else {
            uVar4 = FUN_000019a8((char *)pbVar2,puVar9);
            local_res10[0] = (byte)uVar4;
            if (local_res10[0] < 2) {
              uVar12 = 0xfffe;
              uVar1 = (ushort)(local_res10[0] & 1);
              goto LAB_00005373;
            }
            (**(code **)(DAT_0000d7a0 + 0x58))(pbVar2);
            FUN_000019fc(param_1);
            pcVar10 = s_Value_of_Param__AP_invalid__Valu_0000bad8;
          }
        }
        else if (iVar13 == 3) {
          puVar9 = &DAT_0000b9a4;
          pbVar2 = (byte *)FUN_000016bc(param_1,&DAT_0000b9a4);
          uVar3 = FUN_0000192c(pbVar2);
          if ((char)uVar3 == '\0') {
            (**(code **)(DAT_0000d7a0 + 0x58))();
            FUN_000019fc(param_1);
            FUN_00001530(param_1,s__GS__GPU_switch_support__0000bb10);
            FUN_00001530(param_1,s__GS_1__>_GPU_switch_support_on__0000bb30);
            pcVar10 = s__GS_0__>_GPU_switch_support_off__0000bb50;
          }
          else {
            uVar4 = FUN_000019a8((char *)pbVar2,puVar9);
            local_res10[0] = (byte)uVar4;
            if (local_res10[0] < 2) {
              uVar1 = 0xfffd;
              uVar12 = (ushort)(local_res10[0] & 1) * 2;
LAB_00004889:
              uVar1 = uVar14 & uVar1;
              goto LAB_00005376;
            }
            (**(code **)(DAT_0000d7a0 + 0x58))(pbVar2);
            FUN_000019fc(param_1);
            pcVar10 = s_Value_of_Param__GS_invalid__Valu_0000bb78;
          }
        }
        else if (iVar13 == 4) {
          puVar9 = &DAT_0000b9a8;
          pbVar2 = (byte *)FUN_000016bc(param_1,&DAT_0000b9a8);
          uVar3 = FUN_0000192c(pbVar2);
          if ((char)uVar3 == '\0') {
            (**(code **)(DAT_0000d7a0 + 0x58))();
            FUN_000019fc(param_1);
            FUN_00001530(param_1,s__OC__Over_Clock_support__0000bbb0);
            FUN_00001530(param_1,s__OC_1__>_Over_Clock_support_on__0000bbd0);
            pcVar10 = s__OC_0__>_Over_Clock_support_off__0000bbf0;
          }
          else {
            uVar4 = FUN_000019a8((char *)pbVar2,puVar9);
            local_res10[0] = (byte)uVar4;
            if (local_res10[0] < 2) {
              uVar1 = 0xfffb;
              uVar12 = (ushort)(local_res10[0] & 1) << 2;
              goto LAB_00004889;
            }
            (**(code **)(DAT_0000d7a0 + 0x58))(pbVar2);
            FUN_000019fc(param_1);
            pcVar10 = s_Value_of_Param__OC_invalid__Valu_0000bc18;
          }
        }
        else if (iVar13 == 5) {
          puVar9 = &DAT_0000b9ac;
          pbVar2 = (byte *)FUN_000016bc(param_1,&DAT_0000b9ac);
          uVar3 = FUN_0000192c(pbVar2);
          if ((char)uVar3 == '\0') {
            (**(code **)(DAT_0000d7a0 + 0x58))();
            FUN_000019fc(param_1);
            FUN_00001530(param_1,s__MK__Macro_Key_support__0000bc50);
            FUN_00001530(param_1,s__MK_1__>_Macro_Key_support_on__0000bc68);
            pcVar10 = s__MK_0__>_Macro_Key_support_off__0000bc88;
          }
          else {
            uVar4 = FUN_000019a8((char *)pbVar2,puVar9);
            local_res10[0] = (byte)uVar4;
            if (local_res10[0] < 2) {
              uVar1 = 0xfff7;
              uVar12 = (ushort)(local_res10[0] & 1) << 3;
              goto LAB_00004889;
            }
            (**(code **)(DAT_0000d7a0 + 0x58))(pbVar2);
            FUN_000019fc(param_1);
            pcVar10 = s_Value_of_Param__MK_invalid__Valu_0000bca8;
          }
        }
        else if (iVar13 == 6) {
          puVar9 = &DAT_0000b9b0;
          pbVar2 = (byte *)FUN_000016bc(param_1,&DAT_0000b9b0);
          uVar3 = FUN_0000192c(pbVar2);
          if ((char)uVar3 == '\0') {
            (**(code **)(DAT_0000d7a0 + 0x58))();
            FUN_000019fc(param_1);
            FUN_00001530(param_1,s__SK__Shortcut_Key_support__0000bce0);
            FUN_00001530(param_1,s__SK_1__>_Shortcut_Key_support_on_0000bd00);
            pcVar10 = s__SK_0__>_Shortcut_Key_support_of_0000bd28;
          }
          else {
            uVar4 = FUN_000019a8((char *)pbVar2,puVar9);
            local_res10[0] = (byte)uVar4;
            if (local_res10[0] < 2) {
              uVar1 = 0xffef;
              uVar12 = (ushort)(local_res10[0] & 1) << 4;
              goto LAB_00004889;
            }
            (**(code **)(DAT_0000d7a0 + 0x58))(pbVar2);
            FUN_000019fc(param_1);
            pcVar10 = s_Value_of_Param__SK_invalid__Valu_0000bd50;
          }
        }
        else {
          if (iVar13 != 7) goto LAB_00005386;
          puVar9 = &DAT_0000b9b4;
          pbVar2 = (byte *)FUN_000016bc(param_1,&DAT_0000b9b4);
          uVar3 = FUN_0000192c(pbVar2);
          if ((char)uVar3 == '\0') {
            (**(code **)(DAT_0000d7a0 + 0x58))();
            FUN_000019fc(param_1);
            FUN_00001530(param_1,s__WK__Win_Key_support__0000bd88);
            FUN_00001530(param_1,s__WK_1__>_Win_Key_support_on__0000bda0);
            pcVar10 = s__WK_0__>_Win_Key_support_off__0000bdc0;
          }
          else {
            uVar4 = FUN_000019a8((char *)pbVar2,puVar9);
            local_res10[0] = (byte)uVar4;
            if (local_res10[0] < 2) {
              uVar1 = 0xffdf;
              uVar12 = (ushort)(local_res10[0] & 1) << 5;
              goto LAB_00004889;
            }
            (**(code **)(DAT_0000d7a0 + 0x58))(pbVar2);
            FUN_000019fc(param_1);
            pcVar10 = s_Value_of_Param__WK_invalid__Valu_0000bde0;
          }
        }
        goto LAB_0000543f;
      }
      lVar5 = param_1;
      FUN_000019fc(param_1);
      FUN_000082f4(lVar5,uVar3,0x40,local_d6);
      FUN_000082f4(lVar5,uVar3,0x3c,local_res18);
      FUN_000082f4(lVar5,uVar3,0x3d,&local_d7);
      FUN_00008b40(local_b8,0x80,(byte *)s_Current_APCtrl_Configuration__0x_0000ba28,
                   (ulonglong)uVar12);
      FUN_00001530(param_1,(char *)local_b8);
    }
LAB_00005386:
    uVar12 = local_d0 & 0xe000 | uVar14 & 0x1fff | 0x4000;
    local_d0 = uVar12;
    local_c4 = uVar12;
    lVar5 = FUN_00002648((longlong)&local_d0,2,4);
    FUN_00004614(param_1,lVar5);
    puVar8 = local_c8;
    FUN_00002648((longlong)puVar8,1,10);
    FUN_00008294(puVar8,uVar11,0x65,(char)(uVar14 & 0x1fff));
    FUN_00008294(puVar8,uVar11,0x66,local_c4._1_1_);
    FUN_000046a4(uVar12,local_d6[0],local_res18[0],local_d7);
  }
  else {
    if (iVar13 == 9) {
      puVar9 = &DAT_0000b9bc;
      pbVar2 = (byte *)FUN_000016bc(param_1,&DAT_0000b9bc);
      uVar3 = FUN_0000192c(pbVar2);
      if ((char)uVar3 == '\0') {
        (**(code **)(DAT_0000d7a0 + 0x58))();
        FUN_000019fc(param_1);
        FUN_00001530(param_1,s__FB__Fan_Boost_support__0000beb8);
        FUN_00001530(param_1,s__FB_1__>_Fan_Boost_support_on__0000bed0);
        pcVar10 = s__FB_0__>_Fan_Boost_support_off__0000bef0;
      }
      else {
        uVar4 = FUN_000019a8((char *)pbVar2,puVar9);
        local_res10[0] = (byte)uVar4;
        if (local_res10[0] < 2) {
          uVar12 = 0xff7f;
          uVar1 = (ushort)(local_res10[0] & 1) << 7;
LAB_00005373:
          uVar12 = uVar14 & uVar12;
LAB_00005376:
          uVar14 = uVar12 | uVar1;
LAB_00005379:
          (**(code **)(DAT_0000d7a0 + 0x58))(pbVar2);
          goto LAB_00005386;
        }
        (**(code **)(DAT_0000d7a0 + 0x58))(pbVar2);
        FUN_000019fc(param_1);
        pcVar10 = s_Value_of_Param__FB_invalid__Valu_0000bf10;
      }
    }
    else if (iVar13 == 10) {
      puVar9 = &DAT_0000b9c0;
      pbVar2 = (byte *)FUN_000016bc(param_1,&DAT_0000b9c0);
      uVar3 = FUN_0000192c(pbVar2);
      if ((char)uVar3 == '\0') {
        (**(code **)(DAT_0000d7a0 + 0x58))();
        FUN_000019fc(param_1);
        FUN_00001530(param_1,s__SM__Silent_Mode_support__0000bf48);
        FUN_00001530(param_1,s__SM_1__>_Silent_Mode_support_on__0000bf68);
        pcVar10 = s__SM_0__>_Silent_Mode_support_off_0000bf90;
      }
      else {
        uVar4 = FUN_000019a8((char *)pbVar2,puVar9);
        local_res10[0] = (byte)uVar4;
        if (local_res10[0] < 2) {
          uVar12 = 0xfeff;
          uVar1 = (ushort)(local_res10[0] & 1) << 8;
          goto LAB_00005373;
        }
        (**(code **)(DAT_0000d7a0 + 0x58))(pbVar2);
        FUN_000019fc(param_1);
        pcVar10 = s_Value_of_Param__SM_invalid__Valu_0000bfb8;
      }
    }
    else if (iVar13 == 0xb) {
      puVar9 = &DAT_0000b9c4;
      pbVar2 = (byte *)FUN_000016bc(param_1,&DAT_0000b9c4);
      uVar3 = FUN_0000192c(pbVar2);
      if ((char)uVar3 == '\0') {
        (**(code **)(DAT_0000d7a0 + 0x58))();
        FUN_000019fc(param_1);
        FUN_00001530(param_1,s__UC__USB_Charger_support__0000bff0);
        FUN_00001530(param_1,s__UC_1__>_USB_Charger_support_on__0000c010);
        pcVar10 = s__UC_0__>_USB_Charger_support_off_0000c038;
      }
      else {
        uVar4 = FUN_000019a8((char *)pbVar2,puVar9);
        local_res10[0] = (byte)uVar4;
        if (local_res10[0] < 2) {
          uVar12 = 0xfdff;
          uVar1 = (ushort)(local_res10[0] & 1) << 9;
          goto LAB_00005373;
        }
        (**(code **)(DAT_0000d7a0 + 0x58))(pbVar2);
        FUN_000019fc(param_1);
        pcVar10 = s_Value_of_Param__UC_invalid__Valu_0000c060;
      }
    }
    else if (iVar13 == 0xc) {
      pcVar10 = s__RGBKB_0000b9c8;
      pbVar2 = (byte *)FUN_000016bc(param_1,s__RGBKB_0000b9c8);
      uVar3 = FUN_0000192c(pbVar2);
      if ((char)uVar3 == '\0') {
        (**(code **)(DAT_0000d7a0 + 0x58))();
        FUN_000019fc(param_1);
        FUN_00001530(param_1,s__RGBKB__RGB_Keyboard_support__0000c098);
        FUN_00001530(param_1,s__RGBKB_1__>_RGB_Keyboard_support_0000c0b8);
        pcVar10 = s__RGBKB_0__>_RGB_Keyboard_support_0000c0e0;
      }
      else {
        uVar4 = FUN_000019a8((char *)pbVar2,pcVar10);
        local_res10[0] = (byte)uVar4;
        if (local_res10[0] < 2) {
          uVar12 = 0xfbff;
          uVar1 = (ushort)(local_res10[0] & 1) << 10;
          goto LAB_00005373;
        }
        (**(code **)(DAT_0000d7a0 + 0x58))(pbVar2);
        FUN_000019fc(param_1);
        pcVar10 = s_Value_of_Param__RGBKB_invalid__V_0000c108;
      }
    }
    else if (iVar13 == 0xd) {
      pcVar10 = s__RGBLG_0000b9d0;
      pbVar2 = (byte *)FUN_000016bc(param_1,s__RGBLG_0000b9d0);
      uVar3 = FUN_0000192c(pbVar2);
      if ((char)uVar3 == '\0') {
        (**(code **)(DAT_0000d7a0 + 0x58))();
        FUN_000019fc(param_1);
        FUN_00001530(param_1,s__RGBLG__RGB_Logo_support__0000c140);
        FUN_00001530(param_1,s__RGBLG_1__>_RGB_Logo_support_on__0000c160);
        pcVar10 = s__RGBLG_0__>_RGB_Logo_support_off_0000c188;
      }
      else {
        uVar4 = FUN_000019a8((char *)pbVar2,pcVar10);
        local_res10[0] = (byte)uVar4;
        if (local_res10[0] < 2) {
          uVar12 = 0xf7ff;
          uVar1 = (ushort)(local_res10[0] & 1) << 0xb;
          goto LAB_00005373;
        }
        (**(code **)(DAT_0000d7a0 + 0x58))(pbVar2);
        FUN_000019fc(param_1);
        pcVar10 = s_Value_of_Param__RGBLG_invalid__V_0000c1b0;
      }
    }
    else if (iVar13 == 0xe) {
      pcVar10 = s__CHINA_0000b9d8;
      pbVar2 = (byte *)FUN_000016bc(param_1,s__CHINA_0000b9d8);
      uVar3 = FUN_0000192c(pbVar2);
      if ((char)uVar3 == '\0') {
        (**(code **)(DAT_0000d7a0 + 0x58))();
        FUN_000019fc(param_1);
        FUN_00001530(param_1,s__CHINA__RGB_Keyboard_China_suppo_0000c1e8);
        FUN_00001530(param_1,s__CHINA_1__>_RGB_Keyboard_backlig_0000c210);
        pcVar10 = s__CHINA_0__>_RGB_Keyboard_backlig_0000c260;
      }
      else {
        uVar4 = FUN_000019a8((char *)pbVar2,pcVar10);
        local_res10[0] = (byte)uVar4;
        if (local_res10[0] < 2) {
          uVar3 = 0xefff;
          uVar14 = uVar14 & 0xefff | (ushort)(local_res10[0] & 1) << 0xc;
          FUN_000082f4(0xefff,pcVar10,0x3c,local_res18);
          FUN_000082f4(uVar3,pcVar10,0x82,&local_d8);
          if (local_res10[0] == 1) {
            local_d8 = local_d8 | 0x40;
          }
          else {
            local_d8 = local_d8 & 0xbf;
          }
          local_res20[0] = local_res18[0] & 1;
          if (local_res20[0] == 0) {
            FUN_00002648((longlong)local_res10,1,0x26);
            local_res10[0] = (local_res10[0] != 1) - 1U & 0x14;
            FUN_00002648((longlong)local_res10,1,0x27);
            pbVar7 = &DAT_00009ab0;
LAB_00004fc8:
            uVar3 = 8;
            FUN_00002648((longlong)pbVar7,8,0x14);
          }
          else {
            local_res20[0] = local_res18[0] & 0xf8;
            if (local_res20[0] < 0x39) {
              if (local_res20[0] - 0x10 < 0x29) {
LAB_0000501a:
                FUN_00002648((longlong)local_res10,1,0x26);
                local_res10[0] = (local_res10[0] != 1) - 1U & 0x14;
                FUN_00002648((longlong)local_res10,1,0x27);
                pbVar7 = &DAT_00009ab8;
                goto LAB_00004fc8;
              }
            }
            else {
              uVar6 = local_res20[0] - 0x48;
              if ((uVar6 < 0x31) && ((0x1010000000101U >> ((ulonglong)uVar6 & 0x3f) & 1) != 0))
              goto LAB_0000501a;
            }
            pbVar7 = local_res20;
            uVar3 = uVar11;
            FUN_000027bc((undefined8 *)pbVar7,1,0x11);
            if (local_res20[0] == 1) {
              FUN_00002648((longlong)local_res10,1,0x26);
              local_res10[0] = (local_res10[0] != 1) - 1U & 0x14;
              FUN_00002648((longlong)local_res10,1,0x27);
              pbVar7 = &DAT_00009aa8;
              goto LAB_00004fc8;
            }
          }
          FUN_00008294(pbVar7,uVar3,0x82,local_d8);
          FUN_00002648((longlong)&local_d8,1,0x52);
          goto LAB_00005379;
        }
        (**(code **)(DAT_0000d7a0 + 0x58))(pbVar2);
        FUN_000019fc(param_1);
        pcVar10 = s_Value_of_Param__CHINA_invalid__V_0000c2b0;
      }
    }
    else {
      if (iVar13 != 0xf) goto LAB_00005386;
      puVar9 = &DAT_0000b9e0;
      pbVar2 = (byte *)FUN_000016bc(param_1,&DAT_0000b9e0);
      uVar3 = FUN_0000192c(pbVar2);
      if ((char)uVar3 == '\0') {
        (**(code **)(DAT_0000d7a0 + 0x58))();
        FUN_000019fc(param_1);
        FUN_00001530(param_1,s__PB__Power_battery_support__0000c308);
        FUN_00001530(param_1,s__PB_1__>_Power_battery_default_s_0000c328);
        pcVar10 = s__PB_0__>_Power_battery_default_s_0000c358;
      }
      else {
        uVar4 = FUN_000019a8((char *)pbVar2,puVar9);
        local_res10[0] = (byte)uVar4;
        if (local_res10[0] < 2) {
          uVar12 = 0xbfff;
          uVar1 = 0;
          goto LAB_00005373;
        }
        (**(code **)(DAT_0000d7a0 + 0x58))(pbVar2);
        FUN_000019fc(param_1);
        pcVar10 = s_Value_of_Param__PB_invalid__Valu_0000c388;
      }
    }
LAB_0000543f:
    FUN_00001530(param_1,pcVar10);
  }
  return;
}


// ==== FUN_0000545c @ 0000545c

void FUN_0000545c(longlong param_1,int param_2)

{
  byte *pbVar1;
  undefined8 uVar2;
  ulonglong uVar3;
  longlong lVar4;
  longlong lVar5;
  undefined *puVar6;
  char *pcVar7;
  byte bVar8;
  byte bVar9;
  byte bVar10;
  ulonglong uVar11;
  byte local_res10 [8];
  byte local_98 [128];
  
  uVar11 = (ulonglong)DAT_ff430006;
  if (param_2 == 0) {
    uVar11 = 0;
    local_res10[0] = 0;
    lVar4 = FUN_00002648((longlong)local_res10,1,6);
    FUN_00004614(param_1,lVar4);
    local_res10[0] = 0;
    lVar4 = FUN_00002648((longlong)local_res10,1,7);
    FUN_00004614(param_1,lVar4);
    local_res10[0] = 0;
    lVar5 = FUN_00002648((longlong)local_res10,1,8);
    lVar4 = param_1;
    FUN_00004614(param_1,lVar5);
    FUN_00008294(lVar4,lVar5,0x6c,0);
    FUN_00008294(lVar4,lVar5,0x6d,0);
    FUN_00008294(lVar4,lVar5,0x6e,0);
  }
  else if (param_2 == 1) {
    puVar6 = &DAT_0000ad34;
    pbVar1 = (byte *)FUN_000016bc(param_1,&DAT_0000ad34);
    uVar2 = FUN_0000192c(pbVar1);
    if ((char)uVar2 == '\0') {
      (**(code **)(DAT_0000d7a0 + 0x58))();
      FUN_000019fc(param_1);
      FUN_00001530(param_1,s__Set__Set_RGB_value__0000c3c0);
      pcVar7 = s__Set_<6_digits>__<6_digits>____0_0000c3d8;
    }
    else {
      uVar3 = FUN_000019a8((char *)pbVar1,puVar6);
      uVar11 = (uVar3 & 0xffffffff) / 10000;
      bVar9 = (char)uVar3 + (char)((uVar3 & 0xffffffff) / 100) * -100;
      bVar10 = (byte)uVar11;
      if (((bVar10 < 0x33) &&
          (bVar8 = (byte)((uint)((int)uVar3 + (int)uVar11 * -10000) / 100), bVar8 < 0x33)) &&
         (bVar9 < 0x33)) {
        local_res10[0] = bVar10;
        lVar4 = FUN_00002648((longlong)local_res10,1,6);
        FUN_00004614(param_1,lVar4);
        local_res10[0] = bVar8;
        lVar4 = FUN_00002648((longlong)local_res10,1,7);
        FUN_00004614(param_1,lVar4);
        local_res10[0] = bVar9;
        lVar5 = FUN_00002648((longlong)local_res10,1,8);
        lVar4 = param_1;
        FUN_00004614(param_1,lVar5);
        FUN_00008294(lVar4,lVar5,0x6c,bVar10);
        FUN_00008294(lVar4,lVar5,0x6d,bVar8);
        FUN_00008294(lVar4,lVar5,0x6e,bVar9);
        (**(code **)(DAT_0000d7a0 + 0x58))(pbVar1);
        goto LAB_000056bd;
      }
      (**(code **)(DAT_0000d7a0 + 0x58))(pbVar1);
      FUN_000019fc(param_1);
      pcVar7 = s_Value_of_Param__Set_invalid__Val_0000c480;
    }
    FUN_00001530(param_1,pcVar7);
    FUN_00001530(param_1,s_Sample1___Set_494847__>_Set_Red__0000c408);
    pcVar7 = s_Sample2___Set_090807__>_Set_Red__0000c440;
    goto LAB_000056f2;
  }
LAB_000056bd:
  FUN_00008b40(local_98,0x80,(byte *)s_Current_RGB_Configuration__R__d__0000c4c8,uVar11 & 0xff);
  FUN_000019fc(param_1);
  pcVar7 = (char *)local_98;
LAB_000056f2:
  FUN_00001530(param_1,pcVar7);
  return;
}


// ==== FUN_00005718 @ 00005718

void FUN_00005718(longlong param_1)

{
  *(undefined4 *)(param_1 + 0x14) = 2;
  FUN_000019fc(param_1);
  FUN_00001530(param_1,s__Help___SetApCtrl_support_comman_0000c4f8);
  FUN_00001530(param_1,s__Clear___Revert_SetApCtrl_defaul_0000c520);
  FUN_00001530(param_1,s__GetStatus___Get_the_currently_A_0000c558);
  FUN_00001530(param_1,s__AP___Airplane_Mode_support__0000c588);
  FUN_00001530(param_1,s__GS___GPU_Switch_support__0000c5a8);
  FUN_00001530(param_1,s__OC___Overclock_support__0000c5c8);
  FUN_00001530(param_1,s__MK___Macro_Key_support__0000c5e8);
  FUN_00001530(param_1,s__SK___Shortcut_Key_support__0000c608);
  FUN_00001530(param_1,s__WK___Win_Key_Lock_support__0000c628);
  FUN_00001530(param_1,s__BL___Breath_LED_support__0000c648);
  FUN_00001530(param_1,s__FB___FanBoost_support__0000c668);
  FUN_00001530(param_1,s__SM__Silent_Mode_support__0000bf48);
  FUN_00001530(param_1,s__UC__USB_Charger_support__0000bff0);
  FUN_00001530(param_1,s__RGBKB__RGB_Keyboard_support__0000c098);
  FUN_00001530(param_1,s__RGBLG__RGB_Logo_support__0000c140);
  FUN_00001530(param_1,s__CHINA__RGB_Keyboard_China_suppo_0000c1e8);
  FUN_00001530(param_1,s__PB__Power_battery_support_0000c680);
  return;
}


// ==== FUN_00005834 @ 00005834

undefined8 FUN_00005834(longlong param_1)

{
  undefined8 uVar1;
  
  *(undefined8 *)(param_1 + 0x18) = 0;
  uVar1 = FUN_000015c4(param_1,s__Clear_0000b998);
  if ((char)uVar1 == '\0') {
    uVar1 = FUN_000015c4(param_1,s__Help_0000a6d4);
    if ((char)uVar1 != '\0') {
      FUN_00005718(param_1);
      return 0;
    }
    uVar1 = FUN_000015c4(param_1,s__GetStatus_0000af60);
    if ((char)uVar1 == '\0') {
      uVar1 = FUN_000015c4(param_1,&DAT_0000b9a0);
      if ((char)uVar1 != '\0') {
        FUN_0000478c(param_1,2);
      }
      uVar1 = FUN_000015c4(param_1,&DAT_0000b9a4);
      if ((char)uVar1 != '\0') {
        FUN_0000478c(param_1,3);
      }
      uVar1 = FUN_000015c4(param_1,&DAT_0000b9a8);
      if ((char)uVar1 != '\0') {
        FUN_0000478c(param_1,4);
      }
      uVar1 = FUN_000015c4(param_1,&DAT_0000b9ac);
      if ((char)uVar1 != '\0') {
        FUN_0000478c(param_1,5);
      }
      uVar1 = FUN_000015c4(param_1,&DAT_0000b9b0);
      if ((char)uVar1 != '\0') {
        FUN_0000478c(param_1,6);
      }
      uVar1 = FUN_000015c4(param_1,&DAT_0000b9b4);
      if ((char)uVar1 != '\0') {
        FUN_0000478c(param_1,7);
      }
      uVar1 = FUN_000015c4(param_1,&DAT_0000b9b8);
      if ((char)uVar1 != '\0') {
        FUN_0000478c(param_1,8);
      }
      uVar1 = FUN_000015c4(param_1,&DAT_0000b9bc);
      if ((char)uVar1 != '\0') {
        FUN_0000478c(param_1,9);
      }
      uVar1 = FUN_000015c4(param_1,&DAT_0000b9c0);
      if ((char)uVar1 != '\0') {
        FUN_0000478c(param_1,10);
      }
      uVar1 = FUN_000015c4(param_1,&DAT_0000b9c4);
      if ((char)uVar1 != '\0') {
        FUN_0000478c(param_1,0xb);
      }
      uVar1 = FUN_000015c4(param_1,s__RGBKB_0000b9c8);
      if ((char)uVar1 != '\0') {
        FUN_0000478c(param_1,0xc);
      }
      uVar1 = FUN_000015c4(param_1,s__RGBLG_0000b9d0);
      if ((char)uVar1 != '\0') {
        FUN_0000478c(param_1,0xd);
      }
      uVar1 = FUN_000015c4(param_1,s__CHINA_0000b9d8);
      if ((char)uVar1 != '\0') {
        FUN_0000478c(param_1,0xe);
      }
      uVar1 = FUN_000015c4(param_1,&DAT_0000b9e0);
      if ((char)uVar1 != '\0') {
        FUN_0000478c(param_1,0xf);
      }
      FUN_000019fc(param_1);
      FUN_00001530(param_1,s_Operation_Complete_0000c740);
      return 0;
    }
    uVar1 = 1;
  }
  else {
    uVar1 = 0;
  }
  FUN_0000478c(param_1,uVar1);
  return 0;
}


// ==== FUN_00005b30 @ 00005b30

void FUN_00005b30(undefined1 param_1)

{
  longlong lVar1;
  undefined4 local_res10 [2];
  undefined8 local_res18;
  undefined8 *local_res20;
  undefined1 local_c8 [13];
  undefined1 local_bb;
  
  local_res18 = 0xb4;
  local_res10[0] = 7;
  lVar1 = (**(code **)(DAT_0000d790 + 0xd0))(&DAT_00009040,0,&local_res20);
  if (-1 < lVar1) {
    lVar1 = (*(code *)*local_res20)
                      (u_UniWillVariable_0000ab80,&DAT_000090b0,local_res10,&local_res18,local_c8);
    if (-1 < lVar1) {
      local_bb = param_1;
      (*(code *)local_res20[2])
                (u_UniWillVariable_0000ab80,&DAT_000090b0,local_res10[0],local_res18,local_c8);
    }
  }
  return;
}


// ==== FUN_00005bd8 @ 00005bd8

void FUN_00005bd8(longlong param_1)

{
  *(undefined4 *)(param_1 + 0x14) = 2;
  FUN_000019fc(param_1);
  FUN_00001530(param_1,s__Help___Display_all_Color_Calibr_0000c758);
  FUN_00001530(param_1,s__Set___Set_Color_Calibration_Sup_0000c7a0);
  FUN_00001530(param_1,s__Get___Get_Color_Calibration_Sup_0000c7e8);
  return;
}


// ==== FUN_00005c20 @ 00005c20

void FUN_00005c20(longlong param_1)

{
  byte *pbVar1;
  undefined8 uVar2;
  ulonglong uVar3;
  undefined *puVar4;
  char *pcVar5;
  byte local_res10 [24];
  byte local_108 [256];
  
  puVar4 = &DAT_0000ad34;
  pbVar1 = (byte *)FUN_000016bc(param_1,&DAT_0000ad34);
  uVar2 = FUN_0000192c(pbVar1);
  if ((char)uVar2 == '\0') {
    (**(code **)(DAT_0000d7a0 + 0x58))();
    FUN_000019fc(param_1);
    FUN_00001530(param_1,s__Help___Display_all_Color_Calibr_0000c758);
    FUN_00001530(param_1,s__Set___Set_Color_Calibration_Sup_0000c7a0);
    pcVar5 = s__Get___Get_Color_Calibration_Sup_0000c7e8;
  }
  else {
    uVar3 = FUN_000019a8((char *)pbVar1,puVar4);
    local_res10[0] = (byte)uVar3;
    if (local_res10[0] < 2) {
      (**(code **)(DAT_0000d7a0 + 0x58))(pbVar1);
      (*(code *)PTR_FUN_000090d0)(local_res10,1,0x37);
      FUN_000019fc(param_1);
      FUN_00008b40(local_108,0x100,(byte *)s_Set_Color_Calibration_Support__0_0000c850,
                   (ulonglong)local_res10[0]);
      FUN_00001530(param_1,(char *)local_108);
      FUN_00005b30(local_res10[0]);
      return;
    }
    (**(code **)(DAT_0000d7a0 + 0x58))();
    FUN_000019fc(param_1);
    pcVar5 = s_Value_of_Param__Set_invalid__Val_0000c818;
  }
  FUN_00001530(param_1,pcVar5);
  return;
}


// ==== FUN_00005df4 @ 00005df4

void FUN_00005df4(longlong param_1)

{
  *(undefined4 *)(param_1 + 0x14) = 2;
  FUN_000019fc(param_1);
  FUN_00001530(param_1,s_Usage__0000c900);
  FUN_00001530(param_1,s_RWBlock0__Help___Display_RWBlock_0000c908);
  FUN_00001530(param_1,s_RWBlock0__Dump___Dump_whole_Bloc_0000c940);
  FUN_00001530(param_1,s_RWBlock0__Dump__File___filename__0000c970);
  FUN_00001530(param_1,s_RWBlock0__Load__File___filename__0000c9b8);
  return;
}


// ==== FUN_00005e5c @ 00005e5c

void FUN_00005e5c(longlong param_1)

{
  *(undefined4 *)(param_1 + 0x14) = 2;
  FUN_000019fc(param_1);
  FUN_00001530(param_1,s_Usage__0000c900);
  FUN_00001530(param_1,s_RWBlock0Adv__Help___Display_RWBl_0000c9f8);
  FUN_00001530(param_1,s_RWBlock0Adv__Read__Offset___offs_0000ca30);
  FUN_00001530(param_1,s_RWBlock0Adv__Read__Range___start_0000ca90);
  FUN_00001530(param_1,s_RWBlock0Adv__Write__Offset___off_0000cae0);
  FUN_00001530(param_1,s_RWBlock0Adv__Write__Range___star_0000cb40);
  return;
}


// ==== FUN_00005ed0 @ 00005ed0

undefined8 FUN_00005ed0(longlong param_1,ulonglong *param_2)

{
  byte *pbVar1;
  undefined8 uVar2;
  ulonglong uVar3;
  char *pcVar4;
  
  pcVar4 = s__Offset_0000c8e0;
  pbVar1 = (byte *)FUN_000016bc(param_1,s__Offset_0000c8e0);
  uVar2 = FUN_0000192c(pbVar1);
  if ((char)uVar2 == '\0') {
    (**(code **)(DAT_0000d7a0 + 0x58))();
    FUN_000019fc(param_1);
    FUN_00001530(param_1,s_Value_of_Param__Offset_ivalid__V_0000cbb0);
    uVar2 = 0x8000000000000002;
  }
  else {
    uVar3 = FUN_000019a8((char *)pbVar1,pcVar4);
    *param_2 = uVar3;
    (**(code **)(DAT_0000d7a0 + 0x58))(pbVar1);
    uVar2 = 0;
  }
  return uVar2;
}


// ==== FUN_00005f58 @ 00005f58

undefined8 FUN_00005f58(longlong param_1,ulonglong *param_2,int *param_3)

{
  byte *pbVar1;
  undefined8 uVar2;
  ulonglong uVar3;
  char *pcVar4;
  byte *pbVar5;
  ulonglong uVar6;
  byte *pbVar7;
  ulonglong local_28 [2];
  
  local_28[0] = 0;
  pcVar4 = s__Range_0000c8f0;
  local_28[1] = 0;
  pbVar1 = (byte *)FUN_000016bc(param_1,s__Range_0000c8f0);
  uVar6 = 0;
  do {
    pbVar5 = pbVar1;
    pbVar1 = pbVar5;
    if (*pbVar5 != 0) {
      do {
        if (*pbVar1 == 0x20) goto LAB_00005fb2;
        pbVar1 = pbVar1 + 1;
      } while (*pbVar1 != 0);
      if (*pbVar1 == 0x20) {
LAB_00005fb2:
        *pbVar1 = 0;
        pbVar1 = pbVar1 + 1;
      }
    }
    pbVar7 = pbVar5;
    uVar2 = FUN_0000192c(pbVar5);
    if ((char)uVar2 == '\0') {
      (**(code **)(DAT_0000d7a0 + 0x58))();
      FUN_000019fc(param_1);
      pcVar4 = s_Value_of_Param__Range_ivalid__Va_0000cc50;
      goto LAB_0000602c;
    }
    uVar3 = FUN_000019a8((char *)pbVar7,pcVar4);
    local_28[uVar6] = uVar3;
    uVar6 = uVar6 + 1;
    if (1 < uVar6) {
      if (local_28[0] < local_28[1]) {
        *param_2 = local_28[0];
        *param_3 = (int)local_28[1] - (int)local_28[0];
        (**(code **)(DAT_0000d7a0 + 0x58))(pbVar5);
        uVar2 = 0;
      }
      else {
        FUN_000019fc(param_1);
        pcVar4 = s_Value_of_Param__Range_ivalid_____0000cc98;
LAB_0000602c:
        FUN_00001530(param_1,pcVar4);
        uVar2 = 0x8000000000000002;
      }
      return uVar2;
    }
  } while( true );
}


// ==== FUN_00006264 @ 00006264

char * FUN_00006264(longlong param_1)

{
  byte bVar1;
  undefined4 uVar2;
  undefined8 uVar3;
  longlong lVar4;
  byte *pbVar5;
  ulonglong uVar6;
  char *pcVar7;
  uint uVar8;
  char *pcVar9;
  char *pcVar10;
  int iVar11;
  uint uVar12;
  uint local_res8;
  undefined4 uStackX_c;
  char *local_res10;
  ulonglong uVar13;
  
  *(uint *)(param_1 + 0x14) = *(uint *)(param_1 + 0x14) & 0xfffffffb;
  uVar3 = FUN_000015c4(param_1,s__HelpAdv_0000c8c0);
  pcVar7 = (char *)0x0;
  uVar8 = 0;
  if ((char)uVar3 != '\0') {
    *(undefined8 *)(param_1 + 0x18) = 0;
    goto LAB_0000629b;
  }
  uVar3 = FUN_000015c4(param_1,s__Read_0000c8cc);
  if (((char)uVar3 != '\0') &&
     (uVar3 = FUN_000015c4(param_1,s__Write_0000c8d4), (char)uVar3 != '\0')) {
LAB_000062ca:
    *(undefined8 *)(param_1 + 0x18) = 0x8000000000000002;
LAB_0000629b:
    FUN_00005e5c(param_1);
    return (char *)0x0;
  }
  uVar3 = FUN_000015c4(param_1,s__Read_0000c8cc);
  if ((char)uVar3 == '\0') {
    pcVar9 = (char *)CONCAT44(uStackX_c,local_res8);
LAB_0000643e:
    uVar3 = FUN_000015c4(param_1,s__Write_0000c8d4);
    if ((char)uVar3 == '\0') {
      *(undefined8 *)(param_1 + 0x18) = 0x8000000000000002;
      FUN_00005e5c(param_1);
      return pcVar9;
    }
    local_res10 = (char *)0x0;
    local_res8 = 0;
    uVar3 = FUN_000015c4(param_1,s__Data_0000c8f8);
    if (((char)uVar3 != '\0') &&
       (uVar3 = FUN_000015c4(param_1,s__File_0000a690), (char)uVar3 != '\0')) goto LAB_000062ca;
    uVar3 = FUN_000015c4(param_1,s__Offset_0000c8e0);
    pcVar9 = pcVar7;
    if ((((char)uVar3 != '\0') &&
        (lVar4 = FUN_00005ed0(param_1,(ulonglong *)&local_res10), pcVar9 = local_res10, lVar4 < 0))
       || ((uVar3 = FUN_000015c4(param_1,s__Range_0000c8f0), uVar8 = 0, (char)uVar3 != '\0' &&
           (lVar4 = FUN_00005f58(param_1,(ulonglong *)&local_res10,(int *)&local_res8),
           pcVar9 = local_res10, uVar8 = local_res8, lVar4 < 0)))) goto LAB_00006343;
    uVar3 = FUN_000015c4(param_1,s__Data_0000c8f8);
    if ((char)uVar3 != '\0') {
      pcVar10 = s__Data_0000c8f8;
      pbVar5 = (byte *)FUN_000016bc(param_1,s__Data_0000c8f8);
      FUN_000019fc(param_1);
      uVar3 = FUN_0000192c(pbVar5);
      if ((char)uVar3 != '\0') {
        uVar6 = FUN_000019a8((char *)pbVar5,pcVar10);
        *(ulonglong *)(param_1 + 0x24) = uVar6;
        if (uVar6 < 0x100000000) {
          if (uVar6 < 0x10000) {
            iVar11 = (0xff < uVar6) + 1;
          }
          else {
            iVar11 = 4;
          }
        }
        else {
          iVar11 = 8;
        }
        *(int *)(param_1 + 0x20) = iVar11;
        goto LAB_00006343;
      }
      bVar1 = *pbVar5;
      pcVar10 = pcVar7;
      while (bVar1 != 0) {
        pcVar10 = pcVar10 + 1;
        bVar1 = pcVar10[(longlong)pbVar5];
      }
      if ((pcVar10 != (char *)0x0) && ((byte *)(param_1 + 0x24) != pbVar5)) {
        FUN_00001180((undefined8 *)(param_1 + 0x24),(undefined8 *)pbVar5,(ulonglong)pcVar10);
      }
      bVar1 = *pbVar5;
      pcVar10 = pcVar7;
      while (bVar1 != 0) {
        pcVar10 = pcVar10 + 1;
        bVar1 = pcVar10[(longlong)pbVar5];
      }
      *(int *)(param_1 + 0x20) = (int)pcVar10;
      (**(code **)(DAT_0000d7a0 + 0x58))(pbVar5);
    }
    uVar3 = FUN_000015c4(param_1,s__File_0000a690);
    if ((char)uVar3 == '\0') {
      if (uVar8 == 0) {
        uVar8 = *(uint *)(param_1 + 0x20);
      }
      else {
        uVar12 = *(uint *)(param_1 + 0x20);
        uVar6 = (ulonglong)uVar12;
        if (uVar12 < uVar8) {
          uVar13 = (ulonglong)uVar8 / (ulonglong)uVar12;
          uVar8 = uVar8 % uVar12;
          uVar12 = (uint)uVar13;
          while (uVar12 != 0) {
            FUN_00002648(param_1 + 0x24,(uint)uVar6,(longlong)pcVar9);
            uVar6 = (ulonglong)*(uint *)(param_1 + 0x20);
            pcVar9 = pcVar9 + uVar6;
            uVar12 = (int)uVar13 - 1;
            uVar13 = (ulonglong)uVar12;
          }
        }
      }
      FUN_00002648(param_1 + 0x24,uVar8,(longlong)pcVar9);
      *(undefined4 *)(param_1 + 0x14) = 2;
      *(undefined8 *)(param_1 + 0x18) = 0;
      FUN_000019fc(param_1);
      FUN_00001530(param_1,s_RWBlock0Adv__Write_success__0000cd38);
      return (char *)0x0;
    }
    local_res8 = 0;
    if (*(int *)(param_1 + 0x20) != 0) {
      pcVar7 = FUN_00001824(param_1,&local_res8);
    }
    uVar8 = local_res8;
    FUN_000019fc(param_1);
    if (uVar8 != 0) {
      if ((char *)(param_1 + 0x24) != pcVar7) {
        FUN_00001180((undefined8 *)(param_1 + 0x24),(undefined8 *)pcVar7,(ulonglong)uVar8);
      }
      *(uint *)(param_1 + 0x20) = uVar8;
      (**(code **)(DAT_0000d7a0 + 0x58))(pcVar7);
      goto LAB_00006343;
    }
    (**(code **)(DAT_0000d7a0 + 0x58))(pcVar7);
    pcVar7 = s_File_is_empty_or_file_did_not_ex_0000ccd8;
  }
  else {
    local_res10 = (char *)0x0;
    local_res8 = 0;
    uVar3 = FUN_000015c4(param_1,s__Offset_0000c8e0);
    if (((char)uVar3 == '\0') ||
       (uVar3 = FUN_000015c4(param_1,s__Size_0000c8e8), (char)uVar3 == '\0')) {
      pcVar9 = (char *)CONCAT44(uStackX_c,local_res8);
LAB_000063bb:
      uVar3 = FUN_000015c4(param_1,s__Range_0000c8f0);
      if (((char)uVar3 != '\0') &&
         (pcVar9 = (char *)FUN_00005f58(param_1,(ulonglong *)&local_res10,(int *)&local_res8),
         uVar8 = local_res8, (longlong)pcVar9 < 0)) goto LAB_00006343;
      uVar3 = FUN_000015c4(param_1,s__File_0000a690);
      if (uVar8 != 0) {
        FUN_000019fc(param_1);
        FUN_000027bc((undefined8 *)(param_1 + 0x24),uVar8,(longlong)local_res10);
        *(undefined4 *)(param_1 + 0x14) = 1;
        uVar2 = *(undefined4 *)(param_1 + 0x14);
        if ((char)uVar3 != '\0') {
          uVar2 = 5;
        }
        *(uint *)(param_1 + 0x20) = uVar8;
        *(undefined4 *)(param_1 + 0x14) = uVar2;
        *(undefined8 *)(param_1 + 0x18) = 0;
        return (char *)0x0;
      }
      goto LAB_0000643e;
    }
    lVar4 = FUN_00005ed0(param_1,(ulonglong *)&local_res10);
    if (lVar4 < 0) goto LAB_00006343;
    pcVar9 = s__Size_0000c8e8;
    pbVar5 = (byte *)FUN_000016bc(param_1,s__Size_0000c8e8);
    uVar3 = FUN_0000192c(pbVar5);
    if ((char)uVar3 != '\0') {
      uVar6 = FUN_000019a8((char *)pbVar5,pcVar9);
      uVar8 = (uint)uVar6;
      local_res8 = uVar8;
      (**(code **)(DAT_0000d7a0 + 0x58))(pbVar5);
      pcVar9 = pcVar7;
      goto LAB_000063bb;
    }
    (**(code **)(DAT_0000d7a0 + 0x58))();
    FUN_000019fc(param_1);
    pcVar7 = s_Value_of_Param__Size_ivalid__Val_0000cc00;
  }
  FUN_00001530(param_1,pcVar7);
LAB_00006343:
  *(undefined8 *)(param_1 + 0x18) = 0x8000000000000002;
  return (char *)0x0;
}


// ==== FUN_000066d0 @ 000066d0

void FUN_000066d0(longlong param_1)

{
  longlong lVar1;
  uint *puVar2;
  byte local_108 [256];
  
  FUN_000019fc(param_1);
  FUN_00001530(param_1,s__Help___Display_all__Display_Mod_0000cd70);
  FUN_00001530(param_1,s__Get___Get_current__Display_Mode_0000cda0);
  FUN_00001530(param_1,s__Set___Select_Display_Mode_suppo_0000cdd0);
  puVar2 = &DAT_00009c08;
  lVar1 = 2;
  do {
    FUN_00008b40(local_108,0x100,(byte *)s__Set__d__>__s_0000ade0,(ulonglong)*puVar2);
    FUN_00001530(param_1,(char *)local_108);
    puVar2 = puVar2 + 3;
    lVar1 = lVar1 + -1;
  } while (lVar1 != 0);
  return;
}


// ==== FUN_00006774 @ 00006774

void FUN_00006774(longlong param_1)

{
  char *pcVar1;
  byte bVar2;
  ulonglong uVar3;
  byte local_res10 [24];
  byte local_108 [256];
  
  (*(code *)PTR_FUN_000090d8)(local_res10);
  uVar3 = 0;
  do {
    if ((uint)local_res10[0] == (&DAT_00009c08)[uVar3 * 3]) {
      FUN_00008b40(local_108,0x100,(byte *)s_Current_Display_Mode___s_0000cdf8,
                   *(undefined8 *)((longlong)&PTR_s_Mshybrid_00009c00 + uVar3 * 0xc));
      FUN_000019fc(param_1);
      pcVar1 = (char *)local_108;
      goto LAB_0000680d;
    }
    bVar2 = (char)uVar3 + 1;
    uVar3 = (ulonglong)bVar2;
  } while (bVar2 < 2);
  *(undefined8 *)(param_1 + 0x18) = 0x8000000000000002;
  FUN_000019fc(param_1);
  pcVar1 = s_ERROR__invalid_Display_Mode__0000ce18;
LAB_0000680d:
  FUN_00001530(param_1,pcVar1);
  return;
}


// ==== FUN_00006820 @ 00006820

void FUN_00006820(longlong param_1)

{
  byte *pbVar1;
  undefined8 uVar2;
  ulonglong uVar3;
  undefined *puVar4;
  longlong lVar5;
  byte bVar6;
  uint *puVar7;
  byte local_res10 [8];
  byte local_118 [256];
  
  puVar4 = &DAT_0000ad34;
  pbVar1 = (byte *)FUN_000016bc(param_1,&DAT_0000ad34);
  uVar2 = FUN_0000192c(pbVar1);
  lVar5 = 2;
  if ((char)uVar2 == '\x01') {
    uVar3 = FUN_000019a8((char *)pbVar1,puVar4);
    local_res10[0] = (byte)uVar3;
    (**(code **)(DAT_0000d7a0 + 0x58))(pbVar1);
    uVar3 = 0;
    do {
      if ((uint)local_res10[0] == (&DAT_00009c08)[uVar3 * 3]) {
        (*(code *)PTR_FUN_000090d0)(local_res10,1,0x38);
        FUN_00008b40(local_118,0x100,(byte *)s_Set_Display_Mode___s_s_0000ce38,
                     *(undefined8 *)((longlong)&PTR_s_Mshybrid_00009c00 + uVar3 * 0xc));
        FUN_000019fc(param_1);
        FUN_00001530(param_1,(char *)local_118);
        return;
      }
      bVar6 = (char)uVar3 + 1;
      uVar3 = (ulonglong)bVar6;
    } while (bVar6 < 2);
  }
  FUN_000019fc(param_1);
  *(undefined8 *)(param_1 + 0x18) = 0x8000000000000002;
  FUN_00001530(param_1,s_invalid_parameter__supported_val_0000af08);
  puVar7 = &DAT_00009c08;
  do {
    FUN_00008b40(local_118,0x100,(byte *)s__Set__d__>__s_0000ade0,(ulonglong)*puVar7);
    FUN_00001530(param_1,(char *)local_118);
    puVar7 = puVar7 + 3;
    lVar5 = lVar5 + -1;
  } while (lVar5 != 0);
  (**(code **)(DAT_0000d7a0 + 0x58))(pbVar1);
  return;
}


// ==== FUN_00006a1c @ 00006a1c

void FUN_00006a1c(longlong param_1,byte *param_2,undefined8 param_3,longlong param_4)

{
  longlong lVar1;
  byte local_78 [112];
  
  if ((byte *)(param_4 + 0xff430000) == param_2) {
    lVar1 = 0;
  }
  else {
    lVar1 = FUN_00001200((char *)(param_4 + 0xff430000),(char *)param_2,1);
  }
  if (lVar1 != 0) {
    lVar1 = (*(code *)PTR_FUN_000090d0)(param_2,1,param_4);
    if (lVar1 < 0) {
      FUN_00008b40(local_78,100,(byte *)s_ERROR__Write_data_to_OEM_ROM_are_0000ce70,
                   (ulonglong)*param_2);
      FUN_00001530(param_1,(char *)local_78);
    }
  }
  return;
}


// ==== FUN_00006ab8 @ 00006ab8

void FUN_00006ab8(undefined1 param_1,undefined1 param_2,undefined1 param_3,undefined1 param_4)

{
  longlong lVar1;
  undefined4 local_e8 [2];
  undefined8 local_e0;
  undefined8 *local_d8 [2];
  undefined1 local_c8 [9];
  undefined1 local_bf;
  undefined1 local_be;
  undefined1 local_bd;
  undefined1 local_bc;
  
  local_e0 = 0xb4;
  local_e8[0] = 7;
  lVar1 = (**(code **)(DAT_0000d790 + 0xd0))(&DAT_00009040,0,local_d8);
  if (-1 < lVar1) {
    lVar1 = (*(code *)*local_d8[0])
                      (u_UniWillVariable_0000ab80,&DAT_000090b0,local_e8,&local_e0,local_c8);
    if (-1 < lVar1) {
      local_bf = param_1;
      local_be = param_2;
      local_bd = param_3;
      local_bc = param_4;
      (*(code *)local_d8[0][2])
                (u_UniWillVariable_0000ab80,&DAT_000090b0,local_e8[0],local_e0,local_c8);
    }
  }
  return;
}


// ==== FUN_00006b9c @ 00006b9c

void FUN_00006b9c(longlong param_1)

{
  FUN_000019fc(param_1);
  FUN_00001530(param_1,s_Usage__0000c900);
  FUN_00001530(param_1,s__SetMode_<value>_0000cec8);
  FUN_00001530(param_1,s_0__Disable_0000cee0);
  FUN_00001530(param_1,s_1__Welcome_0000cef8);
  FUN_00001530(param_1,s_2__White_0000cf10);
  FUN_00001530(param_1,s_3__Red_0000cf28);
  FUN_00001530(param_1,s_0xFF__Unsupport_RGB_Light_Bar__0000cf38);
  FUN_00001530(param_1,s__SetControl_<value>_0000cf60);
  FUN_00001530(param_1,s_0__Disable_welcome_light_mode_0000cf78);
  FUN_00001530(param_1,s_0x80__Enable_welcome_light_mode_0000cfa0);
  FUN_00001530(param_1,s__SetRGB_<red_value>_<green_value_0000cfc8);
  FUN_00001530(param_1,s_value_range__0_<__value_<__200_0000d000);
  FUN_00001530(param_1,s__Dump_0000d028);
  FUN_00001530(param_1,s_Dump_Data_0000d030);
  return;
}


// ==== FUN_00006c84 @ 00006c84

void FUN_00006c84(longlong param_1,undefined8 param_2,undefined8 param_3)

{
  byte *pbVar1;
  undefined8 uVar2;
  ulonglong uVar3;
  char *pcVar4;
  undefined1 uVar5;
  undefined7 uVar6;
  undefined8 local_res10;
  
  uVar5 = (undefined1)param_3;
  uVar6 = (undefined7)((ulonglong)param_3 >> 8);
  pcVar4 = s__SetMode_0000b6c8;
  local_res10 = 0;
  pbVar1 = (byte *)FUN_000016bc(param_1,s__SetMode_0000b6c8);
  uVar2 = FUN_0000192c(pbVar1);
  if ((char)uVar2 == '\0') {
    (**(code **)(DAT_0000d7a0 + 0x58))();
    FUN_000019fc(param_1);
    pcVar4 = s__SetMode__Parameter_is_not_a_num_0000d040;
LAB_00006cdb:
    FUN_00001530(param_1,pcVar4);
  }
  else {
    uVar3 = FUN_000019a8((char *)pbVar1,pcVar4);
    local_res10 = CONCAT44(local_res10._4_4_,(int)uVar3) & 0xffffffff000000ff;
    (**(code **)(DAT_0000d7a0 + 0x58))(pbVar1);
    FUN_000019fc(param_1);
    if ((int)local_res10 == 0) {
LAB_00006daa:
      pcVar4 = s_Set_UNSUPPORT_mode__0000d068;
      if ((int)local_res10 != 0xff) {
        pcVar4 = s_Set_DISABLE_mode__0000d080;
      }
      FUN_00001530(param_1,pcVar4);
      local_res10 = local_res10 & 0xffffffff;
    }
    else if ((int)local_res10 == 1) {
      FUN_00001530(param_1,s_Set_WELCOME_mode__0000d098);
      local_res10 = CONCAT44(0x80,(int)local_res10);
    }
    else if ((int)local_res10 == 2) {
      FUN_00001530(param_1,s_Set_WHITE_mode__0000d0b0);
      local_res10 = CONCAT44(0x24242400,(int)local_res10);
    }
    else {
      if ((int)local_res10 != 3) {
        if ((int)local_res10 == 0xfe) {
          pcVar4 = s_Current_not_support_CUSTOMIZATIO_0000d0d0;
          *(undefined8 *)(param_1 + 0x18) = 0x8000000000000003;
        }
        else {
          if ((int)local_res10 == 0xff) goto LAB_00006daa;
          pcVar4 = s_Invalid_settings__NO_changes__0000d0f8;
          *(undefined8 *)(param_1 + 0x18) = 0x8000000000000002;
        }
        goto LAB_00006cdb;
      }
      FUN_00001530(param_1,s_Set_RED_mode__0000d0c0);
      local_res10 = CONCAT44(0x2400,(int)local_res10);
    }
    FUN_00006a1c(param_1,(byte *)&local_res10,CONCAT71(uVar6,uVar5),0x2e);
    FUN_00006a1c(param_1,(byte *)((longlong)&local_res10 + 4),CONCAT71(uVar6,uVar5),0x2f);
    FUN_00006a1c(param_1,(byte *)((longlong)&local_res10 + 5),CONCAT71(uVar6,uVar5),0x30);
    FUN_00006a1c(param_1,(byte *)((longlong)&local_res10 + 6),CONCAT71(uVar6,uVar5),0x31);
    FUN_00006a1c(param_1,(byte *)((longlong)&local_res10 + 7),CONCAT71(uVar6,uVar5),0x32);
    FUN_00006ab8((byte)local_res10,local_res10._5_1_,local_res10._6_1_,local_res10._7_1_);
  }
  return;
}


// ==== FUN_00006e50 @ 00006e50

void FUN_00006e50(longlong param_1)

{
  byte *pbVar1;
  undefined8 uVar2;
  ulonglong uVar3;
  char *pcVar4;
  byte local_res10 [4];
  uint local_res14 [5];
  byte local_78 [112];
  
  local_res10[0] = 0;
  local_res10[1] = 0;
  local_res10[2] = 0;
  local_res10[3] = 0;
  pcVar4 = s__SetControl_0000ce50;
  local_res14[0] = 0;
  pbVar1 = (byte *)FUN_000016bc(param_1,s__SetControl_0000ce50);
  uVar2 = FUN_0000192c(pbVar1);
  if ((char)uVar2 != '\0') {
    local_res10[0] = 0xfe;
    local_res10[1] = 0;
    local_res10[2] = 0;
    local_res10[3] = 0;
    uVar3 = FUN_000019a8((char *)pbVar1,pcVar4);
    local_res14[0] = CONCAT31(local_res14[0]._1_3_,(char)uVar3);
    (**(code **)(DAT_0000d7a0 + 0x58))(pbVar1);
    if ((local_res14[0] & 0x7f) == 0) {
      FUN_000019fc(param_1);
      FUN_00001530(param_1,s_Set_Customization_mode__0000d118);
      pcVar4 = s_Set_Control_value_0x_02x_0000d130;
      FUN_00008b40(local_78,100,(byte *)s_Set_Control_value_0x_02x_0000d130,
                   (ulonglong)(byte)local_res14[0]);
      FUN_00001530(param_1,(char *)local_78);
      FUN_00006a1c(param_1,local_res10,pcVar4,0x2e);
      FUN_00006a1c(param_1,(byte *)local_res14,pcVar4,0x2f);
      return;
    }
  }
  (**(code **)(DAT_0000d7a0 + 0x58))(pbVar1);
  FUN_000019fc(param_1);
  *(undefined8 *)(param_1 + 0x18) = 0x8000000000000002;
  FUN_00001530(param_1,s_invalid_parameter__supported_val_0000af08);
  FUN_00001530(param_1,s__SetControl_0__>_Disable_welcome_0000d150);
  FUN_00001530(param_1,s__SetControl_0x80__>_Enable_welco_0000d188);
  return;
}


// ==== FUN_00006f90 @ 00006f90

void FUN_00006f90(longlong param_1)

{
  byte bVar1;
  byte *pbVar2;
  undefined8 uVar3;
  ulonglong uVar4;
  char *pcVar5;
  byte *pbVar6;
  ulonglong uVar7;
  undefined8 local_res10;
  byte local_88 [112];
  
  pcVar5 = s__SetRGB_0000ce60;
  local_res10 = 0xfe;
  pbVar2 = (byte *)FUN_000016bc(param_1,s__SetRGB_0000ce60);
  FUN_000019fc(param_1);
  uVar7 = 0;
  do {
    pbVar6 = pbVar2;
    if (*pbVar2 != 0) {
      do {
        if (*pbVar6 == 0x20) goto LAB_00006fec;
        pbVar6 = pbVar6 + 1;
      } while (*pbVar6 != 0);
      if (*pbVar6 == 0x20) {
LAB_00006fec:
        *pbVar6 = 0;
        pbVar6 = pbVar6 + 1;
      }
    }
    uVar3 = FUN_0000192c(pbVar2);
    if ((char)uVar3 == '\0') {
      pcVar5 = s__SetRGB__Contain_non_integer_dat_0000d1c0;
LAB_0000713d:
      FUN_00001530(param_1,pcVar5);
      return;
    }
    uVar4 = FUN_000019a8((char *)pbVar2,pcVar5);
    bVar1 = (byte)uVar4;
    if (200 < bVar1) {
      pcVar5 = s__SetRGB__parameter_is_over_than_2_0000d1e8;
      goto LAB_0000713d;
    }
    if (uVar7 == 0) {
      local_res10._0_6_ = CONCAT15(bVar1,(undefined5)local_res10);
    }
    else if (uVar7 == 1) {
      local_res10._0_7_ = CONCAT16(bVar1,(undefined6)local_res10);
    }
    else if (uVar7 == 2) {
      local_res10 = CONCAT17(bVar1,(undefined7)local_res10);
    }
    else {
      FUN_00008b40(local_88,100,(byte *)s__SetRgb__Ignore_parameter_d___s__0000d210,uVar7 + 1);
      pcVar5 = (char *)local_88;
      FUN_00001530(param_1,pcVar5);
    }
    uVar7 = uVar7 + 1;
    pbVar2 = pbVar6;
    if (2 < uVar7) {
      (**(code **)(DAT_0000d7a0 + 0x58))(pbVar6);
      FUN_00001530(param_1,s_Set_Customization_mode__0000d118);
      pcVar5 = s_Set_RGB__0x_02x_0x_02x_0x_02x_0000d238;
      FUN_00008b40(local_88,100,(byte *)s_Set_RGB__0x_02x_0x_02x_0x_02x_0000d238,
                   local_res10 >> 0x28 & 0xff);
      FUN_00001530(param_1,(char *)local_88);
      FUN_00006a1c(param_1,(byte *)&local_res10,pcVar5,0x2e);
      FUN_00006a1c(param_1,(byte *)((longlong)&local_res10 + 4),pcVar5,0x2f);
      FUN_00006a1c(param_1,(byte *)((longlong)&local_res10 + 5),pcVar5,0x30);
      FUN_00006a1c(param_1,(byte *)((longlong)&local_res10 + 6),pcVar5,0x31);
      FUN_00006a1c(param_1,(byte *)((longlong)&local_res10 + 7),pcVar5,0x32);
      FUN_00006ab8((byte)local_res10,local_res10._5_1_,local_res10._6_1_,local_res10._7_1_);
      return;
    }
  } while( true );
}


// ==== FUN_00007160 @ 00007160

/* WARNING: Type propagation algorithm not settling */

void FUN_00007160(longlong param_1)

{
  uint local_res10;
  undefined1 uStackX_15;
  undefined1 uStackX_16;
  undefined4 local_res14;
  undefined1 uStackX_17;
  byte local_78 [112];
  
  local_res10 = 0;
  local_res14 = 0;
  (*(code *)PTR_FUN_000090d8)(&local_res10,1,0x2e);
  (*(code *)PTR_FUN_000090d8)(&stack0x00000014,1,0x2f);
  (*(code *)PTR_FUN_000090d8)(&uStackX_15,1,0x30);
  (*(code *)PTR_FUN_000090d8)(&uStackX_16,1,0x31);
  (*(code *)PTR_FUN_000090d8)(&uStackX_17,1,0x32);
  FUN_000019fc(param_1);
  FUN_00008b40(local_78,100,(byte *)s_Mode_0x_02x__Control_0x_02x__Red_0000d260,
               (ulonglong)local_res10);
  FUN_00001530(param_1,(char *)local_78);
  return;
}


// ==== FUN_000072f0 @ 000072f0

void FUN_000072f0(longlong param_1)

{
  *(undefined4 *)(param_1 + 0x14) = 2;
  FUN_000019fc(param_1);
  FUN_00001530(param_1,s_Usage__0000c900);
  FUN_00001530(param_1,s_LOGO__Help___Display_LOGO_comman_0000d2a8);
  FUN_00001530(param_1,s_LOGO__Load__File___filename____L_0000d2d8);
  return;
}


// ==== FUN_00007594 @ 00007594

void FUN_00007594(longlong param_1)

{
  longlong lVar1;
  uint *puVar2;
  byte local_108 [256];
  
  FUN_000019fc(param_1);
  FUN_00001530(param_1,s__Help___Display_all__Turbo_Mode__0000d378);
  FUN_00001530(param_1,s__Get___Get_current__Turbo_Mode__s_0000d3a8);
  FUN_00001530(param_1,s__Set___Select_Turbo_Mode_support_0000d3d8);
  puVar2 = &DAT_00009cd8;
  lVar1 = 2;
  do {
    FUN_00008b40(local_108,0x100,(byte *)s__Set__d__>__s_0000ade0,(ulonglong)*puVar2);
    FUN_00001530(param_1,(char *)local_108);
    puVar2 = puVar2 + 3;
    lVar1 = lVar1 + -1;
  } while (lVar1 != 0);
  return;
}


// ==== FUN_00007638 @ 00007638

void FUN_00007638(longlong param_1)

{
  char *pcVar1;
  byte bVar2;
  ulonglong uVar3;
  byte local_res10 [24];
  byte local_108 [256];
  
  (*(code *)PTR_FUN_000090d8)(local_res10);
  uVar3 = 0;
  do {
    if ((uint)local_res10[0] == (&DAT_00009cd8)[uVar3 * 3]) {
      FUN_00008b40(local_108,0x100,(byte *)s_Current_Turbo_Mode___s_0000d400,
                   *(undefined8 *)((longlong)&PTR_s_Disable_00009cd0 + uVar3 * 0xc));
      FUN_000019fc(param_1);
      pcVar1 = (char *)local_108;
      goto LAB_000076d1;
    }
    bVar2 = (char)uVar3 + 1;
    uVar3 = (ulonglong)bVar2;
  } while (bVar2 < 2);
  *(undefined8 *)(param_1 + 0x18) = 0x8000000000000002;
  FUN_000019fc(param_1);
  pcVar1 = s_ERROR__invalid_Turbo_Mode__0000d418;
LAB_000076d1:
  FUN_00001530(param_1,pcVar1);
  return;
}


// ==== FUN_000076e4 @ 000076e4

void FUN_000076e4(longlong param_1)

{
  byte *pbVar1;
  undefined8 uVar2;
  ulonglong uVar3;
  undefined *puVar4;
  longlong lVar5;
  byte bVar6;
  uint *puVar7;
  byte local_res10 [8];
  byte local_118 [256];
  
  puVar4 = &DAT_0000ad34;
  pbVar1 = (byte *)FUN_000016bc(param_1,&DAT_0000ad34);
  uVar2 = FUN_0000192c(pbVar1);
  lVar5 = 2;
  if ((char)uVar2 == '\x01') {
    uVar3 = FUN_000019a8((char *)pbVar1,puVar4);
    local_res10[0] = (byte)uVar3;
    (**(code **)(DAT_0000d7a0 + 0x58))(pbVar1);
    uVar3 = 0;
    do {
      if ((uint)local_res10[0] == (&DAT_00009cd8)[uVar3 * 3]) {
        (*(code *)PTR_FUN_000090d0)(local_res10,1,0x36);
        FUN_00008b40(local_118,0x100,(byte *)s_Set_Turbo_Mode___s_s_0000d438,
                     *(undefined8 *)((longlong)&PTR_s_Disable_00009cd0 + uVar3 * 0xc));
        FUN_000019fc(param_1);
        FUN_00001530(param_1,(char *)local_118);
        return;
      }
      bVar6 = (char)uVar3 + 1;
      uVar3 = (ulonglong)bVar6;
    } while (bVar6 < 2);
  }
  FUN_000019fc(param_1);
  *(undefined8 *)(param_1 + 0x18) = 0x8000000000000002;
  FUN_00001530(param_1,s_invalid_parameter__supported_val_0000af08);
  puVar7 = &DAT_00009cd8;
  do {
    FUN_00008b40(local_118,0x100,(byte *)s__Set__d__>__s_0000ade0,(ulonglong)*puVar7);
    FUN_00001530(param_1,(char *)local_118);
    puVar7 = puVar7 + 3;
    lVar5 = lVar5 + -1;
  } while (lVar5 != 0);
  (**(code **)(DAT_0000d7a0 + 0x58))(pbVar1);
  return;
}


// ==== FUN_000078e0 @ 000078e0

undefined8 FUN_000078e0(longlong param_1)

{
  FUN_000019fc(param_1);
  *(undefined4 *)(param_1 + 0x14) = 2;
  *(undefined8 *)(param_1 + 0x18) = 0x8000000000000003;
  FUN_00001530(param_1,s_Unsupported__0000d468);
  return 0;
}


// ==== FUN_0000791c @ 0000791c

void FUN_0000791c(longlong param_1)

{
  *(undefined4 *)(param_1 + 0x14) = 2;
  FUN_000019fc(param_1);
  FUN_00001530(param_1,s__Help___Display_all_KeyboardLigh_0000d478);
  FUN_00001530(param_1,s__Set___Set_KeyboardLight_Support_0000d4b0);
  FUN_00001530(param_1,s__Get___Get_KeyboardLight_Support_0000d500);
  return;
}


// ==== FUN_00007964 @ 00007964

void FUN_00007964(longlong param_1)

{
  byte *pbVar1;
  undefined8 uVar2;
  ulonglong uVar3;
  undefined *puVar4;
  char *pcVar5;
  byte local_res10 [24];
  byte local_108 [256];
  
  puVar4 = &DAT_0000ad34;
  pbVar1 = (byte *)FUN_000016bc(param_1,&DAT_0000ad34);
  uVar2 = FUN_0000192c(pbVar1);
  if ((char)uVar2 == '\0') {
    (**(code **)(DAT_0000d7a0 + 0x58))();
    FUN_000019fc(param_1);
    FUN_00001530(param_1,s__Set_KeyboardLight_Support_NotSu_0000d530);
    FUN_00001530(param_1,s__Set_1__>_KeyboardLight_Support__0000d558);
    pcVar5 = s__Set_0__>_KeyboardLight_NoSuppor_0000d580;
  }
  else {
    uVar3 = FUN_000019a8((char *)pbVar1,puVar4);
    local_res10[0] = (byte)uVar3;
    if (local_res10[0] < 2) {
      (**(code **)(DAT_0000d7a0 + 0x58))(pbVar1);
      (*(code *)PTR_FUN_000090d0)(local_res10,1,0x35);
      FUN_000019fc(param_1);
      FUN_00008b40(local_108,0x100,(byte *)s_Set_KeyBoardLight_Support__0x_02_0000d5a8,
                   (ulonglong)local_res10[0]);
      pcVar5 = (char *)local_108;
    }
    else {
      (**(code **)(DAT_0000d7a0 + 0x58))();
      FUN_000019fc(param_1);
      pcVar5 = s_Value_of_Param__Set_invalid__Val_0000c818;
    }
  }
  FUN_00001530(param_1,pcVar5);
  return;
}


// ==== FUN_00007b1c @ 00007b1c

void FUN_00007b1c(longlong param_1)

{
  longlong lVar1;
  uint *puVar2;
  byte local_108 [256];
  
  FUN_000019fc(param_1);
  FUN_00001530(param_1,s__Help___Display_all__Model_ID__c_0000d630);
  FUN_00001530(param_1,s__Get___Get_current__Model_ID__se_0000d660);
  FUN_00001530(param_1,s__Set___Select_Model_ID__0000d690);
  puVar2 = &DAT_00009d88;
  lVar1 = 10;
  do {
    FUN_00008b40(local_108,0x100,(byte *)s__Set__d__>__s_0000ade0,(ulonglong)*puVar2);
    FUN_00001530(param_1,(char *)local_108);
    puVar2 = puVar2 + 3;
    lVar1 = lVar1 + -1;
  } while (lVar1 != 0);
  return;
}


// ==== FUN_00007bc0 @ 00007bc0

void FUN_00007bc0(longlong param_1)

{
  char *pcVar1;
  byte bVar2;
  ulonglong uVar3;
  byte local_res10 [24];
  byte local_108 [256];
  
  (*(code *)PTR_FUN_000090d8)(local_res10);
  uVar3 = 0;
  do {
    if ((uint)local_res10[0] == (&DAT_00009d88)[uVar3 * 3]) {
      FUN_00008b40(local_108,0x100,(byte *)s_Current_Model_ID___s_0000d6b0,
                   *(undefined8 *)((longlong)&PTR_DAT_00009d80 + uVar3 * 0xc));
      FUN_000019fc(param_1);
      pcVar1 = (char *)local_108;
      goto LAB_00007c59;
    }
    bVar2 = (char)uVar3 + 1;
    uVar3 = (ulonglong)bVar2;
  } while (bVar2 < 10);
  *(undefined8 *)(param_1 + 0x18) = 0x8000000000000002;
  FUN_000019fc(param_1);
  pcVar1 = s_ERROR__invalid_Model_ID__0000d6c8;
LAB_00007c59:
  FUN_00001530(param_1,pcVar1);
  return;
}


// ==== FUN_00007c6c @ 00007c6c

void FUN_00007c6c(longlong param_1)

{
  byte *pbVar1;
  undefined8 uVar2;
  ulonglong uVar3;
  undefined *puVar4;
  longlong lVar5;
  byte bVar6;
  uint *puVar7;
  byte local_res10 [8];
  byte local_118 [256];
  
  puVar4 = &DAT_0000ad34;
  pbVar1 = (byte *)FUN_000016bc(param_1,&DAT_0000ad34);
  uVar2 = FUN_0000192c(pbVar1);
  lVar5 = 10;
  if ((char)uVar2 == '\x01') {
    uVar3 = FUN_000019a8((char *)pbVar1,puVar4);
    local_res10[0] = (byte)uVar3;
    (**(code **)(DAT_0000d7a0 + 0x58))(pbVar1);
    uVar3 = 0;
    do {
      if ((uint)local_res10[0] == (&DAT_00009d88)[uVar3 * 3]) {
        (*(code *)PTR_FUN_000090d0)(local_res10,1,0x39);
        FUN_00008b40(local_118,0x100,(byte *)s_Set_Model_ID___s_s_0000d6e8,
                     *(undefined8 *)((longlong)&PTR_DAT_00009d80 + uVar3 * 0xc));
        FUN_000019fc(param_1);
        FUN_00001530(param_1,(char *)local_118);
        return;
      }
      bVar6 = (char)uVar3 + 1;
      uVar3 = (ulonglong)bVar6;
    } while (bVar6 < 10);
  }
  FUN_000019fc(param_1);
  *(undefined8 *)(param_1 + 0x18) = 0x8000000000000002;
  FUN_00001530(param_1,s_invalid_parameter__supported_val_0000af08);
  puVar7 = &DAT_00009d88;
  do {
    FUN_00008b40(local_118,0x100,(byte *)s__Set__d__>__s_0000ade0,(ulonglong)*puVar7);
    FUN_00001530(param_1,(char *)local_118);
    puVar7 = puVar7 + 3;
    lVar5 = lVar5 + -1;
  } while (lVar5 != 0);
  (**(code **)(DAT_0000d7a0 + 0x58))(pbVar1);
  return;
}


// ==== FUN_00007e68 @ 00007e68

longlong FUN_00007e68(char param_1)

{
  int iVar1;
  
  if ((ushort)((short)param_1 - 0x30U) < 10) {
    iVar1 = param_1 + -0x30;
  }
  else {
    if ((byte)(param_1 + 0x9fU) < 0x1a) {
      param_1 = param_1 + -0x20;
    }
    iVar1 = param_1 + -0x37;
  }
  return (longlong)iVar1;
}


// ==== FUN_00007e98 @ 00007e98

longlong FUN_00007e98(char *param_1,char *param_2,ulonglong param_3)

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


// ==== FUN_00007ecc @ 00007ecc

void FUN_00007ecc(void)

{
  return;
}


// ==== FUN_00007ed0 @ 00007ed0

ulonglong FUN_00007ed0(char *param_1)

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


// ==== FUN_00007ef4 @ 00007ef4

undefined8 FUN_00007ef4(char *param_1,undefined8 param_2,ulonglong *param_3)

{
  char cVar1;
  ulonglong uVar2;
  
  if (((param_1 != (char *)0x0) && (param_3 != (ulonglong *)0x0)) &&
     (uVar2 = FUN_00007ed0(param_1), uVar2 < 0xf4241)) {
    for (; (*param_1 == ' ' || (*param_1 == '\t')); param_1 = param_1 + 1) {
    }
    for (; *param_1 == '0'; param_1 = param_1 + 1) {
    }
    *param_3 = 0;
    while( true ) {
      if (9 < (byte)(*param_1 - 0x30U)) {
        return 0;
      }
      cVar1 = *param_1;
      if ((ulonglong)~(longlong)(cVar1 + -0x30) / 10 < *param_3) break;
      param_1 = param_1 + 1;
      *param_3 = (longlong)(cVar1 + -0x30) + *param_3 * 10;
    }
    *param_3 = 0xffffffffffffffff;
    return 0x8000000000000003;
  }
  return 0x8000000000000002;
}


// ==== FUN_00007f98 @ 00007f98

undefined8 FUN_00007f98(char *param_1,undefined8 param_2,ulonglong *param_3)

{
  char cVar1;
  ulonglong uVar2;
  longlong lVar3;
  char cVar4;
  
  if (((param_1 != (char *)0x0) && (param_3 != (ulonglong *)0x0)) &&
     (uVar2 = FUN_00007ed0(param_1), uVar2 < 0xf4241)) {
    for (; (*param_1 == ' ' || (*param_1 == '\t')); param_1 = param_1 + 1) {
    }
    cVar4 = '0';
    for (; *param_1 == '0'; param_1 = param_1 + 1) {
    }
    cVar1 = *param_1;
    if ((byte)(*param_1 + 0x9fU) < 0x1a) {
      cVar1 = cVar1 + -0x20;
    }
    if (cVar1 == 'X') {
      if (param_1[-1] != '0') {
        *param_3 = 0;
        return 0;
      }
      param_1 = param_1 + 1;
    }
    *param_3 = 0;
    uVar2 = 0xffffffffffffffff;
    for (; (((byte)(*param_1 - cVar4) < 10 || ((byte)(*param_1 + 0xbfU) < 6)) ||
           ((byte)(*param_1 + 0x9fU) < 6)); param_1 = param_1 + 1) {
      lVar3 = FUN_00007e68(*param_1);
      if (uVar2 - lVar3 >> 4 < *param_3) {
        *param_3 = uVar2;
        return 0x8000000000000003;
      }
      *param_3 = *param_3 * 0x10 + lVar3;
    }
    return 0;
  }
  return 0x8000000000000002;
}


// ==== FUN_00008068 @ 00008068

undefined8 FUN_00008068(char param_1,undefined1 param_2)

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
      FUN_00008d58(0xf);
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


// ==== FUN_000080e0 @ 000080e0

undefined8 FUN_000080e0(char param_1)

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
      FUN_00008d58(5000);
      bVar2 = in(uVar1);
      uVar5 = uVar5 + 1;
    } while ((bVar2 & 1) != 0);
    if (0x1ffff < uVar5) {
      return 0x8000000000000007;
    }
  }
  return 0;
}


// ==== FUN_00008168 @ 00008168

undefined8 FUN_00008168(char param_1)

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
      FUN_00008d58(0xf);
      bVar2 = in(uVar1);
      uVar3 = uVar3 + 1;
    } while ((bVar2 & 2) != 0);
    if (0x1ffff < uVar3) {
      return 0x8000000000000007;
    }
  }
  return 0;
}


// ==== FUN_000081cc @ 000081cc

longlong FUN_000081cc(char param_1,undefined1 param_2,undefined1 param_3)

{
  byte bVar1;
  byte bVar2;
  longlong lVar3;
  ulonglong uVar4;
  undefined2 uVar5;
  
  lVar3 = FUN_00008168(param_1);
  uVar4 = 0;
  if (lVar3 < 0) {
    return lVar3;
  }
  FUN_000080e0(param_1);
  FUN_00008068(param_1,param_2);
  FUN_00008168(param_1);
  uVar5 = 0x60;
  bVar1 = 100;
  if (param_1 != '`') {
    bVar1 = 0x66;
  }
  bVar2 = in((ushort)bVar1);
  if ((bVar2 & 2) != 0) {
    do {
      if (0x1ffff < uVar4) goto LAB_0000826e;
      FUN_00008d58(0xf);
      bVar2 = in((ushort)bVar1);
      uVar4 = uVar4 + 1;
    } while ((bVar2 & 2) != 0);
    if (0x1ffff < uVar4) goto LAB_0000826e;
  }
  if (param_1 != '`') {
    uVar5 = 0x62;
  }
  out(uVar5,param_3);
LAB_0000826e:
  FUN_000080e0(param_1);
  return lVar3;
}


// ==== FUN_00008294 @ 00008294

longlong FUN_00008294(undefined8 param_1,undefined8 param_2,undefined1 param_3,undefined1 param_4)

{
  longlong lVar1;
  longlong lVar2;
  
  lVar1 = FUN_000081cc('b',0xa3,7);
  if (((-1 < lVar1) && (lVar1 = FUN_000081cc('b',0xa2,param_3), -1 < lVar1)) &&
     (lVar2 = FUN_000081cc('b',0xa5,param_4), lVar1 = 0, lVar2 < 0)) {
    lVar1 = lVar2;
  }
  return lVar1;
}


// ==== FUN_000082f4 @ 000082f4

longlong FUN_000082f4(undefined8 param_1,undefined8 param_2,undefined1 param_3,undefined1 *param_4)

{
  byte bVar1;
  undefined1 uVar2;
  longlong lVar3;
  ulonglong uVar4;
  
  uVar4 = 0;
  lVar3 = FUN_000081cc('b',0xa3,7);
  if (((-1 < lVar3) && (lVar3 = FUN_000081cc('b',0xa2,param_3), -1 < lVar3)) &&
     (lVar3 = FUN_00008068('b',0xa4), -1 < lVar3)) {
    bVar1 = in(0x66);
    if ((bVar1 & 1) == 0) {
      do {
        if (0x1ffff < uVar4) {
          return -0x7ffffffffffffff9;
        }
        FUN_00008d58(0xf);
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


// ==== FUN_00008390 @ 00008390

undefined8 FUN_00008390(void)

{
  undefined8 uVar1;
  
  uVar1 = 0;
  if (DAT_0000d7a8 == '\0') {
    if (DAT_0000d7c8 == 0) {
      if (DAT_0000d7b8 != '\0') {
        return 0x8000000000000003;
      }
      uVar1 = (**(code **)(DAT_0000d798 + 0x140))(&DAT_00009df8,0,&DAT_0000d7c8);
    }
  }
  else if (DAT_0000d7b0 == 0) {
    if ((DAT_0000d7b8 == '\0') && (DAT_0000d7a0 != 0)) {
                    /* WARNING: Could not recover jumptable at 0x000083cf. Too many branches */
                    /* WARNING: Treating indirect jump as call */
      uVar1 = (**(code **)(DAT_0000d7a0 + 0xd0))(&DAT_00009e08,0,&DAT_0000d7b0);
      return uVar1;
    }
    return 0x8000000000000003;
  }
  return uVar1;
}


// ==== FUN_00008418 @ 00008418

longlong FUN_00008418(void)

{
  longlong lVar1;
  ulonglong uVar2;
  
  if (DAT_0000d7a8 == '\0') {
    if (DAT_0000d7e0 == 0) {
      if (DAT_0000d7b8 == '\x01') {
        return -0x7ffffffffffffffd;
      }
      uVar2 = (**(code **)(DAT_0000d798 + 0x18))(0x1f);
      (**(code **)(DAT_0000d798 + 0x20))(uVar2);
      if (0x10 < uVar2) {
        return -0x7ffffffffffffffd;
      }
      lVar1 = (**(code **)(DAT_0000d798 + 0x140))(&DAT_00009010,0,&DAT_0000d7e0);
      if (lVar1 < 0) {
        DAT_0000d7e0 = 0;
        return lVar1;
      }
      return lVar1;
    }
  }
  else if (DAT_0000d7c0 == 0) {
    if (DAT_0000d7a0 == 0) {
      return -0x7ffffffffffffffd;
    }
    lVar1 = (**(code **)(DAT_0000d7a0 + 0xd0))(&DAT_00009030,0,&DAT_0000d7c0);
    if (lVar1 < 0) {
      DAT_0000d7c0 = 0;
      return lVar1;
    }
    return lVar1;
  }
  return 0;
}


// ==== FUN_000084fc @ 000084fc

longlong FUN_000084fc(void)

{
  longlong lVar1;
  longlong lVar2;
  longlong *plVar3;
  
  if (DAT_0000d7a0 != 0) {
    plVar3 = *(longlong **)(DAT_0000d7a0 + 0xa0);
    for (lVar2 = *(longlong *)(DAT_0000d7a0 + 0x98); lVar2 != 0; lVar2 = lVar2 + -1) {
      lVar1 = FUN_00008b60(plVar3);
      if (lVar1 == 0) {
        return plVar3[2];
      }
      plVar3 = plVar3 + 3;
    }
  }
  return 0;
}


// ==== FUN_00008548 @ 00008548

char * FUN_00008548(ulonglong param_1,char *param_2,int param_3,char param_4)

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


// ==== FUN_000085bc @ 000085bc

int FUN_000085bc(byte *param_1,undefined8 *param_2)

{
  byte bVar1;
  bool bVar2;
  char cVar3;
  byte *pbVar4;
  uint uVar5;
  char cVar6;
  
  bVar2 = false;
  cVar6 = '\x01';
  for (; (*param_1 == 0x20 || (*param_1 == 9)); param_1 = param_1 + 1) {
  }
  if (*param_1 == 0) {
    *param_2 = param_1;
    return 0;
  }
  if (*param_1 == 0x2d) {
    cVar6 = -1;
    param_1 = param_1 + 1;
  }
  pbVar4 = param_1 + 1;
  uVar5 = 0;
  if (*param_1 != 0x2b) {
    pbVar4 = param_1;
    uVar5 = 0;
  }
  do {
    bVar1 = *pbVar4;
    if ((byte)(bVar1 - 0x30) < 10) {
      cVar3 = bVar1 - 0x30;
    }
    else {
      if (0x19 < (byte)((bVar1 & 0xdf) + 0xbf)) {
LAB_00008662:
        *param_2 = pbVar4;
        if ((bVar2) && (uVar5 = 0x7fffffff, cVar6 == -1)) {
          uVar5 = 0x80000000;
        }
        return (int)cVar6 * uVar5;
      }
      cVar3 = (bVar1 & 0xdf) - 0x37;
    }
    if (9 < cVar3) goto LAB_00008662;
    uVar5 = (int)cVar3 + uVar5 * 10;
    if (cVar6 == '\x01') {
      if (0x7fffffff < uVar5) {
        bVar2 = true;
      }
    }
    else if (0x80000000 < uVar5) {
      bVar2 = true;
    }
    pbVar4 = pbVar4 + 1;
  } while( true );
}


// ==== FUN_00008690 @ 00008690

char * FUN_00008690(ulonglong param_1)

{
  char *pcVar1;
  char *pcVar2;
  ulonglong uVar3;
  
  if (param_1 == 0) {
    return s_EFI_SUCCESS_0000d700;
  }
  if ((longlong)param_1 < 0) {
    uVar3 = param_1 & 0x1fffffffffffffff;
    if ((param_1 & 0xa000000000000000) == 0xa000000000000000) {
      if (2 < uVar3) {
        return (char *)0x0;
      }
      pcVar1 = (char *)(uVar3 * 0x19);
      pcVar2 = s_EFI_INTERRUPT_PENDING_00009f00;
      goto LAB_00008753;
    }
    if ((param_1 & 0xc000000000000000) == 0xc000000000000000) {
      if (2 < uVar3) {
        return (char *)0x0;
      }
      pcVar1 = s_EFI_NOT_AVAILABLE_YET_00009f32 + uVar3 * 0x19 + 0x15;
    }
    else {
      if (0x1e < uVar3) {
        return (char *)0x0;
      }
      pcVar1 = s_EFI_DBE_BOF_00009f79 + uVar3 * 0x19 + 0xe;
    }
  }
  else {
    if ((param_1 & 0x2000000000000000) != 0) {
      if (1 < param_1) {
        return (char *)0x0;
      }
      pcVar1 = (char *)(param_1 * 0x23);
      pcVar2 = s_EFI_WARN_INTERRUPT_SOURCE_PENDIN_00009eb0;
      goto LAB_00008753;
    }
    if (4 < param_1) {
      return (char *)0x0;
    }
    pcVar1 = (char *)(param_1 * 0x1a + 0x9e26);
  }
  pcVar2 = (char *)0x0;
LAB_00008753:
  return pcVar1 + (longlong)pcVar2;
}


// ==== FUN_00008758 @ 00008758

longlong FUN_00008758(byte *param_1,longlong param_2,byte *param_3,longlong param_4)

{
  byte bVar1;
  uint uVar2;
  char *pcVar3;
  byte *pbVar4;
  ulonglong uVar5;
  byte *pbVar6;
  byte bVar7;
  int iVar8;
  byte *pbVar9;
  byte *pbVar10;
  longlong lVar11;
  uint *local_res18;
  byte *local_68;
  byte *local_60;
  byte local_58 [32];
  
  if ((param_1 == (byte *)0x0) || (param_3 == (byte *)0x0)) {
    lVar11 = -1;
  }
  else {
    pbVar10 = param_1;
    if (param_2 != 1) {
      local_res18 = (uint *)(param_4 + -8);
      do {
        bVar7 = *param_3;
        if (bVar7 == 0) break;
        pbVar9 = param_3 + 1;
        if (bVar7 == 0x25) {
          if (*pbVar9 == 0x25) {
            pbVar9 = param_3 + 2;
            *pbVar10 = 0x25;
            goto LAB_000087c4;
          }
          bVar7 = 0x20;
          if (*pbVar9 == 0x30) {
            bVar7 = 0x30;
            pbVar9 = param_3 + 2;
          }
          if (*pbVar9 == 0x2a) {
            local_res18 = local_res18 + 2;
            uVar2 = *local_res18;
            pbVar9 = pbVar9 + 1;
          }
          else {
            uVar2 = FUN_000085bc(pbVar9,&local_68);
            pbVar9 = local_68;
          }
          if ((*pbVar9 == 0x73) || (*pbVar9 == 0x61)) {
            for (pbVar6 = *(byte **)(local_res18 + 2); *pbVar6 != 0; pbVar6 = pbVar6 + 1) {
              param_2 = param_2 + -1;
              if (param_2 == 0) goto LAB_00008b08;
              *pbVar10 = *pbVar6;
              pbVar10 = pbVar10 + 1;
            }
LAB_00008af7:
            local_res18 = local_res18 + 2;
            pbVar9 = pbVar9 + 1;
          }
          else {
            if (*pbVar9 == 0x53) {
              for (pbVar6 = *(byte **)(local_res18 + 2); *(short *)pbVar6 != 0; pbVar6 = pbVar6 + 2)
              {
                param_2 = param_2 + -1;
                if (param_2 == 0) goto LAB_00008b08;
                *pbVar10 = *pbVar6;
                pbVar10 = pbVar10 + 1;
              }
              goto LAB_00008af7;
            }
            if (*pbVar9 == 99) {
              *pbVar10 = (byte)local_res18[2];
              pbVar10 = pbVar10 + 1;
              goto LAB_00008af7;
            }
            if ((*pbVar9 & 0xdf) == 0x47) {
              local_60 = pbVar10;
              lVar11 = FUN_00008b40(pbVar10,param_2,
                                    (byte *)s__08x__04x__04x__02x_02x__02x_02x_0000d710,
                                    (ulonglong)**(uint **)(local_res18 + 2));
              pbVar10 = pbVar10 + lVar11;
              pbVar6 = local_60;
              if (*pbVar9 == 0x47) {
                for (; *pbVar6 != 0; pbVar6 = pbVar6 + 1) {
                  if ((byte)(*pbVar6 + 0x9f) < 0x1a) {
                    *pbVar6 = *pbVar6 - 0x20;
                  }
                }
              }
              param_2 = param_2 - lVar11;
              goto LAB_00008af7;
            }
            if (*pbVar9 == 0x72) {
              pcVar3 = FUN_00008690(*(ulonglong *)(local_res18 + 2));
              if (pcVar3 == (char *)0x0) {
                lVar11 = FUN_00008b40(pbVar10,param_2,(byte *)s__s__X__0000d744,
                                      s_Status_Code_00009f50);
              }
              else {
                lVar11 = FUN_00008b40(pbVar10,param_2,&DAT_0000d74c,pcVar3);
              }
              pbVar10 = pbVar10 + lVar11;
              param_2 = param_2 - lVar11;
              goto LAB_00008af7;
            }
            bVar1 = *pbVar9;
            if (bVar1 == 0x6c) {
              pbVar9 = pbVar9 + 1;
            }
            if ((*pbVar9 == 100) || (*pbVar9 == 0x69)) {
              iVar8 = 10;
LAB_000089ef:
              pbVar6 = local_58;
              if (*pbVar9 != 0x70 && bVar1 != 0x6c) {
                pbVar4 = (byte *)FUN_00008548((longlong)(int)*(ulonglong *)(local_res18 + 2),
                                              (char *)local_58,iVar8,'\0');
                if (local_58 < pbVar4) {
                  do {
                    bVar1 = *pbVar6;
                    *pbVar6 = *pbVar4;
                    pbVar6 = pbVar6 + 1;
                    *pbVar4 = bVar1;
                    pbVar4 = pbVar4 + -1;
                  } while (pbVar6 < pbVar4);
                }
              }
              else {
                pbVar4 = (byte *)FUN_00008548(*(ulonglong *)(local_res18 + 2),(char *)local_58,iVar8
                                              ,'\x01');
                if (local_58 < pbVar4) {
                  do {
                    bVar1 = *pbVar6;
                    *pbVar6 = *pbVar4;
                    pbVar6 = pbVar6 + 1;
                    *pbVar4 = bVar1;
                    pbVar4 = pbVar4 + -1;
                  } while (pbVar6 < pbVar4);
                }
              }
              if ((*pbVar9 == 0x58) || (*pbVar9 == 0x70)) {
                pbVar6 = local_58;
                bVar1 = local_58[0];
                while (bVar1 != 0) {
                  if ((byte)(*pbVar6 + 0x9f) < 0x1a) {
                    *pbVar6 = *pbVar6 - 0x20;
                  }
                  pbVar6 = pbVar6 + 1;
                  bVar1 = *pbVar6;
                }
              }
              uVar5 = 0;
              bVar1 = local_58[0];
              while (bVar1 != 0) {
                bVar1 = local_58[uVar5 + 1];
                uVar5 = uVar5 + 1;
              }
              while (uVar5 < uVar2) {
                uVar5 = uVar5 + 1;
                param_2 = param_2 + -1;
                if (param_2 == 0) goto LAB_00008b08;
                *pbVar10 = bVar7;
                pbVar10 = pbVar10 + 1;
              }
              pbVar6 = local_58;
              bVar7 = local_58[0];
              while (bVar7 != 0) {
                param_2 = param_2 + -1;
                if (param_2 == 0) {
LAB_00008b08:
                  *pbVar10 = 0;
                  return (longlong)pbVar10 - (longlong)param_1;
                }
                bVar7 = *pbVar6;
                pbVar6 = pbVar6 + 1;
                *pbVar10 = bVar7;
                pbVar10 = pbVar10 + 1;
                bVar7 = *pbVar6;
              }
              goto LAB_00008af7;
            }
            if (((*pbVar9 & 0xdf) == 0x58) || (*pbVar9 == 0x70)) {
              iVar8 = 0x10;
              goto LAB_000089ef;
            }
          }
        }
        else {
          *pbVar10 = bVar7;
LAB_000087c4:
          pbVar10 = pbVar10 + 1;
          param_2 = param_2 + -1;
        }
        param_3 = pbVar9;
      } while (param_2 != 1);
    }
    *pbVar10 = 0;
    lVar11 = (longlong)pbVar10 - (longlong)param_1;
  }
  return lVar11;
}


// ==== FUN_00008b40 @ 00008b40

void FUN_00008b40(byte *param_1,longlong param_2,byte *param_3,undefined8 param_4)

{
  undefined8 local_res20;
  
  local_res20 = param_4;
  FUN_00008758(param_1,param_2,param_3,(longlong)&local_res20);
  return;
}


// ==== FUN_00008b60 @ 00008b60

longlong FUN_00008b60(longlong *param_1)

{
  longlong *plVar1;
  longlong *plVar2;
  longlong lVar3;
  
  plVar2 = (longlong *)&DAT_00009e30;
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


// ==== FUN_00008bdc @ 00008bdc

ulonglong FUN_00008bdc(ulonglong param_1)

{
  ulonglong in_RAX;
  ulonglong uVar1;
  ulonglong *puVar2;
  
  uVar1 = 0;
  if (DAT_0000d928 != 0) {
    puVar2 = (ulonglong *)(DAT_0000d930 + 8);
    in_RAX = DAT_0000d930;
    do {
      if ((*puVar2 <= param_1) && (in_RAX = puVar2[1], param_1 < *puVar2 + in_RAX)) {
        return CONCAT71((int7)(in_RAX >> 8),1);
      }
      uVar1 = uVar1 + 1;
      puVar2 = puVar2 + 4;
    } while (uVar1 < DAT_0000d928);
  }
  return in_RAX & 0xffffffffffffff00;
}


// ==== FUN_00008c20 @ 00008c20

undefined8 FUN_00008c20(undefined8 param_1,undefined8 param_2)

{
  longlong lVar1;
  undefined8 local_res18 [2];
  
  lVar1 = (**(code **)(DAT_0000d790 + 0x50))(6,param_2,local_res18);
  if (lVar1 < 0) {
    local_res18[0] = 0;
  }
  return local_res18[0];
}


// ==== FUN_00008c50 @ 00008c50

void FUN_00008c50(void)

{
  ulonglong uVar1;
  
  uVar1 = FUN_00008bdc(DAT_0000d930);
  if ((char)uVar1 != '\0') {
                    /* WARNING: Could not recover jumptable at 0x00008c76. Too many branches */
                    /* WARNING: Treating indirect jump as call */
    (**(code **)(DAT_0000d790 + 0x58))();
    return;
  }
                    /* WARNING: Could not recover jumptable at 0x00008c85. Too many branches */
                    /* WARNING: Treating indirect jump as call */
  (**(code **)(DAT_0000d788 + 0x48))(DAT_0000d930);
  return;
}


// ==== FUN_00008c8c @ 00008c8c

longlong FUN_00008c8c(void)

{
  ulonglong uVar1;
  longlong *plVar2;
  
  uVar1 = 0;
  if (DAT_0000d7f0 == 0) {
    DAT_0000d7f0 = 0;
    if (*(ulonglong *)(DAT_0000d780 + 0x68) != 0) {
      plVar2 = *(longlong **)(DAT_0000d780 + 0x70);
      do {
        if ((DAT_00009070 == *plVar2) && (DAT_00009078 == plVar2[1])) {
          DAT_0000d7f0 = (*(longlong **)(DAT_0000d780 + 0x70))[uVar1 * 3 + 2];
          return DAT_0000d7f0;
        }
        uVar1 = uVar1 + 1;
        plVar2 = plVar2 + 3;
      } while (uVar1 < *(ulonglong *)(DAT_0000d780 + 0x68));
    }
  }
  return DAT_0000d7f0;
}


// ==== FUN_00008cf8 @ 00008cf8

void FUN_00008cf8(uint param_1)

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
      FUN_00001260();
    }
    bVar6 = uVar3 != 0;
    uVar3 = uVar3 - 1;
  } while (bVar6);
  return;
}


// ==== FUN_00008d58 @ 00008d58

longlong FUN_00008d58(longlong param_1)

{
  FUN_00008cf8((uint)((ulonglong)(param_1 * 0x369e99) / 1000000));
  return param_1;
}


// ==== FUN_00008e40 @ 00008e40

undefined8 * FUN_00008e40(undefined8 *param_1,undefined8 *param_2,ulonglong param_3)

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


