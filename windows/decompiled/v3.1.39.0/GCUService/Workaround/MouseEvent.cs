using System;
using System.Runtime.InteropServices;
using System.Threading;

namespace Workaround;

internal class MouseEvent
{
	internal static class Win32
	{
		internal struct DISPLAY_DEVICE
		{
			[MarshalAs(UnmanagedType.U4)]
			internal int cb;

			[MarshalAs(UnmanagedType.ByValTStr, SizeConst = 32)]
			internal string DeviceName;

			[MarshalAs(UnmanagedType.ByValTStr, SizeConst = 128)]
			internal string DeviceString;

			[MarshalAs(UnmanagedType.U4)]
			internal int StateFlags;

			[MarshalAs(UnmanagedType.ByValTStr, SizeConst = 128)]
			internal string DeviceID;

			[MarshalAs(UnmanagedType.ByValTStr, SizeConst = 128)]
			internal string DeviceKey;
		}

		internal const int DISPLAY_DEVICE_ACTIVE = 1;

		internal const int DISPLAY_DEVICE_ATTACHED = 2;

		internal const int EDD_GET_DEVICE_INTERFACE_NAME = 1;

		internal const int AttachedToDesktop = 1;

		internal const int MultiDriver = 2;

		internal const int PrimaryDevice = 4;

		internal const int MirroringDriver = 8;

		internal const int VGACompatible = 16;

		internal const int Removable = 32;

		internal const int ModesPruned = 134217728;

		internal const int Remote = 67108864;

		internal const int Disconnect = 33554432;

		internal const uint GENERIC_READ = 2147483648u;

		internal const uint GENERIC_WRITE = 1073741824u;

		internal const uint FILE_SHARE_WRITE = 2u;

		internal const uint FILE_SHARE_READ = 1u;

		internal const uint FILE_FLAG_OVERLAPPED = 1073741824u;

		internal const uint OPEN_EXISTING = 3u;

		internal const uint OPEN_ALWAYS = 4u;

		internal const int WM_SYSCOMMAND = 274;

		internal const int SC_MONITORPOWER = 61808;

		internal const int MONITOR_ON = -1;

		internal const int MONITOR_STANBY = 1;

		internal const int MONITOR_OFF = 2;

		internal const int MOUSEEVENTF_MOVE = 1;

		internal static IntPtr INVALID_HANDLE_VALUE = (IntPtr)(-1);

		internal const string AIRPLANE_DEVICE = "\\\\.\\Vhidcontrol";

		internal const uint IOCTL_VHID_PUSH_BUTTON = 4703232u;

		[DllImport("user32.dll", CharSet = CharSet.Auto, ExactSpelling = true)]
		internal static extern short GetKeyState(int keyCode);

		[DllImport("user32.dll")]
		internal static extern bool EnumDisplayDevices(string lpDevice, uint iDevNum, ref DISPLAY_DEVICE lpDisplayDevice, uint dwFlags);

		[DllImport("user32.dll")]
		internal static extern int SendMessage(int hwnd, int wMsg, int wParam, int lParam);

		[DllImport("user32")]
		internal static extern void mouse_event(int dwFlags, int dx, int dy, int dwData, int dwExtraInfo);

		[DllImport("kernel32.dll", SetLastError = true)]
		internal static extern IntPtr CreateFile([MarshalAs(UnmanagedType.LPStr)] string strName, uint nAccess, uint nShareMode, IntPtr lpSecurity, uint nCreationFlags, uint nAttributes, IntPtr lpTemplate);

		[DllImport("kernel32.dll", SetLastError = true)]
		internal static extern bool CloseHandle(IntPtr hObject);

		[DllImport("kernel32.dll", SetLastError = true)]
		internal static extern bool GetDevicePowerState(IntPtr handle, out bool state);

		[DllImport("kernel32.dll", CharSet = CharSet.Auto, SetLastError = true)]
		internal static extern bool DeviceIoControl(IntPtr handle, uint controlCode, ref uint inBuffer, uint inBufferSize, ref uint outBuffer, uint outBufferSize, out uint bytesReturned, IntPtr overlapped);
	}

	public static void Set(int _dx, int _dy)
	{
		Win32.DISPLAY_DEVICE lpDisplayDevice = default(Win32.DISPLAY_DEVICE);
		lpDisplayDevice.cb = Marshal.SizeOf(lpDisplayDevice);
		try
		{
			for (uint num = 0u; Win32.EnumDisplayDevices(null, num, ref lpDisplayDevice, 0u); num++)
			{
				if ((lpDisplayDevice.StateFlags & 1) != 1)
				{
					continue;
				}
				Console.WriteLine("{0}, {1}", lpDisplayDevice.DeviceName, lpDisplayDevice.StateFlags);
				Win32.DISPLAY_DEVICE lpDisplayDevice2 = default(Win32.DISPLAY_DEVICE);
				lpDisplayDevice2.cb = Marshal.SizeOf(lpDisplayDevice2);
				for (uint num2 = 0u; Win32.EnumDisplayDevices(lpDisplayDevice.DeviceName, num2, ref lpDisplayDevice2, 1u); num2++)
				{
					if ((lpDisplayDevice2.StateFlags & 1) != 1)
					{
						continue;
					}
					Console.WriteLine("{0}, {1}", lpDisplayDevice2.DeviceName, lpDisplayDevice2.StateFlags);
					IntPtr intPtr = Win32.CreateFile(lpDisplayDevice2.DeviceID, 3221225472u, 1u, IntPtr.Zero, 3u, 0u, IntPtr.Zero);
					if (intPtr != IntPtr.Zero)
					{
						bool state = false;
						Win32.GetDevicePowerState(intPtr, out state);
						if (state)
						{
							Win32.mouse_event(1, _dx, _dy, 0, 0);
							Thread.Sleep(40);
						}
						Win32.CloseHandle(intPtr);
					}
				}
			}
		}
		catch (Exception ex)
		{
			Console.WriteLine($"{ex.ToString()}");
		}
	}
}
