using System;
using System.Drawing;
using System.Runtime.InteropServices;
using System.Windows.Forms;

namespace MyControlCenter;

internal class ScreenDetection
{
	private static IntPtr desktopHandle;

	private static IntPtr shellHandle;

	[DllImport("user32.dll")]
	private static extern IntPtr GetForegroundWindow();

	[DllImport("user32.dll")]
	private static extern IntPtr GetDesktopWindow();

	[DllImport("user32.dll")]
	private static extern IntPtr GetShellWindow();

	[DllImport("user32.dll", SetLastError = true)]
	private static extern int GetWindowRect(IntPtr hwnd, out RECT rc);

	public static bool AreApplicationFullScreen()
	{
		desktopHandle = GetDesktopWindow();
		shellHandle = GetShellWindow();
		IntPtr foregroundWindow = GetForegroundWindow();
		if (!foregroundWindow.Equals(IntPtr.Zero) && !foregroundWindow.Equals(desktopHandle) && !foregroundWindow.Equals(shellHandle))
		{
			GetWindowRect(foregroundWindow, out var rc);
			Rectangle bounds = Screen.FromHandle(foregroundWindow).Bounds;
			if (rc.Bottom - rc.Top == bounds.Height && rc.Right - rc.Left == bounds.Width)
			{
				return true;
			}
		}
		return false;
	}
}
