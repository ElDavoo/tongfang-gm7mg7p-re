using System;
using System.Reflection;
using GCUService.MySetting;
using Microsoft.Win32;
using Utility;

namespace MyControlCenter.MySetting.DisplayFeature;

internal class DisplayFeatureManager_Intel : DisplayFeatureManager
{
	private string m_className = "[" + MethodBase.GetCurrentMethod().DeclaringType.Name + "] ";

	private string m_sRegistryPath = "\\OEM\\GamingCenter2\\MySetting";

	private int Brightness = 90;

	private int Red = 128;

	private int Green = 128;

	private int Blue = 128;

	private int ColorTemp = 4200;

	private int Contrast = 50;

	private string m_sBrightness;

	private string m_sRed;

	private string m_sGreen;

	private string m_sBlue;

	private string m_sColorTemp;

	private string m_sContrast;

	public override void LoadRegistry()
	{
		try
		{
			string sBrightness = (string)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures\\GamingMode", "Brightness", Brightness);
			string sRed = (string)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures\\GamingMode", "Red", Red);
			string sGreen = (string)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures\\GamingMode", "Green", Green);
			string sBlue = (string)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures\\GamingMode", "Blue", Blue);
			string sColorTemp = (string)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures\\GamingMode", "ColorTemp", ColorTemp);
			string sContrast = (string)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures\\GamingMode", "Contrast", Contrast);
			string sBrightness2 = (string)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures\\VideoMode", "Brightness", "100");
			string sColorTemp2 = (string)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures\\VideoMode", "ColorTemp", ColorTemp);
			string sBrightness3 = (string)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures\\ReadMode", "Brightness", Brightness);
			string sBlue2 = (string)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures\\ReadMode", "Blue", "0");
			string sColorTemp3 = (string)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures\\ReadMode", "ColorTemp", ColorTemp);
			string sBrightness4 = (string)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures\\CustomizedMode", "Brightness", Brightness);
			string sRed2 = (string)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures\\CustomizedMode", "Red", Red);
			string sGreen2 = (string)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures\\CustomizedMode", "Green", Green);
			string sBlue3 = (string)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures\\CustomizedMode", "Blue", Blue);
			string sColorTemp4 = (string)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures\\CustomizedMode", "ColorTemp", ColorTemp);
			string sContrast2 = (string)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures\\CustomizedMode", "Contrast", Contrast);
			switch (MySettingParams_Intel.sDisplayMode)
			{
			case "DISPLAY_STANDARD_MODE":
				m_sBrightness = "90";
				m_sRed = "128";
				m_sGreen = "128";
				m_sBlue = "128";
				m_sColorTemp = "4200";
				m_sContrast = "50";
				break;
			case "DISPLAY_GAMING_MODE":
				m_sBrightness = sBrightness;
				m_sRed = sRed;
				m_sGreen = sGreen;
				m_sBlue = sBlue;
				m_sColorTemp = sColorTemp;
				m_sContrast = sContrast;
				break;
			case "DISPLAY_VIDEO_MODE":
				m_sBrightness = sBrightness2;
				m_sRed = "128";
				m_sGreen = "128";
				m_sBlue = "128";
				m_sColorTemp = sColorTemp2;
				m_sContrast = "50";
				break;
			case "DISPLAY_READ_MODE":
				m_sBrightness = sBrightness3;
				m_sRed = "128";
				m_sGreen = "128";
				m_sBlue = sBlue2;
				m_sColorTemp = sColorTemp3;
				m_sContrast = "50";
				break;
			case "DISPLAY_CUSTOMIZED_MODE":
				m_sBrightness = sBrightness4;
				m_sRed = sRed2;
				m_sGreen = sGreen2;
				m_sBlue = sBlue3;
				m_sColorTemp = sColorTemp4;
				m_sContrast = sContrast2;
				break;
			}
			GamingModePara.sBrightness = sBrightness;
			GamingModePara.sRed = sRed;
			GamingModePara.sGreen = sGreen;
			GamingModePara.sBlue = sBlue;
			GamingModePara.sColorTemp = sColorTemp;
			GamingModePara.sContrast = sContrast;
			VideoModePara.sBrightness = sBrightness2;
			VideoModePara.sColorTemp = sColorTemp2;
			ReadModePara.sBrightness = sBrightness3;
			ReadModePara.sBlue = sBlue2;
			ReadModePara.sColorTemp = sColorTemp3;
			CutomizedModePara.sBrightness = sBrightness4;
			CutomizedModePara.sRed = sRed2;
			CutomizedModePara.sGreen = sGreen2;
			CutomizedModePara.sBlue = sBlue3;
			CutomizedModePara.sColorTemp = sColorTemp4;
			CutomizedModePara.sContrast = sContrast2;
		}
		catch
		{
			LoadDefaultRegistry();
		}
	}

