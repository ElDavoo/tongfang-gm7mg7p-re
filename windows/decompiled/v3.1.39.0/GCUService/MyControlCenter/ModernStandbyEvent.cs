using System;
using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Interop;
using System.Windows.Threading;
using MyRGBKeyboard;
using Utility;

namespace MyControlCenter;

internal class ModernStandbyEvent
{
	private bool bInit = true;

	private HwndSource _HwndSource;

	private IntPtr _ScreenStateNotify;

	private static readonly ModernStandbyEvent model = new ModernStandbyEvent();

	private const int PBT_APMSUSPEND = 4;

	private const int PBT_APMRESUMESUSPEND = 7;

	private const int PBT_APMRESUMEAUTOMATIC = 18;

	public Dispatcher dispatcher { get; set; }

	public static ModernStandbyEvent CreateInstance => model;

	public event EventHandler ModernStandbyChanged;

	public void MonitorMondernStandBy()
	{
		dispatcher?.BeginInvoke((Action)delegate
		{
			try
			{
				IntPtr intPtr = new WindowInteropHelper(new Window()).EnsureHandle();
				_ScreenStateNotify = NativeMethods.RegisterPowerSettingNotification(intPtr, ref NativeMethods.GUID_CONSOLE_DISPLAY_STATE, 0);
				_HwndSource = HwndSource.FromHwnd(intPtr);
				_HwndSource.AddHook(WndProc);
			}
			catch (Exception)
			{
			}
		}, DispatcherPriority.Background);
	}

	private IntPtr WndProc(IntPtr hwnd, int msg, IntPtr wParam, IntPtr lParam, ref bool handled)
	{
		if (msg == 536)
		{
			if ((int)wParam == 32787)
			{
				NativeMethods.POWERBROADCAST_SETTING pOWERBROADCAST_SETTING = (NativeMethods.POWERBROADCAST_SETTING)Marshal.PtrToStructure(lParam, typeof(NativeMethods.POWERBROADCAST_SETTING));
				if (pOWERBROADCAST_SETTING.PowerSetting == NativeMethods.GUID_CONSOLE_DISPLAY_STATE)
				{
					_ = RGBKeyboard.Instance;
					_ = HIDRGBLightbar.Instance;
					switch (pOWERBROADCAST_SETTING.Data)
					{
					case 0:
						LogCtrl.Write("---------------" + LogCtrl.GetTime() + "---------------");
						LogCtrl.Write("WndProc wParam: PBT_POWERSETTINGCHANGE, Monitor Power Off");
						Console.WriteLine("WndProc wParam: PBT_POWERSETTINGCHANGE, Monitor Power Off");
						if (this.ModernStandbyChanged != null)
						{
							this.ModernStandbyChanged("Off", null);
						}
						break;
					case 1:
						LogCtrl.Write("---------------" + LogCtrl.GetTime() + "---------------");
						LogCtrl.Write("WndProc wParam: PBT_POWERSETTINGCHANGE, Monitor Power On");
						Console.WriteLine("WndProc wParam: PBT_POWERSETTINGCHANGE, Monitor Power On");
						if (bInit)
						{
							bInit = false;
						}
						else if (this.ModernStandbyChanged != null)
						{
							this.ModernStandbyChanged("On", null);
						}
						break;
					case 2:
						LogCtrl.Write("---------------" + LogCtrl.GetTime() + "---------------");
						LogCtrl.Write("WndProc wParam: PBT_POWERSETTINGCHANGE, Monitor Dimmed");
						Console.WriteLine("WndProc wParam: PBT_POWERSETTINGCHANGE, Monitor Dimmed");
						break;
					}
				}
			}
			else
			{
				LogCtrl.Write("---------------" + LogCtrl.GetTime() + "---------------");
				LogCtrl.Write("WndProc wParam: " + wParam);
			}
		}
		return IntPtr.Zero;
	}
}
