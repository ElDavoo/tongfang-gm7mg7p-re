using System.Runtime.InteropServices;

namespace Define;

public class ServCMD
{
	[StructLayout(LayoutKind.Sequential, Size = 1)]
	public struct FAN
	{
		public const string GETSTATUS = "GETSTATUS";

		public const string DEFAULT = "DEFAULT";

		public const string FAN_GAMING_MODE = "FAN_GAMING_MODE";

		public const string FAN_GAMING_MODE_BOOST_ON = "FAN_GAMING_MODE_BOOST_ON";

		public const string FAN_GAMING_MODE_BOOST_OFF = "FAN_GAMING_MODE_BOOST_OFF";

		public const string FAN_TURBO_MODE_BOOST_ON = "FAN_TURBO_MODE_BOOST_ON";

		public const string FAN_TURBO_MODE_BOOST_OFF = "FAN_TURBO_MODE_BOOST_OFF";

		public const string FAN_TURBO_MODE_CPUBOOST_ON = "FAN_TURBO_MODE_CPUBOOST_ON";

		public const string FAN_TURBO_MODE_CPUBOOST_OFF = "FAN_TURBO_MODE_CPUBOOST_OFF";

		public const string FAN_TURBO_MODE = "FAN_TURBO_MODE";

		public const string FAN_OFFICE_MODE = "FAN_OFFICE_MODE";

		public const string FAN_OFFICE_MODE_BASIC = "FAN_OFFICE_MODE_BASIC";

		public const string FAN_OFFICE_MODE_ADVANCED = "FAN_OFFICE_MODE_ADVANCED";

		public const string FAN_OFFICE_MODE_BASIC_L0 = "FAN_OFFICE_MODE_BASIC_L0";

		public const string FAN_OFFICE_MODE_BASIC_L1 = "FAN_OFFICE_MODE_BASIC_L1";

		public const string FAN_OFFICE_MODE_BASIC_L2 = "FAN_OFFICE_MODE_BASIC_L2";

		public const string FAN_OFFICE_MODE_BASIC_L3 = "FAN_OFFICE_MODE_BASIC_L3";

		public const string FAN_OFFICE_MODE_BASIC_L4 = "FAN_OFFICE_MODE_BASIC_L4";

		public const string FAN_OFFICE_MODE_BASIC_L5 = "FAN_OFFICE_MODE_BASIC_L5";

		public const string FAN_OFFICE_MODE_ADVANCED_T1_PWM = "FAN_OFFICE_MODE_ADVANCED_T1_PWM";

		public const string FAN_OFFICE_MODE_ADVANCED_T2_PWM = "FAN_OFFICE_MODE_ADVANCED_T2_PWM";

		public const string FAN_OFFICE_MODE_ADVANCED_T3_PWM = "FAN_OFFICE_MODE_ADVANCED_T3_PWM";

		public const string FAN_OFFICE_MODE_ADVANCED_T4_PWM = "FAN_OFFICE_MODE_ADVANCED_T4_PWM";

		public const string FAN_OFFICE_MODE_ADVANCED_T5_PWM = "FAN_OFFICE_MODE_ADVANCED_T5_PWM";

		public const string FAN_POWER_SETTING_MODE_STD = "FAN_POWER_SETTING_MODE_STD";

		public const string FAN_POWER_SETTING_MODE_ECO = "FAN_POWER_SETTING_MODE_ECO";

		public const string FAN_TURBO_MODE_LV1 = "FAN_TURBO_MODE_LV1";

		public const string FAN_TURBO_MODE_LV2 = "FAN_TURBO_MODE_LV2";

		public const string FAN_TURBO_MODE_LV3 = "FAN_TURBO_MODE_LV3";

		public const string FAN_TURBO_MODE_LV4 = "FAN_TURBO_MODE_LV4";

		public const string FAN_OFFICE_MODE_ADV_MIN_SPEED = "FAN_OFFICE_MODE_ADV_MIN_SPEED";

		public const string FAN_OFFICE_MODE_ADV_MIN_TEMP = "FAN_OFFICE_MODE_ADV_MIN_TEMP";

		public const string FAN_OFFICE_MODE_ADV_EXTRA_SPEED = "FAN_OFFICE_MODE_ADV_EXTRA_SPEED";

		public const string FAN_OFFICE_MODE_ADV_LV1 = "FAN_OFFICE_MODE_ADV_LV1";

		public const string FAN_OFFICE_MODE_ADV_LV2 = "FAN_OFFICE_MODE_ADV_LV2";

