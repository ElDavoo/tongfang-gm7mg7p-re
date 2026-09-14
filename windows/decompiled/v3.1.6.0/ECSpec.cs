using System;

namespace Define
{
	internal static class ECSpec
	{
		[Flags]
		public enum ByteFlag
		{
			Bit0 = 1,
			Bit1 = 2,
			Bit2 = 4,
			Bit3 = 8,
			Bit4 = 0x10,
			Bit5 = 0x20,
			Bit6 = 0x40,
			Bit7 = 0x80
		}

		[Flags]
		public enum MyFanCTLByteFlag
		{
			Normal_Mode = 0,
			Turbo_Mode = 0x10,
			FanBoost_Mode = 0x40,
			User_Fan_Mode = 0x80,
			User_Fan_Level1 = 0x81,
			User_Fan_Level2 = 0x82,
			User_Fan_Level3 = 0x83,
			User_Fan_Level4 = 0x84,
			User_Fan_Level5 = 0x85,
			User_Fan_HiMode = 0xA0
		}

		[Flags]
		public enum TriggerByteFlag
		{
			WinLock_Trigger = 1,
			LightBar_Trigger = 2,
			FanBoost_Trigger = 4,
			SilentMode_Trigger = 8,
			USBCharger_Trigger = 0x10,
			RGBKeybaord_Trigger = 0x20,
			RGBLogo_Trigger = 0x40,
			RGBKeybaordWelcome_Trigger = 0x80
		}

		[Flags]
		public enum SupportByteOneFlag
		{
			AirplaneMode = 1,
			GPSSwitch = 2,
			OverClock = 4,
			MacroKey = 8,
			ShortCutKey = 0x10,
			WinLockKey = 0x20,
			LightBar = 0x40,
			FanBoost = 0x80
		}

		[Flags]
		public enum SupportByteTwoFlag
		{
			SilentMode = 1,
			USBChargerMode = 2,
			RGBKeyBoard = 4,
			MyBat = 0x40
		}

		[Flags]
		public enum SupportByteThreeFlag
		{
			FullZone = 1,
			FourZone = 2,
			FourZoneReady = 4
		}

		[Flags]
		public enum StatusByteOneFlag
		{
			WinLock = 1,
			BreathLed = 2,
			FanBoost = 4,
			MacroKey = 8,
			MyBatPowerBat = 0x10
		}

		[Flags]
		public enum RGBLightBarCtrlByteFlag
		{
			ApExit = 1,
			PowerSaveMode = 2,
			Switch_S0 = 4,
			Switch_S3 = 8,
			LB10NoKey = 0x10,
			LB10KeyPress = 0x20,
			Switch_Breath_MordenStandby = 0x40,
			WelcomeLightMode = 0x80
		}

		[Flags]
		public enum MyFan2SpeedByteFlag
		{
			Speed00 = 0,
			Speed30 = 0x3C,
			Speed35 = 0x46,
			Speed40 = 0x50,
			Speed45 = 0x5A,
			Speed50 = 0x64,
			Speed55 = 0x6E,
			Speed60 = 0x78,
			Speed70 = 0x8C
		}

		[Flags]
		public enum RGBLightbarControlByteFlag
		{
			AP_Exist = 0,
			PowerSaveMode = 2,
			S0_Switch = 4,
			S3_Switch = 8,
			Welcome = 0x80
		}

		public const ushort BIOSFuncReg = 1142;

		public const ushort ecPowSource = 1168;

		public const ushort ADDR_BIOS_INFO_3_BYTE = 1183;

		public const ushort ecBt1Temperature = 1186;

		public const ushort ecBt1RSOC = 1195;

		public const uint FAN_MODE_NORMAL = 0u;

		public const uint FAN_MODE_BOOST = 1u;

		public const uint FAN_MODE_CUSTOMIZE = 2u;

		public const uint FAN_CUSTOMIZEMODE_NORMAL = 0u;

