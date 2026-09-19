using System.IO;
using System.Reflection;
using System.Threading;
using MyECIO;
using Newtonsoft.Json;
using Utility;

namespace MyControlCenter.MyFan.FanTable;

public class FanTable_Manager2
{
	private string className = "[" + MethodBase.GetCurrentMethod().DeclaringType.Name + "] ";

	private MyEcCtrl EcCtrl = MyEcCtrl.Instance;

	private string m_path = new FileInfo(Assembly.GetExecutingAssembly().Location).DirectoryName + "\\FanTable\\User";

	private FanTable2 m_F1_FanTable = new FanTable2(16u);

	private FanTable2 m_F2_FanTable = new FanTable2(16u);

	private FanTable2 m_F3_FanTable = new FanTable2(16u);

	private FanTable2 m_F1_FanTable_dc = new FanTable2(16u);

	private FanTable2 m_F2_FanTable_dc = new FanTable2(16u);

	private FanTable2 m_F3_FanTable_dc = new FanTable2(16u);

	public void FanTable_Init(int _currentPowerMode)
	{
		if (LocalFileLoader.CheckFile("F1_FanTable") && LocalFileLoader.CheckFile("F1_FanTable_dc"))
		{
			m_F1_FanTable = LoadFanTableFromJson("F1_FanTable");
			m_F1_FanTable_dc = LoadFanTableFromJson("F1_FanTable_dc");
			if (_currentPowerMode == 1)
			{
				SetFanTable_F1(m_F1_FanTable);
			}
			else
			{
				SetFanTable_F1(m_F1_FanTable_dc);
			}
		}
		else
		{
			CreateDefaultFanTable(1u);
		}
		if (LocalFileLoader.CheckFile("F2_FanTable") && LocalFileLoader.CheckFile("F2_FanTable_dc"))
		{
			m_F2_FanTable = LoadFanTableFromJson("F2_FanTable");
			m_F2_FanTable_dc = LoadFanTableFromJson("F2_FanTable_dc");
			if (_currentPowerMode == 1)
			{
				SetFanTable_F2(m_F2_FanTable);
			}
			else
			{
				SetFanTable_F2(m_F2_FanTable_dc);
			}
		}
		else
		{
			CreateDefaultFanTable(2u);
		}
		if (LocalFileLoader.CheckFile("F3_FanTable") && LocalFileLoader.CheckFile("F3_FanTable_dc"))
		{
			m_F3_FanTable = LoadFanTableFromJson("F3_FanTable");
			m_F3_FanTable_dc = LoadFanTableFromJson("F3_FanTable_dc");
			if (_currentPowerMode == 1)
			{
				SetFanTable_F3(m_F3_FanTable);
			}
			else
			{
				SetFanTable_F3(m_F3_FanTable_dc);
			}
		}
		else
		{
			CreateDefaultFanTable(3u);
		}
	}

	public void RestoreDefaultFanTableAll(int _currentPowerMode)
	{
		Thread.Sleep(1500);
		LocalFileLoader.DeleteFolder("User");
		CreateDefaultFanTable(1u);
		CreateDefaultFanTable(2u);
		CreateDefaultFanTable(3u);
	}

	private void CreateDefaultFanTable(uint fanMode)
	{
		switch (fanMode)
		{
		case 1u:
			m_F1_FanTable = GetFanTable("F1_FanTable");
			if (m_F1_FanTable.Table != null)
			{
				WriteAllFanTableToJson(m_F1_FanTable, "User", "F1_FanTable");
				m_F1_FanTable_dc = m_F1_FanTable;
				WriteAllFanTableToJson(m_F1_FanTable_dc, "User", "F1_FanTable_dc");
			}
			break;
		case 2u:
			m_F2_FanTable = GetFanTable("F2_FanTable");
			if (m_F2_FanTable.Table != null)
			{
				WriteAllFanTableToJson(m_F2_FanTable, "User", "F2_FanTable");
				m_F2_FanTable_dc = m_F2_FanTable;
				WriteAllFanTableToJson(m_F2_FanTable_dc, "User", "F2_FanTable_dc");
			}
			break;
		case 3u:
			m_F3_FanTable = GetFanTable("F3_FanTable");
			if (m_F3_FanTable.Table != null)
			{
				WriteAllFanTableToJson(m_F3_FanTable, "User", "F3_FanTable");
				m_F3_FanTable_dc = m_F3_FanTable;
				WriteAllFanTableToJson(m_F3_FanTable_dc, "User", "F3_FanTable_dc");
			}
			break;
		}
	}

