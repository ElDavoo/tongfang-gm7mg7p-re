using System;
using System.Collections;
using System.ComponentModel;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.NetworkInformation;
using System.Reflection;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Forms;
using GCService5;
using GCUService.MySetting;
using GCUService.MySetting.Muter;
using Microsoft.Win32;
using MyControlCenter.MySetting.ColorCalibration;
using MyControlCenter.MySetting.DisplayFeature;
using MyECIO;
using Utility;

namespace MyControlCenter;

public class MySettingManager
{
	private string m_className = "[" + MethodBase.GetCurrentMethod().DeclaringType.Name + "] ";

	private ColorProfileControl m_ICCProfileControl;

	private int m_nCustomizeTarget = 1;

	private string m_sBiosProjectID = "";

	private KeyboardCloseTimer keyboardCloseTimer = KeyboardCloseTimer.CreateInstance;

	private MySettingView m_View = new MySettingView();

	private string m_sRegistryPath = "\\OEM\\GamingCenter2\\MySetting";

	private static int m_sCloseTimer;

	private static bool m_EnabbleDone;

	private MyEcCtrl EcCtrl = MyEcCtrl.Instance;

	private int m_nSingleColorKBBLOnOff = 1;

	private MyDisplay_Manager mydisplay;

	private int m_BiosFnKeyStatus;

	private DeviceSwitchItem deviceSwitchItem;

	private GPUDeviceItem gdevice;

	private object MonitorLock = new object();

	private byte g_colibrationBrightness = 70;

	public virtual void Enable()
	{
		LogCtrl.Write(m_className + "[Enable] Write 0x0766 Support Byte");
		Write_Support_BYTE();
		LogCtrl.Write(m_className + "[Enable] LoadRegistry");
		LoadRegistry();
		LogCtrl.Write(m_className + "[Enable] GetStatus");
		GetStatus();
		LogCtrl.Write(m_className + "[Enable] Init");
		Init();
		mydisplay = MyDisplay_Manager.Instance;
		mydisplay.SetSettingMnager(this);
		m_EnabbleDone = true;
	}

