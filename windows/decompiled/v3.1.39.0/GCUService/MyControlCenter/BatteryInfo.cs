using System;
using System.Windows.Forms;
using MyECIO;

namespace MyControlCenter;

internal class BatteryInfo
{
	private MyEcCtrl EcCtrl = MyEcCtrl.Instance;

	private PowerStatus m_BatteryInfo = SystemInformation.PowerStatus;

	private int m_nBatteryAbnormal;

	public string GetBatteryLifePercent()
	{
		return (m_BatteryInfo.BatteryLifePercent * 100f).ToString();
	}

	public string GetCurrentBatteryFullChargeTime()
	{
		int num = -1;
		return m_BatteryInfo.BatteryFullLifetime.ToString();
	}

	public string GetBatteryLifeRemaining()
	{
		return m_BatteryInfo.BatteryLifeRemaining.ToString();
	}

	public string Init()
	{
		GetBatteryLifeCapacity();
		GetECBatteryAlert();
		return GetBatteryAbnormal();
	}

	private void GetBatteryLifeCapacity()
	{
	}

	private void GetECBatteryAlert()
	{
		byte Data = 0;
		EcCtrl.Read(GetType().Name, 1172, ref Data);
		if ((byte)(Convert.ToUInt64(Data) & 0xFF) != 0)
		{
			m_nBatteryAbnormal = 3;
		}
	}

	public string GetBatteryCapacity()
	{
		return 0u + " mWh";
	}

	public string GetFullBatteryCapacity()
	{
		return 0 + " mWh";
	}

	public string GetECBatteryCycleCount()
	{
		byte Data = 0;
		EcCtrl.Read(GetType().Name, 1190, ref Data);
		byte b = (byte)Convert.ToUInt64(Data);
		EcCtrl.Read(GetType().Name, 1191, ref Data);
		return (((byte)Convert.ToUInt64(Data) << 8) | b).ToString();
	}

	public string GetBatteryAbnormal()
	{
		try
		{
			if (m_BatteryInfo.BatteryChargeStatus.ToString().Equals("NoSystemBattery") || m_BatteryInfo.BatteryChargeStatus.ToString().Equals("Unknown"))
			{
				m_nBatteryAbnormal = 1;
			}
			else if (m_nBatteryAbnormal != 2 && m_nBatteryAbnormal != 3)
			{
				m_nBatteryAbnormal = 0;
			}
		}
		catch
		{
		}
		return m_nBatteryAbnormal.ToString();
	}
}
