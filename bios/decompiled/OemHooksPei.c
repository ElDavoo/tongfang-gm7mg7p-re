// OemHooksPei.efi: Ghidra x86:LE:32:default decompile, unedited
// ==== entry @ fff81031

/* WARNING: Removing unreachable block (ram,0xfff81157) */
/* WARNING: Type propagation algorithm not settling */
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

longlong entry(undefined4 param_1,int *param_2)

{
  int *piVar1;
  int local_808 [5];
  undefined1 *local_7f4;
  undefined4 local_7f0;
  undefined4 *local_7ec;
  undefined1 local_7e8 [2];
  int iStack_7e6;
  undefined1 local_7e0 [1836];
  char local_b4;
  
  local_7f4 = local_7e8;
  local_7f0 = 0x7d8;
  local_808[1] = 0xec87d643;
  local_808[2] = 0x4bb5eba4;
  local_808[3] = 0x3e3fe5a1;
  local_808[4] = 0xa90db236;
  InterruptDescriptorTableRegister();
  piVar1 = local_808;
  (**(code **)(**(int **)(iStack_7e6 + -4) + 0x28))(*(int **)(iStack_7e6 + -4),piVar1);
  if (((local_808[0] != 0x11) && (local_808[0] != 0x20)) && (local_808[0] != 0x12)) {
    piVar1 = (int *)0x78;
    FUN_fff818cc(0x50,0x78);
  }
  FUN_fff81685(piVar1,piVar1);
  FUN_fff818cc(0x56,0);
  FUN_fff81732();
  (**(code **)(*param_2 + 0x20))(param_2,&DAT_fff81d1c,0,0,&local_7ec);
  (*(code *)*local_7ec)(local_7ec,u_Setup_fff820fc,local_808 + 1,0,&local_7f0,local_7e0);
  if (local_b4 == '\x01') {
    FUN_fff8134d();
  }
  if (local_b4 == '\x02') {
    FUN_fff8134d();
  }
  _DAT_fd6e0754 = _DAT_fd6e0754 & 0xffffc3ff;
  _DAT_fd6e0750 = _DAT_fd6e0750 & 0xfffffffe;
  out(0x70,0xf0);
  out(0x71,1);
  return (ulonglong)CONCAT22((short)(_DAT_fd6e0750 >> 0x10),0x71) << 0x20;
}


// ==== FUN_fff8117f @ fff8117f

uint __regparm3 FUN_fff8117f(undefined4 param_1,uint param_2,uint param_3)

{
  int iVar1;
  uint uVar2;
  uint uVar3;
  
  iVar1 = FUN_fff81add();
  uVar2 = FUN_fff815dd();
  if (((uVar2 <= param_3) && (uVar2 = FUN_fff815c2(), param_3 <= uVar2)) &&
     ((param_3 & 0xff) < param_3)) {
    uVar3 = *(ushort *)((param_3 & 0xff) * 0x1e + 0x1c + iVar1) - 1;
    uVar2 = uVar3 >> 5;
    if (param_2 <= uVar2) {
      return CONCAT31((uint3)(uVar3 >> 0xd),1);
    }
  }
  return uVar2 & 0xffffff00;
}


// ==== FUN_fff811cc @ fff811cc

void __regparm3
FUN_fff811cc(undefined4 param_1,uint param_2,int param_3,short param_4,undefined4 *param_5)

{
  int iVar1;
  byte *pbVar2;
  short sVar3;
  
  param_2 = param_2 & 0xff;
  iVar1 = FUN_fff81add();
  switch(param_3) {
  case 0:
    pbVar2 = (byte *)(param_2 * 0x1e + iVar1);
    sVar3 = *(short *)(pbVar2 + 4);
    break;
  case 1:
    pbVar2 = (byte *)(param_2 * 0x1e + iVar1);
    sVar3 = *(short *)(pbVar2 + 0xc);
    break;
  case 2:
    pbVar2 = (byte *)(param_2 * 0x1e + iVar1);
    sVar3 = *(short *)(pbVar2 + 10);
    break;
  case 3:
    pbVar2 = (byte *)(param_2 * 0x1e + iVar1);
    sVar3 = *(short *)(pbVar2 + 0x10);
    break;
  case 4:
    pbVar2 = (byte *)(param_2 * 0x1e + iVar1);
    sVar3 = *(short *)(pbVar2 + 0xe);
    break;
  case 5:
    pbVar2 = (byte *)(param_2 * 0x1e + iVar1);
    sVar3 = *(short *)(pbVar2 + 0x14);
    break;
  case 6:
    pbVar2 = (byte *)(param_2 * 0x1e + iVar1);
    sVar3 = *(short *)(pbVar2 + 0x16);
    break;
  case 7:
    pbVar2 = (byte *)(param_2 * 0x1e + iVar1);
    sVar3 = *(short *)(pbVar2 + 0x18);
    break;
  default:
    goto switchD_fff811ea_default;
  }
  if (sVar3 == -1) {
switchD_fff811ea_default:
    *param_5 = 0;
  }
  else {
    if ((param_3 == 6) || (param_3 == 7)) {
      param_4 = param_4 * 8;
    }
    else {
      param_4 = param_4 * 4;
    }
    *param_5 = *(undefined4 *)((*pbVar2 | 0xfffffd00) << 0x10 | (uint)(ushort)(sVar3 + param_4));
  }
  return;
}


