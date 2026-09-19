using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Timers;
using System.Windows.Threading;
using DynamicDesk;
using GCUService.WindowsW;
using Microsoft.Win32;
using Utility;

namespace MyControlCenter;

public class MySystemManager
{
	private MySystemView m_View = new MySystemView();

	private string beforeCpuValue = "0";

	private string beforeMemoryValue = "0";

	private string beforeGpuValue = "0";

	private string beforeBatteryValue = "0";

	private bool UPnPSwtich;

	private bool SqliteDbSwitch;

	private System.Timers.Timer cpuinfoTimer;

	private System.Timers.Timer diskinfoTimer;

	private System.Timers.Timer CpuTempDbTimer;

	private System.Timers.Timer BatteryTimer;

	private System.Timers.Timer FanInfoTimer;

	private CPUInfo cCpuInfo = new CPUInfo();

	private GPUInfo cGpuInfo = new GPUInfo();

	private MemoryInfo cMemoryInfo = new MemoryInfo();

	private NetworkInfo cNetworkInfo = new NetworkInfo();

	private BatteryInfo cBatteryInfo = new BatteryInfo();

	private DiskInfo cDiskInfo = new DiskInfo();

	private FanFuctionErrorInfo _FanFunctionErrorInfo = new FanFuctionErrorInfo();

	private FanInfo _FanInfo = new FanInfo();

	private HwFuelGaugeInfo _HwFuelGaugeInfo = new HwFuelGaugeInfo();

	private bool EnsureStart;

	private WindowW windowsw;

	private WindowsW_Viewmodel ww_viewmodel = WindowsW_Viewmodel.Instance;

	private object gpuInfoLock = new object();

	private int gpuCommandCount;

	private object diskInfoLock = new object();

	private int disErrorCount;

	private int diskCommandCount;

	private bool IsNvGpu;

	private Stopwatch sw = new Stopwatch();

	private object windowswLock = new object();

	private static string _GraphicInfo = new HardwareInfoCollect().getGraphicInfo();

	private void HotkeyEventHandler(object sender, EventArgs e)
	{
		dynamic val = new { };
		m_View.SendStatusToClient("Monitor/Status", val);
	}

	private void SetBackgroundPlayType(string backgroundPlayType)
	{
		windowsw.Dispatcher?.BeginInvoke((Action)delegate
		{
			windowsw.SetBackgroundPlayType(backgroundPlayType);
		}, DispatcherPriority.Background);
	}

	private void SetInitVideoList(string monitorVideoList)
	{
		if (monitorVideoList != null && monitorVideoList != "")
		{
			List<string> videoList = Json.ToObject<List<string>>(monitorVideoList);
			SetVideoList(videoList);
		}
	}

	private void Standby_ModernStandbyChanged(object sender, EventArgs e)
	{
		_ = sender.ToString() == "On";
	}

	public virtual void InitTimers()
	{
		IsNvGpu = UtilityExtensions.IsNvGpu();
		cpuinfoTimer = new System.Timers.Timer();
		cpuinfoTimer.Interval = 2000.0;
		cpuinfoTimer.Elapsed += CpuinfoTimer_Elapsed;
		diskinfoTimer = new System.Timers.Timer();
		diskinfoTimer.Interval = 10000.0;
		diskinfoTimer.Elapsed += DiskinfoTimer_Elapsed;
		CpuTempDbTimer = new System.Timers.Timer();
		CpuTempDbTimer.Interval = 60000.0;
		CpuTempDbTimer.Elapsed += CpuTempDbTimer_Elapsed;
		BatteryTimer = new System.Timers.Timer();
		BatteryTimer.Interval = 60000.0;
		BatteryTimer.Elapsed += BatteryTimer_Elapsed;
		FanInfoTimer = new System.Timers.Timer();
		FanInfoTimer.Interval = 2000.0;
		FanInfoTimer.Elapsed += FanInfoTimer_Elapsed;
	}

	private void StartTimers()
	{
		cpuinfoTimer.Start();
		diskinfoTimer.Start();
		CpuTempDbTimer.Start();
		BatteryTimer.Start();
		FanInfoTimer.Start();
	}