		public const uint FAN_CUSTOMIZEMODE_BASIC = 1u;

		public const uint FAN_CUSTOMIZEMODE_HIGH = 2u;

		public const uint FAN_GAMING_MODE = 0u;

		public const uint FAN_OFFICE_MODE = 1u;

		public const uint FAN_TURBO_MODE = 2u;

		public const uint FAN_OFFICE_MODE_BASIC = 1u;

		public const uint FAN_OFFICE_MODE_ADVANCED = 2u;

		public const uint FAN_GAMING_MODE_SMART = 1u;

		public const uint FAN_GAMING_MODE_PERFENHANCED = 2u;

		public const uint POWER_SETTING_MODE_ECO = 1u;

		public const uint POWER_SETTING_MODE_STD = 2u;

		public const uint FAN_LEVEL_ZERO = 0u;

		public const uint FAN_LEVEL_ONE = 1u;

		public const uint FAN_LEVEL_TWO = 2u;

		public const uint FAN_LEVEL_THREE = 3u;

		public const uint FAN_LEVEL_FOUR = 4u;

		public const uint FAN_LEVEL_FIVE = 5u;

		public const uint TURBO_MODE_1 = 1u;

		public const uint TURBO_MODE_2 = 2u;

		public const uint TURBO_MODE_3 = 3u;

		public const uint TURBO_MODE_4 = 4u;

		public const uint TURBO_MODE_MIN = 1u;

		public const uint TURBO_MODE_MAX = 4u;

		public const uint TURBO_MODE_DEFAULT = 2u;

		public const uint TURBO_MODE_CPUBOOST = 0u;

		public const uint QKEY_MODESWITCH = 0u;

		public const uint QKEY_FANBOOST = 1u;

		public const ushort ADDR_EC_BIF_DC_BYTE1 = 1026;

		public const ushort ADDR_EC_BIF_DC_BYTE2 = 1027;

		public const ushort ADDR_EC_BIF_DV_BYTE1 = 1032;

		public const ushort ADDR_EC_BIF_DV_BYTE2 = 1033;

		public const ushort ADDR_EC_BST_BPR_BYTE1 = 1076;

		public const ushort ADDR_EC_BST_BPR_BYTE2 = 1077;

		public const ushort ADDR_EC_BST_BRC_BYTE1 = 1078;

		public const ushort ADDR_EC_BST_BRC_BYTE2 = 1079;

		public const ushort ADDR_EC_BST_BPV_BYTE1 = 1080;

		public const ushort ADDR_EC_BST_BPV_BYTE2 = 1081;

		public const ushort ADDR_EC_BT1CycleCount_BYTE1 = 1190;

		public const ushort ADDR_EC_BT1CycleCount_BYTE2 = 1191;

		public const ushort ADDR_EC_MAIN_FAN_RPM_BYTE1 = 1124;

		public const ushort ADDR_EC_MAIN_FAN_RPM_BYTE2 = 1125;

		public const ushort ADDR_EC_BIOS_INFO5 = 1126;

		public const ushort ADDR_EC_SECOND_FAN_RPM_BYTE1 = 1132;

		public const ushort ADDR_EC_SECOND_FAN_RPM_BYTE2 = 1131;

		public const ushort ADDR_MAFAN_CONTROL_BYTE = 1873;

		public const ushort ADDR_CPU_VRM_CURRENT_LIMIT_BYTE = 1875;

		public const ushort ADDR_CPU_VRM_MAXI_CURRENT_LIMIT_BYTE = 1876;

		public const ushort ADDR_EC_MAIN_FAN_L_DUTY_BYTE = 1883;

		public const ushort ADDR_EC_MAIN_FAN_R_DUTY_BYTE = 1884;

		public const ushort ADDR_TRIGGER_BYTE2 = 1885;

		public const ushort ADDR_SUPPORT_BYTE1 = 1893;

		public const ushort ADDR_SUPPORT_BYTE2 = 1894;

