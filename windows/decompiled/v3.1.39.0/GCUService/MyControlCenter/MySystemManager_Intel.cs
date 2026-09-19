using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Timers;
using Utility;

namespace MyControlCenter;

public class MySystemManager_Intel : MySystemManager
{
	private MySystemView m_View = new MySystemView();

	private string beforeCpuValue = "0";

	private string beforeMemoryValue = "0";

	private string beforeBatteryValue = "0";

	private bool SqliteDbSwitch;

	private Timer cpuinfoTimer;

	private Timer diskinfoTimer;

	private Timer CpuTempDbTimer;

	private Timer FanInfoTimer;

	private Timer HwFuelGaugeTimer;

	private CPUInfo cCpuInfo = new CPUInfo();

	private GPUInfo cGpuInfo = new GPUInfo();

	private MemoryInfo cMemoryInfo = new MemoryInfo();

	private NetworkInfo cNetworkInfo = new NetworkInfo();

	private BatteryInfo cBatteryInfo = new BatteryInfo();

	private DiskInfo cDiskInfo = new DiskInfo();

	private FanFuctionErrorInfo _FanFunctionErrorInfo = new FanFuctionErrorInfo();

	private FanInfo _FanInfo = new FanInfo();

	private HwFuelGaugeInfo _HwFuelGaugeInfo = new HwFuelGaugeInfo();

	private HardwareInfoCollect _hardwareInfoCollect = new HardwareInfoCollect();

	public override void InitTimers()
	{
		cpuinfoTimer = new Timer();
		cpuinfoTimer.Interval = 2000.0;
		cpuinfoTimer.Elapsed += CpuinfoTimer_Elapsed;
		diskinfoTimer = new Timer();
		diskinfoTimer.Interval = 10000.0;
		diskinfoTimer.Elapsed += DiskinfoTimer_Elapsed;
		CpuTempDbTimer = new Timer();
		CpuTempDbTimer.Interval = 60000.0;
		CpuTempDbTimer.Elapsed += CpuTempDbTimer_Elapsed;
		FanInfoTimer = new Timer();
		FanInfoTimer.Interval = 2000.0;
		FanInfoTimer.Elapsed += FanInfoTimer_Elapsed;
		HwFuelGaugeTimer = new Timer();
		HwFuelGaugeTimer.Interval = 2000.0;
		HwFuelGaugeTimer.Elapsed += HwFuelGaugeTimer_Elapsed;
	}

	private void StartTimers()
	{
		cpuinfoTimer.Start();
		diskinfoTimer.Start();
		CpuTempDbTimer.Start();
		FanInfoTimer.Start();
		HwFuelGaugeTimer.Start();
	}

	private void StopTimers()
	{
		try
		{
			cpuinfoTimer.Stop();
			diskinfoTimer.Stop();
			CpuTempDbTimer.Stop();
			FanInfoTimer.Stop();
			HwFuelGaugeTimer.Stop();
		}
		catch
		{
		}
	}

	private void Enable()
	{
		InitFanFunctionErrorInfo();
		InitDiskBatteryInfo();
		InitSystemInfo();
		StartTimers();
	}

	public override void Disable()
	{
		StopTimers();
	}

	public override void Dispose()
	{
		StopTimers();
	}

	public override async void Receive(byte[] message)
	{
		dynamic val = await Json.ToObjectAsync<object>(Encoding.UTF8.GetString(message));
		string text = val["Action"];
		if (val["Action"] != null)
		{
			text = text.ToLowerInvariant();
			if (text.Contains("on"))
			{
				Enable();
			}
			else
			{
				Disable();
			}
		}
	}

	private void FanInfoTimer_Elapsed(object sender, ElapsedEventArgs e)
	{
		dynamic funInfo = GetFunInfo();
		m_View.SendStatusToClient("System/FanInfo", funInfo);
	}

	private void HwFuelGaugeTimer_Elapsed(object sender, ElapsedEventArgs e)
	{
		dynamic hwFuelGaugeInfo = GetHwFuelGaugeInfo();
		m_View.SendStatusToClient("System/HwFuelGauge", hwFuelGaugeInfo);
	}

