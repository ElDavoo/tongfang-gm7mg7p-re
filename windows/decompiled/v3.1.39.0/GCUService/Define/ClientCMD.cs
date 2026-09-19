using System.Runtime.InteropServices;

namespace Define;

internal class ClientCMD
{
	[StructLayout(LayoutKind.Sequential, Size = 1)]
	public struct FAN
	{
		public const string Mode = "Mode";

		public const string OfficeMode = "OfficeMode";

		public const string BasicFanLevel = "BasicFanLevel";

		public const string FanLeveTem1 = "FanLeveTem1";

		public const string FanLeveTem2 = "FanLeveTem2";

		public const string FanLeveTem3 = "FanLeveTem3";

		public const string FanLeveTem4 = "FanLeveTem4";

		public const string FanLeveTem5 = "FanLeveTem5";

		public const string FanEnhanced = "FanEnhanced";

		public const string FanModeAutoSave = "FanModeAutoSave";

		public const string PowerMode = "PowerMode";

		public const string PowerSettingMode = "PowerSettingMode";
	}

	[StructLayout(LayoutKind.Sequential, Size = 1)]
	public struct OSD
	{
		public const string OSD_HIDDEN_ON = "OSD_HIDDEN_ON";

		public const string OSD_HIDDEN_OFF = "OSD_HIDDEN_OFF";

		public const string OSD_GAMING = "OSD_GAMING";

		public const string OSD_TURBO = "OSD_TURBO";

		public const string OSD_OFFICE = "OSD_OFFICE";

		public const string OSD_FANBOOST_ON = "OSD_FANBOOST_ON";

		public const string OSD_FANBOOST_OFF = "OSD_FANBOOST_OFF";

		public const string OSD_CAPS_Lock = "OSD_CAPS_Lock";

		public const string OSD_CAPS_UnLock = "OSD_CAPS_UnLock";

		public const string OSD_NUM_Lock = "OSD_NUM_Lock";

		public const string OSD_NUM_UnLock = "OSD_NUM_UnLock";

		public const string OSD_SCROL_Lock = "OSD_SCROL_Lock";

		public const string OSD_SCROL_UnLock = "OSD_SCROL_UnLock";

		public const string OSD_WinKey_Lock = "OSD_WinKey_Lock";

		public const string OSD_WinKey_UnLock = "OSD_WinKey_UnLock";

		public const string OSD_Tp_On = "OSD_Tp_On";

		public const string OSD_Tp_Off = "OSD_Tp_Off";

		public const string OSD_Radio_On = "OSD_Radio_On";

		public const string OSD_Radio_Off = "OSD_Radio_Off";

		public const string OSD_KB_LED_LEVEL0 = "OSD_KB_LED_LEVEL0";

		public const string OSD_KB_LED_LEVEL1 = "OSD_KB_LED_LEVEL1";

		public const string OSD_KB_LED_LEVEL2 = "OSD_KB_LED_LEVEL2";

		public const string OSD_KB_LED_LEVEL3 = "OSD_KB_LED_LEVEL3";

		public const string OSD_KB_LED_LEVEL4 = "OSD_KB_LED_LEVEL4";
	}

	[StructLayout(LayoutKind.Sequential, Size = 1)]
	public struct Tray
	{
		public const string Tray_DEFAULT = "Tray_DEFAULT";

		public const string Tray_GAMING = "Tray_GAMING";

		public const string Tray_TURBO = "Tray_TURBO";

		public const string Tray_OFFICE = "Tray_OFFICE";
	}

	[StructLayout(LayoutKind.Sequential, Size = 1)]
	public struct RGBLB
	{
		public const string POWER = "POWER";

		public const string RL = "RL";

		public const string GL = "GL";

		public const string BL = "BL";

		public const string RL_DC = "RL_DC";

		public const string GL_DC = "GL_DC";

		public const string BL_DC = "BL_DC";

		public const string COLORFUL = "COLORFUL";

		public const string BREATHINGLIGHT = "BREATHINGLIGHT";

		public const string ACLINESTATUS = "ACLINESTATUS";

		public const string SUPPORT = "SUPPORT";
	}

	[StructLayout(LayoutKind.Sequential, Size = 1)]
	public struct MySetting
	{
		public const string WinKey = "WinKey";

		public const string LightBar = "LightBar";

		public const string UsbCharger = "UsbCharger";

		public const string DGpu = "DGpu";

		public const string OSD = "OSD";

		public const string DisplayFeatureStatus = "DisplayFeatureStatus";

		public const string DisplayMode = "DisplayMode";

		public const string Game_Brightness = "Game_Brightness";

		public const string Game_Red = "Game_Red";

		public const string Game_Green = "Game_Green";

		public const string Game_Blue = "Game_Blue";

		public const string Game_ColorTemp = "Game_ColorTemp";

		public const string Game_Contrast = "Game_Contrast";

		public const string Video_Brightness = "Video_Brightness";

		public const string Video_ColorTemp = "Video_ColorTemp";

		public const string Read_Brightness = "Read_Brightness";

		public const string Read_Blue = "Read_Blue";

		public const string Read_ColorTemp = "Read_ColorTemp";

		public const string Customized_Brightness = "Customized_Brightness";

		public const string Customized_Red = "Customized_Red";

		public const string Customized_Green = "Customized_Green";

		public const string Customized_Blue = "Customized_Blue";

		public const string Customized_ColorTemp = "Customized_ColorTemp";

		public const string Customized_Contrast = "Customized_Contrast";

		public const string SingleColorKBBL = "SingleColorKBBL";

		public const string ColorCalibrationResultCode = "ColorCalibrationResultCode";

		public const string ColorCalibrationStatus = "ColorCalibrationStatus";

		public const string TouchpadToggle = "TouchpadToggle";
	}
}
