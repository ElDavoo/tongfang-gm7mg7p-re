namespace MyControlCenter;

internal class GPUInfo
{
	private GPUTypeClass GPUType = new GPUTypeClass();

	public GPUInfo()
	{
		string graphicInfo = new HardwareInfoCollect().getGraphicInfo();
		if (graphicInfo.Contains("NVIDIA"))
		{
			GPUType = new NVIDIA();
		}
		else if (graphicInfo.Contains("ATI"))
		{
			GPUType = new ATI();
		}
		else
		{
			GPUType = new GPUTypeClass();
		}
	}

	public uint GetGpuTemperature()
	{
		return GPUType.GetGpuTemperature();
	}

	public uint GetGpuUsage()
	{
		return GPUType.GetGpuUsage();
	}

	public uint GetGpuCoreFreq()
	{
		return GPUType.GetGpuCoreFreq();
	}

	public uint GetGpuMemFreq()
	{
		return GPUType.GetGpuMemFreq();
	}

	public uint GetGpuPState()
	{
		return GPUType.GetGpuPState();
	}

	public ulong GetGpuPhysicalRamSize()
	{
		return GPUType.GetGpuPhysicalRamSize();
	}

	public void GetGpuThermalLimitInfo(ref uint LimitDefault, ref uint LimitMax, ref uint LimitMin, ref uint CurrentValue)
	{
		GPUType.GetGpuThermalLimitInfo(ref LimitDefault, ref LimitMax, ref LimitMin, ref CurrentValue);
	}

	public bool SetGpuCoreFreqOffsetValue(int value)
	{
		return GPUType.SetGpuCoreFreqOffsetValue(value);
	}

	public bool SetGpuMemFreqOffsetValue(int value)
	{
		return GPUType.SetGpuMemFreqOffsetValue(value);
	}

	public bool SetGpuTargetTemperatureValue(int value)
	{
		return GPUType.SetGpuTargetTemperatureValue(value);
	}

	public bool IsGpuWhisperMode2p0Support()
	{
		return GPUType.IsGpuWhisperMode2p0Support();
	}

	public bool SetGpuWhisperModeStatus(bool status)
	{
		return GPUType.SetGpuWhisperModeStatus(status);
	}

	public bool SetGpuWhisperModeSettingValue(int value)
	{
		return GPUType.SetGpuWhisperModeSettingValue(value);
	}

	public bool SetGpuWhisperModeMinFpsValue(int value)
	{
		return GPUType.SetGpuWhisperModeMinFpsValue(value);
	}

	public void GetGpuHandle()
	{
		GPUType.GetGpuHandle();
	}
}
