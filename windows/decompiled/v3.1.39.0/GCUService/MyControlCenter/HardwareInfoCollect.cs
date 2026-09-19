using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Management;
using System.Runtime.InteropServices;
using System.Threading;

namespace MyControlCenter;

internal class HardwareInfoCollect
{
	[StructLayout(LayoutKind.Sequential, CharSet = CharSet.Auto)]
	private class MEMORYSTATUSEX
	{
		public uint dwLength;

		public uint dwMemoryLoad;

		public ulong ullTotalPhys;

		public ulong ullAvailPhys;

		public ulong ullTotalPageFile;

		public ulong ullAvailPageFile;

		public ulong ullTotalVirtual;

		public ulong ullAvailVirtual;

		public ulong ullAvailExtendedVirtual;

		public MEMORYSTATUSEX()
		{
			dwLength = (uint)Marshal.SizeOf(typeof(MEMORYSTATUSEX));
		}
	}

	public static bool bSysInfoRet;

	private static HardwareInfoCollect instance;

	public static Dictionary<string, string> hardwareInfoDict;

	private static List<KeyValuePair<string, string>> otherInfoList;

	private string unKnown;

	private string Mm;

	private string RecognizeFail;

	public HardwareInfoCollect()
	{
		instance = this;
		hardwareInfoDict = new Dictionary<string, string>();
		otherInfoList = new List<KeyValuePair<string, string>>();
	}

	public string getComputerInfo()
	{
		foreach (ManagementObject item in new ManagementObjectSearcher("select * from Win32_ComputerSystem").Get())
		{
			hardwareInfoDict["PCModel"] = ((item["Model"] != null) ? ((string)item["Model"]) : unKnown);
		}
		return hardwareInfoDict["PCModel"];
	}

	public string getSystemInfo()
	{
		string result = "";
		try
		{
			hardwareInfoDict["UserName"] = Environment.UserName;
			foreach (ManagementObject item in new ManagementObjectSearcher("select * from Win32_OperatingSystem").Get())
			{
				hardwareInfoDict["OSName"] = ((item["Caption"] != null) ? ((string)item["Caption"]) : unKnown);
				hardwareInfoDict["OSArchitecture"] = ((item["OSArchitecture"] != null) ? ((string)item["OSArchitecture"]) : unKnown);
				hardwareInfoDict["UserName"] = ((item["RegisteredUser"] != null) ? ((string)item["RegisteredUser"]) : unKnown);
				hardwareInfoDict["OSVersion"] = ((item["Version"] != null) ? ((string)item["Version"]) : unKnown);
				hardwareInfoDict["OSSerialNum"] = ((item["SerialNumber"] != null) ? ((string)item["SerialNumber"]) : unKnown);
			}
		}
		catch (Exception ex)
		{
			Console.WriteLine("Exception: " + ex.Message);
		}
		return result;
	}

	public string getProcessorInfo()
	{
		string result = "";
		foreach (ManagementObject item in new ManagementObjectSearcher("select * from Win32_Processor").Get())
		{
			hardwareInfoDict["ProcessorName"] = ((item["Name"] != null) ? Convert.ToString(item["Name"]) : unKnown);
			hardwareInfoDict["ProcessorCore"] = ((item["NumberOfCores"] != null) ? Convert.ToString(item["NumberOfCores"]) : unKnown);
			hardwareInfoDict["ProcessorThread"] = ((item["NumberOfLogicalProcessors"] != null) ? Convert.ToString(item["NumberOfLogicalProcessors"]) : unKnown);
			hardwareInfoDict["ProcessorMaxSpeed"] = ((item["MaxClockSpeed"] != null) ? Convert.ToString(item["MaxClockSpeed"]) : unKnown);
			result = hardwareInfoDict["ProcessorName"] + ", " + hardwareInfoDict["ProcessorMaxSpeed"] + " Mhz, " + hardwareInfoDict["ProcessorCore"] + " Core(s), " + hardwareInfoDict["ProcessorThread"] + " Logical Processor(s)";
		}
		return result;
	}

	public string getProcessorType()
	{
		using (ManagementObjectCollection.ManagementObjectEnumerator managementObjectEnumerator = new ManagementObjectSearcher("select * from Win32_Processor").Get().GetEnumerator())
		{
			if (managementObjectEnumerator.MoveNext())
			{
				ManagementObject managementObject = (ManagementObject)managementObjectEnumerator.Current;
				hardwareInfoDict["ProcessorName"] = ((managementObject["Name"] != null) ? Convert.ToString(managementObject["Name"]) : unKnown);
				return string.Format("{0}", hardwareInfoDict["ProcessorName"]);
			}
		}
		return string.Empty;
	}

	public string getProcessorHostClockFreq()
	{
		using (ManagementObjectCollection.ManagementObjectEnumerator managementObjectEnumerator = new ManagementObjectSearcher("select * from Win32_Processor").Get().GetEnumerator())
		{
			if (managementObjectEnumerator.MoveNext())
			{
				ManagementObject managementObject = (ManagementObject)managementObjectEnumerator.Current;
				hardwareInfoDict["CurrentClockSpeed"] = ((managementObject["CurrentClockSpeed"] != null) ? Convert.ToString(managementObject["CurrentClockSpeed"]) : unKnown);
				return string.Format("{0} MHz", hardwareInfoDict["CurrentClockSpeed"]);
			}
		}
		return string.Empty;
	}

