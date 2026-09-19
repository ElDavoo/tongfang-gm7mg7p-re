using System;
using System.Management;

namespace GCService5;

public class EventWatcherAsync
{
	public EventArrivedEventHandler brightnessChangeEvnet;

	private void WmiEventHandler(object sender, EventArrivedEventArgs e)
	{
		if (brightnessChangeEvnet != null)
		{
			brightnessChangeEvnet(sender, e);
		}
	}

	public EventWatcherAsync()
	{
		try
		{
			string text = "localhost";
			ManagementScope managementScope;
			if (!text.Equals("localhost", StringComparison.OrdinalIgnoreCase))
			{
				ConnectionOptions options = new ConnectionOptions
				{
					Username = "",
					Password = "",
					Authority = "ntlmdomain:DOMAIN"
				};
				managementScope = new ManagementScope($"\\\\{text}\\root\\WMI", options);
			}
			else
			{
				managementScope = new ManagementScope($"\\\\{text}\\root\\WMI", null);
			}
			managementScope.Connect();
			string query = "Select * From WmiMonitorBrightnessEvent";
			ManagementEventWatcher managementEventWatcher = new ManagementEventWatcher(managementScope, new EventQuery(query));
			managementEventWatcher.EventArrived += WmiEventHandler;
			managementEventWatcher.Start();
		}
		catch (Exception ex)
		{
			Console.WriteLine("Exception {0} Trace {1}", ex.Message, ex.StackTrace);
		}
	}
}