	public void GetFanTable(uint fanMode, int powerMode)
	{
		FanTable2 fanTable = default(FanTable2);
		if (powerMode == 1)
		{
			switch (fanMode)
			{
			case 1u:
				m_F1_FanTable = LoadFanTableFromJson("F1_FanTable");
				fanTable = m_F1_FanTable;
				break;
			case 2u:
				m_F2_FanTable = LoadFanTableFromJson("F2_FanTable");
				fanTable = m_F2_FanTable;
				break;
			case 3u:
				m_F3_FanTable = LoadFanTableFromJson("F3_FanTable");
				fanTable = m_F3_FanTable;
				break;
			}
		}
		else
		{
			switch (fanMode)
			{
			case 1u:
				m_F1_FanTable_dc = LoadFanTableFromJson("F1_FanTable_dc");
				fanTable = m_F1_FanTable_dc;
				break;
			case 2u:
				m_F2_FanTable_dc = LoadFanTableFromJson("F2_FanTable_dc");
				fanTable = m_F2_FanTable_dc;
				break;
			case 3u:
				m_F3_FanTable_dc = LoadFanTableFromJson("F3_FanTable_dc");
				fanTable = m_F3_FanTable_dc;
				break;
			}
		}
		App.m_MQTTService.Publish("Fan/Status", fanTable, retain: false);
	}

	public void SetFanTableSetting(uint fanMode, int powerMode, int id, string key, uint value)
	{
		if (powerMode == 1)
		{
			switch (fanMode)
			{
			case 1u:
				WriteFanTable(m_F1_FanTable, id, key, value);
				WriteFanTableToJson("F1_FanTable", id, key, value);
				break;
			case 2u:
				WriteFanTable(m_F2_FanTable, id, key, value);
				WriteFanTableToJson("F2_FanTable", id, key, value);
				break;
			case 3u:
				WriteFanTable(m_F3_FanTable, id, key, value);
				WriteFanTableToJson("F3_FanTable", id, key, value);
				break;
			}
		}
		else
		{
			switch (fanMode)
			{
			case 1u:
				WriteFanTable(m_F1_FanTable_dc, id, key, value);
				WriteFanTableToJson("F1_FanTable_dc", id, key, value);
				break;
			case 2u:
				WriteFanTable(m_F2_FanTable_dc, id, key, value);
				WriteFanTableToJson("F2_FanTable_dc", id, key, value);
				break;
			case 3u:
				WriteFanTable(m_F3_FanTable_dc, id, key, value);
				WriteFanTableToJson("F3_FanTable_dc", id, key, value);
				break;
			}
		}
	}

	private FanTable2 LoadFanTableFromJson(string fileName)
	{
		FanTable2 result = new FanTable2(16u);
		dynamic val = LocalFileLoader.LoadJsonFromPath_NonAsync<object>(m_path, fileName, Assembly.GetExecutingAssembly());
		if (val != null)
		{
			return JsonConvert.DeserializeObject<FanTable2>(Json.Stringify(val));
		}
		return result;
	}

	private void WriteFanTable(FanTable2 fanTable, int id, string key, uint value)
	{
		if (id >= 0 && id <= 15)
		{
			switch (key)
			{
			case "CpuUpT":
				fanTable.Table[id].CpuUpT = (byte)value;
				break;
			case "CpuDownT":
				fanTable.Table[id].CpuDownT = (byte)value;
				break;
			case "Duty":
				fanTable.Table[id].Duty = (byte)value;
				break;
			case "GpuUpT":
				fanTable.Table[id].GpuUpT = (byte)value;
				break;
			case "GpuDownT":
				fanTable.Table[id].GpuDownT = (byte)value;
				break;
			}
		}
	}

	private void WriteFanTableToJson(string fileName, int id, string key, uint value)
	{
		try
		{
			string path = new FileInfo(Assembly.GetExecutingAssembly().Location).DirectoryName + "\\FanTable\\User\\" + fileName + ".json";
			if (File.Exists(path))
			{
				dynamic val = JsonConvert.DeserializeObject(File.ReadAllText(path));
				val["Table"][id][key] = value;
				string contents = JsonConvert.SerializeObject(val, Formatting.Indented);
				File.WriteAllText(path, contents);
			}
		}
		catch
		{
		}
	}

