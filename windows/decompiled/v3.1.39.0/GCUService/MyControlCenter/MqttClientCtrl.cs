using System;
using System.Collections.Generic;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Win32;
using Utility;
using uPLibrary.Networking.M2Mqtt;
using uPLibrary.Networking.M2Mqtt.Messages;

namespace MyControlCenter;

public class MqttClientCtrl
{
	public delegate void ClientMessageHandler(string topic, MqttMsgPublishEventArgs e);

	public delegate void ClientConnectionHandler(string connectMessage);

	private MqttClient client;

	private static readonly MqttClientCtrl clientService = new MqttClientCtrl();

	private static object process_lock = new object();

	private const string supportTopic = "Customize/SupportControl";

	public static MqttClientCtrl Instance => clientService;

	public event ClientMessageHandler ClientMessage;

	public event ClientConnectionHandler ClientConnection;

	public event EventHandler MqttPublishEvent;

	private MqttClientCtrl()
	{
	}

	public void Run()
	{
		SetClient("MyControlCenter", "MyControlCenterUser", "MyControlCenterPwd888881772688");
	}

	public void SetClient(string UserID, string UserName, string Password)
	{
		string brokerHostName = "localhost";
		int brokerPort = 13688;
		string[] topics = new string[18]
		{
			"Settings/DeviceSwitchItemStatus", "ProcessControl/Control", "BatteryProtection/Control", "System/Control", "Fan/Control", "MyRgbLightbar/Control", "Setting/Control", "EC/Control", "Customize/SupportControl", "Keyboard/Ctrl",
			"HidLightbar/Ctrl", "Service/Close", "Customize/Control", "Languages/Control", "Openvino/Control", "Service/Ctrl", "Display/Control", "TouchPadWorkArea/Control"
		};
		byte[] qosLevels = new byte[18];
		try
		{
			client = new MqttClient(brokerHostName, brokerPort, secure: false, null, null, MqttSslProtocols.None);
			_ = client.Settings.TimeoutOnConnection;
			client.MqttMsgPublishReceived += Client_MqttMsgPublishReceived;
			client.MqttMsgPublished += Client_MqttMsgPublished;
			client.ConnectionClosed += Client_ConnectionClosed;
			client.MqttMsgSubscribed += Client_MqttMsgSubscribed;
			client.Connect(UserID, UserName, Password, cleanSession: true, 10000);
			client.Subscribe(topics, qosLevels);
		}
		catch
		{
			Console.WriteLine("Connect Fail !");
			if (this.ClientConnection != null)
			{
				this.ClientConnection("Disconnection");
			}
		}
	}

	private static void Client_ClientMessage(string topic, object data)
	{
	}

	public async void Publish(string topic, object data, bool retain = true)
	{
		_ = 1;
		try
		{
			if (this.MqttPublishEvent != null)
			{
				string sender = await Json.StringifyAsync(new
				{
					Topic = topic,
					Data = data
				});
				this.MqttPublishEvent(sender, null);
			}
			string s = await Json.StringifyAsync(data);
			client.Publish(topic, Encoding.ASCII.GetBytes(s), 2, retain);
		}
		catch (Exception ex)
		{
			Console.WriteLine("Publish topic error ! " + ex.ToString());
		}
	}

	public async void Publish_ByUTF8(string topic, object data, bool retain = true)
	{
		try
		{
			if (this.MqttPublishEvent != null)
			{
				this.MqttPublishEvent(new
				{
					Topic = topic,
					Data = data
				}, null);
			}
			string s = await Json.StringifyAsync(data);
			client.Publish(topic, Encoding.UTF8.GetBytes(s), 2, retain);
		}
		catch (Exception ex)
		{
			Console.WriteLine("Publish topic error ! " + ex.ToString());
		}
	}

	public async void PublishTopic<T>(string topic, T payload, MqttQualityOfServiceLevel qos, bool retain = true)
	{
		try
		{
			string s = await Json.StringifyAsync(payload);
			client.Publish(topic, Encoding.ASCII.GetBytes(s), (byte)qos, retain);
		}
		catch (Exception ex)
		{
			Console.WriteLine("Publish topic error ! " + ex.ToString());
		}
	}

	private void Client_MqttMsgSubscribed(object sender, MqttMsgSubscribedEventArgs e)
	{
		Console.WriteLine("clinet subscribed " + e.MessageId);
		if (this.ClientConnection != null)
		{
			this.ClientConnection("Connection");
		}
	}

	public void Disconnect()
	{
		try
		{
			if (client.IsConnected)
			{
				client.Disconnect();
			}
		}
		catch
		{
		}
	}

	private void Client_ConnectionClosed(object sender, EventArgs e)
	{
		Console.WriteLine("clinet disconnect " + e.ToString());
		if (this.ClientConnection != null)
		{
			this.ClientConnection("Disconnection");
		}
	}

	private void Client_MqttMsgPublished(object sender, MqttMsgPublishedEventArgs e)
	{
	}

