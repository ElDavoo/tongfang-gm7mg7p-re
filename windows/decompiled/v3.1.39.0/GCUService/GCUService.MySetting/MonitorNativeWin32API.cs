using System;
using System.Runtime.InteropServices;

namespace GCUService.MySetting;

public class MonitorNativeWin32API
{
	public struct RAMP
	{
		[MarshalAs(UnmanagedType.ByValArray, SizeConst = 256)]
		public ushort[] Red;

		[MarshalAs(UnmanagedType.ByValArray, SizeConst = 256)]
		public ushort[] Green;

		[MarshalAs(UnmanagedType.ByValArray, SizeConst = 256)]
		public ushort[] Blue;
	}

	[DllImport("user32.dll", ExactSpelling = true)]
	public static extern IntPtr GetDC(IntPtr hWnd);

	[DllImport("kernel32.dll")]
	public static extern uint GetLastError();

	[DllImport("kernel32.dll", SetLastError = true)]
	private static extern bool SetVolumeLabel(string lpRootPathName, string lpVolumeName);

	[DllImport("gdi32.dll", ExactSpelling = true)]
	public static extern bool SetDeviceGammaRamp(IntPtr hDC, ref RAMP lpRamp);

	[DllImport("gdi32.dll", ExactSpelling = true)]
	public static extern bool GetDeviceGammaRamp(IntPtr hDC, ref RAMP lpRamp);
}