	public override void LoadDefaultRegistry()
	{
		RecoveryDisplayGamingModeReg();
		RecoveryDisplayVideoModeReg();
		RecoveryDisplayReadModeReg();
		RecoveryDisplayCustomizedModeReg();
	}

	public override void Default(string mode)
	{
		switch (mode)
		{
		case "DISPLAY_GAMING_MODE_RECOVERY":
			RecoveryDisplayGamingModeReg();
			Set(90, 128, 128, 128, 4200, 50);
			break;
		case "DISPLAY_VIDEO_MODE_RECOVERY":
			RecoveryDisplayVideoModeReg();
			Set(100, 128, 128, 128, 4200, 50);
			break;
		case "DISPLAY_READ_MODE_RECOVERY":
			RecoveryDisplayReadModeReg();
			Set(90, 128, 128, 0, 4200, 50);
			break;
		case "DISPLAY_CUSTOMIZED_MODE_RECOVERY":
			RecoveryDisplayCustomizedModeReg();
			Set(90, 128, 128, 128, 4200, 50);
			break;
		}
	}

	public override void SetDisplayStdandardMode()
	{
		LogCtrl.Write(m_className + $"[SetDisplayStdandardMode] Brightness[{m_sBrightness}], Red[{m_sRed}, Green[{m_sGreen}, Blue[{m_sBlue}, ColorTemp[{m_sColorTemp}, Contrast[{m_sContrast}]");
		m_sBrightness = "90";
		m_sRed = "128";
		m_sGreen = "128";
		m_sBlue = "128";
		m_sColorTemp = "4200";
		m_sContrast = "50";
		Set(90, 128, 128, 128, 4200, 50);
	}

	public override void SetDisplayGamingModeFromReg()
	{
		string sBrightness = (string)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures\\GamingMode", "Brightness", Brightness);
		string sRed = (string)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures\\GamingMode", "Red", Red);
		string sGreen = (string)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures\\GamingMode", "Green", Green);
		string sBlue = (string)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures\\GamingMode", "Blue", Blue);
		string sColorTemp = (string)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures\\GamingMode", "ColorTemp", ColorTemp);
		string sContrast = (string)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures\\GamingMode", "Contrast", Contrast);
		m_sBrightness = sBrightness;
		m_sRed = sRed;
		m_sGreen = sGreen;
		m_sBlue = sBlue;
		m_sColorTemp = sColorTemp;
		m_sContrast = sContrast;
		Set(int.Parse(m_sBrightness), int.Parse(m_sRed), int.Parse(m_sGreen), int.Parse(m_sBlue), int.Parse(m_sColorTemp), int.Parse(m_sContrast));
	}

	public override void SetDisplayVideoModeFromReg()
	{
		string sBrightness = (string)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures\\VideoMode", "Brightness", "100");
		string sColorTemp = (string)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures\\VideoMode", "ColorTemp", ColorTemp);
		m_sBrightness = sBrightness;
		m_sRed = "128";
		m_sGreen = "128";
		m_sBlue = "128";
		m_sColorTemp = sColorTemp;
		m_sContrast = "50";
		Set(int.Parse(m_sBrightness), int.Parse(m_sRed), int.Parse(m_sGreen), int.Parse(m_sBlue), int.Parse(m_sColorTemp), int.Parse(m_sContrast));
	}

