using System;
using System.Runtime.InteropServices;
using Utility;

namespace MyControlCenter;

internal class GPUTypeClass
{
	public delegate void GPUInfoCBK(IntPtr files, int count);

	public static string[] GpuInfo2 = new string[10] { "0", "0", "0", "0", "0", "0", "0", "0", "0", "0" };

	public uint GpuTempature { get; internal set; }

	public uint GpuUsage { get; internal set; }

	public uint GpuCoreFreq { get; internal set; }

	public uint GpuMemFreq { get; internal set; }

	public uint GpuPState { get; internal set; }

	public ulong GpuPhysicalRamSize { get; internal set; }

	[DllImport("GPUInfoDLL.dll", CallingConvention = CallingConvention.StdCall)]
	public static extern bool GetNVGpuCount(ref uint count);

	[DllImport("GPUInfoDLL.dll", CallingConvention = CallingConvention.StdCall)]
	public static extern bool GetNVTemperature(uint index, ref uint temperature);

	[DllImport("GPUInfoDLL.dll", CallingConvention = CallingConvention.StdCall)]
	public static extern bool GetNVGpuUsage(uint index, ref uint percentage);

	[DllImport("GPUInfoDLL.dll", CallingConvention = CallingConvention.StdCall)]
	public static extern bool GetNVCoreFreq(uint index, ref uint clock);

	[DllImport("GPUInfoDLL.dll", CallingConvention = CallingConvention.StdCall)]
	public static extern bool GetNVMemFreq(uint index, ref uint clock);

	[DllImport("GPUInfoDLL.dll", CallingConvention = CallingConvention.StdCall)]
	public static extern bool GetNVPState(uint index, ref uint pstatue);

	[DllImport("GPUInfoDLL.dll", CallingConvention = CallingConvention.StdCall)]
	public static extern bool GetNVPhysicalRam(uint index, ref ulong RamSize, ref uint RamType);

	[DllImport("GPUInfoDLL.dll", CallingConvention = CallingConvention.StdCall)]
	public static extern bool GetNVGpuInfo2(GPUInfoCBK callback);

	[DllImport("GPUInfoDLL.dll", CallingConvention = CallingConvention.StdCall)]
	public static extern bool GetNvGpuThermalLimitInfo(uint index, ref uint LimitDefault, ref uint LimitMax, ref uint LimitMin, ref uint CurrentValue);

	[DllImport("GPUInfoDLL.dll", CallingConvention = CallingConvention.StdCall)]
	public static extern bool SetNVPState(uint index, ref uint GPUPstate);

	[DllImport("GPUInfoDLL.dll", CallingConvention = CallingConvention.StdCall)]
	public static extern bool SetNVCoreFreqOffset(uint index, ref int CoreclockOffset);

	[DllImport("GPUInfoDLL.dll", CallingConvention = CallingConvention.StdCall)]
	public static extern bool SetNVMemFreqOffset(uint index, ref int MemclockOffset);

	[DllImport("GPUInfoDLL.dll", CallingConvention = CallingConvention.StdCall)]
	public static extern bool SetNVGpuThermalPoliciesStatus(uint index, ref int thermalLimit);

	[DllImport("GPUInfoDLL.dll", CallingConvention = CallingConvention.StdCall)]
	public static extern bool GetNVGpuWhisperMode2p0Support();

	[DllImport("GPUInfoDLL.dll", CallingConvention = CallingConvention.StdCall)]
	public static extern bool SetNVGpuWhisperModeStatus(bool bEnable);

	[DllImport("GPUInfoDLL.dll", CallingConvention = CallingConvention.StdCall)]
	public static extern bool SetNVGpuWhisperModeSetting(ref int Setting);

	[DllImport("GPUInfoDLL.dll", CallingConvention = CallingConvention.StdCall)]
	public static extern bool SetNVGpuWhisperModeMinFps(ref int MinFps);

	[DllImport("GPUInfoDLL.dll", CallingConvention = CallingConvention.StdCall)]
	public static extern void GetNVHandle();

