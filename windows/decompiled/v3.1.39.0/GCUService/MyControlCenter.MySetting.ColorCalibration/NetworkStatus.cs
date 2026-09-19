using System;
using System.Net.NetworkInformation;
using System.Runtime.CompilerServices;

namespace MyControlCenter.MySetting.ColorCalibration;

public static class NetworkStatus
{
	private static bool isAvailable;

	private static NetworkStatusChangedHandler handler;

	public static bool IsAvailable => isAvailable;

	public static event NetworkStatusChangedHandler AvailabilityChanged
	{
		[MethodImpl(MethodImplOptions.Synchronized)]
		add
		{
			if (handler == null)
			{
				NetworkChange.NetworkAvailabilityChanged += DoNetworkAvailabilityChanged;
				NetworkChange.NetworkAddressChanged += DoNetworkAddressChanged;
			}
			handler = (NetworkStatusChangedHandler)Delegate.Combine(handler, value);
		}
		[MethodImpl(MethodImplOptions.Synchronized)]
		remove
		{
			handler = (NetworkStatusChangedHandler)Delegate.Remove(handler, value);
			if (handler == null)
			{
				NetworkChange.NetworkAvailabilityChanged -= DoNetworkAvailabilityChanged;
				NetworkChange.NetworkAddressChanged -= DoNetworkAddressChanged;
			}
		}
	}

	static NetworkStatus()
	{
		isAvailable = IsNetworkAvailable();
	}

	private static bool IsNetworkAvailable()
	{
		if (NetworkInterface.GetIsNetworkAvailable())
		{
			NetworkInterface[] allNetworkInterfaces = NetworkInterface.GetAllNetworkInterfaces();
			foreach (NetworkInterface networkInterface in allNetworkInterfaces)
			{
				if (networkInterface.OperationalStatus == OperationalStatus.Up && networkInterface.NetworkInterfaceType != NetworkInterfaceType.Tunnel && networkInterface.NetworkInterfaceType != NetworkInterfaceType.Loopback)
				{
					IPv4InterfaceStatistics iPv4Statistics = networkInterface.GetIPv4Statistics();
					if (iPv4Statistics.BytesReceived > 0 && iPv4Statistics.BytesSent > 0)
					{
						return true;
					}
				}
			}
		}
		return false;
	}

	private static void DoNetworkAddressChanged(object sender, EventArgs e)
	{
		SignalAvailabilityChange(sender);
	}

	private static void DoNetworkAvailabilityChanged(object sender, NetworkAvailabilityEventArgs e)
	{
		SignalAvailabilityChange(sender);
	}

	private static void SignalAvailabilityChange(object sender)
	{
		bool flag = IsNetworkAvailable();
		if (flag != isAvailable)
		{
			isAvailable = flag;
			if (handler != null)
			{
				handler(sender, new NetworkStatusChangedArgs(isAvailable));
			}
		}
	}
}
