using System;
using System.Collections;
using System.Diagnostics;
using System.Diagnostics.Eventing.Reader;
using System.IO;
using System.Reflection;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Threading;
using Define;
using GCUService.MyFan.Overclocking;
using Microsoft.Win32;
using MyControlCenter.MyFan.FanTable;
using MyECIO;
using Newtonsoft.Json;
using Utility;

namespace MyControlCenter.MyFan;

internal class MyFanManager_RamFan1p5 : MyFanManager
{
	private MyEcCtrl EcCtrl = MyEcCtrl.Instance;

	private string m_RegistryPath = "\\OEM\\GamingCenter2\\SMAPCTable";

	private string m_path = new FileInfo(Assembly.GetExecutingAssembly().Location).DirectoryName + "\\UserPofiles";

	private Dispatcher _dispatcher;

	private bool m_bInit;

	private GpuFeatures cGpuFeatures = new GpuFeatures();

	private MyFanTableCtrl FanTable = MyFanTableCtrl.Instance;

	private bool m_OcSupport = true;

	private bool m_IsNvGpu;

	private bool m_IsAMDPlatform;

	private bool m_IsHeroProject;

	private uint m_DefaultMode;

	private int m_FanSafetyProtect;

	private int m_AmdCpuOverClockSupport;

	private bool m_FanBoostBtnSupport = true;

	private bool m_GpuWhisperModeSupport;

	private const int WhisperModeMinFpsMaximum = 60;

	private const int WhisperModeMinFpsMinimum = 30;

	private MainOption m_Option = new MainOption();

	private PLDefaultValue GamingModePLDefaultValue = new PLDefaultValue();

	private PLDefaultValue OfficeModePLDefaultValue = new PLDefaultValue();

	private PLDefaultValue TurboModePLDefaultValue = new PLDefaultValue();

	private GpuThermalLimitInfo GpuThermalLimitInfo = new GpuThermalLimitInfo();

	private NvramVariableInfo NvramVariableInfo = new NvramVariableInfo();

	private SMAPCTABLE_STRUCT _SmartApcTable;

	private int CpuPL1Minimum = 10;

	private int CpuPL2Minimum = 10;

	private int CpuPL4Minimum = 10;

	private bool m_GpuConfigurableTGPSupport;

	private int m_GpuConfigurableTGPMaximum;

	private const int GpuCoreClockOffsetMaximum = 200;

	private const int GpuCoreClockOffsetMinimum = 0;

	private const int GpuMemoryClockOffsetMaximum = 1000;

	private const int GpuMemoryClockOffsetMinimum = -1000;

	private const int GpuDynamicBoostMinimum = 5;

	private int GpuDynamicBoostDefaultValue = 5;

	private bool m_GpuDynamicBoostSupport;

	private int CpuOffsetCoreVoltageMaximum;

	private int CpuOffsetCoreVoltageMinimum;

	private ModeProfile currentProfile = new ModeProfile();

	private ModeProfile Mode1_Profile1 = new ModeProfile();

	private ModeProfile Mode1_Profile2 = new ModeProfile();

	private ModeProfile Mode1_Profile3 = new ModeProfile();

	private ModeProfile Mode1_Profile4 = new ModeProfile();

	private ModeProfile Mode1_Profile5 = new ModeProfile();

	private ModeProfile Mode2_Profile1 = new ModeProfile();

	private ModeProfile Mode2_Profile2 = new ModeProfile();

	private ModeProfile Mode2_Profile3 = new ModeProfile();

	private ModeProfile Mode2_Profile4 = new ModeProfile();

	private ModeProfile Mode2_Profile5 = new ModeProfile();

	private ModeProfile Mode3_Profile1 = new ModeProfile();

	private ModeProfile Mode3_Profile2 = new ModeProfile();

	private ModeProfile Mode3_Profile3 = new ModeProfile();

	private ModeProfile Mode3_Profile4 = new ModeProfile();

	private ModeProfile Mode3_Profile5 = new ModeProfile();

	private int m_nAppType = 1;

	private string m_sRegPath = "\\OEM\\GamingCenter2";

	private SemaphoreSlim FansemporeSlim2 = new SemaphoreSlim(1, 1);

	private Stopwatch stopwatch2 = new Stopwatch();

	private string LastCommand2 = "M1T1";

	private SemaphoreSlim FansemporeSlim3 = new SemaphoreSlim(1, 1);

	private Stopwatch stopwatch3 = new Stopwatch();

	private string LastCommand3;

	private SemaphoreSlim FansemporeSlim4 = new SemaphoreSlim(1, 1);

	private Stopwatch stopwatch4 = new Stopwatch();

	private int LastCommand4 = -1;

