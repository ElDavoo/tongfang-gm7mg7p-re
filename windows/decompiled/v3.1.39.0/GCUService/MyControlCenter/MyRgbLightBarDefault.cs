using System;
using Microsoft.Win32;
using MyECIO;
using Utility;

namespace MyControlCenter;

internal class MyRgbLightBarDefault
{
	private static MyEcCtrl EcCtrl = MyEcCtrl.Instance;

	private static string m_ClassName = "MyRgbLightBarDefault";

	private static string m_path = "\\OEM\\GamingCenter2\\MyLightBar";

	private static int m_nProjectID = 0;

	public static uint m_nRedLevel = 9u;

	public static uint m_nGreenLevel = 9u;

	public static uint m_nBlueLevel = 9u;

	public static uint m_nRedLevel_dc = 0u;

	public static uint m_nGreenLevel_dc = 0u;

	public static uint m_nBlueLevel_dc = 0u;

	public static uint m_nColorful = 1u;

	public static uint m_nColorful_dc = 0u;

	public static uint m_nBreathingLightEffect = 1u;

	public static int m_nSupportRGBLightBarColorful = 1;

	public static int m_nSupportRGBLightBarBreathEffect = 1;

	public static int m_nLightBarOnOff = 1;

	public static void OnDefaultFromCustomize(int nCustomizeTarget, bool bRecoverReg, bool bRecoverEC, int nACLineStatus)
	{
		LogCtrl.Write("---------------" + LogCtrl.GetTime() + "---------------");
		LogCtrl.Write("[OnDefaultFromCustomize] Start");
		m_nProjectID = GetProjectIdFromEC();
		LogCtrl.Write("[OnDefaultFromCustomize] m_nProjectID: " + m_nProjectID);
		if (m_nProjectID.IsProjectId_NoRgblbSupport())
		{
			LogCtrl.Write("[OnDefaultFromCustomize] RGBLB is not support, End");
			return;
		}
		if (isSupportRGBLBFromEC() == 0 && GetRGBLightBarMode() == 255)
		{
			LogCtrl.Write("[OnDefaultFromCustomize] RGBLB mode is disable, End");
			return;
		}
		RGBLightBarTable.Init(m_nProjectID);
		UpdateParams(m_nProjectID, nCustomizeTarget);
		if (bRecoverReg)
		{
			RecoverReg();
		}
		if (nACLineStatus == 0)
		{
			SetOEMService(m_nLightBarOnOff, m_nColorful_dc, m_nRedLevel, m_nGreenLevel, m_nBlueLevel);
		}
		else
		{
			SetOEMService(m_nLightBarOnOff, m_nColorful, m_nRedLevel, m_nGreenLevel, m_nBlueLevel);
		}
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
		LogCtrl.Write("[OnDefaultFromCustomize] End");
	}

