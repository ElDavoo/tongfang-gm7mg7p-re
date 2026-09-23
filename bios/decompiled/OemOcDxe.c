// OemOcDxe.efi: Ghidra x86:LE:64:default decompile, unedited
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


// ==== entry @ 000003d0

void entry(undefined8 param_1,longlong param_2)

{
  byte bVar1;
  
  bVar1 = (byte)param_1;
  FUN_000003ec(param_1,param_2);
  FUN_000004f8(bVar1,param_2);
  return;
}


// ==== FUN_000003ec @ 000003ec

void FUN_000003ec(undefined8 param_1,longlong param_2)

{
  uint uVar1;
  int iVar2;
  short *psVar3;
  ulonglong uVar4;
  longlong lVar5;
  
  DAT_00001998 = *(longlong *)(param_2 + 0x60);
  DAT_00001990 = param_2;
  FUN_00001000();
  psVar3 = (short *)FUN_00001000();
  do {
    if (*psVar3 == -1) {
      psVar3 = (short *)0x0;
LAB_00000440:
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
LAB_000004a9:
        if ((DAT_000019b8 != (undefined8 *)0x0) ||
           (lVar5 = (**(code **)(DAT_00001998 + 0x140))(&DAT_00001510,0,&DAT_000019b8), -1 < lVar5))
        {
          (*(code *)*DAT_000019b8)(DAT_000019b8,&DAT_000019c0);
        }
        return;
      }
      if ((DAT_00001530 == *(longlong *)(psVar3 + 4)) && (DAT_00001538 == *(longlong *)(psVar3 + 8))
         ) goto LAB_000004a9;
    }
    else if (*psVar3 == 4) goto LAB_00000440;
    psVar3 = (short *)((longlong)psVar3 + (ulonglong)(ushort)psVar3[1]);
  } while( true );
}


// ==== FUN_000004f8 @ 000004f8

undefined8 FUN_000004f8(byte param_1,longlong param_2)

{
  byte bVar1;
  longlong lVar2;
  ulonglong uVar3;
  
  if (DAT_000019a8 == 0) {
    DAT_000019a0 = *(undefined8 *)(param_2 + 0x58);
    DAT_000019a8 = param_2;
  }
  uVar3 = 0;
  lVar2 = FUN_00000f38('b',0xa3,7);
  if (((-1 < lVar2) && (lVar2 = FUN_00000f38('b',0xa2,0x41), -1 < lVar2)) &&
     (lVar2 = FUN_00000dd4('b',0xa4), -1 < lVar2)) {
    bVar1 = in(0x66);
    if ((bVar1 & 1) == 0) {
      do {
        if (0x1ffff < uVar3) goto LAB_0000058f;
        FUN_000010cc(0xf);
        bVar1 = in(0x66);
        uVar3 = uVar3 + 1;
      } while ((bVar1 & 1) == 0);
      if (0x1ffff < uVar3) goto LAB_0000058f;
    }
    param_1 = in(0x62);
  }
LAB_0000058f:
  if ((char)param_1 < '\0') {
    FUN_0000067c();
    lVar2 = FUN_00000f38('b',0xa3,7);
    if ((-1 < lVar2) && (lVar2 = FUN_00000f38('b',0xa2,0x41), -1 < lVar2)) {
      FUN_00000f38('b',0xa5,param_1 & 0x7f);
    }
  }
  else {
    FUN_000007a8();
  }
  return 0;
}


// ==== FUN_000005d8 @ 000005d8

undefined8 FUN_000005d8(void)

{
  undefined8 uVar1;
  uint uVar2;
  uint *puVar3;
  undefined1 *puVar4;
  undefined4 uVar5;
  undefined8 *puVar6;
  uint local_res8 [2];
  undefined1 local_res10 [8];
  undefined8 local_res18 [2];
  undefined4 local_2d8;
  undefined4 local_2d4;
  undefined4 local_2d0;
  undefined4 local_2cc;
  undefined1 local_2c8 [439];
  char local_111;
  
  local_res18[0] = 699;
  puVar6 = local_res18;
  puVar4 = local_res10;
  local_2d8 = 0xb08f97ff;
  uVar2 = 0x1920;
  local_2d4 = 0x4193e6e8;
  local_2d0 = 0x9e5e97a9;
  local_2cc = 0x32db0a9b;
  (**(code **)(DAT_000019a0 + 0x48))(u_CpuSetup_00001920,&local_2d8,puVar4,puVar6,local_2c8);
  uVar5 = SUB84(puVar6,0);
  if (local_111 == '\x01') {
    uVar1 = FUN_00001158(uVar2);
    if ((char)uVar1 != '\0') {
      puVar3 = local_res8;
      FUN_00000c30(uVar2,puVar3);
      if (local_res8[0] == 0) {
        FUN_0000119c(uVar2,(char)puVar3,puVar4,uVar5);
      }
    }
  }
  return 0;
}


