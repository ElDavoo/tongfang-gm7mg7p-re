using System;
using System.Linq;
using System.Management;
using System.Reflection;
using System.Text;
using GCUService.Workaround;
using Microsoft.Win32;
using MyECIO;
using MyRGBKeyboard;
using OemServiceModel;
using Utility;

namespace MyControlCenter;

public class CustomizeCtrl
{
	private static string className = "[" + MethodBase.GetCurrentMethod().DeclaringType.Name + "] ";

	private static MyEcCtrl EcCtrl = MyEcCtrl.Instance;

	private static MyFanCtrl m_MyFan = MyFanCtrl.Instance;

	private static string m_sRegPath = "\\OEM\\GamingCenter2";

	private static int m_CustomizeTarget = 1;

	private static int m_ProjectID;

	private static bool m_IsAMDPlatform = false;

	public static void Init()
	{
		m_CustomizeTarget = RegistryCtrl.GetCustomizeTarget();
		m_ProjectID = EcCtrl.GetProjectIdFromEC();
		CustomizeInfo.m_ProjectID = m_ProjectID.ToString();
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2", "ProjectID", CustomizeInfo.m_ProjectID, RegistryValueKind.DWord);
		m_IsAMDPlatform = EcCtrl.IsAMDPlatform();
		UpdateSetupInfo();
		NvramVariable_Init();
		HIDRGBLightbar.Instance.HIDLightbarInitedEvent += Instance_HIDLightbarInitedEvent;
	}

	public static bool GetIsAMDPlatform()
	{
		return m_IsAMDPlatform;
	}

	private static void OemService_Init()
	{
		LogCtrl.Write(className + "[OemService_Init] 取得 OemService support items, and create support registry");
		OemServiceInfo.Get();
		LogCtrl.Write(className + "[OemService_Init] Check Factory TDR function");
		Tdr.Set();
		CustomizeInfo.m_sKeyboardType = OemServiceInfo.GetKeyboardType();
		CustomizeInfo.m_sLightbarType = OemServiceInfo.GetLightbarSupportType();
		UpdateLightbarSupportItems();
		CustomizeInfo.m_supportColorCalibration = OemServiceInfo.m_supportColorCalibration;
	}

	private static void NvramVariable_Init()
	{
		LogCtrl.Write(className + "[NvramVariable_Init] 取得 NvramVariable support items, and create support registry");
		NvramVariable.Get();
		LogCtrl.Write(className + "[NvramVariable_Init] Check Factory TDR function");
		Tdr2.Set();
		CustomizeInfo.m_sKeyboardType = NvramVariable.GetKeyboardType();
		CustomizeInfo.m_sLightbarType = NvramVariable.GetLightbarSupportType();
		UpdateLightbarSupportItems();
		CustomizeInfo.m_supportColorCalibration = NvramVariable.m_supportColorCalibration;
		RefreshItemSupportReg();
	}

