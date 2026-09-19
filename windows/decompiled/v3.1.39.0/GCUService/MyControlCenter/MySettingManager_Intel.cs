using System;
using System.Reflection;
using System.Text;
using System.Windows.Forms;
using GCUService.MySetting.Muter;
using Microsoft.Win32;
using MyControlCenter.MySetting.DisplayFeature;
using MyECIO;
using Utility;
using Workaround;

namespace MyControlCenter;

public class MySettingManager_Intel : MySettingManager
{
	private string m_className = "[" + MethodBase.GetCurrentMethod().DeclaringType.Name + "] ";

	private int m_nCustomizeTarget = 1;

	private KeyboardCloseTimer keyboardCloseTimer = KeyboardCloseTimer.CreateInstance;

	private MySettingView m_View = new MySettingView();

	private string m_sRegistryPath = "\\OEM\\GamingCenter2\\MySetting";

	private static int m_sCloseTimer;

	private static bool m_EnabbleDone;

	private MyEcCtrl EcCtrl = MyEcCtrl.Instance;

	public override void Enable()
	{
		LogCtrl.Write(m_className + "[Enable] Write 0x0766 Support Byte");
		Write_Support_BYTE();
		LogCtrl.Write(m_className + "[Enable] LoadRegistry");
		LoadRegistry();
		LogCtrl.Write(m_className + "[Enable] Init");
		Init();
		m_EnabbleDone = true;
	}

	public override void Disable()
	{
	}

	public override async void Receive(byte[] data)
	{
		dynamic val = await Json.ToObjectAsync<object>(Encoding.UTF8.GetString(data));
		string text = val["Action"];
		LogCtrl.Write("---------------" + LogCtrl.GetTime() + "---------------");
		LogCtrl.Write(m_className + "[Recieve] msg = " + text);
		switch (text)
		{
		case "KEYBOARD_LIGHTBAR_TIMER_ON":
		{
			KeyboardCloseTimer.CreateInstance.GetStartMoniter();
			KeyboardCloseTimer.CreateInstance.HookEvent();
			int num = 0;
			if (val["Mins"] != null)
			{
				num = Convert.ToInt32(val["Mins"]);
			}
			else if (val["Seconds"] != null)
			{
				num = Convert.ToInt32(val["Seconds"]);
			}
			KeyboardCloseTimer.CreateInstance.SetKeyboardCloseTime(num);
			UserSetCloseTimer(num);
			break;
		}
		case "KEYBOARD_LIGHTBAR_TIMER_OFF":
			KeyboardCloseTimer.CreateInstance.GetStartMoniter();
			KeyboardCloseTimer.CreateInstance.UnHookEvent();
			KeyboardCloseTimer.CreateInstance.DisableCloseTimer();
			UserSetCloseTimer(0);
			break;
		case "DISPLAY_POWER_OFF":
			DisplaySwitch.SetDisplayState(2);
			MouseEvent.Set(0, -25);
			break;
		case "GETSTATUS":
			UpdateStatusToClient(1);
			break;
		case "DISPLAY_FEATURE_STATUS_OFF":
			UserSetDisplayFeatureStatus(0);
			UpdateStatusToClient(1);
			break;
		case "DISPLAY_FEATURE_STATUS_ON":
			UserSetDisplayFeatureStatus(1);
			UpdateStatusToClient(1);
			break;
		case "DISPLAY_STANDARD_MODE":
		case "DISPLAY_GAMING_MODE":
		case "DISPLAY_VIDEO_MODE":
		case "DISPLAY_READ_MODE":
		case "DISPLAY_CUSTOMIZED_MODE":
			UserSetDisplayMode(text);
			break;
		case "DISPLAY_GAMING_MODE_VALUE":
			UserSetDisplayGamingModeValue(val);
			break;
		case "DISPLAY_VIDEO_MODE_VALUE":
			UserSetDisplayVideoModeValue(val);
			break;
		case "DISPLAY_READ_MODE_VALUE":
			UserSetDisplayReadModeValue(val);
			break;
		case "DISPLAY_CUSTOMIZED_MODE_VALUE":
			UserSetDisplayCustomizedModeValue(val);
			break;
		case "DISPLAY_GAMING_MODE_RECOVERY":
		case "DISPLAY_VIDEO_MODE_RECOVERY":
		case "DISPLAY_READ_MODE_RECOVERY":
		case "DISPLAY_CUSTOMIZED_MODE_RECOVERY":
			UserRcoveryDisplayModeValue(text);
			UpdateStatusToClient(1);
			break;
		case "OSD_HIDDEN_ON":
			UserSetOsdHidden(1);
			break;
		case "OSD_HIDDEN_OFF":
			UserSetOsdHidden(0);
			break;
		case "WINKEY_LOCK":
			UserSetWinKey(1);
			break;
		case "WINKEY_UNLOCK":
			UserSetWinKey(0);
			break;
		case "TOUCHPAD_LED_ON":
			UserSetTouchPadLedStatus(1);
			App.m_Osd.SendTpOsdStatusToClient(1u);
			break;
		case "TOUCHPAD_LED_OFF":
			UserSetTouchPadLedStatus(0);
			App.m_Osd.SendTpOsdStatusToClient(0u);
			break;
		case "FNKEY_LOCK":
			UserSetFnKey(1);
			break;
		case "FNKEY_UNLOCK":
			UserSetFnKey(0);
			break;
		case "NUMPAD_LOCK":
			UserSetNumpad(1);
			break;
		case "NUMPAD_UNLOCK":
			UserSetNumpad(0);
			break;
		}
	}

