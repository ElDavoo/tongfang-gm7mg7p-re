using System;
using System.Diagnostics;
using System.Threading;
using System.Threading.Tasks;
using Define;
using MyControlCenter;
using MyECIO;
using Utility;

namespace GCUService.MyFan.Overclocking;

internal class GpuFeatures
{
	private MyEcCtrl EcCtrl = MyEcCtrl.Instance;

	private GPUInfo cGpuInfo = new GPUInfo();

	private GpuThermalLimitInfo GpuThermalLimitInfo = new GpuThermalLimitInfo();

	private const int GpuCoreClockOffsetMaximum = 200;

	private const int GpuCoreClockOffsetMinimum = 0;

	private const int GpuMemoryClockOffsetMaximum = 1000;

	private const int GpuMemoryClockOffsetMinimum = -1000;

	private bool m_GpuWhisperModeSupport;

	private object _PStateHandler = new object();

	private bool _PStateWorker = true;

	private Stopwatch sw = new Stopwatch();

	private Stopwatch pressSw = new Stopwatch();

	private int _SateDelay = 5000;

	private bool PressLock = true;

	private uint PressG;

	private uint LastG;

	private SemaphoreSlim FansemporeSlim = new SemaphoreSlim(1, 1);

	private Stopwatch stopwatch = new Stopwatch();

	private uint LastCommand;

	public GpuFeatures()
	{
		cGpuInfo.GetGpuHandle();
		LoadGpuThermalLimitInfo(ref GpuThermalLimitInfo.DefaultTemperature, ref GpuThermalLimitInfo.MaximumTemperature, ref GpuThermalLimitInfo.MinimumTemperature);
		m_GpuWhisperModeSupport = cGpuInfo.IsGpuWhisperMode2p0Support();
	}

	private bool SetNVPState(uint G)
	{
		PressG = G;
		if (PressLock)
		{
			PressLock = false;
			pressSw.Restart();
			if (LastG != G)
			{
				SetPStateFunction(G);
			}
			Task.Run(delegate
			{
				Thread.Sleep(_SateDelay);
			}).ContinueWith(delegate
			{
				pressSw.Stop();
				PressLock = true;
				if (LastG != PressG)
				{
					SetNVPState(PressG);
				}
			});
		}
		return true;
	}

	private async void SetNVPStateThread(uint G)
	{
		if (FansemporeSlim.CurrentCount == 0)
		{
			LastCommand = G;
			return;
		}
		await FansemporeSlim.WaitAsync();
		try
		{
			stopwatch.Reset();
			stopwatch.Start();
			new Thread((ThreadStart)delegate
			{
				SetNVPState(G);
			}).Start();
			stopwatch.Stop();
			_ = stopwatch.ElapsedMilliseconds;
		}
		catch
		{
		}
		finally
		{
			FansemporeSlim.Release();
			if (LastCommand != 0)
			{
				new Thread((ThreadStart)delegate
				{
					SetNVPState(G);
				}).Start();
				LastCommand = 0u;
			}
		}
	}

