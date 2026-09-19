using System;
using System.Runtime.InteropServices;
using System.Threading;
using System.Windows.Forms;
using Utility;

namespace MyControlCenter;

public class HiddenOSDLib
{
	private NotifyIcon ni;

	private IntPtr hWndInject = IntPtr.Zero;

	private static readonly HiddenOSDLib hiddenosdLib = new HiddenOSDLib();

	public static HiddenOSDLib Instance => hiddenosdLib;

	[DllImport("user32.dll")]
	private static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, int dwExtraInfo);

	[DllImport("user32.dll", SetLastError = true)]
	private static extern IntPtr FindWindowEx(IntPtr hwndParent, IntPtr hwndChildAfter, string lpszClass, string lpszWindow);

	[DllImport("user32.dll", SetLastError = true)]
	private static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);

	public HiddenOSDLib(NotifyIcon ni)
	{
		this.ni = ni;
	}

	private HiddenOSDLib()
	{
	}

	public IntPtr GetCurrentInject()
	{
		return hWndInject;
	}

	public void Init()
	{
		int num = 0;
		while (hWndInject == IntPtr.Zero && num < 5)
		{
			Thread.Sleep(3000);
			keybd_event(175, 0, 0u, 0);
			keybd_event(174, 0, 0u, 0);
			hWndInject = FindOSDWindow(bSilent: true);
			HideOSD();
			num++;
		}
		if (hWndInject != IntPtr.Zero)
		{
			HideOSD();
		}
		hWndInject = FindOSDWindow(bSilent: false);
	}

	private IntPtr FindOSDWindow(bool bSilent)
	{
		IntPtr intPtr = IntPtr.Zero;
		IntPtr intPtr2 = IntPtr.Zero;
		int num = 0;
		while ((intPtr2 = FindWindowEx(IntPtr.Zero, intPtr2, "NativeHWNDHost", "")) != IntPtr.Zero)
		{
			if (FindWindowEx(intPtr2, IntPtr.Zero, "DirectUIHWND", "") != IntPtr.Zero)
			{
				if (num == 0)
				{
					intPtr = intPtr2;
				}
				num++;
				if (num > 1)
				{
					LogCtrl.Write("Severe error: Multiple pairs found!HideOSD");
					return IntPtr.Zero;
				}
			}
		}
		if (intPtr == IntPtr.Zero && !bSilent)
		{
			LogCtrl.Write("Severe error: OSD window not found!HideOSD");
		}
		return intPtr;
	}

	private void Application_ApplicationExit(object sender, EventArgs e)
	{
		ShowOSD();
	}

	public void HideOSD()
	{
		ShowWindow(hWndInject, 6);
	}

	public void ShowOSD()
	{
		ShowWindow(hWndInject, 9);
	}
}
