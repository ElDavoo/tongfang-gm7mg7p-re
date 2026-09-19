using System;
using System.Runtime.InteropServices;

namespace MyControlCenter;

internal static class ReflashTray
{
	public struct RECT
	{
		public int left;

		public int top;

		public int right;

		public int bottom;
	}

	[DllImport("user32.dll")]
	public static extern IntPtr FindWindow(string lpClassName, string lpWindowName);

	[DllImport("user32.dll")]
	public static extern IntPtr FindWindowEx(IntPtr hwndParent, IntPtr hwndChildAfter, string lpszClass, string lpszWindow);

	[DllImport("user32.dll")]
	public static extern bool GetClientRect(IntPtr hWnd, out RECT lpRect);

	[DllImport("user32.dll")]
	public static extern IntPtr SendMessage(IntPtr hWnd, uint msg, int wParam, int lParam);

	public static void RefreshTrayArea()
	{
		IntPtr hwndParent = FindWindowEx(FindWindowEx(FindWindow("Shell_TrayWnd", null), IntPtr.Zero, "TrayNotifyWnd", null), IntPtr.Zero, "SysPager", null);
		IntPtr intPtr = FindWindowEx(hwndParent, IntPtr.Zero, "ToolbarWindow32", "Notification Area");
		if (intPtr == IntPtr.Zero)
		{
			intPtr = FindWindowEx(hwndParent, IntPtr.Zero, "ToolbarWindow32", "User Promoted Notification Area");
			RefreshTrayArea(FindWindowEx(FindWindow("NotifyIconOverflowWindow", null), IntPtr.Zero, "ToolbarWindow32", "Overflow Notification Area"));
		}
		RefreshTrayArea(intPtr);
	}

	private static void RefreshTrayArea(IntPtr windowHandle)
	{
		GetClientRect(windowHandle, out var lpRect);
		for (int i = 0; i < lpRect.right; i += 5)
		{
			for (int j = 0; j < lpRect.bottom; j += 5)
			{
				SendMessage(windowHandle, 512u, 0, (j << 16) + i);
			}
		}
	}
}