// ==== FUN_0000067c @ 0000067c

undefined8 FUN_0000067c(void)

{
  undefined4 local_res8 [2];
  undefined4 local_res10 [2];
  undefined8 local_res18;
  undefined8 local_res20;
  undefined4 local_398;
  undefined4 local_394;
  undefined4 local_390;
  undefined4 local_38c;
  undefined1 local_388 [92];
  undefined1 local_32c;
  undefined1 local_2c8 [439];
  undefined1 local_111;
  
  local_res18 = 699;
  local_398 = 0xb08f97ff;
  local_394 = 0x4193e6e8;
  local_390 = 0x9e5e97a9;
  local_38c = 0x32db0a9b;
  local_res20 = 0xb4;
  local_res10[0] = 7;
  local_res8[0] = 3;
  (**(code **)(DAT_000019a0 + 0x48))
            (u_CpuSetup_00001920,&local_398,local_res8,&local_res18,local_2c8);
  (**(code **)(DAT_000019a0 + 0x48))
            (u_UniWillVariable_00001938,&DAT_00001520,local_res10,&local_res20,local_388);
  local_32c = 1;
  local_111 = 0;
  (**(code **)(DAT_000019a0 + 0x58))
            (u_CpuSetup_00001920,&local_398,local_res8[0],local_res18,local_2c8);
  (**(code **)(DAT_000019a0 + 0x58))
            (u_UniWillVariable_00001938,&DAT_00001520,local_res10[0],local_res20,local_388);
  return 0;
}


// ==== FUN_000007a8 @ 000007a8

undefined8 FUN_000007a8(void)

{
  undefined4 local_res8 [2];
  undefined4 local_res10 [2];
  undefined4 local_res18 [2];
  undefined8 local_res20;
  undefined4 local_b98;
  undefined4 local_b94;
  undefined4 local_b90;
  undefined4 local_b8c;
  undefined4 local_b88;
  undefined4 local_b84;
  undefined4 local_b80;
  undefined4 local_b7c;
  undefined8 local_b78;
  undefined8 local_b70;
  undefined1 local_b68 [51];
  char local_b35;
  undefined2 local_b34;
  undefined4 local_b32;
  short local_b2e;
  undefined4 local_b2c;
  char local_b0b;
  short local_b04;
  char local_b02;
  undefined1 local_aa8 [445];
  short local_8eb;
  char local_8e9;
  undefined2 local_8e8;
  undefined1 local_7e8 [2007];
  char local_11;
  
  local_b70 = 0xb4;
  local_res10[0] = 7;
  local_res8[0] = 3;
  local_res20 = 0x7d8;
  local_b78 = 699;
  local_b88 = 0xb08f97ff;
  local_b84 = 0x4193e6e8;
  local_b80 = 0x9e5e97a9;
  local_b7c = 0x32db0a9b;
  local_b98 = 0xec87d643;
  local_b94 = 0x4bb5eba4;
  local_b90 = 0x3e3fe5a1;
  local_b8c = 0xa90db236;
  (**(code **)(DAT_000019a0 + 0x48))(u_CpuSetup_00001920,&local_b88,local_res8,&local_b78,local_aa8)
  ;
  (**(code **)(DAT_000019a0 + 0x48))
            (u_UniWillVariable_00001938,&DAT_00001520,local_res10,&local_b70,local_b68);
  (**(code **)(DAT_000019a0 + 0x48))(u_Setup_00001958,&local_b98,local_res18,&local_res20,local_7e8)
  ;
  local_11 = local_b35;
  if (local_b35 == '\x01') {
    FUN_000005d8();
  }
  if (local_b0b == '\x01') {
    if (local_b02 == '\x01') {
      local_8e9 = local_b02;
      local_8eb = local_b04;
      local_8e8 = local_b34;
    }
    if (local_b02 == '\0') {
      local_8e9 = '\0';
      local_8eb = local_b2e;
      local_8e8 = local_b34;
    }
    if (local_b02 == '\x02') {
      local_8e8 = local_b34;
      if (local_b04 == 0) {
        local_8e9 = '\0';
        local_8eb = local_b2e;
      }
      else {
        local_8e9 = '\x01';
        local_8eb = local_b04;
      }
    }
  }
  local_b32 = 2000;
  local_b2c = 100;
  (**(code **)(DAT_000019a0 + 0x58))
            (u_Setup_00001958,&local_b98,local_res18[0],local_res20,local_7e8);
  (**(code **)(DAT_000019a0 + 0x58))
            (u_CpuSetup_00001920,&local_b88,local_res8[0],local_b78,local_aa8);
  (**(code **)(DAT_000019a0 + 0x58))
            (u_UniWillVariable_00001938,&DAT_00001520,local_res10[0],local_b70,local_b68);
  return 0;
}


