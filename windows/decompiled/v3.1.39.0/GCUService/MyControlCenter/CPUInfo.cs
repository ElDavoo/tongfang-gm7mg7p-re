using System;
using System.Diagnostics;
using Utility;

namespace MyControlCenter;

internal class CPUInfo
{
	private PerformanceCounter perfUptimeCount;

	private PerformanceCounter perfTempZoneSB;

	private static PerformanceCounter cpuCounter;

	private PerformanceCounter Disk;

	private static PerformanceCounterCategory Network;

	private string[] instanceName;

	private const string _categoryName = "Thermal Zone Information";

	private const string _processIdCounter = "Temperature";

	public CPUInfo()
	{
		try
		{
			cpuCounter = new PerformanceCounter("Processor Information", "% Processor Utility", "_Total");
			perfTempZoneSB = new PerformanceCounter("Thermal Zone Information", "Temperature", GetTInstance().ToString());
		}
		catch (Exception ex)
		{
			LogCtrl.Write("System monitor" + ex.ToString());
		}
	}

	public static string GetTInstance()
	{
		string result = "";
		if (new PerformanceCounterCategory("Thermal Zone Information").CategoryType == PerformanceCounterCategoryType.SingleInstance)
		{
			PerformanceCounter[] counters = new PerformanceCounterCategory("Temperature").GetCounters();
			int num = 0;
			if (num < counters.Length)
			{
				return counters[num].InstanceName;
			}
		}
		else
		{
			PerformanceCounterCategory performanceCounterCategory = new PerformanceCounterCategory("Thermal Zone Information");
			string[] instanceNames = performanceCounterCategory.GetInstanceNames();
			foreach (string text in instanceNames)
			{
				PerformanceCounter[] counters = performanceCounterCategory.GetCounters(text);
				int num2 = 0;
				if (num2 < counters.Length)
				{
					return counters[num2].InstanceName;
				}
			}
		}
		return result;
	}

	public int GetCPUTemperature()
	{
		double num = 0.0;
		LogCtrl.Write("Cpu tempature : " + num);
		if (perfTempZoneSB != null)
		{
			perfTempZoneSB.NextValue();
			LogCtrl.Write("Cpu tempature mid : " + num);
			num = perfTempZoneSB.NextValue();
			num -= 273.2;
		}
		LogCtrl.Write("Cpu tempature next : " + num);
		return (int)num;
	}

	public int GetCPUUsage()
	{
		float num = 0f;
		LogCtrl.Write("Cpu loading : " + num);
		if (cpuCounter != null)
		{
			num = cpuCounter.NextValue();
		}
		if (num > 100f)
		{
			num = 100f;
		}
		LogCtrl.Write("Cpu loading next : " + num);
		return (int)Math.Round(num);
	}

	public int GetDiskUsage()
	{
		return Convert.ToInt32(Disk.NextValue());
	}
}
