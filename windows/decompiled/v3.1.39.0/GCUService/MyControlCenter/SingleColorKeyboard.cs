using System;
using Microsoft.Win32;
using MyECIO;
using Utility;

namespace MyControlCenter;

internal class SingleColorKeyboard
{
	private static MyEcCtrl EcCtrl = MyEcCtrl.Instance;

	private static string m_ClassName = "SingleColorKeyboard";

	private static string m_sRegistryPath = "\\OEM\\GamingCenter2\\MySetting\\" + m_ClassName;

	public const int BacklightLevel_Min = 0;

	public const int BacklightLevel_Max = 2;

	public const int BacklightLevel_Default = 2;

	private static int _BacklightLevel = -1;

	private static int _EcBacklightLevel = -1;

	public static int BacklightLevel
	{
		get
		{
			try
			{
				_BacklightLevel = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegistryPath, "LightLevel", 2);
				LogCtrl.Write("[SingleColorKeyboard] BacklightLevel | get  | level=" + _BacklightLevel);
			}
			catch
			{
				LogCtrl.Write("[SingleColorKeyboard] BacklightLevel | get | read reg fail, set default");
				BacklightLevel = 2;
			}
			return _BacklightLevel;
		}
		set
		{
			LogCtrl.Write("[SingleColorKeyboard] BacklightLevel | set | value=" + value);
			_BacklightLevel = value;
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath, "LightLevel", value, RegistryValueKind.DWord);
			if (_EcBacklightLevel != value)
			{
				LogCtrl.Write("[SingleColorKeyboard] BacklightLevel | set | write to EC");
				EcBacklightLevel = value;
			}
			else
			{
				LogCtrl.Write("[SingleColorKeyboard] BacklightLevel | set | skip write EC");
			}
		}
	}

	public static int EcBacklightLevel
	{
		get
		{
			byte Data = 0;
			EcCtrl.Read(m_ClassName, 1932, ref Data);
			_EcBacklightLevel = Data >> 5;
			LogCtrl.Write("[SingleColorKeyboard] EcBacklightLevel | get | _EcBacklightLevel = " + _EcBacklightLevel);
			return _EcBacklightLevel;
		}
		set
		{
			_EcBacklightLevel = value;
			LogCtrl.Write("[SingleColorKeyboard] EcBacklightLevel | set | value=" + _EcBacklightLevel);
			byte Data = 0;
			EcCtrl.Read(m_ClassName, 1932, ref Data);
			Data |= 0x10;
			Data &= 0x1F;
			uint num = (uint)(_EcBacklightLevel << 5);
			Data = (byte)(Data | num);
			EcCtrl.Write(m_ClassName, 1932, Data);
		}
	}

	public static void SetPower(int mode)
	{
		LogCtrl.Write("[SingleColorKeyboard] SetPower | mode=" + mode);
		byte Data = 0;
		EcCtrl.Read(m_ClassName, 1932, ref Data);
		byte b = (byte)(Convert.ToUInt64(Data) & 0xFF);
		b = ((mode != 1) ? ((byte)(b | 2)) : ((byte)(b & 0xFD)));
		EcCtrl.Write(m_ClassName, 1932, b);
	}

	public static void SetSingleColorKBBLOnOff_Registry(int status)
	{
		try
		{
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath, "SingleColorKBBLOnOff", status, RegistryValueKind.DWord);
		}
		catch
		{
		}
	}

	public static int LoadSingleColorKBBLOnOff_Registry()
	{
		int result = 1;
		try
		{
			result = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegistryPath, "SingleColorKBBLOnOff", 1);
		}
		catch
		{
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegistryPath, "SingleColorKBBLOnOff", 1, RegistryValueKind.DWord);
		}
		return result;
	}
}
