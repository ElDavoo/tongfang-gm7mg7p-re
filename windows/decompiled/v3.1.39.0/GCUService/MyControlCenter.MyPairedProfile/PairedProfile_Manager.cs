using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Text;
using System.Windows;
using System.Windows.Threading;
using Utility;

namespace MyControlCenter.MyPairedProfile;

internal class PairedProfile_Manager
{
	private delegate void WinEventDelegate(IntPtr hWinEventHook, uint eventType, IntPtr hwnd, int idObject, int idChild, uint dwEventThread, uint dwmsEventTime);

	private static readonly PairedProfile_Manager control = new PairedProfile_Manager();

	private const string PairedProfileSettingName = "PairedProfileSetting";

	private bool _PairedSwitch;

	private static List<ProfileControl> profileNameList = new List<ProfileControl>();

	private SettingsManager _SettingsManager;

	private const uint EVENT_SYSTEM_FOREGROUND = 3u;

	private const uint WINEVENT_OUTOFCONTEXT = 0u;

	private WinEventDelegate procDelegate = WinEventProc;

	private IntPtr hhook = IntPtr.Zero;

	private static bool bIsWinEventProcFocused = false;

	private static HashSet<string> PairedApplicationNames = new HashSet<string>();

	public static PairedProfile_Manager Instance => control;

	private PairedProfile_Manager()
	{
		string text = string.Concat(Directory.GetParent(Assembly.GetExecutingAssembly().Location)?.ToString() + "\\PairedProfile\\", "PairedProfile.json");
		if (File.Exists(text))
		{
			_SettingsManager = new SettingsManager(text);
			Application.Current.Dispatcher.BeginInvoke((Action)delegate
			{
				Init();
			}, DispatcherPriority.Background);
		}
	}