// ==== FUN_fff812b0 @ fff812b0

undefined4 __regparm3 FUN_fff812b0(undefined4 param_1,uint param_2,int param_3,int param_4)

{
  ushort uVar1;
  int iVar2;
  undefined4 uVar3;
  undefined4 local_c;
  undefined1 local_5;
  
  local_c = 0;
  iVar2 = FUN_fff81add();
  if (param_3 == 6) {
    uVar1 = *(ushort *)((param_2 & 0xff) * 0x1e + iVar2 + 0x16);
    FUN_fff813f1(&local_c);
  }
  else {
    if (param_3 != 7) {
      return 0x80000003;
    }
    uVar1 = *(ushort *)((param_2 & 0xff) * 0x1e + iVar2 + 0x18);
    FUN_fff8146c(&local_c);
  }
  if (uVar1 == 0xffff) {
    return 0x80000003;
  }
  uVar3 = FUN_fff81b00((uint)uVar1 + param_4 * 8,0,&local_5,0x13);
  return uVar3;
}


// ==== FUN_fff8134d @ fff8134d

undefined4 __regparm3 FUN_fff8134d(undefined4 param_1,undefined4 param_2)

{
  char cVar1;
  undefined4 uVar2;
  undefined4 extraout_ECX;
  
  cVar1 = FUN_fff819a6();
  if (cVar1 == '\0') {
    uVar2 = 0x80000002;
  }
  else {
    cVar1 = FUN_fff8198f();
    if (cVar1 == '\0') {
      uVar2 = 0x80000003;
    }
    else {
      FUN_fff819fe(extraout_ECX,param_2);
      uVar2 = 0;
    }
  }
  return uVar2;
}


// ==== FUN_fff81387 @ fff81387

undefined4 __regparm3 FUN_fff81387(undefined4 param_1,uint *param_2,uint param_3)

{
  char cVar1;
  undefined4 uVar2;
  int iVar3;
  sbyte sVar4;
  int iVar5;
  
  cVar1 = FUN_fff819a6();
  if (cVar1 == '\0') {
    uVar2 = 0x80000002;
  }
  else {
    iVar3 = FUN_fff81add();
    iVar5 = (param_3 >> 0x10 & 0xff) * 0x1e;
    sVar4 = (sbyte)((param_3 & 7) << 2);
    uVar2 = 0;
    *param_2 = (3 << sVar4 &
               *(uint *)((*(byte *)(iVar5 + iVar3) | 0xfffffd00) << 0x10 |
                        (uint)*(ushort *)(iVar5 + 2 + iVar3) + ((param_3 & 0xffff) >> 3) * 4 &
                        0xffff)) >> sVar4;
  }
  return uVar2;
}


// ==== FUN_fff813f1 @ fff813f1

undefined4 __regparm2 FUN_fff813f1(undefined4 param_1,undefined4 param_2,undefined4 param_3)

{
  char cVar1;
  undefined4 uVar2;
  
  cVar1 = FUN_fff8117f();
  if (cVar1 == '\0') {
    uVar2 = 0x80000002;
  }
  else {
    FUN_fff811cc(param_2,param_3);
    uVar2 = 0;
  }
  return uVar2;
}


// ==== FUN_fff8141d @ fff8141d

undefined4 __regparm3 FUN_fff8141d(undefined4 param_1,uint *param_2,uint param_3)

