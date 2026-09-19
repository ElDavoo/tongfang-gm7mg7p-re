using System.Runtime.InteropServices;
using System.Windows;

namespace MyControlCenter;

[StructLayout(LayoutKind.Sequential, CharSet = CharSet.Auto)]
internal struct MonitorInfoEx
{
	public int cbSize;

	public Rect rcMonitor;

	public Rect rcWork;

	public uint dwFlags;

	[MarshalAs(UnmanagedType.ByValTStr, SizeConst = 32)]
	public string szDeviceName;
}