	private static void Customize_Init()
	{
		LogCtrl.Write(className + "[Customize_Init] START");
		CustomizeInfo.m_sKeyboardType = "1";
		if (EcCtrl.isSupportRGBLBFromEC() == 1)
		{
			NvramVariable.m_supportLightBar = 1;
			NvramVariable.m_supportRGBLB = 1;
			CustomizeInfo.m_sLightbarType = "2";
			UpdateLightbarSupportItems();
		}
		else
		{
			CustomizeInfo.m_sLightbarType = "0";
		}
		if (m_CustomizeTarget == 23)
		{
			Wkd_SupportColorCalibration.Init();
		}
		else if ((int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2", "ColorCalibration", 1) == 0)
		{
			CustomizeInfo.m_supportColorCalibration = 255;
		}
		else
		{
			CustomizeInfo.m_supportColorCalibration = 1;
		}
	}

	public static async void Receive(byte[] data)
	{
		string text = ((dynamic)(await Json.ToObjectAsync<object>(Encoding.UTF8.GetString(data))))["Action"];
		_ = string.Empty;
		LogCtrl.Write("---------------" + LogCtrl.GetTime() + "---------------");
		LogCtrl.Write(className + "[Recieve] msg = " + text);
		if (!(text == "GETSETUPINFO"))
		{
			if (text == "GETSUPPORT")
			{
				UpdateSupportAfterProcess();
				PublishSupportAll();
			}
		}
		else
		{
			PublishSetupInfo();
		}
	}

	private static void UpdateSetupInfo()
	{
		try
		{
			SetupPara.nAppType = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegPath, "AppType", 1);
			SetupPara.sAPPTarget = (string)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegPath, "APPTarget", "STD");
			SetupPara.sAppIcon = (string)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegPath, "AppIcon", "gamingcenter256.ico");
			SetupPara.nCustomizeTarget = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegPath, "CustomizeTarget", 1);
			SetupPara.sTitleName = (string)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegPath, "TitleName", "NA");
			SetupPara.sAppVersion = (string)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegPath, "AppVersion", "NA");
			SetupPara.nBatteryCalibration = 1;
			SetupPara.nColorCalibration = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegPath, "ColorCalibration", 0);
			SetupPara.nDebugMode = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegPath, "DebugMode", 0);
		}
		catch (Exception ex)
		{
			LogCtrl.Write(string.Format(className + "[UpdateSetupInfo] RegistrySoftwareKeyRead Failed {0}", ex.ToString()));
		}
	}

	private static void PublishSetupInfo()
	{
		dynamic val = new
		{
			AppType = SetupPara.nAppType,
			APPTarget = SetupPara.sAPPTarget,
			AppIcon = SetupPara.sAppIcon,
			CustomizeTarget = SetupPara.nCustomizeTarget.ToString(),
			TitleName = SetupPara.sTitleName,
			AppVersion = SetupPara.sAppVersion,
			BatteryCalibration = SetupPara.nBatteryCalibration.ToString(),
			PluginPath = PluginInfo.sPluginPath,
			DebugMode = SetupPara.nDebugMode.ToString()
		};
		App.m_MQTTService.Publish("Customize/Info", val, false);
		LogCtrl.TraceMessage("AppType: " + SetupPara.nAppType + "APPTarget: " + SetupPara.sAPPTarget + "AppIcon: " + SetupPara.sAppIcon + "CustomizeTarget: " + SetupPara.nCustomizeTarget + "TitleName: " + SetupPara.sTitleName + "AppVersion: " + SetupPara.sAppVersion + "BatteryCalibration: " + SetupPara.nBatteryCalibration + "PluginPath: " + PluginInfo.sPluginPath + "DebugMode: " + SetupPara.nDebugMode, "PublishSetupInfo", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\Customize\\CustomizeCtrl.cs", 198);
	}

	private static void UpdateSupportAfterProcess()
	{
		CustomizeInfo.m_supportRamFan1p5 = (EcCtrl.IsSuportRamFan1p5() ? "1" : "0");
	}

	private static void PublishSupportAll()
	{
		dynamic val = new
		{
			LightbarType = CustomizeInfo.m_sLightbarType,
			KeyboardType = CustomizeInfo.m_sKeyboardType,
			LEDLightbarColorful = CustomizeInfo.m_sLEDLightbarColorful,
			LEDLightbarBreathEffect = CustomizeInfo.m_sLEDLightbarBreathEffect,
			ProjectID = CustomizeInfo.m_ProjectID,
			SupportColorCalibration = CustomizeInfo.m_supportColorCalibration,
			SupportRamFan1p5 = CustomizeInfo.m_supportRamFan1p5,
			BatteryProtectionType = "2"
		};
		App.m_MQTTService.Publish("Customize/Info", val, false);
		LogCtrl.TraceMessage("LightbarType: " + CustomizeInfo.m_sLightbarType + "KeyboardType: " + CustomizeInfo.m_sKeyboardType + "LEDLightbarColorful: " + CustomizeInfo.m_sLEDLightbarColorful + "LEDLightbarBreathEffect: " + CustomizeInfo.m_sLEDLightbarBreathEffect + "ProjectID: " + CustomizeInfo.m_ProjectID + "SupportColorCalibration: " + CustomizeInfo.m_supportColorCalibration + "SupportRamFan1p5: " + CustomizeInfo.m_supportRamFan1p5 + "BatteryProtectionType: 2", "PublishSupportAll", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\Customize\\CustomizeCtrl.cs", 237);
	}

	private static void UpdateLightbarSupportItems()
	{
		if (CustomizeInfo.m_sLightbarType == "2")
		{
			if (MyRgbLightBarDefault.m_nSupportRGBLightBarColorful == 1)
			{
				CustomizeInfo.m_sLEDLightbarColorful = "1";
			}
			if (MyRgbLightBarDefault.m_nSupportRGBLightBarBreathEffect == 1)
			{
				CustomizeInfo.m_sLEDLightbarBreathEffect = "1";
			}
		}
	}

	public static bool GetFanBoostBtnSupport()
	{
		int customizeTarget = RegistryCtrl.GetCustomizeTarget();
		bool flag = true;
		flag = m_MyFan.m_Manager.g_QkeyDefine == 0;
		int projectIdFromEC = EcCtrl.GetProjectIdFromEC();
		if (projectIdFromEC != 9 && (uint)(projectIdFromEC - 11) > 3u && customizeTarget == 3)
		{
			LogCtrl.Write(string.Format(className + "[GetFanBoostBtnSupport] CustomizeTarget: {0}, hide fanboost button", customizeTarget));
			flag = false;
		}
		if (customizeTarget == 17)
		{
			LogCtrl.Write(string.Format(className + "[GetFanBoostBtnSupport] CustomizeTarget: {0}, hide fanboost button", customizeTarget));
			flag = false;
		}
		return flag;
	}

	private static string GetFanOfficeAdvanceBarSupport()
	{
		if (m_MyFan.m_Manager.g_MyFan3p5Flag == 1)
		{
			return "1";
		}
		return "0";
	}

	public static int GetCustomId()
	{
		return m_CustomizeTarget;
	}

	private static void Instance_HIDLightbarInitedEvent(object sender, EventArgs e)
	{
		NvramVariable.m_sLightbarType = "3";
		CustomizeInfo.m_sLightbarType = "3";
		HIDRGBLightbar.Instance.HIDLightbarInitedEvent -= Instance_HIDLightbarInitedEvent;
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegPath + "\\ItemSupport", "LightbarSupport", 1, RegistryValueKind.DWord);
	}

	private static void DetectQCRefreshFeatures()
	{
		SMBIOSINFO.m_bSupportQcRefreshRule = IsQCRefreshBIOS();
		if (SMBIOSINFO.m_bSupportQcRefreshRule)
		{
			string text = SMBIOSFirmwareTable.GetString(11u, 18u);
			LogCtrl.Write(className + "[GetFeatureSupportFromSMBIOS] SMBIOS GetString: " + text);
			text = text.Replace(" ", "");
			if (text == string.Empty)
			{
				SMBIOSINFO.m_bSupportFnKeySetting = true;
				SMBIOSINFO.m_bSupportBatteryLifeExtension = true;
				SMBIOSINFO.m_bSupportFanDutyCycle = true;
				return;
			}
			char[] array = text.ToArray();
			Array.Reverse(array);
			string key = new string(array);
			SMBIOSINFO.m_bSupportFnKeySetting = GetSwitchStatus(key, 2);
			SMBIOSINFO.m_bSupportBatteryLifeExtension = GetSwitchStatus(key, 4);
			SMBIOSINFO.m_bSupportFanDutyCycle = GetSwitchStatus(key, 3);
		}
	}

	private static bool GetSwitchStatus(string key, int index)
	{
		bool result = false;
		if (index < key.Length)
		{
			result = (key.Substring(index, 1).Contains("1") ? true : false);
		}
		return result;
	}

	private static bool IsQCRefreshBIOS()
	{
		bool result = false;
		string text = "null";
		foreach (ManagementObject item in new ManagementObjectSearcher("SELECT * FROM Win32_BIOS").Get())
		{
			if (((string[])item["BIOSVersion"]).Length > 1)
			{
				text = ((string[])item["BIOSVersion"])[1];
			}
			else
			{
				LogCtrl.Write(className + "[CheckQCRefreshRuleSupport] BIOSVersion format error.");
			}
		}
		if (text != "null")
		{
			string[] array = text.Split('.');
			if (array.Length > 4)
			{
				string text2 = array[array.Length - 4].ToString();
				if (int.Parse(text2) > 100)
				{
					result = true;
				}
				else
				{
					LogCtrl.Write(className + "[CheckQCRefreshRuleSupport] QCRefreshRule is not supported. BIOS version: " + text2);
				}
			}
		}
		return result;
	}

	private static bool IsQcPlatformFromNVSSID()
	{
		bool result = false;
		byte bus = 0;
		byte dev = 0;
		byte func = 0;
		uint offset = 44u;
		uint pData = 0u;
		try
		{
			EcCtrl.ReadPciDword(bus, dev, func, offset, ref pData);
			switch (pData)
			{
			case 274668805u:
			case 545685638u:
			case 545751174u:
			case 806453382u:
			case 806518918u:
				result = true;
				break;
			}
		}
		catch
		{
			return result;
		}
		return result;
	}

	private static void RefreshItemSupportReg()
	{
		NVRAM_STRUCT fwVars = NvramVariable.GetFwVars();
		int aCRecoverySupport = fwVars.ACRecoverySupport;
		int num = 0;
		num = ((Convert.ToInt32(fwVars.OemDisplayMode) != 255) ? 1 : 0);
		int colorCalibrationSupport = fwVars.ColorCalibrationSupport;
		int num2 = Convert.ToInt32(GetFanBoostBtnSupport());
		int num3 = Convert.ToInt32(GetIsAMDPlatform());
		int num4 = Convert.ToInt32(UtilityExtensions.IsNvGpu());
		int num5 = 1;
		int num6 = 0;
		if (Convert.ToInt32(CustomizeInfo.m_sLightbarType) >= 2)
		{
			num6 = 1;
		}
		int num7 = 0;
		if (Convert.ToInt32(CustomizeInfo.m_sLightbarType) == 2)
		{
			num7 = 1;
		}
		int num8 = 0;
		num8 = ((!m_ProjectID.IsProjectId_NonNumPad()) ? 1 : 0);
		int num9 = 0;
		int num10 = 1;
		int num11 = 1;
		if (!m_ProjectID.IsProjectId_Commercial())
		{
			num9 = 0;
			num10 = 1;
			num11 = 1;
		}
		else
		{
			num9 = 1;
			num10 = 0;
			num11 = 0;
		}
		int num12 = Convert.ToInt32(EcCtrl.IsSuportRamFan1p5());
		int num13 = 1;
		int num14 = Convert.ToInt32(EcCtrl.GetTurboModeSupport());
		int num15 = Convert.ToInt32(EcCtrl.GetTypeCAdaptorPrioritySupport());
		string setvalue = Convert.ToString(EcCtrl.GetBiosProjctID());
		int num16 = Convert.ToInt32(EcCtrl.IsHeroProject());
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegPath + "\\ItemSupport", "AcRecoverySwitchSupport", aCRecoverySupport, RegistryValueKind.DWord);
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegPath + "\\ItemSupport", "ColorCalibrationSupport", colorCalibrationSupport, RegistryValueKind.DWord);
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegPath + "\\ItemSupport", "DGpuDirectConnectionSupport", num, RegistryValueKind.DWord);
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegPath + "\\ItemSupport", "FanBoostBtnSupport", num2, RegistryValueKind.DWord);
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegPath + "\\ItemSupport", "IsAMDPlatform", num3, RegistryValueKind.DWord);
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegPath + "\\ItemSupport", "IsNvGpu", num4, RegistryValueKind.DWord);
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegPath + "\\ItemSupport", "KeyboardSupport", num5, RegistryValueKind.DWord);
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegPath + "\\ItemSupport", "LightbarSupport", num6, RegistryValueKind.DWord);
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegPath + "\\ItemSupport", "RGBLightbarSupport", num7, RegistryValueKind.DWord);
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegPath + "\\ItemSupport", "IsProjectIdCommercial", num9, RegistryValueKind.DWord);
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegPath + "\\ItemSupport", "FanSettingsSupport", num10, RegistryValueKind.DWord);
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegPath + "\\ItemSupport", "NumPadSupport", num8, RegistryValueKind.DWord);
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegPath + "\\ItemSupport", "OcSettingsSupport", num11, RegistryValueKind.DWord);
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegPath + "\\ItemSupport", "RamFan1p5Support", num12, RegistryValueKind.DWord);
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegPath + "\\ItemSupport", "SystemMonitorSupport", num13, RegistryValueKind.DWord);
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegPath + "\\ItemSupport", "TurboModeSupport", num14, RegistryValueKind.DWord);
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegPath + "\\ItemSupport", "TypeCSupport", num15, RegistryValueKind.DWord);
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegPath + "\\ItemSupport", "BIOS_PROJECT_ID", setvalue, RegistryValueKind.String);
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegPath + "\\ItemSupport", "IsHeroProject", num16, RegistryValueKind.DWord);
	}
}