	internal virtual void SetGPUTempature()
	{
		uint count = 0u;
		uint temperature = 0u;
		GetNVGpuCount(ref count);
		for (uint num = 0u; num < count; num++)
		{
			GetNVTemperature(num, ref temperature);
		}
		GpuTempature = temperature;
	}

	internal virtual void SetGpuUsage()
	{
		uint count = 0u;
		uint percentage = 0u;
		GetNVGpuCount(ref count);
		for (uint num = 0u; num < count; num++)
		{
			GetNVGpuUsage(num, ref percentage);
		}
		GpuUsage = percentage;
	}

	internal virtual void SetGpuCoreFreq()
	{
		uint count = 0u;
		uint clock = 0u;
		GetNVGpuCount(ref count);
		for (uint num = 0u; num < count; num++)
		{
			GetNVCoreFreq(num, ref clock);
		}
		GpuCoreFreq = clock;
	}

	internal virtual void SetGpuMemFreq()
	{
		uint count = 0u;
		uint clock = 0u;
		GetNVGpuCount(ref count);
		for (uint num = 0u; num < count; num++)
		{
			GetNVMemFreq(num, ref clock);
		}
		GpuMemFreq = clock;
	}

	internal virtual void SetGpuPState()
	{
		uint count = 0u;
		uint pstatue = 0u;
		GetNVGpuCount(ref count);
		for (uint num = 0u; num < count; num++)
		{
			GetNVPState(num, ref pstatue);
		}
		GpuPState = pstatue;
	}

	internal virtual void GetGpuThermalLimitInfoValue(ref uint LimitDefault, ref uint LimitMax, ref uint LimitMin, ref uint CurrentValue)
	{
		uint count = 0u;
		GetNVGpuCount(ref count);
		for (uint num = 0u; num < count; num++)
		{
			GetNvGpuThermalLimitInfo(num, ref LimitDefault, ref LimitMax, ref LimitMin, ref CurrentValue);
		}
	}

	internal virtual void SetGpuPhysicalRamSize()
	{
		uint count = 0u;
		ulong RamSize = 0uL;
		uint RamType = 0u;
		GetNVGpuCount(ref count);
		for (uint num = 0u; num < count; num++)
		{
			GetNVPhysicalRam(num, ref RamSize, ref RamType);
		}
		GpuPhysicalRamSize = RamSize;
	}

	internal virtual bool SetGpuCoreFreqOffset(int value)
	{
		uint count = 0u;
		try
		{
			GetNVGpuCount(ref count);
			for (uint num = 0u; num < count; num++)
			{
				if (!SetNVCoreFreqOffset(num, ref value))
				{
					return false;
				}
			}
		}
		catch (Exception ex)
		{
			Console.WriteLine("SetGpuCoreFreqOffset exception, " + ex.Message);
			return false;
		}
		return true;
	}

	internal virtual bool SetGpuMemFreqOffset(int value)
	{
		uint count = 0u;
		try
		{
			GetNVGpuCount(ref count);
			for (uint num = 0u; num < count; num++)
			{
				if (!SetNVMemFreqOffset(num, ref value))
				{
					return false;
				}
			}
		}
		catch (Exception ex)
		{
			Console.WriteLine("SetGpuMemFreqOffset exception, " + ex.Message);
			return false;
		}
		return true;
	}

	internal virtual bool SetGpuTargetTemperature(int value)
	{
		uint count = 0u;
		try
		{
			GetNVGpuCount(ref count);
			for (uint num = 0u; num < count; num++)
			{
				if (!SetNVGpuThermalPoliciesStatus(num, ref value))
				{
					return false;
				}
			}
		}
		catch (Exception ex)
		{
			Console.WriteLine("SetGpuTargetTemperature exception, " + ex.Message);
			return false;
		}
		return true;
	}

	internal virtual bool GetGpuWhisperMode2p0Support()
	{
		try
		{
			if (!GetNVGpuWhisperMode2p0Support())
			{
				return false;
			}
		}
		catch (Exception ex)
		{
			Console.WriteLine("GetGpuWhisperMode2p0Support exception, " + ex.Message);
			return false;
		}
		return true;
	}

