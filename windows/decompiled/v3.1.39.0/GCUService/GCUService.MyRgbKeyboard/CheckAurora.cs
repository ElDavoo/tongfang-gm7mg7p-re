using System.IO;
using System.Windows.Threading;
using Microsoft.Win32;
using Utility;

namespace GCUService.MyRgbKeyboard;

public class CheckAurora
{
	private static readonly CheckAurora model = new CheckAurora();

	private bool sendMessageTemp;

	private bool _AuroraSupport = true;

	private bool _AuroraEnable;

	private bool _AuroraExist;

	private Dispatcher _dispatcher;

	private FileSystemWatcher fileWatcher = new FileSystemWatcher();

	public ErrorEventHandler AuroraStatusChanged;

	public static CheckAurora Instance => model;

	private CheckAurora()
	{
		GetAuroraSupport();
		GetCurrentAuroraStauts();
	}

	private async void FileWatcher_Changed(object sender, FileSystemEventArgs e)
	{
	}

	public void SetDispatcher(Dispatcher dispatcher)
	{
		_dispatcher = dispatcher;
	}

	private void GetAuroraSupport()
	{
		int num = 0;
		try
		{
			num = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, "\\OEM\\Aurora", "AuroraSupport", 0);
		}
		catch
		{
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, "\\OEM\\Aurora", "AuroraSupport", 1, RegistryValueKind.DWord);
		}
		_AuroraSupport = num == 1;
	}

	private void GetCurrentAuroraStauts()
	{
		int num = 0;
		try
		{
			num = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, "\\OEM\\Aurora", "AuroraSwitch", 0);
		}
		catch
		{
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, "\\OEM\\Aurora", "AuroraSwitch", 0, RegistryValueKind.DWord);
		}
		_AuroraEnable = num == 1;
	}

	public bool GetAuroraExists()
	{
		bool result = true;
		if (!_AuroraSupport)
		{
			return false;
		}
		try
		{
			string text = "\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{9444602B-C5D8-4EF5-9D5B-E76D06B53C71}_is1";
			string name = "InstallLocation";
			string text2 = (string)RegistryKey.OpenBaseKey(RegistryHive.LocalMachine, RegistryView.Registry32).OpenSubKey("SOFTWARE\\WOW6432Node" + text)?.GetValue(name, "");
			if (text2 == null)
			{
				return false;
			}
			if (text2 == string.Empty)
			{
				return false;
			}
		}
		catch
		{
		}
		return result;
	}

	public bool GetAuroraStauts()
	{
		GetCurrentAuroraStauts();
		return _AuroraEnable;
	}

	public void SetAuroraSwtich(bool enable)
	{
		int num = (enable ? 1 : 0);
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, "\\OEM\\Aurora", "AuroraSwitch", num, RegistryValueKind.DWord);
	}
}