{
  char cVar1;
  undefined4 uVar2;
  uint local_8;
  
  local_8 = param_3;
  cVar1 = FUN_fff819a6();
  if (cVar1 == '\0') {
    uVar2 = 0x80000002;
  }
  else {
    FUN_fff811cc((param_3 & 0xffff) >> 5,&local_8);
    *param_2 = local_8 >> ((byte)param_3 & 0x1f) & 1;
    uVar2 = 0;
  }
  return uVar2;
}


// ==== FUN_fff8146c @ fff8146c

undefined4 __regparm2 FUN_fff8146c(undefined4 param_1,undefined4 param_2,undefined4 param_3)

{
  char cVar1;
  undefined4 uVar2;
  
  cVar1 = FUN_fff8117f();
  if (cVar1 == '\0') {
    uVar2 = 0x80000002;
  }
  else {
    FUN_fff811cc(param_2,param_3);
    uVar2 = 0;
  }
  return uVar2;
}


// ==== FUN_fff81498 @ fff81498

undefined4 __regparm3 FUN_fff81498(undefined4 param_1,uint *param_2,uint param_3)

{
  char cVar1;
  undefined4 uVar2;
  uint local_8;
  
  local_8 = param_3;
  cVar1 = FUN_fff819a6();
  if (cVar1 == '\0') {
    uVar2 = 0x80000002;
  }
  else {
    FUN_fff811cc((param_3 & 0xffff) >> 5,&local_8);
    *param_2 = local_8 >> ((byte)param_3 & 0x1f) & 1;
    uVar2 = 0;
  }
  return uVar2;
}


// ==== FUN_fff814e7 @ fff814e7

undefined4 __regparm2 FUN_fff814e7(undefined4 param_1,undefined4 param_2,uint param_3)

{
  char cVar1;
  undefined4 uVar2;
  
  cVar1 = FUN_fff8117f();
  if (cVar1 == '\0') {
    uVar2 = 0x80000002;
  }
  else {
    uVar2 = FUN_fff812b0(param_2,~param_3,0);
  }
  return uVar2;
}


// ==== FUN_fff81517 @ fff81517

undefined4 __regparm2 FUN_fff81517(undefined4 param_1,undefined4 param_2,undefined4 param_3)

{
  char cVar1;
  undefined4 uVar2;
  
  cVar1 = FUN_fff8117f();
  if (cVar1 == '\0') {
    uVar2 = 0x80000002;
  }
  else {
    uVar2 = FUN_fff812b0(param_2,0xffffffff,param_3);
  }
  return uVar2;
}


// ==== FUN_fff81544 @ fff81544

void FUN_fff81544(void)

{
  byte in_CL;
  
  FUN_fff81517(1 << (in_CL & 0x1f));
  return;
}


// ==== FUN_fff81565 @ fff81565

undefined4 __regparm2 FUN_fff81565(undefined4 param_1,undefined4 param_2,uint param_3)

{
  char cVar1;
  undefined4 uVar2;
  
  cVar1 = FUN_fff8117f();
  if (cVar1 == '\0') {
    uVar2 = 0x80000002;
  }
  else {
    uVar2 = FUN_fff812b0(param_2,~param_3,0);
  }
  return uVar2;
}


// ==== FUN_fff81595 @ fff81595

undefined4 __regparm2 FUN_fff81595(undefined4 param_1,undefined4 param_2,undefined4 param_3)

{
  char cVar1;
  undefined4 uVar2;
  
  cVar1 = FUN_fff8117f();
  if (cVar1 == '\0') {
    uVar2 = 0x80000002;
  }
  else {
    uVar2 = FUN_fff812b0(param_2,0xffffffff,param_3);
  }
  return uVar2;
}


// ==== FUN_fff815c2 @ fff815c2

void FUN_fff815c2(void)

{
  undefined4 in_ECX;
  
  FUN_fff81add(in_ECX);
  FUN_fff815dd();
  return;
}


// ==== FUN_fff815dd @ fff815dd

uint FUN_fff815dd(void)

{
  char cVar1;
  uint in_ECX;
  
  cVar1 = FUN_fff81640();
  return ((cVar1 != '\0') + 3) * 0x100 | in_ECX;
}


// ==== FUN_fff815f6 @ fff815f6

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_fff815f6(void)

{
  ushort uVar1;
  
  if (DAT_fff81d2c != -1) {
    return;
  }
  uVar1 = _DAT_e00f8002 & 0xffe0;
  if (uVar1 != 0x280) {
    if (uVar1 == 0x680) {
      DAT_fff81d2c = 1;
      return;
    }
    if (uVar1 != 0x9d80) {
      DAT_fff81d2c = ((uVar1 == 0xa300) - 1U & 0xfe) + 1;
      return;
    }
  }
  DAT_fff81d2c = 2;
  return;
}