// ==== FUN_000009e4 @ 000009e4

ulonglong FUN_000009e4(uint param_1,uint param_2)

{
  char cVar1;
  undefined *puVar2;
  ulonglong uVar3;
  ulonglong uVar4;
  ulonglong uVar5;
  uint uVar6;
  int local_res8 [4];
  uint local_res18 [4];
  
  uVar5 = (ulonglong)param_1;
  puVar2 = FUN_0000123c(local_res18);
  uVar6 = (uint)uVar5;
  uVar5 = uVar5 & 0xff;
  uVar3 = FUN_00001100();
  uVar4 = uVar3 & 0xffffffffffffff00;
  if ((4 - (uint)((char)uVar3 != '\x02')) * 0x100 <= uVar6) {
    FUN_0000123c(local_res8);
    cVar1 = FUN_00001100();
    uVar4 = (ulonglong)(local_res8[0] - 1U);
    if (((uVar6 <= ((4 - (uint)(cVar1 != '\x02')) * 0x100 | local_res8[0] - 1U)) &&
        ((uint)uVar5 < local_res18[0])) &&
       (uVar4 = uVar5 & 0xffffffff, param_2 <= *(ushort *)(puVar2 + uVar5 * 0x1e + 0x1c) - 1 >> 5))
    {
      return CONCAT71((int7)(uVar4 >> 8),1);
    }
  }
  return uVar4 & 0xffffffffffffff00;
}


// ==== FUN_00000a68 @ 00000a68

void FUN_00000a68(int param_1,byte param_2,short param_3,undefined4 *param_4)

{
  short sVar1;
  undefined *puVar2;
  short sVar3;
  undefined1 *puVar4;
  ulonglong uVar5;
  undefined4 local_res8 [2];
  
  uVar5 = (ulonglong)param_2;
  puVar2 = FUN_0000123c(local_res8);
  if (param_1 == 0) {
    puVar4 = puVar2 + uVar5 * 0x1e;
    sVar3 = *(short *)(puVar4 + 4);
  }
  else if (param_1 == 1) {
    puVar4 = puVar2 + uVar5 * 0x1e;
    sVar3 = *(short *)(puVar4 + 0xc);
  }
  else if (param_1 == 2) {
    puVar4 = puVar2 + uVar5 * 0x1e;
    sVar3 = *(short *)(puVar4 + 10);
  }
  else if (param_1 == 3) {
    puVar4 = puVar2 + uVar5 * 0x1e;
    sVar3 = *(short *)(puVar4 + 0x10);
  }
  else if (param_1 == 4) {
    puVar4 = puVar2 + uVar5 * 0x1e;
    sVar3 = *(short *)(puVar4 + 0xe);
  }
  else if (param_1 == 5) {
    puVar4 = puVar2 + uVar5 * 0x1e;
    sVar3 = *(short *)(puVar4 + 0x14);
  }
  else if (param_1 == 6) {
    puVar4 = puVar2 + uVar5 * 0x1e;
    sVar3 = *(short *)(puVar4 + 0x16);
  }
  else {
    if (param_1 != 7) goto LAB_00000b2d;
    puVar4 = puVar2 + uVar5 * 0x1e;
    sVar3 = *(short *)(puVar4 + 0x18);
  }
  if (sVar3 != -1) {
    sVar1 = param_3 * 4;
    if (param_1 - 6U < 2) {
      sVar1 = param_3 * 8;
    }
    *param_4 = *(undefined4 *)((ulonglong)CONCAT12(*puVar4,sVar3 + sVar1) | 0xfd000000);
    return;
  }
LAB_00000b2d:
  *param_4 = 0;
  return;
}


