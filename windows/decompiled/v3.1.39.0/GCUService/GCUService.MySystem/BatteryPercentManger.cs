using System;
using System.Timers;
using MyControlCenter;

namespace GCUService.MySystem;

internal class BatteryPercentManger
{
	private BatteryInfo cBatteryInfo = new BatteryInfo();

	private string BatteryLifePercent;

	private string BatteryLifeRemaining;

	private string BatteryAbnormal;

	private Timer _Timer = new Timer();

	public event EventHandler LifePercentChange;

	public BatteryPercentManger()
	{
		BatteryLifePercent = cBatteryInfo.GetBatteryLifePercent();
		BatteryLifeRemaining = cBatteryInfo.GetBatteryLifeRemaining();
		BatteryAbnormal = cBatteryInfo.Init();
		_Timer.Interval = 10000.0;
		_Timer.Elapsed += _Timer_Elapsed;
		_Timer.Start();
	}

	public void BatteryStop()
	{
		_Timer.Stop();
	}

	public void BatteryStart()
	{
		_Timer.Start();
	}

	public string GetCurrentBatteryLifePercent()
	{
		return cBatteryInfo.GetBatteryLifePercent();
	}

	public string GetCurrentBatteryLifeTime()
	{
		return cBatteryInfo.GetBatteryLifeRemaining();
	}

	public string GetCurrentBatteryFullChargeTime()
	{
		return cBatteryInfo.GetCurrentBatteryFullChargeTime();
	}

	private void _Timer_Elapsed(object sender, ElapsedEventArgs e)
	{
		if (BatteryLifePercent != cBatteryInfo.GetBatteryLifePercent())
		{
			BatteryLifePercent = cBatteryInfo.GetBatteryLifePercent();
			if (this.LifePercentChange != null)
			{
				this.LifePercentChange(BatteryLifePercent, null);
			}
		}
	}
}
