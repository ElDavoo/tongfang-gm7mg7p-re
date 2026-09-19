using System;
using System.Collections;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Threading;
using Define;
using MyControlCenter.MyFan.FanTable;
using MyECIO;
using Newtonsoft.Json;
using Utility;

namespace MyControlCenter.MyFan;

internal class MyFanManager_RamFan1p5_Normal : MyFanManager
{
	private MyEcCtrl EcCtrl = MyEcCtrl.Instance;

	private string m_path = new FileInfo(Assembly.GetExecutingAssembly().Location).DirectoryName + "\\UserPofiles";

	private Dispatcher _dispatcher;

	private bool m_bInit;

	private bool m_IsNvGpu;

	private uint m_DefaultMode;

	private bool m_FanBoostBtnSupport = true;

	private MainOption m_Option = new MainOption();

	private PLDefaultValue GamingModePLDefaultValue = new PLDefaultValue();

	private PLDefaultValue OfficeModePLDefaultValue = new PLDefaultValue();

	private PLDefaultValue TurboModePLDefaultValue = new PLDefaultValue();

	private ModeProfile currentProfile = new ModeProfile();

	private ModeProfile Mode1_Profile1 = new ModeProfile();

	private ModeProfile Mode2_Profile1 = new ModeProfile();

	private SemaphoreSlim FansemporeSlim3 = new SemaphoreSlim(1, 1);

	private Stopwatch stopwatch3 = new Stopwatch();

	private string LastCommand3;

	private SemaphoreSlim FansemporeSlim4 = new SemaphoreSlim(1, 1);

	private Stopwatch stopwatch4 = new Stopwatch();

	private void SetDispatcher(Dispatcher dispatcher)
	{
		_dispatcher = dispatcher;
	}

	public override int GetTurboModeSupportFlag()
	{
		return g_TurboModeSupport;
	}

