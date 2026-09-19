using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Drawing;
using System.Drawing.Imaging;
using System.Runtime.InteropServices;
using Microsoft.Win32;

namespace GCUService.MySetting;

public static class ConnectedMonitors
{
	public class MonitorInfo
	{
		public readonly IntPtr MonitorHandle;

		public readonly IntPtr DeviceContextHandle;

		public readonly string DeviceName;

		public readonly bool IsPrimary;

		public readonly Rectangle Bounds;

		public readonly Rectangle WorkArea;

		public void WithMonitorHdc(Action<MonitorInfo, IntPtr> action)
		{
			IntPtr intPtr = DeviceContextHandle;
			bool flag = IntPtr.Zero.Equals(intPtr);
			try
			{
				if (flag)
				{
					intPtr = CreateDC(null, DeviceName, null, IntPtr.Zero);
				}
				action(this, intPtr);
			}
			finally
			{
				if (flag && !IntPtr.Zero.Equals(intPtr))
				{
					DeleteDC(intPtr);
				}
			}
		}

		internal MonitorInfo(IntPtr hMonitor, IntPtr hDeviceContext, string deviceName, bool isPrimary, Rectangle bounds, Rectangle workArea)
		{
			MonitorHandle = hMonitor;
			DeviceContextHandle = hDeviceContext;
			DeviceName = deviceName;
			IsPrimary = isPrimary;
			Bounds = bounds;
			WorkArea = workArea;
		}
	}

	private class EnumMonitorsCallback
	{
		public List<MonitorInfo> Monitors = new List<MonitorInfo>();

		public bool Callback(IntPtr hMonitor, IntPtr hdcMonitor, ref RECT lprcMonitor, IntPtr lparam)
		{
			MONITORINFOEX lpmi = new MONITORINFOEX
			{
				Size = Marshal.SizeOf(typeof(MONITORINFOEX))
			};
			GetMonitorInfo(hMonitor, ref lpmi);
			bool isPrimary = hMonitor == (IntPtr)(-1163005939) || (lpmi.Flags & 1) != 0;
			Rectangle bounds = Rectangle.FromLTRB(lpmi.Monitor.Left, lpmi.Monitor.Top, lpmi.Monitor.Right, lpmi.Monitor.Bottom);
			Rectangle workArea = Rectangle.FromLTRB(lpmi.WorkArea.Left, lpmi.WorkArea.Top, lpmi.WorkArea.Right, lpmi.WorkArea.Bottom);
			string deviceName = lpmi.DeviceName.TrimEnd(default(char));
			Monitors.Add(new MonitorInfo(hMonitor, hdcMonitor, deviceName, isPrimary, bounds, workArea));
			return true;
		}
	}

	private struct RECT
	{
		public int Left;

		public int Top;

		public int Right;

		public int Bottom;
	}

	[StructLayout(LayoutKind.Sequential, CharSet = CharSet.Auto)]
	private struct MONITORINFOEX
	{
		public int Size;

		public RECT Monitor;

		public RECT WorkArea;

		public uint Flags;

		[MarshalAs(UnmanagedType.ByValTStr, SizeConst = 32)]
		public string DeviceName;
	}

	private delegate bool EnumMonitorsDelegate(IntPtr hMonitor, IntPtr hdcMonitor, ref RECT lprcMonitor, IntPtr dwData);

	private static readonly bool _isSingleMonitor = GetSystemMetrics(80) == 0;

	private static Lazy<List<MonitorInfo>> _monitors = new Lazy<List<MonitorInfo>>(GetMonitors, isThreadSafe: true);

	private const string USER32 = "user32.dll";

	private const string GDI32 = "gdi32.dll";

	private const int PRIMARY_MONITOR = -1163005939;

	private const int MONITORINFOF_PRIMARY = 1;

	private const int SM_CMONITORS = 80;

	private const int BITBLT_SRCCOPY = 13369376;

	private const int BITBLT_CAPTUREBLT = 1073741824;

	private const int BITBLT_CAPTURE = 1087111200;

	public static IEnumerable<MonitorInfo> Monitors => _monitors.Value;

	public static event Action MonitorInfoInvalidated;

	public static void CaptureScreen(MonitorInfo mi, string fileName)
	{
		CaptureScreen(mi).Save(fileName);
	}

	public static Bitmap CaptureScreen(MonitorInfo mi)
	{
		Bitmap screenBmp = null;
		mi.WithMonitorHdc(delegate(MonitorInfo m, IntPtr hdc)
		{
			screenBmp = new Bitmap(m.Bounds.Width, m.Bounds.Height, PixelFormat.Format32bppArgb);
			using Graphics graphics = Graphics.FromImage(screenBmp);
			if (BitBlt(hSrcDC: new HandleRef(null, hdc), hDC: new HandleRef(null, graphics.GetHdc()), x: 0, y: 0, nWidth: m.Bounds.Width, nHeight: m.Bounds.Height, xSrc: 0, ySrc: 0, dwRop: 13369376) == 0)
			{
				throw new Win32Exception();
			}
		});
		return screenBmp;
	}

	private static List<MonitorInfo> GetMonitors()
	{
		EnumMonitorsCallback enumMonitorsCallback = new EnumMonitorsCallback();
		EnumDisplayMonitors(IntPtr.Zero, IntPtr.Zero, enumMonitorsCallback.Callback, IntPtr.Zero);
		SystemEvents.DisplaySettingsChanging += OnDisplaySettingsChanging;
		SystemEvents.UserPreferenceChanged += OnUserPreferenceChanged;
		return enumMonitorsCallback.Monitors;
	}

	private static void OnDisplaySettingsChanging(object sender, EventArgs e)
	{
		InvalidateInfo();
	}

	private static void OnUserPreferenceChanged(object sender, UserPreferenceChangedEventArgs e)
	{
		InvalidateInfo();
	}

	private static void InvalidateInfo()
	{
		SystemEvents.DisplaySettingsChanging -= OnDisplaySettingsChanging;
		SystemEvents.UserPreferenceChanged -= OnUserPreferenceChanged;
		_ = _monitors;
		_monitors = new Lazy<List<MonitorInfo>>(GetMonitors, isThreadSafe: true);
		ConnectedMonitors.MonitorInfoInvalidated?.Invoke();
	}

	[DllImport("user32.dll", CharSet = CharSet.Auto)]
	private static extern bool EnumDisplayMonitors(IntPtr hdc, IntPtr lprcClip, EnumMonitorsDelegate lpfnEnum, IntPtr dwData);

	[DllImport("user32.dll", CharSet = CharSet.Auto)]
	private static extern bool GetMonitorInfo(IntPtr hMonitor, ref MONITORINFOEX lpmi);

	[DllImport("user32.dll", CharSet = CharSet.Auto)]
	private static extern int GetSystemMetrics(int nIndex);

	[DllImport("gdi32.dll", CharSet = CharSet.Auto)]
	private static extern IntPtr CreateDC(string lpszDriver, string lpszDevice, string lpszOutput, IntPtr lpInitData);

	[DllImport("gdi32.dll", CharSet = CharSet.Auto)]
	private static extern bool DeleteDC([In] IntPtr hdc);

	[DllImport("gdi32.dll", CharSet = CharSet.Auto)]
	public static extern int BitBlt(HandleRef hDC, int x, int y, int nWidth, int nHeight, HandleRef hSrcDC, int xSrc, int ySrc, int dwRop);
}