	public override void UpdateStatusToClient(int run)
	{
		if (m_EnabbleDone && run != 0)
		{
			dynamic val = new
			{
				WinKey = MySettingParams_Intel.sWinKey_Status.ToString(),
				OSD = MySettingParams_Intel.sOSD_Status.ToString(),
				DisplayFeatureStatus = MySettingParams_Intel.sDisplayFeatureStatus.ToString(),
				DisplayMode = MySettingParams_Intel.sDisplayMode.ToString(),
				GamingBrightness = DisplayFeatureCtrl.Instance.GamingModePara().sBrightness.ToString(),
				GamingRed = DisplayFeatureCtrl.Instance.GamingModePara().sRed.ToString(),
				GamingGreen = DisplayFeatureCtrl.Instance.GamingModePara().sGreen.ToString(),
				GamingBlue = DisplayFeatureCtrl.Instance.GamingModePara().sBlue.ToString(),
				GamingColorTemp = DisplayFeatureCtrl.Instance.GamingModePara().sColorTemp.ToString(),
				GamingContrast = DisplayFeatureCtrl.Instance.GamingModePara().sContrast.ToString(),
				VideoBrightness = DisplayFeatureCtrl.Instance.VideoModePara().sBrightness.ToString(),
				VideoColorTemp = DisplayFeatureCtrl.Instance.VideoModePara().sColorTemp.ToString(),
				ReadBrightness = DisplayFeatureCtrl.Instance.ReadModePara().sBrightness.ToString(),
				ReadBlue = DisplayFeatureCtrl.Instance.ReadModePara().sBlue.ToString(),
				ReadColorTemp = DisplayFeatureCtrl.Instance.ReadModePara().sColorTemp.ToString(),
				CutomizedBrightness = DisplayFeatureCtrl.Instance.CutomizedModePara().sBrightness.ToString(),
				CutomizedRed = DisplayFeatureCtrl.Instance.CutomizedModePara().sRed.ToString(),
				CutomizedGreen = DisplayFeatureCtrl.Instance.CutomizedModePara().sGreen.ToString(),
				CutomizedBlue = DisplayFeatureCtrl.Instance.CutomizedModePara().sBlue.ToString(),
				CutomizedColorTemp = DisplayFeatureCtrl.Instance.CutomizedModePara().sColorTemp.ToString(),
				CutomizedContrast = DisplayFeatureCtrl.Instance.CutomizedModePara().sContrast.ToString(),
				CloseTimer = MySettingParams_Intel.sCloseTimer.ToString(),
				NumPad = MySettingParams_Intel.sNumPad_Status.ToString(),
				FnKey = MySettingParams_Intel.sFnKey_Status.ToString()
			};
			m_View.SendStatusToClient(val);
		}
	}

	public override void UpdateWinKeyStatus(int mode)
	{
		if (mode == 1)
		{
			MySettingParams_Intel.sWinKey_Status = "WINKEY_STATUS_LOCK";
		}
		else
		{
			MySettingParams_Intel.sWinKey_Status = "WINKEY_STATUS_UNLOCK";
		}
	}

