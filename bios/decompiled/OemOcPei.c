// OemOcPei.efi: Ghidra x86:LE:32:default decompile, unedited
// ==== entry @ fff823b9

undefined4 entry(undefined4 param_1,int *param_2)

{
  int *piVar1;
  
  piVar1 = param_2;
  (**(code **)(*param_2 + 0x24))(param_2,&DAT_fff82afc);
  (**(code **)(*piVar1 + 0x24))(piVar1,&DAT_fff82b08);
  FUN_fff8254f();
  (**(code **)(*piVar1 + 0x20))(piVar1,&DAT_fff82acc,0,0,&param_2);
  (*(code *)param_2[1])(piVar1,param_2,1000000);
  return 0;
}


// ==== FUN_fff8254f @ fff8254f

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

undefined4 FUN_fff8254f(void)

{
  FUN_fff82997();
  FUN_fff829f0();
  FUN_fff82997();
  FUN_fff829f0();
  _DAT_fd882774 = _DAT_fd882774 | 0x800;
  return 0;
}


// ==== FUN_fff825fc @ fff825fc

undefined6 __regparm3 FUN_fff825fc(undefined4 param_1,undefined1 param_2,char param_3)

{
  short sVar1;
  byte bVar2;
  undefined4 uVar3;
  uint uVar4;
  
  uVar4 = 0;
  sVar1 = (ushort)(param_3 != '`') * 2 + 100;
  bVar2 = in(sVar1);
  if ((bVar2 & 2) != 0) {
    do {
      if (0x1ffff < uVar4) goto LAB_fff82640;
      FUN_fff828bd();
      bVar2 = in(sVar1);
      uVar4 = uVar4 + 1;
    } while ((bVar2 & 2) != 0);
    if (0x1ffff < uVar4) {
LAB_fff82640:
      uVar3 = 0x80000007;
      goto LAB_fff8264f;
    }
  }
  out(sVar1,param_2);
  uVar3 = 0;
LAB_fff8264f:
  return CONCAT24(sVar1,uVar3);
}


// ==== FUN_fff82657 @ fff82657

undefined8 __regparm3 FUN_fff82657(undefined4 param_1,undefined4 param_2,char param_3)

{
  short sVar1;
  byte bVar2;
  undefined4 uVar3;
  int iVar4;
  undefined2 extraout_var;
  uint uVar5;
  
  uVar5 = 0;
  sVar1 = (ushort)(param_3 != '`') * 2 + 100;
  iVar4 = CONCAT22((short)((uint)param_2 >> 0x10),sVar1);
  bVar2 = in(sVar1);
  if ((bVar2 & 2) != 0) {
    do {
      if (0x1ffff < uVar5) goto LAB_fff8269d;
      FUN_fff828bd();
      iVar4 = CONCAT22(extraout_var,sVar1);
      bVar2 = in(sVar1);
      uVar5 = uVar5 + 1;
    } while ((bVar2 & 2) != 0);
    if (0x1ffff < uVar5) {
LAB_fff8269d:
      uVar3 = 0x80000007;
      goto LAB_fff826b8;
    }
  }
  iVar4 = (uint)(param_3 != '`') * 2 + 0x60;
  out((short)iVar4,(char)param_2);
  uVar3 = 0;
LAB_fff826b8:
  return CONCAT44(iVar4,uVar3);
}


// ==== FUN_fff826c0 @ fff826c0

undefined4 FUN_fff826c0(void)

{
  short sVar1;
  byte bVar2;
  undefined1 uVar3;
  char in_CL;
  uint uVar4;
  
  uVar4 = 0;
  sVar1 = (ushort)(in_CL != '`') * 2 + 100;
  bVar2 = in(sVar1);
  if ((bVar2 & 1) != 0) {
    do {
      if (0x1ffff < uVar4) {
        return 0x80000007;
      }
      uVar3 = in((ushort)(in_CL != '`') * 2 + 0x60);
      out(0x80,uVar3);
      FUN_fff828bd();
      bVar2 = in(sVar1);
      uVar4 = uVar4 + 1;
    } while ((bVar2 & 1) != 0);
    if (0x1ffff < uVar4) {
      return 0x80000007;
    }
  }
  return 0;
}


// ==== FUN_fff8272d @ fff8272d

undefined4 FUN_fff8272d(void)

{
  short sVar1;
  byte bVar2;
  char in_CL;
  uint uVar3;
  
  uVar3 = 0;
  sVar1 = (ushort)(in_CL != '`') * 2 + 100;
  bVar2 = in(sVar1);
  if ((bVar2 & 2) != 0) {
    do {
      if (0x1ffff < uVar3) {
        return 0x80000007;
      }
      FUN_fff828bd();
      bVar2 = in(sVar1);
      uVar3 = uVar3 + 1;
    } while ((bVar2 & 2) != 0);
    if (0x1ffff < uVar3) {
      return 0x80000007;
    }
  }
  return 0;
}


