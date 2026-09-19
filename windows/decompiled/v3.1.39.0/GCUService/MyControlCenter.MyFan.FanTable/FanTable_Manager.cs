using System.IO;
using System.Reflection;
using MyECIO;
using Newtonsoft.Json;
using Utility;

namespace MyControlCenter.MyFan.FanTable;

public class FanTable_Manager
{
	private string className = "[" + MethodBase.GetCurrentMethod().DeclaringType.Name + "] ";

	private MyEcCtrl EcCtrl = MyEcCtrl.Instance;

	private string m_path = new FileInfo(Assembly.GetExecutingAssembly().Location).DirectoryName + "\\FanTable\\";

	private FanTable m_F1CpuFanTable = new FanTable();

	private FanTable m_F1CpuFanTable_DC = new FanTable();

	private FanTable m_F1GpuFanTable = new FanTable();

	private FanTable m_F1GpuFanTable_DC = new FanTable();

	private FanTable m_F2CpuFanTable = new FanTable();

	private FanTable m_F2CpuFanTable_DC = new FanTable();

	private FanTable m_F2GpuFanTable = new FanTable();

	private FanTable m_F2GpuFanTable_DC = new FanTable();

	private FanTable m_F3CpuFanTable = new FanTable();

	private FanTable m_F3CpuFanTable_DC = new FanTable();

	private FanTable m_F3GpuFanTable = new FanTable();

	private FanTable m_F3GpuFanTable_DC = new FanTable();

	public void FanTable_Init()
	{
		LoadFanTableAll();
	}

	public void GetFanTable(uint _fanMode, uint _tableType, int _powerMode)
	{
		FanTable data = new FanTable();
		if (_powerMode == 1)
		{
			if (_tableType == 1)
			{
				switch (_fanMode)
				{
				case 1u:
					m_F1CpuFanTable = LoadFanTableFromJson("F1_Cpu_FanTable");
					data = m_F1CpuFanTable;
					break;
				case 2u:
					m_F2CpuFanTable = LoadFanTableFromJson("F2_Cpu_FanTable");
					data = m_F2CpuFanTable;
					break;
				case 3u:
					m_F3CpuFanTable = LoadFanTableFromJson("F3_Cpu_FanTable");
					data = m_F3CpuFanTable;
					break;
				}
			}
			else
			{
				switch (_fanMode)
				{
				case 1u:
					m_F1GpuFanTable = LoadFanTableFromJson("F1_Gpu_FanTable");
					data = m_F1GpuFanTable;
					break;
				case 2u:
					m_F2GpuFanTable = LoadFanTableFromJson("F2_Gpu_FanTable");
					data = m_F2GpuFanTable;
					break;
				case 3u:
					m_F3GpuFanTable = LoadFanTableFromJson("F3_Gpu_FanTable");
					data = m_F3GpuFanTable;
					break;
				}
			}
		}
		else if (_tableType == 1)
		{
			switch (_fanMode)
			{
			case 1u:
				m_F1CpuFanTable_DC = LoadFanTableFromJson("F1_Cpu_FanTable_DC");
				data = m_F1CpuFanTable_DC;
				break;
			case 2u:
				m_F2CpuFanTable_DC = LoadFanTableFromJson("F2_Cpu_FanTable_DC");
				data = m_F2CpuFanTable_DC;
				break;
			case 3u:
				m_F3CpuFanTable_DC = LoadFanTableFromJson("F3_Cpu_FanTable_DC");
				data = m_F3CpuFanTable_DC;
				break;
			}
		}
		else
		{
			switch (_fanMode)
			{
			case 1u:
				m_F1GpuFanTable_DC = LoadFanTableFromJson("F1_Gpu_FanTable_DC");
				data = m_F1GpuFanTable_DC;
				break;
			case 2u:
				m_F2GpuFanTable_DC = LoadFanTableFromJson("F2_Gpu_FanTable_DC");
				data = m_F2GpuFanTable_DC;
				break;
			case 3u:
				m_F3GpuFanTable_DC = LoadFanTableFromJson("F3_Gpu_FanTable_DC");
				data = m_F3GpuFanTable_DC;
				break;
			}
		}
		App.m_MQTTService.Publish("Fan/Status", data, retain: false);
	}