		public const string FAN_OFFICE_MODE_ADV_LV3 = "FAN_OFFICE_MODE_ADV_LV3";

		public const string FAN_OFFICE_MODE_ADV_LV4 = "FAN_OFFICE_MODE_ADV_LV4";

		public const string FAN_OFFICE_MODE_ADV_LV1_PWMS = "FAN_OFFICE_MODE_ADV_LV1_PWMS";

		public const string FAN_OFFICE_MODE_ADV_LV2_PWMS = "FAN_OFFICE_MODE_ADV_LV2_PWMS";

		public const string FAN_OFFICE_MODE_ADV_LV3_PWMS = "FAN_OFFICE_MODE_ADV_LV3_PWMS";

		public const string FAN_OFFICE_MODE_ADV_LV4_PWMS = "FAN_OFFICE_MODE_ADV_LV4_PWMS";

		public const string FAN_OFFICE_MODE_ADV_LV4_DEFAULT = "FAN_OFFICE_MODE_ADV_LV4_DEFAULT";

		public const string FAN_OFFICE_MODE_TESTAI_ON = "FAN_OFFICE_MODE_TESTAI_ON";

		public const string FAN_OFFICE_MODE_TESTAI_OFF = "FAN_OFFICE_MODE_TESTAI_OFF";
	}

	[StructLayout(LayoutKind.Sequential, Size = 1)]
	public struct FAN_INTEL
	{
		public const string GETSTATUS = "GETSTATUS";

		public const string DEFAULT = "DEFAULT";

		public const string SYSPOWER_PERFORMANCE_MODE = "SYSPOWER_PERFORMANCE_MODE";

		public const string SYSPOWER_BALANCED_MODE = "SYSPOWER_BALANCED_MODE";

		public const string SYSPOWER_BATTERYSAVER_MODE = "SYSPOWER_BATTERYSAVER_MODE";

		public const string SYSPOWER_PERFORMANCE_SETTING = "SYSPOWER_PERFORMANCE_SETTING";

		public const string SYSPOWER_BALANCED_SETTING = "SYSPOWER_BALANCED_SETTING";

		public const string SYSPOWER_BATTERYSAVER_SETTING = "SYSPOWER_BATTERYSAVER_SETTING";

		public const string BENCHMARK_ON = "BENCHMARK_ON";

		public const string BENCHMARK_OFF = "BENCHMARK_OFF";

		public const string GET_FAN_SPEED_CURVE_SETTING = "GET_FAN_SPEED_CURVE_SETTING";

		public const string SET_FAN_SPEED_CURVE_SETTING = "SET_FAN_SPEED_CURVE_SETTING";

		public const string RESTORE_FAN_SPEED_CURVE_SETTING = "RESTORE_FAN_SPEED_CURVE_SETTING";

		public const string DISABLE_PASSIVECOOLING_MODE_ON = "DISABLE_PASSIVECOOLING_MODE_ON";

		public const string DISABLE_PASSIVECOOLING_MODE_OFF = "DISABLE_PASSIVECOOLING_MODE_OFF";

		public const string BATTERY_CHARGINGLIMIT_SETTING = "BATTERY_CHARGINGLIMIT_SETTING";
	}

	[StructLayout(LayoutKind.Sequential, Size = 1)]
	public struct RGBLB
	{
		public const string GETSTATUS = "GETSTATUS";

		public const string DEFAULT = "DEFAULT";

		public const string POWER_ON = "POWER_ON";

		public const string POWER_OFF = "POWER_OFF";

		public const string RL = "RL";

		public const string GL = "GL";

		public const string BL = "BL";

		public const string RL_DC = "RL_DC";

		public const string GL_DC = "GL_DC";

		public const string BL_DC = "BL_DC";

		public const string COLORFUL_ON = "COLORFUL_ON";

		public const string COLORFUL_OFF = "COLORFUL_OFF";

		public const string BREATHINGLIGHT = "BREATHINGLIGHT";
	}

	[StructLayout(LayoutKind.Sequential, Size = 1)]
	public struct RGBLB_INTEL
	{
		public const string GETSTATUS = "GETSTATUS";

		public const string DEFAULT = "DEFAULT";

		public const string POWER_ON = "POWER_ON";

		public const string POWER_OFF = "POWER_OFF";

		public const string RL = "RL";

		public const string GL = "GL";

		public const string BL = "BL";

		public const string RL_DC = "RL_DC";

		public const string GL_DC = "GL_DC";

		public const string BL_DC = "BL_DC";

