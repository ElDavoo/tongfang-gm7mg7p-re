namespace MyControlCenter;

internal class MySystemView
{
	public void SendStatusToClient(string topic, object data, bool retanin = false)
	{
		App.m_MQTTService.Publish(topic, data, retanin);
	}
}
