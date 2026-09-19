using System.Windows.Threading;

namespace GCUService.WindowsW;

internal class WindowsW_Viewmodel : ManagerBase
{
	private static readonly WindowsW_Viewmodel model = new WindowsW_Viewmodel();

	private uint _CPUUsage;

	private uint _CpuTemperature;

	private uint _GpuUsage;

	private uint _GpuTemperature;

	private uint _MemoryUsage;

	private uint _BatteryLifePercent;

	public static WindowsW_Viewmodel Instance => model;

	public Dispatcher dispatcher { get; set; }

	public uint CPUUsage
	{
		get
		{
			return _CPUUsage;
		}
		set
		{
			if (value != _CPUUsage)
			{
				_CPUUsage = value;
				OnPropertyChanged("CPUUsage");
			}
		}
	}

	public uint CpuTemperature
	{
		get
		{
			return _CpuTemperature;
		}
		set
		{
			if (value != _CpuTemperature)
			{
				_CpuTemperature = value;
				OnPropertyChanged("CpuTemperature");
			}
		}
	}

	public uint GpuUsage
	{
		get
		{
			return _GpuUsage;
		}
		set
		{
			if (value != _GpuUsage)
			{
				_GpuUsage = value;
				OnPropertyChanged("GpuUsage");
			}
		}
	}

	public uint GpuTemperature
	{
		get
		{
			return _GpuTemperature;
		}
		set
		{
			if (value != _GpuTemperature)
			{
				_GpuTemperature = value;
				OnPropertyChanged("GpuTemperature");
			}
		}
	}

	public uint MemoryUsage
	{
		get
		{
			return _MemoryUsage;
		}
		set
		{
			_MemoryUsage = value;
			OnPropertyChanged("MemoryUsage");
		}
	}

	public uint BatteryLifePercent
	{
		get
		{
			return _BatteryLifePercent;
		}
		set
		{
			_BatteryLifePercent = value;
			OnPropertyChanged("BatteryLifePercent");
		}
	}
}