	public void SetFanTable(uint _fanMode, int _powerMode)
	{
		if (_powerMode == 1)
		{
			switch (_fanMode)
			{
			case 1u:
				SetCpuFanTable(m_F1CpuFanTable);
				SetGpuFanTable(m_F1GpuFanTable);
				break;
			case 2u:
				SetCpuFanTable(m_F2CpuFanTable);
				SetGpuFanTable(m_F2GpuFanTable);
				break;
			case 3u:
				SetCpuFanTable(m_F3CpuFanTable);
				SetGpuFanTable(m_F3GpuFanTable);
				break;
			}
		}
		else
		{
			switch (_fanMode)
			{
			case 1u:
				SetCpuFanTable(m_F1CpuFanTable_DC);
				SetGpuFanTable(m_F1CpuFanTable_DC);
				break;
			case 2u:
				SetCpuFanTable(m_F2CpuFanTable_DC);
				SetGpuFanTable(m_F2GpuFanTable_DC);
				break;
			case 3u:
				SetCpuFanTable(m_F3CpuFanTable_DC);
				SetGpuFanTable(m_F3GpuFanTable_DC);
				break;
			}
		}
	}

	public void SetFanTable_Test()
	{
		for (int i = 0; i <= 15; i++)
		{
			EcCtrl.Write(GetType().Name, (ushort)(3840 + i), 0);
			EcCtrl.Write(GetType().Name, (ushort)(3856 + i), 0);
			EcCtrl.Write(GetType().Name, (ushort)(3872 + i), 0);
			EcCtrl.Write(GetType().Name, (ushort)(3888 + i), 0);
			EcCtrl.Write(GetType().Name, (ushort)(3904 + i), 0);
			EcCtrl.Write(GetType().Name, (ushort)(3920 + i), 0);
		}
	}

	public void SetFanTableSetting(uint _fanMode, uint _tableType, int _powerMode, int _id, string _key, uint _value)
	{
		if (_powerMode == 1)
		{
			if (_tableType == 1)
			{
				switch (_fanMode)
				{
				case 1u:
					WriteFanTable(m_F1CpuFanTable, _id, _key, _value);
					WriteFanTableToJson("F1_Cpu_FanTable", _id, _key, _value);
					break;
				case 2u:
					WriteFanTable(m_F2CpuFanTable, _id, _key, _value);
					WriteFanTableToJson("F2_Cpu_FanTable", _id, _key, _value);
					break;
				case 3u:
					WriteFanTable(m_F3CpuFanTable, _id, _key, _value);
					WriteFanTableToJson("F3_Cpu_FanTable", _id, _key, _value);
					break;
				}
			}
			else
			{
				switch (_fanMode)
				{
				case 1u:
					WriteFanTable(m_F1GpuFanTable, _id, _key, _value);
					WriteFanTableToJson("F1_Gpu_FanTable", _id, _key, _value);
					break;
				case 2u:
					WriteFanTable(m_F2GpuFanTable, _id, _key, _value);
					WriteFanTableToJson("F2_Gpu_FanTable", _id, _key, _value);
					break;
				case 3u:
					WriteFanTable(m_F3GpuFanTable, _id, _key, _value);
					WriteFanTableToJson("F3_Gpu_FanTable", _id, _key, _value);
					break;
				}
			}
		}
		else if (_tableType == 1)
		{
			switch (_fanMode)
			{
			case 1u:
				WriteFanTable(m_F1CpuFanTable_DC, _id, _key, _value);
				WriteFanTableToJson("F1_Cpu_FanTable_DC", _id, _key, _value);
				break;
			case 2u:
				WriteFanTable(m_F2CpuFanTable_DC, _id, _key, _value);
				WriteFanTableToJson("F2_Cpu_FanTable_DC", _id, _key, _value);
				break;
			case 3u:
				WriteFanTable(m_F3CpuFanTable_DC, _id, _key, _value);
				WriteFanTableToJson("F3_Cpu_FanTable_DC", _id, _key, _value);
				break;
			}
		}
		else
		{
			switch (_fanMode)
			{
			case 1u:
				WriteFanTable(m_F1GpuFanTable_DC, _id, _key, _value);
				WriteFanTableToJson("F1_Gpu_FanTable_DC", _id, _key, _value);
				break;
			case 2u:
				WriteFanTable(m_F2GpuFanTable_DC, _id, _key, _value);
				WriteFanTableToJson("F2_Gpu_FanTable_DC", _id, _key, _value);
				break;
			case 3u:
				WriteFanTable(m_F3GpuFanTable_DC, _id, _key, _value);
				WriteFanTableToJson("F3_Gpu_FanTable_DC", _id, _key, _value);
				break;
			}
		}
	}

