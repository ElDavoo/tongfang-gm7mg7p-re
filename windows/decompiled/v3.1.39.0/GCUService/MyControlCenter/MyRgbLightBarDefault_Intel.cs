using System;
using Microsoft.Win32;
using MyECIO;
using Utility;

namespace MyControlCenter;

internal class MyRgbLightBarDefault_Intel
{
	private static MyEcCtrl EcCtrl = MyEcCtrl.Instance;

	private static string m_ClassName = "MyRgbLightBarDefault";

	private static string m_path = "\\OEM\\GamingCenter2\\MyLightBar";

	private static int m_nProjectID = 0;

	public static uint m_nRedLevel = 100u;

	public static uint m_nGreenLevel = 100u;

	public static uint m_nBlueLevel = 100u;

	public static uint m_nRedLevel_dc = 0u;

	public static uint m_nGreenLevel_dc = 0u;

	public static uint m_nBlueLevel_dc = 0u;

	public static uint m_nColorful = 0u;

	public static uint m_nColorful_dc = 0u;

	public static uint m_nBreathingLightEffect = 1u;

	public static int m_nSupportRGBLightBarColorful = 1;

	public static int m_nSupportRGBLightBarBreathEffect = 1;

	public static int m_nLightBarOnOff = 1;

	public static void Uninstall()
	{
		m_nProjectID = GetProjectIdFromEC();
		LogCtrl.Write("[Uninstall] m_nProjectID: " + m_nProjectID);
		LogCtrl.Write("[Uninstall] Clear EC");
		EcCtrl.Write(m_ClassName, 1864, 8);
		EcCtrl.Write(m_ClassName, 1865, 0);
		EcCtrl.Write(m_ClassName, 1866, 0);
		EcCtrl.Write(m_ClassName, 1867, 0);
	}

	public static void OnDefault(bool bRecoverEC, int nACLineStatus)
	{
		LogCtrl.Write("---------------" + LogCtrl.GetTime() + "---------------");
		LogCtrl.Write("[OnDefault] Start");
		LoadRegistry();
		if (bRecoverEC)
		{
			if (nACLineStatus == 0)
			{
				WriteECRAM(m_nLightBarOnOff, m_nColorful_dc, m_nBreathingLightEffect, m_nRedLevel, m_nGreenLevel, m_nBlueLevel);
			}
			else
			{
				WriteECRAM(m_nLightBarOnOff, m_nColorful, m_nBreathingLightEffect, m_nRedLevel, m_nGreenLevel, m_nBlueLevel);
			}
		}
		LogCtrl.Write("[OnDefault] End");
	}