	public static void UpdateParams(int nProjectID, int nCustomizeTarget)
	{
		switch (nProjectID)
		{
		case 10:
			m_nRedLevel = 2u;
			m_nGreenLevel = 5u;
			m_nBlueLevel = 9u;
			m_nColorful = 0u;
			break;
		case 8:
			if (nCustomizeTarget == 9)
			{
				m_nRedLevel = 9u;
				m_nGreenLevel = 9u;
				m_nBlueLevel = 9u;
				m_nColorful = 1u;
				m_nLightBarOnOff = 0;
			}
			else
			{
				m_nRedLevel = 9u;
				m_nGreenLevel = 9u;
				m_nBlueLevel = 9u;
				m_nColorful = 1u;
			}
			break;
		case 7:
			switch (nCustomizeTarget)
			{
			case 3:
				m_nRedLevel = 9u;
				m_nGreenLevel = 9u;
				m_nBlueLevel = 9u;
				m_nColorful = 1u;
				break;
			case 4:
				m_nRedLevel = 9u;
				m_nGreenLevel = 9u;
				m_nBlueLevel = 9u;
				m_nColorful = 1u;
				break;
			case 5:
				m_nRedLevel = 9u;
				m_nGreenLevel = 9u;
				m_nBlueLevel = 9u;
				m_nColorful = 0u;
				m_nSupportRGBLightBarColorful = 0;
				m_nSupportRGBLightBarBreathEffect = 0;
				break;
			case 9:
				m_nRedLevel = 9u;
				m_nGreenLevel = 9u;
				m_nBlueLevel = 9u;
				m_nColorful = 1u;
				m_nLightBarOnOff = 0;
				break;
			default:
				m_nRedLevel = 9u;
				m_nGreenLevel = 9u;
				m_nBlueLevel = 9u;
				m_nColorful = 1u;
				break;
			}
			break;
		case 6:
			switch (nCustomizeTarget)
			{
			case 3:
				m_nRedLevel = 2u;
				m_nGreenLevel = 5u;
				m_nBlueLevel = 9u;
				m_nColorful = 0u;
				break;
			case 4:
				m_nRedLevel = 2u;
				m_nGreenLevel = 5u;
				m_nBlueLevel = 9u;
				m_nColorful = 0u;
				break;
			case 5:
				m_nRedLevel = 2u;
				m_nGreenLevel = 5u;
				m_nBlueLevel = 9u;
				m_nColorful = 0u;
				m_nSupportRGBLightBarColorful = 0;
				m_nSupportRGBLightBarBreathEffect = 0;
				break;
			case 9:
				m_nRedLevel = 2u;
				m_nGreenLevel = 5u;
				m_nBlueLevel = 9u;
				m_nColorful = 0u;
				m_nLightBarOnOff = 0;
				break;
			default:
				m_nRedLevel = 2u;
				m_nGreenLevel = 5u;
				m_nBlueLevel = 9u;
				m_nColorful = 0u;
				break;
			}
			break;
		case 3:
			switch (nCustomizeTarget)
			{
			case 3:
				m_nRedLevel = 9u;
				m_nGreenLevel = 9u;
				m_nBlueLevel = 9u;
				m_nColorful = 1u;
				break;
			case 4:
				m_nRedLevel = 0u;
				m_nGreenLevel = 7u;
				m_nBlueLevel = 9u;
				m_nColorful = 0u;
				break;
			case 5:
				m_nRedLevel = 9u;
				m_nGreenLevel = 9u;
				m_nBlueLevel = 9u;
				m_nColorful = 0u;
				m_nSupportRGBLightBarColorful = 0;
				m_nSupportRGBLightBarBreathEffect = 0;
				break;
			case 9:
				m_nRedLevel = 9u;
				m_nGreenLevel = 9u;
				m_nBlueLevel = 9u;
				m_nColorful = 1u;
				m_nLightBarOnOff = 0;
				break;
			default:
				m_nRedLevel = 9u;
				m_nGreenLevel = 9u;
				m_nBlueLevel = 9u;
				m_nColorful = 1u;
				break;
			}
			break;
		default:
			switch (nCustomizeTarget)
			{
			case 11:
				m_nRedLevel_dc = 9u;
				m_nGreenLevel_dc = 9u;
				m_nBlueLevel_dc = 9u;
				m_nColorful_dc = 1u;
				break;
			case 23:
			case 44:
				m_nRedLevel = 0u;
				m_nGreenLevel = 7u;
				m_nBlueLevel = 9u;
				m_nColorful = 0u;
				break;
			default:
				m_nRedLevel = 9u;
				m_nGreenLevel = 9u;
				m_nBlueLevel = 9u;
				m_nColorful = 1u;
				break;
			}
			break;
		}
		if (m_nSupportRGBLightBarColorful == 0)
		{
			m_nColorful = 0u;
		}
		if (m_nSupportRGBLightBarBreathEffect == 0)
		{
			m_nBreathingLightEffect = 0u;
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

	public static int GetRGBLightBarModeFromEC()
	{
		byte Data = 0;
		EcCtrl.Read(m_ClassName, 1856, ref Data);
		return (int)(Convert.ToUInt64(Data) & 0xFF);
	}

	public static int isSupportRGBLBFromEC()
	{
		byte Data = 0;
		EcCtrl.Read(m_ClassName, 1934, ref Data);
		if ((byte)(Convert.ToUInt64(Data) & 0x10) == 16)
		{
			return 1;
		}
		return 0;
	}

	private static void SetOEMService(int _LightBarOnOff, uint _WelcomeMode, uint _red_level, uint _green_level, uint _blue_level)
	{
		SetOEMService_NvramVariable(_LightBarOnOff, _WelcomeMode, _red_level, _green_level, _blue_level);
	}

	private static uint SetOEMService_NvramVariable(int _LightBarOnOff, uint _WelcomeMode, uint _red_level, uint _green_level, uint _blue_level)
	{
		byte b = 1;
		byte red = 0;
		byte green = 0;
		byte blue = 0;
		if (_LightBarOnOff == 1)
		{
			if (_WelcomeMode == 1)
			{
				b = 1;
			}
			else
			{
				red = (byte)RGBLightBarTable.GetTable("Red", _red_level);
				green = (byte)RGBLightBarTable.GetTable("Green", _green_level);
				blue = (byte)RGBLightBarTable.GetTable("Blue", _blue_level);
				b = 254;
			}
		}
		else
		{
			b = 0;
		}
		NvramVariable.SetFwVars_RGBLightbar(b, red, green, blue);
		return Convert.ToUInt32(b);
	}

	private static int GetRGBLightBarMode()
	{
		int result = Convert.ToInt16(NvramVariable.GetFwVars().RGBLightbarMode);
		LogCtrl.TraceMessage("mode = 0x" + result.ToString("X2"), "GetRGBLightBarMode", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbLightbar\\MyRgbLightbarDefault.cs", 663);
		return result;
	}

	private static void WriteECRAM(int _LightBarOnOff, uint _WelcomeMode, uint _BreathingLightEffect, uint _red_level, uint _green_level, uint _blue_level)
	{
		if (_LightBarOnOff == 1)
		{
			if (_WelcomeMode == 1)
			{
				if (_BreathingLightEffect == 1)
				{
					EcCtrl.Write(m_ClassName, 1864, 128);
				}
				else
				{
					EcCtrl.Write(m_ClassName, 1864, 136);
				}
				EcCtrl.Write(m_ClassName, 1865, 0);
				EcCtrl.Write(m_ClassName, 1866, 0);
				EcCtrl.Write(m_ClassName, 1867, 0);
				return;
			}
			if (_BreathingLightEffect == 1)
			{
				EcCtrl.Write(m_ClassName, 1864, 0);
			}
			else
			{
				EcCtrl.Write(m_ClassName, 1864, 8);
			}
			ulong table = RGBLightBarTable.GetTable("Red", _red_level);
			EcCtrl.Write(m_ClassName, 1865, (byte)table);
			table = RGBLightBarTable.GetTable("Green", _green_level);
			EcCtrl.Write(m_ClassName, 1866, (byte)table);
			table = RGBLightBarTable.GetTable("Blue", _blue_level);
			EcCtrl.Write(m_ClassName, 1867, (byte)table);
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