	private async void Init()
	{
		try
		{
			profileNameList.Clear();
			try
			{
				_SettingsManager.GetSetting<PairedProfileSave>("PairedProfileSetting", out var result);
				if (result != null)
				{
					_PairedSwitch = result.PairedSwitch;
					profileNameList = result.ProfileNameList;
					SetPairedApplicationSwitch(_PairedSwitch);
					LogCtrl.TraceMessage("Load json successful !" + DateTime.Now.ToString(), "Init", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyPairedProfile\\PairedProfile_Manager.cs", 65);
				}
			}
			catch
			{
				LogCtrl.TraceMessage("Load json error !", "Init", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyPairedProfile\\PairedProfile_Manager.cs", 85);
			}
		}
		catch (Exception ex)
		{
			LogCtrl.TraceMessage("Load json error !" + ex.ToString(), "Init", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyPairedProfile\\PairedProfile_Manager.cs", 90);
		}
	}

	private void SetPairedApplicationSwitch(bool status)
	{
		if (status)
		{
			foreach (ProfileControl profileName in profileNameList)
			{
				AddPairedApplicationName(profileName.PairedApplicationName);
			}
			HookWinEvent();
		}
		else
		{
			ClearPairedApplicationNameAll();
			UnhookWinEvent();
		}
	}

	public async void Receive(byte[] data)
	{
		dynamic val = await Json.ToObjectAsync<object>(Encoding.UTF8.GetString(data));
		string text = Convert.ToString(val["Action"]);
		LogCtrl.TraceMessage("---------------" + LogCtrl.GetTime() + "---------------", "Receive", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyPairedProfile\\PairedProfile_Manager.cs", 155);
		LogCtrl.TraceMessage("Action = " + text, "Receive", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyPairedProfile\\PairedProfile_Manager.cs", 156);
		switch (text)
		{
		case "GETSTATUS":
			GetPairedProfileStatus();
			break;
		case "SetPairedApplicationSwitch":
			_PairedSwitch = Convert.ToBoolean(val["Status"]);
			SetPairedApplicationSwitch(_PairedSwitch);
			SaveCommand(asyncToUi: true);
			break;
		case "AddPairedApplication":
		{
			ProfileControl profileControl = new ProfileControl();
			profileControl.ProfileName = "Test";
			profileControl.PairedApplicationName = Convert.ToString(val["PairedApplicationName"]);
			profileControl.OperatingGamingProfileIndex = Convert.ToUInt32(val["OperatingGamingProfileIndex"]);
			profileControl.RGBKeyboardProfileIndex = Convert.ToUInt32(val["RGBKeyboardProfileIndex"]);
			profileControl.RGBLightbarProfileIndex = Convert.ToUInt32(val["RGBLightbarProfileIndex"]);
			AddPairedApplication(profileControl);
			break;
		}
		case "RemovePairedApplication":
			RemovePairedApplication(Convert.ToString(val["PairedApplicationName"]));
			break;
		}
	}

	public void GetPairedProfileStatus()
	{
		PairedProfileSave pairedProfileSave = new PairedProfileSave();
		pairedProfileSave.PairedSwitch = _PairedSwitch;
		pairedProfileSave.ProfileNameList = profileNameList;
		App.m_MQTTService.Publish("PairedProfileSetting", pairedProfileSave, retain: false);
	}

	private void SaveCommand(bool asyncToUi = false)
	{
		PairedProfileSave pairedProfileSave = new PairedProfileSave();
		pairedProfileSave.PairedSwitch = _PairedSwitch;
		pairedProfileSave.ProfileNameList = profileNameList;
		_SettingsManager.AddSetting("PairedProfileSetting", pairedProfileSave);
		_SettingsManager.SaveSettings();
		if (asyncToUi)
		{
			App.m_MQTTService.Publish("PairedProfileSetting", pairedProfileSave, retain: false);
		}
	}

	private void AddPairedApplication(ProfileControl profile, bool asyncToUi = false)
	{
		int num = profileNameList.FindIndex((ProfileControl x) => x.PairedApplicationName == profile.PairedApplicationName);
		if (num == -1)
		{
			profileNameList.Add(profile);
			AddPairedApplicationName(profile.PairedApplicationName);
		}
		else
		{
			profileNameList[num].ProfileName = profile.ProfileName;
			profileNameList[num].OperatingGamingProfileIndex = profile.OperatingGamingProfileIndex;
			profileNameList[num].RGBKeyboardProfileIndex = profile.RGBKeyboardProfileIndex;
			profileNameList[num].RGBLightbarProfileIndex = profile.RGBLightbarProfileIndex;
		}
		SaveCommand(asyncToUi: true);
	}

	private void RemovePairedApplication(string ApplicationName, bool asyncToUi = false)
	{
		ProfileControl profileControl = profileNameList.SingleOrDefault((ProfileControl x) => x.PairedApplicationName == ApplicationName);
		if (profileControl != null)
		{
			profileNameList.Remove(profileControl);
			RemovePairedApplicationName(ApplicationName);
			SaveCommand(asyncToUi: true);
		}
	}

	[DllImport("user32.dll")]
	private static extern IntPtr GetForegroundWindow();

	[DllImport("user32.dll")]
	private static extern int GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);

	[DllImport("user32.dll")]
	private static extern IntPtr SetWinEventHook(uint eventMin, uint eventMax, IntPtr hmodWinEventProc, WinEventDelegate lpfnWinEventProc, uint idProcess, uint idThread, uint dwFlags);

	[DllImport("user32.dll")]
	private static extern bool UnhookWinEvent(IntPtr hWinEventHook);

	private void HookWinEvent()
	{
		UnhookWinEvent();
		hhook = SetWinEventHook(3u, 3u, IntPtr.Zero, procDelegate, 0u, 0u, 0u);
	}

	private void UnhookWinEvent()
	{
		if (hhook != IntPtr.Zero)
		{
			UnhookWinEvent(hhook);
		}
	}

	private static void WinEventProc(IntPtr hWinEventHook, uint eventType, IntPtr hwnd, int idObject, int idChild, uint dwEventThread, uint dwmsEventTime)
	{
		string processname = GetForegroundProcessName();
		if (PairedApplicationNames.Contains(processname))
		{
			foreach (string pairedApplicationName in PairedApplicationNames)
			{
				if (processname == pairedApplicationName.ToString())
				{
					Console.WriteLine($"--------------------------{pairedApplicationName} is currently focused.");
					LogCtrl.TraceMessage($"--------------------------{pairedApplicationName} is currently focused.", "WinEventProc", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyPairedProfile\\PairedProfile_Manager.cs", 300);
					ProfileControl profileControl = profileNameList.SingleOrDefault((ProfileControl n) => n.PairedApplicationName.Equals(processname));
					if (profileControl != null)
					{
						Console.WriteLine("selectdProfile.OperatingGamingProfileIndex: " + profileControl.OperatingGamingProfileIndex);
						MyFanCtrl.Instance.SetPairedProfileIndex(profileControl.OperatingGamingProfileIndex);
					}
					bIsWinEventProcFocused = true;
				}
			}
			return;
		}
		if (bIsWinEventProcFocused)
		{
			Console.WriteLine("--------------------------PairedApplicationNames is not currently focused.");
			LogCtrl.TraceMessage("--------------------------PairedApplicationNames is not currently focused.", "WinEventProc", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyPairedProfile\\PairedProfile_Manager.cs", 319);
			MyFanCtrl.Instance.SetPairedProfileIndex(0u);
			bIsWinEventProcFocused = false;
		}
	}

	private static string GetForegroundProcessName()
	{
		IntPtr foregroundWindow = GetForegroundWindow();
		GetWindowThreadProcessId(foregroundWindow, out var lpdwProcessId);
		Process[] processes = Process.GetProcesses();
		foreach (Process process in processes)
		{
			if (process.Id == lpdwProcessId)
			{
				return process.ProcessName;
			}
		}
		return "Unknown";
	}

	private void AddPairedApplicationName(string name)
	{
		if (name != null)
		{
			PairedApplicationNames.Add(name);
		}
	}

	private void RemovePairedApplicationName(string name)
	{
		if (name != null)
		{
			PairedApplicationNames.Remove(name);
		}
	}

	private void ClearPairedApplicationNameAll()
	{
		if (PairedApplicationNames != null)
		{
			PairedApplicationNames.Clear();
		}
	}
}