	public override void SetDisplayReadModeFromReg()
	{
		string sBrightness = (string)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures\\ReadMode", "Brightness", Brightness);
		string sBlue = (string)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures\\ReadMode", "Blue", "0");
		string sColorTemp = (string)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures\\ReadMode", "ColorTemp", ColorTemp);
		m_sBrightness = sBrightness;
		m_sRed = "128";
		m_sGreen = "128";
		m_sBlue = sBlue;
		m_sColorTemp = sColorTemp;
		m_sContrast = "50";
		Set(int.Parse(m_sBrightness), int.Parse(m_sRed), int.Parse(m_sGreen), int.Parse(m_sBlue), int.Parse(m_sColorTemp), int.Parse(m_sContrast));
	}

	public override void SetDisplayCustomizedModeFromReg()
	{
		string sBrightness = (string)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures\\CustomizedMode", "Brightness", Brightness);
		string sRed = (string)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures\\CustomizedMode", "Red", Red);
		string sGreen = (string)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures\\CustomizedMode", "Green", Green);
		string sBlue = (string)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures\\CustomizedMode", "Blue", Blue);
		string sColorTemp = (string)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures\\CustomizedMode", "ColorTemp", ColorTemp);
		string sContrast = (string)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures\\CustomizedMode", "Contrast", Contrast);
		m_sBrightness = sBrightness;
		m_sRed = sRed;
		m_sGreen = sGreen;
		m_sBlue = sBlue;
		m_sColorTemp = sColorTemp;
		m_sContrast = sContrast;
		Set(int.Parse(m_sBrightness), int.Parse(m_sRed), int.Parse(m_sGreen), int.Parse(m_sBlue), int.Parse(m_sColorTemp), int.Parse(m_sContrast));
	}

	public override void SetDisplayGamingModeValue(dynamic tmp2)
	{
		string text = tmp2["Brightness"];
		string text2 = tmp2["Red"];
		string text3 = tmp2["Green"];
		string text4 = tmp2["Blue"];
		string text5 = tmp2["ColorTemp"];
		string text6 = tmp2["Contrast"];
		if (int.Parse(text) >= 0 && int.Parse(text) <= 100 && int.Parse(text2) >= 0 && int.Parse(text2) <= 255 && int.Parse(text3) >= 0 && int.Parse(text3) <= 255 && int.Parse(text4) >= 0 && int.Parse(text4) <= 255 && int.Parse(text5) >= 2000 && int.Parse(text5) <= 4200 && int.Parse(text6) >= 0 && int.Parse(text6) <= 100)
		{
			m_sBrightness = text;
			m_sRed = text2;
			m_sGreen = text3;
			m_sBlue = text4;
			m_sColorTemp = text5;
			m_sContrast = text6;
			GamingModePara.sBrightness = text;
			GamingModePara.sRed = text2;
			GamingModePara.sGreen = text3;
			GamingModePara.sBlue = text4;
			GamingModePara.sColorTemp = text5;
			GamingModePara.sContrast = text6;
			Set(int.Parse(text), int.Parse(text2), int.Parse(text3), int.Parse(text4), int.Parse(text5), int.Parse(text6));
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures\\GamingMode", "Brightness", text, RegistryValueKind.String);
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures\\GamingMode", "Red", text2, RegistryValueKind.String);
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures\\GamingMode", "Green", text3, RegistryValueKind.String);
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures\\GamingMode", "Blue", text4, RegistryValueKind.String);
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures\\GamingMode", "ColorTemp", text5, RegistryValueKind.String);
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures\\GamingMode", "Contrast", text6, RegistryValueKind.String);
		}
	}

	public override void SetDisplayVideoModeValue(dynamic tmp2)
	{
		string text = tmp2["Brightness"];
		string text2 = tmp2["ColorTemp"];
		if (int.Parse(text) >= 0 && int.Parse(text) <= 100 && int.Parse(text2) >= 2000 && int.Parse(text2) <= 4200)
		{
			m_sBrightness = text;
			m_sRed = "128";
			m_sGreen = "128";
			m_sBlue = "128";
			m_sColorTemp = text2;
			m_sContrast = "50";
			VideoModePara.sBrightness = text;
			VideoModePara.sColorTemp = text2;
			Set(int.Parse(text), 128, 128, 128, int.Parse(text2), 50);
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures\\VideoMode", "Brightness", text, RegistryValueKind.String);
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures\\VideoMode", "ColorTemp", text2, RegistryValueKind.String);
		}
	}

