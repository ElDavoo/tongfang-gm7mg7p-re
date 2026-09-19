using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Management;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices.WindowsRuntime;
using System.Threading.Tasks;
using System.Windows.Forms;
using MyControlCenter;
using UniwillConsole;
using Windows.Devices.Enumeration;
using Windows.Devices.Radios;
using Windows.Foundation;

namespace GCService5;

public class DeviceSwitchItem
{
	private const string EnableCamd = "Enable-PnpDevice -InstanceId (Get-PnpDevice -FriendlyName *Webcam* -Class Camera -Status Error).InstanceId -Confirm:$false";

	private const string DisableCamd = "Disable-PnpDevice -InstanceId (Get-PnpDevice -FriendlyName *Webcam* -Class Camera -Status OK).InstanceId -Confirm:$false";

	private const string SearchStatus = "Get-PnpDevice -FriendlyName *webcam* -Class Camera -Status OK";

	private MqttClientCtrl m_MQTTClient = MqttClientCtrl.Instance;

	private object wifilock = new object();

	private bool WIFIEnable { get; set; }

	private bool BTEnable { get; set; }

	private bool WebCamEnable { get; set; }

	private bool TochpadEnable { get; set; }

	private uint ScreenBrightness { get; set; }

	private Radio WIFIModel { get; set; }

	private Radio BTModel { get; set; }

	public DeviceSwitchItem()
	{
		Task.Run(async delegate
		{
			await InitializeAsync();
		}).Wait();
		Radio bTModel = BTModel;
		WindowsRuntimeMarshal.AddEventHandler((Func<TypedEventHandler<Radio, object>, EventRegistrationToken>)bTModel.add_StateChanged, (Action<EventRegistrationToken>)bTModel.remove_StateChanged, (TypedEventHandler<Radio, object>)BTModel_StateChanged);
		bTModel = WIFIModel;
		WindowsRuntimeMarshal.AddEventHandler((Func<TypedEventHandler<Radio, object>, EventRegistrationToken>)bTModel.add_StateChanged, (Action<EventRegistrationToken>)bTModel.remove_StateChanged, (TypedEventHandler<Radio, object>)WIFIModel_StateChanged);
		WebCamEnable = InitCamStatus();
		ScreenBrightness = GetCurrentBrightness();
		EventWatcherAsync eventWatcherAsync = new EventWatcherAsync();
		eventWatcherAsync.brightnessChangeEvnet = (EventArrivedEventHandler)Delegate.Combine(eventWatcherAsync.brightnessChangeEvnet, new EventArrivedEventHandler(BrightnessEventHandler));
	}

	private void BrightnessEventHandler(object sender, EventArrivedEventArgs e)
	{
		Console.WriteLine("Active :          " + e.NewEvent.Properties["Active"].Value.ToString());
		Console.WriteLine("Brightness :      " + e.NewEvent.Properties["Brightness"].Value.ToString());
		Console.WriteLine("InstanceName :    " + e.NewEvent.Properties["InstanceName"].Value.ToString());
		ScreenBrightness = Convert.ToUInt32(e.NewEvent.Properties["Brightness"].Value);
		UpdateToClient();
	}

	private uint GetCurrentBrightness()
	{
		try
		{
			ManagementScope scope = new ManagementScope("root\\WMI");
			SelectQuery query = new SelectQuery("WmiMonitorBrightness");
			ManagementObjectSearcher managementObjectSearcher = new ManagementObjectSearcher(scope, query);
			ManagementObjectCollection managementObjectCollection = managementObjectSearcher.Get();
			byte result = 0;
			using (ManagementObjectCollection.ManagementObjectEnumerator managementObjectEnumerator = managementObjectCollection.GetEnumerator())
			{
				if (managementObjectEnumerator.MoveNext())
				{
					result = (byte)((ManagementObject)managementObjectEnumerator.Current).GetPropertyValue("CurrentBrightness");
				}
			}
			managementObjectCollection.Dispose();
			managementObjectSearcher.Dispose();
			return result;
		}
		catch (Exception)
		{
		}
		return 100u;
	}