// ==== FUN_fff81640 @ fff81640

bool FUN_fff81640(void)

{
  char cVar1;
  
  cVar1 = FUN_fff815f6();
  return cVar1 == '\x02';
}


// ==== FUN_fff8164f @ fff8164f

bool FUN_fff8164f(void)

{
  char cVar1;
  
  cVar1 = FUN_fff815f6();
  return cVar1 == '\x01';
}


// ==== FUN_fff8165e @ fff8165e

undefined8 FUN_fff8165e(uint param_1,uint param_2)

{
  return CONCAT44(param_2 >> 0x10,param_1 >> 0x10 | param_2 << 0x10);
}


// ==== FUN_fff81685 @ fff81685

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

undefined4 FUN_fff81685(void)

{
  FUN_fff81c65();
  FUN_fff81cbe();
  FUN_fff81c65();
  FUN_fff81cbe();
  _DAT_fd882774 = _DAT_fd882774 | 0x800;
  return 0;
}


// ==== FUN_fff81732 @ fff81732

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

undefined4 FUN_fff81732(void)

{
  undefined4 uVar1;
  char cVar2;
  undefined4 in_ECX;
  undefined4 uVar3;
  undefined4 extraout_EDX;
  
  cVar2 = FUN_fff81c08(in_ECX);
  uVar3 = 0xfe410001;
  if (((cVar2 == '\0') || (uVar1 = _DAT_fd882740, (_DAT_e00f80a8 & 0xffff0000) != 0xfe410000)) &&
     (cVar2 = FUN_fff81c26(), uVar3 = extraout_EDX, uVar1 = extraout_EDX, cVar2 != '\0')) {
    return 0x80000003;
  }
  _DAT_fd882740 = uVar1;
  _DAT_e00f8098 = uVar3;
  return 0;
}


// ==== FUN_fff81783 @ fff81783

undefined6 __regparm3 FUN_fff81783(undefined4 param_1,undefined1 param_2)

{
  byte bVar1;
  undefined4 uVar2;
  uint uVar3;
  
  uVar3 = 0;
  bVar1 = in(0x66);
  if ((bVar1 & 2) != 0) {
    do {
      if (0x1ffff < uVar3) goto LAB_fff817b5;
      FUN_fff81948();
      bVar1 = in(0x66);
      uVar3 = uVar3 + 1;
    } while ((bVar1 & 2) != 0);
    if (0x1ffff < uVar3) {
LAB_fff817b5:
      uVar2 = 0x80000007;
      goto LAB_fff817c4;
    }
  }
  out(0x66,param_2);
  uVar2 = 0;
LAB_fff817c4:
  return CONCAT24(0x66,uVar2);
}


// ==== FUN_fff817ca @ fff817ca

undefined6 __regparm3 FUN_fff817ca(undefined4 param_1,undefined1 param_2)

{
  byte bVar1;
  undefined2 uVar2;
  undefined4 uVar3;
  uint uVar4;
  
  uVar4 = 0;
  uVar2 = 0x66;
  bVar1 = in(0x66);
  if ((bVar1 & 2) != 0) {
    do {
      if (0x1ffff < uVar4) goto LAB_fff817fc;
      FUN_fff81948();
      bVar1 = in(0x66);
      uVar4 = uVar4 + 1;
    } while ((bVar1 & 2) != 0);
    if (0x1ffff < uVar4) {
LAB_fff817fc:
      uVar3 = 0x80000007;
      goto LAB_fff8180e;
    }
  }
  uVar2 = 0x62;
  out(0x62,param_2);
  uVar3 = 0;
LAB_fff8180e:
  return CONCAT24(uVar2,uVar3);
}


// ==== FUN_fff81814 @ fff81814

undefined4 FUN_fff81814(void)

{
  byte bVar1;
  undefined1 uVar2;
  uint uVar3;
  
  uVar3 = 0;
  bVar1 = in(0x66);
  if ((bVar1 & 1) != 0) {
    do {
      if (0x1ffff < uVar3) {
        return 0x80000007;
      }
      uVar2 = in(0x62);
      out(0x80,uVar2);
      FUN_fff81948();
      bVar1 = in(0x66);
      uVar3 = uVar3 + 1;
    } while ((bVar1 & 1) != 0);
    if (0x1ffff < uVar3) {
      return 0x80000007;
    }
  }
  return 0;
}