	private void StopTimers()
	{
		try
		{
			cpuinfoTimer.Stop();
			diskinfoTimer.Stop();
			CpuTempDbTimer.Stop();
			BatteryTimer.Stop();
			FanInfoTimer.Stop();
		}
		catch (Exception ex)
		{
			Console.WriteLine("System monitor error " + ex.ToString());
		}
	}

	private void Enable()
	{
		InitFanFunctionErrorInfo();
		Task.Run(delegate
		{
			InitDiskBatteryInfo();
		});
		InitSystemInfo();
		StartTimers();
	}

	public virtual void Disable()
	{
		if (!EnsureStart)
		{
			StopTimers();
		}
	}

	public virtual void Dispose()
	{
	}

	public virtual async void Receive(byte[] message)
	{
		dynamic val = await Json.ToObjectAsync<object>(Encoding.UTF8.GetString(message));
		string text = val["Action"];
		string text2 = val["Location"];
		string text3 = val["BackgroundShow"];
		string text4 = val["BackgroundPlayType"];
		string text5 = val["BackgroundFileName"];
		string text6 = val["MonitorShow"];
		string text7 = val["MonitorHotkey"];
		string text8 = val["MonitorColor"];
		string text9 = val["MonitorTransparent"];
		string text10 = val["MonitorSize"];
		dynamic val2 = val["VideoList"];
		if (val["Action"] != null)
		{
			text = text.ToLowerInvariant();
			if (text.Contains("getgraphicinfo"))
			{
				GetGraphicInfo();
			}
			else if (text.Contains("system_on"))
			{
				Enable();
			}
			else if (text.Contains("system_off"))
			{
				Disable();
			}
			if (text.Contains("getstatus"))
			{
				try
				{
					SetStatusToClient();
				}
				catch (Exception)
				{
				}
			}
		}
		if (text2 != null)
		{
			SetLocation(text2);
		}
		if (text3 != null)
		{
			bool background = (text3.ToLowerInvariant().Contains("on") ? true : false);
			SetBackground(background);
		}
		if (text4 != null)
		{
			SetBackgroundPlayType(text4);
		}
		if (text6 != null)
		{
			bool monitorSwitch = (text6.ToLowerInvariant().Contains("on") ? true : false);
			SetMonitorSwitch(monitorSwitch);
		}
		if (text7 != null)
		{
			bool hotKey = (text7.ToLowerInvariant().Contains("on") ? true : false);
			SetHotKey(hotKey);
		}
		if (text5 != null)
		{
			SetBackgroundFile(text5);
		}
		if (text8 != null)
		{
			SetColor(text8);
		}
		if (text9 != null)
		{
			SetTransparent(text9);
		}
		if (text10 != null)
		{
			SetSize(text10);
		}
		if (!((val2 != null) ? true : false))
		{
			return;
		}
		List<string> list = new List<string>();
		foreach (dynamic item in val2)
		{
			list.Add(Convert.ToString(item));
		}
		SetVideoList(list);
	}

	private void SetStatusToClient()
	{
	}

