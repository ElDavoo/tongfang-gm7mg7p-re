using System;
using System.Reflection;
using System.Text;
using System.Windows.Threading;
using Define;
using GCUService.MySystem;
using Microsoft.Win32;
using MyECIO;
using Utility;

namespace MyControlCenter;

public class MyFanManager
{
	private MyEcCtrl EcCtrl = MyEcCtrl.Instance;

	private MyFanView m_View = new MyFanView();

	private string m_RegistryPath = "\\OEM\\GamingCenter2\\MyFan3";

	private string className = "[" + MethodBase.GetCurrentMethod().DeclaringType.Name + "] ";

	private static int m_nProjectID;

	public uint g_FanMode;

	public uint g_FanOfficeMode = 2u;

	public uint g_PowerSettingMode = 2u;

	public uint g_BasicFanLevel = 1u;

	public uint g_FanLeveTem1 = 1u;

	public uint g_FanLeveTem2 = 2u;

	public uint g_FanLeveTem3 = 3u;

	public uint g_FanLeveTem4 = 4u;

	public uint g_FanLeveTem5 = 5u;

	public uint g_FanMinSpeed;

	public uint g_FanMinTemp = 55u;

	public uint g_FanExtraSpeed = 5u;

	public uint g_AdvancedFanLevel = 2u;

	public uint g_FanTurboModeLevel = 2u;

	public uint g_FanTurboModeCPUBOOST;

	private uint GamingMode_PL1_Default;

	private uint GamingMode_PL2_Default;

	private uint GamingMode_PL4_Default;

	private uint GamingMode_Tau_Default = 56u;

	private uint OfficeMode_PL1_Default = 5u;

	private uint OfficeMode_PL2_Default = 5u;

	private uint OfficeMode_PL4_Default = 5u;

	private uint OfficeMode_Tau_Default = 56u;

	private FanOfficeAdvLvPwms AdvL1Pwms = new FanOfficeAdvLvPwms();

	private FanOfficeAdvLvPwms AdvL2Pwms = new FanOfficeAdvLvPwms();

	private FanOfficeAdvLvPwms AdvL3Pwms = new FanOfficeAdvLvPwms();

	private FanOfficeAdvLvPwms AdvL4Pwms = new FanOfficeAdvLvPwms();

	public int g_FanEnhanced;

	public int g_FanModeAutoSave;

	private int[] DefaultPWM = new int[5];

	private int g_PowerMode;

	public int g_DefaultMode;

	public int g_SupportMyFan3 = 1;

	public int g_TurboModeSupport;

	public int g_TurboLevelSupport;

	public int g_TurboCPUBoostSupport;

	public uint g_QkeyDefine;

	public int g_MyFan3p5Flag;

	public virtual int GetTurboModeSupportFlag()
	{
		return g_TurboModeSupport;
	}

	public virtual void EnableByService(Dispatcher dispatcher = null)
	{
		m_nProjectID = GetProjectIdFromEC();
		g_TurboModeSupport = EcCtrl.GetTurboModeSupport();
		CheckMyFan3p5Flag();
		g_DefaultMode = GetDefaultMode();
		LoadRegistry();
		g_PowerMode = PowerModeEvent.g_ACLineStatus;
		Init();
	}

	public virtual void Disable()
	{
		if (App.OsdOnly == 1)
		{
			LogCtrl.Write("OSD only, skip reset fan mode");
		}
		else
		{
			if (m_nProjectID == 11 && m_nProjectID == 12 && m_nProjectID == 13)
			{
				return;
			}
			if (g_SupportMyFan3 == 1)
			{
				g_DefaultMode = GetDefaultMode();
				if (g_DefaultMode == 0)
				{
					EcCtrl.Write(GetType().Name, 1873, 160);
				}
				else if (g_DefaultMode == 1)
				{
					EcCtrl.Write(GetType().Name, 1873, 0);
				}
			}
			else
			{
				EcCtrl.Write(GetType().Name, 1873, 0);
			}
		}
	}

	public virtual async void Receive(byte[] data)
	{
		dynamic val = await Json.ToObjectAsync<object>(Encoding.UTF8.GetString(data));
		string text = val["Mode"];
		_ = string.Empty;
		LogCtrl.Write("---------------" + LogCtrl.GetTime() + "---------------");
		LogCtrl.Write("[Receive] msg = " + text);
		switch (text)
		{
		case "FAN_TURBO_MODE_CPUBOOST_ON":
			UpdatedTurboCPUBoost(Enable: true);
			break;
		case "FAN_TURBO_MODE_CPUBOOST_OFF":
			UpdatedTurboCPUBoost(Enable: false);
			break;
		case "GETSTATUS":
			UpdateStatusToClient(1);
			break;
		case "DEFAULT":
			UserSet_Default();
			UpdateStatusToClient(1);
			break;
		case "FAN_GAMING_MODE":
			UserSet_Mode1();
			UpdateStatusToClient(1);
			break;
		case "FAN_GAMING_MODE_BOOST_ON":
		case "FAN_TURBO_MODE_BOOST_ON":
			UserSet_FanBoost(1);
			UpdateStatusToClient(1);
			break;
		case "FAN_GAMING_MODE_BOOST_OFF":
		case "FAN_TURBO_MODE_BOOST_OFF":
			UserSet_FanBoost(0);
			UpdateStatusToClient(1);
			break;
		case "FAN_TURBO_MODE":
			UserSet_Mode3();
			UpdateStatusToClient(1);
			break;
		case "FAN_OFFICE_MODE":
			UserSet_Mode2();
			UpdateStatusToClient(1);
			break;
		case "FAN_OFFICE_MODE_BASIC":
			UserSet_OfficeMode_Basic();
			UpdateStatusToClient(1);
			break;
		case "FAN_OFFICE_MODE_BASIC_L0":
		case "FAN_OFFICE_MODE_BASIC_L1":
		case "FAN_OFFICE_MODE_BASIC_L2":
		case "FAN_OFFICE_MODE_BASIC_L3":
		case "FAN_OFFICE_MODE_BASIC_L4":
		case "FAN_OFFICE_MODE_BASIC_L5":
			UserSet_OfficeMode_Basic_Level(text);
			UpdateStatusToClient(1);
			break;
		case "FAN_OFFICE_MODE_ADVANCED":
			UserSet_OfficeMode_Advanced();
			UpdateStatusToClient(1);
			break;
		case "FAN_OFFICE_MODE_ADVANCED_T1_PWM":
		case "FAN_OFFICE_MODE_ADVANCED_T2_PWM":
		case "FAN_OFFICE_MODE_ADVANCED_T3_PWM":
		case "FAN_OFFICE_MODE_ADVANCED_T4_PWM":
		case "FAN_OFFICE_MODE_ADVANCED_T5_PWM":
		{
			string level = val["Level"];
			UserSet_OfficeMode_Advanced_PWM(text, level);
			UpdateStatusToClient(1);
			break;
		}
		case "FAN_POWER_SETTING_MODE_STD":
		case "FAN_POWER_SETTING_MODE_ECO":
			UserSet_PowerSettingMode(text);
			UpdateStatusToClient(1);
			break;
		case "FAN_TURBO_MODE_LV1":
		case "FAN_TURBO_MODE_LV2":
		case "FAN_TURBO_MODE_LV3":
		case "FAN_TURBO_MODE_LV4":
			UserSet_TurboMode_Lev(text);
			UpdateStatusToClient(1);
			break;
		case "FAN_OFFICE_MODE_ADV_LV1":
		case "FAN_OFFICE_MODE_ADV_LV2":
		case "FAN_OFFICE_MODE_ADV_LV3":
		case "FAN_OFFICE_MODE_ADV_LV4":
			UserSet_OfficeMode_AdvancedFanLevel(text);
			UpdateStatusToClient(1);
			break;
		case "FAN_OFFICE_MODE_ADV_LV1_PWMS":
		case "FAN_OFFICE_MODE_ADV_LV2_PWMS":
		case "FAN_OFFICE_MODE_ADV_LV3_PWMS":
		case "FAN_OFFICE_MODE_ADV_LV4_PWMS":
			UserSet_OfficeMode_AdvLvPwms(val);
			UpdateStatusToClient(1);
			break;
		case "FAN_OFFICE_MODE_ADV_LV4_DEFAULT":
			UserSet_OfficeMode_AdvLvDefault();
			UpdateStatusToClient(1);
			break;
		}
	}

