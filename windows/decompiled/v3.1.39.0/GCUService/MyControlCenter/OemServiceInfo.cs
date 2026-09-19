using System;
using System.Collections.Generic;
using System.Linq;
using Microsoft.Win32;
using MyECIO;
using OemServiceModel;
using Utility;

namespace MyControlCenter;

internal class OemServiceInfo
{
	private static MyEcCtrl EcCtrl = MyEcCtrl.Instance;

	private static string m_ClassName = "OemServiceInfo";

	public static int m_projectID = 0;

	public static int m_supportLightBar = 0;

	public static int m_supportRGBLB = 0;

	public static int m_supportKBL = 0;

	public static int m_supportSingleColorKeyboard = 0;

	public static int m_supportCustomerList = 0;

	public static int m_switchColorCalibration = 1;

	public static int m_supportColorCalibration = 255;

	public static string m_sLightbarType = "2";

	public static void Get()
	{
		m_projectID = EcCtrl.GetProjectIdFromEC();
		try
		{
			string text = OemService.Read("setapctrl /GetStatus");
			string text2 = "";
			if (text.Substring(285, 1) == " ")
			{
				text.Substring(290, 1);
			}
			if ("" == " ")
			{
				text2 = text.Substring(300, 1);
			}
			if (text2 == " ")
			{
				m_supportCustomerList = Convert.ToInt16(text.Substring(303, 2), 16);
			}
			Convert.ToInt16(text.Substring(284, 1), 16);
			int num = Convert.ToInt16(text.Substring(283, 1), 16);
			Convert.ToInt16(text.Substring(282, 1), 16);
			Convert.ToInt16(text.Substring(281, 1), 16);
			m_supportLightBar = (((num & 4) == 4) ? 1 : 0);
			LogCtrl.Write($"[Get] ProjectID[{m_projectID}], BL[{m_supportLightBar}], CustomerList[{m_supportCustomerList}]");
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2\\Support", "LightBar", m_supportLightBar, RegistryValueKind.DWord);
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2\\Support", "supportCustomerList", m_supportCustomerList, RegistryValueKind.DWord);
		}
		catch (Exception ex)
		{
			LogCtrl.Write($"[Get] Read OemService Support Data Failed {ex.ToString()}");
		}
		if (m_supportCustomerList == 1)
		{
			OemService.m_sOemCustomerCmd = " /GGYY7878";
		}
		if (EcCtrl.isSupportRGBLBFromEC() == 1)
		{
			m_supportRGBLB = 1;
		}
		else
		{
			m_supportRGBLB = isSupportRGBLB(m_projectID);
		}
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2\\Support", "RGBLB", m_supportRGBLB, RegistryValueKind.DWord);
		m_supportKBL = OemSvcHasKBLSupport();
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2\\Support", "KBL", m_supportKBL, RegistryValueKind.DWord);
		if (m_supportKBL == 1)
		{
			m_supportSingleColorKeyboard = isSupportSingleColorKeyboardFromEC();
		}
		else
		{
			m_supportSingleColorKeyboard = 0;
		}
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2\\Support", "SingleColorKeyboard", m_supportSingleColorKeyboard, RegistryValueKind.DWord);
		LogCtrl.Write($"[Get] KBL[{m_supportKBL}], SingleColorKeyboard[{m_supportSingleColorKeyboard}]");
		m_switchColorCalibration = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2", "ColorCalibration", 1);
		if (m_switchColorCalibration == 0)
		{
			m_supportColorCalibration = 0;
		}
		else
		{
			m_supportColorCalibration = isSupportColorCalibration(m_projectID);
		}
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2\\Support", "ColorCalibration", m_supportColorCalibration, RegistryValueKind.DWord);
		LogCtrl.Write("[Get] End");
	}

	public static List<string[]> GetKeyboardWelcomeEffect()
	{
		string text = OemService.Read("ledkb /GetStatus");
		List<string[]> list = new List<string[]>();
		string[] array = text.Split('>');
		if (array.Count() > 0)
		{
			string[] item = array[1].Split(' ');
			string[] item2 = array[3].Split(' ');
			list.Add(item);
			list.Add(item2);
			return list;
		}
		return list;
	}

	public static List<string[]> GetLightbarWelcomeEffect()
	{
		string text = OemService.Read("usblb /GetMode");
		List<string[]> list = new List<string[]>();
		string[] array = text.Split('>');
		char[] separator = new char[2] { ' ', ':' };
		if (array.Count() > 0)
		{
			string[] source = array[3].Split(separator);
			string[] source2 = array[1].Split(separator);
			list.Add(source.Where((string n) => !n.Equals("")).Skip(1).ToArray());
			list.Add(source2.Where((string n) => !n.Equals("")).Skip(1).ToArray());
			return list;
		}
		return list;
	}

