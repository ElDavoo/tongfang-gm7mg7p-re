using System.Windows.Forms;
using Microsoft.Win32;
using MyECIO;
using Utility;

namespace MyControlCenter;

internal class PowerModeEvent
{
	public static int g_ACLineStatus;

	private PowerStatus BatteryStatus = SystemInformation.PowerStatus;

	private MyEcCtrl EcCtrl = MyEcCtrl.Instance;

	private MyFanCtrl m_MyFan = MyFanCtrl.Instance;

	public void Changed(object sender, PowerModeChangedEventArgs e)
	{
		LogCtrl.Write("---------------" + LogCtrl.GetTime() + "---------------");
		if (e.Mode == PowerModes.StatusChange)
		{
			RefreshACLineStatus();
			LogCtrl.Write("PowerModeEvent | Changed | StatusChange MyFan");
			m_MyFan.PowerStatusChange(g_ACLineStatus);
			if (CustomizeInfo.m_sLightbarType == "2")
			{
				LogCtrl.Write("PowerModeEvent | Changed | StatusChange MyRgbLightbar");
				MyRgbLightbarCtrl.Instance.PowerStatusChange(g_ACLineStatus);
			}
		}
	}

	public void RefreshACLineStatus()
	{
		if (BatteryStatus.PowerLineStatus.ToString().Equals("Offline"))
		{
			g_ACLineStatus = 0;
		}
		else if (BatteryStatus.PowerLineStatus.ToString().Equals("Online"))
		{
			g_ACLineStatus = 1;
		}
	}
}