	public void RestoreDefaultFanTableAll()
	{
		LocalFileLoader.CopyFolderFromPath("Default", "User");
	}

	public void RestoreDefaultFanTable(uint _fanMode, uint _tableType, int _powerMode)
	{
		FanTable data = new FanTable();
		if (_powerMode == 1)
		{
			if (_tableType == 1)
			{
				switch (_fanMode)
				{
				case 1u:
					LocalFileLoader.CopyFileFromPath("F1_Cpu_FanTable");
					m_F1CpuFanTable = LoadFanTableFromJson("F1_Cpu_FanTable");
					data = m_F1CpuFanTable;
					break;
				case 2u:
					LocalFileLoader.CopyFileFromPath("F2_Cpu_FanTable");
					m_F2CpuFanTable = LoadFanTableFromJson("F2_Cpu_FanTable");
					data = m_F2CpuFanTable;
					break;
				case 3u:
					LocalFileLoader.CopyFileFromPath("F3_Cpu_FanTable");
					m_F3CpuFanTable = LoadFanTableFromJson("F3_Cpu_FanTable");
					data = m_F3CpuFanTable;
					break;
				}
			}
			else
			{
				switch (_fanMode)
				{
				case 1u:
					LocalFileLoader.CopyFileFromPath("F1_Gpu_FanTable");
					m_F1GpuFanTable = LoadFanTableFromJson("F1_Gpu_FanTable");
					data = m_F1GpuFanTable;
					break;
				case 2u:
					LocalFileLoader.CopyFileFromPath("F2_Gpu_FanTable");
					m_F2GpuFanTable = LoadFanTableFromJson("F2_Gpu_FanTable");
					data = m_F2GpuFanTable;
					break;
				case 3u:
					LocalFileLoader.CopyFileFromPath("F3_Gpu_FanTable");
					m_F3GpuFanTable = LoadFanTableFromJson("F3_Gpu_FanTable");
					data = m_F3GpuFanTable;
					break;
				}
			}
		}
		else if (_tableType == 1)
		{
			switch (_fanMode)
			{
			case 1u:
				LocalFileLoader.CopyFileFromPath("F1_Cpu_FanTable_DC");
				m_F1CpuFanTable_DC = LoadFanTableFromJson("F1_Cpu_FanTable_DC");
				data = m_F1CpuFanTable_DC;
				break;
			case 2u:
				LocalFileLoader.CopyFileFromPath("F2_Cpu_FanTable_DC");
				m_F2CpuFanTable_DC = LoadFanTableFromJson("F2_Cpu_FanTable_DC");
				data = m_F2CpuFanTable_DC;
				break;
			case 3u:
				LocalFileLoader.CopyFileFromPath("F3_Cpu_FanTable_DC");
				m_F3CpuFanTable_DC = LoadFanTableFromJson("F3_Cpu_FanTable_DC");
				data = m_F3CpuFanTable_DC;
				break;
			}
		}
		else
		{
			switch (_fanMode)
			{
			case 1u:
				LocalFileLoader.CopyFileFromPath("F1_Gpu_FanTable_DC");
				m_F1GpuFanTable_DC = LoadFanTableFromJson("F1_Gpu_FanTable_DC");
				data = m_F1GpuFanTable_DC;
				break;
			case 2u:
				LocalFileLoader.CopyFileFromPath("F2_Gpu_FanTable_DC");
				m_F2GpuFanTable_DC = LoadFanTableFromJson("F2_Gpu_FanTable_DC");
				data = m_F2GpuFanTable_DC;
				break;
			case 3u:
				LocalFileLoader.CopyFileFromPath("F3_Gpu_FanTable_DC");
				m_F3GpuFanTable_DC = LoadFanTableFromJson("F3_Gpu_FanTable_DC");
				data = m_F3GpuFanTable_DC;
				break;
			}
		}
		App.m_MQTTService.Publish("Fan/Status", data, retain: false);
	}

