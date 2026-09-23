// DxeOverClock.efi: Ghidra x86:LE:64:default decompile, unedited
// ==== FUN_00000260 @ 00000260

undefined1 * FUN_00000260(undefined1 *param_1,longlong param_2,undefined1 param_3)

{
  undefined1 *puVar1;
  
  puVar1 = param_1;
  for (; param_2 != 0; param_2 = param_2 + -1) {
    *puVar1 = param_3;
    puVar1 = puVar1 + 1;
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


// ==== FUN_00000320 @ 00000320

void FUN_00000320(void)

{
  return;
}


// ==== FUN_00000330 @ 00000330

ulonglong FUN_00000330(void)

{
  ulonglong uVar1;
  undefined8 in_RAX;
  
  uVar1 = rdtsc();
  return CONCAT44((int)((ulonglong)in_RAX >> 0x20),(int)uVar1) | uVar1 & 0xffffffff00000000;
}


// ==== FUN_00000340 @ 00000340

void FUN_00000340(void)

{
  return;
}


// ==== FUN_00000350 @ 00000350

void FUN_00000350(void)

{
  return;
}


// ==== FUN_00000360 @ 00000360

ulonglong FUN_00000360(void)

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


// ==== entry @ 00000364

void entry(ulonglong param_1,longlong param_2)

{
  uint uVar1;
  int iVar2;
  longlong lVar3;
  ulonglong uVar4;
  uint uVar5;
  
  DAT_00002690 = *(undefined8 *)(param_2 + 0x60);
  DAT_00002698 = *(undefined8 *)(param_2 + 0x58);
  DAT_00002688 = param_2;
  FUN_00001e28();
  lVar3 = FUN_00001e94();
  if (lVar3 == 0) {
    uVar4 = FUN_00000360();
    FUN_00000350();
    uVar1 = in(0x1808);
    FUN_00000330();
    while( true ) {
      iVar2 = in(0x1808);
      uVar5 = ((uVar1 & 0xffffff) + 0x16b) - iVar2;
      param_1 = (ulonglong)uVar5;
      if ((uVar5 >> 0x17 & 1) != 0) break;
      FUN_00000320();
    }
    FUN_00000330();
    if ((uVar4 >> 9 & 1) == 0) {
      FUN_00000350();
    }
    else {
      FUN_00000340();
    }
  }
  FUN_00000400(param_1);
  return;
}


// ==== FUN_00000400 @ 00000400

longlong FUN_00000400(undefined8 param_1)

{
  longlong lVar1;
  undefined1 uVar2;
  undefined8 local_res8;
  undefined8 local_res10;
  undefined8 local_res18;
  undefined1 local_res20 [8];
  
  local_res10 = 699;
  local_res8 = param_1;
  lVar1 = (**(code **)(DAT_00002698 + 0x48))
                    (u_CpuSetup_000025d0,&DAT_00002540,&DAT_00003460,&local_res10,&DAT_00002900);
  if ((-1 < lVar1) && (DAT_00002ab7 != '\0')) {
    local_res10 = 0x21d;
    lVar1 = (**(code **)(DAT_00002698 + 0x48))
                      (u_SaSetup_000025e8,&DAT_00002590,&DAT_000028e0,&local_res10,&DAT_000026c0);
    if (-1 < lVar1) {
      local_res10 = 0x7d8;
      lVar1 = (**(code **)(DAT_00002698 + 0x48))
                        (u_Setup_000025f8,&DAT_00002550,&DAT_00002bbc,&local_res10,&DAT_00002c80);
      if (-1 < lVar1) {
        local_res8 = 0x8a;
        lVar1 = (**(code **)(DAT_00002698 + 0x48))
                          (u_OcSetup_00002608,&DAT_00002560,&DAT_00002bc0,&local_res8,&DAT_00002be0)
        ;
        local_res8 = 0x8a;
        if (lVar1 < 0) {
          DAT_00002711 = 10000;
          FUN_000015d0('\x01');
          DAT_00002be0 = '\0';
          DAT_00002bc0 = 7;
          (**(code **)(DAT_00002698 + 0x58))(u_OcSetup_00002608,&DAT_00002560,7,0x8a,&DAT_00002be0);
        }
        else if (DAT_00002be0 == '\x01') {
          FUN_000015d0('\0');
          (**(code **)(DAT_00002698 + 0x58))
                    (u_CpuSetup_000025d0,&DAT_00002540,DAT_00003460,699,&DAT_00002900);
          (**(code **)(DAT_00002698 + 0x58))
                    (u_SaSetup_000025e8,&DAT_00002590,DAT_000028e0,0x21d,&DAT_000026c0);
          (**(code **)(DAT_00002698 + 0x58))
                    (u_Setup_000025f8,&DAT_00002550,DAT_00002bbc,0x7d8,&DAT_00002c80);
          DAT_00002be0 = '\0';
          (**(code **)(DAT_00002698 + 0x58))
                    (u_OcSetup_00002608,&DAT_00002560,DAT_00002bc0,local_res8,&DAT_00002be0);
          lVar1 = (**(code **)(DAT_00002690 + 0x140))(&DAT_000025a0,0,&DAT_000026a8);
          if (-1 < lVar1) {
            (*(code *)*DAT_000026a8)(8);
            (*(code *)DAT_000026a8[3])();
          }
          (**(code **)(DAT_00002698 + 0x68))(1,0,0,0);
        }
        lVar1 = (**(code **)(DAT_00002690 + 0x140))(&DAT_00002570,0,local_res20);
        if (lVar1 < 0) {
          (**(code **)(DAT_00002690 + 0x50))(0x200,8,0x81c,0,&DAT_00003458);
          (**(code **)(DAT_00002690 + 0xa8))(&DAT_00002570,DAT_00003458,&DAT_000028e8);
        }
        else {
          FUN_0000081c();
        }
        local_res18 = 0;
        lVar1 = (**(code **)(DAT_00002690 + 0x148))(&local_res18,&DAT_00002530,0,0);
        if (lVar1 < 0) {
          return lVar1;
        }
        uVar2 = 0xa0;
        (**(code **)(DAT_00002690 + 0x140))(&DAT_000025a0,0,&DAT_000026a8);
        DAT_00002680 = (*(code *)DAT_000026a8[1])();
        if ((DAT_00002680 == '\0') && (DAT_0000315f != '\x01')) {
          (**(code **)(DAT_00002698 + 0x58))
                    (u_Setup_000025f8,&DAT_00002550,DAT_00002bbc,local_res10,&DAT_00002c80);
          FUN_00000940();
        }
        else {
          FUN_00001118();
          FUN_00002290(uVar2);
        }
        if (DAT_00002681 != '\0') {
          (**(code **)(DAT_00002698 + 0x68))(0,0,0,0);
        }
        FUN_000015d0('\x01');
        (**(code **)(DAT_00002698 + 0x58))
                  (u_OcSetup_00002608,&DAT_00002560,DAT_00002bc0,local_res8,&DAT_00002be0);
        (*(code *)DAT_000026a8[2])();
      }
    }
  }
  return 0;
}


// ==== FUN_0000081c @ 0000081c

void FUN_0000081c(void)

{
  longlong lVar1;
  ulonglong uVar2;
  longlong local_res18 [2];
  
  lVar1 = (**(code **)(DAT_00002690 + 0x140))(&DAT_00002570,0,local_res18);
  if (-1 < lVar1) {
    uVar2 = (ulonglong)*(byte *)(local_res18[0] + 0xe3);
    DAT_000026d0 = *(undefined1 *)(local_res18[0] + 6 + uVar2 * 0x28);
    DAT_000026d1 = *(undefined1 *)(local_res18[0] + 8 + uVar2 * 0x28);
    DAT_000026d2 = *(undefined2 *)(local_res18[0] + 10 + uVar2 * 0x28);
    DAT_000026d4 = *(undefined2 *)(local_res18[0] + 0xc + uVar2 * 0x28);
    DAT_000026d6 = *(undefined1 *)(local_res18[0] + 0xe + uVar2 * 0x28);
    DAT_000026d7 = *(undefined2 *)(local_res18[0] + 0x10 + uVar2 * 0x28);
    DAT_000026d9 = *(undefined2 *)(local_res18[0] + 0x12 + uVar2 * 0x28);
    DAT_000026db = *(undefined1 *)(local_res18[0] + 0x16 + uVar2 * 0x28);
    DAT_000026de = *(undefined1 *)(local_res18[0] + 0x18 + uVar2 * 0x28);
    DAT_000026df = *(undefined1 *)(local_res18[0] + 0x1a + uVar2 * 0x28);
    DAT_000026e0 = *(undefined1 *)(local_res18[0] + 0x1c + uVar2 * 0x28);
    DAT_000026e1 = *(undefined1 *)(local_res18[0] + 0x22 + uVar2 * 0x28);
    DAT_000026e2 = *(undefined1 *)(local_res18[0] + 0x24 + uVar2 * 0x28);
    DAT_000026dc = *(undefined1 *)(local_res18[0] + 0x1e + uVar2 * 0x28);
    DAT_000026dd = *(undefined1 *)(local_res18[0] + 0x20 + uVar2 * 0x28);
    DAT_000026e3 = *(undefined1 *)(local_res18[0] + 4 + uVar2 * 0x28);
    DAT_000026cc = *(undefined1 *)(local_res18[0] + 0xe0);
    DAT_000026ce = *(undefined1 *)(local_res18[0] + 0xe1);
    DAT_000026c3 = *(undefined2 *)
                    (local_res18[0] + 0xb0 + (ulonglong)*(byte *)(local_res18[0] + 0xe3) * 2);
    DAT_00002c5d = *(undefined1 *)(local_res18[0] + 0xe5);
  }
  FUN_00000b94();
  return;
}


// ==== FUN_00000940 @ 00000940

undefined8 FUN_00000940(void)

{
  bool bVar1;
  bool bVar2;
  undefined8 uVar3;
  longlong lVar4;
  int local_res8 [2];
  byte local_res10 [8];
  undefined4 local_res18 [2];
  undefined8 *local_res20;
  undefined *puVar5;
  undefined8 local_a8;
  longlong local_a0;
  undefined8 local_98 [2];
  undefined1 local_84;
  undefined1 local_83;
  int local_80;
  int local_7c;
  ushort local_6c;
  undefined4 local_68;
  undefined4 local_64;
  int local_60;
  undefined4 local_5c;
  undefined4 local_58;
  undefined1 local_54;
  undefined1 local_53;
  
  local_a8 = 0x21d;
  puVar5 = &DAT_000026c0;
  (**(code **)(DAT_00002698 + 0x48))
            (u_SaSetup_000025e8,&DAT_00002590,&DAT_000028e0,&local_a8,&DAT_000026c0);
  bVar2 = false;
  FUN_00000260((undefined1 *)local_98,0x30,0);
  local_84 = 1;
  uVar3 = FUN_00002370();
  bVar1 = bVar2;
  if ((char)uVar3 == '\0') {
    lVar4 = (**(code **)(DAT_00002690 + 0x140))(&DAT_00002520,0,&local_res20);
    if (-1 < lVar4) {
      lVar4 = (*(code *)local_res20[8])(local_res8);
      if ((lVar4 < 0) || (local_res8[0] != 0)) {
        lVar4 = -0x7ffffffffffffffd;
      }
      else {
        lVar4 = (*(code *)local_res20[7])(local_res10);
        if ((lVar4 < 0) || ((local_res10[0] & 0xf) != 0)) goto LAB_00000b0b;
        local_60 = 0;
        local_58 = 0;
        local_54 = local_84;
        local_53 = local_83;
        local_res18[0] = 0x30;
        local_68 = 0x50000;
        local_64 = 0x1a;
        local_5c = 0x1c;
        lVar4 = (*(code *)*local_res20)
                          (0,&local_68,0x30,local_res18,(ulonglong)puVar5 & 0xffffffffffffff00,8);
        if (-1 < lVar4) {
          if (local_60 != 0) {
            lVar4 = -0x7ffffffffffffff9;
          }
          FUN_000002c0(local_98,(undefined8 *)&local_68,0x30);
        }
      }
    }
    if (-1 < lVar4) {
      bVar1 = false;
      if (DAT_00002710 == '\0') goto LAB_00000b2d;
      local_80 = DAT_00002711 * 10000;
      local_84 = 1;
      local_6c = local_6c & 0xffcf | 8;
      local_7c = local_80;
      lVar4 = (**(code **)(DAT_00002690 + 0x140))(&DAT_00002520,0,&local_a0);
      if (-1 < lVar4) {
        lVar4 = FUN_000021b8(local_98,&local_a0);
      }
      bVar1 = bVar2;
      if (-1 < lVar4) {
        bVar1 = true;
      }
    }
  }
LAB_00000b0b:
  if ((DAT_00002710 != '\0') && (!bVar1)) {
    DAT_00002711 = 10000;
  }
LAB_00000b2d:
  DAT_00002710 = 0;
  uVar3 = (**(code **)(DAT_00002698 + 0x58))
                    (u_SaSetup_000025e8,&DAT_00002590,DAT_000028e0,local_a8,&DAT_000026c0);
  if (bVar1) {
    (*(code *)*DAT_000026a8)(2);
    uVar3 = (*(code *)DAT_000026a8[3])();
    uVar3 = CONCAT71((int7)((ulonglong)uVar3 >> 8),6);
    out(0xcf9,6);
  }
  return uVar3;
}


// ==== FUN_00000b94 @ 00000b94

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

undefined8 FUN_00000b94(void)

{
  byte bVar1;
  undefined *puVar2;
  undefined1 *puVar3;
  wchar_t *pwVar4;
  undefined2 *puVar5;
  undefined *puVar6;
  undefined4 uVar7;
  longlong lVar8;
  undefined8 uVar9;
  byte local_res8 [8];
  undefined1 local_res10 [8];
  byte local_res18 [8];
  undefined1 local_res20 [8];
  undefined1 local_38;
  undefined1 local_37;
  undefined1 local_36;
  undefined1 local_35;
  undefined1 local_34 [4];
  ushort local_30 [2];
  ushort local_2c [2];
  undefined2 local_28 [2];
  undefined2 local_24 [10];
  
  if (DAT_00003160 == '\0') {
    _DAT_0000315f = 0x100;
    DAT_00002681 = 1;
    uVar9 = rdmsr(0xce);
    DAT_00002901 = (undefined1)((ulonglong)uVar9 >> 8);
    _DAT_00002a92 = 0x101;
    DAT_000029d9 = 0;
    uVar9 = rdmsr(0xce);
    DAT_00002a8f = (undefined1)((ulonglong)uVar9 >> 0x28);
    uVar9 = rdmsr(0xce);
    DAT_00002a90 = (undefined1)((ulonglong)uVar9 >> 8);
    DAT_000029c8 = DAT_00002901;
    FUN_00002060(local_24,local_28,local_res8,local_res18,local_res20,&local_38,&local_37,&local_36,
                 &local_35,local_34,local_30,local_2c,local_res10);
    DAT_00002912 = (uint)local_30[0] * 0x7d;
    DAT_00002917 = local_res10[0];
    DAT_00002a94 = local_res10[0];
    DAT_00002919 = (uint)local_2c[0] * 0x7d;
    _DAT_00002a9f = local_28[0];
    _DAT_00002aa1 = local_24[0];
    DAT_00002a95 = DAT_00002912;
    DAT_00002a99 = DAT_00002919;
    bVar1 = FUN_00001f78();
    DAT_000029c9 = local_res8[0];
    if ((bVar1 != 0) && (local_res18[0] <= bVar1)) {
      DAT_000029c9 = bVar1;
    }
    DAT_000029cb = local_res20[0];
    DAT_000029cc = local_38;
    DAT_000029cd = local_37;
    DAT_000029ce = local_36;
    DAT_000029cf = local_35;
    DAT_000029d0 = local_34[0];
    DAT_000026cb = DAT_000026cc;
    DAT_000026cd = DAT_000026ce;
    DAT_000026e4 = DAT_000026d0;
    DAT_000026e5 = DAT_000026d1;
    DAT_000026e6 = DAT_000026d2;
    DAT_000026e8 = DAT_000026d4;
    DAT_000026ea = DAT_000026d6;
    DAT_000026eb = DAT_000026d7;
    DAT_000026ed = DAT_000026d9;
    DAT_000026ef = DAT_000026db;
    DAT_000026f2 = DAT_000026de;
    DAT_000026f3 = DAT_000026df;
    DAT_000026f4 = DAT_000026e0;
    DAT_000026f5 = DAT_000026e1;
    DAT_000026f6 = DAT_000026e2;
    DAT_000026f0 = DAT_000026dc;
    DAT_000026f1 = DAT_000026dd;
    DAT_000026f7 = DAT_000026e3;
    DAT_00002acf = DAT_00002ab9;
    DAT_00002ad0 = DAT_00002aba;
    DAT_00002ad1 = DAT_00002abb;
    DAT_00002b7d = DAT_00002b4e;
    DAT_00002b7e = DAT_00002b4f;
    DAT_00002ad3 = DAT_00002abd;
    DAT_00002ad5 = DAT_00002abf;
    DAT_00002ad6 = DAT_00002ac0;
    DAT_00002ada = DAT_00002ac4;
    DAT_00002ade = DAT_00002ac6;
    DAT_00002adf = DAT_00002ac7;
    DAT_00002ae1 = DAT_00002ac9;
    DAT_00002ae3 = DAT_00002acb;
    DAT_00002ae4 = DAT_00002acc;
    DAT_000029ca = local_res18[0];
    DAT_000029da = 0;
    DAT_000026c5 = 0;
    DAT_00002ad8 = DAT_00002ac2;
    puVar3 = &DAT_00002b9d;
    puVar5 = &DAT_00002b7f;
    DAT_00002b3b = DAT_00002b43;
    lVar8 = 0xf;
    DAT_00002b3c = DAT_00002b44;
    DAT_00002b3d = DAT_00002b45;
    DAT_00002b3e = DAT_00002b46;
    DAT_00002b3f = DAT_00002b47;
    DAT_00002b40 = DAT_00002b48;
    DAT_00002b41 = DAT_00002b49;
    DAT_00002b42 = DAT_00002b4a;
    do {
      *puVar5 = *(undefined2 *)((longlong)puVar5 + -0x2f);
      puVar5 = puVar5 + 1;
      *puVar3 = puVar3[-0x2f];
      puVar3 = puVar3 + 1;
      lVar8 = lVar8 + -1;
    } while (lVar8 != 0);
    puVar5 = &DAT_00002afd;
    lVar8 = 5;
    do {
      *puVar5 = puVar5[-0x51];
      puVar5 = puVar5 + 1;
      lVar8 = lVar8 + -1;
    } while (lVar8 != 0);
    uVar9 = rdmsr(0x620);
    DAT_00002b0b = (byte)((ulonglong)uVar9 >> 8) & 0x7f;
    DAT_00002b0d = (byte)uVar9 & 0x7f;
    DAT_0000289d = DAT_0000289a;
    DAT_0000289f = DAT_0000289c;
    DAT_000028b2 = DAT_000028a0;
    DAT_000028b3 = DAT_000028a1;
    DAT_000028b4 = DAT_000028a2;
    DAT_000028b6 = DAT_000028a4;
    DAT_000028b7 = DAT_000028a5;
    DAT_000028b9 = DAT_000028a7;
    DAT_000028bb = DAT_000028a9;
    DAT_000028bc = DAT_000028aa;
    DAT_000028bd = DAT_000028ab;
    DAT_000028bf = DAT_000028ad;
    DAT_000028c0 = DAT_000028ae;
    DAT_000028c2 = DAT_000028b0;
    (**(code **)(DAT_00002698 + 0x58))
              (u_CpuSetup_000025d0,&DAT_00002540,DAT_00003460,699,&DAT_00002900);
    (**(code **)(DAT_00002698 + 0x58))
              (u_SaSetup_000025e8,&DAT_00002590,DAT_000028e0,0x21d,&DAT_000026c0);
    puVar2 = &DAT_00002c80;
    uVar9 = 0x7d8;
    puVar6 = &DAT_00002550;
    pwVar4 = u_Setup_000025f8;
    uVar7 = DAT_00002bbc;
  }
  else {
    puVar2 = &DAT_000026c0;
    uVar9 = 0x21d;
    puVar6 = &DAT_00002590;
    pwVar4 = u_SaSetup_000025e8;
    uVar7 = DAT_000028e0;
  }
  (**(code **)(DAT_00002698 + 0x58))(pwVar4,puVar6,uVar7,uVar9,puVar2);
  return 0;
}


// ==== FUN_00001118 @ 00001118

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

undefined8 FUN_00001118(void)

{
  undefined8 uVar1;
  undefined1 *puVar2;
  undefined8 *puVar3;
  undefined2 *puVar4;
  longlong lVar5;
  
  DAT_00002901 = DAT_000029c8;
  DAT_00002911 = DAT_00002a93;
  DAT_00002909 = DAT_00002a92;
  _DAT_0000315f = 0x100;
  DAT_00002710 = 0;
  DAT_00002711 = 10000;
  uVar1 = rdmsr(0xce);
  DAT_00002a8f = (undefined1)((ulonglong)uVar1 >> 0x28);
  uVar1 = rdmsr(0xce);
  DAT_00002a90 = (undefined1)((ulonglong)uVar1 >> 8);
  DAT_000027f4 = 0;
  DAT_000026c3 = DAT_000026c5;
  DAT_000026cc = DAT_000026cb;
  DAT_000026ce = DAT_000026cd;
  DAT_000026d0 = DAT_000026e4;
  DAT_000026d1 = DAT_000026e5;
  DAT_000026d2 = DAT_000026e6;
  DAT_000026d4 = DAT_000026e8;
  DAT_000026d6 = DAT_000026ea;
  DAT_000026d7 = DAT_000026eb;
  DAT_000026d9 = DAT_000026ed;
  DAT_000026db = DAT_000026ef;
  DAT_000026de = DAT_000026f2;
  DAT_000026df = DAT_000026f3;
  DAT_000026e0 = DAT_000026f4;
  DAT_000026e1 = DAT_000026f5;
  DAT_000026e2 = DAT_000026f6;
  DAT_000026dc = DAT_000026f0;
  DAT_000026dd = DAT_000026f1;
  DAT_000026e3 = DAT_000026f7;
  DAT_000029d1 = DAT_000029c9;
  DAT_000029d2 = DAT_000029ca;
  DAT_000029d3 = DAT_000029cb;
  DAT_000029d4 = DAT_000029cc;
  DAT_000029d5 = DAT_000029cd;
  DAT_000029d6 = DAT_000029ce;
  DAT_000029d7 = DAT_000029cf;
  DAT_000029d8 = DAT_000029d0;
  DAT_00002919 = DAT_00002a99;
  DAT_00002912 = DAT_00002a95;
  DAT_000029da = DAT_000029d9;
  DAT_00002ab9 = DAT_00002acf;
  DAT_00002aba = DAT_00002ad0;
  DAT_00002abb = DAT_00002ad1;
  DAT_00002b4e = DAT_00002b7d;
  DAT_00002b4f = DAT_00002b7e;
  DAT_00002abd = DAT_00002ad3;
  DAT_00002abf = DAT_00002ad5;
  DAT_00002ac0 = DAT_00002ad6;
  DAT_00002916 = 0;
  puVar2 = &DAT_00002b6e;
  puVar4 = &DAT_00002b50;
  DAT_00002b0c = DAT_00002b0d;
  lVar5 = 0xf;
  DAT_00002b0a = DAT_00002b0b;
  DAT_00002ac6 = DAT_00002ade;
  DAT_00002ac7 = DAT_00002adf;
  DAT_00002acc = DAT_00002ae4;
  DAT_00002ac9 = DAT_00002ae1;
  DAT_00002acb = DAT_00002ae3;
  DAT_0000289a = DAT_0000289d;
  DAT_0000289c = DAT_0000289f;
  DAT_000028a0 = DAT_000028b2;
  DAT_000028a1 = DAT_000028b3;
  DAT_000028a2 = DAT_000028b4;
  DAT_000028a4 = DAT_000028b6;
  DAT_000028a5 = DAT_000028b7;
  DAT_000028a7 = DAT_000028b9;
  DAT_000028a9 = DAT_000028bb;
  DAT_000028aa = DAT_000028bc;
  DAT_000028ab = DAT_000028bd;
  DAT_000028ad = DAT_000028bf;
  DAT_000028ae = DAT_000028c0;
  DAT_000028b0 = DAT_000028c2;
  DAT_00002ac2 = DAT_00002ad8;
  DAT_00002b43 = DAT_00002b3b;
  DAT_00002b44 = DAT_00002b3c;
  DAT_00002b45 = DAT_00002b3d;
  DAT_00002b46 = DAT_00002b3e;
  DAT_00002b47 = DAT_00002b3f;
  DAT_00002b48 = DAT_00002b40;
  DAT_00002b49 = DAT_00002b41;
  DAT_00002b4a = DAT_00002b42;
  do {
    *puVar4 = *(undefined2 *)((longlong)puVar4 + 0x2f);
    puVar4 = puVar4 + 1;
    *puVar2 = puVar2[0x2f];
    puVar2 = puVar2 + 1;
    lVar5 = lVar5 + -1;
  } while (lVar5 != 0);
  puVar3 = &DAT_00002a5b;
  lVar5 = 5;
  do {
    *(undefined2 *)puVar3 = *(undefined2 *)((longlong)puVar3 + 0xa2);
    puVar3 = (undefined8 *)((longlong)puVar3 + 2);
    lVar5 = lVar5 + -1;
  } while (lVar5 != 0);
  (**(code **)(DAT_00002698 + 0x58))
            (u_SaSetup_000025e8,&DAT_00002590,DAT_000028e0,0x21d,&DAT_000026c0);
  (**(code **)(DAT_00002698 + 0x58))
            (u_CpuSetup_000025d0,&DAT_00002540,DAT_00003460,699,&DAT_00002900);
  (**(code **)(DAT_00002698 + 0x58))
            (u_Setup_000025f8,&DAT_00002550,DAT_00002bbc,0x7d8,&DAT_00002c80);
  return 0;
}


// ==== FUN_000015d0 @ 000015d0

void FUN_000015d0(char param_1)

{
  if (param_1 == '\x01') {
    DAT_00002be1 = DAT_000026d0;
    DAT_00002c61 = DAT_000026d1;
    DAT_00002be2 = DAT_000026d6;
    DAT_00002be3 = DAT_000026d4;
    DAT_00002be5 = DAT_000026df;
    DAT_00002c62 = DAT_000026d7;
    DAT_00002be6 = DAT_000026d9;
    DAT_00002be8 = DAT_000026db;
    DAT_00002be9 = DAT_000026e0;
    DAT_00002bea = DAT_000026de;
    DAT_00002beb = DAT_000026d2;
    DAT_00002bee = DAT_000026e3;
    DAT_00002bef = DAT_000026cd;
    DAT_00002bf0 = DAT_000026ce;
    DAT_00002bf1 = DAT_000026cf;
    DAT_00002bf2 = DAT_000026c3;
    DAT_00002bf5 = DAT_00002711;
    DAT_00002bf9 = DAT_000028a0;
    DAT_00002bfa = DAT_000027f4;
    DAT_00002bfb = DAT_000026cc;
    DAT_00002bfc = DAT_000028a1;
    DAT_00002bfd = DAT_000028a2;
    DAT_00002bff = DAT_000028a4;
    DAT_00002c00 = DAT_000028a5;
    DAT_00002c02 = DAT_000028a7;
    DAT_00002c04 = DAT_0000289a;
    DAT_00002c06 = DAT_0000289c;
    DAT_00002c53 = DAT_000028a9;
    DAT_00002c54 = DAT_000028aa;
    DAT_00002c55 = DAT_000028ab;
    DAT_00002c57 = DAT_000028ad;
    DAT_00002c58 = DAT_000028ae;
    DAT_00002c5a = DAT_000028b0;
    DAT_00002c5c = DAT_000028c4;
    DAT_00002c5e = DAT_000026dc;
    DAT_00002c5f = DAT_000026dd;
    DAT_00002c07 = DAT_00002ab7;
    DAT_00002c08 = DAT_00002909;
    DAT_00002c09 = DAT_00002901;
    DAT_00002c0a = DAT_00002903;
    DAT_00002c0c = DAT_00002aba;
    DAT_00002c0d = DAT_00002abb;
    DAT_00002c0f = DAT_00002ac0;
    DAT_00002c11 = DAT_00002abd;
    DAT_00002c13 = DAT_00002abf;
    DAT_00002c1d = DAT_00002917;
    DAT_00002c1e = DAT_00002911;
    DAT_00002c1f = DAT_000029d1;
    DAT_00002c20 = DAT_000029d2;
    DAT_00002c21 = DAT_000029d3;
    DAT_00002c22 = DAT_000029d4;
    DAT_00002c23 = DAT_000029d5;
    DAT_00002c24 = DAT_000029d6;
    DAT_00002c25 = DAT_000029d7;
    DAT_00002c26 = DAT_000029d8;
    DAT_00002c27 = DAT_00002b43;
    DAT_00002c28 = DAT_00002b44;
    DAT_00002c29 = DAT_00002b45;
    DAT_00002c2a = DAT_00002b46;
    DAT_00002c2b = DAT_00002b47;
    DAT_00002c2c = DAT_00002b48;
    DAT_00002c2d = DAT_00002b49;
    DAT_00002c2e = DAT_00002b4a;
    DAT_00002c2f = DAT_0000292b;
    DAT_00002c30 = DAT_00002912;
    DAT_00002c34 = DAT_00002a95;
    DAT_00002c38 = DAT_00002918;
    DAT_00002c39 = DAT_00002919;
    DAT_00002c3d = DAT_00002a99;
    DAT_00002c60 = DAT_00002b0c;
    DAT_00002c14 = DAT_00002ac4;
    DAT_00002c15 = DAT_00002ac6;
    DAT_00002c16 = DAT_00002ac7;
    DAT_00002c18 = DAT_00002acc;
    DAT_00002c1a = DAT_00002ac9;
    DAT_00002c1c = DAT_00002acb;
    DAT_00002c41 = DAT_000029da;
    DAT_00002c42 = DAT_00002916;
    DAT_00002c43 = DAT_00002ab2;
    DAT_00002c44 = DAT_00002ab3;
    DAT_00002c51 = DAT_00002ac2;
    DAT_00002c47 = DAT_00002a5b;
    DAT_00002c4f = DAT_00002a63;
    DAT_00002c46 = DAT_0000315f;
    return;
  }
  DAT_000026d0 = DAT_00002be1;
  DAT_000026d1 = DAT_00002c61;
  DAT_000026d6 = DAT_00002be2;
  DAT_000026d4 = DAT_00002be3;
  DAT_000026df = DAT_00002be5;
  DAT_000026d7 = DAT_00002c62;
  DAT_000026d9 = DAT_00002be6;
  DAT_000026db = DAT_00002be8;
  DAT_000026e0 = DAT_00002be9;
  DAT_000026de = DAT_00002bea;
  DAT_000026d2 = DAT_00002beb;
  DAT_000026e3 = DAT_00002bee;
  DAT_000026cd = DAT_00002bef;
  DAT_000026ce = DAT_00002bf0;
  DAT_000026cf = DAT_00002bf1;
  DAT_000026c3 = DAT_00002bf2;
  DAT_00002710 = DAT_00002bf4;
  DAT_00002711 = DAT_00002bf5;
  DAT_000028a0 = DAT_00002bf9;
  DAT_000027f4 = DAT_00002bfa;
  DAT_000026cc = DAT_00002bfb;
  DAT_000028a1 = DAT_00002bfc;
  DAT_000028a2 = DAT_00002bfd;
  DAT_000028a4 = DAT_00002bff;
  DAT_000028a5 = DAT_00002c00;
  DAT_000028a7 = DAT_00002c02;
  DAT_0000289a = DAT_00002c04;
  DAT_0000289c = DAT_00002c06;
  DAT_000028a9 = DAT_00002c53;
  DAT_000028aa = DAT_00002c54;
  DAT_000028ab = DAT_00002c55;
  DAT_000028ad = DAT_00002c57;
  DAT_000028ae = DAT_00002c58;
  DAT_000028b0 = DAT_00002c5a;
  DAT_000028c4 = DAT_00002c5c;
  DAT_000026dc = DAT_00002c5e;
  DAT_000026dd = DAT_00002c5f;
  DAT_00002ab7 = DAT_00002c07;
  DAT_00002909 = DAT_00002c08;
  DAT_00002901 = DAT_00002c09;
  DAT_00002903 = DAT_00002c0a;
  DAT_00002ab9 = DAT_00002c0b;
  DAT_00002aba = DAT_00002c0c;
  DAT_00002abb = DAT_00002c0d;
  DAT_00002ac0 = DAT_00002c0f;
  DAT_00002abd = DAT_00002c11;
  DAT_00002abf = DAT_00002c13;
  DAT_00002917 = DAT_00002c1d;
  DAT_00002911 = DAT_00002c1e;
  DAT_000029d1 = DAT_00002c1f;
  DAT_000029d2 = DAT_00002c20;
  DAT_000029d3 = DAT_00002c21;
  DAT_000029d4 = DAT_00002c22;
  DAT_000029d5 = DAT_00002c23;
  DAT_000029d6 = DAT_00002c24;
  DAT_000029d7 = DAT_00002c25;
  DAT_000029d8 = DAT_00002c26;
  DAT_00002b43 = DAT_00002c27;
  DAT_00002b44 = DAT_00002c28;
  DAT_00002b45 = DAT_00002c29;
  DAT_00002b46 = DAT_00002c2a;
  DAT_00002b47 = DAT_00002c2b;
  DAT_00002b48 = DAT_00002c2c;
  DAT_00002b49 = DAT_00002c2d;
  DAT_00002b4a = DAT_00002c2e;
  DAT_0000292b = DAT_00002c2f;
  DAT_00002912 = DAT_00002c30;
  DAT_00002a95 = DAT_00002c34;
  DAT_00002918 = DAT_00002c38;
  DAT_00002919 = DAT_00002c39;
  DAT_00002a99 = DAT_00002c3d;
  DAT_00002b0c = DAT_00002c60;
  DAT_00002ac4 = DAT_00002c14;
  DAT_00002ac6 = DAT_00002c15;
  DAT_00002ac7 = DAT_00002c16;
  DAT_00002acc = DAT_00002c18;
  DAT_00002ac9 = DAT_00002c1a;
  DAT_00002acb = DAT_00002c1c;
  DAT_000029da = DAT_00002c41;
  DAT_00002916 = DAT_00002c42;
  DAT_00002ab2 = DAT_00002c43;
  DAT_00002ab3 = DAT_00002c44;
  DAT_00002ac2 = DAT_00002c51;
  DAT_00002a5b = DAT_00002c47;
  DAT_00002a63 = DAT_00002c4f;
  DAT_0000315f = DAT_00002c46;
  return;
}


// ==== FUN_00001e28 @ 00001e28

longlong FUN_00001e28(void)

{
  ulonglong uVar1;
  longlong *plVar2;
  
  uVar1 = 0;
  if (DAT_000026a0 == 0) {
    DAT_000026a0 = 0;
    if (*(ulonglong *)(DAT_00002688 + 0x68) != 0) {
      plVar2 = *(longlong **)(DAT_00002688 + 0x70);
      do {
        if ((DAT_00002580 == *plVar2) && (DAT_00002588 == plVar2[1])) {
          DAT_000026a0 = (*(longlong **)(DAT_00002688 + 0x70))[uVar1 * 3 + 2];
          return DAT_000026a0;
        }
        uVar1 = uVar1 + 1;
        plVar2 = plVar2 + 3;
      } while (uVar1 < *(ulonglong *)(DAT_00002688 + 0x68));
    }
  }
  return DAT_000026a0;
}


// ==== FUN_00001e94 @ 00001e94

void FUN_00001e94(void)

{
  short *psVar1;
  
  psVar1 = (short *)FUN_00001e28();
  do {
    if (*psVar1 == -1) {
      psVar1 = (short *)0x0;
LAB_00001ecb:
      if ((psVar1 == (short *)0x0) ||
         ((DAT_000025c0 == *(longlong *)(psVar1 + 4) && (DAT_000025c8 == *(longlong *)(psVar1 + 8)))
         )) {
        return;
      }
    }
    else if (*psVar1 == 4) goto LAB_00001ecb;
    psVar1 = (short *)((longlong)psVar1 + (ulonglong)(ushort)psVar1[1]);
  } while( true );
}


// ==== FUN_00001ee4 @ 00001ee4

void FUN_00001ee4(uint param_1)

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
      FUN_00000320();
    }
    bVar6 = uVar3 != 0;
    uVar3 = uVar3 - 1;
  } while (bVar6);
  return;
}


