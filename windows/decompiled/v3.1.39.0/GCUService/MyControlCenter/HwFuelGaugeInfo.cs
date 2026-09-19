using System;
using MyECIO;

namespace MyControlCenter;

internal class HwFuelGaugeInfo
{
	private MyEcCtrl EcCtrl = MyEcCtrl.Instance;

	public string GetDesignCapacity()
	{
		return 0 + " mWh";
	}

	public string GetECDesignVoltage()
	{
		byte Data = 0;
		EcCtrl.Read(GetType().Name, 1032, ref Data);
		byte b = (byte)Convert.ToUInt64(Data);
		EcCtrl.Read(GetType().Name, 1033, ref Data);
		return (((byte)Convert.ToUInt64(Data) << 8) | b).ToString();
	}

	public string GetVoltage()
	{
		return 0u.ToString();
	}

	public string GetECCurrent()
	{
		byte Data = 0;
		EcCtrl.Read(GetType().Name, 1076, ref Data);
		byte b = (byte)Convert.ToUInt64(Data);
		EcCtrl.Read(GetType().Name, 1077, ref Data);
		return (((byte)Convert.ToUInt64(Data) << 8) | b).ToString();
	}
}