// ==== FUN_fff8277f @ fff8277f

int FUN_fff8277f(void)

{
  int iVar1;
  
  iVar1 = FUN_fff8272d();
  if (-1 < iVar1) {
    FUN_fff826c0();
    FUN_fff825fc();
    FUN_fff8272d();
    FUN_fff82657();
    FUN_fff826c0();
  }
  return iVar1;
}


// ==== FUN_fff827be @ fff827be

int FUN_fff827be(undefined4 param_1,undefined4 param_2)

{
  int iVar1;
  
  iVar1 = FUN_fff8277f(7);
  if (-1 < iVar1) {
    iVar1 = FUN_fff8277f(0x41);
    if (-1 < iVar1) {
      iVar1 = FUN_fff8277f(param_2);
      if (-1 < iVar1) {
        iVar1 = 0;
      }
    }
  }
  return iVar1;
}


// ==== FUN_fff827f3 @ fff827f3

int FUN_fff827f3(undefined4 param_1,undefined1 *param_2)

{
  byte bVar1;
  undefined1 uVar2;
  int iVar3;
  uint uVar4;
  
  uVar4 = 0;
  iVar3 = FUN_fff8277f(7);
  if (((-1 < iVar3) && (iVar3 = FUN_fff8277f(0x41), -1 < iVar3)) &&
     (iVar3 = FUN_fff825fc(), -1 < iVar3)) {
    bVar1 = in(0x66);
    if ((bVar1 & 1) == 0) {
      do {
        if (0x1ffff < uVar4) {
          return -0x7ffffff9;
        }
        FUN_fff828bd();
        bVar1 = in(0x66);
        uVar4 = uVar4 + 1;
      } while ((bVar1 & 1) == 0);
      if (0x1ffff < uVar4) {
        return -0x7ffffff9;
      }
    }
    uVar2 = in(0x62);
    *param_2 = uVar2;
    iVar3 = 0;
  }
  return iVar3;
}


// ==== FUN_fff82874 @ fff82874

void FUN_fff82874(void)

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


// ==== FUN_fff828bd @ fff828bd

undefined4 FUN_fff828bd(void)

{
  undefined4 in_ECX;
  
  FUN_fff82874();
  return in_ECX;
}


// ==== FUN_fff82904 @ fff82904

undefined4 FUN_fff82904(int *param_1)

{
  ushort uVar1;
  ushort uVar2;
  char cVar3;
  int in_ECX;
  ushort uVar4;
  int iVar5;
  int iVar6;
  
  uVar1 = *(ushort *)(in_ECX + 0x1e);
  iVar5 = 0;
  uVar4 = 0;
  if (uVar1 != 0) {
    uVar2 = *(ushort *)(in_ECX + 2);
    do {
      if ((uint)uVar2 < iVar5 + 0x24U) {
        return 0x8000000e;
      }
      iVar6 = in_ECX + 0x24 + iVar5;
      cVar3 = FUN_fff82a4e();
      if (cVar3 != '\0') {
        *param_1 = iVar6;
        return 0;
      }
      iVar5 = iVar5 + (uint)*(ushort *)(iVar6 + 2);
      uVar4 = uVar4 + 1;
    } while (uVar4 < uVar1);
  }
  return 0x8000000e;
}


// ==== FUN_fff82997 @ fff82997

undefined8 FUN_fff82997(void)

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


// ==== FUN_fff829f0 @ fff829f0

undefined8 __regparm3 FUN_fff829f0(undefined4 param_1,undefined2 param_2,uint param_3)

{
  undefined4 uVar1;
  
  uVar1 = in(0xcf8);
  out(0xcf8,param_3 >> 4 & 0xffff00 | param_3 & 0xfc | 0x80000000);
  out((short)((param_3 & 2) + 0xcfc),param_2);
  out(0xcf8,uVar1);
  return CONCAT44(0xcf8,CONCAT22((short)((uint)uVar1 >> 0x10),param_2));
}


// ==== FUN_fff82a4e @ fff82a4e

uint __regparm3 FUN_fff82a4e(undefined4 param_1,uint *param_2,uint *param_3)

{
  uint uVar1;
  
  uVar1 = *param_3;
  if ((((uVar1 == *param_2) && (uVar1 = param_3[1], uVar1 == param_2[1])) &&
      (uVar1 = param_3[2], uVar1 == param_2[2])) && (uVar1 = param_3[3], uVar1 == param_2[3])) {
    return CONCAT31((int3)(uVar1 >> 8),1);
  }
  return uVar1 & 0xffffff00;
}


