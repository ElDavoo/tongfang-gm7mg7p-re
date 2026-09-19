using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Threading;
using MyECIO;
using Newtonsoft.Json;
using Utility;

namespace MyControlCenter.MyFan.FanTable;

public class FanTable_Manager1p5
{
	private MyEcCtrl EcCtrl = MyEcCtrl.Instance;

	private string m_path = new FileInfo(Assembly.GetExecutingAssembly().Location).DirectoryName + "\\UserFanTables";

	private FanTable1p5 DefaultFanTable_Gaming = new FanTable1p5(16u, "DefaultFanTable_Gaming");

	private FanTable1p5 DefaultFanTable_Office = new FanTable1p5(16u, "DefaultFanTable_Office");

	private FanTable1p5 DefaultFanTable_Turbo = new FanTable1p5(16u, "DefaultFanTable_Turbo");

	private FanTable1p5 M1T1;

	private FanTable1p5 M1T2;

	private FanTable1p5 M1T3;

	private FanTable1p5 M1T4;

	private FanTable1p5 M1T5;

	private FanTable1p5 M2T1;

	private FanTable1p5 M2T2;

	private FanTable1p5 M2T3;

	private FanTable1p5 M2T4;

	private FanTable1p5 M2T5;

	private FanTable1p5 M3T1;

	private FanTable1p5 M3T2;

	private FanTable1p5 M3T3;

	private FanTable1p5 M3T4;

	private FanTable1p5 M3T5;

	private bool bInit;

	private bool m_IsNvGpu;

	private List<string> FileNames = new List<string>
	{
		"M1T1", "M1T2", "M1T3", "M1T4", "M1T5", "M2T1", "M2T2", "M2T3", "M2T4", "M2T5",
		"M3T1", "M3T2", "M3T3", "M3T4", "M3T5"
	};

	public FanTable_Manager1p5()
	{
		m_IsNvGpu = UtilityExtensions.IsNvGpu();
	}

	public virtual bool GetFanTableInit()
	{
		return bInit;
	}