	public override void SetDisplayReadModeValue(dynamic tmp2)
	{
		string text = tmp2["Brightness"];
		string text2 = tmp2["Blue"];
		string text3 = tmp2["ColorTemp"];
		if (int.Parse(text) >= 0 && int.Parse(text) <= 100 && int.Parse(text2) >= 0 && int.Parse(text2) <= 255 && int.Parse(text3) >= 2000 && int.Parse(text3) <= 4200)
		{
			m_sBrightness = text;
			m_sRed = "128";
			m_sGreen = "128";
			m_sBlue = text2;
			m_sColorTemp = text3;
			m_sContrast = "50";
			ReadModePara.sBrightness = text;
			ReadModePara.sBlue = text2;
			ReadModePara.sColorTemp = text3;
			Set(int.Parse(text), 128, 128, int.Parse(text2), int.Parse(text3), 50);
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures\\ReadMode", "Brightness", text, RegistryValueKind.String);
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures\\ReadMode", "Blue", text2, RegistryValueKind.String);
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures\\ReadMode", "ColorTemp", text3, RegistryValueKind.String);
		}
	}

	public override void SetDisplayCustomizedModeValue(dynamic tmp2)
	{
		string text = tmp2["Brightness"];
		string text2 = tmp2["Red"];
		string text3 = tmp2["Green"];
		string text4 = tmp2["Blue"];
		string text5 = tmp2["ColorTemp"];
		string text6 = tmp2["Contrast"];
		if (int.Parse(text) >= 0 && int.Parse(text) <= 100 && int.Parse(text2) >= 0 && int.Parse(text2) <= 255 && int.Parse(text3) >= 0 && int.Parse(text3) <= 255 && int.Parse(text4) >= 0 && int.Parse(text4) <= 255 && int.Parse(text5) >= 2000 && int.Parse(text5) <= 4200 && int.Parse(text6) >= 0 && int.Parse(text6) <= 100)
		{
			m_sBrightness = text;
			m_sRed = text2;
			m_sGreen = text3;
			m_sBlue = text4;
			m_sColorTemp = text5;
			m_sContrast = text6;
			CutomizedModePara.sBrightness = text;
			CutomizedModePara.sRed = text2;
			CutomizedModePara.sGreen = text3;
			CutomizedModePara.sBlue = text4;
			CutomizedModePara.sColorTemp = text5;
			CutomizedModePara.sContrast = text6;
			Set(int.Parse(text), int.Parse(text2), int.Parse(text3), int.Parse(text4), int.Parse(text5), int.Parse(text6));
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures\\CustomizedMode", "Brightness", text, RegistryValueKind.String);
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures\\CustomizedMode", "Red", text2, RegistryValueKind.String);
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures\\CustomizedMode", "Green", text3, RegistryValueKind.String);
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures\\CustomizedMode", "Blue", text4, RegistryValueKind.String);
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures\\CustomizedMode", "ColorTemp", text5, RegistryValueKind.String);
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures\\CustomizedMode", "Contrast", text6, RegistryValueKind.String);
		}
	}

	private void RecoveryDisplayGamingModeReg()
	{
		m_sBrightness = "90";
		m_sRed = "128";
		m_sGreen = "128";
		m_sBlue = "128";
		m_sColorTemp = "4200";
		m_sContrast = "50";
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures\\GamingMode", "Brightness", m_sBrightness, RegistryValueKind.String);
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures\\GamingMode", "Red", m_sRed, RegistryValueKind.String);
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures\\GamingMode", "Green", m_sGreen, RegistryValueKind.String);
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures\\GamingMode", "Blue", m_sBlue, RegistryValueKind.String);
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures\\GamingMode", "ColorTemp", m_sColorTemp, RegistryValueKind.String);
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures\\GamingMode", "Contrast", m_sContrast, RegistryValueKind.String);
		GamingModePara.sBrightness = m_sBrightness;
		GamingModePara.sRed = m_sRed;
		GamingModePara.sGreen = m_sGreen;
		GamingModePara.sBlue = m_sBlue;
		GamingModePara.sColorTemp = m_sColorTemp;
		GamingModePara.sContrast = m_sContrast;
	}

