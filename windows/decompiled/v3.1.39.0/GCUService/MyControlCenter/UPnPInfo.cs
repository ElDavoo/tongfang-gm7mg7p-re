namespace MyControlCenter;

internal class UPnPInfo
{
	private static readonly UPnPInfo uPnPInfo = new UPnPInfo();

	private UPnPInfo mQTTDatsService = Instance;

	public static UPnPInfo Instance => uPnPInfo;

	public async void GetExternalIPAddress()
	{
	}

	public async void OpenUPnP()
	{
	}
}