// ==== FUN_fff8185e @ fff8185e

undefined4 FUN_fff8185e(void)

{
  byte bVar1;
  uint uVar2;
  
  uVar2 = 0;
  bVar1 = in(0x66);
  if ((bVar1 & 2) != 0) {
    do {
      if (0x1ffff < uVar2) {
        return 0x80000007;
      }
      FUN_fff81948();
      bVar1 = in(0x66);
      uVar2 = uVar2 + 1;
    } while ((bVar1 & 2) != 0);
    if (0x1ffff < uVar2) {
      return 0x80000007;
    }
  }
  return 0;
}


// ==== FUN_fff81899 @ fff81899

int FUN_fff81899(void)

{
  int iVar1;
  
  iVar1 = FUN_fff8185e();
  if (-1 < iVar1) {
    FUN_fff81814();
    FUN_fff81783();
    FUN_fff8185e();
    FUN_fff817ca();
    FUN_fff81814();
  }
  return iVar1;
}


// ==== FUN_fff818cc @ fff818cc

int FUN_fff818cc(undefined4 param_1,undefined4 param_2)

{
  int iVar1;
  undefined4 in_ECX;
  
  iVar1 = FUN_fff81899(7,in_ECX);
  if (-1 < iVar1) {
    iVar1 = FUN_fff81899(param_1,in_ECX);
    if (-1 < iVar1) {
      iVar1 = FUN_fff81899(param_2,in_ECX);
      if (-1 < iVar1) {
        iVar1 = 0;
      }
    }
  }
  return iVar1;
}


// ==== FUN_fff818ff @ fff818ff

void FUN_fff818ff(void)

{
  uint uVar1;
  int iVar2;
  uint in_ECX;
  int iVar3;
  uint uVar4;
  uint uVar5;
  bool bVar6;
  
  uVar5 = in_ECX & 0x3fffff;
  uVar4 = in_ECX >> 0x16;
  do {
    uVar1 = in(0x1808);
    iVar3 = (uVar1 & 0xffffff) + uVar5;
    uVar5 = 0x400000;
    do {
      iVar2 = in(0x1808);
    } while ((iVar3 - iVar2 & 0x800000U) == 0);
    bVar6 = uVar4 != 0;
    uVar4 = uVar4 - 1;
  } while (bVar6);
  return;
}


// ==== FUN_fff81948 @ fff81948

undefined4 FUN_fff81948(void)

{
  undefined4 in_ECX;
  
  FUN_fff818ff();
  return in_ECX;
}


// ==== FUN_fff8198f @ fff8198f

bool FUN_fff8198f(void)

{
  int in_ECX;
  
  FUN_fff81387();
  return in_ECX == 0;
}


// ==== FUN_fff819a6 @ fff819a6

uint FUN_fff819a6(void)

{
  char cVar1;
  uint uVar2;
  int iVar3;
  uint in_ECX;
  uint uVar4;
  
  cVar1 = FUN_fff81640();
  uVar2 = in_ECX >> 0x18;
  if (uVar2 == (cVar1 != '\0') + 3) {
    FUN_fff81add();
    uVar2 = in_ECX >> 0x10;
    uVar4 = uVar2 & 0xff;
    if (uVar4 < in_ECX) {
      iVar3 = FUN_fff81add();
      uVar2 = in_ECX & 0xffff;
      if (uVar2 < *(ushort *)(uVar4 * 0x1e + 0x1c + iVar3)) {
        return CONCAT31((int3)(uVar2 >> 8),1);
      }
    }
  }
  return uVar2 & 0xffffff00;
}


// ==== FUN_fff819fe @ fff819fe

/* WARNING: Removing unreachable block (ram,0xfff81ab2) */
/* WARNING: Removing unreachable block (ram,0xfff81a2b) */
/* WARNING: Removing unreachable block (ram,0xfff81a56) */
/* WARNING: Removing unreachable block (ram,0xfff81abf) */

void __regparm3
FUN_fff819fe(undefined4 param_1,undefined4 param_2,uint param_3,undefined4 param_4,uint param_5)

