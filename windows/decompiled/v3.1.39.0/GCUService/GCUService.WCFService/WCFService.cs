using System;
using System.ServiceModel;
using System.ServiceModel.Channels;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using MyControlCenter;
using Newtonsoft.Json;

namespace GCUService.WCFService;

[ServiceBehavior(ConcurrencyMode = ConcurrencyMode.Multiple, UseSynchronizationContext = false, InstanceContextMode = InstanceContextMode.Single)]
public class WCFService : IWCFService
{
	private MqttClientCtrl mqttClient = MqttClientCtrl.Instance;

	private bool BasicAuth;

	private bool CallBackStart;

	private string ReturnToClientData;

	private string CpuToClientData;

	private string GpuToClientData;

	private string MemoryToClientData;

	public const string KeyboardTOPIC = "Keyboard/Ctrl";

	private int ReflashTimer = 1;

	public WCFService()
	{
		mqttClient.MqttPublishEvent -= CallBackEvent;
		mqttClient.MqttPublishEvent += CallBackEvent;
	}

	private async void CallBackEvent(object sender, EventArgs e)
	{
		if (!BasicAuth)
		{
			return;
		}
		try
		{
			string text = sender.ToString();
			if (text.Contains("CpuInfo"))
			{
				CpuToClientData = text;
			}
			else if (text.Contains("GpuInfo"))
			{
				GpuToClientData = text;
			}
			else if (text.Contains("MemoryInfo"))
			{
				MemoryToClientData = text;
			}
			else
			{
				ReturnToClientData = text;
			}
		}
		catch (Exception)
		{
		}
	}

	public void SendToServer(string topic, string Command)
	{
		if (BasicAuth)
		{
			JsonConvert.DeserializeObject(Command);
			byte[] bytes = Encoding.ASCII.GetBytes(Command);
			App.Recieve(topic, bytes);
			if (Command.Contains("System_ON"))
			{
				ReflashTimer = 1;
			}
			if (Command.Contains("System_OFF"))
			{
				ReflashTimer = 1;
			}
		}
	}

	void IWCFService.SendToServer(string topic, string Command)
	{
		//ILSpy generated this explicit interface implementation from .override directive in SendToServer
		this.SendToServer(topic, Command);
	}

	public async Task StartSendingToClient(string data)
	{
		bool flag = false;
		if (data.Contains("Inteltzuy&dBtS4wspc6"))
		{
			if (CallBackStart)
			{
				flag = true;
			}
			BasicAuth = true;
			CallBackStart = true;
		}
		else
		{
			BasicAuth = false;
			CallBackStart = false;
		}
		IDataCallback callbackChannel = OperationContext.Current.GetCallbackChannel<IDataCallback>();
		if (((IChannel)callbackChannel).State == CommunicationState.Opened)
		{
			if (flag)
			{
				CallBackByState(CallBackStart: false, callbackChannel, data);
				Thread.Sleep(500);
				CallBackByState(CallBackStart, callbackChannel, data);
			}
			else if (CallBackStart)
			{
				CallBackByState(CallBackStart, callbackChannel, data);
			}
			else
			{
				await callbackChannel.ReceiveData(BasicAuth.ToString(), "Disconnect");
			}
		}
	}

	Task IWCFService.StartSendingToClient(string data)
	{
		//ILSpy generated this explicit interface implementation from .override directive in StartSendingToClient
		return this.StartSendingToClient(data);
	}

	private async void CallBackByState(bool CallBackStart, IDataCallback callback, string data)
	{
		while (CallBackStart)
		{
			if (((IChannel)callback).State == CommunicationState.Faulted)
			{
				CallBackStart = false;
				break;
			}
			try
			{
				if (data != "")
				{
					await callback.ReceiveData(BasicAuth.ToString(), data);
					data = "";
				}
				if (GpuToClientData != null)
				{
					await callback.ReceiveData(BasicAuth.ToString(), GpuToClientData);
					GpuToClientData = null;
				}
				if (ReturnToClientData != null)
				{
					await callback.ReceiveData(BasicAuth.ToString(), ReturnToClientData);
					ReturnToClientData = null;
				}
				if (CpuToClientData != null)
				{
					await callback.ReceiveData(BasicAuth.ToString(), CpuToClientData);
					CpuToClientData = null;
				}
				if (MemoryToClientData != null)
				{
					await callback.ReceiveData(BasicAuth.ToString(), MemoryToClientData);
					MemoryToClientData = null;
				}
			}
			catch (Exception)
			{
				CallBackStart = false;
				break;
			}
			Thread.Sleep(ReflashTimer);
		}
	}
}