// ==== FUN_00000b70 @ 00000b70

ulonglong FUN_00000b70(int param_1,uint param_2,uint param_3,uint param_4,uint param_5)

{
  ushort uVar1;
  undefined *puVar2;
  ulonglong uVar3;
  byte *pbVar4;
  uint local_res8 [2];
  uint local_res10 [2];
  
  local_res8[0] = 0;
  puVar2 = FUN_0000123c(local_res10);
  if (param_1 == 6) {
    pbVar4 = puVar2 + (ulonglong)(byte)param_2 * 0x1e;
    uVar1 = *(ushort *)(pbVar4 + 0x16);
    FUN_00000c8c(param_2,param_3,local_res8);
  }
  else {
    if (param_1 != 7) {
      return 0x8000000000000003;
    }
    pbVar4 = puVar2 + (ulonglong)(byte)param_2 * 0x1e;
    uVar1 = *(ushort *)(pbVar4 + 0x18);
    FUN_00000cdc(param_2,param_3,local_res8);
  }
  if (uVar1 == 0xffff) {
    return 0x8000000000000003;
  }
  local_res10[0] = local_res8[0] & param_4 | param_5;
  uVar3 = FUN_00001270(*pbVar4,(ulonglong)((uint)uVar1 + param_3 * 8),local_res10,(byte *)local_res8
                       ,0x13);
  return uVar3;
}


// ==== FUN_00000c30 @ 00000c30

undefined8 FUN_00000c30(uint param_1,uint *param_2)

{
  undefined8 uVar1;
  undefined *puVar2;
  uint local_res8 [8];
  
  local_res8[0] = param_1;
  uVar1 = FUN_00001158(param_1);
  if ((char)uVar1 == '\0') {
    uVar1 = 0x8000000000000002;
  }
  else {
    puVar2 = FUN_0000123c(local_res8);
    *param_2 = *(uint *)(((ulonglong)(byte)puVar2[0x1e] | 0xfd00) << 0x10 |
                        (ulonglong)(ushort)(*(short *)(puVar2 + 0x20) + 8)) >> 0x18 & 3;
    uVar1 = 0;
  }
  return uVar1;
}


// ==== FUN_00000c8c @ 00000c8c

undefined8 FUN_00000c8c(uint param_1,uint param_2,undefined4 *param_3)

{
  ulonglong uVar1;
  undefined8 uVar2;
  
  uVar1 = FUN_000009e4(param_1,param_2);
  if ((char)uVar1 == '\0') {
    uVar2 = 0x8000000000000002;
  }
  else {
    FUN_00000a68(6,(byte)param_1,(short)param_2,param_3);
    uVar2 = 0;
  }
  return uVar2;
}


// ==== FUN_00000cdc @ 00000cdc

undefined8 FUN_00000cdc(uint param_1,uint param_2,undefined4 *param_3)

{
  ulonglong uVar1;
  undefined8 uVar2;
  
  uVar1 = FUN_000009e4(param_1,param_2);
  if ((char)uVar1 == '\0') {
    uVar2 = 0x8000000000000002;
  }
  else {
    FUN_00000a68(7,(byte)param_1,(short)param_2,param_3);
    uVar2 = 0;
  }
  return uVar2;
}


// ==== FUN_00000d2c @ 00000d2c

ulonglong FUN_00000d2c(uint param_1,uint param_2,uint param_3)

{
  ulonglong uVar1;
  
  uVar1 = FUN_000009e4(param_1,param_2);
  if ((char)uVar1 == '\0') {
    uVar1 = 0x8000000000000002;
  }
  else {
    uVar1 = FUN_00000b70(7,param_1,param_2,~param_3,0);
  }
  return uVar1;
}


// ==== FUN_00000d80 @ 00000d80

ulonglong FUN_00000d80(uint param_1,uint param_2,uint param_3)