	private void Client_MqttMsgPublishReceived(object sender, MqttMsgPublishEventArgs e)
	{
		if (!Monitor.TryEnter(process_lock, 500))
		{
			return;
		}
		try
		{
			if (this.ClientMessage == null)
			{
				return;
			}
			if (e.Topic.ToString() == "Customize/SupportControl")
			{
				Task.Run(async delegate
				{
					Dictionary<string, object> dictionary = await RegistryBuilder();
					int serviceReady = Convert.ToInt32(dictionary["ServiceReady"]);
					if (serviceReady == 1)
					{
						PublishTopic("Customize/SupportInfo", dictionary, MqttQualityOfServiceLevel.ExactlyOnce);
					}
					else
					{
						while (serviceReady == 0)
						{
							dictionary = await RegistryBuilder();
							Thread.Sleep(1000);
						}
						Convert.ToInt32(dictionary["ServiceReady"]);
						PublishTopic("Customize/SupportInfo", dictionary, MqttQualityOfServiceLevel.ExactlyOnce);
					}
				});
			}
			this.ClientMessage(e.Topic, e);
		}
		catch (Exception)
		{
		}
		finally
		{
			Console.WriteLine("Release " + e.Topic.ToString() + " " + Encoding.UTF8.GetString(e.Message));
			Monitor.Exit(process_lock);
		}
	}

	private async Task<Dictionary<string, object>> RegistryBuilder()
	{
		Dictionary<string, object> dictionary = new Dictionary<string, object>();
		int customId = GetCustomId();
		dictionary.Add("CustomizeTarget", Convert.ToInt32(customId));
		IntRegistryLoader("SOFTWARE\\OEM\\GamingCenter2\\ItemSupport", "ServiceReady", dictionary);
		IntRegistryLoader("SOFTWARE\\OEM\\GamingCenter2\\ItemSupport", "AcRecoverySwitchSupport", dictionary);
		IntRegistryLoader("SOFTWARE\\OEM\\GamingCenter2\\ItemSupport", "ColorCalibrationSupport", dictionary);
		IntRegistryLoader("SOFTWARE\\OEM\\GamingCenter2\\ItemSupport", "DGpuDirectConnectionSupport", dictionary);
		IntRegistryLoader("SOFTWARE\\OEM\\GamingCenter2\\ItemSupport", "FanBoostBtnSupport", dictionary);
		IntRegistryLoader("SOFTWARE\\OEM\\GamingCenter2\\ItemSupport", "IsAMDPlatform", dictionary);
		IntRegistryLoader("SOFTWARE\\OEM\\GamingCenter2\\ItemSupport", "IsNvGpu", dictionary);
		IntRegistryLoader("SOFTWARE\\OEM\\GamingCenter2\\ItemSupport", "LightbarSupport", dictionary);
		IntRegistryLoader("SOFTWARE\\OEM\\GamingCenter2\\ItemSupport", "RGBLightbarSupport", dictionary);
		IntRegistryLoader("SOFTWARE\\OEM\\GamingCenter2\\ItemSupport", "IsProjectIdCommercial", dictionary);
		IntRegistryLoader("SOFTWARE\\OEM\\GamingCenter2\\ItemSupport", "FanSettingsSupport", dictionary);
		IntRegistryLoader("SOFTWARE\\OEM\\GamingCenter2\\ItemSupport", "NumPadSupport", dictionary);
		IntRegistryLoader("SOFTWARE\\OEM\\GamingCenter2\\ItemSupport", "OcSettingsSupport", dictionary);
		IntRegistryLoader("SOFTWARE\\OEM\\GamingCenter2\\ItemSupport", "RamFan1p5Support", dictionary);
		IntRegistryLoader("SOFTWARE\\OEM\\GamingCenter2\\ItemSupport", "SystemMonitorSupport", dictionary);
		IntRegistryLoader("SOFTWARE\\OEM\\GamingCenter2\\ItemSupport", "TurboModeSupport", dictionary);
		IntRegistryLoader("SOFTWARE\\OEM\\GamingCenter2\\ItemSupport", "TypeCSupport", dictionary);
		IntRegistryLoader("SOFTWARE\\OEM\\GamingCenter2\\ItemSupport", "IsHeroProject", dictionary);
		string value = Convert.ToString(RegistryKey.OpenBaseKey(RegistryHive.LocalMachine, RegistryView.Registry64).OpenSubKey("SOFTWARE\\OEM\\GamingCenter2\\ItemSupport")?.GetValue("BIOS_PROJECT_ID"));
		dictionary.Add("BIOS_PROJECT_ID", value);
		string value2 = (string)RegistryKey.OpenBaseKey(RegistryHive.LocalMachine, RegistryView.Registry64).OpenSubKey("SOFTWARE\\OEM\\GamingCenter2")?.GetValue("Language");
		dictionary.Add("Language", value2);
		string value3 = (string)RegistryKey.OpenBaseKey(RegistryHive.LocalMachine, RegistryView.Registry64).OpenSubKey("SOFTWARE\\OEM\\GamingCenter2")?.GetValue("LanguageList");
		dictionary.Add("LanguageList", value3);
		return dictionary;
	}

	private int GetCustomId()
	{
		object obj = 1;
		obj = RegistryKey.OpenBaseKey(RegistryHive.LocalMachine, RegistryView.Registry64)?.OpenSubKey("SOFTWARE\\OEM\\GamingCenter2")?.GetValue("CustomizeTarget", 1);
		if (obj == null)
		{
			return 1;
		}
		return Convert.ToInt32(obj);
	}

	private void IntRegistryLoader(string path, string key, Dictionary<string, object> dataset)
	{
		object obj = RegistryKey.OpenBaseKey(RegistryHive.LocalMachine, RegistryView.Registry64).OpenSubKey(path)?.GetValue(key);
		int num = ((obj != null) ? Convert.ToInt32(obj) : 0);
		dataset.Add(key, num);
	}
}
