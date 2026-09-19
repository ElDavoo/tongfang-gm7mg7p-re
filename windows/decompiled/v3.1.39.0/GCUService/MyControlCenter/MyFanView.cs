namespace MyControlCenter;

internal class MyFanView
{
	public void SendStatusToClient(object data)
	{
		App.m_MQTTService.Publish("Fan/Status", data, retain: false);
	}
}