// ==== FUN_00001f44 @ 00001f44

longlong FUN_00001f44(longlong param_1)

{
  FUN_00001ee4((uint)((ulonglong)(param_1 * 0x369e99) / 1000000));
  return param_1;
}


// ==== FUN_00001f78 @ 00001f78

undefined1 FUN_00001f78(void)

{
  longlong lVar1;
  undefined1 uVar2;
  uint uVar3;
  uint local_res8 [2];
  int local_res10;
  uint local_res14;
  undefined8 local_res18;
  int local_res20;
  uint local_res24;
  
  lVar1 = FUN_00002484();
  uVar3 = local_res8[0];
  if (-1 < lVar1) {
    local_res14 = 0x80000007;
    local_res10 = 0;
    FUN_000002c0(&local_res18,(undefined8 *)&local_res10,8);
    wrmsr(0x150,local_res18);
    FUN_00002484();
    local_res18 = rdmsr(0x150);
    FUN_000002c0((undefined8 *)&local_res10,&local_res18,8);
    FUN_00001f44(10);
    local_res18 = rdmsr(0x150);
    FUN_000002c0((undefined8 *)&local_res20,&local_res18,8);
    if ((local_res14 != local_res24) && (local_res10 != local_res20)) {
      return 0;
    }
    uVar3 = local_res14 & 0xff;
    FUN_000002c0((undefined8 *)local_res8,(undefined8 *)&local_res10,4);
  }
  uVar2 = 0;
  if ((-1 < lVar1) && (uVar2 = 0, uVar3 == 0)) {
    uVar2 = (undefined1)local_res8[0];
  }
  return uVar2;
}


