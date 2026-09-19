using System;
using MyECIO;

namespace MyControlCenter;

internal class FanInfo
{
	private MyEcCtrl EcCtrl = MyEcCtrl.Instance;

	public int GetEcCpuFanDuty()
	{
		byte Data = 0;
		EcCtrl.Read(GetType().Name, 1883, ref Data);
		return (byte)Convert.ToUInt64(Data) / 2;
	}

	public int GetEcGpuFanDuty()
	{
		byte Data = 0;
		EcCtrl.Read(GetType().Name, 1884, ref Data);
		return (byte)Convert.ToUInt64(Data) / 2;
	}

	public int GetEcCpuFanRpm()
	{
		byte Data = 0;
		EcCtrl.Read(GetType().Name, 1124, ref Data);
		byte num = (byte)Convert.ToUInt64(Data);
		EcCtrl.Read(GetType().Name, 1125, ref Data);
		byte b = (byte)Convert.ToUInt64(Data);
		return (num << 8) | b;
	}

	public int GetEcGpuFanRpm()
	{
		byte Data = 0;
		EcCtrl.Read(GetType().Name, 1132, ref Data);
		byte num = (byte)Convert.ToUInt64(Data);
		EcCtrl.Read(GetType().Name, 1131, ref Data);
		byte b = (byte)Convert.ToUInt64(Data);
		return (num << 8) | b;
	}
}