	private void InitFanFunctionErrorInfo()
	{
		dynamic funError = GetFunError();
		m_View.SendStatusToClient("System/FanErrorInfo", funError);
	}

	private void InitSystemInfo()
	{
		try
		{
			dynamic val = new
			{
				ProcessorType = _hardwareInfoCollect.getProcessorType(),
				ProcessorL2CacheSize = _hardwareInfoCollect.getL2CacheSize(),
				DiscreteGpuType = _hardwareInfoCollect.getDgpuType(),
				IntegratedGpuType = _hardwareInfoCollect.getIgpuType(),
				MemoryTotalSize = _hardwareInfoCollect.getMemoryInfo() + " GB",
				MemoryUsableSize = _hardwareInfoCollect.getMemoryUsableInfo() + " GB",
				BIOSInfo = _hardwareInfoCollect.getBIOSInfo(),
				ECInfo = _hardwareInfoCollect.getECInfo(),
				ProductInfo = _hardwareInfoCollect.getComputerInfo()
			};
			m_View.SendStatusToClient("System/HardwareInfo", val);
		}
		catch (Exception ex)
		{
			LogCtrl.Write("Hardware info " + ex.ToString());
		}
	}

	private void InitDiskBatteryInfo()
	{
		dynamic val = InitBatteryInfo();
		m_View.SendStatusToClient("System/BatteryInfo", val);
		dynamic diskInfo = GetDiskInfo();
		m_View.SendStatusToClient("System/DiskInfo", diskInfo);
	}

	private void CpuinfoTimer_Elapsed(object sender, ElapsedEventArgs e)
	{
		dynamic cpuInfo = GetCpuInfo();
		m_View.SendStatusToClient("System/CpuInfo", cpuInfo);
		beforeCpuValue = cpuInfo.CpuUsage;
		dynamic memoryInfo = GetMemoryInfo();
		m_View.SendStatusToClient("System/MemoryInfo", memoryInfo);
		dynamic gpuInfo = GetGpuInfo();
		if ((int)Convert.ToInt32(gpuInfo.GpuTemperature) != 0)
		{
			m_View.SendStatusToClient("System/GpuInfo", gpuInfo);
		}
		if (GetNetworkStatus())
		{
			dynamic networkInfo = GetNetworkInfo();
			m_View.SendStatusToClient("System/NetworkInfo", networkInfo);
		}
		dynamic batteryInfo = GetBatteryInfo();
		m_View.SendStatusToClient("System/BatteryInfo", batteryInfo);
		beforeBatteryValue = batteryInfo.BatteryLifePercent;
	}

	private void DiskinfoTimer_Elapsed(object sender, ElapsedEventArgs e)
	{
		dynamic diskInfo = GetDiskInfo();
		m_View.SendStatusToClient("System/DiskInfo", diskInfo);
	}

	private void CpuTempDbTimer_Elapsed(object sender, ElapsedEventArgs e)
	{
		_ = SqliteDbSwitch;
	}

	private object GetFunError()
	{
		return new
		{
			FanErrorStatus = _FanFunctionErrorInfo.GetECFanAlert()
		};
	}

	private object GetFunInfo()
	{
		return new
		{
			CpuFanDuty = _FanInfo.GetEcCpuFanDuty(),
			GpuFanDuty = _FanInfo.GetEcGpuFanDuty()
		};
	}

	private object GetHwFuelGaugeInfo()
	{
		return new
		{
			DesignCapacity = _HwFuelGaugeInfo.GetDesignCapacity(),
			DesignVoltage = _HwFuelGaugeInfo.GetECDesignVoltage(),
			Voltage = _HwFuelGaugeInfo.GetVoltage(),
			Current = _HwFuelGaugeInfo.GetECCurrent()
		};
	}

	private object GetCpuInfo()
	{
		return new
		{
			CpuUsage = GetCpuUsage(),
			CpuTemperature = GetCpuTemperature(),
			ProcessorHostClockFreq = _hardwareInfoCollect.getProcessorHostClockFreq()
		};
	}

	private object GetMemoryInfo()
	{
		return new
		{
			MemoryUsage = (object)GetMemoryUsage()
		};
	}