	public void SetBrightness(int targetBrightness)
	{
		ManagementScope scope = new ManagementScope("root\\WMI");
		SelectQuery query = new SelectQuery("WmiMonitorBrightnessMethods");
		ManagementObjectSearcher managementObjectSearcher = new ManagementObjectSearcher(scope, query);
		ManagementObjectCollection managementObjectCollection = managementObjectSearcher.Get();
		using (ManagementObjectCollection.ManagementObjectEnumerator managementObjectEnumerator = managementObjectCollection.GetEnumerator())
		{
			if (managementObjectEnumerator.MoveNext())
			{
				((ManagementObject)managementObjectEnumerator.Current).InvokeMethod("WmiSetBrightness", new object[2]
				{
					uint.MaxValue,
					targetBrightness
				});
			}
		}
		managementObjectCollection.Dispose();
		managementObjectSearcher.Dispose();
	}

	public void SetTouchpadSwitch(bool Enable)
	{
		TochpadEnable = Enable;
		UpdateToClient();
	}

	public void TriggerTouchpad()
	{
		SendKeyLock.SetState(VirtualKeys.VK_WINKEY, VirtualKeys.VK_L_CTRL, VirtualKeys.VK_F24);
	}

	private void WIFIModel_StateChanged(Radio sender, object args)
	{
		//IL_0004: Unknown result type (might be due to invalid IL or missing references)
		//IL_000a: Invalid comparison between Unknown and I4
		WIFIEnable = (int)sender.State == 1;
		UpdateToClient();
	}

	private void BTModel_StateChanged(Radio sender, object args)
	{
		//IL_0004: Unknown result type (might be due to invalid IL or missing references)
		//IL_000a: Invalid comparison between Unknown and I4
		BTEnable = (int)sender.State == 1;
		UpdateToClient();
	}

	public void UpdateToClient()
	{
		dynamic val = new
		{
			WIFIEnable = WIFIEnable,
			BTEnable = BTEnable,
			WebCamEnable = WebCamEnable,
			TochpadEnable = TochpadEnable,
			ScreenBrightness = GetCurrentBrightness()
		};
		m_MQTTClient.PublishTopic("Settings/DeviceSwitchItemStatus", val, MqttQualityOfServiceLevel.ExactlyOnce);
	}

	private async Task InitializeAsync()
	{
		TaskAwaiter<DeviceInformationCollection> taskAwaiter = WindowsRuntimeSystemExtensions.GetAwaiter<DeviceInformationCollection>(DeviceInformation.FindAllAsync(Radio.GetDeviceSelector()));
		if (!taskAwaiter.IsCompleted)
		{
			await taskAwaiter;
			TaskAwaiter<DeviceInformationCollection> taskAwaiter2 = default(TaskAwaiter<DeviceInformationCollection>);
			taskAwaiter = taskAwaiter2;
		}
		DeviceInformationCollection result = taskAwaiter.GetResult();
		TaskAwaiter<Radio> taskAwaiter4 = default(TaskAwaiter<Radio>);
		foreach (DeviceInformation item in (IEnumerable<DeviceInformation>)result)
		{
			TaskAwaiter<Radio> taskAwaiter3 = WindowsRuntimeSystemExtensions.GetAwaiter<Radio>(Radio.FromIdAsync(item.Id));
			if (!taskAwaiter3.IsCompleted)
			{
				await taskAwaiter3;
				taskAwaiter3 = taskAwaiter4;
				taskAwaiter4 = default(TaskAwaiter<Radio>);
			}
			Radio result2 = taskAwaiter3.GetResult();
			if ((int)result2.Kind == 1)
			{
				WIFIModel = result2;
				WIFIEnable = (int)result2.State == 1;
			}
			if ((int)result2.Kind == 3)
			{
				BTModel = result2;
				BTEnable = (int)result2.State == 1;
			}
		}
		WebCamEnable = InitCamStatus();
	}