	private static int isSupportRGBLB(int projectID)
	{
		int num = 255;
		int num2 = 0;
		int num3 = 0;
		int num4 = 0;
		if (projectID >= 3)
		{
			try
			{
				string text = OemService.Read("RGBLB /DUMP");
				num = Convert.ToInt16(text.Substring(256, 2), 16);
				num2 = Convert.ToInt16(text.Substring(280, 2), 16);
				num3 = Convert.ToInt16(text.Substring(292, 2), 16);
				num4 = Convert.ToInt16(text.Substring(303, 2), 16);
				LogCtrl.Write($"[Get] RGBLB[{num}], R[{num2}], G[{num3}], B[{num4}]");
			}
			catch (Exception ex)
			{
				LogCtrl.Write($"[Get] Read OemService RGBLB Support Data Failed {ex.ToString()}");
			}
		}
		else
		{
			num = 255;
		}
		return num;
	}

	private static int isSupportColorCalibration(int projectID)
	{
		int num = 255;
		try
		{
			num = Convert.ToInt16(OemService.Read("ColorCalibration /get").Substring(293, 2), 16);
			LogCtrl.Write($"status = 0x{num:X}");
			LogCtrl.Write($"[Get] ColorCalibration[{num}]");
		}
		catch (Exception ex)
		{
			LogCtrl.Write($"[Get] Read OemService ColorCalibration Support Data Failed {ex.ToString()}");
		}
		return num;
	}

	private static void GetRgbKeyboardEffect(int projectID)
	{
		ulong value = 1uL;
		object data = 0;
		WMIBIOS.WMIReadBiosRAM("GetUlongEx6", value, ref data);
		byte[] bytes = BitConverter.GetBytes(Convert.ToUInt64(data));
		LogCtrl.Write(string.Format("[Get] GetRgbKeyboardEffectType: bytes[0]=0x{0:X}, bytes[1]=0x{0:X}", bytes[0], bytes[1]));
	}

	private static int OemSvcHasKBLSupport()
	{
		bool flag = m_projectID.IsProjectId_SingleColorKeyboard();
		LogCtrl.Write("[Get] HasKBLSupport | " + flag);
		if (flag)
		{
			return 1;
		}
		return 0;
	}

	private static int isSupportSingleColorKeyboardFromEC()
	{
		byte Data = 0;
		EcCtrl.Read(m_ClassName, 1932, ref Data);
		if ((byte)(Convert.ToUInt64(Data) & 1) == 1)
		{
			LogCtrl.Write("[Get] isSupportSingleColorKeyboard | true");
			return 1;
		}
		LogCtrl.Write("[Get] isSupportSingleColorKeyboard | false");
		return 0;
	}

	private static void SetTdr()
	{
		try
		{
			uint num = Convert.ToUInt32(OemService.Read("OemTdr /GetTdr").Substring(249, 3));
			if (num != 0 || num < 255)
			{
				LogCtrl.TraceMessage("Check Factory TDR function, OemTdr /GetTdr data: " + num + ", then write registry.", "SetTdr", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\Customize\\OemServiceInfo.cs", 379);
				if (Environment.Is64BitProcess)
				{
					RegistryKey.OpenBaseKey(RegistryHive.LocalMachine, RegistryView.Registry64).CreateSubKey("SYSTEM\\CurrentControlSet\\Control\\GraphicsDrivers\\").SetValue("TdrDelay", num, RegistryValueKind.DWord);
				}
				else
				{
					RegistryKey.OpenBaseKey(RegistryHive.LocalMachine, RegistryView.Registry32).CreateSubKey("SYSTEM\\CurrentControlSet\\Control\\GraphicsDrivers\\").SetValue("TdrDelay", num, RegistryValueKind.DWord);
				}
			}
			else
			{
				LogCtrl.TraceMessage("Check Factory TDR function, OemTdr /GetTdr data: " + num + ", then do noyhing.", "SetTdr", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\Customize\\OemServiceInfo.cs", 387);
			}
		}
		catch (Exception ex)
		{
			LogCtrl.TraceMessage($"Check Factory TDR function Failed {ex.ToString()}", "SetTdr", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\Customize\\OemServiceInfo.cs", 392);
		}
	}

	public static void LoadRegistryFromSupport()
	{
		string subKey = "\\OEM\\GamingCenter2\\Support";
		try
		{
			int supportLightBar = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, subKey, "LightBar", 9u);
			int supportRGBLB = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, subKey, "RGBLB", 9u);
			m_supportLightBar = supportLightBar;
			m_supportRGBLB = supportRGBLB;
		}
		catch
		{
			LogCtrl.Write("[LoadRegistryFromSupport] failed.");
		}
	}

	public static string GetLightbarSupportType()
	{
		if (m_sLightbarType != "3")
		{
			if (m_supportLightBar == 0)
			{
				m_sLightbarType = "0";
			}
			else if (m_supportLightBar == 1 && m_supportRGBLB == 255)
			{
				m_sLightbarType = "1";
			}
			if (m_supportRGBLB == 1)
			{
				m_sLightbarType = "2";
			}
		}
		return m_sLightbarType;
	}

	public static string GetKeyboardType()
	{
		string text = "1";
		if (m_supportKBL == 1)
		{
			if (m_supportSingleColorKeyboard == 1)
			{
				return "2";
			}
			return "0";
		}
		return "1";
	}
}
