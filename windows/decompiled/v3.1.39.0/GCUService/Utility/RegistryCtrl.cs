using System;
using Microsoft.Win32;

namespace Utility;

internal class RegistryCtrl
{
	public static bool m_bWriteToReg = true;

	public static void RegistryCurrentUserSoftwareKeyWrite(string hKey, string SubKey, string Name, object setvalue, RegistryValueKind valuekind, bool bWriteToReg)
	{
		if (bWriteToReg)
		{
			RegistryKey registryKey = ((!Environment.Is64BitOperatingSystem) ? Registry.Users.CreateSubKey(hKey + "\\SOFTWARE\\Wow6432Node" + SubKey) : Registry.Users.CreateSubKey(hKey + "\\SOFTWARE" + SubKey));
			registryKey.SetValue(Name, setvalue, valuekind);
			registryKey.Close();
		}
	}

	public static void RegistryCurrentUserSoftwareSubKeyTreeDelete(string hKey, string SubKey)
	{
		if (Environment.Is64BitOperatingSystem)
		{
			Registry.Users.DeleteSubKeyTree(hKey + "\\SOFTWARE" + SubKey);
		}
		else
		{
			Registry.Users.DeleteSubKeyTree(hKey + "\\SOFTWARE\\Wow6432Node" + SubKey);
		}
	}

	public static object RegistrySoftwareKeyRead(RegistryHive hKey, string SubKey, string Name, object defaultvalue)
	{
		if (Environment.Is64BitOperatingSystem)
		{
			RegistryKey registryKey = RegistryKey.OpenBaseKey(RegistryHive.LocalMachine, RegistryView.Registry64).OpenSubKey("SOFTWARE" + SubKey, RegistryKeyPermissionCheck.ReadSubTree);
			if (registryKey == null)
			{
				throw new Exception();
			}
			return registryKey.GetValue(Name, defaultvalue);
		}
		RegistryKey registryKey2 = RegistryKey.OpenBaseKey(RegistryHive.LocalMachine, RegistryView.Registry32).OpenSubKey("SOFTWARE\\WOW6432Node" + SubKey, RegistryKeyPermissionCheck.ReadSubTree);
		if (registryKey2 == null)
		{
			throw new Exception();
		}
		return registryKey2.GetValue(Name, defaultvalue);
	}

	public static object RegistrySoftwareKeyRead(RegistryHive hKey, string SubKey, string Name, object defaultvalue, RegistryValueKind valuekind = RegistryValueKind.String)
	{
		if (Environment.Is64BitOperatingSystem)
		{
			try
			{
				return RegistryKey.OpenBaseKey(hKey, RegistryView.Registry64).OpenSubKey("SOFTWARE" + SubKey).GetValue(Name, defaultvalue);
			}
			catch
			{
				RegistryKey.OpenBaseKey(hKey, RegistryView.Registry64).CreateSubKey("SOFTWARE" + SubKey).SetValue(Name, defaultvalue, valuekind);
				return RegistryKey.OpenBaseKey(hKey, RegistryView.Registry64).OpenSubKey("SOFTWARE" + SubKey).GetValue(Name, defaultvalue);
			}
		}
		return RegistryKey.OpenBaseKey(hKey, RegistryView.Registry32).OpenSubKey("SOFTWARE\\WOW6432Node" + SubKey).GetValue(Name, defaultvalue);
	}

	public static void RegistrySoftwareKeyWrite(RegistryHive hKey, string SubKey, string Name, object setvalue, RegistryValueKind valuekind)
	{
		if (Environment.Is64BitOperatingSystem)
		{
			RegistryKey.OpenBaseKey(hKey, RegistryView.Registry64).CreateSubKey("SOFTWARE" + SubKey).SetValue(Name, setvalue, valuekind);
		}
		else
		{
			RegistryKey.OpenBaseKey(hKey, RegistryView.Registry32).CreateSubKey("SOFTWARE\\WOW6432Node" + SubKey).SetValue(Name, setvalue, valuekind);
		}
	}

	public static void RegistrySoftwareKeyDelete(RegistryHive hKey, string SubKey, string Name)
	{
		if (Environment.Is64BitOperatingSystem)
		{
			RegistryKey.OpenBaseKey(hKey, RegistryView.Registry64).CreateSubKey("SOFTWARE" + SubKey).DeleteValue(Name);
		}
		else
		{
			RegistryKey.OpenBaseKey(hKey, RegistryView.Registry32).CreateSubKey("SOFTWARE\\WOW6432Node" + SubKey).DeleteValue(Name);
		}
	}

	public static void RegistrySoftwareSubKeyDelete(RegistryHive hKey, string SubKey, string Name)
	{
		if (Environment.Is64BitOperatingSystem)
		{
			RegistryKey.OpenBaseKey(hKey, RegistryView.Registry64).CreateSubKey("SOFTWARE" + SubKey).DeleteSubKey(Name);
		}
		else
		{
			RegistryKey.OpenBaseKey(hKey, RegistryView.Registry32).CreateSubKey("SOFTWARE\\WOW6432Node" + SubKey).DeleteSubKey(Name);
		}
	}

