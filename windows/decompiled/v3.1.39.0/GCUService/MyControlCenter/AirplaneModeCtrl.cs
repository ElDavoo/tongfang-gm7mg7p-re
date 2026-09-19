using System;
using System.Runtime.InteropServices;

namespace MyControlCenter;

internal class AirplaneModeCtrl
{
	[DllImport("UWAirplane.dll")]
	private static extern int SwitchAirplaneMode();

	public static void SetAirplaneMode()
	{
		try
		{
			IntPtr intPtr = Win32.CreateFile("\\\\.\\Vhidcontrol", 3221225472u, 3u, IntPtr.Zero, 3u, 0u, IntPtr.Zero);
			if (intPtr != IntPtr.Zero && intPtr != Win32.INVALID_HANDLE_VALUE)
			{
				uint inBuffer = 0u;
				uint outBuffer = 0u;
				uint bytesReturned = 0u;
				Win32.DeviceIoControl(intPtr, 4703232u, ref inBuffer, 0u, ref outBuffer, 0u, out bytesReturned, IntPtr.Zero);
			}
		}
		catch
		{
		}
	}

	public static bool SetAirplaneModeNoDriver()
	{
		try
		{
			return SwitchAirplaneMode() != 1;
		}
		catch (Exception)
		{
			return false;
		}
	}
}
