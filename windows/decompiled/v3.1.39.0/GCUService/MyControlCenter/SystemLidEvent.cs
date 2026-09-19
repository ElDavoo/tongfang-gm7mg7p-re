using System;
using System.Runtime.InteropServices;
using System.Windows.Interop;

namespace MyControlCenter;

internal class SystemLidEvent
{
	internal struct POWERBROADCAST_SETTING
	{
		public Guid PowerSetting;

		public uint DataLength;

		public byte Data;
	}

	public EventArgs LidStatusChange;

	private Guid GUID_LIDSWITCH_STATE_CHANGE = new Guid(3124629325u, 47127, 16532, 162, 209, 213, 99, 121, 230, 160, 243);

	private const int DEVICE_NOTIFY_WINDOW_HANDLE = 0;

	private const int WM_POWERBROADCAST = 536;

	private const int PBT_POWERSETTINGCHANGE = 32787;

	private bool? _previousLidState;

	private IntPtr hwnd;

	[DllImport("User32", CallingConvention = CallingConvention.StdCall, SetLastError = true)]
	private static extern IntPtr RegisterPowerSettingNotification(IntPtr hRecipient, ref Guid PowerSettingGuid, int Flags);

	[DllImport("kernel32.dll", CharSet = CharSet.Auto, SetLastError = true)]
	private static extern IntPtr GetModuleHandle(string lpModuleName);

	public SystemLidEvent()
	{
		hwnd = GetModuleHandle("user32");
		RegisterForPowerNotifications();
		HwndSource.FromHwnd(hwnd).AddHook(WndProc);
	}

	private void RegisterForPowerNotifications()
	{
		RegisterPowerSettingNotification(hwnd, ref GUID_LIDSWITCH_STATE_CHANGE, 0);
	}

	private IntPtr WndProc(IntPtr hwnd, int msg, IntPtr wParam, IntPtr lParam, ref bool handled)
	{
		if (msg == 536)
		{
			OnPowerBroadcast(wParam, lParam);
		}
		return IntPtr.Zero;
	}

	private void OnPowerBroadcast(IntPtr wParam, IntPtr lParam)
	{
		if ((int)wParam != 32787)
		{
			return;
		}
		POWERBROADCAST_SETTING structure = (POWERBROADCAST_SETTING)Marshal.PtrToStructure(lParam, typeof(POWERBROADCAST_SETTING));
		_ = (int)Marshal.PtrToStructure((IntPtr)((int)lParam + Marshal.SizeOf(structure)), typeof(int));
		if (structure.PowerSetting == GUID_LIDSWITCH_STATE_CHANGE)
		{
			bool flag = structure.Data != 0;
			if (!flag == _previousLidState)
			{
				LidStatusChanged(flag);
			}
			_previousLidState = flag;
		}
	}

	private void LidStatusChanged(bool isLidOpen)
	{
	}
}