	private void SetPStateFunction(uint G)
	{
		uint num = 0u;
		uint count = 0u;
		uint GPUPstate = 0u;
		LastG = G;
		switch (G)
		{
		case 1u:
		case 4u:
			GPUPstate = 0u;
			break;
		case 2u:
			GPUPstate = 3u;
			break;
		case 3u:
			GPUPstate = 5u;
			break;
		}
		try
		{
			GPUTypeClass.GetNVGpuCount(ref count);
			for (num = 0u; num < count; num++)
			{
				if (!Monitor.TryEnter(_PStateHandler, 100))
				{
					continue;
				}
				try
				{
					if (_PStateWorker)
					{
						sw.Restart();
						if (GPUTypeClass.SetNVPState(num, ref GPUPstate))
						{
							LogCtrl.TraceMessage("Set GPU " + num + ", P state: " + GPUPstate, "SetPStateFunction", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\Overclocking\\GpuFeatures.cs", 199);
						}
						else
						{
							LogCtrl.TraceMessage("Set GPU " + num + ", P state: " + GPUPstate + " fail", "SetPStateFunction", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\Overclocking\\GpuFeatures.cs", 203);
						}
						sw.Stop();
					}
				}
				finally
				{
					if (sw.ElapsedMilliseconds > 10000)
					{
						_PStateWorker = false;
					}
					Monitor.Exit(_PStateHandler);
				}
			}
		}
		catch (Exception ex)
		{
			LogCtrl.TraceMessage("Set GPU " + num + ", P state: " + GPUPstate + ", exception: " + ex.Message, "SetPStateFunction", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\Overclocking\\GpuFeatures.cs", 228);
		}
	}

	public void SetGpuCoreFreqOffsetValue(int value)
	{
		try
		{
			if (value >= 0 && value <= 200)
			{
				LogCtrl.TraceMessage("Value: " + value, "SetGpuCoreFreqOffsetValue", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\Overclocking\\GpuFeatures.cs", 242);
				cGpuInfo.SetGpuCoreFreqOffsetValue(value);
			}
			else
			{
				LogCtrl.TraceMessage("Set the value failed, and error is out of range.", "SetGpuCoreFreqOffsetValue", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\Overclocking\\GpuFeatures.cs", 247);
			}
		}
		catch (Exception)
		{
			LogCtrl.TraceMessage("GpuInfo  SetGpuCoreFreqOffset failed, and error is out of range.", "SetGpuCoreFreqOffsetValue", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\Overclocking\\GpuFeatures.cs", 252);
		}
	}

	public void SetGpuMemFreqOffsetValue(int value)
	{
		try
		{
			if (value >= -1000 && value <= 1000)
			{
				LogCtrl.TraceMessage("Value: " + value, "SetGpuMemFreqOffsetValue", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\Overclocking\\GpuFeatures.cs", 267);
				cGpuInfo.SetGpuMemFreqOffsetValue(value);
			}
			else
			{
				LogCtrl.TraceMessage("Set the value failed, and error is out of range.", "SetGpuMemFreqOffsetValue", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\Overclocking\\GpuFeatures.cs", 272);
			}
		}
		catch (Exception)
		{
			LogCtrl.TraceMessage("GpuInfo  SetGpuMemFreqOffset failed, and error is out of range.", "SetGpuMemFreqOffsetValue", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\Overclocking\\GpuFeatures.cs", 277);
		}
	}

	public GpuThermalLimitInfo GetGpuThermalLimitInfo()
	{
		return GpuThermalLimitInfo;
	}

	public void SetGpuTargetTemperature(int value)
	{
		if (value >= GpuThermalLimitInfo.MinimumTemperature && value <= GpuThermalLimitInfo.MaximumTemperature)
		{
			cGpuInfo.SetGpuTargetTemperatureValue(value);
		}
		else
		{
			LogCtrl.TraceMessage("Set the value failed, and error is out of range.", "SetGpuTargetTemperature", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\Overclocking\\GpuFeatures.cs", 322);
		}
	}

	private void LoadGpuThermalLimitInfo(ref int DefaultTemperature, ref int MaximumTemperature, ref int MinimumTemperature)
	{
		try
		{
			uint LimitDefault = 0u;
			uint LimitMax = 0u;
			uint LimitMin = 0u;
			uint CurrentValue = 0u;
			cGpuInfo.GetGpuThermalLimitInfo(ref LimitDefault, ref LimitMax, ref LimitMin, ref CurrentValue);
			DefaultTemperature = Convert.ToInt32(LimitDefault);
			MaximumTemperature = Convert.ToInt32(LimitMax);
			MinimumTemperature = Convert.ToInt32(LimitMin);
		}
		catch (Exception ex)
		{
			LogCtrl.TraceMessage("Exception:" + ex.ToString(), "LoadGpuThermalLimitInfo", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyFan\\Overclocking\\GpuFeatures.cs", 362);
		}
	}

	public void SetGpuConfigurableTgpFunCtrlEnable(int status)
	{
		byte Data = 0;
		byte b = 251;
		byte b2 = 0;
		byte b3 = 0;
		b2 = (byte)((status == 1) ? 4 : 0);
		EcCtrl.Read(GetType().Name, 1859, ref Data);
		b3 = (byte)((Data & b) + b2);
		EcCtrl.Write(GetType().Name, 1859, b3);
	}

	public void SetGpuConfigurableTGPTarget(int value, int _SmartApcTableDefaultTGP)
	{
		int num = 0;
		if (value >= _SmartApcTableDefaultTGP)
		{
			num = value - _SmartApcTableDefaultTGP;
			if (num >= 0)
			{
				EcCtrl.Write(GetType().Name, 1860, Convert.ToByte(num));
			}
		}
	}

	public void SetGpuDynamicBoostFunCtrlEnable(int status)
	{
		byte Data = 0;
		byte b = 254;
		byte b2 = 0;
		byte b3 = 0;
		b2 = ((status == 1) ? ((byte)1) : ((byte)0));
		EcCtrl.Read(GetType().Name, 1859, ref Data);
		b3 = (byte)((Data & b) + b2);
		EcCtrl.Write(GetType().Name, 1859, b3);
	}

	public void SetGpuDynamicBoostEnable(int status)
	{
		byte Data = 0;
		byte b = 253;
		byte b2 = 0;
		byte b3 = 0;
		b2 = (byte)((status == 1) ? 2 : 0);
		EcCtrl.Read(GetType().Name, 1859, ref Data);
		b3 = (byte)((Data & b) + b2);
		EcCtrl.Write(GetType().Name, 1859, b3);
	}

	public void SetGpuDynamicBoostTotalProcessingPowerTarget(int value)
	{
		EcCtrl.Write(GetType().Name, 1861, Convert.ToByte(value));
	}

	public void SetGpuDynamicBoostMaxinumTGP(int value)
	{
		EcCtrl.Write(GetType().Name, 1862, Convert.ToByte(value));
	}

	public bool IsGpuWhisperMode2p0Support()
	{
		return m_GpuWhisperModeSupport;
	}

	public bool SetGpuWhisperModeStatus(bool status)
	{
		return cGpuInfo.SetGpuWhisperModeStatus(status);
	}

	public bool SetGpuWhisperModeSettingValue(int value)
	{
		return cGpuInfo.SetGpuWhisperModeSettingValue(value);
	}

	public bool SetGpuWhisperModeMinFpsValue(int value)
	{
		return cGpuInfo.SetGpuWhisperModeMinFpsValue(value);
	}

	public void SetGpuWhisperModeMainSwitch(int status)
	{
		byte Data = 0;
		byte b = 159;
		byte b2 = 0;
		byte b3 = 0;
		if (status == 1)
		{
			b2 = 96;
		}
		else
		{
			SetWhisperModeStatusDisable();
			b2 = 64;
		}
		EcCtrl.Read(GetType().Name, 1989, ref Data);
		b3 = (byte)((Data & b) + b2);
		EcCtrl.Write(GetType().Name, 1989, b3);
	}

	public void SetWhisperModeStatusDisable()
	{
		byte Data = 0;
		byte b = 252;
		byte b2 = 0;
		byte b3 = 0;
		b2 = 0;
		EcCtrl.Read(GetType().Name, 1990, ref Data);
		b3 = (byte)((Data & b) + b2);
		EcCtrl.Write(GetType().Name, 1990, b3);
	}

	public int GetWisperModeStatus()
	{
		byte Data = 0;
		byte b = 3;
		byte b2 = 0;
		int result = -1;
		EcCtrl.Read(GetType().Name, 1990, ref Data);
		switch ((byte)(Data & b))
		{
		case 0:
			result = -1;
			break;
		case 1:
			result = 2;
			break;
		case 2:
			result = 1;
			break;
		case 3:
			result = 0;
			break;
		}
		return result;
	}
}
