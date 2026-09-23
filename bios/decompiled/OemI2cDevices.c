// OemI2cDevices.efi: Ghidra x86:LE:64:default decompile, unedited
// ==== FUN_000002c0 @ 000002c0

void FUN_000002c0(void)

{
  return;
}


// ==== FUN_000002d0 @ 000002d0

ulonglong FUN_000002d0(void)

{
  ulonglong uVar1;
  undefined8 in_RAX;
  
  uVar1 = rdtsc();
  return CONCAT44((int)((ulonglong)in_RAX >> 0x20),(int)uVar1) | uVar1 & 0xffffffff00000000;
}


// ==== FUN_000002e0 @ 000002e0

void FUN_000002e0(void)

{
  return;
}


// ==== FUN_000002f0 @ 000002f0

void FUN_000002f0(void)

{
  return;
}


// ==== FUN_00000300 @ 00000300

ulonglong FUN_00000300(void)

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


// ==== entry @ 00000310

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void entry(undefined8 param_1,longlong param_2)

{
  undefined1 local_res18 [16];
  
  FUN_00000384(param_1,param_2);
  if (DAT_00000e70 == 0) {
    DAT_00000e60 = *(longlong *)(param_2 + 0x60);
    _DAT_00000e68 = *(undefined8 *)(param_2 + 0x58);
    DAT_00000e70 = param_2;
  }
  (**(code **)(DAT_00000e60 + 0x170))(0x200,8,0x4ac,0,0xda0,local_res18);
  return;
}


// ==== FUN_00000384 @ 00000384

void FUN_00000384(undefined8 param_1,longlong param_2)

{
  uint uVar1;
  int iVar2;
  short *psVar3;
  ulonglong uVar4;
  longlong lVar5;
  
  DAT_00000e58 = *(longlong *)(param_2 + 0x60);
  DAT_00000e50 = param_2;
  FUN_00000b34();
  psVar3 = (short *)FUN_00000b34();
  do {
    if (*psVar3 == -1) {
      psVar3 = (short *)0x0;
LAB_000003d8:
      if (psVar3 == (short *)0x0) {
        uVar4 = FUN_00000300();
        FUN_000002f0();
        uVar1 = in(0x1808);
        FUN_000002d0();
        while (iVar2 = in(0x1808), (((uVar1 & 0xffffff) + 0x16b) - iVar2 >> 0x17 & 1) == 0) {
          FUN_000002c0();
        }
        FUN_000002d0();
        if ((uVar4 >> 9 & 1) == 0) {
          FUN_000002f0();
        }
        else {
          FUN_000002e0();
        }
LAB_00000441:
        if ((DAT_00000e80 != (undefined8 *)0x0) ||
           (lVar5 = (**(code **)(DAT_00000e58 + 0x140))(0xdd0,0,0xe80), -1 < lVar5)) {
          (*(code *)*DAT_00000e80)(DAT_00000e80,0xe88);
        }
                    /* WARNING: Could not recover jumptable at 0x000004a3. Too many branches */
                    /* WARNING: Treating indirect jump as call */
        (**(code **)(DAT_00000e58 + 0x140))(0xdb0,0,0xe90);
        return;
      }
      if ((DAT_00000df0 == *(longlong *)(psVar3 + 4)) && (DAT_00000df8 == *(longlong *)(psVar3 + 8))
         ) goto LAB_00000441;
    }
    else if (*psVar3 == 4) goto LAB_000003d8;
    psVar3 = (short *)((longlong)psVar3 + (ulonglong)(ushort)psVar3[1]);
  } while( true );
}


// ==== FUN_000005cc @ 000005cc

undefined8 FUN_000005cc(undefined8 param_1,undefined1 param_2)

{
  byte bVar1;
  ulonglong uVar2;
  
  uVar2 = 0;
  bVar1 = in(0x66);
  if ((bVar1 & 2) != 0) {
    do {
      if (0x1ffff < uVar2) {
        return 0x8000000000000007;
      }
      FUN_00000c00(0xf);
      bVar1 = in(0x66);
      uVar2 = uVar2 + 1;
    } while ((bVar1 & 2) != 0);
    if (0x1ffff < uVar2) {
      return 0x8000000000000007;
    }
  }
  out(0x66,param_2);
  return 0;
}


// ==== FUN_00000630 @ 00000630

undefined8 FUN_00000630(void)

{
  byte bVar1;
  undefined1 uVar2;
  ulonglong uVar3;
  
  uVar3 = 0;
  bVar1 = in(0x66);
  if ((bVar1 & 1) != 0) {
    do {
      if (0x1ffff < uVar3) {
        return 0x8000000000000007;
      }
      uVar2 = in(0x62);
      out(0x80,uVar2);
      FUN_00000c00(5000);
      bVar1 = in(0x66);
      uVar3 = uVar3 + 1;
    } while ((bVar1 & 1) != 0);
    if (0x1ffff < uVar3) {
      return 0x8000000000000007;
    }
  }
  return 0;
}


