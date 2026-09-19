using System;
using System.Collections.Generic;
using System.IO;
using System.Threading;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

namespace Utility;

public class SettingsManager
{
	private JObject settings;

	private string SettingsPath { get; }

	private ReaderWriterLockSlim rwLock { get; }

	public SettingsManager(string settingsPath)
	{
		rwLock = new ReaderWriterLockSlim();
		SettingsPath = settingsPath;
		LoadSettings();
	}

	private void CreateSettingsFile()
	{
		try
		{
			if (!File.Exists(SettingsPath))
			{
				Directory.CreateDirectory(Path.GetDirectoryName(SettingsPath));
				File.Create(SettingsPath).Dispose();
			}
		}
		catch (Exception innerException)
		{
			throw new FileNotFoundException("The provided SettingsPath was invalid", innerException);
		}
	}

	private void LoadSettings()
	{
		if (settings == null)
		{
			using (new WriteLock(rwLock))
			{
				CreateSettingsFile();
				string text = File.ReadAllText(SettingsPath);
				settings = (string.IsNullOrWhiteSpace(text) ? new JObject() : JObject.Parse(text));
			}
		}
	}

	public void AddSetting(string setting, object value)
	{
		LoadSettings();
		using (new WriteLock(rwLock))
		{
			if (settings[setting] == null && value != null)
			{
				settings.Add(setting, JToken.FromObject(value));
			}
			else if (value == null && settings[setting] != null)
			{
				settings[setting] = null;
			}
			else if (value != null)
			{
				settings[setting] = JToken.FromObject(value);
			}
		}
	}

	public void RemoveSetting(string setting)
	{
		LoadSettings();
		using (new WriteLock(rwLock))
		{
			if (settings[setting] != null)
			{
				settings.Remove(setting);
			}
		}
	}

	public void AddSettings(Dictionary<string, object> settings)
	{
		foreach (KeyValuePair<string, object> setting in settings)
		{
			AddSetting(setting.Key, setting.Value);
		}
	}

	public bool GetSetting<T>(string setting, out T result)
	{
		result = default(T);
		try
		{
			LoadSettings();
			using (new ReadLock(rwLock))
			{
				if (settings[setting] == null)
				{
					return false;
				}
				result = settings[setting].ToObject<T>();
			}
			return true;
		}
		catch (Exception)
		{
			try
			{
				using (new ReadLock(rwLock))
				{
					result = settings[setting].Value<T>();
				}
				return true;
			}
			catch (Exception)
			{
				return false;
			}
		}
	}

	public bool GetSettings(Dictionary<string, object> values)
	{
		return GetSettings(out values);
	}

	public bool GetSettings<TValue>(out Dictionary<string, TValue> values)
	{
		try
		{
			LoadSettings();
			using (new ReadLock(rwLock))
			{
				values = settings.ToObject<Dictionary<string, TValue>>();
				return true;
			}
		}
		catch
		{
			values = null;
			return false;
		}
	}

	public void SaveSettings()
	{
		try
		{
			using (new WriteLock(rwLock))
			{
				File.WriteAllText(SettingsPath, settings.ToString(Formatting.Indented));
			}
		}
		catch (Exception)
		{
		}
	}

	public void DeleteSettings()
	{
		using (new WriteLock(rwLock))
		{
			File.Delete(SettingsPath);
			settings = null;
		}
	}
}
