using Microsoft.Win32;
using Utility;

namespace MyRGBKeyboard;

public static class URegistry
{
	public const string TreeKey = "SOFTWARE\\OEM\\GamingCenter2\\";

	public static object RegistryValueRead(string SubKey, string Name, object defaultvalue)
	{
		try
		{
			return RegistryKey.OpenBaseKey(RegistryHive.LocalMachine, RegistryView.Registry64).OpenSubKey("SOFTWARE\\OEM\\GamingCenter2\\" + SubKey).GetValue(Name, defaultvalue);
		}
		catch
		{
			Log.s(LOG_LEVEL.ERROR, string.Format("Registry|RegistryValueRead Failed subkey ={0} Name={1}", "SOFTWARE\\OEM\\GamingCenter2\\" + SubKey, Name));
			return 0;
		}
	}

	public static string[] RegistryKeyRead(string SubKey)
	{
		try
		{
			return RegistryKey.OpenBaseKey(RegistryHive.LocalMachine, RegistryView.Registry64).OpenSubKey("SOFTWARE\\OEM\\GamingCenter2\\" + SubKey).GetSubKeyNames();
		}
		catch
		{
			Log.s(LOG_LEVEL.ERROR, string.Format("Registry|RegistryKeyRead Failed subkey ={0}", "SOFTWARE\\OEM\\GamingCenter2\\" + SubKey));
			return null;
		}
	}

	public static void RegistryValueWrite(string SubKey, string Name, object setvalue, RegistryValueKind valuekind)
	{
		try
		{
			RegistryKey.OpenBaseKey(RegistryHive.LocalMachine, RegistryView.Registry64).CreateSubKey("SOFTWARE\\OEM\\GamingCenter2\\" + SubKey).SetValue(Name, setvalue, valuekind);
		}
		catch
		{
			Log.s(LOG_LEVEL.ERROR, string.Format("Registry|RegistryValueWrite Failed subkey ={0} Name={1} SetValue={2}", "SOFTWARE\\OEM\\GamingCenter2\\" + SubKey, Name, setvalue));
		}
	}
}