// ==== FUN_00002060 @ 00002060

void FUN_00002060(undefined2 *param_1,undefined2 *param_2,undefined1 *param_3,undefined1 *param_4,
                 undefined1 *param_5,undefined1 *param_6,undefined1 *param_7,undefined1 *param_8,
                 undefined1 *param_9,undefined1 *param_10,ushort *param_11,ushort *param_12,
                 undefined1 *param_13)

{
  ulonglong uVar1;
  undefined8 uVar2;
  undefined8 uVar3;
  ulonglong uVar4;
  ulonglong uVar5;
  undefined1 uVar6;
  
  uVar1 = rdmsr(0x610);
  uVar2 = rdmsr(0x606);
  *param_11 = (ushort)uVar1 & 0x7fff;
  *param_12 = (ushort)(uVar1 >> 0x20) & 0x7fff;
  uVar3 = rdmsr(0x1ad);
  uVar6 = 1;
  *param_3 = (char)uVar3;
  uVar4 = 0;
  *param_1 = (short)((uVar1 & 0x7fff) / (2L << (((byte)uVar2 & 0xf) - 1 & 0x3f) & 0xffU));
  *param_4 = (char)((ulonglong)uVar3 >> 8);
  *param_2 = 0;
  *param_5 = (char)((ulonglong)uVar3 >> 0x10);
  *param_6 = (char)((ulonglong)uVar3 >> 0x18);
  *param_7 = (char)((ulonglong)uVar3 >> 0x20);
  *param_8 = (char)((ulonglong)uVar3 >> 0x28);
  *param_9 = (char)((ulonglong)uVar3 >> 0x30);
  *param_10 = (char)((ulonglong)uVar3 >> 0x38);
  uVar5 = uVar4;
  do {
    if (((byte)(uVar1 >> 0x11) & 0x7f) == (&DAT_00002621)[uVar4]) {
      uVar6 = (&DAT_00002620)[uVar5 * 2];
      break;
    }
    uVar5 = (ulonglong)(byte)((char)uVar5 + 1);
    uVar4 = uVar5 * 2;
  } while ((&DAT_00002620)[uVar4] != -1);
  *param_13 = uVar6;
  return;
}


