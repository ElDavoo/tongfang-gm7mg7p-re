using System;

namespace BatteryModel;

public class BM_Manager
{
	private BM_Power bm_power;

	public BM_Manager()
	{
		bm_power = new BM_Power();
	}

	public bool BM_Init()
	{
		return true;
	}

	public bool GetBatteryLife(out double percentage)
	{
		BatteryInformation information = BatteryInfo.GetInformation();
		percentage = Math.Round((double)information.FullChargeCapacity / (double)information.DesignedMaxCapacity, 2);
		return true;
	}

	public bool GetCurrentCapacity(out uint CurrentCapacity)
	{
		CurrentCapacity = BatteryInfo.GetInformation().CurrentCapacity;
		return true;
	}

	public bool GetRate(out int rate)
	{
		rate = BatteryInfo.GetInformation().DischargeRate;
		return true;
	}

	public bool GetDesignCapacity(out int DesignCapacity)
	{
		DesignCapacity = BatteryInfo.GetInformation().DesignedMaxCapacity;
		return true;
	}

	public bool GetFullCapacity(out int FullCapacity)
	{
		FullCapacity = BatteryInfo.GetInformation().FullChargeCapacity;
		return true;
	}

	public bool GetVoltage(out uint Voltage)
	{
		Voltage = BatteryInfo.GetInformation().Voltage;
		return true;
	}
}
