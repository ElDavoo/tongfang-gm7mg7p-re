using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Threading;
using Define;
using MyControlCenter;
using MyECIO;

namespace Utility;

internal class SmartApcTableCtrl
{
	private AcpiCtrl AcpiModel = AcpiCtrl.Instance;

	private MyEcCtrl EcCtrl = MyEcCtrl.Instance;

	private static readonly SmartApcTableCtrl TableCtrl = new SmartApcTableCtrl();

	private int SupportSmartApcTable = 1;

	private List<GN20_GPU_SKU> SupportGpuSkuList = new List<GN20_GPU_SKU>
	{
		GN20_GPU_SKU.E3,
		GN20_GPU_SKU.E4,
		GN20_GPU_SKU.E5,
		GN20_GPU_SKU.MaxQ,
		GN20_GPU_SKU.E7,
		GN20_GPU_SKU.P0,
		GN20_GPU_SKU.P1
	};

	private List<BIOS_PROJECT_ID> SupportProjectIDs = new List<BIOS_PROJECT_ID>
	{
		BIOS_PROJECT_ID.IDR,
		BIOS_PROJECT_ID.IDX,
		BIOS_PROJECT_ID.IDV,
		BIOS_PROJECT_ID.IDO,
		BIOS_PROJECT_ID.IDP,
		BIOS_PROJECT_ID.IDS,
		BIOS_PROJECT_ID.IDY,
		BIOS_PROJECT_ID.IDW,
		BIOS_PROJECT_ID.IDM,
		BIOS_PROJECT_ID.IDM_2ND_SPK
	};

	private object _SmartApcTableLock = new object();

	public static SmartApcTableCtrl Instance => TableCtrl;

	private SmartApcTableCtrl()
	{
	}

	public bool IsSupportSmartApcTable()
	{
		if (SupportSmartApcTable == 1)
		{
			return true;
		}
		return false;
	}

