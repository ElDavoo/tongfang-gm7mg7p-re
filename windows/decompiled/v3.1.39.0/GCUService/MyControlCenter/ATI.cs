using System;
using System.Runtime.InteropServices;

namespace MyControlCenter;

internal class ATI : GPUTypeClass
{
	public delegate int ADL2_OverdriveN_Temperature_GetDelegate(int adapterIndex, int thermalControllerIndex, ref int temperature);

	public static ADL2_OverdriveN_Temperature_GetDelegate ADL2_OverdriveN_Temperature_Get;

	private static string dllname = "atiadlxx.dll";

	private static void GetDelegate<T>(string entryPoint, out T newDelegate) where T : class
	{
		PInvokeDelegateFactory.CreateDelegate<T>(new DllImportAttribute(dllname)
		{
			CallingConvention = CallingConvention.Cdecl,
			PreserveSig = true,
			EntryPoint = entryPoint
		}, out newDelegate);
	}

	public ATI()
	{
		GetDelegate<ADL2_OverdriveN_Temperature_GetDelegate>("ADL2_OverdriveN_Temperature_Get", out ADL2_OverdriveN_Temperature_Get);
	}

	internal override void SetGPUTempature()
	{
		int temperature = 0;
		ADL2_OverdriveN_Temperature_Get(0, 0, ref temperature);
		base.GpuTempature = Convert.ToUInt32(temperature);
	}

	internal override void SetGpuUsage()
	{
		base.GpuUsage = 30u;
	}

	internal override void SetGpuCoreFreq()
	{
		base.GpuCoreFreq = 300u;
	}

	internal override void SetGpuMemFreq()
	{
		base.GpuMemFreq = 400u;
	}

	internal override void SetGpuPState()
	{
		base.GpuPState = 8u;
	}

	internal override void SetGpuPhysicalRamSize()
	{
		base.GpuPhysicalRamSize = 1024uL;
	}

	internal override bool SetGpuCoreFreqOffset(int value)
	{
		return false;
	}

	internal override bool SetGpuMemFreqOffset(int value)
	{
		return false;
	}

	internal override bool SetGpuTargetTemperature(int value)
	{
		return false;
	}

	internal override bool GetGpuWhisperMode2p0Support()
	{
		return false;
	}

	internal override bool SetGpuWhisperMode(bool status)
	{
		return false;
	}

	internal override bool SetGpuWhisperModeSetting(int value)
	{
		return false;
	}

	internal override bool SetGpuWhisperModeMinFps(int value)
	{
		return false;
	}

	internal override void GetNvGpuHandle()
	{
	}
}