{
  int iVar1;
  uint *puVar2;
  int iVar3;
  
  if ((param_5 & 0xfffffffe) != 0) {
    FUN_fff8141d();
  }
  FUN_fff81498();
  iVar1 = FUN_fff81add();
  iVar3 = (param_3 >> 0x10 & 0xff) * 0x1e;
  puVar2 = (uint *)((uint)(ushort)((short)(param_3 << 4) + *(short *)(iVar3 + 0x1a + iVar1)) |
                   (*(byte *)(iVar3 + iVar1) | 0xfffffd00) << 0x10);
  *puVar2 = *puVar2 & 0xfffffffe | param_5;
  return;
}


// ==== FUN_fff81add @ fff81add

undefined * FUN_fff81add(void)

{
  char cVar1;
  undefined4 *extraout_EDX;
  
  cVar1 = FUN_fff81640();
  if (cVar1 != '\0') {
    *extraout_EDX = 0xf;
    return &DAT_fff81f34;
  }
  *extraout_EDX = 0x11;
  return &DAT_fff81d34;
}


// ==== FUN_fff81b00 @ fff81b00

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

uint __regparm3
FUN_fff81b00(undefined4 param_1,undefined4 *param_2,int param_3,uint param_4,undefined4 param_5,
            byte *param_6,int param_7)

{
  byte bVar1;
  uint uVar2;
  int iVar3;
  int iVar4;
  
  if ((param_7 < 2) || ((3 < param_7 && ((param_7 < 8 || (param_7 == 0x13)))))) {
    if (_DAT_e00f9000 == -1) {
      uVar2 = 0x80000007;
    }
    else {
      iVar4 = 0xfffffff;
      iVar3 = 0xfffffff;
      do {
        if ((_DAT_e00f90d8 & 1) == 0) break;
        iVar3 = iVar3 + -1;
      } while (iVar3 != 0);
      if (iVar3 != 0) {
        _DAT_e00f90d0 = param_3 << 0x18 | param_4 & 0xffff;
        *param_6 = 4;
        _DAT_e00f90dc = FUN_fff8165e(param_4,param_5);
        _DAT_e00f90da = 0xf000;
        _DAT_e00f90d4 = *param_2;
        _DAT_e00f90d8 = _DAT_e00f90d8 & 0x7f | 0x1301;
        do {
          if ((_DAT_e00f90d8 & 1) == 0) break;
          iVar4 = iVar4 + -1;
        } while (iVar4 != 0);
        if (iVar4 != 0) {
          bVar1 = (byte)_DAT_e00f90d8 >> 1 & 3;
          *param_6 = bVar1;
          return -(uint)(bVar1 != 0) & 0x80000007;
        }
      }
      uVar2 = 0x80000012;
    }
  }
  else {
    uVar2 = 0x80000002;
  }
  return uVar2;
}


// ==== FUN_fff81c08 @ fff81c08

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

undefined4 FUN_fff81c08(void)

{
  char cVar1;
  
  cVar1 = FUN_fff8164f();
  if ((cVar1 != '\0') && ((_DAT_fd72c210 & 0x1000) != 0)) {
    return 1;
  }
  return 0;
}


// ==== FUN_fff81c26 @ fff81c26

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

uint FUN_fff81c26(void)

{
  char cVar1;
  
  cVar1 = FUN_fff8164f();
  if (cVar1 != '\0') {
    return _DAT_fd8820d8 >> 0x17 & 1;
  }
  return _DAT_fd882234 >> 0x1f;
}


// ==== FUN_fff81c65 @ fff81c65

undefined8 FUN_fff81c65(void)

{
  undefined2 uVar1;
  undefined4 uVar2;
  uint in_ECX;
  
  uVar2 = in(0xcf8);
  out(0xcf8,in_ECX >> 4 & 0xffff00 | in_ECX & 0xfc | 0x80000000);
  uVar1 = in((short)((in_ECX & 2) + 0xcfc));
  out(0xcf8,uVar2);
  return CONCAT44(0xcf8,CONCAT22((short)((uint)uVar2 >> 0x10),uVar1));
}


// ==== FUN_fff81cbe @ fff81cbe

undefined8 __regparm3 FUN_fff81cbe(undefined4 param_1,undefined2 param_2,uint param_3)

{
  undefined4 uVar1;
  
  uVar1 = in(0xcf8);
  out(0xcf8,param_3 >> 4 & 0xffff00 | param_3 & 0xfc | 0x80000000);
  out((short)((param_3 & 2) + 0xcfc),param_2);
  out(0xcf8,uVar1);
  return CONCAT44(0xcf8,CONCAT22((short)((uint)uVar1 >> 0x10),param_2));
}