	private void UserSetCloseTimer(int seconds)
	{
		SetCloseTimer(seconds);
	}

	private void UserSetDisplayFeatureStatus(int status)
	{
		if (status == 0)
		{
			SetDisplayFeatureStatus(-1);
		}
		else
		{
			SetDisplayFeatureStatus(0);
			LoadDisplayFeaturesRegistry();
		}
		SetDisplayMode();
		LogCtrl.Write(m_className + $"[UserSetDisplayFeatureStatus] DisplayFeatureStatus:{status}");
	}

	private void UserSetDisplayMode(string mode)
	{
		switch (mode)
		{
		case "DISPLAY_STANDARD_MODE":
			SetDisplayFeatureStatus(1);
			SetDisplayStdandardMode();
			break;
		case "DISPLAY_GAMING_MODE":
			SetDisplayFeatureStatus(2);
			SetDisplayGamingModeFromReg();
			break;
		case "DISPLAY_VIDEO_MODE":
			SetDisplayFeatureStatus(3);
			SetDisplayVideoModeFromReg();
			break;
		case "DISPLAY_READ_MODE":
			SetDisplayFeatureStatus(4);
			SetDisplayReadModeFromReg();
			break;
		case "DISPLAY_CUSTOMIZED_MODE":
			SetDisplayFeatureStatus(5);
			SetDisplayCustomizedModeFromReg();
			break;
		}
	}

	private void UserSetDisplayGamingModeValue(dynamic tmp2)
	{
		DisplayFeatureCtrl.Instance.SetDisplayGamingModeValue(tmp2);
	}

	private void UserSetDisplayVideoModeValue(dynamic tmp2)
	{
		DisplayFeatureCtrl.Instance.SetDisplayVideoModeValue(tmp2);
	}

	private void UserSetDisplayReadModeValue(dynamic tmp2)
	{
		DisplayFeatureCtrl.Instance.SetDisplayReadModeValue(tmp2);
	}

	private void UserSetDisplayCustomizedModeValue(dynamic tmp2)
	{
		DisplayFeatureCtrl.Instance.SetDisplayCustomizedModeValue(tmp2);
	}

	private void UserRcoveryDisplayModeValue(string mode)
	{
		DisplayFeatureCtrl.Instance.Default(mode);
	}

	private void UserSetWinKey(int status)
	{
		if (status == 1)
		{
			MySettingParams_Intel.sWinKey_Status = "WINKEY_STATUS_LOCK";
		}
		else
		{
			MySettingParams_Intel.sWinKey_Status = "WINKEY_STATUS_UNLOCK";
		}
		SetWinKey(status);
		SetWinKeyREG(status);
	}

	private void UserSetOsdHidden(int status)
	{
		if (status == 1)
		{
			MySettingParams_Intel.sOSD_Status = "OSD_HIDDEN_ON";
			App.m_Osd.SetOSDSwitch(0);
		}
		else
		{
			MySettingParams_Intel.sOSD_Status = "OSD_HIDDEN_OFF";
			App.m_Osd.SetOSDSwitch(1);
		}
		SetOSDHiddenREG(status);
	}

	private void UserSetTouchPadLedStatus(int status)
	{
		byte Data = 0;
		EcCtrl.Read(m_className, 1958, ref Data);
		byte b = (byte)Convert.ToUInt64(Data);
		b = ((status != 1) ? ((byte)(b & 0xF7)) : ((byte)(b | 8)));
		EcCtrl.Write(m_className, 1958, b);
	}

	private void UserSetFnKey(int status)
	{
		byte Data = 0;
		EcCtrl.Read(m_className, 1870, ref Data);
		byte b = (byte)Convert.ToUInt64(Data);
		if (status == 1)
		{
			b |= 0x10;
			MySettingParams_Intel.sFnKey_Status = "FNKEY_LOCK";
		}
		else
		{
			b &= 0xEF;
			MySettingParams_Intel.sFnKey_Status = "FNKEY_UNLOCK";
		}
		EcCtrl.Write(m_className, 1870, b);
	}