	private void LoadFanTableAll()
	{
		m_F1CpuFanTable = LoadFanTableFromJson("F1_Cpu_FanTable");
		m_F1CpuFanTable_DC = LoadFanTableFromJson("F1_Cpu_FanTable_DC");
		m_F1GpuFanTable = LoadFanTableFromJson("F1_Gpu_FanTable");
		m_F1GpuFanTable_DC = LoadFanTableFromJson("F1_Gpu_FanTable_DC");
		m_F2CpuFanTable = LoadFanTableFromJson("F2_Cpu_FanTable");
		m_F2CpuFanTable_DC = LoadFanTableFromJson("F2_Cpu_FanTable_DC");
		m_F2GpuFanTable = LoadFanTableFromJson("F2_Gpu_FanTable");
		m_F2GpuFanTable_DC = LoadFanTableFromJson("F2_Gpu_FanTable_DC");
		m_F3CpuFanTable = LoadFanTableFromJson("F3_Cpu_FanTable");
		m_F3CpuFanTable_DC = LoadFanTableFromJson("F3_Cpu_FanTable_DC");
		m_F3GpuFanTable = LoadFanTableFromJson("F3_Gpu_FanTable");
		m_F3GpuFanTable_DC = LoadFanTableFromJson("F3_Gpu_FanTable_DC");
	}

	private FanTable LoadFanTableFromJson(string _fileName)
	{
		FanTable result = new FanTable();
		dynamic val = LocalFileLoader.LoadJsonFromPath_NonAsync<object>(m_path, _fileName + ".json", Assembly.GetExecutingAssembly());
		if (val != null)
		{
			result = JsonConvert.DeserializeObject<FanTable>(Json.Stringify(val));
		}
		return result;
	}

	private void WriteFanTable(FanTable _fanTable, int _id, string _key, uint _value)
	{
		switch (_key)
		{
		case "UpT":
			_fanTable.Table[_id].UpT = (byte)_value;
			break;
		case "DownT":
			_fanTable.Table[_id].DownT = (byte)_value;
			break;
		case "Duty":
			_fanTable.Table[_id].Duty = (byte)_value;
			break;
		}
	}

	private void WriteFanTableToJson(string _fileName, int _id, string _key, uint _value)
	{
		try
		{
			string path = new FileInfo(Assembly.GetExecutingAssembly().Location).DirectoryName + "\\FanTable\\User\\" + _fileName + ".json";
			if (File.Exists(path))
			{
				dynamic val = JsonConvert.DeserializeObject(File.ReadAllText(path));
				val["Table"][_id][_key] = _value;
				string contents = JsonConvert.SerializeObject(val, Formatting.Indented);
				File.WriteAllText(path, contents);
			}
		}
		catch
		{
		}
	}

	private void ObjectToJson(FanTable _fanTable, string _outputFolderName, string _outputFileName)
	{
		try
		{
			string text = new FileInfo(Assembly.GetExecutingAssembly().Location).DirectoryName + "\\FanTable\\" + _outputFolderName;
			string path = text + "\\" + _outputFileName + ".json";
			if (!Directory.Exists(text))
			{
				Directory.CreateDirectory(text);
			}
			string contents = JsonConvert.SerializeObject(_fanTable, Formatting.Indented);
			File.WriteAllText(path, contents);
		}
		catch
		{
		}
	}

	private void SetCpuFanTable(FanTable _fantable)
	{
		if (_fantable.Table == null)
		{
			return;
		}
		for (int i = 0; i <= 15; i++)
		{
			if (i < 15)
			{
				EcCtrl.Write(GetType().Name, (ushort)(3840 + i), _fantable.Table[i + 1].UpT);
			}
			else
			{
				EcCtrl.Write(GetType().Name, (ushort)(3840 + i), byte.MaxValue);
			}
			if (i < 15)
			{
				EcCtrl.Write(GetType().Name, (ushort)(3856 + (i + 1)), _fantable.Table[i].DownT);
			}
			EcCtrl.Write(GetType().Name, (ushort)(3872 + i), (byte)(_fantable.Table[i].Duty * 2));
		}
	}