	private void RecoveryDisplayVideoModeReg()
	{
		m_sColorTemp = "4200";
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures\\VideoMode", "Brightness", "100", RegistryValueKind.String);
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures\\VideoMode", "ColorTemp", m_sColorTemp, RegistryValueKind.String);
		VideoModePara.sBrightness = "100";
		VideoModePara.sColorTemp = m_sColorTemp;
	}

	private void RecoveryDisplayReadModeReg()
	{
		m_sBrightness = "90";
		m_sColorTemp = "4200";
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures\\ReadMode", "Brightness", m_sBrightness, RegistryValueKind.String);
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures\\ReadMode", "Blue", "0", RegistryValueKind.String);
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures\\ReadMode", "ColorTemp", m_sColorTemp, RegistryValueKind.String);
		ReadModePara.sBrightness = m_sBrightness;
		ReadModePara.sBlue = "0";
		ReadModePara.sColorTemp = m_sColorTemp;
	}

	private void RecoveryDisplayCustomizedModeReg()
	{
		m_sBrightness = "90";
		m_sRed = "128";
		m_sGreen = "128";
		m_sBlue = "128";
		m_sColorTemp = "4200";
		m_sContrast = "50";
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures\\CustomizedMode", "Brightness", m_sBrightness, RegistryValueKind.String);
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures\\CustomizedMode", "Red", m_sRed, RegistryValueKind.String);
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures\\CustomizedMode", "Green", m_sGreen, RegistryValueKind.String);
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures\\CustomizedMode", "Blue", m_sBlue, RegistryValueKind.String);
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures\\CustomizedMode", "ColorTemp", m_sColorTemp, RegistryValueKind.String);
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath + "\\DisplayFeatures\\CustomizedMode", "Contrast", m_sContrast, RegistryValueKind.String);
		CutomizedModePara.sBrightness = m_sBrightness;
		CutomizedModePara.sRed = m_sRed;
		CutomizedModePara.sGreen = m_sGreen;
		CutomizedModePara.sBlue = m_sBlue;
		CutomizedModePara.sColorTemp = m_sColorTemp;
		CutomizedModePara.sContrast = m_sContrast;
	}

	private void SetGamma(int value)
	{
		ColorGamma.SetGamma(value);
		foreach (ConnectedMonitors.MonitorInfo monitor in ConnectedMonitors.Monitors)
		{
			monitor.WithMonitorHdc(delegate(ConnectedMonitors.MonitorInfo m, IntPtr hdc)
			{
				ColorGamma.UpdateRamps(hdc, isIntel: true);
			});
		}
	}

	private void SetContrast(int value)
	{
		ColorGamma.SetContrast(value, isIntel: true);
		foreach (ConnectedMonitors.MonitorInfo monitor in ConnectedMonitors.Monitors)
		{
			monitor.WithMonitorHdc(delegate(ConnectedMonitors.MonitorInfo m, IntPtr hdc)
			{
				ColorGamma.UpdateRamps(hdc, isIntel: true);
			});
		}
	}

	private void SetBrightness(int red, int green, int blue, int nBrightness, int colortemp)
	{
		ColorGamma.SetBrightness(red + (nBrightness - 90) + colortemp * 2, green + (nBrightness - 90) + colortemp / 2, blue + (nBrightness - 90) - colortemp);
		foreach (ConnectedMonitors.MonitorInfo monitor in ConnectedMonitors.Monitors)
		{
			monitor.WithMonitorHdc(delegate(ConnectedMonitors.MonitorInfo m, IntPtr hdc)
			{
				ColorGamma.UpdateRamps(hdc, isIntel: true);
			});
		}
	}

	private void Set(int brightness, int red, int green, int blue, int colortemp, int contrast)
	{
		Contrast = contrast;
		Brightness = brightness;
		Red = red - 128;
		Green = green - 128;
		Blue = blue - 128;
		ColorTemp = Math.Abs((colortemp - 2000) / 55 - 40);
		SetContrast(Contrast);
		SetBrightness(Red, Green, Blue, Brightness, ColorTemp);
	}
}