		public const string COLORFUL_ON = "COLORFUL_ON";

		public const string COLORFUL_OFF = "COLORFUL_OFF";

		public const string BREATHINGLIGHT = "BREATHINGLIGHT";

		public const string COPY_AC_SETTINGS = "COPY_AC_SETTINGS";
	}

	[StructLayout(LayoutKind.Sequential, Size = 1)]
	public struct MySetting
	{
		public const string WIFI_ON = "WIFI_ON";

		public const string WIFI_OFF = "WIFI_OFF";

		public const string BT_ON = "BT_ON";

		public const string BT_OFF = "BT_OFF";

		public const string WEBCAM_ON = "WEBCAM_ON";

		public const string WEBCAM_OFF = "WEBCAM_OFF";

		public const string GPU_POWERSAVEINGMODE = "GPU_POWERSAVEINGMODE";

		public const string GPU_HZSETTING = "GPU_HZSETTING";

		public const string KEYBOARDINGMAPPING_ENABLE = "KEYBOARDINGMAPPING_ENABLE";

		public const string KEYBOARDINGMAPPING_DISABLE = "KEYBOARDINGMAPPING_DISABLE";

		public const string KEYBOARD_LIGHTBAR_TIMER_ON = "KEYBOARD_LIGHTBAR_TIMER_ON";

		public const string KEYBOARD_LIGHTBAR_TIMER_OFF = "KEYBOARD_LIGHTBAR_TIMER_OFF";

		public const string DISPLAY_POWER_OFF = "DISPLAY_POWER_OFF";

		public const string GETSTATUS = "GETSTATUS";

		public const string DISPLAY_FEATURE_STATUS_OFF = "DISPLAY_FEATURE_STATUS_OFF";

		public const string DISPLAY_FEATURE_STATUS_ON = "DISPLAY_FEATURE_STATUS_ON";

		public const string DISPLAY_STANDARD_MODE = "DISPLAY_STANDARD_MODE";

		public const string DISPLAY_GAMING_MODE = "DISPLAY_GAMING_MODE";

		public const string DISPLAY_VIDEO_MODE = "DISPLAY_VIDEO_MODE";

		public const string DISPLAY_READ_MODE = "DISPLAY_READ_MODE";

		public const string DISPLAY_CUSTOMIZED_MODE = "DISPLAY_CUSTOMIZED_MODE";

		public const string DISPLAY_GAMING_MODE_VALUE = "DISPLAY_GAMING_MODE_VALUE";

		public const string DISPLAY_VIDEO_MODE_VALUE = "DISPLAY_VIDEO_MODE_VALUE";

		public const string DISPLAY_READ_MODE_VALUE = "DISPLAY_READ_MODE_VALUE";

		public const string DISPLAY_CUSTOMIZED_MODE_VALUE = "DISPLAY_CUSTOMIZED_MODE_VALUE";

		public const string DISPLAY_GAMING_MODE_RECOVERY = "DISPLAY_GAMING_MODE_RECOVERY";

		public const string DISPLAY_VIDEO_MODE_RECOVERY = "DISPLAY_VIDEO_MODE_RECOVERY";

		public const string DISPLAY_READ_MODE_RECOVERY = "DISPLAY_READ_MODE_RECOVERY";

		public const string DISPLAY_CUSTOMIZED_MODE_RECOVERY = "DISPLAY_CUSTOMIZED_MODE_RECOVERY";

		public const string OSD_HIDDEN_ON = "OSD_HIDDEN_ON";

		public const string OSD_HIDDEN_OFF = "OSD_HIDDEN_OFF";

		public const string NV_CTRL_PANEL_AUTOSELECT = "NV_CTRL_PANEL_AUTOSELECT";

		public const string NV_CTRL_PANEL_HIGHPERFORMANCE = "NV_CTRL_PANEL_HIGHPERFORMANCE";

		public const string WINKEY_LOCK = "WINKEY_LOCK";

		public const string WINKEY_UNLOCK = "WINKEY_UNLOCK";

		public const string WINKEY_TRIGGER = "WINKEY_TRIGGER";

		public const string LIGHT_BAR_TRIGGER = "LIGHT_BAR_TRIGGER";

		public const string USB_CHARGER_ON = "USB_CHARGER_ON";

		public const string USB_CHARGER_OFF = "USB_CHARGER_OFF";

		public const string WINKEY_STATUS_LOCK = "WINKEY_STATUS_LOCK";

		public const string WINKEY_STATUS_UNLOCK = "WINKEY_STATUS_UNLOCK";