	private bool GetMonitorSupport()
	{
		return Convert.ToBoolean(RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2\\", "MonitorSupport", 0, RegistryValueKind.DWord));
	}

	private void SetMonitorSwitch(bool ONFF)
	{
		windowsw.Dispatcher?.BeginInvoke((Action)delegate
		{
			if (windowsw != null)
			{
				windowsw.ShowMonitor(ONFF);
			}
		}, DispatcherPriority.Background);
		if (ONFF)
		{
			EnsureStart = true;
			Enable();
		}
		else
		{
			EnsureStart = false;
			Disable();
		}
	}

	private void SetBackground(bool ONFF)
	{
		windowsw.Dispatcher?.BeginInvoke((Action)delegate
		{
			if (windowsw != null)
			{
				windowsw.ShowBackground(ONFF);
			}
		}, DispatcherPriority.Background);
	}

	private void SetBackgroundFile(string backgroundFileName)
	{
		windowsw.Dispatcher?.BeginInvoke((Action)delegate
		{
			if (windowsw != null)
			{
				windowsw.ChangeAndPlayVideo(backgroundFileName);
			}
		}, DispatcherPriority.Background);
	}

	private void SetLocation(string location)
	{
		windowsw.Dispatcher?.BeginInvoke((Action)delegate
		{
			if (windowsw != null)
			{
				windowsw.ShowMonitorLocation(location);
			}
		}, DispatcherPriority.Background);
	}

	private void SetColor(string monitorColor)
	{
		windowsw.Dispatcher?.BeginInvoke((Action)delegate
		{
			if (windowsw != null)
			{
				windowsw.SetColor(monitorColor, monitorColor);
			}
		}, DispatcherPriority.Background);
	}

	private void SetHotKey(bool ONOFF)
	{
		windowsw.Dispatcher?.BeginInvoke((Action)delegate
		{
			if (windowsw != null)
			{
				windowsw.SetHotkeyEnable(ONOFF);
			}
		}, DispatcherPriority.Background);
	}

	private void SetTransparent(string percent)
	{
		windowsw.Dispatcher?.BeginInvoke((Action)delegate
		{
			if (windowsw != null)
			{
				windowsw.SetTransparent(percent);
			}
		}, DispatcherPriority.Background);
	}

	private void SetSize(string percent)
	{
		windowsw.Dispatcher?.BeginInvoke((Action)delegate
		{
			if (windowsw != null)
			{
				windowsw.SetSize(percent);
			}
		}, DispatcherPriority.Background);
	}

	private void SetVideoList(List<string> SetVideoList)
	{
		windowsw.Dispatcher?.BeginInvoke((Action)delegate
		{
			if (windowsw != null)
			{
				windowsw.SetVideoList(SetVideoList);
			}
		}, DispatcherPriority.Background);
	}

	private void BatteryTimer_Elapsed(object sender, ElapsedEventArgs e)
	{
		dynamic batteryInfo = GetBatteryInfo();
		ww_viewmodel.BatteryLifePercent = Convert.ToUInt32(batteryInfo.BatteryLifePercent);
		m_View.SendStatusToClient("System/BatteryInfo", batteryInfo);
		beforeBatteryValue = batteryInfo.BatteryLifePercent;
	}

	private void FanInfoTimer_Elapsed(object sender, ElapsedEventArgs e)
	{
		dynamic funInfo = GetFunInfo();
		m_View.SendStatusToClient("System/FanInfo", funInfo);
	}

	private void HwFuelGaugeTimer_Elapsed(object sender, ElapsedEventArgs e)
	{
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
			HardwareInfoCollect hardwareInfoCollect = new HardwareInfoCollect();
			string processorInfo = hardwareInfoCollect.getProcessorInfo();
			string graphicInfo = hardwareInfoCollect.getGraphicInfo();
			string memoryUsableInfo = hardwareInfoCollect.getMemoryInfo() + " GB(" + hardwareInfoCollect.getMemoryUsableInfo() + " GB usable)";
			string bIOSInfo = hardwareInfoCollect.getBIOSInfo();
			string eCInfo = hardwareInfoCollect.getECInfo();
			dynamic val = new
			{
				ProcessorInfo = processorInfo,
				GraphicInfo = graphicInfo,
				MemoryUsableInfo = memoryUsableInfo,
				BIOSInfo = bIOSInfo,
				ECInfo = eCInfo
			};
			m_View.SendStatusToClient("System/HardwareInfo", val);
		}
		catch (Exception ex)
		{
			LogCtrl.Write("Hardware info " + ex.ToString());
		}
	}

	private async void InitDiskBatteryInfo()
	{
		dynamic val = InitBatteryInfo();
		ww_viewmodel.BatteryLifePercent = Convert.ToUInt32(val.BatteryLifePercent);
		m_View.SendStatusToClient("System/BatteryInfo", val);
		try
		{
			dynamic diskInfo = GetDiskInfo();
			if (diskInfo != null)
			{
				m_View.SendStatusToClient("System/DiskInfo", diskInfo);
			}
		}
		catch (Exception)
		{
		}
	}