	private string GetGpuUsageOnly()
	{
		return GetGpuUsage();
	}

	private object GetGpuInfo()
	{
		return new
		{
			GpuUsage = GetGpuUsage(),
			GpuTemperature = GetGpuTemperature(),
			GpuCoreFreq = GetGpuCoreFreq(),
			GpuMemFreq = GetGpuMemFreq(),
			GpuPState = GetGpuPState(),
			GpuMem = GetGpuPhysicalRamSize()
		};
	}

	private object GetIGpuInfo()
	{
		return new
		{
			GpuUsage = "0",
			GpuTemperature = "0",
			GpuCoreFreq = "0",
			GpuMemFreq = "0",
			GpuPState = "0",
			GpuMem = "0"
		};
	}

	private object GetBatteryInfo()
	{
		return new
		{
			BatteryLifePercent = GetBatteryLifePercent(),
			BatteryLifeRemaining = GetBatteryLifeRemaining(),
			BatteryAbnormal = GetBatteryAbnormal(),
			BatteryCapacity = cBatteryInfo.GetBatteryCapacity(),
			BatteryCycleCount = cBatteryInfo.GetECBatteryCycleCount()
		};
	}

	private object InitBatteryInfo()
	{
		return new
		{
			BatteryLifePercent = GetBatteryLifePercent(),
			BatteryLifeRemaining = GetBatteryLifeRemaining(),
			BatteryAbnormal = cBatteryInfo.Init(),
			BatteryCapacity = cBatteryInfo.GetBatteryCapacity(),
			BatteryCycleCount = cBatteryInfo.GetECBatteryCycleCount()
		};
	}

	private bool GetNetworkStatus()
	{
		return cNetworkInfo.CheckNetworkInfo();
	}

	private object GetNetworkInfo()
	{
		double size = 0.0;
		string unit = "Kbps";
		double size2 = 0.0;
		string unit2 = "Kbps";
		cNetworkInfo.CheckNetworkInfo();
		double downloadSpeed = cNetworkInfo.GetDownloadSpeed();
		double uploadSpeed = cNetworkInfo.GetUploadSpeed();
		cNetworkInfo.FormatSpeed(downloadSpeed, ref size, ref unit, 1);
		cNetworkInfo.FormatSpeed(uploadSpeed, ref size2, ref unit2, 1);
		return new
		{
			NetworkDownload = Math.Round(size, 1) + " " + unit,
			NetworkUpload = Math.Round(size2, 1) + " " + unit2
		};
	}

	private object GetDiskInfo()
	{
		cDiskInfo.UpdateDiskInfo();
		var result = new
		{
			SSD_One_Model = GetSSD_One_Model(),
			SSD_One_Temperature = GetSSD_One_Temperature(),
			SSD_One_PowerOnHours = GetSSD_One_PowerOnHours(),
			SSD_One_PowerOnCount = GetSSD_One_PowerOnCount(),
			SSD_One_Interface = GetSSD_One_Interface(),
			SSD_One_Usage = GetSSD_One_Usage(),
			SSD_Two_Model = GetSSD_Two_Model(),
			SSD_Two_Temperature = GetSSD_Two_Temperature(),
			SSD_Two_PowerOnHours = GetSSD_Two_PowerOnHours(),
			SSD_Two_PowerOnCount = GetSSD_Two_PowerOnCount(),
			SSD_Two_Interface = GetSSD_Two_Interface(),
			SSD_Two_Usage = GetSSD_Two_Usage(),
			HDDModel = GetHDDModel(),
			HDDTemperature = GetHDDTemperature(),
			HDDPowerOnHours = GetHDDPowerOnHours(),
			HDDPowerOnCount = GetHDDPowerOnCount(),
			HDDInterface = GetHDDInterface(),
			HDDUsage = GetHDDUsage()
		};
		cDiskInfo.ResetArray();
		return result;
	}

	private string GetCpuTemperature()
	{
		return cCpuInfo.GetCPUTemperature().ToString();
	}

	private string GetCpuUsage()
	{
		return cCpuInfo.GetCPUUsage().ToString();
	}

	private string GetGpuTemperature()
	{
		return cGpuInfo.GetGpuTemperature().ToString();
	}

