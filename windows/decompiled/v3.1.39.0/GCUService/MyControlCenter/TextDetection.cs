using System;
using System.Threading.Tasks;

namespace MyControlCenter;

internal class TextDetection
{
	private MqttClientCtrl m_MQTTService = MqttClientCtrl.Instance;

	private const string Topic = "Openvino/TextDetection";

	public TextDetection()
	{
		Start();
	}

	private async void Start()
	{
		try
		{
			while (true)
			{
				await Task.Delay(100);
			}
		}
		catch (Exception)
		{
		}
	}
}
