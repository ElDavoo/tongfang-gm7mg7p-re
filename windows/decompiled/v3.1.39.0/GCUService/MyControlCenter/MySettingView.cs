namespace MyControlCenter;

internal class MySettingView
{
	public void SendStatusToClient(object data)
	{
		App.m_MQTTService.Publish("Setting/Status", data, retain: false);
	}
}