	private bool InitCamStatus()
	{
		if (ExecuteCommand("SearchCamStatus.ps1\"") != "")
		{
			return true;
		}
		return false;
	}

	public async void BTSwitch(bool enable)
	{
		BTEnable = enable;
		SetBTStatusAsync(enable);
	}

	private async void SetBTStatusAsync(bool IsOn)
	{
		_ = 1;
		try
		{
			TaskAwaiter<RadioAccessStatus> taskAwaiter = WindowsRuntimeSystemExtensions.GetAwaiter<RadioAccessStatus>(Radio.RequestAccessAsync());
			TaskAwaiter<RadioAccessStatus> taskAwaiter2 = default(TaskAwaiter<RadioAccessStatus>);
			if (!taskAwaiter.IsCompleted)
			{
				await taskAwaiter;
				taskAwaiter = taskAwaiter2;
				taskAwaiter2 = default(TaskAwaiter<RadioAccessStatus>);
			}
			RadioAccessStatus result = taskAwaiter.GetResult();
			if (1 == (int)result)
			{
				RadioState stateAsync = (RadioState)(IsOn ? 1 : 2);
				taskAwaiter = WindowsRuntimeSystemExtensions.GetAwaiter<RadioAccessStatus>(BTModel.SetStateAsync(stateAsync));
				if (!taskAwaiter.IsCompleted)
				{
					await taskAwaiter;
					taskAwaiter = taskAwaiter2;
				}
				taskAwaiter.GetResult();
			}
		}
		catch (Exception)
		{
		}
	}

	public void WIFISwitch(bool enable)
	{
		WIFIEnable = enable;
		SetwifiStatusAsync(enable);
	}

	private async void SetwifiStatusAsync(bool IsOn)
	{
		_ = 1;
		try
		{
			TaskAwaiter<RadioAccessStatus> taskAwaiter = WindowsRuntimeSystemExtensions.GetAwaiter<RadioAccessStatus>(Radio.RequestAccessAsync());
			TaskAwaiter<RadioAccessStatus> taskAwaiter2 = default(TaskAwaiter<RadioAccessStatus>);
			if (!taskAwaiter.IsCompleted)
			{
				await taskAwaiter;
				taskAwaiter = taskAwaiter2;
				taskAwaiter2 = default(TaskAwaiter<RadioAccessStatus>);
			}
			RadioAccessStatus result = taskAwaiter.GetResult();
			if (1 == (int)result)
			{
				RadioState stateAsync = (RadioState)(IsOn ? 1 : 2);
				taskAwaiter = WindowsRuntimeSystemExtensions.GetAwaiter<RadioAccessStatus>(WIFIModel.SetStateAsync(stateAsync));
				if (!taskAwaiter.IsCompleted)
				{
					await taskAwaiter;
					taskAwaiter = taskAwaiter2;
				}
				taskAwaiter.GetResult();
			}
		}
		catch (Exception)
		{
		}
	}

	public void CamSwitch(bool enable)
	{
		WebCamEnable = enable;
		if (enable)
		{
			ExecuteCommand("enableWebcam.ps1\"");
		}
		else
		{
			ExecuteCommand("disableWebcam.ps1\"");
		}
	}

	private static string ExecuteCommand(string command)
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

	private static string ExecutePowerShellCmd(string strCmdText)
	{
		Process process = new Process();
		process.StartInfo.UseShellExecute = false;
		process.StartInfo.RedirectStandardOutput = true;
		process.StartInfo.FileName = "C:\\windows\\system32\\windowspowershell\\v1.0\\powershell.exe";
		process.StartInfo.Arguments = "-windowstyle hidden " + strCmdText;
		process.Start();
		string result = process.StandardOutput.ReadToEnd();
		process.WaitForExit();
		return result;
	}
}