	public static void LoadRegistry()
	{
		try
		{
			int nRedLevel = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_path, "RedLevel", 100u);
			int nGreenLevel = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_path, "GreenLevel", 100u);
			int nBlueLevel = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_path, "BlueLevel", 100u);
			int nRedLevel_dc = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_path, "RedLevel_dc", 0u);
			int nGreenLevel_dc = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_path, "GreenLevel_dc", 0u);
			int nBlueLevel_dc = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_path, "BlueLevel_dc", 0u);
			int nColorful = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_path, "Colorful", 0);
			int nColorful_dc = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_path, "Colorful_dc", 0);
			int nBreathingLightEffect = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_path, "BreathingLightEffect", 1);
			int nSupportRGBLightBarColorful = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_path + "\\Features", "SupportRGBLightBarColorful", 1);
			int nSupportRGBLightBarBreathEffect = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_path + "\\Features", "SupportRGBLightBarBreathEffect", 1);
			int nLightBarOnOff = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_path, "LightBarOnOff", 1);
			m_nRedLevel = (uint)nRedLevel;
			m_nGreenLevel = (uint)nGreenLevel;
			m_nBlueLevel = (uint)nBlueLevel;
			m_nRedLevel_dc = (uint)nRedLevel_dc;
			m_nGreenLevel_dc = (uint)nGreenLevel_dc;
			m_nBlueLevel_dc = (uint)nBlueLevel_dc;
			m_nColorful = (uint)nColorful;
			m_nColorful_dc = (uint)nColorful_dc;
			m_nBreathingLightEffect = (uint)nBreathingLightEffect;
			m_nSupportRGBLightBarColorful = nSupportRGBLightBarColorful;
			m_nSupportRGBLightBarBreathEffect = nSupportRGBLightBarBreathEffect;
			m_nLightBarOnOff = nLightBarOnOff;
			if (m_nSupportRGBLightBarColorful == 0)
			{
				m_nColorful = 0u;
			}
			if (m_nSupportRGBLightBarBreathEffect == 0)
			{
				m_nBreathingLightEffect = 0u;
			}
		}
		catch (Exception ex)
		{
			LogCtrl.Write("[LoadRegistry] Exception:" + ex.ToString());
		}
	}

	public static void RecoverReg()
	{
		try
		{
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_path, "LightBarOnOff", m_nLightBarOnOff, RegistryValueKind.DWord);
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_path, "RedLevel", m_nRedLevel, RegistryValueKind.DWord);
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_path, "GreenLevel", m_nGreenLevel, RegistryValueKind.DWord);
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_path, "BlueLevel", m_nBlueLevel, RegistryValueKind.DWord);
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_path, "RedLevel_dc", m_nRedLevel_dc, RegistryValueKind.DWord);
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_path, "GreenLevel_dc", m_nGreenLevel_dc, RegistryValueKind.DWord);
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_path, "BlueLevel_dc", m_nBlueLevel_dc, RegistryValueKind.DWord);
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_path, "Colorful", m_nColorful, RegistryValueKind.DWord);
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_path, "Colorful_dc", m_nColorful_dc, RegistryValueKind.DWord);
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_path, "BreathingLightEffect", m_nBreathingLightEffect, RegistryValueKind.DWord);
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_path + "\\Features", "SupportRGBLightBarColorful", m_nSupportRGBLightBarColorful, RegistryValueKind.DWord);
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_path + "\\Features", "SupportRGBLightBarBreathEffect", m_nSupportRGBLightBarBreathEffect, RegistryValueKind.DWord);
			LogCtrl.Write($"LightBarOnOff = {m_nLightBarOnOff}");
			LogCtrl.Write($"RedLevel = {m_nRedLevel}");
			LogCtrl.Write($"GreenLevel = {m_nGreenLevel}");
			LogCtrl.Write($"BlueLevel = {m_nBlueLevel}");
			LogCtrl.Write($"RedLevel_dc = {m_nRedLevel_dc}");
			LogCtrl.Write($"GreenLevel_dc = {m_nGreenLevel_dc}");
			LogCtrl.Write($"BlueLevel_dc = {m_nBlueLevel_dc}");
			LogCtrl.Write($"Colorful = {m_nColorful}");
			LogCtrl.Write($"Colorful_dc = {m_nColorful_dc}");
			LogCtrl.Write($"BreathingLightEffect = {m_nBreathingLightEffect}");
			LogCtrl.Write($"SupportRGBLightBarColorful = {m_nSupportRGBLightBarColorful}");
			LogCtrl.Write($"SupportRGBLightBarBreathEffect = {m_nSupportRGBLightBarBreathEffect}");
		}
		catch
		{
			LogCtrl.Write("[OnDefaultFromCustomize] Write Data Failed.");
		}
	}

	public static int GetProjectIdFromEC()
	{
		byte Data = 0;
		EcCtrl.Read(m_ClassName, 1856, ref Data);
		return (int)(Convert.ToUInt64(Data) & 0xFF);
	}

	private static void WriteECRAM(int _LightBarOnOff, uint _WelcomeMode, uint _BreathingLightEffect, uint _red_level, uint _green_level, uint _blue_level)
	{
		if (_LightBarOnOff == 1)
		{
			if (_WelcomeMode == 1)
			{
				EcCtrl.Write(m_ClassName, 1864, 128);
				EcCtrl.Write(m_ClassName, 1865, 0);
				EcCtrl.Write(m_ClassName, 1866, 0);
				EcCtrl.Write(m_ClassName, 1867, 0);
			}
			else
			{
				EcCtrl.Write(m_ClassName, 1864, 0);
				EcCtrl.Write(m_ClassName, 1865, (byte)(_red_level * 2));
				EcCtrl.Write(m_ClassName, 1866, (byte)(_green_level * 2));
				EcCtrl.Write(m_ClassName, 1867, (byte)(_blue_level * 2));
			}
		}
		else
		{
			EcCtrl.Write(m_ClassName, 1864, 8);
			EcCtrl.Write(m_ClassName, 1865, 0);
			EcCtrl.Write(m_ClassName, 1866, 0);
			EcCtrl.Write(m_ClassName, 1867, 0);
		}
	}
}