	private void SetGpuFanTable(FanTable _fantable)
	{
		if (_fantable.Table == null)
		{
			return;
		}
		for (int i = 0; i <= 15; i++)
		{
			if (i < 15)
			{
				EcCtrl.Write(GetType().Name, (ushort)(3888 + i), _fantable.Table[i + 1].UpT);
			}
			else
			{
				EcCtrl.Write(GetType().Name, (ushort)(3888 + i), byte.MaxValue);
			}
			if (i < 15)
			{
				EcCtrl.Write(GetType().Name, (ushort)(3904 + (i + 1)), _fantable.Table[i].DownT);
			}
			EcCtrl.Write(GetType().Name, (ushort)(3920 + i), (byte)(_fantable.Table[i].Duty * 2));
		}
	}

	private void ClearFanTable_Test()
	{
		for (int i = 0; i <= 15; i++)
		{
			EcCtrl.Write(GetType().Name, (ushort)(3840 + i), 0);
			EcCtrl.Write(GetType().Name, (ushort)(3856 + i), 0);
			EcCtrl.Write(GetType().Name, (ushort)(3872 + i), 0);
			EcCtrl.Write(GetType().Name, (ushort)(3888 + i), 0);
			EcCtrl.Write(GetType().Name, (ushort)(3904 + i), 0);
			EcCtrl.Write(GetType().Name, (ushort)(3920 + i), 0);
		}
	}

	private void CreateFanTableFileFromEC(uint _fanMode, string _outputFolderName)
	{
		FanTable fanTable = new FanTable();
		FanTable fanTable2 = new FanTable();
		byte Data = 0;
		for (int i = 0; i <= 15; i++)
		{
			EcCtrl.Read(GetType().Name, (ushort)(3840 + i), ref Data);
			fanTable.Table[i].UpT = Data;
			EcCtrl.Read(GetType().Name, (ushort)(3856 + i), ref Data);
			fanTable.Table[i].DownT = Data;
			EcCtrl.Read(GetType().Name, (ushort)(3872 + i), ref Data);
			fanTable.Table[i].Duty = (byte)(Data / 2);
			EcCtrl.Read(GetType().Name, (ushort)(3888 + i), ref Data);
			fanTable2.Table[i].UpT = Data;
			EcCtrl.Read(GetType().Name, (ushort)(3904 + i), ref Data);
			fanTable2.Table[i].DownT = Data;
			EcCtrl.Read(GetType().Name, (ushort)(3920 + i), ref Data);
			fanTable2.Table[i].Duty = (byte)(Data / 2);
		}
		if (fanTable.Table != null && fanTable2.Table != null)
		{
			switch (_fanMode)
			{
			case 1u:
				ObjectToJson(fanTable, _outputFolderName, "F1_Cpu_FanTable");
				ObjectToJson(fanTable, _outputFolderName, "F1_Cpu_FanTable_DC");
				ObjectToJson(fanTable2, _outputFolderName, "F1_Gpu_FanTable");
				ObjectToJson(fanTable2, _outputFolderName, "F1_Gpu_FanTable_DC");
				break;
			case 2u:
				ObjectToJson(fanTable, _outputFolderName, "F2_Cpu_FanTable");
				ObjectToJson(fanTable, _outputFolderName, "F2_Cpu_FanTable_DC");
				ObjectToJson(fanTable2, _outputFolderName, "F2_Gpu_FanTable");
				ObjectToJson(fanTable2, _outputFolderName, "F2_Gpu_FanTable_DC");
				break;
			case 3u:
				ObjectToJson(fanTable, _outputFolderName, "F3_Cpu_FanTable");
				ObjectToJson(fanTable, _outputFolderName, "F3_Cpu_FanTable_DC");
				ObjectToJson(fanTable2, _outputFolderName, "F3_Gpu_FanTable");
				ObjectToJson(fanTable2, _outputFolderName, "F3_Gpu_FanTable_DC");
				break;
			}
		}
	}
}