		public const ushort ADDR_PROJECT_ID_BYTE = 1856;

		public const ushort ADDR_AP_OEM_BYTE = 1857;

		public const ushort ADDR_SUPPORT_BYTE5 = 1858;

		public const ushort ADDR_MYFAN2_L1_PWM = 1859;

		public const ushort ADDR_MYFAN2_L2_PWM = 1860;

		public const ushort ADDR_MYFAN2_L3_PWM = 1861;

		public const ushort ADDR_MYFAN2_L4_PWM = 1862;

		public const ushort ADDR_MYFAN2_L5_PWM = 1863;

		public const ushort ADDR_ConfigurableTGP_DynamicBoost_CTRL_BYTE = 1859;

		public const ushort ADDR_ConfigurableTGP_VALUE = 1860;

		public const ushort ADDR_DynamicBoost_TotalProcessingPowerTarget_VALUE = 1861;

		public const ushort ADDR_DynamicBoost_MaxinumTGP_VALUE = 1862;

		public const ushort ADDR_L1_PWM_DEFAULT_MYFAN2 = 1929;

		public const ushort ADDR_L2_PWM_DEFAULT_MYFAN2 = 1930;

		public const ushort ADDR_L3_PWM_DEFAULT_MYFAN2 = 1931;

		public const ushort ADDR_L4_PWM_DEFAULT_MYFAN2 = 1932;

		public const ushort ADDR_L5_PWM_DEFAULT_MYFAN2 = 1933;

		public const ushort ADDR_BIOS_OEM_BYTE = 1870;

		public const ushort ADDR_BIOS_OEM_BYTE2 = 1922;

		public const ushort ADDR_GAMING_PL1_DEFAULT_VALUE = 1840;

		public const ushort ADDR_GAMING_PL2_DEFAULT_VALUE = 1841;

		public const ushort ADDR_GAMING_PL4_DEFAULT_VALUE = 1842;

		public const ushort ADDR_GAMING_D_DEFAULT_VALUE = 1843;

		public const ushort ADDR_OFFICE_PL1_DEFAULT_VALUE = 1844;

		public const ushort ADDR_OFFICE_PL2_DEFAULT_VALUE = 1845;

		public const ushort ADDR_OFFICE_PL4_DEFAULT_VALUE = 1846;

		public const ushort ADDR_OFFICE_D_DEFAULT_VALUE = 1847;

		public const ushort ADDR_PL1_SETTING_VALUE = 1923;

		public const ushort ADDR_PL2_SETTING_VALUE = 1924;

		public const ushort ADDR_PL4_SETTING_VALUE = 1925;

		public const ushort ADDR_L1_PWM_DEFAULT_MYFAN3 = 1926;

		public const ushort ADDR_L2_PWM_DEFAULT_MYFAN3 = 1927;

		public const ushort ADDR_L3_PWM_DEFAULT_MYFAN3 = 1928;

		public const ushort ADDR_L4_PWM_DEFAULT_MYFAN3 = 1929;

		public const ushort ADDR_L5_PWM_DEFAULT_MYFAN3 = 1930;

		public const ushort ADDR_SINGLEKBL_ENABLE = 1932;

		public const ushort ADDR_SINGLEKBL_SUPPORTPOWER = 1934;

		public const ushort ADDR_MYFAN3_CPU_TAU = 1848;

		public const ushort ADDR_TRIGGER_BYTE = 1895;

		public const ushort ADDR_STAUTS_BYTE = 1896;

		public const ushort ADDR_LIGHTBAR_CONTROL_BYTE = 1864;

		public const ushort ADDR_REDBAR_CONTROL_BYTE = 1865;

		public const ushort ADDR_GREENBAR_CONTROL_BYTE = 1866;

		public const ushort ADDR_BLUEBAR_CONTROL_BYTE = 1867;

		public const ushort ADDR_OEMSERVICE_PROJECT_ID_BYTE = 1868;