// ==== FUN_0000068c @ 0000068c

undefined8 FUN_0000068c(void)

{
  byte bVar1;
  ulonglong uVar2;
  
  uVar2 = 0;
  bVar1 = in(0x66);
  if ((bVar1 & 2) != 0) {
    do {
      if (0x1ffff < uVar2) {
        return 0x8000000000000007;
      }
      FUN_00000c00(0xf);
      bVar1 = in(0x66);
      uVar2 = uVar2 + 1;
    } while ((bVar1 & 2) != 0);
    if (0x1ffff < uVar2) {
      return 0x8000000000000007;
    }
  }
  return 0;
}


// ==== FUN_000006dc @ 000006dc

longlong FUN_000006dc(undefined8 param_1,undefined1 param_2,undefined1 param_3)

{
  byte bVar1;
  longlong lVar2;
  ulonglong uVar3;
  
  lVar2 = FUN_0000068c();
  uVar3 = 0;
  if (lVar2 < 0) {
    return lVar2;
  }
  FUN_00000630();
  FUN_000005cc(param_1,param_2);
  FUN_0000068c();
  bVar1 = in(0x66);
  if ((bVar1 & 2) != 0) {
    do {
      if (0x1ffff < uVar3) goto LAB_0000074e;
      FUN_00000c00(0xf);
      bVar1 = in(0x66);
      uVar3 = uVar3 + 1;
    } while ((bVar1 & 2) != 0);
    if (0x1ffff < uVar3) goto LAB_0000074e;
  }
  out(0x62,param_3);
LAB_0000074e:
  FUN_00000630();
  return lVar2;
}


// ==== FUN_0000076c @ 0000076c

undefined8 FUN_0000076c(int *param_1,char *param_2,char *param_3,int param_4,longlong *param_5)