	public virtual void Disable()
	{
		if (CustomizeInfo.m_sKeyboardType == "2")
		{
			if (App.OsdOnly == 0)
			{
				SingleColorKeyboard.SetPower(1);
				SingleColorKeyboard.EcBacklightLevel = 2;
			}
			else
			{
				LogCtrl.TraceMessage("OSD only, skip reset SingleColorKeyboard", "Disable", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MySetting\\MySettingManager.cs", 120);
			}
		}
		TouchpadToggle_ON();
	}

	private void SetBrightness(byte brightness)
	{
		g_colibrationBrightness = brightness;
	}

	public virtual async void Receive(byte[] data)
	{
		dynamic val = await Json.ToObjectAsync<object>(Encoding.UTF8.GetString(data));
		string text = val["Action"];
		if (val["ColibrationBrightness"] != null)
		{
			byte brightness = Convert.ToByte(Convert.ToInt32(val["ColibrationBrightness"]));
			SetBrightness(brightness);
		}
		LogCtrl.Write("---------------" + LogCtrl.GetTime() + "---------------");
		LogCtrl.Write(m_className + "[Recieve] msg = " + text);
		switch (text)
		{
		case "KEYBOARD_LIGHTBAR_TIMER_ON":
			KeyboardCloseTimer.CreateInstance.GetStartMoniter();
			KeyboardCloseTimer.CreateInstance.HookEvent();
			KeyboardCloseTimer.CreateInstance.SetKeyboardCloseTime(Convert.ToInt32(val["Mins"]));
			UserSetCloseTimer(Convert.ToInt32(val["Mins"]));
			break;
		case "KEYBOARD_LIGHTBAR_TIMER_OFF":
			KeyboardCloseTimer.CreateInstance.GetStartMoniter();
			KeyboardCloseTimer.CreateInstance.UnHookEvent();
			KeyboardCloseTimer.CreateInstance.DisableCloseTimer();
			UserSetCloseTimer(0);
			break;
		case "DISPLAY_POWER_OFF":
			if (Monitor.TryEnter(MonitorLock, 500))
			{
				try
				{
					DisplaySwitch.SetDisplayState(2);
					break;
				}
				finally
				{
					Monitor.Exit(MonitorLock);
				}
			}
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
		case "NV_CTRL_PANEL_AUTOSELECT":
			UserSetNVCtrlPanel(0);
			break;
		case "NV_CTRL_PANEL_HIGHPERFORMANCE":
			UserSetNVCtrlPanel(1);
			break;
		case "WINKEY_LOCK":
			UserSetWinKey(1);
			break;
		case "WINKEY_UNLOCK":
			UserSetWinKey(0);
			break;
		case "LIGHT_BAR_TRIGGER":
			LightBar_Trigger();
			break;
		case "USB_CHARGER_ON":
			UserSetUSBCharger(1);
			break;
		case "USB_CHARGER_OFF":
			UserSetUSBCharger(0);
			break;
		case "GAMER_ON":
		case "GAMER_OFF":
			UserSetGamer(text);
			break;
		case "SINGLE_COLOR_KBBL_STATUS_ON":
		case "SINGLE_COLOR_KBBL_STATUS_OFF":
			UserSetSingleColorKeyboard(text);
			UpdateStatusToClient(1);
			break;
		case "ICCPROFILESETING":
			if (val["FilePath"] != null)
			{
				string text2 = val["FilePath"];
				SetDisplayStdandardMode();
				if (m_ICCProfileControl == null)
				{
					m_ICCProfileControl = new ColorProfileControl();
				}
				m_ICCProfileControl.UnInstallProfile(text2, bDelete: true);
				m_ICCProfileControl.InstallProfile(text2);
				if (m_ICCProfileControl.SetMonitorProfile(text2))
				{
					MyDisplay_Manager.Instance.SetDisplaySwitch(ONOFF: false);
				}
			}
			break;
		case "COLOR_CALIBRATION_ON":
			UserSetColorCalibration(text);
			MyDisplay_Manager.Instance.SetDisplaySwitch(ONOFF: false);
			break;
		case "COLOR_CALIBRATION_OFF":
			UnistallCalibration();
			break;
		case "TOUCHPAD_LED_ON":
			deviceSwitchItem?.SetTouchpadSwitch(Enable: true);
			UserSetTouchPadLedStatus(1);
			break;
		case "TOUCHPAD_LED_OFF":
			deviceSwitchItem?.SetTouchpadSwitch(Enable: false);
			UserSetTouchPadLedStatus(0);
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
		case "TOUCHPAD_TOGGLE_ON":
			UserSetTouchpadToggleStatus(1);
			break;
		case "TOUCHPAD_TOGGLE_OFF":
			UserSetTouchpadToggleStatus(0);
			break;
		case "ACRECOVERY_TOGGLE_ON":
			UserSetAcRecoverySwitch(1);
			break;
		case "ACRECOVERY_TOGGLE_OFF":
			UserSetAcRecoverySwitch(0);
			break;
		case "FN_WITH1_HOTKEY_TOGGLE_ON":
			UserSetFnWith1HotkeySwitch(1);
			break;
		case "FN_WITH1_HOTKEY_TOGGLE_OFF":
			UserSetFnWith1HotkeySwitch(0);
			break;
		case "DGPU_DIRECT_CONNECT_TOGGLE_ON":
			UserSetDGgpuDirectConnectionSwitch(1);
			break;
		case "DGPU_DIRECT_CONNECT_TOGGLE_OFF":
			UserSetDGgpuDirectConnectionSwitch(0);
			break;
		}
	}

	public virtual void UpdateStatusToClient(int run)
	{
		if (m_EnabbleDone && run != 0)
		{
			dynamic val = new
			{
				WinKey = MySettingParams.sWinKey_Status.ToString(),
				LightBar = MySettingParams.sLightBar_Status.ToString(),
				UsbCharger = MySettingParams.sUsbCharger_Status.ToString(),
				DGpu = MySettingParams.sDGpu_Status.ToString(),
				OSD = MySettingParams.sOSD_Status.ToString(),
				DisplayFeatureStatus = MySettingParams.sDisplayFeatureStatus.ToString(),
				DisplayMode = MySettingParams.sDisplayMode.ToString(),
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
				SingleColorKBBL = MySettingParams.sSingleColorKBBL_Status.ToString(),
				CloseTimer = MySettingParams.sCloseTimer.ToString(),
				ColorCalibrationResultCode = MySettingParams.sColorCalibrationResultCode,
				NumPad = MySettingParams.sNumPad_Status.ToString(),
				FnKey = MySettingParams.sFnKey_Status.ToString(),
				TouchpadToggle = MySettingParams.sTouchpadToggle_Status.ToString(),
				AcRecoverySwitch_Support = MySettingParams.sAcRecoverySwitch_Support,
				AcRecoverySwitch_Status = MySettingParams.sAcRecoverySwitch_Status,
				FnWith1HotkeySwitch_Status = MySettingParams.sFnWith1HotkeySwitch_Status,
				DiscreteGpuDirectConnectionSwitch_Status = MySettingParams.sDGpuDirectConnectionSwitch_Status,
				DiscreteGpuDirectConnectionSwitch_Support = MySettingParams.sDGpuDirectConnectionSwitch_Support
			};
			m_View.SendStatusToClient(val);
		}
	}

	public virtual void UpdateWinKeyStatus(int mode)
	{
		if (mode == 1)
		{
			MySettingParams.sWinKey_Status = "WINKEY_STATUS_LOCK";
		}
		else
		{
			MySettingParams.sWinKey_Status = "WINKEY_STATUS_UNLOCK";
		}
	}

	private void UserSetCloseTimer(int mins)
	{
		SetCloseTimer(mins);
	}

	private void UserSetDisplayFeatureStatus(int status)
	{
		if (CustomizeInfo.m_supportColorCalibration == 1)
		{
			if (status == 0)
			{
				if (MySettingParams.sColorCalibration_Status == "COLOR_CALIBRATION_ON")
				{
					StartICCProfile();
					return;
				}
				SetDisplayFeatureStatus(-1);
				SetDisplayMode();
				LogCtrl.Write(m_className + $"[UserSetDisplayFeatureStatus] DisplayFeatureStatus:{status}, ColorCalibration_Status:{MySettingParams.sColorCalibration_Status}");
				return;
			}
			SetDisplayFeatureStatus(0);
			LoadDisplayFeaturesRegistry();
			SetDisplayMode();
			try
			{
				string subKey = "\\OEM\\GamingCenter2";
				if ((int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, subKey, "AppType", 1) == 3)
				{
					new Brightness().SetBrightness(g_colibrationBrightness);
				}
			}
			catch
			{
			}
			LogCtrl.Write(m_className + $"[UserSetDisplayFeatureStatus] DisplayFeatureStatus:{status}, ColorCalibration_Status:{MySettingParams.sColorCalibration_Status}");
		}
		else
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

	private void UserSetUSBCharger(int status)
	{
		if (status == 1)
		{
			MySettingParams.sUsbCharger_Status = "USB_CHARGER_STATUS_ON";
			USB_Charger_ON();
		}
		else
		{
			MySettingParams.sUsbCharger_Status = "USB_CHARGER_STATUS_OFF";
			USB_Charger_OFF();
		}
		SetUSBChargerREG(status);
	}

	private void UserSetNVCtrlPanel(int status)
	{
		if (status == 1)
		{
			MySettingParams.sDGpu_Status = "NV_CTRL_PANEL_HIGHPERFORMANCE";
			SetNVCtrlPanel_HighPerformance();
		}
		else
		{
			MySettingParams.sDGpu_Status = "NV_CTRL_PANEL_AUTOSELECT";
			SetNVCtrlPanel_AutoSelect();
		}
		SetNVCtrlPanelREG(status);
	}

	private void UserSetWinKey(int status)
	{
		if (status == 1)
		{
			MySettingParams.sWinKey_Status = "WINKEY_STATUS_LOCK";
		}
		else
		{
			MySettingParams.sWinKey_Status = "WINKEY_STATUS_UNLOCK";
		}
		SetWinKey(status);
		SetWinKeyREG(status);
	}

	private void UserSetOsdHidden(int status)
	{
		if (status == 1)
		{
			MySettingParams.sOSD_Status = "OSD_HIDDEN_ON";
			App.m_Osd.SetOSDSwitch(0);
			App.m_MQTTService.Publish("OSDTpDectect/Control", new
			{
				OSDTpSwitch = "0"
			}, retain: false);
		}
		else
		{
			MySettingParams.sOSD_Status = "OSD_HIDDEN_OFF";
			App.m_Osd.SetOSDSwitch(1);
			App.m_MQTTService.Publish("OSDTpDectect/Control", new
			{
				OSDTpSwitch = "1"
			}, retain: false);
		}
		SetOSDHiddenREG(status);
	}

	private void UserSetPowerPlan(string mode)
	{
	}

	private void UserSetGamer(string mode)
	{
		if (!(mode == "GAMER_ON"))
		{
			if (mode == "GAMER_OFF")
			{
				DisableGamingMode();
			}
		}
		else
		{
			EnableGamingMode();
		}
	}

	private void UserSetSingleColorKeyboard(string mode)
	{
		if (CustomizeInfo.m_sKeyboardType != "2")
		{
			return;
		}
		if (!(mode == "SINGLE_COLOR_KBBL_STATUS_ON"))
		{
			if (mode == "SINGLE_COLOR_KBBL_STATUS_OFF")
			{
				m_nSingleColorKBBLOnOff = 0;
				MySettingParams.sSingleColorKBBL_Status = "SINGLE_COLOR_KBBL_STATUS_OFF";
			}
		}
		else
		{
			m_nSingleColorKBBLOnOff = 1;
			MySettingParams.sSingleColorKBBL_Status = "SINGLE_COLOR_KBBL_STATUS_ON";
		}
		SetSingleColorKeyboard(m_nSingleColorKBBLOnOff);
	}

	private void UserSetColorCalibration(string mode)
	{
		if (CustomizeInfo.m_supportColorCalibration == 1)
		{
			StartICCProfile();
		}
	}

	private void UserSetTouchPadLedStatus(int status)
	{
		byte Data = 0;
		EcCtrl.Read(m_className, 1958, ref Data);
		byte b = (byte)Convert.ToUInt64(Data);
		b = ((status != 1) ? ((byte)(b & 0xF7)) : ((byte)(b | 8)));
		EcCtrl.Write(m_className, 1958, b);
	}

	private void UserSetTouchpadToggleStatus(int status)
	{
		LogCtrl.TraceMessage("status = " + status, "UserSetTouchpadToggleStatus", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MySetting\\MySettingManager.cs", 739);
		if (status == 1)
		{
			MySettingParams.sTouchpadToggle_Status = "TOUCHPAD_TOGGLE_ON";
			TouchpadToggle_ON();
		}
		else
		{
			MySettingParams.sTouchpadToggle_Status = "TOUCHPAD_TOGGLE_OFF";
			TouchpadToggle_OFF();
		}
		SetTouchpadToggleREG(status);
	}

	private void UserSetFnKey(int status)
	{
		LogCtrl.TraceMessage("status = " + status, "UserSetFnKey", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MySetting\\MySettingManager.cs", 755);
		if (status == 1)
		{
			MySettingParams.sFnKey_Status = "FNKEY_LOCK";
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath + "\\FnKey", "FnKeyStatus", 1, RegistryValueKind.DWord);
			if (m_BiosFnKeyStatus != 255)
			{
				NvramVariable.SetFwVars("FnKeyStatus", 1);
			}
		}
		else
		{
			MySettingParams.sFnKey_Status = "FNKEY_UNLOCK";
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath + "\\FnKey", "FnKeyStatus", 0, RegistryValueKind.DWord);
			if (m_BiosFnKeyStatus != 255)
			{
				NvramVariable.SetFwVars("FnKeyStatus", 0);
			}
		}
		SetFnKey(status);
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

	private void UserSetAcRecoverySwitch(int status)
	{
		if (MySettingParams.sAcRecoverySwitch_Support == "Support")
		{
			if (status == 1)
			{
				MySettingParams.sAcRecoverySwitch_Status = "ACRECOVERY_TOGGLE_ON";
				NvramVariable.SetFwVars("ACRecoveryStatus", 1);
			}
			else
			{
				MySettingParams.sAcRecoverySwitch_Status = "ACRECOVERY_TOGGLE_OFF";
				NvramVariable.SetFwVars("ACRecoveryStatus", 0);
			}
		}
	}

	private void UserSetFnWith1HotkeySwitch(int status)
	{
		if (status == 1)
		{
			MySettingParams.sFnWith1HotkeySwitch_Status = "FN_WITH1_HOTKEY_TOGGLE_ON";
		}
		else
		{
			MySettingParams.sFnWith1HotkeySwitch_Status = "FN_WITH1_HOTKEY_TOGGLE_OFF";
		}
	}

	private void UserSetDGgpuDirectConnectionSwitch(int status)
	{
		if (MySettingParams.sDGpuDirectConnectionSwitch_Support == "NotSupport")
		{
			return;
		}
		if (CustomizeCtrl.GetIsAMDPlatform())
		{
			if (status == 1)
			{
				MySettingParams.sDGpuDirectConnectionSwitch_Status = "DGPU_DIRECT_CONNECT_TOGGLE_ON";
				NvramVariable.SetFwVars("OemDisplayMode", 1);
			}
			else
			{
				MySettingParams.sDGpuDirectConnectionSwitch_Status = "DGPU_DIRECT_CONNECT_TOGGLE_OFF";
				NvramVariable.SetFwVars("OemDisplayMode", 0);
			}
		}
		else if (status == 1)
		{
			MySettingParams.sDGpuDirectConnectionSwitch_Status = "DGPU_DIRECT_CONNECT_TOGGLE_ON";
			NvramVariable.SetFwVars("OemDisplayMode", 2);
		}
		else
		{
			MySettingParams.sDGpuDirectConnectionSwitch_Status = "DGPU_DIRECT_CONNECT_TOGGLE_OFF";
			NvramVariable.SetFwVars("OemDisplayMode", 4);
		}
	}

	private void LoadRegistry()
	{
		m_nCustomizeTarget = RegistryCtrl.GetCustomizeTarget();
		m_sBiosProjectID = RegistryCtrl.GetBIOSProjectID();
		try
		{
			int num = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegistryPath, "CloseTimer", 0);
			int num2 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegistryPath, "USBCharger", 0);
			int num3 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegistryPath, "DGpuPowerManagement", 0);
			int num4 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegistryPath, "OSDHidden", 0);
			int num5 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegistryPath, "WinKeyLock", 0);
			int num6 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegistryPath, "TouchpadToggle", 1);
			MySettingParams.sCloseTimer = num.ToString();
			switch (num2)
			{
			case 0:
				MySettingParams.sUsbCharger_Status = "USB_CHARGER_STATUS_OFF";
				break;
			case 1:
				MySettingParams.sUsbCharger_Status = "USB_CHARGER_STATUS_ON";
				break;
			}
			switch (num3)
			{
			case 0:
				MySettingParams.sDGpu_Status = "NV_CTRL_PANEL_AUTOSELECT";
				break;
			case 1:
				MySettingParams.sDGpu_Status = "NV_CTRL_PANEL_HIGHPERFORMANCE";
				break;
			}
			switch (num4)
			{
			case 0:
				MySettingParams.sOSD_Status = "OSD_HIDDEN_OFF";
				break;
			case 1:
				MySettingParams.sOSD_Status = "OSD_HIDDEN_ON";
				break;
			}
			switch (num5)
			{
			case 0:
				MySettingParams.sWinKey_Status = "WINKEY_STATUS_UNLOCK";
				break;
			case 1:
				MySettingParams.sWinKey_Status = "WINKEY_STATUS_LOCK";
				break;
			}
			switch (num6)
			{
			case 0:
				MySettingParams.sTouchpadToggle_Status = "TOUCHPAD_TOGGLE_OFF";
				break;
			case 1:
				MySettingParams.sTouchpadToggle_Status = "TOUCHPAD_TOGGLE_ON";
				break;
			}
		}
		catch
		{
			LoadDefaultRegistry();
		}
		LoadDisplayFeaturesRegistry();
		if (CustomizeInfo.m_sKeyboardType == "2")
		{
			m_nSingleColorKBBLOnOff = SingleColorKeyboard.LoadSingleColorKBBLOnOff_Registry();
			if (m_nSingleColorKBBLOnOff == 1)
			{
				MySettingParams.sSingleColorKBBL_Status = "SINGLE_COLOR_KBBL_STATUS_ON";
			}
			else
			{
				MySettingParams.sSingleColorKBBL_Status = "SINGLE_COLOR_KBBL_STATUS_OFF";
			}
		}
	}

	private bool SingleZonePowerSupport()
	{
		byte Data = 0;
		MyEcCtrl.Instance.Read("MySettingManager", 1934, ref Data);
		return new BitArray(new byte[1] { Data })[5];
	}

	private void LoadDefaultRegistry()
	{
		int projectIdFromEC = EcCtrl.GetProjectIdFromEC();
		switch (RegistryCtrl.GetCustomizeTarget())
		{
		case 9:
			MySettingParams.sCloseTimer = "15";
			break;
		case 11:
			MySettingParams.sCloseTimer = "30";
			break;
		default:
			if (projectIdFromEC.IsProjectId_SingleColorKeyboard())
			{
				MySettingParams.sCloseTimer = "60";
			}
			else
			{
				MySettingParams.sCloseTimer = "0";
			}
			break;
		}
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath, "CloseTimer", Convert.ToInt32(MySettingParams.sCloseTimer), RegistryValueKind.DWord);
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath, "USBCharger", 0, RegistryValueKind.DWord);
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath, "DGpuPowerManagement", 0, RegistryValueKind.DWord);
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath, "OSDHidden", 0, RegistryValueKind.DWord);
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath, "WinKeyLock", 0, RegistryValueKind.DWord);
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath, "TouchpadToggle", 1, RegistryValueKind.DWord);
		MySettingParams.sUsbCharger_Status = "USB_CHARGER_STATUS_OFF";
		MySettingParams.sDGpu_Status = "NV_CTRL_PANEL_AUTOSELECT";
		MySettingParams.sOSD_Status = "OSD_HIDDEN_OFF";
		MySettingParams.sWinKey_Status = "WINKEY_STATUS_UNLOCK";
		MySettingParams.sTouchpadToggle_Status = "TOUCHPAD_TOGGLE_ON";
	}

	private void GetStatus()
	{
		GetStatus_LightBar();
	}

	private void Init()
	{
		LogCtrl.Write(m_className + "[Init] CloseTimer");
		KeyboardCloseTimer createInstance = KeyboardCloseTimer.CreateInstance;
		createInstance.SetKeyboardCloseTime(Convert.ToInt32(MySettingParams.sCloseTimer));
		if (MySettingParams.sCloseTimer.Equals("0"))
		{
			createInstance.UnHookEvent();
			createInstance.DisableCloseTimer();
		}
		else
		{
			createInstance.HookEvent();
			createInstance.EnableCloseTimer();
		}
		LogCtrl.Write(m_className + "[Init] UsbCharger");
		if (MySettingParams.sUsbCharger_Status == "USB_CHARGER_STATUS_OFF")
		{
			USB_Charger_OFF();
		}
		else if (MySettingParams.sUsbCharger_Status == "USB_CHARGER_STATUS_ON")
		{
			USB_Charger_ON();
		}
		try
		{
			LogCtrl.Write(m_className + "[Init] Enable OSDManager");
			App.m_Osd.EnableByService();
			if (MySettingParams.sOSD_Status == "OSD_HIDDEN_ON")
			{
				App.m_Osd.SetOSDSwitch(0);
				App.m_MQTTService.Publish("OSDTpDectect/Control", new
				{
					OSDTpSwitch = "0"
				}, retain: false);
			}
			else if (MySettingParams.sOSD_Status == "OSD_HIDDEN_OFF")
			{
				App.m_Osd.SetOSDSwitch(1);
				App.m_MQTTService.Publish("OSDTpDectect/Control", new
				{
					OSDTpSwitch = "1"
				}, retain: false);
			}
		}
		catch (Exception ex)
		{
			LogCtrl.Write(m_className + $"[Init] OSDHidden Exception: {ex.Message}");
		}
		LogCtrl.Write(m_className + "[Init] WinKey");
		if (MySettingParams.sWinKey_Status == "WINKEY_STATUS_UNLOCK")
		{
			SetWinKey(0);
		}
		else if (MySettingParams.sWinKey_Status == "WINKEY_STATUS_LOCK")
		{
			SetWinKey(1);
		}
		if (CustomizeInfo.m_sKeyboardType == "2")
		{
			LogCtrl.Write(m_className + "[Init] SingleColorKeyboard");
			InitSingleColorKeyboard();
		}
		ColoCalibrationService();
		MicMuteControl.Instance.Init();
		InitNumPad();
		InitTouchpadToggle();
		NVRAM_STRUCT fwVars = NvramVariable.GetFwVars();
		int num = Convert.ToInt32(fwVars.ACRecoverySupport);
		int num2 = Convert.ToInt32(fwVars.ACRecoveryStatus);
		LogCtrl.TraceMessage("ACRecoverySupport = 0x" + num.ToString("X2") + ", ACRecoveryStatus = 0x" + num2.ToString("X2"), "Init", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MySetting\\MySettingManager.cs", 1112);
		if (num == 1)
		{
			MySettingParams.sAcRecoverySwitch_Support = "Support";
			if (num2 == 1)
			{
				MySettingParams.sAcRecoverySwitch_Status = "ACRECOVERY_TOGGLE_ON";
			}
			else
			{
				MySettingParams.sAcRecoverySwitch_Status = "ACRECOVERY_TOGGLE_OFF";
			}
		}
		else
		{
			MySettingParams.sAcRecoverySwitch_Support = "NotSupport";
		}
		int num3 = Convert.ToInt32(fwVars.OemDisplayMode);
		if (num3 == 255)
		{
			MySettingParams.sDGpuDirectConnectionSwitch_Support = "NotSupport";
		}
		else
		{
			MySettingParams.sDGpuDirectConnectionSwitch_Support = "Support";
			if (CustomizeCtrl.GetIsAMDPlatform())
			{
				switch (num3)
				{
				case 0:
					MySettingParams.sDGpuDirectConnectionSwitch_Status = "DGPU_DIRECT_CONNECT_TOGGLE_OFF";
					break;
				case 1:
					MySettingParams.sDGpuDirectConnectionSwitch_Status = "DGPU_DIRECT_CONNECT_TOGGLE_ON";
					break;
				}
			}
			else
			{
				switch (num3)
				{
				case 4:
					MySettingParams.sDGpuDirectConnectionSwitch_Status = "DGPU_DIRECT_CONNECT_TOGGLE_OFF";
					break;
				case 2:
					MySettingParams.sDGpuDirectConnectionSwitch_Status = "DGPU_DIRECT_CONNECT_TOGGLE_ON";
					break;
				}
			}
		}
		m_BiosFnKeyStatus = Convert.ToInt32(fwVars.FnKeyStatus);
		if (m_BiosFnKeyStatus == 255)
		{
			int num4 = 0;
			try
			{
				num4 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegistryPath + "\\FnKey", "FnKeyStatus", 0);
				MySettingParams.sFnKey_Status = ((num4 == 0) ? "FNKEY_UNLOCK" : "FNKEY_LOCK");
			}
			catch
			{
				RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath + "\\FnKey", "FnKeyStatus", num4, RegistryValueKind.DWord);
				MySettingParams.sFnKey_Status = "FNKEY_UNLOCK";
			}
			SetFnKey(num4);
			LogCtrl.TraceMessage("BIOS Variable FnKeyStatus = 0x" + m_BiosFnKeyStatus.ToString("X2") + ", then read registry fnKeyStatusReg = " + num4 + ", sFnKey_Status = " + MySettingParams.sFnKey_Status, "Init", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MySetting\\MySettingManager.cs", 1182);
		}
		else
		{
			MySettingParams.sFnKey_Status = ((m_BiosFnKeyStatus == 0) ? "FNKEY_UNLOCK" : "FNKEY_LOCK");
			SetFnKey(m_BiosFnKeyStatus);
			LogCtrl.TraceMessage("BIOS Variable FnKeyStatus = 0x" + m_BiosFnKeyStatus.ToString("X2") + ", sFnKey_Status = " + MySettingParams.sFnKey_Status, "Init", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MySetting\\MySettingManager.cs", 1190);
		}
	}

	public void ColoCalibrationService()
	{
		if (CustomizeInfo.m_supportColorCalibration == 1)
		{
			LogCtrl.Write(m_className + "[Init] ColorCalibration");
			ColorProfileInfo.strSerialNumber = ColorProfileInfo.GetSerialNumber();
			ColorProfileInfo.strMacAddress = ColorProfileInfo.GetMacAddress();
			int nCustomizeTarget = m_nCustomizeTarget;
			if (nCustomizeTarget == 4 || nCustomizeTarget == 17)
			{
				ColorProfileInfo.UpdateICCProfileInfo();
				if (!ColorProfileInfo.m_ICCProfileInfo.bFileExist)
				{
					CheckForInternetConnection();
				}
				else
				{
					MySettingParams.sColorCalibrationResultCode = "1";
					MySettingParams.sColorCalibration_Status = "COLOR_CALIBRATION_ON";
				}
			}
			LogCtrl.Write(m_className + $"[Init] m_supportColorCalibration:{CustomizeInfo.m_supportColorCalibration}, ColorCalibration_Status:{MySettingParams.sColorCalibration_Status}");
		}
		else
		{
			LogCtrl.Write(m_className + $"[Init] m_supportColorCalibration:{CustomizeInfo.m_supportColorCalibration}, do nothings");
		}
	}

	private void KeyboardcloseTimer_ControlBrigtnessEvent(object sender, EventArgs e)
	{
		if (Convert.ToBoolean(sender))
		{
			SingleColorKeyboard.SetPower(0);
		}
		else if (MySettingParams.sSingleColorKBBL_Status == "SINGLE_COLOR_KBBL_STATUS_ON")
		{
			SingleColorKeyboard.SetPower(1);
		}
	}

	private void InitSingleColorKeyboard()
	{
		LogCtrl.Write(m_className + "[InitSingleColorKeyboard] call SetPower()");
		SingleColorKeyboard.SetPower(m_nSingleColorKBBLOnOff);
		KeyboardCloseTimer.CreateInstance.ControlBrigtnessEvent += KeyboardcloseTimer_ControlBrigtnessEvent;
		if (m_nSingleColorKBBLOnOff == 1)
		{
			if (App.OsdOnly == 0)
			{
				int backlightLevel = SingleColorKeyboard.BacklightLevel;
				SingleColorKeyboard.BacklightLevel = backlightLevel;
				SingleColorKeyboard.EcBacklightLevel = SingleColorKeyboard.BacklightLevel;
			}
			else
			{
				int backlightLevel = SingleColorKeyboard.EcBacklightLevel;
				LogCtrl.Write(m_className + "[InitSingleColorKeyboard] OSD only, EC backlight level = " + backlightLevel);
				SingleColorKeyboard.BacklightLevel = backlightLevel;
			}
		}
	}

	public virtual void InitNumPad()
	{
		if ((Win32.GetKeyState(144) & 1) == 1)
		{
			MySettingParams.sNumPad_Status = "NUMPAD_LOCK";
		}
		else
		{
			MySettingParams.sNumPad_Status = "NUMPAD_UNLOCK";
		}
		LogCtrl.Write(m_className + "[InitNumPad] sNumPad_Status: " + MySettingParams.sNumPad_Status);
	}

	private void InitTouchpadToggle()
	{
		try
		{
			if (MySettingParams.sTouchpadToggle_Status == "TOUCHPAD_TOGGLE_ON")
			{
				TouchpadToggle_ON();
			}
			else if (MySettingParams.sTouchpadToggle_Status == "TOUCHPAD_TOGGLE_OFF")
			{
				TouchpadToggle_OFF();
			}
			LogCtrl.Write(m_className + "[InitTouchpadToggle] sTouchpadToggle_Status: " + MySettingParams.sTouchpadToggle_Status);
		}
		catch (Exception ex)
		{
			LogCtrl.Write(m_className + $"[InitTouchpadToggle] exception: {ex.Message}");
		}
	}

	public virtual int GetFnKeyStatus()
	{
		byte Data = 0;
		byte b = 16;
		EcCtrl.Read(m_className, 1870, ref Data);
		int result = (((byte)(Data & b) == 16) ? 1 : 0);
		LogCtrl.Write(m_className + "[GetFnKeyStatus] " + result);
		return result;
	}

	public virtual void UpdateFnKeyStatus()
	{
		if (GetFnKeyStatus() == 1)
		{
			MySettingParams.sFnKey_Status = "FNKEY_LOCK";
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath + "\\FnKey", "FnKeyStatus", 1, RegistryValueKind.DWord);
			if (m_BiosFnKeyStatus != 255)
			{
				NvramVariable.SetFwVars("FnKeyStatus", 1);
			}
		}
		else
		{
			MySettingParams.sFnKey_Status = "FNKEY_UNLOCK";
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath + "\\FnKey", "FnKeyStatus", 0, RegistryValueKind.DWord);
			if (m_BiosFnKeyStatus != 255)
			{
				NvramVariable.SetFwVars("FnKeyStatus", 0);
			}
		}
		LogCtrl.TraceMessage("sFnKey_Status = " + MySettingParams.sFnKey_Status, "UpdateFnKeyStatus", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MySetting\\MySettingManager.cs", 1394);
	}

	private void SetSingleColorKeyboard(int status)
	{
		if (status == 1)
		{
			MySettingParams.sSingleColorKBBL_Status = "SINGLE_COLOR_KBBL_STATUS_ON";
		}
		else
		{
			MySettingParams.sSingleColorKBBL_Status = "SINGLE_COLOR_KBBL_STATUS_OFF";
		}
		m_nSingleColorKBBLOnOff = status;
		SingleColorKeyboard.SetSingleColorKBBLOnOff_Registry(m_nSingleColorKBBLOnOff);
		SingleColorKeyboard.SetPower(m_nSingleColorKBBLOnOff);
		if (m_nSingleColorKBBLOnOff == 1)
		{
			SingleColorKeyboard.BacklightLevel = SingleColorKeyboard.BacklightLevel;
		}
	}

	public void BacklightLevelChanged()
	{
		if (m_nSingleColorKBBLOnOff == 0)
		{
			m_nSingleColorKBBLOnOff = 1;
			MySettingParams.sSingleColorKBBL_Status = "SINGLE_COLOR_KBBL_STATUS_ON";
			SingleColorKeyboard.SetSingleColorKBBLOnOff_Registry(m_nSingleColorKBBLOnOff);
			SingleColorKeyboard.SetPower(m_nSingleColorKBBLOnOff);
		}
		SingleColorKeyboard.BacklightLevel = SingleColorKeyboard.EcBacklightLevel;
	}

	public void BacklightPowerChanged()
	{
		LogCtrl.TraceMessage("old m_nSingleColorKBBLOnOff = " + m_nSingleColorKBBLOnOff, "BacklightPowerChanged", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MySetting\\MySettingManager.cs", 1430);
		if (m_nSingleColorKBBLOnOff == 0)
		{
			m_nSingleColorKBBLOnOff = 1;
			MySettingParams.sSingleColorKBBL_Status = "SINGLE_COLOR_KBBL_STATUS_ON";
		}
		else
		{
			m_nSingleColorKBBLOnOff = 0;
			MySettingParams.sSingleColorKBBL_Status = "SINGLE_COLOR_KBBL_STATUS_OFF";
		}
		LogCtrl.TraceMessage("new m_nSingleColorKBBLOnOff = " + m_nSingleColorKBBLOnOff, "BacklightPowerChanged", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MySetting\\MySettingManager.cs", 1441);
		SingleColorKeyboard.SetSingleColorKBBLOnOff_Registry(m_nSingleColorKBBLOnOff);
		SingleColorKeyboard.SetPower(m_nSingleColorKBBLOnOff);
		UpdateStatusToClient(1);
	}

	private void GetStatus_LightBar()
	{
		if (CustomizeInfo.m_sLightbarType == "1")
		{
			byte Data = 0;
			EcCtrl.Read(GetType().Name, 1896, ref Data);
			if ((Data & 2) == 2)
			{
				MySettingParams.sLightBar_Status = "LIGHTBAR_STATUS_ON";
			}
			else
			{
				MySettingParams.sLightBar_Status = "LIGHTBAR_STATUS_OFF";
			}
		}
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

	private void LightBar_Trigger()
	{
		LogCtrl.Write(m_className + "[LightBar_Trigger]");
		byte Data = 0;
		EcCtrl.Read(GetType().Name, 1895, ref Data);
		byte b = (byte)(Convert.ToUInt64(Data) & 0xFD);
		EcCtrl.Write(GetType().Name, 1895, (byte)(2 + b));
	}

	internal byte ConvertToByte(BitArray bits)
	{
		_ = bits.Count;
		_ = 8;
		byte[] array = new byte[1];
		bits.CopyTo(array, 0);
		return array[0];
	}

	private void USB_Charger_ON()
	{
		LogCtrl.Write(m_className + "[USB_Charger_ON]");
		byte Data = 0;
		EcCtrl.Read(GetType().Name, 1895, ref Data);
		BitArray bitArray = new BitArray(new byte[1] { Data });
		bitArray[4] = true;
		EcCtrl.Write(GetType().Name, 1895, ConvertToByte(bitArray));
	}

	private void USB_Charger_OFF()
	{
		LogCtrl.Write(m_className + "[USB_Charger_OFF]");
		byte Data = 0;
		EcCtrl.Read(GetType().Name, 1895, ref Data);
		BitArray bitArray = new BitArray(new byte[1] { Data });
		bitArray[4] = false;
		EcCtrl.Write(GetType().Name, 1895, ConvertToByte(bitArray));
	}

	private void TouchpadToggle_ON()
	{
		LogCtrl.Write(m_className + "[TouchpadToggle_ON]");
		byte Data = 0;
		EcCtrl.Read(GetType().Name, 1958, ref Data);
		byte data = (byte)(Convert.ToUInt64(Data) & 0xBF);
		EcCtrl.Write(GetType().Name, 1958, data);
		if (m_sBiosProjectID != null && m_sBiosProjectID == "IDM")
		{
			MyTouchPadCtrl.Instance.m_Manager.HalfToggle_Enable();
		}
	}

	private void TouchpadToggle_OFF()
	{
		LogCtrl.Write(m_className + "[TouchpadToggle_OFF]");
		byte Data = 0;
		EcCtrl.Read(GetType().Name, 1958, ref Data);
		byte b = (byte)(Convert.ToUInt64(Data) & 0xBF);
		EcCtrl.Write(GetType().Name, 1958, (byte)(64 + b));
		if (m_sBiosProjectID != null && m_sBiosProjectID == "IDM")
		{
			MyTouchPadCtrl.Instance.m_Manager.HalfToggle_Disable();
		}
	}

	private void SetFnKey(int status)
	{
		byte Data = 0;
		EcCtrl.Read(m_className, 1870, ref Data);
		byte b = (byte)Convert.ToUInt64(Data);
		b = ((status != 1) ? ((byte)(b & 0xEF)) : ((byte)(b | 0x10)));
		EcCtrl.Write(m_className, 1870, b);
	}

	private void SetNVCtrlPanel_AutoSelect()
	{
		LogCtrl.Write(m_className + "[SetNVCtrlPanel_AutoSelect]");
		try
		{
			NVControlSetting.SetNVCtrlPanel(0);
		}
		catch (Exception ex)
		{
			LogCtrl.Write(m_className + $"[SetNVCtrlPanel_AutoSelect] Exception: {ex.Message}");
		}
	}

	private void SetNVCtrlPanel_HighPerformance()
	{
		LogCtrl.Write(m_className + "[SetNVCtrlPanel_HighPerformance]");
		try
		{
			NVControlSetting.SetNVCtrlPanel(1);
		}
		catch (Exception ex)
		{
			LogCtrl.Write(m_className + $"[SetNVCtrlPanel_HighPerformance] Exception: {ex.Message}");
		}
	}

	public virtual void Resume()
	{
		Write_Support_BYTE();
		LoadRegistry();
		Init();
		GetStatus_LightBar();
	}

	private void Write_Support_BYTE()
	{
		byte Data = 0;
		EcCtrl.Read(GetType().Name, 1894, ref Data);
		byte data = (byte)(Convert.ToUInt64(Data) | 3);
		EcCtrl.Write(GetType().Name, 1894, data);
	}

	private void SetCloseTimer(int Mins)
	{
		MySettingParams.sCloseTimer = Mins.ToString();
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath, "CloseTimer", Mins, RegistryValueKind.DWord);
	}

	private void SetUSBChargerREG(int mode)
	{
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath, "USBCharger", mode, RegistryValueKind.DWord);
	}

	private void SetNVCtrlPanelREG(int mode)
	{
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath, "DGpuPowerManagement", mode, RegistryValueKind.DWord);
	}

	private void SetOSDHiddenREG(int mode)
	{
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath, "OSDHidden", mode, RegistryValueKind.DWord);
	}

	private void SetTouchpadToggleREG(int mode)
	{
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath, "TouchpadToggle", mode, RegistryValueKind.DWord);
	}

	public virtual void SetWinKeyREG(int mode)
	{
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath, "WinKeyLock", mode, RegistryValueKind.DWord);
	}

	private void DisableGamingMode()
	{
		MySettingParams.sDisplayFeatureStatus = "DISPLAY_FEATURE_STATUS_ON";
		SetDisplayFeatureStatus(1);
		SetDisplayStdandardMode();
		MySettingParams.sWinKey_Status = "WINKEY_STATUS_UNLOCK";
		SetWinKey(0);
		SetWinKeyREG(0);
	}

	private void EnableGamingMode()
	{
		MySettingParams.sDisplayFeatureStatus = "DISPLAY_FEATURE_STATUS_ON";
		SetDisplayFeatureStatus(2);
		SetDisplayGamingModeFromReg();
		MySettingParams.sWinKey_Status = "WINKEY_STATUS_LOCK";
		SetWinKey(1);
		SetWinKeyREG(1);
	}

	private void LoadDisplayFeaturesRegistry()
	{
		try
		{
			int num = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures", "DisplayFeatureStatus", 1);
			int num2 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures", "DisplayMode", 1);
			int num3 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures", "ColorCalibration", 0);
			if (num == 1)
			{
				MySettingParams.sDisplayFeatureStatus = "DISPLAY_FEATURE_STATUS_ON";
				switch (num2)
				{
				case 1:
					MySettingParams.sDisplayMode = "DISPLAY_STANDARD_MODE";
					break;
				case 2:
					MySettingParams.sDisplayMode = "DISPLAY_GAMING_MODE";
					break;
				case 3:
					MySettingParams.sDisplayMode = "DISPLAY_VIDEO_MODE";
					break;
				case 4:
					MySettingParams.sDisplayMode = "DISPLAY_READ_MODE";
					break;
				case 5:
					MySettingParams.sDisplayMode = "DISPLAY_CUSTOMIZED_MODE";
					break;
				}
			}
			else
			{
				MySettingParams.sDisplayFeatureStatus = "DISPLAY_FEATURE_STATUS_OFF";
				MySettingParams.sDisplayMode = "DISPLAY_STANDARD_MODE";
			}
			if (num3 == 0)
			{
				MySettingParams.sColorCalibration_Status = "COLOR_CALIBRATION_OFF";
			}
			else
			{
				MySettingParams.sColorCalibration_Status = "COLOR_CALIBRATION_ON";
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
		MySettingParams.sDisplayFeatureStatus = "DISPLAY_FEATURE_STATUS_ON";
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures", "DisplayMode", 1, RegistryValueKind.DWord);
		MySettingParams.sDisplayMode = "DISPLAY_STANDARD_MODE";
		SetColorCalibrationReg(0);
		MySettingParams.sColorCalibration_Status = "COLOR_CALIBRATION_OFF";
	}

	private void SetDisplayMode()
	{
		if (MySettingParams.sDisplayFeatureStatus == "DISPLAY_FEATURE_STATUS_ON")
		{
			switch (MySettingParams.sDisplayMode)
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
			MySettingParams.sDisplayFeatureStatus = "DISPLAY_FEATURE_STATUS_OFF";
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures", "DisplayFeatureStatus", 0, RegistryValueKind.DWord);
			break;
		case 0:
			MySettingParams.sDisplayFeatureStatus = "DISPLAY_FEATURE_STATUS_ON";
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures", "DisplayFeatureStatus", 1, RegistryValueKind.DWord);
			break;
		case 1:
			MySettingParams.sDisplayMode = "DISPLAY_STANDARD_MODE";
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures", "DisplayMode", 1, RegistryValueKind.DWord);
			break;
		case 2:
			MySettingParams.sDisplayMode = "DISPLAY_GAMING_MODE";
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures", "DisplayMode", 2, RegistryValueKind.DWord);
			break;
		case 3:
			MySettingParams.sDisplayMode = "DISPLAY_VIDEO_MODE";
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures", "DisplayMode", 3, RegistryValueKind.DWord);
			break;
		case 4:
			MySettingParams.sDisplayMode = "DISPLAY_READ_MODE";
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures", "DisplayMode", 4, RegistryValueKind.DWord);
			break;
		case 5:
			MySettingParams.sDisplayMode = "DISPLAY_CUSTOMIZED_MODE";
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

	private void StartICCProfile()
	{
		ColorProfileInfo.UpdateICCProfileInfo();
		if (ColorProfileInfo.m_ICCProfileInfo.bFileExist)
		{
			OnColorCalibration(ColorProfileInfo.m_ICCProfileInfo.sFileName);
			return;
		}
		if (NetworkInterface.GetIsNetworkAvailable())
		{
			LogCtrl.Write(m_className + "[StartICCProfile] Download profile.");
			DownloadProfile(ColorProfileInfo.strSerialNumber);
			return;
		}
		MySettingParams.sColorCalibrationResultCode = "2";
		LogCtrl.Write(m_className + $"[StartICCProfile] ResultCode: {MySettingParams.sColorCalibrationResultCode}({ResultCodeString(MySettingParams.sColorCalibrationResultCode)})");
		UpdateStatusToClient(1);
		ReSetResultCode();
	}

	private void DownloadProfile(string filename)
	{
		if (!Directory.Exists(ColorProfileInfo.m_ICCProfilePath))
		{
			Directory.CreateDirectory(ColorProfileInfo.m_ICCProfilePath);
		}
		for (int i = 0; i < ColorProfileInfo.m_ICCProfileLists.Count(); i++)
		{
			WebClient webClient = new WebClient();
			webClient.DownloadFileCompleted += DownloadProfile_DownloadFileCompleted;
			webClient.DownloadFileTaskAsync(new Uri(ColorProfileInfo.m_ICM_Server + ColorProfileInfo.m_ICCProfileLists[i].ToString()), ColorProfileInfo.m_ICCProfilePath + "\\" + ColorProfileInfo.m_ICCProfileLists[i].ToString() + ".icm");
		}
	}

	private void DownloadProfile_DownloadProgressChanged(object sender, DownloadProgressChangedEventArgs e)
	{
	}

	private void DownloadProfile_DownloadFileCompleted(object sender, AsyncCompletedEventArgs e)
	{
		LogCtrl.Write("---------------" + LogCtrl.GetTime() + "---------------");
		_ = string.Empty;
		if (e.Error == null)
		{
			LogCtrl.Write(m_className + "[DownloadProfile_DownloadFileCompleted] OK");
			{
				foreach (string iCCProfileList in ColorProfileInfo.m_ICCProfileLists)
				{
					if (new FileInfo(ColorProfileInfo.m_ICCProfilePath + "\\" + iCCProfileList.ToString() + ".icm").Length != 0L)
					{
						OnColorCalibration(iCCProfileList.ToString());
					}
				}
				return;
			}
		}
		LogCtrl.Write(m_className + "[DownloadProfile_DownloadFileCompleted] AbsoluteUri: " + ((Uri)((TaskCompletionSource<object>)e.UserState).Task.AsyncState).AbsoluteUri);
		if ((HttpWebResponse)((WebException)e.Error).Response != null)
		{
			if (((HttpWebResponse)((WebException)e.Error).Response).StatusCode == HttpStatusCode.NotFound)
			{
				MySettingParams.sColorCalibrationResultCode = "3";
			}
			else
			{
				MySettingParams.sColorCalibrationResultCode = "7";
			}
			Console.WriteLine(m_className + $"[DownloadProfile_DownloadFileCompleted] ResultCode: {MySettingParams.sColorCalibrationResultCode}({ResultCodeString(MySettingParams.sColorCalibrationResultCode)}), HttpStatusCode: {((HttpWebResponse)((WebException)e.Error).Response).StatusCode}");
			LogCtrl.Write(m_className + $"[DownloadProfile_DownloadFileCompleted] ResultCode: {MySettingParams.sColorCalibrationResultCode}({ResultCodeString(MySettingParams.sColorCalibrationResultCode)}), HttpStatusCode: {((HttpWebResponse)((WebException)e.Error).Response).StatusCode}");
		}
		else
		{
			MySettingParams.sColorCalibrationResultCode = "7";
			Console.WriteLine(m_className + $"[DownloadProfile_DownloadFileCompleted] ResultCode: {MySettingParams.sColorCalibrationResultCode}({ResultCodeString(MySettingParams.sColorCalibrationResultCode)}), e.Error.Message: {e.Error.Message.ToString()}, status: {((WebException)e.Error).Status.ToString()}");
			LogCtrl.Write(m_className + $"[DownloadProfile_DownloadFileCompleted] ResultCode: {MySettingParams.sColorCalibrationResultCode}({ResultCodeString(MySettingParams.sColorCalibrationResultCode)}), e.Error.Message: {e.Error.Message.ToString()}, status: {((WebException)e.Error).Status.ToString()}");
		}
		UpdateStatusToClient(1);
		ReSetResultCode();
	}

	private void UnistallCalibration()
	{
		if (m_ICCProfileControl == null)
		{
			m_ICCProfileControl = new ColorProfileControl();
		}
		foreach (string iCCProfileList in ColorProfileInfo.m_ICCProfileLists)
		{
			string text = ColorProfileInfo.m_ICCProfilePath + "\\" + iCCProfileList.ToString() + ".icm";
			if (File.Exists(text) && new FileInfo(text).Length != 0L)
			{
				m_ICCProfileControl.UnInstallProfile(text, bDelete: true);
			}
		}
	}

	private void OnColorCalibration(string filename)
	{
		string text = ColorProfileInfo.m_ICCProfilePath + "\\" + filename + ".icm";
		if (m_ICCProfileControl == null)
		{
			m_ICCProfileControl = new ColorProfileControl();
		}
		m_ICCProfileControl.SetCalibrationState(Enable: true);
		m_ICCProfileControl.UnInstallProfile(text, bDelete: true);
		m_ICCProfileControl.InstallProfile(text);
		if (m_ICCProfileControl.SetMonitorProfile(text))
		{
			new Brightness().SetBrightness(g_colibrationBrightness);
			MySettingParams.sColorCalibrationResultCode = "1";
		}
		else
		{
			MySettingParams.sColorCalibrationResultCode = "4";
		}
		UpdatePrams(MySettingParams.sColorCalibrationResultCode);
		LogCtrl.Write(m_className + $"[OnColorCalibration] ResultCode: {MySettingParams.sColorCalibrationResultCode}({ResultCodeString(MySettingParams.sColorCalibrationResultCode)}), ColorCalibration_Status: {MySettingParams.sColorCalibration_Status}, DisplayFeatureStatus: {MySettingParams.sDisplayFeatureStatus}");
		UpdateStatusToClient(1);
		ReSetResultCode();
	}

	private void DisColorCalibration()
	{
		bool flag = false;
		string empty = string.Empty;
		ColorProfileControl colorProfileControl = new ColorProfileControl();
		foreach (string iCCProfileList in ColorProfileInfo.m_ICCProfileLists)
		{
			empty = ColorProfileInfo.m_ICCProfilePath + "\\" + iCCProfileList.ToString() + ".icm";
			if (new FileInfo(empty).Length != 0L)
			{
				flag = colorProfileControl.DissociateProfile(empty);
				LogCtrl.Write(m_className + $"[DisColorCalibration] result: {flag}");
			}
		}
	}

	private void UpdatePrams(string result)
	{
		switch (result)
		{
		case "1":
			SetDisplayFeatureStatus(-1);
			MySettingParams.sColorCalibration_Status = "COLOR_CALIBRATION_ON";
			SetColorCalibrationReg(1);
			break;
		case "2":
		case "3":
		case "4":
		case "5":
		case "6":
		case "7":
			SetDisplayFeatureStatus(0);
			break;
		}
	}

	private void ReSetResultCode()
	{
		int nCustomizeTarget = m_nCustomizeTarget;
		if (nCustomizeTarget != 4 && nCustomizeTarget != 17)
		{
			MySettingParams.sColorCalibrationResultCode = "0";
		}
	}

	private string ResultCodeString(string code)
	{
		return code switch
		{
			"0" => "Ready", 
			"1" => "Finish", 
			"2" => "NetworkFail", 
			"3" => "SnIsUnsupported", 
			"4" => "ColorCalibrationFail", 
			"5" => "WebClientRequestFail", 
			"6" => "ConnectServerFail", 
			"7" => "WebClientUnknownFail", 
			_ => "", 
		};
	}

	private void SetColorCalibrationReg(int mode)
	{
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures", "ColorCalibration", mode, RegistryValueKind.DWord);
	}

	private void CheckForInternetConnection()
	{
		MySettingParams.sColorCalibrationResultCode = "2";
		ReportAvailability();
		NetworkStatus.AvailabilityChanged += DoAvailabilityChanged;
	}

	private void DoAvailabilityChanged(object sender, NetworkStatusChangedArgs e)
	{
		ColorProfileInfo.UpdateICCProfileInfo();
		if (ColorProfileInfo.m_ICCProfileInfo.bFileExist)
		{
			NetworkStatus.AvailabilityChanged -= DoAvailabilityChanged;
		}
		ReportAvailability();
	}

	private void ReportAvailability()
	{
		if (NetworkStatus.IsAvailable)
		{
			LogCtrl.Write("---------------" + LogCtrl.GetTime() + "---------------");
			LogCtrl.Write(m_className + "[ReportAvailability] Network is available, Download profile.");
			DownloadProfile(ColorProfileInfo.strSerialNumber);
		}
	}

	public virtual void Uninstall()
	{
		LogCtrl.Write(m_className + "[Uninstall] set DISPLAY_STANDARD_MODE");
		SetDisplayStdandardMode();
		if (MySettingParams.sAcRecoverySwitch_Support == "Support")
		{
			NvramVariable.SetFwVars("ACRecoveryStatus", 0);
		}
	}

	public virtual void DeleteAllPowerPlan()
	{
	}

	public virtual void Restore()
	{
		LoadDefaultRegistry();
		LoadDefaultDisplayFeaturesRegistry();
		DisplayFeatureCtrl.Instance.LoadDefaultRegistry();
		Init();
	}
}
