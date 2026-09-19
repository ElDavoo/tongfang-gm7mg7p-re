using System;
using System.Linq;
using System.Management;

namespace MyControlCenter;

internal class MemoryInfo
{
	private const int BytesPerGB = 1048576;

	private ManagementObjectSearcher wmiObject = new ManagementObjectSearcher("select * from Win32_OperatingSystem");

	public dynamic GetMemoryUsage()
	{
		var anon = (from ManagementObject mo in wmiObject.Get()
			select new
			{
				FreePhysicalMemory = double.Parse(mo["FreePhysicalMemory"].ToString()),
				TotalVisibleMemorySize = double.Parse(mo["TotalVisibleMemorySize"].ToString())
			}).FirstOrDefault();
		if (anon != null)
		{
			double num = Math.Round(anon.TotalVisibleMemorySize / 1048576.0, 1);
			double num2 = Math.Round((anon.TotalVisibleMemorySize - anon.FreePhysicalMemory) / 1048576.0, 1);
			double num3 = Math.Round(num2 / num * 100.0);
			return new
			{
				TotalMemory = num,
				TotalUsingMemory = num2,
				MemoryUsage = (int)num3
			};
		}
		return null;
	}
}
