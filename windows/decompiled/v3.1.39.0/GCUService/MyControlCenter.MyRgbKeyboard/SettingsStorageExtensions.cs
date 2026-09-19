using System;
using System.IO;
using System.Reflection;
using System.Threading.Tasks;
using Microsoft.Win32;
using Newtonsoft.Json;
using Utility;

namespace MyControlCenter.MyRgbKeyboard;

public static class SettingsStorageExtensions
{
	private const string FileExtension = ".json";

	private const string m_RegistryPath = "\\OEM\\GamingCenter2\\RGBKeyboard";

	public static void SaveAsync<T>(string KeyboardType, string key, T Value)
	{
		try
		{
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2\\RGBKeyboard\\" + KeyboardType, key, JsonConvert.SerializeObject(Value), RegistryValueKind.String);
		}
		catch (Exception ex)
		{
			LogCtrl.Write(ex.ToString());
		}
	}

	public static async Task<T> ReadAsync<T>(string KeyboardType, string key)
	{
		try
		{
			object obj = RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, Path.Combine("\\OEM\\GamingCenter2\\RGBKeyboard", KeyboardType), key, RegistryValueKind.String);
			if (obj != null)
			{
				return await Json.ToObjectAsync<T>((string)obj);
			}
		}
		catch (Exception ex)
		{
			LogCtrl.Write("read " + KeyboardType + "  " + key + " exception, " + ex.ToString());
		}
		return default(T);
	}

	public static void DeleteRGBKeyboardRegistry()
	{
		try
		{
			RegistryCtrl.RegistrySoftwareSubKeyTreeDelete(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2", "RGBKeyboard");
		}
		catch (Exception)
		{
		}
	}

	public static void CheckingDir(Assembly assembly = null)
	{
		string folderPath = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
		if (assembly == null)
		{
			assembly = Assembly.GetCallingAssembly();
		}
		string text = Path.Combine(folderPath, "Settings");
		if (!Directory.Exists(text))
		{
			Directory.CreateDirectory(text);
		}
		LogCtrl.Write(text + " dir settings !");
	}
}