// ==== FUN_000021b8 @ 000021b8

longlong FUN_000021b8(undefined8 *param_1,longlong *param_2)

{
  longlong lVar1;
  int local_res10 [2];
  byte local_res18 [8];
  undefined4 local_res20 [2];
  undefined4 local_48;
  undefined4 local_44;
  int local_40;
  undefined4 local_3c;
  undefined4 local_38;
  
  lVar1 = (**(code **)(*param_2 + 0x40))(local_res10);
  if ((lVar1 < 0) || (local_res10[0] != 0)) {
    lVar1 = -0x7ffffffffffffffd;
  }
  else {
    lVar1 = (**(code **)(*param_2 + 0x38))(local_res18);
    if ((lVar1 < 0) || ((local_res18[0] & 0xf) != 0)) {
      lVar1 = -0x7ffffffffffffffa;
    }
    else {
      local_res20[0] = 0x30;
      if ((undefined8 *)&local_48 != param_1) {
        FUN_000002c0((undefined8 *)&local_48,param_1,0x30);
      }
      local_40 = 0;
      local_38 = 0;
      local_48 = 0x50000;
      local_44 = 0x1b;
      local_3c = 0x1c;
      lVar1 = (**(code **)*param_2)(0,&local_48,0x30,local_res20,0,8);
      if ((-1 < lVar1) && (local_40 != 0)) {
        lVar1 = -0x7ffffffffffffff9;
      }
    }
  }
  return lVar1;
}