	public static void RegistrySoftwareSubKeyTreeDelete(RegistryHive hKey, string SubKey, string Name)
	{
		if (Environment.Is64BitOperatingSystem)
		{
			RegistryKey.OpenBaseKey(hKey, RegistryView.Registry64).CreateSubKey("SOFTWARE" + SubKey).DeleteSubKeyTree(Name);
		}
		else
		{
			RegistryKey.OpenBaseKey(hKey, RegistryView.Registry32).CreateSubKey("SOFTWARE\\WOW6432Node" + SubKey).DeleteSubKeyTree(Name);
		}
	}

	public static object RegistryKeyRead(RegistryHive hKey, string SubKey, string Name, object defaultvalue)
	{
		if (Environment.Is64BitProcess)
		{
			return RegistryKey.OpenBaseKey(hKey, RegistryView.Registry64).OpenSubKey(SubKey).GetValue(Name, defaultvalue);
		}
		return RegistryKey.OpenBaseKey(hKey, RegistryView.Registry32).OpenSubKey(SubKey).GetValue(Name, defaultvalue);
	}

	public static void RegistryKeyWrite(RegistryHive hKey, string SubKey, string Name, object setvalue, RegistryValueKind valuekind)
	{
		if (Environment.Is64BitProcess)
		{
			RegistryKey.OpenBaseKey(hKey, RegistryView.Registry64).CreateSubKey(SubKey).SetValue(Name, setvalue, valuekind);
		}
		else
		{
			RegistryKey.OpenBaseKey(hKey, RegistryView.Registry32).CreateSubKey(SubKey).SetValue(Name, setvalue, valuekind);
		}
	}

	public static string[] RegistrySoftwareKeyGet(RegistryHive hKey, string SubKey)
	{
		if (Environment.Is64BitOperatingSystem)
		{
			RegistryKey registryKey = RegistryKey.OpenBaseKey(hKey, RegistryView.Registry64).OpenSubKey("SOFTWARE" + SubKey, RegistryKeyPermissionCheck.ReadSubTree);
			if (registryKey == null)
			{
				throw new Exception();
			}
			return registryKey.GetSubKeyNames();
		}
		RegistryKey registryKey2 = RegistryKey.OpenBaseKey(hKey, RegistryView.Registry32).OpenSubKey("SOFTWARE\\WOW6432Node" + SubKey, RegistryKeyPermissionCheck.ReadSubTree);
		if (registryKey2 == null)
		{
			throw new Exception();
		}
		return registryKey2.GetSubKeyNames();
	}

	public static int GetCustomizeTarget()
	{
		int result = 1;
		try
		{
			result = (int)RegistrySoftwareKeyRead(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2", "CustomizeTarget", 1);
		}
		catch
		{
		}
		return result;
	}

	public static int GetBridgeType()
	{
		int result = 1;
		try
		{
			result = (int)RegistrySoftwareKeyRead(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2", "BridgeType", 0);
		}
		catch
		{
		}
		return result;
	}

	public static string GetPluginPath()
	{
		string text = "C:\\Program Files\\OEM\\Plugin";
		string text2 = "\\OEM\\Plugin";
		string name = "Path";
		try
		{
			if (Environment.Is64BitOperatingSystem)
			{
				if (RegistryKey.OpenBaseKey(RegistryHive.LocalMachine, RegistryView.Registry64).OpenSubKey("SOFTWARE" + text2, RegistryKeyPermissionCheck.ReadSubTree) != null)
				{
					text = (string)RegistrySoftwareKeyRead(RegistryHive.LocalMachine, text2, name, text);
				}
			}
			else
			{
				RegistryKey registryKey = RegistryKey.OpenBaseKey(RegistryHive.LocalMachine, RegistryView.Registry32).OpenSubKey("SOFTWARE\\WOW6432Node" + text2, RegistryKeyPermissionCheck.ReadSubTree);
				if (registryKey != null && registryKey != null)
				{
					text = (string)RegistrySoftwareKeyRead(RegistryHive.LocalMachine, text2, name, text);
				}
			}
		}
		catch
		{
		}
		return text;
	}

	public static string GetBIOSProjectID()
	{
		try
		{
			return (string)RegistrySoftwareKeyRead(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2\\ItemSupport\\", "BIOS_PROJECT_ID", null, RegistryValueKind.String);
		}
		catch
		{
		}
		return null;
	}

	public static bool IsNewEcVersion(string currentEcVersion)
	{
		bool result = false;
		if (currentEcVersion != null && currentEcVersion != string.Empty)
		{
			try
			{
				string text = (string)RegistrySoftwareKeyRead(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2\\MyFanTable", "EcVersion", "0.0");
				if (currentEcVersion == text)
				{
					result = false;
				}
				else
				{
					text = currentEcVersion;
					RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2\\MyFanTable", "EcVersion", text, RegistryValueKind.String);
					result = true;
				}
			}
			catch
			{
				RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2\\MyFanTable", "EcVersion", currentEcVersion, RegistryValueKind.String);
				result = true;
			}
		}
		return result;
	}
}
