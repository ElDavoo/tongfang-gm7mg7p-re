using System;
using System.Management;

namespace MyControlCenter.MySetting.ColorCalibration;

internal class Brightness
{
	public int GetBrightness()
	{
		ManagementScope scope = new ManagementScope("root\\WMI");
		SelectQuery query = new SelectQuery("WmiMonitorBrightness");
		ManagementObjectSearcher managementObjectSearcher = new ManagementObjectSearcher(scope, query);
		ManagementObjectCollection managementObjectCollection = managementObjectSearcher.Get();
		byte result = 0;
		using (ManagementObjectCollection.ManagementObjectEnumerator managementObjectEnumerator = managementObjectCollection.GetEnumerator())
		{
			if (managementObjectEnumerator.MoveNext())
			{
				result = (byte)((ManagementObject)managementObjectEnumerator.Current).GetPropertyValue("CurrentBrightness");
			}
		}
		managementObjectCollection.Dispose();
		managementObjectSearcher.Dispose();
		return result;
	}

	public byte[] GetBrightnessLevels()
	{
		ManagementScope scope = new ManagementScope("root\\WMI");
		SelectQuery query = new SelectQuery("WmiMonitorBrightness");
		ManagementObjectSearcher managementObjectSearcher = new ManagementObjectSearcher(scope, query);
		byte[] result = new byte[0];
		try
		{
			ManagementObjectCollection managementObjectCollection = managementObjectSearcher.Get();
			using (ManagementObjectCollection.ManagementObjectEnumerator managementObjectEnumerator = managementObjectCollection.GetEnumerator())
			{
				if (managementObjectEnumerator.MoveNext())
				{
					result = (byte[])((ManagementObject)managementObjectEnumerator.Current).GetPropertyValue("Level");
				}
			}
			managementObjectCollection.Dispose();
			managementObjectSearcher.Dispose();
		}
		catch (Exception)
		{
			Console.WriteLine("Sorry, Your System does not support this brightness control...");
		}
		return result;
	}

	public void SetBrightness(byte targetBrightness)
	{
		ManagementScope scope = new ManagementScope("root\\WMI");
		SelectQuery query = new SelectQuery("WmiMonitorBrightnessMethods");
		ManagementObjectSearcher managementObjectSearcher = new ManagementObjectSearcher(scope, query);
		ManagementObjectCollection managementObjectCollection = managementObjectSearcher.Get();
		using (ManagementObjectCollection.ManagementObjectEnumerator managementObjectEnumerator = managementObjectCollection.GetEnumerator())
		{
			if (managementObjectEnumerator.MoveNext())
			{
				((ManagementObject)managementObjectEnumerator.Current).InvokeMethod("WmiSetBrightness", new object[2]
				{
					uint.MaxValue,
					targetBrightness
				});
			}
		}
		managementObjectCollection.Dispose();
		managementObjectSearcher.Dispose();
	}
}
