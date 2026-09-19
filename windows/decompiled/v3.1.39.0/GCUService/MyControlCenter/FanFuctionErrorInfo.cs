using System;
using System.Collections;
using System.Windows.Forms;
using MyECIO;

namespace MyControlCenter;

internal class FanFuctionErrorInfo
{
	private MyEcCtrl EcCtrl = MyEcCtrl.Instance;

	private PowerStatus m_BatteryInfo = SystemInformation.PowerStatus;

	private int fanerror;

	public int GetECFanAlert()
	{
		byte Data = 0;
		EcCtrl.Read(GetType().Name, 1857, ref Data);
		BitArray bitArray = new BitArray(new byte[1] { Data });
		fanerror = Convert.ToInt32(bitArray[5]);
		return fanerror;
	}
}