	internal virtual bool SetGpuWhisperMode(bool status)
	{
		try
		{
			if (!SetNVGpuWhisperModeStatus(status))
			{
				Console.WriteLine("fail");
				return false;
			}
		}
		catch (Exception ex)
		{
			Console.WriteLine("exception, " + ex.Message);
			return false;
		}
		return true;
	}

	internal virtual bool SetGpuWhisperModeSetting(int value)
	{
		try
		{
			if (!SetNVGpuWhisperModeSetting(ref value))
			{
				Console.WriteLine("fail");
				return false;
			}
			LogCtrl.TraceMessage("SetGpuWhisperModeSetting, value:" + value, "SetGpuWhisperModeSetting", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MySystem\\GPUInfo\\GPUTypeClass.cs", 321);
		}
		catch (Exception ex)
		{
			Console.WriteLine("exception, " + ex.Message);
			return false;
		}
		return true;
	}

	internal virtual bool SetGpuWhisperModeMinFps(int value)
	{
		try
		{
			if (!SetNVGpuWhisperModeMinFps(ref value))
			{
				Console.WriteLine("fail");
				LogCtrl.TraceMessage("fail", "SetGpuWhisperModeMinFps", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MySystem\\GPUInfo\\GPUTypeClass.cs", 350);
				return false;
			}
			LogCtrl.TraceMessage("SetGpuWhisperModeMinFps, value:" + value, "SetGpuWhisperModeMinFps", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MySystem\\GPUInfo\\GPUTypeClass.cs", 345);
		}
		catch (Exception ex)
		{
			Console.WriteLine("exception, " + ex.Message);
			LogCtrl.TraceMessage("exception, " + ex.Message, "SetGpuWhisperModeMinFps", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MySystem\\GPUInfo\\GPUTypeClass.cs", 357);
			return false;
		}
		return true;
	}

	internal virtual void GetNvGpuHandle()
	{
		try
		{
			GetNVHandle();
		}
		catch (Exception ex)
		{
			Console.WriteLine("exception, " + ex.Message);
		}
	}

	public uint GetGpuTemperature()
	{
		SetGPUTempature();
		return GpuTempature;
	}

	public uint GetGpuUsage()
	{
		SetGpuUsage();
		return GpuUsage;
	}

	public uint GetGpuCoreFreq()
	{
		SetGpuCoreFreq();
		return GpuCoreFreq;
	}

	public uint GetGpuMemFreq()
	{
		SetGpuMemFreq();
		return GpuMemFreq;
	}

	public uint GetGpuPState()
	{
		SetGpuPState();
		return GpuPState;
	}

	public ulong GetGpuPhysicalRamSize()
	{
		SetGpuPhysicalRamSize();
		return GpuPhysicalRamSize;
	}

	public void GetGpuThermalLimitInfo(ref uint LimitDefault, ref uint LimitMax, ref uint LimitMin, ref uint CurrentValue)
	{
		GetGpuThermalLimitInfoValue(ref LimitDefault, ref LimitMax, ref LimitMin, ref CurrentValue);
	}

	public bool SetGpuCoreFreqOffsetValue(int value)
	{
		return SetGpuCoreFreqOffset(value);
	}

	public bool SetGpuMemFreqOffsetValue(int value)
	{
		return SetGpuMemFreqOffset(value);
	}

	public bool SetGpuTargetTemperatureValue(int value)
	{
		return SetGpuTargetTemperature(value);
	}

	public bool IsGpuWhisperMode2p0Support()
	{
		return GetGpuWhisperMode2p0Support();
	}

	public bool SetGpuWhisperModeStatus(bool status)
	{
		return SetGpuWhisperMode(status);
	}

	public bool SetGpuWhisperModeSettingValue(int value)
	{
		return SetGpuWhisperModeSetting(value);
	}

	public bool SetGpuWhisperModeMinFpsValue(int value)
	{
		return SetGpuWhisperModeMinFps(value);
	}

	public void GetGpuHandle()
	{
		GetNvGpuHandle();
	}
}