	private string GetGpuUsage()
	{
		return cGpuInfo.GetGpuUsage().ToString();
	}

	private string GetGpuCoreFreq()
	{
		return cGpuInfo.GetGpuCoreFreq().ToString();
	}

	private string GetGpuMemFreq()
	{
		return cGpuInfo.GetGpuMemFreq().ToString();
	}

	private string GetGpuPState()
	{
		return cGpuInfo.GetGpuPState().ToString();
	}

	private string GetGpuPhysicalRamSize()
	{
		return cGpuInfo.GetGpuPhysicalRamSize().ToString();
	}

	private dynamic GetMemoryUsage()
	{
		return cMemoryInfo.GetMemoryUsage();
	}

	private string GetNetworkDownload()
	{
		return cNetworkInfo.GetDownloadSpeed().ToString();
	}

	private string GetNetworkUpload()
	{
		return cNetworkInfo.GetUploadSpeed().ToString();
	}

	private string GetBatteryLifePercent()
	{
		return cBatteryInfo.GetBatteryLifePercent();
	}

	private string GetBatteryLifeRemaining()
	{
		return cBatteryInfo.GetBatteryLifeRemaining();
	}

	private string GetBatteryAbnormal()
	{
		return cBatteryInfo.GetBatteryAbnormal();
	}

	private string GetSSD_One_Model()
	{
		return cDiskInfo.GetSSD_One_Model();
	}

	private string GetSSD_One_Temperature()
	{
		return cDiskInfo.GetSSD_One_Temperature();
	}

	private string GetSSD_One_PowerOnHours()
	{
		return cDiskInfo.GetSSD_One_PowerOnHours();
	}

	private string GetSSD_One_PowerOnCount()
	{
		return cDiskInfo.GetSSD_One_PowerOnCount();
	}

	private string GetSSD_One_Interface()
	{
		return cDiskInfo.GetSSD_One_Interface();
	}

	private string GetSSD_One_Usage()
	{
		return cDiskInfo.GetSSD_One_Usage();
	}

	private string GetSSD_Two_Model()
	{
		return cDiskInfo.GetSSD_Two_Model();
	}

	private string GetSSD_Two_Temperature()
	{
		return cDiskInfo.GetSSD_Two_Temperature();
	}

	private string GetSSD_Two_PowerOnHours()
	{
		return cDiskInfo.GetSSD_Two_PowerOnHours();
	}

	private string GetSSD_Two_PowerOnCount()
	{
		return cDiskInfo.GetSSD_Two_PowerOnCount();
	}

	private string GetSSD_Two_Interface()
	{
		return cDiskInfo.GetSSD_Two_Interface();
	}

	private string GetSSD_Two_Usage()
	{
		return cDiskInfo.GetSSD_Two_Usage();
	}

	private string GetHDDModel()
	{
		return cDiskInfo.GetHDDModel();
	}

	private string GetHDDTemperature()
	{
		return cDiskInfo.GetHDDTemperature();
	}

	private string GetHDDPowerOnHours()
	{
		return cDiskInfo.GetHDDPowerOnHours();
	}

	private string GetHDDPowerOnCount()
	{
		return cDiskInfo.GetHDDPowerOnCount();
	}

	private string GetHDDInterface()
	{
		return cDiskInfo.GetHDDInterface();
	}

	private string GetHDDUsage()
	{
		return cDiskInfo.GetHDDUsage();
	}

	private void test()
	{
		PerformanceCounterCategory performanceCounterCategory = new PerformanceCounterCategory("GPU Adapter Memory");
		string[] instanceNames = performanceCounterCategory.GetInstanceNames();
		List<PerformanceCounter> memoryUsage = new List<PerformanceCounter>();
		string[] array = instanceNames;
		foreach (string instanceName in array)
		{
			memoryUsage.AddRange(performanceCounterCategory.GetCounters(instanceName));
		}
		Task.Run(delegate
		{
			PerformanceCounter performanceCounter = memoryUsage.Where((PerformanceCounter a) => a.CounterName == "Dedicated Usage").FirstOrDefault();
			while (true)
			{
				performanceCounter.NextValue();
			}
		});
	}
}
