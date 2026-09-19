using System;
using System.Collections.Generic;
using System.Linq;
using System.Net.NetworkInformation;
using System.Text;
using Utility;

namespace MyControlCenter;

internal class NetworkInfo
{
	private static int detectcn = 0;

	private static long bytesRX = -1L;

	private static long bytesTX = -1L;

	private static NetworkInterface[] interfaces;

	private IEnumerable<NetworkInterface> nics;

	private static readonly string[] SizeSuffixes = new string[8] { "Kbps", "Mbps", "Gbps", "Tbps", "Pbps", "Ebps", "Zbps", "Ybps" };

	public NetworkInfo()
	{
		NetworkChange.NetworkAddressChanged += AddressChangedCallback;
		InitNetwork();
	}

	private static void AddressChangedCallback(object sender, EventArgs e)
	{
		bytesRX = -1L;
		bytesTX = -1L;
	}

	public bool CheckNetworkInfo()
	{
		if (interfaces == null)
		{
			InitNetwork();
			return false;
		}
		return true;
	}

	private static void InitNetwork()
	{
		try
		{
			detectcn = 0;
			if (!NetworkInterface.GetIsNetworkAvailable())
			{
				return;
			}
			interfaces = NetworkInterface.GetAllNetworkInterfaces();
			NetworkInterface[] array = interfaces;
			foreach (NetworkInterface networkInterface in array)
			{
				if (networkInterface.OperationalStatus == OperationalStatus.Up && (networkInterface.NetworkInterfaceType == NetworkInterfaceType.Wireless80211 || networkInterface.NetworkInterfaceType == NetworkInterfaceType.Ethernet))
				{
					IPv4InterfaceStatistics iPv4Statistics = networkInterface.GetIPv4Statistics();
					if (iPv4Statistics.BytesReceived > 0 && iPv4Statistics.BytesSent > 0)
					{
						break;
					}
				}
				detectcn++;
			}
		}
		catch (Exception ex)
		{
			LogCtrl.TraceMessage(ex.ToString(), "InitNetwork", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MySystem\\NetworkInfo.cs", 86);
		}
	}

	public double GetDownloadSpeed()
	{
		double result = 0.0;
		long num = 0L;
		try
		{
			if (nics == null)
			{
				nics = (from n in NetworkInterface.GetAllNetworkInterfaces()
					where (n.NetworkInterfaceType == NetworkInterfaceType.Ethernet || n.NetworkInterfaceType == NetworkInterfaceType.Wireless80211) && n.OperationalStatus == OperationalStatus.Up
					select n).AsEnumerable();
			}
			foreach (NetworkInterface nic in nics)
			{
				num += nic.GetIPv4Statistics().BytesReceived;
			}
			result = ((bytesRX != -1) ? ((double)((num - bytesRX) * 8 / 1024 / 2)) : 0.0);
			bytesRX = num;
		}
		catch (Exception ex)
		{
			LogCtrl.TraceMessage("Exception: " + ex, "GetDownloadSpeed", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MySystem\\NetworkInfo.cs", 121);
		}
		return result;
	}

	public double GetUploadSpeed()
	{
		double result = 0.0;
		long num = 0L;
		try
		{
			if (nics == null)
			{
				nics = (from n in NetworkInterface.GetAllNetworkInterfaces()
					where (n.NetworkInterfaceType == NetworkInterfaceType.Ethernet || n.NetworkInterfaceType == NetworkInterfaceType.Wireless80211) && n.OperationalStatus == OperationalStatus.Up
					select n).AsEnumerable();
			}
			foreach (NetworkInterface nic in nics)
			{
				num += nic.GetIPv4Statistics().BytesSent;
			}
			result = ((bytesTX != -1) ? ((double)((num - bytesTX) * 8 / 1024 / 2)) : 0.0);
			bytesTX = num;
		}
		catch (Exception ex)
		{
			LogCtrl.TraceMessage("Exception: " + ex, "GetUploadSpeed", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MySystem\\NetworkInfo.cs", 160);
		}
		return result;
	}

	public void FormatSpeed(double value, ref double size, ref string unit, int decimalPlaces = 0)
	{
		if (decimalPlaces < 0)
		{
			throw new ArgumentOutOfRangeException("decimalPlaces");
		}
		if (value < 0.0)
		{
			FormatSpeed(0.0 - value, ref size, ref unit, decimalPlaces);
			size = 0.0 - size;
			return;
		}
		if (value == 0.0)
		{
			size = 0.0;
			unit = "Kbps";
			return;
		}
		int num = (int)Math.Log(value, 1024.0);
		decimal num2 = (decimal)value / (decimal)(1L << num * 10);
		if (Math.Round(num2, decimalPlaces) >= 1000m)
		{
			num++;
			num2 /= 1024m;
		}
		size = (double)num2;
		unit = SizeSuffixes[num];
	}

	private static void LogNetworkInfo()
	{
		try
		{
			StringBuilder stringBuilder = new StringBuilder();
			NetworkInterface[] array = (from n in NetworkInterface.GetAllNetworkInterfaces()
				where n.NetworkInterfaceType == NetworkInterfaceType.Ethernet || n.NetworkInterfaceType == NetworkInterfaceType.Wireless80211
				select n).ToArray();
			stringBuilder.Append("\n");
			NetworkInterface[] array2 = array;
			foreach (NetworkInterface networkInterface in array2)
			{
				stringBuilder.AppendFormat("{0} | {1} | {2} | {3} | {4}\n", networkInterface.Id, networkInterface.Name, networkInterface.Description, networkInterface.NetworkInterfaceType, networkInterface.OperationalStatus);
				UnicastIPAddressInformationCollection unicastAddresses = networkInterface.GetIPProperties().UnicastAddresses;
				if (unicastAddresses.Count > 0)
				{
					foreach (UnicastIPAddressInformation item in unicastAddresses)
					{
						stringBuilder.AppendFormat("  Unicast Address ......................... : {0}\n", item.Address);
					}
				}
				IPv4InterfaceStatistics iPv4Statistics = networkInterface.GetIPv4Statistics();
				if (iPv4Statistics.BytesReceived > 0 && iPv4Statistics.BytesSent > 0)
				{
					stringBuilder.AppendFormat("  BytesReceived ........................... : {0}\n", iPv4Statistics.BytesReceived);
					stringBuilder.AppendFormat("  BytesSent ............................... : {0}\n", iPv4Statistics.BytesSent);
				}
			}
			LogCtrl.TraceMessage(stringBuilder.ToString(), "LogNetworkInfo", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MySystem\\NetworkInfo.cs", 280);
		}
		catch (Exception ex)
		{
			LogCtrl.TraceMessage(ex.ToString(), "LogNetworkInfo", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MySystem\\NetworkInfo.cs", 284);
		}
	}
}