	private void WriteAllFanTableToJson(FanTable2 fanTable, string outputFolderName, string outputFileName)
	{
		try
		{
			string text = new FileInfo(Assembly.GetExecutingAssembly().Location).DirectoryName + "\\FanTable\\" + outputFolderName;
			string path = text + "\\" + outputFileName + ".json";
			if (!Directory.Exists(text))
			{
				Directory.CreateDirectory(text);
			}
			string contents = JsonConvert.SerializeObject(fanTable, Formatting.Indented);
			File.WriteAllText(path, contents);
		}
		catch
		{
		}
	}

	private FanTable2 GetFanTable(string fanmode)
	{
		FanTable2 result = new FanTable2(16u);
		byte Data = 0;
		switch (fanmode)
		{
		case "F1_FanTable":
		{
			for (int j = 0; j <= 15; j++)
			{
				if (j == 0)
				{
					result.Table[j].CpuUpT = 0;
					result.Table[j].GpuUpT = 0;
				}
				else
				{
					EcCtrl.Read(GetType().Name, (ushort)(3840 + j - 1), ref Data);
					result.Table[j].CpuUpT = Data;
					EcCtrl.Read(GetType().Name, (ushort)(3888 + j - 1), ref Data);
					result.Table[j].GpuUpT = Data;
				}
				if (j < 15)
				{
					EcCtrl.Read(GetType().Name, (ushort)(3856 + j + 1), ref Data);
					result.Table[j].CpuDownT = Data;
					EcCtrl.Read(GetType().Name, (ushort)(3904 + j + 1), ref Data);
					result.Table[j].GpuDownT = Data;
				}
				else
				{
					EcCtrl.Read(GetType().Name, (ushort)(3856 + j), ref Data);
					result.Table[j].CpuDownT = Data;
					EcCtrl.Read(GetType().Name, (ushort)(3904 + j), ref Data);
					result.Table[j].GpuDownT = Data;
				}
				EcCtrl.Read(GetType().Name, (ushort)(3872 + j), ref Data);
				result.Table[j].Duty = (byte)(Data / 2);
			}
			break;
		}
		case "F2_FanTable":
		{
			for (int k = 0; k <= 15; k++)
			{
				if (k == 0)
				{
					result.Table[k].CpuUpT = 0;
					result.Table[k].GpuUpT = 0;
				}
				else
				{
					EcCtrl.Read(GetType().Name, (ushort)(3920 + k - 1), ref Data);
					result.Table[k].CpuUpT = Data;
					EcCtrl.Read(GetType().Name, (ushort)(3968 + k - 1), ref Data);
					result.Table[k].GpuUpT = Data;
				}
				if (k < 15)
				{
					EcCtrl.Read(GetType().Name, (ushort)(3936 + k + 1), ref Data);
					result.Table[k].CpuDownT = Data;
					EcCtrl.Read(GetType().Name, (ushort)(3984 + k + 1), ref Data);
					result.Table[k].GpuDownT = Data;
				}
				else
				{
					EcCtrl.Read(GetType().Name, (ushort)(3936 + k), ref Data);
					result.Table[k].CpuDownT = Data;
					EcCtrl.Read(GetType().Name, (ushort)(3984 + k), ref Data);
					result.Table[k].GpuDownT = Data;
				}
				EcCtrl.Read(GetType().Name, (ushort)(3952 + k), ref Data);
				result.Table[k].Duty = (byte)(Data / 2);
			}
			break;
		}
		case "F3_FanTable":
		{
			for (int i = 0; i <= 15; i++)
			{
				if (i == 0)
				{
					result.Table[i].CpuUpT = 0;
					result.Table[i].GpuUpT = 0;
				}
				else
				{
					EcCtrl.Read(GetType().Name, (ushort)(4000 + i - 1), ref Data);
					result.Table[i].CpuUpT = Data;
					EcCtrl.Read(GetType().Name, (ushort)(4048 + i - 1), ref Data);
					result.Table[i].GpuUpT = Data;
				}
				if (i < 15)
				{
					EcCtrl.Read(GetType().Name, (ushort)(4016 + i + 1), ref Data);
					result.Table[i].CpuDownT = Data;
					EcCtrl.Read(GetType().Name, (ushort)(4064 + i + 1), ref Data);
					result.Table[i].GpuDownT = Data;
				}
				else
				{
					EcCtrl.Read(GetType().Name, (ushort)(4016 + i), ref Data);
					result.Table[i].CpuDownT = Data;
					EcCtrl.Read(GetType().Name, (ushort)(4064 + i), ref Data);
					result.Table[i].GpuDownT = Data;
				}
				EcCtrl.Read(GetType().Name, (ushort)(4032 + i), ref Data);
				result.Table[i].Duty = (byte)(Data / 2);
			}
			break;
		}
		}
		return result;
	}

