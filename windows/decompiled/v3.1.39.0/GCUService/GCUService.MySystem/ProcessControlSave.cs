using System;
using System.Threading.Tasks;
using Microsoft.Win32;
using Newtonsoft.Json;
using Utility;

namespace GCUService.MySystem;

public static class ProcessControlSave
{
	private const string FileExtension = ".json";

	private const string m_RegistryPath = "\\OEM\\GamingCenter2";

	public static bool IsRegeditExit(string name)
	{
		bool result = false;
		string[] subKeyNames = Registry.LocalMachine.OpenSubKey("SOFTWARE\\OEM\\GamingCenter2", writable: true).GetSubKeyNames();
		for (int i = 0; i < subKeyNames.Length; i++)
		{
			if (subKeyNames[i] == name)
			{
				return true;
			}
		}
		return result;
	}

	public static string[] ProcessList()
	{
		return Registry.LocalMachine.OpenSubKey("SOFTWARE\\OEM\\GamingCenter2", writable: true).OpenSubKey("ProcessControl", writable: true).GetValueNames();
	}

	public static void DelRegistry(string registrykey, string key)
	{
		try
		{
			RegistryCtrl.RegistrySoftwareKeyDelete(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2\\" + registrykey, key);
		}
		catch (Exception ex)
		{
			LogCtrl.Write(ex.ToString());
		}
	}

	public static void SaveAsync<T>(string registrykey, string key, T Value)
	{
		try
		{
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2\\" + registrykey, key, JsonConvert.SerializeObject(Value), RegistryValueKind.String);
		}
		catch (Exception ex)
		{
			LogCtrl.Write(ex.ToString());
		}
	}

	public static async Task<T> ReadAsync<T>(string registrykey, string key)
	{
		try
		{
			object obj = RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2\\" + registrykey, key, RegistryValueKind.String);
			if (obj != null)
			{
				return await Json.ToObjectAsync<T>((string)obj);
			}
		}
		catch (Exception ex)
		{
			LogCtrl.Write("read " + registrykey + " exception, " + ex.ToString());
		}
		return default(T);
	}
}