{
  ulonglong uVar1;
  
  uVar1 = FUN_000009e4(param_1,param_2);
  if ((char)uVar1 == '\0') {
    uVar1 = 0x8000000000000002;
  }
  else {
    uVar1 = FUN_00000b70(7,param_1,param_2,0xffffffff,param_3);
  }
  return uVar1;
}


// ==== FUN_00000dd4 @ 00000dd4

undefined8 FUN_00000dd4(char param_1,undefined1 param_2)

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
      FUN_000010cc(0xf);
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


// ==== FUN_00000e4c @ 00000e4c

undefined8 FUN_00000e4c(char param_1)

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
      FUN_000010cc(5000);
      bVar2 = in(uVar1);
      uVar5 = uVar5 + 1;
    } while ((bVar2 & 1) != 0);
    if (0x1ffff < uVar5) {
      return 0x8000000000000007;
    }
  }
  return 0;
}


// ==== FUN_00000ed4 @ 00000ed4

undefined8 FUN_00000ed4(char param_1)

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
      FUN_000010cc(0xf);
      bVar2 = in(uVar1);
      uVar3 = uVar3 + 1;
    } while ((bVar2 & 2) != 0);
    if (0x1ffff < uVar3) {
      return 0x8000000000000007;
    }
  }
  return 0;
}


// ==== FUN_00000f38 @ 00000f38

longlong FUN_00000f38(char param_1,undefined1 param_2,undefined1 param_3)

{
  byte bVar1;
  byte bVar2;
  longlong lVar3;
  ulonglong uVar4;
  undefined2 uVar5;
  
  lVar3 = FUN_00000ed4(param_1);
  uVar4 = 0;
  if (lVar3 < 0) {
    return lVar3;
  }
  FUN_00000e4c(param_1);
  FUN_00000dd4(param_1,param_2);
  FUN_00000ed4(param_1);
  uVar5 = 0x60;
  bVar1 = 100;
  if (param_1 != '`') {
    bVar1 = 0x66;
  }
  bVar2 = in((ushort)bVar1);
  if ((bVar2 & 2) != 0) {
    do {
      if (0x1ffff < uVar4) goto LAB_00000fda;
      FUN_000010cc(0xf);
      bVar2 = in((ushort)bVar1);
      uVar4 = uVar4 + 1;
    } while ((bVar2 & 2) != 0);
    if (0x1ffff < uVar4) goto LAB_00000fda;
  }
  if (param_1 != '`') {
    uVar5 = 0x62;
  }
  out(uVar5,param_3);
LAB_00000fda:
  FUN_00000e4c(param_1);
  return lVar3;
}


// ==== FUN_00001000 @ 00001000

longlong FUN_00001000(void)

{
  ulonglong uVar1;
  longlong *plVar2;
  
  uVar1 = 0;
  if (DAT_000019b0 == 0) {
    DAT_000019b0 = 0;
    if (*(ulonglong *)(DAT_00001990 + 0x68) != 0) {
      plVar2 = *(longlong **)(DAT_00001990 + 0x70);
      do {
        if ((DAT_00001500 == *plVar2) && (DAT_00001508 == plVar2[1])) {
          DAT_000019b0 = (*(longlong **)(DAT_00001990 + 0x70))[uVar1 * 3 + 2];
          return DAT_000019b0;
        }
        uVar1 = uVar1 + 1;
        plVar2 = plVar2 + 3;
      } while (uVar1 < *(ulonglong *)(DAT_00001990 + 0x68));
    }
  }
  return DAT_000019b0;
}


// ==== FUN_0000106c @ 0000106c

void FUN_0000106c(uint param_1)

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


// ==== FUN_000010cc @ 000010cc

longlong FUN_000010cc(longlong param_1)

{
  FUN_0000106c((uint)((ulonglong)(param_1 * 0x369e99) / 1000000));
  return param_1;
}


// ==== FUN_00001100 @ 00001100

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_00001100(void)

{
  ushort uVar1;
  
  if (DAT_00001540 != -1) {
    return;
  }
  uVar1 = _DAT_e00f8002 & 0xffe0;
  if (uVar1 != 0x280) {
    if (uVar1 == 0x680) {
      DAT_00001540 = 1;
      return;
    }
    if (uVar1 != 0x9d80) {
      if (uVar1 == 0xa300) {
        DAT_00001540 = 1;
        return;
      }
      DAT_00001540 = 0xff;
      return;
    }
  }
  DAT_00001540 = 2;
  return;
}


