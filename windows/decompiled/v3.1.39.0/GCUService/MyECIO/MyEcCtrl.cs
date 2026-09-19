using System;
using System.Collections;
using Define;
using Utility;

namespace MyECIO;

public class MyEcCtrl
{
	private static readonly MyEcCtrl EcCtrl = new MyEcCtrl();

	private AcpiCtrl AcpiModel;

	public static MyEcCtrl Instance => EcCtrl;

	public MyEcCtrl()
	{
		AcpiModel = AcpiCtrl.Instance;
	}

	public void LoadDrv()
	{
	}

	public void UnloadDrv()
	{
	}

	public void Read(string ReadName, ushort Addr, ref byte Data)
	{
		AcpiModel?.Read(ReadName, Addr, ref Data);
	}

	public void Write(string ReadName, ushort Addr, byte Data)
	{
		AcpiModel?.Write(ReadName, Addr, Data);
	}

	public bool IsChinaMode()
	{
		byte Data = 0;
		Read(GetType().Name, 1894, ref Data);
		if (Convert.ToInt32(new BitArray(new byte[1] { Data })[4]) != 1)
		{
			return false;
		}
		return true;
	}

	public void ReadPciDword(byte Bus, byte Dev, byte Func, uint Offset, ref uint pData)
	{
		AcpiModel?.ReadPciDword(Bus, Dev, Func, Offset, ref pData);
	}

	public int GetProjectIdFromEC()
	{
		byte Data = 0;
		Read(GetType().Name, 1856, ref Data);
		return (int)(Convert.ToUInt64(Data) & 0xFF);
	}

	public int isSupportRGBLBFromEC()
	{
		byte Data = 0;
		Read(GetType().Name, 1934, ref Data);
		if ((byte)(Convert.ToUInt64(Data) & 0x10) == 16)
		{
			return 1;
		}
		return 0;
	}

	public bool IsSuportRamFan1p5()
	{
		byte Data = 0;
		Read(GetType().Name, 1934, ref Data);
		if (UtilityExtensions.GetBitFromByte(Data, 6) != 1)
		{
			return false;
		}
		return true;
	}

	public int GetTurboModeSupport()
	{
		byte Data = 0;
		EcCtrl.Read(GetType().Name, 1183, ref Data);
		if (UtilityExtensions.GetBitFromByte(Data, 1) != 1)
		{
			return 0;
		}
		return 1;
	}

	public bool GetTypeCAdaptorPrioritySupport()
	{
		byte Data = 0;
		EcCtrl.Read(GetType().Name, 1858, ref Data);
		if (UtilityExtensions.GetBitFromByte(Data, 5) != 1)
		{
			return false;
		}
		return true;
	}

	public void Set_APExistToEC(bool bExist)
	{
		byte Data = 0;
		Read(GetType().Name, 1857, ref Data);
		byte b = (byte)Convert.ToUInt64(Data);
		b = ((!bExist) ? ((byte)(b & 0xFE)) : ((byte)(b | 1)));
		Write(GetType().Name, 1857, b);
	}

	public BIOS_PROJECT_ID GetBiosProjctID()
	{
		BIOS_PROJECT_ID result = BIOS_PROJECT_ID.NA;
		byte Data = 0;
		byte b = 15;
		byte b2 = 0;
		AcpiModel.Read(GetType().Name, 1868, ref Data);
		switch ((byte)(Data & b))
		{
		case 0:
			result = BIOS_PROJECT_ID.IDR;
			break;
		case 1:
			result = BIOS_PROJECT_ID.IDX;
			break;
		case 2:
			result = BIOS_PROJECT_ID.IDV;
			break;
		case 3:
			result = BIOS_PROJECT_ID.IDO;
			break;
		case 4:
			result = BIOS_PROJECT_ID.IDP;
			break;
		case 5:
			result = BIOS_PROJECT_ID.IDS;
			break;
		case 6:
			result = BIOS_PROJECT_ID.IDY;
			break;
		case 7:
			result = BIOS_PROJECT_ID.IDW;
			break;
		case 8:
			result = BIOS_PROJECT_ID.IDM;
			break;
		case 9:
			result = BIOS_PROJECT_ID.IDM_2ND_SPK;
			break;
		}
		return result;
	}

	public GN20_GPU_SKU GetSku()
	{
		GN20_GPU_SKU result = GN20_GPU_SKU.NA;
		byte Data = 0;
		byte b = 240;
		byte b2 = 0;
		AcpiModel.Read(GetType().Name, 2003, ref Data);
		switch ((byte)(Data & b))
		{
		case 48:
			result = GN20_GPU_SKU.E3;
			break;
		case 64:
			result = GN20_GPU_SKU.E4;
			break;
		case 80:
			result = GN20_GPU_SKU.E5;
			break;
		case 96:
			result = GN20_GPU_SKU.MaxQ;
			break;
		case 112:
			result = GN20_GPU_SKU.E7;
			break;
		case 128:
			result = GN20_GPU_SKU.P0;
			break;
		case 144:
			result = GN20_GPU_SKU.P1;
			break;
		}
		return result;
	}

	public bool IsHeroProject()
	{
		GN20_GPU_SKU sku = EcCtrl.GetSku();
		BIOS_PROJECT_ID biosProjctID = EcCtrl.GetBiosProjctID();
		int projectIdFromEC = EcCtrl.GetProjectIdFromEC();
		if (sku == GN20_GPU_SKU.MaxQ && biosProjctID == BIOS_PROJECT_ID.IDP)
		{
			return true;
		}
		if (sku == GN20_GPU_SKU.MaxQ && projectIdFromEC == 22)
		{
			return true;
		}
		return false;
	}

	public bool IsAMDPlatform()
	{
		byte bus = 0;
		byte dev = 0;
		byte func = 0;
		uint offset = 0u;
		uint pData = 0u;
		EcCtrl.ReadPciDword(bus, dev, func, offset, ref pData);
		if ((pData & 0xFFFF) == 4130)
		{
			return true;
		}
		return false;
	}
}