	public SMAPCTABLE_STRUCT GetSMAPCTable()
	{
		LogCtrl.TraceMessage("Start", "GetSMAPCTable", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\Utility\\SmartApcTableCtrl.cs", 88);
		SMAPCTABLE_STRUCT result = default(SMAPCTABLE_STRUCT);
		if (SupportSmartApcTable == 0)
		{
			return result;
		}
		try
		{
			EventLog.WriteEntry("GCUService", "Load SMAPCTABLE Start");
			result = GetTableByDriver();
			EventLog.WriteEntry("GCUService", "Load SMAPCTABLE End");
		}
		catch (Exception ex)
		{
			LogCtrl.TraceMessage("Exception: " + ex.ToString(), "GetSMAPCTable", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\Utility\\SmartApcTableCtrl.cs", 106);
		}
		return result;
	}

	private SMAPCTABLE_STRUCT GetTableByDriver()
	{
		byte[] array = new byte[12];
		List<byte> list = new List<byte>();
		for (int i = 0; i < 12; i++)
		{
			if (!Monitor.TryEnter(_SmartApcTableLock, 1000))
			{
				continue;
			}
			try
			{
				byte[] pData = new byte[4];
				AcpiModel.ReadSmartApcTableByKey(Convert.ToByte(i), ref pData);
				list.Add(pData[0]);
			}
			catch (Exception)
			{
			}
			finally
			{
				Monitor.Exit(_SmartApcTableLock);
			}
		}
		array = list.ToArray();
		string text = string.Empty;
		byte[] array2 = array;
		foreach (byte b in array2)
		{
			text += $"{b:x2}";
		}
		LogCtrl.TraceMessage("OutValue: " + text, "GetTableByDriver", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\Utility\\SmartApcTableCtrl.cs", 171);
		EventLog.WriteEntry("GCUService", "Buffer Finish ! OutValue: " + text);
		SMAPCTABLE_STRUCT result = UtilityExtensions.BytesToStructure<SMAPCTABLE_STRUCT>(array);
		EventLog.WriteEntry("GCUService", "Table Finish !");
		return result;
	}

	private SMAPCTABLE_STRUCT GetTableByWMI()
	{
		return default(SMAPCTABLE_STRUCT);
	}

	private SMAPCTABLE_STRUCT GetTableByDLL()
	{
		byte[] pData = new byte[4];
		byte[] pData2 = new byte[4];
		byte[] pData3 = new byte[4];
		Thread.Sleep(100);
		LogCtrl.TraceMessage("ReadSmartApcTableByDll Start", "GetTableByDLL", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\Utility\\SmartApcTableCtrl.cs", 228);
		EventLog.WriteEntry("GCUService", "ReadSmartApcTableByDll Start");
		AcpiModel.ReadSmartApcTableByDll(0, ref pData);
		Thread.Sleep(100);
		AcpiModel.ReadSmartApcTableByDll(4, ref pData2);
		Thread.Sleep(100);
		AcpiModel.ReadSmartApcTableByDll(8, ref pData3);
		LogCtrl.TraceMessage("ReadSmartApcTableByDll End", "GetTableByDLL", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\Utility\\SmartApcTableCtrl.cs", 235);
		EventLog.WriteEntry("GCUService", "ReadSmartApcTableByDll End");
		byte[] array = new byte[12];
		array = UtilityExtensions.Combine(pData, pData2);
		array = UtilityExtensions.Combine(array, pData3);
		string text = string.Empty;
		byte[] array2 = array;
		foreach (byte b in array2)
		{
			text += $"{b:x2}";
		}
		LogCtrl.TraceMessage("OutValue: " + text, "GetTableByDLL", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\Utility\\SmartApcTableCtrl.cs", 248);
		return UtilityExtensions.BytesToStructure<SMAPCTABLE_STRUCT>(array);
	}

	public bool WriteSMAPCTable(string varname, byte value)
	{
		bool result = false;
		if (SupportSmartApcTable == 0)
		{
			return false;
		}
		SMAPCTABLE_STRUCT sMAPCTable = GetSMAPCTable();
		switch (varname)
		{
		case "PL1":
			sMAPCTable.PL1 = value;
			break;
		case "PL2":
			sMAPCTable.PL2 = value;
			break;
		case "PL4":
			sMAPCTable.PL4 = value;
			break;
		case "ConfigurableTGP":
			sMAPCTable.ConfigurableTGP = value;
			break;
		case "DynamicBoost":
			sMAPCTable.DynamicBoost = value;
			break;
		case "DefaultTGP":
			sMAPCTable.DefaultTGP = value;
			break;
		}
		try
		{
			byte[] data = new byte[Marshal.SizeOf(typeof(SMAPCTABLE_STRUCT))];
			AcpiModel.WriteSmartApcTableByDll(data);
			result = true;
		}
		catch (Exception ex)
		{
			LogCtrl.TraceMessage("Exception: " + ex.ToString(), "WriteSMAPCTable", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\Utility\\SmartApcTableCtrl.cs", 310);
		}
		return result;
	}

	public int GetTGP_IncreaseRangeMaximum(int ConfigurableTGP)
	{
		int result = 0;
		int tGP_NormalMinimum = GetTGP_NormalMinimum();
		if (ConfigurableTGP > 0 && tGP_NormalMinimum != 0)
		{
			result = ConfigurableTGP - tGP_NormalMinimum;
		}
		else
		{
			LogCtrl.TraceMessage("Integrity check fail, then TGPIncreaseRangeMaximum: " + result, "GetTGP_IncreaseRangeMaximum", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\Utility\\SmartApcTableCtrl.cs", 327);
		}
		return result;
	}

	private int GetTGP_NormalMinimum()
	{
		GN20_GPU_SKU sku = EcCtrl.GetSku();
		BIOS_PROJECT_ID biosProjctID = EcCtrl.GetBiosProjctID();
		int result = 0;
		if (CustomizeCtrl.GetIsAMDPlatform())
		{
			switch (sku)
			{
			case GN20_GPU_SKU.E3:
				switch (biosProjctID)
				{
				case BIOS_PROJECT_ID.IDS:
				case BIOS_PROJECT_ID.IDM:
					result = 115;
					break;
				case BIOS_PROJECT_ID.IDR:
				case BIOS_PROJECT_ID.IDO:
				case BIOS_PROJECT_ID.IDP:
				case BIOS_PROJECT_ID.IDY:
				case BIOS_PROJECT_ID.IDW:
					result = 80;
					break;
				}
				break;
			case GN20_GPU_SKU.E5:
				switch (biosProjctID)
				{
				case BIOS_PROJECT_ID.IDS:
				case BIOS_PROJECT_ID.IDM:
					result = 115;
					break;
				case BIOS_PROJECT_ID.IDP:
				case BIOS_PROJECT_ID.IDY:
				case BIOS_PROJECT_ID.IDW:
					result = 115;
					break;
				}
				break;
			case GN20_GPU_SKU.E7:
				switch (biosProjctID)
				{
				case BIOS_PROJECT_ID.IDS:
				case BIOS_PROJECT_ID.IDM:
					result = 115;
					break;
				case BIOS_PROJECT_ID.IDP:
				case BIOS_PROJECT_ID.IDY:
				case BIOS_PROJECT_ID.IDW:
					result = 115;
					break;
				}
				break;
			case GN20_GPU_SKU.MaxQ:
				if (biosProjctID == BIOS_PROJECT_ID.IDP)
				{
					result = 80;
				}
				break;
			}
		}
		else
		{
			switch (sku)
			{
			case GN20_GPU_SKU.E3:
				switch (biosProjctID)
				{
				case BIOS_PROJECT_ID.IDM:
					result = 115;
					break;
				case BIOS_PROJECT_ID.IDP:
				case BIOS_PROJECT_ID.IDY:
					result = 80;
					break;
				case BIOS_PROJECT_ID.IDR:
				case BIOS_PROJECT_ID.IDO:
					result = 80;
					break;
				}
				break;
			case GN20_GPU_SKU.E5:
				switch (biosProjctID)
				{
				case BIOS_PROJECT_ID.IDP:
				case BIOS_PROJECT_ID.IDY:
				case BIOS_PROJECT_ID.IDM:
					result = 115;
					break;
				}
				break;
			}
		}
		LogCtrl.TraceMessage("GN20_GPU_SKU: " + sku.ToString() + ", BIOS_PROJECT_ID: " + biosProjctID.ToString() + ", then the minimum: " + result + "W", "GetTGP_NormalMinimum", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\Utility\\SmartApcTableCtrl.cs", 432);
		return result;
	}
}