	private void UpdatedTurboCPUBoost(bool Enable)
	{
		if (Enable)
		{
			g_FanTurboModeCPUBOOST = 1u;
			if (g_PowerMode == 0)
			{
				LogCtrl.Write(className + "[SetFanMode] DC Turbo mode, Set PL124Tau to 0,0,0," + GamingMode_Tau_Default);
				SetPL124Tau(0u, 0u, 0u, GamingMode_Tau_Default);
			}
			else
			{
				LogCtrl.Write(className + "[SetFanMode] AC Turbo mode, Set PL124Tau to 73,73,90," + GamingMode_Tau_Default);
				SetPL124Tau(73u, 73u, 90u, GamingMode_Tau_Default);
			}
		}
		else
		{
			g_FanTurboModeCPUBOOST = 0u;
			LogCtrl.Write(className + "[SetFanMode] DC Turbo mode, Set PL124Tau to 0,0,0," + GamingMode_Tau_Default);
			SetPL124Tau(0u, 0u, 0u, GamingMode_Tau_Default);
		}
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_RegistryPath, "TurboModeCPUBoost", g_FanTurboModeCPUBOOST, RegistryValueKind.DWord);
	}

	public virtual void UpdateStatusToClient(int autosave, int cpuusage = 0, int cputemp = 0, bool updateOperationMode = true)
	{
		if (autosave != 0)
		{
			var data = new
			{
				Mode = g_FanMode.ToString(),
				OfficeMode = g_FanOfficeMode.ToString(),
				BasicFanLevel = g_BasicFanLevel.ToString(),
				FanLeveTem1 = g_FanLeveTem1.ToString(),
				FanLeveTem2 = g_FanLeveTem2.ToString(),
				FanLeveTem3 = g_FanLeveTem3.ToString(),
				FanLeveTem4 = g_FanLeveTem4.ToString(),
				FanLeveTem5 = g_FanLeveTem5.ToString(),
				FanEnhanced = g_FanEnhanced.ToString(),
				FanModeAutoSave = g_FanModeAutoSave.ToString(),
				PowerMode = g_PowerMode.ToString(),
				PowerSettingMode = g_PowerSettingMode.ToString(),
				FanTurboModeLevel = g_FanTurboModeLevel.ToString(),
				FanTurboCPUBoostSupport = g_TurboCPUBoostSupport.ToString(),
				FanTurboCPUBoost = g_FanTurboModeCPUBOOST.ToString(),
				AdvanceFanLevel = g_AdvancedFanLevel.ToString(),
				AdvL1_T1_PWM = AdvL1Pwms.T1_PWM.ToString(),
				AdvL1_T2_PWM = AdvL1Pwms.T2_PWM.ToString(),
				AdvL1_T3_PWM = AdvL1Pwms.T3_PWM.ToString(),
				AdvL1_T4_PWM = AdvL1Pwms.T4_PWM.ToString(),
				AdvL1_T5_PWM = AdvL1Pwms.T5_PWM.ToString(),
				AdvL2_T1_PWM = AdvL2Pwms.T1_PWM.ToString(),
				AdvL2_T2_PWM = AdvL2Pwms.T2_PWM.ToString(),
				AdvL2_T3_PWM = AdvL2Pwms.T3_PWM.ToString(),
				AdvL2_T4_PWM = AdvL2Pwms.T4_PWM.ToString(),
				AdvL2_T5_PWM = AdvL2Pwms.T5_PWM.ToString(),
				AdvL3_T1_PWM = AdvL3Pwms.T1_PWM.ToString(),
				AdvL3_T2_PWM = AdvL3Pwms.T2_PWM.ToString(),
				AdvL3_T3_PWM = AdvL3Pwms.T3_PWM.ToString(),
				AdvL3_T4_PWM = AdvL3Pwms.T4_PWM.ToString(),
				AdvL3_T5_PWM = AdvL3Pwms.T5_PWM.ToString(),
				AdvL4_T1_PWM = AdvL4Pwms.T1_PWM.ToString(),
				AdvL4_T2_PWM = AdvL4Pwms.T2_PWM.ToString(),
				AdvL4_T3_PWM = AdvL4Pwms.T3_PWM.ToString(),
				AdvL4_T4_PWM = AdvL4Pwms.T4_PWM.ToString(),
				AdvL4_T5_PWM = AdvL4Pwms.T5_PWM.ToString(),
				Default_Max_PWM = (DefaultPWM[4] / 2).ToString(),
				Default_Min_PWM = (DefaultPWM[0] / 2).ToString(),
				FanCPUUsage = cpuusage,
				FanCPUTemp = cputemp
			};
			m_View.SendStatusToClient(data);
		}
	}

	public virtual void UpdateStatusToTray()
	{
	}

	public virtual void Resume()
	{
		LoadRegistry();
		Init();
	}

	public virtual void OnModernStandby()
	{
	}

	public virtual void PowerStatusChange(int mode)
	{
		g_PowerMode = mode;
		if (g_TurboModeSupport == 1)
		{
			LogCtrl.Write(className + "[PowerModeChanged] show turbo mode");
		}
		else
		{
			LogCtrl.Write(className + "[PowerModeChanged] hide turbo mode");
			if (g_FanMode == 2)
			{
				LogCtrl.Write(className + "[PowerModeChanged] Turbo mode fallback to DefaultMode=" + g_DefaultMode + " " + FanModeString((uint)g_DefaultMode));
				g_FanMode = (uint)g_DefaultMode;
			}
		}
		switch (mode)
		{
		case 0:
			LogCtrl.Write(className + "[PowerModeChanged] DC Mode");
			break;
		case 1:
			LogCtrl.Write(className + "[PowerModeChanged] AC Mode");
			_ = g_FanMode;
			_ = 1;
			break;
		}
		if (g_FanMode == 0)
		{
			LogCtrl.Write(className + "[PowerModeChanged] Gaming mode");
			SetFanMode(g_FanMode, 0u);
		}
		else if (g_FanMode == 1)
		{
			LogCtrl.Write(className + "[PowerModeChanged] Office mode");
			SetFanMode(g_FanMode, g_FanOfficeMode);
		}
		else if (g_FanMode == 2)
		{
			LogCtrl.Write(className + "[PowerModeChanged] Turbo mode");
			SetFanMode(g_FanMode, g_FanTurboModeLevel);
		}
	}

	public virtual void Uninstall()
	{
		SetApExist(exist: false);
	}

	public virtual void Restore()
	{
		LoadFanDefault();
		Init();
	}

	public virtual void ModeSwitchChanged()
	{
		string text = "[QKey_FanModeSwitch] ";
		if (g_TurboModeSupport == 0)
		{
			LogCtrl.Write(text + " turbo mode support OFF");
			if (g_FanMode == 0)
			{
				UserSet_Mode2();
			}
			else if (g_FanMode == 1)
			{
				UserSet_Mode1();
			}
		}
		else
		{
			bool clockwise = true;
			int projectIdFromEC = EcCtrl.GetProjectIdFromEC();
			if (RegistryCtrl.GetCustomizeTarget() == 9)
			{
				clockwise = false;
			}
			projectIdFromEC.IsProjectId_Commercial();
			uint num = UtilityExtensions.ModeSwitchClockWise(g_FanMode, clockwise);
			LogCtrl.Write(text + " turbo mode support ON");
			switch (num)
			{
			case 1u:
				UserSet_Mode2();
				break;
			case 2u:
				UserSet_Mode3();
				break;
			case 0u:
				UserSet_Mode1();
				break;
			}
		}
		App.m_Osd.ShowOSDByName(g_FanMode);
		UpdateStatusToClient(1);
	}

	public virtual void FanBoostUpdate()
	{
		if (g_SupportMyFan3 == 1)
		{
			if (g_QkeyDefine == 1)
			{
				App.m_Osd.SetOsdWay(167);
			}
			if (RegistryCtrl.GetCustomizeTarget() == 3)
			{
				LogCtrl.Write($"Customer Machenike, always show OSD");
				App.m_Osd.ShowOSD(167);
			}
		}
	}

	public virtual void FanBoostOffFromEC()
	{
	}

	public virtual void SafetyProtectionUpdate()
	{
	}

	public virtual void WhisperUpdate()
	{
	}

	private void UserSet_AutoSave()
	{
		if (g_FanModeAutoSave == 0)
		{
			g_FanModeAutoSave = 1;
			SetFanModeRegistry(g_FanMode, g_FanModeAutoSave);
		}
		else
		{
			switch (GetDefaultMode())
			{
			case 0:
				SetFanModeRegistry(1u, g_FanModeAutoSave);
				break;
			case 1:
				SetFanModeRegistry(0u, g_FanModeAutoSave);
				break;
			}
			g_FanModeAutoSave = 0;
		}
		SetFanAutoSaveRegistry(g_FanModeAutoSave);
	}

	private void UserSet_Default()
	{
		Restore();
	}

	public virtual void UserSet_Mode1()
	{
		g_FanMode = 0u;
		SetFanMode(g_FanMode, 0u);
		SetFanModeRegistry(g_FanMode, g_FanModeAutoSave);
		if (g_SupportMyFan3 == 1 && g_QkeyDefine == 0)
		{
			App.m_TrayCtrl?.ChangeIcon(g_FanMode, bIcon: true);
		}
		else
		{
			App.m_TrayCtrl?.ChangeIcon(g_FanMode, bIcon: false);
		}
	}

	private void UserSet_FanBoost(int status)
	{
		g_FanEnhanced = status;
		SetFanMode(g_FanMode, 0u);
		SetFanEnhancedRegistry(g_FanEnhanced, g_FanModeAutoSave);
	}

	public virtual void UserSet_Mode3()
	{
		g_FanMode = 2u;
		SetFanMode(g_FanMode, g_FanTurboModeLevel);
		SetFanModeRegistry(g_FanMode, g_FanModeAutoSave);
		if (g_SupportMyFan3 == 1 && g_QkeyDefine == 0)
		{
			App.m_TrayCtrl?.ChangeIcon(g_FanMode, bIcon: true);
		}
		else
		{
			App.m_TrayCtrl?.ChangeIcon(g_FanMode, bIcon: false);
		}
	}

	public virtual void UserSet_Mode2()
	{
		g_FanMode = 1u;
		SetFanMode(g_FanMode, g_FanOfficeMode);
		SetFanModeRegistry(g_FanMode, g_FanModeAutoSave);
		if (g_SupportMyFan3 == 1 && g_QkeyDefine == 0)
		{
			App.m_TrayCtrl?.ChangeIcon(g_FanMode, bIcon: true);
		}
		else
		{
			App.m_TrayCtrl?.ChangeIcon(g_FanMode, bIcon: false);
		}
	}

	public virtual void SetPairedProfileIndex(uint index)
	{
	}

	private void UserSet_OfficeMode_Basic()
	{
		g_FanMode = 1u;
		g_FanOfficeMode = 1u;
		SetFanMode(g_FanMode, g_FanOfficeMode);
		SetFanOfficeModeRegistry(g_FanOfficeMode, g_FanModeAutoSave);
	}

	private void UserSet_OfficeMode_Basic_Level(string msg)
	{
		g_FanMode = 1u;
		g_FanOfficeMode = 1u;
		switch (msg)
		{
		case "FAN_OFFICE_MODE_BASIC_L0":
			g_BasicFanLevel = 0u;
			break;
		case "FAN_OFFICE_MODE_BASIC_L1":
			g_BasicFanLevel = 1u;
			break;
		case "FAN_OFFICE_MODE_BASIC_L2":
			g_BasicFanLevel = 2u;
			break;
		case "FAN_OFFICE_MODE_BASIC_L3":
			g_BasicFanLevel = 3u;
			break;
		case "FAN_OFFICE_MODE_BASIC_L4":
			g_BasicFanLevel = 4u;
			break;
		case "FAN_OFFICE_MODE_BASIC_L5":
			g_BasicFanLevel = 5u;
			break;
		}
		SetFanMode(g_FanMode, g_FanOfficeMode);
		SetOfficeModeBasicLevelRegistry(g_BasicFanLevel, g_FanModeAutoSave);
	}

	private void UserSet_OfficeMode_Advanced()
	{
		g_FanMode = 1u;
		g_FanOfficeMode = 2u;
		SetFanMode(g_FanMode, g_FanOfficeMode);
		SetFanOfficeModeRegistry(g_FanOfficeMode, g_FanModeAutoSave);
	}

	private void UserSet_OfficeMode_Advanced_PWM(string msg, string level)
	{
		switch (msg)
		{
		case "FAN_OFFICE_MODE_ADVANCED_T1_PWM":
			g_FanLeveTem1 = (uint)int.Parse(level);
			SetFan_L1_PWM(g_FanLeveTem1);
			SetAdvancedTempLevelRegistry("LevelTemp1", g_FanLeveTem1);
			break;
		case "FAN_OFFICE_MODE_ADVANCED_T2_PWM":
			g_FanLeveTem2 = (uint)int.Parse(level);
			SetFan_L2_PWM(g_FanLeveTem2);
			SetAdvancedTempLevelRegistry("LevelTemp2", g_FanLeveTem2);
			break;
		case "FAN_OFFICE_MODE_ADVANCED_T3_PWM":
			g_FanLeveTem3 = (uint)int.Parse(level);
			SetFan_L3_PWM(g_FanLeveTem3);
			SetAdvancedTempLevelRegistry("LevelTemp3", g_FanLeveTem3);
			break;
		case "FAN_OFFICE_MODE_ADVANCED_T4_PWM":
			g_FanLeveTem4 = (uint)int.Parse(level);
			SetFan_L4_PWM(g_FanLeveTem4);
			SetAdvancedTempLevelRegistry("LevelTemp4", g_FanLeveTem4);
			break;
		case "FAN_OFFICE_MODE_ADVANCED_T5_PWM":
			g_FanLeveTem5 = (uint)int.Parse(level);
			SetFan_L5_PWM(g_FanLeveTem5);
			SetAdvancedTempLevelRegistry("LevelTemp5", g_FanLeveTem5);
			break;
		}
	}

	private void UserSet_OfficeMode_AdvancedFanLevel(string msg)
	{
		switch (msg)
		{
		case "FAN_OFFICE_MODE_ADV_LV1":
			g_AdvancedFanLevel = 1u;
			break;
		case "FAN_OFFICE_MODE_ADV_LV2":
			g_AdvancedFanLevel = 2u;
			break;
		case "FAN_OFFICE_MODE_ADV_LV3":
			g_AdvancedFanLevel = 3u;
			break;
		case "FAN_OFFICE_MODE_ADV_LV4":
			g_AdvancedFanLevel = 4u;
			break;
		}
		SetFanMode(g_FanMode, g_FanOfficeMode);
		SetRegistry("OfficeAdvancedLevel", g_AdvancedFanLevel, g_FanModeAutoSave);
	}

	private void UserSet_OfficeMode_AdvLvPwms(dynamic data)
	{
		string text = data.Mode;
		string s = data.T1;
		string s2 = data.T2;
		string s3 = data.T3;
		string s4 = data.T4;
		string s5 = data.T5;
		uint t1_PWM = (uint)int.Parse(s);
		uint t2_PWM = (uint)int.Parse(s2);
		uint t3_PWM = (uint)int.Parse(s3);
		uint t4_PWM = (uint)int.Parse(s4);
		uint t5_PWM = (uint)int.Parse(s5);
		switch (text)
		{
		case "FAN_OFFICE_MODE_ADV_LV1_PWMS":
			AdvL1Pwms = UpdateAdvPwms(t1_PWM, t2_PWM, t3_PWM, t4_PWM, t5_PWM);
			SetOfficeAdvPwmRegistry(text, AdvL1Pwms, g_FanModeAutoSave);
			break;
		case "FAN_OFFICE_MODE_ADV_LV2_PWMS":
			AdvL2Pwms = UpdateAdvPwms(t1_PWM, t2_PWM, t3_PWM, t4_PWM, t5_PWM);
			SetOfficeAdvPwmRegistry(text, AdvL2Pwms, g_FanModeAutoSave);
			break;
		case "FAN_OFFICE_MODE_ADV_LV3_PWMS":
			AdvL3Pwms = UpdateAdvPwms(t1_PWM, t2_PWM, t3_PWM, t4_PWM, t5_PWM);
			SetOfficeAdvPwmRegistry(text, AdvL3Pwms, g_FanModeAutoSave);
			break;
		case "FAN_OFFICE_MODE_ADV_LV4_PWMS":
			AdvL4Pwms = UpdateAdvPwms(t1_PWM, t2_PWM, t3_PWM, t4_PWM, t5_PWM);
			SetOfficeAdvPwmRegistry(text, AdvL4Pwms, g_FanModeAutoSave);
			break;
		}
		SetFanMode(g_FanMode, g_FanOfficeMode);
	}

	private void UserSet_OfficeMode_AdvLvDefault()
	{
		LoadOfficeAdvLvPwmsDefault();
		SetFanMode(g_FanMode, g_FanOfficeMode);
	}

	private void UserSet_TurboMode_Lev(string msg)
	{
		switch (msg)
		{
		case "FAN_TURBO_MODE_LV1":
			g_FanTurboModeLevel = 1u;
			break;
		case "FAN_TURBO_MODE_LV2":
			g_FanTurboModeLevel = 2u;
			break;
		case "FAN_TURBO_MODE_LV3":
			g_FanTurboModeLevel = 3u;
			break;
		case "FAN_TURBO_MODE_LV4":
			g_FanTurboModeLevel = 4u;
			break;
		}
		SetTurboMode(g_FanTurboModeLevel);
		SetFanTurboModeLevelRegistry(g_FanTurboModeLevel, g_FanModeAutoSave);
	}

	private void UserSet_PowerSettingMode(string msg)
	{
		if (!(msg == "FAN_POWER_SETTING_MODE_STD"))
		{
			if (msg == "FAN_POWER_SETTING_MODE_ECO")
			{
				g_PowerSettingMode = 1u;
			}
		}
		else
		{
			g_PowerSettingMode = 2u;
		}
		g_FanMode = 1u;
		SetFanMode(g_FanMode, g_FanOfficeMode);
		SetPowerSettingModeRegistry(g_PowerSettingMode, g_FanModeAutoSave);
	}

	private void LoadRegistry()
	{
		int num = 0;
		int num2 = 0;
		int num3 = 0;
		int num4 = 0;
		int num5 = 0;
		int num6 = 0;
		int num7 = 0;
		int num8 = 0;
		int num9 = 0;
		int num10 = 0;
		int num11 = 0;
		int num12 = 0;
		int num13 = 0;
		int num14 = 0;
		int num15 = 0;
		int num16 = 0;
		int num17 = 0;
		int num18 = 0;
		int num19 = 0;
		int num20 = 0;
		int num21 = 0;
		int num22 = 0;
		int num23 = 0;
		int num24 = 0;
		int num25 = 0;
		int num26 = 0;
		int num27 = 0;
		int num28 = 0;
		int num29 = 0;
		int num30 = 0;
		int num31 = 0;
		int num32 = 0;
		int num33 = 0;
		int num34 = 0;
		try
		{
			DefaultPWM = GetFanTablePWMDefault();
			DefaultPWM = CheckFanTablePWMDefault(DefaultPWM);
			GetGamingPLDefaultValue(ref GamingMode_PL1_Default, ref GamingMode_PL2_Default, ref GamingMode_PL4_Default);
			GetOfficePLDefaultValue(ref OfficeMode_PL1_Default, ref OfficeMode_PL2_Default, ref OfficeMode_PL4_Default);
			GamingMode_Tau_Default = GetTauDefaultValue();
			OfficeMode_Tau_Default = GamingMode_Tau_Default;
			num = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_RegistryPath, "FanMode", 1u);
			num2 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_RegistryPath, "OfficeMode", 2u);
			num3 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_RegistryPath, "PowerSettingMode", 2u);
			num4 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_RegistryPath, "FanEnhanced", 0);
			num5 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_RegistryPath, "TurboModeLevel", 2u);
			num7 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_RegistryPath, "FanModeAutoSave", 1);
			num8 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_RegistryPath, "TurboModeCPUBoost", 0);
			num9 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_RegistryPath + "\\GamingModePL", "Default_PL1", 0);
			num10 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_RegistryPath + "\\GamingModePL", "Default_PL2", 0);
			num11 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_RegistryPath + "\\GamingModePL", "Default_PL4", 0);
			num12 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_RegistryPath + "\\OfficeModePL", "Default_PL1", 0);
			num13 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_RegistryPath + "\\OfficeModePL", "Default_PL2", 0);
			num14 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_RegistryPath + "\\OfficeModePL", "Default_PL4", 0);
			num15 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_RegistryPath + "\\OfficeModeAdvL1", "T1_PWM", 0);
			num16 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_RegistryPath + "\\OfficeModeAdvL1", "T2_PWM", 0);
			num17 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_RegistryPath + "\\OfficeModeAdvL1", "T3_PWM", 0);
			num18 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_RegistryPath + "\\OfficeModeAdvL1", "T4_PWM", 0);
			num19 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_RegistryPath + "\\OfficeModeAdvL1", "T5_PWM", 0);
			num20 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_RegistryPath + "\\OfficeModeAdvL2", "T1_PWM", 0);
			num21 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_RegistryPath + "\\OfficeModeAdvL2", "T2_PWM", 0);
			num22 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_RegistryPath + "\\OfficeModeAdvL2", "T3_PWM", 0);
			num23 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_RegistryPath + "\\OfficeModeAdvL2", "T4_PWM", 0);
			num24 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_RegistryPath + "\\OfficeModeAdvL2", "T5_PWM", 0);
			num25 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_RegistryPath + "\\OfficeModeAdvL3", "T1_PWM", 0);
			num26 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_RegistryPath + "\\OfficeModeAdvL3", "T2_PWM", 0);
			num27 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_RegistryPath + "\\OfficeModeAdvL3", "T3_PWM", 0);
			num28 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_RegistryPath + "\\OfficeModeAdvL3", "T4_PWM", 0);
			num29 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_RegistryPath + "\\OfficeModeAdvL3", "T5_PWM", 0);
			num30 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_RegistryPath + "\\OfficeModeAdvL4", "T1_PWM", 0);
			num31 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_RegistryPath + "\\OfficeModeAdvL4", "T2_PWM", 0);
			num32 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_RegistryPath + "\\OfficeModeAdvL4", "T3_PWM", 0);
			num33 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_RegistryPath + "\\OfficeModeAdvL4", "T4_PWM", 0);
			num34 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_RegistryPath + "\\OfficeModeAdvL4", "T5_PWM", 0);
			num6 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_RegistryPath, "OfficeAdvancedLevel", 2u);
			g_AdvancedFanLevel = (uint)num6;
			g_AdvancedFanLevel = g_AdvancedFanLevel.LimitToRange(1u, 4u);
			if (GamingMode_PL1_Default != num9 || GamingMode_PL2_Default != num10 || GamingMode_PL4_Default != num11 || OfficeMode_PL1_Default != num12 || OfficeMode_PL2_Default != num13 || OfficeMode_PL4_Default != num14)
			{
				LogCtrl.Write("[LoadRegistry] MyFan3 LoadRegistry: Power limit default values mismatch, restore default");
				throw new Exception();
			}
			g_FanMode = (uint)num;
			g_FanOfficeMode = (uint)num2;
			g_PowerSettingMode = (uint)num3;
			g_FanEnhanced = num4;
			g_FanTurboModeLevel = (uint)num5;
			g_FanModeAutoSave = num7;
			LogCtrl.Write(className + "[LoadRegistry]        g_FanMode=" + g_FanMode + ", " + FanModeString(g_FanMode));
			uint num35 = 0u;
			uint num36 = 1u;
			if (g_TurboModeSupport == 1)
			{
				num36 = 2u;
			}
			if (g_FanMode < num35 || g_FanMode > num36)
			{
				g_FanMode = (uint)g_DefaultMode;
				LogCtrl.Write(className + "[LoadRegistry] limited g_FanMode=" + g_FanMode + ", " + FanModeString(g_FanMode));
			}
			g_FanOfficeMode = g_FanOfficeMode.LimitToRange(1u, 2u);
			g_PowerSettingMode = g_PowerSettingMode.LimitToRange(1u, 2u);
			g_FanTurboModeLevel = g_FanTurboModeLevel.LimitToRange(1u, 4u);
			g_FanModeAutoSave = g_FanModeAutoSave.LimitToRange(0, 1);
			g_FanTurboModeCPUBOOST = Convert.ToUInt32(num8);
			AdvL1Pwms = UpdateAdvPwms((uint)num15, (uint)num16, (uint)num17, (uint)num18, (uint)num19);
			AdvL2Pwms = UpdateAdvPwms((uint)num20, (uint)num21, (uint)num22, (uint)num23, (uint)num24);
			AdvL3Pwms = UpdateAdvPwms((uint)num25, (uint)num26, (uint)num27, (uint)num28, (uint)num29);
			AdvL4Pwms = UpdateAdvPwms((uint)num30, (uint)num31, (uint)num32, (uint)num33, (uint)num34);
		}
		catch
		{
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_RegistryPath + "\\GamingModePL", "Default_PL1", GamingMode_PL1_Default, RegistryValueKind.DWord);
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_RegistryPath + "\\GamingModePL", "Default_PL2", GamingMode_PL2_Default, RegistryValueKind.DWord);
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_RegistryPath + "\\GamingModePL", "Default_PL4", GamingMode_PL4_Default, RegistryValueKind.DWord);
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_RegistryPath + "\\OfficeModePL", "Default_PL1", OfficeMode_PL1_Default, RegistryValueKind.DWord);
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_RegistryPath + "\\OfficeModePL", "Default_PL2", OfficeMode_PL2_Default, RegistryValueKind.DWord);
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_RegistryPath + "\\OfficeModePL", "Default_PL4", OfficeMode_PL4_Default, RegistryValueKind.DWord);
			LoadFanDefault();
			LoadOfficeAdvLvPwmsDefault();
		}
	}

	private void LoadFanDefault()
	{
		switch (GetDefaultMode())
		{
		case 0:
			g_FanMode = 1u;
			break;
		case 1:
			g_FanMode = 0u;
			break;
		}
		if (RegistryCtrl.GetCustomizeTarget() == 9)
		{
			if (m_nProjectID < 11)
			{
				g_FanOfficeMode = 1u;
			}
			else
			{
				g_FanOfficeMode = 2u;
			}
		}
		else
		{
			g_FanOfficeMode = 2u;
		}
		g_PowerSettingMode = 2u;
		g_FanTurboModeLevel = 2u;
		g_FanEnhanced = 0;
		g_FanModeAutoSave = 1;
		g_FanTurboModeCPUBOOST = 0u;
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_RegistryPath, "FanMode", g_FanMode, RegistryValueKind.DWord);
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_RegistryPath, "OfficeMode", g_FanOfficeMode, RegistryValueKind.DWord);
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_RegistryPath, "PowerSettingMode", g_PowerSettingMode, RegistryValueKind.DWord);
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_RegistryPath, "TurboModeLevel", g_FanTurboModeLevel, RegistryValueKind.DWord);
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_RegistryPath, "FanEnhanced", g_FanEnhanced, RegistryValueKind.DWord);
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_RegistryPath, "FanModeAutoSave", g_FanModeAutoSave, RegistryValueKind.DWord);
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_RegistryPath, "TurboModeCPUBoost", g_FanTurboModeCPUBOOST, RegistryValueKind.DWord);
		g_AdvancedFanLevel = 2u;
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_RegistryPath, "OfficeAdvancedLevel", g_AdvancedFanLevel, RegistryValueKind.DWord);
	}

	private void LoadOfficeAdvLvPwmsDefault()
	{
		int t1_PWM = DefaultPWM[0] / 2;
		int num = DefaultPWM[1] / 2;
		int num2 = DefaultPWM[2] / 2;
		int num3 = DefaultPWM[3] / 2;
		int t5_PWM = DefaultPWM[4] / 2;
		AdvL1Pwms.T1_PWM = (uint)t1_PWM;
		AdvL1Pwms.T2_PWM = (uint)Math.Round((double)num * 0.9, 0, MidpointRounding.AwayFromZero);
		AdvL1Pwms.T3_PWM = (uint)Math.Round((double)num2 * 0.9, 0, MidpointRounding.AwayFromZero);
		AdvL1Pwms.T4_PWM = (uint)Math.Round((double)num3 * 0.9, 0, MidpointRounding.AwayFromZero);
		AdvL1Pwms.T5_PWM = (uint)t5_PWM;
		AdvL2Pwms.T1_PWM = (uint)t1_PWM;
		AdvL2Pwms.T2_PWM = (uint)num;
		AdvL2Pwms.T3_PWM = (uint)num2;
		AdvL2Pwms.T4_PWM = (uint)num3;
		AdvL2Pwms.T5_PWM = (uint)t5_PWM;
		AdvL3Pwms.T1_PWM = (uint)t1_PWM;
		AdvL3Pwms.T2_PWM = (uint)Math.Round((double)num * 1.1, 0, MidpointRounding.AwayFromZero);
		AdvL3Pwms.T3_PWM = (uint)Math.Round((double)num2 * 1.1, 0, MidpointRounding.AwayFromZero);
		AdvL3Pwms.T4_PWM = (uint)Math.Round((double)num3 * 1.1, 0, MidpointRounding.AwayFromZero);
		AdvL3Pwms.T5_PWM = (uint)t5_PWM;
		AdvL4Pwms.T1_PWM = (uint)t1_PWM;
		AdvL4Pwms.T2_PWM = (uint)num;
		AdvL4Pwms.T3_PWM = (uint)num2;
		AdvL4Pwms.T4_PWM = (uint)num3;
		AdvL4Pwms.T5_PWM = (uint)t5_PWM;
		AdvL1Pwms = UpdateAdvPwms(AdvL1Pwms.T1_PWM, AdvL1Pwms.T2_PWM, AdvL1Pwms.T3_PWM, AdvL1Pwms.T4_PWM, AdvL1Pwms.T5_PWM);
		AdvL2Pwms = UpdateAdvPwms(AdvL2Pwms.T1_PWM, AdvL2Pwms.T2_PWM, AdvL2Pwms.T3_PWM, AdvL2Pwms.T4_PWM, AdvL2Pwms.T5_PWM);
		AdvL3Pwms = UpdateAdvPwms(AdvL3Pwms.T1_PWM, AdvL3Pwms.T2_PWM, AdvL3Pwms.T3_PWM, AdvL3Pwms.T4_PWM, AdvL3Pwms.T5_PWM);
		AdvL4Pwms = UpdateAdvPwms(AdvL4Pwms.T1_PWM, AdvL4Pwms.T2_PWM, AdvL4Pwms.T3_PWM, AdvL4Pwms.T4_PWM, AdvL4Pwms.T5_PWM);
		SetOfficeAdvPwmRegistry("FAN_OFFICE_MODE_ADV_LV1_PWMS", AdvL1Pwms, g_FanModeAutoSave);
		SetOfficeAdvPwmRegistry("FAN_OFFICE_MODE_ADV_LV2_PWMS", AdvL2Pwms, g_FanModeAutoSave);
		SetOfficeAdvPwmRegistry("FAN_OFFICE_MODE_ADV_LV3_PWMS", AdvL3Pwms, g_FanModeAutoSave);
		SetOfficeAdvPwmRegistry("FAN_OFFICE_MODE_ADV_LV4_PWMS", AdvL4Pwms, g_FanModeAutoSave);
	}

	private FanOfficeAdvLvPwms UpdateAdvPwms(uint T1_PWM, uint T2_PWM, uint T3_PWM, uint T4_PWM, uint T5_PWM)
	{
		FanOfficeAdvLvPwms fanOfficeAdvLvPwms = new FanOfficeAdvLvPwms();
		uint num = (uint)DefaultPWM[0] / 2u;
		uint num2 = (uint)DefaultPWM[4] / 2u;
		if (T1_PWM < num)
		{
			T1_PWM = num;
		}
		if (T1_PWM > num2)
		{
			T1_PWM = num2;
		}
		if (T2_PWM < num)
		{
			T2_PWM = num;
		}
		if (T2_PWM > num2)
		{
			T2_PWM = num2;
		}
		if (T3_PWM < num)
		{
			T3_PWM = num;
		}
		if (T3_PWM > num2)
		{
			T3_PWM = num2;
		}
		if (T4_PWM < num)
		{
			T4_PWM = num;
		}
		if (T4_PWM > num2)
		{
			T4_PWM = num2;
		}
		if (T5_PWM < num)
		{
			T5_PWM = num;
		}
		if (T5_PWM > num2)
		{
			T5_PWM = num2;
		}
		if (T2_PWM < T1_PWM)
		{
			T2_PWM = T1_PWM;
		}
		if (T3_PWM < T2_PWM)
		{
			T3_PWM = T2_PWM;
		}
		if (T4_PWM < T3_PWM)
		{
			T4_PWM = T3_PWM;
		}
		if (T5_PWM < T4_PWM)
		{
			T5_PWM = T4_PWM;
		}
		fanOfficeAdvLvPwms.T1_PWM = T1_PWM;
		fanOfficeAdvLvPwms.T2_PWM = T2_PWM;
		fanOfficeAdvLvPwms.T3_PWM = T3_PWM;
		fanOfficeAdvLvPwms.T4_PWM = T4_PWM;
		fanOfficeAdvLvPwms.T5_PWM = T5_PWM;
		return fanOfficeAdvLvPwms;
	}

	private void Init()
	{
		g_QkeyDefine = GetQkeyDefine();
		if (m_nProjectID == 16 && CustomizeCtrl.GetIsAMDPlatform())
		{
			g_TurboCPUBoostSupport = 1;
		}
		if (m_nProjectID == 11 || m_nProjectID == 12 || m_nProjectID == 13)
		{
			if (g_TurboLevelSupport == 0 && g_TurboModeSupport == 1)
			{
				g_FanTurboModeLevel = GetTurboModeLevel();
				SetFanTurboModeLevelRegistry(g_FanTurboModeLevel, g_FanModeAutoSave);
			}
			if (g_QkeyDefine == 0)
			{
				if (IsOnApLoadFromEc())
				{
					LogCtrl.Write(className + "[Init] 非首次上電開機, Sync up FanMode From EC 0751");
					g_FanMode = GetFanMode();
					SetFanModeRegistry(g_FanMode, g_FanModeAutoSave);
				}
				else
				{
					LogCtrl.Write(className + "[Init] 首次上電開機, write EC 07A6.0 = 1, FanMode Sync from AP");
					SetApExist(exist: true);
				}
			}
		}
		if (App.OsdOnly == 1)
		{
			g_FanMode = GetFanMode();
			LogCtrl.Write(className + "[Init] OSD only, Sync up FanMode From EC 0751, g_FanMode=" + g_FanMode);
			SetFanModeRegistry(g_FanMode, g_FanModeAutoSave);
		}
		if (g_FanMode == 1)
		{
			SetFanMode(g_FanMode, g_FanOfficeMode);
			if (g_SupportMyFan3 != 0)
			{
				if (g_QkeyDefine == 0)
				{
					App.m_TrayCtrl?.ChangeIcon(g_FanMode, bIcon: true);
				}
				else
				{
					App.m_TrayCtrl?.ChangeIcon(g_FanMode, bIcon: false);
				}
			}
		}
		else if (g_FanMode == 0)
		{
			SetFanMode(g_FanMode, 0u);
			if (g_SupportMyFan3 != 0)
			{
				if (g_QkeyDefine == 0)
				{
					App.m_TrayCtrl?.ChangeIcon(g_FanMode, bIcon: true);
				}
				else
				{
					App.m_TrayCtrl?.ChangeIcon(g_FanMode, bIcon: false);
				}
			}
		}
		else
		{
			if (g_FanMode != 2)
			{
				return;
			}
			SetFanMode(g_FanMode, g_FanTurboModeLevel);
			if (g_SupportMyFan3 != 0)
			{
				if (g_QkeyDefine == 0)
				{
					App.m_TrayCtrl?.ChangeIcon(g_FanMode, bIcon: true);
				}
				else
				{
					App.m_TrayCtrl?.ChangeIcon(g_FanMode, bIcon: false);
				}
			}
		}
	}

	private void SetPL124Tau(uint PL1, uint PL2, uint PL4, uint Tau)
	{
		SetPL1Value(PL1);
		SetPL2Value(PL2);
		SetPL4Value(PL4);
	}

	private void SetFanBoost(uint mode, uint type)
	{
		LogCtrl.Write(className + "[SetFanBoost] mode=" + mode + ", type=" + type + ", PowerMode=" + g_PowerMode);
		if (g_FanEnhanced == 1)
		{
			EcCtrl.Write(GetType().Name, 1873, 64);
		}
		else
		{
			EcCtrl.Write(GetType().Name, 1873, 0);
		}
	}

	private void SetFanMode(uint mode, uint type)
	{
		switch (mode)
		{
		case 0u:
			if (g_FanEnhanced == 1)
			{
				EcCtrl.Write(GetType().Name, 1873, 64);
			}
			else
			{
				EcCtrl.Write(GetType().Name, 1873, 0);
			}
			if (g_PowerMode == 0)
			{
				LogCtrl.Write(className + "[SetFanMode] DC, Gaming mode, Set PL124Tau to 0,0,0," + GamingMode_Tau_Default);
				SetPL124Tau(0u, 0u, 0u, GamingMode_Tau_Default);
			}
			else
			{
				LogCtrl.Write(className + "[SetFanMode] AC, Gaming mode, Set PL124Tau to default: " + GamingMode_PL1_Default + "," + GamingMode_PL2_Default + "," + GamingMode_PL4_Default + "," + GamingMode_Tau_Default);
				SetPL124Tau(GamingMode_PL1_Default, GamingMode_PL2_Default, GamingMode_PL4_Default, GamingMode_Tau_Default);
			}
			ProcessControl.Instance.EnableProcessing();
			return;
		case 1u:
			switch (type)
			{
			case 1u:
				EcCtrl.Write(GetType().Name, 1873, 160);
				if (g_MyFan3p5Flag == 1)
				{
					SetOfficeModeAdv_ExtraSpeed(0u);
					SetFan_L1_PWM(1u);
					SetFan_L2_PWM(2u);
					SetFan_L3_PWM(3u);
					SetFan_L4_PWM(4u);
					SetFan_L5_PWM(5u);
				}
				else if (m_nProjectID == 9)
				{
					SetOfficeModeAdv_ExtraSpeed(0u);
					SetFan_L1_PWM(1u);
					SetFan_L2_PWM(2u);
					SetFan_L3_PWM(3u);
					SetFan_L4_PWM(4u);
					SetFan_L5_PWM(5u);
				}
				else
				{
					SetOfficeModeAdv_MinSpeed(0u);
					SetOfficeModeAdv_MinTemp(55u);
					SetOfficeModeAdv_ExtraSpeed(8u);
				}
				break;
			case 2u:
				EcCtrl.Write(GetType().Name, 1873, 160);
				if (g_MyFan3p5Flag == 1)
				{
					SetOfficeModeAdv_ExtraSpeed(0u);
					switch (g_AdvancedFanLevel)
					{
					case 1u:
						SetFan_Optimized_PWM(AdvL1Pwms);
						break;
					case 2u:
						SetFan_Optimized_PWM(AdvL2Pwms);
						break;
					case 3u:
						SetFan_Optimized_PWM(AdvL3Pwms);
						break;
					case 4u:
						SetFan_Optimized_PWM(AdvL4Pwms);
						break;
					}
					break;
				}
				if (m_nProjectID == 9)
				{
					SetOfficeModeAdv_ExtraSpeed(0u);
					switch (g_AdvancedFanLevel)
					{
					case 1u:
						SetFan_Optimized_PWM(AdvL1Pwms);
						break;
					case 2u:
						SetFan_Optimized_PWM(AdvL2Pwms);
						break;
					case 3u:
						SetFan_Optimized_PWM(AdvL3Pwms);
						break;
					case 4u:
						SetFan_Optimized_PWM(AdvL4Pwms);
						break;
					}
					break;
				}
				switch (g_AdvancedFanLevel)
				{
				case 1u:
					g_FanMinSpeed = 0u;
					g_FanMinTemp = 55u;
					g_FanExtraSpeed = 5u;
					break;
				case 2u:
					g_FanMinSpeed = 0u;
					g_FanMinTemp = 55u;
					g_FanExtraSpeed = 10u;
					break;
				case 3u:
					g_FanMinSpeed = 0u;
					g_FanMinTemp = 55u;
					g_FanExtraSpeed = 15u;
					break;
				}
				SetOfficeModeAdv_MinSpeed(g_FanMinSpeed);
				SetOfficeModeAdv_MinTemp(g_FanMinTemp);
				SetOfficeModeAdv_ExtraSpeed(g_FanExtraSpeed);
				break;
			}
			if (g_PowerSettingMode == 1)
			{
				if (g_PowerMode == 0)
				{
					LogCtrl.Write(className + "[SetFanMode] DC, Office ECO mode, Set PL124Tau to 0,0,0," + OfficeMode_Tau_Default);
					SetPL124Tau(0u, 0u, 0u, OfficeMode_Tau_Default);
				}
				else
				{
					LogCtrl.Write(className + "[SetFanMode] AC, Office ECO mode, Set PL124Tau to 25/25/default/default : 25,25," + OfficeMode_PL4_Default + "," + OfficeMode_Tau_Default);
					SetPL124Tau(25u, 25u, OfficeMode_PL4_Default, OfficeMode_Tau_Default);
				}
			}
			else if (g_PowerSettingMode == 2)
			{
				if (g_PowerMode == 0)
				{
					LogCtrl.Write(className + "[SetFanMode] DC, Office Standard mode, Set PL124Tau to 0,0,0," + OfficeMode_Tau_Default);
					SetPL124Tau(0u, 0u, 0u, OfficeMode_Tau_Default);
				}
				else
				{
					LogCtrl.Write(className + "[SetFanMode] AC, Office Standard mode, Set PL124Tau to default : " + OfficeMode_PL1_Default + "," + OfficeMode_PL2_Default + "," + OfficeMode_PL4_Default + "," + OfficeMode_Tau_Default);
					SetPL124Tau(OfficeMode_PL1_Default, OfficeMode_PL2_Default, OfficeMode_PL4_Default, OfficeMode_Tau_Default);
				}
			}
			ProcessControl.Instance.DisableProcessing();
			return;
		}
		if (g_FanMode != 2)
		{
			return;
		}
		LogCtrl.Write(className + "[SetFanMode] Turbo mode, Set ECRAM 0x" + ((ushort)1873).ToString("X") + " = 0x" + ECSpec.MyFanCTLByteFlag.Turbo_Mode.ToString("X"));
		EcCtrl.Write(GetType().Name, 1873, 16);
		SetTurboMode(type);
		if (GetProjectIdFromEC() == 16 && CustomizeCtrl.GetIsAMDPlatform())
		{
			if (g_FanTurboModeCPUBOOST == 1)
			{
				UpdatedTurboCPUBoost(Enable: true);
			}
			else
			{
				UpdatedTurboCPUBoost(Enable: false);
			}
		}
		else
		{
			LogCtrl.Write(className + "[SetFanMode] DC, Turbo mode, Set PL124Tau to 0,0,0," + GamingMode_Tau_Default);
			SetPL124Tau(0u, 0u, 0u, GamingMode_Tau_Default);
		}
		SetFanBoost(g_FanEnhanced);
	}

	private int[] GetFanTablePWMDefault()
	{
		int[] array = new int[5];
		byte Data = 0;
		byte Data2 = 0;
		byte Data3 = 0;
		byte Data4 = 0;
		byte Data5 = 0;
		EcCtrl.Read(GetType().Name, 1926, ref Data);
		EcCtrl.Read(GetType().Name, 1927, ref Data2);
		EcCtrl.Read(GetType().Name, 1928, ref Data3);
		EcCtrl.Read(GetType().Name, 1929, ref Data4);
		EcCtrl.Read(GetType().Name, 1930, ref Data5);
		array[0] = (int)(Convert.ToUInt64(Data) & 0xFF);
		array[1] = (int)(Convert.ToUInt64(Data2) & 0xFF);
		array[2] = (int)(Convert.ToUInt64(Data3) & 0xFF);
		array[3] = (int)(Convert.ToUInt64(Data4) & 0xFF);
		array[4] = (int)(Convert.ToUInt64(Data5) & 0xFF);
		return array;
	}

	private int[] CheckFanTablePWMDefault(int[] nDefaultPWM)
	{
		if (nDefaultPWM[0] == 0 || nDefaultPWM[1] == 0 || nDefaultPWM[2] == 0 || nDefaultPWM[3] == 0 || nDefaultPWM[4] == 0)
		{
			nDefaultPWM[0] = 60;
			nDefaultPWM[1] = 70;
			nDefaultPWM[2] = 80;
			nDefaultPWM[3] = 90;
			nDefaultPWM[4] = 100;
		}
		return nDefaultPWM;
	}

	private int GetBitFromByte(byte data, int num)
	{
		return (data >> num) & 1;
	}

	private int GetProjectIdFromEC()
	{
		byte Data = 0;
		EcCtrl.Read(GetType().Name, 1856, ref Data);
		return (int)(Convert.ToUInt64(Data) & 0xFF);
	}

	private void SetFanBoost(int status)
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
		int bitFromByte = GetBitFromByte(data, 4);
		int bitFromByte2 = GetBitFromByte(data, 7);
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
		LogCtrl.Write(className + $"[GetFanMode] EC 0751 bit4[{bitFromByte}], bit7[{bitFromByte2}]");
		return result;
	}

	private void SetTurboMode(uint type)
	{
		byte Data = 0;
		byte b = 243;
		byte b2 = 0;
		byte b3 = 0;
		switch (type)
		{
		case 1u:
			b2 = 0;
			break;
		case 2u:
			b2 = 4;
			break;
		case 3u:
			b2 = 8;
			break;
		case 4u:
			b2 = 12;
			break;
		}
		EcCtrl.Read(GetType().Name, 1932, ref Data);
		b3 = (byte)((Data & b) + b2);
		LogCtrl.Write(className + "[SetTurboMode] Turbo mode type " + type + ", Set ECRAM 0x" + ((ushort)1932).ToString("X") + " = 0x" + b3.ToString("X2"));
		EcCtrl.Write(GetType().Name, 1932, b3);
	}

	private uint GetTurboModeLevel()
	{
		byte Data = 0;
		byte b = 12;
		byte b2 = 0;
		uint result = 2u;
		EcCtrl.Read(GetType().Name, 1932, ref Data);
		switch ((byte)(Data & b))
		{
		case 0:
			result = 1u;
			break;
		case 4:
			result = 2u;
			break;
		case 8:
			result = 3u;
			break;
		case 12:
			result = 4u;
			break;
		}
		return result;
	}

	private int GetMyFan3p5Flag()
	{
		byte Data = 0;
		EcCtrl.Read(GetType().Name, 1934, ref Data);
		if (GetBitFromByte(Data, 2) != 1)
		{
			return 0;
		}
		return 1;
	}

	private int CheckMyFan3p5Flag()
	{
		g_MyFan3p5Flag = GetMyFan3p5Flag();
		return g_MyFan3p5Flag;
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

	private int GetDefaultMode()
	{
		int result = 0;
		byte Data = 0;
		EcCtrl.Read(GetType().Name, 1922, ref Data);
		switch ((byte)(Convert.ToUInt64(Data) & 0x10))
		{
		case 0:
			result = 0;
			break;
		case 16:
			result = 1;
			break;
		}
		return result;
	}

	private void SetOfficeModeAdv_MinSpeed(uint level)
	{
		EcCtrl.Write(GetType().Name, 1950, (byte)Level2Pwm(level));
	}

	private void SetOfficeModeAdv_MinTemp(uint temp)
	{
		EcCtrl.Write(GetType().Name, 1951, (byte)temp);
	}

	private void SetOfficeModeAdv_ExtraSpeed(uint level)
	{
		EcCtrl.Write(GetType().Name, 1952, (byte)level);
	}

	private bool IsOnApLoadFromEc()
	{
		byte Data = 0;
		EcCtrl.Read(GetType().Name, 1958, ref Data);
		if (GetBitFromByte(Data, 0) != 1)
		{
			return false;
		}
		return true;
	}

	private void SetApExist(bool exist)
	{
		byte Data = 0;
		EcCtrl.Read(GetType().Name, 1958, ref Data);
		byte b = (byte)Convert.ToUInt64(Data);
		b = ((!exist) ? ((byte)(b & 0xFE)) : ((byte)(b | 1)));
		EcCtrl.Write(GetType().Name, 1958, b);
	}

	private void GetGamingPLDefaultValue(ref uint PL1, ref uint PL2, ref uint PL4)
	{
		byte Data = 0;
		byte Data2 = 0;
		byte Data3 = 0;
		EcCtrl.Read(GetType().Name, 1840, ref Data);
		EcCtrl.Read(GetType().Name, 1841, ref Data2);
		EcCtrl.Read(GetType().Name, 1842, ref Data3);
		PL1 = (uint)(Convert.ToUInt64(Data) & 0xFF);
		PL2 = (uint)(Convert.ToUInt64(Data2) & 0xFF);
		PL4 = (uint)(Convert.ToUInt64(Data3) & 0xFF);
	}

	private void GetOfficePLDefaultValue(ref uint PL1, ref uint PL2, ref uint PL4)
	{
		byte Data = 0;
		byte Data2 = 0;
		byte Data3 = 0;
		EcCtrl.Read(GetType().Name, 1844, ref Data);
		EcCtrl.Read(GetType().Name, 1845, ref Data2);
		EcCtrl.Read(GetType().Name, 1846, ref Data3);
		PL1 = (uint)(Convert.ToUInt64(Data) & 0xFF);
		PL2 = (uint)(Convert.ToUInt64(Data2) & 0xFF);
		PL4 = (uint)(Convert.ToUInt64(Data3) & 0xFF);
	}

	private uint GetTauDefaultValue()
	{
		uint num = 0u;
		byte Data = 0;
		EcCtrl.Read(GetType().Name, 1848, ref Data);
		num = (uint)(Convert.ToUInt64(Data) & 0xFF);
		if (num == 0)
		{
			num = 56u;
		}
		return num;
	}

	private void SetBasicFanLevel(uint level)
	{
		EcCtrl.Write(GetType().Name, 1873, (byte)(128 + level));
	}

	private void SetFan_L1_PWM(uint level)
	{
		EcCtrl.Write(GetType().Name, 1859, (byte)PWM2Byte(level));
	}

	private void SetFan_L2_PWM(uint level)
	{
		EcCtrl.Write(GetType().Name, 1860, (byte)PWM2Byte(level));
	}

	private void SetFan_L3_PWM(uint level)
	{
		EcCtrl.Write(GetType().Name, 1861, (byte)PWM2Byte(level));
	}

	private void SetFan_L4_PWM(uint level)
	{
		EcCtrl.Write(GetType().Name, 1862, (byte)PWM2Byte(level));
	}

	private void SetFan_L5_PWM(uint level)
	{
		EcCtrl.Write(GetType().Name, 1863, (byte)PWM2Byte(level));
	}

	private void SetFan_Optimized_PWM(byte pwm1, byte pwm2, byte pwm3, byte pwm4, byte pwm5)
	{
		if (pwm1 < DefaultPWM[0])
		{
			pwm1 = (byte)DefaultPWM[0];
		}
		if (pwm2 < DefaultPWM[0] || pwm2 > DefaultPWM[4])
		{
			pwm2 = (byte)DefaultPWM[1];
		}
		if (pwm3 < DefaultPWM[0] || pwm3 > DefaultPWM[4])
		{
			pwm3 = (byte)DefaultPWM[2];
		}
		if (pwm4 < DefaultPWM[0] || pwm4 > DefaultPWM[4])
		{
			pwm4 = (byte)DefaultPWM[3];
		}
		if (pwm5 > DefaultPWM[4])
		{
			pwm5 = (byte)DefaultPWM[4];
		}
		EcCtrl.Write(GetType().Name, 1859, pwm1);
		EcCtrl.Write(GetType().Name, 1860, pwm2);
		EcCtrl.Write(GetType().Name, 1861, pwm3);
		EcCtrl.Write(GetType().Name, 1862, pwm4);
		EcCtrl.Write(GetType().Name, 1863, pwm5);
	}

	private void SetFan_Optimized_PWM(FanOfficeAdvLvPwms Pwms)
	{
		EcCtrl.Write(GetType().Name, 1859, (byte)(Pwms.T1_PWM * 2));
		EcCtrl.Write(GetType().Name, 1860, (byte)(Pwms.T2_PWM * 2));
		EcCtrl.Write(GetType().Name, 1861, (byte)(Pwms.T3_PWM * 2));
		EcCtrl.Write(GetType().Name, 1862, (byte)(Pwms.T4_PWM * 2));
		EcCtrl.Write(GetType().Name, 1863, (byte)(Pwms.T5_PWM * 2));
	}

	private void SetPL1Value(ulong PL1)
	{
		EcCtrl.Write(GetType().Name, 1923, (byte)PL1);
	}

	private void SetPL2Value(ulong PL2)
	{
		EcCtrl.Write(GetType().Name, 1924, (byte)PL2);
	}

	private void SetPL4Value(ulong PL4)
	{
		EcCtrl.Write(GetType().Name, 1925, (byte)PL4);
	}

	private void SetFanModeRegistry(uint FanMode, int AutoSave)
	{
		if (AutoSave == 1)
		{
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_RegistryPath, "FanMode", FanMode, RegistryValueKind.DWord);
		}
	}

	private void SetFanEnhancedRegistry(int status, int AutoSave)
	{
		if (AutoSave == 1)
		{
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_RegistryPath, "FanEnhanced", status, RegistryValueKind.DWord);
		}
	}

	private void SetFanOfficeModeRegistry(uint OfficeMode, int AutoSave)
	{
		if (AutoSave == 1)
		{
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_RegistryPath, "OfficeMode", OfficeMode, RegistryValueKind.DWord);
		}
	}

	private void SetPowerSettingModeRegistry(uint PowerSettingMode, int AutoSave)
	{
		if (AutoSave == 1)
		{
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_RegistryPath, "PowerSettingMode", PowerSettingMode, RegistryValueKind.DWord);
		}
	}

	private void SetOfficeModeBasicLevelRegistry(uint FanLevel, int AutoSave)
	{
		if (AutoSave == 1)
		{
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_RegistryPath, "OfficeBasicLevel", FanLevel, RegistryValueKind.DWord);
		}
	}

	private void SetFanAutoSaveRegistry(int AutoSave)
	{
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_RegistryPath, "FanModeAutoSave", AutoSave, RegistryValueKind.DWord);
	}

	private void SetAdvancedTempLevelRegistry(string key, uint LevelTem)
	{
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_RegistryPath, key, LevelTem, RegistryValueKind.DWord);
	}

	private void SetFanTurboModeLevelRegistry(uint TurboModeLevel, int AutoSave)
	{
		if (AutoSave == 1)
		{
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_RegistryPath, "TurboModeLevel", TurboModeLevel, RegistryValueKind.DWord);
		}
	}

	private void SetRegistry(string name, uint value, int autosave)
	{
		if (autosave == 1)
		{
			switch (name)
			{
			case "OfficeAdvancedLevel":
			case "FanMinSpeed":
			case "FanMinTemp":
			case "FanExtraSpeed":
				RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_RegistryPath, name, value, RegistryValueKind.DWord);
				break;
			}
		}
	}

	private void SetOfficeAdvPwmRegistry(string level, FanOfficeAdvLvPwms pwms, int autosave)
	{
		string text = "\\OfficeModeAdvL1";
		if (autosave == 1)
		{
			switch (level)
			{
			case "FAN_OFFICE_MODE_ADV_LV1_PWMS":
				text = "\\OfficeModeAdvL1";
				break;
			case "FAN_OFFICE_MODE_ADV_LV2_PWMS":
				text = "\\OfficeModeAdvL2";
				break;
			case "FAN_OFFICE_MODE_ADV_LV3_PWMS":
				text = "\\OfficeModeAdvL3";
				break;
			case "FAN_OFFICE_MODE_ADV_LV4_PWMS":
				text = "\\OfficeModeAdvL4";
				break;
			}
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_RegistryPath + text, "T1_PWM", pwms.T1_PWM, RegistryValueKind.DWord);
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_RegistryPath + text, "T2_PWM", pwms.T2_PWM, RegistryValueKind.DWord);
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_RegistryPath + text, "T3_PWM", pwms.T3_PWM, RegistryValueKind.DWord);
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_RegistryPath + text, "T4_PWM", pwms.T4_PWM, RegistryValueKind.DWord);
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_RegistryPath + text, "T5_PWM", pwms.T5_PWM, RegistryValueKind.DWord);
		}
	}

	private ulong PWM2Byte(uint level)
	{
		ulong result = 0uL;
		switch (level)
		{
		case 0u:
			result = 0uL;
			break;
		case 1u:
			result = (ulong)DefaultPWM[0];
			break;
		case 2u:
			result = (ulong)DefaultPWM[1];
			break;
		case 3u:
			result = (ulong)DefaultPWM[2];
			break;
		case 4u:
			result = (ulong)DefaultPWM[3];
			break;
		case 5u:
			result = (ulong)DefaultPWM[4];
			break;
		}
		return result;
	}

	private ulong Level2Pwm(uint level)
	{
		ulong result = 0uL;
		switch (level)
		{
		case 0u:
			result = 0uL;
			break;
		case 1u:
			result = 60uL;
			break;
		case 2u:
			result = 80uL;
			break;
		case 3u:
			result = 100uL;
			break;
		case 4u:
			result = 120uL;
			break;
		case 5u:
			result = 140uL;
			break;
		}
		return result;
	}

	private void SetTauValue(uint value)
	{
	}

	private void IsSupportMyFan3()
	{
		byte Data = 0;
		EcCtrl.Read(GetType().Name, 1922, ref Data);
		if ((byte)(Convert.ToUInt64(Data) & 8) == 8)
		{
			g_SupportMyFan3 = 1;
		}
		else
		{
			g_SupportMyFan3 = 0;
		}
		LogCtrl.Write(className + "[IsSupportMyFan3] g_SupportMyFan3 = " + g_SupportMyFan3);
	}

	private string FanModeString(uint FanMode)
	{
		return FanMode switch
		{
			0u => "Gaming mode", 
			1u => "Office mode", 
			2u => "Turbo mode", 
			_ => "", 
		};
	}
}
