using System;
using System.Runtime.InteropServices;
using Utility;

namespace MyControlCenter;

internal static class DisplaySwitch
{
	public static int SC_MONITORPOWER = 61808;

	public static int WM_SYSCOMMAND = 274;

	[DllImport("kernel32.dll")]
	public static extern IntPtr GetConsoleWindow();

	[DllImport("user32.dll", ExactSpelling = true)]
	public static extern int SendMessageW(int hWnd, int wMsg, int wParam, int lParam);

	public static void SetDisplayState(int state)
	{
		LogCtrl.Write("[MySetting] Recieve DISPLAY_POWER_OFF");
		SendMessageW(65535, WM_SYSCOMMAND, SC_MONITORPOWER, state);
	}
}