	private void SetFanTable_F1(FanTable2 fantable)
	{
		if (fantable.Table == null)
		{
			return;
		}
		for (int i = 0; i <= 15; i++)
		{
			if (i < 15)
			{
				EcCtrl.Write(GetType().Name, (ushort)(3840 + i), fantable.Table[i + 1].CpuUpT);
				EcCtrl.Write(GetType().Name, (ushort)(3888 + i), fantable.Table[i + 1].GpuUpT);
			}
			else
			{
				EcCtrl.Write(GetType().Name, (ushort)(3840 + i), byte.MaxValue);
				EcCtrl.Write(GetType().Name, (ushort)(3888 + i), byte.MaxValue);
			}
			if (i < 15)
			{
				EcCtrl.Write(GetType().Name, (ushort)(3856 + i + 1), fantable.Table[i].CpuDownT);
				EcCtrl.Write(GetType().Name, (ushort)(3904 + i + 1), fantable.Table[i].GpuDownT);
			}
			EcCtrl.Write(GetType().Name, (ushort)(3872 + i), (byte)(fantable.Table[i].Duty * 2));
		}
	}

	private void SetFanTable_F2(FanTable2 fantable)
	{
		if (fantable.Table == null)
		{
			return;
		}
		for (int i = 0; i <= 15; i++)
		{
			if (i < 15)
			{
				EcCtrl.Write(GetType().Name, (ushort)(3920 + i), fantable.Table[i + 1].CpuUpT);
				EcCtrl.Write(GetType().Name, (ushort)(3968 + i), fantable.Table[i + 1].GpuUpT);
			}
			else
			{
				EcCtrl.Write(GetType().Name, (ushort)(3920 + i), byte.MaxValue);
				EcCtrl.Write(GetType().Name, (ushort)(3968 + i), byte.MaxValue);
			}
			if (i < 15)
			{
				EcCtrl.Write(GetType().Name, (ushort)(3936 + i + 1), fantable.Table[i].CpuDownT);
				EcCtrl.Write(GetType().Name, (ushort)(3984 + i + 1), fantable.Table[i].GpuDownT);
			}
			EcCtrl.Write(GetType().Name, (ushort)(3952 + i), (byte)(fantable.Table[i].Duty * 2));
		}
	}

	private void SetFanTable_F3(FanTable2 fantable)
	{
		if (fantable.Table == null)
		{
			return;
		}
		for (int i = 0; i <= 15; i++)
		{
			if (i < 15)
			{
				EcCtrl.Write(GetType().Name, (ushort)(4000 + i), fantable.Table[i + 1].CpuUpT);
				EcCtrl.Write(GetType().Name, (ushort)(4048 + i), fantable.Table[i + 1].GpuUpT);
			}
			else
			{
				EcCtrl.Write(GetType().Name, (ushort)(4000 + i), byte.MaxValue);
				EcCtrl.Write(GetType().Name, (ushort)(4048 + i), byte.MaxValue);
			}
			if (i < 15)
			{
				EcCtrl.Write(GetType().Name, (ushort)(4016 + i + 1), fantable.Table[i].CpuDownT);
				EcCtrl.Write(GetType().Name, (ushort)(4064 + i + 1), fantable.Table[i].GpuDownT);
			}
			EcCtrl.Write(GetType().Name, (ushort)(4032 + i), (byte)(fantable.Table[i].Duty * 2));
		}
	}

	public void ClearFanTableAll()
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
			EcCtrl.Write(GetType().Name, (ushort)(3936 + i), data);
			EcCtrl.Write(GetType().Name, (ushort)(3952 + i), data);
			EcCtrl.Write(GetType().Name, (ushort)(3968 + i), data);
			EcCtrl.Write(GetType().Name, (ushort)(3984 + i), data);
			EcCtrl.Write(GetType().Name, (ushort)(4000 + i), data);
			EcCtrl.Write(GetType().Name, (ushort)(4016 + i), data);
			EcCtrl.Write(GetType().Name, (ushort)(4032 + i), data);
			EcCtrl.Write(GetType().Name, (ushort)(4048 + i), data);
			EcCtrl.Write(GetType().Name, (ushort)(4064 + i), data);
		}
	}
}