		public const string LIGHTBAR_STATUS_ON = "LIGHTBAR_STATUS_ON";

		public const string LIGHTBAR_STATUS_OFF = "LIGHTBAR_STATUS_OFF";

		public const string CPU_SILENT_MODE_STATUS_ON = "CPU_SILENT_MODE_STATUS_ON";

		public const string CPU_SILENT_MODE_STATUS_OFF = "CPU_SILENT_MODE_STATUS_OFF";

		public const string USB_CHARGER_STATUS_ON = "USB_CHARGER_STATUS_ON";

		public const string USB_CHARGER_STATUS_OFF = "USB_CHARGER_STATUS_OFF";

		public const string POWER_PLAN_GAMING = "POWER_PLAN_GAMING";

		public const string POWER_PLAN_HIPERFORMANCE = "POWER_PLAN_HIPERFORMANCE";

		public const string POWER_PLAN_BALANCED = "POWER_PLAN_BALANCED";

		public const string POWER_PLAN_POWERSAVING = "POWER_PLAN_POWERSAVING";

		public const string POWER_PLAN_DELETE = "POWER_PLAN_DELETE";

		public const string GAMER_ON = "GAMER_ON";

		public const string GAMER_OFF = "GAMER_OFF";

		public const string UNINSTALL_MYSETTING = "UNINSTALL_MYSETTING";

		public const string SINGLE_COLOR_KBBL_STATUS_ON = "SINGLE_COLOR_KBBL_STATUS_ON";

		public const string SINGLE_COLOR_KBBL_STATUS_OFF = "SINGLE_COLOR_KBBL_STATUS_OFF";

		public const string ICCPROFILESETING = "ICCPROFILESETING";

		public const string COLOR_CALIBRATION_ON = "COLOR_CALIBRATION_ON";

		public const string COLOR_CALIBRATION_OFF = "COLOR_CALIBRATION_OFF";

		public const string TOUCHPAD_ON = "TOUCHPAD_ON";

		public const string TOUCHPAD_OFF = "TOUCHPAD_OFF";

		public const string TOUCHPAD_LED_ON = "TOUCHPAD_LED_ON";

		public const string TOUCHPAD_LED_OFF = "TOUCHPAD_LED_OFF";

		public const string TOUCHPAD_TOGGLE_ON = "TOUCHPAD_TOGGLE_ON";

		public const string TOUCHPAD_TOGGLE_OFF = "TOUCHPAD_TOGGLE_OFF";

		public const string ACRECOVERY_TOGGLE_ON = "ACRECOVERY_TOGGLE_ON";

		public const string ACRECOVERY_TOGGLE_OFF = "ACRECOVERY_TOGGLE_OFF";

		public const string FN_WITH1_HOTKEY_TOGGLE_ON = "FN_WITH1_HOTKEY_TOGGLE_ON";

		public const string FN_WITH1_HOTKEY_TOGGLE_OFF = "FN_WITH1_HOTKEY_TOGGLE_OFF";

		public const string DGPU_DIRECT_CONNECT_TOGGLE_ON = "DGPU_DIRECT_CONNECT_TOGGLE_ON";

		public const string DGPU_DIRECT_CONNECT_TOGGLE_OFF = "DGPU_DIRECT_CONNECT_TOGGLE_OFF";

		public const string FNKEY_LOCK = "FNKEY_LOCK";

		public const string FNKEY_UNLOCK = "FNKEY_UNLOCK";

		public const string NUMPAD_LOCK = "NUMPAD_LOCK";

		public const string NUMPAD_UNLOCK = "NUMPAD_UNLOCK";

		public const string SETSCREENBRIGHTNESS = "SETSCREENBRIGHTNESS";
	}

	[StructLayout(LayoutKind.Sequential, Size = 1)]
	public struct MyEC
	{
		public const string WRITE = "WRITE";

		public const string READ = "READ";
	}

	[StructLayout(LayoutKind.Sequential, Size = 1)]
	public struct CustomizeInfoCMD
	{
		public const string GETSETUPINFO = "GETSETUPINFO";

		public const string GETSUPPORT = "GETSUPPORT";
	}

	[StructLayout(LayoutKind.Sequential, Size = 1)]
	public struct Tray
	{
		public const string Lang_GET = "GET";

		public const string Lang_SET = "SET";

		public const string EnableTray = "EnableTray";
	}

	[StructLayout(LayoutKind.Sequential, Size = 1)]
	public struct GamingCenter_WPF
	{
		public const string System_OFF = "System_OFF";
	}
}