	public virtual void FanTable_Init()
	{
		RefreshFanTable(ref M1T1, "M1T1");
		RefreshFanTable(ref M1T2, "M1T2");
		RefreshFanTable(ref M1T3, "M1T3");
		RefreshFanTable(ref M1T4, "M1T4");
		RefreshFanTable(ref M1T5, "M1T5");
		RefreshFanTable(ref M2T1, "M2T1");
		RefreshFanTable(ref M2T2, "M2T2");
		RefreshFanTable(ref M2T3, "M2T3");
		RefreshFanTable(ref M2T4, "M2T4");
		RefreshFanTable(ref M2T5, "M2T5");
		RefreshFanTable(ref M3T1, "M3T1");
		RefreshFanTable(ref M3T2, "M3T2");
		RefreshFanTable(ref M3T3, "M3T3");
		RefreshFanTable(ref M3T4, "M3T4");
		RefreshFanTable(ref M3T5, "M3T5");
		if (RegistryCtrl.IsNewEcVersion(new HardwareInfoCollect().getECInfo()))
		{
			LogCtrl.TraceMessage("EC is the different version, then load EC default fan table.", "FanTable_Init", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\FanTable\\FanTable_Manager1p5.cs", 85);
			FanTable_Refresh();
			return;
		}
		bool flag = true;
		foreach (string fileName in FileNames)
		{
			if (!CheckFile(fileName))
			{
				flag = false;
				break;
			}
		}
		if (flag)
		{
			LogCtrl.TraceMessage("EC is the same version, then load local fan table.", "FanTable_Init", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\FanTable\\FanTable_Manager1p5.cs", 103);
			DefaultFanTable_Office = LoadFanTableFromJson("DefaultFanTable_Office");
			DefaultFanTable_Gaming = LoadFanTableFromJson("DefaultFanTable_Gaming");
			DefaultFanTable_Turbo = LoadFanTableFromJson("DefaultFanTable_Turbo");
			if (IsInvalidDefaultFanTable())
			{
				LogCtrl.TraceMessage("The local data is invalid, then load EC default fan table.", "FanTable_Init", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\FanTable\\FanTable_Manager1p5.cs", 110);
				FanTable_Refresh();
				return;
			}
			if (IsInvalidDefaultFanTableAllZero())
			{
				LogCtrl.TraceMessage("The local data is all zero , then load EC default fan table.", "FanTable_Init", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\FanTable\\FanTable_Manager1p5.cs", 115);
				FanTable_Refresh();
				return;
			}
			M1T1 = LoadFanTableFromJson(M1T1.Name);
			M1T2 = LoadFanTableFromJson(M1T2.Name);
			M1T3 = LoadFanTableFromJson(M1T3.Name);
			M1T4 = LoadFanTableFromJson(M1T4.Name);
			M1T5 = LoadFanTableFromJson(M1T5.Name);
			M2T1 = LoadFanTableFromJson(M2T1.Name);
			M2T2 = LoadFanTableFromJson(M2T2.Name);
			M2T3 = LoadFanTableFromJson(M2T3.Name);
			M2T4 = LoadFanTableFromJson(M2T4.Name);
			M2T5 = LoadFanTableFromJson(M2T5.Name);
			M3T1 = LoadFanTableFromJson(M3T1.Name);
			M3T2 = LoadFanTableFromJson(M3T2.Name);
			M3T3 = LoadFanTableFromJson(M3T3.Name);
			M3T4 = LoadFanTableFromJson(M3T4.Name);
			M3T5 = LoadFanTableFromJson(M3T5.Name);
		}
		else
		{
			LogCtrl.TraceMessage("EC is the same version but local fan table is not found, then load EC default fan table.", "FanTable_Init", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\FanTable\\FanTable_Manager1p5.cs", 139);
			FanTable_Refresh();
		}
	}

	private bool CheckFanTable()
	{
		throw new NotImplementedException();
	}

	private bool IsInvalidDefaultFanTable()
	{
		bool result = false;
		for (int i = 0; i <= 14; i++)
		{
			if (DefaultFanTable_Office.CPU[i].Duty > DefaultFanTable_Office.CPU[i + 1].Duty)
			{
				return true;
			}
			if (DefaultFanTable_Gaming.CPU[i].Duty > DefaultFanTable_Gaming.CPU[i + 1].Duty)
			{
				return true;
			}
			if (DefaultFanTable_Turbo.CPU[i].Duty > DefaultFanTable_Turbo.CPU[i + 1].Duty)
			{
				return true;
			}
			if (m_IsNvGpu)
			{
				if (DefaultFanTable_Office.GPU[i].Duty > DefaultFanTable_Office.GPU[i + 1].Duty)
				{
					return true;
				}
				if (DefaultFanTable_Gaming.GPU[i].Duty > DefaultFanTable_Gaming.GPU[i + 1].Duty)
				{
					return true;
				}
				if (DefaultFanTable_Turbo.GPU[i].Duty > DefaultFanTable_Turbo.GPU[i + 1].Duty)
				{
					return true;
				}
			}
		}
		return result;
	}

	private bool IsInvalidDefaultFanTableAllZero()
	{
		bool result = false;
		for (int i = 0; i <= 14; i++)
		{
			if (DefaultFanTable_Office.CPU.All((FanTable1p5Buffer n) => n.Duty == 0))
			{
				return true;
			}
			if (DefaultFanTable_Gaming.CPU.All((FanTable1p5Buffer n) => n.Duty == 0))
			{
				return true;
			}
			if (DefaultFanTable_Turbo.CPU.All((FanTable1p5Buffer n) => n.Duty == 0))
			{
				return true;
			}
			if (m_IsNvGpu)
			{
				if (DefaultFanTable_Office.GPU.All((FanTable1p5Buffer n) => n.Duty == 0))
				{
					return true;
				}
				if (DefaultFanTable_Gaming.GPU.All((FanTable1p5Buffer n) => n.Duty == 0))
				{
					return true;
				}
				if (DefaultFanTable_Turbo.GPU.All((FanTable1p5Buffer n) => n.Duty == 0))
				{
					return true;
				}
			}
		}
		return result;
	}

	private void FanTable_Refresh()
	{
		bInit = RefreshDefaultFanTableAll();
		M1T1 = CopyFanTable(DefaultFanTable_Gaming, "M1T1");
		M1T2 = CopyFanTable(DefaultFanTable_Gaming, "M1T2");
		M1T3 = CopyFanTable(DefaultFanTable_Gaming, "M1T3");
		M1T4 = CopyFanTable(DefaultFanTable_Gaming, "M1T4");
		M1T5 = CopyFanTable(DefaultFanTable_Gaming, "M1T5");
		WriteFanTableToJson(M1T1, activated: false);
		WriteFanTableToJson(M1T2, activated: false);
		WriteFanTableToJson(M1T3, activated: false);
		WriteFanTableToJson(M1T4, activated: false);
		WriteFanTableToJson(M1T5, activated: false);
		M2T1 = CopyFanTable(DefaultFanTable_Office, "M2T1");
		M2T2 = CopyFanTable(DefaultFanTable_Office, "M2T2");
		M2T3 = CopyFanTable(DefaultFanTable_Office, "M2T3");
		M2T4 = CopyFanTable(DefaultFanTable_Office, "M2T4");
		M2T5 = CopyFanTable(DefaultFanTable_Office, "M2T5");
		WriteFanTableToJson(M2T1, activated: false);
		WriteFanTableToJson(M2T2, activated: false);
		WriteFanTableToJson(M2T3, activated: false);
		WriteFanTableToJson(M2T4, activated: false);
		WriteFanTableToJson(M2T5, activated: false);
		M3T1 = CopyFanTable(DefaultFanTable_Turbo, "M3T1");
		M3T2 = CopyFanTable(DefaultFanTable_Turbo, "M3T2");
		M3T3 = CopyFanTable(DefaultFanTable_Turbo, "M3T3");
		M3T4 = CopyFanTable(DefaultFanTable_Turbo, "M3T4");
		M3T5 = CopyFanTable(DefaultFanTable_Turbo, "M3T5");
		WriteFanTableToJson(M3T1, activated: false);
		WriteFanTableToJson(M3T2, activated: false);
		WriteFanTableToJson(M3T3, activated: false);
		WriteFanTableToJson(M3T4, activated: false);
		WriteFanTableToJson(M3T5, activated: false);
	}

	public virtual void SetFanControlRespective(dynamic data)
	{
		try
		{
			if (data["Name"] != null && data["FanControlRespective"] != null)
			{
				string name = Convert.ToString(data["Name"]);
				bool flag = Convert.ToBoolean(data["FanControlRespective"]);
				SetFanTableActivated(name, activated: true);
				RefreshFanControlRespective(name, flag);
				SetEcFanControlRespective(flag);
				WriteFanTableToJson(TableTransform(name), activated: true);
			}
		}
		catch (Exception ex)
		{
			LogCtrl.TraceMessage("Exception: " + ex.Message, "SetFanControlRespective", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\FanTable\\FanTable_Manager1p5.cs", 391);
		}
	}

	public virtual void GetFanTable(string name)
	{
		FanTable1p5 fanTable1p = default(FanTable1p5);
		fanTable1p = TableTransform(name);
		App.m_MQTTService.Publish("Fan/Table", fanTable1p, retain: false);
	}

	public virtual void SetFanTable(string name)
	{
		SetEcFanControlRespective(TableTransform(name).FanControlRespective);
		SetEcFanTable(TableTransform(name));
	}

	public virtual void SetFanTableSetting(dynamic data, bool saveEC)
	{
		try
		{
			if (data["Name"] != null && data["Type"] != null)
			{
				string name = Convert.ToString(data["Name"]);
				string text = Convert.ToString(data["Type"]);
				SetFanTableActivated(name, activated: true);
				SetFanTableSetting(TableTransform(name), text, data, saveEC);
			}
		}
		catch (Exception ex)
		{
			LogCtrl.TraceMessage("Exception: " + ex.Message, "SetFanTableSetting", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\FanTable\\FanTable_Manager1p5.cs", 436);
		}
	}

	public virtual void RestoreDefaultFanTableAll()
	{
		M1T1 = CopyFanTable(DefaultFanTable_Gaming, "M1T1");
		M1T2 = CopyFanTable(DefaultFanTable_Gaming, "M1T2");
		M1T3 = CopyFanTable(DefaultFanTable_Gaming, "M1T3");
		M1T4 = CopyFanTable(DefaultFanTable_Gaming, "M1T4");
		M1T5 = CopyFanTable(DefaultFanTable_Gaming, "M1T5");
		WriteFanTableToJson(M1T1, activated: false);
		WriteFanTableToJson(M1T2, activated: false);
		WriteFanTableToJson(M1T3, activated: false);
		WriteFanTableToJson(M1T4, activated: false);
		WriteFanTableToJson(M1T5, activated: false);
		M2T1 = CopyFanTable(DefaultFanTable_Office, "M2T1");
		M2T2 = CopyFanTable(DefaultFanTable_Office, "M2T2");
		M2T3 = CopyFanTable(DefaultFanTable_Office, "M2T3");
		M2T4 = CopyFanTable(DefaultFanTable_Office, "M2T4");
		M2T5 = CopyFanTable(DefaultFanTable_Office, "M2T5");
		WriteFanTableToJson(M2T1, activated: false);
		WriteFanTableToJson(M2T2, activated: false);
		WriteFanTableToJson(M2T3, activated: false);
		WriteFanTableToJson(M2T4, activated: false);
		WriteFanTableToJson(M2T5, activated: false);
		M3T1 = CopyFanTable(DefaultFanTable_Turbo, "M3T1");
		M3T2 = CopyFanTable(DefaultFanTable_Turbo, "M3T2");
		M3T3 = CopyFanTable(DefaultFanTable_Turbo, "M3T3");
		M3T4 = CopyFanTable(DefaultFanTable_Turbo, "M3T4");
		M3T5 = CopyFanTable(DefaultFanTable_Turbo, "M3T5");
		WriteFanTableToJson(M3T1, activated: false);
		WriteFanTableToJson(M3T2, activated: false);
		WriteFanTableToJson(M3T3, activated: false);
		WriteFanTableToJson(M3T4, activated: false);
		WriteFanTableToJson(M3T5, activated: false);
	}

	public virtual void RestoreDefaultFanTable(dynamic data)
	{
		if (data["Name"] != null)
		{
			string text = Convert.ToString(data["Name"]);
			FanTable1p5 fanTable1p = default(FanTable1p5);
			switch (text)
			{
			case "M1T1":
				M1T1 = CopyFanTable(DefaultFanTable_Gaming, text);
				fanTable1p = M1T1;
				break;
			case "M1T2":
				M1T2 = CopyFanTable(DefaultFanTable_Gaming, text);
				fanTable1p = M1T2;
				break;
			case "M1T3":
				M1T3 = CopyFanTable(DefaultFanTable_Gaming, text);
				fanTable1p = M1T3;
				break;
			case "M1T4":
				M1T4 = CopyFanTable(DefaultFanTable_Gaming, text);
				fanTable1p = M1T4;
				break;
			case "M1T5":
				M1T5 = CopyFanTable(DefaultFanTable_Gaming, text);
				fanTable1p = M1T5;
				break;
			case "M2T1":
				M2T1 = CopyFanTable(DefaultFanTable_Office, text);
				fanTable1p = M2T1;
				break;
			case "M2T2":
				M2T2 = CopyFanTable(DefaultFanTable_Office, text);
				fanTable1p = M2T2;
				break;
			case "M2T3":
				M2T3 = CopyFanTable(DefaultFanTable_Office, text);
				fanTable1p = M2T3;
				break;
			case "M2T4":
				M2T4 = CopyFanTable(DefaultFanTable_Office, text);
				fanTable1p = M2T4;
				break;
			case "M2T5":
				M2T5 = CopyFanTable(DefaultFanTable_Office, text);
				fanTable1p = M2T5;
				break;
			case "M3T1":
				M3T1 = CopyFanTable(DefaultFanTable_Turbo, text);
				fanTable1p = M3T1;
				break;
			case "M3T2":
				M3T2 = CopyFanTable(DefaultFanTable_Turbo, text);
				fanTable1p = M3T2;
				break;
			case "M3T3":
				M3T3 = CopyFanTable(DefaultFanTable_Turbo, text);
				fanTable1p = M3T3;
				break;
			case "M3T4":
				M3T4 = CopyFanTable(DefaultFanTable_Turbo, text);
				fanTable1p = M3T4;
				break;
			case "M3T5":
				M3T5 = CopyFanTable(DefaultFanTable_Turbo, text);
				fanTable1p = M3T5;
				break;
			}
			if (fanTable1p.CPU != null && fanTable1p.GPU != null)
			{
				WriteFanTableToJson(fanTable1p, activated: false);
				SetEcFanControlRespective(fanTable1p.FanControlRespective);
				SetEcFanTable(fanTable1p);
				App.m_MQTTService.Publish("Fan/Table", fanTable1p, retain: false);
			}
		}
	}

	public virtual void GetPLDefaultValue(string name, ref string PL1, ref string PL2, ref string PL1_dc, ref string PL2_dc)
	{
		PL1 = "NA";
		PL2 = "NA";
		PL1_dc = "NA";
		PL2_dc = "NA";
	}

	public virtual void GetGpuFeatureDefaultValue(string name, ref string DB, ref string WM)
	{
		DB = "NA";
		WM = "NA";
	}

	private void RefreshFanTable(ref FanTable1p5 fantable, string name)
	{
		fantable.Name = name;
	}

	private void LoadOfficeFanTables()
	{
		M2T1 = GenerateFanDuty(DefaultFanTable_Office, 0.8, "M2T1");
		M2T2 = GenerateFanDuty(DefaultFanTable_Office, 0.9, "M2T2");
		M2T3 = CopyFanTable(DefaultFanTable_Office, "M2T3");
		M2T4 = GenerateFanDuty(DefaultFanTable_Office, 1.1, "M2T4");
		M2T5 = GenerateFanDuty(DefaultFanTable_Office, 1.2, "M2T5");
	}

	private bool CheckFile(string _fileName)
	{
		bool result = false;
		try
		{
			if (File.Exists(m_path + "\\" + _fileName + ".json"))
			{
				result = true;
			}
		}
		catch
		{
			result = false;
		}
		return result;
	}

	private void WriteFanTableToJson(FanTable1p5 fantable, bool activated)
	{
		try
		{
			string path = m_path + "\\" + fantable.Name + ".json";
			if (!Directory.Exists(m_path))
			{
				Directory.CreateDirectory(m_path);
			}
			fantable.Activated = activated;
			string contents = JsonConvert.SerializeObject(fantable, Formatting.Indented);
			File.WriteAllText(path, contents);
		}
		catch (Exception ex)
		{
			LogCtrl.TraceMessage("Exception: " + ex.Message, "WriteFanTableToJson", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\FanTable\\FanTable_Manager1p5.cs", 631);
		}
	}

	private FanTable1p5 LoadFanTableFromJson(string fileName)
	{
		FanTable1p5 result = default(FanTable1p5);
		dynamic val = LocalFileLoader.LoadJsonFromPath_NonAsync<object>(m_path, fileName, Assembly.GetExecutingAssembly());
		if (val != null)
		{
			return JsonConvert.DeserializeObject<FanTable1p5>(Json.Stringify(val));
		}
		return result;
	}

	private void GetEcFanTable(ref FanTable1p5 fantable)
	{
		byte Data = 0;
		for (int i = 0; i <= 15; i++)
		{
			if (i == 0)
			{
				fantable.CPU[i].UpT = 0;
			}
			else
			{
				EcCtrl.Read(GetType().Name, (ushort)(3840 + i - 1), ref Data);
				fantable.CPU[i].UpT = Data;
			}
			if (i < 15)
			{
				EcCtrl.Read(GetType().Name, (ushort)(3856 + i + 1), ref Data);
				fantable.CPU[i].DownT = Data;
			}
			else
			{
				EcCtrl.Read(GetType().Name, (ushort)(3856 + i), ref Data);
				fantable.CPU[i].DownT = Data;
			}
			EcCtrl.Read(GetType().Name, (ushort)(3872 + i), ref Data);
			fantable.CPU[i].Duty = (byte)(Data / 2);
		}
		if (!m_IsNvGpu)
		{
			return;
		}
		for (int j = 0; j <= 15; j++)
		{
			if (j == 0)
			{
				fantable.GPU[j].UpT = 0;
			}
			else
			{
				EcCtrl.Read(GetType().Name, (ushort)(3888 + j - 1), ref Data);
				fantable.GPU[j].UpT = Data;
			}
			if (j < 15)
			{
				EcCtrl.Read(GetType().Name, (ushort)(3904 + j + 1), ref Data);
				fantable.GPU[j].DownT = Data;
			}
			else
			{
				EcCtrl.Read(GetType().Name, (ushort)(3904 + j), ref Data);
				fantable.GPU[j].DownT = Data;
			}
			EcCtrl.Read(GetType().Name, (ushort)(3920 + j), ref Data);
			fantable.GPU[j].Duty = (byte)(Data / 2);
		}
	}

	private void SetEcFanTable(FanTable1p5 fantable)
	{
		if (fantable.CPU != null)
		{
			for (int i = 0; i <= 15; i++)
			{
				if (i < 15)
				{
					EcCtrl.Write(GetType().Name, (ushort)(3840 + i), fantable.CPU[i + 1].UpT);
				}
				else
				{
					EcCtrl.Write(GetType().Name, (ushort)(3840 + i), byte.MaxValue);
				}
				if (i < 15)
				{
					EcCtrl.Write(GetType().Name, (ushort)(3856 + i + 1), fantable.CPU[i].DownT);
				}
				EcCtrl.Write(GetType().Name, (ushort)(3872 + i), (byte)(fantable.CPU[i].Duty * 2));
			}
		}
		if (!m_IsNvGpu || fantable.GPU == null)
		{
			return;
		}
		for (int j = 0; j <= 15; j++)
		{
			if (j < 15)
			{
				EcCtrl.Write(GetType().Name, (ushort)(3888 + j), fantable.GPU[j + 1].UpT);
			}
			else
			{
				EcCtrl.Write(GetType().Name, (ushort)(3888 + j), byte.MaxValue);
			}
			if (j < 15)
			{
				EcCtrl.Write(GetType().Name, (ushort)(3904 + j + 1), fantable.GPU[j].DownT);
			}
			EcCtrl.Write(GetType().Name, (ushort)(3920 + j), (byte)(fantable.GPU[j].Duty * 2));
		}
	}

	private void SetEcFanTable_Cpu(FanTable1p5 fantable)
	{
		if (fantable.CPU == null)
		{
			return;
		}
		for (int i = 0; i <= 15; i++)
		{
			if (i < 15)
			{
				EcCtrl.Write(GetType().Name, (ushort)(3840 + i), fantable.CPU[i + 1].UpT);
			}
			else
			{
				EcCtrl.Write(GetType().Name, (ushort)(3840 + i), byte.MaxValue);
			}
			if (i < 15)
			{
				EcCtrl.Write(GetType().Name, (ushort)(3856 + i + 1), fantable.CPU[i].DownT);
			}
			EcCtrl.Write(GetType().Name, (ushort)(3872 + i), (byte)(fantable.CPU[i].Duty * 2));
		}
	}

	private void SetEcFanTable_Gpu(FanTable1p5 fantable)
	{
		if (fantable.GPU == null)
		{
			return;
		}
		for (int i = 0; i <= 15; i++)
		{
			if (i < 15)
			{
				EcCtrl.Write(GetType().Name, (ushort)(3888 + i), fantable.GPU[i + 1].UpT);
			}
			else
			{
				EcCtrl.Write(GetType().Name, (ushort)(3888 + i), byte.MaxValue);
			}
			if (i < 15)
			{
				EcCtrl.Write(GetType().Name, (ushort)(3904 + i + 1), fantable.GPU[i].DownT);
			}
			EcCtrl.Write(GetType().Name, (ushort)(3920 + i), (byte)(fantable.GPU[i].Duty * 2));
		}
	}

	private void SetFanTableSetting(FanTable1p5 fanTable, string type, int id, string key, int value)
	{
		if (id < 0 || id > 15 || fanTable.CPU == null || fanTable.GPU == null)
		{
			return;
		}
		if (type == "CPU")
		{
			switch (key)
			{
			case "Duty":
				fanTable.CPU[id].Duty = (byte)value;
				break;
			case "UpT":
				fanTable.CPU[id].UpT = (byte)value;
				break;
			case "DownT":
				fanTable.CPU[id].DownT = (byte)value;
				break;
			}
		}
		else if (type == "GPU")
		{
			switch (key)
			{
			case "Duty":
				fanTable.GPU[id].Duty = (byte)value;
				break;
			case "UpT":
				fanTable.GPU[id].UpT = (byte)value;
				break;
			case "DownT":
				fanTable.GPU[id].DownT = (byte)value;
				break;
			}
		}
		WriteFanTableToJson(fanTable, activated: true);
		SetEcFanTable(fanTable);
	}

	private void SetFanTableSetting(FanTable1p5 fanTable, string type, dynamic data, bool saveEC)
	{
		if (type == "CPU")
		{
			fanTable.CPU[0].Duty = Convert.ToByte(data["T0"]);
			fanTable.CPU[1].Duty = Convert.ToByte(data["T1"]);
			fanTable.CPU[2].Duty = Convert.ToByte(data["T2"]);
			fanTable.CPU[3].Duty = Convert.ToByte(data["T3"]);
			fanTable.CPU[4].Duty = Convert.ToByte(data["T4"]);
			fanTable.CPU[5].Duty = Convert.ToByte(data["T5"]);
			fanTable.CPU[6].Duty = Convert.ToByte(data["T6"]);
			fanTable.CPU[7].Duty = Convert.ToByte(data["T7"]);
			fanTable.CPU[8].Duty = Convert.ToByte(data["T8"]);
			fanTable.CPU[9].Duty = Convert.ToByte(data["T9"]);
			fanTable.CPU[10].Duty = Convert.ToByte(data["T10"]);
			fanTable.CPU[11].Duty = Convert.ToByte(data["T11"]);
			fanTable.CPU[12].Duty = Convert.ToByte(data["T12"]);
			fanTable.CPU[13].Duty = Convert.ToByte(data["T13"]);
			fanTable.CPU[14].Duty = Convert.ToByte(data["T14"]);
			fanTable.CPU[15].Duty = Convert.ToByte(data["T15"]);
			WriteFanTableToJson(fanTable, activated: true);
			if (saveEC)
			{
				SetEcFanTable_Cpu(fanTable);
			}
		}
		else if (type == "GPU")
		{
			fanTable.GPU[0].Duty = Convert.ToByte(data["T0"]);
			fanTable.GPU[1].Duty = Convert.ToByte(data["T1"]);
			fanTable.GPU[2].Duty = Convert.ToByte(data["T2"]);
			fanTable.GPU[3].Duty = Convert.ToByte(data["T3"]);
			fanTable.GPU[4].Duty = Convert.ToByte(data["T4"]);
			fanTable.GPU[5].Duty = Convert.ToByte(data["T5"]);
			fanTable.GPU[6].Duty = Convert.ToByte(data["T6"]);
			fanTable.GPU[7].Duty = Convert.ToByte(data["T7"]);
			fanTable.GPU[8].Duty = Convert.ToByte(data["T8"]);
			fanTable.GPU[9].Duty = Convert.ToByte(data["T9"]);
			fanTable.GPU[10].Duty = Convert.ToByte(data["T10"]);
			fanTable.GPU[11].Duty = Convert.ToByte(data["T11"]);
			fanTable.GPU[12].Duty = Convert.ToByte(data["T12"]);
			fanTable.GPU[13].Duty = Convert.ToByte(data["T13"]);
			fanTable.GPU[14].Duty = Convert.ToByte(data["T14"]);
			fanTable.GPU[15].Duty = Convert.ToByte(data["T15"]);
			WriteFanTableToJson(fanTable, activated: true);
			if (saveEC)
			{
				SetEcFanTable_Gpu(fanTable);
			}
		}
	}

	private FanTable1p5 GenerateFanDuty(FanTable1p5 defaultFantable, double ratio, string name)
	{
		byte b = 0;
		FanTable1p5 result = new FanTable1p5(16u, name);
		result.CpuTemp_DefaultMaxLevel = defaultFantable.CpuTemp_DefaultMaxLevel;
		result.GpuTemp_DefaultMaxLevel = defaultFantable.GpuTemp_DefaultMaxLevel;
		for (int i = 0; i <= 15; i++)
		{
			result.CPU[i].UpT = defaultFantable.CPU[i].UpT;
			result.GPU[i].UpT = defaultFantable.GPU[i].UpT;
			result.CPU[i].DownT = defaultFantable.CPU[i].DownT;
			result.GPU[i].DownT = defaultFantable.GPU[i].DownT;
			b = defaultFantable.CPU[i].Duty;
			result.CPU[i].Duty = Convert.ToByte((double)(int)b * ratio);
			b = defaultFantable.GPU[i].Duty;
			result.GPU[i].Duty = Convert.ToByte((double)(int)b * ratio);
		}
		return result;
	}

	private FanTable1p5 CopyFanTable(FanTable1p5 defaultFantable, string name)
	{
		FanTable1p5 result = new FanTable1p5(16u, name);
		result.CpuTemp_DefaultMaxLevel = defaultFantable.CpuTemp_DefaultMaxLevel;
		result.GpuTemp_DefaultMaxLevel = defaultFantable.GpuTemp_DefaultMaxLevel;
		for (int i = 0; i <= 15; i++)
		{
			result.CPU[i].UpT = defaultFantable.CPU[i].UpT;
			result.GPU[i].UpT = defaultFantable.GPU[i].UpT;
			result.CPU[i].DownT = defaultFantable.CPU[i].DownT;
			result.GPU[i].DownT = defaultFantable.GPU[i].DownT;
			result.CPU[i].Duty = defaultFantable.CPU[i].Duty;
			result.GPU[i].Duty = defaultFantable.GPU[i].Duty;
		}
		return result;
	}

	public virtual void ClearFanTableAll()
	{
		byte data = 0;
		for (int i = 0; i <= 15; i++)
		{
			EcCtrl.Write(GetType().Name, (ushort)(3840 + i), data);
			EcCtrl.Write(GetType().Name, (ushort)(3856 + i), data);
			EcCtrl.Write(GetType().Name, (ushort)(3872 + i), data);
			EcCtrl.Write(GetType().Name, (ushort)(3888 + i), data);
			EcCtrl.Write(GetType().Name, (ushort)(3904 + i), data);
			EcCtrl.Write(GetType().Name, (ushort)(3920 + i), data);
		}
	}

	private bool RefreshDefaultFanTableAll()
	{
		bool result = false;
		EcCtrl.Set_APExistToEC(bExist: false);
		bool num = RefreshDefaultFanTable(ref DefaultFanTable_Gaming, 2);
		DefaultFanTable_Gaming.CpuTemp_DefaultMaxLevel = GetCpuTemMaxLevel(ref DefaultFanTable_Gaming);
		DefaultFanTable_Gaming.GpuTemp_DefaultMaxLevel = GetGpuTemMaxLevel(ref DefaultFanTable_Gaming);
		bool flag = RefreshDefaultFanTable(ref DefaultFanTable_Office, 3);
		DefaultFanTable_Office.CpuTemp_DefaultMaxLevel = GetCpuTemMaxLevel(ref DefaultFanTable_Office);
		DefaultFanTable_Office.GpuTemp_DefaultMaxLevel = GetGpuTemMaxLevel(ref DefaultFanTable_Office);
		bool flag2 = RefreshDefaultFanTable(ref DefaultFanTable_Turbo, 1);
		DefaultFanTable_Turbo.CpuTemp_DefaultMaxLevel = GetCpuTemMaxLevel(ref DefaultFanTable_Turbo);
		DefaultFanTable_Turbo.GpuTemp_DefaultMaxLevel = GetGpuTemMaxLevel(ref DefaultFanTable_Turbo);
		if (num && flag && flag2)
		{
			WriteFanTableToJson(DefaultFanTable_Gaming, activated: false);
			WriteFanTableToJson(DefaultFanTable_Office, activated: false);
			WriteFanTableToJson(DefaultFanTable_Turbo, activated: false);
			result = true;
		}
		EcCtrl.Set_APExistToEC(bExist: true);
		return result;
	}

	private bool IsReadyToRead()
	{
		byte Data = 253;
		byte Data2 = 201;
		EcCtrl.Read(GetType().Name, 3933, ref Data);
		EcCtrl.Read(GetType().Name, 3934, ref Data2);
		if (Data != 253 && Data2 != 201)
		{
			return true;
		}
		return false;
	}

	private bool RefreshDefaultFanTable(ref FanTable1p5 fantable, byte mode)
	{
		bool flag = false;
		EcCtrl.Write(GetType().Name, 3935, mode);
		EcCtrl.Write(GetType().Name, 3933, 253);
		EcCtrl.Write(GetType().Name, 3934, 201);
		int num = 0;
		do
		{
			Thread.Sleep(500);
			if (IsReadyToRead())
			{
				GetEcFanTable(ref fantable);
				LogCtrl.TraceMessage("GetFanTable success.", "RefreshDefaultFanTable", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\FanTable\\FanTable_Manager1p5.cs", 1025);
				return true;
			}
			num++;
		}
		while (num != 3);
		LogCtrl.TraceMessage("GetFanTable fail.", "RefreshDefaultFanTable", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\FanTable\\FanTable_Manager1p5.cs", 1033);
		return false;
	}

	private FanTable1p5 TableTransform(string name)
	{
		return name switch
		{
			"M1T1" => M1T1, 
			"M1T2" => M1T2, 
			"M1T3" => M1T3, 
			"M1T4" => M1T4, 
			"M1T5" => M1T5, 
			"M2T1" => M2T1, 
			"M2T2" => M2T2, 
			"M2T3" => M2T3, 
			"M2T4" => M2T4, 
			"M2T5" => M2T5, 
			"M3T1" => M3T1, 
			"M3T2" => M3T2, 
			"M3T3" => M3T3, 
			"M3T4" => M3T4, 
			"M3T5" => M3T5, 
			"DefaultFanTable_Gaming" => DefaultFanTable_Gaming, 
			"DefaultFanTable_Office" => DefaultFanTable_Office, 
			"DefaultFanTable_Turbo" => DefaultFanTable_Turbo, 
			_ => default(FanTable1p5), 
		};
	}

	private void SetFanTableActivated(string name, bool activated)
	{
		switch (name)
		{
		case "M1T1":
			M1T1.Activated = activated;
			break;
		case "M1T2":
			M1T2.Activated = activated;
			break;
		case "M1T3":
			M1T3.Activated = activated;
			break;
		case "M1T4":
			M1T4.Activated = activated;
			break;
		case "M1T5":
			M1T5.Activated = activated;
			break;
		case "M2T1":
			M2T1.Activated = activated;
			break;
		case "M2T2":
			M2T2.Activated = activated;
			break;
		case "M2T3":
			M2T3.Activated = activated;
			break;
		case "M2T4":
			M2T4.Activated = activated;
			break;
		case "M2T5":
			M2T5.Activated = activated;
			break;
		case "M3T1":
			M3T1.Activated = activated;
			break;
		case "M3T2":
			M3T2.Activated = activated;
			break;
		case "M3T3":
			M3T3.Activated = activated;
			break;
		case "M3T4":
			M3T4.Activated = activated;
			break;
		case "M3T5":
			M3T5.Activated = activated;
			break;
		}
	}

	private void RefreshFanControlRespective(string name, bool status)
	{
		switch (name)
		{
		case "M1T1":
			M1T1.FanControlRespective = status;
			break;
		case "M1T2":
			M1T2.FanControlRespective = status;
			break;
		case "M1T3":
			M1T3.FanControlRespective = status;
			break;
		case "M1T4":
			M1T4.FanControlRespective = status;
			break;
		case "M1T5":
			M1T5.FanControlRespective = status;
			break;
		case "M2T1":
			M2T1.FanControlRespective = status;
			break;
		case "M2T2":
			M2T2.FanControlRespective = status;
			break;
		case "M2T3":
			M2T3.FanControlRespective = status;
			break;
		case "M2T4":
			M2T4.FanControlRespective = status;
			break;
		case "M2T5":
			M2T5.FanControlRespective = status;
			break;
		case "M3T1":
			M3T1.FanControlRespective = status;
			break;
		case "M3T2":
			M3T2.FanControlRespective = status;
			break;
		case "M3T3":
			M3T3.FanControlRespective = status;
			break;
		case "M3T4":
			M3T4.FanControlRespective = status;
			break;
		case "M3T5":
			M3T5.FanControlRespective = status;
			break;
		}
	}

	private int GetCpuTemMaxLevel(ref FanTable1p5 fantable)
	{
		int num = 10;
		for (int i = 1; i <= 15; i++)
		{
			if (fantable.CPU[i].Duty > fantable.CPU[i - 1].Duty)
			{
				num = i;
			}
		}
		return num + 1;
	}

	private int GetGpuTemMaxLevel(ref FanTable1p5 fantable)
	{
		int num = 10;
		for (int i = 1; i <= 15; i++)
		{
			if (fantable.GPU[i].Duty > fantable.GPU[i - 1].Duty)
			{
				num = i;
			}
		}
		return num + 1;
	}

	private void SetEcFanControlRespective(bool bEnable)
	{
		byte Data = 0;
		byte b = 127;
		byte b2 = 0;
		byte b3 = 0;
		b2 = (byte)(bEnable ? 128 : 0);
		EcCtrl.Read(GetType().Name, 1989, ref Data);
		b3 = (byte)((Data & b) + b2);
		EcCtrl.Write(GetType().Name, 1989, b3);
	}
}