	public override void EnableByService(Dispatcher dispatcher = null)
	{
		SetDispatcher(dispatcher);
		g_TurboModeSupport = EcCtrl.GetTurboModeSupport();
		LogCtrl.TraceMessage("g_TurboModeSupport: " + g_TurboModeSupport, "EnableByService", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5_Normal.cs", 79);
		m_DefaultMode = GetDefaultMode();
		LogCtrl.TraceMessage("m_DefaultMode: " + m_DefaultMode, "EnableByService", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5_Normal.cs", 82);
		g_QkeyDefine = GetQkeyDefine();
		LogCtrl.TraceMessage("g_QkeyDefine: " + g_QkeyDefine, "EnableByService", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5_Normal.cs", 85);
		m_FanBoostBtnSupport = CustomizeCtrl.GetFanBoostBtnSupport();
		LogCtrl.TraceMessage("m_FanBoostBtnSupport: " + m_FanBoostBtnSupport, "EnableByService", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5_Normal.cs", 88);
		LoadProfileAll();
		syncBiosSettings();
		Init();
		m_bInit = true;
	}

	public override void Disable()
	{
		m_DefaultMode = GetDefaultMode();
		LogCtrl.TraceMessage("m_DefaultMode: " + m_DefaultMode, "Disable", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5_Normal.cs", 101);
		SetFanMode(m_DefaultMode);
	}

	public override async void Receive(byte[] data)
	{
		dynamic val = await Json.ToObjectAsync<object>(Encoding.UTF8.GetString(data));
		string text = Convert.ToString(val["Action"]);
		LogCtrl.TraceMessage("---------------" + LogCtrl.GetTime() + "---------------", "Receive", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5_Normal.cs", 111);
		LogCtrl.TraceMessage("Action = " + text, "Receive", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5_Normal.cs", 112);
		switch (text)
		{
		case "GETSTATUS":
			if (m_bInit)
			{
				UpdateStatusToClient(1);
			}
			break;
		case "DEFAULT":
			UserSet_Default();
			UpdateStatusToClient(1);
			break;
		case "FAN_BOOST_ON":
			UserSet_FanBoost(1u);
			UpdateStatusToClient(1);
			break;
		case "FAN_BOOST_OFF":
			UserSet_FanBoost(0u);
			UpdateStatusToClient(1);
			break;
		case "OPERATING_GAMING_MODE":
			SetOperatingModeProfileIndexThread("M1P1");
			break;
		case "OPERATING_OFFICE_MODE":
			SetOperatingModeProfileIndexThread("M2P1");
			break;
		case "TestModeSwitch":
			ModeSwitchChanged();
			break;
		}
	}

	public override void UpdateStatusToClient(int autosave = 1, int cpuusage = 0, int cputemp = 0, bool updateOperationMode = true)
	{
		var data = new
		{
			OperatingMode = Convert.ToString(m_Option.OperatingMode),
			FanBoostEnable = Convert.ToString(m_Option.FanBoostEnable),
			ProfileName = currentProfile.Name,
			FAN_FanSwitchSpeed = Convert.ToString(currentProfile.FAN.FanSwitchSpeed),
			FAN_TableName = currentProfile.FAN.TableName,
			OcSupport = false,
			IsNvGpu = false,
			TurboModeOption = Convert.ToString(g_TurboModeSupport),
			FanBoostBtnSupport = m_FanBoostBtnSupport,
			PowerMode = Convert.ToString(PowerModeEvent.g_ACLineStatus)
		};
		App.m_MQTTService.Publish("Fan/Status", data, retain: false);
	}

	public override void UpdateStatusToTray()
	{
		var data = new
		{
			OperatingMode = Convert.ToString(m_Option.OperatingMode)
		};
		App.m_MQTTService.Publish("Tray/Status", data, retain: false);
	}

	public override void Resume()
	{
		LoadProfileAll();
		Init();
	}

	public override void OnModernStandby()
	{
	}

	public override void PowerStatusChange(int mode)
	{
		Init();
	}

	public override void Uninstall()
	{
		m_DefaultMode = GetDefaultMode();
		SetFanMode(m_DefaultMode);
		NvramVariable.SetFwVars("PowerMode", Convert.ToByte(m_DefaultMode));
		NvramVariable.SetFwVars("ApExistFlag", 0);
	}

	public override void Restore()
	{
		LoadDefault();
		Init();
	}

	public override void ModeSwitchChanged()
	{
		SetModeSwitchChangeThread();
	}

	public override void FanBoostUpdate()
	{
		App.m_Osd.SetOsdWay(167);
		byte Data = 0;
		EcCtrl.Read(GetType().Name, 1873, ref Data);
		if (((byte)(Convert.ToUInt64(Data) & 0xC0) & 0x40) == 64)
		{
			m_Option.FanBoostEnable = 1u;
		}
		else
		{
			m_Option.FanBoostEnable = 0u;
		}
		SetFanMode(m_Option.OperatingMode);
		WriteMainOptionToJson("FanBoostEnable", m_Option.FanBoostEnable);
		UpdateStatusToClient(1);
	}

	public override void FanBoostOffFromEC()
	{
		m_Option.FanBoostEnable = 0u;
		SetFanMode(m_Option.OperatingMode);
		WriteMainOptionToJson("FanBoostEnable", m_Option.FanBoostEnable);
		UpdateStatusToClient(1);
	}

	public override void SafetyProtectionUpdate()
	{
	}

	public override void WhisperUpdate()
	{
	}

	public override void UserSet_Mode1()
	{
		m_Option.OperatingMode = 1u;
		RefreshCurrentProfile(m_Option.OperatingMode, save: false);
		SetUserProfile(1u);
		WriteMainOptionToJson("OperatingMode", 1u);
		NvramVariable.SetFwVars("PowerMode", Convert.ToByte(1u));
	}

	public override void UserSet_Mode2()
	{
		m_Option.OperatingMode = 0u;
		RefreshCurrentProfile(m_Option.OperatingMode, save: false);
		SetUserProfile(0u);
		WriteMainOptionToJson("OperatingMode", 0u);
		NvramVariable.SetFwVars("PowerMode", Convert.ToByte(0u));
	}

	public override void UserSet_Mode3()
	{
	}

	public override void SetPairedProfileIndex(uint index)
	{
	}

	private void UserSet_Default()
	{
		Restore();
	}

	private void UserSet_FanBoost(uint status)
	{
		m_Option.FanBoostEnable = status;
		SetFanMode(m_Option.OperatingMode);
		WriteMainOptionToJson("FanBoostEnable", status);
	}

	private void LoadProfileAll()
	{
		GetGamingPLDefaultValue(ref GamingModePLDefaultValue.PL1, ref GamingModePLDefaultValue.PL2, ref GamingModePLDefaultValue.PL4, ref GamingModePLDefaultValue.DState);
		GetOfficePLDefaultValue(ref OfficeModePLDefaultValue.PL1, ref OfficeModePLDefaultValue.PL2, ref OfficeModePLDefaultValue.PL4, ref OfficeModePLDefaultValue.DState);
		GetTurboPLDefaultValue(ref TurboModePLDefaultValue.PL1, ref TurboModePLDefaultValue.PL2, ref TurboModePLDefaultValue.PL4, ref TurboModePLDefaultValue.DState);
		if (Directory.Exists(m_path))
		{
			m_Option = LoadMainOptionFromJson("MainOption");
			Mode1_Profile1 = LoadProfileFromJson("Mode1_Profile1");
			Mode2_Profile1 = LoadProfileFromJson("Mode2_Profile1");
			RefreshDefaultProfiles();
		}
		else
		{
			LoadDefault();
		}
		if (g_TurboModeSupport == 0 && m_Option.OperatingMode == 2)
		{
			m_Option.OperatingMode = m_DefaultMode;
		}
	}

	private void RefreshDefaultProfiles()
	{
		if (!Mode1_Profile1.Activated)
		{
			RefreshMode(ref Mode1_Profile1, "Mode1_Profile1", "1", GamingModePLDefaultValue, "M1T1");
			CreateModeProfiles(Mode1_Profile1);
		}
		if (!Mode2_Profile1.Activated)
		{
			RefreshMode(ref Mode2_Profile1, "Mode2_Profile1", "1", OfficeModePLDefaultValue, "M2T1");
			CreateModeProfiles(Mode2_Profile1);
		}
	}

	private void LoadDefault()
	{
		m_Option.OperatingMode = m_DefaultMode;
		m_Option.GamingProfileIndex = 0u;
		m_Option.OfficeProfileIndex = 0u;
		m_Option.TurboProfileIndex = 0u;
		m_Option.FanBoostEnable = 0u;
		m_Option.DefaultNotify = 0u;
		CreateMainOption(m_Option);
		RefreshMode(ref Mode1_Profile1, "Mode1_Profile1", "1", GamingModePLDefaultValue, "M1T1");
		RefreshMode(ref Mode2_Profile1, "Mode2_Profile1", "1", OfficeModePLDefaultValue, "M2T1");
		CreateModeProfiles(Mode1_Profile1);
		CreateModeProfiles(Mode2_Profile1);
	}

	private void RefreshMode(ref ModeProfile profile, string name, string customizeName, PLDefaultValue defaultValue, string fanTableName)
	{
		profile.Activated = false;
		profile.Name = name;
		profile.CustomizeName = customizeName;
		profile.FAN.FanSwitchSpeed = 300;
		profile.FAN.TableName = fanTableName;
		profile.CPU.PL1 = defaultValue.PL1;
		profile.CPU.PL2 = defaultValue.PL2;
		profile.CPU.TccOffset = 5;
		profile.CPU.AmdSPL = defaultValue.PL1;
		profile.CPU.AmdSPPT = defaultValue.PL2;
		profile.CPU.AmdTccTarget = 95;
	}

	private void CreateMainOption(MainOption option)
	{
		try
		{
			string path = m_path + "\\MainOption.json";
			if (!Directory.Exists(m_path))
			{
				Directory.CreateDirectory(m_path);
			}
			string contents = JsonConvert.SerializeObject(option, Formatting.Indented);
			File.WriteAllText(path, contents);
		}
		catch (Exception ex)
		{
			LogCtrl.TraceMessage("Exception" + ex.Message, "CreateMainOption", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5_Normal.cs", 490);
		}
	}

	private void CreateModeProfiles(ModeProfile profile)
	{
		try
		{
			string path = m_path + "\\" + profile.Name + ".json";
			if (!Directory.Exists(m_path))
			{
				Directory.CreateDirectory(m_path);
			}
			string contents = JsonConvert.SerializeObject(profile, Formatting.Indented);
			File.WriteAllText(path, contents);
		}
		catch (Exception ex)
		{
			LogCtrl.TraceMessage("Exception" + ex.Message, "CreateModeProfiles", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5_Normal.cs", 508);
		}
	}

	private MainOption LoadMainOptionFromJson(string fileName)
	{
		MainOption result = new MainOption();
		dynamic val = LocalFileLoader.LoadJsonFromPath_NonAsync<object>(m_path, fileName, Assembly.GetExecutingAssembly());
		if (val != null)
		{
			result = JsonConvert.DeserializeObject<MainOption>(Json.Stringify(val));
		}
		return result;
	}

	private ModeProfile LoadProfileFromJson(string fileName)
	{
		ModeProfile result = new ModeProfile();
		dynamic val = LocalFileLoader.LoadJsonFromPath_NonAsync<object>(m_path, fileName, Assembly.GetExecutingAssembly());
		if (val != null)
		{
			result = JsonConvert.DeserializeObject<ModeProfile>(Json.Stringify(val));
		}
		return result;
	}

	private void WriteMainOptionToJson(string key, uint value)
	{
		try
		{
			string path = m_path + "\\MainOption.json";
			if (File.Exists(path))
			{
				dynamic val = JsonConvert.DeserializeObject(File.ReadAllText(path));
				val[key] = value;
				string contents = JsonConvert.SerializeObject(val, Formatting.Indented);
				File.WriteAllText(path, contents);
			}
		}
		catch (Exception ex)
		{
			LogCtrl.TraceMessage("Exception" + ex.Message, "WriteMainOptionToJson", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5_Normal.cs", 560);
		}
	}

	private void WriteProfileToJson(ModeProfile profile)
	{
		try
		{
			string path = m_path + "\\" + profile.Name + ".json";
			profile.Activated = true;
			string contents = JsonConvert.SerializeObject(profile, Formatting.Indented);
			File.WriteAllText(path, contents);
		}
		catch (Exception ex)
		{
			LogCtrl.TraceMessage("Exception" + ex.Message, "WriteProfileToJson", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5_Normal.cs", 576);
		}
	}

	private void syncBiosSettings()
	{
		NvramVariable.SetFwVars("ApExistFlag", 1);
		uint num = Convert.ToUInt32(NvramVariable.GetFwVars().PowerMode);
		LogCtrl.TraceMessage("PowerMode = 0x" + num.ToString("X2"), "syncBiosSettings", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5_Normal.cs", 587);
		if (num != 255)
		{
			if (m_Option.OperatingMode != num)
			{
				LogCtrl.TraceMessage("Change local Power Mode.", "syncBiosSettings", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5_Normal.cs", 593);
				m_Option.OperatingMode = num;
				WriteMainOptionToJson("OperatingMode", m_Option.OperatingMode);
			}
		}
		else
		{
			LogCtrl.TraceMessage("NvramVariable Power Mode = 0XFF, then change to default Power Mode.", "syncBiosSettings", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5_Normal.cs", 600);
			m_Option.OperatingMode = m_DefaultMode;
			WriteMainOptionToJson("OperatingMode", m_Option.OperatingMode);
		}
	}

	private void Init()
	{
		LogCtrl.TraceMessage("OperatingMode = " + m_Option.OperatingMode + ", " + OperatingModeString(m_Option.OperatingMode), "Init", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5_Normal.cs", 630);
		RefreshCurrentProfile(m_Option.OperatingMode, save: false);
		SetUserProfile(m_Option.OperatingMode);
	}

	private void RefreshCurrentProfile(uint mode, bool save = true)
	{
		switch (mode)
		{
		case 1u:
			currentProfile = Mode1_Profile1;
			break;
		case 0u:
			currentProfile = Mode2_Profile1;
			break;
		}
		if (save)
		{
			WriteProfileToJson(currentProfile);
		}
	}

	private void SetUserProfile(uint mode)
	{
		SetFanMode(mode);
		UpdateStatusToTray();
		SkipFanSafetyAbnormalProtection(currentProfile.FAN.SkipSafetyAbnormalProtection);
		if (CustomizeCtrl.GetIsAMDPlatform())
		{
			if (PowerModeEvent.g_ACLineStatus == 1)
			{
				SetPL1Value(currentProfile.CPU.AmdSPL);
				SetPL2Value(currentProfile.CPU.AmdSPPT);
			}
			else
			{
				SetPL1Value(0);
				SetPL2Value(0);
			}
		}
		else if (PowerModeEvent.g_ACLineStatus == 1)
		{
			SetPL1Value(currentProfile.CPU.PL1);
			SetPL2Value(currentProfile.CPU.PL2);
		}
		else
		{
			SetPL1Value(0);
			SetPL2Value(0);
		}
	}

	private void SetFanMode(uint mode)
	{
		switch (mode)
		{
		case 1u:
			if (m_Option.FanBoostEnable == 1)
			{
				BitArray bitArray3 = new BitArray(new byte[1]);
				bitArray3[6] = true;
				EcCtrl.Write(GetType().Name, 1873, ConvertToByte(bitArray3));
			}
			else
			{
				EcCtrl.Write(GetType().Name, 1873, 0);
			}
			break;
		case 0u:
			if (m_Option.FanBoostEnable == 1)
			{
				BitArray bitArray2 = new BitArray(new byte[1] { 160 });
				bitArray2[6] = true;
				EcCtrl.Write(GetType().Name, 1873, ConvertToByte(bitArray2));
			}
			else
			{
				EcCtrl.Write(GetType().Name, 1873, 160);
			}
			break;
		case 2u:
			if (m_Option.FanBoostEnable == 1)
			{
				BitArray bitArray = new BitArray(new byte[1] { 16 });
				bitArray[6] = true;
				EcCtrl.Write(GetType().Name, 1873, ConvertToByte(bitArray));
			}
			else
			{
				EcCtrl.Write(GetType().Name, 1873, 16);
			}
			break;
		}
	}

	internal byte ConvertToByte(BitArray bits)
	{
		_ = bits.Count;
		_ = 8;
		byte[] array = new byte[1];
		bits.CopyTo(array, 0);
		return array[0];
	}

	private void SetFanBoost(uint status)
	{
		byte Data = 0;
		EcCtrl.Read(GetType().Name, 1873, ref Data);
		byte b = (byte)Convert.ToUInt64(Data);
		b = ((status != 1) ? ((byte)(b & 0xBF)) : ((byte)(b | 0x40)));
		EcCtrl.Write(GetType().Name, 1873, b);
	}

	private uint GetFanMode()
	{
		uint result = 0u;
		byte Data = 0;
		EcCtrl.Read(GetType().Name, 1873, ref Data);
		byte data = (byte)Convert.ToUInt64(Data);
		int bitFromByte = UtilityExtensions.GetBitFromByte(data, 4);
		int bitFromByte2 = UtilityExtensions.GetBitFromByte(data, 7);
		if (bitFromByte == 0 && bitFromByte2 == 0)
		{
			result = 0u;
		}
		else if (bitFromByte == 0 && bitFromByte2 == 1)
		{
			result = 1u;
		}
		else if (bitFromByte == 1 && bitFromByte2 == 0)
		{
			result = 2u;
		}
		LogCtrl.TraceMessage($"EC 0751 bit4[{bitFromByte}], bit7[{bitFromByte2}]", "GetFanMode", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5_Normal.cs", 800);
		return result;
	}

	private void SetPL1Value(int value)
	{
		EcCtrl.Write(GetType().Name, 1923, (byte)value);
	}

	private void SetPL2Value(int value)
	{
		EcCtrl.Write(GetType().Name, 1924, (byte)value);
	}

	private void SetPL4Value(int value)
	{
		EcCtrl.Write(GetType().Name, 1925, (byte)value);
	}

	private void SetCpuTccOffset(int value, bool bApExist)
	{
		byte b = 0;
		if (bApExist)
		{
			b = (byte)(value | 0x80);
			EcCtrl.Write(GetType().Name, 1926, b);
		}
		else
		{
			EcCtrl.Write(GetType().Name, 1926, 0);
		}
	}

	private void SetFanSwitchSpeed(int value, bool bApExist)
	{
		byte b = 0;
		if (bApExist)
		{
			int num = value / 100;
			if (num > 0)
			{
				b = (byte)(num | 0x80);
				EcCtrl.Write(GetType().Name, 1927, b);
			}
		}
		else
		{
			EcCtrl.Write(GetType().Name, 1927, 0);
		}
	}

	private void SetGPUdstate(uint dstate)
	{
		byte Data = 0;
		EcCtrl.Read(GetType().Name, 1931, ref Data);
		ulong num = Convert.ToUInt64(Data);
		num &= 0xF8;
		num |= dstate;
		EcCtrl.Write(GetType().Name, 1931, (byte)num);
		LogCtrl.TraceMessage("Set D-State to: " + dstate, "SetGPUdstate", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5_Normal.cs", 890);
	}

	private void SetGPUdstateByGpuMode(uint G)
	{
		uint num = 1u;
		switch (G)
		{
		case 1u:
		case 2u:
		case 4u:
			num = 1u;
			break;
		case 3u:
			num = 2u;
			break;
		}
		byte Data = 0;
		EcCtrl.Read(GetType().Name, 1931, ref Data);
		ulong num2 = Convert.ToUInt64(Data);
		num2 &= 0xF8;
		num2 |= num;
		EcCtrl.Write(GetType().Name, 1931, (byte)num2);
		LogCtrl.TraceMessage("Set D-State to: " + num, "SetGPUdstateByGpuMode", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5_Normal.cs", 921);
	}

	private uint GetQkeyDefine()
	{
		byte Data = 0;
		EcCtrl.Read(GetType().Name, 1922, ref Data);
		if ((byte)(Convert.ToUInt64(Data) & 2) == 2)
		{
			return 1u;
		}
		return 0u;
	}

	private int GetOfficeModeFanTableType()
	{
		int num = 0;
		byte Data = 0;
		EcCtrl.Read(GetType().Name, 1922, ref Data);
		if ((byte)(Convert.ToUInt64(Data) & 4) == 4)
		{
			return 2;
		}
		return 1;
	}

	private uint GetDefaultMode()
	{
		byte Data = 0;
		EcCtrl.Read(GetType().Name, 1922, ref Data);
		if ((byte)(Convert.ToUInt64(Data) & 0x10) == 0)
		{
			return 0u;
		}
		return 1u;
	}

	private void SetPowerLedStatus(uint mode)
	{
		byte Data = 0;
		byte b = 252;
		byte b2 = 0;
		byte b3 = 0;
		switch (mode)
		{
		case 2u:
			b2 = 0;
			break;
		case 1u:
			b2 = 1;
			break;
		case 3u:
			b2 = 2;
			break;
		case 4u:
			b2 = 1;
			break;
		}
		EcCtrl.Read(GetType().Name, 1957, ref Data);
		b3 = (byte)((Data & b) + b2);
		LogCtrl.TraceMessage("Mode: " + mode + ", Set ECRAM 0x" + ((ushort)1957).ToString("X") + " = 0x" + b3.ToString("X2"), "SetPowerLedStatus", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5_Normal.cs", 1003);
		EcCtrl.Write(GetType().Name, 1957, b3);
	}

	private void SetFanQuietModeEnable(bool bEnable)
	{
		byte Data = 0;
		byte b = 251;
		byte b2 = 0;
		byte b3 = 0;
		b2 = (byte)(bEnable ? 4 : 0);
		EcCtrl.Read(GetType().Name, 1957, ref Data);
		b3 = (byte)((Data & b) + b2);
		LogCtrl.TraceMessage("bEnable " + bEnable + ", Set ECRAM 0x" + ((ushort)1957).ToString("X") + " = 0x" + b3.ToString("X2"), "SetFanQuietModeEnable", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5_Normal.cs", 1024);
		EcCtrl.Write(GetType().Name, 1957, b3);
	}

	private void SetOverBoostMode(bool bEnable)
	{
		byte Data = 0;
		byte b = 239;
		byte b2 = 0;
		byte b3 = 0;
		b2 = (byte)(bEnable ? 16 : 0);
		EcCtrl.Read(GetType().Name, 1957, ref Data);
		b3 = (byte)((Data & b) + b2);
		LogCtrl.TraceMessage("bEnable " + bEnable + ", Set ECRAM 0x" + ((ushort)1957).ToString("X") + " = 0x" + b3.ToString("X2"), "SetOverBoostMode", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5_Normal.cs", 1045);
		EcCtrl.Write(GetType().Name, 1957, b3);
	}

	private void SetPowerStatus(bool bHigh)
	{
		byte Data = 0;
		byte b = 127;
		byte b2 = 0;
		byte b3 = 0;
		b2 = (byte)(bHigh ? 128 : 0);
		EcCtrl.Read(GetType().Name, 1957, ref Data);
		b3 = (byte)((Data & b) + b2);
		LogCtrl.TraceMessage("bHigh " + bHigh + ", Set ECRAM 0x" + ((ushort)1957).ToString("X") + " = 0x" + b3.ToString("X2"), "SetPowerStatus", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5_Normal.cs", 1066);
		EcCtrl.Write(GetType().Name, 1957, b3);
	}

	private void SetOverBoostByDynamicTemp(bool bEnable)
	{
		byte Data = 0;
		byte b = 253;
		byte b2 = 0;
		byte b3 = 0;
		b2 = (byte)((!bEnable) ? 2 : 0);
		EcCtrl.Read(GetType().Name, 1958, ref Data);
		b3 = (byte)((Data & b) + b2);
		LogCtrl.TraceMessage("bEnable " + bEnable + ", Set ECRAM 0x" + ((ushort)1958).ToString("X") + " = 0x" + b3.ToString("X2"), "SetOverBoostByDynamicTemp", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5_Normal.cs", 1089);
		EcCtrl.Write(GetType().Name, 1958, b3);
	}

	private void GetGamingPLDefaultValue(ref int PL1, ref int PL2, ref int PL4, ref int DState)
	{
		byte Data = 0;
		byte Data2 = 0;
		byte Data3 = 0;
		byte Data4 = 0;
		EcCtrl.Read(GetType().Name, 1840, ref Data);
		EcCtrl.Read(GetType().Name, 1841, ref Data2);
		EcCtrl.Read(GetType().Name, 1842, ref Data3);
		EcCtrl.Read(GetType().Name, 1843, ref Data4);
		PL1 = (int)(Convert.ToUInt64(Data) & 0xFF);
		PL2 = (int)(Convert.ToUInt64(Data2) & 0xFF);
		PL4 = (int)(Convert.ToUInt64(Data3) & 0xFF);
		DState = (int)(Convert.ToUInt64(Data4) & 0xFF);
		LogCtrl.TraceMessage("PL1:" + PL1 + ", PL2:" + PL2 + ", PL4:" + PL4 + ", DState:" + DState, "GetGamingPLDefaultValue", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5_Normal.cs", 1109);
	}

	private void GetOfficePLDefaultValue(ref int PL1, ref int PL2, ref int PL4, ref int DState)
	{
		byte Data = 0;
		byte Data2 = 0;
		byte Data3 = 0;
		byte Data4 = 0;
		EcCtrl.Read(GetType().Name, 1844, ref Data);
		EcCtrl.Read(GetType().Name, 1845, ref Data2);
		EcCtrl.Read(GetType().Name, 1846, ref Data3);
		EcCtrl.Read(GetType().Name, 1847, ref Data4);
		PL1 = (int)(Convert.ToUInt64(Data) & 0xFF);
		PL2 = (int)(Convert.ToUInt64(Data2) & 0xFF);
		PL4 = (int)(Convert.ToUInt64(Data3) & 0xFF);
		DState = (int)(Convert.ToUInt64(Data4) & 0xFF);
		LogCtrl.TraceMessage("PL1:" + PL1 + ", PL2:" + PL2 + ", PL4:" + PL4 + ", DState:" + DState, "GetOfficePLDefaultValue", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5_Normal.cs", 1126);
	}

	private void GetTurboPLDefaultValue(ref int PL1, ref int PL2, ref int PL4, ref int DState)
	{
		byte Data = 0;
		byte Data2 = 0;
		byte Data3 = 0;
		byte Data4 = 0;
		EcCtrl.Read(GetType().Name, 1959, ref Data);
		EcCtrl.Read(GetType().Name, 1960, ref Data2);
		EcCtrl.Read(GetType().Name, 1961, ref Data3);
		EcCtrl.Read(GetType().Name, 1962, ref Data4);
		PL1 = (int)(Convert.ToUInt64(Data) & 0xFF);
		PL2 = (int)(Convert.ToUInt64(Data2) & 0xFF);
		PL4 = (int)(Convert.ToUInt64(Data3) & 0xFF);
		DState = (int)(Convert.ToUInt64(Data4) & 0xFF);
		LogCtrl.TraceMessage("PL1:" + PL1 + ", PL2:" + PL2 + ", PL4:" + PL4 + ", DState:" + DState, "GetTurboPLDefaultValue", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5_Normal.cs", 1143);
	}

	private int GetTauDefaultValue()
	{
		int num = 0;
		byte Data = 0;
		EcCtrl.Read(GetType().Name, 1848, ref Data);
		num = (int)(Convert.ToUInt64(Data) & 0xFF);
		if (num == 0)
		{
			num = 56;
		}
		return num;
	}

	private void SkipFanSafetyAbnormalProtection(int status)
	{
		byte Data = 0;
		byte b = 239;
		byte b2 = 0;
		byte b3 = 0;
		b2 = (byte)((status == 1) ? 16 : 0);
		EcCtrl.Read(GetType().Name, 1989, ref Data);
		b3 = (byte)((Data & b) + b2);
		EcCtrl.Write(GetType().Name, 1989, b3);
		LogCtrl.TraceMessage("status:" + status, "SkipFanSafetyAbnormalProtection", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5_Normal.cs", 1179);
	}

	private void SetGpuWhisperModeSwitch(int status)
	{
		byte Data = 0;
		byte b = 159;
		byte b2 = 0;
		byte b3 = 0;
		b2 = (byte)((status != 1) ? 64 : 96);
		EcCtrl.Read(GetType().Name, 1989, ref Data);
		b3 = (byte)((Data & b) + b2);
		EcCtrl.Write(GetType().Name, 1989, b3);
	}

	private void SetGpuDynamicBoostEnable(int status)
	{
		byte Data = 0;
		byte b = 252;
		byte b2 = 0;
		byte b3 = 0;
		b2 = (byte)((status == 1) ? 3 : 0);
		EcCtrl.Read(GetType().Name, 1859, ref Data);
		b3 = (byte)((Data & b) + b2);
		EcCtrl.Write(GetType().Name, 1859, b3);
	}

	private void SetGpuConfigurableTGP(int value)
	{
		EcCtrl.Write(GetType().Name, 1860, Convert.ToByte(value));
	}

	private void SetGpuDynamicBoostTotalProcessingPowerTarget(int value)
	{
		EcCtrl.Write(GetType().Name, 1861, Convert.ToByte(value));
	}

	private void SetGpuDynamicBoostMaxinumTGP(int value)
	{
		EcCtrl.Write(GetType().Name, 1862, Convert.ToByte(value));
	}

	private string OperatingModeString(uint mode)
	{
		return mode switch
		{
			0u => "Office mode", 
			1u => "Gaming mode", 
			2u => "Turbo mode", 
			_ => "", 
		};
	}

	private uint TransToGlobalType(uint mode)
	{
		uint result = 1u;
		switch (mode)
		{
		case 0u:
			result = 1u;
			break;
		case 1u:
			result = 0u;
			break;
		case 2u:
			result = 2u;
			break;
		}
		return result;
	}

	private void SetOperatingModeProfileIndex(string _modeProfileIndex)
	{
		LogCtrl.TraceMessage("modeProfileIndex: " + _modeProfileIndex, "SetOperatingModeProfileIndex", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5_Normal.cs", 1336);
		if (!(_modeProfileIndex == "M1P1"))
		{
			if (_modeProfileIndex == "M2P1")
			{
				m_Option.OfficeProfileIndex = 0u;
				WriteMainOptionToJson("OfficeProfileIndex", m_Option.OfficeProfileIndex);
				UserSet_Mode2();
			}
		}
		else
		{
			m_Option.GamingProfileIndex = 0u;
			WriteMainOptionToJson("GamingProfileIndex", m_Option.GamingProfileIndex);
			UserSet_Mode1();
		}
	}

	private async void SetOperatingModeProfileIndexThread(string _modeProfileIndex)
	{
		if (_modeProfileIndex == null)
		{
			return;
		}
		LogCtrl.TraceMessage(_modeProfileIndex, "SetOperatingModeProfileIndexThread", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5_Normal.cs", 1398);
		if (FansemporeSlim3.CurrentCount == 0)
		{
			LastCommand3 = _modeProfileIndex;
			return;
		}
		await FansemporeSlim3.WaitAsync();
		try
		{
			stopwatch3.Reset();
			stopwatch3.Start();
			SetOperatingModeProfileIndex(_modeProfileIndex);
			await Task.Delay(200);
			stopwatch3.Stop();
			_ = stopwatch3.ElapsedMilliseconds;
		}
		catch
		{
		}
		finally
		{
			FansemporeSlim3.Release();
			if (LastCommand3 != null)
			{
				SetOperatingModeProfileIndex(LastCommand3);
				LastCommand3 = null;
			}
		}
	}

	private async void SetModeSwitchChangeThread()
	{
		if (FansemporeSlim4.CurrentCount == 0)
		{
			return;
		}
		await FansemporeSlim4.WaitAsync();
		try
		{
			stopwatch4.Reset();
			stopwatch4.Start();
			SetModeSwitchChange();
			await Task.Delay(200);
			stopwatch4.Stop();
			_ = stopwatch4.ElapsedMilliseconds;
		}
		catch
		{
		}
		finally
		{
			FansemporeSlim4.Release();
		}
	}

	private void SetModeSwitchChange()
	{
		if (g_TurboModeSupport == 0)
		{
			switch (m_Option.OperatingMode)
			{
			case 1u:
				App.m_Osd.ShowOSDByName(TransToGlobalType(0u));
				LogCtrl.TraceMessage("-----------------------------------SetModeSwitchChange to Office----", "SetModeSwitchChange", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5_Normal.cs", 1529);
				UserSet_Mode2();
				break;
			case 0u:
				App.m_Osd.ShowOSDByName(TransToGlobalType(1u));
				LogCtrl.TraceMessage("-----------------------------------SetModeSwitchChange to Gaming----", "SetModeSwitchChange", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5_Normal.cs", 1534);
				UserSet_Mode1();
				break;
			}
		}
		else
		{
			switch (m_Option.OperatingMode)
			{
			case 1u:
				App.m_Osd.ShowOSDByName(TransToGlobalType(2u));
				LogCtrl.TraceMessage("-----------------------------------SetModeSwitchChange to Turbo----", "SetModeSwitchChange", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5_Normal.cs", 1545);
				UserSet_Mode3();
				break;
			case 0u:
				App.m_Osd.ShowOSDByName(TransToGlobalType(1u));
				LogCtrl.TraceMessage("-----------------------------------SetModeSwitchChange to Gaming----", "SetModeSwitchChange", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5_Normal.cs", 1550);
				UserSet_Mode1();
				break;
			case 2u:
				App.m_Osd.ShowOSDByName(TransToGlobalType(0u));
				LogCtrl.TraceMessage("-----------------------------------SetModeSwitchChange to Office----", "SetModeSwitchChange", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5_Normal.cs", 1555);
				UserSet_Mode2();
				break;
			}
		}
		UpdateStatusToClient(1);
	}
}