// ==== FUN_00001158 @ 00001158

ulonglong FUN_00001158(uint param_1)

{
  undefined *puVar1;
  uint local_res8 [8];
  
  local_res8[0] = param_1;
  puVar1 = (undefined *)FUN_00001100();
  if ((((char)puVar1 != '\x02') && (puVar1 = FUN_0000123c(local_res8), 1 < local_res8[0])) &&
     (puVar1 = FUN_0000123c(local_res8), 0x16 < *(ushort *)(puVar1 + 0x3a))) {
    return CONCAT71((int7)((ulonglong)puVar1 >> 8),1);
  }
  return (ulonglong)puVar1 & 0xffffffffffffff00;
}


// ==== FUN_0000119c @ 0000119c

void FUN_0000119c(uint param_1,undefined1 param_2,undefined8 param_3,undefined4 param_4)

{
  undefined8 uVar1;
  undefined *puVar2;
  uint uVar3;
  uint *puVar4;
  uint local_res10 [4];
  undefined4 local_res20 [2];
  
  local_res10[0] = CONCAT31(local_res10[0]._1_3_,param_2);
  uVar3 = 0;
  local_res20[0] = param_4;
  uVar1 = FUN_00001158(param_1);
  if ((char)uVar1 != '\0') {
    FUN_00000a68(7,1,0,local_res10);
    uVar3 = local_res10[0] >> 0x16 & 1;
    if (uVar3 != 0) {
      FUN_00000d2c(0x301,0,0x400000);
    }
  }
  puVar2 = FUN_0000123c(local_res20);
  puVar4 = (uint *)(((ulonglong)(byte)puVar2[0x1e] | 0xfd00) << 0x10 |
                   (ulonglong)(ushort)(*(short *)(puVar2 + 0x38) + 0x160));
  *puVar4 = *puVar4 | 1;
  if (uVar3 != 0) {
    FUN_00000d80(0x301,0,0x400000);
  }
  return;
}


// ==== FUN_0000123c @ 0000123c

undefined * FUN_0000123c(undefined4 *param_1)

{
  char cVar1;
  undefined *puVar2;
  
  cVar1 = FUN_00001100();
  if (cVar1 == '\x02') {
    *param_1 = 0xf;
    puVar2 = &DAT_00001750;
  }
  else {
    *param_1 = 0x11;
    puVar2 = &DAT_00001550;
  }
  return puVar2;
}


// ==== FUN_00001270 @ 00001270

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

ulonglong FUN_00001270(byte param_1,undefined8 param_2,undefined4 *param_3,byte *param_4,
                      uint param_5)

{
  byte bVar1;
  ulonglong uVar2;
  longlong lVar3;
  longlong lVar4;
  
  if (((param_5 < 0x13) && ((0x7ff0cU >> (param_5 & 0x1f) & 1) != 0)) || (0x13 < (int)param_5)) {
    uVar2 = 0x8000000000000002;
  }
  else if (_DAT_e00f9000 == -1) {
    uVar2 = 0x8000000000000007;
  }
  else {
    lVar4 = 0xfffffff;
    lVar3 = 0xfffffff;
    do {
      if ((_DAT_e00f90d8 & 1) == 0) break;
      lVar3 = lVar3 + -1;
    } while (lVar3 != 0);
    if (lVar3 != 0) {
      _DAT_e00f90d0 = (uint)param_1 << 0x18 | (uint)param_2 & 0xffff;
      *param_4 = 4;
      _DAT_e00f90dc = (undefined4)((ulonglong)param_2 >> 0x10);
      _DAT_e00f90da = 0xf000;
      _DAT_e00f90d4 = *param_3;
      _DAT_e00f90d8 = _DAT_e00f90d8 & 0x7f | 0x1301;
      do {
        if ((_DAT_e00f90d8 & 1) == 0) break;
        lVar4 = lVar4 + -1;
      } while (lVar4 != 0);
      if (lVar4 != 0) {
        bVar1 = (byte)_DAT_e00f90d8 >> 1 & 3;
        *param_4 = bVar1;
        return -(ulonglong)(bVar1 != 0) & 0x8000000000000007;
      }
    }
    uVar2 = 0x8000000000000012;
  }
  return uVar2;
}