	public MyFanManager_RamFan1p5()
	{
		m_nAppType = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegPath, "AppType", 1);
	}

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
		LogCtrl.TraceMessage("g_TurboModeSupport: " + g_TurboModeSupport, "EnableByService", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5.cs", 122);
		m_DefaultMode = GetDefaultMode();
		LogCtrl.TraceMessage("m_DefaultMode: " + m_DefaultMode, "EnableByService", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5.cs", 125);
		g_QkeyDefine = GetQkeyDefine();
		LogCtrl.TraceMessage("g_QkeyDefine: " + g_QkeyDefine, "EnableByService", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5.cs", 128);
		m_FanBoostBtnSupport = CustomizeCtrl.GetFanBoostBtnSupport();
		LogCtrl.TraceMessage("m_FanBoostBtnSupport: " + m_FanBoostBtnSupport, "EnableByService", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5.cs", 131);
		LogCtrl.TraceMessage("m_OcSupport: " + m_OcSupport, "EnableByService", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5.cs", 134);
		m_IsNvGpu = UtilityExtensions.IsNvGpu();
		LogCtrl.TraceMessage("m_IsNvGpu: " + m_IsNvGpu, "EnableByService", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5.cs", 137);
		m_IsAMDPlatform = CustomizeCtrl.GetIsAMDPlatform();
		LogCtrl.TraceMessage("m_IsAMDPlatform: " + m_IsAMDPlatform, "EnableByService", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5.cs", 140);
		m_IsHeroProject = EcCtrl.IsHeroProject();
		LogCtrl.TraceMessage("m_IsHeroProject: " + m_IsHeroProject, "EnableByService", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5.cs", 143);
		LoadProfileAll();
		syncBiosSettings();
		Init();
		m_bInit = true;
	}

	public override void Disable()
	{
		FanTable.DisableByService();
		m_DefaultMode = GetDefaultMode();
		LogCtrl.TraceMessage("m_DefaultMode: " + m_DefaultMode, "Disable", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5.cs", 156);
		SetFanMode(m_DefaultMode);
		if (!m_OcSupport)
		{
			return;
		}
		SetCpuTccOffset(0, bApExist: false);
		SetFanSwitchSpeedEnabled(0);
		if (m_IsNvGpu)
		{
			SetGpuDynamicBoostSwitch(0);
			cGpuFeatures.SetGpuWhisperModeMainSwitch(1);
			if (m_DefaultMode == 0)
			{
				SetGpuWhisperModeSwitchOnOFF(1);
			}
			else
			{
				SetGpuWhisperModeSwitchOnOFF(0);
			}
		}
	}

	public override void Uninstall()
	{
		FanTable.Uninstall();
		m_DefaultMode = GetDefaultMode();
		LogCtrl.TraceMessage("m_DefaultMode: " + m_DefaultMode, "Uninstall", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5.cs", 189);
		SetFanMode(m_DefaultMode);
		if (m_OcSupport)
		{
			SetCpuTccOffset(0, bApExist: false);
			SetFanSwitchSpeedEnabled(0);
			if (m_IsNvGpu)
			{
				SetGpuDynamicBoostSwitch(0);
				cGpuFeatures.SetGpuWhisperModeMainSwitch(1);
				if (m_DefaultMode == 0)
				{
					SetGpuWhisperModeSwitchOnOFF(1);
				}
				else
				{
					SetGpuWhisperModeSwitchOnOFF(0);
				}
			}
		}
		NvramVariable.SetFwVars("ApUseFlag", 0);
		NvramVariable.SetFwVars("PowerMode", Convert.ToByte(m_DefaultMode));
		NvramVariable.SetFwVars("MemoryOverClockSwitch", 0);
		NvramVariable.SetFwVars("ApExistFlag", 0);
		LogCtrl.TraceMessage("Sync up BIOS Variable, ApUseFlag: 0, PowerMode: " + m_DefaultMode + ", MemoryOverClockSwitch: 0, ApExistFlag: 0", "Uninstall", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5.cs", 221);
	}

	public override async void Receive(byte[] data)
	{
		dynamic val = await Json.ToObjectAsync<object>(Encoding.UTF8.GetString(data));
		string text = Convert.ToString(val["Action"]);
		LogCtrl.TraceMessage("---------------" + LogCtrl.GetTime() + "---------------", "Receive", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5.cs", 236);
		LogCtrl.TraceMessage("Action = " + text, "Receive", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5.cs", 237);
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
			if (val["ProfileIndex"] != null && Convert.ToInt32(val["ProfileIndex"]) > -1)
			{
				string operatingModeProfileIndexThread3 = TransferToName("OPERATING_GAMING_MODE", Convert.ToUInt32(val["ProfileIndex"]));
				SetOperatingModeProfileIndexThread(operatingModeProfileIndexThread3);
			}
			else
			{
				string operatingModeProfileIndexThread4 = TransferToName("OPERATING_GAMING_MODE", m_Option.GamingProfileIndex);
				SetOperatingModeProfileIndexThread(operatingModeProfileIndexThread4);
				UpdateStatusToClient(1);
			}
			break;
		case "OPERATING_OFFICE_MODE":
			if (val["ProfileIndex"] != null && Convert.ToInt32(val["ProfileIndex"]) > -1)
			{
				string operatingModeProfileIndexThread5 = TransferToName("OPERATING_OFFICE_MODE", Convert.ToUInt32(val["ProfileIndex"]));
				SetOperatingModeProfileIndexThread(operatingModeProfileIndexThread5);
			}
			else
			{
				string operatingModeProfileIndexThread6 = TransferToName("OPERATING_OFFICE_MODE", m_Option.OfficeProfileIndex);
				SetOperatingModeProfileIndexThread(operatingModeProfileIndexThread6);
				UpdateStatusToClient(1);
			}
			break;
		case "OPERATING_TURBO_MODE":
			if (val["ProfileIndex"] != null && Convert.ToInt32(val["ProfileIndex"]) > -1)
			{
				string operatingModeProfileIndexThread = TransferToName("OPERATING_TURBO_MODE", Convert.ToUInt32(val["ProfileIndex"]));
				SetOperatingModeProfileIndexThread(operatingModeProfileIndexThread);
			}
			else
			{
				string operatingModeProfileIndexThread2 = TransferToName("OPERATING_TURBO_MODE", m_Option.TurboProfileIndex);
				SetOperatingModeProfileIndexThread(operatingModeProfileIndexThread2);
				UpdateStatusToClient(1);
			}
			break;
		case "SET_OPERATING_MODE_DETAIL":
			UserSet_Mode_Detail(val);
			break;
		case "RESTORE_OPERATING_MODE_DETAIL":
			UserRestore_Mode_Details();
			UpdateStatusToClient(1);
			break;
		case "GET_FAN_SPEED_CURVE_SETTING":
			FanTable.GetFanTable(currentProfile.FAN.TableName);
			break;
		case "SET_FAN_SPEED_CURVE_SETTING":
			if (m_FanSafetyProtect == 0)
			{
				FanTable.SetFanTableSetting(val, true);
			}
			else
			{
				FanTable.SetFanTableSetting(val, false);
			}
			break;
		case "SET_FAN_CONTROL_RESPECTIVE":
			if (m_FanSafetyProtect == 0)
			{
				FanTable.SetFanControlRespective(val);
			}
			break;
		case "RESTORE_FAN_SPEED_CURVE_SETTING_ALL":
			FanTable.RestoreDefaultFanTableAll();
			break;
		case "RESTORE_FAN_SPEED_CURVE_SETTING":
			FanTable.RestoreDefaultFanTable(val);
			break;
		case "SET_DEFAULT_NOTIFY_OFF":
			UserSet_DefaultNotifyStatus(0u);
			break;
		case "SET_FAN_SAFETY_PROTECT_NOTIFY_OFF":
			UserSet_FanSafetyProtectNotifyStatus(0u);
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
			OperatingMode = (updateOperationMode ? Convert.ToString(m_Option.OperatingMode) : null),
			GamingProfileIndex = Convert.ToString(m_Option.GamingProfileIndex),
			OfficeProfileIndex = Convert.ToString(m_Option.OfficeProfileIndex),
			TurboProfileIndex = Convert.ToString(m_Option.TurboProfileIndex),
			FanBoostEnable = Convert.ToString(m_Option.FanBoostEnable),
			ProfileName = currentProfile.Name,
			FAN_FanSwitchSpeedEnabled = Convert.ToString(currentProfile.FAN.FanSwitchSpeedEnabled),
			FAN_FanSwitchSpeed = Convert.ToString(currentProfile.FAN.FanSwitchSpeed),
			FAN_TableName = currentProfile.FAN.TableName,
			FAN_SafetyProtectNotify = Convert.ToString(m_Option.FanSafetyProtectNotify),
			FAN_SafetyProtect = Convert.ToString(m_FanSafetyProtect),
			CPU_PL1 = Convert.ToString(currentProfile.CPU.PL1),
			CPU_PL1Maximum = Convert.ToString(_SmartApcTable.PL1),
			CPU_PL1Minimum = Convert.ToString(CpuPL1Minimum),
			CPU_PL2 = Convert.ToString(currentProfile.CPU.PL2),
			CPU_PL2Maximum = Convert.ToString(_SmartApcTable.PL2),
			CPU_PL2Minimum = Convert.ToString(CpuPL2Minimum),
			CPU_PL4 = Convert.ToString(currentProfile.CPU.PL4),
			CPU_PL4Maximum = Convert.ToString(_SmartApcTable.PL4),
			CPU_PL4Minimum = Convert.ToString(CpuPL4Minimum),
			CPU_OffsetCoreVoltage = Convert.ToString(currentProfile.CPU.OffsetCoreVoltage),
			CPU_OffsetCoreVoltageMaximum = Convert.ToString(CpuOffsetCoreVoltageMaximum),
			CPU_OffsetCoreVoltageMinimum = Convert.ToString(CpuOffsetCoreVoltageMinimum),
			CPU_TccOffsetSwitch = Convert.ToString(currentProfile.CPU.TccOffsetSwitch),
			CPU_TccOffsetMaximum = Convert.ToString(_SmartApcTable.TccOffset),
			CPU_TccOffset = Convert.ToString(currentProfile.CPU.TccOffset),
			GPU_CoreClockOffset = Convert.ToString(currentProfile.GPU.CoreClockOffset),
			GPU_CoreClockOffsetMaximum = Convert.ToString(200),
			GPU_CoreClockOffsetMinimum = Convert.ToString(0),
			GPU_MemoryClockOffset = Convert.ToString(currentProfile.GPU.MemoryClockOffset),
			GPU_MemoryClockOffsetMaximum = Convert.ToString(1000),
			GPU_MemoryClockOffsetMinimum = Convert.ToString(-1000),
			GPU_TargetTemperature = Convert.ToString(currentProfile.GPU.TargetTemperature),
			GPU_TargetTemperatureMaximum = Convert.ToString(GpuThermalLimitInfo.MaximumTemperature),
			GPU_TargetTemperatureMinimum = Convert.ToString(GpuThermalLimitInfo.MinimumTemperature),
			GPU_ConfigurableTGPSwitch = Convert.ToString(currentProfile.GPU.ConfigurableTGPSwitch),
			GPU_ConfigurableTGPTarget = Convert.ToString(currentProfile.GPU.ConfigurableTGPTarget),
			GPU_ConfigurableTGPMaximum = Convert.ToString(m_GpuConfigurableTGPMaximum),
			GPU_ConfigurableTGPMinimum = Convert.ToString(_SmartApcTable.DefaultTGP),
			GPU_DynamicBoostSwitch = Convert.ToString(currentProfile.GPU.DynamicBoostSwitch),
			GPU_DynamicBoost = Convert.ToString(currentProfile.GPU.DynamicBoost),
			GPU_DynamicBoostMaximum = Convert.ToString(_SmartApcTable.DynamicBoost),
			GPU_DynamicBoostMinimum = Convert.ToString(5),
			GPU_DynamicBoostTotalProcessingPowerTarget = Convert.ToString(currentProfile.GPU.DynamicBoostTotalProcessingPowerTarget),
			GPU_WhisperModeSupport = m_GpuWhisperModeSupport,
			GPU_WhisperModeSwitch = Convert.ToString(m_Option.WhisperModeSwitch),
			GPU_WhisperModeSetting = Convert.ToString(m_Option.WhisperModeSetting),
			GPU_WhisperModeMinFps_QUIETER = Convert.ToString(m_Option.WhisperModeMinFps_QUIETER),
			GPU_WhisperModeMinFps_QUIET = Convert.ToString(m_Option.WhisperModeMinFps_QUIET),
			GPU_WhisperModeMinFps_BALANCED = Convert.ToString(m_Option.WhisperModeMinFps_BALANCED),
			GPU_WhisperModeMinFpsMaximum = Convert.ToString(60),
			GPU_WhisperModeMinFpsMinimum = Convert.ToString(30),
			CPU_AmdSPL = Convert.ToString(currentProfile.CPU.AmdSPL),
			CPU_AmdSPPT = Convert.ToString(currentProfile.CPU.AmdSPPT),
			CPU_AmdFPPT = Convert.ToString(currentProfile.CPU.AmdFPPT),
			CPU_AmdTccTarget = Convert.ToString(currentProfile.CPU.AmdTccTarget),
			CPU_AmdOverClockSupport = Convert.ToString(NvramVariableInfo.ACpuOverClockSupport),
			CPU_AmdCoreFreq = Convert.ToString(currentProfile.CPU.AmdCoreFreq),
			CPU_AmdCoreFreqMaximum = Convert.ToString(NvramVariableInfo.ACpuFreqValueMaximum),
			CPU_AmdCoreVoltage = Convert.ToString(currentProfile.CPU.AmdCoreVoltage),
			CPU_AmdCoreVoltageMaximum = Convert.ToString(NvramVariableInfo.ACpuVoltageValueMaximum),
			MEM_MemoryOverClockSupport = Convert.ToString(NvramVariableInfo.MemoryOverClockSupport),
			MEM_MemoryOverClockSwitch = Convert.ToString(currentProfile.MEM.MemoryOverClockSwitch),
			BSOD_DefaultNotify = Convert.ToString(m_Option.DefaultNotify),
			BSOD_TimestampRestored = m_Option.BsodTimestampRestored.ToString("yyyy-MM-dd H:mm:ss"),
			OcSupport = m_OcSupport,
			IsAMDPlatform = m_IsAMDPlatform,
			IsNvGpu = m_IsNvGpu,
			TurboModeOption = Convert.ToString(g_TurboModeSupport),
			FanBoostBtnSupport = m_FanBoostBtnSupport,
			PowerMode = Convert.ToString(PowerModeEvent.g_ACLineStatus)
		};
		App.m_MQTTService.Publish("Fan/Status", data, retain: false);
	}

	private void UpdateWhisperModeStatusToClient()
	{
		var data = new
		{
			GPU_WhisperModeSupport = m_GpuWhisperModeSupport,
			GPU_WhisperModeSwitch = Convert.ToString(m_Option.WhisperModeSwitch),
			GPU_WhisperModeSetting = Convert.ToString(m_Option.WhisperModeSetting),
			GPU_WhisperModeMinFps_QUIETER = Convert.ToString(m_Option.WhisperModeMinFps_QUIETER),
			GPU_WhisperModeMinFps_QUIET = Convert.ToString(m_Option.WhisperModeMinFps_QUIET),
			GPU_WhisperModeMinFps_BALANCED = Convert.ToString(m_Option.WhisperModeMinFps_BALANCED),
			GPU_WhisperModeMinFpsMaximum = Convert.ToString(60),
			GPU_WhisperModeMinFpsMinimum = Convert.ToString(30)
		};
		App.m_MQTTService.Publish("WhisperMode/Status", data, retain: false);
	}

	public override void UpdateStatusToTray()
	{
		var data = new
		{
			OperatingMode = Convert.ToString(m_Option.OperatingMode),
			FanBoostEnable = Convert.ToString(m_Option.FanBoostEnable)
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

	public override void Restore()
	{
		LoadDefault();
		Init();
	}

	public override void ModeSwitchChanged()
	{
		if (g_TurboModeSupport == 0)
		{
			switch (m_Option.OperatingMode)
			{
			case 1u:
				SetModeSwitchChangeThread(0);
				break;
			case 0u:
				SetModeSwitchChangeThread(1);
				break;
			}
		}
		else if (m_nAppType == 3)
		{
			switch (m_Option.OperatingMode)
			{
			case 1u:
				SetModeSwitchChangeThread(0);
				break;
			case 0u:
				SetModeSwitchChangeThread(2);
				break;
			case 2u:
				SetModeSwitchChangeThread(0);
				break;
			}
		}
		else
		{
			switch (m_Option.OperatingMode)
			{
			case 1u:
				SetModeSwitchChangeThread(2);
				break;
			case 0u:
				SetModeSwitchChangeThread(1);
				break;
			case 2u:
				SetModeSwitchChangeThread(0);
				break;
			}
		}
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
		m_FanSafetyProtect = GetFanSafetyProtectStatus();
		if (m_FanSafetyProtect == 1)
		{
			m_Option.FanSafetyProtectNotify = 1u;
			if (m_Option.OperatingMode == 1)
			{
				FanTable.SetFanTable("DefaultFanTable_Gaming");
			}
			else if (m_Option.OperatingMode == 0)
			{
				FanTable.SetFanTable("DefaultFanTable_Office");
			}
			else if (m_Option.OperatingMode == 2)
			{
				FanTable.SetFanTable("DefaultFanTable_Turbo");
			}
		}
		else
		{
			m_Option.FanSafetyProtectNotify = 0u;
			FanTable.SetFanTable(currentProfile.FAN.TableName);
		}
		WriteMainOptionToJson("FanSafetyProtectNotify", m_Option.FanSafetyProtectNotify);
		UpdateStatusToClient(1);
	}

	public override void WhisperUpdate()
	{
		if (m_GpuWhisperModeSupport)
		{
			UpdateWhisperStatus();
			UpdateWhisperModeStatusToClient();
		}
	}

	private void UpdateWhisperStatus()
	{
		int wisperModeStatus = cGpuFeatures.GetWisperModeStatus();
		if (wisperModeStatus == -1)
		{
			m_Option.WhisperModeSwitch = 0;
			LogCtrl.TraceMessage("GetWisperModeStatus: " + wisperModeStatus + ", WhisperModeSwitch: " + m_Option.WhisperModeSwitch, "UpdateWhisperStatus", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5.cs", 643);
			WriteMainOptionToJson("WhisperModeSwitch", Convert.ToUInt32(m_Option.WhisperModeSwitch));
			return;
		}
		m_Option.WhisperModeSwitch = 1;
		m_Option.WhisperModeSetting = wisperModeStatus;
		LogCtrl.TraceMessage("GetWisperModeStatus: " + wisperModeStatus + ", WhisperModeSwitch: " + m_Option.WhisperModeSwitch + ", WhisperModeSetting: " + m_Option.WhisperModeSetting, "UpdateWhisperStatus", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5.cs", 652);
		WriteMainOptionToJson("WhisperModeSwitch", Convert.ToUInt32(m_Option.WhisperModeSwitch));
		WriteMainOptionToJson("WhisperModeSetting", Convert.ToUInt32(m_Option.WhisperModeSetting));
	}

	public override void UserSet_Mode1()
	{
		if (m_nAppType == 3)
		{
			m_Option.OperatingMode = 2u;
			RefreshCurrentProfile(m_Option.OperatingMode, save: false);
			SetUserProfile(2u);
			WriteMainOptionToJson("OperatingMode", 2u);
			NvramVariable.SetFwVars("PowerMode", Convert.ToByte(2u));
		}
		else
		{
			m_Option.OperatingMode = 1u;
			RefreshCurrentProfile(m_Option.OperatingMode, save: false);
			SetUserProfile(1u);
			WriteMainOptionToJson("OperatingMode", 1u);
			NvramVariable.SetFwVars("PowerMode", Convert.ToByte(1u));
		}
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
		m_Option.OperatingMode = 2u;
		RefreshCurrentProfile(m_Option.OperatingMode, save: false);
		SetUserProfile(2u);
		WriteMainOptionToJson("OperatingMode", 2u);
		NvramVariable.SetFwVars("PowerMode", Convert.ToByte(2u));
	}

	public override void SetPairedProfileIndex(uint index)
	{
		if (index == 0)
		{
			RefreshCurrentProfile(m_Option.OperatingMode, save: false);
			SetUserProfile(m_Option.OperatingMode);
			UpdateStatusToClient(1);
			return;
		}
		m_Option.GamingProfileIndex = index;
		WriteMainOptionToJson("GamingProfileIndex", m_Option.GamingProfileIndex);
		RefreshCurrentProfile(1u, save: false);
		SetUserProfile(1u);
		var data = new
		{
			OperatingMode = Convert.ToString(1u),
			GamingProfileIndex = Convert.ToString(m_Option.GamingProfileIndex),
			OfficeProfileIndex = Convert.ToString(m_Option.OfficeProfileIndex),
			TurboProfileIndex = Convert.ToString(m_Option.TurboProfileIndex),
			FanBoostEnable = Convert.ToString(m_Option.FanBoostEnable),
			ProfileName = currentProfile.Name,
			FAN_FanSwitchSpeed = Convert.ToString(currentProfile.FAN.FanSwitchSpeed),
			FAN_TableName = currentProfile.FAN.TableName,
			CPU_PL1 = Convert.ToString(currentProfile.CPU.PL1),
			CPU_PL2 = Convert.ToString(currentProfile.CPU.PL2),
			CPU_PL4 = Convert.ToString(currentProfile.CPU.PL4),
			CPU_OffsetCoreVoltage = Convert.ToString(currentProfile.CPU.OffsetCoreVoltage),
			CPU_TccOffsetSwitch = Convert.ToString(currentProfile.CPU.TccOffsetSwitch),
			CPU_TccOffset = Convert.ToString(currentProfile.CPU.TccOffset),
			GPU_CoreClockOffset = Convert.ToString(currentProfile.GPU.CoreClockOffset),
			GPU_MemoryClockOffset = Convert.ToString(currentProfile.GPU.MemoryClockOffset),
			GPU_TargetTemperature = Convert.ToString(currentProfile.GPU.TargetTemperature),
			GPU_ConfigurableTGPSwitch = Convert.ToString(currentProfile.GPU.ConfigurableTGPSwitch),
			GPU_ConfigurableTGPTarget = Convert.ToString(currentProfile.GPU.ConfigurableTGPTarget),
			GPU_DynamicBoostSwitch = Convert.ToString(currentProfile.GPU.DynamicBoostSwitch),
			GPU_DynamicBoost = Convert.ToString(currentProfile.GPU.DynamicBoost),
			GPU_WhisperModeSwitch = Convert.ToString(m_Option.WhisperModeSwitch),
			CPU_AmdSPL = Convert.ToString(currentProfile.CPU.AmdSPL),
			CPU_AmdSPPT = Convert.ToString(currentProfile.CPU.AmdSPPT),
			CPU_AmdFPPT = Convert.ToString(currentProfile.CPU.AmdFPPT),
			CPU_AmdTccTarget = Convert.ToString(currentProfile.CPU.AmdTccTarget),
			CPU_AmdCoreFreq = Convert.ToString(currentProfile.CPU.AmdCoreFreq),
			CPU_AmdCoreVoltage = Convert.ToString(currentProfile.CPU.AmdCoreVoltage),
			MEM_MemoryOverClockSwitch = Convert.ToString(currentProfile.MEM.MemoryOverClockSwitch)
		};
		App.m_MQTTService.Publish("Fan/Status", data, retain: false);
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

	private void UserSet_Mode_Detail(dynamic data)
	{
		try
		{
			if (data["PL1"] != null)
			{
				currentProfile.CPU.PL1 = Convert.ToInt32(data["PL1"]);
				SetPL1Value(currentProfile.CPU.PL1);
			}
			if (data["PL2"] != null)
			{
				currentProfile.CPU.PL2 = Convert.ToInt32(data["PL2"]);
				SetPL2Value(currentProfile.CPU.PL2);
			}
			if (data["PL4"] != null)
			{
				currentProfile.CPU.PL4 = Convert.ToInt32(data["PL4"]);
				SetPL4Value(currentProfile.CPU.PL4);
			}
			if (data["CpuAmdSPL"] != null)
			{
				currentProfile.CPU.AmdSPL = Convert.ToInt32(data["CpuAmdSPL"]);
				SetPL1Value(currentProfile.CPU.AmdSPL);
				if (PowerModeEvent.g_ACLineStatus == 1 && currentProfile.CPU.AmdSPL >= 75)
				{
					SetCpuVrmCurrentLimit(65, 120);
				}
			}
			if (data["CpuAmdSPPT"] != null)
			{
				currentProfile.CPU.AmdSPPT = Convert.ToInt32(data["CpuAmdSPPT"]);
				SetPL2Value(currentProfile.CPU.AmdSPPT);
				if (PowerModeEvent.g_ACLineStatus == 1 && currentProfile.CPU.AmdSPPT >= 75)
				{
					SetCpuVrmCurrentLimit(65, 120);
				}
			}
			if (data["CpuAmdFPPT"] != null)
			{
				currentProfile.CPU.AmdFPPT = Convert.ToInt32(data["CpuAmdFPPT"]);
				SetPL4Value(currentProfile.CPU.AmdFPPT);
			}
			if (data["FanSwitchSpeed"] != null)
			{
				currentProfile.FAN.FanSwitchSpeed = Convert.ToInt32(data["FanSwitchSpeed"]);
				SetFanSwitchSpeed(currentProfile.FAN.FanSwitchSpeed, bApExist: true);
			}
			else if (data["FanSwitchSpeedEnabled"] != null)
			{
				currentProfile.FAN.FanSwitchSpeedEnabled = Convert.ToInt32(data["FanSwitchSpeedEnabled"]);
				SetFanSwitchSpeedEnabled(currentProfile.FAN.FanSwitchSpeedEnabled);
			}
			else if (data["CpuOffsetCoreVoltage"] != null)
			{
				currentProfile.CPU.OffsetCoreVoltage = Convert.ToInt32(data["CpuOffsetCoreVoltage"]);
				SetCpuCoreVoltageOffset(currentProfile.CPU.OffsetCoreVoltage);
			}
			else if (data["CpuTccOffsetSwitch"] != null)
			{
				currentProfile.CPU.TccOffsetSwitch = Convert.ToInt32(data["CpuTccOffsetSwitch"]);
				if (currentProfile.CPU.TccOffsetSwitch == 1)
				{
					if (m_IsAMDPlatform)
					{
						SetCpuTccOffset(currentProfile.CPU.AmdTccTarget, bApExist: true);
					}
					else
					{
						SetCpuTccOffset(currentProfile.CPU.TccOffset, bApExist: true);
					}
				}
				else
				{
					SetCpuTccOffset(0, bApExist: false);
				}
			}
			else if (data["CpuTccOffset"] != null)
			{
				currentProfile.CPU.TccOffset = Convert.ToInt32(data["CpuTccOffset"]);
				SetCpuTccOffset(currentProfile.CPU.TccOffset, bApExist: true);
			}
			else if (data["GpuCoreClockOffset"] != null)
			{
				currentProfile.GPU.CoreClockOffset = Convert.ToInt32(data["GpuCoreClockOffset"]);
				cGpuFeatures.SetGpuCoreFreqOffsetValue(currentProfile.GPU.CoreClockOffset);
			}
			else if (data["GpuMemoryClockOffset"] != null)
			{
				currentProfile.GPU.MemoryClockOffset = Convert.ToInt32(data["GpuMemoryClockOffset"]);
				cGpuFeatures.SetGpuMemFreqOffsetValue(currentProfile.GPU.MemoryClockOffset);
			}
			else if (data["GpuTargetTemperature"] != null)
			{
				currentProfile.GPU.TargetTemperature = Convert.ToInt32(data["GpuTargetTemperature"]);
				cGpuFeatures.SetGpuTargetTemperature(currentProfile.GPU.TargetTemperature);
			}
			else if (data["GpuConfigurableTGPSwitch"] != null)
			{
				currentProfile.GPU.ConfigurableTGPSwitch = Convert.ToInt32(data["GpuConfigurableTGPSwitch"]);
				cGpuFeatures.SetGpuConfigurableTgpFunCtrlEnable(currentProfile.GPU.ConfigurableTGPSwitch);
			}
			else if (data["GpuConfigurableTGPTarget"] != null)
			{
				currentProfile.GPU.ConfigurableTGPTarget = Convert.ToInt32(data["GpuConfigurableTGPTarget"]);
				cGpuFeatures.SetGpuConfigurableTGPTarget(currentProfile.GPU.ConfigurableTGPTarget, _SmartApcTable.DefaultTGP);
			}
			else if (data["GpuDynamicBoostSwitch"] != null)
			{
				currentProfile.GPU.DynamicBoostSwitch = Convert.ToInt32(data["GpuDynamicBoostSwitch"]);
				SetGpuDynamicBoostSwitch(currentProfile.GPU.DynamicBoostSwitch);
				if (currentProfile.GPU.DynamicBoostSwitch == 1)
				{
					if (currentProfile.GPU.ConfigurableTGPTarget > m_GpuConfigurableTGPMaximum)
					{
						cGpuFeatures.SetGpuConfigurableTGPTarget(m_GpuConfigurableTGPMaximum, _SmartApcTable.DefaultTGP);
					}
					else
					{
						cGpuFeatures.SetGpuConfigurableTGPTarget(currentProfile.GPU.ConfigurableTGPTarget, _SmartApcTable.DefaultTGP);
					}
				}
				else
				{
					cGpuFeatures.SetGpuConfigurableTGPTarget(currentProfile.GPU.ConfigurableTGPTarget, _SmartApcTable.DefaultTGP);
					cGpuFeatures.SetGpuConfigurableTgpFunCtrlEnable(currentProfile.GPU.ConfigurableTGPSwitch);
				}
			}
			else if (data["GpuDynamicBoost"] != null)
			{
				currentProfile.GPU.DynamicBoost = Convert.ToInt32(data["GpuDynamicBoost"]);
				cGpuFeatures.SetGpuDynamicBoostMaxinumTGP(currentProfile.GPU.DynamicBoost);
			}
			else if (data["GpuDynamicBoostTotalProcessingPowerTarget"] != null)
			{
				currentProfile.GPU.DynamicBoostTotalProcessingPowerTarget = Convert.ToInt32(data["GpuDynamicBoostTotalProcessingPowerTarget"]);
				cGpuFeatures.SetGpuDynamicBoostTotalProcessingPowerTarget(currentProfile.GPU.DynamicBoostTotalProcessingPowerTarget);
			}
			else if (data["WhisperModeSwitch"] != null)
			{
				if (m_GpuWhisperModeSupport)
				{
					m_Option.WhisperModeSwitch = Convert.ToInt32(data["WhisperModeSwitch"]);
					WriteMainOptionToJson("WhisperModeSwitch", Convert.ToUInt32(m_Option.WhisperModeSwitch));
					SetGpuWhisperModeSwitchOnOFF(m_Option.WhisperModeSwitch);
				}
			}
			else if (data["GpuWhisperModeSetting"] != null)
			{
				if (m_GpuWhisperModeSupport)
				{
					m_Option.WhisperModeSetting = Convert.ToInt32(data["GpuWhisperModeSetting"]);
					WriteMainOptionToJson("WhisperModeSetting", Convert.ToUInt32(m_Option.WhisperModeSetting));
					cGpuFeatures.SetGpuWhisperModeSettingValue(m_Option.WhisperModeSetting);
					switch (m_Option.WhisperModeSetting)
					{
					case 0:
						cGpuFeatures.SetGpuWhisperModeMinFpsValue(m_Option.WhisperModeMinFps_QUIETER);
						break;
					case 1:
						cGpuFeatures.SetGpuWhisperModeMinFpsValue(m_Option.WhisperModeMinFps_QUIET);
						break;
					case 2:
						cGpuFeatures.SetGpuWhisperModeMinFpsValue(m_Option.WhisperModeMinFps_BALANCED);
						break;
					}
				}
			}
			else if (data["GpuWhisperModeMinFps"] != null)
			{
				if (m_GpuWhisperModeSupport)
				{
					int num = 0;
					num = Convert.ToInt32(data["GpuWhisperModeMinFps"]);
					switch (m_Option.WhisperModeSetting)
					{
					case 0:
						m_Option.WhisperModeMinFps_QUIETER = num;
						WriteMainOptionToJson("WhisperModeMinFps_QUIETER", Convert.ToUInt32(num));
						break;
					case 1:
						m_Option.WhisperModeMinFps_QUIET = num;
						WriteMainOptionToJson("WhisperModeMinFps_QUIET", Convert.ToUInt32(num));
						break;
					case 2:
						m_Option.WhisperModeMinFps_BALANCED = num;
						WriteMainOptionToJson("WhisperModeMinFps_BALANCED", Convert.ToUInt32(num));
						break;
					}
					cGpuFeatures.SetGpuWhisperModeMinFpsValue(num);
				}
			}
			else if (data["CpuAmdTccTarget"] != null)
			{
				currentProfile.CPU.AmdTccTarget = Convert.ToInt32(data["CpuAmdTccTarget"]);
				SetCpuTccOffset(currentProfile.CPU.AmdTccTarget, bApExist: true);
			}
			else if (data["CpuAmdCoreFreq"] != null)
			{
				currentProfile.CPU.AmdCoreFreq = Convert.ToInt32(data["CpuAmdCoreFreq"]);
				SetCpuAmdCoreFreq(currentProfile.CPU.AmdCoreFreq);
			}
			else if (data["CpuAmdCoreVoltage"] != null)
			{
				currentProfile.CPU.AmdCoreVoltage = Convert.ToInt32(data["CpuAmdCoreVoltage"]);
				SetCpuAmdCoreVoltage(currentProfile.CPU.AmdCoreVoltage);
			}
			else if (data["MemoryOverClockSwitch"] != null)
			{
				currentProfile.MEM.MemoryOverClockSwitch = Convert.ToInt32(data["MemoryOverClockSwitch"]);
				SetMemoryOverClockSwitch(currentProfile.MEM.MemoryOverClockSwitch);
			}
			RefreshCurrentProfile(m_Option.OperatingMode);
		}
		catch (Exception ex)
		{
			LogCtrl.TraceMessage("Exception" + ex.Message, "UserSet_Mode_Detail", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5.cs", 1060);
		}
	}

	private void UserRestore_Mode_Details()
	{
		RestoreCurrentProfile(m_Option.OperatingMode);
		if (m_Option.OperatingMode == 0 && m_GpuWhisperModeSupport)
		{
			m_Option.WhisperModeSwitch = 1;
			if (CustomizeCtrl.GetCustomId() == 22)
			{
				m_Option.WhisperModeSetting = 2;
			}
			else
			{
				m_Option.WhisperModeSetting = 0;
			}
			m_Option.WhisperModeMinFps_QUIETER = 30;
			m_Option.WhisperModeMinFps_QUIET = 40;
			m_Option.WhisperModeMinFps_BALANCED = 60;
			WriteMainOptionToJson("WhisperModeSwitch", Convert.ToUInt32(m_Option.WhisperModeSwitch));
			WriteMainOptionToJson("WhisperModeSetting", Convert.ToUInt32(m_Option.WhisperModeSetting));
			WriteMainOptionToJson("WhisperModeMinFps_QUIETER", Convert.ToUInt32(m_Option.WhisperModeMinFps_QUIETER));
			WriteMainOptionToJson("WhisperModeMinFps_QUIET", Convert.ToUInt32(m_Option.WhisperModeMinFps_QUIET));
			WriteMainOptionToJson("WhisperModeMinFps_BALANCED", Convert.ToUInt32(m_Option.WhisperModeMinFps_BALANCED));
		}
		SetUserProfile(m_Option.OperatingMode);
	}

	private void UserSet_DefaultNotifyStatus(uint status)
	{
		if (status == 1)
		{
			m_Option.DefaultNotify = 1u;
		}
		else
		{
			m_Option.DefaultNotify = 0u;
		}
		WriteMainOptionToJson("DefaultNotify", m_Option.DefaultNotify);
	}

	private void UserSet_FanSafetyProtectNotifyStatus(uint status)
	{
		if (status == 1)
		{
			m_Option.FanSafetyProtectNotify = 1u;
		}
		else
		{
			m_Option.FanSafetyProtectNotify = 0u;
		}
		WriteMainOptionToJson("FanSafetyProtectNotify", m_Option.FanSafetyProtectNotify);
	}

	private void LoadProfileAll()
	{
		GetGamingPLDefaultValue(ref GamingModePLDefaultValue.PL1, ref GamingModePLDefaultValue.PL2, ref GamingModePLDefaultValue.PL4, ref GamingModePLDefaultValue.DState);
		GetOfficePLDefaultValue(ref OfficeModePLDefaultValue.PL1, ref OfficeModePLDefaultValue.PL2, ref OfficeModePLDefaultValue.PL4, ref OfficeModePLDefaultValue.DState);
		GetTurboPLDefaultValue(ref TurboModePLDefaultValue.PL1, ref TurboModePLDefaultValue.PL2, ref TurboModePLDefaultValue.PL4, ref TurboModePLDefaultValue.DState);
		GetTccDefaultValue(ref GamingModePLDefaultValue.TCC, ref OfficeModePLDefaultValue.TCC, ref TurboModePLDefaultValue.TCC);
		RefreshCpuPLMinimumValue();
		if (m_IsNvGpu)
		{
			GpuThermalLimitInfo = cGpuFeatures.GetGpuThermalLimitInfo();
			m_GpuWhisperModeSupport = cGpuFeatures.IsGpuWhisperMode2p0Support();
			LogCtrl.TraceMessage("NV API WhisperModeSupport: " + m_GpuWhisperModeSupport, "LoadProfileAll", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5.cs", 1183);
			if (m_IsHeroProject)
			{
				GpuDynamicBoostDefaultValue = 20;
			}
			else
			{
				GpuDynamicBoostDefaultValue = 5;
			}
			LogCtrl.TraceMessage("m_IsHeroProject: " + m_IsHeroProject + ", then GpuDynamicBoostDefaultValue: " + GpuDynamicBoostDefaultValue, "LoadProfileAll", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5.cs", 1195);
		}
		LoadNvramVariableInfo();
		if (NvramVariableInfo.ApUseFlag != 1)
		{
			LogCtrl.TraceMessage("NvramVariable ApUseFlag != 1, then get BIOS SMAPCTable.", "LoadProfileAll", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5.cs", 1213);
			_SmartApcTable = SmartApcTableCtrl.Instance.GetSMAPCTable();
			NvramVariable.SetFwVars("ApUseFlag", 1);
			WriteSMAPCTableRegistryAll(_SmartApcTable);
		}
		else
		{
			LogCtrl.TraceMessage("NvramVariable ApUseFlag == 1, then get SMAPCTable from local registry.", "LoadProfileAll", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5.cs", 1220);
			try
			{
				int num = 0;
				int num2 = 0;
				int num3 = 0;
				int num4 = 0;
				int num5 = 0;
				int num6 = 0;
				int num7 = 0;
				num = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_RegistryPath, "PL1", 0);
				num2 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_RegistryPath, "PL2", 0);
				num3 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_RegistryPath, "PL4", 0);
				num4 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_RegistryPath, "TccOffset", 0);
				num5 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_RegistryPath, "ConfigurableTGP", 0);
				num6 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_RegistryPath, "DynamicBoost", 0);
				num7 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_RegistryPath, "DefaultTGP", 0);
				_SmartApcTable.PL1 = Convert.ToByte(num);
				_SmartApcTable.PL2 = Convert.ToByte(num2);
				_SmartApcTable.PL4 = Convert.ToByte(num3);
				_SmartApcTable.TccOffset = Convert.ToByte(num4);
				_SmartApcTable.ConfigurableTGP = Convert.ToByte(num5);
				_SmartApcTable.DynamicBoost = Convert.ToByte(num6);
				_SmartApcTable.DefaultTGP = Convert.ToByte(num7);
				if (CheckIvalidSmartAPCTable(_SmartApcTable))
				{
					LogCtrl.TraceMessage("NvramVariable ApUseFlag == 1, but smartapctabl error load default", "LoadProfileAll", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5.cs", 1250);
					_SmartApcTable = SmartApcTableCtrl.Instance.GetSMAPCTable();
					WriteSMAPCTableRegistryAll(_SmartApcTable);
				}
			}
			catch
			{
				LogCtrl.TraceMessage("Load SMAPCTable Registry Fail, then get BIOS SMAPCTable.", "LoadProfileAll", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5.cs", 1259);
				_SmartApcTable = SmartApcTableCtrl.Instance.GetSMAPCTable();
				WriteSMAPCTableRegistryAll(_SmartApcTable);
			}
		}
		try
		{
			if ((int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2", "DebugMode", 0) == 1)
			{
				NvramVariableInfo.ICpuCoreVoltageOffsetRangeType = 1;
				NvramVariableInfo.CoreVoltageOffsetMaximum = 100;
				NvramVariableInfo.ACpuOverClockSupport = 0;
				NvramVariableInfo.ACpuFreqValueMaximum = 255u;
				NvramVariableInfo.ACpuFreqValueMinimum = 0u;
				NvramVariableInfo.ACpuVoltageValueMaximum = 2000u;
				NvramVariableInfo.ACpuVoltageValueMinimum = 0u;
				NvramVariableInfo.MemoryOverClockSupport = 1;
				_SmartApcTable.PL1 = 120;
				_SmartApcTable.PL2 = 120;
				_SmartApcTable.PL4 = 165;
				if (m_IsAMDPlatform)
				{
					_SmartApcTable.TccOffset = 95;
				}
				else
				{
					_SmartApcTable.TccOffset = 5;
				}
				_SmartApcTable.ConfigurableTGP = 20;
				_SmartApcTable.DynamicBoost = 15;
				_SmartApcTable.DefaultTGP = 115;
				WriteSMAPCTableRegistryAll(_SmartApcTable);
				m_GpuWhisperModeSupport = true;
			}
		}
		catch (Exception ex)
		{
			LogCtrl.TraceMessage("Load Features Registry Exception" + ex.Message, "LoadProfileAll", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5.cs", 1305);
		}
		LogCtrl.TraceMessage("NvramVariableInfo, CoreVoltageOffsetMaximum: " + NvramVariableInfo.CoreVoltageOffsetMaximum + ", ACpuOverClockSupport: " + NvramVariableInfo.ACpuOverClockSupport + ", ACpuFreqValueMaximum: " + NvramVariableInfo.ACpuFreqValueMaximum + ", ACpuFreqValueMinimum: " + NvramVariableInfo.ACpuFreqValueMinimum + ", ACpuVoltageValueMaximum: " + NvramVariableInfo.ACpuVoltageValueMaximum + ", ACpuVoltageValueMinimum: " + NvramVariableInfo.ACpuVoltageValueMinimum + ", OverClockRecoveryFlag: " + NvramVariableInfo.OverClockRecoveryFlag, "LoadProfileAll", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5.cs", 1308);
		if (NvramVariableInfo.ICpuCoreVoltageOffsetRangeType == 0)
		{
			CpuOffsetCoreVoltageMinimum = 0;
			CpuOffsetCoreVoltageMaximum = NvramVariableInfo.CoreVoltageOffsetMaximum;
		}
		else if (NvramVariableInfo.ICpuCoreVoltageOffsetRangeType == 1)
		{
			CpuOffsetCoreVoltageMinimum = -NvramVariableInfo.CoreVoltageOffsetMaximum;
			CpuOffsetCoreVoltageMaximum = 0;
		}
		else if (NvramVariableInfo.ICpuCoreVoltageOffsetRangeType == 2)
		{
			CpuOffsetCoreVoltageMinimum = -NvramVariableInfo.CoreVoltageOffsetMaximum;
			CpuOffsetCoreVoltageMaximum = NvramVariableInfo.CoreVoltageOffsetMaximum;
		}
		LogCtrl.TraceMessage("ICpuCoreVoltageOffset, RangeType: " + NvramVariableInfo.ICpuCoreVoltageOffsetRangeType + ", Minimum: " + CpuOffsetCoreVoltageMinimum + ", Maximum: " + CpuOffsetCoreVoltageMaximum, "LoadProfileAll", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5.cs", 1335);
		LogCtrl.TraceMessage("SmartApcTable, PL1: " + _SmartApcTable.PL1 + ", PL2: " + _SmartApcTable.PL2 + ", PL4: " + _SmartApcTable.PL4 + ", TccOffset: " + _SmartApcTable.TccOffset + ", ConfigurableTGP(range): " + _SmartApcTable.ConfigurableTGP + ", DynamicBoost: " + _SmartApcTable.DynamicBoost + ", DefaultTGP(base): " + _SmartApcTable.DefaultTGP, "LoadProfileAll", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5.cs", 1339);
		CheckInvalidSmartApcTable();
		m_GpuConfigurableTGPMaximum = _SmartApcTable.DefaultTGP + _SmartApcTable.ConfigurableTGP;
		m_GpuConfigurableTGPSupport = _SmartApcTable.ConfigurableTGP > 0;
		m_GpuDynamicBoostSupport = _SmartApcTable.DynamicBoost > 0;
		if (Directory.Exists(m_path))
		{
			m_Option = LoadMainOptionFromJson("MainOption");
			Mode1_Profile1 = LoadProfileFromJson("Mode1_Profile1");
			Mode1_Profile2 = LoadProfileFromJson("Mode1_Profile2");
			Mode1_Profile3 = LoadProfileFromJson("Mode1_Profile3");
			Mode1_Profile4 = LoadProfileFromJson("Mode1_Profile4");
			Mode1_Profile5 = LoadProfileFromJson("Mode1_Profile5");
			Mode2_Profile1 = LoadProfileFromJson("Mode2_Profile1");
			Mode2_Profile2 = LoadProfileFromJson("Mode2_Profile2");
			Mode2_Profile3 = LoadProfileFromJson("Mode2_Profile3");
			Mode2_Profile4 = LoadProfileFromJson("Mode2_Profile4");
			Mode2_Profile5 = LoadProfileFromJson("Mode2_Profile5");
			Mode3_Profile1 = LoadProfileFromJson("Mode3_Profile1");
			Mode3_Profile2 = LoadProfileFromJson("Mode3_Profile2");
			Mode3_Profile3 = LoadProfileFromJson("Mode3_Profile3");
			Mode3_Profile4 = LoadProfileFromJson("Mode3_Profile4");
			Mode3_Profile5 = LoadProfileFromJson("Mode3_Profile5");
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

	private void WriteSMAPCTableRegistryAll(SMAPCTABLE_STRUCT _table)
	{
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_RegistryPath, "PL1", _table.PL1, RegistryValueKind.DWord);
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_RegistryPath, "PL2", _table.PL2, RegistryValueKind.DWord);
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_RegistryPath, "PL4", _table.PL4, RegistryValueKind.DWord);
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_RegistryPath, "TccOffset", _table.TccOffset, RegistryValueKind.DWord);
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_RegistryPath, "ConfigurableTGP", _table.ConfigurableTGP, RegistryValueKind.DWord);
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_RegistryPath, "DynamicBoost", _table.DynamicBoost, RegistryValueKind.DWord);
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_RegistryPath, "DefaultTGP", _table.DefaultTGP, RegistryValueKind.DWord);
	}

	private bool CheckIvalidSmartAPCTable(SMAPCTABLE_STRUCT _SmartApcTable)
	{
		LogCtrl.TraceMessage("Check SmartApcTable, PL1: " + _SmartApcTable.PL1 + ", PL2: " + _SmartApcTable.PL2 + ", PL4: " + _SmartApcTable.PL4 + ", TccOffset: " + _SmartApcTable.TccOffset + ", ConfigurableTGP(range): " + _SmartApcTable.ConfigurableTGP + ", DynamicBoost: " + _SmartApcTable.DynamicBoost + ", DefaultTGP(base): " + _SmartApcTable.DefaultTGP, "CheckIvalidSmartAPCTable", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5.cs", 1403);
		if (_SmartApcTable.PL1 != byte.MaxValue)
		{
			return false;
		}
		if (_SmartApcTable.PL2 != byte.MaxValue)
		{
			return false;
		}
		if (_SmartApcTable.PL4 != byte.MaxValue)
		{
			return false;
		}
		if (_SmartApcTable.TccOffset != byte.MaxValue)
		{
			return false;
		}
		if (_SmartApcTable.ConfigurableTGP != byte.MaxValue)
		{
			return false;
		}
		if (_SmartApcTable.DynamicBoost != byte.MaxValue)
		{
			return false;
		}
		if (_SmartApcTable.DefaultTGP != byte.MaxValue)
		{
			return false;
		}
		return true;
	}

	private void CheckInvalidSmartApcTable()
	{
		if (_SmartApcTable.PL1 == byte.MaxValue)
		{
			_SmartApcTable.PL1 = 0;
		}
		if (_SmartApcTable.PL2 == byte.MaxValue)
		{
			_SmartApcTable.PL2 = 0;
		}
		if (_SmartApcTable.PL4 == byte.MaxValue)
		{
			_SmartApcTable.PL4 = 0;
		}
		if (_SmartApcTable.TccOffset == byte.MaxValue)
		{
			_SmartApcTable.TccOffset = 0;
		}
		if (_SmartApcTable.ConfigurableTGP == byte.MaxValue)
		{
			_SmartApcTable.ConfigurableTGP = 0;
		}
		if (_SmartApcTable.DynamicBoost == byte.MaxValue)
		{
			_SmartApcTable.DynamicBoost = 0;
		}
		if (_SmartApcTable.DefaultTGP == byte.MaxValue)
		{
			_SmartApcTable.DefaultTGP = 0;
		}
	}

	private void RefreshDefaultProfiles()
	{
		if (!Mode1_Profile1.Activated)
		{
			RefreshMode(ref Mode1_Profile1, "Mode1_Profile1", "1", GamingModePLDefaultValue, "M1T1");
			CreateModeProfiles(Mode1_Profile1);
		}
		if (!Mode1_Profile2.Activated)
		{
			RefreshMode(ref Mode1_Profile2, "Mode1_Profile2", "2", GamingModePLDefaultValue, "M1T2");
			CreateModeProfiles(Mode1_Profile2);
		}
		if (!Mode1_Profile3.Activated)
		{
			RefreshMode(ref Mode1_Profile3, "Mode1_Profile3", "3", GamingModePLDefaultValue, "M1T3");
			CreateModeProfiles(Mode1_Profile3);
		}
		if (!Mode1_Profile4.Activated)
		{
			RefreshMode(ref Mode1_Profile4, "Mode1_Profile4", "4", GamingModePLDefaultValue, "M1T4");
			CreateModeProfiles(Mode1_Profile4);
		}
		if (!Mode1_Profile5.Activated)
		{
			RefreshMode(ref Mode1_Profile5, "Mode1_Profile5", "5", GamingModePLDefaultValue, "M1T5");
			CreateModeProfiles(Mode1_Profile5);
		}
		if (!Mode2_Profile1.Activated)
		{
			RefreshMode(ref Mode2_Profile1, "Mode2_Profile1", "1", OfficeModePLDefaultValue, "M2T1");
			CreateModeProfiles(Mode2_Profile1);
		}
		if (!Mode2_Profile2.Activated)
		{
			RefreshMode(ref Mode2_Profile2, "Mode2_Profile2", "2", OfficeModePLDefaultValue, "M2T2");
			CreateModeProfiles(Mode2_Profile2);
		}
		if (!Mode2_Profile3.Activated)
		{
			RefreshMode(ref Mode2_Profile3, "Mode2_Profile3", "3", OfficeModePLDefaultValue, "M2T3");
			CreateModeProfiles(Mode2_Profile3);
		}
		if (!Mode2_Profile4.Activated)
		{
			RefreshMode(ref Mode2_Profile4, "Mode2_Profile4", "4", OfficeModePLDefaultValue, "M2T4");
			CreateModeProfiles(Mode2_Profile4);
		}
		if (!Mode2_Profile5.Activated)
		{
			RefreshMode(ref Mode2_Profile5, "Mode2_Profile5", "5", OfficeModePLDefaultValue, "M2T5");
			CreateModeProfiles(Mode2_Profile5);
		}
		if (!Mode3_Profile1.Activated)
		{
			RefreshMode(ref Mode3_Profile1, "Mode3_Profile1", "1", TurboModePLDefaultValue, "M3T1");
			CreateModeProfiles(Mode3_Profile1);
		}
		if (!Mode3_Profile2.Activated)
		{
			RefreshMode(ref Mode3_Profile2, "Mode3_Profile2", "2", TurboModePLDefaultValue, "M3T2");
			CreateModeProfiles(Mode3_Profile2);
		}
		if (!Mode3_Profile3.Activated)
		{
			RefreshMode(ref Mode3_Profile3, "Mode3_Profile3", "3", TurboModePLDefaultValue, "M3T3");
			CreateModeProfiles(Mode3_Profile3);
		}
		if (!Mode3_Profile4.Activated)
		{
			RefreshMode(ref Mode3_Profile4, "Mode3_Profile4", "4", TurboModePLDefaultValue, "M3T4");
			CreateModeProfiles(Mode3_Profile4);
		}
		if (!Mode3_Profile5.Activated)
		{
			RefreshMode(ref Mode3_Profile5, "Mode3_Profile5", "5", TurboModePLDefaultValue, "M3T5");
			CreateModeProfiles(Mode3_Profile5);
		}
	}

	private void LoadDefault()
	{
		m_Option.OperatingMode = m_DefaultMode;
		m_Option.GamingProfileIndex = 0u;
		m_Option.OfficeProfileIndex = 0u;
		m_Option.TurboProfileIndex = 0u;
		m_Option.FanBoostEnable = 0u;
		m_Option.FanSafetyProtectNotify = 0u;
		m_Option.DefaultNotify = 0u;
		m_Option.BsodTimestampRestored = DateTime.Now;
		m_Option.WhisperModeSwitch = 1;
		if (CustomizeCtrl.GetCustomId() == 22)
		{
			m_Option.WhisperModeSetting = 2;
		}
		else
		{
			m_Option.WhisperModeSetting = 0;
		}
		m_Option.WhisperModeMinFps_QUIETER = 30;
		m_Option.WhisperModeMinFps_QUIET = 40;
		m_Option.WhisperModeMinFps_BALANCED = 60;
		CreateMainOption(m_Option);
		RefreshMode(ref Mode1_Profile1, "Mode1_Profile1", "1", GamingModePLDefaultValue, "M1T1");
		RefreshMode(ref Mode1_Profile2, "Mode1_Profile2", "2", GamingModePLDefaultValue, "M1T2");
		RefreshMode(ref Mode1_Profile3, "Mode1_Profile3", "3", GamingModePLDefaultValue, "M1T3");
		RefreshMode(ref Mode1_Profile4, "Mode1_Profile4", "4", GamingModePLDefaultValue, "M1T4");
		RefreshMode(ref Mode1_Profile5, "Mode1_Profile5", "5", GamingModePLDefaultValue, "M1T5");
		RefreshMode(ref Mode2_Profile1, "Mode2_Profile1", "1", OfficeModePLDefaultValue, "M2T1");
		RefreshMode(ref Mode2_Profile2, "Mode2_Profile2", "2", OfficeModePLDefaultValue, "M2T2");
		RefreshMode(ref Mode2_Profile3, "Mode2_Profile3", "3", OfficeModePLDefaultValue, "M2T3");
		RefreshMode(ref Mode2_Profile4, "Mode2_Profile4", "4", OfficeModePLDefaultValue, "M2T4");
		RefreshMode(ref Mode2_Profile5, "Mode2_Profile5", "5", OfficeModePLDefaultValue, "M2T5");
		RefreshMode(ref Mode3_Profile1, "Mode3_Profile1", "1", TurboModePLDefaultValue, "M3T1");
		RefreshMode(ref Mode3_Profile2, "Mode3_Profile2", "2", TurboModePLDefaultValue, "M3T2");
		RefreshMode(ref Mode3_Profile3, "Mode3_Profile3", "3", TurboModePLDefaultValue, "M3T3");
		RefreshMode(ref Mode3_Profile4, "Mode3_Profile4", "4", TurboModePLDefaultValue, "M3T4");
		RefreshMode(ref Mode3_Profile5, "Mode3_Profile5", "5", TurboModePLDefaultValue, "M3T5");
		CreateModeProfiles(Mode1_Profile1);
		CreateModeProfiles(Mode1_Profile2);
		CreateModeProfiles(Mode1_Profile3);
		CreateModeProfiles(Mode1_Profile4);
		CreateModeProfiles(Mode1_Profile5);
		CreateModeProfiles(Mode2_Profile1);
		CreateModeProfiles(Mode2_Profile2);
		CreateModeProfiles(Mode2_Profile3);
		CreateModeProfiles(Mode2_Profile4);
		CreateModeProfiles(Mode2_Profile5);
		CreateModeProfiles(Mode3_Profile1);
		CreateModeProfiles(Mode3_Profile2);
		CreateModeProfiles(Mode3_Profile3);
		CreateModeProfiles(Mode3_Profile4);
		CreateModeProfiles(Mode3_Profile5);
	}

	private void RefreshMode(ref ModeProfile profile, string name, string customizeName, PLDefaultValue defaultValue, string fanTableName)
	{
		profile.Activated = false;
		profile.Name = name;
		profile.CustomizeName = customizeName;
		profile.FAN.FanSwitchSpeedEnabled = 0;
		profile.FAN.FanSwitchSpeed = 300;
		profile.FAN.TableName = fanTableName;
		profile.CPU.PL1 = defaultValue.PL1;
		profile.CPU.PL2 = defaultValue.PL2;
		profile.CPU.PL4 = defaultValue.PL4;
		profile.CPU.OffsetCoreVoltage = 0;
		profile.CPU.TccOffsetSwitch = 0;
		profile.CPU.TccOffset = defaultValue.TCC;
		profile.GPU.CoreClockOffset = 0;
		profile.GPU.MemoryClockOffset = 0;
		profile.GPU.TargetTemperature = GpuThermalLimitInfo.DefaultTemperature;
		profile.GPU.ConfigurableTGPSwitch = 0;
		profile.GPU.ConfigurableTGPTarget = m_GpuConfigurableTGPMaximum;
		if (CustomizeCtrl.GetCustomId() == 11)
		{
			if (fanTableName.Substring(0, 2) != "M3")
			{
				profile.GPU.DynamicBoostSwitch = 0;
			}
			else
			{
				profile.GPU.DynamicBoostSwitch = 1;
			}
		}
		else
		{
			profile.GPU.DynamicBoostSwitch = 1;
		}
		profile.GPU.DynamicBoost = GpuDynamicBoostDefaultValue;
		profile.GPU.DynamicBoostTotalProcessingPowerTarget = 255;
		profile.CPU.AmdSPL = defaultValue.PL1;
		profile.CPU.AmdSPPT = defaultValue.PL2;
		profile.CPU.AmdFPPT = defaultValue.PL4;
		profile.CPU.AmdTccTarget = defaultValue.TCC;
		profile.CPU.AmdCoreFreq = 0;
		profile.CPU.AmdCoreVoltage = 0;
		profile.MEM.MemoryOverClockSwitch = 0;
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
			LogCtrl.TraceMessage("Exception" + ex.Message, "CreateMainOption", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5.cs", 1676);
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
			LogCtrl.TraceMessage("Exception" + ex.Message, "CreateModeProfiles", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5.cs", 1694);
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
			LogCtrl.TraceMessage("Exception" + ex.Message, "WriteMainOptionToJson", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5.cs", 1746);
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
			LogCtrl.TraceMessage("Exception" + ex.Message, "WriteProfileToJson", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5.cs", 1762);
		}
	}

	private void syncBiosSettings()
	{
		NvramVariable.SetFwVars("ApExistFlag", 1);
		uint num = Convert.ToUInt32(NvramVariable.GetFwVars().PowerMode);
		LogCtrl.TraceMessage("PowerMode = 0x" + num.ToString("X2"), "syncBiosSettings", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5.cs", 1775);
		if (num != 255)
		{
			if (m_Option.OperatingMode != num)
			{
				LogCtrl.TraceMessage("Change local Power Mode.", "syncBiosSettings", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5.cs", 1781);
				m_Option.OperatingMode = num;
				WriteMainOptionToJson("OperatingMode", m_Option.OperatingMode);
			}
		}
		else
		{
			LogCtrl.TraceMessage("NvramVariable Power Mode = 0XFF, then change to default Power Mode.", "syncBiosSettings", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5.cs", 1788);
			m_Option.OperatingMode = m_DefaultMode;
			WriteMainOptionToJson("OperatingMode", m_Option.OperatingMode);
		}
	}

	private void Init()
	{
		if (m_OcSupport)
		{
			DetectRecoveryFlagFromBiosVariable();
			if (m_GpuWhisperModeSupport)
			{
				if (m_IsHeroProject)
				{
					UpdateWhisperStatus();
				}
				else
				{
					m_Option.WhisperModeSwitch = 1;
					WriteMainOptionToJson("WhisperModeSwitch", Convert.ToUInt32(m_Option.WhisperModeSwitch));
				}
			}
		}
		LogCtrl.TraceMessage("OperatingMode = " + m_Option.OperatingMode + ", " + OperatingModeString(m_Option.OperatingMode), "Init", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5.cs", 1837);
		RefreshCurrentProfile(m_Option.OperatingMode, save: false);
		SetUserProfile(m_Option.OperatingMode);
	}

	private void RefreshCurrentProfile(uint mode, bool save = true)
	{
		switch (mode)
		{
		case 1u:
			switch (m_Option.GamingProfileIndex)
			{
			case 0u:
				currentProfile = Mode1_Profile1;
				break;
			case 1u:
				currentProfile = Mode1_Profile2;
				break;
			case 2u:
				currentProfile = Mode1_Profile3;
				break;
			case 3u:
				currentProfile = Mode1_Profile4;
				break;
			case 4u:
				currentProfile = Mode1_Profile5;
				break;
			}
			break;
		case 0u:
			switch (m_Option.OfficeProfileIndex)
			{
			case 0u:
				currentProfile = Mode2_Profile1;
				break;
			case 1u:
				currentProfile = Mode2_Profile2;
				break;
			case 2u:
				currentProfile = Mode2_Profile3;
				break;
			case 3u:
				currentProfile = Mode2_Profile4;
				break;
			case 4u:
				currentProfile = Mode2_Profile5;
				break;
			}
			break;
		case 2u:
			switch (m_Option.TurboProfileIndex)
			{
			case 0u:
				currentProfile = Mode3_Profile1;
				break;
			case 1u:
				currentProfile = Mode3_Profile2;
				break;
			case 2u:
				currentProfile = Mode3_Profile3;
				break;
			case 3u:
				currentProfile = Mode3_Profile4;
				break;
			case 4u:
				currentProfile = Mode3_Profile5;
				break;
			}
			break;
		}
		CheckInvalidParameter();
		if (save)
		{
			WriteProfileToJson(currentProfile);
		}
	}

	private void CheckInvalidParameter()
	{
		if (currentProfile.CPU.PL1 > currentProfile.CPU.PL2)
		{
			currentProfile.CPU.PL2 = currentProfile.CPU.PL1;
		}
		if (currentProfile.CPU.AmdSPL > currentProfile.CPU.AmdSPPT)
		{
			currentProfile.CPU.AmdSPPT = currentProfile.CPU.AmdSPL;
		}
	}

	private void RestoreCurrentProfile(uint mode)
	{
		switch (mode)
		{
		case 1u:
			switch (m_Option.GamingProfileIndex)
			{
			case 0u:
				RefreshMode(ref Mode1_Profile1, "Mode1_Profile1", "1", GamingModePLDefaultValue, "M1T1");
				CreateModeProfiles(Mode1_Profile1);
				currentProfile = Mode1_Profile1;
				break;
			case 1u:
				RefreshMode(ref Mode1_Profile2, "Mode1_Profile2", "2", GamingModePLDefaultValue, "M1T2");
				CreateModeProfiles(Mode1_Profile2);
				currentProfile = Mode1_Profile2;
				break;
			case 2u:
				RefreshMode(ref Mode1_Profile3, "Mode1_Profile3", "3", GamingModePLDefaultValue, "M1T3");
				CreateModeProfiles(Mode1_Profile3);
				currentProfile = Mode1_Profile3;
				break;
			case 3u:
				RefreshMode(ref Mode1_Profile4, "Mode1_Profile4", "4", GamingModePLDefaultValue, "M1T4");
				CreateModeProfiles(Mode1_Profile4);
				currentProfile = Mode1_Profile4;
				break;
			case 4u:
				RefreshMode(ref Mode1_Profile5, "Mode1_Profile5", "5", GamingModePLDefaultValue, "M1T5");
				CreateModeProfiles(Mode1_Profile5);
				currentProfile = Mode1_Profile5;
				break;
			}
			break;
		case 0u:
			switch (m_Option.OfficeProfileIndex)
			{
			case 0u:
				RefreshMode(ref Mode2_Profile1, "Mode2_Profile1", "1", OfficeModePLDefaultValue, "M2T1");
				CreateModeProfiles(Mode2_Profile1);
				currentProfile = Mode2_Profile1;
				break;
			case 1u:
				RefreshMode(ref Mode2_Profile2, "Mode2_Profile2", "2", OfficeModePLDefaultValue, "M2T2");
				CreateModeProfiles(Mode2_Profile2);
				currentProfile = Mode2_Profile2;
				break;
			case 2u:
				RefreshMode(ref Mode2_Profile3, "Mode2_Profile3", "3", OfficeModePLDefaultValue, "M2T3");
				CreateModeProfiles(Mode2_Profile3);
				currentProfile = Mode2_Profile3;
				break;
			case 3u:
				RefreshMode(ref Mode2_Profile4, "Mode2_Profile4", "4", OfficeModePLDefaultValue, "M2T4");
				CreateModeProfiles(Mode2_Profile4);
				currentProfile = Mode2_Profile4;
				break;
			case 4u:
				RefreshMode(ref Mode2_Profile5, "Mode2_Profile5", "5", OfficeModePLDefaultValue, "M2T5");
				CreateModeProfiles(Mode2_Profile5);
				currentProfile = Mode2_Profile5;
				break;
			}
			break;
		case 2u:
			switch (m_Option.TurboProfileIndex)
			{
			case 0u:
				RefreshMode(ref Mode3_Profile1, "Mode3_Profile1", "1", TurboModePLDefaultValue, "M3T1");
				CreateModeProfiles(Mode3_Profile1);
				currentProfile = Mode3_Profile1;
				break;
			case 1u:
				RefreshMode(ref Mode3_Profile2, "Mode3_Profile2", "2", TurboModePLDefaultValue, "M3T2");
				CreateModeProfiles(Mode3_Profile2);
				currentProfile = Mode3_Profile2;
				break;
			case 2u:
				RefreshMode(ref Mode3_Profile3, "Mode3_Profile3", "3", TurboModePLDefaultValue, "M3T3");
				CreateModeProfiles(Mode3_Profile3);
				currentProfile = Mode3_Profile3;
				break;
			case 3u:
				RefreshMode(ref Mode3_Profile4, "Mode3_Profile4", "4", TurboModePLDefaultValue, "M3T4");
				CreateModeProfiles(Mode3_Profile4);
				currentProfile = Mode3_Profile4;
				break;
			case 4u:
				RefreshMode(ref Mode3_Profile5, "Mode3_Profile5", "5", TurboModePLDefaultValue, "M3T5");
				CreateModeProfiles(Mode3_Profile5);
				currentProfile = Mode3_Profile5;
				break;
			}
			break;
		}
	}

	private void SetUserProfile(uint mode)
	{
		SetFanMode(mode);
		UpdateStatusToTray();
		m_FanSafetyProtect = GetFanSafetyProtectStatus();
		if (m_FanSafetyProtect == 1)
		{
			m_Option.FanSafetyProtectNotify = 1u;
			switch (mode)
			{
			case 1u:
				FanTable.SetFanTable("DefaultFanTable_Gaming");
				break;
			case 0u:
				FanTable.SetFanTable("DefaultFanTable_Office");
				break;
			case 2u:
				FanTable.SetFanTable("DefaultFanTable_Turbo");
				break;
			}
		}
		else
		{
			m_Option.FanSafetyProtectNotify = 0u;
			FanTable.SetFanTable(currentProfile.FAN.TableName);
		}
		WriteMainOptionToJson("FanSafetyProtectNotify", m_Option.FanSafetyProtectNotify);
		if (!m_OcSupport)
		{
			return;
		}
		if (m_IsAMDPlatform)
		{
			if (PowerModeEvent.g_ACLineStatus == 1)
			{
				SetPL1Value(currentProfile.CPU.AmdSPL);
				SetPL2Value(currentProfile.CPU.AmdSPPT);
				SetPL4Value(currentProfile.CPU.AmdFPPT);
				if (currentProfile.CPU.AmdSPL >= 75 || currentProfile.CPU.AmdSPPT >= 75)
				{
					SetCpuVrmCurrentLimit(65, 120);
				}
			}
			else
			{
				SetPL1Value(0);
				SetPL2Value(0);
				SetPL4Value(0);
			}
			if (currentProfile.CPU.TccOffsetSwitch == 1)
			{
				SetCpuTccOffset(currentProfile.CPU.AmdTccTarget, bApExist: true);
			}
			else
			{
				SetCpuTccOffset(0, bApExist: false);
			}
			if (NvramVariableInfo.ACpuOverClockSupport == 1)
			{
				SetCpuAmdCoreFreq(currentProfile.CPU.AmdCoreFreq);
				SetCpuAmdCoreVoltage(currentProfile.CPU.AmdCoreVoltage);
			}
		}
		else
		{
			if (PowerModeEvent.g_ACLineStatus == 1)
			{
				SetPL1Value(currentProfile.CPU.PL1);
				SetPL2Value(currentProfile.CPU.PL2);
				SetPL4Value(currentProfile.CPU.PL4);
			}
			else
			{
				SetPL1Value(0);
				SetPL2Value(0);
				SetPL4Value(0);
			}
			SetCpuCoreVoltageOffset(currentProfile.CPU.OffsetCoreVoltage);
			if (currentProfile.CPU.TccOffsetSwitch == 1)
			{
				SetCpuTccOffset(currentProfile.CPU.TccOffset, bApExist: true);
			}
			else
			{
				SetCpuTccOffset(0, bApExist: false);
			}
		}
		if (m_IsNvGpu)
		{
			cGpuFeatures.SetGpuCoreFreqOffsetValue(currentProfile.GPU.CoreClockOffset);
			cGpuFeatures.SetGpuMemFreqOffsetValue(currentProfile.GPU.MemoryClockOffset);
			cGpuFeatures.SetGpuTargetTemperature(currentProfile.GPU.TargetTemperature);
			if (m_IsHeroProject)
			{
				if (mode == 0)
				{
					cGpuFeatures.SetGpuWhisperModeMainSwitch(1);
				}
				else
				{
					cGpuFeatures.SetGpuWhisperModeMainSwitch(0);
				}
			}
			if (PowerModeEvent.g_ACLineStatus == 1)
			{
				if (m_GpuConfigurableTGPSupport)
				{
					if (currentProfile.GPU.DynamicBoostSwitch == 1)
					{
						if (currentProfile.GPU.ConfigurableTGPTarget > m_GpuConfigurableTGPMaximum)
						{
							cGpuFeatures.SetGpuConfigurableTGPTarget(m_GpuConfigurableTGPMaximum, _SmartApcTable.DefaultTGP);
						}
						else
						{
							cGpuFeatures.SetGpuConfigurableTGPTarget(currentProfile.GPU.ConfigurableTGPTarget, _SmartApcTable.DefaultTGP);
						}
					}
					else
					{
						cGpuFeatures.SetGpuConfigurableTGPTarget(currentProfile.GPU.ConfigurableTGPTarget, _SmartApcTable.DefaultTGP);
					}
					cGpuFeatures.SetGpuConfigurableTgpFunCtrlEnable(currentProfile.GPU.ConfigurableTGPSwitch);
				}
				else if (currentProfile.GPU.DynamicBoostSwitch == 1)
				{
					cGpuFeatures.SetGpuConfigurableTGPTarget(0, _SmartApcTable.DefaultTGP);
					cGpuFeatures.SetGpuConfigurableTgpFunCtrlEnable(0);
				}
				else
				{
					cGpuFeatures.SetGpuConfigurableTGPTarget(currentProfile.GPU.ConfigurableTGPTarget, _SmartApcTable.DefaultTGP);
					cGpuFeatures.SetGpuConfigurableTgpFunCtrlEnable(currentProfile.GPU.ConfigurableTGPSwitch);
				}
				if (m_GpuDynamicBoostSupport)
				{
					SetGpuDynamicBoostSwitch(currentProfile.GPU.DynamicBoostSwitch);
					cGpuFeatures.SetGpuDynamicBoostFunCtrlEnable(1);
				}
				else
				{
					SetGpuDynamicBoostSwitch(0);
					cGpuFeatures.SetGpuDynamicBoostFunCtrlEnable(0);
				}
				if (mode == 0)
				{
					if (m_IsHeroProject)
					{
						SetGpuWhisperModeSwitchOnOFF(m_Option.WhisperModeSwitch);
					}
					else
					{
						m_Option.WhisperModeSwitch = 1;
						SetGpuWhisperModeSwitchOnOFF(m_Option.WhisperModeSwitch);
					}
				}
				else
				{
					SetGpuWhisperModeSwitchOnOFF(0);
				}
			}
			else
			{
				cGpuFeatures.SetGpuConfigurableTGPTarget(0, _SmartApcTable.DefaultTGP);
				cGpuFeatures.SetGpuConfigurableTgpFunCtrlEnable(0);
				SetGpuDynamicBoostSwitch(0);
				cGpuFeatures.SetGpuDynamicBoostFunCtrlEnable(0);
				SetGpuWhisperModeSwitchOnOFF(0);
			}
		}
		SetFanSwitchSpeedEnabled(currentProfile.FAN.FanSwitchSpeedEnabled);
		if (NvramVariableInfo.MemoryOverClockSupport == 1)
		{
			SetMemoryOverClockSwitch(currentProfile.MEM.MemoryOverClockSwitch);
		}
	}

	private void SetGpuDynamicBoostSwitch(int status)
	{
		if (status == 1)
		{
			cGpuFeatures.SetGpuDynamicBoostTotalProcessingPowerTarget(currentProfile.GPU.DynamicBoostTotalProcessingPowerTarget);
			cGpuFeatures.SetGpuDynamicBoostMaxinumTGP(currentProfile.GPU.DynamicBoost);
			cGpuFeatures.SetGpuDynamicBoostEnable(status);
		}
		else
		{
			cGpuFeatures.SetGpuDynamicBoostTotalProcessingPowerTarget(0);
			cGpuFeatures.SetGpuDynamicBoostMaxinumTGP(0);
			cGpuFeatures.SetGpuDynamicBoostEnable(status);
		}
	}

	private void SetGpuWhisperModeSwitchOnOFF(int status)
	{
		if (!m_GpuWhisperModeSupport)
		{
			return;
		}
		if (status == 1)
		{
			cGpuFeatures.SetGpuWhisperModeStatus(status: true);
			cGpuFeatures.SetGpuWhisperModeSettingValue(m_Option.WhisperModeSetting);
			switch (m_Option.WhisperModeSetting)
			{
			case 0:
				cGpuFeatures.SetGpuWhisperModeMinFpsValue(m_Option.WhisperModeMinFps_QUIETER);
				break;
			case 1:
				cGpuFeatures.SetGpuWhisperModeMinFpsValue(m_Option.WhisperModeMinFps_QUIET);
				break;
			case 2:
				cGpuFeatures.SetGpuWhisperModeMinFpsValue(m_Option.WhisperModeMinFps_BALANCED);
				break;
			}
			LogCtrl.TraceMessage("SetGpuWhisperModeStatus: " + status + ", SetGpuWhisperModeSettingValue: " + m_Option.WhisperModeSetting, "SetGpuWhisperModeSwitchOnOFF", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5.cs", 2358);
		}
		else
		{
			cGpuFeatures.SetGpuWhisperModeStatus(status: false);
			LogCtrl.TraceMessage("SetGpuWhisperModeStatus: " + status, "SetGpuWhisperModeSwitchOnOFF", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5.cs", 2364);
		}
	}

	private void SetFanSwitchSpeedEnabled(int status)
	{
		if (status == 1)
		{
			SetFanSwitchSpeed(currentProfile.FAN.FanSwitchSpeed, bApExist: true);
		}
		else
		{
			SetFanSwitchSpeed(0, bApExist: false);
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
		LogCtrl.TraceMessage($"EC 0751 bit4[{bitFromByte}], bit7[{bitFromByte2}]", "GetFanMode", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5.cs", 2463);
		return result;
	}

	private void SetCpuVrmCurrentLimit(int limit, int maximum)
	{
		EcCtrl.Write(GetType().Name, 1875, (byte)limit);
		EcCtrl.Write(GetType().Name, 1876, (byte)maximum);
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
		LogCtrl.TraceMessage("Set D-State to: " + dstate, "SetGPUdstate", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5.cs", 2560);
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
		LogCtrl.TraceMessage("Set D-State to: " + num, "SetGPUdstateByGpuMode", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5.cs", 2591);
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
		LogCtrl.TraceMessage("Mode: " + mode + ", Set ECRAM 0x" + ((ushort)1957).ToString("X") + " = 0x" + b3.ToString("X2"), "SetPowerLedStatus", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5.cs", 2676);
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
		LogCtrl.TraceMessage("bEnable " + bEnable + ", Set ECRAM 0x" + ((ushort)1957).ToString("X") + " = 0x" + b3.ToString("X2"), "SetFanQuietModeEnable", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5.cs", 2697);
		EcCtrl.Write(GetType().Name, 1957, b3);
	}

	private int GetFanSafetyProtectStatus()
	{
		byte Data = 0;
		EcCtrl.Read(GetType().Name, 1957, ref Data);
		if (UtilityExtensions.GetBitFromByte(Data, 3) == 1)
		{
			return m_FanSafetyProtect = 1;
		}
		return m_FanSafetyProtect = 0;
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
		LogCtrl.TraceMessage("bEnable " + bEnable + ", Set ECRAM 0x" + ((ushort)1957).ToString("X") + " = 0x" + b3.ToString("X2"), "SetOverBoostMode", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5.cs", 2734);
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
		LogCtrl.TraceMessage("bHigh " + bHigh + ", Set ECRAM 0x" + ((ushort)1957).ToString("X") + " = 0x" + b3.ToString("X2"), "SetPowerStatus", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5.cs", 2755);
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
		LogCtrl.TraceMessage("bEnable " + bEnable + ", Set ECRAM 0x" + ((ushort)1958).ToString("X") + " = 0x" + b3.ToString("X2"), "SetOverBoostByDynamicTemp", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5.cs", 2778);
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
		LogCtrl.TraceMessage("PL1:" + PL1 + ", PL2:" + PL2 + ", PL4:" + PL4 + ", DState:" + DState, "GetGamingPLDefaultValue", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5.cs", 2798);
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
		LogCtrl.TraceMessage("PL1:" + PL1 + ", PL2:" + PL2 + ", PL4:" + PL4 + ", DState:" + DState, "GetOfficePLDefaultValue", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5.cs", 2815);
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
		LogCtrl.TraceMessage("PL1:" + PL1 + ", PL2:" + PL2 + ", PL4:" + PL4 + ", DState:" + DState, "GetTurboPLDefaultValue", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5.cs", 2832);
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

	private void GetTccDefaultValue(ref int gamingTcc, ref int officeTcc, ref int turboTcc)
	{
		byte Data = 0;
		byte Data2 = 0;
		byte Data3 = 0;
		EcCtrl.Read(GetType().Name, 2008, ref Data);
		EcCtrl.Read(GetType().Name, 2009, ref Data2);
		EcCtrl.Read(GetType().Name, 2010, ref Data3);
		gamingTcc = (int)(Convert.ToUInt64(Data) & 0xFF);
		officeTcc = (int)(Convert.ToUInt64(Data2) & 0xFF);
		turboTcc = (int)(Convert.ToUInt64(Data3) & 0xFF);
		LogCtrl.TraceMessage("GamingTcc:" + gamingTcc + ", OfficeTcc:" + officeTcc + ", TurboTcc:" + turboTcc, "GetTccDefaultValue", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5.cs", 2860);
	}

	private void SkipOfficeModeSafetyProtect(int status)
	{
		byte Data = 0;
		byte b = 239;
		byte b2 = 0;
		byte b3 = 0;
		b2 = (byte)((status == 1) ? 16 : 0);
		EcCtrl.Read(GetType().Name, 1989, ref Data);
		b3 = (byte)((Data & b) + b2);
		EcCtrl.Write(GetType().Name, 1989, b3);
	}

	private void SetCpuCoreVoltageOffset(int value)
	{
		if (value == 0)
		{
			LogCtrl.TraceMessage("ICpuCoreVoltageOffsetValue: " + value + ", ICpuCoreVoltageOffsetNegativeValue: " + value, "SetCpuCoreVoltageOffset", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5.cs", 2913);
			NvramVariable.SetFwVars("ICpuCoreVoltageOffsetValue", Convert.ToUInt16(value));
			NvramVariable.SetFwVars("ICpuCoreVoltageOffsetNegativeValue", Convert.ToUInt16(value));
		}
		else if (value > 0 && value <= CpuOffsetCoreVoltageMaximum)
		{
			LogCtrl.TraceMessage("ICpuCoreVoltageOffsetValue: " + value + ", ICpuCoreVoltageOffsetNegativeValue: 0", "SetCpuCoreVoltageOffset", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5.cs", 2927);
			NvramVariable.SetFwVars("ICpuCoreVoltageOffsetValue", Convert.ToUInt16(value));
			NvramVariable.SetFwVars("ICpuCoreVoltageOffsetNegativeValue", Convert.ToUInt16(0));
		}
		else if (value >= CpuOffsetCoreVoltageMinimum && value < 0)
		{
			LogCtrl.TraceMessage("ICpuCoreVoltageOffsetValue: 0, ICpuCoreVoltageOffsetNegativeValue: " + Convert.ToUInt16(Math.Abs(value)), "SetCpuCoreVoltageOffset", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5.cs", 2938);
			NvramVariable.SetFwVars("ICpuCoreVoltageOffsetValue", Convert.ToUInt16(0));
			NvramVariable.SetFwVars("ICpuCoreVoltageOffsetNegativeValue", Convert.ToUInt16(Math.Abs(value)));
		}
		else
		{
			LogCtrl.TraceMessage("Set the value failed, and error is out of range.", "SetCpuCoreVoltageOffset", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5.cs", 2950);
			value = 0;
			NvramVariable.SetFwVars("ICpuCoreVoltageOffsetValue", Convert.ToUInt16(value));
			NvramVariable.SetFwVars("ICpuCoreVoltageOffsetNegativeValue", Convert.ToUInt16(value));
		}
	}

	private void SetCpuAmdCoreFreq(int value)
	{
		if (value >= NvramVariableInfo.ACpuFreqValueMinimum && value <= NvramVariableInfo.ACpuFreqValueMaximum)
		{
			LogCtrl.TraceMessage("ACpuFreqValue: " + value, "SetCpuAmdCoreFreq", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5.cs", 2968);
			NvramVariable.SetFwVars("ACpuFreqValue", Convert.ToUInt32(value));
		}
		else
		{
			LogCtrl.TraceMessage("Set the value failed, and error is out of range.", "SetCpuAmdCoreFreq", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5.cs", 2977);
		}
	}

	private void SetCpuAmdCoreVoltage(int value)
	{
		if (value >= NvramVariableInfo.ACpuVoltageValueMinimum && value <= NvramVariableInfo.ACpuVoltageValueMaximum)
		{
			LogCtrl.TraceMessage("ACpuVoltageValue: " + value, "SetCpuAmdCoreVoltage", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5.cs", 2984);
			NvramVariable.SetFwVars("ACpuVoltageValue", Convert.ToUInt32(value));
		}
		else
		{
			LogCtrl.TraceMessage("Set the value failed, and error is out of range.", "SetCpuAmdCoreVoltage", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5.cs", 2994);
		}
	}

	private void LoadNvramVariableInfo()
	{
		NVRAM_STRUCT fwVars = NvramVariable.GetFwVars();
		NvramVariableInfo.ICpuCoreVoltageOffsetRangeType = fwVars.ICpuCoreVoltageOffsetRangeType;
		NvramVariableInfo.CoreVoltageOffsetMaximum = fwVars.ICpuCoreVoltageOffsetMaximum;
		NvramVariableInfo.ACpuOverClockSupport = fwVars.ACpuOverClockSupport;
		if (NvramVariableInfo.ACpuOverClockSupport == 1)
		{
			NvramVariableInfo.ACpuFreqValueMaximum = fwVars.ACpuFreqValueMaximum;
			NvramVariableInfo.ACpuFreqValueMinimum = fwVars.ACpuFreqValueMinimum;
			NvramVariableInfo.ACpuVoltageValueMaximum = fwVars.ACpuVoltageValueMaximum;
			NvramVariableInfo.ACpuVoltageValueMinimum = fwVars.ACpuVoltageValueMinimum;
		}
		NvramVariableInfo.OverClockRecoveryFlag = fwVars.OverClockRecoveryFlag;
		NvramVariableInfo.MemoryOverClockSupport = fwVars.MemoryOverClockSupport;
		NvramVariableInfo.ApUseFlag = fwVars.ApUseFlag;
	}

	private void SetMemoryOverClockSwitch(int value)
	{
		LogCtrl.TraceMessage("MemoryOverClockSwitch: " + value, "SetMemoryOverClockSwitch", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5.cs", 3064);
		NvramVariable.SetFwVars("MemoryOverClockSwitch", Convert.ToByte(value));
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

	private async void SetFanTableThread(string _tableName)
	{
		if (_tableName == null)
		{
			return;
		}
		LogCtrl.TraceMessage(_tableName, "SetFanTableThread", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5.cs", 3098);
		if (FansemporeSlim2.CurrentCount == 0)
		{
			LastCommand2 = _tableName;
			return;
		}
		await FansemporeSlim2.WaitAsync();
		try
		{
			stopwatch2.Reset();
			stopwatch2.Start();
			new Thread((ThreadStart)delegate
			{
				FanTable.SetFanTable(_tableName);
			}).Start();
			stopwatch2.Stop();
			_ = stopwatch2.ElapsedMilliseconds;
		}
		catch
		{
		}
		finally
		{
			FansemporeSlim2.Release();
			if (LastCommand2 != "M1T1")
			{
				new Thread((ThreadStart)delegate
				{
					FanTable.SetFanTable(_tableName);
				}).Start();
				LastCommand2 = "M1T1";
			}
		}
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

	private void DetectBsodFromEventLog()
	{
		string query = "*[System/EventID=41]";
		DateTime dateTime = DateTime.Now;
		bool flag = false;
		EventLogReader eventLogReader = new EventLogReader(new EventLogQuery("System", PathType.LogName, query));
		for (EventRecord eventRecord = eventLogReader.ReadEvent(); eventRecord != null; eventRecord = eventLogReader.ReadEvent())
		{
			dateTime = eventRecord.TimeCreated.Value;
			flag = true;
		}
		if (flag && dateTime > m_Option.BsodTimestampRestored)
		{
			LogCtrl.TraceMessage("Detect the last BSOD TimeCreated > Timestamp, then restore OC settings.", "DetectBsodFromEventLog", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5.cs", 3172);
			m_Option.DefaultNotify = 1u;
			LoadDefault();
			FanTable.RestoreDefaultFanTableAll();
		}
	}

	private void DetectErrorFanTable()
	{
		LoadDefault();
		FanTable.RestoreDefaultFanTableAll();
	}

	private void DetectRecoveryFlagFromBiosVariable()
	{
		if (NvramVariableInfo.OverClockRecoveryFlag == 1)
		{
			LogCtrl.TraceMessage("Detect BiosVariable OverClockRecoveryFlag = 1, then restore OC settings.", "DetectRecoveryFlagFromBiosVariable", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5.cs", 3195);
			m_Option.DefaultNotify = 1u;
			LoadDefault();
			FanTable.RestoreDefaultFanTableAll();
			NvramVariableInfo.OverClockRecoveryFlag = 0;
			NvramVariable.SetFwVars("OverClockRecoveryFlag", 0);
		}
	}

	private void SetOperatingModeProfileIndex(string _modeProfileIndex)
	{
		switch (_modeProfileIndex)
		{
		case "M1P1":
			m_Option.GamingProfileIndex = 0u;
			WriteMainOptionToJson("GamingProfileIndex", m_Option.GamingProfileIndex);
			UserSet_Mode1();
			break;
		case "M1P2":
			m_Option.GamingProfileIndex = 1u;
			WriteMainOptionToJson("GamingProfileIndex", m_Option.GamingProfileIndex);
			UserSet_Mode1();
			break;
		case "M1P3":
			m_Option.GamingProfileIndex = 2u;
			WriteMainOptionToJson("GamingProfileIndex", m_Option.GamingProfileIndex);
			UserSet_Mode1();
			break;
		case "M1P4":
			m_Option.GamingProfileIndex = 3u;
			WriteMainOptionToJson("GamingProfileIndex", m_Option.GamingProfileIndex);
			UserSet_Mode1();
			break;
		case "M1P5":
			m_Option.GamingProfileIndex = 4u;
			WriteMainOptionToJson("GamingProfileIndex", m_Option.GamingProfileIndex);
			UserSet_Mode1();
			break;
		case "M2P1":
			m_Option.OfficeProfileIndex = 0u;
			WriteMainOptionToJson("OfficeProfileIndex", m_Option.OfficeProfileIndex);
			UserSet_Mode2();
			break;
		case "M2P2":
			m_Option.OfficeProfileIndex = 1u;
			WriteMainOptionToJson("OfficeProfileIndex", m_Option.OfficeProfileIndex);
			UserSet_Mode2();
			break;
		case "M2P3":
			m_Option.OfficeProfileIndex = 2u;
			WriteMainOptionToJson("OfficeProfileIndex", m_Option.OfficeProfileIndex);
			UserSet_Mode2();
			break;
		case "M2P4":
			m_Option.OfficeProfileIndex = 3u;
			WriteMainOptionToJson("OfficeProfileIndex", m_Option.OfficeProfileIndex);
			UserSet_Mode2();
			break;
		case "M2P5":
			m_Option.OfficeProfileIndex = 4u;
			WriteMainOptionToJson("OfficeProfileIndex", m_Option.OfficeProfileIndex);
			UserSet_Mode2();
			break;
		case "M3P1":
			m_Option.TurboProfileIndex = 0u;
			WriteMainOptionToJson("TurboProfileIndex", m_Option.TurboProfileIndex);
			UserSet_Mode3();
			break;
		case "M3P2":
			m_Option.TurboProfileIndex = 1u;
			WriteMainOptionToJson("TurboProfileIndex", m_Option.TurboProfileIndex);
			UserSet_Mode3();
			break;
		case "M3P3":
			m_Option.TurboProfileIndex = 2u;
			WriteMainOptionToJson("TurboProfileIndex", m_Option.TurboProfileIndex);
			UserSet_Mode3();
			break;
		case "M3P4":
			m_Option.TurboProfileIndex = 3u;
			WriteMainOptionToJson("TurboProfileIndex", m_Option.TurboProfileIndex);
			UserSet_Mode3();
			break;
		case "M3P5":
			m_Option.TurboProfileIndex = 4u;
			WriteMainOptionToJson("TurboProfileIndex", m_Option.TurboProfileIndex);
			UserSet_Mode3();
			break;
		}
		UpdateStatusToClient(1, 0, 0, updateOperationMode: false);
	}

	private async void SetOperatingModeProfileIndexThread(string _modeProfileIndex)
	{
		if (_modeProfileIndex == null)
		{
			return;
		}
		LogCtrl.TraceMessage(_modeProfileIndex, "SetOperatingModeProfileIndexThread", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5.cs", 3306);
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
			await Task.Delay(1500);
			stopwatch3.Stop();
			LogCtrl.Write("ModeProfileIndex : " + _modeProfileIndex + " SetOperatingModeProfileIndexThread time: " + stopwatch3.ElapsedMilliseconds);
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

	private string TransferToName(string mode, uint index)
	{
		string result = "M1P1";
		switch (mode)
		{
		case "OPERATING_GAMING_MODE":
			switch (index)
			{
			case 0u:
				result = "M1P1";
				break;
			case 1u:
				result = "M1P2";
				break;
			case 2u:
				result = "M1P3";
				break;
			case 3u:
				result = "M1P4";
				break;
			case 4u:
				result = "M1P5";
				break;
			}
			break;
		case "OPERATING_OFFICE_MODE":
			switch (index)
			{
			case 0u:
				result = "M2P1";
				break;
			case 1u:
				result = "M2P2";
				break;
			case 2u:
				result = "M2P3";
				break;
			case 3u:
				result = "M2P4";
				break;
			case 4u:
				result = "M2P5";
				break;
			}
			break;
		case "OPERATING_TURBO_MODE":
			switch (index)
			{
			case 0u:
				result = "M3P1";
				break;
			case 1u:
				result = "M3P2";
				break;
			case 2u:
				result = "M3P3";
				break;
			case 3u:
				result = "M3P4";
				break;
			case 4u:
				result = "M3P5";
				break;
			}
			break;
		}
		return result;
	}

	private async void SetModeSwitchChangeThread(int _mode)
	{
		if (_mode == -1)
		{
			return;
		}
		if (FansemporeSlim4.CurrentCount == 0)
		{
			LastCommand4 = _mode;
			return;
		}
		await FansemporeSlim4.WaitAsync();
		try
		{
			stopwatch4.Reset();
			stopwatch4.Start();
			SetModeSwitchChange(_mode);
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
			if (LastCommand4 != -1)
			{
				SetModeSwitchChange(_mode);
				LastCommand4 = -1;
			}
		}
	}

	private void SetModeSwitchChange(int mode)
	{
		switch (mode)
		{
		case 1:
			App.m_Osd.ShowOSDByName(TransToGlobalType(1u));
			LogCtrl.TraceMessage("Switch to Gaming", "SetModeSwitchChange", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5.cs", 3485);
			UserSet_Mode1();
			break;
		case 0:
			App.m_Osd.ShowOSDByName(TransToGlobalType(0u));
			LogCtrl.TraceMessage("Switch to Office", "SetModeSwitchChange", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5.cs", 3490);
			UserSet_Mode2();
			break;
		case 2:
			App.m_Osd.ShowOSDByName(TransToGlobalType(2u));
			LogCtrl.TraceMessage("Switch to Turbo", "SetModeSwitchChange", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\MyFanManager_RamFan1p5.cs", 3495);
			UserSet_Mode3();
			break;
		}
		UpdateStatusToClient(1);
		FanTable.GetFanTable(currentProfile.FAN.TableName);
	}

	private void RefreshCpuPLMinimumValue()
	{
		GN20_GPU_SKU sku = EcCtrl.GetSku();
		BIOS_PROJECT_ID biosProjctID = EcCtrl.GetBiosProjctID();
		if (sku == GN20_GPU_SKU.E5 && biosProjctID == BIOS_PROJECT_ID.IDR)
		{
			CpuPL1Minimum = 30;
			CpuPL2Minimum = 30;
			CpuPL4Minimum = 30;
		}
		else
		{
			CpuPL1Minimum = 10;
			CpuPL2Minimum = 10;
			CpuPL4Minimum = 10;
		}
	}
}