	public string getProcessorMaxTurboFreq()
	{
		PerformanceCounter performanceCounter = new PerformanceCounter("Processor Information", "% Processor Performance", "_Total");
		double num = performanceCounter.NextValue();
		Thread thread = new Thread((ThreadStart)delegate
		{
			InfiniteLoop();
		});
		thread.Start();
		Thread.Sleep(1000);
		num = performanceCounter.NextValue();
		thread.Abort();
		using (ManagementObjectCollection.ManagementObjectEnumerator managementObjectEnumerator = new ManagementObjectSearcher("SELECT *, Name FROM Win32_Processor").Get().GetEnumerator())
		{
			if (managementObjectEnumerator.MoveNext())
			{
				double num2 = Convert.ToDouble(((ManagementObject)managementObjectEnumerator.Current)["MaxClockSpeed"]) / 1000.0 * num / 100.0;
				return $"{num2:0.00} Ghz";
			}
		}
		return string.Empty;
	}

	private void InfiniteLoop()
	{
		int num = 0;
		while (true)
		{
			num = num + 1 - 1;
		}
	}

	public string getL2CacheSize()
	{
		_ = (uint)new ManagementObject("Win32_Processor.DeviceID='CPU0'")["L2CacheSize"];
		return (1638u / 1024u).ToString("F1") + " MB";
	}

	public string getGraphicInfo()
	{
		string text = "";
		int num = 0;
		foreach (ManagementObject item in new ManagementObjectSearcher("select * from Win32_VideoController").Get())
		{
			Convert.ToString(item["Caption"]);
			hardwareInfoDict["GraphicName" + Convert.ToString(num)] = ((item["Caption"] != null) ? Convert.ToString(item["Caption"]) : unKnown);
			text = ((num != 0) ? (text + ", " + hardwareInfoDict["GraphicName" + Convert.ToString(num)]) : hardwareInfoDict["GraphicName" + Convert.ToString(num)]);
			num++;
		}
		Console.WriteLine(text);
		return text;
	}

	public string getDgpuType()
	{
		string text = string.Empty;
		foreach (ManagementObject item in new ManagementObjectSearcher("SELECT Name FROM Win32_VideoController").Get())
		{
			foreach (PropertyData property in item.Properties)
			{
				if (text == string.Empty && property.Value.ToString().ToLower().IndexOf("intel") == -1)
				{
					text = property.Value.ToString();
					break;
				}
			}
		}
		return text;
	}

	public string getIgpuType()
	{
		string text = string.Empty;
		foreach (ManagementObject item in new ManagementObjectSearcher("SELECT Name FROM Win32_VideoController").Get())
		{
			foreach (PropertyData property in item.Properties)
			{
				if (text == string.Empty && property.Value.ToString().ToLower().IndexOf("intel") == 0)
				{
					text = property.Value.ToString();
					break;
				}
			}
		}
		return text;
	}

	public string getMemoryInfo()
	{
		string result = "null";
		try
		{
			ManagementScope managementScope = new ManagementScope(string.Format("\\\\{0}\\root\\CIMV2", "."), null);
			managementScope.Connect();
			ObjectQuery query = new ObjectQuery("SELECT Capacity FROM Win32_PhysicalMemory");
			ManagementObjectSearcher managementObjectSearcher = new ManagementObjectSearcher(managementScope, query);
			ulong num = 0uL;
			foreach (ManagementObject item in managementObjectSearcher.Get())
			{
				num += (ulong)item["Capacity"];
			}
			result = (num / 1073741824).ToString();
		}
		catch (Exception ex)
		{
			Console.WriteLine($"Exception {ex.Message} Trace {ex.StackTrace}");
		}
		return result;
	}

	[DllImport("kernel32.dll", CharSet = CharSet.Auto, SetLastError = true)]
	[return: MarshalAs(UnmanagedType.Bool)]
	private static extern bool GlobalMemoryStatusEx([In][Out] MEMORYSTATUSEX lpBuffer);

	public string getMemoryUsableInfo()
	{
		MEMORYSTATUSEX mEMORYSTATUSEX = new MEMORYSTATUSEX();
		GlobalMemoryStatusEx(mEMORYSTATUSEX);
		double num = Math.Round((float)mEMORYSTATUSEX.ullTotalPhys * 1f / 1024f / 1024f / 1024f, 2);
		Console.WriteLine("{0}", num);
		return num.ToString();
	}

	public string getBIOSInfo()
	{
		string result = "null";
		foreach (ManagementObject item in new ManagementObjectSearcher("SELECT * FROM Win32_BIOS").Get())
		{
			result = ((((string[])item["BIOSVersion"]).Length <= 1) ? ((string[])item["BIOSVersion"])[0] : (((string[])item["BIOSVersion"])[0] + " - " + ((string[])item["BIOSVersion"])[1]));
		}
		return result;
	}

	public string getECInfo()
	{
		string result = "null";
		foreach (ManagementObject item in new ManagementObjectSearcher("\\\\.\\ROOT\\WMI", "SELECT * FROM MS_SystemInformation").Get())
		{
			result = item["ECFirmwareMajorRelease"].ToString() + "." + item["ECFirmwareMinorRelease"].ToString();
		}
		return result;
	}
}
