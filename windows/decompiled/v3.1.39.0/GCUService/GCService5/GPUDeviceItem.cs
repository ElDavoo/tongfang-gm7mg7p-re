using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Windows.Forms;
using Magic.Samples.DisplaySettings;
using MyControlCenter;
using Utility;

namespace GCService5;

public class GPUDeviceItem
{
	private SettingsManager GPUPowerSavingSetting;

	private GPUPowerSavingSettings settings = new GPUPowerSavingSettings();

	private const string EnableGPUCmdString = "Enable-PnpDevice -InstanceId (Get-PnpDevice -FriendlyName *NVIDIA* -Class Display -Status Error).InstanceId -Confirm:$false";

	private const string DisableGPUCmdString = "Disable-PnpDevice -InstanceId (Get-PnpDevice -FriendlyName *NVIDIA* -Class Display -Status OK).InstanceId -Confirm:$false";

	private MqttClientCtrl m_MQTTClient = MqttClientCtrl.Instance;

	private GPUPORWERSAVING currentSaveingMode;

	public GPUDeviceItem()
	{
		Init();
	}

	public dynamic GetGPUStatus()
	{
		return new { settings.currentSaveingMode, settings.currentHZ, settings.currentHZList };
	}

	private void Init()
	{
		string text = Directory.GetParent(Assembly.GetExecutingAssembly().Location)?.ToString() + "\\GPUPowerSavingSettings\\";
		GPUPowerSavingSetting = new SettingsManager(text + "GPUPowerSavingSettings.json");
		GPUPowerSavingSetting.GetSetting<GPUPowerSavingSettings>("GPUPowerSaving", out settings);
		if (settings == null)
		{
			settings = new GPUPowerSavingSettings();
			settings.currentSaveingMode = GPUPORWERSAVING.ENABLE;
		}
		settings.currentHZList = GetDisplayList().First().Value;
	}

	public void UpudateGpuStatus2Client()
	{
		SendToUI(GetGPUStatus());
	}

	private void SendToUI(dynamic status)
	{
		m_MQTTClient.Publish("GPUDevice/Status", status, false);
	}

	public void DisplayPowerSavingMode(GPUPORWERSAVING mode)
	{
		switch (mode)
		{
		case GPUPORWERSAVING.ENABLE:
			ExecuteCommandPs1("enableDGpu.ps1");
			break;
		case GPUPORWERSAVING.DISABLE:
			ExecuteCommandPs1("disableDGpu.ps1");
			break;
		case GPUPORWERSAVING.AUTO:
		{
			string command = "dGpuCycle.bat";
			ExecuteCommand(command);
			break;
		}
		}
		settings.currentSaveingMode = mode;
		GPUPowerSavingSetting.AddSetting("GPUPowerSaving", settings);
		GPUPowerSavingSetting.SaveSettings();
	}

	public List<string> GetGPUUsageList()
	{
		return new List<string>();
	}

	public Dictionary<string, List<string>> GetDisplayList()
	{
		List<SafeNativeMethods.DISPLAY_DEVICE> list = Display();
		Dictionary<string, List<string>> dictionary = new Dictionary<string, List<string>>();
		foreach (SafeNativeMethods.DISPLAY_DEVICE item in list)
		{
			string deviceName = item.DeviceName;
			IEnumerable<SafeNativeMethods.DEVMODE> source = DisplayManager.EnumerateCompatibleModes(deviceName);
			List<string> list2 = new List<string>();
			foreach (IGrouping<uint, SafeNativeMethods.DEVMODE> item2 in from n in source
				group n by n.dmDisplayFrequency)
			{
				list2.Add(item2.First().dmDisplayFrequency.ToString());
			}
			dictionary.Add(deviceName, list2);
		}
		return dictionary;
	}

	public void SetDisplayHZ(int freq)
	{
		foreach (SafeNativeMethods.DISPLAY_DEVICE item in Display())
		{
			try
			{
				string deviceName = item.DeviceName;
				DisplaySettings currentSettings = DisplayManager.GetCurrentSettings(deviceName);
				currentSettings.Frequency = Convert.ToInt32(freq);
				DisplayManager.SetDisplaySettings(currentSettings, deviceName);
				Console.WriteLine(currentSettings.Frequency);
			}
			catch (Exception)
			{
			}
		}
		settings.currentHZ = freq;
		GPUPowerSavingSetting.AddSetting("GPUPowerSaving", settings);
		GPUPowerSavingSetting.SaveSettings();
	}

	private List<SafeNativeMethods.DISPLAY_DEVICE> Display()
	{
		List<SafeNativeMethods.DISPLAY_DEVICE> list = new List<SafeNativeMethods.DISPLAY_DEVICE>();
		SafeNativeMethods.DISPLAY_DEVICE lpDisplayDevice = default(SafeNativeMethods.DISPLAY_DEVICE);
		lpDisplayDevice.cb = Marshal.SizeOf(lpDisplayDevice);
		try
		{
			for (uint num = 0u; SafeNativeMethods.EnumDisplayDevices(null, num, ref lpDisplayDevice, 0); num++)
			{
				if (lpDisplayDevice.StateFlags.HasFlag(SafeNativeMethods.DisplayDeviceStateFlags.AttachedToDesktop))
				{
					list.Add(lpDisplayDevice);
					lpDisplayDevice.cb = Marshal.SizeOf(lpDisplayDevice);
					SafeNativeMethods.EnumDisplayDevices(lpDisplayDevice.DeviceName, 0u, ref lpDisplayDevice, 0);
					Console.WriteLine($"{lpDisplayDevice.DeviceName}, {lpDisplayDevice.DeviceString}");
				}
			}
		}
		catch (Exception ex)
		{
			Console.WriteLine($"{ex.ToString()}");
		}
		return list;
	}

	private void ExecuteCommand(string command)
	{
		Process process = Process.Start(new ProcessStartInfo("cmd.exe", "/c " + command)
		{
			CreateNoWindow = true,
			UseShellExecute = false,
			RedirectStandardError = true,
			RedirectStandardOutput = true
		});
		process.WaitForExit();
		process.StandardOutput.ReadToEnd();
		process.StandardError.ReadToEnd();
		_ = process.ExitCode;
		process.Close();
	}

	private static string ExecuteCommandPs1(string command)
	{
		string text = Application.ExecutablePath.Replace("GCUService.exe", "") + "\\Command\\";
		text = "powershell.exe -ExecutionPolicy Bypass -File \"" + text;
		text += command;
		Process process = Process.Start(new ProcessStartInfo("cmd.exe", "/c " + text)
		{
			CreateNoWindow = true,
			UseShellExecute = false,
			RedirectStandardError = true,
			RedirectStandardOutput = true
		});
		process.WaitForExit();
		string result = process.StandardOutput.ReadToEnd();
		process.StandardError.ReadToEnd();
		Console.WriteLine("ExitCode: " + process.ExitCode, "ExecuteCommand");
		process.Close();
		return result;
	}

	private void ExecutePowerShellCmd(string strCmdText)
	{
		Process process = new Process();
		process.StartInfo.UseShellExecute = false;
		process.StartInfo.RedirectStandardOutput = true;
		process.StartInfo.FileName = "C:\\windows\\system32\\windowspowershell\\v1.0\\powershell.exe";
		process.StartInfo.Arguments = "-windowstyle hidden " + strCmdText;
		process.Start();
		process.StandardOutput.ReadToEnd();
		process.WaitForExit();
	}
}