	private void CpuinfoTimer_Elapsed(object sender, ElapsedEventArgs e)
	{
		dynamic cpuInfo = GetCpuInfo();
		ww_viewmodel.CPUUsage = Convert.ToUInt32(cpuInfo.CpuUsage);
		ww_viewmodel.CpuTemperature = Convert.ToUInt32(cpuInfo.CpuTemperature);
		m_View.SendStatusToClient("System/CpuInfo", cpuInfo);
		beforeCpuValue = cpuInfo.CpuUsage;
		dynamic memoryInfo = GetMemoryInfo();
		ww_viewmodel.MemoryUsage = Convert.ToUInt32(memoryInfo.MemoryUsage);
		m_View.SendStatusToClient("System/MemoryInfo", memoryInfo);
		dynamic gpuInfo = GetGpuInfo();
		ww_viewmodel.GpuUsage = 0u;
		ww_viewmodel.GpuTemperature = 0u;
		if (gpuInfo != null)
		{
			ww_viewmodel.GpuUsage = Convert.ToUInt32(gpuInfo?.GpuUsage);
			ww_viewmodel.GpuTemperature = Convert.ToUInt32(gpuInfo.GpuTemperature);
			if ((int)Convert.ToInt32(gpuInfo.GpuTemperature) != 0)
			{
				m_View.SendStatusToClient("System/GpuInfo", gpuInfo);
			}
		}
		if (GetNetworkStatus())
		{
			dynamic networkInfo = GetNetworkInfo();
			m_View.SendStatusToClient("System/NetworkInfo", networkInfo);
		}
	}

	private async void DiskinfoTimer_Elapsed(object sender, ElapsedEventArgs e)
	{
		try
		{
			dynamic diskInfo = GetDiskInfo();
			if (diskInfo != null)
			{
				m_View.SendStatusToClient("System/DiskInfo", diskInfo);
			}
		}
		catch (Exception)
		{
		}
	}

	private void CpuTempDbTimer_Elapsed(object sender, ElapsedEventArgs e)
	{
		_ = SqliteDbSwitch;
	}

	private void GetCalanderData(DateTime dt)
	{
		new Calendar.ChineseCalendar(dt);
	}

	private void GetGraphicInfo()
	{
		try
		{
			dynamic val = new
			{
				GraphicInfo = _GraphicInfo
			};
			m_View.SendStatusToClient("System/HardwareInfo", val);
		}
		catch (Exception ex)
		{
			LogCtrl.Write("Graphic info " + ex.ToString());
		}
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
		if (IsNvGpu)
		{
			return new
			{
				CpuFanDuty = _FanInfo.GetEcCpuFanDuty(),
				GpuFanDuty = _FanInfo.GetEcGpuFanDuty()
			};
		}
		return new
		{
			CpuFanDuty = _FanInfo.GetEcCpuFanDuty()
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
			CpuTemperature = GetCpuTemperature()
		};
	}

	private object GetMemoryInfo()
	{
		return GetMemoryUsage();
	}

	private string GetGpuUsageOnly()
	{
		return GetGpuUsage();
	}

	private object GetGpuInfo()
	{
		if (gpuCommandCount == 0 && Monitor.TryEnter(gpuInfoLock, 2000))
		{
			try
			{
				gpuCommandCount++;
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
			catch
			{
			}
			finally
			{
				Monitor.Exit(gpuInfoLock);
				gpuCommandCount = 0;
			}
		}
		return null;
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
		if (diskCommandCount == 0 && Monitor.TryEnter(diskInfoLock, 1000))
		{
			try
			{
				diskCommandCount++;
				cDiskInfo.UpdateDiskInfo();
				var result = new
				{
					SSD_One_Model = GetSSD_One_Model(),
					SSD_One_Temperature = GetSSD_One_Temperature(),
					SSD_One_PowerOnHours = GetSSD_One_PowerOnHours(),
					SSD_One_PowerOnCount = GetSSD_One_PowerOnCount(),
					SSD_One_Interface = GetSSD_One_Interface(),
					SSD_Two_Model = GetSSD_Two_Model(),
					SSD_Two_Temperature = GetSSD_Two_Temperature(),
					SSD_Two_PowerOnHours = GetSSD_Two_PowerOnHours(),
					SSD_Two_PowerOnCount = GetSSD_Two_PowerOnCount(),
					SSD_Two_Interface = GetSSD_Two_Interface(),
					HDDModel = GetHDDModel(),
					HDDTemperature = GetHDDTemperature(),
					HDDPowerOnHours = GetHDDPowerOnHours(),
					HDDPowerOnCount = GetHDDPowerOnCount(),
					HDDInterface = GetHDDInterface()
				};
				cDiskInfo.ResetArray();
				return result;
			}
			catch
			{
			}
			finally
			{
				Monitor.Exit(diskInfoLock);
				diskCommandCount = 0;
			}
		}
		disErrorCount++;
		return null;
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
}