		public const ushort ADDR_BATTERY_ALERT_BYTE = 1172;

		public const ushort ADDR_FAN_ALERT_BYTE = 1857;

		public const ushort ADDR_SILENTMODE_STATUS_BYTE = 1115;

		public const ushort ADDR_MYFAN3_GPU_SETTING = 1931;

		public const ushort ADDR_AP_OEM_BYTE2 = 1932;

		public const ushort ADDR_AP_OEM_BYTE5 = 1989;

		public const ushort ADDR_AP_OEM_BYTE6 = 1990;

		public const ushort ADDR_SUPPORT_BYTE6 = 1934;

		public const ushort ADDR_MYFANI_MIN_SPEED = 1950;

		public const ushort ADDR_MYFANI_MIN_TEMP = 1951;

		public const ushort ADDR_MYFANI_EXTRA_SPEED = 1952;

		public const ushort ADDR_BIOS_OEM_BYTE3 = 1955;

		public const ushort ADDR_AP_BIOS_BYTE = 1956;

		public const ushort ADDR_AP_OEM_BYTE3 = 1957;

		public const ushort ADDR_AP_OEM_BYTE4 = 1958;

		public const ushort ADDR_BATTERYSAVER_PL1_DEFAULT_VALUE = 1959;

		public const ushort ADDR_BATTERYSAVER_PL2_DEFAULT_VALUE = 1960;

		public const ushort ADDR_BATTERYSAVER_PL4_DEFAULT_VALUE = 1961;

		public const ushort ADDR_BATTERYSAVER_D_DEFAULT_VALUE = 1962;

		public const ushort ADDR_MyFanCCI_Mode_Index = 1963;

		public const ushort ADDR_MyFanCCI_Mode_Profile1 = 1968;

		public const ushort ADDR_MyFanCCI_Mode_Profile2 = 1969;

		public const ushort ADDR_MyFanCCI_Mode_Profile3 = 1970;

		public const ushort ADDR_BATTERY_CHARGE_LIMIT_UP = 1977;

		public const ushort ADDR_COMPLEX_POWER_STATUS = 1996;

		public const ushort ADDR_BATTERY_CHARGE_LIMIT_DOWN = 2000;

		public const ushort ADDR_ModuleID = 2003;

		public const ushort ADDR_GAMING_TCC_OFFSET_DEFAULT_VALUE = 2008;

		public const ushort ADDR_OFFICE_TCC_OFFSET_DEFAULT_VALUE = 2009;

		public const ushort ADDR_TURBO_TCC_OFFSET_DEFAULT_VALUE = 2010;

		public const ushort ADDR_CHANGE_PORT_ID_WKD = 2043;

		public const ushort OSD_CAPSLOCK = 1;

		public const ushort OSD_NUMLOCK = 2;

		public const ushort OSD_SROLLOCK = 3;

		public const ushort OSD_TPON = 4;

		public const ushort OSD_TPOFF = 5;

		public const ushort OSD_SILENTON = 6;

		public const ushort OSD_SILENTOFF = 7;

		public const ushort OSD_WLANON = 8;

		public const ushort OSD_WLANOFF = 9;

		public const ushort OSD_WINMAXON = 10;

		public const ushort OSD_WINMAXOFF = 11;

		public const ushort OSD_BTON = 12;

		public const ushort OSD_BTOFF = 13;

		public const ushort OSD_RFON = 14;

		public const ushort OSD_RFOFF = 15;

		public const ushort OSD_3GON = 16;

		public const ushort OSD_3GOFF = 17;

		public const ushort OSD_WEBCAMON = 18;

		public const ushort OSD_WEBCAMOFF = 19;

		public const ushort OSD_BRIGHTNESSUP = 20;

		public const ushort OSD_BRIGHTNESSDOWN = 21;

		public const ushort OSD_RADIOON = 26;

		public const ushort OSD_RADIOOFF = 27;

		public const ushort OSD_POWERSAVEON = 49;