{
  byte bVar1;
  longlong lVar2;
  char *pcVar3;
  ulonglong uVar4;
  char *pcVar5;
  char cVar6;
  uint uVar7;
  int *piVar8;
  char cVar9;
  ulonglong uVar10;
  char *pcVar11;
  int *piVar12;
  longlong lVar13;
  int local_res8 [2];
  
  do {
    uVar10 = 0;
    cVar9 = *param_3;
    while (cVar9 != '\0') {
      uVar10 = uVar10 + 1;
      cVar9 = param_3[uVar10];
    }
    local_res8[0] = 0x5f5f5f5f;
    FUN_00000cf0((undefined8 *)local_res8,(undefined8 *)param_3,uVar10);
    uVar7 = 0;
    if (param_2 != (char *)0x0) {
      pcVar11 = (char *)0x0;
      do {
        piVar8 = (int *)(pcVar11 + (longlong)param_1);
        if (*piVar8 == local_res8[0]) goto LAB_000007d2;
        uVar7 = uVar7 + 1;
        pcVar11 = (char *)(ulonglong)uVar7;
      } while (pcVar11 < param_2);
    }
    piVar8 = (int *)0x0;
LAB_000007d2:
    if (piVar8 == (int *)0x0) {
      return 0x800000000000000e;
    }
    if (param_4 == 1) {
      cVar9 = '\x10';
LAB_00000855:
      lVar13 = 0;
LAB_00000858:
      cVar6 = '\0';
    }
    else {
      if (param_4 == 3) {
        cVar9 = '\b';
        goto LAB_00000855;
      }
      if (param_4 != 4) {
        if (param_4 == 5) {
          lVar13 = 0;
          cVar6 = '[';
          cVar9 = -0x7b;
          goto LAB_0000085a;
        }
        if (param_4 == 6) {
          lVar13 = 0;
          cVar6 = '[';
          cVar9 = -0x7e;
          goto LAB_0000085a;
        }
        if (param_4 != 7) {
          if (param_4 == 8) {
            lVar13 = 3;
            cVar6 = '[';
            cVar9 = -0x7c;
          }
          else {
            if (param_4 != 9) {
              return 0x800000000000000e;
            }
            lVar13 = 0;
            cVar6 = '[';
            cVar9 = -0x80;
          }
          goto LAB_0000085a;
        }
        lVar13 = 1;
        cVar9 = '\x14';
        goto LAB_00000858;
      }
      lVar13 = 6;
      cVar6 = '[';
      cVar9 = -0x7d;
    }
LAB_0000085a:
    piVar12 = piVar8;
    if ((*(char *)((longlong)piVar8 + -1) + 0xa4U & 0xfd) == 0) {
      piVar12 = (int *)((longlong)piVar8 + -1);
    }
    if (cVar9 == '\b') {
      if (cVar6 == '\0') {
        pcVar11 = (char *)((longlong)piVar12 + -1);
        cVar6 = *pcVar11;
LAB_0000087c:
        if (cVar6 == cVar9) {
          *(undefined8 *)((longlong)param_5 + 0x1c) = 0;
          *param_5 = (longlong)pcVar11;
LAB_0000094f:
          param_5[1] = (longlong)piVar12;
          *(int *)(param_5 + 3) = param_4;
          param_5[2] = (longlong)((longlong)piVar8 + lVar13 + 4);
          return 0;
        }
      }
      else {
LAB_000008a8:
        lVar2 = 2;
        pcVar11 = (char *)((longlong)piVar12 + -2);
        do {
          if (cVar6 == '\0') {
            pcVar5 = (char *)0x0;
          }
          else {
            pcVar5 = pcVar11 + -1;
          }
          if (((pcVar5 == (char *)0x0) || (*pcVar5 == cVar6)) && (*pcVar11 == cVar9)) {
            pcVar3 = pcVar11;
            if (pcVar5 != (char *)0x0) {
              pcVar3 = pcVar5;
            }
            *param_5 = (longlong)pcVar3;
            bVar1 = pcVar11[1];
            if ((bVar1 & 0xc0) == 0) {
              uVar10 = (ulonglong)(bVar1 & 0x3f);
            }
            else {
              uVar10 = (ulonglong)(bVar1 & 0xf);
              bVar1 = bVar1 >> 6;
              if (bVar1 == 1) {
                uVar7 = (uint)(byte)pcVar11[2];
LAB_00000943:
                uVar4 = (ulonglong)(int)(uVar7 << 4);
              }
              else {
                if (bVar1 == 2) {
                  uVar7 = (uint)*(ushort *)(pcVar11 + 2);
                  goto LAB_00000943;
                }
                if (bVar1 != 3) goto LAB_0000094b;
                uVar4 = (ulonglong)((*(uint *)(pcVar11 + 2) & 0xffffff) << 4);
              }
              uVar10 = uVar10 | uVar4;
            }
LAB_0000094b:
            *(ulonglong *)((longlong)param_5 + 0x1c) = uVar10;
            goto LAB_0000094f;
          }
          lVar2 = lVar2 + 1;
          pcVar11 = pcVar11 + -1;
        } while (lVar2 < 6);
      }
    }
    else {
      if ((cVar9 != -0x80) || (cVar6 == '\0')) goto LAB_000008a8;
      pcVar11 = (char *)((longlong)piVar12 + -2);
      if (*pcVar11 == cVar6) {
        cVar6 = *(char *)((longlong)piVar12 + -1);
        goto LAB_0000087c;
      }
    }
    param_2 = param_2 + (longlong)((longlong)param_1 + (4 - (longlong)piVar8));
    param_1 = piVar8 + 1;
  } while( true );
}


// ==== FUN_00000984 @ 00000984

longlong FUN_00000984(int *param_1,char *param_2,char *param_3,ulonglong param_4)

{
  longlong lVar1;
  longlong local_38 [2];
  byte *local_28;
  
  lVar1 = FUN_0000076c(param_1,param_2,param_3,3,local_38);
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


// ==== FUN_00000b34 @ 00000b34

longlong FUN_00000b34(void)

{
  ulonglong uVar1;
  longlong *plVar2;
  
  uVar1 = 0;
  if (DAT_00000e78 == 0) {
    DAT_00000e78 = 0;
    if (*(ulonglong *)(DAT_00000e50 + 0x68) != 0) {
      plVar2 = *(longlong **)(DAT_00000e50 + 0x70);
      do {
        if ((DAT_00000dc0 == *plVar2) && (DAT_00000dc8 == plVar2[1])) {
          DAT_00000e78 = (*(longlong **)(DAT_00000e50 + 0x70))[uVar1 * 3 + 2];
          return DAT_00000e78;
        }
        uVar1 = uVar1 + 1;
        plVar2 = plVar2 + 3;
      } while (uVar1 < *(ulonglong *)(DAT_00000e50 + 0x68));
    }
  }
  return DAT_00000e78;
}


// ==== FUN_00000ba0 @ 00000ba0

void FUN_00000ba0(uint param_1)

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
      FUN_000002c0();
    }
    bVar6 = uVar3 != 0;
    uVar3 = uVar3 - 1;
  } while (bVar6);
  return;
}


// ==== FUN_00000c00 @ 00000c00

longlong FUN_00000c00(longlong param_1)

{
  FUN_00000ba0((uint)((ulonglong)(param_1 * 0x369e99) / 1000000));
  return param_1;
}


// ==== FUN_00000cf0 @ 00000cf0

undefined8 * FUN_00000cf0(undefined8 *param_1,undefined8 *param_2,ulonglong param_3)

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