	private void UserSetNumpad(int status)
	{
		bool flag = (Win32.GetKeyState(144) & 1) == 1;
		if (status == 1)
		{
			if (!flag)
			{
				KeybdEvent.KeyDown(Keys.NumLock);
				KeybdEvent.KeyUp(Keys.NumLock);
			}
		}
		else if (flag)
		{
			KeybdEvent.KeyDown(Keys.NumLock);
			KeybdEvent.KeyUp(Keys.NumLock);
		}
	}

	private void LoadRegistry()
	{
		m_nCustomizeTarget = RegistryCtrl.GetCustomizeTarget();
		try
		{
			int num = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegistryPath, "CloseTimer", 0);
			int num2 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegistryPath, "OSDHidden", 0);
			int num3 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegistryPath, "WinKeyLock", 0);
			MySettingParams_Intel.sCloseTimer = num.ToString();
			switch (num2)
			{
			case 0:
				MySettingParams_Intel.sOSD_Status = "OSD_HIDDEN_OFF";
				break;
			case 1:
				MySettingParams_Intel.sOSD_Status = "OSD_HIDDEN_ON";
				break;
			}
			switch (num3)
			{
			case 0:
				MySettingParams_Intel.sWinKey_Status = "WINKEY_STATUS_UNLOCK";
				break;
			case 1:
				MySettingParams_Intel.sWinKey_Status = "WINKEY_STATUS_LOCK";
				break;
			}
		}
		catch
		{
			LoadDefaultRegistry();
		}
		LoadDisplayFeaturesRegistry();
	}

	private void LoadDefaultRegistry()
	{
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath, "CloseTimer", 0, RegistryValueKind.DWord);
		MySettingParams_Intel.sCloseTimer = "0";
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath, "OSDHidden", 0, RegistryValueKind.DWord);
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath, "WinKeyLock", 0, RegistryValueKind.DWord);
		MySettingParams_Intel.sOSD_Status = "OSD_HIDDEN_OFF";
		MySettingParams_Intel.sWinKey_Status = "WINKEY_STATUS_UNLOCK";
	}

	private void Init()
	{
		LogCtrl.Write(m_className + "[Init] CloseTimer");
		KeyboardCloseTimer createInstance = KeyboardCloseTimer.CreateInstance;
		createInstance.SetKeyboardCloseTime(Convert.ToInt32(MySettingParams_Intel.sCloseTimer));
		if (MySettingParams_Intel.sCloseTimer.Equals("0"))
		{
			createInstance.UnHookEvent();
			createInstance.DisableCloseTimer();
		}
		else
		{
			createInstance.HookEvent();
			createInstance.EnableCloseTimer();
		}
		try
		{
			LogCtrl.Write(m_className + "[Init] Enable OSDManager");
			App.m_Osd.EnableByService();
			if (MySettingParams_Intel.sOSD_Status == "OSD_HIDDEN_ON")
			{
				App.m_Osd.SetOSDSwitch(0);
			}
			else if (MySettingParams_Intel.sOSD_Status == "OSD_HIDDEN_OFF")
			{
				App.m_Osd.SetOSDSwitch(1);
			}
			App.m_MQTTService.Publish("OSDTpDectect/Control", new
			{
				OSDTpSwitch = "0"
			}, retain: false);
		}
		catch (Exception ex)
		{
			LogCtrl.Write(m_className + $"[Init] OSDHidden Exception: {ex.Message}");
		}
		LogCtrl.Write(m_className + "[Init] WinKey");
		if (MySettingParams_Intel.sWinKey_Status == "WINKEY_STATUS_UNLOCK")
		{
			SetWinKey(0);
		}
		else if (MySettingParams_Intel.sWinKey_Status == "WINKEY_STATUS_LOCK")
		{
			SetWinKey(1);
		}
		SetDisplayMode();
		MicMuteControl.Instance.Init();
		InitNumPad();
		InitFnKey();
	}

	public override void InitNumPad()
	{
		if ((Win32.GetKeyState(144) & 1) == 1)
		{
			MySettingParams_Intel.sNumPad_Status = "NUMPAD_LOCK";
		}
		else
		{
			MySettingParams_Intel.sNumPad_Status = "NUMPAD_UNLOCK";
		}
		LogCtrl.Write(m_className + "[InitNumPad] sNumPad_Status: " + MySettingParams_Intel.sNumPad_Status);
	}

	private void InitFnKey()
	{
		if (GetFnKeyStatus() == 1)
		{
			MySettingParams_Intel.sFnKey_Status = "FNKEY_LOCK";
		}
		else
		{
			MySettingParams_Intel.sFnKey_Status = "FNKEY_UNLOCK";
		}
		LogCtrl.Write(m_className + "[InitFnKey] sFnKey_Status: " + MySettingParams_Intel.sFnKey_Status);
	}

	public override int GetFnKeyStatus()
	{
		byte Data = 0;
		byte b = 16;
		EcCtrl.Read(m_className, 1870, ref Data);
		int result = (((byte)(Data & b) == 16) ? 1 : 0);
		LogCtrl.Write(m_className + "[GetFnKeyStatus] " + result);
		return result;
	}

	public override void UpdateFnKeyStatus()
	{
	}

	private void SetWinKey(int status)
	{
		byte Data = 0;
		EcCtrl.Read(GetType().Name, 1896, ref Data);
		LogCtrl.Write(m_className + $"[SetWinKey] 0x0768=0x{Data:X}");
		if (status == 0)
		{
			if ((Data & 1) != 0)
			{
				LogCtrl.Write(m_className + "[SetWinKey] 0x0768.0!=0, Set WinKeyLock_Trigger");
				WinKeyLock_Trigger();
			}
			LogCtrl.Write(m_className + "[SetWinKey] 0x0768.0=0, Do nothing");
		}
		else
		{
			if ((Data & 1) != 1)
			{
				LogCtrl.Write(m_className + "[SetWinKey] 0x0768.0!=1, Set WinKeyLock_Trigger");
				WinKeyLock_Trigger();
			}
			LogCtrl.Write(m_className + "[SetWinKey] 0x0768.0=1, Do nothing");
		}
	}

	private void WinKeyLock_Trigger()
	{
		LogCtrl.Write(m_className + "[WinKeyLock_Trigger]");
		byte Data = 0;
		EcCtrl.Read(GetType().Name, 1895, ref Data);
		byte b = (byte)(Convert.ToUInt64(Data) & 0xFE);
		EcCtrl.Write(GetType().Name, 1895, (byte)(1 + b));
	}

	public override void Resume()
	{
		Write_Support_BYTE();
		LoadRegistry();
		Init();
	}

	private void Write_Support_BYTE()
	{
		byte Data = 0;
		EcCtrl.Read(GetType().Name, 1894, ref Data);
		byte data = (byte)(Convert.ToUInt64(Data) | 3);
		EcCtrl.Write(GetType().Name, 1894, data);
	}

	private void SetCloseTimer(int seconds)
	{
		MySettingParams_Intel.sCloseTimer = seconds.ToString();
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath, "CloseTimer", seconds, RegistryValueKind.DWord);
	}

	private void SetOSDHiddenREG(int mode)
	{
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath, "OSDHidden", mode, RegistryValueKind.DWord);
	}

	public override void SetWinKeyREG(int mode)
	{
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath, "WinKeyLock", mode, RegistryValueKind.DWord);
	}

	private void LoadDisplayFeaturesRegistry()
	{
		try
		{
			int num = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures", "DisplayFeatureStatus", 1);
			int num2 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures", "DisplayMode", 1);
			if (num == 1)
			{
				MySettingParams_Intel.sDisplayFeatureStatus = "DISPLAY_FEATURE_STATUS_ON";
				switch (num2)
				{
				case 1:
					MySettingParams_Intel.sDisplayMode = "DISPLAY_STANDARD_MODE";
					break;
				case 2:
					MySettingParams_Intel.sDisplayMode = "DISPLAY_GAMING_MODE";
					break;
				case 3:
					MySettingParams_Intel.sDisplayMode = "DISPLAY_VIDEO_MODE";
					break;
				case 4:
					MySettingParams_Intel.sDisplayMode = "DISPLAY_READ_MODE";
					break;
				case 5:
					MySettingParams_Intel.sDisplayMode = "DISPLAY_CUSTOMIZED_MODE";
					break;
				}
			}
			else
			{
				MySettingParams_Intel.sDisplayFeatureStatus = "DISPLAY_FEATURE_STATUS_OFF";
				MySettingParams_Intel.sDisplayMode = "DISPLAY_STANDARD_MODE";
			}
		}
		catch
		{
			LoadDefaultDisplayFeaturesRegistry();
		}
		DisplayFeatureCtrl.Instance.LoadRegistry();
	}

	private void LoadDefaultDisplayFeaturesRegistry()
	{
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures", "DisplayFeatureStatus", 1, RegistryValueKind.DWord);
		MySettingParams_Intel.sDisplayFeatureStatus = "DISPLAY_FEATURE_STATUS_ON";
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures", "DisplayMode", 1, RegistryValueKind.DWord);
		MySettingParams_Intel.sDisplayMode = "DISPLAY_STANDARD_MODE";
	}

	private void SetDisplayMode()
	{
		if (MySettingParams_Intel.sDisplayFeatureStatus == "DISPLAY_FEATURE_STATUS_ON")
		{
			switch (MySettingParams_Intel.sDisplayMode)
			{
			case "DISPLAY_STANDARD_MODE":
				SetDisplayStdandardMode();
				break;
			case "DISPLAY_GAMING_MODE":
				SetDisplayGamingModeFromReg();
				break;
			case "DISPLAY_VIDEO_MODE":
				SetDisplayVideoModeFromReg();
				break;
			case "DISPLAY_READ_MODE":
				SetDisplayReadModeFromReg();
				break;
			case "DISPLAY_CUSTOMIZED_MODE":
				SetDisplayCustomizedModeFromReg();
				break;
			}
		}
		else
		{
			SetDisplayStdandardMode();
		}
	}

	private void SetDisplayFeatureStatus(int mode)
	{
		switch (mode)
		{
		case -1:
			MySettingParams_Intel.sDisplayFeatureStatus = "DISPLAY_FEATURE_STATUS_OFF";
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures", "DisplayFeatureStatus", 0, RegistryValueKind.DWord);
			break;
		case 0:
			MySettingParams_Intel.sDisplayFeatureStatus = "DISPLAY_FEATURE_STATUS_ON";
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures", "DisplayFeatureStatus", 1, RegistryValueKind.DWord);
			break;
		case 1:
			MySettingParams_Intel.sDisplayMode = "DISPLAY_STANDARD_MODE";
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures", "DisplayMode", 1, RegistryValueKind.DWord);
			break;
		case 2:
			MySettingParams_Intel.sDisplayMode = "DISPLAY_GAMING_MODE";
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures", "DisplayMode", 2, RegistryValueKind.DWord);
			break;
		case 3:
			MySettingParams_Intel.sDisplayMode = "DISPLAY_VIDEO_MODE";
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures", "DisplayMode", 3, RegistryValueKind.DWord);
			break;
		case 4:
			MySettingParams_Intel.sDisplayMode = "DISPLAY_READ_MODE";
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures", "DisplayMode", 4, RegistryValueKind.DWord);
			break;
		case 5:
			MySettingParams_Intel.sDisplayMode = "DISPLAY_CUSTOMIZED_MODE";
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures", "DisplayMode", 5, RegistryValueKind.DWord);
			break;
		}
	}

	private void SetDisplayStdandardMode()
	{
		DisplayFeatureCtrl.Instance.SetDisplayStdandardMode();
	}

	private void SetDisplayGamingModeFromReg()
	{
		DisplayFeatureCtrl.Instance.SetDisplayGamingModeFromReg();
	}

	private void SetDisplayVideoModeFromReg()
	{
		DisplayFeatureCtrl.Instance.SetDisplayVideoModeFromReg();
	}

	private void SetDisplayReadModeFromReg()
	{
		DisplayFeatureCtrl.Instance.SetDisplayReadModeFromReg();
	}

	private void SetDisplayCustomizedModeFromReg()
	{
		DisplayFeatureCtrl.Instance.SetDisplayCustomizedModeFromReg();
	}

	public override void Uninstall()
	{
		LogCtrl.Write(m_className + "[Uninstall] set DISPLAY_STANDARD_MODE");
		SetDisplayStdandardMode();
	}

	public override void DeleteAllPowerPlan()
	{
	}

	public override void Restore()
	{
		LoadDefaultRegistry();
		LoadDefaultDisplayFeaturesRegistry();
		DisplayFeatureCtrl.Instance.LoadDefaultRegistry();
		Init();
	}
}
