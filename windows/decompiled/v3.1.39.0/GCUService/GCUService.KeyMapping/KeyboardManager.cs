using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using Utility;

namespace GCUService.KeyMapping;

internal class KeyboardManager
{
	private string MS = "Microsoft";

	private string MStool = "PowerToys";

	private string MSFeature = "Keyboard Manager";

	private string MSFile = "default.json";

	private SettingsManager defaultSettings;

	private remapKeys remap = new remapKeys();

	private string keyboardManagerPath = Environment.CurrentDirectory;

	private static readonly KeyboardManager kbmodel = new KeyboardManager();

	private string powerToysKeyboard = "PowerToys.KeyboardManagerEngine.exe";

	public static KeyboardManager Instance => kbmodel;

	private KeyboardManager()
	{
		InitSettingDir();
	}

	private void InitSettingDir()
	{
		try
		{
			string folderPath = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
			string text = folderPath + "\\" + MS + "\\" + MStool + "\\" + MSFeature + "\\";
			DirectoryInfo directoryInfo = new DirectoryInfo(text);
			if (!directoryInfo.Exists)
			{
				directoryInfo.Create();
			}
			defaultSettings = new SettingsManager(text + "\\" + MSFile);
			defaultSettings.GetSetting<remapKeys>("remapKeys", out remap);
			if (remap == null)
			{
				remap = new remapKeys();
				remap.inProcess = new List<inProcess>();
				remap.remapShortcuts = new remapShortcuts();
				remap.remapShortcuts.global = new List<string>();
				remap.remapShortcuts.appSpecific = new List<string>();
				defaultSettings.AddSetting("remapKeys", remap);
				defaultSettings.SaveSettings();
			}
		}
		catch (Exception ex)
		{
			Console.WriteLine(ex.ToString());
		}
	}

	public void Enable()
	{
		LaunchProcess("KeyboardManager\\KeyboardManagerEngine\\", powerToysKeyboard);
	}

	private void Reflash()
	{
		InitSettingDir();
		LaunchProcess("KeyboardManager\\KeyboardManagerEngine\\", powerToysKeyboard);
	}

	private void LaunchProcess(string path, string appName)
	{
		string text = path + appName;
		if (File.Exists(text))
		{
			Process[] processesByName = Process.GetProcessesByName(appName.Replace(".exe", ""));
			for (int i = 0; i < processesByName.Count(); i++)
			{
				processesByName[i].Kill();
			}
			try
			{
				Process.Start(text);
				return;
			}
			catch (Exception ex)
			{
				Console.WriteLine("LaunchAllPlugins | Process Start Exception: " + ex.Message);
				return;
			}
		}
		Console.WriteLine("LaunchAllPlugins | " + appName + " is not found.");
	}

	public void Disable()
	{
		KillProcess(powerToysKeyboard.Replace(".exe", ""));
	}

	public List<inProcess> GetCurrentKeyList()
	{
		return remap.inProcess;
	}

	public void AddKey(string originalKeys, string newRemapKeys)
	{
		remap.inProcess.Add(new inProcess
		{
			originalKeys = originalKeys,
			newRemapKeys = newRemapKeys
		});
		defaultSettings.AddSetting("remapKeys", remap);
		defaultSettings.SaveSettings();
		Reflash();
	}

	private void RemoveKey(int index)
	{
		remap.inProcess.RemoveAt(index);
		defaultSettings.AddSetting("remapKeys", remap);
		defaultSettings.SaveSettings();
		Reflash();
	}

	private void KillProcess(string processName)
	{
		try
		{
			Process[] processesByName = Process.GetProcessesByName(processName);
			for (int i = 0; i < processesByName.Count(); i++)
			{
				processesByName[i].Kill();
			}
		}
		catch (Exception)
		{
		}
	}
}
