using System;
using System.ServiceModel;
using System.ServiceModel.Description;

namespace GCUService.WCFService;

internal class WCFServiceHost
{
	private ServiceHost host;

	public WCFServiceHost()
	{
		if (host == null)
		{
			try
			{
				string uriString = "http://localhost:58594/Service";
				host = new ServiceHost(typeof(WCFService), new Uri(uriString));
				NetHttpBinding binding = new NetHttpBinding
				{
					OpenTimeout = new TimeSpan(1, 0, 0, 0),
					CloseTimeout = new TimeSpan(1, 0, 0, 0),
					ReceiveTimeout = new TimeSpan(1, 0, 0, 0),
					SendTimeout = new TimeSpan(1, 0, 0, 0)
				};
				host.AddServiceEndpoint(typeof(IWCFService), binding, "");
				ServiceMetadataBehavior item = new ServiceMetadataBehavior
				{
					HttpGetEnabled = true
				};
				host.Description.Behaviors.Add(item);
				host.Open();
			}
			catch (Exception)
			{
			}
		}
	}

	public void CloseConnect()
	{
		host.Close();
	}
}