		public const ushort OSD_POWERSAVEOFF = 50;

		public const ushort OSD_MENU = 52;

		public const ushort OSD_MUTE = 53;

		public const ushort OSD_VOLUMEDOWN = 54;

		public const ushort OSD_VOLUMEUP = 55;

		public const ushort OSD_OSD_MENU_2 = 56;

		public const ushort OSD_BREATH_LED_ON = 57;

		public const ushort OSD_BREATH_LED_OFF = 58;

		public const ushort OSD_KB_LED_LEVEL0 = 59;

		public const ushort OSD_KB_LED_LEVEL1 = 60;

		public const ushort OSD_KB_LED_LEVEL2 = 61;

		public const ushort OSD_KB_LED_LEVEL3 = 62;

		public const ushort OSD_KB_LED_LEVEL4 = 63;

		public const ushort OSD_WINKEY_LOCK = 64;

		public const ushort OSD_WINKEY_UNLOCK = 65;

		public const ushort OSD_MENU_JP = 66;

		public const ushort OSD_CAMERAON = 144;

		public const ushort OSD_CAMERAOFF = 145;

		public const ushort OSD_AIRPLANEMODE = 164;

		public const ushort OSD_FANBOOST_UPDATE = 167;

		public const ushort OSD_LCD_SW = 169;

		public const ushort TimAP_MyFanOT = 170;

		public const ushort OSD_MyBat_ACUpdate = 171;

		public const ushort TimAP_MyBat_HPOff = 172;

		public const ushort TimAP_ReleaseUSM = 173;

		public const ushort OSD_Battery_Alert = 174;

		public const ushort TimAP_HaierLB_Sw = 175;

		public const ushort WinKey_Update = 165;

		public const ushort OSD_FanModeSwitch = 176;

		public const ushort BacklightLevelChange = 179;

		public const ushort BacklightPowerChange = 180;

		public const ushort TimAP_MicMute_Sw = 183;

		public const ushort OSD_FnChange = 184;

		public const ushort CallAP = 186;

		public const ushort TimAP_HighTemp = 187;

		public const ushort TimAP_WhisperUpdate = 188;

		public const int OS_VK_CAPITAL = 20;

		public const int OS_VK_NUMLOCK = 144;

		public const int OS_VK_SCROLL = 145;

		public const ushort Light_ChinaMode = 1894;

		public const ushort Light_SetToChinaMode = 1922;

		public const uint APP_Normal_Mode = 0u;

		public const uint APP_ImageProjectionLight_Mode = 1u;

		public const uint APP_LightBar_Mode = 2u;

		public const uint LEVEL_ZERO = 0u;

		public const uint LEVEL_ONE = 1u;

		public const uint LEVEL_TWO = 2u;

		public const uint LEVEL_THREE = 3u;

		public const uint LEVEL_FOUR = 4u;

		public const uint LEVEL_FIVE = 5u;

		public const uint LEVEL_SIX = 6u;

		public const uint LEVEL_SEVEN = 7u;

		public const uint LEVEL_EIGHT = 8u;

		public const uint LEVEL_NINE = 9u;

		public const uint LEVEL_MAX = 100u;

		public const int Animation_OFF = 0;

		public const int Animation_ON = 1;

		public const byte Enable_RGB_Music = 254;

		public const byte Disable_RGB_Music = 0;

		public const ushort ADDR_RGBKB_LEVEL_R = 1897;

		public const ushort ADDR_RGBKB_LEVEL_G = 1898;

		public const ushort ADDR_RGBKB_LEVEL_B = 1899;

		public const ushort ADDR_RGBKB_LEVEL_DEFAULT_R = 1900;

		public const ushort ADDR_RGBKB_LEVEL_DEFAULT_G = 1901;

		public const ushort ADDR_RGBKB_LEVEL_DEFAULT_B = 1902;

		public const ushort ADDR_RGBKB_MUSIC_NO = 1903;
	}
}