// ==== FUN_00002290 @ 00002290

longlong FUN_00002290(undefined1 param_1)

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
  lVar1 = (**(code **)(DAT_00002690 + 0x140))(&DAT_00002520,0,&local_res20);
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


// ==== FUN_00002370 @ 00002370

ulonglong FUN_00002370(void)

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
  
  lVar1 = (**(code **)(DAT_00002690 + 0x140))(&DAT_000025b0,0,local_30);
  if (lVar1 < 0) {
    uVar2 = (**(code **)(DAT_00002690 + 0x140))(&DAT_00002520,0,&local_res18);
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
        lVar1 = (**(code **)(DAT_00002690 + 0x140))(&DAT_000025b0,0,local_28);
        if (lVar1 == -0x7ffffffffffffff2) {
          local_38 = 0;
          lVar1 = (**(code **)(DAT_00002690 + 0x80))(&local_38,&DAT_000025b0,0,0);
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


// ==== FUN_00002484 @ 00002484

undefined8 FUN_00002484(void)

{
  char cVar1;
  ushort uVar2;
  undefined8 uVar3;
  undefined8 local_res10;
  undefined8 local_res18;
  
  uVar3 = 0;
  uVar2 = 0;
  do {
    local_res10 = rdmsr(0x150);
    FUN_000002c0(&local_res18,&local_res10,8);
    cVar1 = local_res18._7_1_;
    FUN_00001f44(1);
    uVar2 = uVar2 + 1;
    if (-1 < cVar1) {
      return 0;
    }
  } while (uVar2 < 1000);
  if (uVar2 == 1000) {
    uVar3 = 0x8000000000000012;
  }
  return uVar3;
}


