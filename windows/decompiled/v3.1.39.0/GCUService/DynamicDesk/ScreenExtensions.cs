using System;
using System.Drawing;
using System.Runtime.InteropServices;
using System.Windows.Forms;

namespace DynamicDesk;

public static class ScreenExtensions
{
	public static void GetDpi(this Screen screen, DpiType dpiType, out uint dpiX, out uint dpiY)
	{
		GetDpiForMonitor(MonitorFromPoint(new Point(screen.Bounds.Left + 1, screen.Bounds.Top + 1), 2u), dpiType, out dpiX, out dpiY);
	}

	[DllImport("User32.dll")]
	private static extern IntPtr MonitorFromPoint([In] Point pt, [In] uint dwFlags);

	[DllImport("Shcore.dll")]
	private static extern IntPtr GetDpiForMonitor([In] IntPtr hmonitor, [In] DpiType dpiType, out uint dpiX, out uint dpiY);
}
