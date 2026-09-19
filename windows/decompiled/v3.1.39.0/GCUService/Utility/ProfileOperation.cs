using System;
using System.IO;
using System.Reflection;
using System.Threading;
using System.Threading.Tasks;
using Newtonsoft.Json;

namespace Utility;

internal class ProfileOperation
{
	private const string FileExtension = ".json";

	private static object _SettingLock = new object();

	public static async Task SaveAsync<T>(string key, T Value)
	{
		string text = Directory.GetParent(Assembly.GetExecutingAssembly().Location)?.ToString() + "\\DisplayProfile\\";
		if (!Monitor.TryEnter(_SettingLock, 1000))
		{
			return;
		}
		try
		{
			File.WriteAllText(text + key + ".json", JsonConvert.SerializeObject(Value));
		}
		catch (Exception ex)
		{
			LogCtrl.Write(key + " Write settings error !" + ex.ToString());
		}
		finally
		{
			Monitor.Exit(_SettingLock);
		}
	}

	public static T Read<T>(string key)
	{
		string text = Directory.GetParent(Assembly.GetExecutingAssembly().Location)?.ToString() + "\\DisplayProfile\\";
		if (Monitor.TryEnter(_SettingLock, 1000))
		{
			try
			{
				string text2 = File.ReadAllText(text + key + ".json");
				if (text2 != null)
				{
					return Json.ToObject<T>(text2);
				}
			}
			catch (Exception ex)
			{
				LogCtrl.Write(key + " Read settings error !" + ex.ToString());
			}
			finally
			{
				Monitor.Exit(_SettingLock);
			}
		}
		return default(T);
	}

	public static async Task<T> ReadAsync<T>(string key)
	{
		string text = Directory.GetParent(Assembly.GetExecutingAssembly().Location)?.ToString() + "\\DisplayProfile\\";
		if (Monitor.TryEnter(_SettingLock, 1000))
		{
			try
			{
				string text2 = File.ReadAllText(text + key + ".json");
				if (text2 != null)
				{
					return await Json.ToObjectAsync<T>(text2);
				}
			}
			catch (Exception ex)
			{
				if (key == "NavigationSwitch")
				{
					await SaveAsync("NavigationSwitch", Value: true);
					return await Json.ToObjectAsync<T>("true");
				}
				LogCtrl.Write(key + " Read settings error !" + ex.ToString());
			}
			finally
			{
				Monitor.Exit(_SettingLock);
			}
		}
		return default(T);
	}
}
