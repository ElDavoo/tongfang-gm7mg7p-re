namespace MyControlCenter;

internal class MyRgbLightbarView
{
	public void SendStatusToClient(object data)
	{
		App.m_MQTTService.Publish("MyRgbLightbar/Status", data, retain: false);
	}
}
